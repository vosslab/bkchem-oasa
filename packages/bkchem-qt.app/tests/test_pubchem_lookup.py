"""Focused offline authority coverage for PubChem lookup insertion."""

# Standard Library
import dataclasses

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.actions.pubchem_actions
import bkchem_qt.bridge.worker
import bkchem_qt.models.document_session
import oasa.cdml_xml
import oasa.cdml_document
import oasa.cdml
import oasa.safe_xml


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


def _pubchem_transport(url: str) -> dict:
	"""Return one complete methane response without making a network request."""
	if "/synonyms/" in url:
		return {"InformationList": {"Information": [{
			"CID": 297,
			"Synonym": ["methane"],
		}]}}
	return {"PropertyTable": {"Properties": [{
		"CID": 297,
		"Title": "Methane",
		"MolecularFormula": "CH4",
		"MolecularWeight": "16.043",
		"SMILES": "C",
		"InChI": "InChI=1S/CH4/h1H4",
		"InChIKey": "VNWKTOKETHGBQD-UHFFFAOYSA-N",
	}]}}


#============================================
def _current_session(main_window: object) -> object:
	"""Return the session that owns MainWindow's public active document."""
	return next(
		session for session in main_window.sessions
		if session.document is main_window.document
	)


#============================================
def _new_session(main_window: object) -> object:
	"""Create and select one independent test session."""
	if not main_window.on_new():
		raise RuntimeError("Public New did not create a PubChem test session")
	return _current_session(main_window)


#============================================
def _close_clean_session(main_window: object, session: object) -> None:
	"""Close one clean session through the public tab route."""
	if not main_window.close_session_at(main_window.sessions.index(session)):
		raise RuntimeError("Public close did not remove the PubChem test session")


#============================================
def _undo_and_close(main_window: object, session: object) -> None:
	"""Restore one accepted edit to baseline before closing its session."""
	if session.undo_backend().status != "accepted":
		raise RuntimeError("Public backend undo did not restore the PubChem baseline")
	_close_clean_session(main_window, session)


#============================================
def _prepared(session: object, token: int) -> object:
	"""Build one deterministic prepared PubChem result without a Qt worker."""
	return bkchem_qt.actions.pubchem_actions._prepare_pubchem_lookup(
		"Name", "methane", _pubchem_transport, session.backend_snapshot.revision,
		"pubchem-r%s-i%s" % (session.backend_snapshot.revision, token),
		40.0, (2000.0, 1500.0),
	)


#============================================
def _methane_in_cdml(cdml: str) -> bool:
	"""Use the hardened CDML reader to find one single-carbon molecule."""
	oasa.cdml_xml.inspect_cdml_xml(cdml.encode("utf-8"))
	root = oasa.safe_xml.parse_dom_from_string(cdml).documentElement
	for child in root.childNodes:
		if getattr(child, "localName", None) != "molecule":
			continue
		atoms = [
			atom for atom in child.childNodes
			if getattr(atom, "localName", None) == "atom"
		]
		if len(atoms) == 1 and atoms[0].getAttribute("name") == "C":
			return True
	return False


#============================================
def _insertion_geometry(cdml: str) -> tuple[float, tuple[float, float]]:
	"""Measure a hardened CCO proposal or accepted backend snapshot."""
	oasa.cdml_xml.inspect_cdml_xml(cdml.encode("utf-8"))
	molecules = list(oasa.cdml.read_cdml(cdml))
	atoms = [atom for molecule in molecules for atom in molecule.vertices]
	lengths = [
		((first.x - second.x) ** 2 + (first.y - second.y) ** 2) ** 0.5
		for molecule in molecules for bond in molecule.edges
		for first, second in (bond.vertices,)
	]
	return sum(lengths) / len(lengths), (
		sum(atom.x for atom in atoms) / len(atoms),
		sum(atom.y for atom in atoms) / len(atoms),
	)


#============================================
def _close_dialog(qapp: PySide6.QtWidgets.QApplication, dialog: object) -> None:
	"""Close a modeless dialog while Qt and its Python wrapper remain valid."""
	dialog.close()
	qapp.processEvents()
	dialog.deleteLater()
	PySide6.QtCore.QCoreApplication.sendPostedEvents(
		None, PySide6.QtCore.QEvent.Type.DeferredDelete,
	)


