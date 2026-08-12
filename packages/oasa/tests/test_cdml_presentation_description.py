"""Behavior checks for the Qt-free direct-root presentation observation."""

# Standard Library
import dataclasses
import json

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document


_CDML = '''<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" version="26.07">
<arrow id="arrow-1"><point x="1cm" y="2cm"/><point x="2cm" y="2cm"/></arrow>
<plus id="plus-1"><point x="216px" y="288"/></plus>
<text id="text-1"><point x="5cm" y="6cm"/>
<ftext>&lt;b&gt;H&lt;/b&gt;&lt;sub&gt;2&lt;/sub&gt;O</ftext></text>
<rect id="rect-1" x1="4cm" y1="3cm" x2="1cm" y2="2cm"/>
<polyline id="wave-1" style="wavy"><point x="1cm" y="1cm"/><point x="2cm" y="1cm"/></polyline>
<foreign:opaque xmlns:foreign="urn:opaque" id="opaque-1"/>
</cdml>'''


#============================================
def test_presentation_description_keeps_source_order_geometry_and_rich_text() -> None:
	"""Supported roots expose scene geometry and authored Text runs in source order."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	description = session.presentation_description(
		oasa.cdml_document.CDMLPresentationDescriptionQuery(session.revision),
	)
	assert tuple(record.identifier for record in description.records) == (
		"arrow-1", "plus-1", "text-1", "rect-1", "wave-1",
	)
	assert description.records[2].ftext_runs == (("H", ("b",)), ("2", ("sub",)), ("O", ()))


#============================================
def test_presentation_description_reports_opaque_content_and_is_plain_immutable() -> None:
	"""Opaque roots remain backend content while the observation is value-only."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	description = session.presentation_description(
		oasa.cdml_document.CDMLPresentationDescriptionQuery(session.revision),
	)
	plain_description = dataclasses.asdict(description)
	json.dumps(plain_description)
	assert description.issues[0].identifier == "opaque-1"
	assert description.records[1].points[0][:2] == pytest.approx((216.0, 288.0))


#============================================
def test_presentation_description_rejects_stale_revision_without_changing_session() -> None:
	"""The read-only observation uses the same stale-revision behavior as other queries."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.presentation_description(oasa.cdml_document.CDMLPresentationDescriptionQuery(1))
	assert session.snapshot() == before


#============================================
def test_presentation_description_diagnoses_unprojectable_direct_content() -> None:
	"""Unexpected child content is display-only and malformed geometry is omitted."""
	cdml = '''<cdml xmlns:vendor="urn:vendor" version="26.07">
	<text id="text-1"><point x="1cm" y="1cm"/><ftext>safe</ftext>
	<vendor:metadata keep="yes"/></text>
	<arrow id="arrow-1"><point x="1cm" y="1cm"/></arrow></cdml>'''
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	description = session.presentation_description(
		oasa.cdml_document.CDMLPresentationDescriptionQuery(session.revision),
	)
	assert description.records[0].disposition == "display-only"
	assert tuple(issue.identifier for issue in description.issues) == ("text-1", "arrow-1")


#============================================
def test_presentation_description_omits_text_without_required_ftext() -> None:
	"""A malformed Text root stays in backend CDML instead of becoming editable."""
	cdml = '<cdml><text id="text-1"><point x="1cm" y="1cm"/></text></cdml>'
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	description = session.presentation_description(
		oasa.cdml_document.CDMLPresentationDescriptionQuery(session.revision),
	)
	assert not description.records
	assert description.issues[0].reason == "Text presentation requires one direct ftext"


#============================================
def test_presentation_description_resolves_standard_line_appearance() -> None:
	"""A root without authored stroke values receives normalized backend facts."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<cdml><standard line_width="2px" line_color="#123"/>'
		'<arrow id="a"><point x="0cm" y="0cm"/><point x="1cm" y="0cm"/>'
		'</arrow></cdml>',
	)
	record = session.projection_snapshot().plan.presentation_description.records[0]
	assert (record.appearance.line_width, record.appearance.line_color) == (2.0, "#112233")


#============================================
def test_presentation_description_resolves_standard_text_appearance() -> None:
	"""Text editing receives the same effective font values as projection."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<cdml><standard font_family="Palatino" font_size="16" line_color="#234"/>'
		'<text id="t"><point x="0cm" y="0cm"/><ftext>water</ftext></text></cdml>',
	)
	appearance = session.projection_snapshot().plan.presentation_description.records[0].appearance
	assert (appearance.font_family, appearance.font_size, appearance.font_color) == (
		"Palatino", 16, "#223344",
	)


#============================================
def test_presentation_description_keeps_plus_semantic_size_default_in_backend() -> None:
	"""The classic Plus size default is an OASA fact rather than a Qt fallback."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<cdml><plus id="p"><point x="0cm" y="0cm"/></plus></cdml>',
	)
	appearance = session.projection_snapshot().plan.presentation_description.records[0].appearance
	assert appearance.font_size == 14
