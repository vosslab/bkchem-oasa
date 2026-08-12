"""Behavioral coverage for backend-owned bounded top-level transforms."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m" z="7"><atom id="a" name="C"><point x="1cm" y="1cm"/><mark type="plus" x="2cm" y="1cm"/><v:keep/></atom><group id="g"><point x="1cm" y="3cm"/></group><bond id="b" start="a" end="g" type="w1"/></molecule>
 <arrow id="ar" z="4"><point x="5cm" y="2cm"/><point x="7cm" y="2cm"/></arrow><text id="tx"><point x="9cm" y="4cm"/><ftext>hello</ftext></text><plus id="pl"><point x="12cm" y="5cm"/></plus>
 <rect id="box" x1="14cm" y1="2cm" x2="16cm" y2="6cm" line_color="#123456"/><polygon id="pg"><point x="18cm" y="1cm"/><point x="20cm" y="1cm"/><point x="19cm" y="3cm"/></polygon><polyline id="ln"><point x="22cm" y="1cm"/><point x="24cm" y="4cm"/></polyline><v:opaque id="opaque" keep="yes"/>
</cdml>
"""


#============================================
def _request(
		session: object, mode: str, roots: tuple[str, ...], *factors: float,
		delta: tuple[float, float] | None = None,
		) -> object:
	"""Build an exact request from the current public session revision."""
	return oasa.cdml_document.CDMLTopLevelTransformRequest(
		session.revision, mode, roots, *factors, delta=delta,
	)


#============================================
def _coordinates(cdml: str, identifier: str) -> tuple[tuple[float, float], ...]:
	"""Read accepted result geometry through the public hardened CDML parser."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for root in dom.documentElement.childNodes:
		if getattr(root, "tagName", None) is None or root.getAttribute("id") != identifier:
			continue
		return tuple(
			(float(element.getAttribute("x").removesuffix("cm")),
				float(element.getAttribute("y").removesuffix("cm")))
			for element in root.getElementsByTagName("*")
			if element.tagName == "point"
			or (
				element.tagName == "mark"
				and element.hasAttribute("x") and element.hasAttribute("y")
			)
		)
	raise AssertionError("accepted CDML did not contain selected root: %s" % identifier)


#============================================
@pytest.mark.parametrize(
	("mode", "roots", "expected"),
	(
		("align-top", ("ar", "tx"), ((5.0, 2.0), (7.0, 2.0))),
		("align-bottom", ("ar", "tx"), ((5.0, 4.0), (7.0, 4.0))),
		("align-left", ("ar", "tx"), ((5.0, 2.0), (7.0, 2.0))),
		("align-right", ("ar", "tx"), ((7.0, 2.0), (9.0, 2.0))),
		("align-center-x", ("ar", "tx"), ((6.5, 2.0), (8.5, 2.0))),
		("align-center-y", ("ar", "tx"), ((5.0, 3.0), (7.0, 3.0))),
	),
)
def test_alignment_uses_persistent_root_bounds(mode: str, roots: tuple[str, ...], expected: tuple) -> None:
	"""Each edge and center family derives placement from backend CDML bounds."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.apply_top_level_transform(_request(session, mode, roots))

	assert result.changed
	assert _coordinates(result.snapshot.cdml, "ar") == expected


#============================================
def test_scale_and_mirrors_preserve_mixed_root_content_and_root_order() -> None:
	"""Affine operations include vertex marks and retain unrelated durable XML."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	scaled = session.apply_top_level_transform(_request(session, "scale", ("m", "ar"), 2.0, 1.0))
	vertical = session.apply_top_level_transform(_request(session, "mirror-vertical", ("m", "ar")))
	horizontal = session.apply_top_level_transform(_request(session, "mirror-horizontal", ("m", "ar")))

	assert scaled.changed and vertical.changed and horizontal.changed
	assert _coordinates(horizontal.snapshot.cdml, "m") == ((10.0, 3.0), (8.0, 3.0), (10.0, 1.0))
	assert 'z="7"' in horizontal.snapshot.cdml and 'type="w1"' in horizontal.snapshot.cdml
	assert 'line_color="#123456"' in horizontal.snapshot.cdml and 'v:opaque id="opaque" keep="yes"' in horizontal.snapshot.cdml


#============================================
def test_scale_transforms_shape_polygon_and_polyline_geometry() -> None:
	"""One mixed selection changes every supported persistent geometry spelling."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.apply_top_level_transform(
		_request(session, "scale", ("ln", "box", "m", "pg", "pl", "tx", "ar"), 2.0, 1.0),
	)

	assert 'x1="15.500cm"' in result.snapshot.cdml and 'x2="19.500cm"' in result.snapshot.cdml
	assert _coordinates(result.snapshot.cdml, "pg") == ((23.5, 1.0), (27.5, 1.0), (25.5, 3.0))
	assert _coordinates(result.snapshot.cdml, "ln") == ((31.5, 1.0), (35.5, 4.0))


