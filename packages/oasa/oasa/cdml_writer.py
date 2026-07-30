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

"""CDML molecule read/write helpers for the OASA codec."""

# Standard Library
import re
import xml.dom.minidom as dom

# local repo modules
from oasa import bond_semantics
from oasa import cdml_bond_io
from oasa import dom_extensions as dom_ext
from oasa import smiles_lib as smiles
from oasa.atom_lib import Atom as atom
from oasa.bond_lib import Bond as bond
from oasa.known_groups import cdml_to_smiles
from oasa.molecule_lib import Molecule as molecule
from oasa.periodic_table import periodic_table as PT


# CPK element colors for non-carbon heteroatom coloring in CDML output
CPK_COLORS = {
	'H':  '#FFFFFF',
	'C':  '#909090',
	'N':  '#3050F8',
	'O':  '#FF0D0D',
	'S':  '#FFFF30',
	'P':  '#FF8000',
	'F':  '#90E050',
	'Cl': '#1FF01F',
	'Br': '#A62929',
	'I':  '#940094',
	'B':  '#FFB5B5',
	'Se': '#FFA100',
	'Fe': '#E06633',
}

POINTS_PER_CM = 72.0 / 2.54
DEFAULT_FONT_SIZE = 12
DEFAULT_FONT_FAMILY = "helvetica"
CDML_NAMESPACE = "http://www.freesoftware.fsf.org/bkchem/cdml"
CDML_DOC_URL = "https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md"
DEFAULT_CDML_VERSION = "26.07"
_INSERTION_TOKEN_STEM_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,48}$")

reads_text = False
writes_text = True
reads_files = False
writes_files = True


#============================================
def read_cdml_molecule_element(mol_el: object) -> molecule | None:
	"""Decode a CDML molecule element with legacy descendant semantics.

	Compatibility callers historically receive matching descendants regardless of
	namespace.  Authoritative document operations use
	:func:`read_direct_core_cdml_molecule_element` instead, so opaque extension
	content cannot become chemistry by name collision.
	"""
	return _read_cdml_molecule_element(mol_el, dom_ext.simpleXPathSearch)


#============================================
def read_direct_core_cdml_molecule_element(mol_el: object) -> molecule | None:
	"""Decode only direct core CDML records from an authoritative molecule.

	The direct-root document boundary accepts both canonical-namespace and
	legacy no-namespace CDML.  Foreign namespaces and nested wrappers remain
	preservation-only content, even when their local names look like molecule
	chemistry records.
	"""
	return _read_cdml_molecule_element(mol_el, _direct_core_children)


