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

"""chem_paper - main drawing part for BKChem.

"""




import builtins
import importlib
import io
import oasa
import xml.dom.minidom as dom

try:
	from tkinter import Canvas, ALL
except ImportError:
	from tkinter import Canvas, ALL

from bkchem.bk_dialogs import BkTextDialog
from bkchem import bkchem_utils
from bkchem import undo
from bkchem import checks
from bkchem import oasa_bridge
from bkchem import dom_extensions
import bkchem.chem_compat
import bkchem.grid_overlay

from bkchem.singleton_store import Store
from bkchem.helper_graphics import selection_rect
from bkchem.external_data import external_data_manager
from oasa import periodic_table as PT

try:
	from bkchem.paper_lib.paper_zoom import PaperZoomMixin
	from bkchem.paper_lib.paper_transforms import PaperTransformsMixin
	from bkchem.paper_lib.paper_selection import PaperSelectionMixin
	from bkchem.paper_lib.paper_id_manager import PaperIdManagerMixin
	from bkchem.paper_lib.paper_events import PaperEventsMixin
	from bkchem.paper_lib.paper_factories import PaperFactoriesMixin
	from bkchem.paper_lib.paper_cdml import PaperCDMLMixin
	from bkchem.paper_lib.paper_properties import PaperPropertiesMixin
	from bkchem.paper_lib.paper_layout import PaperLayoutMixin
except ImportError:
	PaperZoomMixin = importlib.import_module("paper_lib.paper_zoom").PaperZoomMixin
	PaperTransformsMixin = importlib.import_module("paper_lib.paper_transforms").PaperTransformsMixin
	PaperSelectionMixin = importlib.import_module("paper_lib.paper_selection").PaperSelectionMixin
	PaperIdManagerMixin = importlib.import_module("paper_lib.paper_id_manager").PaperIdManagerMixin
	PaperEventsMixin = importlib.import_module("paper_lib.paper_events").PaperEventsMixin
	PaperFactoriesMixin = importlib.import_module("paper_lib.paper_factories").PaperFactoriesMixin
	PaperCDMLMixin = importlib.import_module("paper_lib.paper_cdml").PaperCDMLMixin
	PaperPropertiesMixin = importlib.import_module("paper_lib.paper_properties").PaperPropertiesMixin
	PaperLayoutMixin = importlib.import_module("paper_lib.paper_layout").PaperLayoutMixin

# gettext i18n translation fallbacks
_ = builtins.__dict__.get('_', lambda m: m)
ngettext = builtins.__dict__.get('ngettext', lambda s, p, n: s if n == 1 else p)


