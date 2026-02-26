# SPDX-License-Identifier: LGPL-3.0-or-later
#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#--------------------------------------------------------------------------

"""RDKit-backed file format codecs for Molfile V2000/V3000, SDF, SMILES, SMARTS, and InChI."""

# Standard Library
import io

# PIP3 modules
import rdkit.Chem
import rdkit.Chem.AllChem
import rdkit.Chem.inchi

# local repo modules
from oasa import coords_generator
from oasa import rdkit_bridge


#============================================
def _oasa_to_rdkit(mol):
	"""Convert an OASA molecule to an RDKit Mol for export.

	Args:
		mol: OASA molecule object.

	Returns:
		RDKit Mol object with 2D coordinates.
	"""
	rmol, _atom_map = rdkit_bridge.oasa_to_rdkit_mol(mol)
	# generate 2D coords if none exist on the RDKit mol
	if rmol.GetNumConformers() == 0:
		rdkit.Chem.AllChem.Compute2DCoords(rmol)
	return rmol


#============================================
def _rdkit_to_oasa(rmol):
	"""Convert an RDKit Mol to an OASA molecule, generating coords if needed.

	Kekulizes the RDKit molecule first so aromatic bonds are converted to
	explicit single/double orders. Without this, the bridge would produce
	OASA bonds with order=None (the OASA aromatic sentinel), which breaks
	downstream code that compares bond.order to integers.

	Args:
		rmol: RDKit Mol object.

	Returns:
		OASA molecule with 2D coordinates.
	"""
	# kekulize so aromatic bonds become explicit single/double
	rdkit.Chem.Kekulize(rmol, clearAromaticFlags=False)
	omol, _idx_map = rdkit_bridge.rdkit_to_oasa_mol(rmol)
	# generate coords only when the molecule lacks them
	coords_generator.calculate_coords(omol, bond_length=1.0, force=0)
	return omol


# ===================================================================
# Molfile V2000 codec
# ===================================================================

#============================================
def molfile_text_to_mol(text):
	"""Read a V2000 (or V3000) mol block and return an OASA molecule.

	RDKit auto-detects V2000 vs V3000 on read.

	Args:
		text: Molfile text string.

	Returns:
		OASA molecule.
	"""
	rmol = rdkit.Chem.MolFromMolBlock(text, sanitize=True, removeHs=False)
	if rmol is None:
		raise ValueError("RDKit could not parse the mol block.")
	return _rdkit_to_oasa(rmol)


#============================================
def molfile_mol_to_text(mol):
	"""Write an OASA molecule as a V2000 mol block.

	Args:
		mol: OASA molecule.

	Returns:
		V2000 mol block string.
	"""
	rmol = _oasa_to_rdkit(mol)
	text = rdkit.Chem.MolToMolBlock(rmol)
	return text


#============================================
def molfile_file_to_mol(file_obj):
	"""Read a mol block from a file object.

	Args:
		file_obj: Readable file object (text mode).

	Returns:
		OASA molecule.
	"""
	return molfile_text_to_mol(file_obj.read())


#============================================
def molfile_mol_to_file(mol, file_obj):
	"""Write an OASA molecule as a V2000 mol block to a file object.

	Args:
		mol: OASA molecule.
		file_obj: Writable file object.
	"""
	text = molfile_mol_to_text(mol)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text)
	else:
		file_obj.write(text.encode("utf-8"))


# ===================================================================
# Molfile V3000 codec
# ===================================================================

#============================================
def molfile_v3000_text_to_mol(text):
	"""Read a V3000 (or V2000) mol block and return an OASA molecule.

	Args:
		text: Molfile text (V2000 or V3000 auto-detected by RDKit).

	Returns:
		OASA molecule.
	"""
	rmol = rdkit.Chem.MolFromMolBlock(text, sanitize=True, removeHs=False)
	if rmol is None:
		raise ValueError("RDKit could not parse the mol block.")
	return _rdkit_to_oasa(rmol)


