"""Behavior tests for explicit durable-ID three-ring Haworth assembly."""

# Standard Library
import dataclasses
import math

# Third Party
import pytest

# Local modules
import oasa.haworth.assembly
import oasa.smiles_lib


#============================================
def _ref(index: int) -> oasa.haworth.assembly.HaworthAtomRef:
	"""Return one stable fixture reference from its intentionally assigned ID."""
	result = oasa.haworth.assembly.HaworthAtomRef("three-rings", f"a{index}")
	return result


#============================================
def _identified_molecule(smiles: str) -> object:
	"""Build a detached graph with the explicit IDs required by the public API."""
	molecule = oasa.smiles_lib.text_to_mol(smiles, calc_coords=1)
	molecule.id = "three-rings"
	for index, atom in enumerate(molecule.vertices):
		atom.id = f"a{index}"
	return molecule


#============================================
def _linear_request() -> oasa.haworth.assembly.HaworthAssemblyRequest:
	"""Return a fully explicit three-ring chain without topology discovery."""
	rings = (
		oasa.haworth.assembly.HaworthRingDeclaration(
			"r1", tuple(_ref(index) for index in (0, 1, 2, 3, 4, 5)), "canonical", "front"),
		oasa.haworth.assembly.HaworthRingDeclaration(
			"r2", tuple(_ref(index) for index in (8, 9, 10, 11, 12, 13)), "canonical", "front"),
		oasa.haworth.assembly.HaworthRingDeclaration(
			"r3", tuple(_ref(index) for index in (16, 17, 18, 19, 20, 21)), "canonical", "front"),
	)
	links = (
		oasa.haworth.assembly.HaworthLinkDeclaration(
			"l1", "r1", _ref(5), "r2", _ref(8), (_ref(6), _ref(7)), "east"),
		oasa.haworth.assembly.HaworthLinkDeclaration(
			"l2", "r2", _ref(13), "r3", _ref(16), (_ref(14), _ref(15)), "south"),
	)
	result = oasa.haworth.assembly.HaworthAssemblyRequest("three-rings", "r1", rings, links)
	return result


#============================================
def _branched_request() -> oasa.haworth.assembly.HaworthAssemblyRequest:
	"""Return a rooted east/south branch with separately declared link paths."""
	rings = (
		oasa.haworth.assembly.HaworthRingDeclaration(
			"r0", tuple(_ref(index) for index in (0, 1, 2, 12, 13, 14)), "canonical", "front"),
		oasa.haworth.assembly.HaworthRingDeclaration(
			"re", tuple(_ref(index) for index in (6, 7, 8, 9, 10, 11)), "canonical", "front"),
		oasa.haworth.assembly.HaworthRingDeclaration(
			"rs", tuple(_ref(index) for index in (17, 18, 19, 20, 21, 22)), "canonical", "front"),
	)
	links = (
		oasa.haworth.assembly.HaworthLinkDeclaration(
			"east", "r0", _ref(2), "re", _ref(6), (_ref(3), _ref(4), _ref(5)), "east"),
		oasa.haworth.assembly.HaworthLinkDeclaration(
			"west", "r0", _ref(14), "rs", _ref(17), (_ref(15), _ref(16)), "west"),
	)
	result = oasa.haworth.assembly.HaworthAssemblyRequest("three-rings", "r0", rings, links)
	return result


#============================================
def _style_facts(molecule: object) -> tuple[tuple[str, str], ...]:
	"""Return only durable Haworth paint semantics, independent of edge ordering."""
	result = tuple(sorted(
		(bond.type, bond.properties_["haworth_position"])
		for bond in molecule.edges if "haworth_position" in bond.properties_
	))
	return result


#============================================
def _state(molecule: object) -> tuple:
	"""Capture all mutable fields this operation is permitted to change."""
	result = (
		tuple((atom.x, atom.y) for atom in molecule.vertices),
		tuple((bond.type, tuple(bond.vertices), tuple(sorted(bond.properties_.items())))
			for bond in molecule.edges),
	)
	return result


