"""Plus symbol mode."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode


#============================================
class PlusMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for placing plus symbols between molecules.

	Click on the canvas to insert a plus symbol at the clicked
	position, commonly used in reaction scheme diagrams.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the plus symbol mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Plus"

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse press to place a plus symbol.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self.status_message.emit("Plus mode: not yet implemented")
