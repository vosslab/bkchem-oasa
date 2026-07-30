"""Text annotation mode."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode


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
	def __init__(
			self,
			view: PySide6.QtWidgets.QGraphicsView,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize the text mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Text"
		self._persistent_operation = None
		self._cursor = PySide6.QtCore.Qt.CursorShape.IBeamCursor

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install or clear the generic immutable-request callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Text persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	def mouse_press(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Show a text input dialog and place text at the click position.

		Opens a QInputDialog for the user to type annotation text.
		If the user confirms, a document-owned text object is added at
		the clicked position through the session's persistent-operation seam.

		Args:
			scene_pos: Position in scene coordinates where text will be placed.
			event: The mouse event.
		"""
		scene = self._env.scene
		if scene is None:
			return
		# show input dialog for text entry
		text, accepted = PySide6.QtWidgets.QInputDialog.getText(
			self._view,
			"Add Text",
			"Enter annotation text:",
		)
		plain_text = text.strip()
		if not accepted or not plain_text:
			return
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		from bkchem_qt.models import document_session
		request = document_session.PersistentOperationRequest(
			"text.add", "Text",
			(("text", plain_text), ("position", (scene_pos.x(), scene_pos.y()))),
		)
		outcome = self._persistent_operation(request)
		self.status_message.emit(outcome.message)
