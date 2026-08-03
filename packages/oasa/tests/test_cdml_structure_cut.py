"""Behavioral tests for backend-authoritative structural clipboard extraction."""

import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


#============================================
def _session() -> cdml_document.CDMLDocumentSession:
	"""Create one three-atom chain through the public CDML boundary."""
	return cdml_document.CDMLDocumentSession.load("""\
<cdml><molecule id="m0">
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
 <atom id="a2" name="C"><point x="1cm" y="0cm" /></atom>
 <atom id="a3" name="O"><point x="2cm" y="0cm" /></atom>
 <bond id="b1" start="a1" end="a2" type="n1" />
 <bond id="b2" start="a2" end="a3" type="n1" />
</molecule></cdml>
""")


#============================================
def _query(
		session: cdml_document.CDMLDocumentSession, atom_ids: tuple[str, ...] = (),
		bond_ids: tuple[str, ...] = (),
		) -> cdml_document.CDMLStructureFragmentExtractionQuery:
	"""Build one exact current-revision extraction query."""
	return cdml_document.CDMLStructureFragmentExtractionQuery(
		session.revision, "m0", atom_ids, bond_ids,
	)


#============================================
def _accepted_xml(cdml: str) -> object:
	"""Parse backend-accepted CDML for one structural preservation assertion."""
	return oasa.safe_xml.parse_xml_string(cdml)


#============================================
def test_bond_extraction_closes_endpoints_and_inserts_elsewhere() -> None:
	"""A selected bond exports both endpoints as one independently insertable molecule."""
	source = _session()
	result = source.extract_structure_fragment(_query(source, bond_ids=("b1",)))
	target = cdml_document.CDMLDocumentSession.load("<cdml />")
	commit = target.insert_top_level(cdml_document.CDMLTopLevelInsertionRequest(
		target.revision, result.fragment_cdml, (0.0, 0.0), "Paste",
	))

	assert (result.atom_ids, result.bond_ids) == (("a1", "a2"), ("b1",))
	assert "<bond" in commit.snapshot.cdml


#============================================
def test_extraction_is_read_only_and_preserves_source_order() -> None:
	"""A connected subset is ordered by authoritative molecule order without history."""
	session = _session()
	before = session.snapshot()
	result = session.extract_structure_fragment(_query(session, ("a3", "a2"), ("b2",)))

	assert (result.atom_ids, result.bond_ids) == (("a2", "a3"), ("b2",))
	assert session.snapshot() == before


#============================================
def test_disconnected_structural_selection_is_rejected_atomically() -> None:
	"""Two isolated selected atoms cannot silently become a multi-root clipboard fragment."""
	session = _session()
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLStructureFragmentExtractionError):
		session.extract_structure_fragment(_query(session, ("a1", "a3")))

	assert session.snapshot() == before


#============================================
def test_missing_extraction_root_is_typed_and_atomic() -> None:
	"""A missing direct root remains a typed read-only target rejection."""
	session = _session()
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLStructureFragmentExtractionError):
		session.extract_structure_fragment(cdml_document.CDMLStructureFragmentExtractionQuery(
			session.revision, "missing", ("a1",), (),
		))

	assert session.snapshot() == before


#============================================
def test_selected_atom_opaque_child_survives_extraction_and_paste() -> None:
	"""A compatible foreign child stays persistent through the structural clipboard route."""
	session = cdml_document.CDMLDocumentSession.load(
		_session().snapshot().cdml.replace(
			"</atom>",
			"<v:opaque xmlns:v=\"urn:vendor\" v:kind=\"atom-detail\">"
			"payload<v:nested flag=\"kept\"/></v:opaque></atom>",
			1,
		),
	)
	before = session.snapshot()
	fragment = session.extract_structure_fragment(_query(session, ("a1",)))
	target = cdml_document.CDMLDocumentSession.load("<cdml />")
	commit = target.insert_top_level(cdml_document.CDMLTopLevelInsertionRequest(
		target.revision, fragment.fragment_cdml, (0.0, 0.0), "Paste",
	))

	opaque = _accepted_xml(commit.snapshot.cdml).find(".//{urn:vendor}opaque")
	assert (
		opaque.attrib["{urn:vendor}kind"], opaque.text,
		opaque.find("{urn:vendor}nested").attrib["flag"],
	) == ("atom-detail", "payload", "kept")
	assert session.snapshot() == before


#============================================
def test_selected_atom_misplaced_core_child_is_typed_and_atomic() -> None:
	"""A misplaced known CDML child remains rejected before a clipboard result escapes."""
	session = cdml_document.CDMLDocumentSession.load(
		_session().snapshot().cdml.replace(
			"</atom>",
			"<c:bond xmlns:c=\"http://www.freesoftware.fsf.org/bkchem/cdml\"/></atom>",
			1,
		),
	)
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLStructureFragmentExtractionError):
		session.extract_structure_fragment(_query(session, ("a1",)))

	assert session.snapshot() == before


#============================================
def test_stale_extraction_uses_the_established_revision_conflict() -> None:
	"""A stale read query remains fenced before source extraction."""
	session = _session()
	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.extract_structure_fragment(cdml_document.CDMLStructureFragmentExtractionQuery(
			-1, "m0", ("a1",), (),
		))


#============================================
def test_prefixed_namespace_extraction_remains_parseable_and_insertable() -> None:
	"""Detached selections retain inherited namespace bindings for later insertion."""
	namespace = "http://www.freesoftware.fsf.org/bkchem/cdml"
	source = cdml_document.CDMLDocumentSession.load(
		'<c:cdml xmlns:c="%s"><c:molecule id="m">'
		'<c:atom id="a" name="C"><c:point x="0cm" y="0cm"/></c:atom>'
		'</c:molecule></c:cdml>' % namespace,
	)
	result = source.extract_structure_fragment(cdml_document.CDMLStructureFragmentExtractionQuery(
		source.revision, "m", ("a",), (),
	))
	target = cdml_document.CDMLDocumentSession.load("<cdml />")
	commit = target.insert_top_level(cdml_document.CDMLTopLevelInsertionRequest(
		target.revision, result.fragment_cdml, (0.0, 0.0), "Paste",
	))

	assert 'xmlns:c="%s"' % namespace in result.fragment_cdml
	assert "<c:atom" in commit.snapshot.cdml
