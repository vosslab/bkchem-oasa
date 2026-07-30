"""Focused semantic checks for disposable Plus projections."""

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.io.cdml_document_io
import bkchem_qt.models.document_object


#============================================
def test_local_plus_projection_keeps_literal_glyph_centered(
		qapp: object,
		) -> None:
	"""A local symbolic Plus retains its glyph and stored center point."""
	model = bkchem_qt.models.document_object.PresentationObject(
		"plus",
		attributes={"font_size": "18", "color": "#000000"},
		points=[(100.0, 200.0, None)],
	)
	item = bkchem_qt.canvas.document_projection.create_presentation_item(model)
	if item is None:
		model.deleteLater()
		raise RuntimeError("Local Plus projection did not create a graphics item")
	try:
		center = item.pos() + item.boundingRect().center()
		assert item.toPlainText() == "+"
		assert (center.x(), center.y()) == pytest.approx((100.0, 200.0), abs=0.1)
	finally:
		bkchem_qt.canvas.document_projection.dispose_detached_items([item])
		model.deleteLater()


#============================================
def test_loaded_plus_projection_keeps_literal_glyph_centered(
		qapp: object,
		) -> None:
	"""A legacy-compatible Plus record keeps its literal glyph and center."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_projection_from_cdml(
		'<cdml version="0.15"><plus id="plus-1" font_size="18" '
		'color="#000000"><point x="3.528cm" y="7.056cm"/>'
		'<ftext>Ignored <b>rich text</b></ftext></plus></cdml>',
	)
	item = prepared.presentation_items[0]
	try:
		center = item.pos() + item.boundingRect().center()
		assert item.toPlainText() == "+"
		assert (center.x(), center.y()) == pytest.approx((100.006, 200.013), abs=0.1)
	finally:
		bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)
