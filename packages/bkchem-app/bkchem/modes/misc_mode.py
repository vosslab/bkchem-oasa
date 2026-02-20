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

"""Miscellaneous mode for numbering, wavy lines, and other small tools."""

import math

from warnings import warn
from oasa import geometry

from bkchem.singleton_store import Store
from bkchem.modes.edit_mode import edit_mode


# -------------------- MISCELANOUS MODE --------------------
class misc_mode( edit_mode):
	"""container mode for small, seldom needed modes"""

	wavy_width = 3

	def __init__( self):
		edit_mode.__init__( self)
		# submodes, name loaded from YAML

		self._number = 1
		self._line = None


	def mouse_click( self, event):
		if self.get_submode( 0) == "numbering":
			if self.focused and hasattr( self.focused, 'number'):
				self.focused.number = str( self._number)
				self._number += 1
				for m in self.focused.get_marks_by_type( "atom_number"):
					m.auto = False
				Store.app.paper.start_new_undo_record()


	def mouse_down( self, event, modifiers=None):
		edit_mode.mouse_down( self, event)


	def mouse_drag( self, event):
		if self.get_submode( 0) == "numbering":
			edit_mode.mouse_drag( self, event)
		else:
			coords = self._startx, self._starty, event.x, event.y
			if self._line:
				Store.app.paper.coords( self._line, *coords)
			else:
				self._line = Store.app.paper.create_line( *coords)


	def mouse_up( self, event):
		if self.get_submode( 0) == "numbering":
			edit_mode.mouse_up( self, event)
		elif self.get_submode( 0) == "wavy":
			coords = self._startx, self._starty, event.x, event.y
			if self._line:
				Store.app.paper.delete( self._line)
				self._line = None
				# create the wavy line
				self._draw_wavy( coords)
			Store.app.paper.start_new_undo_record()


	def _draw_wavy( self, coords):
		x1, y1, x2, y2 = coords
		# main item
		x, y, x0, y0 = geometry.find_parallel( x1, y1, x2, y2, self.wavy_width/2.0)
		d = math.sqrt( (x1-x2)**2 + (y1-y2)**2) # length of the BkBond
		step_size = self.wavy_width
		dx = (x2 - x1)/d
		dy = (y2 - y1)/d
		ddx = x - x1
		ddy = y - y1

		coords2 = []
		coords2.extend((x1, y1))
		for i in range( 0, int( round( d/ step_size))+1):
			coords = [x1+dx*i*step_size+ddx, y1+dy*i*step_size+ddy, x1+dx*i*step_size-ddx, y1+dy*i*step_size-ddy]
			if i % 2:
				coords2.extend((coords[0], coords[1]))
			else:
				coords2.extend((coords[2], coords[3]))
		coords2.extend((x2, y2))
		Store.app.paper.new_polyline( coords2).draw()


	def cleanup( self):
		edit_mode.cleanup( self)
		Store.app.paper.remove_bindings()
		Store.app.paper.add_bindings()


	def startup( self):
		Store.app.paper.remove_bindings()
		Store.app.paper.add_bindings( active_names=('atom',))
		Store.app.paper.unselect_all()
		self._number = 1


	def leave_object( self, event):
		if self.focused:
			self.focused.unfocus()
			self.focused = None
		else:
			warn( "leaving NONE", UserWarning, 2)
