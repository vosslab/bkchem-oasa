"""Arrow drawing mode."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode

# visual constants for the preview arrow
_PREVIEW_PEN_COLOR = "#888888"
_PREVIEW_PEN_WIDTH = 1.5
_PREVIEW_PEN_STYLE = PySide6.QtCore.Qt.PenStyle.DashLine


#============================================
class ArrowMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for drawing reaction arrows.

	Click to set the start point, drag to preview, and release to
	create the arrow. The preview is shown as a dashed line while
	dragging.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the arrow mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Arrow"
		# preview line item shown during drag
		self._preview_line = None
		# start point in scene coordinates
		self._start_point = None
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Set the arrow start point.

		Args:
			scene_pos: Position in scene coordinates where the arrow begins.
			event: The mouse event.
		"""
		self._start_point = scene_pos
		self.status_message.emit("Drag to set arrow endpoint")

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Update the preview arrow line during drag.

		Creates a dashed line from the start point to the current
		mouse position to show where the arrow will be placed.

		Args:
			scene_pos: Current position in scene coordinates.
			event: The mouse event.
		"""
		if self._start_point is None:
			return
		scene = self._view.scene()
		if scene is None:
			return
		# remove old preview line if it exists
		if self._preview_line is not None:
			scene.removeItem(self._preview_line)
			self._preview_line = None
		# create a new preview line
		pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(_PREVIEW_PEN_COLOR))
		pen.setWidthF(_PREVIEW_PEN_WIDTH)
		pen.setStyle(_PREVIEW_PEN_STYLE)
		self._preview_line = scene.addLine(
			self._start_point.x(), self._start_point.y(),
			scene_pos.x(), scene_pos.y(),
			pen,
		)

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Create the final arrow item and clean up the preview.

		Removes the preview dashed line and adds an arrow line item
		with an arrowhead to the scene.

		Args:
			scene_pos: End position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._view.scene()
		if scene is None:
			self._start_point = None
			return
		# remove preview line
		if self._preview_line is not None:
			scene.removeItem(self._preview_line)
			self._preview_line = None
		# only create the arrow if we have a start point and some distance
		if self._start_point is not None:
			dx = scene_pos.x() - self._start_point.x()
			dy = scene_pos.y() - self._start_point.y()
			# minimum distance threshold to avoid accidental zero-length arrows
			if (dx * dx + dy * dy) > 25.0:
				_create_arrow_item(scene, self._start_point, scene_pos)
		self._start_point = None
		self.status_message.emit("Arrow mode active")

	#============================================
	def deactivate(self) -> None:
		"""Clean up the preview line when leaving arrow mode."""
		if self._preview_line is not None:
			scene = self._view.scene()
			if scene is not None:
				scene.removeItem(self._preview_line)
			self._preview_line = None
		self._start_point = None
		super().deactivate()


#============================================
def _create_arrow_item(scene, start: PySide6.QtCore.QPointF,
					   end: PySide6.QtCore.QPointF) -> None:
	"""Add a line with an arrowhead to the scene.

	Draws a solid line from start to end and adds a small triangular
	arrowhead at the end point.

	Args:
		scene: QGraphicsScene to add the arrow to.
		start: Arrow start position.
		end: Arrow end position (where the arrowhead points).
	"""
	import math
	# draw the main line
	pen = PySide6.QtGui.QPen(PySide6.QtCore.Qt.GlobalColor.black)
	pen.setWidthF(1.5)
	line_item = scene.addLine(
		start.x(), start.y(), end.x(), end.y(), pen,
	)
	line_item.setFlag(
		PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
	)
	# compute arrowhead triangle
	arrow_size = 10.0
	angle = math.atan2(end.y() - start.y(), end.x() - start.x())
	# two points of the arrowhead, offset from the end point
	angle_offset = math.pi / 6  # 30 degrees
	p1_x = end.x() - arrow_size * math.cos(angle - angle_offset)
	p1_y = end.y() - arrow_size * math.sin(angle - angle_offset)
	p2_x = end.x() - arrow_size * math.cos(angle + angle_offset)
	p2_y = end.y() - arrow_size * math.sin(angle + angle_offset)
	# create the arrowhead polygon
	arrowhead = PySide6.QtGui.QPolygonF([
		end,
		PySide6.QtCore.QPointF(p1_x, p1_y),
		PySide6.QtCore.QPointF(p2_x, p2_y),
	])
	head_item = scene.addPolygon(
		arrowhead,
		PySide6.QtGui.QPen(PySide6.QtCore.Qt.GlobalColor.black),
		PySide6.QtGui.QBrush(PySide6.QtCore.Qt.GlobalColor.black),
	)
	head_item.setFlag(
		PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
	)
