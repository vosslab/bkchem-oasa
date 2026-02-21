#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program

#--------------------------------------------------------------------------

"""Template manager resides here.

"""

import math
import os.path
import xml.sax
import xml.etree.ElementTree as ElementTree

from warnings import warn
from oasa.transform_lib import Transform

import oasa
import oasa.atom_lib
import oasa.oasa_config
import oasa.smiles_lib
from oasa.molecule_lib import Molecule as oasa_molecule_class

from bkchem import bkchem_config
from bkchem import os_support
from bkchem import safe_xml

from bkchem.molecule_lib import BkMolecule
from bkchem.singleton_store import Store, Screen


#============================================
def _choose_anchor_atom(mol):
	"""Pick a deterministic anchor atom for template placement.

	Args:
		mol: OASA BkMolecule with computed coordinates.

	Returns:
		The atom with the largest x (then smallest y, then symbol).
	"""
	return max(mol.vertices, key=lambda atom: (atom.x, -atom.y, atom.symbol))


#============================================
def _choose_anchor_neighbor(anchor):
	"""Pick a deterministic neighbor for the anchor bond.

	Args:
		anchor: The anchor atom.

	Returns:
		The neighbor sorted by (x, y, symbol), or None if no neighbors.
	"""
	if not anchor.neighbors:
		return None
	return sorted(anchor.neighbors, key=lambda atom: (atom.x, atom.y, atom.symbol))[0]


#============================================
def _normalize_coordinates(atoms):
	"""Shift atoms so all coordinates are positive and start near 1 cm.

	Args:
		atoms: List of atoms to normalize in place.
	"""
	minx = min(atom.x for atom in atoms)
	miny = min(atom.y for atom in atoms)
	shift_x = 1.0 - minx
	shift_y = 1.0 - miny
	for atom in atoms:
		atom.x += shift_x
		atom.y += shift_y


#============================================
def _build_cdml_string(name, mol, anchor, neighbor, template_atom):
	"""Build a CDML XML string for a biomolecule template.

	Args:
		name: Display name for the BkMolecule.
		mol: OASA BkMolecule with computed coordinates.
		anchor: The anchor atom in the BkMolecule.
		neighbor: The anchor's neighbor for the template bond.
		template_atom: The extra template attachment atom.

	Returns:
		str: CDML XML string.
	"""
	cdml_version = bkchem_config.current_CDML_version
	root = ElementTree.Element(
		"cdml",
		{
			"version": cdml_version,
			"xmlns": "http://www.freesoftware.fsf.org/bkchem/cdml",
		},
	)
	# info block
	info = ElementTree.SubElement(root, "info")
	author = ElementTree.SubElement(info, "author_program", {"version": cdml_version})
	author.text = "BKchem"
	# paper and viewport
	ElementTree.SubElement(root, "paper", {
		"crop_svg": "0", "orientation": "landscape", "type": "Letter",
	})
	ElementTree.SubElement(root, "viewport", {
		"viewport": "0.000000 0.000000 640.000000 480.000000",
	})
	# standard block
	standard = ElementTree.SubElement(root, "standard", {
		"area_color": "#ffffff", "font_family": "helvetica",
		"font_size": "14", "line_color": "#000",
		"line_width": "2.0px", "paper_crop_svg": "0",
		"paper_orientation": "landscape", "paper_type": "Letter",
	})
	ElementTree.SubElement(standard, "bond", {
		"double-ratio": "0.75", "length": "1.0cm",
		"wedge-width": "5.0px", "width": "6.0px",
	})
	ElementTree.SubElement(standard, "arrow", {"length": "1.6cm"})

	# molecule element
	mol_el = ElementTree.SubElement(root, "molecule", {
		"id": "molecule1", "name": name,
	})

	# build atom id map
	atom_id_map = {}
	sorted_atoms = sorted(mol.vertices, key=lambda a: (a.x, a.y, a.symbol))
	for index, atom in enumerate(sorted_atoms, start=1):
		atom_id_map[atom] = f"atom_{index}"

	# template element
	template_atom_id = "atom_t"
	template_el = ElementTree.SubElement(mol_el, "template", {"atom": template_atom_id})
	if anchor and neighbor:
		template_el.set("bond_first", atom_id_map[anchor])
		template_el.set("bond_second", atom_id_map[neighbor])

	# normalize all atom coordinates to positive values
	all_atoms = sorted_atoms + [template_atom]
	_normalize_coordinates(all_atoms)

	# write molecule atoms
	for atom in sorted_atoms:
		atom_el = ElementTree.SubElement(mol_el, "atom", {
			"id": atom_id_map[atom], "name": atom.symbol,
		})
		if atom.charge:
			atom_el.set("charge", str(atom.charge))
		ElementTree.SubElement(atom_el, "point", {
			"x": f"{atom.x:.3f}cm", "y": f"{atom.y:.3f}cm",
		})

	# write template anchor atom
	t_atom_el = ElementTree.SubElement(mol_el, "atom", {
		"id": template_atom_id, "name": template_atom.symbol,
	})
	ElementTree.SubElement(t_atom_el, "point", {
		"x": f"{template_atom.x:.3f}cm", "y": f"{template_atom.y:.3f}cm",
	})

	# write bonds
	for bond in mol.bonds:
		bond_type = bond.type or "n"
		bond_order = bond.order or 1
		start_id = atom_id_map[bond.vertices[0]]
		end_id = atom_id_map[bond.vertices[1]]
		ElementTree.SubElement(mol_el, "bond", {
			"double_ratio": "0.75", "end": end_id,
			"line_width": "1.0", "start": start_id,
			"type": f"{bond_type}{bond_order}",
		})

	# bond from template atom to anchor
	ElementTree.SubElement(mol_el, "bond", {
		"double_ratio": "0.75",
		"end": atom_id_map[anchor],
		"line_width": "1.0",
		"start": template_atom_id,
		"type": "n1",
	})

	# serialize to string
	xml_string = ElementTree.tostring(root, encoding='unicode', xml_declaration=True)
	return xml_string