#============================================
def _read_cdml_molecule_element(
		mol_el: object, child_selector: object,
		) -> molecule | None:
	"""Decode one molecule through the supplied compatibility or core selector."""
	atom_id_remap = {}
	mol = molecule()
	mol_id = mol_el.getAttribute("id")
	if mol_id:
		mol.id = mol_id
	mol_name = mol_el.getAttribute("name")
	if mol_name:
		mol.name = mol_name
	for atom_el in child_selector(mol_el, "atom"):
		name = atom_el.getAttribute("name")
		if not name:
			return None
		pos_nodes = child_selector(atom_el, "point")
		if not pos_nodes:
			return None
		pos = pos_nodes[0]
		x = _cm_to_float_coord(pos.getAttribute("x"))
		y = _cm_to_float_coord(pos.getAttribute("y"))
		z = _cm_to_float_coord(pos.getAttribute("z"))
		charge = atom_el.getAttribute("charge")
		if name in PT:
			a = atom(
				symbol=name,
				charge=charge and int(charge) or 0,
				coords=(x, y, z),
			)
			multiplicity = atom_el.getAttribute("multiplicity")
			if multiplicity:
				a.multiplicity = int(multiplicity)
			valency = atom_el.getAttribute("valency")
			if valency:
				a.valency = int(valency)
			free_sites = atom_el.getAttribute("free_sites")
			if free_sites:
				a.free_sites = int(free_sites)
			isotope = atom_el.getAttribute("isotope")
			if isotope:
				a.isotope = int(isotope)
			explicit_hydrogens = atom_el.getAttribute("explicit_hydrogens")
			if explicit_hydrogens:
				a.explicit_hydrogens = int(explicit_hydrogens)
			mol.add_vertex(v=a)
		elif name in cdml_to_smiles:
			group = smiles.text_to_mol(cdml_to_smiles[name], calc_coords=0)
			a = group.vertices[0]
			a.x = x
			a.y = y
			a.z = z
			mol.insert_a_graph(group)
		else:
			return None
		atom_id = atom_el.getAttribute("id")
		if atom_id:
			a.id = atom_id
		show = atom_el.getAttribute("show")
		if show:
			a.properties_["show"] = show
		hydrogens = atom_el.getAttribute("hydrogens")
		if hydrogens:
			a.properties_["show_hydrogens"] = hydrogens
		font_elements = child_selector(atom_el, "font")
		if font_elements:
			font_el = font_elements[0]
			font_size = font_el.getAttribute("size")
			if font_size:
				a.properties_["font_size"] = font_size
			font_family = font_el.getAttribute("family")
			if font_family:
				a.properties_["font_family"] = font_family
			line_color = font_el.getAttribute("color")
			if line_color:
				a.properties_["line_color"] = line_color
		atom_id_remap[atom_id] = a

	for bond_el in child_selector(mol_el, "bond"):
		type_value = bond_el.getAttribute("type")
		bond_type, order, legacy = bond_semantics.parse_cdml_bond_type(type_value)
		if order == 0:
			continue
		if not bond_type:
			bond_type = "n"
		v1 = atom_id_remap.get(bond_el.getAttribute("start"))
		v2 = atom_id_remap.get(bond_el.getAttribute("end"))
		if v1 is None or v2 is None:
			continue
		e = bond(order=order, type=bond_type)
		bond_id = bond_el.getAttribute("id")
		if bond_id:
			e.id = bond_id
		if legacy:
			e.properties_["legacy_bond_type"] = legacy
		cdml_bond_io.read_cdml_bond_attributes(
			bond_el,
			e,
			preserve_attrs={
				"line_width",
				"bond_width",
				"wedge_width",
				"double_ratio",
				"center",
				"auto_sign",
				"equithick",
				"simple_double",
				"haworth_position",
			},
		)
		mol.add_edge(v1, v2, e=e)

	return mol


#============================================
def _direct_core_children(element: object, local_name: str) -> list:
	"""Return direct canonical or legacy core children with one local name."""
	children = []
	for child in element.childNodes:
		if child.nodeType != child.ELEMENT_NODE:
			continue
		child_local_name = child.localName or child.nodeName.rsplit(":", 1)[-1]
		if (
				child_local_name == local_name
				and (child.namespaceURI or "") in ("", CDML_NAMESPACE)
			):
			children.append(child)
	return children


#============================================
def write_cdml_molecule_element(
		mol: molecule, *, doc: object = None, policy: str = "present_only",
		coord_to_text: object = None, width_to_text: object = None,
		reserved_atom_ids: set[str] | None = None,
		reserved_bond_ids: set[str] | None = None,
		) -> object:
	"""Serialize a molecule into a CDML <molecule> element."""
	if doc is None:
		doc = dom.Document()
	mol_el = doc.createElement("molecule")
	name = getattr(mol, "name", None)
	if name:
		mol_el.setAttribute("name", str(name))
	mol_id = getattr(mol, "id", None)
	if mol_id:
		mol_el.setAttribute("id", str(mol_id))
	# These reservations are deliberately an output concern.  Callers which
	# retain source XML can avoid reusing a deleted node's ID without assigning
	# a serializer-generated ID back onto an editable chemistry object.
	reserved_ids = set(reserved_atom_ids or ())
	reserved_ids.update(reserved_bond_ids or ())
	if mol_id:
		reserved_ids.add(str(mol_id))
	atom_ids = _assign_atom_ids(mol.vertices, reserved_ids=reserved_ids)
	reserved_ids.update(atom_ids.values())
	bond_ids = _assign_bond_ids(mol.edges, reserved_ids=reserved_ids)
	for atom_obj in mol.vertices:
		mol_el.appendChild(
			_write_cdml_atom_element(
				doc,
				atom_obj,
				atom_ids,
				coord_to_text=coord_to_text,
			)
		)
	for bond_obj in mol.edges:
		mol_el.appendChild(
			_write_cdml_bond_element(
				doc,
				bond_obj,
				atom_ids,
				bond_ids,
				policy=policy,
				width_to_text=width_to_text,
			)
		)
	return mol_el


