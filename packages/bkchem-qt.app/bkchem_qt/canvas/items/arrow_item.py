"""Arrow graphics item for reaction arrows."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# -- visual constants --
# arrowhead triangle size relative to line width
_ARROWHEAD_LENGTH = 14.0
_ARROWHEAD_HALF_WIDTH = 5.0
# extra padding for bounding rect
_BOUNDS_PADDING = 10.0
# width of the expanded shape path for easier click targeting
_HIT_PATH_WIDTH = 12.0
# selection highlight color
_SELECTION_COLOR = "#3399ff"
# hover highlight color
_HOVER_COLOR = "#66bbff"
# highlight pen width
_HIGHLIGHT_PEN_WIDTH = 2.0


#============================================
class ArrowItem(PySide6.QtWidgets.QGraphicsItem):
	"""Arrow item with configurable heads and optional spline curve.

	Draws a straight line or cubic spline path between two points
	with optional arrowheads at either end.

	Args:
		start: Starting point as (x, y) tuple or QPointF.
		end: Ending point as (x, y) tuple or QPointF.
		parent: Optional parent QGraphicsItem.
	"""

	#============================================
	def __init__(self, start, end, parent=None):
		"""Initialize the arrow item.

		Args:
			start: Starting point as (x, y) tuple or QPointF.
			end: Ending point as (x, y) tuple or QPointF.
			parent: Optional parent QGraphicsItem.
		"""
		super().__init__(parent)
		self._start = PySide6.QtCore.QPointF(start[0], start[1])
		self._end = PySide6.QtCore.QPointF(end[0], end[1])
		self._start_head = False
		self._end_head = True
		self._line_width = 2.0
		self._color = "#000000"
		self._spline = False
		self._control_points = []
		self._hovered = False
		# configure item flags
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
			True,
		)
		self.setAcceptHoverEvents(True)

	# ------------------------------------------------------------------
	# QGraphicsItem interface
	# ------------------------------------------------------------------

	#============================================
	def boundingRect(self) -> PySide6.QtCore.QRectF:
		"""Return the bounding rectangle enclosing the arrow.

		Returns:
			QRectF that encloses the arrow line and arrowheads with padding.
		"""
		# collect all relevant points
		xs = [self._start.x(), self._end.x()]
		ys = [self._start.y(), self._end.y()]
		for cp in self._control_points:
			xs.append(cp.x())
			ys.append(cp.y())
		padding = _BOUNDS_PADDING + self._line_width
		x_min = min(xs) - padding
		y_min = min(ys) - padding
		x_max = max(xs) + padding
		y_max = max(ys) + padding
		rect = PySide6.QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min)
		return rect

	#============================================
	def paint(self, painter: PySide6.QtGui.QPainter,
			option: PySide6.QtWidgets.QStyleOptionGraphicsItem,
			widget: PySide6.QtWidgets.QWidget = None) -> None:
		"""Paint the arrow line/spline and arrowheads.

		Draws selection or hover highlights behind the arrow when the
		item is selected or hovered.

		Args:
			painter: The QPainter provided by the scene.
			option: Style options (unused beyond selection state).
			widget: Target widget (unused).
		"""
		# draw selection or hover highlight
		if self.isSelected() or self._hovered:
			if self.isSelected():
				highlight_color = PySide6.QtGui.QColor(_SELECTION_COLOR)
			else:
				highlight_color = PySide6.QtGui.QColor(_HOVER_COLOR)
			highlight_color.setAlpha(80)
			highlight_pen = PySide6.QtGui.QPen(highlight_color)
			highlight_pen.setWidthF(_HIT_PATH_WIDTH)
			highlight_pen.setCapStyle(PySide6.QtCore.Qt.PenCapStyle.RoundCap)
			painter.setPen(highlight_pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			painter.drawLine(self._start, self._end)

		# set up main pen
		pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(self._color))
		pen.setWidthF(self._line_width)
		pen.setCapStyle(PySide6.QtCore.Qt.PenCapStyle.RoundCap)
		pen.setJoinStyle(PySide6.QtCore.Qt.PenJoinStyle.RoundJoin)
		painter.setPen(pen)
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)

		# draw the line or spline path
		if self._spline and len(self._control_points) >= 2:
			path = PySide6.QtGui.QPainterPath()
			path.moveTo(self._start)
			path.cubicTo(
				self._control_points[0],
				self._control_points[1],
				self._end,
			)
			painter.drawPath(path)
		else:
			painter.drawLine(self._start, self._end)

		# draw arrowheads
		if self._end_head:
			angle = self._angle_between(self._start, self._end)
			self._draw_arrowhead(painter, self._end, angle)
		if self._start_head:
			angle = self._angle_between(self._end, self._start)
			self._draw_arrowhead(painter, self._start, angle)

	#============================================
	def shape(self) -> PySide6.QtGui.QPainterPath:
		"""Return a thick path along the arrow for easier click targeting.

		Returns:
			QPainterPath with a stroked outline around the arrow axis.
		"""
		line_path = PySide6.QtGui.QPainterPath()
		line_path.moveTo(self._start)
		line_path.lineTo(self._end)
		# stroke it into a thick region for hit testing
		stroker = PySide6.QtGui.QPainterPathStroker()
		stroker.setWidth(_HIT_PATH_WIDTH)
		stroker.setCapStyle(PySide6.QtCore.Qt.PenCapStyle.RoundCap)
		thick_path = stroker.createStroke(line_path)
		return thick_path

	# ------------------------------------------------------------------
	# Hover events
	# ------------------------------------------------------------------

	#============================================
	def hoverEnterEvent(self, event) -> None:
		"""Show a highlight when the mouse enters the arrow.

		Args:
			event: The hover enter event.
		"""
		self._hovered = True
		self.update()

	#============================================
	def hoverLeaveEvent(self, event) -> None:
		"""Remove the highlight when the mouse leaves the arrow.

		Args:
			event: The hover leave event.
		"""
		self._hovered = False
		self.update()

	# ------------------------------------------------------------------
	# Arrowhead drawing
	# ------------------------------------------------------------------

	#============================================
	def _draw_arrowhead(self, painter: PySide6.QtGui.QPainter,
			tip: PySide6.QtCore.QPointF, direction_angle: float) -> None:
		"""Draw a triangular arrowhead at tip pointing in direction.

		Args:
			painter: The QPainter to draw with.
			tip: The tip point of the arrowhead.
			direction_angle: Angle in radians from start to tip.
		"""
		# compute the two base points of the triangle
		left_angle = direction_angle + math.pi - 0.35
		right_angle = direction_angle + math.pi + 0.35
		left_x = tip.x() + _ARROWHEAD_LENGTH * math.cos(left_angle)
		left_y = tip.y() + _ARROWHEAD_LENGTH * math.sin(left_angle)
		right_x = tip.x() + _ARROWHEAD_LENGTH * math.cos(right_angle)
		right_y = tip.y() + _ARROWHEAD_LENGTH * math.sin(right_angle)
		# draw filled triangle
		triangle = PySide6.QtGui.QPolygonF([
			tip,
			PySide6.QtCore.QPointF(left_x, left_y),
			PySide6.QtCore.QPointF(right_x, right_y),
		])
		painter.setBrush(PySide6.QtGui.QColor(self._color))
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		painter.drawPolygon(triangle)

	#============================================
	@staticmethod
	def _angle_between(p1: PySide6.QtCore.QPointF,
			p2: PySide6.QtCore.QPointF) -> float:
		"""Compute the angle in radians from p1 to p2.

		Args:
			p1: Starting point.
			p2: Ending point.

		Returns:
			Angle in radians.
		"""
		dx = p2.x() - p1.x()
		dy = p2.y() - p1.y()
		angle = math.atan2(dy, dx)
		return angle

	# ------------------------------------------------------------------
	# Properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def start(self) -> PySide6.QtCore.QPointF:
		"""Starting point of the arrow."""
		return self._start

	#============================================
	@start.setter
	def start(self, point) -> None:
		"""Set the starting point and trigger repaint.

		Args:
			point: New starting point as QPointF or (x, y) tuple.
		"""
		self.prepareGeometryChange()
		if isinstance(point, PySide6.QtCore.QPointF):
			self._start = point
		else:
			self._start = PySide6.QtCore.QPointF(point[0], point[1])
		self.update()

	#============================================
	@property
	def end(self) -> PySide6.QtCore.QPointF:
		"""Ending point of the arrow."""
		return self._end

	#============================================
	@end.setter
	def end(self, point) -> None:
		"""Set the ending point and trigger repaint.

		Args:
			point: New ending point as QPointF or (x, y) tuple.
		"""
		self.prepareGeometryChange()
		if isinstance(point, PySide6.QtCore.QPointF):
			self._end = point
		else:
			self._end = PySide6.QtCore.QPointF(point[0], point[1])
		self.update()

	#============================================
	@property
	def start_head(self) -> bool:
		"""Whether the arrow has a head at the start."""
		return self._start_head

	#============================================
	@start_head.setter
	def start_head(self, value: bool) -> None:
		self._start_head = bool(value)
		self.update()

	#============================================
	@property
	def end_head(self) -> bool:
		"""Whether the arrow has a head at the end."""
		return self._end_head

	#============================================
	@end_head.setter
	def end_head(self, value: bool) -> None:
		self._end_head = bool(value)
		self.update()

	#============================================
	@property
	def line_width(self) -> float:
		"""Line width in pixels."""
		return self._line_width

	#============================================
	@line_width.setter
	def line_width(self, value: float) -> None:
		self._line_width = float(value)
		self.update()

	#============================================
	@property
	def color(self) -> str:
		"""Arrow color as hex string."""
		return self._color

	#============================================
	@color.setter
	def color(self, value: str) -> None:
		self._color = str(value)
		self.update()

	#============================================
	@property
	def spline(self) -> bool:
		"""Whether the arrow uses a spline curve path."""
		return self._spline

	#============================================
	@spline.setter
	def spline(self, value: bool) -> None:
		self._spline = bool(value)
		self.update()
