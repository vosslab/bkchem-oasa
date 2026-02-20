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

"""Plus mode for placing plus signs on the canvas."""

from warnings import warn
from bkchem.singleton_store import Store
from bkchem.modes.edit_mode import edit_mode


class plus_mode( edit_mode):

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
			pl = Store.app.paper.new_plus( event.x, event.y)
			Store.app.paper.select( [pl])
		else:
			pass
		Store.app.paper.start_new_undo_record()
		Store.app.paper.add_bindings()


	def leave_object( self, event):
		if self.focused:
			self.focused.unfocus()
			self.focused = None
		else:
			warn( "leaving NONE", UserWarning, 2)