#============================================
def test_translation_moves_mixed_persistent_geometry_and_preserves_document_content() -> None:
	"""One point delta moves selected roots without rebuilding persistent CDML."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.apply_top_level_transform(
		_request(
			session, "translate", ("m", "ar", "tx", "pl", "box", "pg", "ln"),
			delta=(72.0, -36.0),
		),
	)

	assert (
		result.changed
		and _coordinates(result.snapshot.cdml, "m") == ((3.54, -0.27), (4.54, -0.27), (3.54, 1.73))
		and _coordinates(result.snapshot.cdml, "ar") == ((7.54, 0.73), (9.54, 0.73))
		and _coordinates(result.snapshot.cdml, "pg") == ((20.54, -0.27), (22.54, -0.27), (21.54, 1.73))
		and _coordinates(result.snapshot.cdml, "ln") == ((24.54, -0.27), (26.54, 2.73))
		and 'x1="16.540cm" y1="0.730cm" x2="18.540cm" y2="4.730cm"' in result.snapshot.cdml
		and 'z="7"' in result.snapshot.cdml
		and 'type="w1"' in result.snapshot.cdml
		and 'v:opaque id="opaque" keep="yes"' in result.snapshot.cdml
	)


#============================================
@pytest.mark.parametrize(("root_id", "path", "expected"), (
	(
		"ar",
		'<arrow id="ar"><point x="1cm" y="1cm"/><point x="2cm" y="2cm"/>'
		'<point x="3cm" y="3cm"/></arrow>',
		((1.0, 8.0), (2.0, 9.0), (3.0, 10.0)),
	),
	(
		"pg",
		'<polygon id="pg"><point x="1cm" y="1cm"/><point x="2cm" y="2cm"/>'
		'<point x="3cm" y="3cm"/><point x="4cm" y="4cm"/></polygon>',
		((1.0, 7.0), (2.0, 8.0), (3.0, 9.0), (4.0, 10.0)),
	),
	(
		"ln",
		'<polyline id="ln"><point x="1cm" y="1cm"/><point x="2cm" y="2cm"/>'
		'<point x="3cm" y="3cm"/></polyline>',
		((1.0, 8.0), (2.0, 9.0), (3.0, 10.0)),
	),
))
def test_paths_at_authored_minimum_or_more_transform_every_direct_point(
		root_id: str, path: str, expected: tuple,
		) -> None:
	"""Valid path records retain each ordered direct point during alignment."""
	cdml = '<cdml version="26.07">%s<plus id="anchor"><point x="0cm" y="10cm"/></plus></cdml>' % path
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	result = session.apply_top_level_transform(_request(session, "align-bottom", (root_id, "anchor")))

	assert result.changed and _coordinates(result.snapshot.cdml, root_id) == expected


#============================================
def test_identity_scale_preserves_lexical_snapshot_and_history_after_revision_check() -> None:
	"""A canonical affine no-op still fences stale callers without rewriting CDML."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML.replace('x="5cm"', 'x="5.000cm"'))
	before = session.snapshot()
	result = session.apply_top_level_transform(_request(session, "scale", ("m", "ar"), 1.0, 1.0))

	assert not result.changed and result.commit is None
	assert session.snapshot() == before


#============================================
def test_zero_translation_preserves_lexical_snapshot_and_history_after_revision_check() -> None:
	"""A numeric zero delta is a stale-checked history-free lexical no-op."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML.replace('x="5cm"', 'x="5.000cm"'))
	before = session.snapshot()
	before_history = dict(session._history)
	result = session.apply_top_level_transform(
		_request(session, "translate", ("m", "ar"), delta=(-0.0, 0.0)),
	)

	assert not result.changed and result.commit is None
	assert session.snapshot() == before and session._history == before_history


#============================================
def test_changed_transform_uses_revision_history_and_dirty_state() -> None:
	"""One accepted transform is one backend revision and supports restore/redo state."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	changed = session.apply_top_level_transform(_request(session, "align-top", ("ar", "tx")))
	restored = session.restore(target_revision=before.revision, expected_revision=changed.snapshot.revision)

	assert changed.snapshot.revision == 1 and changed.snapshot.is_dirty
	assert restored.cdml == before.cdml and not restored.snapshot.is_dirty


