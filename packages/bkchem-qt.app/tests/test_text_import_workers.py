"""Behavior coverage for authoritative interactive InChI and peptide insertion."""

# PIP3 modules
import pytest
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.chemistry_actions
import bkchem_qt.bridge.worker
import oasa.cdml
import oasa.peptide_utils


#============================================
def _formula_from_proposal(proposal_cdml: str) -> str:
	"""Return the formula carried by one validated insertion proposal."""
	molecule = next(iter(oasa.cdml.read_cdml(proposal_cdml)))
	return str(molecule.get_formula_dict())


#============================================
@pytest.mark.parametrize(
	("codec_name", "source_text", "label", "expected_formula"),
	[
		("inchi", "InChI=1S/CH4/h1H4", "Imported InChI molecule", "CH4"),
		("peptide", "AN", "Imported peptide sequence 'AN'", "C7H13N3O4"),
	],
)
def test_text_insertion_preparation_returns_a_plain_backend_proposal(
		codec_name: str, source_text: str, label: str, expected_formula: str,
		) -> None:
	"""Both supported text codecs produce the same immutable insertion shape."""
	prepared = bkchem_qt.bridge.worker._prepare_text_molecule_insertion(
		codec_name, source_text, 4, "text-import", 35.0, (120.0, 240.0), label,
	)

	assert prepared.label == label
	assert _formula_from_proposal(prepared.proposal_cdml) == expected_formula


#============================================
def test_peptide_text_validation_carries_its_dialog_stage() -> None:
	"""Invalid peptide input keeps the parser-specific UI failure vocabulary."""
	with pytest.raises(bkchem_qt.bridge.worker.TextImportPreparationError) as error:
		bkchem_qt.bridge.worker._prepare_text_molecule_insertion(
			"peptide", "A?", 0, "invalid", 35.0, (0.0, 0.0), "Import peptide",
		)

	assert error.value.stage == "peptide-validation"


#============================================
@pytest.mark.parametrize(
	("codec_name", "source_text", "label"),
	[
		("inchi", "InChI=1S/CH4/h1H4", "Imported InChI molecule"),
		("peptide", "AN", "Imported peptide sequence 'AN'"),
	],
)
def test_text_insertion_commits_through_backend_history_only(
		main_window: object, codec_name: str, source_text: str, label: str,
		) -> None:
	"""Accepted text insertion changes backend state and remains backend-undoable."""
	target = main_window._active_session
	request_token = target.begin_import_request()
	prepared = bkchem_qt.bridge.worker._prepare_text_molecule_insertion(
		codec_name, source_text, target.backend_snapshot.revision,
		"accepted-%s" % codec_name,
		35.0, (120.0, 240.0), label,
	)
	delivery = bkchem_qt.actions.chemistry_actions.MoleculeInsertionDelivery(
		main_window, target, request_token, prepared.expected_revision,
		codec_name, label, lambda _app, _message: None,
	)
	accepted = delivery.deliver(prepared)
	qt_undo_available = target.document.undo_stack.canUndo()
	undone = target.undo_backend().status
	redone = target.redo_backend().status
	# Return the fixture session to its clean backend baseline.
	target.undo_backend()

	assert accepted.status == "accepted", accepted.message
	assert not qt_undo_available
	assert (undone, redone) == ("accepted", "accepted")


#============================================
def test_stale_text_insertion_leaves_the_backend_snapshot_unchanged(
		main_window: object,
		) -> None:
	"""A stale text proposal is discarded before an authoritative commit begins."""
	target = main_window._active_session
	prepared = bkchem_qt.bridge.worker._prepare_text_molecule_insertion(
		"inchi", "InChI=1S/CH4/h1H4", target.backend_snapshot.revision,
		"stale", 35.0, (120.0, 240.0), "Imported InChI molecule",
	)
	request_token = target.begin_import_request()
	delivery = bkchem_qt.actions.chemistry_actions.MoleculeInsertionDelivery(
		main_window, target, request_token, prepared.expected_revision, "InChI",
		prepared.label, lambda _app, _message: None,
	)
	target.invalidate_import_requests()
	before = target.backend_snapshot
	outcome = delivery.deliver(prepared)

	assert outcome.status == "discarded"
	assert target.backend_snapshot == before


