"""Focused topology and geometry tests for direct glycosidic Haworth plans."""

# Standard Library
import math

# Third Party
import pytest

# Local modules
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
import oasa.haworth.multiring_layout


#============================================
def _add_ring(mol: object, size: int, oxygen_index: int=0) -> list[object]:
	"""Add one simple C/O ring and return its atoms in construction order."""
	atoms = []
	for index in range(size):
		symbol = "O" if index == oxygen_index else "C"
		atom = oasa.atom_lib.Atom(symbol=symbol)
		mol.add_vertex(atom)
		atoms.append(atom)
	for index, atom in enumerate(atoms):
		next_atom = atoms[(index + 1) % size]
		mol.add_edge(atom, next_atom, oasa.bond_lib.Bond(order=1, type="n"))
	return atoms


#============================================
def _add_bond(mol: object, first: object, second: object) -> None:
	"""Connect two already constructed atoms with a normal single bond."""
	mol.add_edge(first, second, oasa.bond_lib.Bond(order=1, type="n"))


#============================================
def _direct_disaccharide(
		left_size: int=6,
		right_size: int=5,
		left_attachment_index: int=0,
		right_attachment_index: int=1) -> object:
	"""Build two C/O rings with one direct external oxygen bridge."""
	mol = oasa.molecule_lib.Molecule()
	left_oxygen_index = 2 if left_size == 6 else 4
	right_oxygen_index = 2 if right_size == 6 else 4
	pyranose = _add_ring(mol, left_size, oxygen_index=left_oxygen_index)
	furanose = _add_ring(mol, right_size, oxygen_index=right_oxygen_index)
	bridge = oasa.atom_lib.Atom(symbol="O")
	mol.add_vertex(bridge)
	_add_bond(mol, bridge, pyranose[left_attachment_index])
	_add_bond(mol, bridge, furanose[right_attachment_index])
	return mol


#============================================
def _bridge_distances(plan: object) -> tuple[float, float]:
	"""Return the two planned atom-to-oxygen bridge distances."""
	left_index = plan.left_ring.vertex_indexes.index(plan.bridge.left_attachment_vertex_index)
	right_index = plan.right_ring.vertex_indexes.index(plan.bridge.right_attachment_vertex_index)
	left_x, left_y = plan.left_ring.coordinates[left_index]
	right_x, right_y = plan.right_ring.coordinates[right_index]
	bridge_x, bridge_y = plan.bridge.coordinate
	distances = (
		math.hypot(left_x - bridge_x, left_y - bridge_y),
		math.hypot(right_x - bridge_x, right_y - bridge_y),
	)
	return distances


#============================================
def _bridge_crosses_ring(plan: object, ring: object, attachment_vertex_index: int) -> bool:
	"""Check bridge segments against every nonincident ring edge."""
	attachment_index = ring.vertex_indexes.index(attachment_vertex_index)
	attachment = ring.coordinates[attachment_index]
	for index, start in enumerate(ring.coordinates):
		end_index = (index + 1) % len(ring.coordinates)
		if index == attachment_index or end_index == attachment_index:
			continue
		end = ring.coordinates[end_index]
		if _properly_intersects(attachment, plan.bridge.coordinate, start, end):
			return True
	return False


#============================================
def _properly_intersects(
		first_start: tuple[float, float],
		first_end: tuple[float, float],
		second_start: tuple[float, float],
		second_end: tuple[float, float]) -> bool:
	"""Return whether two non-collinear line segments have a proper crossing."""
	first_a = _orientation(first_start, first_end, second_start)
	first_b = _orientation(first_start, first_end, second_end)
	second_a = _orientation(second_start, second_end, first_start)
	second_b = _orientation(second_start, second_end, first_end)
	result = (first_a * first_b < 0.0) and (second_a * second_b < 0.0)
	return result


#============================================
def _orientation(
		start: tuple[float, float],
		end: tuple[float, float],
		point: tuple[float, float]) -> float:
	"""Return the signed area predicate for one segment and point."""
	start_x, start_y = start
	end_x, end_y = end
	point_x, point_y = point
	value = ((end_x - start_x) * (point_y - start_y)) - ((end_y - start_y) * (point_x - start_x))
	return value


#============================================
def _add_shared_ring_path(mol: object, start: object, end: object, count: int) -> None:
	"""Close a simple ring by adding a fresh path between two existing atoms."""
	previous = start
	for _index in range(count):
		atom = oasa.atom_lib.Atom(symbol="C")
		mol.add_vertex(atom)
		_add_bond(mol, previous, atom)
		previous = atom
	_add_bond(mol, previous, end)


