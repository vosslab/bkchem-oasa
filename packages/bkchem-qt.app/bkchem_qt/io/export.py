"""Export scene to SVG, PNG, and PDF formats."""

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
def render_snapshot_request(
		request: oasa.cdml_render.CDMLRenderRequest,
		) -> oasa.cdml_render.CDMLRenderResult | oasa.cdml_render.CDMLRenderFailure:
	"""Render one backend-owned snapshot without consulting a retained scene."""
	return bkchem_qt.io.snapshot_render.render_request(request)


#============================================
def write_snapshot_artifact(
		request: oasa.cdml_render.CDMLRenderRequest, file_path: str,
		) -> oasa.cdml_render.CDMLRenderResult | oasa.cdml_render.CDMLRenderFailure:
	"""Render one snapshot request and publish only its returned bytes to a path."""
	result = render_snapshot_request(request)
	if isinstance(result, oasa.cdml_render.CDMLRenderFailure):
		return result
	if result.artifact is None:
		return oasa.cdml_render.CDMLRenderFailure(
			"render-failed", "Snapshot render did not return an artifact",
			result.snapshot_revision,
		)
	try:
		with open(file_path, "wb") as destination:
			destination.write(result.artifact)
	except OSError as exc:
		return oasa.cdml_render.CDMLRenderFailure(
			"artifact-write-failed", str(exc), result.snapshot_revision,
		)
	return oasa.cdml_render.CDMLRenderResult(
		result.snapshot_revision, result.format_name, result.artifact,
		artifact_path=file_path, warnings=result.warnings,
	)


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
