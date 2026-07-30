"""Legacy molecule-only CDML import helpers for BKChem-Qt."""

# local repo modules
import oasa.cdml_writer
from oasa import dom_extensions as dom_ext
from oasa import safe_xml
from oasa.cdml_writer import POINTS_PER_CM

import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.io.cdml_document_io
import bkchem_qt.models.molecule_model


load_cdml_document_file = bkchem_qt.io.cdml_document_io.load_cdml_document_file
load_cdml_document_string = bkchem_qt.io.cdml_document_io.load_cdml_document_string


#============================================
def load_cdml_file(file_path: str, bond_length_pt: float | None = None) -> list:
	"""Load a CDML file and return a list of MoleculeModel objects.

	Parses the CDML XML document, extracts each ``<molecule>`` element,
	converts it to an OASA molecule via ``read_cdml_molecule_element()``,
	and wraps each in a MoleculeModel through the bridge layer. Handles
	disconnected molecules by splitting into separate models.

	CDML coordinates are stored in cm with a ``cm`` suffix. The OASA
	reader converts these to points (72 dpi) internally. The bridge
	then rescales to scene-space points.

	Args:
		file_path: Path to the CDML file on disk.
		bond_length_pt: Target bond length in scene-space points.

	Returns:
		List of MoleculeModel instances parsed from the file.
	"""
	with open(file_path, "r") as f:
		text = f.read()
	return load_cdml_string(text, bond_length_pt=bond_length_pt)


#============================================
def load_cdml_string(cdml_text: str, bond_length_pt: float | None = None) -> list:
	"""Load CDML from a string and return a list of MoleculeModel objects.

	Useful for clipboard paste and unit testing. Delegates parsing to
	the OASA CDML reader and converts results through the bridge.

	Args:
		cdml_text: CDML XML text.
		bond_length_pt: Target bond length in scene-space points.

	Returns:
		List of MoleculeModel instances parsed from the text.
	"""
	doc = safe_xml.parse_dom_from_string(cdml_text)
	target_bond_length = (
		bkchem_qt.bridge.oasa_bridge.DEFAULT_BOND_LENGTH_PT
		if bond_length_pt is None
		else bond_length_pt
	)
	# search for all <molecule> elements anywhere in the document
	molecule_elements = dom_ext.simpleXPathSearch(doc, "//molecule")
	results = []
	for mol_el in molecule_elements:
		oasa_mol = oasa.cdml_writer.read_cdml_molecule_element(mol_el)
		if oasa_mol is None:
			continue
		# split disconnected molecules into separate models
		if oasa_mol.is_connected():
			parts = [oasa_mol]
		else:
			parts = oasa_mol.get_disconnected_subgraphs()
		for part in parts:
			mol_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(
				part, bond_length_pt=target_bond_length,
			)
			results.append(mol_model)
	return results


#============================================
def _px_to_cm_text(value: float) -> str:
	"""Convert a pixel coordinate to a CDML-style cm string.

	Args:
		value: Coordinate value in scene-space points.

	Returns:
		String like '3.500cm'.
	"""
	if value is None:
		value = 0.0
	cm_value = float(value) / POINTS_PER_CM
	text = "%.3fcm" % cm_value
	return text
