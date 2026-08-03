"""Focused backend-authority evidence for Haworth sugar insertion."""

# Standard Library
import ast
import dataclasses
import inspect
import pathlib
import threading

# PIP3 modules
import PySide6.QtCore
import PySide6.QtTest
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.actions.haworth_actions
import bkchem_qt.actions.pubchem_actions
import bkchem_qt.bridge.chemistry_preparation
import bkchem_qt.bridge.worker
import oasa.cdml
import oasa.cdml_document


#============================================
#============================================
def _install_projection_port(session: object, deliver: object) -> None:
	"""Install one fresh typed projection lifecycle port for this session."""
	port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, deliver)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(snapshot: object) -> object:
	"""Report one deliberately unavailable typed projection outcome."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
	)


def _new_session(main_window: object) -> object:
	"""Create and select an independent public session for one test."""
	if not main_window.on_new():
		raise RuntimeError("Public New did not create a Haworth test session")
	return main_window._active_session


#============================================
def _close_clean_session(main_window: object, session: object) -> None:
	"""Close one clean session through the public tab lifecycle."""
	if not main_window.close_session_at(main_window.sessions.index(session)):
		raise RuntimeError("Public close did not remove the Haworth test session")


#============================================
def _undo_and_close(main_window: object, session: object) -> None:
	"""Restore a one-edit session to baseline before public tab close."""
	if session.undo_backend().status != "accepted":
		raise RuntimeError("Public backend undo did not restore the Haworth baseline")
	_close_clean_session(main_window, session)


#============================================
def _prepared(session: object, token_stem: str) -> object:
	"""Build one deterministic detached Haworth proposal for delivery tests."""
	return bkchem_qt.bridge.chemistry_preparation.prepare_haworth_insertion(
		"ARLRDM", "pyranose", "alpha", session.backend_snapshot.revision, token_stem,
		40.0, (2000.0, 1500.0),
	)


#============================================
def _prepared_verified_sucrose(session: object, token_stem: str) -> object:
	"""Build the named backend-owned fixed preset for a delivery test."""
	return bkchem_qt.bridge.chemistry_preparation.prepare_verified_sucrose_insertion(
		session.backend_snapshot.revision, token_stem, 40.0, (2000.0, 1500.0),
	)


#============================================
def _prepared_direct_glycosidic(session: object, token_stem: str) -> object:
	"""Build one offline non-sucrose direct-glycosidic proposal."""
	return bkchem_qt.bridge.chemistry_preparation.prepare_direct_glycosidic_haworth_insertion(
		"OCC1OC(OC2OC(CO)C(O)C(O)C2O)C(O)C(O)C1O",
		session.backend_snapshot.revision,
		token_stem,
		40.0,
		(2000.0, 1500.0),
	)


#============================================
def _delivery(main_window: object, session: object) -> tuple[object, object]:
	"""Create one current origin-bound delivery controller and proposal."""
	token = session.begin_import_request()
	delivery = bkchem_qt.actions.haworth_actions.HaworthInsertionDelivery(
		main_window, session, token, session.backend_snapshot.revision,
	)
	return delivery, _prepared(session, "haworth-r%s-i%s" % (session.backend_snapshot.revision, token))


#============================================
def _haworth_styles(cdml_text: str) -> set[tuple[str, str | None]]:
	"""Read accepted CDML through OASA before inspecting reloaded bond semantics."""
	oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	styles = set()
	for molecule in oasa.cdml.read_cdml(cdml_text):
		styles.update(
			(bond.type, bond.properties_.get("haworth_position"))
			for bond in molecule.edges
		)
	return styles


#============================================
def _haworth_geometry(cdml_text: str) -> tuple[float, tuple[float, float], tuple[float, float, float, float]]:
	"""Measure authorized accepted CDML geometry without inspecting Qt wrappers."""
	oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	molecules = list(oasa.cdml.read_cdml(cdml_text))
	atoms = [atom for molecule in molecules for atom in molecule.vertices]
	lengths = []
	for molecule in molecules:
		for bond in molecule.edges:
			atom_one, atom_two = bond.vertices
			delta_x = atom_one.x - atom_two.x
			delta_y = atom_one.y - atom_two.y
			lengths.append((delta_x * delta_x + delta_y * delta_y) ** 0.5)
	mean_length = sum(lengths) / len(lengths)
	centroid = (
		sum(atom.x for atom in atoms) / len(atoms),
		sum(atom.y for atom in atoms) / len(atoms),
	)
	bounds = (
		min(atom.x for atom in atoms), min(atom.y for atom in atoms),
		max(atom.x for atom in atoms), max(atom.y for atom in atoms),
	)
	return mean_length, centroid, bounds


#============================================
def _visible_menu_action(menu_bar: object, label: str) -> object:
	"""Return a visible recursive menu action by its public text."""
	pending = [action.menu() for action in menu_bar.actions()]
	while pending:
		menu = pending.pop()
		if menu is None:
			continue
		for action in menu.actions():
			if action.text().replace("&", "") == label:
				return action
			pending.append(action.menu())
	raise RuntimeError("Visible menu action is absent: %s" % label)


#============================================
def _enter_direct_glycosidic_smiles(smiles: str) -> None:
	"""Enter one visible direct-glycosidic request and press its real OK button."""
	dialog = PySide6.QtWidgets.QApplication.activeModalWidget()
	if not isinstance(dialog, bkchem_qt.actions.haworth_actions.DirectGlycosidicHaworthDialog):
		raise RuntimeError("Direct glycosidic Haworth dialog did not become modal")
	field = dialog.findChild(PySide6.QtWidgets.QLineEdit)
	buttons = dialog.findChild(PySide6.QtWidgets.QDialogButtonBox)
	if field is None or buttons is None:
		raise RuntimeError("Direct glycosidic Haworth dialog controls are unavailable")
	button = buttons.button(PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok)
	if button is None:
		raise RuntimeError("Direct glycosidic Haworth dialog has no OK button")
	field.setFocus()
	PySide6.QtTest.QTest.keyClicks(field, smiles)
	PySide6.QtTest.QTest.mouseClick(button, PySide6.QtCore.Qt.MouseButton.LeftButton)


#============================================
def test_haworth_worker_returns_frozen_plain_proposal(qtbot: object) -> None:
	"""The actual worker emits CDML data, never its mutable OASA graph."""
	worker = bkchem_qt.bridge.worker.OasaWorker(
		bkchem_qt.bridge.chemistry_preparation.prepare_haworth_insertion,
		"ARLRDM", "pyranose", "alpha", 7, "haworth-r7-i1", 40.0, (2000.0, 1500.0),
	)
	values = []
	worker.result.connect(values.append)
	worker.finished.connect(worker.deleteLater)
	with qtbot.waitSignal(worker.finished, timeout=1000):
		worker.start()
	prepared = values[0]
	with pytest.raises(dataclasses.FrozenInstanceError):
		prepared.expected_revision = 8

	assert isinstance(prepared.proposal_cdml, str) and prepared.expected_revision == 7


#============================================
def test_haworth_insertion_stays_with_its_origin_after_tab_switch(
		main_window: object,
		) -> None:
	"""A ready proposal commits only to the captured tab, not the active tab."""
	origin = _new_session(main_window)
	other = _new_session(main_window)
	try:
		delivery, prepared = _delivery(main_window, origin)
		other_start = other.backend_snapshot
		outcome = delivery.deliver(prepared)
		reprojected = bool(_haworth_styles(origin.backend_snapshot.cdml))
		undo_status = origin.undo_backend().status
		result = (
			outcome.status, reprojected, undo_status,
			not _haworth_styles(origin.backend_snapshot.cdml),
			other.backend_snapshot == other_start,
		)
	finally:
		_close_clean_session(main_window, origin)
		_close_clean_session(main_window, other)

	assert result == ("accepted", True, "accepted", True, True)


#============================================
def test_haworth_backend_undo_redo_owns_the_accepted_revision(main_window: object) -> None:
	"""Backend history, rather than Qt local undo, restores the sugar snapshot."""
	session = _new_session(main_window)
	try:
		delivery, prepared = _delivery(main_window, session)
		delivery.deliver(prepared)
		qt_undo_empty = not session.document.undo_stack.canUndo()
		session.undo_backend()
		undone = not _haworth_styles(session.backend_snapshot.cdml)
		session.redo_backend()
		redone = bool(_haworth_styles(session.backend_snapshot.cdml))
	finally:
		_undo_and_close(main_window, session)

	assert qt_undo_empty
	assert undone and redone


#============================================
def test_haworth_stale_token_and_revision_are_inert(
		main_window: object, monkeypatch: object,
		) -> None:
	"""A stale delivery cannot change the revision, history, or projection."""
	session = _new_session(main_window)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", lambda *_args: None)
	try:
		delivery, prepared = _delivery(main_window, session)
		session.invalidate_import_requests()
		before_token = session.backend_snapshot
		token_outcome = delivery.deliver(prepared)
		current_token = session.begin_import_request()
		stale_delivery = bkchem_qt.actions.haworth_actions.HaworthInsertionDelivery(
			main_window, session, current_token, session.backend_snapshot.revision - 1,
		)
		before_revision = session.backend_snapshot
		revision_outcome = stale_delivery.deliver(prepared)
		unchanged = (
			session.backend_snapshot == before_token == before_revision
			and not session.can_undo_backend
		)
	finally:
		_close_clean_session(main_window, session)

	assert token_outcome.status == "discarded" and revision_outcome.status == "rejected"
	assert unchanged


#============================================
def test_haworth_projection_retry_uses_accepted_backend_snapshot(
		main_window: object,
		) -> None:
	"""Projection recovery restores acceptance without submitting its proposal again."""
	session = _new_session(main_window)
	live_session = _new_session(main_window)
	try:
		delivery, prepared = _delivery(main_window, session)
		start_revision = session.backend_snapshot.revision
		_install_projection_port(session, _projection_unavailable)
		outcome = delivery.deliver(prepared)
		_install_projection_port(session, session.replace_projection_from_backend_snapshot)
		retry = session.retry_current_backend_projection()
		PySide6.QtWidgets.QApplication.processEvents()
		result = (outcome.submitted, session.backend_snapshot.revision - start_revision, retry.status)
	finally:
		_undo_and_close(main_window, session)
		_close_clean_session(main_window, live_session)

	assert result == (True, 1, "accepted")


#============================================
def test_haworth_annotations_survive_proposal_commit_and_reload() -> None:
	"""Front and back Haworth q/w/n semantics survive the OASA-only boundary."""
	prepared = bkchem_qt.bridge.chemistry_preparation.prepare_haworth_insertion(
		"ARLRDM", "pyranose", "alpha", 0, "haworth-persistence", 40.0, (2000.0, 1500.0),
	)
	session = oasa.cdml_document.CDMLDocumentSession.load("<cdml />")
	commit = session.insert_molecules(oasa.cdml_document.CDMLMoleculeInsertionRequest(
		expected_revision=0, proposal_cdml=prepared.proposal_cdml,
	))
	styles = _haworth_styles(commit.cdml)

	assert {("q", "front"), ("w", "front"), ("n", "back")} <= styles


#============================================
def test_verified_sucrose_haworth_uses_the_existing_authoritative_delivery(
		main_window: object,
		) -> None:
	"""The fixed preset commits once, then backend undo/redo restores snapshots."""
	session = _new_session(main_window)
	try:
		token = session.begin_import_request()
		delivery = bkchem_qt.actions.haworth_actions.HaworthInsertionDelivery(
			main_window, session, token, session.backend_snapshot.revision,
		)
		prepared = _prepared_verified_sucrose(
			session, "verified-sucrose-r%s-i%s" % (session.backend_snapshot.revision, token),
		)
		outcome = delivery.deliver(prepared)
		accepted = bool(_haworth_styles(session.backend_snapshot.cdml))
		session.undo_backend()
		undone = not _haworth_styles(session.backend_snapshot.cdml)
		session.redo_backend()
		redone = bool(_haworth_styles(session.backend_snapshot.cdml))
	finally:
		_undo_and_close(main_window, session)

	assert outcome.submitted and accepted
	assert undone and redone


#============================================
def test_direct_glycosidic_haworth_commits_persists_and_reprojects(
		main_window: object, tmp_path: pathlib.Path,
		) -> None:
	"""A non-sucrose two-ring request has one durable, disposable projection."""
	session = _new_session(main_window)
	path = tmp_path / "direct-glycosidic-haworth.cdml"
	try:
		token = session.begin_import_request()
		delivery = bkchem_qt.actions.haworth_actions.HaworthInsertionDelivery(
			main_window, session, token, session.backend_snapshot.revision,
		)
		prepared = _prepared_direct_glycosidic(
			session, "direct-glycosidic-r%s-i%s" % (session.backend_snapshot.revision, token),
		)
		outcome = delivery.deliver(prepared)
		saved = session.write_backend_snapshot(str(path))
		reloaded = oasa.cdml_document.CDMLDocumentSession.load(path.read_text(encoding="utf-8"))
		reloaded_styles = _haworth_styles(reloaded.snapshot().cdml)
		session.undo_backend()
		undone = not _haworth_styles(session.backend_snapshot.cdml)
		session.redo_backend()
		retry = session.retry_current_backend_projection()
		result = (
			outcome.status,
			saved.is_dirty,
			{("q", "front"), ("w", "front"), ("n", "back")} <= reloaded_styles,
			undone,
			retry.status,
		)
	finally:
		_close_clean_session(main_window, session)

	assert result == ("accepted", False, True, True, "accepted")


#============================================
def test_direct_glycosidic_haworth_delivery_keeps_its_origin_tab(
		main_window: object,
		) -> None:
	"""A prepared two-ring drawing commits to its captured inactive session only."""
	origin = _new_session(main_window)
	other = _new_session(main_window)
	try:
		token = origin.begin_import_request()
		delivery = bkchem_qt.actions.haworth_actions.HaworthInsertionDelivery(
			main_window, origin, token, origin.backend_snapshot.revision,
		)
		prepared = _prepared_direct_glycosidic(origin, "direct-glycosidic-origin")
		other_before = other.backend_snapshot
		outcome = delivery.deliver(prepared)
		result = (
			outcome.status,
			bool(_haworth_styles(origin.backend_snapshot.cdml)),
			other.backend_snapshot == other_before,
		)
	finally:
		_undo_and_close(main_window, origin)
		_close_clean_session(main_window, other)

	assert result == ("accepted", True, True)


#============================================
def test_closed_direct_glycosidic_haworth_result_is_inert(
		main_window: object,
		) -> None:
	"""A completed two-ring proposal cannot redirect into a surviving tab."""
	origin = _new_session(main_window)
	survivor = _new_session(main_window)
	try:
		token = origin.begin_import_request()
		delivery = bkchem_qt.actions.haworth_actions.HaworthInsertionDelivery(
			main_window, origin, token, origin.backend_snapshot.revision,
		)
		prepared = _prepared_direct_glycosidic(origin, "direct-glycosidic-closed")
		before = survivor.backend_snapshot
		_close_clean_session(main_window, origin)
		outcome = delivery.deliver(prepared)
		result = (outcome.status, survivor.backend_snapshot == before)
	finally:
		_close_clean_session(main_window, survivor)

	assert result == ("discarded", True)


#============================================
def test_direct_glycosidic_haworth_menu_cancel_is_inert(
		main_window: object, qapp: object, monkeypatch: object,
		) -> None:
	"""The visible action opens a cancellable request without persistent mutation."""
	class _CancelledDialog:
		def __init__(self, parent: object) -> None:
			self.parent = parent

		def exec(self) -> PySide6.QtWidgets.QDialog.DialogCode:
			return PySide6.QtWidgets.QDialog.DialogCode.Rejected

	session = main_window._active_session
	before = session.backend_snapshot
	monkeypatch.setattr(
		bkchem_qt.actions.haworth_actions,
		"DirectGlycosidicHaworthDialog",
		_CancelledDialog,
	)
	action = _visible_menu_action(
		main_window.menuBar(), "Direct Glycosidic Haworth from SMILES...",
	)
	action.trigger()
	qapp.processEvents()

	assert session.backend_snapshot == before


#============================================
def test_visible_direct_glycosidic_action_commits_once_through_its_worker(
		main_window: object, qtbot: object, monkeypatch: object,
		) -> None:
	"""The visible action commits once through queued delivery to its origin tab."""
	origin = _new_session(main_window)
	before = origin.backend_snapshot
	worker_started = threading.Event()
	allow_preparation = threading.Event()
	worker_threads = []
	delivery_threads = []
	main_thread = threading.get_ident()
	prepare = bkchem_qt.bridge.chemistry_preparation.prepare_direct_glycosidic_haworth_insertion
	submit = origin.submit_persistent_operation

	def controlled_prepare(
			smiles: str, expected_revision: int, token_stem: str,
			bond_length_pt: float, insertion_anchor: tuple[float, float],
			) -> object:
		"""Hold the real backend preparation until the source tab becomes inactive."""
		worker_threads.append(threading.get_ident())
		worker_started.set()
		allow_preparation.wait()
		return prepare(smiles, expected_revision, token_stem, bond_length_pt, insertion_anchor)

	def record_delivery(request: object) -> object:
		"""Record the thread that submits the authoritative persistent operation."""
		delivery_threads.append(threading.get_ident())
		return submit(request)

	monkeypatch.setattr(
		bkchem_qt.bridge.chemistry_preparation,
		"prepare_direct_glycosidic_haworth_insertion",
		controlled_prepare,
	)
	monkeypatch.setattr(origin, "submit_persistent_operation", record_delivery)
	action = _visible_menu_action(
		main_window.menuBar(), "Direct Glycosidic Haworth from SMILES...",
	)
	other = None
	try:
		PySide6.QtCore.QTimer.singleShot(
			0,
			lambda: _enter_direct_glycosidic_smiles(
				"OCC1OC(OC2OC(CO)C(O)C(O)C2O)C(O)C(O)C1O",
			),
		)
		action.trigger()
		qtbot.waitUntil(worker_started.is_set, timeout=1000)
		other = _new_session(main_window)
		other_before = other.backend_snapshot
		allow_preparation.set()
		qtbot.waitUntil(lambda: origin.backend_snapshot.revision > before.revision, timeout=2000)
		qtbot.waitUntil(lambda: origin.can_write_authoritative_snapshot, timeout=2000)
		accepted = origin.backend_snapshot
		undone = origin.undo_backend()
		undone_snapshot = origin.backend_snapshot
		redone = origin.redo_backend()
		result = (
			accepted.revision == before.revision + 1
			and accepted.is_dirty
			and accepted.cdml == oasa.cdml_document.CDMLDocument.parse(
				accepted.cdml, validation="strict",
			).serialize()
			and {("q", "front"), ("w", "front"), ("n", "back")}
			<= _haworth_styles(accepted.cdml)
			and origin.can_write_authoritative_snapshot
			and other.backend_snapshot == other_before
			and len(worker_threads) == 1
			and worker_threads[0] != main_thread
			and delivery_threads == [main_thread]
		)
		back_to_baseline = (
			undone.status == "accepted"
			and undone_snapshot.cdml == before.cdml
			and redone.status == "accepted"
			and origin.backend_snapshot.cdml == accepted.cdml
		)
	finally:
		allow_preparation.set()
		if origin in main_window.sessions and origin.can_undo_backend:
			_undo_and_close(main_window, origin)
		if other is not None and other in main_window.sessions:
			_close_clean_session(main_window, other)

	assert result
	assert back_to_baseline


#============================================
def test_direct_glycosidic_haworth_rejects_unsupported_topology_without_mutation(
		main_window: object, monkeypatch: object,
		) -> None:
	"""Malformed or non-direct input returns a current typed rejection only."""
	session = _new_session(main_window)
	before = session.backend_snapshot
	warnings = []
	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox,
		"warning",
		lambda *_args: warnings.append("shown"),
	)
	try:
		token = session.begin_import_request()
		delivery = bkchem_qt.actions.haworth_actions.HaworthInsertionDelivery(
			main_window, session, token, session.backend_snapshot.revision,
		)
		with pytest.raises(ValueError):
			bkchem_qt.bridge.chemistry_preparation.prepare_direct_glycosidic_haworth_insertion(
				"C1CCCCC1",
				session.backend_snapshot.revision,
				"invalid-direct-glycosidic",
				40.0,
				(2000.0, 1500.0),
			)
		current = delivery.report_error("unsupported direct glycosidic topology")
		session.invalidate_import_requests()
		late = delivery.report_error("late failure")
		result = (current, late, session.backend_snapshot == before)
	finally:
		_close_clean_session(main_window, session)

	assert result == (True, False, True) and warnings == ["shown"]


#============================================
@pytest.mark.parametrize("ring_type", ("pyranose", "furanose"))
def test_haworth_accepted_cdml_uses_captured_scene_geometry(
		ring_type: str, main_window: object,
		) -> None:
	"""Both public forms persist usable scene-scale coordinates around the anchor."""
	spacing, anchor = bkchem_qt.actions.haworth_actions._capture_haworth_geometry(
		main_window._active_session,
	)
	prepared = bkchem_qt.bridge.chemistry_preparation.prepare_haworth_insertion(
		"ARLRDM", ring_type, "alpha", 0, "haworth-%s-geometry" % ring_type,
		spacing, anchor,
	)
	session = oasa.cdml_document.CDMLDocumentSession.load("<cdml />")
	commit = session.insert_molecules(oasa.cdml_document.CDMLMoleculeInsertionRequest(
		expected_revision=0, proposal_cdml=prepared.proposal_cdml,
	))
	mean_length, centroid, bounds = _haworth_geometry(commit.cdml)
	min_x, min_y, max_x, max_y = bounds

	assert mean_length == pytest.approx(spacing, rel=0.02) and min_x < anchor[0] < max_x and min_y < anchor[1] < max_y
	assert centroid == pytest.approx(anchor, abs=0.01)


#============================================
def test_haworth_and_pubchem_actions_use_the_bridge_chemistry_boundary() -> None:
	"""Qt action sources leave OASA imports inside the named preparation bridge."""
	modules = (
		bkchem_qt.actions.haworth_actions,
		bkchem_qt.actions.pubchem_actions,
	)
	oasa_imports = []
	for module in modules:
		tree = ast.parse(inspect.getsource(module))
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				for alias in node.names:
					if alias.name == "oasa" or alias.name.startswith("oasa."):
						oasa_imports.append(alias.name)
			elif (
					isinstance(node, ast.ImportFrom)
					and node.module is not None
					and (node.module == "oasa" or node.module.startswith("oasa."))
					):
				oasa_imports.append(node.module)

	assert not oasa_imports


#============================================
def test_haworth_action_captures_plain_scene_geometry(
		main_window: object, monkeypatch: object,
		) -> None:
	"""Action start sends plain captured scale and anchor values to its worker."""
	session = _new_session(main_window)
	captured = []
	monkeypatch.setattr(
		bkchem_qt.bridge.worker.OasaWorker,
		"start",
		lambda worker: captured.append(worker._args),
	)
	try:
		bkchem_qt.actions.haworth_actions._start_haworth_insert(
			main_window, "ARLRDM", "pyranose", "alpha",
		)
		worker_args = captured[0]
		geometry_types = (type(worker_args[-2]), type(worker_args[-1]),
			tuple(type(value) for value in worker_args[-1]))
	finally:
		session.release_import_worker(next(iter(session._import_workers)))
		_close_clean_session(main_window, session)

	assert geometry_types == (float, tuple, (float, float))


#============================================
def test_haworth_dialog_cancel_has_no_mutation(main_window: object, monkeypatch: object) -> None:
	"""Cancelling the dialog does not create an import request or document edit."""
	class _CancelledDialog:
		def __init__(self, ring_type: str, parent: object) -> None:
			self.ring_type = ring_type

		def exec(self) -> PySide6.QtWidgets.QDialog.DialogCode:
			return PySide6.QtWidgets.QDialog.DialogCode.Rejected

	monkeypatch.setattr(bkchem_qt.actions.haworth_actions, "HaworthInsertDialog", _CancelledDialog)
	session = main_window._active_session
	before = session.backend_snapshot
	bkchem_qt.actions.haworth_actions.insert_haworth(main_window, "pyranose")

	assert session.backend_snapshot == before


#============================================
def test_haworth_preparation_error_is_current_only(
		main_window: object, monkeypatch: object,
		) -> None:
	"""Current preparation errors surface once; stale errors are inert."""
	session = _new_session(main_window)
	warnings = []
	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox, "warning", lambda *_args: warnings.append("shown"),
	)
	try:
		token = session.begin_import_request()
		delivery = bkchem_qt.actions.haworth_actions.HaworthInsertionDelivery(
			main_window, session, token, session.backend_snapshot.revision,
		)
		current = delivery.report_error("invalid sugar")
		session.invalidate_import_requests()
		stale = delivery.report_error("late error")
	finally:
		_close_clean_session(main_window, session)

	assert (current, stale, warnings) == (True, False, ["shown"])


#============================================
def test_closed_haworth_origin_makes_ready_result_inert(
		main_window: object, monkeypatch: object,
		) -> None:
	"""A closed source result cannot redirect into the remaining active tab."""
	origin = _new_session(main_window)
	survivor = _new_session(main_window)
	delivery, prepared = _delivery(main_window, origin)
	warnings = []
	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox, "warning", lambda *_args: warnings.append("shown"),
	)
	try:
		before = survivor.backend_snapshot
		_close_clean_session(main_window, origin)
		outcome = delivery.deliver(prepared)
		inert = survivor.backend_snapshot == before and not warnings
	finally:
		_close_clean_session(main_window, survivor)

	assert outcome.status == "discarded"
	assert inert