#============================================
def mol_to_text(
		mol: molecule, *, policy: str = "present_only",
		version: str | None = None, namespace: str | None = None,
		coord_to_text: object = None, width_to_text: object = None,
		reserved_atom_ids: set[str] | None = None,
		reserved_bond_ids: set[str] | None = None,
		) -> str:
	"""Serialize a molecule to CDML text."""
	doc = dom.Document()
	cdml_el = doc.createElement("cdml")
	cdml_el.setAttribute("version", str(version or DEFAULT_CDML_VERSION))
	cdml_el.setAttribute("xmlns", str(namespace or CDML_NAMESPACE))
	metadata_el = dom_ext.elementUnder(cdml_el, "metadata")
	dom_ext.elementUnder(metadata_el, "doc", attributes=(("href", CDML_DOC_URL),))
	cdml_el.appendChild(
		write_cdml_molecule_element(
			mol,
			doc=doc,
			policy=policy,
			coord_to_text=coord_to_text,
			width_to_text=width_to_text,
			reserved_atom_ids=reserved_atom_ids,
			reserved_bond_ids=reserved_bond_ids,
		)
	)
	doc.appendChild(cdml_el)
	return doc.toxml(encoding="utf-8").decode("utf-8")


#============================================
def molecules_to_insertion_proposal(
		molecules: list[molecule], *, token_stem: str,
		) -> str:
	"""Serialize detached molecules as one complete provisional CDML proposal.

		The proposal contains only top-level molecule elements.  Its identifiers
		are transaction-local correlation tokens, never source graph identifiers
		or durable-looking serializer defaults.
		"""
	if not molecules:
		raise ValueError("molecule insertion proposal requires at least one molecule")
	if not _INSERTION_TOKEN_STEM_PATTERN.fullmatch(token_stem):
		raise ValueError("molecule insertion token stem is invalid")
	doc = dom.Document()
	cdml_el = doc.createElement("cdml")
	cdml_el.setAttribute("version", DEFAULT_CDML_VERSION)
	cdml_el.setAttribute("xmlns", CDML_NAMESPACE)
	doc.appendChild(cdml_el)
	atom_serial = 1
	bond_serial = 1
	for molecule_serial, mol in enumerate(molecules, start=1):
		molecule_el = write_cdml_molecule_element(mol, doc=doc)
		molecule_el.setAttribute("id", _insertion_token(token_stem, "m", molecule_serial))
		atom_elements = list(molecule_el.getElementsByTagName("atom"))
		if len(atom_elements) != len(mol.vertices):
			raise ValueError("molecule insertion proposal could not serialize every atom")
		atom_tokens = {}
		for atom_obj, atom_el in zip(mol.vertices, atom_elements):
			atom_token = _insertion_token(token_stem, "a", atom_serial)
			atom_el.setAttribute("id", atom_token)
			atom_tokens[atom_obj] = atom_token
			atom_serial += 1
		bond_elements = list(molecule_el.getElementsByTagName("bond"))
		if len(bond_elements) != len(mol.edges):
			raise ValueError("molecule insertion proposal could not serialize every bond")
		for bond_obj, bond_el in zip(mol.edges, bond_elements):
			start_atom, end_atom = bond_obj.vertices
			bond_el.setAttribute("id", _insertion_token(token_stem, "b", bond_serial))
			bond_el.setAttribute("start", atom_tokens[start_atom])
			bond_el.setAttribute("end", atom_tokens[end_atom])
			bond_serial += 1
		cdml_el.appendChild(molecule_el)
	proposal_text = doc.toxml(encoding="utf-8").decode("utf-8")
	return proposal_text


