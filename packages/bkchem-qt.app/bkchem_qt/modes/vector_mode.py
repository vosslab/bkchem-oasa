"""Vector graphics mode for rectangles, ovals, polygons."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode


#============================================
class VectorMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for drawing vector graphics shapes.

	Supports drawing rectangles, ovals, and polygons on the canvas.
	The user clicks to start a shape, drags to size it, and releases
	to finalize.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the vector graphics mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Vector"
		# current shape type: "rectangle", "oval", or "polygon"
		self._shape_type = "rectangle"

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse press to start a shape.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self.status_message.emit("Vector mode: not yet implemented")
