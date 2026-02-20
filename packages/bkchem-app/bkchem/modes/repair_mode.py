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

"""Repair mode for click-to-repair geometry operations on individual molecules."""

# local repo modules
import oasa.repair_ops

from bkchem.singleton_store import Store, Screen
from bkchem.modes.edit_mode import edit_mode


# -------------------- REPAIR MODE --------------------
class repair_mode(edit_mode):
	"""Click a molecule to apply the selected repair operation."""

	def __init__(self):
		edit_mode.__init__(self)
		# submodes loaded from YAML

	#============================================
	def _get_bond_length_px(self) -> float:
		"""Return the standard bond length in pixels.

		Returns:
			Standard bond length in pixels.
		"""
		return Screen.any_to_px(Store.app.paper.standard.bond_length)

	#============================================
	def _get_molecule_from_focused(self):
		"""Return the molecule that the focused object belongs to, or None.

		Returns:
			The parent molecule of the focused atom/bond, or None.
		"""
		if not self.focused:
			return None
		# atoms and bonds have a .molecule attribute
		if hasattr(self.focused, 'molecule'):
			return self.focused.molecule
		return None

	#============================================
	def mouse_click(self, event):
		"""Apply the selected repair operation to the clicked molecule."""
		mol = self._get_molecule_from_focused()
		if mol is None:
			return
		op = self.get_submode(0)
		bl = self._get_bond_length_px()
		# dispatch to the correct repair operation
		if op == "normalize_lengths":
			oasa.repair_ops.normalize_bond_lengths(mol, bl)
		elif op == "normalize_angles":
			oasa.repair_ops.normalize_bond_angles(mol, bl)
		elif op == "normalize_rings":
			oasa.repair_ops.normalize_rings(mol, bl)
		elif op == "straighten":
			oasa.repair_ops.straighten_bonds(mol)
		elif op == "snap_hex":
			oasa.repair_ops.snap_to_hex_grid(mol, bl)
		elif op == "clean":
			# select all atoms and bonds in the molecule, clean, restore selection
			items = list(mol.atoms) + list(mol.bonds)
			Store.app.paper.unselect_all()
			Store.app.paper.select(items)
			Store.app.paper.clean_selected()
			Store.app.paper.unselect_all()
		else:
			return
		# redraw and record undo
		mol.redraw(reposition_double=1)
		Store.app.paper.start_new_undo_record()

	#============================================
	def mouse_down(self, event, modifiers=None):
		edit_mode.mouse_down(self, event)

	#============================================
	def mouse_drag(self, event):
		# no drag behavior in repair mode; just delegate for focus tracking
		edit_mode.mouse_drag(self, event)

	#============================================
	def startup(self):
		"""Set up bindings for repair mode (molecule targets only)."""
		Store.app.paper.remove_bindings()
		Store.app.paper.add_bindings(active_names=('atom', 'bond'))
		Store.app.paper.unselect_all()

	#============================================
	def cleanup(self):
		"""Restore standard bindings on mode exit."""
		edit_mode.cleanup(self)
		Store.app.paper.remove_bindings()
		Store.app.paper.add_bindings()

	#============================================
	def leave_object(self, event):
		if self.focused:
			self.focused.unfocus()
			self.focused = None