#============================================
def test_linear_explicit_assembly_applies_complete_haworth_semantics() -> None:
	"""A declared three-ring chain receives finite coordinates and each ring's style set."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	plan = oasa.haworth.assembly.plan_haworth_assembly(molecule, _linear_request())
	for link in plan.request.links:
		parent = next(ring for ring in plan.rings if ring.ring_id == link.parent_ring_id)
		child = next(ring for ring in plan.rings if ring.ring_id == link.child_ring_id)
		link_plan = next(item for item in plan.links if item.link_id == link.link_id)
		path = (
			parent.coordinates[parent.vertex_refs.index(link.parent_attachment)],
			*link_plan.coordinates,
			child.coordinates[child.vertex_refs.index(link.child_attachment)],
		)
		assert all(math.isclose(math.dist(first, second), plan.request.bond_length)
			for first, second in zip(path, path[1:]))
	oasa.haworth.assembly.apply_haworth_assembly(molecule, plan)
	assert all(math.isfinite(atom.x) and math.isfinite(atom.y) for atom in molecule.vertices)
	assert _style_facts(molecule).count(("q", "front")) == 3


#============================================
def test_branched_explicit_assembly_preserves_declared_parent_child_identity() -> None:
	"""One root can place distinct east and west children without hidden inference."""
	molecule = _identified_molecule("O1CC(COCC2OCCCC2)CCC1OCC3OCCCC3")
	plan = oasa.haworth.assembly.plan_haworth_assembly(molecule, _branched_request())
	oasa.haworth.assembly.apply_haworth_assembly(molecule, plan)
	assert {link.link_id for link in plan.links} == {"east", "west"}
	assert _style_facts(molecule).count(("w", "front")) == 6


#============================================
def test_stale_plan_rejection_is_atomic() -> None:
	"""A changed graph fails before any planned coordinate or style mutation."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	plan = oasa.haworth.assembly.plan_haworth_assembly(molecule, _linear_request())
	molecule.vertices[0].symbol = "N"
	before = _state(molecule)
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyApplicationError, match="does not match"):
		oasa.haworth.assembly.apply_haworth_assembly(molecule, plan)
	assert _state(molecule) == before

#============================================
def test_duplicate_sibling_direction_is_a_declaration_error() -> None:
	"""Ambiguous branch placement is rejected as a caller declaration defect."""
	molecule = _identified_molecule("O1CC(COCC2OCCCC2)CCC1OCC3OCCCC3")
	request = _branched_request()
	duplicate = oasa.haworth.assembly.HaworthLinkDeclaration(
		"south", "r0", _ref(14), "rs", _ref(17), (_ref(15), _ref(16)), "east")
	invalid = oasa.haworth.assembly.HaworthAssemblyRequest(
		request.molecule_id, request.root_ring_id, request.rings, (request.links[0], duplicate))
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyDeclarationError, match="directions"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, invalid)


#============================================
def test_ring_declarations_must_be_vertex_disjoint() -> None:
	"""A durable ID cannot make two declared rings fused or spiro by accident."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	request = _linear_request()
	reused_ring = dataclasses.replace(request.rings[1], vertices=request.rings[0].vertices)
	invalid = dataclasses.replace(request, rings=(request.rings[0], reused_ring, request.rings[2]))
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyTopologyError, match="vertex-disjoint"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, invalid)


#============================================
def test_undeclared_interring_bridge_is_rejected() -> None:
	"""A second connection between declared rings cannot silently change topology."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	molecule.add_edge(molecule.vertices[0], molecule.vertices[8])
	with pytest.raises(
			oasa.haworth.assembly.HaworthAssemblyTopologyError,
			match="undeclared exterior bridge"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, _linear_request())


#============================================
def test_link_topology_drift_rejection_is_atomic() -> None:
	"""A bond-chemistry change invalidates the fingerprint before application."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	plan = oasa.haworth.assembly.plan_haworth_assembly(molecule, _linear_request())
	next(iter(molecule.edges)).order = 2
	before = _state(molecule)
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyApplicationError, match="does not match"):
		oasa.haworth.assembly.apply_haworth_assembly(molecule, plan)
	assert _state(molecule) == before


#============================================
def test_declared_ring_edge_must_remain_a_simple_single_bond() -> None:
	"""A chemically incompatible declared cycle fails during planning."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	molecule.get_edge_between(molecule.vertices[0], molecule.vertices[1]).order = 2
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyTopologyError, match="ring edge"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, _linear_request())


