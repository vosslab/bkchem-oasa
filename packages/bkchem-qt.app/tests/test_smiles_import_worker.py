"""Focused public acceptance evidence for interactive SMILES insertion."""

# Standard Library
import math
import xml.dom.minidom

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.bridge.worker
import oasa.cdml_writer
import oasa.cdml
import oasa.cdml_document
import oasa.cdml_xml
import oasa.coords_generator
import oasa.safe_xml
import oasa.smiles_lib


_MIXED_CDML = '''<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml"
xmlns:vendor="urn:example:vendor" version="0.15"><bk:molecule id="molecule_1"><bk:atom
id="atom_1" name="C"><bk:point x="1cm" y="1cm" /></bk:atom></bk:molecule><bk:text
id="text_1"><bk:ftext>yield</bk:ftext></bk:text><vendor:note keep="yes">opaque
<vendor:child flag="keep" /></vendor:note></bk:cdml>'''


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


def _current_session(main_window: object) -> object:
	"""Return the session that owns MainWindow's public active document."""
	return next(
		session for session in main_window.sessions
		if session.document is main_window.document
	)


#============================================
def _new_session(main_window: object) -> object:
	"""Create and select one independent public test session."""
	if not main_window.on_new():
		raise RuntimeError("Public New did not create a SMILES test session")
	return _current_session(main_window)


#============================================
def _close_clean_session(main_window: object, session: object) -> None:
	"""Close one already-clean test session through the public tab API."""
	if not main_window.close_session_at(main_window.sessions.index(session)):
		raise RuntimeError("Public close did not remove the clean SMILES test session")


#============================================
def _undo_and_close(main_window: object, session: object) -> None:
	"""Return one accepted edit to its saved backend baseline and close its tab."""
	if session.undo_backend().status != "accepted":
		raise RuntimeError("Public backend undo did not restore the SMILES baseline")
	_close_clean_session(main_window, session)


#============================================
def _prepared_ethanol(session: object, token_stem: str) -> object:
	"""Build a valid deterministic proposal for delivery-controller tests."""
	molecule = oasa.smiles_lib.text_to_mol("CCO")
	oasa.coords_generator.calculate_coords(molecule, bond_length=1.0, force=1)
	proposal_cdml = oasa.cdml_writer.molecules_to_insertion_proposal(
		[molecule], token_stem=token_stem,
	)
	return bkchem_qt.bridge.worker.PreparedMoleculeInsertion(
		proposal_cdml, session.backend_snapshot.revision,
	)


#============================================
def _direct_elements(element: xml.dom.minidom.Element) -> list[xml.dom.minidom.Element]:
	"""Return direct CDML element children in their semantic order."""
	return [
		child for child in element.childNodes
		if isinstance(child, xml.dom.minidom.Element)
	]


#============================================
def _inspected_compatibility_root(cdml: str) -> xml.dom.minidom.Element:
	"""Authorize CDML before compatibility-only DOM structure assertions."""
	oasa.cdml_xml.inspect_cdml_xml(cdml.encode("utf-8"))
	root = oasa.safe_xml.parse_dom_from_string(cdml).documentElement
	return root


#============================================
def _molecule_is_cco(molecule: xml.dom.minidom.Element) -> bool:
	"""Return whether one canonical molecule has finite C-C-O topology."""
	atom_symbols = {}
	for atom in molecule.getElementsByTagName("atom"):
		point = next(child for child in _direct_elements(atom) if child.localName == "point")
		try:
			x = float(point.getAttribute("x")[:-2])
			y = float(point.getAttribute("y")[:-2])
		except ValueError:
			return False
		if not math.isfinite(x) or not math.isfinite(y):
			return False
		atom_symbols[atom.getAttribute("id")] = atom.getAttribute("name")
	if sorted(atom_symbols.values()) != ["C", "C", "O"]:
		return False
	bonds = {
		tuple(sorted((
			atom_symbols[bond.getAttribute("start")],
			atom_symbols[bond.getAttribute("end")],
		))) for bond in molecule.getElementsByTagName("bond")
	}
	return bonds == {("C", "C"), ("C", "O")}


#============================================
def _canonical_has_cco(cdml: str) -> bool:
	"""Find the inserted C-C-O molecule by semantic shape, not source order."""
	root = _inspected_compatibility_root(cdml)
	return any(
		_molecule_is_cco(child) for child in _direct_elements(root)
		if child.localName == "molecule"
	)


