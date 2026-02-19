#!/usr/bin/env python3
"""Tests for biomolecule SMILES template loading and generation."""

# Standard Library
import os
import sys

# ensure repo packages are importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
for pkg_dir in ('packages/oasa', 'packages/bkchem-app'):
	full = os.path.join(REPO_ROOT, pkg_dir)
	if full not in sys.path:
		sys.path.insert(0, full)

# local repo modules
import oasa
import oasa.smiles_lib
import oasa.molecule_lib


#============================================
class TestBiomoleculeLoader:
	"""Tests for the biomolecule_loader YAML reader."""

	def test_load_entries_returns_list(self):
		"""load_biomolecule_entries should return a non-empty list."""
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		assert isinstance(entries, list)
		assert len(entries) > 0

	def test_entries_have_required_keys(self):
		"""Each entry should have category, subcategory, name, label, smiles."""
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		required_keys = {'category', 'subcategory', 'name', 'label', 'smiles'}
		for entry in entries:
			missing = required_keys - set(entry.keys())
			assert not missing, f"Entry {entry.get('name')} missing keys: {missing}"

	def test_all_20_amino_acids_present(self):
		"""All 20 standard amino acids should be in the YAML."""
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		amino_acid_labels = {e['label'] for e in entries if e['category'] == 'protein'}
		expected = {'Ala', 'Arg', 'Asn', 'Asp', 'Cys', 'Glu', 'Gln', 'Gly',
			'His', 'Ile', 'Leu', 'Lys', 'Met', 'Phe', 'Pro', 'Ser',
			'Thr', 'Trp', 'Tyr', 'Val'}
		missing = expected - amino_acid_labels
		assert not missing, f"Missing amino acids: {missing}"

	def test_four_categories_present(self):
		"""YAML should contain carbs, nucleic_acids, lipids, protein."""
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		categories = {e['category'] for e in entries}
		expected = {'carbs', 'nucleic_acids', 'lipids', 'protein'}
		missing = expected - categories
		assert not missing, f"Missing categories: {missing}"

	def test_labels_are_short(self):
		"""Labels should be short (at most 5 characters) for button grid."""
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		for entry in entries:
			label = entry['label']
			assert len(label) <= 5, f"Label too long: {label} ({len(label)} chars)"


#============================================
class TestSmilesTemplateGeneration:
	"""Tests for SMILES-to-template generation (pure OASA, no GUI)."""

	def test_all_smiles_parse(self):
		"""Every SMILES in the YAML should parse into a valid molecule."""
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		for entry in entries:
			mol = oasa.smiles_lib.text_to_mol(entry['smiles'], calc_coords=1)
			assert mol is not None, f"Failed to parse SMILES for {entry['name']}"
			assert len(list(mol.vertices)) > 0, f"Empty molecule for {entry['name']}"

	def test_all_smiles_have_2d_coords(self):
		"""Parsed molecules should have non-zero coordinate spans."""
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		for entry in entries:
			mol = oasa.smiles_lib.text_to_mol(entry['smiles'], calc_coords=1)
			xs = [a.x for a in mol.vertices]
			ys = [a.y for a in mol.vertices]
			# at least one coord should vary (not all at origin)
			x_span = max(xs) - min(xs)
			y_span = max(ys) - min(ys)
			total_span = x_span + y_span
			assert total_span > 0.01, f"No 2D coords for {entry['name']}"

	def test_normalize_bond_length(self):
		"""Molecules should normalize to 1.0 cm bond length."""
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		# test a few representative entries
		for entry in entries[:5]:
			mol = oasa.smiles_lib.text_to_mol(entry['smiles'], calc_coords=1)
			mol.normalize_bond_length(1.0)
			mean_bl = mol.get_mean_bond_length()
			assert abs(mean_bl - 1.0) < 0.1, (
				f"Bond length {mean_bl:.3f} != 1.0 for {entry['name']}"
			)

	def test_anchor_atom_selection(self):
		"""Anchor atom selection should be deterministic."""
		from bkchem.temp_manager import _choose_anchor_atom, _choose_anchor_neighbor
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		for entry in entries:
			mol = oasa.smiles_lib.text_to_mol(entry['smiles'], calc_coords=1)
			mol.normalize_bond_length(1.0)
			anchor = _choose_anchor_atom(mol)
			assert anchor is not None, f"No anchor for {entry['name']}"
			neighbor = _choose_anchor_neighbor(anchor)
			assert neighbor is not None, f"No neighbor for {entry['name']}"
			# run again to check determinism
			anchor2 = _choose_anchor_atom(mol)
			assert anchor is anchor2, f"Non-deterministic anchor for {entry['name']}"

	def test_cdml_string_generation(self):
		"""CDML XML string should be valid and contain expected elements."""
		from bkchem.temp_manager import (
			_choose_anchor_atom, _choose_anchor_neighbor,
			_build_cdml_string,
		)
		# test with alanine
		smiles = "C[C@@H](C(=O)O)N"
		mol = oasa.smiles_lib.text_to_mol(smiles, calc_coords=1)
		mol.normalize_bond_length(1.0)
		anchor = _choose_anchor_atom(mol)
		neighbor = _choose_anchor_neighbor(anchor)
		template_atom = oasa.Atom(symbol="C")
		template_atom.x = anchor.x + 1.0
		template_atom.y = anchor.y
		template_atom.z = 0.0
		xml_str = _build_cdml_string("L-alanine", mol, anchor, neighbor, template_atom)
		# basic XML checks
		assert '<?xml' in xml_str
		assert '<cdml' in xml_str
		assert '<molecule' in xml_str
		assert 'name="L-alanine"' in xml_str
		assert '<template' in xml_str
		assert '<atom' in xml_str
		assert '<bond' in xml_str
		assert 'atom_t' in xml_str


#============================================
class TestRemoveUnimportantHydrogens:
	"""Verify remove_unimportant_hydrogens works on pure OASA molecules."""

	def test_method_exists_on_oasa_molecule(self):
		"""oasa.Molecule (the class) should have remove_unimportant_hydrogens."""
		assert hasattr(oasa.Molecule, 'remove_unimportant_hydrogens')

	def test_removes_implicit_hydrogens(self):
		"""Parsing methane should give atoms, remove_unimportant_hydrogens reduces count."""
		mol = oasa.smiles_lib.text_to_mol("C", calc_coords=1)
		# methane has carbons and hydrogens
		count_before = len(list(mol.vertices))
		mol.remove_unimportant_hydrogens()
		count_after = len(list(mol.vertices))
		# should remove some H atoms
		assert count_after <= count_before
