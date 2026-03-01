"""CDML file loading and saving for BKChem-Qt."""

# local repo modules
import oasa.cdml_writer
from oasa import dom_extensions as dom_ext
from oasa import safe_xml
from oasa.cdml_writer import POINTS_PER_CM

import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.models.molecule_model


#============================================
def load_cdml_file(file_path: str) -> list:
	"""Load a CDML file and return a list of MoleculeModel objects.

	Parses the CDML XML document, extracts each ``<molecule>`` element,
	converts it to an OASA molecule via ``read_cdml_molecule_element()``,
	and wraps each in a MoleculeModel through the bridge layer. Handles
	disconnected molecules by splitting into separate models.

	CDML coordinates are stored in cm with a ``cm`` suffix. The OASA
	reader converts these to points (72 dpi) internally. The bridge
	then rescales to scene pixels.

	Args:
		file_path: Path to the CDML file on disk.

	Returns:
		List of MoleculeModel instances parsed from the file.
	"""
	with open(file_path, "r") as f:
		text = f.read()
	return load_cdml_string(text)


#============================================
def load_cdml_string(cdml_text: str) -> list:
	"""Load CDML from a string and return a list of MoleculeModel objects.

	Useful for clipboard paste and unit testing. Delegates parsing to
	the OASA CDML reader and converts results through the bridge.

	Args:
		cdml_text: CDML XML text.

	Returns:
		List of MoleculeModel instances parsed from the text.
	"""
	doc = safe_xml.parse_dom_from_string(cdml_text)
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
			mol_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(part)
			results.append(mol_model)
	return results


#============================================
def save_cdml_file(file_path: str, document) -> None:
	"""Save a Document to a CDML file.

	Converts each MoleculeModel to an OASA molecule, serializes to a
	CDML XML document, and writes to disk. Coordinates are converted
	from scene pixels to cm using ``_px_to_cm_text()``.

	Args:
		file_path: Destination file path.
		document: Document model containing molecules.
	"""
	import xml.dom.minidom as dom

	doc = dom.Document()
	cdml_el = doc.createElement("cdml")
	cdml_el.setAttribute("version", str(oasa.cdml_writer.DEFAULT_CDML_VERSION))
	cdml_el.setAttribute("xmlns", str(oasa.cdml_writer.CDML_NAMESPACE))
	# add metadata element
	metadata_el = dom_ext.elementUnder(cdml_el, "metadata")
	dom_ext.elementUnder(
		metadata_el, "doc",
		attributes=(("href", oasa.cdml_writer.CDML_DOC_URL),),
	)
	# serialize each molecule
	for mol_model in document.molecules:
		oasa_mol = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(mol_model)
		mol_el = oasa.cdml_writer.write_cdml_molecule_element(
			oasa_mol,
			doc=doc,
			coord_to_text=_px_to_cm_text,
		)
		cdml_el.appendChild(mol_el)
	doc.appendChild(cdml_el)
	# write the XML to disk
	xml_text = doc.toxml(encoding="utf-8").decode("utf-8")
	with open(file_path, "w", encoding="utf-8") as f:
		f.write(xml_text)


#============================================
def _px_to_cm_text(value: float) -> str:
	"""Convert a pixel coordinate to a CDML-style cm string.

	Args:
		value: Coordinate value in scene pixels.

	Returns:
		String like '3.500cm'.
	"""
	if value is None:
		value = 0.0
	cm_value = float(value) / POINTS_PER_CM
	text = "%.3fcm" % cm_value
	return text