#============================================
def molecules_to_complete_document(molecules: list[molecule]) -> str:
	"""Serialize detached components as one strict, durable CDML document.

	This is the backend-owned import boundary.  Unlike an insertion proposal,
	it assigns ordinary document IDs and contains no transaction-local tokens.
	The caller validates the returned complete document through ``CDMLDocument``
	before it crosses a frontend worker boundary.
	"""
	if not molecules:
		raise ValueError("complete CDML import requires at least one molecule")
	doc = dom.Document()
	cdml_el = doc.createElement("cdml")
	cdml_el.setAttribute("version", DEFAULT_CDML_VERSION)
	cdml_el.setAttribute("xmlns", CDML_NAMESPACE)
	doc.appendChild(cdml_el)
	atom_serial = 1
	bond_serial = 1
	for molecule_serial, mol in enumerate(molecules, start=1):
		molecule_el = write_cdml_molecule_element(mol, doc=doc)
		molecule_el.setAttribute("id", "m%d" % molecule_serial)
		atom_elements = list(molecule_el.getElementsByTagName("atom"))
		if len(atom_elements) != len(mol.vertices):
			raise ValueError("complete CDML import could not serialize every atom")
		atom_ids = {}
		for atom_obj, atom_el in zip(mol.vertices, atom_elements):
			atom_id = "a%d" % atom_serial
			atom_el.setAttribute("id", atom_id)
			atom_ids[atom_obj] = atom_id
			atom_serial += 1
		bond_elements = list(molecule_el.getElementsByTagName("bond"))
		if len(bond_elements) != len(mol.edges):
			raise ValueError("complete CDML import could not serialize every bond")
		for bond_obj, bond_el in zip(mol.edges, bond_elements):
			start_atom, end_atom = bond_obj.vertices
			bond_el.setAttribute("id", "b%d" % bond_serial)
			bond_el.setAttribute("start", atom_ids[start_atom])
			bond_el.setAttribute("end", atom_ids[end_atom])
			bond_serial += 1
		cdml_el.appendChild(molecule_el)
	complete_cdml = doc.toxml(encoding="utf-8").decode("utf-8")
	return complete_cdml


#============================================
def _insertion_token(token_stem: str, kind: str, serial: int) -> str:
	"""Build one valid provisional token with an OASA-owned local suffix."""
	token = f"__bkchem_new__{token_stem}_{kind}{serial}"
	if len(token.removeprefix("__bkchem_new__")) > 64:
		raise ValueError("molecule insertion proposal has too many identifiers")
	return token


#============================================
def mol_to_file(mol: molecule, f: object, **kwargs) -> None:
	"""Write CDML text for a molecule into a file-like object."""
	f.write(mol_to_text(mol, **kwargs))


#============================================
def _assign_atom_ids(
		atoms: object, reserved_ids: set[str] | None = None,
		) -> dict[object, str]:
	"""Return stable, collision-free CDML IDs for ``atoms``.

	Existing IDs commonly come from a loaded CDML document.  Reserve every
	existing ID before assigning IDs to newly created atoms so an added atom
	cannot reuse (for example) ``a1`` later in the vertex sequence.
	"""
	atom_list = list(atoms)
	used_ids = set(reserved_ids or ())
	ids = {}
	counter = 1
	for atom_obj in atom_list:
		atom_id = getattr(atom_obj, "id", None)
		if atom_id and str(atom_id) not in used_ids:
			assigned_id = str(atom_id)
		else:
			while "a%d" % counter in used_ids:
				counter += 1
			assigned_id = "a%d" % counter
			counter += 1
		ids[atom_obj] = assigned_id
		used_ids.add(assigned_id)
	return ids


