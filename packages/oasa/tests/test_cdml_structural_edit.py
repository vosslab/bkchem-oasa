"""Behavioral tests for backend-authoritative Draw-mode structural edits."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


#============================================
BASE_CDML = """\
<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:vendor="urn:vendor">
 <vendor:note id="opaque_note" marker="keep">unchanged</vendor:note>
 <bk:molecule id="m_existing">
  <bk:atom id="a_existing" name="C"><bk:point x="0cm" y="0cm" /></bk:atom>
 </bk:molecule>
</bk:cdml>
"""


#============================================
THREE_ATOM_CDML = """\
<cdml>
 <molecule id="m_one">
  <atom id="a_one" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="a_two" name="C"><point x="1cm" y="0cm" /></atom>
  <atom id="a_three" name="O"><point x="2cm" y="0cm" /></atom>
  <bond id="b_one" start="a_one" end="a_two" type="n1" />
 </molecule>
 <molecule id="m_two">
  <atom id="a_other" name="N"><point x="3cm" y="0cm" /></atom>
 </molecule>
</cdml>
"""


#============================================
def _request(revision: int, kind: str, **values: object) -> cdml_document.CDMLStructuralEditRequest:
	"""Build one plain structural request with the selected Draw-mode settings."""
	settings = {
		"bond_type": "n",
		"bond_order": 1,
		"simple_double": False,
	}
	settings.update(values)
	return cdml_document.CDMLStructuralEditRequest(
		expected_revision=revision,
		kind=kind,
		**settings,
	)


#============================================
def _record(cdml_text: str, identifier: str) -> cdml_document.CDMLObjectRecord:
	"""Read an accepted persistent object through the owning CDML boundary."""
	record = cdml_document.CDMLDocument.parse(cdml_text, validation="strict").find_by_id(identifier)
	assert record is not None
	return record


#============================================
def _accepted_element(cdml_text: str, identifier: str) -> object:
	"""Read one accepted record structurally after the owning CDML boundary."""
	accepted = cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for element in dom.getElementsByTagName("*"):
		if element.getAttribute("id") == identifier:
			return element
	raise AssertionError(f"accepted CDML did not contain {identifier}")


#============================================
def _point_attributes(element: object) -> tuple[str, str]:
	"""Read the direct point values independently of the document namespace prefix."""
	for child in element.childNodes:
		if child.nodeType != child.ELEMENT_NODE:
			continue
		if child.localName == "point" or child.tagName == "point":
			return child.getAttribute("x"), child.getAttribute("y")
	raise AssertionError("accepted atom did not contain a direct point")


#============================================
def _root_molecule_ids(cdml_text: str) -> tuple[str, ...]:
	"""Return direct-root molecule IDs in persistent document order."""
	accepted = cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	root = accepted._dom_document.documentElement
	identifiers = []
	for child in root.childNodes:
		if child.nodeType != child.ELEMENT_NODE:
			continue
		if child.localName == "molecule" or child.tagName == "molecule":
			identifiers.append(child.getAttribute("id"))
	return tuple(identifiers)


#============================================
def _state(session: cdml_document.CDMLDocumentSession) -> tuple[int, str]:
	"""Capture observable authoritative state for rejected-operation checks."""
	snapshot = session.snapshot()
	return snapshot.revision, snapshot.cdml


#============================================
def test_blank_pair_creates_a_new_root_molecule_without_rewriting_opaque_content() -> None:
	"""Every blank gesture receives a new backend-owned molecule and bonded pair."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	first = session.edit_structure(_request(
		session.revision,
		"create-bonded-pair",
		source_position=(10.0, 20.0),
		target_position=(40.0, 20.0),
		element="O",
	))
	second = session.edit_structure(_request(
		session.revision,
		"create-bonded-pair",
		source_position=(50.0, 20.0),
		target_position=(80.0, 20.0),
		element="N",
	))
	accepted = second.snapshot.cdml
	bond = _accepted_element(accepted, second.created_bond_ids[0])

	assert (bond.getAttribute("start"), bond.getAttribute("end")) == second.created_atom_ids
	assert (
		'marker="keep">unchanged</vendor:note>' in accepted
		and _root_molecule_ids(accepted) == ("m_existing", first.created_molecule_id, second.created_molecule_id)
	)


