"""Repair mode for normalizing molecular geometry."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode


#============================================
class RepairMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for normalizing bond lengths and angles via OASA.

	Click on a molecule to regenerate its 2D coordinates using
	the OASA coordinate generator, producing uniform bond lengths
	and standard angles.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the repair mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Repair"

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse press to select a molecule for repair.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self.status_message.emit("Repair mode: not yet implemented")