#============================================
def _insertion_geometry(cdml: str) -> tuple[float, tuple[float, float]]:
	"""Measure authorized proposal or accepted-CDML molecule coordinates."""
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
def _projection_has_cco(document: object) -> bool:
	"""Find the inserted projected molecule by its C-C-O semantic shape."""
	for molecule in document.molecules:
		if sorted(atom.symbol for atom in molecule.atoms) != ["C", "C", "O"]:
			continue
		bonds = {
			tuple(sorted((bond.atom1.symbol, bond.atom2.symbol))) for bond in molecule.bonds
		}
		if bonds == {("C", "C"), ("C", "O")}:
			return True
	return False


#============================================
def _delivery(main_window: object, session: object) -> tuple[object, object]:
	"""Create one current named SMILES delivery controller and proposal."""
	token = session.begin_import_request()
	delivery = bkchem_qt.actions.chemistry_actions.MoleculeInsertionDelivery(
		main_window, session, token, session.backend_snapshot.revision, "SMILES",
		"Imported SMILES molecule", bkchem_qt.actions.chemistry_actions._show_smiles_import_error,
	)
	return delivery, _prepared_ethanol(session, "smiles-r%s" % token)


#============================================
def _opaque_presentation_survives(cdml: str) -> bool:
	"""Return whether the existing text sibling and vendor extension survive."""
	root = _inspected_compatibility_root(cdml)
	text = next(child for child in _direct_elements(root) if child.localName == "text")
	note = next(child for child in _direct_elements(root) if child.localName == "note")
	ftext = next(child for child in _direct_elements(text) if child.localName == "ftext")
	child = next(item for item in _direct_elements(note) if item.localName == "child")
	return (
		"".join(item.data for item in ftext.childNodes if item.nodeType == item.TEXT_NODE)
		== "yield"
		and note.getAttribute("keep") == "yes"
		and "".join(item.data for item in note.childNodes if item.nodeType == item.TEXT_NODE).strip()
		== "opaque"
		and child.getAttribute("flag") == "keep"
	)


#============================================
def test_smiles_worker_prepares_frozen_plain_cco_proposal(qtbot: object) -> None:
	"""The actual worker emits a plain positioned C-C-O proposal before delivery."""
	worker = bkchem_qt.bridge.worker.TextMoleculeInsertionWorker(
		"smiles", "CCO", 7, "worker", 40.0, (2000.0, 1500.0),
		"Imported SMILES molecule",
	)
	prepared_values = []
	worker.result.connect(prepared_values.append)
	worker.finished.connect(worker.deleteLater)
	try:
		with qtbot.waitSignal(worker.finished, timeout=1000):
			worker.start()
	finally:
		if worker.isRunning():
			worker.quit()
			worker.wait(1000)
	PySide6.QtCore.QCoreApplication.sendPostedEvents(
		None, PySide6.QtCore.QEvent.Type.DeferredDelete,
	)

	assert prepared_values[0].expected_revision == 7
	assert _canonical_has_cco(prepared_values[0].proposal_cdml)


#============================================
def test_smiles_preparation_persists_captured_insertion_geometry() -> None:
	"""The actual CCO proposal and accepted backend state retain scene geometry."""
	prepared = bkchem_qt.bridge.worker._prepare_text_molecule_insertion(
		"smiles", "CCO", 0, "smiles-geometry", 35.0, (321.0, 654.0),
		"Imported SMILES molecule",
	)
	session = oasa.cdml_document.CDMLDocumentSession.load("<cdml />")
	accepted = session.insert_molecules(oasa.cdml_document.CDMLMoleculeInsertionRequest(
		expected_revision=0, proposal_cdml=prepared.proposal_cdml,
	)).cdml

	accepted_mean, accepted_centroid = _insertion_geometry(accepted)
	proposal_mean, proposal_centroid = _insertion_geometry(prepared.proposal_cdml)
	assert (accepted_mean, *accepted_centroid) == pytest.approx((35.0, 321.0, 654.0), rel=0.02)
	assert (proposal_mean, *proposal_centroid) == pytest.approx((accepted_mean, *accepted_centroid))


