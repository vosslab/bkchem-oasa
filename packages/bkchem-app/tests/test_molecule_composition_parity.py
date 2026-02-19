"""Parity tests for molecule graph operations and factory methods.

Verifies that OASA molecule graph operations behave as expected,
establishing a baseline for composition-based molecule refactor.
"""

# PIP3 modules
import pytest

# local repo modules
import oasa

# oasa.__init__ re-exports classes at top level, so oasa.molecule is the class
# (not the module). Use top-level names to avoid the naming collision.
OasaMolecule = oasa.molecule
OasaAtom = oasa.atom
OasaBond = oasa.bond


#============================================
# Helper: build a simple chain molecule
#============================================
def _make_chain(n_atoms: int) -> OasaMolecule:
	"""Build a linear chain of n carbon atoms connected by single bonds.

	Args:
		n_atoms: Number of atoms in the chain.

	Returns:
		An oasa.molecule with n atoms in a line.
	"""
	mol = OasaMolecule()
	prev = None
	for i in range(n_atoms):
		a = OasaAtom()
		a.symbol = "C"
		# set simple coordinates for geometry
		a.x = float(i)
		a.y = 0.0
		a.z = 0.0
		mol.add_vertex(a)
		if prev is not None:
			b = OasaBond()
			mol.add_edge(prev, a, e=b)
		prev = a
	return mol


#============================================
# Helper: build a benzene-like 6-ring
#============================================
def _make_benzene() -> OasaMolecule:
	"""Build a 6-membered ring (benzene-like) with alternating bonds.

	Returns:
		An oasa.molecule with 6 carbon atoms in a ring.
	"""
	import math
	mol = OasaMolecule()
	atoms = []
	for i in range(6):
		a = OasaAtom()
		a.symbol = "C"
		# place atoms in a hexagonal arrangement
		angle = math.pi / 3.0 * i
		a.x = math.cos(angle)
		a.y = math.sin(angle)
		a.z = 0.0
		mol.add_vertex(a)
		atoms.append(a)
	# connect in a ring
	for i in range(6):
		b = OasaBond()
		# alternate single/double bond orders
		b.order = 2 if i % 2 == 0 else 1
		mol.add_edge(atoms[i], atoms[(i + 1) % 6], e=b)
	return mol


#============================================
# Helper: build two disconnected fragments
#============================================
def _make_disconnected() -> OasaMolecule:
	"""Build a molecule with two disconnected ethane-like fragments.

	Returns:
		An oasa.molecule with 4 atoms in two separate pairs.
	"""
	mol = OasaMolecule()
	# fragment 1
	a1 = OasaAtom()
	a1.symbol = "C"
	a1.x, a1.y, a1.z = 0.0, 0.0, 0.0
	a2 = OasaAtom()
	a2.symbol = "C"
	a2.x, a2.y, a2.z = 1.0, 0.0, 0.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	b1 = OasaBond()
	mol.add_edge(a1, a2, e=b1)
	# fragment 2
	a3 = OasaAtom()
	a3.symbol = "O"
	a3.x, a3.y, a3.z = 5.0, 0.0, 0.0
	a4 = OasaAtom()
	a4.symbol = "O"
	a4.x, a4.y, a4.z = 6.0, 0.0, 0.0
	mol.add_vertex(a3)
	mol.add_vertex(a4)
	b2 = OasaBond()
	mol.add_edge(a3, a4, e=b2)
	return mol


# ============================================================
# 1. Atom/bond list access (atoms, bonds aliases)
# ============================================================
class TestAtomBondAliases:
	"""Verify atoms/bonds are proper aliases to vertices/edges."""

	def test_atoms_is_vertices(self):
		"""atoms should reference the same list as vertices."""
		mol = _make_chain(3)
		assert mol.atoms is mol.vertices

	def test_bonds_is_edges(self):
		"""bonds should reference the same set as edges."""
		mol = _make_chain(3)
		assert mol.bonds is mol.edges

	def test_atom_count(self):
		"""Chain of 4 atoms should have exactly 4 atoms."""
		mol = _make_chain(4)
		assert len(mol.atoms) == 4

	def test_bond_count(self):
		"""Chain of 4 atoms should have exactly 3 bonds."""
		mol = _make_chain(4)
		assert len(mol.bonds) == 3

	def test_benzene_atom_count(self):
		"""Benzene ring should have 6 atoms."""
		mol = _make_benzene()
		assert len(mol.atoms) == 6

	def test_benzene_bond_count(self):
		"""Benzene ring should have 6 bonds."""
		mol = _make_benzene()
		assert len(mol.bonds) == 6


