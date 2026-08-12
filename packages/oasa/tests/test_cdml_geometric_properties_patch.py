"""Behavioral laws for backend-owned geometric presentation appearance."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.cdml_presentation_properties
import oasa.safe_xml


_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:v" '
	'version="26.07"><plus id="before"><point x="0cm" y="0cm"/></plus>'
	'<rect id="shape1" x1="1cm" y1="2cm" x2="3cm" y2="4cm" '
	'width="01.50" line_color="#ABC" area_color="#DDEEFF" v:flag="keep">'
	'<v:extra keep="child"/><!--shape--><?shape keep?></rect>'
	'<polyline id="line1" width="2" color="#123456" spline="1" v:flag="keep">'
	'<point x="1cm" y="1cm"/><point x="2cm" y="2cm"/><!--line--></polyline>'
	'<polygon id="polygon1" width="1" line_color="#000" area_color="none">'
	'<point x="4cm" y="1cm"/><point x="5cm" y="2cm"/>'
	'<point x="6cm" y="1cm"/></polygon>'
	'<text id="after"><point x="7cm" y="1cm"/><ftext>keep</ftext></text>'
	'</cdml>'
)


#============================================
def _patch(
		session: object, identifier: str,
		changes: tuple[tuple[str, object], ...],
		) -> object:
	"""Submit one geometric patch at the public current revision."""
	request = oasa.cdml_presentation_properties.CDMLGeometricPropertiesPatch(
		session.revision, identifier, changes,
	)
	return oasa.cdml_presentation_properties.patch_geometric_properties(session, request)


#============================================
def _root_facts(cdml: str, identifier: str) -> tuple[object, ...]:
	"""Return edited and preservation facts without comparing serializer bytes."""
	document = oasa.safe_xml.parse_dom_from_string(cdml)
	root = document.documentElement
	element = next(
		child for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.getAttribute("id") == identifier
	)
	points = tuple(
		(child.getAttribute("x"), child.getAttribute("y"))
		for child in element.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.localName == "point"
	)
	non_elements = tuple(
		(child.nodeType, child.nodeName, child.data) for child in element.childNodes
		if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE)
	)
	extensions = tuple(
		child.toxml() for child in element.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.namespaceURI == "urn:v"
	)
	root_order = tuple(
		child.getAttribute("id") for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	return (
		element.tagName, element.getAttribute("width"),
		element.getAttribute("line_color"), element.getAttribute("area_color"),
		element.getAttribute("color"), element.getAttribute("spline"),
		element.getAttribute("v:flag"), extensions, points, non_elements, root_order,
	)


#============================================
def test_closed_shape_patch_preserves_geometry_content_and_history() -> None:
	"""A closed-shape appearance edit changes no geometry or opaque residue."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	before_facts = _root_facts(before.cdml, "shape1")
	result = _patch(session, "shape1", (
		("line_width", 2.5), ("line_color", "#445566"),
		("area_color", None),
	))
	after_facts = _root_facts(result.snapshot.cdml, "shape1")
	restored = session.restore(
		target_revision=before.revision, expected_revision=result.snapshot.revision,
	)

	assert result.changed and result.commit is not None and result.snapshot.is_dirty
	assert after_facts[1:4] == ("2.5", "#445566", "none")
	assert after_facts[:1] + after_facts[4:] == before_facts[:1] + before_facts[4:]
	assert restored.snapshot.cdml == before.cdml


