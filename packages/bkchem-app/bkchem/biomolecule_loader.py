#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program

#--------------------------------------------------------------------------

"""Loader for biomolecule SMILES templates from oasa_data YAML."""

# Standard Library
import os

# PIP3 modules
import yaml

# local repo modules
import oasa


# path to oasa_data directory inside the oasa package
_OASA_DATA_DIR = os.path.join(os.path.dirname(oasa.__file__), '..', 'oasa_data')
_YAML_FILENAME = 'biomolecule_smiles.yaml'


#============================================
def _locate_yaml() -> str:
	"""Locate the biomolecule_smiles.yaml file in the oasa_data directory.

	Returns:
		str: Absolute path to the YAML file.

	Raises:
		FileNotFoundError: If the YAML file cannot be found.
	"""
	yaml_path = os.path.normpath(os.path.join(_OASA_DATA_DIR, _YAML_FILENAME))
	if not os.path.isfile(yaml_path):
		raise FileNotFoundError(f"biomolecule SMILES YAML not found: {yaml_path}")
	return yaml_path


#============================================
def load_biomolecule_entries() -> list:
	"""Load biomolecule entries from the YAML file.

	Parses the nested YAML structure and returns a flat list of
	entry dicts suitable for template registration.

	Returns:
		list[dict]: Each dict has keys: category, subcategory, name,
			label, smiles.
	"""
	yaml_path = _locate_yaml()
	with open(yaml_path, 'r') as handle:
		data = yaml.safe_load(handle)
	if not data:
		return []
	entries = []
	# walk the nested category -> subcategory -> molecule structure
	for category, subcats in data.items():
		if not isinstance(subcats, dict):
			continue
		for subcategory, molecules in subcats.items():
			if not isinstance(molecules, dict):
				continue
			for mol_name, props in molecules.items():
				if not isinstance(props, dict):
					continue
				smiles = props.get('smiles')
				if not smiles:
					continue
				label = props.get('label', mol_name)
				entry = {
					'category': category,
					'subcategory': subcategory,
					'name': mol_name,
					'label': label,
					'smiles': smiles,
				}
				entries.append(entry)
	return entries