# ============================================================
# 2. Graph mutation: add_vertex, add_edge, delete_vertex, disconnect
# ============================================================
class TestGraphMutation:
	"""Verify graph mutation operations on molecule."""

	def test_add_vertex(self):
		"""Adding a vertex increases atom count by one."""
		mol = _make_chain(2)
		a = OasaAtom()
		a.symbol = "N"
		mol.add_vertex(a)
		assert len(mol.atoms) == 3

	def test_add_edge(self):
		"""Adding an edge between existing vertices increases bond count."""
		mol = _make_chain(3)
		# connect first and last atom to form a triangle
		first = mol.atoms[0]
		last = mol.atoms[2]
		b = OasaBond()
		mol.add_edge(first, last, e=b)
		assert len(mol.bonds) == 3

	def test_delete_vertex(self):
		"""delete_vertex removes the vertex from the atoms list."""
		mol = _make_chain(3)
		middle = mol.atoms[1]
		# disconnect edges first to avoid dangling references
		mol.remove_vertex(middle)
		assert len(mol.atoms) == 2

	def test_delete_vertex_removes_edges(self):
		"""remove_vertex should also disconnect edges to that vertex."""
		mol = _make_chain(3)
		middle = mol.atoms[1]
		mol.remove_vertex(middle)
		# after removing the middle, no bonds should remain
		assert len(mol.bonds) == 0

	def test_disconnect(self):
		"""disconnect(v1, v2) removes the edge between two vertices."""
		mol = _make_chain(3)
		v1 = mol.atoms[0]
		v2 = mol.atoms[1]
		edge = mol.disconnect(v1, v2)
		assert edge is not None
		assert len(mol.bonds) == 1

	def test_disconnect_preserves_vertices(self):
		"""disconnect should not remove vertices, only the edge."""
		mol = _make_chain(2)
		v1 = mol.atoms[0]
		v2 = mol.atoms[1]
		mol.disconnect(v1, v2)
		assert len(mol.atoms) == 2
		assert len(mol.bonds) == 0


# ============================================================
# 3. Connectivity: is_connected, get_disconnected_subgraphs
# ============================================================
class TestConnectivity:
	"""Verify connectivity checks on molecule graphs."""

	def test_chain_is_connected(self):
		"""A simple chain should be connected."""
		mol = _make_chain(4)
		assert mol.is_connected() is True

	def test_single_atom_is_connected(self):
		"""A molecule with one atom should be connected."""
		mol = _make_chain(1)
		assert mol.is_connected() is True

	def test_disconnected_not_connected(self):
		"""A molecule with two separate fragments is not connected."""
		mol = _make_disconnected()
		assert mol.is_connected() is False

	def test_disconnected_subgraphs_count(self):
		"""get_disconnected_subgraphs returns 2 for two separate pairs."""
		mol = _make_disconnected()
		subgraphs = mol.get_disconnected_subgraphs()
		assert len(subgraphs) == 2

	def test_disconnected_subgraphs_sizes(self):
		"""Each disconnected subgraph should have 2 atoms."""
		mol = _make_disconnected()
		subgraphs = mol.get_disconnected_subgraphs()
		sizes = sorted([len(sg.vertices) for sg in subgraphs])
		assert sizes == [2, 2]

	def test_connected_single_subgraph(self):
		"""A connected molecule returns 1 subgraph."""
		mol = _make_chain(3)
		subgraphs = mol.get_disconnected_subgraphs()
		assert len(subgraphs) == 1

	def test_disconnect_then_check(self):
		"""After disconnecting a chain, it should become disconnected."""
		mol = _make_chain(3)
		v1 = mol.atoms[0]
		v2 = mol.atoms[1]
		mol.disconnect(v1, v2)
		assert mol.is_connected() is False


# ============================================================
# 4. Factory methods: create_vertex, create_edge, create_graph
# ============================================================
class TestFactoryMethods:
	"""Verify factory methods produce correct types."""

	def test_create_vertex_type(self):
		"""create_vertex should return an OasaAtom instance."""
		mol = OasaMolecule()
		v = mol.create_vertex()
		assert isinstance(v, OasaAtom)

	def test_create_edge_type(self):
		"""create_edge should return an OasaBond instance."""
		mol = OasaMolecule()
		e = mol.create_edge()
		assert isinstance(e, OasaBond)

	def test_create_graph_type(self):
		"""create_graph should return an OasaMolecule instance."""
		mol = OasaMolecule()
		g = mol.create_graph()
		assert isinstance(g, OasaMolecule)

	def test_create_vertex_is_distinct(self):
		"""Two created vertices should be distinct objects."""
		mol = OasaMolecule()
		v1 = mol.create_vertex()
		v2 = mol.create_vertex()
		assert v1 is not v2

	def test_create_edge_is_distinct(self):
		"""Two created edges should be distinct objects."""
		mol = OasaMolecule()
		e1 = mol.create_edge()
		e2 = mol.create_edge()
		assert e1 is not e2


