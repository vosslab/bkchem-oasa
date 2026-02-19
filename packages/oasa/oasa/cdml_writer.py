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
import xml.dom.minidom as dom

# local repo modules
from . import bond_semantics
from . import cdml_bond_io
from . import dom_extensions as dom_ext
from . import smiles
from .atom import atom
from .bond import bond
from .known_groups import cdml_to_smiles
from .molecule import molecule
from .periodic_table import periodic_table as PT


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
CDML_NAMESPACE = "http://www.freesoftware.fsf.org/bkchem/cdml"
CDML_DOC_URL = "https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md"
DEFAULT_CDML_VERSION = "26.02"

reads_text = False
writes_text = True
reads_files = False
writes_files = True


#============================================
def read_cdml_molecule_element(mol_el):
	"""Decode a CDML molecule element into an OASA molecule."""
	atom_id_remap = {}
	mol = molecule()
	for atom_el in dom_ext.simpleXPathSearch(mol_el, "atom"):
		name = atom_el.getAttribute("name")
		if not name:
			return None
		pos_nodes = dom_ext.simpleXPathSearch(atom_el, "point")
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
		atom_id_remap[atom_el.getAttribute("id")] = a
		_record_atom_cdml_attrs(atom_el, a)

	for bond_el in dom_ext.simpleXPathSearch(mol_el, "bond"):
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
			},
		)
		mol.add_edge(v1, v2, e=e)
		bond_semantics.canonicalize_bond_vertices(e)

	return mol


#============================================
def write_cdml_molecule_element(mol, *, doc=None, policy="present_only", coord_to_text=None, width_to_text=None):
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
	atom_ids = _assign_atom_ids(mol.vertices)
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
				policy=policy,
				width_to_text=width_to_text,
			)
		)
	return mol_el


#============================================
def mol_to_text(mol, *, policy="present_only", version=None, namespace=None, coord_to_text=None, width_to_text=None):
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
		)
	)
	doc.appendChild(cdml_el)
	return doc.toxml(encoding="utf-8").decode("utf-8")


#============================================
def mol_to_file(mol, f, **kwargs):
	"""Write CDML text for a molecule into a file-like object."""
	f.write(mol_to_text(mol, **kwargs))


#============================================
def _assign_atom_ids(atoms):
	ids = {}
	counter = 1
	for atom_obj in atoms:
		atom_id = getattr(atom_obj, "id", None)
		if atom_id:
			ids[atom_obj] = str(atom_id)
			continue
		ids[atom_obj] = "a%d" % counter
		counter += 1
	return ids


#============================================
def _record_atom_cdml_attrs(atom_el, atom_obj):
	present = set()
	unknown = {}
	if hasattr(atom_el, "attributes") and atom_el.attributes is not None:
		for attr in atom_el.attributes.values():
			name = attr.name
			value = attr.value
			present.add(name)
			if name in _KNOWN_ATOM_ATTRS:
				continue
			unknown[name] = value
	if present:
		atom_obj._cdml_present = set(present)
	if unknown:
		atom_obj._cdml_unknown_attrs = dict(unknown)


#============================================
def _write_cdml_atom_element(doc, atom_obj, atom_ids, coord_to_text=None):
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

	# emit CPK color for non-carbon atoms so BKChem picks it up via <font>
	cpk_color = CPK_COLORS.get(symbol)
	if cpk_color and symbol != 'C':
		dom_ext.elementUnder(a_el, 'font', attributes=(('color', cpk_color),))

	unknown = getattr(atom_obj, "_cdml_unknown_attrs", None)
	present = getattr(atom_obj, "_cdml_present", None)
	if isinstance(unknown, dict):
		for name, value in sorted(unknown.items()):
			if present is not None and name not in present:
				continue
			if a_el.hasAttribute(name):
				continue
			a_el.setAttribute(name, str(value))
	return a_el


