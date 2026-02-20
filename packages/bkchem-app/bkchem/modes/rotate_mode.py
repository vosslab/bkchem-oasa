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

"""Rotate mode for 2D and 3D rotation of molecules."""

import math
import builtins
import tkinter.messagebox

from oasa import geometry
from oasa.transform_lib import Transform
from oasa.transform3d_lib import Transform3d

import bkchem.chem_compat
from bkchem import bkchem_utils
from bkchem.bond_lib import BkBond
from bkchem.arrow_lib import BkArrow
from bkchem.singleton_store import Store
from bkchem.modes.edit_mode import edit_mode

_ = builtins.__dict__.get( '_', lambda m: m)


class rotate_mode( edit_mode):

	def __init__( self):
		edit_mode.__init__( self)
		# submodes, name loaded from YAML
		self._rotated_mol = None
		self._rotated_atoms = []
		self._fixed = None


	def mouse_down( self, event, modifiers = []):
		edit_mode.mouse_down( self, event, modifiers = modifiers)
		# blocking is not necessary in rotate mode
		self._block_leave_event = 0
		self._fixed = None
		self._rotated_atoms = []
		if self.get_submode(0) == "3D" and self.get_submode(1) == "fixsomething":
			if len( Store.app.paper.selected) == 1:
				sel = Store.app.paper.selected[0]
				if isinstance( sel, BkBond):
					self._fixed = sel
				else:
					Store.log( _("The selected item must be a bond."), message_type="warning")
			else:
				Store.log( _("Exactly one item should be selected to fixed rotation to work, normal rotation will be used."), message_type="hint")
		Store.app.paper.unselect_all()
		if self.focused and (bkchem.chem_compat.is_chemistry_vertex( self.focused) or isinstance(self.focused, BkBond)):
			self._rotated_mol = self.focused.molecule
			if self._fixed:
				# 3D rotation around a bond
				self._rotated_atoms = self._get_objs_to_rotate()
			x1, y1, x2, y2 = Store.app.paper.list_bbox( [o.item for o in self._rotated_mol.atoms])
			self._centerx = x1+(x2-x1)/2.0
			self._centery = y1+(y2-y1)/2.0
		elif self.focused and self.get_submode(0) == '2D' and (isinstance( self.focused, BkArrow) or (hasattr( self.focused, 'arrow') and isinstance( self.focused.arrow, BkArrow))):
			if isinstance( self.focused, BkArrow):
				self._rotated_mol = self.focused
			else:
				self._rotated_mol = self.focused.arrow
			x1, y1, x2, y2 = self._rotated_mol.bbox()
			self._centerx = x1+(x2-x1)/2.0
			self._centery = y1+(y2-y1)/2.0
		elif self.focused:
			if self.get_submode(0) == '3D':
				tkinter.messagebox.showerror( _("You can only rotate molecules in 3D!"), _("Sorry but you can only rotate molecules in 3D."))
			else:
				tkinter.messagebox.showerror( _("You can only rotate molecules and arrows in 2D!"), _("Sorry but you can only rotate molecules and arrows in 2D."))


	def mouse_up( self, event):
		if not self._dragging:
			self.mouse_click( event)
		else:
			self._dragging = 0
			self._moved_atom = None
			if self._rotated_mol:
				if self.get_submode( 0) == '3D':
					[b.redraw( recalc_side=1) for b in self._rotated_mol.bonds]
					[a.reposition_marks() for a in self._rotated_mol.atoms]
				self._rotated_mol = None
				Store.app.paper.start_new_undo_record()
			if self._fixed:
				Store.app.paper.select( [self._fixed])
		Store.app.paper.add_bindings()


	def mouse_drag( self, event):
		if self.focused:
			self.focused.unfocus()
			self.focused = None
		if not self._dragging:
			self._dragging = 1
		if self._rotated_mol:
			dx1 = event.x - self._startx
			dy1 = event.y - self._starty
			sig = -geometry.on_which_side_is_point( (self._centerx, self._centery, self._startx, self._starty), (event.x, event.y))
			self._startx, self._starty = event.x, event.y
			if self.submode[0] == 0:
				# 2D rotation
				angle = round( sig * (abs( dx1) +abs( dy1)) / 50.0, 2)
				tr = Transform()
				tr.set_move( -self._centerx, -self._centery)
				tr.set_rotation( angle)
				tr.set_move( self._centerx, self._centery)
				self._rotated_mol.transform( tr)
			else:
				# 3D rotation
				if self.get_submode(1) == "fixsomething" and self._fixed and isinstance( self._fixed, BkBond):
					# we have a fixed part
					if self._fixed.molecule != self._rotated_mol:
						Store.log( _("You can only rotate the molecule for which you fixed a bond."), message_type="error")
						return
					sig = abs(dx1) > abs(dy1) and bkchem_utils.signum(dx1) or bkchem_utils.signum(dy1)
					angle = round( sig * math.sqrt(dx1**2 +dy1**2) / 50.0, 3)
					t = geometry.create_transformation_to_rotate_around_particular_axis( self._fixed.atom2.get_xyz(), self._fixed.atom1.get_xyz(), angle)
					for a in self._rotated_atoms:
						x, y, z = a.x, a.y, a.z
						x, y, z = t.transform_xyz( x, y, z)
						a.move_to( x, y)
						a.z = z
					for a in self._rotated_mol.bonds:
						a.simple_redraw()
				else:
					# normal rotation
					angle1 = round( dx1 / 50.0, 2)
					angle2 = round( dy1 / 50.0, 2)
					tr = Transform3d()
					tr.set_move( -self._centerx, -self._centery, 0)
					tr.set_rotation( -angle2, angle1, 0)
					tr.set_move( self._centerx, self._centery, 0)
					for a in self._rotated_mol.atoms:
						x, y, z = a.x, a.y, a.z
						x, y, z = tr.transform_xyz( x, y, z)
						a.move_to( x, y)
						a.z = z
					for a in self._rotated_mol.bonds:
						a.simple_redraw()


	def mouse_click( self, event):
		edit_mode.mouse_click( self, event)


	def _get_objs_to_rotate( self):
		if not self._shift:
			return self._fixed.molecule.atoms
		b = self._fixed
		mol = b.molecule
		mol.temporarily_disconnect_edge( b)
		cc = list( mol.get_connected_components())
		mol.reconnect_temporarily_disconnected_edge( b)
		if len( cc) == 1:
			return cc[0]
		else:
			if bkchem.chem_compat.is_chemistry_vertex( self.focused):
				to_use = self.focused in cc[0] and cc[0] or cc[1]
			elif isinstance( self.focused, BkBond):
				if self.focused in mol.vertex_subgraph_to_edge_subgraph( cc[0]):
					to_use = cc[0]
				else:
					to_use = cc[1]
			else:
				assert bkchem.chem_compat.is_chemistry_vertex( self.focused) or isinstance( self.focused, BkBond)
			return to_use
