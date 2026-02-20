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

"""Edit mode - the primary editing mode and parent for most leaf modes."""

import math
import time
import string
import builtins

import oasa.hex_grid
import bkchem.chem_compat
from bkchem import parents
from bkchem import dialogs
from bkchem import bkchem_utils
from bkchem import interactors
from bkchem import dom_extensions
from bkchem import helper_graphics as hg
from bkchem.bond_lib import BkBond
from bkchem.atom_lib import BkAtom
from bkchem.group_lib import BkGroup
from bkchem.textatom_lib import BkTextatom
from bkchem.context_menu import context_menu
from bkchem.singleton_store import Store, Screen
from bkchem.modes.modes_lib import basic_mode

_ = builtins.__dict__.get( '_', lambda m: m)


### -------------------- EDIT MODE --------------------
class edit_mode(basic_mode):
	"""Basic editing mode.

	Also good as parent for more specialized modes.
	"""
	def __init__( self):
		basic_mode.__init__( self)
		# name loaded from YAML
		self._dragging = 0
		self._dragged_molecule = None
		self._block_leave_event = 0
		self._moving_selected_arrow = None
		self._last_click_time = 0
		self.focused = None
		# responses to key events
		self.register_key_sequence( ' ', self._set_name_to_selected)
		self.register_key_sequence( '##'+string.ascii_lowercase, self._set_name_to_selected)
		self.register_key_sequence( 'S-##'+string.ascii_lowercase, self._set_name_to_selected)
		self.register_key_sequence( 'Return', self._set_old_name_to_selected)
		self.register_key_sequence( 'Delete', self._delete_selected, use_warning=0)
		self.register_key_sequence( 'BackSpace', self._delete_selected, use_warning=0)
		# object related key bindings
		self.register_key_sequence( 'C-o C-e', self._expand_groups)
		# emacs like key bindings
		self.register_key_sequence( 'A-w', lambda : Store.app.paper.selected_to_clipboard())
		self.register_key_sequence( 'M-w', lambda : Store.app.paper.selected_to_clipboard())
		self.register_key_sequence( 'C-w', lambda : Store.app.paper.selected_to_clipboard( delete_afterwards=1))
		self.register_key_sequence( 'C-y', self._paste_clipboard)
		# windows style key bindings
		self.register_key_sequence( 'C-c', lambda : Store.app.paper.selected_to_clipboard())
		self.register_key_sequence( 'C-v', self._paste_clipboard)
		# 'C-x' from windoze is in use - 'C-k' instead
		self.register_key_sequence( 'C-k', lambda : Store.app.paper.selected_to_clipboard( delete_afterwards=1))
		# 'C-a' from windoze is in use - 'C-S-a' instead
		# chains (C-d as draw)
		self.register_key_sequence_ending_with_number_range( 'C-d', self.add_chain, numbers=list(range(2,10)))
		# config
		self.rectangle_selection = True  # this can be overriden by children

		self._move_sofar = 0

	def mouse_down( self, event, modifiers=None):
		mods = modifiers or []
		self._shift = 'shift' in mods
		self._ctrl = 'ctrl' in mods
		self._alt = 'alt' in mods
		# we focus what is under cursor if its not focused already
		if not self.focused:
			ids = Store.app.paper.find_overlapping( event.x, event.y, event.x, event.y)
			if ids and Store.app.paper.is_registered_id( ids[-1]):
				self.focused = Store.app.paper.id_to_object( ids[-1])
				self.focused.focus()
		if self.focused and isinstance( self.focused, hg.selection_square):
			# we will need that later to fix the right corner of the selection_square
			self._startx, self._starty = self.focused.get_fix()
		else:
			self._startx, self._starty = event.x, event.y
		self._block_leave_event = 1


	def mouse_down3( self, event, modifiers=None):
		if self.focused:
			if self.focused not in Store.app.paper.selected:
				Store.app.paper.unselect_all()
				Store.app.paper.select( [self.focused])
			dialog = context_menu( Store.app.paper.selected[:])
			dialog.post( event.x_root, event.y_root)


	def mouse_down2( self, event, modifiers=None):
		mods = modifiers or []
		if self.focused and not isinstance( self.focused, marks.mark):
			if self.focused not in Store.app.paper.selected:
				if not "shift" in mods:
					Store.app.paper.unselect_all()
				Store.app.paper.select( [self.focused])
			dialog = dialogs.config_dialog( Store.app, Store.app.paper.selected[:])
			if dialog.changes_made:
				Store.app.paper.start_new_undo_record()
			Store.app.paper.add_bindings()


	def mouse_up( self, event):
		self._block_leave_event = 0
		self._move_sofar = 0
		# this strange thing makes the moving of selected arrows and polygons possible - the problem is
		# that these objects are not in Store.app.paper.selected (only their points) and thus ...
		if self._moving_selected_arrow:
			Store.app.paper.select( [self._moving_selected_arrow])
			self._moving_selected_arrow = None
		if not self._dragging:
			self.mouse_click( event)
		else:
			if self._dragging == 3:
				### select everything in selection rectangle
				self._end_of_empty_drag( self._startx, self._starty, event.x, event.y)
				Store.app.paper.delete( self._selection_rect)
			elif self._dragging == 1:
				### move all selected
				# snap selected atoms to hex grid on drop if enabled
				if getattr(Store.app.paper, 'hex_grid_snap_enabled', False):
					spacing_px = Screen.any_to_px(Store.app.paper.standard.bond_length)
					for o in Store.app.paper.selected:
						if bkchem.chem_compat.is_chemistry_vertex(o):
							ax, ay = o.get_xy()
							sx, sy = oasa.hex_grid.snap_to_hex_grid(ax, ay, spacing_px)
							o.move_to(sx, sy, use_paper_coords=False)
				# repositioning of atoms and double bonds
				atoms = [j for i in [o.neighbors for o in Store.app.paper.selected
																if (bkchem.chem_compat.is_chemistry_vertex(o) and
																	o not in Store.app.paper.selected)]
								for j in i]
				atoms = bkchem_utils.filter_unique( [o for o in Store.app.paper.selected if bkchem.chem_compat.is_chemistry_vertex( o)] + atoms)
				[o.decide_pos() for o in atoms]
				[o.redraw() for o in atoms]
				[self.reposition_bonds_around_atom( o) for o in atoms]
				[self.reposition_bonds_around_bond( o) for o in self._bonds_to_update]
				Store.app.paper.handle_overlap()
				Store.app.paper.start_new_undo_record()
			elif self._dragging == 2:
				### move container of focused item
				Store.app.paper.handle_overlap()
				Store.app.paper.start_new_undo_record()
			elif self._dragging == 4:
				if self.focused:
					# the unfocus will otherwise not happen and cursor won't be restored
					self.focused.unfocus()
					self.focused = None
				Store.app.paper.start_new_undo_record()
			self._dragging = 0
			Store.app.paper.add_bindings()


	def mouse_click( self, event):
		if not self._shift:
			Store.app.paper.unselect_all()

		if self.focused:
