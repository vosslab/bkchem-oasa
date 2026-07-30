"""Application bootstrap for BKChem-Qt."""

# Standard Library
import dataclasses
import json
import math
import os
import pathlib
import signal
import sys

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.themes.theme_manager
import bkchem_qt.main_window
import bkchem_qt.io.clipboard_mime
import bkchem_qt.versioning

# application metadata
APP_NAME = "BKChem-Qt"
APP_ORG = "BKChem"
SMOKE_RECEIPT_SCHEMA = "bkchem-smoke-1"


#============================================
@dataclasses.dataclass
class _SmokeTimerDelivery:
	"""Retain controlled-smoke timer delivery until the event loop has retired."""

	timer_fired: bool = False


#============================================
def _schedule_controlled_smoke_exit(
		app: PySide6.QtWidgets.QApplication,
		milliseconds: int,
		delivery: _SmokeTimerDelivery,
		) -> None:
	"""Schedule normal Qt exit after recording controlled timer delivery.

	The delivery record is deliberately separate from the callback closure so the
	post-event-loop receipt gate can require evidence from this callback.
	"""
	def finish_controlled_smoke() -> None:
		"""Record timer delivery before asking Qt to leave its normal event loop."""
		delivery.timer_fired = True
		app.quit()

	PySide6.QtCore.QTimer.singleShot(milliseconds, finish_controlled_smoke)


#============================================
def _clear_application_clipboard(app: PySide6.QtWidgets.QApplication) -> None:
	"""Release only BKChem's wrapped MIME data before Python exits.

	Plain text remains available after shutdown, while foreign clipboard content
	is never changed.
	"""
	clipboard = app.clipboard()
	mime_data = clipboard.mimeData()
	if mime_data is None or not mime_data.property(
		bkchem_qt.io.clipboard_mime.BKCHEM_OWNED_MIME_PROPERTY,
	):
		return
	plain_text = mime_data.text()
	clipboard.clear()
	PySide6.QtCore.QCoreApplication.sendPostedEvents(
		None, PySide6.QtCore.QEvent.Type.DeferredDelete,
	)
	app.processEvents()
	if plain_text:
		clipboard.setText(plain_text)


#============================================
def _open_launch_files(window: object, files: list | None) -> int:
	"""Open command-line paths through the same document-session API as File."""
	opened = 0
	for file_path in files or []:
		if window.open_file_path(file_path):
			opened += 1
	return opened


#============================================
def _finalize_event_loop_exit(
		app: PySide6.QtWidgets.QApplication,
		window: bkchem_qt.main_window.MainWindow | None,
		exit_code: int,
		) -> int | None:
	"""Retire one MainWindow after the QApplication event loop returns.

	Returns:
		The event-loop exit code after controlled retirement, or None when the
		user keeps the window live through the normal Save/Discard/Cancel path.
	"""
	if window is None:
		_clear_application_clipboard(app)
		return exit_code
	if not window.prepare_application_shutdown():
		return None
	if not bkchem_qt.main_window.drain_pending_session_deletions(app, window):
		return 1
	_clear_application_clipboard(app)
	if not bkchem_qt.main_window.delete_qobject_and_wait(app, window):
		return 1
	return exit_code


#============================================
def _validate_smoke_configuration(
		smoke_exit_seconds: float | None, smoke_receipt_path: str | pathlib.Path | None,
		) -> None:
	"""Require one valid timer for every requested controlled-smoke receipt.

	Args:
		smoke_exit_seconds: Optional requested event-loop timer duration.
		smoke_receipt_path: Optional controlled-smoke completion destination.

	Raises:
		ValueError: If a timer is non-finite/non-positive, or a receipt lacks one.
	"""
	if smoke_exit_seconds is not None and (
		not math.isfinite(smoke_exit_seconds) or smoke_exit_seconds <= 0.0
	):
		raise ValueError("--smoke-exit must be a finite positive number of seconds")
	if smoke_receipt_path is not None and smoke_exit_seconds is None:
		raise ValueError("--smoke-receipt requires a finite positive --smoke-exit")


