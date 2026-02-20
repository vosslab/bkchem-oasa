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

"""Draw mode for creating bonds and atoms."""

import builtins

from oasa import geometry
import oasa.hex_grid
import bkchem.chem_compat
from bkchem.bond_lib import BkBond
from bkchem.group_lib import BkGroup
from bkchem.singleton_store import Store, Screen
from bkchem.modes.edit_mode import edit_mode

_ = builtins.__dict__.get( '_', lambda m: m)


### -------------------- DRAW MODE --------------------
class draw_mode( edit_mode):

	def __init__( self):
		edit_mode.__init__( self)
		# submodes, name loaded from YAML
		self._moved_atom = None
		self._start_atom = None


	def mouse_down( self, event, modifiers = []):
		"""Starts a new bond, if no atom is focused (the mouse is being
		   pressed on bank space) creates a new BkAtom.
		   The BkBond is completed upon release (mouse_up())."""
		edit_mode.mouse_down( self, event, modifiers = modifiers)
		Store.app.paper.unselect_all()
		if not self.focused:
			mol = Store.app.paper.new_molecule()
			x = Store.app.paper.canvas_to_real(event.x)
			y = Store.app.paper.canvas_to_real(event.y)
			# snap new atom to hex grid if enabled
			if getattr(Store.app.paper, 'hex_grid_snap_enabled', False):
				spacing_px = Screen.any_to_px(Store.app.paper.standard.bond_length)
				x, y = oasa.hex_grid.snap_to_hex_grid(x, y, spacing_px)
			a = mol.create_new_atom( x, y)
			a.focus()
			self.focused = a
		#Store.app.paper.add_bindings()


	def mouse_up( self, event):
		"""Completion of bond started when pressing (mouse_down())."""
		if not self._dragging:
			#Make sure this was not thrown after click
			self.mouse_click( event)
		else:
			if self._moved_atom:
				Store.app.paper.select( [self._moved_atom])
			deleted, preserved = Store.app.paper.handle_overlap() # should be done before repositioning for ring closure to take effect
			# repositioning of double bonds

			for vrx in preserved + [self._start_atom]:
				if vrx:
					# at first atom text
					if hasattr( vrx, 'update_after_valency_change'):
						vrx.update_after_valency_change()
					# warn when valency is exceeded
					if vrx.free_valency < 0:
						Store.log( _("maximum valency exceeded!"), message_type="warning")
					# adding more than one bond to group
					if isinstance( vrx, BkGroup):
						# we need to change the class of the vertex
						a = vrx
						m = a.molecule
						v = m.create_vertex_according_to_text( None, a.xml_ftext, interpret=0)
						a.copy_settings( v)
						a.molecule.replace_vertices( a, v)
						a.delete()
						v.draw()
						Store.log( _("Groups could have valency of 1 only! It was transformed to text!"), message_type="warning")

					self.reposition_bonds_around_atom( vrx)

			self._dragging = 0
			self._start_atom = None
			self._moved_atom = None
			Store.app.paper.add_bindings()
			Store.app.paper.start_new_undo_record()


	def mouse_click( self, event):
		if not self.focused:
			#print("it should not get here!!!")
			mol = Store.app.paper.new_molecule()
			x = Store.app.paper.canvas_to_real(event.x)
			y = Store.app.paper.canvas_to_real(event.y)
			a = mol.create_new_atom( x, y)
			Store.app.paper.add_bindings()
			b = BkBond( standard = Store.app.paper.standard,
						type=self.__mode_to_bond_type(),
						order=self.__mode_to_bond_order(),
						simple_double=self.submode[4])
			Store.app.paper.select( [mol.add_atom_to( a, bond_to_use=b)[0]])
			self.focused = a
		else:
			if bkchem.chem_compat.is_chemistry_vertex( self.focused):
				b = BkBond( standard = Store.app.paper.standard,
						  type=self.__mode_to_bond_type(),
						  order=self.__mode_to_bond_order(),
						  simple_double=self.submode[4])
				a, b = self.focused.molecule.add_atom_to( self.focused, bond_to_use=b)
				# update atom text
				if hasattr( self.focused, 'update_after_valency_change'):
					self.focused.update_after_valency_change()
					self.reposition_bonds_around_atom(self.focused)
				# warn when valency is exceeded
				if self.focused.free_valency < 0:
					Store.log( _("maximum valency exceeded!"), message_type="warning")
				# adding more than one bond to group
				if isinstance( self.focused, BkGroup):
					# we need to change the class of the vertex
					a = self.focused
					m = a.molecule
					v = m.create_vertex_according_to_text( None, a.xml_ftext, interpret=0)
					a.copy_settings( v)
					a.molecule.replace_vertices( a, v)
					a.delete()
					v.draw()
					v.focus()
					self.focused = v
					Store.log( _("Groups could have valency of 1 only! It was transformed to text!"), message_type="warning")
				# repositioning of double bonds
				self.reposition_bonds_around_bond( b)
				Store.app.paper.select( [a])
			elif isinstance( self.focused, BkBond):
				if self._shift:
					self.focused.toggle_type( only_shift = 1, to_type=self.__mode_to_bond_type(),
												to_order=self.__mode_to_bond_order(),
												simple_double = self.submode[4])
					self.focused.focus() # refocus
				else:
					self.focused.toggle_type( to_type=self.__mode_to_bond_type(),
												to_order=self.__mode_to_bond_order(),
												simple_double = self.submode[4])
					# update the atoms
					[a.redraw() for a in self.focused.atoms]
					# warn when valency is exceeded
					if self.focused.atom1.free_valency < 0 or self.focused.atom2.free_valency < 0:
						Store.log( _("maximum valency exceeded!"), message_type="warning")
					else:
						self.focused.focus() # refocus

		Store.app.paper.handle_overlap()
		Store.app.paper.start_new_undo_record()
		Store.app.paper.add_bindings()


	def mouse_drag( self, event):
		if not self._dragging:
			self._dragging = 1
			if self.focused and bkchem.chem_compat.is_chemistry_vertex( self.focused):
				self._start_atom = self.focused
				b = BkBond( standard = Store.app.paper.standard,
						  type=self.__mode_to_bond_type(),
						  order=self.__mode_to_bond_order(),
						  simple_double=self.submode[4])
				if self.submode[3] == 1:
					# Free-hand lenght
					self._moved_atom, self._bonds_to_update = self.focused.molecule.add_atom_to( self.focused,
																								   bond_to_use=b,
																								   pos=(event.x, event.y))
				else:
					self._moved_atom, self._bonds_to_update = self.focused.molecule.add_atom_to( self.focused,
																								   bond_to_use=b)

				# deactivate the new atom and bond for focus
				Store.app.paper._do_not_focus = [self._moved_atom, b]

				# update atom text
				if hasattr( self.focused, 'update_after_valency_change'):
					self.focused.update_after_valency_change()

				#Store.app.paper.add_bindings( active_names=('atom',))

		if self._start_atom:
			z = 0
			if self.focused and self.focused != self._start_atom and bkchem.chem_compat.is_chemistry_vertex( self.focused):
				# Close bond on existing atom.
				x, y = self.focused.get_xy()
				z = self.focused.z
				self._moved_atom.move_to( x, y, use_paper_coords=False)
			elif self.submode[3] == 1:
				# Free-hand lenght
				x, y = event.x, event.y
				# snap free-hand endpoint to hex grid if enabled
				if getattr(Store.app.paper, 'hex_grid_snap_enabled', False):
					spacing_px = Screen.any_to_px(Store.app.paper.standard.bond_length)
					# convert canvas coords to model coords, snap, convert back
					rx = Store.app.paper.canvas_to_real(x)
					ry = Store.app.paper.canvas_to_real(y)
					rx, ry = oasa.hex_grid.snap_to_hex_grid(rx, ry, spacing_px)
					x = Store.app.paper.real_to_canvas(rx)
					y = Store.app.paper.real_to_canvas(ry)
				self._moved_atom.move_to( x, y, use_paper_coords=True)
			else:
				# Fixed lenght
				dx = event.x - self._startx
				dy = event.y - self._starty
				x0, y0 = self._start_atom.get_xy_on_paper()
				x,y = geometry.point_on_circle( x0, y0,
												Store.app.paper.real_to_canvas(Screen.any_to_px( Store.app.paper.standard.bond_length)),
												direction = (dx, dy),
												resolution = int( self.submodes[0][ self.submode[ 0]]))
				# snap fixed-length endpoint to hex grid if enabled
				if getattr(Store.app.paper, 'hex_grid_snap_enabled', False):
					spacing_px = Screen.any_to_px(Store.app.paper.standard.bond_length)
					rx = Store.app.paper.canvas_to_real(x)
					ry = Store.app.paper.canvas_to_real(y)
					rx, ry = oasa.hex_grid.snap_to_hex_grid(rx, ry, spacing_px)
					x = Store.app.paper.real_to_canvas(rx)
					y = Store.app.paper.real_to_canvas(ry)
				self._moved_atom.move_to( x, y, use_paper_coords=True)
			# to be able to connect atoms with non-zero z coordinate
			if z != 0:
				self._moved_atom.z = z
			self._bonds_to_update.redraw()


	def enter_object( self, object, event):
		if self.focused:
			self.focused.unfocus()
		self.focused = object
		self.focused.focus()


	def leave_object( self, event):
		if self.focused:
			self.focused.unfocus()
			self.focused = None
		else:
			pass #warn( "leaving NONE", UserWarning, 2)


	def __mode_to_bond_type( self):
		"""maps bond type submode to bond_type"""
		type = self.get_submode( 2)
		if type == 'dotted':
			return "o"
		elif type == 'wavy':
			return "s"
		else:
			return type[0]


	def __mode_to_bond_order( self):
		order = self.submode[1]+1
		return order
