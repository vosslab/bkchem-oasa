"""Behavioral coverage for backend-owned direct-root Arrow property patches."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.cdml_presentation_properties
import oasa.safe_xml


_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:v" '
	'version="26.07"><plus id="before"><point x="0cm" y="0cm"/></plus>'
	'<arrow id="arrow1" type="normal" start="no" end="yes" spline="no" '
	'width="01.50" color="#AABBCC" length="2cm" shape="(8,10,3)" v:flag="keep">'
	'<point x="1cm" y="1cm"/><!--keep--><?arrow keep?>'
	'<point x="2cm" y="2cm"/><point x="3cm" y="1cm"/></arrow>'
	'<text id="after"><point x="4cm" y="4cm"/><ftext>keep</ftext></text>'
	'</cdml>'
)


#============================================
def _patch(session: object, changes: tuple[tuple[str, object], ...]) -> object:
	"""Submit one Arrow patch at the public current revision."""
	request = oasa.cdml_presentation_properties.CDMLArrowPropertiesPatch(
		session.revision, "arrow1", changes,
	)
	return oasa.cdml_presentation_properties.patch_arrow_properties(session, request)


#============================================
def _arrow_facts(cdml: str) -> tuple[object, ...]:
	"""Return edited and preserved Arrow facts without comparing XML bytes."""
	document = oasa.safe_xml.parse_dom_from_string(cdml)
	root = document.documentElement
	arrow = next(
		child for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.getAttribute("id") == "arrow1"
	)
	points = tuple(
		(point.getAttribute("x"), point.getAttribute("y"))
		for point in arrow.childNodes
		if point.nodeType == point.ELEMENT_NODE and point.localName == "point"
	)
	root_order = tuple(
		child.getAttribute("id") for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	non_elements = tuple(
		(child.nodeType, child.nodeName, child.data) for child in arrow.childNodes
		if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE)
	)
	return (
		arrow.getAttribute("start"), arrow.getAttribute("end"),
		arrow.getAttribute("spline"), arrow.getAttribute("width"),
		arrow.getAttribute("color"), arrow.getAttribute("type"),
		arrow.getAttribute("length"), arrow.getAttribute("shape"),
		arrow.getAttribute("v:flag"), points, non_elements, root_order,
	)


#============================================
def test_patch_preserves_geometry_content_and_participates_in_history() -> None:
	"""One accepted patch changes only declared fields and restores exactly."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	before_facts = _arrow_facts(before.cdml)
	result = _patch(session, (
		("start_head", True), ("end_head", False), ("spline", True),
		("line_width", 2.5), ("color", "#DDEEFF"),
	))
	after_facts = _arrow_facts(result.snapshot.cdml)
	restored = session.restore(
		target_revision=before.revision, expected_revision=result.snapshot.revision,
	)

	assert result.changed and result.commit is not None and result.snapshot.is_dirty
	assert after_facts[:5] == ("yes", "no", "yes", "2.5", "#ddeeff")
	assert after_facts[5:] == before_facts[5:]
	assert restored.snapshot.cdml == before.cdml


#============================================
def test_semantic_defaults_and_lexical_equivalents_are_history_free() -> None:
	"""Visible equality never materializes defaults or allocates a revision."""
	source = _CDML.replace(
		' start="no" end="yes" spline="no" width="01.50" color="#AABBCC"',
		'',
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	before = session.snapshot()
	result = _patch(session, (
		("start_head", False), ("end_head", True), ("spline", False),
		("line_width", 1.0), ("color", "#000000"),
	))

	assert not result.changed and result.commit is None
	assert result.snapshot == before and session.snapshot() == before


#============================================
@pytest.mark.parametrize("changes", (
	(("start_head", 1),), (("line_width", float("nan")),),
	(("line_width", 20.1),), (("color", "black"),),
	(("color", "#112233"), ("color", "#445566")), (("shape", "keep"),),
))
def test_invalid_intent_is_typed_and_atomic(
		changes: tuple[tuple[str, object], ...],
		) -> None:
	"""Malformed, repeated, or unsupported scalar intent cannot mutate authority."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(
		oasa.cdml_presentation_properties.CDMLArrowPropertiesPatchError,
	):
		_patch(session, changes)

	assert session.snapshot() == before


#============================================
def test_target_and_revision_failures_leave_the_latest_snapshot_unchanged() -> None:
	"""Display-only targets and stale callbacks cannot retarget or partially edit."""
	display_only = _CDML.replace(
		'<point x="3cm" y="1cm"/></arrow>',
		'<point x="3cm" y="1cm"/><v:opaque keep="yes"/></arrow>',
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(display_only)
	before = session.snapshot()
	with pytest.raises(
		oasa.cdml_presentation_properties.CDMLArrowPropertiesPatchError,
	):
		_patch(session, (("line_width", 2.0),))
	assert session.snapshot() == before

	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	accepted = _patch(session, (("line_width", 2.0),))
	stale = oasa.cdml_presentation_properties.CDMLArrowPropertiesPatch(
		0, "arrow1", (("color", "#112233"),),
	)
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		oasa.cdml_presentation_properties.patch_arrow_properties(session, stale)
	assert session.snapshot() == accepted.snapshot