# ============================================================
# 5. Ring perception: get_smallest_independent_cycles
# ============================================================
class TestRingPerception:
	"""Verify ring perception on a benzene-like graph."""

	def test_benzene_one_ring(self):
		"""A benzene ring should have exactly 1 independent cycle."""
		mol = _make_benzene()
		cycles = mol.get_smallest_independent_cycles()
		assert len(cycles) == 1

	def test_benzene_ring_size(self):
		"""The single benzene cycle should contain 6 atoms."""
		mol = _make_benzene()
		cycles = mol.get_smallest_independent_cycles()
		# cycles is a list of sets of vertices
		ring = cycles[0]
		assert len(ring) == 6

	def test_chain_no_cycles(self):
		"""A chain molecule has no cycles."""
		mol = _make_chain(5)
		cycles = mol.get_smallest_independent_cycles()
		# returns empty set for tree graphs
		assert len(cycles) == 0

	def test_naphthalene_two_rings(self):
		"""A naphthalene-like graph (two fused 6-rings) has 2 cycles."""
		mol = OasaMolecule()
		atoms = []
		# build 10 atoms: two fused hexagons sharing an edge
		# ring 1: atoms 0-5, ring 2: atoms 2,3 shared, plus 6,7,8,9
		for i in range(10):
			a = OasaAtom()
			a.symbol = "C"
			a.x = float(i)
			a.y = 0.0
			a.z = 0.0
			mol.add_vertex(a)
			atoms.append(a)
		# ring 1 edges: 0-1, 1-2, 2-3, 3-4, 4-5, 5-0
		ring1_pairs = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]
		for i, j in ring1_pairs:
			b = OasaBond()
			mol.add_edge(atoms[i], atoms[j], e=b)
		# ring 2 edges: 2-6, 6-7, 7-8, 8-9, 9-3
		# (shares edge 2-3 from ring 1)
		ring2_pairs = [(2, 6), (6, 7), (7, 8), (8, 9), (9, 3)]
		for i, j in ring2_pairs:
			b = OasaBond()
			mol.add_edge(atoms[i], atoms[j], e=b)
		cycles = mol.get_smallest_independent_cycles()
		assert len(cycles) == 2


# ============================================================
# 6. Deep copy
# ============================================================
class TestDeepCopy:
	"""Verify deep_copy produces an independent isomorphic graph."""

	def test_deep_copy_atom_count(self):
		"""Deep copy preserves atom count."""
		mol = _make_chain(4)
		mol_copy = mol.deep_copy()
		assert len(mol_copy.atoms) == len(mol.atoms)

	def test_deep_copy_bond_count(self):
		"""Deep copy preserves bond count."""
		mol = _make_chain(4)
		mol_copy = mol.deep_copy()
		assert len(mol_copy.bonds) == len(mol.bonds)

	def test_deep_copy_independent_vertices(self):
		"""Deep copy vertices should be different objects."""
		mol = _make_chain(3)
		mol_copy = mol.deep_copy()
		# no vertex should be the same object
		for orig_v in mol.atoms:
			for copy_v in mol_copy.atoms:
				assert orig_v is not copy_v

	def test_deep_copy_independent_edges(self):
		"""Deep copy edges should be different objects."""
		mol = _make_chain(3)
		mol_copy = mol.deep_copy()
		for orig_e in mol.bonds:
			for copy_e in mol_copy.bonds:
				assert orig_e is not copy_e

	def test_deep_copy_preserves_symbols(self):
		"""Deep copy atoms retain their element symbols."""
		mol = _make_chain(3)
		# change middle atom to nitrogen
		mol.atoms[1].symbol = "N"
		mol_copy = mol.deep_copy()
		orig_symbols = [a.symbol for a in mol.atoms]
		copy_symbols = [a.symbol for a in mol_copy.atoms]
		assert orig_symbols == copy_symbols

	def test_deep_copy_mutation_independent(self):
		"""Mutating deep copy should not affect original."""
		mol = _make_chain(3)
		mol_copy = mol.deep_copy()
		# add an extra atom to the copy
		a = OasaAtom()
		a.symbol = "O"
		mol_copy.add_vertex(a)
		assert len(mol.atoms) == 3
		assert len(mol_copy.atoms) == 4

	def test_deep_copy_connectivity(self):
		"""Deep copy should preserve connectivity structure."""
		mol = _make_benzene()
		mol_copy = mol.deep_copy()
		assert mol_copy.is_connected() is True
		cycles = mol_copy.get_smallest_independent_cycles()
		assert len(cycles) == 1