#============================================
@pytest.mark.parametrize(
	("codec_name", "source_text", "label"),
	[
		("inchi", "InChI=1S/CH4/h1H4", "Imported InChI molecule"),
		("peptide", "AN", "Imported peptide sequence 'AN'"),
	],
)
def test_mismatched_text_revision_is_rejected_before_backend_mutation(
		main_window: object, codec_name: str, source_text: str, label: str,
		) -> None:
	"""A delayed text proposal is never rebased onto a later session revision."""
	target = main_window._active_session
	prepared = bkchem_qt.bridge.worker._prepare_text_molecule_insertion(
		codec_name, source_text, target.backend_snapshot.revision,
		"mismatched-%s" % codec_name, 35.0, (120.0, 240.0), label,
	)
	delivery = bkchem_qt.actions.chemistry_actions.MoleculeInsertionDelivery(
		main_window, target, target.begin_import_request(),
		prepared.expected_revision + 1, codec_name, label, lambda _app, _message: None,
	)
	before = target.backend_snapshot
	outcome = delivery.deliver(prepared)

	assert outcome.status == "rejected"
	assert target.backend_snapshot == before


#============================================
@pytest.mark.parametrize(
	("action_name", "codec_name", "source_text", "source_label", "success_message"),
	[
		("_read_smiles", "smiles", "CCO", "SMILES", "Imported SMILES molecule"),
		("_read_inchi", "inchi", "InChI=1S/CH4/h1H4", "InChI", "Imported InChI molecule"),
		("_read_peptide", "peptide", "AN", "Peptide Sequence", "Imported peptide sequence 'AN'"),
	],
)
def test_text_action_uses_the_shared_plain_proposal_worker(
		main_window: object, monkeypatch: pytest.MonkeyPatch, action_name: str,
		codec_name: str, source_text: str, source_label: str, success_message: str,
		) -> None:
	"""Every text route constructs the shared worker from plain scalar inputs."""
	captured = []
	original_init = bkchem_qt.bridge.worker.TextMoleculeInsertionWorker.__init__
	def capture_init(
			worker: object, worker_codec: str, worker_text: str,
			expected_revision: int, token_stem: str, mean_bond_length: float,
			insertion_anchor: tuple[float, float], worker_label: str,
			) -> None:
		captured.append((
			worker_codec, worker_text, expected_revision, token_stem,
			mean_bond_length, insertion_anchor, worker_label,
		))
		original_init(
			worker, worker_codec, worker_text, expected_revision, token_stem,
			mean_bond_length, insertion_anchor, worker_label,
		)
	monkeypatch.setattr(
		bkchem_qt.bridge.worker.TextMoleculeInsertionWorker, "__init__", capture_init,
	)
	monkeypatch.setattr(
		bkchem_qt.bridge.worker.TextMoleculeInsertionWorker, "start", lambda _worker: None,
	)
	monkeypatch.setattr(
		PySide6.QtWidgets.QInputDialog, "getText", lambda *_args: (source_text, True),
	)
	try:
		getattr(bkchem_qt.actions.chemistry_actions, action_name)(main_window)
		status_message = main_window.statusBar().currentMessage()
	finally:
		for worker in tuple(main_window._active_session._import_workers):
			main_window._active_session.release_import_worker(worker)

	worker_codec, worker_text, _revision, _token, mean_bond_length, anchor, worker_label = captured[0]
	assert (worker_codec, worker_text, worker_label) == (
		codec_name, source_text, success_message,
	)
	assert isinstance(mean_bond_length, float)
	assert type(anchor) is tuple
	assert tuple(type(value) for value in anchor) == (float, float)
	assert status_message == "Loading %s..." % source_label


#============================================
def test_peptide_worker_preserves_validation_error_through_the_common_relay(
		qapp: PySide6.QtWidgets.QApplication, main_window: object,
		monkeypatch: pytest.MonkeyPatch, qtbot: object,
		) -> None:
	"""The generic worker still reports peptide validation with its existing label."""
	reported = []
	worker = bkchem_qt.bridge.worker.TextMoleculeInsertionWorker(
		"peptide", "A?", 0, "invalid", 35.0, (0.0, 0.0), "Import peptide",
	)
	delivery = bkchem_qt.actions.chemistry_actions.MoleculeInsertionDelivery(
		main_window, main_window._active_session,
		main_window._active_session.begin_import_request(), 0, "Peptide Sequence",
		"Import peptide", bkchem_qt.actions.chemistry_actions._show_peptide_import_error,
	)
	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox, "warning",
		lambda _app, title, body: reported.append((title, body)),
	)
	relay = bkchem_qt.actions.chemistry_actions._MoleculeInsertionResultRelay(
		main_window._active_session, worker, delivery,
	)
	worker._result_relay = relay
	worker.error.connect(relay.on_error)
	worker.finished.connect(relay.on_thread_finished)
	main_window._active_session.track_import_worker(worker)
	with qtbot.waitSignal(worker.finished, timeout=2000):
		worker.start()
	qapp.processEvents()

	assert reported == [
		("Peptide Sequence Error", "Unrecognized amino acid code(s): ?\n"
		"Supported: " + ", ".join(sorted(oasa.peptide_utils.AMINO_ACID_SMILES))),
	]
