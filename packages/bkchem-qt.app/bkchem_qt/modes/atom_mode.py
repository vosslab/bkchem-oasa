"""Atom mode for changing atom element types."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item


#============================================
class AtomMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for setting atom element by clicking.

	Click on an atom to change its element to the currently selected
	element. The current element can be changed via ``set_element()``.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the atom mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Atom"
		# the element symbol that will be applied on click
		self._current_element = "C"
		self._cursor = PySide6.QtCore.Qt.CursorShape.PointingHandCursor

	#============================================
	@property
	def current_element(self) -> str:
		"""Return the element symbol that will be applied on click."""
		return self._current_element

	#============================================
	def set_element(self, symbol: str) -> None:
		"""Set the element symbol for subsequent clicks.

		Args:
			symbol: Element symbol string (e.g. 'C', 'N', 'O').
		"""
		self._current_element = symbol
		self.status_message.emit(f"Atom mode: {symbol}")

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Change the element of the atom under the cursor.

		If the click lands on an AtomItem, changes its symbol to
		the current element and triggers a visual update.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		item = self._item_at(scene_pos)
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return
		# change the atom element
		old_symbol = item.atom_model.symbol
		item.atom_model.symbol = self._current_element
		self.status_message.emit(
			f"Changed {old_symbol} -> {self._current_element}"
		)