#============================================
def molfile_v3000_mol_to_text(mol):
	"""Write an OASA molecule as a V3000 mol block.

	Args:
		mol: OASA molecule.

	Returns:
		V3000 mol block string.
	"""
	rmol = _oasa_to_rdkit(mol)
	text = rdkit.Chem.MolToV3KMolBlock(rmol)
	return text


#============================================
def molfile_v3000_file_to_mol(file_obj):
	"""Read a V3000 mol block from a file object.

	Args:
		file_obj: Readable file object (text mode).

	Returns:
		OASA molecule.
	"""
	return molfile_v3000_text_to_mol(file_obj.read())


#============================================
def molfile_v3000_mol_to_file(mol, file_obj):
	"""Write an OASA molecule as a V3000 mol block to a file object.

	Args:
		mol: OASA molecule.
		file_obj: Writable file object.
	"""
	text = molfile_v3000_mol_to_text(mol)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text)
	else:
		file_obj.write(text.encode("utf-8"))


# ===================================================================
# SDF (V2000) codec
# ===================================================================

#============================================
def sdf_text_to_mol(text):
	"""Read an SDF string and return merged OASA molecules.

	Multiple records are merged into one disconnected OASA molecule.
	The bridge layer splits disconnected subgraphs into separate
	BKChem molecules.

	Args:
		text: SDF file content as a string.

	Returns:
		OASA molecule (may contain disconnected components).
	"""
	# ForwardSDMolSupplier needs binary input
	data = text.encode("utf-8") if isinstance(text, str) else text
	supplier = rdkit.Chem.ForwardSDMolSupplier(
		io.BytesIO(data), sanitize=True, removeHs=False,
	)
	merged = None
	count = 0
	for rmol in supplier:
		if rmol is None:
			continue
		omol = _rdkit_to_oasa(rmol)
		if merged is None:
			merged = omol
		else:
			# merge atoms and bonds into a single disconnected molecule
			# copy atoms first, then bonds referencing those atoms
			from oasa.atom_lib import Atom as atom_cls
			from oasa.bond_lib import Bond as bond_cls
			atom_map = {}
			for oatom in list(omol.atoms):
				new_atom = atom_cls(symbol=oatom.symbol, charge=oatom.charge)
				new_atom.x = oatom.x
				new_atom.y = oatom.y
				merged.add_vertex(new_atom)
				atom_map[oatom] = new_atom
			for obond in list(omol.bonds):
				a1, a2 = obond.vertices
				new_bond = bond_cls(order=obond.order)
				merged.add_edge(atom_map[a1], atom_map[a2], new_bond)
		count += 1
	if merged is None or count == 0:
		raise ValueError("No valid molecules found in the SDF data.")
	return merged


#============================================
def sdf_mol_to_text(mol):
	"""Write an OASA molecule as an SDF record.

	Args:
		mol: OASA molecule.

	Returns:
		SDF string with trailing $$$$ delimiter.
	"""
	rmol = _oasa_to_rdkit(mol)
	out = io.StringIO()
	writer = rdkit.Chem.SDWriter(out)
	writer.write(rmol)
	writer.close()
	return out.getvalue()


#============================================
def sdf_file_to_mol(file_obj):
	"""Read an SDF file and return merged OASA molecules.

	Args:
		file_obj: Readable file object (text mode).

	Returns:
		OASA molecule.
	"""
	return sdf_text_to_mol(file_obj.read())


#============================================
def sdf_mol_to_file(mol, file_obj):
	"""Write an OASA molecule to an SDF file.

	Args:
		mol: OASA molecule.
		file_obj: Writable file object.
	"""
	text = sdf_mol_to_text(mol)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text)
	else:
		file_obj.write(text.encode("utf-8"))


# ===================================================================
# SDF V3000 codec
# ===================================================================