#============================================
def test_open_and_closed_records_share_stroke_semantics_without_fill_leakage() -> None:
	"""Both geometry classes share stroke intent while fill remains shape-only."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	line_result = _patch(session, "line1", (
		("line_width", 3.0), ("line_color", "#AABBCC"),
	))
	line_facts = _root_facts(line_result.snapshot.cdml, "line1")
	polygon_result = _patch(session, "polygon1", (("area_color", "#abcdef"),))
	polygon_facts = _root_facts(polygon_result.snapshot.cdml, "polygon1")

	assert line_facts[1:6] == ("3", "#aabbcc", "", "#123456", "1")
	assert (
		polygon_facts[3] == "#abcdef"
		and polygon_result.snapshot.revision > line_result.snapshot.revision
	)


#============================================
@pytest.mark.parametrize("kind", ("rect", "square", "oval", "circle"))
def test_bound_based_closed_shape_family_shares_one_patch_contract(kind: str) -> None:
	"""Every bounds-based shape accepts the same stroke and fill semantics."""
	source = (
		f'<cdml><{kind} id="shape" x1="1cm" y1="2cm" x2="3cm" y2="4cm" '
		f'width="1" line_color="#000" area_color="#fff"/></cdml>'
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	result = _patch(session, "shape", (
		("line_width", 2.0), ("line_color", "#112233"),
		("area_color", "#445566"),
	))

	assert _root_facts(result.snapshot.cdml, "shape")[1:4] == (
		"2", "#112233", "#445566",
	)


#============================================
def test_semantic_legacy_colors_defaults_and_transparency_are_history_free() -> None:
	"""Visible equality preserves compact colors and lexical numeric spellings."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = _patch(session, "shape1", (
		("line_width", 1.5), ("line_color", "#aabbcc"),
		("area_color", "#ddeeff"),
	))
	transparent = _patch(session, "polygon1", (("area_color", None),))

	assert not result.changed and result.commit is None and result.snapshot == before
	assert not transparent.changed and transparent.commit is None and session.snapshot() == before


#============================================
@pytest.mark.parametrize("identifier,changes", (
	("line1", (("area_color", "#112233"),)),
	("line1", (("line_width", float("nan")),)),
	("shape1", (("line_color", "black"),)),
	("shape1", (("line_color", "#abc"),)),
	("shape1", (("line_color", "#112233"), ("line_color", "#445566"))),
))
def test_invalid_or_inapplicable_intent_is_typed_and_atomic(
		identifier: str, changes: tuple[tuple[str, object], ...],
		) -> None:
	"""Bad scalar intent and fill on an open line cannot mutate authority."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(
		oasa.cdml_presentation_properties.CDMLGeometricPropertiesPatchError,
	):
		_patch(session, identifier, changes)

	assert session.snapshot() == before


#============================================
def test_wavy_display_only_and_stale_targets_cannot_retarget() -> None:
	"""Specialized, preservation-only, and stale roots remain atomic failures."""
	wavy = _CDML.replace('id="line1"', 'id="line1" style="wavy"')
	session = oasa.cdml_document.CDMLDocumentSession.load(wavy)
	before = session.snapshot()
	with pytest.raises(
		oasa.cdml_presentation_properties.CDMLGeometricPropertiesPatchError,
	):
		_patch(session, "line1", (("line_width", 3.0),))
	assert session.snapshot() == before

	accepted = _patch(session, "shape1", (("line_width", 2.0),))
	stale = oasa.cdml_presentation_properties.CDMLGeometricPropertiesPatch(
		0, "shape1", (("line_color", "#112233"),),
	)
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		oasa.cdml_presentation_properties.patch_geometric_properties(session, stale)
	assert session.snapshot() == accepted.snapshot


#============================================
def test_unsafe_current_snapshot_is_rejected_without_a_property_commit(
		monkeypatch: object,
		) -> None:
	"""The public geometric operation reauthorizes its detached CDML source."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	hostile = oasa.cdml_document.CDMLSnapshot(
		before.revision,
		'<!DOCTYPE cdml [<!ENTITY value "unsafe">]><cdml>&value;</cdml>',
		before.is_dirty,
	)
	monkeypatch.setattr(session, "snapshot", lambda: hostile)
	request = oasa.cdml_presentation_properties.CDMLGeometricPropertiesPatch(
		before.revision, "shape1", (("line_width", 2.0),),
	)
	with pytest.raises(oasa.cdml_presentation_properties.CDMLGeometricPropertiesPatchError):
		oasa.cdml_presentation_properties.patch_geometric_properties(session, request)
	monkeypatch.undo()

	assert session.snapshot() == before
