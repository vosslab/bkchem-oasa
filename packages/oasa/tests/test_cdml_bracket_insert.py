"""Behavioral coverage for backend-owned rectangular and round brackets."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_bracket
import oasa.cdml_document
import oasa.cdml_writer
import oasa.cdml_xml


_CDML = (
	'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml" '
	'xmlns:v="urn:vendor" version="26.07"><c:standard line_width="2px" '
	'font_size="12" font_family="Helvetica" line_color="#123456" area_color="">'
	'<c:bond width="6px" wedge-width="5px" double-ratio="0.75"/>'
	'<c:atom show_hydrogens="0"/></c:standard><!--keep--><v:note keep="yes"/>'
	'</c:cdml>'
)

_PAIRED_CDML = _CDML.replace(
	"</c:cdml>",
	'<c:polyline id="pair_left" bracket_pair="pair_left" '
	'bracket_side="left" width="2" line_color="#112233" spline="no">'
	'<c:point x="1cm" y="1cm"/><c:point x="1cm" y="2cm"/>'
	'</c:polyline><c:polyline id="pair_right" bracket_pair="pair_left" '
	'bracket_side="right" width="2" line_color="#112233" spline="no">'
	'<c:point x="3cm" y="1cm"/><c:point x="3cm" y="2cm"/>'
	'</c:polyline></c:cdml>',
)


#============================================
def _insert(
		session: object, style: str,
		) -> oasa.cdml_bracket.CDMLBracketInsertResult:
	"""Insert one test bracket pair through the public backend operation."""
	return oasa.cdml_bracket.insert_brackets(
		session,
		oasa.cdml_bracket.CDMLBracketInsertRequest(
			session.revision, style, (10.0, 20.0, 50.0, 70.0),
		),
	)


#============================================
def _polyline_facts(
		cdml_text: str,
		) -> tuple[tuple[str, str, str, tuple[tuple[float, float], ...]], ...]:
	"""Read generated bracket facts through the hardened CDML parser."""
	document = oasa.cdml_xml.parse_cdml_dom(cdml_text.encode("utf-8"))
	result = []
	for child in document.documentElement.childNodes:
		if (
			child.nodeType != child.ELEMENT_NODE
			or (child.localName or child.tagName) != "polyline"
		):
			continue
		points = tuple(
			tuple(
				float(point.getAttribute(axis).removesuffix("cm"))
				* oasa.cdml_writer.POINTS_PER_CM
				for axis in ("x", "y")
			)
			for point in child.childNodes
			if point.nodeType == point.ELEMENT_NODE
			and (point.localName or point.tagName) == "point"
		)
		result.append((
			child.getAttribute("id"), child.getAttribute("spline"),
			child.getAttribute("line_color"), points,
		))
	return tuple(result)


#============================================
def _pair_strokes(cdml_text: str) -> tuple[tuple[str, str, str], ...]:
	"""Return durable pair-member stroke facts through the hardened CDML boundary."""
	document = oasa.cdml_xml.parse_cdml_dom(cdml_text.encode("utf-8"))
	return tuple(
		(
			child.getAttribute("id"), child.getAttribute("width"),
			child.getAttribute("line_color"),
		)
		for child in document.documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE
		and (child.localName or child.tagName) == "polyline"
		and child.getAttribute("bracket_pair") == "pair_left"
	)


#============================================
@pytest.mark.parametrize(("style", "spline", "middle_offset"), (
	("rectangular", "no", 0.0),
	("round", "yes", 2.5),
))
def test_insert_uses_classic_geometry_and_preserves_document(
		style: str, spline: str, middle_offset: float,
		) -> None:
	"""Both styles share one proportional, standard-aware backend operation."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = _insert(session, style)
	facts = _polyline_facts(result.snapshot.cdml)
	dx = 0.05 * math.hypot(40.0, 50.0)
	expected = (
		((10.0 + dx, 20.0), (10.0, 20.0 + middle_offset),
			(10.0, 70.0 - middle_offset), (10.0 + dx, 70.0)),
		((50.0 - dx, 20.0), (50.0, 20.0 + middle_offset),
			(50.0, 70.0 - middle_offset), (50.0 - dx, 70.0)),
	)
	document = oasa.cdml_xml.parse_cdml_dom(result.snapshot.cdml.encode("utf-8"))
	root_children = tuple(document.documentElement.childNodes)

	assert result.changed and result.commit is not None
	assert result.pair_id == result.left_id
	assert len(facts) == 2 and len(result.commit.id_map) == 2
	assert tuple(
		(child.getAttribute("bracket_pair"), child.getAttribute("bracket_side"))
		for child in root_children
		if child.nodeType == child.ELEMENT_NODE and child.localName == "polyline"
	) == ((result.left_id, "left"), (result.left_id, "right"))
	assert all(identifier and curve == spline and color == "#123456"
		for identifier, curve, color, _points in facts)
	assert all(
		abs(actual - target) <= 0.02
		for fact, expected_points in zip(facts, expected)
		for actual_point, expected_point in zip(fact[3], expected_points)
		for actual, target in zip(actual_point, expected_point)
	)
	assert all(
		element.getAttribute("width") == "2"
		for element in root_children
		if element.nodeType == element.ELEMENT_NODE and element.localName == "polyline"
	)
	assert root_children[1].nodeType == root_children[1].COMMENT_NODE
	assert root_children[1].data == "keep"
	assert root_children[2].nodeType == root_children[2].ELEMENT_NODE
	assert root_children[2].namespaceURI == "urn:vendor"
	assert session.restore(
		target_revision=before.revision, expected_revision=result.commit.revision,
	).snapshot.cdml == before.cdml


