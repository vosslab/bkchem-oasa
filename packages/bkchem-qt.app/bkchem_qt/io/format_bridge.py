"""Format bridge integrating OASA codec registry for chemistry file I/O."""

# Standard Library
import os

# local repo modules
import oasa.codec_registry
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.io.import_capabilities

# Export capability work is intentionally outside this import-only slice.
# Retain the established export query separately so import routing cannot
# accidentally advertise a writer as a reader.
_EXPORT_FORMAT_MAP = {
	".mol": "molfile",
	".sdf": "sdf",
	".smi": "smiles",
	".cdml": "cdml",
	".cdxml": "cdxml",
	".cdsvg": "cdsvg",
	".inchi": "inchi",
}
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
	capability = bkchem_qt.io.import_capabilities.capability_for_extension(ext)
	if capability.route != "worker":
		raise ValueError(
			"Native CDML must be loaded through the document loader: %s" % ext
		)
	# read via OASA bridge
	with open(file_path, "r") as f:
		results = bkchem_qt.bridge.oasa_bridge.read_codec_file(
			capability.codec_name, f,
		)
	return results


#============================================
def get_supported_import_formats() -> dict:
	"""Return dict of extension -> description for supported import formats.

	Only includes formats whose OASA codec supports reading files.

	Returns:
		Dict mapping file extension strings to human-readable descriptions.
	"""
	return {
		extension: capability.description
		for capability in bkchem_qt.io.import_capabilities.all_import_capabilities()
		for extension in capability.extensions
	}


#============================================
def get_supported_export_formats() -> dict:
	"""Return dict of extension -> description for supported export formats.

	Only includes formats whose OASA codec supports writing files.

	Returns:
		Dict mapping file extension strings to human-readable descriptions.
	"""
	supported = {}
	for extension, description in _EXPORT_DESCRIPTIONS.items():
		codec_name = _EXPORT_FORMAT_MAP[extension]
		codec = oasa.codec_registry.get_codec(codec_name)
		if codec.writes_files:
			supported[extension] = description
	return supported
