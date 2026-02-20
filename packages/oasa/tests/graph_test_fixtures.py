#!/usr/bin/env python3
"""Reusable test fixtures that build molecules in both OASA and rustworkx formats.

Each make_*() function returns a dict with keys:
	oasa_mol   - the OASA Molecule object
	rx_graph   - equivalent rustworkx.PyGraph
	v_to_i     - dict mapping OASA vertex -> rustworkx node index
	i_to_v     - dict mapping rustworkx node index -> OASA vertex
	name       - human-readable molecule name
	expected   - dict of expected graph properties for parity assertions
"""

# PIP3 modules
import rustworkx

# local repo modules
import oasa


#============================================
def build_rx_from_oasa(mol) -> tuple:
	"""Convert an OASA molecule to a rustworkx PyGraph with identity maps.

	Args:
		mol: An oasa.Molecule instance.

	Returns:
		Tuple of (rx_graph, v_to_i, i_to_v) where:
			rx_graph is a rustworkx.PyGraph(multigraph=False)
			v_to_i maps OASA vertex objects to rustworkx integer indices
			i_to_v maps rustworkx integer indices to OASA vertex objects
	"""
	rx = rustworkx.PyGraph(multigraph=False)
	v_to_i = {}
	i_to_v = {}
	# add all vertices as nodes with the OASA vertex as payload
	for v in mol.vertices:
		idx = rx.add_node(v)
		v_to_i[v] = idx
		i_to_v[idx] = v
	# add all edges with the OASA edge as payload
	for e in mol.edges:
		verts = e.vertices
		v1, v2 = verts[0], verts[1]
		rx.add_edge(v_to_i[v1], v_to_i[v2], e)
	return (rx, v_to_i, i_to_v)


#============================================
def _smiles_to_fixture(smiles: str, name: str, expected: dict, calc_coords: bool = True) -> dict:
	"""Helper to build a fixture dict from a SMILES string.

	Args:
		smiles: SMILES string to parse.
		name: Human-readable molecule name.
		expected: Dict of expected graph properties.
		calc_coords: Whether to calculate 2D coordinates (some bridged
			molecules fail coord generation due to a known geometry bug).

	Returns:
		Fixture dict with oasa_mol, rx_graph, v_to_i, i_to_v, name, expected.
	"""
	mol = oasa.smiles_lib.text_to_mol(smiles, calc_coords=calc_coords)
	mol.remove_zero_order_bonds()
	rx_graph, v_to_i, i_to_v = build_rx_from_oasa(mol)
	return {
		"oasa_mol": mol,
		"rx_graph": rx_graph,
		"v_to_i": v_to_i,
		"i_to_v": i_to_v,
		"name": name,
		"expected": expected,
	}


#============================================
def make_benzene() -> dict:
	"""Build benzene (aromatic 6-ring).

	Returns:
		Fixture dict for benzene: 6 atoms, 6 bonds, 1 cycle.
	"""
	return _smiles_to_fixture(
		smiles="c1ccccc1",
		name="benzene",
		expected={
			"atom_count": 6,
			"bond_count": 6,
			"is_connected": True,
			"component_count": 1,
			"cycle_count": 1,
			"diameter": 3,
			"has_bridges": False,
		},
	)


#============================================
def make_cholesterol() -> dict:
	"""Build cholesterol (4-ring steroid with side chain).

	Returns:
		Fixture dict for cholesterol: 28 atoms, 31 bonds, 4 cycles.
	"""
	return _smiles_to_fixture(
		smiles="CC(C)CCCC(C)C1CCC2C1(CCC3C2CC=C4C3(CCC(C4)O)C)C",
		name="cholesterol",
		expected={
			"atom_count": 28,
			"bond_count": 31,
			"is_connected": True,
			"component_count": 1,
			"cycle_count": 4,
			"has_bridges": True,
		},
	)


#============================================
def make_naphthalene() -> dict:
	"""Build naphthalene (fused bicyclic aromatic).

	Returns:
		Fixture dict for naphthalene: 10 atoms, 11 bonds, 2 cycles.
	"""
	return _smiles_to_fixture(
		smiles="c1ccc2ccccc2c1",
		name="naphthalene",
		expected={
			"atom_count": 10,
			"bond_count": 11,
			"is_connected": True,
			"component_count": 1,
			"cycle_count": 2,
			"has_bridges": False,
		},
	)


#============================================
def make_steroid_skeleton() -> dict:
	"""Build steroid skeleton (4 fused saturated rings).

	Uses calc_coords=False due to a known coords_generator bug with
	multi-anelated ring systems.

	Returns:
		Fixture dict for steroid skeleton: 17 atoms, 20 bonds, 4 cycles.
	"""
	return _smiles_to_fixture(
		smiles="C1CCC2C(C1)CCC3C2CCC4CCCC34",
		name="steroid_skeleton",
		expected={
			"atom_count": 17,
			"bond_count": 20,
			"is_connected": True,
			"component_count": 1,
			"cycle_count": 4,
			"has_bridges": False,
		},
		calc_coords=False,
	)


