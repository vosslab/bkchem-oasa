"""Behavior test for GUI-thread delivery of prepared OASA imports."""

# Standard Library
import threading

# local repo modules
import bkchem_qt.actions.file_actions
import bkchem_qt.bridge.worker


#============================================
def _delete_worker(worker: object) -> None:
	"""Release a worker wrapper unless its controlled owner already did so."""
	try:
		worker.deleteLater()
	except RuntimeError:
		pass


#============================================
def test_interruption_cancels_delivery_only_after_native_callable_returns(
		qtbot: object) -> None:
	"""An interrupted opaque call runs through its release boundary silently."""
	started = threading.Event()
	release = threading.Event()
	deliveries = []

	def controlled_call() -> str:
		"""Block until the test permits native completion."""
		started.set()
		release.wait()
		return "prepared"

	worker = bkchem_qt.bridge.worker.OasaWorker(controlled_call)
	worker.result.connect(deliveries.append)
	worker.start()
	try:
		qtbot.waitUntil(started.is_set)
		worker.requestInterruption()
		with qtbot.waitSignal(worker.finished):
			release.set()
		qtbot.waitUntil(lambda: worker.outcome is not None)
		assert worker.outcome is bkchem_qt.bridge.worker.WorkerTerminalOutcome.DELIVERY_CANCELLED
		assert deliveries == []
	finally:
		release.set()
		try:
			if worker.isRunning():
				worker.wait()
		except RuntimeError:
			pass
		_delete_worker(worker)


#============================================
def test_worker_reports_completed_and_failed_delivery_outcomes(qtbot: object) -> None:
	"""Normal result and exception paths expose distinct terminal semantics."""
	completed = bkchem_qt.bridge.worker.OasaWorker(lambda: "prepared")
	failed = bkchem_qt.bridge.worker.OasaWorker(
		lambda: (_ for _ in ()).throw(ValueError("bad input")),
	)
	for worker in (completed, failed):
		with qtbot.waitSignal(worker.finished):
			worker.start()
	assert (completed.outcome, failed.outcome) == (
		bkchem_qt.bridge.worker.WorkerTerminalOutcome.COMPLETED,
		bkchem_qt.bridge.worker.WorkerTerminalOutcome.FAILED,
	)
	assert (completed.lifecycle_state, failed.lifecycle_state) == (
		bkchem_qt.bridge.worker.WorkerLifecycleState.FINISHED,
		bkchem_qt.bridge.worker.WorkerLifecycleState.FINISHED,
	)
	_delete_worker(completed)
	_delete_worker(failed)


#============================================
def test_pre_start_invalidation_still_runs_native_work_without_delivery(qtbot: object) -> None:
	"""Qt's advisory pre-start interruption cannot reopen the delivery fence."""
	started = threading.Event()
	worker = bkchem_qt.bridge.worker.OasaWorker(lambda: started.set())
	worker.requestInterruption()
	try:
		with qtbot.waitSignal(worker.finished):
			worker.start()
		assert started.is_set()
		assert worker.outcome is bkchem_qt.bridge.worker.WorkerTerminalOutcome.DELIVERY_CANCELLED
	finally:
		if worker.isRunning():
			worker.wait()
		_delete_worker(worker)


#============================================
def test_direct_session_disposal_owns_running_worker_until_finished(
		main_window: object, qtbot: object) -> None:
	"""An unregistered session transfers a live worker to the orphan owner."""
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window,
		theme_manager=main_window._theme_manager,
		prefs=main_window._prefs,
		mode_host=main_window,
	)
	started = threading.Event()
	release = threading.Event()
	deliveries = []

	def controlled_call() -> str:
		"""Hold native completion until the source session is fully disposed."""
		started.set()
		release.wait()
		return "prepared"

	worker = bkchem_qt.bridge.worker.OasaWorker(controlled_call)
	worker.result.connect(deliveries.append)
	session.track_import_worker(worker)
	worker.start()
	try:
		qtbot.waitUntil(started.is_set)
		before = bkchem_qt.models.document_session.orphaned_import_worker_count()
		session.dispose()
		assert (
			session.is_disposed,
			bkchem_qt.models.document_session.orphaned_import_worker_count(),
		) == (True, before + 1)
		with qtbot.waitSignal(worker.finished):
			release.set()
		qtbot.waitUntil(
			lambda: bkchem_qt.models.document_session.orphaned_import_worker_count() == before,
		)
		assert (
			bkchem_qt.models.document_session.orphaned_import_worker_count(), deliveries,
		) == (before, [])
	finally:
		release.set()
		try:
			if worker.isRunning():
				worker.wait()
		except RuntimeError:
			pass
		_delete_worker(worker)