#============================================
def _write_cdml_bond_element(doc, bond_obj, atom_ids, policy="present_only", width_to_text=None):
	b_el = doc.createElement("bond")
	bond_type = getattr(bond_obj, "type", "n") or "n"
	order = getattr(bond_obj, "order", 1) or 1
	b_el.setAttribute("type", "%s%d" % (bond_type, order))
	v1, v2 = bond_obj.vertices
	b_el.setAttribute("start", atom_ids[v1])
	b_el.setAttribute("end", atom_ids[v2])
	bond_id = getattr(bond_obj, "id", None)
	if bond_id:
		b_el.setAttribute("id", str(bond_id))

	values, defaults = _bond_values_and_defaults(bond_obj, width_to_text=width_to_text)
	present = cdml_bond_io.get_cdml_present(bond_obj)
	force = set()
	allow_non_default = policy != "present_only"
	attrs = cdml_bond_io.select_cdml_attributes(
		values,
		defaults=defaults,
		present=present,
		force=force,
		allow_non_default_without_presence=allow_non_default,
	)
	for name, value in attrs:
		b_el.setAttribute(name, str(value))
	unknown = cdml_bond_io.collect_unknown_cdml_attributes(
		bond_obj,
		known_attrs=cdml_bond_io.CDML_ALL_ATTRS,
		present=present if policy == "present_only" else None,
	)
	for name, value in unknown:
		if b_el.hasAttribute(name):
			continue
		b_el.setAttribute(name, str(value))
	return b_el


#============================================
def _bond_values_and_defaults(bond_obj, width_to_text=None):
	values = {}
	defaults = {}
	line_width = getattr(bond_obj, "line_width", None)
	if line_width is not None:
		values["line_width"] = _width_to_text(
			line_width,
			width_to_text=width_to_text,
			name="line_width",
			bond_obj=bond_obj,
		)
	double_ratio = getattr(bond_obj, "double_length_ratio", None)
	if double_ratio is not None:
		values["double_ratio"] = str(double_ratio)
	if getattr(bond_obj, "equithick", 0):
		values["equithick"] = "1"
	order = getattr(bond_obj, "order", 1) or 1
	if order != 1:
		bond_width = getattr(bond_obj, "bond_width", None)
		if bond_width is not None:
			values["bond_width"] = _width_to_text(
				bond_width,
				width_to_text=width_to_text,
				name="bond_width",
				bond_obj=bond_obj,
			)
		center = getattr(bond_obj, "center", None)
		if center is not None:
			values["center"] = ["no", "yes"][int(center)]
		auto_sign = getattr(bond_obj, "auto_bond_sign", None)
		if auto_sign is not None and auto_sign != 1:
			values["auto_sign"] = str(auto_sign)
	if bond_obj.type != "n":
		wedge_width = getattr(bond_obj, "wedge_width", None)
		if wedge_width is not None:
			values["wedge_width"] = _width_to_text(
				wedge_width,
				width_to_text=width_to_text,
				name="wedge_width",
				bond_obj=bond_obj,
			)
	if bond_obj.type != "n" and order != 1:
		simple_double = getattr(bond_obj, "simple_double", None)
		if simple_double is not None:
			values["simple_double"] = str(int(simple_double))

	line_color = getattr(bond_obj, "line_color", None)
	if not line_color:
		line_color = bond_obj.properties_.get("line_color") or bond_obj.properties_.get("color")
	if line_color and line_color != "#000":
		values["color"] = line_color
	wavy_style = getattr(bond_obj, "wavy_style", None)
	if not wavy_style:
		wavy_style = bond_obj.properties_.get("wavy_style")
	if wavy_style:
		values["wavy_style"] = wavy_style
	return values, defaults


#============================================
def _coord_to_text(value, coord_to_text=None):
	if coord_to_text:
		return str(coord_to_text(value))
	if value is None:
		value = 0.0
	return "%.3fcm" % (float(value) / POINTS_PER_CM)


#============================================
def _width_to_text(value, width_to_text=None, name=None, bond_obj=None):
	if width_to_text:
		return str(width_to_text(value, name=name, bond_obj=bond_obj))
	return str(value)


#============================================
def _cm_to_float_coord(x):
	if not x:
		return 0
	if x[-2:] == "cm":
		return float(x[:-2]) * POINTS_PER_CM
	return float(x)


_KNOWN_ATOM_ATTRS = {
	"id",
	"name",
	"charge",
	"multiplicity",
	"valency",
	"isotope",
	"free_sites",
}