#      if self.focused.object_type == 'arrow':
#        Store.app.paper.select( self.focused.points)
#      else:
			if self.focused in Store.app.paper.selected:
				Store.app.paper.unselect( [self.focused])
			elif (self.focused.object_type == 'selection_rect') and (self.focused.object in Store.app.paper.selected):
				Store.app.paper.unselect( [self.focused.object])
			else:
				if self.focused.object_type == 'selection_rect':
					Store.app.paper.select( [self.focused.object])
				else:
					Store.app.paper.select( [self.focused])
			# double click?
			t = time.time()
			if t - self._last_click_time < 0.3:
				self._last_click_time = 0
				self.double_click( event)
			else:
				self._last_click_time = t

			# when clicked with Ctrl pressed delete the focused atom
			if self._ctrl:
				self._delete_selected()

		Store.app.paper.add_bindings()


	def double_click( self, event):
		if self.focused:
			if bkchem.chem_compat.is_chemistry_vertex(self.focused) or isinstance(self.focused, BkBond):
				Store.app.paper.select( tuple( self.focused.molecule)) # molecule is iterator


	def mouse_drag( self, event):
		if self._ctrl:
			dx = 0
		else:
			dx = event.x-self._startx
		if self._shift: # shift to move only in x
			dy = 0
		else:
			dy = event.y-self._starty
		if not self._dragging:
			# drag threshold
			self._move_sofar += math.sqrt( dx**2 + dy**2)
			if self._move_sofar <= 1.0:
				return

			if self.focused and (self.focused.object_type == 'arrow' or self.focused.object_type == 'polygon' or self.focused.object_type == "polyline"):
				for p in self.focused.points:
					if p in Store.app.paper.selected:
						self._moving_selected_arrow = self.focused
						Store.app.paper.unselect( self.focused.points)
						break
			if self.focused and self.focused.object_type == 'selection_rect':
				# resizing of vector graphics
				self._dragging = 4
				self._dragged_molecule = self.focused
			elif self.focused and (self.focused in Store.app.paper.selected) or self._moving_selected_arrow:
				### move all selected
				self._dragging = 1
				Store.app.paper.select( Store.app.paper.atoms_to_update())
				self._bonds_to_update = Store.app.paper.bonds_to_update()
				self._arrows_to_update = Store.app.paper.arrows_to_update()
				self.focused.unfocus()
				self.focused = None
			elif self.focused:
				### move container of focused item
				self._dragging = 2
				if isinstance( self.focused, parents.child):
					self._dragged_molecule = self.focused.parent
				else:
					self._dragged_molecule = self.focused
				self.focused.unfocus()
				self.focused = None
			elif self.rectangle_selection:
				### select everything in selection rectangle
				if not self._shift:
					Store.app.paper.unselect_all()
				self._dragging = 3
				self._selection_rect = Store.app.paper.create_rectangle( self._startx, self._starty, event.x, event.y)
			else:
				### don't do anything
				self._dragging = 10  # just a placeholder to know that click should not be called
		if self._dragging == 1:
			### move all selected
			[o.move( dx, dy, use_paper_coords=True) for o in Store.app.paper.selected]
			if self._moving_selected_arrow:
				self._moving_selected_arrow.move( dx, dy, use_paper_coords=True)
			[o.redraw() for o in self._bonds_to_update]
			[o.redraw() for o in self._arrows_to_update]
			self._startx, self._starty = event.x, event.y
		elif self._dragging == 2:
			### move container of focused item
			self._dragged_molecule.move( dx, dy, use_paper_coords=True)
			self._startx, self._starty = event.x, event.y
		elif self._dragging == 3:
			# Creating the selection rectangle
			Store.app.paper.coords( self._selection_rect, self._startx, self._starty, event.x, event.y)
		elif self._dragging == 4:
			# whole means that the selection-rect is moving whole, not only one part
			whole = self._dragged_molecule.drag( event.x, event.y, fix=(self._startx, self._starty))
			if whole:
				self._startx, self._starty = event.x, event.y
			else:
				Store.log( '%i, %i' % ( dx, dy))


	def enter_object( self, object, event):
		if not self._dragging:
			if self.focused:
				self.focused.unfocus()
			self.focused = object
			if self.focused.object_type == 'selection_rect':
				self.focused.focus( item= Store.app.paper.find_withtag( 'current')[0])
			else:
				self.focused.focus()


	def leave_object( self, event):
		if self._block_leave_event:
			return
		if not self._dragging:
			if self.focused:
				self.focused.unfocus()
				self.focused = None


	def reposition_bonds_around_atom( self, a):
		bs = a.neighbor_edges
		[b.redraw( recalc_side = 1) for b in bs] # if b.order == 2]
		if isinstance( a, BkTextatom) or isinstance( a, BkAtom):
			a.reposition_marks()


	def reposition_bonds_around_bond( self, b):
		bs = bkchem_utils.filter_unique( b.atom1.neighbor_edges + b.atom2.neighbor_edges)
		[b.redraw( recalc_side = 1) for b in bs if b.order == 2]
		# all atoms to update
		atms = bkchem_utils.filter_unique(j for i in [[b.atom1, b.atom2] for b in bs] for j in i)
		[a.reposition_marks() for a in atms if isinstance( a, BkAtom)]


	def _end_of_empty_drag( self, x1, y1, x2, y2):
		Store.app.paper.select( [o for o in map( Store.app.paper.id_to_object,\
													Store.app.paper.find_enclosed( x1, y1, x2, y2)) if o])


	## METHODS FOR KEY EVENTS RESPONSES
	def _delete_selected( self):
		if self.focused and self.focused.object_type == 'selection_rect' and self.focused.object in Store.app.paper.selected:
			self.focused.unfocus()
			self.focused = None
		Store.app.paper.delete_selected()
		if self.focused and not Store.app.paper.is_registered_object( self.focused):
			# focused object was deleted
			self.focused = None
		Store.app.paper.add_bindings()


	def _paste_clipboard( self):
		Store.app.paper.unselect_all()
		xy = (Store.app.paper.canvasx( Store.app.paper.winfo_pointerx() -Store.app.paper.winfo_rootx()),
				Store.app.paper.canvasy( Store.app.paper.winfo_pointery() -Store.app.paper.winfo_rooty()))
		if xy[0] > 0 and xy[1] > 0:
			Store.app.paper.paste_clipboard( xy)


	def _set_name_to_selected( self, char=''):
		if Store.app.paper.selected:
			if not [i for i in Store.app.paper.selected if isinstance( i, parents.text_like)]:
				return # well, we do not want to set text to bonds and pluses anyway
			# check if we should start with the last used text or edit the one of selected things
			text = ''
			select = 1
			# the initial value for editing
			if char != '':
				if char.startswith("S-"):
					text = char[2:].upper()
				else:
					text = char
				select = 0
			elif len( Store.app.paper.selected) == 1:
				item = Store.app.paper.selected[0]
				if isinstance( item, parents.text_like):
					text = item.xml_ftext
			if text:
				name = Store.app.editPool.activate( text=text, select=select)
			else:
				name = Store.app.editPool.activate()
			if not name or dom_extensions.isOnlyTags( name):
				return
			self.set_given_name_to_selected( name, interpret=Store.app.editPool.interpret)


	def _set_old_name_to_selected( self):
		self.set_given_name_to_selected( Store.app.editPool.text)


	def set_given_name_to_selected( self, name, interpret=1):
		vtype = Store.app.paper.set_name_to_selected( name, interpret=interpret)
		# inform the user what was set
		interactors.log_atom_type( vtype)
		# cleanup
		[self.reposition_bonds_around_bond( o) for o in Store.app.paper.bonds_to_update()]
		[self.reposition_bonds_around_atom( o) for o in Store.app.paper.selected if o.object_type == "atom"]
		Store.app.paper.add_bindings()


	def _move_selected( self, dx, dy):
		Store.app.paper.select( Store.app.paper.atoms_to_update())
		_bonds_to_update = Store.app.paper.bonds_to_update()
		_arrows_to_update = Store.app.paper.arrows_to_update()

		[o.move( dx, dy) for o in Store.app.paper.selected]
		[o.redraw() for o in _bonds_to_update]
		[o.redraw() for o in _arrows_to_update]
		if Store.app.paper.um.get_last_record_name() == "arrow-key-move":
			Store.app.paper.um.delete_last_record()
		Store.app.paper.add_bindings()
		Store.app.paper.start_new_undo_record( name="arrow-key-move")


	def _expand_groups( self):
		if self.focused:
			self.focused.unfocus()
			self.focused = None
		Store.app.paper.expand_groups()


	def add_chain( self, n):
		if not self.focused:
			return
		a = self.focused
		mol = a.molecule
		for i in range( n):
			a, b = mol.add_atom_to( a)
			Store.app.paper.select( [a])
		Store.app.paper.start_new_undo_record()
		Store.app.paper.add_bindings()


# deferred import for marks (used in mouse_down2)
from bkchem import marks
