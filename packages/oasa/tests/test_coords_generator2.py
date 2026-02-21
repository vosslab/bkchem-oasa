"""Tests for the RDKit-backed 2D coordinate generator (coords_generator)."""

# Standard Library
import math

import oasa.coords_generator as cg
import oasa.smiles_lib


#============================================
def _mol_from_smiles(smiles_text: str):
	"""Parse SMILES and return an OASA molecule with no coords."""
	mol = oasa.smiles_lib.text_to_mol(smiles_text, calc_coords=False)
	return mol


#============================================
def _all_coords_set(mol) -> bool:
	"""Return True if every atom has non-None x and y."""
	for a in mol.vertices:
		if a.x is None or a.y is None:
			return False
	return True


#============================================
def _bond_lengths(mol) -> list:
	"""Return list of bond lengths for all edges."""
	lengths = []
	for b in mol.edges:
		a1, a2 = b.vertices
		d = math.sqrt((a1.x - a2.x) ** 2 + (a1.y - a2.y) ** 2)
		lengths.append(d)
	return lengths


#============================================
def _min_nonbonded_distance(mol) -> float:
	"""Return minimum distance between non-bonded atom pairs."""
	atoms = mol.vertices
	min_d = float("inf")
	for i in range(len(atoms)):
		a1 = atoms[i]
		for j in range(i + 1, len(atoms)):
			a2 = atoms[j]
			if a2 in a1.neighbors:
				continue
			d = math.sqrt((a1.x - a2.x) ** 2 + (a1.y - a2.y) ** 2)
			if d < min_d:
				min_d = d
	return min_d


# ======================================================
# Test: single atom
# ======================================================

#============================================
class TestSingleAtom:
	def test_single_atom(self):
		mol = _mol_from_smiles("C")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)
		a = mol.vertices[0]
		assert a.x == 0.0
		assert a.y == 0.0


# ======================================================
# Test: ethanol (simple chain)
# ======================================================

#============================================
class TestEthanol:
	def test_all_coords_set(self):
		mol = _mol_from_smiles("CCO")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_bond_lengths_uniform(self):
		"""All bond lengths should be close to target."""
		mol = _mol_from_smiles("CCO")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		for bl in lengths:
			assert abs(bl - 1.0) < 0.15, f"bond length {bl:.3f} too far from 1.0"

	def test_three_atoms(self):
		mol = _mol_from_smiles("CCO")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 3


# ======================================================
# Test: benzene (single ring)
# ======================================================

