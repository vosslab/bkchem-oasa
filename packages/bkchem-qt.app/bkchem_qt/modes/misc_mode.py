"""Miscellaneous mode for numbering, wavy lines, etc."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode


#============================================
class MiscMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for miscellaneous operations like atom numbering.

	Provides access to less common drawing operations including
	atom numbering, wavy lines, and other special annotations.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the miscellaneous mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Misc"

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse press to apply a miscellaneous operation.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self.status_message.emit("Misc mode: not yet implemented")
