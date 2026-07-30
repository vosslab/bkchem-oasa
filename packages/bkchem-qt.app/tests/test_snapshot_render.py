"""Focused backend-snapshot visual export coverage."""

# PIP3 modules
import PySide6.QtWidgets
import pytest
import shiboken6

# local repo modules
import oasa.cdml_document
import oasa.cdml_render
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.io.snapshot_render


_CDML = """<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
<paper type="a4" crop_svg="1" crop_margin="7"/>
<molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="1cm"/></atom></molecule>
<molecule id="m2"><atom id="a2" name="O"><point x="4cm" y="1cm"/></atom></molecule>
<vendor:opaque xmlns:vendor="urn:vendor" id="opaque-1"/>
</cdml>"""


#============================================
@pytest.mark.parametrize("format_name, prefix", [
	("svg", b"<?xml"), ("png", b"\x89PNG"), ("pdf", b"%PDF"),
])
def test_snapshot_render_returns_each_requested_artifact(
		qapp: PySide6.QtWidgets.QApplication, format_name: str, prefix: bytes,
		) -> None:
	"""Each format is rendered from a complete immutable backend snapshot."""
	request = oasa.cdml_render.CDMLRenderRequest(
		oasa.cdml_document.CDMLSnapshot(11, _CDML, True), format_name,
	)
	result = bkchem_qt.io.snapshot_render.render_request(request)
	assert isinstance(result, oasa.cdml_render.CDMLRenderResult)
	assert result.artifact is not None and result.artifact.startswith(prefix)
	assert any(warning.code == "unsupported-persistent-object" for warning in result.warnings)
	bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()


