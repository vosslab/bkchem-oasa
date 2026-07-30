"""Focused Qt behavior checks for authoritative CDML SMILES export."""

# Standard Library
import types

# PIP3 modules
import pytest
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.actions.context_menu
import bkchem_qt.actions.file_actions
import bkchem_qt.canvas.items.arrow_item
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.canvas.document_projection
import bkchem_qt.models.document_session
import bkchem_qt.models.document_object
import oasa.cdml_document


_LEGACY_IDLESS_CORE_CDML = (
	'<cdml version="0.15"><molecule id="legacy-molecule">'
	'<atom name="C"><point x="1cm" y="1cm"/><mark type="plus"/></atom>'
	'<atom id="known-a2" name="C"><point x="2cm" y="1cm"/></atom>'
	'<atom id="known-a3" name="O"><point x="3cm" y="1cm"/></atom>'
	'<bond start="known-a2" end="known-a3" type="n1"/>'
	'</molecule></cdml>'
)


#============================================
def _active_session(main_window: object) -> object:
	"""Return the session owning the public active projection."""
	for session in main_window.sessions:
		if session.document is main_window.document and session.scene is main_window.scene:
			return session
	raise AssertionError("Main window has no active document session")


#============================================
def _draw_root_pair(session: object) -> None:
	"""Create one direct-root molecule through the existing Draw route."""
	session.mode_manager.set_mode("draw")
	mode = session.mode_manager.current_mode
	point = PySide6.QtCore.QPointF(120.0, 160.0)
	mode.mouse_press(point, None)
	mode.mouse_release(point, None)


#============================================
def _install_native_cdml_session(main_window: object, cdml: str) -> object:
	"""Install one native backend snapshot as the active production session."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(cdml)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	bkchem_qt.actions.file_actions._project_molecules_to_scene(
		session.scene, session.document.molecules,
	)
	bkchem_qt.canvas.document_projection.project_document_presentation(
		session.document, session.scene,
	)
	return main_window._register_session(session, activate=True)


#============================================
def _select_one_atom(session: object) -> object:
	"""Select one live atom so Document resolves its durable root molecule."""
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			item.setSelected(True)
			return item
	raise AssertionError("Draw route did not project an atom")


#============================================
def _capture_dialogs(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, str]]:
	"""Replace modal dialog calls with an inspectable non-modal record."""
	records = []

	def record_information(_parent: object, title: str, text: str) -> None:
		"""Record a successful SMILES dialog."""
		records.append(("information", title, text))

	def record_warning(_parent: object, title: str, text: str) -> None:
		"""Record a failed SMILES dialog."""
		records.append(("warning", title, text))

	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "information", record_information)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", record_warning)
	return records


#============================================
def test_smiles_export_reads_authoritative_cdml_without_mutation(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Export observes backend CDML and leaves history, dirty state, and projection intact."""
	session = _active_session(main_window)
	_draw_root_pair(session)
	atom_item = _select_one_atom(session)
	before_snapshot = session.backend_snapshot
	before_document = session.document
	before_history = session._backend_history
	before_undo_count = session.document.undo_stack.count()
	dialogs = _capture_dialogs(monkeypatch)

	bkchem_qt.actions.chemistry_actions._gen_smiles(main_window)

	assert (
		PySide6.QtWidgets.QApplication.clipboard().text() == "CC"
		and dialogs == [("information", "Export SMILES", "SMILES (copied to clipboard):\n\nCC")]
		and session.backend_snapshot == before_snapshot
		and session.document is before_document
		and session._backend_history == before_history
		and session.document.undo_stack.count() == before_undo_count
		and atom_item.isSelected()
	)


#============================================
def test_selected_atom_resolves_one_durable_direct_root_in_document_order(
		main_window: object,
		) -> None:
	"""An atom selection provides its owning direct-root molecule ID."""
	session = _active_session(main_window)
	_draw_root_pair(session)
	_select_one_atom(session)

	assert session.document.selected_direct_root_molecule_ids == (
		session.document.molecules[0].mol_id,
	)


#============================================
def test_selected_bond_resolves_its_durable_direct_root_molecule(
		main_window: object,
		) -> None:
	"""A live bond selection resolves through its owning direct-root molecule."""
	session = _active_session(main_window)
	_draw_root_pair(session)
	bond_item = next(
		item for item in session.scene.items()
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
	)
	bond_item.setSelected(True)

	assert session.document.selected_direct_root_molecule_ids == (
		session.document.molecules[0].mol_id,
	)


