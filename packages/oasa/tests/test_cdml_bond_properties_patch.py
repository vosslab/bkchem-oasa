"""Behavioral tests for atomic backend-authoritative bond-properties patches."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = """
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="2cm"/></atom><atom id="a2" name="O"><point x="3cm" y="4cm"/></atom><bond id="b1" start="a1" end="a2" type="w1" vendor_keep="yes"><v:keep/></bond></molecule>
 <v:opaque id="x1"/>
</cdml>
"""


#============================================
def _patch(revision: int, changes: tuple[tuple[str, object], ...]) -> object:
	"""Create one direct durable patch against the inline molecule and bond."""
	return oasa.cdml_document.CDMLBondPropertiesPatch(revision, "m1", "b1", changes)


#============================================
def _attributes(cdml_text: str) -> dict[str, str]:
	"""Read the accepted direct bond through the hardened CDML boundary."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	bond = next(item for item in dom.getElementsByTagName("bond") if item.getAttribute("id") == "b1")
	return {item.name: item.value for item in bond.attributes.values()}


#============================================
def test_bond_properties_patch_commits_all_explicit_fields_once() -> None:
	"""One valid multi-field patch creates exactly one authoritative history revision."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.patch_bond_properties(_patch(session.revision, (
		("order", 2), ("type", "h"), ("center", True), ("line_width", 1.5),
		("bond_width", 7.0), ("wedge_width", 8.0), ("color", "#A0b1C2"),
	)))
	attributes = _attributes(result.snapshot.cdml)

	assert result.changed and result.snapshot.revision == 1
	assert attributes["type"] == "h2" and attributes["color"] == "#a0b1c2"
	assert attributes["line_width"] == "1.5" and attributes["center"] == "yes"
	assert "vendor_keep=\"yes\"" in result.snapshot.cdml and "<v:keep/>" in result.snapshot.cdml
	assert result.snapshot.cdml.index("</molecule>") < result.snapshot.cdml.index("<v:opaque")


#============================================
def test_bond_properties_patch_noop_and_untouched_absence_preserve_snapshot() -> None:
	"""Canonical equality is history-free and never materializes untouched attributes."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = session.patch_bond_properties(_patch(before.revision, (("order", 1),)))

	assert not result.changed and result.snapshot == before
	assert "line_width=" not in result.snapshot.cdml and "center=" not in result.snapshot.cdml


#============================================
@pytest.mark.parametrize("changes", (
	(("order", 2), ("type", "q")),
	(("color", "blue"),), (("order", 1), ("order", 2)),
))
def test_bond_properties_patch_rejects_invalid_intent_atomically(
		changes: tuple[tuple[str, object], ...],
		) -> None:
	"""Invalid final intent or duplicate fields cannot alter the accepted snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLBondPropertiesPatchError):
		session.patch_bond_properties(_patch(before.revision, changes))

	assert session.snapshot() == before


#============================================
def test_bond_properties_patch_rejects_unhashable_field_atomically() -> None:
	"""Malformed field names are typed failures before duplicate-field tracking."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	request = oasa.cdml_document.CDMLBondPropertiesPatch(
		before.revision, "m1", "b1", ((["color"], "#112233"),),
	)

	with pytest.raises(oasa.cdml_document.CDMLBondPropertiesPatchError):
		session.patch_bond_properties(request)

	assert session.snapshot() == before and tuple(session._history) == (0,)


#============================================
def test_bond_properties_patch_rejects_non_plain_type_atomically() -> None:
	"""A hostile equality implementation remains a typed atomic rejection."""
	class ExplosiveType:
		"""Raise when tuple membership tries to compare an invalid request value."""
		def __eq__(self, other: object) -> bool:
			raise RuntimeError("comparison must not escape the CDML boundary")

	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	request = _patch(before.revision, (("type", ExplosiveType()),))

	with pytest.raises(oasa.cdml_document.CDMLBondPropertiesPatchError):
		session.patch_bond_properties(request)

	assert session.snapshot() == before and tuple(session._history) == (0,)


#============================================
def test_bond_properties_patch_retains_hashed_compatibility_spelling() -> None:
	"""An explicit h request retains l1 while applying another explicit property."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML.replace('type="w1"', 'type="l1"'))
	result = session.patch_bond_properties(_patch(session.revision, (("type", "h"), ("color", "#112233"))))

	assert result.changed and 'type="l1"' in result.snapshot.cdml
	assert 'color="#112233"' in result.snapshot.cdml


#============================================
def test_bond_properties_patch_rejects_stale_or_non_direct_targets() -> None:
	"""Revision and direct durable-target checks leave the accepted snapshot intact."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	accepted = session.patch_bond_properties(_patch(session.revision, (("color", "#112233"),)))
	before = session.snapshot()
	missing_bond = oasa.cdml_document.CDMLBondPropertiesPatch(
		before.revision, "m1", "missing", (("order", 2),),
	)

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.patch_bond_properties(_patch(0, (("order", 2),)))
	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		session.patch_bond_properties(missing_bond)

	assert accepted.changed and session.snapshot() == before


#============================================
def test_bond_properties_patch_preserves_haworth_when_type_and_order_are_untouched() -> None:
	"""A presentation-only patch keeps q1 spelling rather than normalizing it."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML.replace('type="w1"', 'type="q1"'))
	result = session.patch_bond_properties(_patch(session.revision, (("color", "#445566"),)))

	assert result.changed and 'type="q1"' in result.snapshot.cdml
