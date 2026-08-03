"""Behavioral tests for backend-owned direct-root clipboard extraction."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


_SOURCE = """<cdml xmlns=\"http://www.freesoftware.fsf.org/bkchem/cdml\">
<molecule id=\"m1\"><atom id=\"a1\" name=\"C\"><point x=\"0cm\" y=\"0cm\" /></atom></molecule>
<arrow id=\"r1\" type=\"normal\" start=\"no\" end=\"yes\" spline=\"no\" width=\"1\" color=\"#000000\" shape=\"(8,10,3)\"><point x=\"1cm\" y=\"0cm\" /><point x=\"2cm\" y=\"0cm\" /></arrow>
<plus id=\"p1\"><point x=\"2cm\" y=\"0cm\" /></plus>
</cdml>"""


#============================================
def _session() -> cdml_document.CDMLDocumentSession:
	"""Load one mixed direct-root document through the public CDML boundary."""
	return cdml_document.CDMLDocumentSession.load(_SOURCE)


#============================================
def test_extraction_preserves_source_order_and_enters_top_level_insertion() -> None:
	"""Reversed durable requests return source-ordered roots accepted by Paste."""
	source = _session()
	result = source.extract_top_level_fragment(
		cdml_document.CDMLTopLevelFragmentExtractionQuery(source.revision, ("r1", "m1")),
	)
	target = cdml_document.CDMLDocumentSession.load("<cdml />")
	commit = target.insert_top_level(cdml_document.CDMLTopLevelInsertionRequest(
		target.revision, result.fragment_cdml, (0.0, 0.0), "Paste",
	))

	assert result.root_ids == ("m1", "r1")
	assert "molecule" in commit.snapshot.cdml


#============================================
def test_molecule_extraction_preserves_foreign_descendants_through_paste() -> None:
	"""Whole-root Copy preserves nested opaque molecule content through Paste."""
	source = cdml_document.CDMLDocumentSession.load(_SOURCE.replace(
		'</atom>', '<v:extension xmlns:v="urn:vendor" role="keep">'
		'<v:point x="9cm" y="8cm"/></v:extension></atom>',
	))
	fragment = source.extract_top_level_fragment(
		cdml_document.CDMLTopLevelFragmentExtractionQuery(source.revision, ("m1",)),
	)
	target = cdml_document.CDMLDocumentSession.load("<cdml />")
	commit = target.insert_top_level(cdml_document.CDMLTopLevelInsertionRequest(
		target.revision, fragment.fragment_cdml, (100.0, 0.0), "Paste",
	))
	extension = oasa.safe_xml.parse_dom_from_string(commit.snapshot.cdml).getElementsByTagNameNS(
		"urn:vendor", "extension",
	)[0]

	assert extension.getAttribute("role") == "keep"
	assert extension.getElementsByTagNameNS("urn:vendor", "point")[0].getAttribute("x") == "9cm"


#============================================
def test_core_molecule_child_cannot_bypass_insertion_validation() -> None:
	"""Only foreign extension children bypass the recognized molecule grammar."""
	session = cdml_document.CDMLDocumentSession.load(_SOURCE.replace(
		'</atom>', '<bond/></atom>',
	))
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLTopLevelFragmentExtractionError):
		session.extract_top_level_fragment(
			cdml_document.CDMLTopLevelFragmentExtractionQuery(session.revision, ("m1",)),
		)

	assert session.snapshot() == before
#============================================
def test_invalid_or_stale_extraction_is_typed_and_read_only() -> None:
	"""A bad direct-root query cannot change authoritative document state."""
	session = _session()
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLTopLevelFragmentExtractionError):
		session.extract_top_level_fragment(
			cdml_document.CDMLTopLevelFragmentExtractionQuery(session.revision, ("missing",)),
		)

	assert session.snapshot() == before


#============================================
def test_insertion_invalid_root_is_typed_and_read_only() -> None:
	"""A preserved opaque child cannot evade the established Paste grammar."""
	session = cdml_document.CDMLDocumentSession.load(_SOURCE.replace(
		'<point x="2cm" y="0cm" />',
		'<v:note xmlns:v="urn:vendor">opaque</v:note>',
	))
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLTopLevelFragmentExtractionError):
		session.extract_top_level_fragment(
			cdml_document.CDMLTopLevelFragmentExtractionQuery(session.revision, ("r1",)),
		)

	assert session.snapshot() == before
