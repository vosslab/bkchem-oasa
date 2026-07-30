"""Focused backend-authority evidence for Haworth sugar insertion."""

# Standard Library
import dataclasses

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.models.document_session
import bkchem_qt.actions.haworth_actions
import bkchem_qt.bridge.worker
import oasa.cdml
import oasa.cdml_document


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
	return bkchem_qt.actions.haworth_actions._prepare_haworth_insertion(
		"ARLRDM", "pyranose", "alpha", session.backend_snapshot.revision, token_stem,
		40.0, (2000.0, 1500.0),
	)


#============================================
def _prepared_verified_sucrose(session: object, token_stem: str) -> object:
	"""Build the named backend-owned fixed preset for a delivery test."""
	return bkchem_qt.actions.haworth_actions._prepare_verified_sucrose_insertion(
		session.backend_snapshot.revision, token_stem, 40.0, (2000.0, 1500.0),
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
def test_haworth_worker_returns_frozen_plain_proposal(qtbot: object) -> None:
	"""The actual worker emits CDML data, never its mutable OASA graph."""
	worker = bkchem_qt.bridge.worker.OasaWorker(
		bkchem_qt.actions.haworth_actions._prepare_haworth_insertion,
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
		origin_start = origin.backend_snapshot.revision
		other_start = other.backend_snapshot
		delivery.deliver(prepared)
		result = (
			origin.backend_snapshot.revision - origin_start,
			other.backend_snapshot == other_start,
		)
	finally:
		_undo_and_close(main_window, origin)
		_close_clean_session(main_window, other)

	assert result == (1, True)


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
	prepared = bkchem_qt.actions.haworth_actions._prepare_haworth_insertion(
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
@pytest.mark.parametrize("ring_type", ("pyranose", "furanose"))
def test_haworth_accepted_cdml_uses_captured_scene_geometry(
		ring_type: str, main_window: object,
		) -> None:
	"""Both public forms persist usable scene-scale coordinates around the anchor."""
	spacing, anchor = bkchem_qt.actions.haworth_actions._capture_haworth_geometry(
		main_window._active_session,
	)
	prepared = bkchem_qt.actions.haworth_actions._prepare_haworth_insertion(
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
