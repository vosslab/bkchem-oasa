#!/usr/bin/env python3
"""Tests for the OASA RDKit bridge module."""

# Standard Library
import math
import pathlib
import sys

# ensure OASA is importable
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
oasa_path = REPO_ROOT / "packages" / "oasa"
if str(oasa_path) not in sys.path:
	sys.path.insert(0, str(oasa_path))

# PIP3 modules
import rdkit.Chem

# local repo modules
import oasa.rdkit_bridge as rdkit_bridge
import oasa.smiles as smiles_mod
from oasa.molecule import molecule
from oasa.atom import atom
from oasa.bond import bond


#============================================
def _make_ethanol_oasa():
	"""Build a simple ethanol molecule (CCO) in OASA."""
	omol = molecule()
	c1 = atom(symbol='C')
	c2 = atom(symbol='C')
	o1 = atom(symbol='O')
	omol.add_vertex(c1)
	omol.add_vertex(c2)
	omol.add_vertex(o1)
	b1 = bond(order=1)
	b2 = bond(order=1)
	omol.add_edge(c1, c2, b1)
	omol.add_edge(c2, o1, b2)
	return omol


#============================================
def _make_oasa_mol_from_smiles(smiles_text: str):
	"""Parse a SMILES string into an OASA molecule."""
	conv = smiles_mod.converter()
	result = conv.read_text(smiles_text)
	# read_text returns a list of molecules; take the first one
	if isinstance(result, list):
		return result[0]
	return result


#============================================
def test_oasa_to_rdkit_roundtrip():
	"""Convert ethanol OASA -> RDKit -> OASA and verify atom/bond counts."""
	omol = _make_ethanol_oasa()
	rmol, oatom_to_ridx = rdkit_bridge.oasa_to_rdkit_mol(omol)
	# RDKit mol should have 3 atoms and 2 bonds
	assert rmol.GetNumAtoms() == 3
	assert rmol.GetNumBonds() == 2
	# convert back
	omol2, ridx_to_oatom = rdkit_bridge.rdkit_to_oasa_mol(rmol)
	assert len(omol2.atoms) == 3
	assert len(omol2.bonds) == 2


#============================================
def test_atom_symbols_preserved():
	"""Verify that atom symbols survive the OASA -> RDKit -> OASA roundtrip."""
	omol = _make_ethanol_oasa()
	rmol, _ = rdkit_bridge.oasa_to_rdkit_mol(omol)
	omol2, _ = rdkit_bridge.rdkit_to_oasa_mol(rmol)
	# collect symbols from both molecules
	original_symbols = sorted([a.symbol for a in omol.atoms])
	roundtrip_symbols = sorted([a.symbol for a in omol2.atoms])
	assert original_symbols == roundtrip_symbols


#============================================
def test_calculate_coords_sets_coordinates():
	"""Verify that calculate_coords_rdkit sets non-None x/y on all atoms."""
	omol = _make_ethanol_oasa()
	rdkit_bridge.calculate_coords_rdkit(omol, bond_length=1.0)
	for a in omol.atoms:
		assert a.x is not None, f"Atom {a.symbol} has None x"
		assert a.y is not None, f"Atom {a.symbol} has None y"


#============================================
def test_bond_lengths_roughly_uniform():
	"""Verify bond lengths are close to the requested bond_length."""
	omol = _make_ethanol_oasa()
	target_bl = 1.5
	rdkit_bridge.calculate_coords_rdkit(omol, bond_length=target_bl)
	for b in omol.bonds:
		a1, a2 = b.vertices
		dx = a1.x - a2.x
		dy = a1.y - a2.y
		bl = math.sqrt(dx * dx + dy * dy)
		# allow 30% tolerance for bond length variation
		assert abs(bl - target_bl) < target_bl * 0.30, (
			f"Bond length {bl:.3f} deviates too much from target {target_bl}"
		)


#============================================
def test_smiles_roundtrip_acetic_acid():
	"""Parse acetic acid from SMILES, convert through RDKit, verify structure."""
	omol = _make_oasa_mol_from_smiles("CC(=O)O")
	rmol, _ = rdkit_bridge.oasa_to_rdkit_mol(omol)
	# acetic acid: C, C, O, O = 4 heavy atoms
	assert rmol.GetNumAtoms() >= 4
	omol2, _ = rdkit_bridge.rdkit_to_oasa_mol(rmol)
	assert len(omol2.atoms) >= 4


#============================================
def test_calculate_coords_benzene():
	"""Verify coordinate generation works for a ring molecule (benzene)."""
	omol = _make_oasa_mol_from_smiles("c1ccccc1")
	rdkit_bridge.calculate_coords_rdkit(omol, bond_length=1.0)
	for a in omol.atoms:
		assert a.x is not None
		assert a.y is not None
	# benzene ring should produce roughly equal bond lengths
	for b in omol.bonds:
		a1, a2 = b.vertices
		dx = a1.x - a2.x
		dy = a1.y - a2.y
		bl = math.sqrt(dx * dx + dy * dy)
		assert bl > 0.5, f"Bond length {bl:.3f} unexpectedly short"


#============================================
def test_double_bond_preserved():
	"""Verify that double bonds survive the conversion roundtrip."""
	omol = _make_oasa_mol_from_smiles("C=C")
	rmol, _ = rdkit_bridge.oasa_to_rdkit_mol(omol)
	# check that there is a double bond in the RDKit mol
	has_double = False
	for rbond in rmol.GetBonds():
		if rbond.GetBondType() == rdkit.Chem.BondType.DOUBLE:
			has_double = True
	assert has_double, "Double bond not found in RDKit mol"
	# roundtrip back
	omol2, _ = rdkit_bridge.rdkit_to_oasa_mol(rmol)
	has_double_oasa = any(b.order == 2 for b in omol2.bonds)
	assert has_double_oasa, "Double bond not found after roundtrip"
