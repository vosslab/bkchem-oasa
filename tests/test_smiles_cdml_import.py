"""Tests for smiles_to_cdml_elements() in oasa_bridge."""

# Standard Library
import builtins
import math
import re
import sys

# Third Party
import pytest

# Local repo modules
import conftest

# set up sys.path for bkchem and oasa packages
conftest.add_bkchem_to_sys_path()
conftest.add_oasa_to_sys_path()

# ensure gettext fallbacks exist before importing bkchem modules
if "_" not in builtins.__dict__:
	builtins.__dict__["_"] = lambda m: m
if "ngettext" not in builtins.__dict__:
	builtins.__dict__["ngettext"] = lambda s, p, n: s if n == 1 else p

# initialize Screen singleton with a typical DPI before importing oasa_bridge
from singleton_store import Screen
Screen.dpi = 72

# import the function under test
import oasa_bridge


#============================================
class _MockStandard:
	"""Minimal stand-in for paper.standard with a bond_length attribute."""
	bond_length = "0.7cm"


#============================================
class _MockPaper:
	"""Minimal stand-in for the BKChem paper object."""
	def __init__(self):
		self.standard = _MockStandard()


#============================================
@pytest.fixture
def paper():
	"""Provide a mock paper with standard bond length."""
	return _MockPaper()


#============================================
def test_smiles_to_cdml_element_ethanol(paper):
	"""CCO produces 1 molecule element with 3 atoms and 2 bonds."""
	elements = oasa_bridge.smiles_to_cdml_elements("CCO", paper)
	assert len(elements) == 1
	mol_elem = elements[0]
	atoms = mol_elem.getElementsByTagName("atom")
	bonds = mol_elem.getElementsByTagName("bond")
	assert len(atoms) == 3
	assert len(bonds) == 2


#============================================
def test_smiles_to_cdml_element_benzene(paper):
	"""c1ccccc1 produces 6 atoms and 6 bonds."""
	elements = oasa_bridge.smiles_to_cdml_elements("c1ccccc1", paper)
	assert len(elements) == 1
	mol_elem = elements[0]
	atoms = mol_elem.getElementsByTagName("atom")
	bonds = mol_elem.getElementsByTagName("bond")
	assert len(atoms) == 6
	assert len(bonds) == 6


#============================================
def test_smiles_to_cdml_element_coordinates_in_cm(paper):
	"""All point elements in CCO output have x and y attributes ending in cm."""
	elements = oasa_bridge.smiles_to_cdml_elements("CCO", paper)
	mol_elem = elements[0]
	points = mol_elem.getElementsByTagName("point")
	assert len(points) > 0
	for pt in points:
		x_val = pt.getAttribute("x")
		y_val = pt.getAttribute("y")
		assert x_val.endswith("cm"), f"x attribute does not end with cm: {x_val}"
		assert y_val.endswith("cm"), f"y attribute does not end with cm: {y_val}"


#============================================
def _parse_cm(text: str) -> float:
	"""Extract the numeric value from a string like '11.289cm'."""
	match = re.match(r"([+-]?\d*\.?\d+)cm", text)
	assert match, f"Could not parse cm value: {text}"
	return float(match.group(1))


#============================================
def test_smiles_to_cdml_element_bond_length_reasonable(paper):
	"""Average bond distance in CCO output is close to 0.7 cm (within 0.2)."""
	elements = oasa_bridge.smiles_to_cdml_elements("CCO", paper)
	mol_elem = elements[0]
	# collect atom coordinates keyed by atom id
	atoms = mol_elem.getElementsByTagName("atom")
	coords = {}
	for atom_elem in atoms:
		atom_id = atom_elem.getAttribute("id")
		point = atom_elem.getElementsByTagName("point")[0]
		x = _parse_cm(point.getAttribute("x"))
		y = _parse_cm(point.getAttribute("y"))
		coords[atom_id] = (x, y)
	# measure bond lengths
	bonds = mol_elem.getElementsByTagName("bond")
	lengths = []
	for bond_elem in bonds:
		id1 = bond_elem.getAttribute("start")
		id2 = bond_elem.getAttribute("end")
		x1, y1 = coords[id1]
		x2, y2 = coords[id2]
		dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
		lengths.append(dist)
	avg_length = sum(lengths) / len(lengths)
	assert abs(avg_length - 0.7) < 0.2, f"Average bond length {avg_length:.3f} cm not close to 0.7"


#============================================
def test_smiles_to_cdml_element_disconnected(paper):
	"""CC.OO (disconnected SMILES) produces 2 molecule elements."""
	elements = oasa_bridge.smiles_to_cdml_elements("CC.OO", paper)
	assert len(elements) == 2


#============================================
def test_smiles_to_cdml_element_empty_raises(paper):
	"""Empty string raises ValueError."""
	with pytest.raises(ValueError):
		oasa_bridge.smiles_to_cdml_elements("", paper)


#============================================
def test_smiles_to_cdml_element_atom_names(paper):
	"""CCO output has atom name attributes including C and O."""
	elements = oasa_bridge.smiles_to_cdml_elements("CCO", paper)
	mol_elem = elements[0]
	atoms = mol_elem.getElementsByTagName("atom")
	names = {a.getAttribute("name") for a in atoms}
	assert "C" in names, f"Expected 'C' in atom names, got {names}"
	assert "O" in names, f"Expected 'O' in atom names, got {names}"
