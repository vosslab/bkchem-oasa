#!/usr/bin/env python3
"""Tests for haworth/fragment_layout.py - substituent fragment positioning."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
from packages.oasa.oasa.haworth import fragment_layout
from packages.oasa.oasa.haworth.fragment_layout import FragmentAtom


#============================================
# SMILES lookup tests
#============================================

def test_smiles_for_ch_oh_ch2oh():
	assert fragment_layout._smiles_for_label("CH(OH)CH2OH") == "C(O)CO"


def test_smiles_for_chain2():
	assert fragment_layout._smiles_for_label("CHAIN2") == "C(O)CO"


def test_smiles_for_chain3():
	assert fragment_layout._smiles_for_label("CHAIN3") == "C(O)C(O)CO"


def test_smiles_for_chain4():
	assert fragment_layout._smiles_for_label("CHAIN4") == "C(O)C(O)C(O)CO"


def test_smiles_unknown_label():
	assert fragment_layout._smiles_for_label("OH") is None
	assert fragment_layout._smiles_for_label("H") is None
	assert fragment_layout._smiles_for_label("CH2OH") is None
	assert fragment_layout._smiles_for_label("CH3") is None


def test_smiles_chain1_not_handled():
	"""CHAIN1 is below minimum; not a valid chain label."""
	assert fragment_layout._smiles_for_label("CHAIN1") is None


#============================================
# layout_fragment return type tests
#============================================

def test_layout_fragment_unknown_returns_none():
	result = fragment_layout.layout_fragment("OH", 30.0, (0.0, 0.0), (0.0, -1.0))
	assert result is None


def test_layout_fragment_ch_oh_ch2oh_returns_list():
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	assert result is not None
	assert isinstance(result, list)
	assert len(result) == 3


def test_layout_fragment_chain3_returns_list():
	result = fragment_layout.layout_fragment(
		"CHAIN3", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	assert result is not None
	assert isinstance(result, list)
	# CHAIN3 = C(O)C(O)CO produces 5 groups: junction, OH, junction, OH, CH2OH
	assert len(result) == 5


#============================================
# Two-carbon tail geometry tests
#============================================

def test_two_carbon_tail_up_root_at_offset():
	"""Root junction should be one bond_length from attachment in direction."""
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	root = result[0]
	assert root.label == ""
	assert root.x == pytest.approx(100.0)
	assert root.y == pytest.approx(50.0 - 13.5)


def test_two_carbon_tail_up_labels():
	"""Up direction produces OH and CH2OH branches."""
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	labels = [fa.label for fa in result]
	assert labels == ["", "OH", "CH2OH"]


def test_two_carbon_tail_up_bond_styles():
	"""Up direction: OH is solid, CH2OH is hashed."""
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	styles = [fa.bond_style for fa in result]
	assert styles == ["solid", "solid", "hashed"]


def test_two_carbon_tail_down_bond_styles():
	"""Down direction: OH is hashed, CH2OH is solid."""
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (100.0, 50.0), (0.0, 1.0), "down",
	)
	styles = [fa.bond_style for fa in result]
	assert styles == ["solid", "hashed", "solid"]


def test_two_carbon_tail_up_oh_goes_left():
	"""Up direction: OH branch should go to the left (negative dx)."""
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	root = result[0]
	oh = result[1]
	assert oh.x < root.x


def test_two_carbon_tail_up_ch2oh_goes_right():
	"""Up direction: CH2OH branch should go to the right (positive dx)."""
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	root = result[0]
	ch2oh = result[2]
	assert ch2oh.x > root.x


def test_two_carbon_tail_up_branch_angles():
	"""Up direction: OH at 210 deg screen, CH2OH at 330 deg screen."""
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	root = result[0]
	oh = result[1]
	ch2oh = result[2]
	# OH angle from root (screen coords)
	oh_angle = math.degrees(math.atan2(oh.y - root.y, oh.x - root.x)) % 360
	assert oh_angle == pytest.approx(210.0, abs=0.1)
	# CH2OH angle from root
	ch2_angle = math.degrees(math.atan2(ch2oh.y - root.y, ch2oh.x - root.x)) % 360
	assert ch2_angle == pytest.approx(330.0, abs=0.1)


def test_two_carbon_tail_down_left_side():
	"""Down left-side: symmetric 120-degree branches from coords_generator2."""
	# Ring center to the right of vertex = left side
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (50.0, 50.0), (0.0, 1.0), "down",
		ring_center=(100.0, 50.0),
	)
	root = result[0]
	oh = result[1]
	ch2oh = result[2]
	oh_angle = math.degrees(math.atan2(oh.y - root.y, oh.x - root.x)) % 360
	ch2_angle = math.degrees(math.atan2(ch2oh.y - root.y, ch2oh.x - root.x)) % 360
	# coords_generator2 produces symmetric 30/150 for down direction
	assert oh_angle == pytest.approx(30.0, abs=0.1)
	assert ch2_angle == pytest.approx(150.0, abs=0.1)


def test_two_carbon_tail_down_right_side():
	"""Down right-side: symmetric 120-degree branches from coords_generator2."""
	# Ring center to the left of vertex = right side
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (150.0, 50.0), (0.0, 1.0), "down",
		ring_center=(100.0, 50.0),
	)
	root = result[0]
	oh = result[1]
	ch2oh = result[2]
	oh_angle = math.degrees(math.atan2(oh.y - root.y, oh.x - root.x)) % 360
	ch2_angle = math.degrees(math.atan2(ch2oh.y - root.y, ch2oh.x - root.x)) % 360
	# coords_generator2 produces symmetric 30/150 for down direction
	assert oh_angle == pytest.approx(30.0, abs=0.1)
	assert ch2_angle == pytest.approx(150.0, abs=0.1)


def test_two_carbon_tail_parent_indices():
	"""All branches share root (index 0) as parent."""
	result = fragment_layout.layout_fragment(
		"CH(OH)CH2OH", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	assert result[0].parent_index == -1
	assert result[1].parent_index == 0
	assert result[2].parent_index == 0


#============================================
# Chain fragment tests (CHAIN<N>)
#============================================

def test_chain3_group_labels():
	"""CHAIN3 groups: junction, OH, junction, OH, CH2OH."""
	result = fragment_layout.layout_fragment(
		"CHAIN3", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	labels = [fa.label for fa in result]
	assert labels == ["", "OH", "", "OH", "CH2OH"]


def test_chain3_all_solid_bonds():
	"""CHAIN3 (not two-carbon tail) should have all solid bonds."""
	result = fragment_layout.layout_fragment(
		"CHAIN3", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	for fa in result:
		assert fa.bond_style == "solid"


def test_chain3_root_offset():
	"""CHAIN3 root should be offset from attachment point."""
	result = fragment_layout.layout_fragment(
		"CHAIN3", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	root = result[0]
	assert root.x == pytest.approx(100.0, abs=1.0)
	assert root.y == pytest.approx(50.0 - 13.5, abs=1.0)


def test_chain2_group_count():
	"""CHAIN2 = C(O)CO should produce same structure as CH(OH)CH2OH."""
	result = fragment_layout.layout_fragment(
		"CHAIN2", 13.5, (100.0, 50.0), (0.0, -1.0), "up",
	)
	assert result is not None
	# CHAIN2 goes through coords_generator2 path, not two-carbon tail
	assert len(result) >= 3


#============================================
# Molecule identification tests
#============================================

def test_identify_groups_c_o_co():
	"""C(O)CO should produce 3 groups: junction, OH, CH2OH."""
	mol = fragment_layout._build_molecule("C(O)CO")
	groups = fragment_layout._identify_fragment_groups(mol)
	labels = [g["label"] for g in groups]
	assert "" in labels
	assert "OH" in labels
	assert "CH2OH" in labels


def test_identify_groups_c_o_c_o_co():
	"""C(O)C(O)CO should produce 5 groups."""
	mol = fragment_layout._build_molecule("C(O)C(O)CO")
	groups = fragment_layout._identify_fragment_groups(mol)
	labels = [g["label"] for g in groups]
	assert labels.count("") == 2
	assert labels.count("OH") == 2
	assert labels.count("CH2OH") == 1
