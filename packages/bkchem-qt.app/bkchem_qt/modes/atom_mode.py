"""Atom mode for changing atom element types."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.document_projection


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
	def __init__(self, view: object, parent: PySide6.QtCore.QObject | None = None) -> None:
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
		self._persistent_operation = None

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install the session-owned immutable persistent-operation callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Atom persistent operation must be callable")
		self._persistent_operation = operation

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
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Change the element of the atom under the cursor.

		If the click lands on an AtomItem, submit its durable identity and
		the selected element to the authoritative document session.  The
		session owns the accepted commit, history, and replacement projection.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		item = self._item_at(scene_pos)
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return
		atom_model = item.atom_model
		old_symbol = atom_model.symbol
		new_symbol = self._current_element
		if old_symbol == new_symbol:
			return
		if self._persistent_operation is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		molecule = self._env.find_molecule_for_atom(atom_model)
		molecule_id = getattr(molecule, "mol_id", None)
		atom_id = atom_model.backend_durable_id
		if not molecule_id or not atom_id:
			self.status_message.emit("Selected atom has no durable backend identity")
			return
		owner = getattr(self._persistent_operation, "__self__", None)
		snapshot = getattr(owner, "backend_snapshot", None)
		if snapshot is None:
			self.status_message.emit("Document cannot accept a persistent edit")
			return
		from bkchem_qt.models import document_session
		molecule_key = str(molecule_id)
		atom_key = str(atom_id)
		request = document_session.build_atom_element_request(
			snapshot.revision, molecule_key, atom_key, new_symbol,
		)
		outcome = self._persistent_operation(request)
		if getattr(outcome, "status", None) == "accepted":
			self._select_fresh_atom(atom_key)
		self.status_message.emit(outcome.message)

	#============================================
	def _select_fresh_atom(self, atom_id: str) -> None:
		"""Restore selection only through the accepted projection's durable ID."""
		scene = self._env.scene
		if scene is None:
			return
		scene.clearSelection()
		bkchem_qt.canvas.document_projection.select_projected_persistent_keys(
			scene, frozenset({("atom", atom_id)}),
		)
