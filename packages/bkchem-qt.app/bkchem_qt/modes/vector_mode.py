"""Frontend-only gesture mode for backend-owned geometric presentations."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.modes.base_mode

_PREVIEW_STYLE = PySide6.QtCore.Qt.PenStyle.DashLine
_BOUNDED_SHAPES = frozenset({"rect", "square", "oval", "circle"})
_PATH_SHAPES = frozenset({"polyline", "polygon"})
_SHAPES = _BOUNDED_SHAPES | _PATH_SHAPES


#============================================
class VectorMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Create a typed geometric request from drag or accessible point gestures."""

	#============================================
	def __init__(
			self, view: PySide6.QtWidgets.QGraphicsView,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize the Vector gesture and preview state."""
		super().__init__(view, parent)
		self._name = "Vector"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		self._shape_type = "rect"
		self._persistent_operation = None
		self._drag_start = None
		self._path_points = []
		self._preview_item = None
		self._preview_scene = None

	#============================================
	@property
	def status_hint(self) -> str:
		"""Describe the next usable Vector interaction in plain language."""
		if self._shape_type in _PATH_SHAPES:
			finish = "three" if self._shape_type == "polygon" else "two"
			return f"Click points for a {self._shape_type}; double-click, Enter, or right-click after {finish} points"
		return f"Drag to draw a {self._shape_type}"

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install or clear the generic immutable-request callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Vector persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Select one declared shape and discard an unfinished prior gesture."""
		if submode_index != 0:
			raise ValueError("Vector submode group is unsupported")
		shape_map = {
			"rectangle": "rect", "square": "square", "oval": "oval",
			"circle": "circle", "polyline": "polyline", "polygon": "polygon",
		}
		if name not in shape_map:
			raise ValueError("Vector shape is unsupported")
		self._reset_gesture()
		self._shape_type = shape_map[name]
		self.status_message.emit(self.status_hint)

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Begin a bounded drag or append one explicit path vertex."""
		if self._shape_type in _PATH_SHAPES:
			self._append_path_point(scene_pos)
			return
		self._drag_start = scene_pos

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Refresh transient feedback for the active Vector gesture."""
		if self._shape_type in _PATH_SHAPES:
			if self._path_points:
				self._show_path_preview(scene_pos)
			return
		if self._drag_start is not None:
			self._show_bounded_preview(scene_pos)

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Commit a bounded gesture; path gestures finish explicitly elsewhere."""
		if self._shape_type in _PATH_SHAPES:
			return
		start = self._drag_start
		self._retire_preview_item()
		self._drag_start = None
		if start is None:
			return
		end = self._constrained_end(start, scene_pos)
		if abs(end.x() - start.x()) < 5.0 and abs(end.y() - start.y()) < 5.0:
			self.status_message.emit("Drag farther to draw the shape")
			return
		self._submit_points(((start.x(), start.y()), (end.x(), end.y())))

	#============================================
	def mouse_double_click(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Finish an explicit polyline or polygon without adding a duplicate vertex."""
		if self._shape_type not in _PATH_SHAPES:
			return
		self._append_path_point(scene_pos)
		self._finish_path()

	#============================================
	def mouse_press3(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Finish a valid path or cancel an unfinished path with an actionable hint."""
		if self._shape_type not in _PATH_SHAPES:
			return
		if self._path_is_valid():
			self._finish_path()
		else:
			self._reset_gesture()
			self.status_message.emit("Path cancelled; click points to begin again")

	#============================================
	def key_press(self, event: object) -> None:
		"""Offer keyboard completion and cancellation for multi-point gestures."""
		if self._shape_type not in _PATH_SHAPES or not hasattr(event, "key"):
			return
		key = event.key()
		if key in {PySide6.QtCore.Qt.Key.Key_Return, PySide6.QtCore.Qt.Key.Key_Enter}:
			self._finish_path()
		elif key == PySide6.QtCore.Qt.Key.Key_Escape:
			self._reset_gesture()
			self.status_message.emit("Path cancelled; click points to begin again")

	#============================================
	def deactivate(self) -> None:
		"""Discard every transient path and preview before another mode activates."""
		self._reset_gesture()
		super().deactivate()

	#============================================
	def _append_path_point(self, scene_pos: PySide6.QtCore.QPointF) -> None:
		"""Keep a meaningful ordered vertex and show a durable next-step hint."""
		point = scene_pos.x(), scene_pos.y()
		if self._path_points and self._path_points[-1] == point:
			return
		self._path_points.append(point)
		self._show_path_preview(scene_pos)
		self.status_message.emit(self.status_hint)

	#============================================
	def _finish_path(self) -> None:
		"""Submit one valid immutable point sequence or keep the gesture editable."""
		if not self._path_is_valid():
			minimum = 3 if self._shape_type == "polygon" else 2
			self.status_message.emit(f"Add {minimum} distinct points to finish the {self._shape_type}")
			return
		points = tuple(self._path_points)
		self._reset_gesture()
		self._submit_points(points)

	#============================================
	def _path_is_valid(self) -> bool:
		"""Return whether the transient path meets the backend's minimum grammar."""
		minimum = 3 if self._shape_type == "polygon" else 2
		return len(self._path_points) >= minimum

	#============================================
	def _submit_points(self, points: tuple[tuple[float, float], ...]) -> None:
		"""Send only declared geometry intent to the session-owned backend adapter."""
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		from bkchem_qt.models import document_session
		request = document_session.PersistentOperationRequest(
			"vector.add", "Add " + self._shape_type.title(),
			(("kind", self._shape_type), ("points", points)),
		)
		outcome = self._persistent_operation(request)
		self.status_message.emit(outcome.message)

	#============================================
	def _constrained_end(
			self, start: PySide6.QtCore.QPointF, end: PySide6.QtCore.QPointF,
			) -> PySide6.QtCore.QPointF:
		"""Constrain square and circle drags to equal signed extents."""
		if self._shape_type not in {"square", "circle"}:
			return end
		delta_x = end.x() - start.x()
		delta_y = end.y() - start.y()
		side = max(abs(delta_x), abs(delta_y))
		constrained_x = side if delta_x >= 0.0 else -side
		constrained_y = side if delta_y >= 0.0 else -side
		return PySide6.QtCore.QPointF(start.x() + constrained_x, start.y() + constrained_y)

	#============================================
	def _show_bounded_preview(self, scene_pos: PySide6.QtCore.QPointF) -> None:
		"""Render one disposable rectangle or oval preview from the drag endpoints."""
		start = self._drag_start
		if start is None:
			return
		self._retire_preview_item()
		scene = self._env.scene
		if scene is None:
			return
		end = self._constrained_end(start, scene_pos)
		pen = _preview_pen()
		rectangle = _make_rect(start, end)
		if self._shape_type in {"oval", "circle"}:
			self._preview_item = scene.addEllipse(rectangle, pen)
		else:
			self._preview_item = scene.addRect(rectangle, pen)
		self._preview_scene = scene

	#============================================
	def _show_path_preview(self, cursor: PySide6.QtCore.QPointF) -> None:
		"""Render the accumulated vertices and current cursor as disposable feedback."""
		self._retire_preview_item()
		scene = self._env.scene
		if scene is None or not self._path_points:
			return
		path = PySide6.QtGui.QPainterPath()
		first_x, first_y = self._path_points[0]
		path.moveTo(first_x, first_y)
		for point_x, point_y in self._path_points[1:]:
			path.lineTo(point_x, point_y)
		path.lineTo(cursor.x(), cursor.y())
		if self._shape_type == "polygon" and len(self._path_points) >= 2:
			path.lineTo(first_x, first_y)
		self._preview_item = scene.addPath(path, _preview_pen())
		self._preview_scene = scene

	#============================================
	def _reset_gesture(self) -> None:
		"""Discard all temporary geometry without submitting a mutation."""
		self._retire_preview_item()
		self._drag_start = None
		self._path_points = []

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
					preview_scene, [preview_item], reaper=self._graphics_retirement_reaper,
				)
			coordinator.raise_if_callback_failed("Vector preview retirement failed")
		finally:
			self._preview_item = None
			self._preview_scene = None


#============================================
def _preview_pen() -> PySide6.QtGui.QPen:
	"""Create the shared neutral dashed preview pen."""
	pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(80, 80, 80, 150))
	pen.setWidthF(1.0)
	pen.setStyle(_PREVIEW_STYLE)
	return pen


#============================================
def _make_rect(
		p1: PySide6.QtCore.QPointF, p2: PySide6.QtCore.QPointF,
		) -> PySide6.QtCore.QRectF:
	"""Build the normalized preview rectangle enclosing two scene points."""
	x1 = min(p1.x(), p2.x())
	y1 = min(p1.y(), p2.y())
	x2 = max(p1.x(), p2.x())
	y2 = max(p1.y(), p2.y())
	rectangle = PySide6.QtCore.QRectF(x1, y1, x2 - x1, y2 - y1)
	return rectangle