#============================================
def test_blank_pubchem_query_starts_no_request(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""Blank input remains a non-mutating validation state."""
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	try:
		dialog._query.setText("  ")
		dialog._request_lookup()
		status = dialog._status.text()
		unchanged = not _current_session(main_window).backend_snapshot.is_dirty
	finally:
		_close_dialog(qapp, dialog)

	assert "Enter a PubChem query." in status
	assert unchanged


#============================================
def test_pubchem_worker_returns_frozen_plain_display_and_proposal(
		qtbot: object,
		) -> None:
	"""The worker emits display facts and CDML, never a live molecule graph."""
	worker = bkchem_qt.bridge.worker.OasaWorker(
		bkchem_qt.actions.pubchem_actions._prepare_pubchem_lookup,
		"Name", "methane", _pubchem_transport, 7, "pubchem-r7-i1",
		40.0, (2000.0, 1500.0),
	)
	values = []
	worker.result.connect(values.append)
	worker.finished.connect(worker.deleteLater)
	with qtbot.waitSignal(worker.finished, timeout=1000):
		worker.start()
	prepared = values[0]
	with pytest.raises(dataclasses.FrozenInstanceError):
		prepared.insertion = prepared.insertion
	plain = (
		dataclasses.is_dataclass(prepared)
		and prepared.compound.cid == 297
		and prepared.insertion.expected_revision == 7
		and isinstance(prepared.insertion.proposal_cdml, str)
	)

	assert plain and _methane_in_cdml(prepared.insertion.proposal_cdml)


#============================================
def test_pubchem_lookup_start_passes_plain_captured_placement_to_worker(
		main_window: object,
		) -> None:
	"""Lookup captures scene values before worker creation and keeps them plain."""
	class _Dialog:
		_target_session = main_window._active_session

		def set_lookup_error(self, _message: object) -> None:
			raise RuntimeError("Unexpected placement capture error")

	worker = bkchem_qt.actions.pubchem_actions._create_pubchem_lookup_worker(
		main_window, _Dialog(), "Name", "methane", _pubchem_transport,
	)
	if worker is None:
		raise RuntimeError("PubChem worker creation unexpectedly failed")
	try:
		placement_types = (
			type(worker._args[-2]), type(worker._args[-1]),
			tuple(type(value) for value in worker._args[-1]),
		)
	finally:
		main_window._active_session.release_import_worker(worker)

	assert placement_types == (float, tuple, (float, float))


#============================================
def test_pubchem_preparation_persists_captured_cco_geometry() -> None:
	"""Offline CCO preparation commits the exact geometry already in its proposal."""
	def ethanol_transport(url: str) -> dict:
		result = _pubchem_transport(url)
		if "PropertyTable" in result:
			result["PropertyTable"]["Properties"][0]["SMILES"] = "CCO"
		return result

	prepared = bkchem_qt.actions.pubchem_actions._prepare_pubchem_lookup(
		"Name", "ethanol", ethanol_transport, 0, "pubchem-geometry", 30.0,
		(123.0, 456.0),
	)
	session = oasa.cdml_document.CDMLDocumentSession.load("<cdml />")
	accepted = session.insert_molecules(oasa.cdml_document.CDMLMoleculeInsertionRequest(
		expected_revision=0, proposal_cdml=prepared.insertion.proposal_cdml,
	)).cdml

	mean, centroid = _insertion_geometry(accepted)
	assert (mean, *centroid) == pytest.approx((30.0, 123.0, 456.0), rel=0.02)
	proposal_mean, proposal_centroid = _insertion_geometry(prepared.insertion.proposal_cdml)
	assert (proposal_mean, *proposal_centroid) == pytest.approx((mean, *centroid))


#============================================
def test_pubchem_insert_changes_only_captured_origin_backend(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""Explicit Insert commits once to its lookup origin, not the active tab."""
	origin = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	other = _new_session(main_window)
	try:
		# The public New route activates other after the dialog captures origin.
		token = origin.begin_import_request()
		dialog.set_lookup_result(_prepared(origin, token), origin, token)
		origin_start = origin.backend_snapshot.revision
		other_start = other.backend_snapshot
		inserted = bkchem_qt.actions.pubchem_actions._insert_dialog_result(
			main_window, dialog,
		)
		origin_delta = origin.backend_snapshot.revision - origin_start
		other_unchanged = other.backend_snapshot == other_start
	finally:
		_close_dialog(qapp, dialog)
		_undo_and_close(main_window, origin)
		_close_clean_session(main_window, other)

	assert inserted and origin_delta == 1
	assert other_unchanged


#============================================
def test_pubchem_insert_uses_backend_history_not_qt_undo(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""A committed lookup is dirty and undoable through backend history only."""
	session = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	try:
		token = session.begin_import_request()
		dialog.set_lookup_result(_prepared(session, token), session, token)
		bkchem_qt.actions.pubchem_actions._insert_dialog_result(main_window, dialog)
		backend_state = (session.backend_snapshot.is_dirty, session.can_undo_backend)
		qt_undo_empty = not session.document.undo_stack.canUndo()
	finally:
		_close_dialog(qapp, dialog)
		_undo_and_close(main_window, session)

	assert backend_state == (True, True)
	assert qt_undo_empty


#============================================
def test_pubchem_backend_undo_redo_restores_canonical_methane(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""Backend undo and redo remove and restore the accepted molecule snapshot."""
	session = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	try:
		token = session.begin_import_request()
		dialog.set_lookup_result(_prepared(session, token), session, token)
		bkchem_qt.actions.pubchem_actions._insert_dialog_result(main_window, dialog)
		session.undo_backend()
		undone = not _methane_in_cdml(session.backend_snapshot.cdml)
		session.redo_backend()
		redone = _methane_in_cdml(session.backend_snapshot.cdml)
	finally:
		_close_dialog(qapp, dialog)
		_undo_and_close(main_window, session)

	assert undone
	assert redone


#============================================
def test_stale_pubchem_result_is_inert(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""A superseded result cannot submit a candidate or change backend state."""
	session = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	try:
		token = session.begin_import_request()
		dialog.set_lookup_result(_prepared(session, token), session, token)
		before = session.backend_snapshot
		session.begin_import_request()
		inserted = bkchem_qt.actions.pubchem_actions._insert_dialog_result(
			main_window, dialog,
		)
		unchanged = session.backend_snapshot == before
	finally:
		_close_dialog(qapp, dialog)
		_close_clean_session(main_window, session)

	assert not inserted
	assert unchanged


#============================================
def test_stale_pubchem_revision_is_inert(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""A current token with an obsolete proposal revision cannot rebase itself."""
	session = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	try:
		token = session.begin_import_request()
		prepared = _prepared(session, token)
		prepared = dataclasses.replace(
			prepared,
			insertion=dataclasses.replace(
				prepared.insertion,
				expected_revision=prepared.insertion.expected_revision + 1,
			),
		)
		current_token = session.begin_import_request()
		dialog.set_lookup_result(prepared, session, current_token)
		before = session.backend_snapshot
		inserted = bkchem_qt.actions.pubchem_actions._insert_dialog_result(
			main_window, dialog,
		)
		unchanged = session.backend_snapshot == before
	finally:
		_close_dialog(qapp, dialog)
		_close_clean_session(main_window, session)

	assert not inserted
	assert unchanged


#============================================
def test_malformed_pubchem_delivery_is_inert(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""A malformed queued worker value never becomes an insertable result."""
	session = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	worker = bkchem_qt.bridge.worker.OasaWorker(lambda: None)
	try:
		token = session.begin_import_request()
		relay = bkchem_qt.actions.pubchem_actions._PubChemLookupRelay(
			main_window, dialog, session, token, worker,
		)
		before = session.backend_snapshot
		relay.on_result(object())
		unchanged = session.backend_snapshot == before
		insertable = dialog._insert_button.isEnabled()
	finally:
		_close_dialog(qapp, dialog)
		_close_clean_session(main_window, session)

	assert not insertable
	assert unchanged


#============================================
def test_pubchem_worker_error_is_inert(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""A current worker error reports inline without creating document state."""
	session = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	worker = bkchem_qt.bridge.worker.OasaWorker(lambda: None)
	try:
		token = session.begin_import_request()
		relay = bkchem_qt.actions.pubchem_actions._PubChemLookupRelay(
			main_window, dialog, session, token, worker,
		)
		before = session.backend_snapshot
		relay.on_error("offline transport")
		unchanged = session.backend_snapshot == before
		status = dialog._status.text()
	finally:
		_close_dialog(qapp, dialog)
		_close_clean_session(main_window, session)

	assert "offline transport" in status
	assert unchanged


#============================================
def test_closed_pubchem_source_cannot_insert_ready_proposal(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""A closed origin cannot redirect its ready proposal into a live tab."""
	origin = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	survivor = _new_session(main_window)
	try:
		token = origin.begin_import_request()
		dialog.set_lookup_result(_prepared(origin, token), origin, token)
		before = survivor.backend_snapshot
		_close_clean_session(main_window, origin)
		qapp.processEvents()
		inserted = bkchem_qt.actions.pubchem_actions._insert_dialog_result(
			main_window, dialog,
		)
		unchanged = survivor.backend_snapshot == before
	finally:
		_close_dialog(qapp, dialog)
		_close_clean_session(main_window, survivor)

	assert not inserted
	assert unchanged


#============================================
def test_pubchem_worker_terminal_delivery_skips_closed_source_session(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Queued lookup completion cannot revisit a source session after tab close."""
	origin = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	survivor = _new_session(main_window)
	origin_identity = id(origin)
	release_calls = []
	original_release = bkchem_qt.models.document_session.DocumentSession.release_import_worker

	def record_direct_origin_release(session: object, worker: object) -> None:
		"""Record a legacy terminal callback without dereferencing its wrapper."""
		if id(session) == origin_identity:
			release_calls.append(worker)
			return
		original_release(session, worker)

	monkeypatch.setattr(
		bkchem_qt.models.document_session.DocumentSession,
		"release_import_worker",
		record_direct_origin_release,
	)
	try:
		dialog._query.setText("methane")
		dialog._lookup_button.click()
		worker = next(iter(origin._import_workers))
		if not worker.wait(1000):
			raise RuntimeError("Controlled PubChem worker did not finish")
		survivor_before = survivor.backend_snapshot
		_close_clean_session(main_window, origin)
		closed_status = dialog._status.text()
		qapp.processEvents()
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.MetaCall,
		)
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.DeferredDelete,
		)
		qapp.processEvents()
		terminal_delivery_inert = not release_calls and dialog._status.text() == closed_status
		survivor_unchanged = survivor.backend_snapshot == survivor_before
	finally:
		_close_dialog(qapp, dialog)
		_close_clean_session(main_window, survivor)

	assert terminal_delivery_inert
	assert survivor_unchanged


#============================================
def test_accepted_unprojectable_pubchem_result_is_consumed_once(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		) -> None:
	"""Projection recovery reuses only the accepted snapshot, never the proposal."""
	session = _new_session(main_window)
	dialog = bkchem_qt.actions.pubchem_actions.open_pubchem_lookup(
		main_window, _pubchem_transport,
	)
	live_session = _new_session(main_window)
	try:
		token = session.begin_import_request()
		dialog.set_lookup_result(_prepared(session, token), session, token)
		start_revision = session.backend_snapshot.revision
		_install_projection_port(session, _projection_unavailable)
		inserted = bkchem_qt.actions.pubchem_actions._insert_dialog_result(
			main_window, dialog,
		)
		revision_delta = session.backend_snapshot.revision - start_revision
		resubmitted = bkchem_qt.actions.pubchem_actions._insert_dialog_result(
			main_window, dialog,
		)
		_install_projection_port(session, session.replace_projection_from_backend_snapshot)
		recovered = session.retry_current_backend_projection().status == "accepted"
	finally:
		_close_dialog(qapp, dialog)
		_undo_and_close(main_window, session)
		_close_clean_session(main_window, live_session)

	assert inserted and not resubmitted and revision_delta == 1
	assert recovered