#============================================
def test_disposed_session_cancels_later_import_worker(
		main_window: object, qtbot: object) -> None:
	"""A disposed session retains and cancels a subsequently tracked worker."""
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window,
		theme_manager=main_window._theme_manager,
		prefs=main_window._prefs,
		mode_host=main_window,
	)
	before = bkchem_qt.models.document_session.orphaned_import_worker_count()
	session.dispose()
	started = threading.Event()
	worker = bkchem_qt.bridge.worker.OasaWorker(started.set)
	session.track_import_worker(worker)
	try:
		assert bkchem_qt.models.document_session.orphaned_import_worker_count() == before + 1
		with qtbot.waitSignal(worker.finished):
			worker.start()
		qtbot.waitUntil(
			lambda: bkchem_qt.models.document_session.orphaned_import_worker_count() == before,
		)
		assert (started.is_set(), worker.outcome) == (
			True, bkchem_qt.bridge.worker.WorkerTerminalOutcome.DELIVERY_CANCELLED,
		)
	finally:
		if worker.isRunning():
			worker.wait()
		_delete_worker(worker)


#============================================
def test_tab_close_transfers_blocked_worker_without_stale_delivery(
		main_window: object, qtbot: object) -> None:
	"""Closing a tab returns before its native call finishes and releases later."""
	session = main_window.sessions[0]
	started = threading.Event()
	release = threading.Event()
	deliveries = []

	def controlled_call() -> str:
		"""Hold native work while its source session is disposed."""
		started.set()
		release.wait()
		return "prepared"

	worker = bkchem_qt.bridge.worker.OasaWorker(controlled_call)
	worker.result.connect(deliveries.append)
	worker.finished.connect(lambda: main_window._release_import_worker(worker))
	session.track_import_worker(worker)
	main_window._on_new()
	worker.start()
	try:
		qtbot.waitUntil(started.is_set)
		assert main_window.close_session_at(0) and session.is_disposed
		with qtbot.waitSignal(worker.finished):
			release.set()
		qtbot.waitUntil(lambda: main_window.retiring_worker_count == 0)
		assert deliveries == []
	finally:
		release.set()
		try:
			if worker.isRunning():
				worker.wait()
		except RuntimeError:
			pass
		_delete_worker(worker)


#============================================
def test_import_relay_delivers_prepared_complete_cdml(main_window: object) -> None:
	"""External document Open crosses the GUI boundary as plain complete CDML."""
	deliveries = []
	prepared = bkchem_qt.bridge.worker.PreparedCompleteCDML(
		'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07"></cdml>',
		"sample.mol",
	)

	relay = bkchem_qt.actions.file_actions._ImportResultRelay(
		main_window, object(), "sample.mol",
		on_loaded=deliveries.append,
	)
	relay.on_result(prepared)
	assert deliveries == [prepared]


#============================================
def test_import_relay_reports_no_molecules_for_none(main_window: object) -> None:
	"""The established empty import outcome reaches the session error path."""
	errors = []
	relay = bkchem_qt.actions.file_actions._ImportResultRelay(
		main_window, object(), "sample.mol", on_error=errors.append,
	)
	relay.on_result(None)
	assert errors == ["No molecules found"]


#============================================
def test_import_relay_rejects_missing_delivery_without_session_mutation(
		main_window: object) -> None:
	"""A prepared import without a delivery capability becomes a typed error."""
	errors = []
	target = main_window.sessions[0]
	original_document = target.document
	prepared = bkchem_qt.bridge.worker.PreparedCompleteCDML("<cdml />", "sample.mol")
	relay = bkchem_qt.actions.file_actions._ImportResultRelay(
		main_window, object(), "sample.mol", on_error=errors.append,
	)
	relay.on_result(prepared)
	assert (type(errors[0]), target.document) == (TypeError, original_document)


#============================================
def test_import_relay_rejects_graph_shaped_result_without_session_mutation(
		main_window: object) -> None:
	"""A graph-shaped worker result cannot reach the target document session."""
	errors = []
	target = main_window.sessions[0]
	original_document = target.document
	relay = bkchem_qt.actions.file_actions._ImportResultRelay(
		main_window, object(), "sample.mol", on_error=errors.append,
	)
	relay.on_result([object()])
	assert (type(errors[0]), target.document) == (TypeError, original_document)
