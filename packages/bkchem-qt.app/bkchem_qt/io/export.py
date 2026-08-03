"""Export scene to SVG, PNG, and PDF formats."""

# Standard Library
import os
import tempfile
import dataclasses

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import oasa.cdml_render
import bkchem_qt.io.render_plan
import bkchem_qt.io.snapshot_render

# default margin around exported content in pixels
_DEFAULT_MARGIN = 20
# default scale factor for PNG export (2x for retina quality)
_DEFAULT_PNG_SCALE = 2.0


#============================================
@dataclasses.dataclass(frozen=True)
class SnapshotExportOutcome:
	"""One immutable frontend result from an exact backend snapshot export.

	The explicit export adapter translates backend request, result, and failure
	objects into built-in values before ordinary Qt actions observe the outcome.
	"""

	status: str
	error_code: str | None
	message: str
	snapshot_revision: int | None
	format_name: str
	artifact: bytes | None = None
	artifact_path: str | None = None
	warnings: tuple[str, ...] = ()

	#============================================
	@property
	def succeeded(self) -> bool:
		"""Return whether the adapter produced a nonempty exact-snapshot artifact."""
		return self.status == "success" and self.artifact is not None and bool(self.artifact)


#============================================
def _warning_messages(warnings: object) -> tuple[str, ...]:
	"""Freeze backend warning detail as human-readable plain values."""
	messages = []
	for warning in warnings:
		message = getattr(warning, "message", None)
		if not isinstance(message, str) or not message:
			message = str(warning)
		messages.append(message)
	return tuple(messages)


#============================================
def _failure_outcome(failure: oasa.cdml_render.CDMLRenderFailure,
		format_name: str) -> SnapshotExportOutcome:
	"""Translate one backend typed failure into the frontend result vocabulary."""
	return SnapshotExportOutcome(
		"failure", failure.code, failure.message, failure.snapshot_revision,
		format_name, warnings=_warning_messages(failure.diagnostics),
	)


#============================================
def render_snapshot_capture(capture: object, format_name: str) -> SnapshotExportOutcome:
	"""Render one opaque session capture and return only frozen plain data."""
	if isinstance(capture, oasa.cdml_render.CDMLRenderFailure):
		return _failure_outcome(capture, format_name)
	if not isinstance(capture, oasa.cdml_render.CDMLRenderRequest):
		return SnapshotExportOutcome(
			"failure", "invalid-render-request",
			"Visual export did not receive an exact backend snapshot request",
			None, format_name,
		)
	result = bkchem_qt.io.snapshot_render.render_request(capture)
	if isinstance(result, oasa.cdml_render.CDMLRenderFailure):
		return _failure_outcome(result, format_name)
	artifact = result.artifact
	if not isinstance(artifact, bytes) or not artifact:
		return SnapshotExportOutcome(
			"failure", "empty-artifact",
			"Snapshot render did not return a nonempty artifact",
			result.snapshot_revision, result.format_name,
			warnings=_warning_messages(result.warnings),
		)
	return SnapshotExportOutcome(
		"success", None, "Snapshot rendered", result.snapshot_revision,
		result.format_name, artifact, warnings=_warning_messages(result.warnings),
	)


#============================================
def render_session_snapshot(
		session: object, format_name: str, scope: str = "page",
		) -> SnapshotExportOutcome:
	"""Capture and render one session snapshot without leaking backend values."""
	try:
		capture = session.capture_visual_render_request(format_name, scope)
	except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
		return SnapshotExportOutcome(
			"failure", "session-unavailable", str(exc), None, format_name,
		)
	return render_snapshot_capture(capture, format_name)


#============================================
def _discard_staged_artifact(staged_path: str) -> str | None:
	"""Retire one unpublished staged artifact and preserve any cleanup diagnostic."""
	try:
		os.unlink(staged_path)
	except OSError as exc:
		return "Could not remove unpublished staged artifact: %s" % exc
	return None


