"""Focused Qt clipboard routing and retained Copy/Cut behavior."""

# Standard Library
import pathlib

# PIP3 modules
import PySide6.QtCore
import pytest

# local repo modules
import bkchem_qt.models.document_session
import bkchem_qt.actions.context_menu
import bkchem_qt.actions.file_actions
import bkchem_qt.io.clipboard_manager
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.molecule_model
import oasa.cdml_conformance
import oasa.cdml_writer
import oasa.safe_xml


_MIXED_FRAGMENT = """<cdml><molecule id="source-molecule"><atom id="source-atom" name="C"><point x="1cm" y="2cm" /></atom></molecule><arrow id="source-arrow" type="normal" start="no" end="yes" spline="no" width="1.5" color="#000000" shape="(8,10,3)"><point x="3cm" y="2cm" /><point x="4cm" y="2cm" /></arrow></cdml>"""

_COPY_SOURCE = """<cdml version="26.07" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" source_document="retained-only">
  <info><author_program>Clipboard coverage</author_program></info>
  <metadata><source>full document only</source></metadata>
  <paper type="A4" orientation="portrait" />
  <standard line_width="2.0px" />
  <molecule id="selected-molecule"><atom id="selected-atom" name="C"><point x="1cm" y="2cm" /></atom></molecule>
  <molecule id="unselected-molecule"><atom id="unselected-atom" name="O"><point x="5cm" y="2cm" /></atom></molecule>
  <arrow id="selected-arrow" type="normal" start="no" end="yes" spline="no" width="1.5" color="#000000" shape="(8,10,3)"><point x="3cm" y="2cm" /><point x="4cm" y="2cm" /></arrow>
  <plus id="unselected-plus"><point x="6cm" y="2cm" /></plus>
</cdml>"""


#============================================
#============================================
def _install_projection_port(session: object, deliver: object) -> None:
	"""Install one fresh typed projection lifecycle port for this session."""
	port = bkchem_qt.models.document_session.SessionProjectionLifecyclePort(session, deliver)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(snapshot: object) -> object:
	"""Report one deliberately unavailable typed projection outcome."""
	return bkchem_qt.models.document_session.ProjectionLifecycleResult(
		bkchem_qt.models.document_session.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.document_session.ProjectionLifecyclePhase.PREPARATION,
	)


def _molecule() -> bkchem_qt.models.molecule_model.MoleculeModel:
	"""Build a small molecule whose whole-object selection is observable."""
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	carbon = bkchem_qt.models.atom_model.AtomModel()
	carbon.set_xyz(10.0, 20.0)
	oxygen = bkchem_qt.models.atom_model.AtomModel()
	oxygen.symbol = "O"
	oxygen.set_xyz(40.0, 20.0)
	molecule.add_atom(carbon)
	molecule.add_atom(oxygen)
	bond = bkchem_qt.models.bond_model.BondModel()
	molecule.add_bond(carbon, oxygen, bond)
	return molecule


#============================================
def _add_molecule(main_window: object) -> bkchem_qt.models.molecule_model.MoleculeModel:
	"""Add a molecule to the active test document without creating undo history."""
	molecule = _molecule()
	bkchem_qt.actions.file_actions._add_molecules_to_scene(
		main_window, [molecule], undoable=False,
	)
	return molecule


#============================================
def _copy_selected_molecule(main_window: object, molecule: object) -> None:
	"""Select one atom and put its complete parent molecule on the clipboard."""
	atom_item = next(
		item for item in main_window.scene.items()
		if getattr(item, "atom_model", None) is molecule.atoms[0]
	)
	atom_item.setSelected(True)
	main_window._clipboard_manager.copy_selection(main_window.document)


#============================================
def _clipboard_fragment(qapp: object, fragment: str) -> None:
	"""Install one raw complete CDML value using the custom MIME type."""
	mime_data = PySide6.QtCore.QMimeData()
	mime_data.setData(
		bkchem_qt.io.clipboard_manager.CDML_MIME_TYPE,
		PySide6.QtCore.QByteArray(fragment.encode("utf-8")),
	)
	qapp.clipboard().setMimeData(mime_data)


