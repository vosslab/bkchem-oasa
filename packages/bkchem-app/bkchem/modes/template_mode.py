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

"""Template mode for applying molecule templates."""

import builtins

from oasa import geometry

import bkchem.chem_compat
from bkchem import bkchem_utils
from bkchem.bond_lib import BkBond
from bkchem.singleton_store import Store, Screen
from bkchem.modes.edit_mode import edit_mode
from bkchem.modes.config import get_modes_config, _TEMPLATE_MANAGERS

# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


## -------------------- TEMPLATE MODE --------------------
class template_mode( edit_mode):

	def __init__( self):
		edit_mode.__init__( self)
		# name loaded from YAML; determine template source from YAML config
		yaml_key = type(self).__name__.replace('_mode', '')
		cfg = get_modes_config()['modes'].get(yaml_key, {})
		source_key = cfg.get('template_source', 'system')
		self.template_manager = _TEMPLATE_MANAGERS[source_key]()
		# build submodes from template manager
		if cfg.get('use_categories'):
			self._build_categorized_submodes()
		else:
			self._build_flat_submodes()
		self.register_key_sequence( 'C-t', self._mark_focused_as_template_atom_or_bond)
		self._user_selected_template = ''


	def mouse_click( self, event):
		if self.submodes == [[]]:
			Store.log( _("No template is available"))
			return
		Store.app.paper.unselect_all()
		if not self.focused:
			xy = Store.app.paper.canvas_to_real((event.x, event.y))
			t = self._get_transformed_template( self.submode[0],
												xy,
												type='empty', paper=Store.app.paper)
		else:
			if bkchem.chem_compat.is_chemistry_vertex( self.focused):
				if self.focused.z != 0:
					Store.log( _("Sorry, it is not possible to append a template to an atom with non-zero Z coordinate, yet."),
									message_type="hint")
					return
				if self.focused.free_valency >= self._get_templates_valency():
					x1, y1 = self.focused.neighbors[0].get_xy()
					x2, y2 = self.focused.get_xy()
					t = self._get_transformed_template( self.submode[0], (x1,y1,x2,y2), type='atom1', paper=Store.app.paper)
				else:
					x1, y1 = self.focused.get_xy()
					x2, y2 = self.focused.molecule.find_place( self.focused, Screen.any_to_px( Store.app.paper.standard.bond_length))
					t = self._get_transformed_template( self.submode[0], (x1,y1,x2,y2), type='atom2', paper=Store.app.paper)
			elif isinstance( self.focused, BkBond):
				x1, y1 = self.focused.atom1.get_xy()
				x2, y2 = self.focused.atom2.get_xy()
				#find right side of bond to append template to
				atms = self.focused.atom1.neighbors + self.focused.atom2.neighbors
				atms = bkchem_utils.difference( atms, [self.focused.atom1, self.focused.atom2])
				coords = [a.get_xy() for a in atms]
				if sum(geometry.on_which_side_is_point((x1,y1,x2,y2), xy) for xy in coords) > 0:
					x1, y1, x2, y2 = x2, y2, x1, y1
				t = self._get_transformed_template( self.submode[0], (x1,y1,x2,y2), type='bond', paper=Store.app.paper)
				if not t:
					return # the template was not meant to be added to a BkBond
			else:
				return
		Store.app.paper.stack.append( t)
		t.draw( automatic="both")
		#Store.app.paper.signal_to_app( ("Added molecule from template: ")+\
		#                              Store.tm.get_template_names()[ self.submode[0]].encode('utf-8'))
		Store.app.paper.select( [o for o in t])
		Store.app.paper.handle_overlap()
		# checking of valency
		if self.focused:
			if isinstance( self.focused, BkBond) and (self.focused.atom1.free_valency < 0 or self.focused.atom2.free_valency < 0):
				Store.log( _("maximum valency exceeded!"), message_type="warning")
			elif bkchem.chem_compat.is_chemistry_vertex( self.focused) and self.focused.free_valency < 0:
				Store.log( _("maximum valency exceeded!"), message_type="warning")

		Store.app.paper.start_new_undo_record()
		Store.app.paper.add_bindings()


	def _mark_focused_as_template_atom_or_bond( self):
		if self.focused and bkchem.chem_compat.is_chemistry_vertex( self.focused):
			self.focused.molecule.mark_template_atom( self.focused)
			Store.log( _("focused atom marked as 'template atom'"))
		elif self.focused and isinstance( self.focused, BkBond):
			self.focused.molecule.mark_template_bond( self.focused)
			Store.log( _("focused bond marked as 'template bond'"))


	def _build_flat_submodes( self):
		"""Build a simple flat list of template names as submodes."""
		names = self.template_manager.get_template_names()
		if names:
			self.submodes = [names]
			self.submodes_names = [names]
			self.submode = [0]


	def _build_categorized_submodes( self):
		"""Build category + template submodes from biomolecule_loader YAML."""
		from bkchem import biomolecule_loader
		entries = biomolecule_loader.load_biomolecule_entries()
		template_names = self.template_manager.get_template_names()
		# map name -> index in template manager
		name_to_index = {}
		for i, tname in enumerate(template_names):
			name_to_index[tname] = i
		# group entries by category
		category_order = []
		category_entries = {}
		for entry in entries:
			cat = entry['category']
			if cat not in category_entries:
				category_order.append(cat)
				category_entries[cat] = []
			category_entries[cat].append(entry)
		self._category_keys = category_order
		self._category_labels = [k.replace('_', ' ').strip() for k in self._category_keys]
		self._category_label_to_key = dict(zip(self._category_labels, self._category_keys))
		# build per-category template info
		self._category_template_names = {}
		self._category_template_labels = {}
		self._category_template_indices = {}
		for key in self._category_keys:
			cat_entries = category_entries[key]
			names = []
			labels = []
			indices = []
			for entry in cat_entries:
				mol_name = entry['name']
				if mol_name not in name_to_index:
					continue
				names.append(mol_name)
				labels.append(entry['label'])
				indices.append(name_to_index[mol_name])
			self._category_template_names[key] = names
			self._category_template_labels[key] = labels
			self._category_template_indices[key] = indices
		# set initial template list from first category
		self._template_names_list = []
		self._template_labels_list = []
		self._template_indices = []
		if self._category_labels:
			self._apply_category_selection(self._category_labels[0])
		# submodes[0] = category keys, submodes[1] = template full names
		self.submodes = [self._category_labels, self._template_names_list]
		# submodes_names[0] = category display, submodes_names[1] = short labels
		self.submodes_names = [self._category_labels, self._template_labels_list]
		self.submode = [0, 0]
		# override group_layouts since YAML parser skips dynamic groups
		self.group_layouts = ['row', 'grid']
		self.group_labels = [_('Category'), _('Templates')]
		# build tooltip map: full name -> full name (for tooltip display)
		for key in self._category_keys:
			for mol_name in self._category_template_names.get(key, []):
				self.tooltip_map[mol_name] = mol_name.replace('_', ' ')


	def _apply_category_selection( self, label):
		"""Update template lists for the selected category label."""
		key = self._category_label_to_key.get(label)
		if not key and self._category_keys:
			key = self._category_keys[0]
		if key:
			self._template_names_list = self._category_template_names.get(key, [])
			self._template_labels_list = self._category_template_labels.get(key, [])
			self._template_indices = self._category_template_indices.get(key, [])
		else:
			self._template_names_list = []
			self._template_labels_list = []
			self._template_indices = []


	def _update_template_menu( self):
		"""Refresh the template button grid in the UI."""
		if not hasattr(Store.app, "subbuttons"):
			return
		if len(Store.app.subbuttons) < 2:
			return
		# rebuild the grid widget for the template group
		Store.app.refresh_submode_buttons(1)


	def _get_selected_template_index( self):
		"""Get the template manager index for the currently selected template."""
		if not hasattr(self, '_template_indices') or not self._template_indices:
			return None
		if len(self.submode) < 2:
			return self._template_indices[0]
		index = self.submode[1]
		if index < 0 or index >= len(self._template_indices):
			return None
		return self._template_indices[index]


	def on_submode_switch( self, submode_index, name=''):
		"""When category changes, refresh template list."""
		if submode_index == 0 and hasattr(self, '_category_keys'):
			self._apply_category_selection(name)
			self.submodes[1] = self._template_names_list
			self.submodes_names[1] = self._template_labels_list
			if self._template_names_list:
				self.submode[1] = 0
			self._update_template_menu()


	def _get_transformed_template( self, name, coords, type='empty', paper=None):
		# for categorized modes, use the resolved template index
		if hasattr(self, '_template_indices') and self._template_indices:
			template_index = self._get_selected_template_index()
			if template_index is not None:
				return self.template_manager.get_transformed_template(template_index, coords, type=type, paper=paper)
		return self.template_manager.get_transformed_template( self.submode[0], coords, type=type, paper=paper)


	def _get_templates_valency( self, template_index=None):
		# for categorized modes, use the resolved template index
		if template_index is not None:
			return self.template_manager.get_templates_valency(template_index)
		if hasattr(self, '_template_indices') and self._template_indices:
			idx = self._get_selected_template_index()
			if idx is not None:
				return self.template_manager.get_templates_valency(idx)
		return self.template_manager.get_templates_valency( self.submode[0])



## -------------------- BIOMOLECULE / USER TEMPLATE MODES --------------------
# These are subclasses of template_mode with YAML keys 'biotemplate' and
# 'usertemplate'. The template_mode base class reads template_source and
# use_categories from YAML to parameterize behavior automatically.

class biotemplate_mode( template_mode):
	"""Biomolecule template mode. Config driven by YAML key 'biotemplate'."""
	pass

# backwards-compatible alias
biomolecule_template_mode = biotemplate_mode


class usertemplate_mode( template_mode):
	"""User template mode. Config driven by YAML key 'usertemplate'."""
	pass

# backwards-compatible alias
user_template_mode = usertemplate_mode
