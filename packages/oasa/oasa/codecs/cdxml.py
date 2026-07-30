#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""CDXML molecule import/export helpers for OASA."""

# Standard Library
import io
import xml.dom.minidom

# PIP3 modules
import lxml.etree

# local repo modules
from oasa import dom_extensions
from oasa.atom_lib import Atom as atom
from oasa.bond_lib import Bond as bond
from oasa.molecule_lib import Molecule as molecule
from oasa.periodic_table import periodic_table


_DISPLAY_TO_BOND_TYPE = {
	"WedgeBegin": "w",
	"WedgedHashBegin": "h",
	"Wavy": "a",
	"Bold": "b",
	"Dash": "d",
}
_BOND_TYPE_TO_DISPLAY = {
	"w": "WedgeBegin",
	"h": "WedgedHashBegin",
	"a": "Wavy",
	"b": "Bold",
	"d": "Dash",
}


#============================================
def _safe_text(value: object) -> str:
	if value is None:
		return ""
	return str(value).strip()


#============================================
def _safe_float(value: object, default: object=0.0) -> float:
	text = _safe_text(value)
	if not text:
		return float(default)
	try:
		return float(text)
	except ValueError:
		return float(default)


#============================================
def _safe_int(value: object, default: object=0) -> int:
	text = _safe_text(value)
	if not text:
		return int(default)
	try:
		return int(text)
	except ValueError:
		return int(default)


#============================================
def _normalize_symbol(symbol_text: object) -> str:
	text = _safe_text(symbol_text)
	if not text:
		return "C"
	candidate = text[0].upper() + text[1:].lower()
	if candidate in periodic_table:
		return candidate
	return "C"


#============================================
def _lxml_element_name(node: object) -> str:
	"""Return an lxml element's local name without accepting non-elements."""
	tag = getattr(node, "tag", None)
	if not isinstance(tag, str):
		return ""
	if tag.startswith("{"):
		return tag.rsplit("}", 1)[1]
	return tag


#============================================
def _is_unprefixed_lxml_element(node: object, name: str) -> bool:
	"""Match legacy minidom's unprefixed, case-sensitive CDXML name matching."""
	return getattr(node, "prefix", None) is None and _lxml_element_name(node) == name


#============================================
def _cdxml_input_parser() -> object:
	"""Create a fresh hardened lxml parser for one external CDXML input."""
	parser = lxml.etree.XMLParser(
		resolve_entities=False,
		load_dtd=False,
		no_network=True,
		dtd_validation=False,
		recover=False,
		huge_tree=False,
		remove_comments=False,
		remove_pis=False,
	)
	return parser


#============================================
def _parse_cdxml_input(text: object) -> object:
	"""Parse external CDXML and reject every DOCTYPE before import traversal.

	Args:
		text: CDXML supplied as text or UTF-8 bytes.

	Raises:
		ValueError: If the input contains any internal or external DOCTYPE.
		lxml.etree.XMLSyntaxError: If the XML is malformed.
	"""
	if isinstance(text, bytes):
		payload = text
	else:
		payload = str(text).encode("utf-8")
	document = lxml.etree.parse(io.BytesIO(payload), _cdxml_input_parser())
	if document.docinfo.doctype:
		raise ValueError("CDXML DOCTYPE is not accepted")
	root = document.getroot()
	return root


#============================================
def _read_atom_label(atom_node: object) -> str:
	"""Read the first nested, unprefixed CDXML text/style label."""
	labels = []
	for text_node in atom_node.iter():
		if not _is_unprefixed_lxml_element(text_node, "t"):
			continue
		for style_node in text_node.iter():
			if not _is_unprefixed_lxml_element(style_node, "s"):
				continue
			text_value = _safe_text("".join(style_node.itertext()))
			if text_value:
				labels.append(text_value)
	if labels:
		return labels[0]
	return "C"


#============================================
def _parse_fragment(fragment_node: object) -> object:
	"""Create one OASA molecule from supported direct CDXML fragment children."""
	out = molecule()
	atom_id_map = {}
	for node in fragment_node:
		if not _is_unprefixed_lxml_element(node, "n"):
			continue
		atom_id = _safe_text(node.get("id"))
		coords = _safe_text(node.get("p")).split()
		x_value = _safe_float(coords[0] if len(coords) > 0 else 0.0)
		y_value = _safe_float(coords[1] if len(coords) > 1 else 0.0)
		label = _read_atom_label(node)
		symbol = _normalize_symbol(label)
		new_atom = atom(symbol=symbol)
		new_atom.x = x_value
		new_atom.y = y_value
		if label and label != symbol:
			new_atom.properties_["cdxml_label"] = label
		out.add_vertex(new_atom)
		if atom_id:
			atom_id_map[atom_id] = new_atom

	for node in fragment_node:
		if not _is_unprefixed_lxml_element(node, "b"):
			continue
		ref_begin = _safe_text(node.get("B"))
		ref_end = _safe_text(node.get("E"))
		atom_1 = atom_id_map.get(ref_begin)
		atom_2 = atom_id_map.get(ref_end)
		if atom_1 is None or atom_2 is None:
			continue
		order = _safe_int(node.get("Order"), default=1)
		bond_type = _DISPLAY_TO_BOND_TYPE.get(_safe_text(node.get("Display")), "n")
		new_bond = bond(order=order, type=bond_type)
		out.add_edge(atom_1, atom_2, new_bond)
	return out


