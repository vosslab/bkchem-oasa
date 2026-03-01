"""Export scene to SVG, PNG, and PDF formats."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# default margin around exported content in pixels
_DEFAULT_MARGIN = 20
# default scale factor for PNG export (2x for retina quality)
_DEFAULT_PNG_SCALE = 2.0


#============================================
def _compute_scene_rect(scene, margin: int) -> PySide6.QtCore.QRectF:
	"""Compute the bounding rect of all scene items with margin.

	Finds the tight bounding rect around all items in the scene,
	then expands it by the requested margin on all sides.

	Args:
		scene: QGraphicsScene to measure.
		margin: Pixel margin to add around the content.

	Returns:
		QRectF enclosing all items with margin applied.
	"""
	# itemsBoundingRect gives the union of all item bounding rects
	rect = scene.itemsBoundingRect()
	# expand by margin on all sides
	expanded = rect.adjusted(-margin, -margin, margin, margin)
	return expanded


#============================================
def export_svg(scene, file_path: str, margin: int = _DEFAULT_MARGIN) -> None:
	"""Export scene to SVG file using QSvgGenerator.

	Computes the bounding rect of all items, adds margin,
	and renders the scene into an SVG generator.

	Args:
		scene: QGraphicsScene to export.
		file_path: Output SVG file path.
		margin: Pixel margin around content (default 20).
	"""
	# import SVG generator; try QtSvgWidgets first, fall back to QtSvg
	try:
		import PySide6.QtSvgWidgets
		generator_class = PySide6.QtSvgWidgets.QSvgGenerator
	except (ImportError, AttributeError):
		import PySide6.QtSvg
		generator_class = PySide6.QtSvg.QSvgGenerator

	rect = _compute_scene_rect(scene, margin)
	# set up the SVG generator
	generator = generator_class()
	generator.setFileName(file_path)
	generator.setSize(PySide6.QtCore.QSize(int(rect.width()), int(rect.height())))
	generator.setViewBox(rect)
	generator.setTitle("BKChem-Qt Export")
	generator.setDescription("Chemistry structure exported from BKChem-Qt")
	# render the scene into the SVG
	painter = PySide6.QtGui.QPainter()
	painter.begin(generator)
	scene.render(painter, PySide6.QtCore.QRectF(), rect)
	painter.end()


#============================================
def export_png(scene, file_path: str, margin: int = _DEFAULT_MARGIN,
			   scale: float = _DEFAULT_PNG_SCALE) -> None:
	"""Export scene to PNG file using QImage and QPainter.

	Creates a transparent QImage at the requested scale factor and
	renders the scene content onto it.

	Args:
		scene: QGraphicsScene to export.
		file_path: Output PNG file path.
		margin: Pixel margin around content (default 20).
		scale: Resolution multiplier (default 2.0 for retina quality).
	"""
	rect = _compute_scene_rect(scene, margin)
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
	painter = PySide6.QtGui.QPainter()
	painter.begin(image)
	painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.Antialiasing, True)
	painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.TextAntialiasing, True)
	# map the scene rect to the full image rect
	target_rect = PySide6.QtCore.QRectF(0, 0, width, height)
	scene.render(painter, target_rect, rect)
	painter.end()
	# save to file
	image.save(file_path, "PNG")


#============================================
def export_pdf(scene, file_path: str, margin: int = _DEFAULT_MARGIN) -> None:
	"""Export scene to PDF using QPdfWriter.

	Sets page size to match the scene content dimensions and
	renders the scene onto the PDF page.

	Args:
		scene: QGraphicsScene to export.
		file_path: Output PDF file path.
		margin: Pixel margin around content (default 20).
	"""
	rect = _compute_scene_rect(scene, margin)
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
	painter = PySide6.QtGui.QPainter()
	painter.begin(writer)
	painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.Antialiasing, True)
	painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.TextAntialiasing, True)
	# map scene rect to the full page
	target_rect = PySide6.QtCore.QRectF(
		0, 0,
		writer.width(), writer.height(),
	)
	scene.render(painter, target_rect, rect)
	painter.end()
