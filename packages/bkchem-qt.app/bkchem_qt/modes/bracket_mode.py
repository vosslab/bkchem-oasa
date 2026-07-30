"""Transient rectangular-bracket gesture for backend-owned CDML."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.modes.base_mode


_BRACKET_MARGIN = 6.0


#============================================
class BracketMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Create one backend-authoritative rectangular bracket pair.

	Qt owns only the drag preview and selected-atom geometry lookup.  The live
	session owns the revision-bound immutable operation and canonical reproject.
	"""

	#============================================
	def __init__(
			self, view: PySide6.QtWidgets.QGraphicsView,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		super().__init__(view, parent)
		self._name = "Bracket"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		self._persistent_operation = None
		self._drag_start = None
		self._preview_rect = None
		self._preview_scene = None

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return the one supported rectangular-bracket interaction hint."""
		return "Click to bracket selected atoms | Drag to draw bracket region"

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install or clear the session-owned immutable-request callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Bracket persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Use selected atoms immediately or begin one transient drag."""
		scene = self._env.scene
		if scene is None:
			self._clear_gesture()
			return
		atom_items = tuple(
			item for item in scene.selectedItems()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		)
		if atom_items:
			# Read selection geometry while its projection is live, then retire any
			# interrupted drag before a backend acceptance can replace that projection.
			bounds = _expanded_union_bounds(atom_items)
			self._clear_gesture()
			self._submit_bounds(bounds)
			return
		self._drag_start = PySide6.QtCore.QPointF(scene_pos)

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Replace the disposable dashed rectangle during a manual drag."""
		if self._drag_start is None:
			return
		self._retire_preview_rect()
		scene = self._env.scene
		if scene is None:
			self._drag_start = None
			return
		pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(100, 100, 100, 128))
		pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
		pen.setWidthF(1.0)
		self._preview_rect = scene.addRect(_make_rect(self._drag_start, scene_pos), pen)
		self._preview_scene = scene

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Retire preview before submitting one accepted-size bracket request."""
		try:
			self._retire_preview_rect()
			if self._drag_start is None or self._env.scene is None:
				return
			rectangle = _make_rect(self._drag_start, scene_pos)
			if rectangle.width() > 10.0 and rectangle.height() > 10.0:
				self._submit_bounds(_rect_bounds(rectangle))
		finally:
			self._drag_start = None

	#============================================
	def deactivate(self) -> None:
		"""Retire every transient item before the mode becomes inactive."""
		self._clear_gesture()
		super().deactivate()

	#============================================
	def _submit_bounds(self, bounds: tuple[float, float, float, float]) -> None:
		"""Submit the sole plain-data bracket operation and report its outcome."""
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		from bkchem_qt.models.document_session import PersistentOperationRequest
		outcome = self._persistent_operation(PersistentOperationRequest(
			"bracket.add", "Add Brackets", (("bounds", bounds),),
		))
		self.status_message.emit(outcome.message)

	#============================================
	def _clear_gesture(self) -> None:
		"""Retire preview and clear all terminal gesture state."""
		self._retire_preview_rect()
		self._drag_start = None

	#============================================
	def _retire_preview_rect(self) -> None:
		"""Terminally retire the known preview wrapper before releasing it."""
		preview_rect = self._preview_rect
		preview_scene = self._preview_scene
		if preview_rect is None:
			return
		try:
			coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
			if preview_scene is None:
				coordinator.retire_detached_projection_items(
					[preview_rect], reaper=self._graphics_retirement_reaper,
				)
			else:
				coordinator.retire_scene_projection_items(
					preview_scene, [preview_rect],
					reaper=self._graphics_retirement_reaper,
				)
			coordinator.raise_if_callback_failed("Bracket preview retirement failed")
		finally:
			self._preview_rect = None
			self._preview_scene = None


#============================================
def _make_rect(
		first: PySide6.QtCore.QPointF, second: PySide6.QtCore.QPointF,
		) -> PySide6.QtCore.QRectF:
	"""Return the normalized rectangle spanned by two scene positions."""
	return PySide6.QtCore.QRectF(
		min(first.x(), second.x()), min(first.y(), second.y()),
		abs(second.x() - first.x()), abs(second.y() - first.y()),
	)


#============================================
def _rect_bounds(rectangle: PySide6.QtCore.QRectF) -> tuple[float, float, float, float]:
	"""Return one immutable left, top, right, bottom scene-space tuple."""
	return rectangle.left(), rectangle.top(), rectangle.right(), rectangle.bottom()


#============================================
def _expanded_union_bounds(
		items: tuple[bkchem_qt.canvas.items.atom_item.AtomItem, ...],
		) -> tuple[float, float, float, float]:
	"""Return selected atom visual bounds expanded by the historical margin."""
	rectangle = PySide6.QtCore.QRectF(items[0].sceneBoundingRect())
	for item in items[1:]:
		rectangle = rectangle.united(item.sceneBoundingRect())
	rectangle.adjust(-_BRACKET_MARGIN, -_BRACKET_MARGIN, _BRACKET_MARGIN, _BRACKET_MARGIN)
	return _rect_bounds(rectangle)
