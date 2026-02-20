"""Parity tests: Gasteiger edge-based cycle basis vs rustworkx vertex cycle_basis + edge conversion.

Compares the existing get_smallest_independent_cycles_e() (Gasteiger, ~175 lines)
against a thin wrapper that takes rustworkx vertex-based cycle_basis output and
converts each vertex cycle to its edge set. If results match, we can replace the
Gasteiger implementation with the wrapper.
"""

# PIP3 modules
import pytest

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
from oasa import smiles_lib


# test SMILES covering a range of topologies
MOLECULES = {
	"benzene": "c1ccccc1",
	"naphthalene": "c1ccc2ccccc2c1",
	"anthracene": "c1ccc2cc3ccccc3cc2c1",
	"cholesterol": "OC1CCC2(C1)C1CCC3C(CCC4CC(=O)CCC43C)C1CC=C2C1CCCCC1",
	"caffeine": "Cn1c(=O)c2c(ncn2C)n(C)c1=O",
	"cyclopentane": "C1CCCC1",
	"hexane": "CCCCCC",
	"biphenyl": "c1ccc(-c2ccccc2)cc1",
	"cubane": "C12C3C4C1C5C3C4C25",
	"adamantane": "C1C2CC3CC1CC(C2)C3",
	"spiro_compound": "C1CCC2(CC1)CCCC2",
	"steroid_core": "C1CCC2C(C1)CCC1C2CCC2CCCCC21",
}


#============================================
def vertex_cycles_to_edge_cycles(mol, vertex_cycles: list) -> set:
	"""Convert rustworkx vertex-based cycle basis to edge-based cycle sets.

	This is the proposed replacement wrapper for Gasteiger. It takes the
	vertex cycles from get_smallest_independent_cycles() (already delegating
	to rustworkx.cycle_basis) and converts each to a frozenset of edges
	by walking consecutive vertex pairs.

	Args:
		mol: Graph instance with edge lookup capability.
		vertex_cycles: List of sets of vertices (from cycle_basis).

	Returns:
		Set of frozensets of edges (same format as get_smallest_independent_cycles_e).
	"""
	edge_cycles = set()
	for v_cycle in vertex_cycles:
		# convert set to ordered list by walking adjacency
		ordered = _order_cycle_vertices(v_cycle)
		# collect edges between consecutive vertices
		edges = set()
		for i in range(len(ordered)):
			v1 = ordered[i]
			v2 = ordered[(i + 1) % len(ordered)]
			edge = v1.get_edge_leading_to(v2)
			if edge is not None:
				edges.add(edge)
		if edges:
			edge_cycles.add(frozenset(edges))
	return edge_cycles


#============================================
def _order_cycle_vertices(v_set: set) -> list:
	"""Order a set of cycle vertices into a connected ring path.

	Walks the adjacency from an arbitrary start vertex, only visiting
	vertices in v_set, to produce a sequential ordering.

	Args:
		v_set: Set of Vertex objects forming a cycle.

	Returns:
		List of vertices in ring-walk order.
	"""
	if len(v_set) <= 2:
		return list(v_set)
	v_list = list(v_set)
	ordered = [v_list[0]]
	visited = {v_list[0]}
	current = v_list[0]
	while len(ordered) < len(v_set):
		found_next = False
		for neighbor in current.neighbors:
			if neighbor in v_set and neighbor not in visited:
				ordered.append(neighbor)
				visited.add(neighbor)
				current = neighbor
				found_next = True
				break
		if not found_next:
			# should not happen for a valid cycle
			break
	return ordered


#============================================
def _normalize_cycle_set(cycles: set) -> set:
	"""Normalize a set of edge-based cycles for comparison.

	Each cycle is a frozenset of edge objects. We sort by cycle size
	then by id-based signature for deterministic comparison.

	Args:
		cycles: Set of frozensets of Edge objects.

	Returns:
		Frozenset of frozensets (hashable, order-independent).
	"""
	return frozenset(cycles)


#============================================
def _parse_smiles(smiles: str):
	"""Parse a SMILES string into an OASA molecule.

	Args:
		smiles: SMILES string.

	Returns:
		oasa.molecule_lib.Molecule instance, or None if parsing fails.
	"""
	try:
		mol = smiles_lib.text_to_mol(smiles)
		return mol
	except Exception:
		return None


