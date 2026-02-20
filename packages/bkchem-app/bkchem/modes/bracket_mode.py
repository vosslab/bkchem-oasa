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

"""Bracket mode for creating rectangular and round brackets."""

import math

from bkchem.singleton_store import Store
from bkchem.modes.edit_mode import edit_mode


# -------------------- BRACKETS MODE --------------------
class bracket_mode( edit_mode):

	def __init__( self):
		edit_mode.__init__( self)
		# submodes, name loaded from YAML


	def _end_of_empty_drag( self, x1, y1, x2, y2):
		#convert to real coords
		x1 = Store.app.paper.canvas_to_real(x1)
		x2 = Store.app.paper.canvas_to_real(x2)
		y1 = Store.app.paper.canvas_to_real(y1)
		y2 = Store.app.paper.canvas_to_real(y2)
		if self.get_submode(0) == "rectangularbracket":
			dx = 0.05*math.sqrt( (y2-y1)**2 + (x2-x1)**2)
			Store.app.paper.new_polyline( [x1+dx, y1,
										   x1,    y1,
										   x1,    y2,
										   x1+dx, y2]).draw()

			Store.app.paper.new_polyline( [x2-dx, y1,
										   x2,    y1,
										   x2,    y2,
										   x2-dx, y2]).draw()

		elif self.get_submode(0) == "roundbracket":
			dx = 0.05*math.sqrt( (y2-y1)**2 + (x2-x1)**2)
			dy = abs( 0.05*(y2-y1))
			l1 = Store.app.paper.new_polyline( [x1+dx, y1,
												x1,    y1+dy,
												x1,    y2-dy,
												x1+dx, y2])
			l1.spline = True
			l1.draw()
			l2 = Store.app.paper.new_polyline( [x2-dx, y1,
												x2,    y1+dy,
												x2,    y2-dy,
												x2-dx, y2])
			l2.spline = True
			l2.draw()
		Store.app.paper.start_new_undo_record()
