# SPDX-License-Identifier: LGPL-3.0-or-later

"""Unit tests for RDKit-backed file format codecs."""

# Standard Library
import io

# Third Party
import pytest

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
import oasa.codec_registry
from oasa.codecs import rdkit_formats


#============================================
def _make_simple_mol():
	"""Create a simple C-O molecule for testing."""
	mol = oasa.molecule_lib.Molecule()
	a1 = oasa.atom_lib.Atom(symbol="C")
	a1.x = 0.0
	a1.y = 0.0
	a2 = oasa.atom_lib.Atom(symbol="O")
	a2.x = 1.0
	a2.y = 0.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	bond = oasa.bond_lib.Bond(order=1, type="n")
	bond.vertices = (a1, a2)
	mol.add_edge(a1, a2, bond)
	return mol


#============================================
def _make_ethanol():
	"""Create ethanol (CCO) for testing."""
	mol = oasa.molecule_lib.Molecule()
	c1 = oasa.atom_lib.Atom(symbol="C")
	c1.x = 0.0
	c1.y = 0.0
	c2 = oasa.atom_lib.Atom(symbol="C")
	c2.x = 1.0
	c2.y = 0.0
	o = oasa.atom_lib.Atom(symbol="O")
	o.x = 2.0
	o.y = 0.0
	mol.add_vertex(c1)
	mol.add_vertex(c2)
	mol.add_vertex(o)
	b1 = oasa.bond_lib.Bond(order=1, type="n")
	b1.vertices = (c1, c2)
	mol.add_edge(c1, c2, b1)
	b2 = oasa.bond_lib.Bond(order=1, type="n")
	b2.vertices = (c2, o)
	mol.add_edge(c2, o, b2)
	return mol


# ===================================================================
# Molfile V3000 tests
# ===================================================================

#============================================
def test_molfile_v3000_roundtrip():
	mol = _make_simple_mol()
	text = rdkit_formats.molfile_v3000_mol_to_text(mol)
	assert "V3000" in text
	loaded = rdkit_formats.molfile_v3000_text_to_mol(text)
	assert len(loaded.atoms) == 2
	assert len(loaded.bonds) == 1


#============================================
def test_molfile_v3000_file_roundtrip():
	mol = _make_simple_mol()
	out = io.BytesIO()
	rdkit_formats.molfile_v3000_mol_to_file(mol, out)
	out.seek(0)
	text = out.read().decode("utf-8")
	assert "V3000" in text
	loaded = rdkit_formats.molfile_v3000_text_to_mol(text)
	assert len(loaded.atoms) == 2


#============================================
def test_molfile_v3000_invalid_input():
	with pytest.raises(ValueError):
		rdkit_formats.molfile_v3000_text_to_mol("not a mol block")


# ===================================================================
# SDF tests
# ===================================================================

#============================================
def test_sdf_roundtrip():
	mol = _make_ethanol()
	text = rdkit_formats.sdf_mol_to_text(mol)
	assert "$$$$" in text
	loaded = rdkit_formats.sdf_text_to_mol(text)
	assert len(loaded.atoms) == 3
	assert len(loaded.bonds) == 2


#============================================
def test_sdf_file_roundtrip():
	mol = _make_ethanol()
	out = io.BytesIO()
	rdkit_formats.sdf_mol_to_file(mol, out)
	out.seek(0)
	inp = io.StringIO(out.read().decode("utf-8"))
	loaded = rdkit_formats.sdf_file_to_mol(inp)
	assert len(loaded.atoms) == 3


#============================================
def test_sdf_multi_molecule():
	"""Write two separate molecules, read back, verify both present."""
	mol1 = _make_simple_mol()
	mol2 = _make_ethanol()
	# produce SDF text for each and concatenate
	text1 = rdkit_formats.sdf_mol_to_text(mol1)
	text2 = rdkit_formats.sdf_mol_to_text(mol2)
	combined = text1 + text2
	loaded = rdkit_formats.sdf_text_to_mol(combined)
	# mol1 has 2 atoms, mol2 has 3 atoms -> total 5
	assert len(loaded.atoms) == 5
	# mol1 has 1 bond, mol2 has 2 bonds -> total 3
	assert len(loaded.bonds) == 3


#============================================
def test_sdf_empty_raises():
	with pytest.raises(ValueError):
		rdkit_formats.sdf_text_to_mol("")


# ===================================================================
# SDF V3000 tests
# ===================================================================

#============================================
def test_sdf_v3000_roundtrip():
	mol = _make_simple_mol()
	text = rdkit_formats.sdf_v3000_mol_to_text(mol)
	assert "V3000" in text
	loaded = rdkit_formats.sdf_v3000_text_to_mol(text)
	assert len(loaded.atoms) == 2


#============================================
def test_sdf_v3000_file_roundtrip():
	mol = _make_simple_mol()
	out = io.BytesIO()
	rdkit_formats.sdf_v3000_mol_to_file(mol, out)
	out.seek(0)
	text = out.read().decode("utf-8")
	assert "V3000" in text