#============================================
def _assign_bond_ids(
		bonds: object, reserved_ids: set[str] | None = None,
		) -> dict[object, str]:
	"""Return collision-free CDML IDs for bonds without mutating ``bonds``."""
	used_ids = set(reserved_ids or ())
	ids = {}
	counter = 1
	for bond_obj in bonds:
		bond_id = getattr(bond_obj, "id", None)
		if bond_id and str(bond_id) not in used_ids:
			assigned_id = str(bond_id)
		else:
			while "b%d" % counter in used_ids:
				counter += 1
			assigned_id = "b%d" % counter
			counter += 1
		ids[bond_obj] = assigned_id
		used_ids.add(assigned_id)
	return ids


#============================================
def _write_cdml_atom_element(doc: object, atom_obj: atom, atom_ids: dict[object, str], coord_to_text: object = None) -> object:
	a_el = doc.createElement("atom")
	a_el.setAttribute("id", atom_ids[atom_obj])
	symbol = getattr(atom_obj, "symbol", "C")
	a_el.setAttribute("name", str(symbol))
	charge = getattr(atom_obj, "charge", 0)
	if charge:
		a_el.setAttribute("charge", str(charge))
	multiplicity = getattr(atom_obj, "multiplicity", 1)
	if multiplicity and multiplicity != 1:
		a_el.setAttribute("multiplicity", str(multiplicity))
	valency = getattr(atom_obj, "valency", None)
	if valency is not None:
		a_el.setAttribute("valency", str(valency))
	free_sites = getattr(atom_obj, "free_sites", 0)
	if free_sites:
		a_el.setAttribute("free_sites", str(free_sites))
	isotope = getattr(atom_obj, "isotope", None)
	if isotope is not None:
		a_el.setAttribute("isotope", str(isotope))
	explicit_hydrogens = getattr(atom_obj, "explicit_hydrogens", 0)
	if explicit_hydrogens:
		a_el.setAttribute("explicit_hydrogens", str(explicit_hydrogens))

	x = getattr(atom_obj, "x", 0.0)
	y = getattr(atom_obj, "y", 0.0)
	z = getattr(atom_obj, "z", 0.0)
	x_text = _coord_to_text(x, coord_to_text=coord_to_text)
	y_text = _coord_to_text(y, coord_to_text=coord_to_text)
	point_attrs = (("x", x_text), ("y", y_text))
	if z:
		z_text = _coord_to_text(z, coord_to_text=coord_to_text)
		point_attrs = point_attrs + (("z", z_text),)
	dom_ext.elementUnder(a_el, "point", attributes=point_attrs)

	properties = atom_obj.properties_
	show = properties.get("show")
	if show:
		a_el.setAttribute("show", show)
	hydrogens = properties.get("show_hydrogens")
	if hydrogens:
		a_el.setAttribute("hydrogens", hydrogens)
	font_size = properties.get("font_size")
	font_family = properties.get("font_family")
	line_color = properties.get("line_color")
	if font_size or font_family or line_color:
		font_attrs = (
			("size", str(font_size or DEFAULT_FONT_SIZE)),
			("family", str(font_family or DEFAULT_FONT_FAMILY)),
		)
		font_el = dom_ext.elementUnder(a_el, "font", attributes=font_attrs)
		if line_color:
			font_el.setAttribute("color", line_color)
	else:
		# Emit CPK color for uncustomized non-carbon atoms, as before.
		cpk_color = CPK_COLORS.get(symbol)
		if cpk_color and symbol != 'C':
			dom_ext.elementUnder(a_el, 'font', attributes=(
				('size', str(DEFAULT_FONT_SIZE)),
				('family', DEFAULT_FONT_FAMILY),
				('color', cpk_color),
			))

	return a_el


