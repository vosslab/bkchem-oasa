"""Behavioral coverage for backend-owned plain Plus property patches."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" '
	'version="26.07" v:root="keep"><molecule id="m1"><atom id="a1" name="C">'
	'<point x="1cm" y="1cm"/></atom></molecule><v:before keep="yes"/><!--root keep-->'
	'<?root keep?>'
	'<plus id="plus1" font_size="014" color="#AABBCC" background-color="#DEF" '
	'keep="root" v:flag="yes">'
	'<point x="3cm" y="4cm" keep="point"><v:data keep="yes"/></point><!--plus keep-->'
	'<?plus keep?>'
	'<font family="Courier" size="99" color="#010203" v:font="keep"/>'
	'<v:extra keep="yes"/></plus>'
	'<text id="text1"><point x="5cm" y="6cm"/><ftext>keep</ftext></text>'
	'</cdml>'
)


#============================================
def _dom(cdml_text: str) -> object:
	"""Return a hardened DOM for one accepted complete-CDML value."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="compat")
	return oasa.safe_xml.parse_dom_from_string(accepted.serialize())


#============================================
def _direct_element(document: object, name: str, identifier: str) -> object:
	"""Return one direct element by local name and durable ID."""
	for child in document.documentElement.childNodes:
		if (
			child.nodeType == child.ELEMENT_NODE
			and (child.localName or child.tagName) == name
			and child.getAttribute("id") == identifier
		):
			return child
	raise AssertionError("missing direct element: %s" % name)


#============================================
def _direct_child(element: object, name: str) -> object:
	"""Return one direct child element by local name."""
	for child in element.childNodes:
		if child.nodeType == child.ELEMENT_NODE and (child.localName or child.tagName) == name:
			return child
	raise AssertionError("missing direct child: %s" % name)


#============================================
def _patch(session: object, changes: tuple[tuple[str, object], ...]) -> object:
	"""Submit one plain Plus patch at the public current revision."""
	request = oasa.cdml_document.CDMLPlusPropertiesPatch(
		session.revision, "plus1", changes,
	)
	return session.patch_plus_properties(request)


#============================================
def test_patch_changes_only_root_fields_and_preserves_opaque_content() -> None:
	"""One accepted patch retains source order and every unmentioned value."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = _patch(session, (
		("font_family", "Helvetica"), ("font_size", 24), ("color", "#DDEEFF"),
		("background_color", "#112233"),
	))
	after = _dom(result.snapshot.cdml)
	plus = _direct_element(after, "plus", "plus1")
	point = _direct_child(plus, "point")
	font = _direct_child(plus, "font")
	child_names = tuple(
		child.localName or child.tagName for child in plus.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	observed = {
		"root": (
			plus.getAttribute("font_size"), plus.getAttribute("color"),
			plus.getAttribute("background-color"), plus.getAttribute("keep"),
			plus.getAttribute("v:flag"),
		),
		"children": child_names,
		"point": (point.getAttribute("keep"), _direct_child(point, "data").getAttribute("keep")),
		"font": (
			font.getAttribute("family"), font.getAttribute("size"),
			font.getAttribute("color"), font.getAttribute("v:font"),
		),
		"opaque_nodes": tuple(
			(child.nodeType, child.nodeName, child.data)
			for child in plus.childNodes
			if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE)
		),
		"root_opaque_nodes": tuple(
			(child.nodeType, child.nodeName, child.data)
			for child in after.documentElement.childNodes
			if child.nodeType in (child.COMMENT_NODE, child.PROCESSING_INSTRUCTION_NODE)
		),
	}

	assert result.changed and result.commit is not None
	assert observed == {
		"root": ("24", "#ddeeff", "#112233", "root", "yes"),
		"children": ("point", "font", "extra"),
		"point": ("point", "yes"),
		"font": ("Helvetica", "99", "#010203", "keep"),
		"opaque_nodes": (
			(plus.COMMENT_NODE, "#comment", "plus keep"),
			(plus.PROCESSING_INSTRUCTION_NODE, "plus", "keep"),
		),
		"root_opaque_nodes": (
			(after.COMMENT_NODE, "#comment", "root keep"),
			(after.PROCESSING_INSTRUCTION_NODE, "root", "keep"),
		),
	}


#============================================
def test_semantic_noop_retains_exact_lexical_snapshot() -> None:
	"""Equivalent size and case-normalized color allocate no revision or history."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = _patch(session, (
		("font_family", "Courier"), ("font_size", 14), ("color", "#aabbcc"),
		("background_color", "#ddeeff"),
	))

	assert not result.changed and result.commit is None
	assert result.snapshot == before and session.snapshot() == before


