"""Load biomolecule SMILES templates from OASA package data."""

# Standard Library
import pathlib

# PIP3 modules
import yaml

# local repo modules
import oasa


_YAML_FILENAME = "biomolecule_smiles.yaml"


#============================================
def _locate_yaml() -> pathlib.Path:
	"""Locate the biomolecule template data installed with OASA.

	Returns:
		Path to the biomolecule SMILES YAML file.

	Raises:
		FileNotFoundError: If the OASA package data is unavailable.
	"""
	oasa_dir = pathlib.Path(oasa.__file__).resolve().parent
	yaml_path = oasa_dir.parent / "oasa_data" / _YAML_FILENAME
	if not yaml_path.is_file():
		raise FileNotFoundError(f"biomolecule SMILES YAML not found: {yaml_path}")
	return yaml_path


#============================================
def load_biomolecule_entries() -> list:
	"""Load biomolecule entries for the Qt template mode.

	Returns:
		List of dictionaries with category, subcategory, name, label, and smiles.
	"""
	yaml_path = _locate_yaml()
	with open(yaml_path, "r") as handle:
		data = yaml.safe_load(handle)
	if not data:
		return []
	entries = []
	for category, subcategories in data.items():
		if not isinstance(subcategories, dict):
			continue
		for subcategory, molecules in subcategories.items():
			if not isinstance(molecules, dict):
				continue
			for molecule_name, properties in molecules.items():
				if not isinstance(properties, dict):
					continue
				smiles = properties.get("smiles")
				if not smiles:
					continue
				label = properties.get("label", molecule_name)
				entry = {
					"category": category,
					"subcategory": subcategory,
					"name": molecule_name,
					"label": label,
					"smiles": smiles,
				}
				entries.append(entry)
	return entries
