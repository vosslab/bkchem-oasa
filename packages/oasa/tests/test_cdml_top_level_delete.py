"""Focused authority tests for revision-bound CDML root deletion."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:test" version="26.07">
 <paper id="paper_1" type="A4" orientation="portrait" />
 <molecule id="mol_1"><atom id="atom_1" name="C"><point x="1cm" y="1cm" /></atom></molecule>
 <arrow id="arrow_1"><point x="1cm" y="2cm" /><point x="2cm" y="2cm" /></arrow>
 <plus id="plus_1" pos="3cm 2cm" />
 <text id="text_1"><ftext>condition</ftext></text>
 <rect id="rect_1" x="1" y="1" width="2" height="3" />
 <reaction id="reaction_1"><condition idref="text_1" /></reaction>
 <v:opaque id="opaque_1" idref="arrow_1">arrow_1</v:opaque>
</cdml>
"""


#============================================
def _request(session: cdml_document.CDMLDocumentSession, *identifiers: str) -> object:
	"""Build one ordinary current-revision delete request."""
	return cdml_document.CDMLTopLevelDeleteRequest(session.revision, identifiers, "Delete")


#============================================
def _state(session: cdml_document.CDMLDocumentSession) -> tuple[int, str]:
	"""Return the externally visible state failures must preserve exactly."""
	snapshot = session.snapshot()
	return snapshot.revision, snapshot.cdml


#============================================
def test_delete_top_level_removes_requested_roots_and_preserves_surviving_order() -> None:
	"""One accepted Delete removes only requested roots and keeps opaque content."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	commit = session.delete_top_level(_request(session, "mol_1", "rect_1"))
	objects = cdml_document.CDMLDocument.parse(commit.cdml).objects()
	assert [record.identifier for record in objects] == [
		"paper_1", "arrow_1", "plus_1", "text_1", "reaction_1", "opaque_1",
	]
	assert 'idref="arrow_1">arrow_1' in commit.cdml
	assert commit.revision == 1


@pytest.mark.parametrize("identifiers", [(), ("arrow_1", "arrow_1"), ("atom_1",), ("opaque_1",), ("paper_1",), ("reaction_1",), ("missing",)])
def test_delete_top_level_rejections_are_atomic(identifiers: tuple[str, ...]) -> None:
	"""Malformed, nested, opaque, header, unsupported, and absent targets mutate nothing."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	before = _state(session)
	with pytest.raises(cdml_document.CDMLValidationError):
		session.delete_top_level(_request(session, *identifiers))
	assert _state(session) == before


#============================================
def test_delete_top_level_rejects_reaction_references_without_mutation() -> None:
	"""A recognized reaction role prevents dangling direct-root deletion."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	before = _state(session)
	with pytest.raises(cdml_document.CDMLValidationError, match="reaction role"):
		session.delete_top_level(_request(session, "text_1"))
	assert _state(session) == before


#============================================
def test_delete_top_level_stale_request_and_idless_legacy_root_are_atomic() -> None:
	"""Delete uses optimistic revision binding and never allocates legacy IDs."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	stale = _request(session, "arrow_1")
	session.commit(expected_revision=0, complete_cdml=session.snapshot().cdml)
	before = _state(session)
	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.delete_top_level(stale)
	assert _state(session) == before
	legacy = _CDML.replace(' id="plus_1"', "", 1)
	legacy_session = cdml_document.CDMLDocumentSession.load(legacy)
	legacy_before = _state(legacy_session)
	with pytest.raises(cdml_document.CDMLValidationError):
		legacy_session.delete_top_level(_request(legacy_session, "plus_1"))
	assert _state(legacy_session) == legacy_before


#============================================
def test_delete_top_level_uses_existing_backend_restore_history() -> None:
	"""Backend restore returns exact predecessor content after one accepted deletion."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	deleted = session.delete_top_level(_request(session, "arrow_1"))
	restored = session.restore(target_revision=before.revision, expected_revision=deleted.revision)
	assert restored.cdml == before.cdml