#============================================
def _write_smoke_receipt(
		receipt_path: str | pathlib.Path, exit_code: int, *, timer_fired: bool,
		) -> None:
	"""Atomically publish the fixed successful lifecycle receipt.

	Args:
		receipt_path: Caller-selected destination below its isolated run root.
		exit_code: Completed controlled-shutdown result.
		timer_fired: Whether the scheduled controlled-smoke timer callback ran.

	Raises:
		RuntimeError: If lifecycle completion was not timer-driven, was unsuccessful,
			or publication fails.
	"""
	if not timer_fired:
		raise RuntimeError("A smoke receipt requires delivery of the controlled smoke timer")
	if exit_code != 0:
		raise RuntimeError("A smoke receipt requires a successful controlled shutdown")
	path = pathlib.Path(receipt_path)
	if path.exists():
		raise RuntimeError(f"Smoke receipt destination already exists: {path}")
	path.parent.mkdir(parents=True, exist_ok=True)
	temporary_path = path.with_name(f".{path.name}.tmp")
	if temporary_path.exists():
		raise RuntimeError(f"Smoke receipt temporary destination already exists: {temporary_path}")
	payload = json.dumps(
		{"schema": SMOKE_RECEIPT_SCHEMA, "exit_code": 0}, separators=(",", ":"), sort_keys=True,
	)
	try:
		with temporary_path.open("x", encoding="utf-8") as output:
			output.write(payload)
			output.flush()
			os.fsync(output.fileno())
		os.replace(temporary_path, path)
	except OSError as error:
		raise RuntimeError(f"Could not publish smoke receipt: {path}: {error}") from error


#============================================
def _complete_event_loop_exit(
		app: PySide6.QtWidgets.QApplication,
		window: bkchem_qt.main_window.MainWindow | None,
		exit_code: int,
		smoke_receipt_path: str | pathlib.Path | None,
		timer_fired: bool,
		) -> int | None:
	"""Finalize one event-loop return and publish only timer-driven smoke success.

	An ordinary early window close may finish cleanly, but it is not evidence that
	the requested controlled-smoke callback was delivered and therefore cannot
	publish a smoke receipt.
	"""
	completed_exit = _finalize_event_loop_exit(app, window, exit_code)
	if completed_exit is not None and smoke_receipt_path is not None and timer_fired:
		_write_smoke_receipt(smoke_receipt_path, completed_exit, timer_fired=True)
	return completed_exit


#============================================
def main(
		files: list | None = None, smoke_exit_seconds: float | None = None,
		smoke_receipt_path: str | pathlib.Path | None = None,
		) -> int:
	"""Create and run the BKChem-Qt application.

	Args:
		files: Optional list of file paths to open on launch.
		smoke_exit_seconds: Optional positive timer duration for a controlled
			startup and normal-shutdown smoke check.
		smoke_receipt_path: Optional success-only lifecycle receipt destination.

	Returns:
		Application exit code from the Qt event loop.
	"""
	_validate_smoke_configuration(smoke_exit_seconds, smoke_receipt_path)
	app = PySide6.QtWidgets.QApplication(sys.argv)
	style = app.style()
	app_icon = style.standardIcon(
		PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileIcon
	)

	# allow Ctrl+C in terminal to kill the Qt app
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	# set application metadata
	app.setApplicationName(APP_NAME)
	app.setOrganizationName(APP_ORG)
	app.setApplicationVersion(bkchem_qt.versioning.application_version())
	if not app_icon.isNull():
		app.setWindowIcon(app_icon)

	# set up Qt built-in string translations
	translator = PySide6.QtCore.QTranslator(app)
	locale_name = PySide6.QtCore.QLocale.system().name()
	qt_translations_path = PySide6.QtCore.QLibraryInfo.path(
		PySide6.QtCore.QLibraryInfo.LibraryPath.TranslationsPath
	)
	# load Qt's own translations for the system locale
	if translator.load(f"qtbase_{locale_name}", qt_translations_path):
		app.installTranslator(translator)

	# create the theme manager, restore saved or system theme
	theme_mgr = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_mgr.restore_theme()

	# create the main window
	window = bkchem_qt.main_window.MainWindow(theme_mgr)
	if not app_icon.isNull():
		window.setWindowIcon(app_icon)
	window.show()

	# restore saved geometry
	window.restore_geometry()

	# Open command-line files after the window is fully initialised.  The
	# session-aware MainWindow decides whether each path is a new tab or an
	# already-open source document.
	_open_launch_files(window, files)
	timer_delivery = _SmokeTimerDelivery()
	if smoke_exit_seconds is not None:
		# Use the normal Qt event-loop exit so coordinator-backed retirement runs.
		milliseconds = round(smoke_exit_seconds * 1000)
		_schedule_controlled_smoke_exit(app, milliseconds, timer_delivery)

	# A programmatic QApplication.quit() ends app.exec() without sending this
	# top-level window a close event.  Route that return through the same
	# approval and coordinator-backed retirement boundary as an ordinary close.
	while True:
		exit_code = app.exec()
		completed_exit = _complete_event_loop_exit(
			app, window, exit_code, smoke_receipt_path, timer_delivery.timer_fired,
		)
		if completed_exit is not None:
			return completed_exit
		window.show()
