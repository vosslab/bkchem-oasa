"""Text annotation mode."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode

# default font settings for text annotations
_DEFAULT_FONT_FAMILY = "Arial"
_DEFAULT_FONT_SIZE = 14


#============================================
class TextMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for placing text annotations on the canvas.

	Clicking on the canvas opens an input dialog. The entered text
	is placed as a QGraphicsTextItem at the click position.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the text mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Text"
		self._cursor = PySide6.QtCore.Qt.CursorShape.IBeamCursor

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Show a text input dialog and place text at the click position.

		Opens a QInputDialog for the user to type annotation text.
		If the user confirms, a text item is added to the scene at
		the clicked position.

		Args:
			scene_pos: Position in scene coordinates where text will be placed.
			event: The mouse event.
		"""
		scene = self._view.scene()
		if scene is None:
			return
		# show input dialog for text entry
		text, accepted = PySide6.QtWidgets.QInputDialog.getText(
			self._view,
			"Add Text",
			"Enter annotation text:",
		)
		if not accepted or not text.strip():
			return
		# create a text item at the click position
		text_item = scene.addText(
			text.strip(),
			PySide6.QtGui.QFont(_DEFAULT_FONT_FAMILY, _DEFAULT_FONT_SIZE),
		)
		text_item.setPos(scene_pos)
		text_item.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
		)
		text_item.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True,
		)
		text_item.setDefaultTextColor(PySide6.QtCore.Qt.GlobalColor.black)
		self.status_message.emit(f"Text placed: {text.strip()}")
