"""Backend-authoritative atom-mark interaction mode."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item


_MARK_TYPE_BY_SUBMODE = {
	"radical": "radical",
	"biradical": "biradical",
	"electronpair": "electronpair",
	"dottedelectronpair": "dotted_electronpair",
	"plusincircle": "plus",
	"minusincircle": "minus",
	"pzorbital": "pz_orbital",
}
_MARK_ACTIONS = frozenset({"add", "remove"})


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
	def __init__(
			self,
			view: PySide6.QtWidgets.QGraphicsView,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize the mark mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Mark"
		# Defaults mirror the two YAML submode-group defaults exactly.
		self._current_mark_type = "radical"
		self._current_action = "add"
		self._cursor = PySide6.QtCore.Qt.CursorShape.PointingHandCursor
		self._persistent_operation = None
		self._atom_mark_revision = None

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install or clear the session-owned immutable-request callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Mark persistent operation must be callable")
		self._persistent_operation = operation

	#============================================
	def set_atom_mark_revision(self, provider: object | None) -> None:
		"""Install or clear the session-bound backend revision provider."""
		if provider is not None and not callable(provider):
			raise TypeError("Mark revision provider must be callable")
		self._atom_mark_revision = provider

	#============================================
	@property
	def current_mark_type(self) -> str:
		"""Return the current mark type that will be applied on click."""
		return self._current_mark_type

	#============================================
	def set_mark_type(self, mark_type: str) -> None:
		"""Set one backend-supported mark type for subsequent clicks."""
		if mark_type not in set(_MARK_TYPE_BY_SUBMODE.values()):
			raise ValueError("Mark type is unsupported")
		self._current_mark_type = mark_type
		self.status_message.emit(f"Mark mode: {mark_type}")

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Map both public YAML submode groups to backend operation scalars."""
		if submode_index == 0:
			mark_type = _MARK_TYPE_BY_SUBMODE.get(name)
			if mark_type is None:
				raise ValueError("Mark YAML type is unsupported")
			self._current_mark_type = mark_type
		elif submode_index == 1:
			if name not in _MARK_ACTIONS:
				raise ValueError("Mark YAML action is unsupported")
			self._current_action = name
		else:
			raise ValueError("Mark submode group is unsupported")
		self.status_message.emit(
			"Mark mode: %s %s" % (self._current_action, self._current_mark_type),
		)

	#============================================
	def mouse_press(
			self,
			scene_pos: PySide6.QtCore.QPointF,
			event: object,
			) -> None:
		"""Submit one revision-bound atom-mark request for a durable atom.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		atom_item = self._item_at(scene_pos)
		if not isinstance(atom_item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return
		if self._persistent_operation is None or self._atom_mark_revision is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		atom_model = atom_item.atom_model
		molecule = self._env.find_molecule_for_atom(atom_model)
		molecule_id = getattr(molecule, "mol_id", None)
		atom_id = getattr(atom_model, "backend_durable_id", None)
		if (
				not isinstance(molecule_id, str) or not molecule_id
				or not isinstance(atom_id, str) or not atom_id
			):
			self.status_message.emit("Selected atom has no durable backend identity")
			return
		expected_revision = self._atom_mark_revision()
		if type(expected_revision) is not int:
			raise ValueError("Mark revision provider must return an integer")
		from bkchem_qt.models import document_session
		request = document_session.build_atom_mark_request(
			expected_revision, molecule_id, atom_id,
			self._current_action, self._current_mark_type,
		)
		outcome = self._persistent_operation(request)
		self.status_message.emit(outcome.message)
