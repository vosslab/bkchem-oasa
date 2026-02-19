#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later

"""Unit tests for oasa.peptide_utils."""

# Standard Library
import random

# Third Party
import pytest

# local repo modules
import oasa
from oasa import peptide_utils
from oasa import smiles as smiles_module


#============================================
def _random_sequence(length: int) -> str:
	"""Generate a random amino acid sequence of the given length.

	Args:
		length: number of residues

	Returns:
		string of single-letter amino acid codes
	"""
	letters = sorted(peptide_utils.AMINO_ACID_SMILES.keys())
	return ''.join(random.choice(letters) for _ in range(length))


#============================================
def test_sequence_to_smiles_ankle():
	"""ANKLE should produce a valid SMILES that OASA can parse."""
	smiles_text = peptide_utils.sequence_to_smiles('ANKLE')
	assert smiles_text, "SMILES string should not be empty"
	# parse through OASA SMILES reader
	sm = smiles_module.smiles()
	sm.read_smiles(smiles_text)
	mol = sm.structure
	# ANKLE has 5 residues, molecule should have atoms
	assert len(mol.vertices) > 5, f"expected many atoms, got {len(mol.vertices)}"


#============================================
def test_sequence_to_smiles_random_9():
	"""A random 9-residue sequence should produce parseable SMILES."""
	sequence = _random_sequence(9)
	smiles_text = peptide_utils.sequence_to_smiles(sequence)
	assert smiles_text, f"SMILES for '{sequence}' should not be empty"
	# verify OASA can parse the generated SMILES
	sm = smiles_module.smiles()
	sm.read_smiles(smiles_text)
	mol = sm.structure
	# 9 residues should produce a substantial molecule
	assert len(mol.vertices) > 9, (
		f"sequence '{sequence}' produced only {len(mol.vertices)} atoms"
	)


#============================================
def test_sequence_to_smiles_single_residue():
	"""Each supported amino acid should work as a single residue."""
	for aa in sorted(peptide_utils.AMINO_ACID_SMILES.keys()):
		smiles_text = peptide_utils.sequence_to_smiles(aa)
		sm = smiles_module.smiles()
		sm.read_smiles(smiles_text)
		mol = sm.structure
		assert len(mol.vertices) > 0, f"residue '{aa}' produced no atoms"


#============================================
def test_invalid_residue_raises():
	"""Unknown amino acid letters should raise ValueError."""
	with pytest.raises(ValueError, match="Unknown amino acid"):
		peptide_utils.sequence_to_smiles('ANKXLE')


#============================================
def test_proline_raises():
	"""Proline (P) should raise ValueError with a clear message."""
	with pytest.raises(ValueError, match="Proline"):
		peptide_utils.sequence_to_smiles('APE')


#============================================
def test_lowercase_input():
	"""Lowercase input should be accepted and uppercased."""
	smiles_lower = peptide_utils.sequence_to_smiles('ankle')
	smiles_upper = peptide_utils.sequence_to_smiles('ANKLE')
	assert smiles_lower == smiles_upper


#============================================
def test_no_placeholder_leaks():
	"""Generated SMILES should never contain R-group placeholder text."""
	sequence = _random_sequence(9)
	smiles_text = peptide_utils.sequence_to_smiles(sequence)
	# R followed by a digit would indicate a leaked placeholder
	import re
	assert not re.search(r'R\d', smiles_text), (
		f"placeholder leaked in SMILES for '{sequence}': {smiles_text}"
	)