#============================================
def _point_x(point: object) -> float:
	"""Return one canonical CDML centimetre x-coordinate in scene points."""
	value = point.get("x")
	return float(value.removesuffix("cm")) * oasa.cdml_writer.POINTS_PER_CM


#============================================
def _paste_action(main_window: object) -> object:
	"""Return the long-lived YAML-backed Edit/Paste action."""
	return main_window._adapter.get_action_by_key("edit.paste")


#============================================
def _new_disposable_session(main_window: object) -> object:
	"""Open one tab whose persistent backend state the test will dispose."""
	main_window._on_new()
	return main_window._active_session


#============================================
def _selected_copy_records(
		fragment: str,
		) -> tuple[str, str, tuple[tuple[str, str], ...]]:
	"""Return accepted fragment status, root source marker, and direct records."""
	report = oasa.cdml_conformance.inspect_cdml(fragment)
	root = oasa.safe_xml.parse_xml_string(fragment)
	records = tuple(
		(child.tag.rsplit("}", 1)[-1], child.get("id", ""))
		for child in root
	)
	return (
		"valid" if report.is_valid else "invalid",
		root.get("source_document", ""),
		records,
	)


#============================================
def _select_copy_source_objects(main_window: object) -> None:
	"""Select the source molecule and arrow through their live projections."""
	document = main_window.document
	molecule = next(
		model for model in document.molecules
		if model.mol_id == "selected-molecule"
	)
	atom_item = next(
		item for item in main_window.scene.items()
		if getattr(item, "atom_model", None) is molecule.atoms[0]
	)
	arrow = next(
		model for model in document.presentation_objects
		if model.object_id == "selected-arrow"
	)
	arrow_item = next(
		item for item in main_window.scene.items()
		if getattr(item, "document_object_model", None) is arrow
	)
	atom_item.setSelected(True)
	arrow_item.setSelected(True)