#============================================
class TestBenzene:
	def test_all_coords_set(self):
		mol = _mol_from_smiles("c1ccccc1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_six_atoms(self):
		mol = _mol_from_smiles("c1ccccc1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 6

	def test_hexagonal_bond_lengths(self):
		"""All 6 bonds should be near target length."""
		mol = _mol_from_smiles("c1ccccc1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		assert len(lengths) == 6
		for bl in lengths:
			assert abs(bl - 1.0) < 0.15, f"benzene bond {bl:.3f} off target"

	def test_ring_symmetry(self):
		"""All atoms should be roughly equidistant from center."""
		mol = _mol_from_smiles("c1ccccc1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		cx = sum(a.x for a in mol.vertices) / 6
		cy = sum(a.y for a in mol.vertices) / 6
		radii = [math.sqrt((a.x - cx) ** 2 + (a.y - cy) ** 2)
			for a in mol.vertices]
		avg_r = sum(radii) / len(radii)
		for r in radii:
			assert abs(r - avg_r) < 0.2, "ring not symmetric"


# ======================================================
# Test: naphthalene (fused rings)
# ======================================================

#============================================
class TestNaphthalene:
	def test_all_coords_set(self):
		mol = _mol_from_smiles("c1ccc2ccccc2c1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_ten_atoms(self):
		mol = _mol_from_smiles("c1ccc2ccccc2c1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 10

	def test_bond_lengths(self):
		mol = _mol_from_smiles("c1ccc2ccccc2c1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		for bl in lengths:
			assert abs(bl - 1.0) < 0.3, f"naphthalene bond {bl:.3f} off target"


# ======================================================
# Test: acetic acid (branched)
# ======================================================

#============================================
class TestAceticAcid:
	def test_all_coords_set(self):
		mol = _mol_from_smiles("CC(=O)O")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_four_atoms(self):
		mol = _mol_from_smiles("CC(=O)O")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 4


# ======================================================
# Test: cyclohexane
# ======================================================

#============================================
class TestCyclohexane:
	def test_all_coords_set(self):
		mol = _mol_from_smiles("C1CCCCC1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_six_atoms(self):
		mol = _mol_from_smiles("C1CCCCC1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 6


# ======================================================
# Test: spiro compound
# ======================================================

#============================================
class TestSpiro:
	def test_spiro_coords_set(self):
		"""Spiro[4.4]nonane: two 5-membered rings sharing one atom."""
		mol = _mol_from_smiles("C1CCC2(C1)CCCC2")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)


# ======================================================
# Test: steroid skeleton (complex fused)
# ======================================================

#============================================
class TestSteroid:
	def test_steroid_coords_set(self):
		"""Steroid core: four fused rings (6-6-6-5)."""
		smiles_text = "C1CCC2C(C1)CCC3C2CCC4CCCC34"
		mol = _mol_from_smiles(smiles_text)
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_steroid_atom_count(self):
		smiles_text = "C1CCC2C(C1)CCC3C2CCC4CCCC34"
		mol = _mol_from_smiles(smiles_text)
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert all(a.x is not None for a in mol.vertices)


# ======================================================
# Test: force parameter
# ======================================================

#============================================
class TestForceParameter:
	def test_force_recalculates(self):
		"""Setting force=1 should recalculate even if coords exist."""
		mol = _mol_from_smiles("CC")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		# change coords manually
		mol.vertices[0].x = 999.0
		# recalculate with force
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert mol.vertices[0].x != 999.0

	def test_no_force_keeps_existing(self):
		"""Without force, existing coords should be preserved."""
		mol = _mol_from_smiles("CC")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		x_before = mol.vertices[0].x
		cg.calculate_coords(mol, bond_length=1.0, force=0)
		assert mol.vertices[0].x == x_before


# ======================================================
# Test: longer chain
# ======================================================

#============================================
class TestLongChain:
	def test_hexane(self):
		mol = _mol_from_smiles("CCCCCC")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)
		assert len(mol.vertices) == 6

	def test_zigzag_pattern(self):
		"""Long chain should not fold back on itself."""
		mol = _mol_from_smiles("CCCCCCCCCC")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)
		# the endpoints should be reasonably far apart
		a1 = mol.vertices[0]
		a2 = mol.vertices[-1]
		d = math.sqrt((a1.x - a2.x) ** 2 + (a1.y - a2.y) ** 2)
		# 10 atoms, 9 bonds; zigzag should span several bond lengths
		assert d > 3.0, f"chain too compact: endpoint dist = {d:.2f}"


# ======================================================
# Test: triple bond linearity
# ======================================================

#============================================
class TestTripleBond:
	def test_acetylene_linear(self):
		"""Triple bond atoms should be roughly linear."""
		mol = _mol_from_smiles("C#C")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)


# ======================================================
# Test: cubane (cage molecule)
# ======================================================

#============================================
class TestCubane:
	def test_cubane_coords_set(self):
		"""Cubane: all 8 atoms should get coordinates."""
		mol = _mol_from_smiles("C12C3C4C1C5C4C3C25")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_cubane_atom_count(self):
		"""Cubane has 8 heavy atoms."""
		mol = _mol_from_smiles("C12C3C4C1C5C4C3C25")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 8

	def test_cubane_no_overlap(self):
		"""No two non-bonded atoms should overlap."""
		mol = _mol_from_smiles("C12C3C4C1C5C4C3C25")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		min_d = _min_nonbonded_distance(mol)
		assert min_d > 0.2, f"cubane has overlapping atoms: min dist {min_d:.3f}"


# ======================================================
# Test: adamantane (cage molecule)
# ======================================================

#============================================
class TestAdamantane:
	def test_adamantane_coords_set(self):
		"""Adamantane: all 10 atoms should get coordinates."""
		mol = _mol_from_smiles("C1C2CC3CC1CC(C2)C3")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_adamantane_atom_count(self):
		"""Adamantane has 10 heavy atoms."""
		mol = _mol_from_smiles("C1C2CC3CC1CC(C2)C3")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 10

	def test_adamantane_no_overlap(self):
		"""No two non-bonded atoms should overlap."""
		mol = _mol_from_smiles("C1C2CC3CC1CC(C2)C3")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		min_d = _min_nonbonded_distance(mol)
		assert min_d > 0.1, f"adamantane has overlapping atoms: min dist {min_d:.3f}"


# ======================================================
# Test: norbornane (bridged bicyclic)
# ======================================================

#============================================
class TestNorbornane:
	def test_norbornane_coords_set(self):
		"""Norbornane: all 7 atoms should get coordinates."""
		mol = _mol_from_smiles("C1CC2CCC1C2")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_norbornane_atom_count(self):
		"""Norbornane has 7 heavy atoms."""
		mol = _mol_from_smiles("C1CC2CCC1C2")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 7


# ======================================================
# Helpers for ring geometry tests
# ======================================================

#============================================
def _ring_centroid(mol, ring_atoms: list) -> tuple:
	"""Compute centroid of a set of ring atoms."""
	cx = sum(a.x for a in ring_atoms) / len(ring_atoms)
	cy = sum(a.y for a in ring_atoms) / len(ring_atoms)
	return (cx, cy)


#============================================
def _ring_internal_angles(mol, ring_atoms: list) -> list:
	"""Compute internal angles at each vertex of a ring.

	Ring atoms must be in order around the ring.
	Returns angles in degrees.
	"""
	n = len(ring_atoms)
	angles = []
	for i in range(n):
		prev_atom = ring_atoms[(i - 1) % n]
		curr_atom = ring_atoms[i]
		next_atom = ring_atoms[(i + 1) % n]
		dx1 = prev_atom.x - curr_atom.x
		dy1 = prev_atom.y - curr_atom.y
		dx2 = next_atom.x - curr_atom.x
		dy2 = next_atom.y - curr_atom.y
		dot = dx1 * dx2 + dy1 * dy2
		cross = dx1 * dy2 - dy1 * dx2
		angle = math.atan2(abs(cross), dot)
		angles.append(math.degrees(angle))
	return angles


# ======================================================
# Test: biphenyl (two separate ring systems)
# ======================================================

#============================================
class TestBiphenyl:
	def test_biphenyl_coords_set(self):
		"""Both phenyl rings should get coordinates."""
		mol = _mol_from_smiles("c1ccc(-c2ccccc2)cc1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_biphenyl_ring_systems_separated(self):
		"""The two hexagons must not overlap; centroids > 1 bond length apart."""
		mol = _mol_from_smiles("c1ccc(-c2ccccc2)cc1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		rings = mol.get_smallest_independent_cycles()
		assert len(rings) == 2
		c1 = _ring_centroid(mol, rings[0])
		c2 = _ring_centroid(mol, rings[1])
		dist = math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)
		assert dist > 1.0, f"ring centroids too close: {dist:.3f}"

	def test_biphenyl_bond_lengths(self):
		"""All bonds should be close to target after proper ring placement."""
		mol = _mol_from_smiles("c1ccc(-c2ccccc2)cc1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		for bl in lengths:
			assert abs(bl - 1.0) < 0.1, f"biphenyl bond {bl:.3f} off target"


# ======================================================
# Test: spiro ring quality
# ======================================================

#============================================
class TestSpiroQuality:
	def test_spiro44_bond_lengths(self):
		"""Spiro[4.4]nonane bonds should be near target."""
		mol = _mol_from_smiles("C1CCC2(C1)CCCC2")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		for bl in lengths:
			assert abs(bl - 1.0) < 0.25, f"spiro bond {bl:.3f} off target"

	def test_spiro55_bond_lengths(self):
		"""Spiro[5.5]undecane bonds should be near target."""
		mol = _mol_from_smiles("C1CCCCC12CCCCC2")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		for bl in lengths:
			assert abs(bl - 1.0) < 0.25, f"spiro bond {bl:.3f} off target"


# ======================================================
# Test: ring geometry preserved after full pipeline
# ======================================================

#============================================
class TestRingGeometryPreservation:
	def test_benzene_angles_after_pipeline(self):
		"""Benzene internal angles should be ~120 deg."""
		mol = _mol_from_smiles("c1ccccc1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		rings = mol.get_smallest_independent_cycles()
		assert len(rings) == 1
		ring_sorted = mol.sort_vertices_in_path(list(rings[0]))
		angles = _ring_internal_angles(mol, ring_sorted)
		ideal = 120.0
		for ang in angles:
			assert abs(ang - ideal) < 5.0, (
				f"benzene angle {ang:.1f} deg, expected {ideal:.1f}"
			)

	def test_naphthalene_ring_angles(self):
		"""Naphthalene hexagon angles should be near 120 deg."""
		mol = _mol_from_smiles("c1ccc2ccccc2c1")
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		rings = mol.get_smallest_independent_cycles()
		for ring in rings:
			ring_sorted = mol.sort_vertices_in_path(list(ring))
			if ring_sorted is None:
				continue
			ideal = 180.0 * (len(ring_sorted) - 2) / len(ring_sorted)
			angles = _ring_internal_angles(mol, ring_sorted)
			for ang in angles:
				assert abs(ang - ideal) < 10.0, (
					f"angle {ang:.1f} deg, expected {ideal:.1f}"
				)

	def test_cholesterol_skeleton_bond_lengths(self):
		"""Steroid skeleton bonds should be near target length."""
		smiles_text = "C1CCC2C(C1)CCC1C2CCC2CCCC21"
		mol = _mol_from_smiles(smiles_text)
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		for bl in lengths:
			assert abs(bl - 1.0) < 0.3, (
				f"steroid bond {bl:.3f} off target"
			)


# ======================================================
# Test: sucrose (two ring systems connected by chain bridge)
# ======================================================

#============================================
class TestSucrose:
	"""Sucrose has two ring systems (glucose 6-ring + fructose 5-ring)
	connected by a glycosidic oxygen chain bridge."""

	SMILES = (
		"OC[C@H]1OC(O[C@@]2(CO)OC[C@@H](O)[C@@H]2O)"
		"[C@H](O)[C@@H](O)[C@@H]1O"
	)

	def test_sucrose_all_coords_set(self):
		"""Every atom in sucrose gets non-None x,y coordinates."""
		mol = _mol_from_smiles(self.SMILES)
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_sucrose_rings_separated(self):
		"""Centroids of the two ring systems must be > 1.5 bond lengths apart."""
		mol = _mol_from_smiles(self.SMILES)
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		rings = mol.get_smallest_independent_cycles()
		assert len(rings) >= 2, f"expected 2+ rings, got {len(rings)}"
		c1 = _ring_centroid(mol, rings[0])
		c2 = _ring_centroid(mol, rings[1])
		dist = math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2)
		assert dist > 1.5, (
			f"ring centroids too close: {dist:.3f}, rings overlap"
		)

	def test_sucrose_bond_lengths(self):
		"""All bonds should be within tolerance of target bond_length."""
		mol = _mol_from_smiles(self.SMILES)
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		for bl in lengths:
			assert abs(bl - 1.0) < 0.35, (
				f"sucrose bond {bl:.3f} off target"
			)


# ======================================================
# Test: raffinose (three ring systems, two chain bridges)
# ======================================================

#============================================
class TestRaffinose:
	"""Raffinose has three ring systems connected by two chain bridges.
	Tests cascading deferred ring placement."""

	SMILES = (
		"OC[C@H]1OC(OC[C@H]2OC(O[C@@]3(CO)OC[C@@H](O)[C@@H]3O)"
		"[C@H](O)[C@@H](O)[C@@H]2O)[C@H](O)[C@@H](O)[C@@H]1O"
	)

	def test_raffinose_all_coords_set(self):
		"""Every atom in raffinose gets non-None x,y coordinates."""
		mol = _mol_from_smiles(self.SMILES)
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_raffinose_rings_separated(self):
		"""All ring system centroids must be pairwise separated."""
		mol = _mol_from_smiles(self.SMILES)
		cg.calculate_coords(mol, bond_length=1.0, force=1)
		rings = mol.get_smallest_independent_cycles()
		assert len(rings) >= 3, f"expected 3+ rings, got {len(rings)}"
		centroids = [_ring_centroid(mol, r) for r in rings]
		for i in range(len(centroids)):
			for j in range(i + 1, len(centroids)):
				ci = centroids[i]
				cj = centroids[j]
				dist = math.sqrt(
					(ci[0] - cj[0]) ** 2 + (ci[1] - cj[1]) ** 2
				)
				assert dist > 1.0, (
					f"ring centroids {i} and {j} too close: {dist:.3f}"
				)
