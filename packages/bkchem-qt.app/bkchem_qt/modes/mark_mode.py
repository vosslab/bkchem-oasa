"""Mark mode for adding chemical marks to atoms."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.mark_item


#============================================
class MarkMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for adding or removing chemical marks on atoms.

	Click on an atom to add a mark of the current type. If the atom
	already has a mark of the same type, it is removed (toggle behavior).
	The mark type can be changed via ``set_mark_type()``.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the mark mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Mark"
		# default mark type to add
		self._current_mark_type = bkchem_qt.canvas.items.mark_item.MARK_PLUS
		self._cursor = PySide6.QtCore.Qt.CursorShape.PointingHandCursor

	#============================================
	@property
	def current_mark_type(self) -> str:
		"""Return the current mark type that will be applied on click."""
		return self._current_mark_type

	#============================================
	def set_mark_type(self, mark_type: str) -> None:
		"""Set the mark type for subsequent clicks.

		Args:
			mark_type: One of the MARK_* constants from mark_item module.
		"""
		self._current_mark_type = mark_type
		self.status_message.emit(f"Mark mode: {mark_type}")

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Add or toggle a mark on the atom under the cursor.

		If the click lands on an AtomItem, checks whether a mark of
		the current type already exists. If so, removes it; otherwise
		adds a new mark at the default angle for that type.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		item = self._item_at(scene_pos)
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return
		# check for existing mark of the same type on this atom
		existing_mark = None
		for child in item.childItems():
			if isinstance(child, bkchem_qt.canvas.items.mark_item.MarkItem):
				if child.mark_type == self._current_mark_type:
					existing_mark = child
					break
		if existing_mark is not None:
			# toggle off: remove the existing mark
			scene = self._view.scene()
			if scene is not None:
				scene.removeItem(existing_mark)
			self.status_message.emit(f"Removed {self._current_mark_type} mark")
		else:
			# add a new mark with a default angle based on type
			angle = _default_angle_for_type(self._current_mark_type)
			_add_mark = bkchem_qt.canvas.items.mark_item.MarkItem(
				item, self._current_mark_type, angle,
			)
			# the mark is automatically visible because it is a child of the atom item
			# suppress unused variable warning: _add_mark is kept alive as child of item
			assert _add_mark.parentItem() is item
			self.status_message.emit(f"Added {self._current_mark_type} mark")


#============================================
def _default_angle_for_type(mark_type: str) -> float:
	"""Return a default placement angle for the given mark type.

	Args:
		mark_type: One of the MARK_* constants.

	Returns:
		Angle in degrees.
	"""
	angle_map = {
		bkchem_qt.canvas.items.mark_item.MARK_PLUS: 45.0,
		bkchem_qt.canvas.items.mark_item.MARK_MINUS: 45.0,
		bkchem_qt.canvas.items.mark_item.MARK_RADICAL: 90.0,
		bkchem_qt.canvas.items.mark_item.MARK_ELECTRON_PAIR: 180.0,
		bkchem_qt.canvas.items.mark_item.MARK_LONE_PAIR: 180.0,
	}
	angle = angle_map.get(mark_type, 0.0)
	return angle
