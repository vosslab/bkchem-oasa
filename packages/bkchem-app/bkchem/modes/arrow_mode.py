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

"""Arrow mode for creating and editing arrows."""

from warnings import warn
from oasa import geometry
from bkchem.singleton_store import Store, Screen
from bkchem.modes.edit_mode import edit_mode


## -------------------- ARROW MODE --------------------
class arrow_mode( edit_mode):

	def __init__( self):
		edit_mode.__init__( self)
		# submodes, name loaded from YAML (arrow types previously from arrow.available_types)
		self._start_point = None
		self._moved_point = None
		self._arrow_to_update = None
		self.__nothing_special = 0 # to easy determine whether new undo record should be started


	def mouse_down( self, event, modifiers = []):
		edit_mode.mouse_down( self, event, modifiers = modifiers)
		Store.app.paper.unselect_all()
		if not self.focused:
			spline = (self.get_submode( 2) == 'spline')
			type = self.get_submode( 3)
			arr = Store.app.paper.new_arrow( spline=spline, type=type)
			self._start_point = arr.create_new_point( event.x, event.y, use_paper_coords=True)
			self._start_point.focus()
			self.focused = self._start_point
			self._arrow_to_update = arr
			#arr.draw()
		elif self.focused.object_type == 'point' and self.focused.arrow.object_type == 'arrow':
			self._start_point = self.focused
			self._arrow_to_update = self._start_point.arrow
		elif self.focused.object_type == 'arrow':
			self._arrow_to_update = self.focused
			self._start_point = None
		else:
			self.__nothing_special = 1
		self._block_leave_event = 0
		Store.app.paper.add_bindings()


	def mouse_drag( self, event):
		if self._start_point:
			if not self._dragging:
				self._dragging = 1
				# update the spline-notspline in case it differs from the set submode
				spline = (self.get_submode( 2) == 'spline')
				if self._arrow_to_update.spline != spline:
					self._arrow_to_update.spline = spline
				if self._start_point == self._arrow_to_update.points[-1]:
					pos = -1
				else:
					pos = self._arrow_to_update.points.index( self._start_point)
				self._moved_point = self._start_point.arrow.create_new_point( event.x, event.y, position=pos, use_paper_coords=True)
			if self.submode[1] == 1:
				x, y = event.x, event.y
			else:
				dx = event.x - self._startx
				dy = event.y - self._starty
				x0, y0 = self._start_point.get_xy_on_paper()
				x,y = geometry.point_on_circle( x0, y0,
												Store.app.paper.real_to_canvas( Screen.any_to_px( Store.app.paper.standard.arrow_length)),
												direction = (dx, dy),
												resolution = int( self.submodes[0][ self.submode[ 0]]))
			self._moved_point.move_to( x, y, use_paper_coords=True)
			self._arrow_to_update.redraw()


	def mouse_up( self, event):
		if not self._dragging:
			# update the spline-notspline in case it differs from the set submode
			spline = (self.get_submode( 2) == 'spline')
			if self._arrow_to_update and self._arrow_to_update.spline != spline:
				self._arrow_to_update.spline = spline
				self._arrow_to_update.redraw()
			# change the arrow direction only if the spline was not changed
			elif self._arrow_to_update and not self._start_point:
				self._arrow_to_update.change_direction()
			# add point
			elif self._arrow_to_update:
				x0, y0 = self._start_point.get_xy_on_paper()
				if self._start_point == self._arrow_to_update.points[-1]:
					pos = -1
				else:
					pos = self._arrow_to_update.points.index( self._start_point)
				pnt = self._arrow_to_update.create_new_point(
				x0+Store.app.paper.real_to_canvas( Screen.any_to_px( Store.app.paper.standard.arrow_length)),
				y0, position=pos, use_paper_coords=True)
				Store.app.paper.select( [pnt])
				self._arrow_to_update.redraw()
			#self.mouse_click( event)
		else:
			if self._moved_point:
				Store.app.paper.select( [self._moved_point])
			self._dragging = 0
		self._start_point = None
		self._moved_point = None
		self._arrow_to_update = None
		if self.__nothing_special:
			self.__nothing_special = 0
		else:
			Store.app.paper.start_new_undo_record()
		Store.app.paper.add_bindings()


	def mouse_click( self, event):
		pass


	def enter_object( self, object, event):
		if self.focused:
			self.focused.unfocus()
		self.focused = object
		if self.focused.object_type == 'selection_rect':
			self.focused.focus( item= Store.app.paper.find_withtag( 'current')[0])
		else:
			self.focused.focus()


	def leave_object( self, event):
		if self.focused:
			self.focused.unfocus()
			self.focused = None
		else:
			warn( "leaving NONE", UserWarning, 2)
