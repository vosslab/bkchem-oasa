"""Behavioral tests for backend-authoritative exact CDML bond-order edits."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="2cm"/></atom><atom id="a2" name="O"><point x="3cm" y="4cm"/></atom><bond id="b1" start="a1" end="a2" type="w2" simple_double="1" center="no" auto_sign="1"><v:keep/></bond></molecule>
 <v:opaque id="x1"/><molecule id="m2"><atom id="a3" name="N"><point x="5cm" y="6cm"/></atom></molecule>
</cdml>
"""


#============================================
def _request(revision: int, order: int) -> object:
	"""Create one exact-order request against the inline durable target."""
	return oasa.cdml_document.CDMLBondOrderEditRequest(revision, "m1", "b1", order)


#============================================
def _bond_attributes(cdml_text: str) -> dict[str, str]:
	"""Read one bond after hardened CDML acceptance."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for bond in dom.getElementsByTagName("bond"):
		if bond.getAttribute("id") == "b1":
			return {
				bond.attributes.item(index).name: bond.attributes.item(index).value
				for index in range(bond.attributes.length)
			}
	raise AssertionError("accepted CDML did not contain bond b1")


#============================================
def test_bond_order_edit_changes_only_order_digit_and_preserves_document_content() -> None:
	"""Styled bond orders retain their type, depiction, children, and root order."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.set_bond_order(_request(session.revision, 3))
	attributes = _bond_attributes(result.snapshot.cdml)

	assert result.changed and attributes == {
		"id": "b1", "start": "a1", "end": "a2", "type": "w3",
		"simple_double": "1", "center": "no", "auto_sign": "1",
	}
	assert "<v:keep/>" in result.snapshot.cdml and "<v:opaque id=\"x1\"/>" in result.snapshot.cdml
	assert result.snapshot.cdml.index('id="m1"') < result.snapshot.cdml.index('id="x1"')


#============================================
def test_bond_order_edit_semantic_noop_preserves_lexical_snapshot() -> None:
	"""An already matching exact order does not allocate a revision or normalize XML."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = session.set_bond_order(_request(before.revision, 2))

	assert not result.changed and result.commit is None and result.snapshot == before


#============================================
def test_bond_order_edit_updates_normal_authored_type() -> None:
	"""A normal authored type changes only its exact order digit."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		_CDML.replace('type="w2"', 'type="n1"'),
	)
	result = session.set_bond_order(_request(session.revision, 2))

	assert result.changed and _bond_attributes(result.snapshot.cdml)["type"] == "n2"


#============================================
@pytest.mark.parametrize(
	"type_text, requested_order",
	(("q1", 2), ("q2", 1), ("l1", 1), ("w2x", 1), ("n", 2), ("q", 1)),
)
def test_bond_order_edit_rejects_ambiguous_or_restricted_type_without_commit(
		type_text: str, requested_order: int,
		) -> None:
	"""Unsupported source grammar and Haworth order changes fail atomically."""
	cdml = _CDML.replace('type="w2"', 'type="%s"' % type_text)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		session.set_bond_order(_request(before.revision, requested_order))

	assert session.snapshot() == before


#============================================
def test_bond_order_edit_rejects_stale_or_invalid_target_atomically() -> None:
	"""A stale revision and invalid direct target or endpoints leave CDML unchanged."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.set_bond_order(_request(before.revision + 1, 1))
	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		session.set_bond_order(oasa.cdml_document.CDMLBondOrderEditRequest(
			before.revision, "m1", "missing", 1,
		))

	assert session.snapshot() == before

	self_loop = _CDML.replace('end="a2"', 'end="a1"')
	self_loop_session = oasa.cdml_document.CDMLDocumentSession.load(self_loop)
	self_loop_before = self_loop_session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		self_loop_session.set_bond_order(_request(self_loop_before.revision, 3))

	assert self_loop_session.snapshot() == self_loop_before

	independent_order = _CDML.replace('type="w2"', 'type="w2" order="2"')
	independent_order_session = oasa.cdml_document.CDMLDocumentSession.load(independent_order)
	independent_order_before = independent_order_session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		independent_order_session.set_bond_order(_request(independent_order_before.revision, 3))

	assert independent_order_session.snapshot() == independent_order_before
