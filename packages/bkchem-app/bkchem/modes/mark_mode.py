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

"""Mark mode for adding and removing marks on atoms."""

import builtins

import bkchem.chem_compat
from bkchem import marks
from bkchem import special_parents
from bkchem.atom_lib import BkAtom
from bkchem.textatom_lib import BkTextatom
from bkchem.context_menu import context_menu
from bkchem.singleton_store import Store
from bkchem.modes.edit_mode import edit_mode

_ = builtins.__dict__.get( '_', lambda m: m)


## -------------------- MARK MODE --------------------
class mark_mode( edit_mode):

	def __init__( self):
		edit_mode.__init__( self)
		# submodes, name loaded from YAML

		self.register_key_sequence( 'Up', lambda : self._move_mark_for_selected( 0, -1), use_warning=0)
		self.register_key_sequence( 'Down', lambda : self._move_mark_for_selected( 0, 1), use_warning=0)
		self.register_key_sequence( 'Left', lambda : self._move_mark_for_selected( -1, 0), use_warning=0)
		self.register_key_sequence( 'Right', lambda : self._move_mark_for_selected( 1, 0), use_warning=0)

		self.rectangle_selection = False


	def mouse_click( self, event):
		mark_name = self.get_submode( 0)
		recode = {'dottedelectronpair':'dotted_electronpair',
				  'plusincircle'      :'plus',
				  'minusincircle'     :'minus',
				  'pzorbital'         :'pz_orbital'}
		if mark_name in recode:
			mark_name = recode[ mark_name]
		if self.get_submode( 1) == 'add':
			# we are adding a mark
			if self.focused and (isinstance( self.focused, special_parents.drawable_chem_vertex)):
				try:
					m = self.focused.set_mark( mark=mark_name)
				except ValueError:
					Store.log( _("This mark type is not allowed for this object"))
					return
				if m:
					m.register()
				if (self.focused.show_hydrogens and self.focused.show) and not isinstance( self.focused, BkTextatom):
					self.focused.redraw()
				Store.app.paper.start_new_undo_record()

		elif self.get_submode( 1) == 'remove':
			# we are removing a mark
			if self.focused:
				if isinstance( self.focused, BkAtom) or isinstance( self.focused, BkTextatom):
					# we do it by name
					m = self.focused.remove_mark( mark_name)
					if not m:
						Store.log( _("There are no marks of type %s on the focused atom") % mark_name, message_type="warning")
					else:
						if (self.focused.show_hydrogens and self.focused.show) and not isinstance( self.focused, BkTextatom):
							self.focused.redraw()
						Store.app.paper.start_new_undo_record()
				elif isinstance( self.focused, marks.mark):
					# we do it by reference
					m = self.focused.atom.remove_mark( self.focused)
					if (self.focused.atom.show_hydrogens and self.focused.atom.show) and not isinstance( self.focused, BkTextatom):
						self.focused.atom.redraw()
					self.focused = None
					Store.app.paper.start_new_undo_record()

		Store.app.paper.add_bindings()


	def mouse_down3( self, event, modifiers = []):
		if self.focused and isinstance( self.focused, marks.mark):
			dialog = context_menu( [self.focused])
			dialog.post( event.x_root, event.y_root)
			if dialog.changes_made:
				Store.app.paper.start_new_undo_record()


	def mouse_drag( self, event):
		# this is here because the pz_orbital is rotated instead of moved when dragging,
		# therefore we need to use the move_to to position the mark
		# "pivot point" under the cursor when drags begins
		if not self._dragging and self.focused and self.focused.object_type == "mark" and self.focused.__class__.__name__ == "pz_orbital":
			self.focused.move_to( event.x, event.y)
		edit_mode.mouse_drag( self, event)


	def _move_mark_for_selected( self, dx, dy):
		to_move = [a for a in Store.app.paper.selected if bkchem.chem_compat.is_chemistry_vertex( a)]

		for a in to_move:
			for m in a.marks:
				m.move( dx, dy)

		if Store.app.paper.um.get_last_record_name() == "arrow-key-move":
			Store.app.paper.um.delete_last_record()
		Store.app.paper.start_new_undo_record( name="arrow-key-move")


	def startup( self):
		self._register_all_marks( Store.app.paper)
		Store.app.paper.remove_bindings()
		Store.app.paper.add_bindings( active_names=("mark","atom"))


	def cleanup( self, paper=None):
		edit_mode.cleanup( self, paper=paper)
		pap = paper or Store.app.paper
		self._unregister_all_marks( pap)
		pap.remove_bindings()
		pap.add_bindings()


	def _register_all_marks( self, paper):
		[i.register() for i in self._all_marks( paper)]


	def _unregister_all_marks( self, paper):
		[i.unregister() for i in self._all_marks( paper)]


	def _all_marks( self, paper):
		for m in paper.molecules:
			for a in m.atoms:
				if hasattr( a, 'marks'):
					for mark in a.marks:
						yield mark


	def on_paper_switch( self, old, new):
		self.cleanup( old)
		self.startup()