#============================================
def test_unknown_attachment_id_is_rejected_without_inference() -> None:
	"""Callers must supply an addressable durable attachment, never an index fallback."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	request = _linear_request()
	invalid_link = dataclasses.replace(
		request.links[0], parent_attachment=oasa.haworth.assembly.HaworthAtomRef(
			"three-rings", "missing"))
	invalid = dataclasses.replace(request, links=(invalid_link, request.links[1]))
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyIdentityError, match="unknown"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, invalid)


#============================================
def test_connector_identity_cannot_be_reused_between_links() -> None:
	"""Two declared paths cannot silently share a connector atom."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	request = _linear_request()
	invalid_link = dataclasses.replace(request.links[1], connector_atoms=(_ref(7), _ref(15)))
	invalid = dataclasses.replace(request, links=(request.links[0], invalid_link))
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyTopologyError, match="cannot be reused"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, invalid)


#============================================
def test_child_ring_cannot_have_two_declared_parents() -> None:
	"""The ring incidence contract is a rooted tree rather than a cycle basis guess."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	request = _linear_request()
	second_parent = oasa.haworth.assembly.HaworthLinkDeclaration(
		"l2", "r3", _ref(16), "r2", _ref(13), (_ref(15), _ref(14)), "west")
	invalid = dataclasses.replace(request, links=(request.links[0], second_parent))
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyTopologyError, match="multiple parents"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, invalid)


#============================================
def test_connector_branch_is_rejected_before_layout() -> None:
	"""A declared linkage cannot hide an undeclared side branch on its path."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	branch = molecule.create_vertex()
	branch.id = "branch"
	branch.symbol = "C"
	molecule.add_vertex(branch)
	molecule.add_edge(molecule.vertices[6], branch)
	with pytest.raises(
			oasa.haworth.assembly.HaworthAssemblyTopologyError,
			match="undeclared branches"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, _linear_request())


#============================================
def test_nonfinite_existing_coordinate_is_a_geometry_error() -> None:
	"""Planning validates all resulting coordinates before any mutation is possible."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	substituent = molecule.create_vertex()
	substituent.id = "substituent"
	substituent.symbol = "C"
	substituent.x = float("nan")
	molecule.add_vertex(substituent)
	molecule.add_edge(molecule.vertices[0], substituent)
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyGeometryError, match="finite"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, _linear_request())


#============================================
#============================================
def test_incompatible_cardinal_face_declaration_is_rejected() -> None:
	"""A link direction outside the legacy template's compatible face sector fails."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	request = _linear_request()
	incompatible_link = dataclasses.replace(request.links[1], direction="east")
	incompatible = dataclasses.replace(
		request, links=(request.links[0], incompatible_link))
	with pytest.raises(
			oasa.haworth.assembly.HaworthAssemblyGeometryError,
			match="attachment faces conflict"):
		oasa.haworth.assembly.plan_haworth_assembly(molecule, incompatible)


#============================================
def test_incident_link_overlap_is_rejected_before_mutation() -> None:
	"""A caller cannot apply a stale-looking plan with a link covering a ring edge."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	plan = oasa.haworth.assembly.plan_haworth_assembly(molecule, _linear_request())
	first_ring = plan.rings[0]
	first_link = plan.links[0]
	attachment = first_ring.vertex_refs.index(plan.request.links[0].parent_attachment)
	overlapped = first_ring.coordinates[(attachment - 1) % len(first_ring.coordinates)]
	bad_link = dataclasses.replace(first_link, coordinates=(overlapped,) + first_link.coordinates[1:])
	bad_plan = dataclasses.replace(plan, links=(bad_link,) + plan.links[1:])
	before = _state(molecule)
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyGeometryError, match="overlapping"):
		oasa.haworth.assembly.apply_haworth_assembly(molecule, bad_plan)
	assert _state(molecule) == before


#============================================
def test_nonbonded_clearance_rejection_is_atomic() -> None:
	"""A moved unrelated atom cannot crowd the planned assembly before application."""
	molecule = _identified_molecule("O1CCCCC1OCC2OCCCC2OCC3OCCCC3")
	unrelated = molecule.create_vertex()
	unrelated.id = "unrelated"
	unrelated.symbol = "C"
	unrelated.x = 1000.0
	unrelated.y = 1000.0
	molecule.add_vertex(unrelated)
	plan = oasa.haworth.assembly.plan_haworth_assembly(molecule, _linear_request())
	target = plan.rings[-1].coordinates[0]
	unrelated.x, unrelated.y = target
	before = _state(molecule)
	with pytest.raises(oasa.haworth.assembly.HaworthAssemblyGeometryError, match="clearance"):
		oasa.haworth.assembly.apply_haworth_assembly(molecule, plan)
	assert _state(molecule) == before