#============================================
def _shared_ring_molecule(shared_edge: bool) -> object:
	"""Build a fused or spiro two-cycle topology for rejection coverage."""
	mol = oasa.molecule_lib.Molecule()
	first_ring = _add_ring(mol, 6, oxygen_index=0)
	if shared_edge:
		_add_shared_ring_path(mol, first_ring[0], first_ring[1], 4)
	else:
		_add_shared_ring_path(mol, first_ring[0], first_ring[0], 4)
	return mol


#============================================
def test_direct_sucrose_like_bridge_has_canonical_ring_semantics() -> None:
	mol = _direct_disaccharide()
	original_geometry = (tuple((atom.x, atom.y) for atom in mol.vertices), tuple((bond.order, bond.type) for bond in mol.edges))
	plan = oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(mol)
	assert (plan.left_ring.ring_type, plan.right_ring.ring_type) == ("pyranose", "furanose")
	assert (tuple((atom.x, atom.y) for atom in mol.vertices), tuple((bond.order, bond.type) for bond in mol.edges)) == original_geometry


#============================================
def test_plan_is_deterministic_with_nonfinite_input_coordinates() -> None:
	mol = _direct_disaccharide()
	mol.vertices[0].x = float("nan")
	mol.vertices[0].y = float("inf")
	first_plan = oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(mol, bond_length=17.0)
	second_plan = oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(mol, bond_length=17.0)
	assert first_plan == second_plan
	assert _bridge_distances(first_plan) == pytest.approx((17.0, 17.0))


#============================================
def test_c3_to_c3_bridge_does_not_cross_nonincident_ring_edges() -> None:
	plan = oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(
		_direct_disaccharide(left_attachment_index=3, right_attachment_index=3))
	assert not _bridge_crosses_ring(plan, plan.left_ring, plan.bridge.left_attachment_vertex_index) and not _bridge_crosses_ring(plan, plan.right_ring, plan.bridge.right_attachment_vertex_index)


#============================================
@pytest.mark.parametrize("left_size,right_size", ((5, 5), (6, 6)))
def test_same_size_ring_combinations_keep_direct_bridge_geometry(left_size: int, right_size: int) -> None:
	plan = oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(
		_direct_disaccharide(left_size=left_size, right_size=right_size), bond_length=23.0)
	assert _bridge_distances(plan) == pytest.approx((23.0, 23.0))
	assert not _bridge_crosses_ring(plan, plan.left_ring, plan.bridge.left_attachment_vertex_index) and not _bridge_crosses_ring(plan, plan.right_ring, plan.bridge.right_attachment_vertex_index)


#============================================
@pytest.mark.parametrize("shared_edge", (False, True))
def test_fused_and_spiro_rings_are_rejected(shared_edge: bool) -> None:
	with pytest.raises(ValueError, match="vertex-disjoint"):
		oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(_shared_ring_molecule(shared_edge=shared_edge))


#============================================
def test_indirect_oxygen_carbon_linkage_is_rejected() -> None:
	mol = oasa.molecule_lib.Molecule()
	left_ring = _add_ring(mol, 6, oxygen_index=0)
	right_ring = _add_ring(mol, 5, oxygen_index=0)
	bridge = oasa.atom_lib.Atom(symbol="O")
	exocyclic_carbon = oasa.atom_lib.Atom(symbol="C")
	mol.add_vertex(bridge)
	mol.add_vertex(exocyclic_carbon)
	_add_bond(mol, bridge, left_ring[1])
	_add_bond(mol, bridge, exocyclic_carbon)
	_add_bond(mol, exocyclic_carbon, right_ring[1])
	with pytest.raises(ValueError, match="directly bonded"):
		oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(mol)


#============================================
def test_non_single_bridge_bond_is_rejected() -> None:
	non_single = _direct_disaccharide()
	non_single_bridge = non_single.vertices[-1]
	non_single_bond = non_single.get_edge_between(non_single_bridge, non_single.vertices[0])
	non_single_bond.order = 2
	with pytest.raises(ValueError, match="directly bonded"):
		oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(non_single)


#============================================
def test_positional_map_rejects_reordered_vertices() -> None:
	mol = _direct_disaccharide()
	plan = oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(mol)
	mol.vertices.reverse()
	assert not plan.matches_positional_vertex_map(mol)


#============================================
def test_topology_validation_rejects_same_order_bond_chemistry_change() -> None:
	mol = _direct_disaccharide()
	plan = oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(mol)
	bridge_bond = mol.get_edge_between(mol.vertices[-1], mol.vertices[0])
	bridge_bond.order = 2
	assert not plan.matches_molecule_topology(mol)
