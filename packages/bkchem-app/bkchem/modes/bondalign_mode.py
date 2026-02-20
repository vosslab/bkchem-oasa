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

"""Bond alignment mode for aligning, mirroring, and inverting molecules."""

import math
import builtins

from oasa import geometry
from oasa.transform_lib import Transform

import bkchem.chem_compat
from bkchem.bond_lib import BkBond
from bkchem.singleton_store import Store
from bkchem.modes.edit_mode import edit_mode

# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


class bondalign_mode( edit_mode):

	def __init__( self):
		edit_mode.__init__( self)
		# submodes, name loaded from YAML
		self._rotated_mol = None
		self.first_atom_selected = None
		self._needs_two_atoms = [1,1,0,1,-1]  #-1 is for those that accept only bonds


	def mouse_down( self, event, modifiers = []):
		if not self.focused:
			return
		if not (bkchem.chem_compat.is_chemistry_vertex(self.focused) or isinstance(self.focused, BkBond)):
			return
		if self._needs_two_atoms[ self.submode[0]] == -1 and bkchem.chem_compat.is_chemistry_vertex( self.focused):
			return
		# edit_mode.mouse_down( self, event, modifiers = modifiers)
		self._block_leave_event = 0
		if not self.first_atom_selected:
			Store.app.paper.unselect_all()
		if isinstance(self.focused, BkBond):
			if self.first_atom_selected:
				# waiting for second atom selection, clicking bond does nothing
				Store.log( _("select the second atom, please."), message_type="hint")
				return
			self._rotated_mol = self.focused.molecule
			x1, y1 = self.focused.atom1.get_xy()
			x2, y2 = self.focused.atom2.get_xy()
			coords = (x1,y1,x2,y2)
		elif bkchem.chem_compat.is_chemistry_vertex( self.focused):
			if not self.first_atom_selected: # first BkAtom picked
				if self._needs_two_atoms[ self.submode[0]] > 0:
					self.first_atom_selected = self.focused
					self.first_atom_selected.select()
					Store.app.paper.add_bindings()
					self._rotated_mol = self.focused.molecule
					return
				else:
					self._rotated_mol = self.focused.molecule
					coords = self.focused.get_xy()
			else: # second BkAtom picked
				if self.focused.molecule != self.first_atom_selected.molecule:
					Store.log( _("atoms must be in the same molecule!"), message_type="hint")
					return
				if self.focused == self.first_atom_selected:
					Store.log( _("atoms must be different!"), message_type="hint")
					return
				x1, y1 = self.first_atom_selected.get_xy()
				x2, y2 = self.focused.get_xy()
				coords = (x1,y1,x2,y2)
				self.first_atom_selected.unselect()
				self.first_atom_selected = None
		tr = self.__class__.__dict__['_transform_'+self.get_submode(0)]( self, coords)
		if hasattr( self, '_apply_to_'+self.get_submode(0)):
			apply_to = self.__class__.__dict__['_apply_to_'+self.get_submode(0)]( self)
			if apply_to == None:
				return
			[o.transform( tr) for o in apply_to]
		else:
			self._rotated_mol.transform( tr)
		# Force full canvas refresh after transform-based edits so paper state is
		# visually consistent immediately (bboxes/selection helpers/labels).
		Store.app.paper.redraw_all()
		Store.app.paper.update_idletasks()
		self._rotated_mol = None
		Store.app.paper.start_new_undo_record()
		Store.app.paper.add_bindings()

#    if self.focused:
#      self.focused.unfocus()
#      self.focused = None


	def _transform_tohoriz( self, coords):
		x1, y1, x2, y2 = coords
		centerx = ( x1 + x2) / 2
		centery = ( y1 + y2) / 2
		angle0 = geometry.clockwise_angle_from_east( x2 - x1, y2 - y1)
		if angle0 >= math.pi :
			angle0 = angle0 - math.pi
		if (angle0 > -0.005) and (angle0 < .005) :
		# if angle0 == 0  :
			# bond is already horizontal => horizontal "flip"
			angle = math.pi
		elif angle0 <= math.pi/2:
			angle = -angle0
		else: # pi/2 < angle < pi
			angle = math.pi - angle0
		tr = Transform()
		tr.set_move( -centerx, -centery)
		tr.set_rotation( angle)
		tr.set_move(centerx, centery)
		return tr


	def _transform_tovert( self, coords):
		x1, y1, x2, y2 = coords
		centerx = ( x1 + x2) / 2
		centery = ( y1 + y2) / 2
		angle0 = geometry.clockwise_angle_from_east( x2 - x1, y2 - y1)
		if angle0 >= math.pi :
			angle0 = angle0 - math.pi
		if (angle0 > math.pi/2 - .005) and (angle0 < math.pi/2 + 0.005):
		# if angle0 == math.pi/2:
			# bond is already vertical => vertical "flip"
			angle = math.pi
		else:
			angle = math.pi/2 - angle0
		tr = Transform()
		tr.set_move( -centerx, -centery)
		tr.set_rotation( angle)
		tr.set_move(centerx, centery)
		return tr


	def _transform_invertthrough( self, coords):
		if len( coords) == 4:
			x1, y1, x2, y2 = coords
			x = ( x1 +x2) /2.0
			y = ( y1 +y2) /2.0
		else:
			x, y = coords
		tr = Transform()
		tr.set_move( -x, -y)
		tr.set_scaling_xy( -1, -1)
		tr.set_move( x, y)
		return tr


	def _transform_mirrorthrough( self, coords):
		x1, y1, x2, y2 = coords
		centerx = ( x1 + x2) / 2
		centery = ( y1 + y2) / 2
		angle0 = geometry.clockwise_angle_from_east( x2 - x1, y2 - y1)
		if angle0 >= math.pi :
			angle0 = angle0 - math.pi
		tr = Transform()
		tr.set_move( -centerx, -centery)
		tr.set_rotation( -angle0)
		tr.set_scaling_xy( 1, -1)
		tr.set_rotation( angle0)
		tr.set_move(centerx, centery)
		return tr


	def _transform_freerotation( self, coords):
		return self._transform_mirrorthrough( coords)


	def _apply_to_freerotation( self):
		assert isinstance( self.focused, BkBond)
		b = self.focused
		mol = b.molecule
		mol.delete_bond( b)
		cc = list( mol.get_connected_components())
		mol.add_edge( b.atom1, b.atom2, b)
		b.draw()
		b.focus()
		if len( cc) == 1:
			Store.log( _("Bond is part of a ring, there is no possiblity for rotation!"),
						message_type="hint")
			return None
		else:
			to_use = list( len( cc[0]) < len( cc[1]) and cc[0] or cc[1])
			return to_use + [b for b in mol.bonds if b.atom1 in to_use and b.atom2 in to_use]


	def cleanup( self):
		edit_mode.cleanup( self)
		if self.first_atom_selected:
			self.first_atom_selected.unselect()
			self.first_atom_selected = None


	def mouse_click( self, event):
		pass


	def mouse_up( self, event):
		pass


	def mouse_drag( self, event):
		pass

# backwards-compatible alias
bond_align_mode = bondalign_mode