#============================================
def _stage_artifact(
		artifact: bytes, file_path: str,
		) -> tuple[str | None, str | None, str | None]:
	"""Write bytes beside their destination before atomic publication."""
	directory = os.path.dirname(os.path.abspath(file_path))
	staged_path = None
	try:
		file_descriptor, staged_path = tempfile.mkstemp(
			prefix=".bkchem-export-", dir=directory,
		)
		with os.fdopen(file_descriptor, "wb") as destination:
			destination.write(artifact)
	except OSError as exc:
		cleanup_warning = None
		if staged_path is not None:
			cleanup_warning = _discard_staged_artifact(staged_path)
		return None, str(exc), cleanup_warning
	return staged_path, None, None


#============================================
def write_snapshot_artifact(capture: object, format_name: str,
		file_path: str) -> SnapshotExportOutcome:
	"""Render one opaque capture and publish only a successful exact artifact."""
	result = render_snapshot_capture(capture, format_name)
	if not result.succeeded:
		return result
	artifact = result.artifact
	if not isinstance(artifact, bytes) or not artifact:
		return SnapshotExportOutcome(
			"failure", "empty-artifact", "Snapshot render did not return a nonempty artifact",
			result.snapshot_revision, result.format_name, warnings=result.warnings,
		)
	staged_path, stage_error, cleanup_warning = _stage_artifact(artifact, file_path)
	if staged_path is None:
		warnings = result.warnings
		if cleanup_warning is not None:
			warnings += (cleanup_warning,)
		return SnapshotExportOutcome(
			"failure", "artifact-write-failed", stage_error or "Could not stage artifact",
			result.snapshot_revision, result.format_name, warnings=warnings,
		)
	try:
		os.replace(staged_path, file_path)
	except OSError as exc:
		cleanup_warning = _discard_staged_artifact(staged_path)
		warnings = result.warnings
		if cleanup_warning is not None:
			warnings += (cleanup_warning,)
		return SnapshotExportOutcome(
			"failure", "artifact-write-failed", str(exc), result.snapshot_revision,
			result.format_name, warnings=warnings,
		)
	return dataclasses.replace(
		result, artifact_path=file_path, message="Snapshot artifact exported",
	)


#============================================
def write_session_snapshot_artifact(
		session: object, format_name: str, file_path: str,
		) -> SnapshotExportOutcome:
	"""Capture, render, and write one exact snapshot through the explicit adapter."""
	try:
		capture = session.capture_visual_render_request(format_name)
	except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
		return SnapshotExportOutcome(
			"failure", "session-unavailable", str(exc), None, format_name,
		)
	return write_snapshot_artifact(capture, format_name, file_path)


#============================================
def _export_source(scene: PySide6.QtWidgets.QGraphicsScene,
		format_name: str, margin: int) -> tuple[PySide6.QtWidgets.QGraphicsScene,
			bkchem_qt.io.render_plan.RenderPlan,
			bkchem_qt.io.render_plan.ExportProjection | None]:
	"""Return the non-decorative source scene needed by one render plan."""
	plan = bkchem_qt.io.render_plan.build_render_plan(scene, format_name, margin)
	if not plan.crop_to_content:
		return scene, plan, None
	projection = bkchem_qt.io.render_plan.project_supported_items(scene)
	try:
		# Recompute content bounds after projection so cloned number labels and marks
		# participate while paper/grid decorations remain absent.
		plan = bkchem_qt.io.render_plan.build_render_plan(
			projection.scene, format_name, margin, force_content_crop=True,
		)
	except Exception:
		# This is the only pre-handoff projection failure path.  Disposal exhausts
		# its own cleanup; suppress its error so render-plan failure stays primary.
		try:
			projection.dispose()
		except Exception:
			pass
		raise
	return projection.scene, plan, projection