#============================================
def test_accepted_smiles_changes_only_its_origin_revision(main_window: object) -> None:
	"""A captured origin receives one revision while a separately opened tab does not."""
	origin = _new_session(main_window)
	other = _new_session(main_window)
	origin_start = origin.backend_snapshot
	other_start = other.backend_snapshot
	try:
		delivery, prepared = _delivery(main_window, origin)
		delivery.deliver(prepared)
		origin_delta = origin.backend_snapshot.revision - origin_start.revision
		other_unchanged = other.backend_snapshot == other_start
	finally:
		_undo_and_close(main_window, origin)
		_close_clean_session(main_window, other)

	assert origin_delta == 1
	assert other_unchanged


#============================================
def test_accepted_smiles_matches_canonical_and_projected_cco_semantics(
		main_window: object,
		) -> None:
	"""The accepted canonical molecule and disposable projection agree semantically."""
	session = _new_session(main_window)
	try:
		delivery, prepared = _delivery(main_window, session)
		delivery.deliver(prepared)
		canonical_cco = _canonical_has_cco(session.backend_snapshot.cdml)
		projected_cco = _projection_has_cco(session.document)
	finally:
		_undo_and_close(main_window, session)

	assert canonical_cco
	assert projected_cco


#============================================
def test_accepted_smiles_marks_the_public_backend_snapshot_dirty(
		main_window: object,
		) -> None:
	"""One accepted insertion is visible as an unsaved authoritative edit."""
	session = _new_session(main_window)
	try:
		delivery, prepared = _delivery(main_window, session)
		delivery.deliver(prepared)
		dirty = session.backend_snapshot.is_dirty
	finally:
		_undo_and_close(main_window, session)

	assert dirty


#============================================
def test_smiles_insertion_preserves_mixed_canonical_siblings(
		main_window: object, tmp_path: object, monkeypatch: object,
		) -> None:
	"""A native-opened presentation sibling and opaque extension survive insertion."""
	source = tmp_path / "mixed.cdml"
	source.write_text(_MIXED_CDML, encoding="utf-8")
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", lambda *_args: None)
	staging = _new_session(main_window)
	main_window.open_file_path(str(source))
	session = _current_session(main_window)
	_close_clean_session(main_window, staging)
	try:
		delivery, prepared = _delivery(main_window, session)
		delivery.deliver(prepared)
		preserved = _opaque_presentation_survives(session.backend_snapshot.cdml)
		inserted = _canonical_has_cco(session.backend_snapshot.cdml)
		session.write_backend_snapshot(str(tmp_path / "saved-mixed.cdml"))
		_close_clean_session(main_window, session)
	finally:
		if session in main_window.sessions:
			_close_clean_session(main_window, session)

	assert preserved
	assert inserted


#============================================
def test_smiles_insertion_has_no_qt_local_undo_command(main_window: object) -> None:
	"""The migration leaves the public Qt undo stack empty after acceptance."""
	session = _new_session(main_window)
	try:
		delivery, prepared = _delivery(main_window, session)
		delivery.deliver(prepared)
		qt_undo_available = session.document.undo_stack.canUndo()
		backend_undo_available = session.can_undo_backend
	finally:
		_undo_and_close(main_window, session)

	assert not qt_undo_available
	assert backend_undo_available


#============================================
def test_backend_undo_then_redo_removes_and_restores_smiles_topology(
		main_window: object,
		) -> None:
	"""Backend navigation, rather than Qt-local commands, controls the insertion."""
	session = _new_session(main_window)
	try:
		delivery, prepared = _delivery(main_window, session)
		delivery.deliver(prepared)
		session.undo_backend()
		undone = not _canonical_has_cco(session.backend_snapshot.cdml)
		session.redo_backend()
		redone = _canonical_has_cco(session.backend_snapshot.cdml)
	finally:
		_undo_and_close(main_window, session)

	assert undone
	assert redone


#============================================
def test_invalidated_smiles_request_is_inert(main_window: object) -> None:
	"""The public request-invalidation fence discards an old prepared result."""
	session = _new_session(main_window)
	before = session.backend_snapshot
	try:
		delivery, prepared = _delivery(main_window, session)
		session.invalidate_import_requests()
		outcome = delivery.deliver(prepared)
		unchanged = session.backend_snapshot == before
	finally:
		_close_clean_session(main_window, session)

	assert outcome.status == "discarded"
	assert unchanged


