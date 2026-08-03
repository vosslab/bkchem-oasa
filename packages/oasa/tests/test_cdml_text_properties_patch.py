"""Behavioral coverage for backend-owned plain Text property patches."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor"
 version="26.07" v:root="keep"><molecule id="m1"><atom id="a1" name="C">
<point x="1cm" y="1cm"/></atom></molecule><v:before keep="yes"/>
<text id="text1" background-color="#ffffff" v:flag="kept"><point x="3cm"
 y="4cm"><v:point-data keep="yes"/></point><font family="Courier" size="11"
 color="#ABCDEF" v:font-data="kept"/><ftext>old label</ftext><v:text-data keep="yes"/>
</text><v:after keep="yes"/></cdml>
"""


#============================================
def _dom(cdml_text: str) -> object:
	"""Return a hardened DOM for one accepted complete-CDML value."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="compat")
	document = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	return document


#============================================
def _direct_element(document: object, name: str, identifier: str | None = None) -> object:
	"""Return one direct core or extension element by local name and optional ID."""
	for child in document.documentElement.childNodes:
		if child.nodeType != child.ELEMENT_NODE:
			continue
		local_name = child.localName or child.tagName
		if local_name == name and (identifier is None or child.getAttribute("id") == identifier):
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
def _direct_names(document: object) -> tuple[str, ...]:
	"""Return direct root element names in persistent source order."""
	return tuple(
		child.localName or child.tagName for child in document.documentElement.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)


#============================================
def _patch(session: object, changes: tuple[tuple[str, object], ...]) -> object:
	"""Submit one plain Text patch at the public current revision."""
	request = oasa.cdml_document.CDMLTextPropertiesPatch(
		session.revision, "text1", changes,
	)
	result = session.patch_text_properties(request)
	return result


#============================================
def test_real_patch_preserves_unrelated_and_text_owned_opaque_content() -> None:
	"""A plain edit changes only ftext and named font attributes in source order."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		_CDML.replace("#ABCDEF", "#abcdef"),
	)
	before = _dom(session.snapshot().cdml)
	result = _patch(session, (
		("text", "  new label  "), ("font_family", " Helvetica "),
		("font_size", 24), ("font_color", "#A1B2C3"),
	))
	after = _dom(result.snapshot.cdml)
	text = _direct_element(after, "text", "text1")
	font = _direct_child(text, "font")
	observed_edit = {
		"text": _direct_child(text, "ftext").firstChild.data,
		"font": (
			font.getAttribute("family"), font.getAttribute("size"), font.getAttribute("color"),
		),
	}
	preserved = {
		"root_order": _direct_names(after),
		"root_attributes": (
			after.documentElement.getAttribute("version"),
			after.documentElement.getAttribute("v:root"),
		),
		"unrelated": tuple(
			_direct_element(after, name).toxml() == _direct_element(before, name).toxml()
			for name in ("molecule", "before", "after")
		),
		"text_opaque": (
			text.getAttribute("v:flag"), font.getAttribute("v:font-data"),
			_direct_child(text, "point").toxml()
			== _direct_child(_direct_element(before, "text", "text1"), "point").toxml(),
		),
	}

	assert result.changed and observed_edit == {
		"text": "  new label  ", "font": ("Helvetica", "24", "#a1b2c3"),
	}
	assert preserved == {
		"root_order": ("molecule", "before", "text", "after"),
		"root_attributes": ("26.07", "keep"),
		"unrelated": (True, True, True),
		"text_opaque": ("kept", "kept", True),
	}


