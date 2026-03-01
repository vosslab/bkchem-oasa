"""Format bridge integrating OASA codec registry for chemistry file I/O."""

# Standard Library
import os

# local repo modules
import oasa.codec_registry
import oasa.inchi_lib
import bkchem_qt.bridge.oasa_bridge

# Supported format mappings: extension -> codec name
FORMAT_MAP = {
	".mol": "molfile",
	".sdf": "sdf",
	".smi": "smiles",
	".smiles": "smiles",
	".cml": "cml",
	".cdml": "cdml",
	".cdxml": "cdxml",
	".cdsvg": "cdsvg",
	".inchi": "inchi",
	".txt": "inchi",
}

# Human-readable descriptions for import formats
_IMPORT_DESCRIPTIONS = {
	".mol": "MDL Molfile (V2000/V3000)",
	".sdf": "Structure-Data File",
	".smi": "SMILES",
	".smiles": "SMILES",
	".cml": "Chemical Markup Language",
	".cdml": "CDML (BKChem native)",
	".cdxml": "ChemDraw XML",
	".cdsvg": "CDML in SVG",
	".inchi": "InChI",
	".txt": "InChI (text)",
}

# Human-readable descriptions for export formats
_EXPORT_DESCRIPTIONS = {
	".mol": "MDL Molfile (V2000)",
	".sdf": "Structure-Data File",
	".smi": "SMILES",
	".cdml": "CDML (BKChem native)",
	".cdxml": "ChemDraw XML",
	".cdsvg": "CDML in SVG",
	".inchi": "InChI",
}


#============================================
def import_file(file_path: str) -> list:
	"""Import a chemistry file and return list of MoleculeModel.

	Determines format from file extension, uses OASA codec to read,
	then converts to Qt model objects via bridge.

	Args:
		file_path: Path to the chemistry file to import.

	Returns:
		List of MoleculeModel instances, one per connected component.

	Raises:
		ValueError: If the file extension is not recognized.
		FileNotFoundError: If the file does not exist.
	"""
	if not os.path.isfile(file_path):
		raise FileNotFoundError(f"File not found: {file_path}")
	# determine codec from extension
	ext = os.path.splitext(file_path)[1].lower()
	codec_name = FORMAT_MAP.get(ext)
	if codec_name is None:
		raise ValueError(f"Unsupported file extension: {ext}")
	# read via OASA bridge
	with open(file_path, "r") as f:
		results = bkchem_qt.bridge.oasa_bridge.read_codec_file(codec_name, f)
	return results


#============================================
def export_smiles(mol_model) -> str:
	"""Export molecule as SMILES string.

	Converts the MoleculeModel to an OASA molecule and uses the
	SMILES codec to generate a SMILES string.

	Args:
		mol_model: MoleculeModel to export.

	Returns:
		SMILES string representation of the molecule.
	"""
	oasa_mol = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(mol_model)
	codec = oasa.codec_registry.get_codec("smiles")
	smiles_str = codec.mol_to_text(oasa_mol)
	return smiles_str


#============================================
def export_inchi(mol_model) -> tuple:
	"""Export molecule as InChI.

	Converts the MoleculeModel to an OASA molecule and generates
	InChI, InChIKey, and any warnings from the conversion.

	Args:
		mol_model: MoleculeModel to export.

	Returns:
		Tuple of (inchi_string, inchikey_string, warnings_list).
	"""
	oasa_mol = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(mol_model)
	result = oasa.inchi_lib.generate_inchi_and_inchikey(oasa_mol)
	return result


#============================================
def get_supported_import_formats() -> dict:
	"""Return dict of extension -> description for supported import formats.

	Only includes formats whose OASA codec supports reading files.

	Returns:
		Dict mapping file extension strings to human-readable descriptions.
	"""
	oasa.codec_registry._ensure_defaults_registered()
	supported = {}
	for ext, codec_name in FORMAT_MAP.items():
		codec = oasa.codec_registry.get_codec(codec_name)
		if codec.reads_files:
			description = _IMPORT_DESCRIPTIONS.get(ext, codec_name)
			supported[ext] = description
	return supported


#============================================
def get_supported_export_formats() -> dict:
	"""Return dict of extension -> description for supported export formats.

	Only includes formats whose OASA codec supports writing files.

	Returns:
		Dict mapping file extension strings to human-readable descriptions.
	"""
	oasa.codec_registry._ensure_defaults_registered()
	supported = {}
	for ext, description in _EXPORT_DESCRIPTIONS.items():
		codec_name = FORMAT_MAP.get(ext)
		if codec_name is None:
			continue
		codec = oasa.codec_registry.get_codec(codec_name)
		if codec.writes_files:
			supported[ext] = description
	return supported
