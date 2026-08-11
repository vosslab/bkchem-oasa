"""Focused usability evidence for authoritative Qt InChI export."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.identifier_actions
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.canvas.items.atom_item
import oasa.cdml_document


#============================================
class _SmilesSession:
	"""Small exact-revision session port for identifier bridge tests."""

	def __init__(self, smiles: str) -> None:
		"""Retain the authoritative scalar returned by the fake query."""
		self.smiles = smiles
		self.calls: list[tuple[int, str]] = []

	def query_molecule_smiles(self, revision: int, molecule_id: str) -> object:
		"""Return one immutable backend-style SMILES observation."""
		self.calls.append((revision, molecule_id))
		return oasa.cdml_document.CDMLMoleculeSmilesResult(
			revision, molecule_id, self.smiles,
		)


#============================================
def _draw_and_select_one_molecule(main_window: object) -> object:
	"""Create one authoritative ethane molecule and select its live atom."""
	session = main_window._active_session
	session.mode_manager.set_mode("draw")
	point = PySide6.QtCore.QPointF(120.0, 160.0)
	session.mode_manager.current_mode.mouse_press(point, None)
	session.mode_manager.current_mode.mouse_release(point, None)
	item = next(
		item for item in session.scene.items()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
	)
	item.setSelected(True)
	main_window._refresh_document_actions()
	return item


#============================================
def test_identifier_bridge_derives_inchi_from_exact_backend_smiles() -> None:
	"""Qt passes only revision, durable ID, and scalar SMILES into OASA."""
	session = _SmilesSession("CC")
	response = bkchem_qt.bridge.oasa_bridge.query_molecule_identifiers(
		session, 7, "molecule-7",
	)

	assert response.failure is None
	assert response.value == bkchem_qt.bridge.oasa_bridge.MoleculeIdentifierObservation(
		7, "molecule-7", "CC", "InChI=1S/C2H6/c1-2/h1-2H3",
		"OTMSDBZUPAUEDD-UHFFFAOYSA-N", (),
	)
	assert session.calls == [(7, "molecule-7")]


#============================================
def test_identifier_bridge_returns_typed_failure_for_invalid_backend_smiles() -> None:
	"""A failed chemistry conversion remains a display-safe observation result."""
	response = bkchem_qt.bridge.oasa_bridge.query_molecule_identifiers(
		_SmilesSession("not-a-smiles"), 3, "molecule-3",
	)

	assert response.value is None
	assert response.failure is not None and response.failure.kind == "unavailable"


#============================================
def test_visible_inchi_action_copies_identifiers_without_mutating_document(
		main_window: object, monkeypatch: object,
		) -> None:
	"""A user can trigger InChI export while revision and selection stay intact."""
	action = main_window._adapter.get_action_by_key("chemistry.gen_inchi")
	assert not action.isEnabled()
	selected_item = _draw_and_select_one_molecule(main_window)
	session = main_window._active_session
	before = session.backend_snapshot
	before_history = session._backend_history
	before_undo_count = session.document.undo_stack.count()
	dialogs = []
	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox, "information",
		lambda _parent, title, text: dialogs.append((title, text)),
	)

	assert action.isEnabled()
	action.trigger()

	clipboard_text = PySide6.QtWidgets.QApplication.clipboard().text()
	expected_text = (
		"InChI=1S/C2H6/c1-2/h1-2H3\n"
		"InChIKey=OTMSDBZUPAUEDD-UHFFFAOYSA-N"
	)
	assert clipboard_text == expected_text
	assert dialogs == [(
		"Export InChI",
		"InChI and InChIKey (copied to clipboard):\n\n%s" % expected_text,
	)]
	assert (
		session.backend_snapshot == before
		and session._backend_history == before_history
		and session.document.undo_stack.count() == before_undo_count
		and selected_item.isSelected()
	)
