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

"""Atom mode for creating and editing atom types."""

from warnings import warn

import bkchem.chem_compat
from bkchem import dom_extensions
from bkchem import interactors
from bkchem.singleton_store import Store
from bkchem.modes.edit_mode import edit_mode


## -------------------- ATOM MODE --------------------
class atom_mode( edit_mode):

	def __init__( self):
		edit_mode.__init__( self)
		# name loaded from YAML
		self._start_point = None
		self._moved_point = None


	def mouse_down( self, event, modifiers = []):
		edit_mode.mouse_down( self, event, modifiers = modifiers)
		Store.app.paper.unselect_all()


	def mouse_drag( self, event):
		if not self._dragging:
			self._dragging = 1


	def mouse_up( self, event):
		if not self._dragging:
			self.mouse_click( event)
		self._dragging = 0


	def mouse_click( self, event):
		if not self.focused:
			name = Store.app.editPool.activate()
			if not name:
				return
			if name and not dom_extensions.isOnlyTags( name):
				mol = Store.app.paper.new_molecule()
				a = mol.create_vertex_according_to_text( None, name, interpret=Store.app.editPool.interpret)
				a.x = event.x
				a.y = event.y
				mol.insert_atom( a)
				a.draw()
				interactors.log_atom_type( a.__class__.__name__)
				Store.app.paper.select( [a])
				Store.app.paper.add_bindings()
				Store.app.paper.start_new_undo_record()
		else:
			if bkchem.chem_compat.is_chemistry_vertex( self.focused):
				a = self.focused
				name = Store.app.editPool.activate( text = a.symbol)
				if name and not dom_extensions.isOnlyTags( name):
					# we need to change the class of the vertex
					v = a.molecule.create_vertex_according_to_text( a, name, interpret=Store.app.editPool.interpret)
					a.copy_settings( v)
					a.molecule.replace_vertices( a, v)
					a.delete()
					v.draw()
					Store.app.paper.select( [v])
					interactors.log_atom_type( v.__class__.__name__)

					# cleanup
					[self.reposition_bonds_around_bond( o) for o in Store.app.paper.bonds_to_update()]
					[self.reposition_bonds_around_atom( o) for o in Store.app.paper.selected if o.object_type == "atom"]

					Store.app.paper.start_new_undo_record()
					Store.app.paper.add_bindings()


	def leave_object( self, event):
		if self.focused:
			self.focused.unfocus()
			self.focused = None
		else:
			warn( "leaving NONE", UserWarning, 2)