#============================================
def _open_copy_source(main_window: object, tmp_path: pathlib.Path) -> object:
	"""Open the mixed durable-root source through the normal backend path."""
	source = tmp_path / "cut-source.cdml"
	source.write_text(_COPY_SOURCE, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	return main_window._active_session


#============================================
def test_mixed_paste_canonicalizes_the_fragment_with_one_translation(
		main_window: object, qapp: object,
		) -> None:
	"""Backend Paste preserves both objects and translates them together."""
	session = _new_disposable_session(main_window)
	try:
		_clipboard_fragment(qapp, _MIXED_FRAGMENT)
		main_window.on_paste()
		root = oasa.safe_xml.parse_xml_string(session.backend_snapshot.cdml)
		children = list(root)
		molecule = next(child for child in children if child.tag.endswith("molecule"))
		arrow = next(child for child in children if child.tag.endswith("arrow"))
		molecule_point = list(list(molecule)[0])[0]
		arrow_point = list(arrow)[0]
	finally:
		if not session.is_disposed:
			main_window._remove_session(session)

	assert tuple(child.tag.rsplit("}", 1)[-1] for child in children) == (
		"molecule", "arrow",
	)
	assert (_point_x(molecule_point), _point_x(arrow_point)) == pytest.approx((
		oasa.cdml_writer.POINTS_PER_CM + 20.0,
		3.0 * oasa.cdml_writer.POINTS_PER_CM + 20.0,
	), abs=0.02)


#============================================
def test_copy_builds_a_bounded_selected_fragment_that_public_paste_accepts(
		main_window: object, qapp: object, tmp_path: pathlib.Path,
		) -> None:
	"""Copy proposes selected records only, then Paste accepts that proposal."""
	source = tmp_path / "copy-source.cdml"
	source.write_text(_COPY_SOURCE, encoding="utf-8")
	assert main_window.open_file_path(str(source))
	session = main_window._active_session
	try:
		_select_copy_source_objects(main_window)
		before_copy = session.backend_snapshot
		main_window._clipboard_manager.copy_selection(main_window.document)
		copied = main_window._clipboard_manager.read_fragment()
		fragment = copied[1]
		assert fragment is not None
		copy_records = _selected_copy_records(fragment)
		after_copy = session.backend_snapshot
		main_window.on_paste()
		after_paste = session.backend_snapshot
	finally:
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert (copied[0], copy_records, after_copy) == (
		"ok",
		(
			"valid", "",
			(("molecule", "selected-molecule"), ("arrow", "selected-arrow")),
		),
		before_copy,
	)
	assert after_paste.revision == before_copy.revision + 1


#============================================
def test_cut_of_mixed_durable_roots_uses_one_backend_delete_and_replays(
		main_window: object, tmp_path: pathlib.Path,
		) -> None:
	"""Cut resolves an atom to its molecule and deletes mixed roots atomically."""
	session = _open_copy_source(main_window, tmp_path)
	try:
		_select_copy_source_objects(main_window)
		before_document = session.document
		before = session.backend_snapshot
		qt_undo_count = before_document.undo_stack.count()
		main_window.on_cut()
		after_document = session.document
		after = session.backend_snapshot
		after_qt_undo_count = after_document.undo_stack.count()
		root = oasa.safe_xml.parse_xml_string(after.cdml)
		remaining_ids = {
			child.get("id", "") for child in root
		}
		undone = session.undo_backend()
		undo_snapshot = session.backend_snapshot
		redone = session.redo_backend()
		redo_snapshot = session.backend_snapshot
	finally:
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert (
		after.revision == before.revision + 1,
		after_document is not before_document,
		after_document.has_selection,
		{"selected-molecule", "selected-arrow"}.isdisjoint(remaining_ids),
		{"unselected-molecule", "unselected-plus"} <= remaining_ids,
		'<metadata><source>full document only</source>' in after.cdml,
	) == (True, True, False, True, True, True)
	assert (
		qt_undo_count,
		after_qt_undo_count,
		undone.status,
		redone.status,
		undo_snapshot.cdml == before.cdml,
		redo_snapshot.cdml == after.cdml,
	) == (0, 0, "accepted", "accepted", True, True)


#============================================
@pytest.mark.parametrize("case", ("unavailable", "idless", "rejected"))
def test_synchronized_cut_failures_keep_the_document_inert_after_copy(
		main_window: object, tmp_path: pathlib.Path, case: str,
		) -> None:
	"""Copied Cut fragments do not authorize a local fallback on failure."""
	session = _open_copy_source(main_window, tmp_path)
	restore_delivery = lambda snapshot: main_window._replace_session_projection(session, snapshot)
	try:
		_select_copy_source_objects(main_window)
		molecule = next(
			model for model in session.document.molecules
			if model.mol_id == "selected-molecule"
		)
		before = session.backend_snapshot
		qt_undo_count = session.document.undo_stack.count()
		if case == "unavailable":
			session.clear_projection_lifecycle_port()
		elif case == "idless":
			molecule.mol_id = ""
		else:
			molecule.mol_id = "missing-root"
		main_window.on_cut()
		clipboard_status, clipboard_fragment = main_window._clipboard_manager.read_fragment()
		after = session.backend_snapshot
		after_qt_undo_count = session.document.undo_stack.count()
	finally:
		if not session.is_disposed:
			_install_projection_port(session, restore_delivery)
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert (clipboard_status, clipboard_fragment is not None) == ("ok", True)
	assert (after.cdml, after.revision, qt_undo_count, after_qt_undo_count) == (
		before.cdml, before.revision, 0, 0,
	)


#============================================
def test_cut_stays_bound_to_the_originating_tab_after_clipboard_delivery(
		main_window: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A tab change during clipboard delivery cannot redirect Cut to that tab."""
	session = _open_copy_source(main_window, tmp_path)
	original_copy = main_window._clipboard_manager.copy_selection
	try:
		_select_copy_source_objects(main_window)
		before_other = None

		def copy_then_activate_other(document: object) -> int:
			"""Publish the fragment, then make a new tab current before submission."""
			nonlocal before_other
			count = original_copy(document)
			main_window._on_new()
			before_other = main_window._active_session.backend_snapshot
			return count

		monkeypatch.setattr(
			main_window._clipboard_manager, "copy_selection", copy_then_activate_other,
		)
		main_window.on_cut()
		origin_snapshot = session.backend_snapshot
		other_snapshot = main_window._active_session.backend_snapshot
	finally:
		if not session.is_disposed:
			main_window._remove_session(session)

	assert (
		'id="selected-molecule"' not in origin_snapshot.cdml,
		'id="selected-arrow"' not in origin_snapshot.cdml,
		other_snapshot == before_other,
	) == (True, True, True)


#============================================
def test_cut_uses_its_frozen_revision_after_clipboard_callback_mutation(
		main_window: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A callback commit leaves copied Cut roots intact through stale rejection."""
	session = _open_copy_source(main_window, tmp_path)
	original_copy = main_window._clipboard_manager.copy_selection
	try:
		_select_copy_source_objects(main_window)
		before = session.backend_snapshot
		qt_undo_count = session.document.undo_stack.count()
		callback_outcome = None

		def copy_then_mutate_origin(document: object) -> int:
			"""Publish first, then accept one real mutation in the origin session."""
			nonlocal callback_outcome
			count = original_copy(document)
			callback_outcome = session.submit_clipboard_fragment(_MIXED_FRAGMENT)
			return count

		monkeypatch.setattr(
			main_window._clipboard_manager, "copy_selection", copy_then_mutate_origin,
		)
		main_window.on_cut()
		clipboard_status, clipboard_fragment = main_window._clipboard_manager.read_fragment()
		after = session.backend_snapshot
		after_qt_undo_count = session.document.undo_stack.count()
	finally:
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert callback_outcome is not None
	assert (
		callback_outcome.status,
		clipboard_status,
		clipboard_fragment is not None,
		after.revision,
		after_qt_undo_count,
		'id="selected-molecule"' in after.cdml,
		'id="selected-arrow"' in after.cdml,
	) == ("accepted", "ok", True, before.revision + 1, qt_undo_count, True, True)


#============================================
def test_synchronized_cut_never_downgrades_to_local_after_clipboard_callback(
		main_window: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A callback isolation transition makes a synchronized Cut unavailable."""
	session = _open_copy_source(main_window, tmp_path)
	original_copy = main_window._clipboard_manager.copy_selection
	try:
		_select_copy_source_objects(main_window)
		before = session.backend_snapshot
		qt_undo_count = session.document.undo_stack.count()

		def copy_then_isolate_origin(document: object) -> int:
			"""Publish the fragment and turn the origin into a local projection."""
			count = original_copy(document)
			session.document.mark_dirty()
			return count

		monkeypatch.setattr(
			main_window._clipboard_manager, "copy_selection", copy_then_isolate_origin,
		)
		main_window.on_cut()
		clipboard_status, clipboard_fragment = main_window._clipboard_manager.read_fragment()
		after = session.backend_snapshot
		after_qt_undo_count = session.document.undo_stack.count()
	finally:
		if not session.is_disposed:
			main_window._on_new()
			main_window._remove_session(session)

	assert (
		session.legacy_isolated,
		clipboard_status,
		clipboard_fragment is not None,
		after == before,
		after_qt_undo_count == qt_undo_count,
	) == (True, "ok", True, True, True)


#============================================
def test_accepted_paste_projects_and_undo_redo_replays_backend_snapshots(
		main_window: object,
		) -> None:
	"""A persistent Paste is projected and is one observable backend history step."""
	session = _new_disposable_session(main_window)
	try:
		baseline = session.backend_snapshot
		accepted = session.submit_clipboard_fragment(_MIXED_FRAGMENT)
		accepted_snapshot = session.backend_snapshot
		projection_counts = (
			len(session.document.molecules), len(session.document.presentation_objects),
		)
		session.undo_backend()
		undo_snapshot = session.backend_snapshot
		session.redo_backend()
		redo_snapshot = session.backend_snapshot
	finally:
		if not session.is_disposed:
			main_window._remove_session(session)

	assert (accepted.status, projection_counts) == ("accepted", (1, 1))
	assert (undo_snapshot.cdml, redo_snapshot.cdml) == (
		baseline.cdml, accepted_snapshot.cdml,
	)


#============================================
def test_rejected_paste_does_not_add_a_logical_backend_history_step(
		main_window: object,
		) -> None:
	"""One undo after rejection returns the preceding accepted document."""
	session = _new_disposable_session(main_window)
	try:
		baseline = session.backend_snapshot
		session.submit_clipboard_fragment(_MIXED_FRAGMENT)
		rejected = session.submit_clipboard_fragment("<cdml><paper /></cdml>")
		session.undo_backend()
		undo_snapshot = session.backend_snapshot
	finally:
		if not session.is_disposed:
			main_window._remove_session(session)

	assert (rejected.status, rejected.submitted) == ("rejected", False)
	assert undo_snapshot.cdml == baseline.cdml


#============================================
def test_unavailable_clipboard_session_does_not_submit(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Unavailable sessions refuse raw clipboard data before backend entry."""
	session = main_window._active_session
	restore_delivery = lambda snapshot: main_window._replace_session_projection(session, snapshot)
	session.clear_projection_lifecycle_port()

	def unexpected_insert(_request: object) -> object:
		"""Prove the unavailable gate prevents backend submission."""
		raise AssertionError("unavailable clipboard paste submitted")

	try:
		monkeypatch.setattr(
			session._backend_session, "insert_top_level", unexpected_insert,
		)
		outcome = session.submit_clipboard_fragment(_MIXED_FRAGMENT)
	finally:
		_install_projection_port(session, restore_delivery)

	assert (outcome.status, outcome.submitted) == ("unavailable", False)


#============================================
def test_paste_does_not_retarget_an_unregistered_captured_session(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Clipboard reads cannot redirect Paste after the captured tab is removed."""
	session = _new_disposable_session(main_window)
	submitted = []
	removed = False

	def unregister_during_read() -> tuple[str, str]:
		"""Remove only the captured session before returning raw clipboard CDML."""
		nonlocal removed
		main_window._remove_session(session)
		removed = True
		return ("ok", _MIXED_FRAGMENT)

	def unexpected_submit(fragment: str) -> object:
		"""Record any impermissible submit after the stale clipboard read."""
		submitted.append(fragment)
		return None

	try:
		monkeypatch.setattr(
			main_window._clipboard_manager, "read_fragment", unregister_during_read,
		)
		monkeypatch.setattr(session, "submit_clipboard_fragment", unexpected_submit)
		main_window.on_paste()
	finally:
		if not removed:
			main_window._remove_session(session)

	assert submitted == []


#============================================
def test_accepted_projection_failure_retries_the_exact_snapshot_once(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Recovery reprojects acceptance without resubmitting a candidate fragment."""
	session = _new_disposable_session(main_window)
	restore_delivery = lambda snapshot: main_window._replace_session_projection(session, snapshot)
	calls = []
	failed_snapshots = []
	retried_snapshots = []
	original_insert = session._backend_session.insert_top_level

	def count_insert(request: object) -> object:
		"""Record backend entry while retaining normal atomic insertion behavior."""
		calls.append(request)
		return original_insert(request)

	def failed_projection(snapshot: object) -> bool:
		"""Record the accepted snapshot before deliberately declining it."""
		failed_snapshots.append(snapshot)
		return _projection_unavailable(snapshot)

	def recovered_projection(snapshot: object) -> bool:
		"""Record the exact snapshot supplied to normal reprojection."""
		retried_snapshots.append(snapshot)
		return restore_delivery(snapshot)

	try:
		monkeypatch.setattr(session._backend_session, "insert_top_level", count_insert)
		_install_projection_port(session, failed_projection)
		accepted = session.submit_clipboard_fragment(_MIXED_FRAGMENT)
		_install_projection_port(session, recovered_projection)
		retry = session.retry_current_backend_projection()
	finally:
		if not session.is_disposed:
			_install_projection_port(session, restore_delivery)
			main_window._remove_session(session)

	assert (accepted.status, accepted.submitted, retry.status, len(calls)) == (
		"unavailable", True, "accepted", 1,
	)
	assert (failed_snapshots, retried_snapshots) == (
		[accepted.commit.snapshot], [accepted.commit.snapshot],
	)


#============================================
def test_clipboard_reader_reports_no_data_and_invalid_utf8(
		qapp: object,
		) -> None:
	"""The Qt adapter reports read states without parsing a CDML fragment."""
	manager = bkchem_qt.io.clipboard_manager.ClipboardManager()
	qapp.clipboard().clear()
	no_data = manager.read_fragment()
	mime_data = PySide6.QtCore.QMimeData()
	mime_data.setData(bkchem_qt.io.clipboard_manager.CDML_MIME_TYPE, b"\xff")
	qapp.clipboard().setMimeData(mime_data)
	decode_error = manager.read_fragment()

	assert (no_data, decode_error) == (("no_data", None), ("decode_error", None))


#============================================
def test_paste_action_tracks_clipboard_changes_without_manual_refresh(
		main_window: object, qapp: object,
		) -> None:
	"""The long-lived Edit/Paste action follows QClipboard dataChanged events."""
	action = _paste_action(main_window)
	qapp.clipboard().clear()
	qapp.processEvents()
	empty_enabled = action.isEnabled()
	_clipboard_fragment(qapp, _MIXED_FRAGMENT)
	qapp.processEvents()
	fragment_enabled = action.isEnabled()
	qapp.clipboard().clear()
	qapp.processEvents()
	cleared_enabled = action.isEnabled()

	assert (empty_enabled, fragment_enabled, cleared_enabled) == (False, True, False)


#============================================
def test_unavailable_session_disables_paste_in_menu_and_context_menu(
		main_window: object, qapp: object,
		) -> None:
	"""Projection-unavailable sessions never advertise a persistent Paste."""
	session = main_window._active_session
	restore_delivery = lambda snapshot: main_window._replace_session_projection(session, snapshot)
	context_menu = None
	_clipboard_fragment(qapp, _MIXED_FRAGMENT)
	qapp.processEvents()
	try:
		session.clear_projection_lifecycle_port()
		main_window._refresh_document_actions()
		context_menu = bkchem_qt.actions.context_menu._empty_context_menu(
			main_window.view,
		)
		availability = (
			_paste_action(main_window).isEnabled(),
			context_menu.actions()[0].isEnabled(),
		)
	finally:
		_install_projection_port(session, restore_delivery)
		if context_menu is not None:
			context_menu.deleteLater()

	assert availability == (False, False)


#============================================
def test_cut_keeps_legacy_isolated_paste_disabled_in_each_menu(
		main_window: object,
		) -> None:
	"""Legacy Cut remains whole-molecule behavior and disables persistent Paste."""
	session = _new_disposable_session(main_window)
	context_menu = None
	try:
		document = main_window.document
		molecule = _add_molecule(main_window)
		# This test exercises the explicitly isolated compatibility state, not an
		# unaddressable selection in an otherwise synchronized session.
		document.mark_dirty()
		_copy_selected_molecule(main_window, molecule)
		main_window.on_cut()
		was_removed = molecule not in document.molecules
		document.undo_stack.undo()
		was_restored = molecule in document.molecules
		main_window._refresh_document_actions()
		context_menu = bkchem_qt.actions.context_menu._empty_context_menu(
			main_window.view,
		)
		availability = (
			_paste_action(main_window).isEnabled(),
			context_menu.actions()[0].isEnabled(),
		)
	finally:
		if context_menu is not None:
			context_menu.deleteLater()
		if not session.is_disposed:
			main_window._remove_session(session)

	assert (was_removed, was_restored) == (True, True)
	assert availability == (False, False)
