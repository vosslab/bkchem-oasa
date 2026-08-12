"""Behavioral coverage for backend-owned geometric presentation insertion."""

# Standard Library
import fractions
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.cdml_presentation_insert
import oasa.cdml_writer
import oasa.safe_xml


_CDML = (
	'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml" '
	'xmlns:v="urn:vendor" version="26.07"><c:standard line_width="2.5px" '
	'font_size="12" font_family="Helvetica" line_color="#123456" '
	'area_color="#ddeeff"><c:bond width="6px" wedge-width="5px" '
	'double-ratio="0.75"/><c:atom show_hydrogens="0"/></c:standard>'
	'<!--keep--><v:note keep="yes"/></c:cdml>'
)

_STACK_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" '
	'xmlns:x="urn:opaque" version="0.15"><info/><paper type="A4"/>'
	'<viewport><transform/></viewport><molecule id="mol-1"><atom id="atom-1" '
	'name="C"><point x="1cm" y="1cm"/></atom></molecule><arrow id="arrow-1">'
	'<point x="1cm" y="1cm"/><point x="2cm" y="1cm"/></arrow><!--preserve-->'
	'<?keep value?><plus id="plus-1"><point x="3cm" y="1cm"/></plus>'
	'<plus><point x="3.5cm" y="1cm"/></plus><x:external keep="yes"/>'
	'<text id="text-1"><point x="4cm" y="1cm"/><font/><ftext>note</ftext>'
	'</text></cdml>'
)


#============================================
def _insert(
		session: oasa.cdml_document.CDMLDocumentSession, kind: str,
		points: tuple[tuple[float, float], ...] = ((40.0, 30.0), (10.0, 60.0)),
		) -> oasa.cdml_presentation_insert.CDMLPresentationInsertResult:
	"""Insert one geometric root through the public OASA operation."""
	return oasa.cdml_presentation_insert.insert_geometric(
		session,
		oasa.cdml_presentation_insert.CDMLGeometricInsertRequest(
			session.revision, kind, points,
		),
	)


#============================================
def _coordinates(element: object) -> tuple:
	"""Return scene coordinates from one accepted geometric root."""
	if element.localName in {"arrow", "polygon", "polyline"}:
		return tuple(
			tuple(
				float(point.getAttribute(axis).removesuffix("cm"))
				* oasa.cdml_writer.POINTS_PER_CM
				for axis in ("x", "y")
			)
			for point in element.childNodes
			if point.nodeType == point.ELEMENT_NODE and point.localName == "point"
		)
	return tuple(
		float(element.getAttribute(name).removesuffix("cm"))
		* oasa.cdml_writer.POINTS_PER_CM
		for name in ("x1", "y1", "x2", "y2")
	)


#============================================
def _assert_coordinates(actual: tuple, expected: tuple) -> None:
	"""Assert centimetre-rounded CDML geometry preserves each scene value."""
	for actual_value, expected_value in zip(actual, expected):
		actual_values = actual_value if isinstance(actual_value, tuple) else (actual_value,)
		expected_values = (
			expected_value if isinstance(expected_value, tuple) else (expected_value,)
		)
		for value, target in zip(actual_values, expected_values):
			assert math.isclose(value, target, abs_tol=0.02)


