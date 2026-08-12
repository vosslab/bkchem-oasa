#!/usr/bin/env python3
"""Capture the managed BKChem-Qt documentation screenshot catalog."""

# Standard Library
import argparse
import collections.abc
import dataclasses
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.themes.theme_manager
import bkchem_qt.versioning
import oasa.cdml_document
import oasa.cdml_writer
import oasa.haworth.verified_sucrose
import oasa.insertion_geometry


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TMP_ROOT = REPO_ROOT / "tmp" / "documentation_screenshots"
SCREENSHOT_ROOT = REPO_ROOT / "docs" / "screenshots"
TIMEOUT_EXIT_CODE = 124
WINDOW_SIZE = PySide6.QtCore.QSize(1280, 800)


@dataclasses.dataclass(frozen=True)
class CaptureScenario:
	"""One reproducible native-CDML view in the documentation catalog."""

	key: str
	output_name: str
	required_presentation_kinds: frozenset[str]
	required_markers: tuple[str, ...]
	molecule_count: int


_SCENARIOS = (
	CaptureScenario(
		"document", "bkchem_qt_cdml_projection.png",
		frozenset(("arrow", "plus", "text")),
		("benzene", "reaction_arrow", "product"), 2,
	),
	CaptureScenario(
		"drawing-objects", "bkchem_qt_drawing_objects.png",
		frozenset(("arrow", "oval", "plus", "polygon", "polyline", "rect", "text")),
		("persistent_objects_title", "left_bracket", "right_bracket", "vector_shape"), 0,
	),
	CaptureScenario(
		"haworth", "bkchem_qt_verified_sucrose_haworth.png",
		frozenset(("text",)),
		("verified_sucrose_title", "Verified sucrose Haworth"), 1,
	),
)
_SCENARIOS_BY_KEY = {scenario.key: scenario for scenario in _SCENARIOS}


_DOCUMENT_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <molecule id="benzene">
  <atom id="benzene_a1" name="C"><point x="62.0cm" y="43.0cm"/></atom>
  <atom id="benzene_a2" name="C"><point x="63.0cm" y="42.3cm"/></atom>
  <atom id="benzene_a3" name="C"><point x="64.0cm" y="43.0cm"/></atom>
  <atom id="benzene_a4" name="C"><point x="64.0cm" y="44.4cm"/></atom>
  <atom id="benzene_a5" name="C"><point x="63.0cm" y="45.1cm"/></atom>
  <atom id="benzene_a6" name="C"><point x="62.0cm" y="44.4cm"/></atom>
  <bond id="benzene_b1" start="benzene_a1" end="benzene_a2" type="n2"/>
  <bond id="benzene_b2" start="benzene_a2" end="benzene_a3" type="n1"/>
  <bond id="benzene_b3" start="benzene_a3" end="benzene_a4" type="n2"/>
  <bond id="benzene_b4" start="benzene_a4" end="benzene_a5" type="n1"/>
  <bond id="benzene_b5" start="benzene_a5" end="benzene_a6" type="n2"/>
  <bond id="benzene_b6" start="benzene_a6" end="benzene_a1" type="n1"/>
 </molecule>
 <text id="conditions">
  <point x="66.3cm" y="42.2cm"/>
  <font family="Arial" size="10" color="#173b6c"/>
  <ftext>Heat, catalyst</ftext>
 </text>
 <arrow id="reaction_arrow" type="normal" width="1.5" color="#173b6c">
  <point x="65.5cm" y="43.7cm"/><point x="68.9cm" y="43.7cm"/>
 </arrow>
 <plus id="reaction_plus" font_size="16" color="#173b6c">
  <point x="69.8cm" y="43.7cm"/><font family="Arial"/>
 </plus>
 <molecule id="product">
  <atom id="product_c1" name="C"><point x="70.6cm" y="43.7cm"/></atom>
  <atom id="product_c2" name="C"><point x="71.8cm" y="43.7cm"/></atom>
  <atom id="product_o" name="O"><point x="73.0cm" y="43.7cm"/></atom>
  <bond id="product_b1" start="product_c1" end="product_c2" type="n1"/>
  <bond id="product_b2" start="product_c2" end="product_o" type="n1"/>
 </molecule>