#============================================
def test_selected_attached_mark_resolves_its_durable_direct_root_molecule(
		main_window: object,
		) -> None:
	"""A live mark selection resolves through its attached atom's molecule."""
	session = _active_session(main_window)
	_draw_root_pair(session)
	atom_item = _select_one_atom(session)
	atom_item.setSelected(False)
	mark_model = bkchem_qt.models.document_object.AtomMarkModel(
		atom_item.atom_model, {"type": "plus"},
	)
	mark_item = bkchem_qt.canvas.document_projection.create_mark_item(
		mark_model, atom_item,
	)
	assert mark_item is not None
	mark_item.setSelected(True)

	assert session.document.selected_direct_root_molecule_ids == (
		session.document.molecules[0].mol_id,
	)


#============================================
def test_idless_legacy_children_observe_only_their_durable_root(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""ID-less children may observe their durable root without becoming addressable."""
	session = _install_native_cdml_session(main_window, _LEGACY_IDLESS_CORE_CDML)
	assert 'id="atom1"' not in session.backend_snapshot.cdml
	assert 'id="bond1"' not in session.backend_snapshot.cdml
	dialogs = _capture_dialogs(monkeypatch)
	queries: list[tuple[int, str]] = []
	mutations = []
	before_snapshot = session.backend_snapshot
	before_history = session._backend_history
	before_undo_count = session.document.undo_stack.count()

	def query_root_only(revision: int, molecule_id: str) -> object:
		"""Record the one durable root accepted by the observation boundary."""
		queries.append((revision, molecule_id))
		return oasa.cdml_document.CDMLMoleculeSmilesResult(
			revision=revision, molecule_id=molecule_id, smiles="C.C=O",
		)

	def mutation_must_not_run(*_args: object) -> object:
		"""Record an unexpected backend mutation from a local-only selection."""
		mutations.append(True)
		raise AssertionError("ID-less legacy projection submitted a mutation")

	monkeypatch.setattr(session, "query_molecule_smiles", query_root_only)
	monkeypatch.setattr(session, "submit_persistent_operation", mutation_must_not_run)
	idless_atom = next(
		item for item in session.scene.items()
		if (
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id is None
		)
	)
	idless_bond = next(
		item for item in session.scene.items()
		if (
			isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
			and item.bond_model.backend_durable_id is None
		)
	)
	idless_mark = next(
		item for item in session.scene.items()
		if (
			getattr(item, "atom_mark_model", None) is not None
			and item.atom_mark_model.atom_model.backend_durable_id is None
		)
	)
	for item in (idless_atom, idless_bond, idless_mark):
		selected_items = tuple(session.scene.selectedItems())
		for selected_item in selected_items:
			selected_item.setSelected(False)
		del selected_items
		item.setSelected(True)
		assert (
			bkchem_qt.canvas.document_projection.persistent_selection_key(item) is None
			and session.document.selected_direct_root_molecule_ids == ("legacy-molecule",)
		)
		bkchem_qt.actions.chemistry_actions._gen_smiles(main_window)

	# This remains a child-addressed operation, so the ID-less atom is inert.
	bkchem_qt.actions.context_menu._set_atom_symbol(
		session.view, idless_atom.atom_model, "N",
	)

	assert (
		queries == [(before_snapshot.revision, "legacy-molecule")] * 3
		and not mutations
		and idless_atom.atom_model.symbol == "C"
		and session.backend_snapshot == before_snapshot
		and session._backend_history == before_history
		and session.document.undo_stack.count() == before_undo_count
		and dialogs == [("information", "Export SMILES", "SMILES (copied to clipboard):\n\nC.C=O")] * 3
	)


#============================================
def test_backend_issued_internal_ids_remain_usable_query_targets(main_window: object) -> None:
	"""A canonical direct core selection still exposes its backend molecule key."""
	session = _install_native_cdml_session(
		main_window,
		'<cdml version="26.07"><molecule id="m1"><atom id="a1" name="C">'
		'<point x="1cm" y="1cm"/></atom></molecule></cdml>',
	)
	atom_item = _select_one_atom(session)

	assert (
		atom_item.atom_model.backend_durable_id == "a1"
		and bkchem_qt.canvas.document_projection.persistent_selection_key(atom_item) == ("atom", "a1")
		and session.document.selected_direct_root_molecule_ids == ("m1",)
	)


#============================================
def test_smiles_export_rejects_no_mixed_and_multiple_selection_without_query(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Only one wholly molecular direct-root selection reaches the backend query."""
	session = _active_session(main_window)
	dialogs = _capture_dialogs(monkeypatch)
	called = []

	def query_must_not_run(*_args: object) -> object:
		"""Record an invalid query after an unsupported selection."""
		called.append(True)
		raise AssertionError("unsupported selection queried OASA")

	monkeypatch.setattr(session, "query_molecule_smiles", query_must_not_run)
	bkchem_qt.actions.chemistry_actions._gen_smiles(main_window)
	assert not called

	_draw_root_pair(session)
	_select_one_atom(session)
	session.commit_arrow((20.0, 20.0), (60.0, 20.0))
	atom_item = _select_one_atom(session)
	arrow_item = next(
		item for item in session.scene.items()
		if isinstance(item, bkchem_qt.canvas.items.arrow_item.ArrowItem)
	)
	atom_item.setSelected(True)
	arrow_item.setSelected(True)
	bkchem_qt.actions.chemistry_actions._gen_smiles(main_window)
	assert session.document.selected_direct_root_molecule_ids == ()
	assert not called

	selected_items = tuple(session.scene.selectedItems())
	for item in selected_items:
		item.setSelected(False)
	del selected_items
	_draw_root_pair(session)
	molecule_items = {}
	for item in session.scene.items():
		if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			continue
		molecule = session.document.molecule_for_graphics_item(item)
		molecule_items.setdefault(molecule.mol_id, item)
	for item in molecule_items.values():
		item.setSelected(True)
	bkchem_qt.actions.chemistry_actions._gen_smiles(main_window)

	assert len(session.document.selected_direct_root_molecule_ids) == 2
	assert not called and len(dialogs) == 3


#============================================
def test_smiles_export_rejects_unregistered_active_session_alias_without_query(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An alias matching the projection but not registration cannot query OASA."""
	session = _active_session(main_window)
	_draw_root_pair(session)
	_select_one_atom(session)
	before_snapshot = session.backend_snapshot
	before_undo_count = session.document.undo_stack.count()
	clipboard = PySide6.QtWidgets.QApplication.clipboard()
	clipboard.setText("existing clipboard")
	dialogs = _capture_dialogs(monkeypatch)
	called = []

	def query_must_not_run(*_args: object) -> object:
		"""Record an invalid query through the unregistered alias."""
		called.append(True)
		raise AssertionError("unregistered session alias queried OASA")

	false_alias = types.SimpleNamespace(
		document=session.document,
		scene=session.scene,
		view=session.view,
		is_disposed=False,
		can_write_authoritative_snapshot=True,
		query_molecule_smiles=query_must_not_run,
	)
	main_window._active_session = false_alias
	try:
		assert not main_window._registry.is_enabled("chemistry.gen_smiles", main_window)
		bkchem_qt.actions.chemistry_actions._gen_smiles(main_window)
	finally:
		main_window._active_session = session

	assert (
		not called
		and session.backend_snapshot == before_snapshot
		and session.document.undo_stack.count() == before_undo_count
		and clipboard.text() == "existing clipboard"
		and dialogs == [(
			"warning", "Export SMILES",
			"SMILES export requires an active synchronized document session.",
		)]
	)


#============================================
def test_smiles_export_rejects_unsynchronized_projection_without_query(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A stale Qt projection reports a local warning and preserves backend state."""
	session = _active_session(main_window)
	_draw_root_pair(session)
	_select_one_atom(session)
	before_snapshot = session.backend_snapshot
	dialogs = _capture_dialogs(monkeypatch)
	called = []

	def query_must_not_run(*_args: object) -> object:
		"""Record an invalid backend observation attempt."""
		called.append(True)
		raise AssertionError("out-of-sync action queried OASA")

	monkeypatch.setattr(session, "query_molecule_smiles", query_must_not_run)
	session._backend_projection_synchronized = False
	bkchem_qt.actions.chemistry_actions._gen_smiles(main_window)

	assert (
		not called
		and session.backend_snapshot == before_snapshot
		and dialogs[0][0:2] == ("warning", "Export SMILES")
	)


#============================================
@pytest.mark.parametrize(
	("error_type", "message"),
	(
		(oasa.cdml_document.CDMLMoleculeSmilesUnavailableError, "unavailable"),
		(oasa.cdml_document.CDMLRevisionConflictError, "older document revision"),
	),
)
def test_smiles_export_reports_typed_backend_failures_without_mutation(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		error_type: type[Exception], message: str,
		) -> None:
	"""Typed OASA observation failures leave the synchronized document unchanged."""
	session = _active_session(main_window)
	_draw_root_pair(session)
	_select_one_atom(session)
	before_snapshot = session.backend_snapshot
	dialogs = _capture_dialogs(monkeypatch)

	def raise_typed_failure(*_args: object) -> object:
		"""Model a typed backend query failure after valid target capture."""
		raise error_type("typed query failure")

	monkeypatch.setattr(session, "query_molecule_smiles", raise_typed_failure)
	bkchem_qt.actions.chemistry_actions._gen_smiles(main_window)

	assert (
		session.backend_snapshot == before_snapshot
		and dialogs[0][0] == "warning"
		and message in dialogs[0][2]
	)
