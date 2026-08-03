"""Focused application event-loop shutdown coverage."""

# Standard Library
import pathlib
import threading

# PIP3 modules
import pytest
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.app
import bkchem_qt.main_window
import bkchem_qt.themes.theme_manager
import bkchem_qt.bridge.worker


#============================================
class _ControlledTimerApplication:
	"""Minimal event-loop seam for one deterministic controlled-smoke callback."""

	def __init__(self, delivery: bkchem_qt.app._SmokeTimerDelivery) -> None:
		"""Retain the delivery state that quit must observe."""
		self._delivery = delivery
		self.delivery_before_quit = False
		self.quit_requested = False

	def quit(self) -> None:
		"""Observe delivery state at the exact controlled event-loop exit request."""
		self.delivery_before_quit = self._delivery.timer_fired
		self.quit_requested = True

	def exec(self) -> int:
		"""Return the normal event-loop result only after controlled quit."""
		return 0 if self.quit_requested else 1


#============================================
def test_programmatic_event_loop_exit_retires_live_session_through_window_boundary(
		qapp: PySide6.QtWidgets.QApplication,
		theme_manager: bkchem_qt.themes.theme_manager.ThemeManager,
		) -> None:
	"""A direct application quit still drains the window-owned session graph."""
	window = bkchem_qt.main_window.MainWindow(theme_manager)
	session = window.sessions[0]
	PySide6.QtCore.QTimer.singleShot(0, qapp.quit)

	assert qapp.exec() == 0
	assert bkchem_qt.app._finalize_event_loop_exit(qapp, window, 0) == 0
	assert session.is_disposed


#============================================
def test_shutdown_drains_retired_worker_through_a_nested_qt_event_loop(
		qapp: PySide6.QtWidgets.QApplication,
		theme_manager: bkchem_qt.themes.theme_manager.ThemeManager,
		qtbot: object,
		) -> None:
	"""Shutdown retains native work until its queued finished signal releases it."""
	window = bkchem_qt.main_window.MainWindow(theme_manager)
	session = window.sessions[0]
	started = threading.Event()
	release = threading.Event()

	def controlled_call() -> str:
		"""Hold native completion until shutdown has entered draining."""
		started.set()
		release.wait()
		return "prepared"

	worker = bkchem_qt.bridge.worker.OasaWorker(controlled_call)
	session.track_import_worker(worker)
	worker.finished.connect(lambda: window._release_import_worker(worker))
	worker.start()
	try:
		qtbot.waitUntil(started.is_set)
		assert window.prepare_application_shutdown()
		assert window.shutdown_state is bkchem_qt.main_window.ShutdownState.DRAINING
		assert window.retiring_worker_count == 1 and not window.sessions
		PySide6.QtCore.QTimer.singleShot(0, release.set)
		assert bkchem_qt.main_window.drain_pending_session_deletions(qapp, window)
		assert window.shutdown_state is bkchem_qt.main_window.ShutdownState.READY
		assert session.is_disposed
	finally:
		release.set()
		try:
			if worker.isRunning():
				worker.wait()
		except RuntimeError:
			pass
		bkchem_qt.main_window.delete_qobject_and_wait(qapp, window)


#============================================
def test_successful_smoke_receipt_is_published_atomically_after_timer_success(
		tmp_path: pathlib.Path,
		) -> None:
	"""A zero controlled-shutdown result publishes only the fixed receipt schema."""
	receipt_path = tmp_path / "completion.json"

	bkchem_qt.app._write_smoke_receipt(receipt_path, 0, timer_fired=True)

	assert receipt_path.read_text(encoding="utf-8") == '{"exit_code":0,"schema":"bkchem-smoke-1"}'