#============================================
def test_selection_render_resolves_durable_molecule_identity(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Selection output is reconstructed from a durable request key, not a scene item."""
	request = oasa.cdml_render.CDMLRenderRequest(
		oasa.cdml_document.CDMLSnapshot(12, _CDML, False), "svg", "selection",
		(oasa.cdml_render.CDMLRenderSelectionKey("molecule", "m1"),),
	)
	result = bkchem_qt.io.snapshot_render.render_request(request)
	assert isinstance(result, oasa.cdml_render.CDMLRenderResult)
	assert result.artifact is not None and b"<svg" in result.artifact
	bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()


#============================================
def test_snapshot_render_retires_actual_installed_scene_roots(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Snapshot cleanup gives the terminal reaper the installed graphics tree."""
	request = oasa.cdml_render.CDMLRenderRequest(
		oasa.cdml_document.CDMLSnapshot(121, _CDML, False), "svg",
	)
	reaper = bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper
	retire = reaper.retire
	captured_items = []

	#============================================
	def record_installed_roots(
			scene: object, scene_items: list[object], detached_items: list[object],
			) -> object:
		"""Record scene-owned roots before the production terminal transition."""
		if scene_items:
			captured_items.extend(scene_items)
		return retire(scene, scene_items, detached_items)

	monkeypatch.setattr(reaper, "retire", record_installed_roots)
	result = bkchem_qt.io.snapshot_render.render_request(request)

	assert (
		isinstance(result, oasa.cdml_render.CDMLRenderResult)
		and captured_items
		and not any(shiboken6.isValid(item) for item in captured_items)
	)


#============================================
def test_cropped_svg_uses_snapshot_paper_metadata(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Snapshot crop metadata selects content bounds instead of the A4 page."""
	request = oasa.cdml_render.CDMLRenderRequest(
		oasa.cdml_document.CDMLSnapshot(13, _CDML, False), "svg",
	)
	result = bkchem_qt.io.snapshot_render.render_request(request)
	assert isinstance(result, oasa.cdml_render.CDMLRenderResult)
	assert result.artifact is not None and b'width="' in result.artifact
	assert b'width="595' not in result.artifact
	bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()


#============================================
def test_snapshot_render_uses_the_backend_paper_catalog_beyond_legacy_a_sizes(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A broad CDML catalog type supplies the page dimensions for snapshot rendering."""
	page = bkchem_qt.io.snapshot_render._paper_rect({"type": "C10"})

	assert page.width() == pytest.approx(28.0 * 72.0 / 25.4)


#============================================
def test_snapshot_projection_failure_has_typed_nonmutating_outcome(
		qapp: PySide6.QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A decode failure reports its snapshot revision without a live-scene fallback."""
	request = oasa.cdml_render.CDMLRenderRequest(
		oasa.cdml_document.CDMLSnapshot(14, _CDML, True), "svg",
	)
	def fail_projection(_cdml: str) -> object:
		"""Inject a detached snapshot decoder failure."""
		raise RuntimeError("injected snapshot projection failure")
	monkeypatch.setattr(
		bkchem_qt.io.snapshot_render.bkchem_qt.io.cdml_document_io,
		"prepare_projection_from_cdml", fail_projection,
	)
	result = bkchem_qt.io.snapshot_render.render_request(request)
	assert (
		isinstance(result, oasa.cdml_render.CDMLRenderFailure)
		and result.code == "render-failed"
		and result.snapshot_revision == 14
	)


#============================================
def test_snapshot_render_cleanup_failure_withholds_success_artifact(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A terminal reaper diagnostic rejects an otherwise complete SVG render."""
	session = main_window._active_session
	request = session.capture_visual_render_request("svg")
	if not isinstance(request, oasa.cdml_render.CDMLRenderRequest):
		raise TypeError("Live session did not capture a visual render request")
	backend = session._backend_session
	before_state = (
		session.backend_snapshot, backend._revision, backend._saved_revision,
		backend._saved_cdml, tuple(backend._history), session._backend_history,
		tuple(session.scene.selectedItems()), session.document, session.scene,
		session._projected_backend_snapshot,
	)
	reaper = bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper
	retire = reaper.retire
	def retire_with_diagnostic(
			scene: object, scene_items: list[object], detached_items: list[object],
			) -> object:
		"""Retain the ordinary terminal record and expose its reaper diagnostic."""
		record = retire(scene, scene_items, detached_items)
		record.diagnostics.append(RuntimeError("injected temporary reaper failure"))
		return record
	monkeypatch.setattr(reaper, "retire", retire_with_diagnostic)
	result = bkchem_qt.io.snapshot_render.render_request(request)
	assert (
		isinstance(result, oasa.cdml_render.CDMLRenderFailure)
		and result.code == "render-cleanup-failed"
		and result.diagnostics == (
			"Snapshot projection cleanup failed: "
			"RuntimeError: injected temporary reaper failure",
		)
	)
	after_state = (
		session.backend_snapshot, backend._revision, backend._saved_revision,
		backend._saved_cdml, tuple(backend._history), session._backend_history,
		tuple(session.scene.selectedItems()), session.document, session.scene,
		session._projected_backend_snapshot,
	)
	assert after_state == before_state
	bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()


#============================================
def test_snapshot_render_keeps_primary_failure_when_cleanup_also_fails(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Render failure remains primary while disposal retains its diagnostic."""
	session = main_window._active_session
	request = session.capture_visual_render_request("svg")
	if not isinstance(request, oasa.cdml_render.CDMLRenderRequest):
		raise TypeError("Live session did not capture a visual render request")
	backend = session._backend_session
	before_state = (
		session.backend_snapshot, backend._revision, backend._saved_revision,
		backend._saved_cdml, tuple(backend._history), session._backend_history,
		tuple(session.scene.selectedItems()), session.document, session.scene,
		session._projected_backend_snapshot,
	)
	reaper = bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper
	retire = reaper.retire
	def fail_render(
			scene: object, plan: object, format_name: str,
			) -> bytes:
		"""Inject one explicit render-stage failure after projection succeeds."""
		raise RuntimeError("injected snapshot render failure")
	def retire_with_diagnostic(
			scene: object, scene_items: list[object], detached_items: list[object],
			) -> object:
		"""Expose an independent temporary-projection retirement diagnostic."""
		record = retire(scene, scene_items, detached_items)
		record.diagnostics.append(RuntimeError("injected temporary reaper failure"))
		return record
	monkeypatch.setattr(bkchem_qt.io.snapshot_render, "_render_bytes", fail_render)
	monkeypatch.setattr(
		reaper,
		"retire", retire_with_diagnostic,
	)
	result = bkchem_qt.io.snapshot_render.render_request(request)
	assert (
		isinstance(result, oasa.cdml_render.CDMLRenderFailure)
		and result.code == "render-failed"
		and result.diagnostics == (
			"Snapshot projection cleanup failed: "
			"RuntimeError: injected temporary reaper failure",
		)
	)
	after_state = (
		session.backend_snapshot, backend._revision, backend._saved_revision,
		backend._saved_cdml, tuple(backend._history), session._backend_history,
		tuple(session.scene.selectedItems()), session.document, session.scene,
		session._projected_backend_snapshot,
	)
	assert after_state == before_state
	bkchem_qt.canvas.graphics_retirement.temporary_scene_retirement_reaper.drain()