</cdml>
"""


_DRAWING_OBJECTS_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <text id="persistent_objects_title">
  <point x="62.0cm" y="40.8cm"/>
  <font family="Arial" size="15" color="#173b6c"/>
  <ftext>Persistent CDML drawing objects</ftext>
 </text>
 <text id="arrow_label"><point x="62.0cm" y="42.4cm"/>
  <font family="Arial" size="9" color="#3e4a5b"/><ftext>Arrows and labels</ftext></text>
 <arrow id="double_headed_arrow" type="normal" start="yes" end="yes"
   width="2" color="#2f5d8c">
  <point x="62.0cm" y="44.1cm"/><point x="67.0cm" y="44.1cm"/>
 </arrow>
 <plus id="drawing_plus" font_size="20" color="#8b3a3a">
  <point x="68.4cm" y="44.1cm"/><font family="Arial"/>
 </plus>
 <rect id="filled_rect" x1="70.0cm" y1="42.7cm" x2="73.2cm" y2="45.4cm"
   width="2" line_color="#2f5d8c" area_color="#dceafb"/>
 <oval id="filled_oval" x1="74.1cm" y1="42.7cm" x2="77.3cm" y2="45.4cm"
   width="2" line_color="#7a3f76" area_color="#f1def0"/>
 <polygon id="filled_polygon" width="2" line_color="#39704a" area_color="#dceede">
  <point x="62.0cm" y="48.3cm"/><point x="64.0cm" y="46.4cm"/>
  <point x="66.0cm" y="48.3cm"/><point x="65.2cm" y="50.5cm"/>
  <point x="62.8cm" y="50.5cm"/>
 </polygon>
 <polyline id="left_bracket" bracket_pair="left_bracket" bracket_side="left"
   spline="no" width="2" line_color="#173b6c">
  <point x="68.0cm" y="46.4cm"/><point x="67.3cm" y="46.4cm"/>
  <point x="67.3cm" y="50.5cm"/><point x="68.0cm" y="50.5cm"/>
 </polyline>
 <polyline id="right_bracket" bracket_pair="left_bracket" bracket_side="right"
   spline="no" width="2" line_color="#173b6c">
  <point x="73.0cm" y="46.4cm"/><point x="73.7cm" y="46.4cm"/>
  <point x="73.7cm" y="50.5cm"/><point x="73.0cm" y="50.5cm"/>
 </polyline>
 <text id="bracket_text"><point x="68.4cm" y="47.7cm"/>
  <font family="Arial" size="14" color="#173b6c"/><ftext>CH2-CH2</ftext></text>
 <text id="vector_label"><point x="74.7cm" y="47.2cm"/>
  <font family="Arial" size="10" color="#3e4a5b"/><ftext>Vectors</ftext></text>
 <polyline id="vector_shape" spline="no" width="2" line_color="#b24b32">
	<point x="74.8cm" y="48.2cm"/><point x="76.8cm" y="49.7cm"/>
	<point x="76.1cm" y="49.5cm"/><point x="76.8cm" y="49.7cm"/>
	<point x="76.5cm" y="49.0cm"/>
 </polyline>
</cdml>
"""


#============================================
class CaptureFailure(RuntimeError):
	"""Describe a finished capture that did not meet its proof contract."""


#============================================
def _parse_args() -> argparse.Namespace:
	"""Parse a catalog scenario, optional output, and bounded Qt lifetime."""
	parser = argparse.ArgumentParser(description=__doc__)
	choices = ("all",) + tuple(scenario.key for scenario in _SCENARIOS)
	parser.add_argument(
		"--scenario", choices=choices, default="all",
		help="capture one named view or the complete managed catalog (default: all)",
	)
	parser.add_argument(
		"-o", "--output", dest="output_path", metavar="PNG",
		help="PNG destination inside this repository; valid with one scenario",
	)
	parser.add_argument(
		"-k", "--kill-after", dest="kill_after", type=float, default=3.0,
		metavar="SECONDS", help="per-scenario application deadline (default: 3)",
	)
	parser.add_argument("-r", "--receipt", dest="receipt_path", metavar="JSON")
	args = parser.parse_args()
	if not math.isfinite(args.kill_after) or args.kill_after <= 0.0:
		parser.error("--kill-after requires a finite positive number of seconds")
	if args.scenario == "all" and args.output_path is not None:
		parser.error("--output requires one named --scenario")
	return args