# ===================================================================
# SMARTS tests
# ===================================================================

#============================================
def test_smarts_export():
	mol = _make_simple_mol()
	text = rdkit_formats.smarts_mol_to_text(mol)
	assert isinstance(text, str)
	assert len(text) > 0


#============================================
def test_smarts_file_export():
	mol = _make_simple_mol()
	out = io.BytesIO()
	rdkit_formats.smarts_mol_to_file(mol, out)
	content = out.getvalue().decode("utf-8")
	assert len(content.strip()) > 0


# ===================================================================
# InChI tests (RDKit-native)
# ===================================================================

#============================================
def test_inchi_roundtrip():
	mol = _make_ethanol()
	text = rdkit_formats.inchi_mol_to_text(mol)
	assert text.startswith("InChI=")
	loaded = rdkit_formats.inchi_text_to_mol(text)
	assert loaded is not None
	assert len(loaded.atoms) >= 3


#============================================
def test_inchi_file_roundtrip():
	mol = _make_ethanol()
	out = io.BytesIO()
	rdkit_formats.inchi_mol_to_file(mol, out)
	content = out.getvalue().decode("utf-8")
	assert content.strip().startswith("InChI=")


#============================================
def test_inchi_and_key_generation():
	mol = _make_ethanol()
	inchi, key, warnings = rdkit_formats.generate_inchi_and_inchikey(mol)
	assert inchi.startswith("InChI=")
	assert key is not None
	assert len(key) > 0
	assert isinstance(warnings, list)


#============================================
def test_inchi_empty_raises():
	with pytest.raises(ValueError):
		rdkit_formats.inchi_text_to_mol("")


# ===================================================================
# Molfile V2000 tests
# ===================================================================

#============================================
def test_molfile_v2000_roundtrip():
	mol = _make_ethanol()
	text = rdkit_formats.molfile_mol_to_text(mol)
	assert "V2000" in text
	loaded = rdkit_formats.molfile_text_to_mol(text)
	assert len(loaded.atoms) == 3
	assert len(loaded.bonds) == 2


#============================================
def test_molfile_v2000_file_roundtrip():
	mol = _make_ethanol()
	out = io.BytesIO()
	rdkit_formats.molfile_mol_to_file(mol, out)
	out.seek(0)
	text = out.read().decode("utf-8")
	assert "V2000" in text
	loaded = rdkit_formats.molfile_text_to_mol(text)
	assert len(loaded.atoms) == 3


# ===================================================================
# SMILES tests
# ===================================================================

#============================================
def test_smiles_roundtrip():
	mol = _make_ethanol()
	text = rdkit_formats.smiles_mol_to_text(mol)
	assert isinstance(text, str)
	assert len(text) > 0
	loaded = rdkit_formats.smiles_text_to_mol(text)
	assert len(loaded.atoms) == 3
	assert len(loaded.bonds) == 2


#============================================
def test_smiles_file_roundtrip():
	mol = _make_ethanol()
	out = io.BytesIO()
	rdkit_formats.smiles_mol_to_file(mol, out)
	content = out.getvalue().decode("utf-8")
	assert len(content.strip()) > 0
	loaded = rdkit_formats.smiles_text_to_mol(content.strip())
	assert len(loaded.atoms) == 3


#============================================
def test_smiles_empty_raises():
	with pytest.raises(ValueError):
		rdkit_formats.smiles_text_to_mol("")


#============================================
def test_smiles_benzene():
	"""Verify aromatic SMILES roundtrip preserves atom and bond counts."""
	mol = rdkit_formats.smiles_text_to_mol("c1ccccc1")
	assert len(mol.atoms) == 6
	assert len(mol.bonds) == 6
	text = rdkit_formats.smiles_mol_to_text(mol)
	assert len(text) > 0


# ===================================================================
# NxN cholesterol super roundtrip test
# ===================================================================

# cholesterol SMILES: 28 heavy atoms (27C + 1O), 31 bonds
CHOLESTEROL_SMILES = "CC(C)CCCC(C)C1CCC2C1(CCC1C2CC=C2CC(O)CCC21C)C"
CHOLESTEROL_HEAVY_ATOMS = 28
CHOLESTEROL_BONDS = 31

# codec name -> (write_func, read_func)
# only codecs that support both text write and text read
_ROUNDTRIP_CODECS = {
	"smiles": (rdkit_formats.smiles_mol_to_text, rdkit_formats.smiles_text_to_mol),
	"molfile": (rdkit_formats.molfile_mol_to_text, rdkit_formats.molfile_text_to_mol),
	"molfile_v3000": (rdkit_formats.molfile_v3000_mol_to_text, rdkit_formats.molfile_v3000_text_to_mol),
	"sdf": (rdkit_formats.sdf_mol_to_text, rdkit_formats.sdf_text_to_mol),
	"sdf_v3000": (rdkit_formats.sdf_v3000_mol_to_text, rdkit_formats.sdf_v3000_text_to_mol),
	"inchi": (rdkit_formats.inchi_mol_to_text, rdkit_formats.inchi_text_to_mol),
}

