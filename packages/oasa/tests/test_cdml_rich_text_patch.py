"""Behavioral coverage for backend-owned CDML 26.07 rich Text patches."""

# PIP3 modules
from lxml import etree
import pytest

# local repo modules
import oasa.cdml_document
import oasa.cdml_ftext


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor"
 version="26.07" v:root="keep"><v:before/><text id="text1" v:flag="keep">
<point x="3cm" y="4cm"/><font family="Courier"/><ftext>&lt;b&gt;old&lt;/b&gt;</ftext>
<v:after/></text><!--root--><?vendor keep?><v:tail/></cdml>
"""


#============================================
def _runs(*values: tuple[str, tuple[str, ...]]) -> tuple[oasa.cdml_ftext.CDMLFTextRun, ...]:
	"""Build exact immutable public rich-text run values."""
	return tuple(oasa.cdml_ftext.CDMLFTextRun(text, styles) for text, styles in values)


#============================================
def _patch(
		session: object, runs: tuple[oasa.cdml_ftext.CDMLFTextRun, ...],
		changes: tuple[tuple[str, object], ...] = (),
		) -> object:
	"""Submit one public rich-text patch at the current revision."""
	return session.patch_rich_text(
		oasa.cdml_document.CDMLRichTextPatch(session.revision, "text1", runs, changes),
	)


#============================================
def _text_state(cdml: str) -> tuple[str, dict[str, str]]:
	"""Read authored ftext and root-font attributes through hardened lxml."""
	parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
	root = etree.fromstring(cdml.encode("utf-8"), parser)
	namespace = "{http://www.freesoftware.fsf.org/bkchem/cdml}"
	text = root.find(namespace + "text")
	if text is None:
		raise AssertionError("missing rich Text root")
	ftext = text.find(namespace + "ftext")
	if ftext is None or ftext.text is None:
		raise AssertionError("missing rich ftext")
	font = text.find(namespace + "font")
	return ftext.text, dict(font.attrib) if font is not None else {}


#============================================
def test_codec_normalizes_nested_formatting_and_literal_metacharacters() -> None:
	"""Nested supported markup and literal text round-trip through public runs."""
	runs = _runs(("H", ("b",)), ("2", ("sub", "b")), ("O", ("b",)), (" <>&", ()))
	encoded = oasa.cdml_ftext.encode(runs)

	assert oasa.cdml_ftext.decode(encoded) == _runs(
		("H", ("b",)), ("2", ("b", "sub")), ("O", ("b",)), (" <>&", ()),
	)


#============================================
@pytest.mark.parametrize("runs", (
	_runs(("a", ("b", "b")),),
	_runs(("a", ("sub", "sup")),),
))
def test_invalid_style_combinations_are_typed(
		runs: tuple[oasa.cdml_ftext.CDMLFTextRun, ...],
		) -> None:
	"""Duplicate styles and simultaneous baseline shifts have no codec meaning."""
	with pytest.raises(oasa.cdml_ftext.CDMLFTextCodecError):
		oasa.cdml_ftext.normalize(runs)


#============================================
@pytest.mark.parametrize("authored", (
	"<u>x</u>", "<b class=\"x\">x</b>", "<x:b xmlns:x=\"urn:x\">x</x:b>",
	"<b><!--x--></b>", "<b><?x y?></b>", "<!DOCTYPE x><b>x</b>", "&custom;",
	"<b>x",
))
def test_unsupported_or_malformed_authored_markup_is_typed(authored: str) -> None:
	"""The codec accepts only the small CDML 26.07 formatted-text grammar."""
	with pytest.raises(oasa.cdml_ftext.CDMLFTextCodecError):
		oasa.cdml_ftext.decode(authored)


#============================================
def test_patch_writes_canonical_escaped_cdml_and_preserves_root_content() -> None:
	"""One accepted run update changes ftext while opaque root state remains owned."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	expected = _runs(("H", ("b",)), ("2", ("b", "sub")), ("O <>&", ()))
	result = _patch(session, expected)
	authored, _font = _text_state(result.snapshot.cdml)

	assert oasa.cdml_ftext.decode(authored) == expected
	assert all(token in result.snapshot.cdml for token in (
		"v:root=\"keep\"", "<!--root-->", "<?vendor keep?>", "v:tail",
	))