#============================================
class TestEdgeCycleParity:
	"""Compare Gasteiger edge cycles vs rustworkx vertex cycles + edge conversion."""

	@pytest.fixture(params=list(MOLECULES.keys()))
	def molecule_pair(self, request):
		"""Fixture providing (mol, name) pairs for each test molecule."""
		name = request.param
		smiles = MOLECULES[name]
		mol = _parse_smiles(smiles)
		if mol is None:
			pytest.skip(f"Could not parse SMILES for {name}")
		return (mol, name)

	def test_cycle_count_matches(self, molecule_pair):
		"""Gasteiger and wrapper must find the same number of independent cycles."""
		mol, name = molecule_pair
		gasteiger_cycles = mol.get_smallest_independent_cycles_e()
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		assert len(gasteiger_cycles) == len(wrapper_cycles), (
			f"{name}: Gasteiger found {len(gasteiger_cycles)} cycles, "
			f"wrapper found {len(wrapper_cycles)}"
		)

	def test_cycle_sizes_match(self, molecule_pair):
		"""Each cycle must have the same number of edges."""
		mol, name = molecule_pair
		gasteiger_cycles = mol.get_smallest_independent_cycles_e()
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		# compare sorted lists of cycle sizes
		g_sizes = sorted(len(c) for c in gasteiger_cycles)
		w_sizes = sorted(len(c) for c in wrapper_cycles)
		assert g_sizes == w_sizes, (
			f"{name}: Gasteiger cycle sizes {g_sizes} != wrapper cycle sizes {w_sizes}"
		)

	def test_edge_sets_match(self, molecule_pair):
		"""The actual edge sets must be identical (same edges in each cycle)."""
		mol, name = molecule_pair
		gasteiger_cycles = mol.get_smallest_independent_cycles_e()
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		# both are sets of frozensets of Edge objects
		assert gasteiger_cycles == wrapper_cycles, (
			f"{name}: edge cycle sets differ.\n"
			f"  Gasteiger only: {gasteiger_cycles - wrapper_cycles}\n"
			f"  Wrapper only:   {wrapper_cycles - gasteiger_cycles}"
		)

	def test_edge_count_per_cycle_equals_vertex_count(self, molecule_pair):
		"""In a simple cycle, edge count must equal vertex count."""
		mol, name = molecule_pair
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		for edge_cycle in wrapper_cycles:
			verts = set()
			for e in edge_cycle:
				v1, v2 = e.get_vertices()
				verts.add(v1)
				verts.add(v2)
			assert len(edge_cycle) == len(verts), (
				f"{name}: cycle has {len(edge_cycle)} edges but {len(verts)} vertices"
			)

	def test_theoretical_cycle_count(self, molecule_pair):
		"""Both methods must find E - V + C cycles (circuit rank formula)."""
		mol, name = molecule_pair
		num_edges = len(mol.edges)
		num_verts = len(mol.vertices)
		num_components = len(mol.get_connected_components())
		expected_ncycles = num_edges - num_verts + num_components
		if expected_ncycles <= 0:
			pytest.skip(f"{name}: acyclic molecule (ncycles={expected_ncycles})")
		gasteiger_cycles = mol.get_smallest_independent_cycles_e()
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		assert len(gasteiger_cycles) == expected_ncycles, (
			f"{name}: Gasteiger found {len(gasteiger_cycles)}, expected {expected_ncycles}"
		)
		assert len(wrapper_cycles) == expected_ncycles, (
			f"{name}: Wrapper found {len(wrapper_cycles)}, expected {expected_ncycles}"
		)

	def test_hexane_returns_empty(self, molecule_pair):
		"""Acyclic molecules should return empty cycle sets from both methods."""
		mol, name = molecule_pair
		if name != "hexane":
			pytest.skip("Only testing hexane for acyclic case")
		gasteiger_cycles = mol.get_smallest_independent_cycles_e()
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		assert len(gasteiger_cycles) == 0, f"Gasteiger returned cycles for acyclic {name}"
		assert len(wrapper_cycles) == 0, f"Wrapper returned cycles for acyclic {name}"


#============================================
class TestWrapperEdgeCases:
	"""Test edge conversion wrapper on tricky topologies."""

	def test_single_atom(self):
		"""Single atom graph has no cycles."""
		mol = oasa.molecule_lib.Molecule()
		v = oasa.atom_lib.Atom("C")
		mol.add_vertex(v)
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		assert len(wrapper_cycles) == 0

	def test_two_atoms_one_bond(self):
		"""Two atoms with one bond has no cycles."""
		mol = oasa.molecule_lib.Molecule()
		v1 = oasa.atom_lib.Atom("C")
		v2 = oasa.atom_lib.Atom("C")
		mol.add_vertex(v1)
		mol.add_vertex(v2)
		mol.add_edge(v1, v2)
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		assert len(wrapper_cycles) == 0

	def test_triangle(self):
		"""Triangle (3 vertices, 3 edges) should give exactly 1 cycle of 3 edges."""
		mol = oasa.molecule_lib.Molecule()
		v1 = oasa.atom_lib.Atom("C")
		v2 = oasa.atom_lib.Atom("C")
		v3 = oasa.atom_lib.Atom("C")
		mol.add_vertex(v1)
		mol.add_vertex(v2)
		mol.add_vertex(v3)
		e1 = mol.add_edge(v1, v2)
		e2 = mol.add_edge(v2, v3)
		e3 = mol.add_edge(v3, v1)
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		assert len(wrapper_cycles) == 1
		cycle = list(wrapper_cycles)[0]
		assert len(cycle) == 3
		# the cycle should contain all 3 edges
		assert cycle == frozenset([e1, e2, e3])

	def test_disconnected_rings(self):
		"""Two disconnected triangles should give 2 independent cycles."""
		mol = oasa.molecule_lib.Molecule()
		# first triangle
		a1 = oasa.atom_lib.Atom("C")
		a2 = oasa.atom_lib.Atom("C")
		a3 = oasa.atom_lib.Atom("C")
		mol.add_vertex(a1)
		mol.add_vertex(a2)
		mol.add_vertex(a3)
		mol.add_edge(a1, a2)
		mol.add_edge(a2, a3)
		mol.add_edge(a3, a1)
		# second triangle
		b1 = oasa.atom_lib.Atom("C")
		b2 = oasa.atom_lib.Atom("C")
		b3 = oasa.atom_lib.Atom("C")
		mol.add_vertex(b1)
		mol.add_vertex(b2)
		mol.add_vertex(b3)
		mol.add_edge(b1, b2)
		mol.add_edge(b2, b3)
		mol.add_edge(b3, b1)
		vertex_cycles = mol.get_smallest_independent_cycles()
		wrapper_cycles = vertex_cycles_to_edge_cycles(mol, vertex_cycles)
		gasteiger_cycles = mol.get_smallest_independent_cycles_e()
		assert len(wrapper_cycles) == 2
		assert len(gasteiger_cycles) == 2
		assert wrapper_cycles == gasteiger_cycles
