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

		# submode data, populated from modes.yaml at registration time
		# each list is indexed by group index
		self.submodes = []          # list of lists of submode key strings
		self.submodes_names = []    # list of lists of display name strings
		self.submode = []           # list of ints: current index per group
		self.icon_map = {}          # submode key -> icon name
		self.group_labels = []      # group label strings
		self.group_layouts = []     # layout type per group ('row', 'grid', etc.)
		self.tooltip_map = {}       # submode key -> tooltip text
		self.size_map = {}          # submode key -> size hint ('large', etc.)
		self.show_edit_pool = False # whether to show the EditRibbon

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
	# Submode management
	# ------------------------------------------------------------------

	#============================================
	def set_submode(self, name: str) -> None:
		"""Set the active submode by key name.

		Searches all submode groups for the key and updates the
		current index for its group. Calls on_submode_switch() when
		the submode is found.

		Args:
			name: The submode key string to activate.
		"""
		for group_keys in self.submodes:
			if name in group_keys:
				group_idx = self.submodes.index(group_keys)
				self.submode[group_idx] = group_keys.index(name)
				self.on_submode_switch(group_idx, name)
				break

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Hook called when a submode selection changes.

		Subclasses override this to respond to submode switches,
		for example updating cursor style or triggering a file action.

		Args:
			submode_index: Group index of the changed submode.
			name: Key string of the newly selected submode.
		"""

	#============================================
	def get_submode(self, group_index: int) -> str:
		"""Return the currently selected submode key for a group.

		Args:
			group_index: Index of the submode group.

		Returns:
			The active submode key string.

		Raises:
			ValueError: If group_index is out of range.
		"""
		if group_index < len(self.submodes):
			idx = self.submode[group_index]
			return self.submodes[group_index][idx]
		raise ValueError(f"invalid submode group index: {group_index}")

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