# smarts is write-only, so test separately
_WRITE_ONLY_CODECS = {
	"smarts": rdkit_formats.smarts_mol_to_text,
}

# build the list of all (write_format, read_format) pairs for NxN test
_NXN_PAIRS = []
_codec_names = sorted(_ROUNDTRIP_CODECS.keys())
for write_fmt in _codec_names:
	for read_fmt in _codec_names:
		_NXN_PAIRS.append((write_fmt, read_fmt))


#============================================
@pytest.fixture(scope="module")
def cholesterol_mol():
	"""Parse cholesterol once for the whole test module."""
	mol = rdkit_formats.smiles_text_to_mol(CHOLESTEROL_SMILES, calc_coords=1)
	assert len(mol.atoms) == CHOLESTEROL_HEAVY_ATOMS
	assert len(mol.bonds) == CHOLESTEROL_BONDS
	return mol


#============================================
@pytest.mark.parametrize("write_fmt", sorted(_ROUNDTRIP_CODECS.keys()))
def test_cholesterol_single_roundtrip(cholesterol_mol, write_fmt):
	"""Write cholesterol to format, read back, verify atom/bond counts."""
	write_func, read_func = _ROUNDTRIP_CODECS[write_fmt]
	text = write_func(cholesterol_mol)
	assert text and len(text) > 0
	loaded = read_func(text)
	n_atoms = len(loaded.atoms)
	n_bonds = len(loaded.bonds)
	assert n_atoms == CHOLESTEROL_HEAVY_ATOMS, (
		f"{write_fmt} roundtrip: expected {CHOLESTEROL_HEAVY_ATOMS} atoms, got {n_atoms}")
	assert n_bonds == CHOLESTEROL_BONDS, (
		f"{write_fmt} roundtrip: expected {CHOLESTEROL_BONDS} bonds, got {n_bonds}")


#============================================
@pytest.mark.parametrize("write_fmt,read_fmt", _NXN_PAIRS,
	ids=[f"{w}->{r}" for w, r in _NXN_PAIRS])
def test_cholesterol_nxn_roundtrip(cholesterol_mol, write_fmt, read_fmt):
	"""NxN roundtrip: write cholesterol in format A, read back, write in
	format B, read back, verify atom/bond counts survive both hops.

	This tests all N*N combinations of the 6 read/write codecs:
	  smiles, molfile, molfile_v3000, sdf, sdf_v3000, inchi

	Each pair verifies that no atoms or bonds are lost when chaining
	two different format conversions.
	"""
	# first hop: write in format A, read back
	write_a, read_a = _ROUNDTRIP_CODECS[write_fmt]
	text_a = write_a(cholesterol_mol)
	mol_a = read_a(text_a)
	# second hop: write mol_a in format B, read back
	write_b, read_b = _ROUNDTRIP_CODECS[read_fmt]
	text_b = write_b(mol_a)
	mol_ab = read_b(text_b)
	n_atoms = len(mol_ab.atoms)
	n_bonds = len(mol_ab.bonds)
	assert n_atoms == CHOLESTEROL_HEAVY_ATOMS, (
		f"{write_fmt}->{read_fmt}: expected {CHOLESTEROL_HEAVY_ATOMS} atoms, got {n_atoms}")
	assert n_bonds == CHOLESTEROL_BONDS, (
		f"{write_fmt}->{read_fmt}: expected {CHOLESTEROL_BONDS} bonds, got {n_bonds}")


#============================================
def test_cholesterol_smarts_export(cholesterol_mol):
	"""Verify SMARTS export produces a non-empty string."""
	text = rdkit_formats.smarts_mol_to_text(cholesterol_mol)
	assert isinstance(text, str)
	assert len(text) > 10


# ===================================================================
# Codec registry integration tests
# ===================================================================

#============================================
def test_new_codecs_in_registry():
	oasa.codec_registry.reset_registry()
	codecs = oasa.codec_registry.list_codecs()
	assert "molfile_v3000" in codecs
	assert "sdf" in codecs
	assert "sdf_v3000" in codecs
	assert "smarts" in codecs


#============================================
def test_sdf_extension_resolves():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec_by_extension(".sdf")
	assert codec.name == "sdf"


#============================================
def test_sma_extension_resolves():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec_by_extension(".sma")
	assert codec.name == "smarts"


#============================================
def test_v3000_alias_resolves():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("v3000")
	assert codec.name == "molfile_v3000"


#============================================
def test_sdf_v3000_alias_resolves():
	oasa.codec_registry.reset_registry()
	codec = oasa.codec_registry.get_codec("sdf-v3000")
	assert codec.name == "sdf_v3000"