#============================================
@pytest.mark.parametrize(("style", "bounds"), (
	("square", (0.0, 0.0, 10.0, 10.0)),
	("round", (0.0, 0.0, math.nan, 10.0)),
	("rectangular", (0.0, 0.0, 0.0, 10.0)),
	("rectangular", (False, 0.0, 10.0, 10.0)),
))
def test_invalid_insert_is_typed_and_atomic(style: str, bounds: tuple) -> None:
	"""Malformed style or geometry cannot allocate IDs, history, or content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	request = oasa.cdml_bracket.CDMLBracketInsertRequest(
		before.revision, style, bounds,
	)

	with pytest.raises(oasa.cdml_bracket.CDMLBracketInsertError):
		oasa.cdml_bracket.insert_brackets(session, request)

	assert session.snapshot() == before


#============================================
def test_stale_insert_cannot_mutate_current_revision() -> None:
	"""A bracket intent remains bound to the revision that supplied its bounds."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	stale = oasa.cdml_bracket.CDMLBracketInsertRequest(
		session.revision, "round", (0.0, 0.0, 10.0, 20.0),
	)
	accepted = _insert(session, "rectangular")

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		oasa.cdml_bracket.insert_brackets(session, stale)

	assert session.snapshot() == accepted.snapshot


#============================================
def test_bracket_properties_patch_updates_both_members_once_and_roundtrips() -> None:
	"""One valid durable pair receives one shared revision-bound appearance edit."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_PAIRED_CDML)
	before = session.snapshot()
	result = oasa.cdml_bracket.patch_bracket_properties(
		session,
		oasa.cdml_bracket.CDMLBracketPropertiesPatch(
			before.revision, "pair_left", (("line_width", 3.5), ("line_color", "#AABBCC")),
		),
	)
	reloaded = oasa.cdml_document.CDMLDocumentSession.load(result.snapshot.cdml)

	assert result.changed and result.commit is not None
	assert result.member_ids == ("pair_left", "pair_right")
	assert _pair_strokes(result.snapshot.cdml) == (
		("pair_left", "3.5", "#aabbcc"), ("pair_right", "3.5", "#aabbcc"),
	)
	assert _pair_strokes(reloaded.snapshot().cdml) == _pair_strokes(result.snapshot.cdml)
	restored = session.restore(
		target_revision=before.revision, expected_revision=result.snapshot.revision,
	).snapshot
	assert restored.cdml == before.cdml and restored.is_dirty == before.is_dirty


#============================================
def test_bracket_properties_noop_and_stale_intent_leave_history_unchanged() -> None:
	"""No-op and stale pair appearance requests cannot manufacture history entries."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_PAIRED_CDML)
	before = session.snapshot()
	request = oasa.cdml_bracket.CDMLBracketPropertiesPatch(
		before.revision, "pair_left", (("line_width", 2.0),),
	)
	unchanged = oasa.cdml_bracket.patch_bracket_properties(session, request)
	accepted = oasa.cdml_bracket.patch_bracket_properties(
		session,
		oasa.cdml_bracket.CDMLBracketPropertiesPatch(
			before.revision, "pair_left", (("line_color", "#445566"),),
		),
	)

	assert not unchanged.changed and unchanged.commit is None
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		oasa.cdml_bracket.patch_bracket_properties(session, request)
	assert session.snapshot() == accepted.snapshot


#============================================
@pytest.mark.parametrize("candidate", (
	_PAIRED_CDML.replace('bracket_side="right"', 'bracket_side="left"'),
	_PAIRED_CDML.replace('bracket_pair="pair_left" bracket_side="right"', ''),
	_PAIRED_CDML.replace(
		'<c:polyline id="pair_right"', '<v:polyline id="pair_right"',
	).replace('</c:polyline></c:cdml>', '</v:polyline></c:cdml>', 1),
	_PAIRED_CDML.replace(
		'<c:polyline id="pair_right"', '<c:molecule><c:polyline id="pair_right"',
	).replace('</c:polyline></c:cdml>', '</c:polyline></c:molecule></c:cdml>', 1),
	_PAIRED_CDML.replace('spline="no"', 'spline="yes"', 1),
	_PAIRED_CDML.replace(' spline="no"', '', 1),
))
def test_bracket_properties_rejects_malformed_pair_without_mutation(candidate: str) -> None:
	"""Only a complete direct-core left/right pair is an editable composite."""
	session = oasa.cdml_document.CDMLDocumentSession.load(candidate)
	before = session.snapshot()
	request = oasa.cdml_bracket.CDMLBracketPropertiesPatch(
		before.revision, "pair_left", (("line_color", "#445566"),),
	)

	with pytest.raises(oasa.cdml_bracket.CDMLBracketPropertiesPatchError):
		oasa.cdml_bracket.patch_bracket_properties(session, request)

	assert session.snapshot() == before
