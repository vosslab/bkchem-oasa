"""Behavioral tests for the bounded backend ``structure.delete`` operation."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


#============================================
def _session(cdml_text: str) -> cdml_document.CDMLDocumentSession:
	"""Load one inline complete CDML input through the public hardened boundary."""
	return cdml_document.CDMLDocumentSession.load(cdml_text)


#============================================
def _request(
		session: cdml_document.CDMLDocumentSession, atom_ids: tuple[str, ...] = (),
		bond_ids: tuple[str, ...] = (),
		) -> cdml_document.CDMLStructureDeleteRequest:
	"""Build one current-revision structural deletion request."""
	return cdml_document.CDMLStructureDeleteRequest(
		session.revision, "m0", atom_ids, bond_ids, "Delete",
	)


#============================================
def _state(session: cdml_document.CDMLDocumentSession) -> tuple[int, str]:
	"""Capture visible authoritative state for atomic-rejection checks."""
	snapshot = session.snapshot()
	return snapshot.revision, snapshot.cdml


#============================================
def _root_molecules(cdml_text: str) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
	"""Inspect accepted CDML root components after public boundary acceptance."""
	accepted = cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	components = []
	for molecule in dom.documentElement.childNodes:
		if molecule.nodeType != molecule.ELEMENT_NODE or molecule.localName != "molecule":
			continue
		atoms = []
		bonds = []
		for child in molecule.childNodes:
			if child.nodeType != child.ELEMENT_NODE:
				continue
			if child.localName == "atom":
				atoms.append(child.getAttribute("id"))
			elif child.localName == "bond":
				bonds.append(child.getAttribute("id"))
		components.append((molecule.getAttribute("id"), tuple(atoms), tuple(bonds)))
	return tuple(components)


#============================================
def _chain_cdml(extra: str = "") -> str:
	"""Return one direct-root three-atom chain with an optional root sibling."""
	return f"""\
<cdml xmlns:v="urn:vendor">
 <molecule id="m0" name="parent">
  <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="a2" name="C"><point x="1cm" y="0cm" /></atom>
  <atom id="a3" name="O"><point x="2cm" y="0cm" /></atom>
  <bond id="b1" start="a1" end="a2" type="n1" />
  <bond id="b2" start="a2" end="a3" type="n1" />
 </molecule>
 {extra}
</cdml>
"""


#============================================
def test_terminal_atom_removes_its_incident_bond_and_keeps_one_root() -> None:
	"""A terminal target removes its edge and preserves the surviving component."""
	session = _session(_chain_cdml())
	result = session.delete_structure(_request(session, ("a3",)))

	assert (result.removed_atom_ids, result.removed_bond_ids) == (("a3",), ("b2",))
	assert result.components == (
		cdml_document.CDMLStructureDeleteComponent("m0", ("a1", "a2"), ("b1",)),
	)


#============================================
def test_selected_bond_splits_two_atoms_into_durable_singleton_roots() -> None:
	"""Deleting an edge preserves both isolated atoms as ordered root components."""
	session = _session("""\
<cdml><molecule id="m0" name="pair">
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
 <atom id="a2" name="C"><point x="1cm" y="0cm" /></atom>
 <bond id="b1" start="a1" end="a2" type="n1" />
</molecule></cdml>
""")
	result = session.delete_structure(_request(session, bond_ids=("b1",)))

	assert _root_molecules(result.snapshot.cdml) == (("m0", ("a1",), ()), ("m1", ("a2",), ()))
	assert (
		'id="m1"' in result.snapshot.cdml
		and 'name="pair"' not in result.snapshot.cdml.split('id="m1"', 1)[1]
	)


#============================================
def test_central_atom_uses_deterministic_component_ids_and_root_order() -> None:
	"""Split roots reserve opaque document IDs and follow earliest surviving atoms."""
	session = _session(_chain_cdml('<v:reserve id="m1" />'))
	result = session.delete_structure(_request(session, ("a2",)))

	assert result.components == (
		cdml_document.CDMLStructureDeleteComponent("m0", ("a1",), ()),
		cdml_document.CDMLStructureDeleteComponent("m2", ("a3",), ()),
	)
	assert _root_molecules(result.snapshot.cdml) == (("m0", ("a1",), ()), ("m2", ("a3",), ()))


#============================================
def test_selected_atom_and_explicit_incident_bond_are_reported_once() -> None:
	"""One explicit incident bond does not duplicate an implicit atom-edge removal."""
	session = _session(_chain_cdml())
	result = session.delete_structure(_request(session, ("a2",), ("b1",)))

	assert result.removed_bond_ids == ("b1", "b2")
	assert result.components[0].atom_ids == ("a1",)


#============================================
def test_last_atom_removes_the_original_molecule_root() -> None:
	"""Deleting the only atom removes its now-empty direct-root molecule."""
	session = _session("""\