#============================================
def test_extend_atom_allocates_new_ids_inside_the_named_direct_root_molecule() -> None:
	"""An atom extension leaves the source molecule authoritative and addressable."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	result = session.edit_structure(_request(
		session.revision,
		"extend-atom",
		molecule_id="m_existing",
		source_atom_id="a_existing",
		target_position=(28.0, 0.0),
		element="Cl",
	))
	bond = _accepted_element(result.snapshot.cdml, result.created_bond_ids[0])

	assert (bond.getAttribute("start"), bond.getAttribute("end")) == ("a_existing", result.created_atom_ids[0])
	assert result.commit.id_map == {}


#============================================
def test_join_atoms_adds_one_new_edge_between_existing_same_molecule_atoms() -> None:
	"""A same-root join preserves existing topology and assigns the new bond ID."""
	session = cdml_document.CDMLDocumentSession.load(THREE_ATOM_CDML)
	result = session.edit_structure(_request(
		session.revision,
		"join-atoms",
		molecule_id="m_one",
		source_atom_id="a_two",
		target_atom_id="a_three",
	))
	bond = _accepted_element(result.snapshot.cdml, result.created_bond_ids[0])

	assert (bond.getAttribute("start"), bond.getAttribute("end")) == ("a_two", "a_three")
	assert _record(result.snapshot.cdml, "b_one").identifier == "b_one"


#============================================
def test_opaque_identifiers_reserve_generated_durable_ids() -> None:
	"""Opaque ID declarations remain unavailable to backend structural allocation."""
	cdml_text = BASE_CDML.replace(
		'<vendor:note id="opaque_note" marker="keep">',
		'<vendor:note id="m1" marker="keep"><vendor:reserved id="a1" /><vendor:reserved id="b1" /></vendor:note><vendor:note id="opaque_note" marker="keep">',
	)
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	result = session.edit_structure(_request(
		session.revision,
		"create-bonded-pair",
		source_position=(0.0, 0.0),
		target_position=(72.0, 36.0),
		element="C",
	))

	assert (result.created_molecule_id, result.created_atom_ids, result.created_bond_ids) == (
		"m2", ("a2", "a3"), ("b2",),
	)
	target_coordinates = _point_attributes(_accepted_element(
		result.snapshot.cdml,
		result.created_atom_ids[1],
	))
	assert target_coordinates == (
		"2.540cm", "1.270cm",
	)


#============================================
def test_join_ignores_unrelated_supported_non_atom_bonds() -> None:
	"""An existing group edge cannot block a distinct direct atom-to-atom join."""
	cdml_text = """
<cdml>
 <molecule id="m_one">
  <atom id="a_one" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="a_two" name="C"><point x="1cm" y="0cm" /></atom>
  <group id="g_one" name="OH"><point x="2cm" y="0cm" /></group>
  <bond id="b_group" start="a_one" end="g_one" type="n1" />
 </molecule>
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	result = session.edit_structure(_request(
		session.revision,
		"join-atoms",
		molecule_id="m_one",
		source_atom_id="a_one",
		target_atom_id="a_two",
	))
	bond = _accepted_element(result.snapshot.cdml, result.created_bond_ids[0])

	assert (bond.getAttribute("start"), bond.getAttribute("end")) == ("a_one", "a_two")
	assert _accepted_element(result.snapshot.cdml, "b_group").getAttribute("end") == "g_one"


#============================================
@pytest.mark.parametrize("kind, values", (
	("join-atoms", {"molecule_id": "m_one", "source_atom_id": "a_one", "target_atom_id": "a_one"}),
	("join-atoms", {"molecule_id": "m_one", "source_atom_id": "a_one", "target_atom_id": "a_two"}),
	("join-atoms", {"molecule_id": "m_one", "source_atom_id": "a_one", "target_atom_id": "a_other"}),
	("extend-atom", {"molecule_id": "m_one", "source_atom_id": "a_one", "target_position": (float("inf"), 0.0), "element": "C"}),
	("create-bonded-pair", {"source_position": (0.0, 0.0), "target_position": (28.0, 0.0), "element": "NotAnElement"}),
	("join-atoms", {"molecule_id": "m_one", "source_atom_id": "a_one", "target_atom_id": "a_three", "bond_order": 4}),
	("join-atoms", {"molecule_id": "m_one", "source_atom_id": "a_one", "target_atom_id": "a_three", "bond_type": "q", "bond_order": 2}),
))
def test_invalid_structural_topology_or_coordinates_leave_the_session_unchanged(
		kind: str, values: dict[str, object],
		) -> None:
	"""Rejected structural requests cannot alter topology, IDs, or revisions."""
	session = cdml_document.CDMLDocumentSession.load(THREE_ATOM_CDML)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.edit_structure(_request(session.revision, kind, **values))

	assert _state(session) == before


