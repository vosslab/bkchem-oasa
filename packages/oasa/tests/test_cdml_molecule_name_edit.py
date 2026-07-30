"""Behavioral tests for backend-owned direct-root molecule display names."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


_CDML = """\
<cdml xmlns:v="urn:vendor">
 <v:note id="before" marker="first">keep<v:detail rank="1">payload</v:detail>tail</v:note>
 <molecule id="m1" name="old" role="source">
  <atom id="a1" name="C" charge="1"><point x="1cm" y="1cm" /><font family="serif" size="12" /><mark type="radical" /></atom>
  <atom id="a2" name="O"><point x="2cm" y="1cm" /></atom>
  <bond id="b1" type="n1" start="a1" end="a2" />
  <fragment id="nested" />
 </molecule>
 <arrow id="arr1"><point x="1cm" y="2cm" /><point x="2cm" y="2cm" /></arrow>
 <molecule id="m2" name="unrelated"><atom id="a3" name="N"><point x="3cm" y="1cm" /></atom></molecule>
 <reaction id="reaction1"><reactant idref="m1" /><product idref="m2" /><arrow idref="arr1" /></reaction>
 <v:molecule id="opaque" name="keep" /><v:note id="after" marker="last">keep</v:note>
</cdml>
"""


#============================================
def _request(revision: object, molecule_id: object, name: object) -> object:
	"""Build one plain request, including invalid runtime shapes."""
	return cdml_document.CDMLMoleculeNameEditRequest(revision, molecule_id, name)


#============================================
def _accepted_dom(cdml_text: str) -> object:
	"""Return a compatibility DOM only after the complete CDML boundary accepted it."""
	accepted = cdml_document.CDMLDocument.parse(cdml_text, validation="compat")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	return dom


#============================================
def _direct_root_element(dom: object, identifier: str) -> object:
	"""Return one direct core root by durable identifier."""
	for element in dom.documentElement.childNodes:
		if element.nodeType == element.ELEMENT_NODE and element.getAttribute("id") == identifier:
			return element
	raise AssertionError("accepted CDML did not contain the requested direct root")


#============================================
def _molecule_name(cdml_text: str, identifier: str) -> str:
	"""Read one accepted direct-root molecule display name."""
	dom = _accepted_dom(cdml_text)
	element = _direct_root_element(dom, identifier)
	return element.getAttribute("name")


#============================================
def _element_children_xml(element: object) -> tuple[str, ...]:
	"""Return direct element children as exact accepted XML subtrees."""
	children = tuple(
		child.toxml() for child in element.childNodes
		if child.nodeType == child.ELEMENT_NODE
	)
	return children


#============================================
def _non_name_attributes(element: object) -> tuple[tuple[str, str], ...]:
	"""Return one direct-root attribute record apart from mutable molecule name."""
	attributes = tuple(sorted(
		(attribute.name, attribute.value)
		for index in range(element.attributes.length)
		for attribute in (element.attributes.item(index),)
		if attribute.name != "name"
	))
	return attributes


#============================================
def _preservation_record(cdml_text: str) -> dict:
	"""Capture persistent content that a direct-root name edit must retain."""
	dom = _accepted_dom(cdml_text)
	root = dom.documentElement
	molecule = _direct_root_element(dom, "m1")
	reaction = _direct_root_element(dom, "reaction1")
	root_order = tuple(
		(child.tagName, child.getAttribute("id"))
		for child in root.childNodes if child.nodeType == child.ELEMENT_NODE
	)
	reaction_roles = tuple(
		(child.tagName, child.getAttribute("idref"))
		for child in reaction.childNodes if child.nodeType == child.ELEMENT_NODE
	)
	other_roots = tuple(
		(child.tagName, child.getAttribute("id"), child.toxml())
		for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.getAttribute("id") != "m1"
	)
	record = {
		"root_order": root_order,
		"molecule_attributes": _non_name_attributes(molecule),
		"molecule_children": _element_children_xml(molecule),
		"reaction_roles": reaction_roles,
		"other_roots": other_roots,
	}
	return record


#============================================
def test_molecule_name_replace_preserves_unrelated_document_content() -> None:
	"""A direct-root replacement retains IDs, IDREF roles, order, children, and opaque XML."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	before = _preservation_record(session.snapshot().cdml)
	commit = session.set_molecule_name(_request(session.revision, "m1", "new name"))
	after = _preservation_record(commit.cdml)

	assert _molecule_name(commit.cdml, "m1") == "new name"
	assert after == before


#============================================
def test_molecule_name_clear_and_whitespace_are_exact_persistent_values() -> None:
	"""An empty name clears the attribute while whitespace remains a name."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	changed = session.set_molecule_name(_request(session.revision, "m1", "  "))
	cleared = session.set_molecule_name(_request(changed.revision, "m1", ""))
	cleared_molecule = _direct_root_element(_accepted_dom(cleared.cdml), "m1")

	assert _molecule_name(changed.cdml, "m1") == "  "
	assert not cleared_molecule.hasAttribute("name")


#============================================
def test_molecule_name_noop_and_stale_request_preserve_authoritative_revision() -> None:
	"""No-op stays history-free and stale rejection precedes its no-op comparison."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	no_op = session.set_molecule_name(_request(session.revision, "m1", "old"))
	session.set_molecule_name(_request(session.revision, "m1", "new"))
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.set_molecule_name(_request(no_op.revision, "m1", "new"))

	assert no_op.revision == 0
	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("attempt", (
	object(), _request(True, "m1", "x"), _request(0, "", "x"),
	_request(0, "m1", None), _request(0, "missing", "x"), _request(0, "arr1", "x"),
	_request(0, "nested", "x"), _request(0, "opaque", "x"),
))
def test_molecule_name_invalid_targets_are_atomic(attempt: object) -> None:
	"""Malformed, absent, wrong-kind, nested, and opaque targets leave the snapshot untouched."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLValidationError):
		session.set_molecule_name(attempt)

	assert session.snapshot() == before