#============================================
@pytest.mark.parametrize(("kind", "expected"), (
	("rect", (10.0, 30.0, 40.0, 60.0)),
	("oval", (10.0, 30.0, 40.0, 60.0)),
	("square", (10.0, 30.0, 40.0, 60.0)),
	("circle", (10.0, 30.0, 40.0, 60.0)),
	("polyline", ((40.0, 30.0), (10.0, 60.0))),
))
def test_insert_geometric_uses_standard_and_preserves_document(
		kind: str, expected: tuple,
		) -> None:
	"""Every supported kind shares standard, identity, and preservation rules."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = _insert(session, kind)
	document = oasa.safe_xml.parse_dom_from_string(result.snapshot.cdml)
	elements = tuple(
		child for child in document.documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	presentation = elements[-1]
	actual = _coordinates(presentation)

	assert result.changed and result.commit.snapshot == result.snapshot
	assert result.presentation_ids == (presentation.getAttribute("id"),)
	assert tuple(result.commit.id_map.values()) == result.presentation_ids
	assert "__bkchem_new__" not in result.snapshot.cdml
	assert tuple(element.localName for element in elements) == (
		"standard", "note", kind,
	)
	assert elements[1].namespaceURI == "urn:vendor"
	assert presentation.getAttribute("line_color") == "#123456"
	assert presentation.getAttribute("width") == "2.5"
	assert presentation.getAttribute("area_color") == (
		"" if kind == "polyline" else "#ddeeff"
	)
	assert presentation.getAttribute("spline") == (
		"no" if kind == "polyline" else ""
	)
	_assert_coordinates(actual, expected)
	comments = tuple(
		child.data for child in document.documentElement.childNodes
		if child.nodeType == child.COMMENT_NODE
	)
	assert comments == ("keep",)
	assert session.restore(
		target_revision=before.revision,
		expected_revision=result.snapshot.revision,
	).snapshot.cdml == before.cdml


#============================================
@pytest.mark.parametrize(("kind", "points"), (
	("unknown", ((0.0, 0.0), (10.0, 10.0))),
	("rect", ((0.0, 0.0), (math.nan, 10.0))),
	("rect", ((False, 0.0), (10.0, 10.0))),
	("rect", ((0.0, 0.0), (0.0, 0.0))),
	("rect", ([0.0, 0.0], (10.0, 10.0))),
	("polygon", ((0.0, 0.0), (10.0, 10.0))),
))
def test_invalid_geometric_insert_is_typed_and_atomic(
		kind: str, points: object,
		) -> None:
	"""Malformed kind or geometry cannot allocate identity or document history."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	request = oasa.cdml_presentation_insert.CDMLGeometricInsertRequest(
		before.revision, kind, points,
	)

	with pytest.raises(oasa.cdml_presentation_insert.CDMLPresentationInsertError):
		oasa.cdml_presentation_insert.insert_geometric(session, request)

	assert session.snapshot() == before


