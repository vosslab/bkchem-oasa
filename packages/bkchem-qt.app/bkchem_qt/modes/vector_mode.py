"""Vector graphics mode for rectangles, ovals, and lines."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.graphics_retirement

# preview pen style
_PREVIEW_STYLE = PySide6.QtCore.Qt.PenStyle.DashLine


#============================================
class VectorMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for drawing vector graphics shapes.

	Supports drawing rectangles, ovals, and lines on the canvas.
	Click to start a shape, drag to size it, release to finalize.
	The shape type can be switched via submodes.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(
			self,
			view: PySide6.QtWidgets.QGraphicsView,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize the vector graphics mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Vector"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		# current complete-CDML presentation shape
		self._shape_type = "rect"
		self._persistent_operation = None
		# drag state
		self._drag_start = None
		self._preview_item = None
		self._preview_scene = None

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return vector mode hint for the status bar.

		Returns:
			A short description of available interactions.
		"""
		return f"Drag to draw {self._shape_type}"

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install or clear the generic immutable-request callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Vector persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Switch the active shape type when a submode is selected.

		Args:
			submode_index: Group index of the changed submode.
			name: Key string of the newly selected submode.
		"""
		# map submode keys to shape types
		shape_map = {
			"rectangle": "rect",
			"oval": "oval",
			"polyline": "polyline",
		}
		shape = shape_map[name]
		self._shape_type = shape
		self.status_message.emit(f"Vector: {shape}")

	#============================================
	def mouse_press(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Start drawing a shape at the click position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self._drag_start = scene_pos

	#============================================
	def mouse_move(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Update the shape preview during drag.

		Args:
			scene_pos: Current position in scene coordinates.
			event: The mouse event.
		"""
		if self._drag_start is None:
			return
		self._retire_preview_item()
		scene = self._env.scene
		if scene is None:
			return
		# build preview pen
		pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(80, 80, 80, 150))
		pen.setWidthF(1.0)
		pen.setStyle(_PREVIEW_STYLE)
		# create shape preview
		if self._shape_type == "polyline":
			self._preview_item = scene.addLine(
				self._drag_start.x(), self._drag_start.y(),
				scene_pos.x(), scene_pos.y(), pen,
			)
		else:
			rect = _make_rect(self._drag_start, scene_pos)
			if self._shape_type == "oval":
				self._preview_item = scene.addEllipse(rect, pen)
			else:
				self._preview_item = scene.addRect(rect, pen)
		self._preview_scene = scene

	#============================================
	def mouse_release(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Submit one backend-authoritative Vector candidate request.

		Args:
			scene_pos: End position in scene coordinates.
			event: The mouse event.
		"""
		self._retire_preview_item()
		if self._env.scene is None:
			self._drag_start = None
			return
		if self._drag_start is None:
			return
		# minimum drag distance
		dx = abs(scene_pos.x() - self._drag_start.x())
		dy = abs(scene_pos.y() - self._drag_start.y())
		if dx < 5.0 and dy < 5.0:
			self._drag_start = None
			return
		if self._persistent_operation is None:
			message = "Document cannot accept a persistent edit"
		else:
			from bkchem_qt.models import document_session
			request = document_session.PersistentOperationRequest(
				"vector.add", self._shape_type.title(),
				(
					("shape", self._shape_type),
					("start", (self._drag_start.x(), self._drag_start.y())),
					("end", (scene_pos.x(), scene_pos.y())),
				),
			)
			outcome = self._persistent_operation(request)
			message = outcome.message
		self._drag_start = None
		self.status_message.emit(message)

	#============================================
	def deactivate(self) -> None:
		"""Clean up preview when leaving vector mode."""
		self._retire_preview_item()
		self._drag_start = None
		super().deactivate()

	#============================================
	def _retire_preview_item(self) -> None:
		"""Terminally retire the known preview item before releasing its wrapper."""
		preview_item = self._preview_item
		preview_scene = self._preview_scene
		if preview_item is None:
			return
		try:
			coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
			if preview_scene is None:
				coordinator.retire_detached_projection_items(
					[preview_item], reaper=self._graphics_retirement_reaper,
				)
			else:
				coordinator.retire_scene_projection_items(
					preview_scene, [preview_item],
					reaper=self._graphics_retirement_reaper,
				)
			coordinator.raise_if_callback_failed("Vector preview retirement failed")
		finally:
			self._preview_item = None
			self._preview_scene = None


#============================================
def _make_rect(
		p1: PySide6.QtCore.QPointF,
		p2: PySide6.QtCore.QPointF) -> PySide6.QtCore.QRectF:
	"""Build a QRectF from two corner points.

	Args:
		p1: First corner point.
		p2: Second corner point.

	Returns:
		Normalized QRectF enclosing both points.
	"""
	x1 = min(p1.x(), p2.x())
	y1 = min(p1.y(), p2.y())
	x2 = max(p1.x(), p2.x())
	y2 = max(p1.y(), p2.y())
	rectangle = PySide6.QtCore.QRectF(x1, y1, x2 - x1, y2 - y1)
	return rectangle
