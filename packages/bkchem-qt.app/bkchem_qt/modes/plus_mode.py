"""Plus symbol mode for placing + between molecules in reaction schemes."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode


#============================================
class PlusMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for placing plus symbols between molecules.

	Click on the canvas to insert a + symbol at the clicked
	position, commonly used in reaction scheme diagrams.

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
		"""Initialize the plus symbol mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Plus"
		self._persistent_operation = None
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install or clear the generic immutable-request callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Plus persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return plus mode hint for the status bar.

		Returns:
			A short description of available interactions.
		"""
		return "Click to place + symbol"

	#============================================
	def mouse_press(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Place a plus symbol at the click position.

		Submits one backend-authoritative Plus request at the click position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._env.scene
		if scene is None:
			return
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		from bkchem_qt.models import document_session
		request = document_session.PersistentOperationRequest(
			"plus.add", "Plus", (("position", (scene_pos.x(), scene_pos.y())),),
		)
		outcome = self._persistent_operation(request)
		self.status_message.emit(outcome.message)