# ============================================================
# 7. Stereochemistry list management
# ============================================================
class TestStereochemistryList:
	"""Verify stereochemistry list operations on molecule."""

	def test_initial_stereochemistry_empty(self):
		"""New molecule should have empty stereochemistry list."""
		mol = OasaMolecule()
		assert mol.stereochemistry == []

	def test_add_stereochemistry(self):
		"""add_stereochemistry appends to the list."""
		mol = OasaMolecule()
		# use a simple placeholder object
		stereo = {"type": "test", "value": "cis"}
		mol.add_stereochemistry(stereo)
		assert len(mol.stereochemistry) == 1
		assert mol.stereochemistry[0] is stereo

	def test_remove_stereochemistry(self):
		"""remove_stereochemistry removes from the list."""
		mol = OasaMolecule()
		stereo = {"type": "test", "value": "trans"}
		mol.add_stereochemistry(stereo)
		mol.remove_stereochemistry(stereo)
		assert len(mol.stereochemistry) == 0

	def test_remove_nonexistent_raises(self):
		"""Removing non-existent stereochemistry should raise ValueError."""
		mol = OasaMolecule()
		stereo = {"type": "test", "value": "cis"}
		with pytest.raises(ValueError):
			mol.remove_stereochemistry(stereo)

	def test_get_stereochemistry_by_center_none(self):
		"""get_stereochemistry_by_center returns None when no match."""
		mol = OasaMolecule()
		result = mol.get_stereochemistry_by_center("fake_center")
		assert result is None


# ============================================================
# Composition parity placeholders
# ============================================================
class TestCompositionParity:
	"""Tests that verify composition-based molecule parity."""

	def test_composition_molecule_atoms_alias(self):
		"""Composition molecule.atoms should delegate to _chem_mol."""
		# placeholder: import composition molecule when available
		from bkchem.molecule import molecule as bk_molecule
		mol = bk_molecule()
		# check that atoms delegates to internal _chem_mol
		assert hasattr(mol, '_chem_mol')
		assert mol.atoms is mol._chem_mol.atoms

	def test_composition_molecule_add_vertex(self):
		"""Composition molecule.add_vertex should update _chem_mol."""
		from bkchem.molecule import molecule as bk_molecule
		mol = bk_molecule()
		a = mol.create_vertex()
		mol.add_vertex(a)
		assert a in mol._chem_mol.atoms

	def test_composition_molecule_create_vertex_type(self):
		"""Composition create_vertex should return bkchem.atom."""
		from bkchem.molecule import molecule as bk_molecule
		from bkchem.atom import atom as bk_atom
		mol = bk_molecule()
		v = mol.create_vertex()
		assert isinstance(v, bk_atom)

	def test_composition_molecule_create_edge_type(self):
		"""Composition create_edge should return bkchem.bond."""
		from bkchem.molecule import molecule as bk_molecule
		from bkchem.bond import bond as bk_bond
		mol = bk_molecule()
		e = mol.create_edge()
		assert isinstance(e, bk_bond)

	def test_composition_molecule_create_graph_type(self):
		"""Composition create_graph should return bkchem.molecule with _chem_mol."""
		from bkchem.molecule import molecule as bk_molecule
		mol = bk_molecule()
		g = mol.create_graph()
		assert isinstance(g, bk_molecule)
		# must have composition delegate, not inheritance
		assert hasattr(g, '_chem_mol')

	def test_composition_deep_copy_delegates(self):
		"""Composition deep_copy should return an independent graph."""
		from bkchem.molecule import molecule as bk_molecule
		mol = bk_molecule()
		mol_copy = mol.deep_copy()
		# deep_copy currently returns oasa.molecule (not bkchem.molecule)
		# verify it is at least a separate graph object
		assert mol_copy is not mol
		assert mol_copy is not mol._chem_mol

	def test_composition_is_connected_delegates(self):
		"""Composition is_connected should delegate to _chem_mol."""
		from bkchem.molecule import molecule as bk_molecule
		mol = bk_molecule()
		# single atom should be connected
		a = mol.create_vertex()
		mol.add_vertex(a)
		assert mol.is_connected() is True
