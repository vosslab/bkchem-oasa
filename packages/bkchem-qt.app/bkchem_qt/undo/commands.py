"""QUndoCommand subclasses for undo/redo support."""

# PIP3 modules
import PySide6.QtGui


#============================================
class AddAtomCommand(PySide6.QtGui.QUndoCommand):
	"""Undo command for adding an atom to the scene.

	On redo, adds the atom to the molecule model and its visual item
	to the scene. On undo, removes both.

	Args:
		scene: The QGraphicsScene containing visual items.
		molecule_model: The MoleculeModel to add/remove the atom from.
		atom_model: The AtomModel being added.
		atom_item: The AtomItem visual representation.
		text: Description shown in the undo history.
	"""

	#============================================
	def __init__(self, scene, molecule_model, atom_model, atom_item, text="Add Atom"):
		"""Initialize the add atom command.

		Args:
			scene: The QGraphicsScene.
			molecule_model: The MoleculeModel owning this atom.
			atom_model: The AtomModel to add.
			atom_item: The AtomItem for scene display.
			text: Undo history description.
		"""
		super().__init__(text)
		self._scene = scene
		self._molecule_model = molecule_model
		self._atom_model = atom_model
		self._atom_item = atom_item

	#============================================
	def redo(self) -> None:
		"""Add the atom to the molecule model and scene."""
		self._molecule_model.add_atom(self._atom_model)
		self._scene.addItem(self._atom_item)

	#============================================
	def undo(self) -> None:
		"""Remove the atom from the molecule model and scene."""
		self._scene.removeItem(self._atom_item)
		self._molecule_model.remove_atom(self._atom_model)


#============================================
class RemoveAtomCommand(PySide6.QtGui.QUndoCommand):
	"""Undo command for removing an atom and its connected bonds.

	On redo, removes the atom and all connected bonds from the molecule
	and scene. On undo, restores them.

	Args:
		scene: The QGraphicsScene containing visual items.
		molecule_model: The MoleculeModel to remove the atom from.
		atom_model: The AtomModel being removed.
		atom_item: The AtomItem visual representation.
		connected_bonds: List of (BondModel, BondItem) tuples for bonds
			connected to this atom.
		text: Description shown in the undo history.
	"""

	#============================================
	def __init__(self, scene, molecule_model, atom_model, atom_item,
				 connected_bonds, text="Remove Atom"):
		"""Initialize the remove atom command.

		Args:
			scene: The QGraphicsScene.
			molecule_model: The MoleculeModel owning this atom.
			atom_model: The AtomModel to remove.
			atom_item: The AtomItem for scene display.
			connected_bonds: List of (BondModel, BondItem) tuples.
			text: Undo history description.
		"""
		super().__init__(text)
		self._scene = scene
		self._molecule_model = molecule_model
		self._atom_model = atom_model
		self._atom_item = atom_item
		self._connected_bonds = list(connected_bonds)

	#============================================
	def redo(self) -> None:
		"""Remove connected bonds first, then the atom."""
		# remove connected bonds from scene and model
		for bond_model, bond_item in self._connected_bonds:
			self._scene.removeItem(bond_item)
			self._molecule_model.remove_bond(bond_model)
		# remove the atom
		self._scene.removeItem(self._atom_item)
		self._molecule_model.remove_atom(self._atom_model)

	#============================================
	def undo(self) -> None:
		"""Restore the atom and its connected bonds."""
		# restore the atom
		self._molecule_model.add_atom(self._atom_model)
		self._scene.addItem(self._atom_item)
		# restore connected bonds
		for bond_model, bond_item in self._connected_bonds:
			atom1 = bond_model.atom1
			atom2 = bond_model.atom2
			if atom1 is not None and atom2 is not None:
				self._molecule_model.add_bond(atom1, atom2, bond_model)
			self._scene.addItem(bond_item)


#============================================
class AddBondCommand(PySide6.QtGui.QUndoCommand):
	"""Undo command for adding a bond to the scene.

	On redo, adds the bond edge between the two endpoint atoms in the
	molecule model and adds the visual item to the scene. On undo,
	removes both.

	When ``_first_redo`` is True, the first redo call is skipped because
	the bond was already added during the draw interaction.

	Args:
		scene: The QGraphicsScene containing visual items.
		molecule_model: The MoleculeModel to add/remove the bond from.
		bond_model: The BondModel being added.
		bond_item: The BondItem visual representation.
		text: Description shown in the undo history.
	"""

	#============================================
	def __init__(self, scene, molecule_model, bond_model, bond_item, text="Add Bond"):
		"""Initialize the add bond command.

		Args:
			scene: The QGraphicsScene.
			molecule_model: The MoleculeModel owning this bond.
			bond_model: The BondModel to add.
			bond_item: The BondItem for scene display.
			text: Undo history description.
		"""
		super().__init__(text)
		self._scene = scene
		self._molecule_model = molecule_model
		self._bond_model = bond_model
		self._bond_item = bond_item
		# save endpoint references for redo
		self._atom1 = bond_model.atom1
		self._atom2 = bond_model.atom2
		# flag to skip first redo when bond is pre-added
		self._first_redo = False

	#============================================
	def redo(self) -> None:
		"""Add the bond to the molecule model and scene."""
		if self._first_redo:
			self._first_redo = False
			return
		self._molecule_model.add_bond(
			self._atom1, self._atom2, self._bond_model,
		)
		self._scene.addItem(self._bond_item)

	#============================================
	def undo(self) -> None:
		"""Remove the bond from the molecule model and scene."""
		self._scene.removeItem(self._bond_item)
		self._molecule_model.remove_bond(self._bond_model)