#============================================
def test_plain_text_replacement_preserves_ftext_comments_and_processing_instructions() -> None:
	"""Plain character replacement retains non-rich persistent ftext nodes."""
	source = _CDML.replace(
		"<ftext>old label</ftext>",
		"<ftext>old<!--keep-comment--><?vendor keep?> label</ftext>",
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	result = _patch(session, (("text", "replacement"),))
	ftext = _direct_child(_direct_element(_dom(result.snapshot.cdml), "text", "text1"), "ftext")
	nodes = tuple(
		(child.nodeType, getattr(child, "data", None), getattr(child, "target", None))
		for child in ftext.childNodes
	)

	assert nodes == (
		(ftext.TEXT_NODE, "replacement", None),
		(ftext.COMMENT_NODE, "keep-comment", None),
		(ftext.PROCESSING_INSTRUCTION_NODE, "keep", "vendor"),
	)


#============================================
def test_plain_comparison_symbols_remain_editable_character_data() -> None:
	"""Literal comparison symbols do not make an ftext value rich markup."""
	source = _CDML.replace("<ftext>old label</ftext>", "<ftext>x &lt; y</ftext>")
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	result = _patch(session, (("text", "a < b"),))
	ftext = _direct_child(_direct_element(_dom(result.snapshot.cdml), "text", "text1"), "ftext")

	assert ftext.firstChild.data == "a < b"


#============================================
def test_missing_font_is_created_before_ftext_without_reordering_other_children() -> None:
	"""An explicit font field creates one core font in the established child position."""
	without_font = _CDML.replace(
		'<font family="Courier" size="11"\n color="#ABCDEF" v:font-data="kept"/>',
		"",
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(without_font)
	result = _patch(session, (("font_size", 18),))
	text = _direct_element(_dom(result.snapshot.cdml), "text", "text1")
	core_names = tuple(
		child.localName for child in text.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.namespaceURI == text.namespaceURI
	)

	assert core_names == ("point", "font", "ftext")
	assert _direct_child(text, "font").getAttribute("size") == "18"


#============================================
def test_semantic_noop_returns_current_snapshot_without_revision() -> None:
	"""Canonical equal values retain the exact snapshot and allocate no commit."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		_CDML.replace("#ABCDEF", "#abcdef"),
	)
	before = session.snapshot()
	result = _patch(session, (
		("text", "old label"), ("font_family", "Courier"),
		("font_size", 11), ("font_color", "#abcdef"),
	))

	assert not result.changed and result.commit is None
	assert result.snapshot == before and session.snapshot() == before


#============================================
@pytest.mark.parametrize("changes", (
	(("text", "   "),),
	(("font_family", ""),),
	(("font_size", 145),),
	(("font_color", "#abc"),),
	(("text", "one"), ("text", "two")),
))
def test_invalid_scalar_intent_is_typed_and_atomic(
		changes: tuple[tuple[str, object], ...],
		) -> None:
	"""Malformed or repeated plain fields cannot change the authoritative snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLTextPropertiesPatchError):
		_patch(session, changes)

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("source", (
	_CDML.replace('id="text1"', 'id="other"'),
	_CDML.replace(
		'<text id="text1"', '<v:wrapper><text id="text1"',
	).replace('</text><v:after', '</text></v:wrapper><v:after'),
	_CDML.replace("<ftext>old label</ftext>", "<ftext>old label</ftext><ftext>again</ftext>"),
	_CDML.replace("<ftext>old label</ftext>", '<font size="9"/><ftext>old label</ftext>'),
	_CDML.replace("<ftext>old label</ftext>", "<ftext><b>old</b> label</ftext>"),
))
def test_missing_nondirect_ambiguous_and_rich_targets_are_typed_atomic_failures(
		source: str,
		) -> None:
	"""Only one direct-root Text with one plain ftext and optional font is editable."""
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLTextPropertiesPatchError):
		_patch(session, (("text", "replacement"),))

	assert session.snapshot() == before


#============================================
def test_escaped_supported_rich_ftext_is_a_typed_atomic_failure() -> None:
	"""Modern escaped supported formatting stays outside the plain-edit contract."""
	source = _CDML.replace(
		"<ftext>old label</ftext>",
		"<ftext>&lt;b&gt;old &lt;i&gt;label&lt;/i&gt;&lt;/b&gt;</ftext>",
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLTextPropertiesPatchError):
		_patch(session, (("text", "replacement"),))

	assert session.snapshot() == before


#============================================
def test_stale_patch_and_public_restore_preserve_exact_history_semantics() -> None:
	"""Revision conflicts are inert and restore returns the exact pre-edit snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	changed = _patch(session, (("text", "replacement"),))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.patch_text_properties(
			oasa.cdml_document.CDMLTextPropertiesPatch(
				before.revision, "text1", (("font_size", 20),),
			),
		)
	restored = session.restore(
		target_revision=before.revision,
		expected_revision=changed.snapshot.revision,
	)

	assert restored.snapshot.cdml == before.cdml
	assert session.snapshot() == restored.snapshot