#============================================
def export_svg(scene: PySide6.QtWidgets.QGraphicsScene, file_path: str,
		margin: int = _DEFAULT_MARGIN) -> None:
	"""Export scene to SVG file using QSvgGenerator.

	Uses the modeled paper page unless CDML enables ``crop_svg``. Cropped SVG
	renders a temporary supported-content projection with ``crop_margin``.

	Args:
		scene: QGraphicsScene to export.
		file_path: Output SVG file path.
		margin: Fallback content margin when CDML omits ``crop_margin``.
	"""
	# import SVG generator; try QtSvgWidgets first, fall back to QtSvg
	try:
		import PySide6.QtSvgWidgets
		generator_class = PySide6.QtSvgWidgets.QSvgGenerator
	except (ImportError, AttributeError):
		import PySide6.QtSvg
		generator_class = PySide6.QtSvg.QSvgGenerator

	source_scene, plan, projection = _export_source(scene, "svg", margin)
	rect = plan.source_rect
	painter = PySide6.QtGui.QPainter()
	with bkchem_qt.io.render_plan.ExportRenderScope(projection, painter):
		# set up the SVG generator
		generator = generator_class()
		generator.setFileName(file_path)
		generator.setSize(PySide6.QtCore.QSize(int(rect.width()), int(rect.height())))
		generator.setViewBox(rect)
		generator.setTitle("BKChem-Qt Export")
		generator.setDescription("Chemistry structure exported from BKChem-Qt")
		# render the scene into the SVG
		painter.begin(generator)
		source_scene.render(painter, PySide6.QtCore.QRectF(), rect)


#============================================
def export_png(scene: PySide6.QtWidgets.QGraphicsScene, file_path: str,
		margin: int = _DEFAULT_MARGIN, scale: float = _DEFAULT_PNG_SCALE) -> None:
	"""Export scene to PNG file using QImage and QPainter.

	Creates a transparent QImage at the requested scale factor and renders the
	modeled paper page onto it.

	Args:
		scene: QGraphicsScene to export.
		file_path: Output PNG file path.
		margin: Retained API compatibility parameter; PNG uses the paper page.
		scale: Resolution multiplier (default 2.0 for retina quality).
	"""
	source_scene, plan, projection = _export_source(scene, "png", margin)
	rect = plan.source_rect
	painter = PySide6.QtGui.QPainter()
	with bkchem_qt.io.render_plan.ExportRenderScope(projection, painter):
		# compute image dimensions at the given scale
		width = int(rect.width() * scale)
		height = int(rect.height() * scale)
		# create a transparent image
		image = PySide6.QtGui.QImage(
			width, height,
			PySide6.QtGui.QImage.Format.Format_ARGB32_Premultiplied,
		)
		image.fill(PySide6.QtCore.Qt.GlobalColor.transparent)
		# render the scene onto the image
		painter.begin(image)
		painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.Antialiasing, True)
		painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.TextAntialiasing, True)
		# map the scene rect to the full image rect
		target_rect = PySide6.QtCore.QRectF(0, 0, width, height)
		source_scene.render(painter, target_rect, rect)
		# save to file only after the painter closes in the scope exit.
		painter.end()
		image.save(file_path, "PNG")


#============================================
def export_pdf(scene: PySide6.QtWidgets.QGraphicsScene, file_path: str,
		margin: int = _DEFAULT_MARGIN) -> None:
	"""Export scene to PDF using QPdfWriter.

	Sets page size to the modeled paper dimensions and renders the page onto PDF.

	Args:
		scene: QGraphicsScene to export.
		file_path: Output PDF file path.
		margin: Retained API compatibility parameter; PDF uses the paper page.
	"""
	source_scene, plan, projection = _export_source(scene, "pdf", margin)
	rect = plan.source_rect
	painter = PySide6.QtGui.QPainter()
	with bkchem_qt.io.render_plan.ExportRenderScope(projection, painter):
		# create PDF writer
		writer = PySide6.QtGui.QPdfWriter(file_path)
		# set page size to match content dimensions (in points, 72 dpi)
		page_size = PySide6.QtCore.QSizeF(rect.width(), rect.height())
		page_layout = PySide6.QtGui.QPageLayout(
			PySide6.QtGui.QPageSize(page_size, PySide6.QtGui.QPageSize.Unit.Point),
			PySide6.QtGui.QPageLayout.Orientation.Portrait,
			PySide6.QtCore.QMarginsF(0, 0, 0, 0),
		)
		writer.setPageLayout(page_layout)
		# render the scene
		painter.begin(writer)
		painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.Antialiasing, True)
		painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.TextAntialiasing, True)
		# map scene rect to the full page
		target_rect = PySide6.QtCore.QRectF(
			0, 0,
			writer.width(), writer.height(),
		)
		source_scene.render(painter, target_rect, rect)