#============================================
class template_manager(object):
	templates = []

	def __init__( self):
		self.templates = []
		self._prepared_templates = []
		self._template_names = []
		# SMILES registry for lazy template generation
		self._smiles_registry = {}


	def add_template_from_CDML( self, file, name_override=None):
		if not os.path.isfile( file):
			file = os_support.get_path( file, "template")
			if not file:
				warn( "template file %s does not exist - ignoring" % file)
				return
		try:
			doc = safe_xml.parse_dom_from_file( file).getElementsByTagName( 'cdml')[0]
		except xml.sax.SAXException:
			warn( "template file %s cannot be parsed - ignoring" % file)
			return
		# when loading old versions of CDML try to convert them, but do nothing when they cannot be converted
		from bkchem import CDML_versions
		CDML_versions.transform_dom_to_version( doc, bkchem_config.current_CDML_version)
		Store.app.paper.onread_id_sandbox_activate()
		for tmp in doc.getElementsByTagName('molecule'):
			if name_override:
				tmp.setAttribute( 'name', name_override)
			self.templates.append( tmp)
			m = BkMolecule( Store.app.paper, package=tmp)
			if name_override:
				m.name = name_override
			self._prepared_templates.append( m)
			self._template_names.append( name_override or m.name)
		Store.app.paper.onread_id_sandbox_finish( apply_to=[])


	def register_smiles_template(self, smiles: str, name_override: str = '') -> None:
		"""Register a SMILES string for lazy template generation.

		No BkMolecule is created at registration time. The template
		is generated on first access via _ensure_template_ready().

		Args:
			smiles: SMILES string for the BkMolecule.
			name_override: Display name for the template.
		"""
		index = len(self.templates)
		# placeholders -- filled lazily
		self.templates.append(None)
		self._prepared_templates.append(None)
		self._template_names.append(name_override)
		# store SMILES for lazy generation
		self._smiles_registry[index] = smiles


	def _ensure_template_ready(self, n: int) -> None:
		"""Generate a template from SMILES on first access.

		If the template at index n is already generated (not None),
		this is a no-op. Otherwise, parses the SMILES string,
		builds a CDML DOM, and stores the template.

		Args:
			n: Template index.
		"""
		# already generated or loaded from CDML
		if self.templates[n] is not None:
			return
		# not a SMILES template
		if n not in self._smiles_registry:
			return

		smiles = self._smiles_registry[n]
		name = self._template_names[n]

		# temporarily restore oasa.molecule as the molecule class so
		# text_to_mol creates pure OASA molecules (BKChem overrides
		# Config.molecule_class with its own molecule which lacks
		# chemistry-only methods like remove_unimportant_hydrogens)
		saved_class = oasa.oasa_config.Config.molecule_class
		oasa.oasa_config.Config.molecule_class = oasa_molecule_class
		# parse SMILES and generate 2D coordinates
		mol = oasa.smiles_lib.text_to_mol(smiles, calc_coords=1)
		# restore the BKChem molecule class
		oasa.oasa_config.Config.molecule_class = saved_class
		if not mol:
			warn(f"Failed to parse SMILES for template '{name}': {smiles}")
			return
		# clean up and normalize
		mol.remove_unimportant_hydrogens()
		mol.normalize_bond_length(1.0)

		# choose anchor atom and neighbor for template attachment
		anchor = _choose_anchor_atom(mol)
		neighbor = _choose_anchor_neighbor(anchor)

		# build template anchor atom one bond length to the right
		template_atom = oasa.atom_lib.Atom(symbol="C")
		template_atom.x = anchor.x + 1.0
		template_atom.y = anchor.y
		template_atom.z = 0.0

		# build CDML XML string and parse it as DOM
		xml_string = _build_cdml_string(name, mol, anchor, neighbor, template_atom)
		doc = safe_xml.parse_dom_from_string(xml_string)
		cdml_el = doc.getElementsByTagName('cdml')[0]

		# convert CDML version if needed
		from bkchem import CDML_versions
		CDML_versions.transform_dom_to_version(cdml_el, bkchem_config.current_CDML_version)

		# load the molecule from the DOM
		Store.app.paper.onread_id_sandbox_activate()
		mol_nodes = cdml_el.getElementsByTagName('molecule')
		if mol_nodes:
			tmp = mol_nodes[0]
			tmp.setAttribute('name', name)
			self.templates[n] = tmp
			m = BkMolecule(Store.app.paper, package=tmp)
			m.name = name
			self._prepared_templates[n] = m
		Store.app.paper.onread_id_sandbox_finish(apply_to=[])


	def get_template( self, n):
		self._ensure_template_ready(n)
		return self.templates[n]


	def get_templates_valency( self, name):
		self._ensure_template_ready(name)
		return self._prepared_templates[ name].next_to_t_atom.occupied_valency -1


	def get_template_names( self):
		return list(self._template_names)


	def get_transformed_template( self, n, coords, type='empty', paper=None):
		"""type is type of connection - 'bond', 'atom1'(for single atom), 'atom2'(for atom with more than 1 bond), 'empty'"""
		self._ensure_template_ready(n)
		pap = paper or Store.app.paper
		pap.onread_id_sandbox_activate() # must be here to mangle the ids
		current = BkMolecule( pap, package=self.templates[n])
		pap.onread_id_sandbox_finish( apply_to= [current]) # id mangling
		current.name = ''
		self._scale_ratio = 1
		trans = Transform()
		# type empty - just draws the template - no conection
		if type == 'empty':
			xt1, yt1 = current.t_atom.get_xy()
			xt2, yt2 = current.next_to_t_atom.get_xy()
			x1, y1 = coords
			bond_length = Screen.any_to_px( Store.app.paper.standard.bond_length)
			current.delete_items( [current.t_atom], redraw=0, delete_single_atom=0)
			trans.set_move( -xt2, -yt2)
			trans.set_scaling( bond_length / math.sqrt( (xt1-xt2)**2 + (yt1-yt2)**2))
			trans.set_move( x1, y1)
		#type atom
		elif type == 'atom1' or type == 'atom2':
			xt1, yt1 = current.t_atom.get_xy()
			xt2, yt2 = current.next_to_t_atom.get_xy()
			x1, y1, x2, y2 = coords
			trans.set_move( -xt2, -yt2)
			trans.set_scaling( math.sqrt( (x1-x2)**2 + (y1-y2)**2) / math.sqrt( (xt1-xt2)**2 + (yt1-yt2)**2))
			trans.set_rotation( math.atan2( xt1-xt2, yt1-yt2) - math.atan2( x1-x2, y1-y2))
			trans.set_move( x2, y2)
		#type bond
		elif type == 'bond':
			if not (current.t_bond_first and current.t_bond_second):
				warn( "this template is not capable to be added to bond - sorry.")
				return None
			current.delete_items( [current.t_atom], redraw=0, delete_single_atom=0)
			xt1, yt1 = current.t_bond_first.get_xy()
			xt2, yt2 = current.t_bond_second.get_xy()
			x1, y1, x2, y2 = coords
			self._scale_ratio = math.sqrt( (x1-x2)**2 + (y1-y2)**2) / math.sqrt( (xt1-xt2)**2 + (yt1-yt2)**2) # further needed for bond.bond_width transformation
			trans.set_move( -xt1, -yt1)
			trans.set_rotation( math.atan2( xt1-xt2, yt1-yt2) - math.atan2( x1-x2, y1-y2))
			trans.set_scaling( self._scale_ratio)
			trans.set_move( x1, y1)
		self.transform_template( current, trans)
		#remove obsolete info from template
		if type == 'atom1':
			current.delete_items( [current.t_atom], redraw=0, delete_single_atom=0)
		elif type == 'atom2':
			current.t_atom.x = x1
			current.t_atom.y = y1
		current.t_atom = None
		current.t_bond_first = None
		current.t_bond_second = None
		#return ready template
		return current


	def transform_template( self, temp, trans):
		for a in temp.atoms:
			a.x, a.y = trans.transform_xy( a.x, a.y)
			a.scale_font( self._scale_ratio)
		for b in temp.bonds:
			if b.order != 1:
				b.bond_width *= self._scale_ratio
		# update template according to current default values
		Store.app.paper.apply_current_standard( [temp], template_mode=1)
		# return the ready template
		return temp
