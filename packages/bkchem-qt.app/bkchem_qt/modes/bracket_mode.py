"""Bracket insertion mode."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode


#============================================
class BracketMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for inserting brackets around molecule fragments.

	Allows the user to click on a molecule to place square brackets
	around a selected fragment, commonly used for polymer repeat
	units and complex ions.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the bracket mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Bracket"

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse press for bracket insertion.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self.status_message.emit("Bracket mode: not yet implemented")
