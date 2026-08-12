#!/usr/bin/env python3
"""Exercise installed BKChem-Qt authoritative edit, Save, close, and reopen."""

# Standard Library
import argparse
import importlib.metadata
import json
import math
import os
import pathlib
import sys


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt
import bkchem_qt.main_window
import bkchem_qt.themes.theme_manager
import oasa
import oasa.cdml_document


RECEIPT_SCHEMA = "bkchem-installed-authoritative-roundtrip-1"
TIMEOUT_EXIT_CODE = 124
_EMPTY_CDML = '<cdml version="0.15"/>'


#============================================
class ScenarioFailure(RuntimeError):
	"""Describe a completed scenario whose semantic assertion failed."""


#============================================
def _parse_args() -> argparse.Namespace:
	"""Parse one caller-owned output location and application deadline."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--kill-after", type=float, default=3.0, metavar="SECONDS",
		help="finish through Qt or record timeout after this many seconds (default: 3)",
	)
	parser.add_argument(
		"--output", required=True, metavar="PATH",
		help="existing output directory or new .cdml destination for this one run",
	)
	parser.add_argument(
		"--receipt", metavar="PATH",
		help="optional new JSON receipt destination",
	)
	args = parser.parse_args()
	if not math.isfinite(args.kill_after) or args.kill_after <= 0.0:
		parser.error("--kill-after requires a finite positive number of seconds")
	return args


#============================================
def _new_path(value: str, label: str) -> pathlib.Path:
	"""Accept one non-existing caller-controlled output path with an existing parent."""
	if not value.strip():
		raise ValueError("%s path must not be empty" % label)
	path = pathlib.Path(value).expanduser()
	if path.name in ("", ".", ".."):
		raise ValueError("%s path must name a file or directory" % label)
	if not path.parent.is_dir():
		raise ValueError("%s parent directory does not exist: %s" % (label, path.parent))
	return path.resolve()


#============================================
def _repo_tmp_path(value: str, label: str) -> pathlib.Path:
	"""Accept one new caller path only within the repository's retained tmp tree."""
	path = _new_path(value, label)
	tmp_root = pathlib.Path(__file__).resolve().parents[2] / "tmp"
	try:
		path.relative_to(tmp_root)
	except ValueError as error:
		raise ValueError("%s path must be inside %s" % (label, tmp_root)) from error
	return path


#============================================
def _output_paths(value: str) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
	"""Resolve one new Save target and two private native-CDML input paths."""
	path = _repo_tmp_path(value, "output")
	if path.suffix.lower() == ".cdml":
		saved_path = path
	else:
		if not path.is_dir():
			raise ValueError("output without a .cdml suffix must be an existing directory")
		saved_path = path / "authoritative_roundtrip.cdml"
	if saved_path.exists():
		raise ValueError("output CDML destination already exists: %s" % saved_path)
	source_path = saved_path.with_name(".%s.source.cdml" % saved_path.stem)
	if source_path.exists():
		raise ValueError("run input destination already exists: %s" % source_path)
	control_path = saved_path.with_name(".%s.control.cdml" % saved_path.stem)
	if control_path.exists():
		raise ValueError("run control destination already exists: %s" % control_path)
	return saved_path, source_path, control_path


#============================================
def _installed_origin(module: object, package_name: str) -> str:
	"""Return one installed module origin after rejecting repository package roots."""
	module_path = getattr(module, "__file__", None)
	if not isinstance(module_path, str):
		raise RuntimeError("%s has no module origin" % package_name)
	origin = pathlib.Path(module_path).resolve()
	repository_root = pathlib.Path(__file__).resolve().parents[2]
	for source_root in (
		repository_root / "packages" / "oasa",
		repository_root / "packages" / "bkchem-qt.app",
	):
		try:
			origin.relative_to(source_root)
		except ValueError:
			continue
		raise RuntimeError("installed mode resolved %s from source checkout: %s" % (
			package_name, origin,
		))
	return str(origin)


#============================================
def _arrow_identifier(snapshot: oasa.cdml_document.CDMLSnapshot) -> str:
	"""Read one durable editable Arrow from backend-owned projection facts."""
	backend = oasa.cdml_document.CDMLDocumentSession.load(snapshot.cdml)
	description = backend.projection_snapshot().plan.presentation_description
	for record in description.records:
		if record.kind == "arrow" and record.disposition == "editable":
			if record.identifier is None:
				break
			return record.identifier
	raise ScenarioFailure("backend presentation observation lacks an editable Arrow")


