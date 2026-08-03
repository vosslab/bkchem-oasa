"""Behavior checks for the revision-bound backend paper/layout observation."""

# Standard Library
import dataclasses
import json

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document


_CDML = """\
<cdml xmlns=\"http://www.freesoftware.fsf.org/bkchem/cdml\" xmlns:v=\"urn:vendor\">
 <v:paper type=\"vendor\" /><standard paper_type=\"Letter\" paper_orientation=\"landscape\" />
 <paper type=\"A4\" orientation=\"portrait\" keep=\"first\" />
 <paper type=\"A3\" orientation=\"landscape\" keep=\"later\" />
 <viewport viewport=\"0 0 10 10\" /><v:viewport viewport=\"opaque\" />
</cdml>"""


#============================================
def test_paper_layout_is_plain_and_selects_only_first_direct_core_records() -> None:
	"""Foreign lookalikes and later duplicates remain backend-only CDML content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	layout = session.paper_layout(oasa.cdml_document.CDMLPaperLayoutQuery(session.revision))

	json.dumps(dataclasses.asdict(layout))
	paper_attributes = dict(layout.paper_attributes)
	assert (
		paper_attributes["type"] == "A4"
		and paper_attributes["keep"] == "first"
		and dict(layout.viewport_attributes)["viewport"] == "0 0 10 10"
	)


#============================================
def test_paper_layout_uses_standard_defaults_only_when_direct_paper_is_absent() -> None:
	"""An absent paper has the backend's effective standard-derived display facts."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<cdml><standard paper_type="Letter" paper_orientation="landscape" /></cdml>',
	)
	layout = session.paper_layout(oasa.cdml_document.CDMLPaperLayoutQuery(session.revision))

	effective_attributes = dict(layout.effective_paper_attributes)
	assert (
		not layout.paper_present
		and not layout.paper_attributes
		and layout.default_type == "Letter"
		and layout.default_orientation == "landscape"
		and effective_attributes["type"] == "Letter"
		and effective_attributes["orientation"] == "landscape"
	)


#============================================
def test_stale_paper_layout_query_leaves_the_authoritative_snapshot_unchanged() -> None:
	"""Read-only stale rejection cannot alter the current backend snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.paper_layout(oasa.cdml_document.CDMLPaperLayoutQuery(before.revision + 1))
	assert session.snapshot() == before
