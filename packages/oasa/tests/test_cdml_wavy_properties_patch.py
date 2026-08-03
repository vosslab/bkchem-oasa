"""Behavioral coverage for backend-owned plain Wavy property patches."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = (
	'<cdml version="26.07"><text id="before"><ftext>keep</ftext></text><!--root-->'
	'<?root keep?><polyline id="w1" style="wavy" width="01.50" '
	'color="#AABBCC" spline="no" keep="yes"><point x="1cm" y="1cm"/>'
	'<!--keep--><?wavy keep?><point x="2cm" y="2cm" z="0cm"/>'
	'<v:extra xmlns:v="urn:v" flag="keep"><v:child>opaque</v:child></v:extra>'
	'</polyline><plus id="after"><point x="3cm" y="3cm"/></plus></cdml>'
)


#============================================
def _patch(session: object, changes: tuple[tuple[str, object], ...]) -> object:
	"""Submit one Wavy patch at the public current revision."""
	return session.patch_wavy_properties(oasa.cdml_document.CDMLWavyPropertiesPatch(
		session.revision, "w1", changes,
	))


#============================================
def _wavy_semantics(cdml: str) -> tuple[object, ...]:
	"""Return preservation facts without comparing serialized XML bytes."""
	document = oasa.cdml_document.CDMLDocument.parse(cdml, validation="compat")
	root = oasa.safe_xml.parse_dom_from_string(document.serialize()).documentElement
	wavy = next(child for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.getAttribute("id") == "w1")
	points = tuple(
		(point.getAttribute("x"), point.getAttribute("y"), point.getAttribute("z"))
		for point in wavy.childNodes
		if point.nodeType == point.ELEMENT_NODE and point.localName == "point"
	)
	extension = next(child for child in wavy.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.namespaceURI == "urn:v")
	root_order = tuple(
		(child.localName, child.getAttribute("id")) for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	child_order = tuple(
		("element", child.localName) if child.nodeType == child.ELEMENT_NODE else
		("comment", child.data) if child.nodeType == child.COMMENT_NODE else
		("pi", child.target, child.data) for child in wavy.childNodes
		if child.nodeType in (child.ELEMENT_NODE, child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE)
	)
	return (
		points, wavy.getAttribute("spline"), wavy.getAttribute("keep"),
		wavy.getAttribute("color"), child_order, extension.getAttribute("flag"),
		extension.firstChild.localName, extension.firstChild.firstChild.data, root_order,
	)


#============================================
def test_patch_changes_visible_root_fields_and_preserves_wavy_content() -> None:
	"""An accepted Wavy patch retains geometry, legacy color, and opaque content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = _wavy_semantics(session.snapshot().cdml)
	result = _patch(session, (("width", 2.5), ("line_color", "#DDEEFF")))
	after = _wavy_semantics(result.snapshot.cdml)
	document = oasa.safe_xml.parse_dom_from_string(result.snapshot.cdml)
	wavy = next(child for child in document.documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.getAttribute("id") == "w1")

	assert result.changed and result.commit is not None
	assert after == before and (wavy.getAttribute("width"), wavy.getAttribute("line_color")) == ("2.5", "#ddeeff")


#============================================
def test_semantic_noop_preserves_lexical_snapshot() -> None:
	"""Equivalent lexical values allocate no history or replacement snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = _patch(session, (("width", 1.5), ("line_color", "#aabbcc")))

	assert not result.changed and result.commit is None
	assert result.snapshot == before


#============================================
def test_missing_visible_defaults_are_a_history_free_semantic_noop() -> None:
	"""Absent Wavy width and colors retain their historical visible defaults."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<cdml version="26.07"><polyline id="w1" style="wavy"><point x="1cm" '
		'y="1cm"/><point x="2cm" y="2cm"/></polyline></cdml>',
	)
	before = session.snapshot()
	result = _patch(session, (("width", 1.0), ("line_color", "#000000")))

	assert not result.changed and result.commit is None
	assert result.snapshot == before


#============================================
@pytest.mark.parametrize("changes", (
	(("width", True),),
	(("width", float("inf")),),
	(("width", 20.1),),
	(("line_color", "#abc"),),
	(("width", 2.0), ("width", 3.0)),
))
def test_invalid_explicit_intent_is_typed_and_atomic(
		changes: tuple[tuple[str, object], ...],
		) -> None:
	"""Invalid Wavy scalar intent cannot mutate the authoritative snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLWavyPropertiesPatchError):
		_patch(session, changes)

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("source", (
	_CDML.replace('id="w1"', 'id="other"'),
	_CDML.replace('style="wavy"', 'style="normal"'),
	_CDML.replace('<polyline id="w1"', '<v:wrap xmlns:v="urn:v"><polyline id="w1"').replace(
		'</polyline><plus', '</polyline></v:wrap><plus',
	),
	_CDML.replace('<point x="2cm" y="2cm" z="0cm"/>', ''),
	_CDML.replace('<point x="2cm" y="2cm" z="0cm"/>', '<point x="2cm"/>'),
	_CDML.replace('<!--keep-->', 'visible'),
	_CDML.replace('<v:extra', '<font/><v:extra'),
	_CDML.replace('<point x="2cm" y="2cm" z="0cm"/>', '<point x="2cm" y="2cm"><point x="3cm" y="3cm"/></point>'),
	_CDML.replace('z="0cm"', 'z="NaN"'),
))
def test_invalid_or_indirect_targets_are_typed_atomic_failures(source: str) -> None:
	"""Wavy target ambiguity and unsupported roots never partially commit."""
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLWavyPropertiesPatchError):
		_patch(session, (("width", 2.0),))

	assert session.snapshot() == before


#============================================
def test_duplicate_direct_wavy_identity_is_rejected_at_document_load() -> None:
	"""A duplicate durable Wavy ID cannot enter an authoritative session."""
	source = _CDML.replace('<plus id="after">', '<polyline id="w1" style="wavy">'
		'<point x="3cm" y="3cm"/><point x="4cm" y="4cm"/></polyline><plus id="after">')
	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		oasa.cdml_document.CDMLDocumentSession.load(source)


#============================================
def test_history_restores_wavy_predecessor_and_successor_semantically() -> None:
	"""Backend history returns both accepted Wavy states without semantic loss."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = _wavy_semantics(session.snapshot().cdml)
	changed = _patch(session, (("width", 3.0),))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.patch_wavy_properties(oasa.cdml_document.CDMLWavyPropertiesPatch(
			0, "w1", (("width", 4.0),),
		))
	restored = session.restore(
		target_revision=0,
		expected_revision=changed.snapshot.revision,
	)
	successor = session.restore(
		target_revision=changed.snapshot.revision,
		expected_revision=restored.snapshot.revision,
	)

	assert _wavy_semantics(restored.snapshot.cdml) == before
	assert _wavy_semantics(successor.snapshot.cdml) == _wavy_semantics(changed.snapshot.cdml)
