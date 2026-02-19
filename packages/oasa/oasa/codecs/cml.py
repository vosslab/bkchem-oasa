#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""CML import helpers for OASA molecules.

Supports CML 1.0 style and CML 2.0 read paths for legacy recovery.
"""

# local repo modules
from oasa import dom_extensions
from oasa import safe_xml
from oasa.atom_lib import Atom as atom
from oasa.bond_lib import Bond as bond
from oasa.molecule_lib import Molecule as molecule
from oasa.periodic_table import periodic_table


_VERSION_1 = "1"
_STEREO_TO_TYPE = {"W": "w", "H": "h"}


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
def _read_cml1_atom(atom_node):
	atom_id = _safe_text(atom_node.getAttribute("id"))
	symbol = ""
	x_value = 0.0
	y_value = 0.0
	z_value = 0.0
	charge = 0
	for node in atom_node.childNodes:
		if node.nodeType != node.ELEMENT_NODE:
			continue
		builtin = _safe_text(node.getAttribute("builtin"))
		if builtin == "atomId":
			atom_id = _safe_text(dom_extensions.getTextFromElement(node))
		elif builtin == "elementType":
			symbol = _safe_text(dom_extensions.getTextFromElement(node))
		elif builtin in ("x2", "x3"):
			x_value = _safe_float(dom_extensions.getTextFromElement(node))
		elif builtin in ("y2", "y3"):
			y_value = _safe_float(dom_extensions.getTextFromElement(node))
		elif builtin == "z3":
			z_value = _safe_float(dom_extensions.getTextFromElement(node))
		elif builtin == "formalCharge":
			charge = _safe_int(dom_extensions.getTextFromElement(node))
	return atom_id, symbol, x_value, y_value, z_value, charge


#============================================
def _read_cml2_atom(atom_node):
	atom_id = _safe_text(atom_node.getAttribute("id"))
	symbol = _safe_text(atom_node.getAttribute("elementType"))
	x_value = _safe_float(atom_node.getAttribute("x2"))
	y_value = _safe_float(atom_node.getAttribute("y2"))
	if atom_node.hasAttribute("x3"):
		x_value = _safe_float(atom_node.getAttribute("x3"))
	if atom_node.hasAttribute("y3"):
		y_value = _safe_float(atom_node.getAttribute("y3"))
	z_value = _safe_float(atom_node.getAttribute("z3"))
	charge = _safe_int(atom_node.getAttribute("formalCharge"))
	return atom_id, symbol, x_value, y_value, z_value, charge


#============================================
def _read_atom(atom_node):
	if atom_node.hasAttribute("elementType") or atom_node.hasAttribute("x2"):
		return _read_cml2_atom(atom_node)
	return _read_cml1_atom(atom_node)


#============================================
def _read_cml1_bond(bond_node):
	atom_refs = []
	order = 1
	stereo = "n"
	for node in bond_node.childNodes:
		if node.nodeType != node.ELEMENT_NODE:
			continue
		builtin = _safe_text(node.getAttribute("builtin"))
		if builtin == "atomRef":
			atom_refs.append(_safe_text(dom_extensions.getTextFromElement(node)))
		elif builtin == "order":
			order_text = _safe_text(dom_extensions.getTextFromElement(node)).upper()
			if order_text == "A":
				order = 1
			elif order_text:
				order = _safe_int(order_text, default=1)
		elif builtin == "stereo":
			stereo_text = _safe_text(dom_extensions.getTextFromElement(node)).upper()
			if stereo_text:
				stereo = _STEREO_TO_TYPE.get(stereo_text, "n")
	if len(atom_refs) < 2:
		return None
	return atom_refs[0], atom_refs[1], order, stereo


#============================================
def _read_cml2_bond(bond_node):
	refs_text = _safe_text(bond_node.getAttribute("atomRefs2"))
	refs = [part for part in refs_text.split() if part]
	if len(refs) < 2:
		return None
	order = 1
	order_text = _safe_text(bond_node.getAttribute("order")).upper()
	if order_text:
		if order_text in ("S", "D", "T"):
			order = {"S": 1, "D": 2, "T": 3}[order_text]
		elif order_text == "A":
			order = 1
		else:
			order = _safe_int(order_text, default=1)
	stereo = "n"
	for node in bond_node.getElementsByTagName("stereo"):
		stereo_text = _safe_text(dom_extensions.getTextFromElement(node)).upper()
		if stereo_text:
			stereo = _STEREO_TO_TYPE.get(stereo_text, "n")
			break
	return refs[0], refs[1], order, stereo


#============================================
def _read_bond(bond_node):
	if bond_node.hasAttribute("atomRefs2"):
		return _read_cml2_bond(bond_node)
	return _read_cml1_bond(bond_node)


#============================================
def _collect_direct_children(parent_node, tag_name):
	return [
		node for node in parent_node.childNodes
		if node.nodeType == node.ELEMENT_NODE and node.nodeName == tag_name
	]


#============================================
def _parse_molecule(molecule_node):
	out = molecule()
	atom_id_map = {}
	atom_nodes = []
	bond_nodes = []
	for child in molecule_node.childNodes:
		if child.nodeType != child.ELEMENT_NODE:
			continue
		if child.nodeName == "atomArray":
			atom_nodes.extend(_collect_direct_children(child, "atom"))
		elif child.nodeName == "bondArray":
			bond_nodes.extend(_collect_direct_children(child, "bond"))
	if not atom_nodes:
		atom_nodes = molecule_node.getElementsByTagName("atom")
	if not bond_nodes:
		bond_nodes = molecule_node.getElementsByTagName("bond")

	for atom_node in atom_nodes:
		atom_id, symbol, x_value, y_value, z_value, charge = _read_atom(atom_node)
		new_atom = atom(symbol=_normalize_symbol(symbol))
		new_atom.x = x_value
		new_atom.y = y_value
		new_atom.z = z_value
		new_atom.charge = charge
		out.add_vertex(new_atom)
		if atom_id:
			atom_id_map[atom_id] = new_atom

	for bond_node in bond_nodes:
		parsed_bond = _read_bond(bond_node)
		if not parsed_bond:
			continue
		atom_ref_1, atom_ref_2, order, stereo_type = parsed_bond
		atom_1 = atom_id_map.get(atom_ref_1)
		atom_2 = atom_id_map.get(atom_ref_2)
		if atom_1 is None or atom_2 is None:
			continue
		new_bond = bond(order=order, type=stereo_type)
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
def _collect_molecules_from_text(text):
	document = safe_xml.parse_dom_from_string(text)
	molecule_nodes = document.getElementsByTagName("molecule")
	result = []
	for molecule_node in molecule_nodes:
		parsed = _parse_molecule(molecule_node)
		if parsed and parsed.vertices:
			result.append(parsed)
	return result


#============================================
def text_to_mol(text, version=_VERSION_1):
	_ = version
	molecules = _collect_molecules_from_text(text)
	return _merge_molecules(molecules)


#============================================
def file_to_mol(file_obj, version=_VERSION_1):
	text = file_obj.read()
	return text_to_mol(text, version=version)