#============================================
class InstalledRoundtrip:
	"""Run one authoritative lifecycle entirely through the Qt event loop."""

	#============================================
	def __init__(
			self, app: PySide6.QtWidgets.QApplication, deadline_seconds: float,
			saved_path: pathlib.Path, source_path: pathlib.Path, control_path: pathlib.Path,
			) -> None:
		"""Retain only the application-owned state for one bounded scenario."""
		self._app = app
		self._deadline_seconds = deadline_seconds
		self._saved_path = saved_path
		self._source_path = source_path
		self._control_path = control_path
		self._window = None
		self._phase = "initialized"
		self._completed_phases = []
		self._status = "python-exception"
		self._diagnostic = "scenario did not run"
		self._exit_code = 1
		self._scenario_completed = False
		self._timer = PySide6.QtCore.QTimer(app)
		self._timer.setSingleShot(True)
		self._timer.timeout.connect(self._expire)

	#============================================
	def start(self) -> None:
		"""Start the sole lifetime deadline before the first scheduled phase."""
		self._timer.start(round(self._deadline_seconds * 1000))
		PySide6.QtCore.QTimer.singleShot(0, self._run)

	#============================================
	def _complete(self, phase: str) -> None:
		"""Record one completed public lifecycle phase."""
		self._phase = phase
		self._completed_phases.append(phase)

	#============================================
	def _expire(self) -> None:
		"""Reject modal interaction and request the bounded timeout exit."""
		self._status = "timeout"
		self._diagnostic = "deadline expired during %s" % self._phase
		self._exit_code = TIMEOUT_EXIT_CODE
		for widget in self._app.topLevelWidgets():
			if isinstance(widget, PySide6.QtWidgets.QDialog):
				widget.reject()
		self._app.exit(TIMEOUT_EXIT_CODE)

	#============================================
	def _run(self) -> None:
		"""Perform native Open, public Arrow commit, Save, close, and reopen."""
		try:
			self._source_path.write_text(_EMPTY_CDML, encoding="utf-8")
			self._control_path.write_text(_EMPTY_CDML, encoding="utf-8")
			self._complete("native-inputs-written")
			theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(self._app)
			self._window = bkchem_qt.main_window.MainWindow(theme_manager)
			self._window.show()
			self._complete("window-created")
			if not self._window.open_file_path(str(self._source_path)):
				raise ScenarioFailure("native CDML Open did not create a session")
			session = self._window.sessions[-1]
			if not self._window.open_file_path(str(self._control_path)):
				raise ScenarioFailure("control native CDML Open did not create a session")
			self._complete("native-sessions-opened")
			outcome = session.commit_arrow((20.0, 30.0), (120.0, 30.0))
			if outcome.status != "accepted" or not session.backend_projection_synchronized:
				raise ScenarioFailure("public Arrow operation was not accepted and projected")
			arrow_id = _arrow_identifier(session.backend_snapshot)
			self._complete("authoritative-arrow-committed")
			session.write_backend_snapshot(str(self._saved_path))
			if session.backend_snapshot.is_dirty:
				raise ScenarioFailure("authoritative Save did not establish the clean baseline")
			self._complete("authoritative-save-completed")
			index = self._window.sessions.index(session)
			if not self._window.close_session_at(index):
				raise ScenarioFailure("public close rejected the clean saved session")
			if not bkchem_qt.main_window.drain_pending_session_deletions(self._app, self._window):
				raise ScenarioFailure("session retirement did not drain")
			if session in self._window.sessions or len(self._window.sessions) != 1:
				raise ScenarioFailure("public tab close did not retire only the saved session")
			self._complete("saved-session-closed")
			if not self._window.open_file_path(str(self._saved_path)):
				raise ScenarioFailure("saved native CDML did not reopen")
			reopened = self._window.sessions[-1]
			if (
				not reopened.backend_projection_synchronized
				or reopened.backend_snapshot.is_dirty
				or _arrow_identifier(reopened.backend_snapshot) != arrow_id
			):
				raise ScenarioFailure("reopened backend snapshot and Qt projection diverged")
			self._complete("saved-session-reopened")
			reopened_index = self._window.sessions.index(reopened)
			if not self._window.close_session_at(reopened_index):
				raise ScenarioFailure("public close rejected the reopened saved session")
			if not bkchem_qt.main_window.drain_pending_session_deletions(self._app, self._window):
				raise ScenarioFailure("reopened session retirement did not drain")
			if len(self._window.sessions) != 1:
				raise ScenarioFailure("reopened tab close did not leave the control session")
			if not self._window.close_session_at(0):
				raise ScenarioFailure("public sole-tab close rejected the clean control session")
			self._complete("sole-session-closed")
			self._scenario_completed = True
		except ScenarioFailure as error:
			self._status = "semantic-failure"
			self._diagnostic = str(error)
		except Exception as error:
			self._status = "python-exception"
			self._diagnostic = "%s: %s" % (type(error).__name__, error)
		finally:
			if self._status != "timeout":
				try:
					self._shutdown()
				except ScenarioFailure as error:
					self._status = "semantic-failure"
					self._diagnostic += "; shutdown failed: %s" % error
				except Exception as error:
					self._status = "python-exception"
					self._diagnostic += "; shutdown exception: %s: %s" % (
						type(error).__name__, error,
					)
				else:
					if self._scenario_completed:
						self._status = "completed"
						self._diagnostic = "authoritative lifecycle completed"
						self._exit_code = 0
				self._timer.stop()
			self._app.exit(self._exit_code)

	#============================================
	def _shutdown(self) -> None:
		"""Use the production close and QObject-retirement boundary once."""
		if self._window is None:
			return
		if not self._window.prepare_application_shutdown():
			raise ScenarioFailure("production application shutdown was not approved")
		self._window.close()
		if not bkchem_qt.main_window.drain_pending_session_deletions(self._app, self._window):
			raise ScenarioFailure("application session retirement did not drain")
		if not bkchem_qt.main_window.delete_qobject_and_wait(self._app, self._window):
			raise ScenarioFailure("MainWindow destruction was not delivered")
		self._complete("application-closed")
		self._window = None

	#============================================
	def receipt(self, origins: dict[str, str]) -> dict[str, object]:
		"""Return one structured terminal record without environment contents."""
		return {
			"completed_phases": self._completed_phases,
			"deadline_seconds": self._deadline_seconds,
			"diagnostic": self._diagnostic,
			"exit_code": self._exit_code,
			"installed_origins": origins,
			"installed_versions": {
				"bkchem-qt": importlib.metadata.version("bkchem-qt"),
				"oasa": importlib.metadata.version("oasa"),
			},
			"last_phase": self._phase,
			"saved_path": str(self._saved_path),
			"schema": RECEIPT_SCHEMA,
			"status": self._status,
		}