#============================================
def test_absent_root_values_use_historical_visible_defaults_for_noop() -> None:
	"""A missing size and color compare semantically as 14 and black."""
	source = _CDML.replace(
		' font_size="014" color="#AABBCC" background-color="#DEF"', "",
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	result = _patch(session, (
		("font_size", 14), ("color", "#000000"), ("background_color", None),
	))

	assert not result.changed and result.snapshot.cdml == session.snapshot().cdml


#============================================
@pytest.mark.parametrize("changes", (
	(("font_size", True),),
	(("font_size", 145),),
	(("color", "#abc"),),
	(("background_color", "#abc"),),
	(("background_color", "transparent"),),
	(("font_family", "  "),),
	(("font_family", 12),),
	(("color", "#112233"), ("color", "#445566")),
	(("family", "Arial"),),
))
def test_invalid_explicit_intent_is_typed_and_atomic(
		changes: tuple[tuple[str, object], ...],
		) -> None:
	"""Malformed, unsupported, or repeated fields cannot mutate authority."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLPlusPropertiesPatchError):
		_patch(session, changes)

	assert session.snapshot() == before


#============================================
def test_explicit_background_clear_is_persistent_and_unambiguous() -> None:
	"""Clear intent writes explicit transparent content instead of exposing stale color."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = _patch(session, (("background_color", None),))
	plus = _direct_element(_dom(result.snapshot.cdml), "plus", "plus1")

	assert result.changed and plus.hasAttribute("background-color")
	assert plus.getAttribute("background-color") == ""


#============================================
def test_family_patch_creates_one_core_font_and_survives_reload() -> None:
	"""A Plus without a font gains one portable family override through history."""
	source = _CDML.replace(
		'<font family="Courier" size="99" color="#010203" v:font="keep"/>', "",
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	result = _patch(session, (("font_family", "Arial"),))
	font = _direct_child(_direct_element(_dom(result.snapshot.cdml), "plus", "plus1"), "font")
	reloaded = oasa.cdml_document.CDMLDocumentSession.load(result.snapshot.cdml)

	assert result.changed and result.commit is not None
	assert font.getAttribute("family") == "Arial"
	assert reloaded.snapshot().cdml == result.snapshot.cdml


#============================================
def test_presentation_description_resolves_missing_family_from_standard() -> None:
	"""The backend projects effective family separately from authored font data."""
	standard = (
		'<standard font_family="Palatino" font_size="12" line_width="1px" '
		'line_color="#000000" area_color=""><bond width="6px" wedge-width="5px" '
		'double-ratio="0.75"/><atom show_hydrogens="0"/></standard>'
	)
	source = _CDML.replace('<molecule id="m1">', standard + '<molecule id="m1">').replace(
		'<font family="Courier" size="99" color="#010203" v:font="keep"/>',
		'<font size="99" color="#010203" v:font="keep"/>',
	)
	record = next(
		record for record in oasa.cdml_document.CDMLDocumentSession.load(source)
		.projection_snapshot().presentation_description.records
		if record.identifier == "plus1"
	)

	assert record.effective_font_family == "Palatino"
	assert dict(record.font_attributes).get("family") is None


#============================================
@pytest.mark.parametrize("source", (
	_CDML.replace('id="plus1"', 'id="other"'),
	_CDML.replace('<plus id="plus1"', '<arrow id="plus1"').replace('</plus>', '</arrow>'),
	_CDML.replace('<plus id="plus1"', '<v:wrapper><plus id="plus1"').replace(
		'</plus><text', '</plus></v:wrapper><text',
	),
	_CDML.replace(
		'</point><!--plus keep-->',
		'</point><point x="7cm" y="8cm"/><!--plus keep-->',
	),
	_CDML.replace('<v:extra', '<font family="Arial"/><v:extra'),
	_CDML.replace('<font family="Courier"', '<ftext>rich</ftext><font family="Courier"'),
	_CDML.replace('<point x="3cm"', 'visible<point x="3cm"'),
))
def test_nonplain_or_indirect_targets_are_typed_atomic_failures(source: str) -> None:
	"""Ambiguous, rich, nested, or missing Plus targets remain preservation-only."""
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLPlusPropertiesPatchError):
		_patch(session, (("font_size", 20),))

	assert session.snapshot() == before


#============================================
def test_stale_patch_is_inert_and_restore_recovers_exact_predecessor() -> None:
	"""Revision conflicts cannot alter accepted state and restore is exact."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	changed = _patch(session, (("font_size", 20),))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.patch_plus_properties(oasa.cdml_document.CDMLPlusPropertiesPatch(
			before.revision, "plus1", (("color", "#112233"),),
		))
	restored = session.restore(
		target_revision=before.revision,
		expected_revision=changed.snapshot.revision,
	)

	assert restored.snapshot.cdml == before.cdml
	assert session.snapshot() == restored.snapshot