#============================================
class RemoveBondCommand(PySide6.QtGui.QUndoCommand):
	"""Undo command for removing a bond.

	On redo, removes the bond from the molecule model and scene. On
	undo, restores the bond.

	Args:
		scene: The QGraphicsScene containing visual items.
		molecule_model: The MoleculeModel to remove the bond from.
		bond_model: The BondModel being removed.
		bond_item: The BondItem visual representation.
		text: Description shown in the undo history.
	"""

	#============================================
	def __init__(self, scene, molecule_model, bond_model, bond_item, text="Remove Bond"):
		"""Initialize the remove bond command.

		Args:
			scene: The QGraphicsScene.
			molecule_model: The MoleculeModel owning this bond.
			bond_model: The BondModel to remove.
			bond_item: The BondItem for scene display.
			text: Undo history description.
		"""
		super().__init__(text)
		self._scene = scene
		self._molecule_model = molecule_model
		self._bond_model = bond_model
		self._bond_item = bond_item
		# save endpoint references for undo restore
		self._atom1 = bond_model.atom1
		self._atom2 = bond_model.atom2

	#============================================
	def redo(self) -> None:
		"""Remove the bond from the molecule model and scene."""
		self._scene.removeItem(self._bond_item)
		self._molecule_model.remove_bond(self._bond_model)

	#============================================
	def undo(self) -> None:
		"""Restore the bond in the molecule model and scene."""
		if self._atom1 is not None and self._atom2 is not None:
			self._molecule_model.add_bond(
				self._atom1, self._atom2, self._bond_model,
			)
		self._scene.addItem(self._bond_item)


#============================================
class MoveAtomsCommand(PySide6.QtGui.QUndoCommand):
	"""Undo command for moving atoms, with merge support for continuous drags.

	Consecutive MoveAtomsCommand instances with the same merge ID are
	merged into a single undo step so that a long drag does not create
	many undo entries.

	Args:
		items_and_offsets: List of (AtomItem, dx, dy) tuples describing
			the atoms moved and their offsets.
		text: Description shown in the undo history.
	"""

	_MERGE_ID = 1001

	#============================================
	def __init__(self, items_and_offsets: list, text: str = "Move Atoms"):
		"""Initialize the move atoms command.

		Args:
			items_and_offsets: List of (AtomItem, dx, dy) tuples.
			text: Undo history description.
		"""
		super().__init__(text)
		# store as list of (atom_item, dx, dy)
		self._items_and_offsets = list(items_and_offsets)
		# flag to skip redo on first push (items already moved)
		self._first_redo = True

	#============================================
	def id(self) -> int:
		"""Return the merge ID for this command type.

		Returns:
			Integer merge identifier.
		"""
		return self._MERGE_ID

	#============================================
	def mergeWith(self, other) -> bool:
		"""Merge another MoveAtomsCommand into this one.

		Combines the offsets when the same atoms are moved in
		consecutive commands.

		Args:
			other: Another QUndoCommand to merge with.

		Returns:
			True if the merge succeeded, False otherwise.
		"""
		if not isinstance(other, MoveAtomsCommand):
			return False
		# build a lookup from atom item to index in our list
		item_index = {}
		for idx, (atom_item, _dx, _dy) in enumerate(self._items_and_offsets):
			item_index[id(atom_item)] = idx
		# merge offsets from the other command
		for atom_item, dx, dy in other._items_and_offsets:
			key = id(atom_item)
			if key in item_index:
				idx = item_index[key]
				old_item, old_dx, old_dy = self._items_and_offsets[idx]
				self._items_and_offsets[idx] = (old_item, old_dx + dx, old_dy + dy)
			else:
				self._items_and_offsets.append((atom_item, dx, dy))
		return True

	#============================================
	def redo(self) -> None:
		"""Move atoms by their offsets.

		Skips the first redo call because the items were already moved
		during the drag interaction.
		"""
		if self._first_redo:
			self._first_redo = False
			return
		for atom_item, dx, dy in self._items_and_offsets:
			model = atom_item.atom_model
			model.x = model.x + dx
			model.y = model.y + dy

	#============================================
	def undo(self) -> None:
		"""Move atoms back by the negative of their offsets."""
		for atom_item, dx, dy in self._items_and_offsets:
			model = atom_item.atom_model
			model.x = model.x - dx
			model.y = model.y - dy


#============================================
class ChangePropertyCommand(PySide6.QtGui.QUndoCommand):
	"""Generic property change undo command.

	Stores the old and new values for a named property on a model
	object and applies or reverts the change using ``setattr``.

	Args:
		model: The model object whose property is being changed.
		property_name: Name of the property to set.
		old_value: Previous value (for undo).
		new_value: New value (for redo).
		text: Description shown in the undo history.
	"""

	#============================================
	def __init__(self, model, property_name: str, old_value, new_value,
				 text: str = "Change Property"):
		"""Initialize the change property command.

		Args:
			model: The model object to modify.
			property_name: Attribute name to set.
			old_value: Value before the change.
			new_value: Value after the change.
			text: Undo history description.
		"""
		super().__init__(text)
		self._model = model
		self._property_name = property_name
		self._old_value = old_value
		self._new_value = new_value

	#============================================
	def redo(self) -> None:
		"""Apply the new property value."""
		setattr(self._model, self._property_name, self._new_value)

	#============================================
	def undo(self) -> None:
		"""Revert to the old property value."""
		setattr(self._model, self._property_name, self._old_value)