class chem_paper(
	PaperLayoutMixin,
	PaperPropertiesMixin,
	PaperCDMLMixin,
	PaperFactoriesMixin,
	PaperEventsMixin,
	PaperIdManagerMixin,
	PaperSelectionMixin,
	PaperTransformsMixin,
	PaperZoomMixin,
	Canvas,
	object,
):

	object_type = 'paper'
	all_names_to_bind = ('atom','bond','arrow','point','plus','text','vector','helper_rect')
	# the following classes should have refocus triggered when a different item of these
	# composite objects is focused - this is typical for selection_rect that needs to respond
	# differently in different corners
	classes_with_per_item_reselection = (selection_rect,)
	highlight_color = 'blue'


	def __init__( self, master = None, file_name={}, **kw):
		Canvas.__init__( self, master, kw)

		self.clipboard = None

		self.standard = self.get_personal_standard()
		self.submode = None
		self.selected = []    # selected item
		self._in = 1
		self._in_id = 0
		self._id_2_object = {}
		self.stack = []

		# bindings to input events
		self.set_bindings()

		self.set_viewport()

		# undo manages
		self.um = undo.undo_manager( self)  # undo manager

		# external data management
		self.edm = external_data_manager()
		self.edm.load_available_definitions()

		# file name
		self.file_name = file_name

		# paper sizes etc.
		self._scale = 1.0
		self._paper_properties = {}
		self.set_default_paper_properties()

		self.changes_made = 0

		self._do_not_focus = [] # this is to enable an ugly hack in a drag-and-focus hack
		self._hex_grid_overlay = None
		# both snap and grid dots on by default (Inkscape-style)
		self.hex_grid_snap_enabled = True
		self._hex_grid_show_on_bindings = True


	#============================================
	def _ensure_hex_grid_overlay(self):
		"""Lazily create the hex grid overlay."""
		if self._hex_grid_overlay is None:
			self._hex_grid_overlay = bkchem.grid_overlay.HexGridOverlay(
				self, self.standard.bond_length)

	#============================================
	def toggle_hex_grid(self):
		"""Toggle hex grid dot visibility (does not affect snap)."""
		self._ensure_hex_grid_overlay()
		self._hex_grid_overlay.toggle()

	#============================================
	def toggle_hex_grid_snap(self):
		"""Toggle snap-to-grid on or off (does not affect dot visibility)."""
		self.hex_grid_snap_enabled = not self.hex_grid_snap_enabled
		# log the change so user has feedback
		if self.hex_grid_snap_enabled:
			Store.log(_("Hex grid snap enabled"))
		else:
			Store.log(_("Hex grid snap disabled"))

	#============================================
	def show_hex_grid(self):
		"""Show hex grid dots."""
		self._ensure_hex_grid_overlay()
		self._hex_grid_overlay.show()

	#============================================
	def hide_hex_grid(self):
		"""Hide hex grid dots."""
		if self._hex_grid_overlay is not None:
			self._hex_grid_overlay.hide()


	def selected_to_clipboard( self, delete_afterwards=0, strict=0):
		"""strict means that only what is selected is copied, not the whole molecule"""
		if self.selected:
			cp, unique = self.selected_to_unique_top_levels()
			# now find center of bbox of all objects in cp
			xmin, ymin, xmax, ymax = self.common_bbox( cp)
			xy = ( xmin+(xmax-xmin)/2, ymin+(ymax-ymin)/2)
			clipboard_doc = dom.Document()
			clipboard = dom_extensions.elementUnder( clipboard_doc, 'clipboard')
			for o in cp:
				if strict and bkchem.chem_compat.is_chemistry_graph(o):
					clipboard.appendChild( o.get_package( clipboard_doc, items=bkchem_utils.intersection( o.children, self.selected)))
				else:
					clipboard.appendChild( o.get_package( clipboard_doc))
			Store.app.put_to_clipboard( clipboard, xy)
			if delete_afterwards:
				[self.del_container(o) for o in cp]
				Store.log( _("killed %s object(s) to clipboard") % str( len( cp)))
				self.start_new_undo_record()
			else:
				Store.log( _("copied %s object(s) to clipboard") % str( len( cp)))
			self.event_generate( "<<clipboard-changed>>")
			return [xmin, ymin, xmax, ymax]


	def paste_clipboard( self, xy):
		"""pastes items from clipboard to position xy"""
		clipboard = Store.app.get_clipboard()
		clipboard_pos = Store.app.get_clipboard_pos()
		if clipboard:
			self.unselect_all()
			if xy:
				dx = xy[0] - clipboard_pos[0]
				dy = xy[1] - clipboard_pos[1]
			else:
				dx, dy = 20, 20
			# the same trick as in reading of files
			self.onread_id_sandbox_activate()

			os = []
			for p in clipboard.childNodes:
				o = self.add_object_from_package( p)
				os.append( o)
				o.draw()
				o.move( dx, dy)
				if o.object_type == 'molecule':
					self.select( o)
				elif o.object_type == 'arrow':
					self.select( o.points)
				else:
					self.select( [o])
			self.add_bindings()
			Store.log( _("pasted from clipboard"))

			# put the id_manager back
			self.onread_id_sandbox_finish( apply_to=os)
			self.handle_overlap()
			self.start_new_undo_record()


	def selected_to_real_clipboard_as_SVG( self):
		"""exports selected molecules as SVG to system clipboard"""
		selected_mols = self.selected_mols
		if not selected_mols:
			Store.log( _("no molecule selected for SVG clipboard export"))
			return
		oasa_mols = [oasa_bridge.bkchem_mol_to_oasa_mol( mol) for mol in selected_mols]
		merged = oasa.molecule_utils.merge_molecules( oasa_mols)
		if merged is None:
			Store.log( _("unable to export selected molecules to SVG"))
			return
		svg_buffer = io.StringIO()
		oasa.render_out.render_to_svg( merged, svg_buffer)
		self.clipboard_clear()
		xml = svg_buffer.getvalue()
		self.clipboard_append( xml)
		Store.log( _("selected molecules were exported to clipboard in SVG"))


	def undo( self):
		self.unselect_all()
		i = self.um.undo()
		self.changes_made = 1
		if i > 0:
			Store.log(ngettext("undo (%d further undo available)",
													"undo (%d further undos available)",
													i) % i)
		else:
			Store.log( _("no further undo"))
		self.event_generate( "<<undo>>")


	def redo( self):
		self.unselect_all()
		i = self.um.redo()
		self.changes_made = 1
		if i > 0:
			Store.log(ngettext("redo (%d further redo available)",
													"redo (%d further redos available)",
													i) % i)
		else:
			Store.log( _("no further redo"))
		self.event_generate( "<<redo>>")


	def start_new_undo_record( self, name=''):
		if name != "arrow-key-move":
			self.before_undo_record()
		if not self.changes_made:
			self.changes_made = 1
		self.um.start_new_record( name=name)
		self.after_undo_record()


	def before_undo_record( self):
		"""this method is place where periodical checks and other things that should be done before
		undo is recorded should be done"""
		checks.check_linear_fragments( self)


	def after_undo_record( self):
		"""similar to before_undo_record but is run after the undo was recorded"""
		# check the bbox to see if we need to update scroll region
		if not hasattr( self, "_old_bbox"):
			self._old_bbox = self.bbox(ALL)
			self.update_scrollregion()
		else:
			_bbox = self.bbox(ALL)
			if _bbox != self._old_bbox:
				self.update_scrollregion()


	def display_weight_of_selected( self):
		s_mols = [m for m in self.selected_to_unique_top_levels()[0] if m.object_type == 'molecule']
		w = 0
		for m in s_mols:
			w += m.get_formula_dict().get_molecular_weight()
		Store.app.update_status( str( w))


	def display_info_on_selected( self):
		s_mols = [m for m in self.selected_to_unique_top_levels()[0] if m.object_type == 'molecule']
		if not s_mols:
			return

		dialog = BkTextDialog( self, title=_("Info on selected molecules"), defaultbutton=0)
		dialog.withdraw()

		comps = PT.formula_dict()
		for m in s_mols:
			comp = m.get_formula_dict()
			comps += comp
			dialog.insert( 'end', _("Name: %s") % m.name)
			dialog.insert( 'end', "\n")
			dialog.insert( 'end', _("Id: %s") % m.id)
			dialog.insert( 'end', "\n")
			dialog.insert( 'end', _("Formula: %s") % comp)
			dialog.insert( 'end', "\n")
			dialog.insert( 'end', _("Weight: %4.4f") % comp.get_molecular_weight())
			dialog.insert( 'end', "\n")
			dialog.insert( 'end', _("Monoisotopic mass: %12.8f") % comp.get_exact_molecular_mass())
			dialog.insert( 'end', "\n")
			dialog.insert( 'end', _("Composition: %s") % PT.dict_to_composition( comp))
			dialog.insert( 'end', "\n\n")
		if len( s_mols) > 1:
			dialog.insert( '1.0', "\n")
			dialog.insert( "1.0", _("Individual molecules:"), 'headline')
			dialog.insert( '1.end', "\n")
			dialog.insert( 'end', "\n")
			dialog.insert( "end", _("Summary for all selected molecules:"), 'headline')
			dialog.insert( 'end', "\n\n")
			dialog.insert( "end", _("Formula: %s") % comps)
			dialog.insert( 'end', "\n")
			dialog.insert( "end", _("Weight: %4.4f") % comps.get_molecular_weight())
			dialog.insert( 'end', "\n")
			dialog.insert( 'end', _("Monoisotopic mass: %12.8f") % comps.get_exact_molecular_mass())
			dialog.insert( 'end', "\n")
			dialog.insert( 'end', _("Composition: %s") % PT.dict_to_composition( comps))
		dialog.tag_config( 'headline', underline=1)
		dialog.activate()


	def check_chemistry_of_selected( self):
		from bkchem import validator
		val = validator.validator()
		s_mols = [m for m in self.selected_to_unique_top_levels()[0] if m.object_type == 'molecule']
		if not s_mols:
			return

		dialog = BkTextDialog( self, title=_("Chemistry check of selected molecules"), defaultbutton=0)
		dialog.withdraw()

		val.validate( s_mols)
		dialog.insert( 'end', val.report.get_summary())

		dialog.activate()
