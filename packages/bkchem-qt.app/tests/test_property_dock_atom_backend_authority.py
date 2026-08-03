"""Focused authority checks for synchronized PropertyDock atom controls."""

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.main_window
import bkchem_qt.models.atom_model
import bkchem_qt.models.document
import bkchem_qt.models.document_session
import bkchem_qt.models.molecule_model
import bkchem_qt.widgets.property_dock
import tests.graphics_test_retirement


_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'</molecule></cdml>'
)


#============================================
def _install_native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Register one native CDML session with a direct durable atom."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native CDML projection is unavailable")
	return registered


#============================================
def _atom_item(session: object) -> object:
	"""Return this session's direct-core atom projection."""
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return item
	raise AssertionError("Projected CDML did not produce an AtomItem")


#============================================
def _select_atom(main_window: object, session: object) -> object:
	"""Select one atom and refresh the active PropertyDock."""
	atom_item = _atom_item(session)
	atom_item.setSelected(True)
	main_window._property_dock.update_from_selection()
	return atom_item


#============================================
def _apply_atom_control(dock: object, control: str) -> None:
	"""Exercise one concrete PropertyDock atom widget event."""
	if control == "symbol":
		dock._atom_symbol_edit.setText("O")
		dock._atom_symbol_edit.editingFinished.emit()
	elif control == "charge":
		dock._atom_charge_spin.setValue(1)
	elif control == "show":
		dock._atom_show_check.setChecked(False)
	else:
		raise AssertionError("Unknown atom dock control %s" % control)