#============================================
def make_caffeine() -> dict:
	"""Build caffeine (purine derivative with methyl groups).

	Returns:
		Fixture dict for caffeine: 14 atoms, 15 bonds.
	"""
	return _smiles_to_fixture(
		smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
		name="caffeine",
		expected={
			"atom_count": 14,
			"bond_count": 15,
			"is_connected": True,
			"component_count": 1,
			"cycle_count": 2,
		},
	)


#============================================
def make_hexane() -> dict:
	"""Build hexane (linear 6-carbon chain).

	Returns:
		Fixture dict for hexane: 6 atoms, 5 bonds, 0 cycles, all bridges.
	"""
	return _smiles_to_fixture(
		smiles="CCCCCC",
		name="hexane",
		expected={
			"atom_count": 6,
			"bond_count": 5,
			"is_connected": True,
			"component_count": 1,
			"cycle_count": 0,
			"diameter": 5,
			"has_bridges": True,
		},
	)


#============================================
def make_single_atom() -> dict:
	"""Build a single carbon atom (trivial graph).

	Returns:
		Fixture dict for single atom: 1 atom, 0 bonds, diameter 0.
	"""
	return _smiles_to_fixture(
		smiles="C",
		name="single_atom",
		expected={
			"atom_count": 1,
			"bond_count": 0,
			"is_connected": True,
			"component_count": 1,
			"cycle_count": 0,
			"diameter": 0,
			"has_bridges": False,
		},
	)


#============================================
def make_disconnected() -> dict:
	"""Build a disconnected graph with two separate C-C fragments.

	Constructed manually since SMILES always produces connected molecules.

	Returns:
		Fixture dict for disconnected: 4 atoms, 2 bonds, 2 components.
	"""
	mol = oasa.Molecule()
	# first fragment: C-C
	a1 = oasa.Atom("C")
	a2 = oasa.Atom("C")
	b1 = oasa.Bond()
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	mol.add_edge(a1, a2, b1)
	# second fragment: C-C
	a3 = oasa.Atom("C")
	a4 = oasa.Atom("C")
	b2 = oasa.Bond()
	mol.add_vertex(a3)
	mol.add_vertex(a4)
	mol.add_edge(a3, a4, b2)
	# build rustworkx equivalent
	rx_graph, v_to_i, i_to_v = build_rx_from_oasa(mol)
	return {
		"oasa_mol": mol,
		"rx_graph": rx_graph,
		"v_to_i": v_to_i,
		"i_to_v": i_to_v,
		"name": "disconnected",
		"expected": {
			"atom_count": 4,
			"bond_count": 2,
			"is_connected": False,
			"component_count": 2,
			"cycle_count": 0,
			"has_bridges": True,
		},
	}


#============================================
def make_cyclopentane() -> dict:
	"""Build cyclopentane (odd-membered saturated ring).

	Returns:
		Fixture dict for cyclopentane: 5 atoms, 5 bonds, 1 cycle.
	"""
	return _smiles_to_fixture(
		smiles="C1CCCC1",
		name="cyclopentane",
		expected={
			"atom_count": 5,
			"bond_count": 5,
			"is_connected": True,
			"component_count": 1,
			"cycle_count": 1,
			"diameter": 2,
			"has_bridges": False,
		},
	)


#============================================
def make_bridged_bicyclic() -> dict:
	"""Build norbornane-like bridged bicyclic (C1CC2CCC1C2).

	Uses calc_coords=False due to a known coords_generator bug with
	multi-anelated ring systems.

	Returns:
		Fixture dict for bridged bicyclic: 7 atoms, 8 bonds, 2 cycles.
	"""
	return _smiles_to_fixture(
		smiles="C1CC2CCC1C2",
		name="bridged_bicyclic",
		expected={
			"atom_count": 7,
			"bond_count": 8,
			"is_connected": True,
			"component_count": 1,
			"cycle_count": 2,
			"has_bridges": False,
		},
		calc_coords=False,
	)


#============================================
def get_all_fixtures() -> list:
	"""Return a list of all fixture dicts for iteration in tests.

	Returns:
		List of fixture dicts from all make_*() functions.
	"""
	makers = [
		make_benzene,
		make_cholesterol,
		make_naphthalene,
		make_steroid_skeleton,
		make_caffeine,
		make_hexane,
		make_single_atom,
		make_disconnected,
		make_cyclopentane,
		make_bridged_bicyclic,
	]
	return [fn() for fn in makers]