#============================================
def test_stale_structural_request_leaves_the_newer_authoritative_snapshot_unchanged() -> None:
	"""Optimistic revision conflicts never replay an old Draw-mode gesture."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	request = _request(
		session.revision,
		"create-bonded-pair",
		source_position=(0.0, 0.0),
		target_position=(28.0, 0.0),
		element="C",
	)
	session.edit_structure(request)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.edit_structure(request)

	assert _state(session) == before


#============================================
@pytest.mark.parametrize(("bond_type", "reverses_endpoints"), (
	("w", True),
	("h", True),
	("s", False),
))
def test_bond_tool_preserves_canonical_directed_and_wavy_semantics(
		bond_type: str, reverses_endpoints: bool,
		) -> None:
	"""Repeated selected tools change only the documented directed bond records."""
	cdml_text = THREE_ATOM_CDML.replace('type="n1" />', f'type="{bond_type}1" />', 1)
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	result = session.edit_structure(_request(
		session.revision,
		"apply-bond-tool",
		molecule_id="m_one",
		bond_id="b_one",
		bond_type=bond_type,
	))
	bond = _accepted_element(result.snapshot.cdml, "b_one")
	expected_endpoints = ("a_two", "a_one") if reverses_endpoints else ("a_one", "a_two")

	assert bond.getAttribute("type") == f"{bond_type}1"
	assert (bond.getAttribute("start"), bond.getAttribute("end")) == expected_endpoints


#============================================
def test_bond_tool_cycles_the_current_normal_and_dashed_selections() -> None:
	"""Normal and dashed single selections retain the established 1-2-3 cycle."""
	session = cdml_document.CDMLDocumentSession.load(THREE_ATOM_CDML)
	first = session.edit_structure(_request(
		session.revision,
		"apply-bond-tool",
		molecule_id="m_one",
		bond_id="b_one",
		bond_type="n",
	))
	second = session.edit_structure(_request(
		session.revision,
		"apply-bond-tool",
		molecule_id="m_one",
		bond_id="b_one",
		bond_type="d",
	))
	third = session.edit_structure(_request(
		session.revision,
		"apply-bond-tool",
		molecule_id="m_one",
		bond_id="b_one",
		bond_type="d",
	))

	assert _accepted_element(first.snapshot.cdml, "b_one").getAttribute("type") == "n2"
	assert (
		_accepted_element(second.snapshot.cdml, "b_one").getAttribute("type"),
		_accepted_element(third.snapshot.cdml, "b_one").getAttribute("type"),
	) == ("d1", "d2")


#============================================
def test_simple_double_is_persistent_for_a_normal_double_bond() -> None:
	"""The selected normal-double depiction reaches canonical CDML durably."""
	session = cdml_document.CDMLDocumentSession.load(THREE_ATOM_CDML)
	result = session.edit_structure(_request(
		session.revision,
		"apply-bond-tool",
		molecule_id="m_one",
		bond_id="b_one",
		bond_type="n",
		bond_order=2,
		simple_double=True,
	))
	bond = _accepted_element(result.snapshot.cdml, "b_one")

	assert (bond.getAttribute("type"), bond.getAttribute("simple_double")) == ("n2", "1")
	assert result.updated_bond_ids == ("b_one",)


#============================================
def test_styled_triple_structural_edit_persists_outer_lane_selection() -> None:
	"""Authored styled triples retain the selected outer-lane depiction."""
	session = cdml_document.CDMLDocumentSession.load(THREE_ATOM_CDML)
	result = session.edit_structure(_request(
		session.revision,
		"apply-bond-tool",
		molecule_id="m_one",
		bond_id="b_one",
		bond_type="o",
		bond_order=3,
		simple_double=False,
	))
	bond = _accepted_element(result.snapshot.cdml, "b_one")

	assert (bond.getAttribute("type"), bond.getAttribute("simple_double")) == ("o3", "0")


#============================================
def test_bond_tool_rejects_a_nested_or_missing_edit_target_atomically() -> None:
	"""Opaque or nested records cannot be selected through the core edit grammar."""
	cdml_text = """\
<cdml xmlns:vendor="urn:vendor">
 <vendor:molecule id="m_hidden"><atom id="a_hidden" name="C"><point x="0cm" y="0cm" /></atom></vendor:molecule>
 <molecule id="m_visible"><atom id="a_visible" name="C"><point x="0cm" y="0cm" /></atom></molecule>
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.edit_structure(_request(
			session.revision,
			"apply-bond-tool",
			molecule_id="m_hidden",
			bond_id="b_missing",
		))

	assert _state(session) == before