#============================================
def test_stale_geometric_insert_cannot_mutate_current_revision() -> None:
	"""A geometric intent remains bound to the revision that supplied defaults."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	stale = oasa.cdml_presentation_insert.CDMLGeometricInsertRequest(
		session.revision, "oval", ((0.0, 0.0), (10.0, 20.0)),
	)
	accepted = _insert(session, "rect")

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		oasa.cdml_presentation_insert.insert_geometric(session, stale)

	assert session.snapshot() == accepted.snapshot


#============================================
def test_symbol_text_arrow_and_wavy_share_one_insertion_contract() -> None:
	"""All drawing roots inherit one standard, identity, and preservation policy."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	arrow = oasa.cdml_presentation_insert.insert_arrow(
		session,
		oasa.cdml_presentation_insert.CDMLArrowInsertRequest(
			session.revision, "normal", False, ((0.0, 0.0), (24.0, 0.0)),
		),
	)
	text = oasa.cdml_presentation_insert.insert_text(
		session,
		oasa.cdml_presentation_insert.CDMLTextInsertRequest(
			session.revision, (12.0, 18.0), "A & B",
		),
	)
	plus = oasa.cdml_presentation_insert.insert_plus(
		session,
		oasa.cdml_presentation_insert.CDMLPlusInsertRequest(
			session.revision, (30.0, 40.0),
		),
	)
	wavy = oasa.cdml_presentation_insert.insert_wavy(
		session,
		oasa.cdml_presentation_insert.CDMLWavyInsertRequest(
			session.revision, (0.0, 50.0), (36.0, 50.0),
		),
	)
	document = oasa.safe_xml.parse_dom_from_string(session.snapshot().cdml)
	elements = tuple(
		child for child in document.documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	arrow_element, text_element, plus_element, wavy_element = elements[-4:]
	font = next(
		child for child in text_element.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.localName == "font"
	)
	ftext = next(
		child for child in text_element.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.localName == "ftext"
	)

	assert tuple(element.localName for element in elements[-4:]) == (
		"arrow", "text", "plus", "polyline",
	)
	assert (
		arrow.presentation_ids[0], text.presentation_ids[0],
		plus.presentation_ids[0], wavy.presentation_ids[0],
	) == tuple(element.getAttribute("id") for element in elements[-4:])
	assert len(set(element.getAttribute("id") for element in elements[-4:])) == 4
	assert (
		arrow_element.getAttribute("width"), arrow_element.getAttribute("color"),
		arrow_element.getAttribute("start"), arrow_element.getAttribute("end"),
	) == ("2.5", "#123456", "no", "yes")
	assert (
		font.getAttribute("family"), font.getAttribute("size"),
		font.getAttribute("color"), text_element.getAttribute("background-color"),
	) == ("Helvetica", "12", "#123456", "#ddeeff")
	assert ftext.firstChild.data == "A & B"
	assert (
		plus_element.getAttribute("font_size"), plus_element.getAttribute("color"),
		plus_element.getAttribute("background-color"),
	) == ("18", "#123456", "#ddeeff")
	assert (
		wavy_element.getAttribute("line_color"), wavy_element.getAttribute("width"),
		wavy_element.getAttribute("spline"), wavy_element.getAttribute("style"),
	) == ("#123456", "2.5", "no", "wavy")
	assert "<v:note keep=\"yes\"/>" in session.snapshot().cdml


#============================================
@pytest.mark.parametrize(("inserter", "insert_request"), (
	(
		oasa.cdml_presentation_insert.insert_arrow,
		oasa.cdml_presentation_insert.CDMLArrowInsertRequest(
			0, "normal", False, ((1.0, 1.0), (1.0, 1.0)),
		),
	),
	(
		oasa.cdml_presentation_insert.insert_text,
		oasa.cdml_presentation_insert.CDMLTextInsertRequest(
			0, (1.0, 1.0), " untrimmed",
		),
	),
	(
		oasa.cdml_presentation_insert.insert_plus,
		oasa.cdml_presentation_insert.CDMLPlusInsertRequest(
			0, (math.nan, 1.0),
		),
	),
	(
		oasa.cdml_presentation_insert.insert_wavy,
		oasa.cdml_presentation_insert.CDMLWavyInsertRequest(
			0, (1.0, 1.0), (1.0, 1.0),
		),
	),
))
def test_invalid_drawing_root_insertion_is_atomic(
		inserter: object, insert_request: object,
		) -> None:
	"""Each drawing-root request rejects before identity, history, or XML changes."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_presentation_insert.CDMLPresentationInsertError):
		inserter(session, insert_request)

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize(("kind", "expected_bounds"), (
	("square", (0.0, 0.0, 30.0, 30.0)),
	("circle", (0.0, 0.0, 30.0, 30.0)),
))
def test_constrained_shapes_use_a_canonical_square_bounds_grammar(
		kind: str, expected_bounds: tuple[float, float, float, float],
		) -> None:
	"""Square-derived shapes keep equal durable dimensions after unequal drags."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = _insert(session, kind, ((0.0, 0.0), (30.0, 12.0)))
	document = oasa.safe_xml.parse_dom_from_string(result.snapshot.cdml)
	presentation = tuple(
		child for child in document.documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)[-1]

	_assert_coordinates(_coordinates(presentation), expected_bounds)


#============================================
def test_path_grammar_preserves_order_and_uses_implicit_polygon_closure() -> None:
	"""Open polylines and closed polygons retain each authored vertex exactly once."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	polyline_points = ((0.0, 0.0), (12.0, 8.0), (24.0, 0.0))
	polygon_points = ((0.0, 0.0), (18.0, 0.0), (9.0, 15.0))
	polyline = _insert(session, "polyline", polyline_points)
	polygon = _insert(session, "polygon", polygon_points)
	document = oasa.safe_xml.parse_dom_from_string(polygon.snapshot.cdml)
	elements = tuple(
		child for child in document.documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	polyline_element, polygon_element = elements[-2:]

	assert polyline.presentation_ids[0] == polyline_element.getAttribute("id")
	assert polygon.presentation_ids[0] == polygon_element.getAttribute("id")
	_assert_coordinates(_coordinates(polyline_element), polyline_points)
	_assert_coordinates(_coordinates(polygon_element), polygon_points)
	assert polygon_element.getAttribute("area_color") == "#ddeeff"
	assert polygon_element.getAttribute("spline") == ""


#============================================
@pytest.mark.parametrize("insertion_request", (
	oasa.cdml_presentation_insert.CDMLGeometricInsertRequest(
		0, "polyline", ((0.0, 0.0), (0.0, 0.0)),
	),
	oasa.cdml_presentation_insert.CDMLGeometricInsertRequest(
		0, "polygon", ((0.0, 0.0), (12.0, 0.0), (0.0, 0.0)),
	),
	oasa.cdml_presentation_insert.CDMLGeometricInsertRequest(
		0, "polygon", [(0.0, 0.0), (12.0, 0.0), (6.0, 12.0)],
	),
))
def test_invalid_path_grammar_is_atomic(
		insertion_request: oasa.cdml_presentation_insert.CDMLGeometricInsertRequest,
		) -> None:
	"""Zero segments, explicit duplicate closure, and mutable paths are inert."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_presentation_insert.CDMLPresentationInsertError):
		oasa.cdml_presentation_insert.insert_geometric(session, insertion_request)

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("kind", (
	"normal", "electron", "retro", "equilibrium", "equilibrium2",
))
def test_arrow_kind_and_spline_are_authoritative_persistent_semantics(
		kind: str,
		) -> None:
	"""Every declared Arrow choice maps to a stable typed CDML representation."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = oasa.cdml_presentation_insert.insert_arrow(
		session,
		oasa.cdml_presentation_insert.CDMLArrowInsertRequest(
			session.revision, kind, True, ((0.0, 0.0), (24.0, 0.0)),
		),
	)
	document = oasa.safe_xml.parse_dom_from_string(result.snapshot.cdml)
	arrow = tuple(
		child for child in document.documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)[-1]

	assert arrow.getAttribute("type") == kind
	assert arrow.getAttribute("spline") == "yes"
	assert (
		arrow.getAttribute("start"), arrow.getAttribute("end"),
		arrow.getAttribute("shape"), arrow.getAttribute("width"),
	) == ("no", "yes", "(8,10,3)", "2.5")
	_assert_coordinates(_coordinates(arrow), ((0.0, 0.0), (24.0, 0.0)))


#============================================
@pytest.mark.parametrize("insertion_request", (
	oasa.cdml_presentation_insert.CDMLArrowInsertRequest(
		0, "unsupported", False, ((0.0, 0.0), (24.0, 0.0)),
	),
	oasa.cdml_presentation_insert.CDMLArrowInsertRequest(
		0, "normal", 1, ((0.0, 0.0), (24.0, 0.0)),
	),
	oasa.cdml_presentation_insert.CDMLArrowInsertRequest(
		0, "normal", False, ((0.0, 0.0), (0.0, 0.0)),
	),
))
def test_invalid_arrow_grammar_is_atomic(
		insertion_request: oasa.cdml_presentation_insert.CDMLArrowInsertRequest,
		) -> None:
	"""Unsupported Arrow intent cannot allocate an ID or write document history."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_presentation_insert.CDMLPresentationInsertError):
		oasa.cdml_presentation_insert.insert_arrow(session, insertion_request)

	assert session.snapshot() == before


#============================================
def test_wavy_points_retain_endpoints_and_alternate_on_drag_normal() -> None:
	"""Backend Wavy geometry retains endpoints and deterministic zigzag shape."""
	points = oasa.cdml_presentation_insert.wavy_points((0, 0), (24, 0))

	assert (points[0], points[1], points[-1]) == (
		(0.0, 0.0), (12.0, 4.0), (24.0, 0.0),
	)


#============================================
def test_wavy_points_zero_length_is_an_interaction_no_op() -> None:
	"""An unchanged finite preview gesture creates no geometry."""
	assert oasa.cdml_presentation_insert.wavy_points((2, 3), (2, 3)) == ()


#============================================
@pytest.mark.parametrize(("start", "end"), (
	((0, 0), (float("nan"), 0)),
	((0, 0), (True, 0)),
	((0, 0), [1, 2]),
	((0, 0), (fractions.Fraction(10 ** 1000), 0)),
	((-1e308, 0), (1e308, 0)),
	((0, 0), (49159, 0)),
))
def test_wavy_points_reject_invalid_or_unbounded_geometry(
		start: object, end: object,
		) -> None:
	"""Malformed, nonfinite, extreme, and oversized geometry is rejected."""
	with pytest.raises(oasa.cdml_presentation_insert.CDMLPresentationInsertError):
		oasa.cdml_presentation_insert.wavy_points(start, end)


#============================================
def _root_node_slots(cdml: str) -> tuple[str, ...]:
	"""Return compact root node slots after hardened complete-CDML acceptance."""
	document = oasa.safe_xml.parse_dom_from_string(cdml)
	return tuple(
		"comment" if child.nodeType == child.COMMENT_NODE else
		"pi" if child.nodeType == child.PROCESSING_INSTRUCTION_NODE else
		(child.localName or child.tagName)
		for child in document.documentElement.childNodes
	)


#============================================
def test_reorder_preserves_root_records_and_non_element_slots() -> None:
	"""Backend stack order retains opaque roots and comment/PI node slots."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_STACK_CDML)
	before = session.snapshot()
	result = oasa.cdml_presentation_insert.reorder_presentations(
		session,
		oasa.cdml_presentation_insert.CDMLPresentationReorderRequest(
			before.revision, "bring-to-front", ("text-1", "arrow-1"),
		),
	)
	after = result.snapshot.cdml
	before_slots = _root_node_slots(before.cdml)
	after_slots = _root_node_slots(after)

	assert result.changed and result.commit is not None
	assert after.index('id="arrow-1"') < after.index('id="text-1"')
	assert after.index('id="mol-1"') < after.index("x:external") < after.index('id="arrow-1"')
	assert (after_slots.index("comment"), after_slots.index("pi")) == (
		before_slots.index("comment"), before_slots.index("pi"),
	)
	comment_index = after_slots.index("comment")
	assert after_slots[comment_index - 1:comment_index + 3] == (
		"plus", "comment", "pi", "plus",
	)


#============================================
@pytest.mark.parametrize("root_ids", (("atom-1",), ("",), ("missing",)))
def test_reorder_rejects_non_presentation_or_invalid_roots(
		root_ids: tuple[str, ...],
		) -> None:
	"""Only exact direct durable presentation roots can enter stack order."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_STACK_CDML)
	before = session.snapshot()
	request = oasa.cdml_presentation_insert.CDMLPresentationReorderRequest(
		before.revision, "send-back", root_ids,
	)

	with pytest.raises(oasa.cdml_presentation_insert.CDMLPresentationInsertError):
		oasa.cdml_presentation_insert.reorder_presentations(session, request)

	assert session.snapshot() == before


#============================================
def test_reorder_semantic_noop_is_history_free() -> None:
	"""An already-front request returns the unchanged authoritative snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_STACK_CDML)
	first = oasa.cdml_presentation_insert.reorder_presentations(
		session,
		oasa.cdml_presentation_insert.CDMLPresentationReorderRequest(
			session.revision, "bring-to-front", ("arrow-1", "text-1"),
		),
	)
	before_noop = session.snapshot()
	no_op = oasa.cdml_presentation_insert.reorder_presentations(
		session,
		oasa.cdml_presentation_insert.CDMLPresentationReorderRequest(
			session.revision, "bring-to-front", ("text-1", "arrow-1"),
		),
	)

	assert first.changed and first.commit is not None
	assert not no_op.changed and no_op.commit is None
	assert no_op.snapshot == before_noop and session.snapshot() == before_noop
