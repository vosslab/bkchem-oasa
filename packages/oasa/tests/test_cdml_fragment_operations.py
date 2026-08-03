"""Behavioral contract tests for backend-owned ordinary CDML fragments."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = """<cdml xmlns:v="urn:vendor"><molecule id="m1"><atom id="a1" name="C"><point x="0cm" y="0cm"/></atom><atom id="a2" name="O"><point x="1cm" y="0cm"/></atom><bond id="b1" start="a1" end="a2" type="n1"/><fragment id="legacy" type="linear_form"><name>keep</name><vertex id="a1"/><property name="spacing" value="1"/></fragment><v:opaque id="extension">keep</v:opaque></molecule></cdml>"""


#============================================
def test_fragment_create_delete_and_restore_preserve_opaque_siblings() -> None:
	"""Ordinary fragment edits preserve unsupported content and backend history."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	created = session.create_fragment(oasa.cdml_document.CDMLFragmentCreateRequest(
		0, "m1", "  selected chain  ", "explicit", ("a1", "a2"), ("b1",),
	))
	created_root = oasa.safe_xml.parse_xml_string(created.snapshot.cdml)
	fragment = next(
		element for element in created_root.findall(".//fragment")
		if element.get("id") == created.fragment_id
	)
	assert tuple(child.tag for child in fragment) == (
		"name", "bond", "vertex", "vertex",
	)
	deleted = session.delete_fragment(oasa.cdml_document.CDMLFragmentDeleteRequest(
		created.snapshot.revision, "m1", created.fragment_id,
	))
	session.restore(target_revision=created.snapshot.revision, expected_revision=deleted.snapshot.revision)
	assert "linear_form" in session.snapshot().cdml and created.fragment_id in session.snapshot().cdml


#============================================
@pytest.mark.parametrize("fragment_request", (
	oasa.cdml_document.CDMLFragmentCreateRequest(0, "m1", "x", "explicit", ("a1", "a1"), ()),
	oasa.cdml_document.CDMLFragmentCreateRequest(0, "m1", "x", "explicit", ("a1",), ("b1",)),
	oasa.cdml_document.CDMLFragmentCreateRequest(0, "m1", "x", "linear_form", ("a1",), ()),
))
def test_fragment_create_rejections_are_typed_and_atomic(
		fragment_request: oasa.cdml_document.CDMLFragmentCreateRequest,
		) -> None:
	"""Malformed ordinary fragment intent cannot change authoritative state."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	with pytest.raises(oasa.cdml_document.CDMLFragmentOperationError):
		session.create_fragment(fragment_request)
	assert session.snapshot().revision == 0


#============================================
def test_fragment_delete_rejects_preservation_only_metadata() -> None:
	"""A rich imported fragment remains retained rather than becoming editable."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot().cdml
	with pytest.raises(oasa.cdml_document.CDMLFragmentOperationError):
		session.delete_fragment(oasa.cdml_document.CDMLFragmentDeleteRequest(0, "m1", "legacy"))
	assert session.snapshot().cdml == before


#============================================
def test_fragment_metadata_separates_ordinary_and_linear_form_records() -> None:
	"""The observation exposes ordinary eligibility and keeps linear forms read-only."""
	text = _CDML.replace(
		'<v:opaque id="extension">keep</v:opaque>',
		'<fragment id="ordinary" type="explicit"><name>pair</name><vertex id="a1"/></fragment>'
		'<v:fragment id="foreign"><name>extension</name></v:fragment>',
	)
	metadata = oasa.cdml_document.CDMLDocument.parse(text, validation="strict").fragment_metadata(4)
	assert {
		(record.fragment_id, record.disposition) for record in metadata.records
	} == {
		("legacy", "display-only"), ("ordinary", "editable"),
		("foreign", "display-only"),
	}


#============================================
def test_fragment_metadata_stale_query_is_typed_and_nonmutating() -> None:
	"""An obsolete observation query does not alter the authoritative revision."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	session.create_fragment(oasa.cdml_document.CDMLFragmentCreateRequest(
		0, "m1", "pair", "explicit", ("a1",), (),
	))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.fragment_metadata(oasa.cdml_document.CDMLFragmentMetadataQuery(0))
	assert session.snapshot().revision == 1


#============================================
def test_fragment_metadata_marks_ambiguous_ids_display_only() -> None:
	"""Compatibility inspection never offers a duplicate durable ID for editing."""
	text = _CDML.replace(
		'<v:opaque id="extension">keep</v:opaque>',
		'<fragment id="same" type="explicit"><name>first</name><vertex id="a1"/></fragment>'
		'<fragment id="same" type="explicit"><name>second</name><vertex id="a2"/></fragment>',
	)
	metadata = oasa.cdml_document.CDMLDocument.parse(text).fragment_metadata(0)
	assert all(record.disposition == "display-only" for record in metadata.records if record.fragment_id == "same")