#============================================
def _path_inside_repo(value: str, label: str, suffix: str) -> pathlib.Path:
	"""Resolve one caller path that remains inside this checkout."""
	path = pathlib.Path(value).expanduser()
	if not path.is_absolute():
		path = REPO_ROOT / path
	path = path.resolve()
	try:
		path.relative_to(REPO_ROOT)
	except ValueError as error:
		raise ValueError("%s must be inside the repository: %s" % (label, path)) from error
	if path.suffix.lower() != suffix:
		raise ValueError("%s must have a %s suffix" % (label, suffix))
	return path


#============================================
def _receipt_path(value: str | None) -> pathlib.Path | None:
	"""Accept an optional JSON receipt below the repository's retained tmp tree."""
	if value is None:
		return None
	path = _path_inside_repo(value, "receipt", ".json")
	try:
		path.relative_to(REPO_ROOT / "tmp")
	except ValueError as error:
		raise ValueError("receipt must be inside %s" % (REPO_ROOT / "tmp")) from error
	return path


#============================================
def _scenario_output(scenario: CaptureScenario, value: str | None) -> pathlib.Path:
	"""Return the managed or caller-selected PNG for one scenario."""
	if value is None:
		return SCREENSHOT_ROOT / scenario.output_name
	return _path_inside_repo(value, "output", ".png")


#============================================
def _haworth_cdml() -> str:
	"""Build one authoritative complete document from OASA's verified preset."""
	base_cdml = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
 <text id="verified_sucrose_title"><point x="65.0cm" y="45.6cm"/>
  <font family="Arial" size="15" color="#173b6c"/>
  <ftext>Verified sucrose Haworth</ftext>
 </text>