#============================================
def sdf_v3000_text_to_mol(text):
	"""Read an SDF V3000 string and return merged OASA molecules.

	Args:
		text: SDF file content as a string (V3000 or V2000 auto-detected).

	Returns:
		OASA molecule (may contain disconnected components).
	"""
	# reuse the same reader; RDKit auto-detects V2000 vs V3000
	return sdf_text_to_mol(text)


#============================================
def sdf_v3000_mol_to_text(mol):
	"""Write an OASA molecule as an SDF V3000 record.

	Args:
		mol: OASA molecule.

	Returns:
		SDF V3000 string.
	"""
	rmol = _oasa_to_rdkit(mol)
	out = io.StringIO()
	writer = rdkit.Chem.SDWriter(out)
	writer.SetForceV3000(True)
	writer.write(rmol)
	writer.close()
	return out.getvalue()


#============================================
def sdf_v3000_file_to_mol(file_obj):
	"""Read an SDF V3000 file and return merged OASA molecules.

	Args:
		file_obj: Readable file object (text mode).

	Returns:
		OASA molecule.
	"""
	return sdf_v3000_text_to_mol(file_obj.read())


#============================================
def sdf_v3000_mol_to_file(mol, file_obj):
	"""Write an OASA molecule to an SDF V3000 file.

	Args:
		mol: OASA molecule.
		file_obj: Writable file object.
	"""
	text = sdf_v3000_mol_to_text(mol)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text)
	else:
		file_obj.write(text.encode("utf-8"))


# ===================================================================
# SMARTS codec (export-only)
# ===================================================================

#============================================
def smarts_mol_to_text(mol):
	"""Write an OASA molecule as a SMARTS string.

	Args:
		mol: OASA molecule.

	Returns:
		SMARTS string.
	"""
	rmol = _oasa_to_rdkit(mol)
	text = rdkit.Chem.MolToSmarts(rmol)
	if not text:
		raise ValueError("RDKit could not generate SMARTS for this molecule.")
	return text


#============================================
def smarts_mol_to_file(mol, file_obj):
	"""Write an OASA molecule as SMARTS to a file.

	Args:
		mol: OASA molecule.
		file_obj: Writable file object.
	"""
	text = smarts_mol_to_text(mol)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text + "\n")
	else:
		file_obj.write((text + "\n").encode("utf-8"))


# ===================================================================
# SMILES codec
# ===================================================================

#============================================
def smiles_text_to_mol(text, calc_coords=1, localize_aromatic_bonds=True,
	include_hydrogens=False):
	"""Read a SMILES string and return an OASA molecule using RDKit.

	Args:
		text: SMILES string.
		calc_coords: Bond length for coordinate generation, 0/False to skip.
		localize_aromatic_bonds: Whether to localize aromatic bonds.
		include_hydrogens: If True, keep explicit hydrogens.

	Returns:
		OASA molecule with 2D coordinates (if calc_coords is truthy).
	"""
	smiles_str = text.strip()
	if not smiles_str:
		raise ValueError("Empty SMILES string.")
	rmol = rdkit.Chem.MolFromSmiles(smiles_str, sanitize=True)
	if rmol is None:
		raise ValueError("RDKit could not parse the SMILES string.")
	if not include_hydrogens:
		# RDKit adds implicit Hs; keep only explicit ones
		rmol = rdkit.Chem.RemoveHs(rmol)
	else:
		rmol = rdkit.Chem.AddHs(rmol)
	omol = _rdkit_to_oasa(rmol)
	if localize_aromatic_bonds:
		# RDKit already kekulizes during sanitization, but mark for OASA
		for bond in omol.bonds:
			bond.aromatic = 0
	if calc_coords:
		bond_length = calc_coords if isinstance(calc_coords, (int, float)) and calc_coords > 0 else 1.0
		coords_generator.calculate_coords(omol, bond_length=bond_length, force=1)
	return omol