<cdml><molecule id="m0"><atom id="a1" name="C"><point x="0cm" y="0cm" /></atom></molecule></cdml>
""")
	result = session.delete_structure(_request(session, ("a1",)))

	assert result.components == ()
	assert _root_molecules(result.snapshot.cdml) == ()


#============================================
def test_surviving_singletons_and_owned_opaque_descendants_are_preserved() -> None:
	"""Split cloning retains opaque descendants owned by surviving atom and bond nodes."""
	session = _session("""\
<cdml xmlns:v="urn:vendor"><molecule id="m0">
 <atom id="a1" name="C"><point x="0cm" y="0cm" /><v:atom-note>keep atom</v:atom-note></atom>
 <atom id="a2" name="C"><point x="1cm" y="0cm" /></atom>
 <atom id="a3" name="O"><point x="2cm" y="0cm" /></atom>
 <bond id="b1" start="a1" end="a2" type="n1" />
 <bond id="b2" start="a2" end="a3" type="n1"><v:bond-note>keep bond</v:bond-note></bond>
</molecule></cdml>
""")
	result = session.delete_structure(_request(session, bond_ids=("b1",)))

	assert _root_molecules(result.snapshot.cdml) == (
		("m0", ("a1",), ()), ("m1", ("a2", "a3"), ("b2",)),
	)
	assert "keep atom" in result.snapshot.cdml and "keep bond" in result.snapshot.cdml


#============================================
def test_whitespace_only_direct_cdata_is_accepted() -> None:
	"""Whitespace CDATA is character data and does not block structural deletion."""
	session = _session("""\
<cdml><molecule id="m0">
 <![CDATA[
	]]>
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
</molecule></cdml>
""")
	result = session.delete_structure(_request(session, ("a1",)))

	assert result.components == ()


#============================================
@pytest.mark.parametrize("direct_content", (
	pytest.param("<![CDATA[not whitespace]]>", id="cdata"),
	pytest.param("not whitespace", id="text"),
	pytest.param("<!-- direct comment -->", id="comment"),
	pytest.param("<?direct processing?>", id="processing-instruction"),
))
def test_unsupported_direct_character_data_or_nondata_nodes_are_atomic(
		direct_content: str,
		) -> None:
	"""Non-whitespace character data and non-data direct nodes are rejected."""
	session = _session(f"""\
<cdml><molecule id="m0">
 {direct_content}
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
</molecule></cdml>
""")
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.delete_structure(_request(session, ("a1",)))

	assert _state(session) == before


#============================================
def test_unsupported_root_molecule_attribute_is_atomic() -> None:
	"""An unowned root attribute keeps the narrow deletion grammar inert."""
	session = _session("""\
<cdml><molecule id="m0" color="#112233">
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
</molecule></cdml>
""")
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.delete_structure(_request(session, ("a1",)))

	assert _state(session) == before


#============================================
@pytest.mark.parametrize("delete_request", (
	cdml_document.CDMLStructureDeleteRequest(0, " ", ("a1",), (), None),
	cdml_document.CDMLStructureDeleteRequest(0, "m0", ("\t",), (), None),
	cdml_document.CDMLStructureDeleteRequest(0, "m0", (), ("\n",), None),
))
def test_whitespace_only_request_ids_are_atomic(delete_request: object) -> None:
	"""Every durable ID in the exact request must contain non-whitespace text."""
	session = _session(_chain_cdml())
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.delete_structure(delete_request)

	assert _state(session) == before


#============================================
def test_authored_surrounding_id_whitespace_is_not_normalized() -> None:
	"""Durable IDs retain authored spelling when they contain non-whitespace text."""
	session = _session("""\
<cdml><molecule id=" m0 ">
 <atom id=" a1 " name="C"><point x="0cm" y="0cm" /></atom>
 <atom id=" a2 " name="C"><point x="1cm" y="0cm" /></atom>
 <bond id=" b1 " start=" a1 " end=" a2 " type="n1" />
</molecule></cdml>
""")
	request = cdml_document.CDMLStructureDeleteRequest(
		session.revision, " m0 ", (), (" b1 ",), None,
	)
	result = session.delete_structure(request)

	assert result.removed_bond_ids == (" b1 ",)
	assert result.components[0] == cdml_document.CDMLStructureDeleteComponent(
		" m0 ", (" a1 ",), (),
	)


#============================================
@pytest.mark.parametrize("cdml_text, delete_request", (
	pytest.param(
		"""\
<cdml><molecule id=" ">
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
</molecule></cdml>
""",
		cdml_document.CDMLStructureDeleteRequest(0, " ", ("a1",), (), None),
		id="molecule",
	),
	pytest.param(
		"""\
<cdml><molecule id="m0">
 <atom id=" " name="C"><point x="0cm" y="0cm" /></atom>
 <atom id="a1" name="C"><point x="1cm" y="0cm" /></atom>
