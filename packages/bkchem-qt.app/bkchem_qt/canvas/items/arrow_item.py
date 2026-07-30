"""Arrow graphics item for reaction arrows."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.render_ops_painter

# -- visual constants --
# arrowhead triangle size relative to line width
_ARROWHEAD_LENGTH = 14.0
_ARROWHEAD_HALF_WIDTH = 5.0
# width of the expanded shape path for easier click targeting
_HIT_PATH_WIDTH = 12.0


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
	def __init__(self, start: object, end: object,
			parent: PySide6.QtWidgets.QGraphicsItem | None = None) -> None:
		"""Initialize the arrow item.

		Args:
			start: Starting point as (x, y) tuple or QPointF.
			end: Ending point as (x, y) tuple or QPointF.
			parent: Optional parent QGraphicsItem.
		"""
		super().__init__(parent)
		if isinstance(start, PySide6.QtCore.QPointF):
			self._start = PySide6.QtCore.QPointF(start)
		else:
			self._start = PySide6.QtCore.QPointF(start[0], start[1])
		if isinstance(end, PySide6.QtCore.QPointF):
			self._end = PySide6.QtCore.QPointF(end)
		else:
			self._end = PySide6.QtCore.QPointF(end[0], end[1])
		self._start_head = False
		self._end_head = True
		self._line_width = 2.0
		self._color = None
		self._spline = False
		self._control_points: list[PySide6.QtCore.QPointF] = []
		self._hovered = False
		self._disposed = False
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
		bounding_rect = self._interaction_path().boundingRect()
		return bounding_rect

	#============================================
	def paint(self, painter: PySide6.QtGui.QPainter,
			option: PySide6.QtWidgets.QStyleOptionGraphicsItem,
			widget: PySide6.QtWidgets.QWidget | None = None) -> None:
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
				highlight_color = PySide6.QtGui.QColor(
					bkchem_qt.canvas.items.render_ops_painter.get_canvas_color(
						"selection",
					),
				)
			else:
				highlight_color = PySide6.QtGui.QColor(
					bkchem_qt.canvas.items.render_ops_painter.get_canvas_color("hover"),
				)
			highlight_color.setAlpha(80)
			highlight_pen = PySide6.QtGui.QPen(highlight_color)
			highlight_pen.setWidthF(_HIT_PATH_WIDTH)
			highlight_pen.setCapStyle(PySide6.QtCore.Qt.PenCapStyle.RoundCap)
			painter.setPen(highlight_pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			painter.drawPath(self._axis_path())

		# set up main pen - resolve color at paint time for theme support
		if self._color is None:
			resolved_color = bkchem_qt.canvas.items.render_ops_painter._default_color
		else:
			resolved_color = PySide6.QtGui.QColor(self._color)
		pen = PySide6.QtGui.QPen(resolved_color)
		pen.setWidthF(self._line_width)
		pen.setCapStyle(PySide6.QtCore.Qt.PenCapStyle.RoundCap)
		pen.setJoinStyle(PySide6.QtCore.Qt.PenJoinStyle.RoundJoin)
		painter.setPen(pen)
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)

		painter.drawPath(self._axis_path())

		# draw arrowheads
		if self._end_head:
			self._draw_arrowhead(painter, self._end, self._end_head_angle())
		if self._start_head:
			self._draw_arrowhead(painter, self._start, self._start_head_angle())

	#============================================
	def shape(self) -> PySide6.QtGui.QPainterPath:
		"""Return a thick path along the arrow for easier click targeting.

		Returns:
			QPainterPath with a stroked outline around the arrow axis.
		"""
		interaction_path = self._interaction_path()
		return interaction_path

	#============================================
	def _axis_path(self) -> PySide6.QtGui.QPainterPath:
		"""Return the one geometric path used for line, curve, and hit testing."""
		path = PySide6.QtGui.QPainterPath(self._start)
		if not self._spline or not self._control_points:
			path.lineTo(self._end)
		elif len(self._control_points) == 1:
			path.quadTo(self._control_points[0], self._end)
		elif len(self._control_points) == 2:
			path.cubicTo(
				self._control_points[0], self._control_points[1], self._end,
			)
		else:
			self._append_smooth_multi_control_path(path)
		return path

	#============================================
	def _append_smooth_multi_control_path(
			self, path: PySide6.QtGui.QPainterPath,
			) -> None:
		"""Append a deterministic smooth quadratic path for three or more controls.

		Adjacent control-point midpoints join successive quadratic segments with
		matching tangents, so imported multi-control arrows remain continuous.
		"""
		for index in range(len(self._control_points) - 1):
			control = self._control_points[index]
			next_control = self._control_points[index + 1]
			midpoint = PySide6.QtCore.QPointF(
				(control.x() + next_control.x()) / 2.0,
				(control.y() + next_control.y()) / 2.0,
			)
			path.quadTo(control, midpoint)
		path.quadTo(self._control_points[-1], self._end)

	#============================================
	def _interaction_path(self) -> PySide6.QtGui.QPainterPath:
		"""Return the selectable region enclosing the axis and active heads."""
		stroker = PySide6.QtGui.QPainterPathStroker()
		stroker.setWidth(max(_HIT_PATH_WIDTH, self._line_width))
		stroker.setCapStyle(PySide6.QtCore.Qt.PenCapStyle.RoundCap)
		stroker.setJoinStyle(PySide6.QtCore.Qt.PenJoinStyle.RoundJoin)
		path = stroker.createStroke(self._axis_path())
		if self._end_head:
			path.addPolygon(self._arrowhead_polygon(self._end, self._end_head_angle()))
		if self._start_head:
			path.addPolygon(self._arrowhead_polygon(
				self._start, self._start_head_angle(),
			))
		return path

	#============================================
	def _end_head_angle(self) -> float:
		"""Return the tangent direction of the arrow at its end."""
		if self._spline and self._control_points:
			angle = self._angle_between(self._control_points[-1], self._end)
		else:
			angle = self._angle_between(self._start, self._end)
		return angle

	#============================================
	def _start_head_angle(self) -> float:
		"""Return the outward tangent direction of the arrow at its start."""
		if self._spline and self._control_points:
			angle = self._angle_between(self._control_points[0], self._start)
		else:
			angle = self._angle_between(self._end, self._start)
		return angle

	# ------------------------------------------------------------------
	# Hover events
	# ------------------------------------------------------------------

	#============================================
	def hoverEnterEvent(self, event: PySide6.QtWidgets.QGraphicsSceneHoverEvent) -> None:
		"""Show a highlight when the mouse enters the arrow.

		Args:
			event: The hover enter event.
		"""
		self._hovered = True
		self.update()

	#============================================
	def hoverLeaveEvent(self, event: PySide6.QtWidgets.QGraphicsSceneHoverEvent) -> None:
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
		triangle = self._arrowhead_polygon(tip, direction_angle)
		# resolve color at paint time for theme support
		if self._color is None:
			fill_color = bkchem_qt.canvas.items.render_ops_painter._default_color
		else:
			fill_color = PySide6.QtGui.QColor(self._color)
		painter.setBrush(fill_color)
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		painter.drawPolygon(triangle)

	#============================================
	@staticmethod
	def _arrowhead_polygon(tip: PySide6.QtCore.QPointF,
			direction_angle: float) -> PySide6.QtGui.QPolygonF:
		"""Return the filled triangular geometry for an arrowhead."""
		left_angle = direction_angle + math.pi - 0.35
		right_angle = direction_angle + math.pi + 0.35
		left = PySide6.QtCore.QPointF(
			tip.x() + _ARROWHEAD_LENGTH * math.cos(left_angle),
			tip.y() + _ARROWHEAD_LENGTH * math.sin(left_angle),
		)
		right = PySide6.QtCore.QPointF(
			tip.x() + _ARROWHEAD_LENGTH * math.cos(right_angle),
			tip.y() + _ARROWHEAD_LENGTH * math.sin(right_angle),
		)
		polygon = PySide6.QtGui.QPolygonF([tip, left, right])
		return polygon

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
	def start(self, point: object) -> None:
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
	def end(self, point: object) -> None:
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
		self.prepareGeometryChange()
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
		self.prepareGeometryChange()
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
		self.prepareGeometryChange()
		self._line_width = float(value)
		self.update()

	#============================================
	@property
	def color(self) -> str | None:
		"""Arrow color as hex string."""
		return self._color

	#============================================
	@color.setter
	def color(self, value: str | None) -> None:
		self._color = None if value is None else str(value)
		self.update()

	#============================================
	@property
	def spline(self) -> bool:
		"""Whether the arrow uses a spline curve path."""
		return self._spline

	#============================================
	@spline.setter
	def spline(self, value: bool) -> None:
		self.prepareGeometryChange()
		self._spline = bool(value)
		self.update()

	#============================================
	@property
	def control_points(self) -> list:
		"""Return a copy of the spline control points."""
		points = list(self._control_points)
		return points

	#============================================
	@control_points.setter
	def control_points(self, points: list) -> None:
		"""Set spline control points and refresh the item geometry."""
		self.prepareGeometryChange()
		converted = []
		for point in points:
			if isinstance(point, PySide6.QtCore.QPointF):
				converted.append(PySide6.QtCore.QPointF(point))
			else:
				converted.append(PySide6.QtCore.QPointF(point[0], point[1]))
		self._control_points = converted
		self.update()

	#============================================
	def dispose(self) -> None:
		"""Release projection-owned callbacks before scene teardown."""
		self._disposed = True
