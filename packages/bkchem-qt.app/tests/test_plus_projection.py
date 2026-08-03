"""Focused semantic checks for disposable Plus projections."""

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.io.cdml_document_io
import bkchem_qt.models.document_object
import oasa.cdml_document


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
	prepared = bkchem_qt.io.cdml_document_io.prepare_compatibility_projection_from_cdml(
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


#============================================
def test_backend_described_plus_has_no_retained_presentation_xml(
		qapp: object,
		) -> None:
	"""The synchronized presentation model is rebuilt from OASA plain values."""
	backend_session = oasa.cdml_document.CDMLDocumentSession.load(
		'<cdml version="0.15"><plus id="plus-1"><point x="1cm" y="2cm"/></plus></cdml>',
	)
	prepared = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection(
		backend_session.projection_snapshot(),
	)
	try:
		assert prepared.document.presentation_objects[0].raw_xml is None
		assert prepared.presentation_items[0].toPlainText() == "+"
	finally:
		bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)


#============================================
def test_loaded_plus_without_root_style_uses_historical_visible_defaults(
		qapp: object,
		) -> None:
	"""A missing root size remains 14 points and missing color remains black."""
	prepared = bkchem_qt.io.cdml_document_io.prepare_compatibility_projection_from_cdml(
		'<cdml version="0.15"><plus id="plus-1">'
		'<point x="1cm" y="2cm"/></plus></cdml>',
	)
	item = prepared.presentation_items[0]
	try:
		assert item.font().pointSizeF() == pytest.approx(14.0)
		assert item.defaultTextColor().name() == "#000000"
	finally:
		bkchem_qt.io.cdml_document_io.dispose_prepared_projection(prepared)