</cdml>
"""
	molecule = oasa.haworth.verified_sucrose.prepare_verified_sucrose_haworth()
	oasa.insertion_geometry.place_molecules_for_insertion(
		[molecule], 40.0, (2000.0, 1500.0),
	)
	proposal = oasa.cdml_writer.molecules_to_insertion_proposal(
		[molecule], token_stem="docs-verified-sucrose",
	)
	backend = oasa.cdml_document.CDMLDocumentSession.load(base_cdml)
	accepted = backend.insert_molecules(oasa.cdml_document.CDMLMoleculeInsertionRequest(
		expected_revision=backend.revision,
		proposal_cdml=proposal,
		label="Generate verified sucrose documentation view",
	))
	return accepted.cdml


#============================================
def _scenario_cdml(scenario: CaptureScenario) -> str:
	"""Return the complete native CDML value for one managed view."""
	if scenario.key == "document":
		return _DOCUMENT_CDML
	if scenario.key == "drawing-objects":
		return _DRAWING_OBJECTS_CDML
	if scenario.key == "haworth":
		return _haworth_cdml()
	raise ValueError("Unknown capture scenario: %s" % scenario.key)


#============================================
def _configure_isolated_settings() -> None:
	"""Keep deterministic screenshot preferences below the repository tmp tree."""
	settings_path = TMP_ROOT / "settings"
	settings_path.mkdir(parents=True, exist_ok=True)
	settings_format = PySide6.QtCore.QSettings.Format.IniFormat
	PySide6.QtCore.QSettings.setDefaultFormat(settings_format)
	PySide6.QtCore.QSettings.setPath(
		settings_format,
		PySide6.QtCore.QSettings.Scope.UserScope,
		str(settings_path),
	)


#============================================
class QtCdmlCapture:
	"""Open, verify, frame, and capture one backend-authoritative Qt projection."""

	#============================================
	def __init__(
			self, app: PySide6.QtWidgets.QApplication,
			window: bkchem_qt.main_window.MainWindow,
			scenario: CaptureScenario, output_path: pathlib.Path,
			deadline_seconds: float,
			) -> None:
		"""Retain one controlled application workflow and terminal receipt."""
		self._app = app
		self._window = window
		self._scenario = scenario
		self._output_path = output_path
		self._deadline_seconds = deadline_seconds
		self._input_path = TMP_ROOT / (scenario.key + ".cdml")
		self._staged_path = TMP_ROOT / (
			"capture.%s.%s.pending.png" % (os.getpid(), scenario.key)
		)
		self._phase = "initialized"
		self._status = "python-exception"
		self._diagnostic = "capture did not run"
		self._exit_code = 1
		self._timer = PySide6.QtCore.QTimer(app)
		self._timer.setSingleShot(True)
		self._timer.timeout.connect(self._expire)

	#============================================
	@property
	def exit_code(self) -> int:
		"""Return the terminal process status."""
		return self._exit_code

	#============================================
	def start(self) -> None:
		"""Start one deadline before scheduling native CDML Open."""
		self._timer.start(round(self._deadline_seconds * 1000))
		PySide6.QtCore.QTimer.singleShot(0, self._open_document)

	#============================================
	def _open_document(self) -> None:
		"""Use the public MainWindow path for one generated complete document."""
		try:
			self._phase = "writing-native-cdml"
			TMP_ROOT.mkdir(parents=True, exist_ok=True)
			self._input_path.write_text(
				_scenario_cdml(self._scenario), encoding="utf-8",
			)
			self._phase = "opening-native-cdml"
			if not self._window.open_file_path(str(self._input_path)):
				raise CaptureFailure("MainWindow rejected the managed CDML document")
			self._verify_projection()
			self._phase = "settling-projection"
			if self._window.sessions[-1].scene.grid_visible:
				self._window.on_toggle_grid()
			self._window.view.set_background_color("#ffffff")
			self._window.on_zoom_to_content()
			PySide6.QtCore.QTimer.singleShot(0, self._capture_window)
		except Exception as error:
			self._fail(error)

	#============================================
	def _verify_projection(self) -> None:
		"""Verify the authoritative snapshot before capturing its disposable scene."""
		session = self._window.sessions[-1]
		if not session.backend_projection_synchronized:
			raise CaptureFailure("native Open did not install a synchronized projection")
		backend = oasa.cdml_document.CDMLDocumentSession.load(session.backend_snapshot.cdml)
		kinds = {
			record.kind
			for record in backend.projection_snapshot().plan.presentation_description.records
		}
		if not self._scenario.required_presentation_kinds.issubset(kinds):
			raise CaptureFailure(
				"backend snapshot lacks required presentation kinds: %s"
				% sorted(self._scenario.required_presentation_kinds - kinds)
			)
		for marker in self._scenario.required_markers:
			if marker not in session.backend_snapshot.cdml:
				raise CaptureFailure("backend snapshot lacks marker: %s" % marker)
		if len(session.document.molecules) != self._scenario.molecule_count:
			raise CaptureFailure(
				"projected molecule count differs from the managed scenario"
			)

	#============================================
	def _capture_window(self) -> None:
		"""Atomically replace the managed PNG after the projection has painted."""
		try:
			self._phase = "grabbing-widget"
			# MainWindow performs its normal post-Open page framing through the Qt
			# event queue.  Apply the documentation framing after those lifecycle
			# callbacks so the capture proves readable content rather than a tiny
			# page overview.  This calls the same public Content action users have.
			self._window.on_zoom_to_content()
			pixmap = self._window.grab()
			if pixmap.isNull():
				raise CaptureFailure("QWidget.grab returned an empty screenshot")
			pixel_size = pixmap.size() * pixmap.devicePixelRatio()
			if pixel_size != WINDOW_SIZE:
				raise CaptureFailure(
					"managed screenshot must be 1280x800; got %sx%s"
					% (pixel_size.width(), pixel_size.height())
				)
			self._staged_path.parent.mkdir(parents=True, exist_ok=True)
			if not pixmap.save(str(self._staged_path), "PNG"):
				raise CaptureFailure("Qt could not encode the managed PNG")
			if self._staged_path.stat().st_size > 1024 * 1024:
				raise CaptureFailure("managed PNG exceeds the 1 MiB documentation target")
			self._output_path.parent.mkdir(parents=True, exist_ok=True)
			os.replace(self._staged_path, self._output_path)
			self._phase = "captured"
			self._status = "completed"
			self._diagnostic = (
				"captured %sx%s to %s"
				% (pixel_size.width(), pixel_size.height(),
					self._output_path.relative_to(REPO_ROOT))
			)
			self._exit_code = 0
			self._timer.stop()
			self._app.quit()
		except Exception as error:
			self._fail(error)

	#============================================
	def _fail(self, error: Exception) -> None:
		"""Record one semantic or Python failure and leave the event loop."""
		if self._exit_code == TIMEOUT_EXIT_CODE:
			return
		self._status = "capture-failed"
		self._diagnostic = "%s: %s" % (type(error).__name__, error)
		self._exit_code = 1
		self._timer.stop()
		self._app.exit(1)

	#============================================
	def _expire(self) -> None:
		"""Reject nested dialogs and leave the application at the deadline."""
		self._status = "timeout"
		self._diagnostic = "deadline expired during %s" % self._phase
		self._exit_code = TIMEOUT_EXIT_CODE
		for widget in self._app.topLevelWidgets():
			if isinstance(widget, PySide6.QtWidgets.QDialog):
				widget.reject()
		self._app.exit(TIMEOUT_EXIT_CODE)

	#============================================
	def receipt(self) -> dict[str, object]:
		"""Return the stable terminal result without retaining Qt objects."""
		return {
			"deadline_seconds": self._deadline_seconds,
			"diagnostic": self._diagnostic,
			"exit_code": self._exit_code,
			"output_path": str(self._output_path),
			"phase": self._phase,
			"scenario": self._scenario.key,
			"schema": "bkchem-qt-documentation-screenshot-1",
			"status": self._status,
		}


#============================================
def _retire_window(
		app: PySide6.QtWidgets.QApplication,
		window: bkchem_qt.main_window.MainWindow,
		) -> bool:
	"""Retire one captured window through the production Qt lifetime boundary."""
	if not window.prepare_application_shutdown():
		return False
	if not bkchem_qt.main_window.drain_pending_session_deletions(app, window):
		return False
	return bkchem_qt.main_window.delete_qobject_and_wait(app, window)


#============================================
def _write_receipt(path: pathlib.Path, payload: dict[str, object]) -> None:
	"""Atomically write one compact receipt below the repository tmp tree."""
	path.parent.mkdir(parents=True, exist_ok=True)
	staged_path = path.with_name("%s.%s.pending" % (path.name, os.getpid()))
	staged_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
	os.replace(staged_path, path)


#============================================
def _validate_catalog_artifact(path: pathlib.Path) -> None:
	"""Confirm a staged catalog artifact is a managed-size PNG before publication."""
	if not path.is_file():
		raise CaptureFailure(f"catalog staging did not produce {path.name}")
	if path.stat().st_size > 1024 * 1024:
		raise CaptureFailure(f"catalog artifact exceeds the 1 MiB target: {path.name}")
	reader = PySide6.QtGui.QImageReader(str(path))
	if bytes(reader.format()).lower() != b"png":
		raise CaptureFailure(f"catalog artifact is not PNG data: {path.name}")
	image = reader.read()
	if image.isNull() or image.size() != WINDOW_SIZE:
		raise CaptureFailure(f"catalog artifact is not a {WINDOW_SIZE.width()}x{WINDOW_SIZE.height()} PNG: {path.name}")


#============================================
def _publish_catalog(
		staging_root: pathlib.Path, screenshot_root: pathlib.Path,
		scenarios: tuple[CaptureScenario, ...] = _SCENARIOS,
		replace_path: collections.abc.Callable[[pathlib.Path, pathlib.Path], None] = os.replace,
		) -> None:
	"""Publish a complete validated catalog and restore the prior gallery on failure.

	A filesystem cannot replace several independent PNG paths in one operation. This
	publisher therefore validates every staged image before touching the gallery, keeps
	private copies of the prior files, and restores those copies if a later replacement
	fails. A successful run is coherent; a failed run leaves the previously published
	catalog intact.
	"""
	staged_paths = [staging_root / scenario.output_name for scenario in scenarios]
	for staged_path in staged_paths:
		_validate_catalog_artifact(staged_path)
	backup_root = staging_root / "prior-gallery"
	backup_root.mkdir(parents=True, exist_ok=True)
	previous_paths: dict[pathlib.Path, pathlib.Path | None] = {}
	for scenario in scenarios:
		final_path = screenshot_root / scenario.output_name
		if final_path.exists():
			backup_path = backup_root / scenario.output_name
			shutil.copy2(final_path, backup_path)
			previous_paths[final_path] = backup_path
		else:
			previous_paths[final_path] = None
	try:
		for scenario in scenarios:
			final_path = screenshot_root / scenario.output_name
			final_path.parent.mkdir(parents=True, exist_ok=True)
			replace_path(staging_root / scenario.output_name, final_path)
	except OSError:
		for final_path, backup_path in previous_paths.items():
			if backup_path is None:
				if final_path.exists():
					final_path.unlink()
			else:
				os.replace(backup_path, final_path)
		raise


#============================================
def _capture_one(
		scenario: CaptureScenario, output_path: pathlib.Path,
		deadline_seconds: float,
		) -> tuple[int, dict[str, object]]:
	"""Run one fresh QApplication and return its terminal receipt."""
	_configure_isolated_settings()
	app = PySide6.QtWidgets.QApplication(sys.argv[:1])
	app.setApplicationName("BKChem-Qt documentation capture")
	app.setOrganizationName("BKChem")
	app.setApplicationVersion(bkchem_qt.versioning.application_version())
	app.setQuitOnLastWindowClosed(False)
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_manager.apply_theme("light")
	window = bkchem_qt.main_window.MainWindow(theme_manager)
	window.resize(WINDOW_SIZE)
	window.show()
	run = QtCdmlCapture(app, window, scenario, output_path, deadline_seconds)
	run.start()
	app.exec()
	retired = _retire_window(app, window)
	if not retired and run.exit_code == 0:
		payload = run.receipt()
		payload.update({
			"diagnostic": "screenshot completed but the Qt window did not retire",
			"exit_code": 1,
			"status": "retirement-failed",
		})
		return 1, payload
	return run.exit_code, run.receipt()


#============================================
def _capture_catalog(
		deadline_seconds: float, receipt_path: pathlib.Path | None,
		) -> int:
	"""Capture a complete catalog privately, then publish one coherent generation."""
	results = []
	TMP_ROOT.mkdir(parents=True, exist_ok=True)
	staging_root = pathlib.Path(tempfile.mkdtemp(prefix="catalog-", dir=TMP_ROOT))
	for scenario in _SCENARIOS:
		command = (
			sys.executable, str(pathlib.Path(__file__).resolve()),
			"--scenario", scenario.key,
			"--output", str(staging_root / scenario.output_name),
			"--kill-after", str(deadline_seconds),
		)
		try:
			completed = subprocess.run(
				command, check=False, capture_output=True, text=True,
				timeout=deadline_seconds + 2.0,
			)
		except subprocess.TimeoutExpired:
			payload = {
				"diagnostic": "capture process exceeded its bounded parent timeout",
				"exit_code": TIMEOUT_EXIT_CODE,
				"scenario": scenario.key,
				"status": "process-timeout",
			}
			results.append(payload)
			break
		if completed.stderr:
			print(completed.stderr, file=sys.stderr, end="")
		try:
			payload = json.loads(completed.stdout.strip().splitlines()[-1])
		except (IndexError, json.JSONDecodeError):
			payload = {
				"diagnostic": "capture process returned no readable receipt",
				"exit_code": completed.returncode,
				"scenario": scenario.key,
				"status": "invalid-receipt",
			}
		results.append(payload)
		if completed.returncode != 0:
			break
	completed = len(results) == len(_SCENARIOS) and all(
		result.get("exit_code") == 0 for result in results
	)
	publication_diagnostic = "catalog scenarios did not all complete"
	if completed:
		try:
			_publish_catalog(staging_root, SCREENSHOT_ROOT)
			publication_diagnostic = "validated catalog generation published"
		except (CaptureFailure, OSError) as error:
			completed = False
			publication_diagnostic = f"catalog publication kept the prior gallery: {error}"
	payload = {
		"diagnostic": publication_diagnostic,
		"results": results,
		"schema": "bkchem-qt-documentation-screenshot-catalog-1",
		"status": "completed" if completed else "failed",
	}
	if receipt_path is not None:
		_write_receipt(receipt_path, payload)
	print(json.dumps(payload, sort_keys=True))
	return 0 if payload["status"] == "completed" else 1


#============================================
def main() -> int:
	"""Capture one managed view or the complete isolated screenshot catalog."""
	args = _parse_args()
	try:
		receipt_path = _receipt_path(args.receipt_path)
		if args.scenario == "all":
			return _capture_catalog(args.kill_after, receipt_path)
		scenario = _SCENARIOS_BY_KEY[args.scenario]
		output_path = _scenario_output(scenario, args.output_path)
	except ValueError as error:
		print("ERROR: %s" % error, file=sys.stderr)
		return 2
	exit_code, payload = _capture_one(scenario, output_path, args.kill_after)
	if receipt_path is not None:
		_write_receipt(receipt_path, payload)
	stream = sys.stdout if exit_code == 0 else sys.stderr
	print(json.dumps(payload, sort_keys=True), file=stream)
	return exit_code


if __name__ == "__main__":
	raise SystemExit(main())
