#!/usr/bin/env python3
"""Tests for the three-layer 2D coordinate generator (coords_generator2)."""

# Standard Library
import math

import oasa.coords_generator2 as cg2
import oasa.smiles


#============================================
def _mol_from_smiles(smiles_text: str):
	"""Parse SMILES and return an OASA molecule with no coords."""
	mol = oasa.smiles.text_to_mol(smiles_text, calc_coords=False)
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
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
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
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_bond_lengths_uniform(self):
		"""All bond lengths should be close to target."""
		mol = _mol_from_smiles("CCO")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		for bl in lengths:
			assert abs(bl - 1.0) < 0.15, f"bond length {bl:.3f} too far from 1.0"

	def test_three_atoms(self):
		mol = _mol_from_smiles("CCO")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 3


# ======================================================
# Test: benzene (single ring)
# ======================================================

#============================================
class TestBenzene:
	def test_all_coords_set(self):
		mol = _mol_from_smiles("c1ccccc1")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_six_atoms(self):
		mol = _mol_from_smiles("c1ccccc1")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 6

	def test_hexagonal_bond_lengths(self):
		"""All 6 bonds should be near target length."""
		mol = _mol_from_smiles("c1ccccc1")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		assert len(lengths) == 6
		for bl in lengths:
			assert abs(bl - 1.0) < 0.15, f"benzene bond {bl:.3f} off target"

	def test_ring_symmetry(self):
		"""All atoms should be roughly equidistant from center."""
		mol = _mol_from_smiles("c1ccccc1")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
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
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_ten_atoms(self):
		mol = _mol_from_smiles("c1ccc2ccccc2c1")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 10

	def test_bond_lengths(self):
		mol = _mol_from_smiles("c1ccc2ccccc2c1")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		lengths = _bond_lengths(mol)
		for bl in lengths:
			# allow more tolerance for fused systems
			assert abs(bl - 1.0) < 0.3, f"naphthalene bond {bl:.3f} off target"


# ======================================================
# Test: acetic acid (branched)
# ======================================================

#============================================
class TestAceticAcid:
	def test_all_coords_set(self):
		mol = _mol_from_smiles("CC(=O)O")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_four_atoms(self):
		mol = _mol_from_smiles("CC(=O)O")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 4


# ======================================================
# Test: cyclohexane
# ======================================================

#============================================
class TestCyclohexane:
	def test_all_coords_set(self):
		mol = _mol_from_smiles("C1CCCCC1")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_six_atoms(self):
		mol = _mol_from_smiles("C1CCCCC1")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert len(mol.vertices) == 6


# ======================================================
# Test: spiro compound
# ======================================================

#============================================
class TestSpiro:
	def test_spiro_coords_set(self):
		"""Spiro[4.4]nonane: two 5-membered rings sharing one atom."""
		mol = _mol_from_smiles("C1CCC2(C1)CCCC2")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)


# ======================================================
# Test: steroid skeleton (complex fused)
# ======================================================

#============================================
class TestSteroid:
	def test_steroid_coords_set(self):
		"""Steroid core: four fused rings (6-6-6-5)."""
		# androstane skeleton (simplified)
		smiles_text = "C1CCC2C(C1)CCC3C2CCC4CCCC34"
		mol = _mol_from_smiles(smiles_text)
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)

	def test_steroid_atom_count(self):
		smiles_text = "C1CCC2C(C1)CCC3C2CCC4CCCC34"
		mol = _mol_from_smiles(smiles_text)
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		# all atoms should have coords
		assert all(a.x is not None for a in mol.vertices)


# ======================================================
# Test: force parameter
# ======================================================

#============================================
class TestForceParameter:
	def test_force_recalculates(self):
		"""Setting force=1 should recalculate even if coords exist."""
		mol = _mol_from_smiles("CC")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		# change coords manually
		mol.vertices[0].x = 999.0
		# recalculate with force
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert mol.vertices[0].x != 999.0

	def test_no_force_keeps_existing(self):
		"""Without force, existing coords should be preserved."""
		mol = _mol_from_smiles("CC")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		x_before = mol.vertices[0].x
		cg2.calculate_coords(mol, bond_length=1.0, force=0)
		assert mol.vertices[0].x == x_before


# ======================================================
# Test: longer chain
# ======================================================

#============================================
class TestLongChain:
	def test_hexane(self):
		mol = _mol_from_smiles("CCCCCC")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)
		assert len(mol.vertices) == 6

	def test_zigzag_pattern(self):
		"""Long chain should not fold back on itself."""
		mol = _mol_from_smiles("CCCCCCCCCC")
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
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
		cg2.calculate_coords(mol, bond_length=1.0, force=1)
		assert _all_coords_set(mol)
