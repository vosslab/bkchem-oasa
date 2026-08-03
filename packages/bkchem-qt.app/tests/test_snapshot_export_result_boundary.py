"""Focused plain-result boundary checks for authoritative snapshot export."""

# Standard Library
import ast
import pathlib

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.actions.edit_actions
import bkchem_qt.io.export
import bkchem_qt.main_window
import oasa.cdml_document
import oasa.cdml_render


_CDML = """<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
<text id="text1"><point x="1cm" y="1cm"/><ftext>Hello</ftext></text>
</cdml>"""


#============================================
class _CapturedSession:
	"""Provide one opaque backend capture to the explicit export adapter."""

	#============================================
	def __init__(self, capture: object) -> None:
		"""Store the response the session capture boundary will provide."""
		self._capture = capture

	#============================================
	def capture_visual_render_request(self, format_name: str, scope: str = "page") -> object:
		"""Return the configured opaque capture without exposing its type to callers."""
		return self._capture


#============================================
def _request() -> object:
	"""Build one real immutable backend snapshot request for adapter tests."""
	snapshot = oasa.cdml_document.CDMLSnapshot(41, _CDML, False)
	return oasa.cdml_render.CDMLRenderRequest(snapshot, "svg")


#============================================
def _oasa_imports(module: object) -> tuple[str, ...]:
	"""Return direct OASA imports under either Python import syntax."""
	source_path = pathlib.Path(module.__file__)
	tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
	imports = []
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			imports.extend(
				alias.name for alias in node.names
				if alias.name == "oasa" or alias.name.startswith("oasa.")
			)
		elif isinstance(node, ast.ImportFrom) and node.module is not None:
			if node.module == "oasa" or node.module.startswith("oasa."):
				imports.append(node.module)
	return tuple(imports)


#============================================
def test_edit_action_and_main_window_keep_oasa_inside_named_adapters() -> None:
	"""Ordinary UI modules consume only the export/session adapter outcome."""
	violations = _oasa_imports(bkchem_qt.actions.edit_actions)
	violations += _oasa_imports(bkchem_qt.main_window)

	assert not violations


#============================================
def test_capture_failure_becomes_one_plain_frontend_outcome() -> None:
	"""A typed capture failure crosses the adapter as status, code, and message."""
	capture = oasa.cdml_render.CDMLRenderFailure(
		"selection-unavailable", "Selection requires a current projection", 41,
	)
	outcome = bkchem_qt.io.export.render_session_snapshot(
		_CapturedSession(capture), "svg", "selection",
	)

	assert outcome.error_code == "selection-unavailable" and not outcome.succeeded


#============================================
def test_render_failure_and_empty_artifact_withhold_publication(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Render faults and empty bytes remain typed failures before Qt publication."""
	capture = _request()
	monkeypatch.setattr(
		bkchem_qt.io.export.bkchem_qt.io.snapshot_render, "render_request",
		lambda _capture: oasa.cdml_render.CDMLRenderFailure(
			"render-failed", "Injected render failure", 41,
		),
	)
	failure = bkchem_qt.io.export.render_snapshot_capture(capture, "svg")
	monkeypatch.setattr(
		bkchem_qt.io.export.bkchem_qt.io.snapshot_render, "render_request",
		lambda _capture: oasa.cdml_render.CDMLRenderResult(41, "svg", b""),
	)
	empty = bkchem_qt.io.export.render_snapshot_capture(capture, "svg")

	assert failure.error_code == "render-failed" and empty.error_code == "empty-artifact"


#============================================
def test_copy_as_svg_publishes_only_a_successful_nonempty_artifact(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Clipboard content remains intact until the explicit adapter returns SVG bytes."""
	clipboard = PySide6.QtWidgets.QApplication.clipboard()
	clipboard.setText("clipboard-before-export")
	failed = bkchem_qt.io.export.SnapshotExportOutcome(
		"failure", "render-failed", "Injected render failure", 41, "svg",
	)
	monkeypatch.setattr(
		bkchem_qt.io.export, "render_session_snapshot", lambda *_args: failed,
	)
	bkchem_qt.actions.edit_actions._selected_to_svg(main_window)
	before_success = clipboard.text()
	success = bkchem_qt.io.export.SnapshotExportOutcome(
		"success", None, "Snapshot rendered", 41, "svg", b"<svg/>"
	)
	monkeypatch.setattr(
		bkchem_qt.io.export, "render_session_snapshot", lambda *_args: success,
	)
	bkchem_qt.actions.edit_actions._selected_to_svg(main_window)

	assert before_success == "clipboard-before-export" and bytes(clipboard.mimeData().data("image/svg+xml"))


#============================================
def test_path_write_failure_preserves_the_authoritative_snapshot(
		tmp_path: pathlib.Path,
		) -> None:
	"""Artifact path failure is typed and cannot mutate a captured backend snapshot."""
	capture = _request()
	before_snapshot = capture.snapshot
	outcome = bkchem_qt.io.export.write_snapshot_artifact(capture, "svg", str(tmp_path))

	assert outcome.error_code == "artifact-write-failed" and capture.snapshot == before_snapshot


#============================================
def _raise_replace_failure(_staged_path: str, _file_path: str) -> None:
	"""Raise one deterministic final-publication failure for the adapter test."""
	raise OSError("replace failed")


#============================================
def test_failed_publication_preserves_an_existing_destination(
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed final replacement leaves a previous export readable and unchanged."""
	capture = _request()
	destination = tmp_path / "structure.svg"
	destination.write_bytes(b"previous-export")
	monkeypatch.setattr(
		bkchem_qt.io.export.os, "replace",
		_raise_replace_failure,
	)
	outcome = bkchem_qt.io.export.write_snapshot_artifact(capture, "svg", str(destination))

	assert outcome.error_code == "artifact-write-failed" and destination.read_bytes() == b"previous-export"