#============================================
def _write_receipt(path: pathlib.Path, payload: dict[str, object]) -> None:
	"""Atomically write a terminal receipt to one caller-reserved path."""
	if path.exists():
		raise RuntimeError("receipt destination already exists: %s" % path)
	temporary = path.with_name(".%s.tmp" % path.name)
	if temporary.exists():
		raise RuntimeError("receipt temporary destination already exists: %s" % temporary)
	with temporary.open("x", encoding="utf-8") as output:
		json.dump(payload, output, sort_keys=True)
		output.write("\n")
		output.flush()
		os.fsync(output.fileno())
	os.replace(temporary, path)


#============================================
def main() -> int:
	"""Run the installed Qt lifecycle and return its terminal status."""
	args = _parse_args()
	try:
		saved_path, source_path, control_path = _output_paths(args.output)
		receipt_path = None if args.receipt is None else _repo_tmp_path(args.receipt, "receipt")
		if receipt_path is not None and receipt_path.exists():
			raise ValueError("receipt destination already exists: %s" % receipt_path)
		if receipt_path in (saved_path, source_path, control_path):
			raise ValueError("receipt destination must differ from all scenario CDML paths")
	except ValueError as error:
		print("ERROR: %s" % error, file=sys.stderr)
		return 2
	try:
		origins = {
			"bkchem_qt": _installed_origin(bkchem_qt, "bkchem_qt"),
			"oasa": _installed_origin(oasa, "oasa"),
		}
	except RuntimeError as error:
		print("ERROR: %s" % error, file=sys.stderr)
		return 2
	app = PySide6.QtWidgets.QApplication([])
	run = InstalledRoundtrip(app, args.kill_after, saved_path, source_path, control_path)
	run.start()
	event_exit_code = app.exec()
	if run._status == "timeout":
		run._exit_code = TIMEOUT_EXIT_CODE
	elif event_exit_code != 0 and run._exit_code == 0:
		run._status = "python-exception"
		run._diagnostic = "Qt event loop exited with status %s" % event_exit_code
		run._exit_code = event_exit_code
	payload = run.receipt(origins)
	if receipt_path is not None:
		_write_receipt(receipt_path, payload)
	print(json.dumps(payload, sort_keys=True))
	return run._exit_code


if __name__ == "__main__":
	raise SystemExit(main())
