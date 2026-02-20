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

"""Text mode for creating and editing text objects."""

import builtins

from warnings import warn

import bkchem.chem_compat
from bkchem import dom_extensions
from bkchem.singleton_store import Store
from bkchem.modes.edit_mode import edit_mode

# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


##--------------------TEXT MODE--------------------
class text_mode( edit_mode):

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
			# there is either something selected or a new thing is added
			# the unselecting code before does ensure that nothing is selected
			# when we click outside to create something new
			Store.app.paper.set_name_to_selected( name)
			if name and not dom_extensions.isOnlyTags( name):
				txt = Store.app.paper.new_text( event.x, event.y, text=name)
				txt.draw()
				Store.app.paper.select( [txt])
				Store.app.paper.add_bindings()
				Store.app.paper.start_new_undo_record()
		else:
			if self.focused.object_type == 'text':
				Store.app.paper.select( [self.focused])
				name = Store.app.editPool.activate( text = self.focused.xml_ftext)
				if name and not dom_extensions.isOnlyTags( name):
					Store.app.paper.set_name_to_selected( name)
					Store.app.paper.add_bindings()
			elif bkchem.chem_compat.is_chemistry_vertex( self.focused):
				Store.log( _("The text mode can no longer be used to edit atoms, use atom mode."),
								message_type="warning")


	def leave_object( self, event):
		if self.focused:
			self.focused.unfocus()
			self.focused = None
		else:
			warn( "leaving NONE", UserWarning, 2)
