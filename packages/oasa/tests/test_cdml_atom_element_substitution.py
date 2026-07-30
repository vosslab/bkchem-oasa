"""Behavioral tests for backend-owned CDML atom element substitution."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


#============================================
BASE_CDML = """\
<cdml xmlns:vendor="urn:vendor">
 <vendor:note id="opaque_before" marker="keep">before</vendor:note>
 <molecule id="m_one">
  <atom id="a_carbon" name="C" charge="1" valency="4" isotope="13" vendor:flag="keep"><point x="0cm" y="0cm" /><vendor:payload marker="retain">payload</vendor:payload></atom>
  <atom id="a_nitrogen" name="N"><point x="1cm" y="0cm" /></atom>
  <fragment id="f_one"><atom id="a_nested" name="C"><point x="2cm" y="0cm" /></atom></fragment>
  <vendor:atom id="a_opaque" name="C"><point x="3cm" y="0cm" /></vendor:atom>
 </molecule>
 <vendor:molecule id="m_opaque"><atom id="a_hidden" name="C"><point x="4cm" y="0cm" /></atom></vendor:molecule>
 <vendor:note id="opaque_after" marker="keep">after</vendor:note>
</cdml>
"""


#============================================
def _request(revision: object, molecule_id: object, atom_id: object, element: object) -> object:
	"""Build one deliberately plain request, including invalid runtime shapes."""
	return cdml_document.CDMLAtomElementEditRequest(
		expected_revision=revision,
		molecule_id=molecule_id,
		atom_id=atom_id,
		element=element,
	)


#============================================
def _state(session: cdml_document.CDMLDocumentSession) -> tuple[int, str]:
	"""Capture observable authoritative state for atomic-rejection checks."""
	snapshot = session.snapshot()
	return snapshot.revision, snapshot.cdml


#============================================
def _accepted_atom(cdml_text: str, identifier: str) -> object:
	"""Read one accepted atom after the owning CDML boundary parsed it first."""
	accepted = cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for element in dom.getElementsByTagName("*"):
		if element.getAttribute("id") == identifier:
			return element
	raise AssertionError(f"accepted CDML did not contain atom {identifier}")


#============================================
def _preserves_carbon_context(target: object, cdml_text: str) -> bool:
	"""Recognize the non-element CDML content a C-to-O edit must retain."""
	return (
		target.getAttribute("charge") == "1"
		and target.getAttribute("valency") == "4"
		and target.getAttribute("isotope") == "13"
		and target.getAttribute("vendor:flag") == "keep"
		and 'vendor:payload marker="retain">payload</vendor:payload>' in target.toxml()
		and cdml_text.index('id="opaque_before"') < cdml_text.index('id="m_one"')
		< cdml_text.index('id="opaque_after"')
		and cdml_text.index('id="a_carbon"') < cdml_text.index('id="a_nitrogen"')
	)


#============================================
def test_carbon_to_oxygen_changes_only_the_named_direct_atom_and_preserves_document_content() -> None:
	"""A direct C atom replacement retains its durable atom and surrounding CDML."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	commit = session.set_atom_element(_request(session.revision, "m_one", "a_carbon", "O"))
	target = _accepted_atom(commit.cdml, "a_carbon")

	assert target.getAttribute("name") == "O"
	assert _preserves_carbon_context(target, commit.cdml)


#============================================
def test_noncarbon_atom_replacement_retains_the_existing_durable_identity() -> None:
	"""The bounded operation keeps established AtomMode replacement behavior generic."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	commit = session.set_atom_element(_request(session.revision, "m_one", "a_nitrogen", "O"))
	target = _accepted_atom(commit.cdml, "a_nitrogen")

	assert (target.getAttribute("id"), target.getAttribute("name")) == ("a_nitrogen", "O")


#============================================
@pytest.mark.parametrize("cdml_text, attempt", (
	(BASE_CDML, object()),
	(BASE_CDML, _request(True, "m_one", "a_carbon", "O")),
	(BASE_CDML, _request(0, "", "a_carbon", "O")),
	(BASE_CDML, _request(0, "m_one", "", "O")),
	(BASE_CDML, _request(0, "m_one", "a_carbon", "NotAnElement")),
	(BASE_CDML, _request(0, "m_one", "a_carbon", "C")),
	(BASE_CDML.replace('id="a_carbon" name="C"', 'id="a_carbon" name="NotAnElement"'), _request(0, "m_one", "a_carbon", "O")),
	(BASE_CDML, _request(0, "m_one", "a_nested", "O")),
	(BASE_CDML, _request(0, "m_one", "a_opaque", "O")),
	(BASE_CDML, _request(0, "m_opaque", "a_hidden", "O")),
))
def test_invalid_or_nondirect_element_requests_leave_authoritative_state_unchanged(
		cdml_text: str, attempt: object,
		) -> None:
	"""Malformed, opaque, nested, and unsupported replacements remain atomic."""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.set_atom_element(attempt)

	assert _state(session) == before


#============================================
def test_stale_element_request_never_replays_over_the_newer_authoritative_snapshot() -> None:
	"""Optimistic revision conflicts leave the later accepted element untouched."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	request = _request(session.revision, "m_one", "a_carbon", "O")
	session.set_atom_element(request)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.set_atom_element(request)

	assert _state(session) == before