#============================================
def test_stale_smiles_revision_does_not_change_current_snapshot(
		main_window: object, monkeypatch: object,
		) -> None:
	"""A current delivery with an old revision is rejected without rebasing."""
	session = _new_session(main_window)
	monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", lambda *_args: None)
	try:
		initial_revision = session.backend_snapshot.revision
		current_delivery, current_prepared = _delivery(main_window, session)
		current_delivery.deliver(current_prepared)
		before = session.backend_snapshot
		stale_token = session.begin_import_request()
		stale_delivery = bkchem_qt.actions.chemistry_actions.MoleculeInsertionDelivery(
			main_window, session, stale_token, initial_revision, "SMILES",
			"Imported SMILES molecule", bkchem_qt.actions.chemistry_actions._show_smiles_import_error,
		)
		stale_prepared = bkchem_qt.bridge.worker.PreparedMoleculeInsertion(
			_prepared_ethanol(session, "stale").proposal_cdml, initial_revision,
		)
		outcome = stale_delivery.deliver(stale_prepared)
		unchanged = session.backend_snapshot == before
	finally:
		_undo_and_close(main_window, session)

	assert outcome.status == "rejected"
	assert unchanged


#============================================
def test_closed_origin_suppresses_result_and_error_without_affecting_live_tab(
		main_window: object, monkeypatch: object,
		) -> None:
	"""A closed source tab discards both worker paths and leaves the live tab intact."""
	origin = _new_session(main_window)
	other = _new_session(main_window)
	delivery, prepared = _delivery(main_window, origin)
	warnings = []
	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox, "warning",
		lambda *_args: warnings.append("shown"),
	)
	other_before = other.backend_snapshot
	try:
		_close_clean_session(main_window, origin)
		delivery.deliver(prepared)
		delivery.report_error("closed worker failure")
		other_unchanged = other.backend_snapshot == other_before
	finally:
		_close_clean_session(main_window, other)

	assert warnings == []
	assert other_unchanged


#============================================
def test_stale_smiles_error_is_silent(main_window: object, monkeypatch: object) -> None:
	"""An invalidated request does not surface a late worker warning."""
	session = _new_session(main_window)
	warnings = []
	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox, "warning",
		lambda *_args: warnings.append("shown"),
	)
	try:
		delivery, _prepared = _delivery(main_window, session)
		session.invalidate_import_requests()
		reported = delivery.report_error("late worker failure")
	finally:
		_close_clean_session(main_window, session)

	assert not reported
	assert warnings == []


#============================================
def test_unprojectable_smiles_acceptance_records_one_backend_revision(
		main_window: object,
		) -> None:
	"""Projection failure retains the accepted backend result exactly once."""
	session = _new_session(main_window)
	live_session = _new_session(main_window)
	try:
		start = session.backend_snapshot
		delivery, prepared = _delivery(main_window, session)
		_install_projection_port(session, _projection_unavailable)
		outcome = delivery.deliver(prepared)
		revision_delta = session.backend_snapshot.revision - start.revision
		_install_projection_port(session, session.replace_projection_from_backend_snapshot)
		session.retry_current_backend_projection()
		PySide6.QtWidgets.QApplication.processEvents()
	finally:
		_undo_and_close(main_window, session)
		_close_clean_session(main_window, live_session)

	assert outcome.submitted
	assert revision_delta == 1


#============================================
def test_smiles_reprojection_restores_the_exact_current_projection(
		main_window: object,
		) -> None:
	"""Recovery projects only the already accepted current canonical snapshot."""
	session = _new_session(main_window)
	live_session = _new_session(main_window)
	try:
		delivery, prepared = _delivery(main_window, session)
		_install_projection_port(session, _projection_unavailable)
		delivery.deliver(prepared)
		canonical_cco = _canonical_has_cco(session.backend_snapshot.cdml)
		_install_projection_port(session, session.replace_projection_from_backend_snapshot)
		outcome = session.retry_current_backend_projection()
		PySide6.QtWidgets.QApplication.processEvents()
		projected_cco = _projection_has_cco(session.document)
	finally:
		_undo_and_close(main_window, session)
		_close_clean_session(main_window, live_session)

	assert outcome.status == "accepted"
	assert canonical_cco and projected_cco