</molecule></cdml>
""",
		cdml_document.CDMLStructureDeleteRequest(0, "m0", ("a1",), (), None),
		id="atom",
	),
	pytest.param(
		"""\
<cdml><molecule id="m0">
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
 <atom id="a2" name="C"><point x="1cm" y="0cm" /></atom>
 <bond id=" " start="a1" end="a2" type="n1" />
</molecule></cdml>
""",
		cdml_document.CDMLStructureDeleteRequest(0, "m0", ("a2",), (), None),
		id="bond",
	),
))
def test_whitespace_only_source_ids_in_strict_sessions_are_atomic(
		cdml_text: str, delete_request: object,
		) -> None:
	"""Compatibility-strict sessions may retain these IDs, but Delete cannot use them."""
	session = _session(cdml_text)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.delete_structure(delete_request)

	assert _state(session) == before


#============================================
@pytest.mark.parametrize("bond_xml", (
	pytest.param('<bond id="b1" end="a2" type="n1" />', id="missing-endpoint"),
	pytest.param('<bond id="b1" start="a1" end="a1" type="n1" />', id="self-edge"),
))
def test_malformed_topology_in_strict_sessions_is_atomic(bond_xml: str) -> None:
	"""Operation topology checks reject strict-compatible missing or self endpoints."""
	session = _session(f"""\
<cdml><molecule id="m0">
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
 <atom id="a2" name="C"><point x="1cm" y="0cm" /></atom>
 {bond_xml}
</molecule></cdml>
""")
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.delete_structure(_request(session, ("a2",)))

	assert _state(session) == before


#============================================
def test_unresolved_bond_endpoint_is_rejected_by_public_strict_load() -> None:
	"""The strict IDREF gate rejects unresolved topology before a session can exist."""
	cdml_text = """\
<cdml><molecule id="m0">
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
 <bond id="b1" start="a1" end="missing" type="n1" />
</molecule></cdml>
"""

	with pytest.raises(cdml_document.CDMLValidationError, match="unresolved end reference"):
		cdml_document.CDMLDocumentSession.load(cdml_text)


#============================================
@pytest.mark.parametrize("delete_request", (
	cdml_document.CDMLStructureDeleteRequest(0, "m0", (), (), None),
	cdml_document.CDMLStructureDeleteRequest(0, "m0", ("a1", "a1"), (), None),
	cdml_document.CDMLStructureDeleteRequest(0, "m0", ("missing",), (), None),
))
def test_invalid_or_ambiguous_targets_are_atomic(delete_request: object) -> None:
	"""Malformed, repeated, and missing direct targets leave one session unchanged."""
	session = _session(_chain_cdml())
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.delete_structure(delete_request)

	assert _state(session) == before


#============================================
def test_stale_structural_delete_is_atomic() -> None:
	"""An obsolete deletion never replays against the newer authoritative revision."""
	session = _session(_chain_cdml())
	stale = _request(session, ("a3",))
	session.commit(expected_revision=0, complete_cdml=session.snapshot().cdml)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.delete_structure(stale)

	assert _state(session) == before


#============================================
def test_unsupported_direct_molecule_content_is_atomic() -> None:
	"""A direct core group keeps the narrow structural-delete grammar inert."""
	session = _session("""\
<cdml><molecule id="m0">
 <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
 <group id="g1" name="OH"><point x="1cm" y="0cm" /></group>
</molecule></cdml>
""")
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.delete_structure(_request(session, ("a1",)))

	assert _state(session) == before


#============================================
@pytest.mark.parametrize("atom_ids, bond_ids", ((("a2",), ()), (("a1", "a2", "a3"), ())))
def test_reaction_referenced_split_or_removal_is_atomic(
		atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> None:
	"""A recognized role protects its molecule from split and removal operations."""
	session = _session(_chain_cdml('<reaction id="r0"><product idref="m0" /></reaction>'))
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError, match="reaction-referenced"):
		session.delete_structure(_request(session, atom_ids, bond_ids))

	assert _state(session) == before


#============================================
def test_reaction_referenced_one_component_edit_is_accepted() -> None:
	"""A role remains valid when one surviving component keeps its original root."""
	session = _session(_chain_cdml('<reaction id="r0"><product idref="m0" /></reaction>'))
	result = session.delete_structure(_request(session, ("a3",)))

	assert result.components == (
		cdml_document.CDMLStructureDeleteComponent("m0", ("a1", "a2"), ("b1",)),
	)


#============================================
def test_backend_restore_returns_the_exact_predecessor_snapshot() -> None:
	"""One accepted structural delete uses the ordinary backend undo history."""
	session = _session(_chain_cdml())
	before = session.snapshot()
	deleted = session.delete_structure(_request(session, ("a3",)))
	restored = session.restore(
		target_revision=before.revision,
		expected_revision=deleted.snapshot.revision,
	)

	assert restored.cdml == before.cdml
