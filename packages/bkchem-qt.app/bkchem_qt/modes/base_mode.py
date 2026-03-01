"""Abstract base mode for BKChem-Qt interaction modes."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item


#============================================
class BaseMode(PySide6.QtCore.QObject):
	"""Abstract base class for all interaction modes.

	Modes handle mouse and keyboard events dispatched from ChemView.
	Each mode defines cursor appearance and event behavior. Subclasses
	override the event handler methods to implement mode-specific logic.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	# emitted to update the status bar with contextual hints
	status_message = PySide6.QtCore.Signal(str)

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the base mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._view = view
		self._name = "Base"
		self._cursor = PySide6.QtCore.Qt.CursorShape.ArrowCursor

	# ------------------------------------------------------------------
	# Properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def name(self) -> str:
		"""Return the human-readable mode name."""
		return self._name

	#============================================
	@property
	def cursor(self) -> PySide6.QtCore.Qt.CursorShape:
		"""Return the cursor shape for this mode."""
		return self._cursor

	# ------------------------------------------------------------------
	# Lifecycle
	# ------------------------------------------------------------------

	#============================================
	def activate(self) -> None:
		"""Called when this mode becomes active.

		Sets the cursor on the view and emits an initial status message.
		Subclasses should call super().activate() first.
		"""
		self._view.setCursor(PySide6.QtGui.QCursor(self._cursor))
		self.status_message.emit(f"{self._name} mode active")

	#============================================
	def deactivate(self) -> None:
		"""Called when switching away from this mode.

		Restores the default cursor. Subclasses should call
		super().deactivate() and clean up any transient state.
		"""
		self._view.setCursor(PySide6.QtGui.QCursor(
			PySide6.QtCore.Qt.CursorShape.ArrowCursor
		))

	# ------------------------------------------------------------------
	# Event handlers
	# ------------------------------------------------------------------

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle a mouse press event at the given scene position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The QGraphicsSceneMouseEvent or QMouseEvent.
		"""

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle a mouse release event at the given scene position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The QGraphicsSceneMouseEvent or QMouseEvent.
		"""

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle a mouse move event at the given scene position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The QGraphicsSceneMouseEvent or QMouseEvent.
		"""

	#============================================
	def mouse_double_click(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle a mouse double-click event at the given scene position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The QGraphicsSceneMouseEvent or QMouseEvent.
		"""

	#============================================
	def key_press(self, event) -> None:
		"""Handle a key press event.

		Args:
			event: The QKeyEvent.
		"""

	#============================================
	def key_release(self, event) -> None:
		"""Handle a key release event.

		Args:
			event: The QKeyEvent.
		"""

	# ------------------------------------------------------------------
	# Helpers
	# ------------------------------------------------------------------

	#============================================
	def _item_at(self, scene_pos: PySide6.QtCore.QPointF):
		"""Find the topmost interactive item at a scene position.

		Searches the scene for items at ``scene_pos`` and returns the
		first AtomItem or BondItem found. Returns None if no interactive
		item is under the cursor.

		Args:
			scene_pos: Position in scene coordinates.

		Returns:
			An AtomItem, BondItem, or None.
		"""
		scene = self._view.scene()
		if scene is None:
			return None
		# items() returns items in descending z-order (topmost first)
		items = scene.items(scene_pos)
		for item in items:
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				return item
			if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				return item
		return None