#============================================
@pytest.mark.parametrize("source", (
	_CDML.replace("&lt;b&gt;old&lt;/b&gt;", "<b>old</b>"),
	_CDML.replace("&lt;b&gt;old&lt;/b&gt;", "old<!--preserve-->"),
	_CDML.replace("&lt;b&gt;old&lt;/b&gt;", "old<?vendor keep?>"),
	_CDML.replace("<ftext>", '<ftext v:preserve="yes">'),
	_CDML.replace("</ftext>", "</ftext><ftext>again</ftext>"),
	_CDML.replace("<point x=\"3cm\" y=\"4cm\"/>", ""),
	_CDML.replace("<font family=\"Courier\"/>", "<font/><font/>"),
))
def test_ineligible_target_grammar_is_typed_and_atomic(source: str) -> None:
	"""Legacy markup and ambiguous direct children remain preservation-only content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLRichTextPatchError):
		_patch(session, _runs(("new", ("i",)),))

	assert session.snapshot() == before


#============================================
def test_stale_request_wins_over_invalid_payload_without_mutation() -> None:
	"""A stale rich request is rejected before its target or runs are inspected."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	accepted = _patch(session, _runs(("new", ("i",)),))
	stale = oasa.cdml_document.CDMLRichTextPatch(0, "missing", ())
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.patch_rich_text(stale)

	assert session.snapshot() == accepted.snapshot


#============================================
def test_duplicate_direct_root_text_id_cannot_enter_authoritative_session() -> None:
	"""A target ID identifies exactly one direct-root core Text record."""
	duplicate_text = '<text id="text1"><point x="5cm" y="6cm"/><ftext>other</ftext></text>'
	source = _CDML.replace("</text>", "</text>" + duplicate_text, 1)

	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		oasa.cdml_document.CDMLDocumentSession.load(source)


#============================================
def test_blank_request_and_malformed_current_authored_value_are_atomic() -> None:
	"""A rich edit requires visible content and decodable current authored markup."""
	for source, runs in (
		(_CDML, _runs(("   ", ()),)),
		(_CDML.replace("&lt;b&gt;old&lt;/b&gt;", "<u>old</u>"), _runs(("new", ()),)),
	):
		session = oasa.cdml_document.CDMLDocumentSession.load(source)
		before = session.snapshot()
		with pytest.raises(oasa.cdml_document.CDMLRichTextPatchError):
			_patch(session, runs)

		assert session.snapshot() == before


#============================================
def test_semantic_noop_and_restore_preserve_saved_baseline() -> None:
	"""Canonical equal runs are history-free; restore returns the saved content dirty state."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	saved = session.mark_saved(expected_revision=session.revision)
	noop = _patch(session, _runs(("old", ("b",)),))
	changed = _patch(session, _runs(("new", ("sup",)),))
	restored = session.restore(
		target_revision=saved.revision,
		expected_revision=changed.snapshot.revision,
	)
	authored, _font = _text_state(restored.snapshot.cdml)

	assert not noop.changed and noop.snapshot == saved
	assert not restored.snapshot.is_dirty and authored == "<b>old</b>"


#============================================
def test_root_font_changes_create_only_the_named_attributes() -> None:
	"""One accepted rich patch creates a missing font without inventing its siblings."""
	source = _CDML.replace('<font family="Courier"/>', "")
	session = oasa.cdml_document.CDMLDocumentSession.load(source)
	result = _patch(
		session, _runs(("H", ("b",)), ("2", ("sub",))),
		(("font_size", 18), ("font_color", "#AABBCC")),
	)
	_authored, font = _text_state(result.snapshot.cdml)

	assert font == {"size": "18", "color": "#aabbcc"}


#============================================
def test_canonical_requested_font_value_is_history_free() -> None:
	"""Equal runs and one equal canonical font intent return the current snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = _patch(session, _runs(("old", ("b",)),), (("font_family", "Courier"),))

	assert not result.changed and result.snapshot == before


#============================================
def test_absent_or_noncanonical_requested_font_value_is_a_real_change() -> None:
	"""A named root font request is not erased by run equality or raw legacy spelling."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		_CDML.replace('family="Courier"', 'family=" Courier "'),
	)
	result = _patch(session, _runs(("old", ("b",)),), (("font_family", "Courier"),))
	_authored, font = _text_state(result.snapshot.cdml)

	assert result.changed
	assert font["family"] == "Courier"
