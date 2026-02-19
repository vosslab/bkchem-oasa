#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""CDXML molecule import/export helpers for OASA."""

# Standard Library
import xml.dom.minidom

# local repo modules
from oasa import dom_extensions
from oasa import safe_xml
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
def _safe_text(value):
	if value is None:
		return ""
	return str(value).strip()


#============================================
def _safe_float(value, default=0.0):
	text = _safe_text(value)
	if not text:
		return float(default)
	try:
		return float(text)
	except ValueError:
		return float(default)


#============================================
def _safe_int(value, default=0):
	text = _safe_text(value)
	if not text:
		return int(default)
	try:
		return int(text)
	except ValueError:
		return int(default)


#============================================
def _normalize_symbol(symbol_text):
	text = _safe_text(symbol_text)
	if not text:
		return "C"
	candidate = text[0].upper() + text[1:].lower()
	if candidate in periodic_table:
		return candidate
	return "C"


#============================================
def _read_atom_label(atom_node):
	labels = []
	for text_node in atom_node.getElementsByTagName("t"):
		for style_node in text_node.getElementsByTagName("s"):
			text_value = _safe_text(dom_extensions.getAllTextFromElement(style_node))
			if text_value:
				labels.append(text_value)
	if labels:
		return labels[0]
	return "C"


#============================================
def _parse_fragment(fragment_node):
	out = molecule()
	atom_id_map = {}
	for node in fragment_node.childNodes:
		if node.nodeType != node.ELEMENT_NODE:
			continue
		if node.nodeName != "n":
			continue
		atom_id = _safe_text(node.getAttribute("id"))
		coords = _safe_text(node.getAttribute("p")).split()
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

	for node in fragment_node.childNodes:
		if node.nodeType != node.ELEMENT_NODE:
			continue
		if node.nodeName != "b":
			continue
		ref_begin = _safe_text(node.getAttribute("B"))
		ref_end = _safe_text(node.getAttribute("E"))
		atom_1 = atom_id_map.get(ref_begin)
		atom_2 = atom_id_map.get(ref_end)
		if atom_1 is None or atom_2 is None:
			continue
		order = _safe_int(node.getAttribute("Order"), default=1)
		bond_type = _DISPLAY_TO_BOND_TYPE.get(_safe_text(node.getAttribute("Display")), "n")
		new_bond = bond(order=order, type=bond_type)
		out.add_edge(atom_1, atom_2, new_bond)
	return out


#============================================
def _merge_molecules(molecules):
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
def _collect_molecules(text):
	document = safe_xml.parse_dom_from_string(text)
	molecules = []
	for fragment_node in document.getElementsByTagName("fragment"):
		parent_name = _safe_text(getattr(fragment_node.parentNode, "nodeName", ""))
		if parent_name and parent_name != "page":
			continue
		parsed = _parse_fragment(fragment_node)
		if parsed and parsed.vertices:
			molecules.append(parsed)
	return molecules


#============================================
def text_to_mol(text):
	molecules = _collect_molecules(text)
	return _merge_molecules(molecules)


#============================================
def file_to_mol(file_obj):
	return text_to_mol(file_obj.read())


#============================================
def _atom_label(atom_obj):
	label = atom_obj.properties_.get("cdxml_label")
	if label:
		return _safe_text(label)
	return atom_obj.symbol


#============================================
def _write_fragment(doc, parent_node, mol, fragment_index):
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
def mol_to_text(mol):
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
def mol_to_file(mol, file_obj):
	file_obj.write(mol_to_text(mol))
