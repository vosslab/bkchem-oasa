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

"""Vector mode for creating rectangles, ovals, polygons, and polylines."""

from bkchem.singleton_store import Store
from bkchem.modes.edit_mode import edit_mode


class vector_mode( edit_mode):

	def __init__( self):
		edit_mode.__init__( self)
		# submodes, name loaded from YAML
		self._polygon_points = []
		self._polygon_line = None
		self._current_obj = None


	def mouse_down( self, event, modifiers=[]):
		edit_mode.mouse_down( self, event)
		if self.get_submode(0) in ("polyline","polygon"):
			Store.app.paper.unselect_all()
			self._block_leave_event = 0
			self._polygon_points += [event.x, event.y]


	def mouse_drag( self, event):
		if self.get_submode(0) in ("polyline","polygon"):
			self.mouse_move( event)
			return
		if not self.focused and not self._dragging:
			self._dragging = 5
			Store.app.paper.unselect_all()
			if self.get_submode( 0) == "rectangle":
				self._current_obj = Store.app.paper.new_rect( (self._startx, self._starty, event.x, event.y))
			elif self.get_submode( 0) == "square":
				self._current_obj = Store.app.paper.new_square( (self._startx, self._starty, event.x, event.y))
			elif self.get_submode( 0) == "oval":
				self._current_obj = Store.app.paper.new_oval( (self._startx, self._starty, event.x, event.y))
			elif self.get_submode( 0) == "circle":
				self._current_obj = Store.app.paper.new_circle( (self._startx, self._starty, event.x, event.y))
			self._current_obj.draw()
		elif not self.focused and self._dragging and self._current_obj:
			self._current_obj.resize( (self._startx, self._starty, event.x, event.y), fix=( self._startx, self._starty))
			Store.log( '%i, %i' % ( abs( self._startx-event.x), abs( self._starty-event.y)))
		elif self.focused or self._dragging in (1,2):
			edit_mode.mouse_drag( self, event)


	def mouse_up( self, event):
		if self.get_submode( 0) in ("polyline","polygon"):
			if not self._polygon_line:
				self._polygon_line = Store.app.paper.create_line( tuple( self._polygon_points + [event.x, event.y]), fill='black')
			else:
				Store.app.paper.coords( self._polygon_line, tuple( self._polygon_points + [event.x, event.y]))
			return
		self._block_leave_event = 0
		if self._dragging == 5:
			self._dragging = 0
			if self._current_obj:
				if self._current_obj.object_type != 'selection_rect':
					Store.app.paper.select( [self._current_obj])
				self._current_obj = None
			Store.app.paper.start_new_undo_record()
			Store.app.paper.add_bindings()
		elif self._dragging:
			edit_mode.mouse_up( self, event)
		else:
			self.mouse_click( event)


	def mouse_down3( self, event, modifiers = []):
		if self._polygon_line:
			Store.app.paper.delete( self._polygon_line)
			poly = None
			if self.get_submode( 0) == "polygon":
				if len( self._polygon_points) > 2:
					poly = Store.app.paper.new_polygon( tuple( self._polygon_points + [event.x, event.y]))
			elif self.get_submode( 0) == "polyline":
				poly = Store.app.paper.new_polyline( tuple( self._polygon_points + [event.x, event.y]))
			if poly:
				poly.draw()
				Store.app.paper.select( [poly])
			self._polygon_points = []
			self._polygon_line = None
			Store.app.paper.start_new_undo_record()
			Store.app.paper.add_bindings()
		else:
			edit_mode.mouse_down3( self, event, modifiers=modifiers)


	def mouse_move( self, event):
		if self.get_submode( 0) in ("polyline","polygon") and self._polygon_points:
			if not self._polygon_line:
				self._polygon_line = Store.app.paper.create_line( tuple( self._polygon_points + [event.x, event.y]), fill='black')
			else:
				Store.app.paper.coords( self._polygon_line, tuple( self._polygon_points + [event.x, event.y]))