#============================================
@pytest.mark.parametrize(
	("control", "expected_cdml"),
	(("symbol", 'name="O"'), ("charge", 'charge="1"'), ("show", 'show="no"')),
)
def test_property_dock_atom_control_commits_authoritative_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		control: str, expected_cdml: str,
		) -> None:
	"""Each concrete atom control creates one backend-owned replacement edit."""
	session = _install_native_session(main_window)
	try:
		_select_atom(main_window, session)
		before_document = session.document
		before_revision = session.backend_snapshot.revision
		before_history_size = len(session._backend_history.entries)

		_apply_atom_control(main_window._property_dock, control)

		assert (
			expected_cdml in session.backend_snapshot.cdml
			and session.backend_snapshot.revision == before_revision + 1
			and len(session._backend_history.entries) == before_history_size + 1
			and session.document is not before_document
			and session.document.undo_stack.count() == 0
			and session.document.dirty
		)
		assert {
			item.atom_model.backend_durable_id
			for item in session.scene.selectedItems()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		} == {"a1"}
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_property_dock_atom_capability_stays_with_its_original_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A captured dock callback cannot redirect after another tab activates."""
	first = _install_native_session(main_window)
	first_capture = main_window._property_dock._atom_properties_capture
	second = _install_native_session(main_window)
	try:
		expected_revision, first_capability = first_capture("m1", "a1")
		outcome = first_capability(expected_revision, "m1", "a1", (("charge", 1),))

		assert outcome.status == "accepted" and 'charge="1"' in first.backend_snapshot.cdml
		assert 'charge="1"' not in second.backend_snapshot.cdml
	finally:
		if second in main_window.sessions:
			main_window._remove_session(second)
		if first in main_window.sessions:
			main_window._remove_session(first)


#============================================
def test_property_dock_captures_a_fresh_revision_for_each_control(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Two controls commit sequentially rather than reusing the bind revision."""
	session = _install_native_session(main_window)
	try:
		_select_atom(main_window, session)
		_apply_atom_control(main_window._property_dock, "charge")
		_select_atom(main_window, session)
		_apply_atom_control(main_window._property_dock, "symbol")

		assert session.backend_snapshot.revision == 2 and 'charge="1"' in session.backend_snapshot.cdml
		assert 'name="O"' in session.backend_snapshot.cdml and session.document.undo_stack.count() == 0
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_property_dock_stale_event_refreshes_without_local_undo(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A revision changed between dock capture and submit rejects atomically."""
	session = _install_native_session(main_window)
	try:
		_select_atom(main_window, session)
		original_capture = main_window._property_dock._atom_properties_capture
		observed = {}
		def stale_capture(molecule_id: str, atom_id: str) -> tuple[int, object] | None:
			"""Advance authority after capture so the returned revision is stale."""
			captured = original_capture(molecule_id, atom_id)
			if captured is None:
				return None
			outcome = session.submit_atom_properties_patch(
				session.backend_snapshot.revision, molecule_id, atom_id, (("charge", 2),),
			)
			if outcome.status != "accepted":
				raise AssertionError("intervening backend edit was rejected")
			observed["snapshot"] = session.backend_snapshot
			observed["document"] = session.document
			observed["history"] = tuple(session._backend_history.entries)

			def reject_stale(
					expected_revision: int, captured_molecule_id: str,
					captured_atom_id: str, changes: tuple[tuple[str, object], ...],
					) -> object:
				"""Record the stale result and prove it cannot reach OASA's executor."""
				outcome = captured[1](
					expected_revision, captured_molecule_id, captured_atom_id, changes,
				)
				observed["outcome"] = outcome
				return outcome

			def fail_executor(_request: object) -> object:
				"""Fail if the stale dock event reaches the backend patch executor."""
				raise AssertionError("stale dock event reached the property executor")

			monkeypatch.setattr(session._backend_session, "patch_atom_properties", fail_executor)
			return captured[0], reject_stale

		main_window._property_dock._atom_properties_capture = stale_capture
		_apply_atom_control(main_window._property_dock, "charge")

		outcome = observed["outcome"]
		assert (
			outcome.status == "rejected" and outcome.failure_kind == "revision-conflict"
			and session.backend_snapshot == observed["snapshot"]
			and session.document is observed["document"]
			and tuple(session._backend_history.entries) == observed["history"]
			and session.document.dirty and session.document.undo_stack.count() == 0
			and main_window._property_dock._atom_charge_spin.value() == 2
			and {
				item.atom_model.backend_durable_id for item in session.scene.selectedItems()
				if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			} == {"a1"}
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_property_dock_idless_synchronized_atom_is_inert(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An ID-less synchronized target cannot fall through to local mutation."""
	session = _install_native_session(main_window)
	try:
		atom_item = _select_atom(main_window, session)
		atom_item.atom_model.bind_backend_durable_id(None)
		before = session.backend_snapshot

		_apply_atom_control(main_window._property_dock, "symbol")

		assert session.backend_snapshot == before and atom_item.atom_model.symbol == "C"
		assert session.document.undo_stack.count() == 0
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_property_dock_rejected_symbol_refreshes_authoritative_value(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A rejected synchronized request restores the authoritative atom display."""
	session = _install_native_session(main_window)
	try:
		_select_atom(main_window, session)
		dock = main_window._property_dock
		dock._atom_symbol_edit.setText("Xx")
		dock._atom_symbol_edit.editingFinished.emit()

		assert session.backend_snapshot.revision == 0 and dock._atom_symbol_edit.text() == "C"
		assert session.document.undo_stack.count() == 0
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_isolated_property_dock_atom_symbol_uses_local_undo(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A standalone dock retains its deliberately isolated local edit behavior."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	atom = bkchem_qt.models.atom_model.AtomModel(symbol="C")
	molecule.add_atom(atom)
	dock = bkchem_qt.widgets.property_dock.PropertyDock(document)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		try:
			document.add_molecule(molecule, mark_dirty=False)
			atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom)
			scene.addItem(atom_item)
			atom_item.setSelected(True)
			dock.update_from_selection()
			dock._atom_symbol_edit.setText("O")
			dock._atom_symbol_edit.editingFinished.emit()

			assert atom.symbol == "O" and document.undo_stack.count() == 1
		finally:
			dock.set_document(None)
			dock.close()
			assert bkchem_qt.main_window.delete_qobject_and_wait(qapp, dock)