#============================================
def _merge_molecules(molecules: object) -> object | None:
	if not molecules:
		return None
	if len(molecules) == 1:
		return molecules[0]
	merged = molecule()
	for part in molecules:
		vertex_map = {}
		for original_vertex in part.vertices:
			copied_vertex = original_vertex.copy()
			merged.add_vertex(copied_vertex)
			vertex_map[original_vertex] = copied_vertex
		for original_edge in part.edges:
			copied_edge = original_edge.copy()
			vertex_1, vertex_2 = original_edge.vertices
			merged.add_edge(vertex_map[vertex_1], vertex_map[vertex_2], copied_edge)
	return merged


#============================================
def _collect_molecules(text: object) -> list:
	"""Import direct page fragments from one hardened external CDXML input."""
	root = _parse_cdxml_input(text)
	molecules = []
	for fragment_node in root.iter():
		if not _is_unprefixed_lxml_element(fragment_node, "fragment"):
			continue
		parent_node = fragment_node.getparent()
		if not _is_unprefixed_lxml_element(parent_node, "page"):
			continue
		parsed = _parse_fragment(fragment_node)
		if parsed and parsed.vertices:
			molecules.append(parsed)
	return molecules


#============================================
def text_to_mol(text: object) -> object | None:
	molecules = _collect_molecules(text)
	return _merge_molecules(molecules)


#============================================
def file_to_mol(file_obj: object) -> object | None:
	return text_to_mol(file_obj.read())


#============================================
def _atom_label(atom_obj: object) -> str:
	label = atom_obj.properties_.get("cdxml_label")
	if label:
		return _safe_text(label)
	return atom_obj.symbol


#============================================
def _write_fragment(
	doc: object,
	parent_node: object,
	mol: object,
	fragment_index: object,
) -> None:
	fragment_node = doc.createElement("fragment")
	fragment_node.setAttribute("id", f"f{fragment_index}")
	parent_node.appendChild(fragment_node)
	atom_id_map = {}
	for atom_index, atom_obj in enumerate(mol.vertices, start=1):
		atom_id = f"a{fragment_index}_{atom_index}"
		atom_id_map[atom_obj] = atom_id
		atom_node = doc.createElement("n")
		fragment_node.appendChild(atom_node)
		atom_node.setAttribute("id", atom_id)
		atom_node.setAttribute("p", f"{atom_obj.x:.6f} {atom_obj.y:.6f}")
		label = _atom_label(atom_obj)
		if label and label != "C":
			text_node = doc.createElement("t")
			atom_node.appendChild(text_node)
			style_node = doc.createElement("s")
			style_node.setAttribute("font", "1")
			style_node.setAttribute("size", "12")
			style_node.appendChild(doc.createTextNode(label))
			text_node.appendChild(style_node)
	for bond_index, bond_obj in enumerate(mol.edges, start=1):
		bond_node = doc.createElement("b")
		fragment_node.appendChild(bond_node)
		bond_node.setAttribute("id", f"b{fragment_index}_{bond_index}")
		atom_1, atom_2 = bond_obj.vertices
		bond_node.setAttribute("B", atom_id_map[atom_1])
		bond_node.setAttribute("E", atom_id_map[atom_2])
		bond_node.setAttribute("Order", str(int(bond_obj.order)))
		display = _BOND_TYPE_TO_DISPLAY.get(_safe_text(bond_obj.type))
		if display:
			bond_node.setAttribute("Display", display)


#============================================
def mol_to_text(mol: object) -> str:
	document = xml.dom.minidom.Document()
	root = document.createElement("CDXML")
	document.appendChild(root)
	font_table = document.createElement("fonttable")
	root.appendChild(font_table)
	font_node = document.createElement("font")
	font_table.appendChild(font_node)
	font_node.setAttribute("id", "1")
	font_node.setAttribute("name", "Arial")
	page_node = document.createElement("page")
	root.appendChild(page_node)
	fragments = [mol]
	if not mol.is_connected():
		fragments = mol.get_disconnected_subgraphs()
	for index, fragment in enumerate(fragments, start=1):
		_write_fragment(document, page_node, fragment, index)
	dom_extensions.safe_indent(root)
	return document.toxml("utf-8").decode("utf-8")


#============================================
def mol_to_file(mol: object, file_obj: object) -> None:
	file_obj.write(mol_to_text(mol))