#============================================
@pytest.mark.parametrize(
	"request_builder",
	(
		lambda session: _request(session, "align-top", ("ar",)),
		lambda session: _request(session, "scale", ("ar", "tx"), 0.0, 1.0),
		lambda session: _request(session, "mirror-vertical", ("ar", "ar")),
		lambda session: _request(session, "scale", ("missing",), 1.0, 1.0),
		lambda session: _request(session, "scale", ("opaque",), 1.0, 1.0),
		lambda session: _request(session, "scale", ("box",), False, 1.0),
		lambda session: _request(session, "translate", ("ar",)),
		lambda session: _request(session, "translate", ("ar",), delta=(False, 0.0)),
		lambda session: _request(session, "translate", ("ar",), delta=(float("inf"), 0.0)),
		lambda session: _request(session, "translate", ("ar",), 1.0, 1.0, delta=(1.0, 1.0)),
	),
)
def test_invalid_requests_are_typed_atomic_failures(request_builder: object) -> None:
	"""Invalid targets and factors leave the authoritative snapshot untouched."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLTopLevelTransformError):
		session.apply_top_level_transform(request_builder(session))

	assert session.snapshot() == before


#============================================
def test_stale_request_and_invalid_later_geometry_cannot_commit_earlier_root() -> None:
	"""The revision fence and full geometry validation precede detached mutation."""
	malformed = _CDML.replace('x="9cm" y="4cm"', 'x="9cm"')
	session = oasa.cdml_document.CDMLDocumentSession.load(malformed)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLTopLevelTransformError):
		session.apply_top_level_transform(_request(session, "align-top", ("ar", "tx")))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.apply_top_level_transform(
			oasa.cdml_document.CDMLTopLevelTransformRequest(-1, "scale", ("ar",), 1.0, 1.0),
		)

	assert session.snapshot() == before


#============================================
def test_backend_rejects_nonroot_identifier_without_frontend_classification() -> None:
	"""OASA rejects a nested ID without requiring frontend CDML classification."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	request = oasa.cdml_document.CDMLTopLevelTransformRequest(
		session.revision, "mirror-horizontal", ("a",),
	)
	with pytest.raises(oasa.cdml_document.CDMLTopLevelTransformError):
		session.apply_top_level_transform(request)

	assert session.snapshot() == before


#============================================
def test_align_overflow_from_finite_coordinates_is_an_atomic_failure() -> None:
	"""Finite authored coordinates that overflow alignment retain exact session state."""
	cdml = (
		'<cdml version="26.07"><arrow id="left"><point x="-1e308cm" y="0cm"/>'
		'<point x="-1e308cm" y="1cm"/></arrow><arrow id="right">'
		'<point x="1e308cm" y="0cm"/><point x="1e308cm" y="1cm"/>'
		'</arrow></cdml>'
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLTopLevelTransformError):
		session.apply_top_level_transform(_request(session, "align-right", ("left", "right")))

	assert session.snapshot() == before


#============================================
def test_scale_overflow_from_finite_coordinates_is_an_atomic_failure() -> None:
	"""Finite affine overflow rejects before changing the public backend snapshot."""
	cdml = (
		'<cdml version="26.07"><arrow id="left"><point x="-1e308cm" y="0cm"/>'
		'<point x="-1e308cm" y="1cm"/></arrow><arrow id="right">'
		'<point x="1e308cm" y="0cm"/><point x="1e308cm" y="1cm"/>'
		'</arrow></cdml>'
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLTopLevelTransformError):
		session.apply_top_level_transform(_request(session, "scale", ("left", "right"), 2.0, 1.0))

	assert session.snapshot() == before


#============================================
def test_translation_overflow_from_finite_coordinates_is_an_atomic_failure() -> None:
	"""A finite point delta that overflows selected geometry commits nothing."""
	cdml = (
		'<cdml version="26.07"><arrow id="ar"><point x="1.79e308cm" y="0cm"/>'
		'<point x="1.79e308cm" y="1cm"/></arrow></cdml>'
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLTopLevelTransformError):
		session.apply_top_level_transform(
			_request(session, "translate", ("ar",), delta=(1e308, 0.0)),
		)

	assert session.snapshot() == before


#============================================
def test_translation_is_revision_bound_and_uses_backend_history() -> None:
	"""A stale translation rejects while restore returns the retained snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	original = session.snapshot()
	translated = session.apply_top_level_transform(
		_request(session, "translate", ("m", "ar"), delta=(36.0, 0.0)),
	)
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.apply_top_level_transform(
			oasa.cdml_document.CDMLTopLevelTransformRequest(
				original.revision, "translate", ("m", "ar"), delta=(36.0, 0.0),
			),
		)
	restored = session.restore(
		target_revision=original.revision, expected_revision=translated.snapshot.revision,
	)

	assert translated.changed and translated.snapshot.is_dirty
	assert restored.cdml == original.cdml and not restored.snapshot.is_dirty


#============================================
@pytest.mark.parametrize(
	("cdml", "roots"),
	(
		(_CDML.replace('<arrow id="ar" z="4">', '<reaction id="rx"><arrow id="ar" z="4">').replace('</arrow><text id="tx">', '</arrow></reaction><text id="tx">'), ("rx",)),
		(_CDML.replace('<point x="5cm" y="2cm"/><point x="7cm" y="2cm"/>', '<point x="5cm" y="2cm"/>'), ("ar",)),
		(_CDML.replace('<polygon id="pg">', '<fragment><polygon id="pg">').replace('</polygon><polyline', '</polygon></fragment><polyline'), ("pg",)),
	),
)
def test_reaction_nested_and_cardinality_targets_reject_atomically(cdml: str, roots: tuple[str, ...]) -> None:
	"""Only complete direct-root supported geometry participates in transforms."""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLTopLevelTransformError):
		session.apply_top_level_transform(_request(session, "scale", roots, 1.0, 1.0))

	assert session.snapshot() == before