#============================================
def smiles_mol_to_text(mol):
	"""Write an OASA molecule as a SMILES string using RDKit.

	Args:
		mol: OASA molecule.

	Returns:
		SMILES string.
	"""
	rmol = _oasa_to_rdkit(mol)
	text = rdkit.Chem.MolToSmiles(rmol)
	if text is None:
		raise ValueError("RDKit could not generate SMILES for this molecule.")
	return text


#============================================
def smiles_file_to_mol(file_obj):
	"""Read a SMILES file and return an OASA molecule.

	Args:
		file_obj: Readable file object (text mode).

	Returns:
		OASA molecule.
	"""
	return smiles_text_to_mol(file_obj.read())


#============================================
def smiles_mol_to_file(mol, file_obj):
	"""Write an OASA molecule as SMILES to a file.

	Args:
		mol: OASA molecule.
		file_obj: Writable file object.
	"""
	text = smiles_mol_to_text(mol)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text + "\n")
	else:
		file_obj.write((text + "\n").encode("utf-8"))


# ===================================================================
# InChI codec (RDKit-native, replaces external binary)
# ===================================================================

#============================================
def inchi_text_to_mol(text, include_hydrogens=True, calc_coords=1):
	"""Read an InChI string and return an OASA molecule using RDKit.

	Args:
		text: InChI string (with or without "InChI=" prefix).
		include_hydrogens: If False, remove unimportant hydrogens.
		calc_coords: Bond length for coordinate generation, 0 to skip.

	Returns:
		OASA molecule with 2D coordinates.
	"""
	inchi_str = text.strip()
	if not inchi_str:
		raise ValueError("Empty InChI string.")
	rmol = rdkit.Chem.inchi.MolFromInchi(inchi_str, sanitize=True, removeHs=False)
	if rmol is None:
		raise ValueError("RDKit could not parse the InChI string.")
	omol = _rdkit_to_oasa(rmol)
	if not include_hydrogens:
		omol.remove_unimportant_hydrogens()
	if calc_coords:
		coords_generator.calculate_coords(omol, bond_length=calc_coords)
	return omol


#============================================
def inchi_file_to_mol(file_obj):
	"""Read an InChI file and return an OASA molecule.

	Args:
		file_obj: Readable file object (text mode).

	Returns:
		OASA molecule.
	"""
	return inchi_text_to_mol(file_obj.read())


#============================================
def inchi_mol_to_text(mol):
	"""Write an OASA molecule as an InChI string using RDKit.

	Args:
		mol: OASA molecule.

	Returns:
		InChI string.
	"""
	rmol = _oasa_to_rdkit(mol)
	inchi_str = rdkit.Chem.inchi.MolToInchi(rmol)
	if not inchi_str:
		raise ValueError("RDKit could not generate InChI for this molecule.")
	return inchi_str


#============================================
def inchi_mol_to_file(mol, file_obj):
	"""Write an OASA molecule as InChI to a file.

	Args:
		mol: OASA molecule.
		file_obj: Writable file object.
	"""
	text = inchi_mol_to_text(mol)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text + "\n")
	else:
		file_obj.write((text + "\n").encode("utf-8"))


#============================================
def generate_inchi_and_inchikey(mol, fixed_hs=True):
	"""Generate InChI and InChIKey for an OASA molecule using RDKit.

	Args:
		mol: OASA molecule.
		fixed_hs: Whether to use fixed hydrogen layer.

	Returns:
		Tuple of (inchi_string, inchikey_string, warnings_list).
	"""
	rmol = _oasa_to_rdkit(mol)
	options = ""
	if fixed_hs:
		options = "/FixedH"
	inchi_str = rdkit.Chem.inchi.MolToInchi(rmol, options=options)
	if not inchi_str:
		raise ValueError("RDKit could not generate InChI for this molecule.")
	key = rdkit.Chem.inchi.InchiToInchiKey(inchi_str)
	warnings = []
	return inchi_str, key, warnings