#============================================
def test_failed_smoke_shutdown_does_not_publish_a_receipt(tmp_path: pathlib.Path) -> None:
	"""A failed retirement result cannot be mistaken for completed Qt lifecycle."""
	receipt_path = tmp_path / "completion.json"

	with pytest.raises(RuntimeError, match="successful controlled shutdown"):
		bkchem_qt.app._write_smoke_receipt(receipt_path, 1, timer_fired=True)

	assert not receipt_path.exists()


#============================================
def test_smoke_receipt_requires_a_delivered_timer(tmp_path: pathlib.Path) -> None:
	"""Receipt publication refuses a clean result without timer delivery evidence."""
	receipt_path = tmp_path / "completion.json"

	with pytest.raises(RuntimeError, match="controlled smoke timer"):
		bkchem_qt.app._write_smoke_receipt(receipt_path, 0, timer_fired=False)

	assert not receipt_path.exists()


#============================================
@pytest.mark.parametrize("timer_seconds", (None, 0.0, float("nan")))
def test_app_rejects_a_receipt_configuration_without_a_valid_timer(
		timer_seconds: float | None, tmp_path: pathlib.Path,
		) -> None:
	"""The app entry boundary requires a finite positive timer for a smoke receipt."""

	with pytest.raises(ValueError, match="finite positive"):
		bkchem_qt.app._validate_smoke_configuration(timer_seconds, tmp_path / "completion.json")


#============================================
def test_early_clean_exit_does_not_publish_a_smoke_receipt(
		monkeypatch: pytest.MonkeyPatch, qapp: PySide6.QtWidgets.QApplication,
		tmp_path: pathlib.Path,
		) -> None:
	"""An ordinary early close is clean but cannot certify timer-driven smoke."""
	receipt_path = tmp_path / "completion.json"
	monkeypatch.setattr(bkchem_qt.app, "_finalize_event_loop_exit", lambda *_args: 0)

	completed = bkchem_qt.app._complete_event_loop_exit(
		qapp, None, 0, receipt_path, timer_fired=False,
	)

	assert completed == 0
	assert not receipt_path.exists()


#============================================
def test_timer_fired_clean_exit_publishes_a_smoke_receipt(
		monkeypatch: pytest.MonkeyPatch, qapp: PySide6.QtWidgets.QApplication,
		tmp_path: pathlib.Path,
		) -> None:
	"""A delivered timer plus successful finalization publishes the fixed receipt."""
	receipt_path = tmp_path / "completion.json"
	monkeypatch.setattr(bkchem_qt.app, "_finalize_event_loop_exit", lambda *_args: 0)

	completed = bkchem_qt.app._complete_event_loop_exit(
		qapp, None, 0, receipt_path, timer_fired=True,
	)

	assert completed == 0
	assert receipt_path.read_text(encoding="utf-8") == '{"exit_code":0,"schema":"bkchem-smoke-1"}'


#============================================
def test_scheduled_smoke_callback_records_delivery_before_quit_and_publishes_receipt(
		monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
		) -> None:
	"""The captured Qt timer callback proves delivery before controlled quit and receipt."""
	receipt_path = tmp_path / "completion.json"
	delivery = bkchem_qt.app._SmokeTimerDelivery()
	application = _ControlledTimerApplication(delivery)
	callbacks: list = []

	def capture_timer_callback(_milliseconds: int, callback: object) -> None:
		"""Capture the production callback without starting a Qt event loop."""
		callbacks.append(callback)

	monkeypatch.setattr(PySide6.QtCore.QTimer, "singleShot", capture_timer_callback)
	monkeypatch.setattr(bkchem_qt.app, "_finalize_event_loop_exit", lambda *_args: 0)
	bkchem_qt.app._schedule_controlled_smoke_exit(application, 2000, delivery)
	callbacks[0]()
	completed = bkchem_qt.app._complete_event_loop_exit(
		application, None, application.exec(), receipt_path, delivery.timer_fired,
	)

	assert application.delivery_before_quit and completed == 0
	assert receipt_path.read_text(encoding="utf-8") == '{"exit_code":0,"schema":"bkchem-smoke-1"}'