#============================================
def _write_cdml_bond_element(
		doc: object, bond_obj: bond, atom_ids: dict[object, str],
		bond_ids: dict[object, str], policy: str = "present_only",
		width_to_text: object = None,
		) -> object:
	b_el = doc.createElement("bond")
	bond_type = getattr(bond_obj, "type", "n") or "n"
	order = getattr(bond_obj, "order", 1) or 1
	if not bond_semantics.is_authored_bond_order(bond_type, order):
		raise ValueError(
			"Unsupported authored CDML bond type/order pair: %s%d" % (bond_type, order)
		)
	b_el.setAttribute("type", "%s%d" % (bond_type, order))
	v1, v2 = bond_obj.vertices
	b_el.setAttribute("start", atom_ids[v1])
	b_el.setAttribute("end", atom_ids[v2])
	b_el.setAttribute("id", bond_ids[bond_obj])

	values, defaults = _bond_values_and_defaults(bond_obj, width_to_text=width_to_text)
	attrs = cdml_bond_io.select_cdml_attributes(
		values,
		defaults=defaults,
	)
	for name, value in attrs:
		b_el.setAttribute(name, str(value))
	return b_el


#============================================
def _bond_values_and_defaults(bond_obj: bond, width_to_text: object = None) -> tuple[dict[str, str], dict[str, str]]:
	values = {}
	defaults = {}
	depiction = cdml_bond_io.resolve_bond_depiction(bond_obj)
	explicit = depiction.explicit_fields
	line_width = depiction.line_width
	if line_width is not None and "line_width" in explicit:
		values["line_width"] = _width_to_text(
			line_width,
			width_to_text=width_to_text,
			name="line_width",
			bond_obj=bond_obj,
		)
	if "double_ratio" in explicit:
		values["double_ratio"] = str(depiction.double_ratio)
	if depiction.equithick and "equithick" in explicit:
		values["equithick"] = "1"
	order = getattr(bond_obj, "order", 1) or 1
	if order != 1:
		bond_width = depiction.bond_width
		if bond_width is not None and "bond_width" in explicit:
			values["bond_width"] = _width_to_text(
				bond_width,
				width_to_text=width_to_text,
				name="bond_width",
				bond_obj=bond_obj,
			)
		if depiction.center is not None and "center" in explicit:
			values["center"] = ["no", "yes"][int(depiction.center)]
		if depiction.auto_sign != 1 and "auto_sign" in explicit:
			values["auto_sign"] = str(depiction.auto_sign)
	if bond_obj.type != "n":
		wedge_width = depiction.wedge_width
		if wedge_width is not None and "wedge_width" in explicit:
			values["wedge_width"] = _width_to_text(
				wedge_width,
				width_to_text=width_to_text,
				name="wedge_width",
				bond_obj=bond_obj,
			)
	if bond_obj.type != "n" and order != 1:
		if "simple_double" in explicit:
			values["simple_double"] = str(int(depiction.simple_double))

	if depiction.color and depiction.color != "#000" and "color" in explicit:
		values["color"] = depiction.color
	if depiction.wavy_style and "wavy_style" in explicit:
		values["wavy_style"] = depiction.wavy_style
	if (
			depiction.haworth_position in cdml_bond_io.HAWORTH_POSITIONS
			and "haworth_position" in explicit
			):
		values["haworth_position"] = depiction.haworth_position
	return values, defaults


#============================================
def _coord_to_text(value: float | None, coord_to_text: object = None) -> str:
	if coord_to_text:
		return str(coord_to_text(value))
	if value is None:
		value = 0.0
	return "%.3fcm" % (float(value) / POINTS_PER_CM)


#============================================
def _width_to_text(value: object, width_to_text: object = None, name: str | None = None, bond_obj: bond | None = None) -> str:
	if width_to_text:
		return str(width_to_text(value, name=name, bond_obj=bond_obj))
	return str(value)


#============================================
def _cm_to_float_coord(x: str) -> float:
	if not x:
		return 0
	if x[-2:] == "cm":
		return float(x[:-2]) * POINTS_PER_CM
	return float(x)
