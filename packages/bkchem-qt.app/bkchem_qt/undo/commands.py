"""QUndoCommand subclasses for undo/redo support."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.document
import bkchem_qt.models.document_object
import bkchem_qt.models.fragment_model
import bkchem_qt.models.molecule_model


#============================================
def dispose_undo_stack_graphics(
		undo_stack: PySide6.QtGui.QUndoStack, seen: set | None = None,
		) -> None:
	"""Disconnect graphics retained only by commands before clearing a stack.

	Args:
		undo_stack: Stack whose commands may retain off-scene graphics items.
		seen: Optional item-identity set already disposed from the live scene.
	"""
	from bkchem_qt.canvas.graphics_retirement import GraphicsRetirementCoordinator
	coordinator = GraphicsRetirementCoordinator()
	coordinator.dispose_undo_stack_graphics(undo_stack, seen)
	coordinator.raise_if_callback_failed(
		"Undo graphics were detached after a disposal failure",
	)


#============================================
def _dispose_command_graphics(
		command: PySide6.QtGui.QUndoCommand, seen: set, errors: list,
		) -> None:
	"""Compatibility shim for legacy direct callers.

	All production retirement routes use :class:`GraphicsRetirementCoordinator`.
	"""
	from bkchem_qt.canvas.graphics_retirement import GraphicsRetirementCoordinator
	coordinator = GraphicsRetirementCoordinator()
	coordinator._dispose_command_graphics(command, seen, False)
	errors.extend(coordinator.report.callback_errors)


#============================================
class AddFragmentCommand(PySide6.QtGui.QUndoCommand):
	"""Add immutable fragment metadata without changing the molecular graph."""

	#============================================
	def __init__(
			self, molecule_model: bkchem_qt.models.molecule_model.MoleculeModel,
			fragment: bkchem_qt.models.fragment_model.FragmentModel,
			atom_id_changes: tuple[tuple[object, str, str], ...] = (),
			bond_id_changes: tuple[tuple[object, str, str], ...] = (),
			text: str = "Create Fragment",
			) -> None:
		"""Capture metadata and its required deterministic ID normalization."""
		super().__init__(text)
		self._molecule_model = molecule_model
		self._fragment = fragment
		self._position = len(molecule_model.fragments)
		self._atom_id_changes = tuple(atom_id_changes)
		self._bond_id_changes = tuple(bond_id_changes)

	#============================================
	def redo(self) -> None:
		"""Apply stable IDs, then insert the fragment at its original position."""
		self._apply_ids(after=True)
		self._molecule_model.insert_fragment(self._position, self._fragment)

	#============================================
	def undo(self) -> None:
		"""Remove metadata and restore every prior atom and bond ID exactly."""
		self._molecule_model.remove_fragment(self._fragment.fragment_id)
		self._apply_ids(after=False)

	#============================================
	def _apply_ids(self, after: bool) -> None:
		"""Apply the captured ID plan without changing graph topology."""
		for model, before, after_value in self._atom_id_changes:
			chemistry = model._chem_atom
			chemistry.id = after_value if after else before
		for model, before, after_value in self._bond_id_changes:
			chemistry = model._chem_bond
			chemistry.id = after_value if after else before


#============================================
class RemoveFragmentCommand(PySide6.QtGui.QUndoCommand):
	"""Remove editable fragment metadata without changing the molecular graph."""

	#============================================
	def __init__(
			self, molecule_model: bkchem_qt.models.molecule_model.MoleculeModel,
			fragment_id: str,
			text: str = "Remove Fragment",
			) -> None:
		"""Capture the exact fragment and its durable list position."""
		super().__init__(text)
		self._molecule_model = molecule_model
		for position, fragment in enumerate(molecule_model.fragments):
			if fragment.fragment_id == fragment_id:
				self._position = position
				self._fragment = fragment
				break
		else:
			raise ValueError("fragment ID is not editable metadata for this molecule")

	#============================================
	def redo(self) -> None:
		"""Remove the captured metadata from its owning molecule."""
		self._molecule_model.remove_fragment(self._fragment.fragment_id)

	#============================================
	def undo(self) -> None:
		"""Restore the exact immutable metadata at its original position."""
		self._molecule_model.insert_fragment(self._position, self._fragment)


#============================================
class AddMoleculeCommand(PySide6.QtGui.QUndoCommand):
	"""Add or remove one complete molecule and its graphics atomically.

	Args:
		document: Document that owns the MoleculeModel.
		scene: QGraphicsScene that owns the molecule's graphics items.
		molecule_model: MoleculeModel being inserted.
		graphics_items: Fully constructed graphics items for the molecule.
		text: Description shown in the undo history.
	"""

	#============================================
	def __init__(
			self, document: bkchem_qt.models.document.Document,
			scene: PySide6.QtWidgets.QGraphicsScene,
			molecule_model: bkchem_qt.models.molecule_model.MoleculeModel,
			graphics_items: list[PySide6.QtWidgets.QGraphicsItem],
			text: str = "Add Molecule",
			index: int | None = None,
			) -> None:
		"""Initialize a complete-molecule structural command."""
		super().__init__(text)
		self._document = document
		self._scene = scene
		self._molecule_model = molecule_model
		self._graphics_items = list(graphics_items)
		self._stack_index = index

	#============================================
	def redo(self) -> None:
		"""Add the molecule model and all of its graphics items."""
		self._document.add_molecule(
			self._molecule_model,
			mark_dirty=False,
			index=self._stack_index,
		)
		for item in self._graphics_items:
			self._scene.addItem(item)

	#============================================
	def undo(self) -> None:
		"""Remove all graphics items and the molecule model."""
		for item in reversed(self._graphics_items):
			self._scene.removeItem(item)
		self._document.remove_molecule(self._molecule_model, mark_dirty=False)

	#============================================
	def graphics_items(self) -> list:
		"""Return graphics retained by this command across undo states."""
		return list(self._graphics_items)


#============================================
class RemoveMoleculeCommand(PySide6.QtGui.QUndoCommand):
	"""Remove one complete molecule and retain its scene projection for undo."""

	#============================================
	def __init__(
			self, document: bkchem_qt.models.document.Document,
			scene: PySide6.QtWidgets.QGraphicsScene,
			molecule_model: bkchem_qt.models.molecule_model.MoleculeModel,
			graphics_items: list[PySide6.QtWidgets.QGraphicsItem],
			text: str = "Remove Molecule",
			) -> None:
		"""Capture a molecule and its original canonical stack position."""
		super().__init__(text)
		self._document = document
		self._scene = scene
		self._molecule_model = molecule_model
		self._graphics_items = list(graphics_items)
		self._stack_index = document.object_index(molecule_model)

	#============================================
	def redo(self) -> None:
		"""Detach molecule graphics and remove the model from its document."""
		for item in reversed(self._graphics_items):
			if item.scene() is self._scene:
				self._scene.removeItem(item)
		self._document.remove_molecule(self._molecule_model, mark_dirty=False)
		self._document._synchronize_scene_object_stack()

	#============================================
	def undo(self) -> None:
		"""Restore molecule ownership, graphics, and its original stack slot."""
		self._document.insert_molecule(
			self._molecule_model,
			index=self._stack_index,
			mark_dirty=False,
		)
		for item in self._graphics_items:
			if item.scene() is not self._scene:
				self._scene.addItem(item)
		self._document._synchronize_scene_object_stack()

	#============================================
	def graphics_items(self) -> list:
		"""Return graphics retained by this command across undo states."""
		return list(self._graphics_items)


#============================================
class AddPresentationObjectCommand(PySide6.QtGui.QUndoCommand):
	"""Add one document-owned presentation model and its scene projection."""

	#============================================
	def __init__(
			self,
			document: bkchem_qt.models.document.Document,
			scene: PySide6.QtWidgets.QGraphicsScene,
			object_model: bkchem_qt.models.document_object.PresentationObject,
			graphics_item: PySide6.QtWidgets.QGraphicsItem,
			text: str = "Add Drawing Object",
			) -> None:
		"""Initialize an atomic presentation-object insertion."""
		super().__init__(text)
		self._document = document
		self._scene = scene
		self._object_model = object_model
		self._graphics_item = graphics_item

	#============================================
	def redo(self) -> None:
		"""Add the persistent model and its scene projection."""
		self._document.add_presentation_object(
			self._object_model, mark_dirty=False,
		)
		if self._graphics_item.scene() is not self._scene:
			self._scene.addItem(self._graphics_item)

	#============================================
	def undo(self) -> None:
		"""Remove the scene projection and its persistent model."""
		if self._graphics_item.scene() is self._scene:
			self._scene.removeItem(self._graphics_item)
		self._document.remove_presentation_object(
			self._object_model, mark_dirty=False,
		)

	#============================================
	def graphics_items(self) -> list:
		"""Return the graphics item retained across undo states."""
		return [self._graphics_item]


#============================================
class RemovePresentationObjectCommand(PySide6.QtGui.QUndoCommand):
	"""Remove one presentation object while retaining its projection for undo."""

	#============================================
	def __init__(
			self,
			document: bkchem_qt.models.document.Document,
			scene: PySide6.QtWidgets.QGraphicsScene,
			object_model: bkchem_qt.models.document_object.PresentationObject,
			graphics_item: PySide6.QtWidgets.QGraphicsItem,
			text: str = "Remove Drawing Object",
			) -> None:
		"""Capture a document-owned object and its original stack position.

		Args:
			document: Document that owns ``object_model`` before the command runs.
			scene: Scene that currently owns ``graphics_item``.
			object_model: Persistent presentation model to remove.
			graphics_item: Existing Qt projection retained for undo.
			text: Description shown in undo history.
		"""
		super().__init__(text)
		self._document = document
		self._scene = scene
		self._object_model = object_model
		self._graphics_item = graphics_item
		self._stack_index = document.object_index(object_model)

	#============================================
	def redo(self) -> None:
		"""Detach the projection and remove the persistent object."""
		if self._graphics_item.scene() is self._scene:
			self._scene.removeItem(self._graphics_item)
		self._document.remove_presentation_object(
			self._object_model, mark_dirty=False,
		)
		self._document._synchronize_scene_object_stack()

	#============================================
	def undo(self) -> None:
		"""Restore the same model and projection at their original position."""
		self._document.insert_presentation_object(
			self._object_model,
			index=self._stack_index,
			mark_dirty=False,
		)
		if self._graphics_item.scene() is not self._scene:
			self._scene.addItem(self._graphics_item)
		self._document._synchronize_scene_object_stack()

	#============================================
	def graphics_items(self) -> list:
		"""Return the projection retained by this command across undo states."""
		return [self._graphics_item]


#============================================
class MovePresentationObjectsCommand(PySide6.QtGui.QUndoCommand):
	"""Apply precomputed presentation geometry without movable scene items.

	The model is authoritative for presentation geometry.  Interaction code
	captures both states after a drag and pushes this command; item projections
	refresh through their existing model signal bindings.
	"""

	#============================================
	def __init__(
			self,
			changes: list[
				tuple[
					bkchem_qt.models.document_object.PresentationObject,
					tuple[
						list[tuple[float, float, float | None]],
						tuple[float, float, float, float] | None,
					],
					tuple[
						list[tuple[float, float, float | None]],
						tuple[float, float, float, float] | None,
					],
				],
			],
			text: str = "Move Drawing Objects",
			) -> None:
		"""Initialize model geometry snapshots for an undoable move.

		Args:
			changes: ``(model, before, after)`` triples.  Each geometry state is
				``(points, bounds)`` and is copied to isolate it from later drags.
			text: Description shown in undo history.
		"""
		super().__init__(text)
		self._changes = [
			(
				object_model,
				(list(before_points), tuple(before_bounds) if before_bounds is not None else None),
				(list(after_points), tuple(after_bounds) if after_bounds is not None else None),
			)
			for object_model, (before_points, before_bounds), (after_points, after_bounds)
			in changes
		]

	#============================================
	def redo(self) -> None:
		"""Apply the captured post-drag geometry through presentation models."""
		self._apply_geometry(after=True)

	#============================================
	def undo(self) -> None:
		"""Restore the captured pre-drag geometry through presentation models."""
		self._apply_geometry(after=False)

	#============================================
	def _apply_geometry(self, after: bool) -> None:
		"""Apply one stored geometry side to every affected presentation model."""
		for object_model, before_geometry, after_geometry in self._changes:
			points, bounds = after_geometry if after else before_geometry
			object_model.set_points(points)
			object_model.set_bounds(bounds)


#============================================
class TransformGeometryCommand(PySide6.QtGui.QUndoCommand):
	"""Apply one complete model-space geometry change without command merging.

	A discrete interaction can affect atom coordinates and presentation
	objects together. This command holds both states and applies them only
	through document models, leaving item projections to their signal bindings.
	"""

	#============================================
	def __init__(
			self,
			atom_changes: list[
				tuple[
					bkchem_qt.models.atom_model.AtomModel,
					tuple[float, float], tuple[float, float],
				]
			],
			presentation_changes: list[
				tuple[
					bkchem_qt.models.document_object.PresentationObject,
					tuple[
						list[tuple[float, float, float | None]],
						tuple[float, float, float, float] | None,
					],
					tuple[
						list[tuple[float, float, float | None]],
						tuple[float, float, float, float] | None,
					],
				]
			],
			text: str = "Transform Objects",
			) -> None:
		"""Capture complete before/after geometry for a discrete action."""
		super().__init__(text)
		self._atom_changes = [
			(atom_model, tuple(before), tuple(after))
			for atom_model, before, after in atom_changes
		]
		self._presentation_changes = [
			(
				object_model,
				(list(before_points), tuple(before_bounds) if before_bounds is not None else None),
				(list(after_points), tuple(after_bounds) if after_bounds is not None else None),
			)
			for object_model, (before_points, before_bounds), (after_points, after_bounds)
			in presentation_changes
		]
		self._fragment_changes = self._linear_fragment_changes()

	#============================================
	def redo(self) -> None:
		"""Apply the captured post-transform model state."""
		self._apply(after=True)

	#============================================
	def undo(self) -> None:
		"""Restore the captured pre-transform model state."""
		self._apply(after=False)

	#============================================
	def _apply(self, after: bool) -> None:
		"""Apply matching atom and presentation snapshots as one command."""
		for atom_model, before, after_state in self._atom_changes:
			x, y = after_state if after else before
			atom_model.x = x
			atom_model.y = y
		for object_model, before, after_state in self._presentation_changes:
			points, bounds = after_state if after else before
			object_model.set_points(points)
			object_model.set_bounds(bounds)
		for molecule_model, before_fragments, after_fragments in self._fragment_changes:
			fragments = after_fragments if after else before_fragments
			molecule_model.restore_fragment_snapshot(fragments)

	#============================================
	def _linear_fragment_changes(self) -> list[tuple[object, tuple, tuple]]:
		"""Capture lifecycle snapshots for linear metadata touched by geometry."""
		coordinates_by_molecule = {}
		for atom_model, _before, after in self._atom_changes:
			molecule_model = getattr(atom_model, "_molecule_model", None)
			if molecule_model is None:
				continue
			coordinates = coordinates_by_molecule.setdefault(molecule_model, {})
			coordinates[atom_model] = after
		changes = []
		for molecule_model, coordinates in coordinates_by_molecule.items():
			before_fragments = molecule_model.fragment_snapshot()
			after_fragments = molecule_model.linear_fragment_snapshot_after_geometry(
				coordinates,
			)
			if after_fragments != before_fragments:
				changes.append((molecule_model, before_fragments, after_fragments))
		return changes


#============================================
class ReorderDocumentObjectsCommand(PySide6.QtGui.QUndoCommand):
	"""Replace document stack order using the model's identity validation."""

	#============================================
	def __init__(
			self,
			document: bkchem_qt.models.document.Document,
			ordered_objects: list,
			text: str = "Reorder Objects",
			) -> None:
		"""Capture old and requested stack orders before the command runs.

		``Document.replace_object_order`` validates both redo and undo by object
		identity and synchronizes all projected z values after every transition.

		Args:
			document: Document whose complete top-level stack is reordered.
			ordered_objects: New complete object order.
			text: Description shown in undo history.
		"""
		super().__init__(text)
		self._document = document
		self._before_order = document.objects
		self._after_order = list(ordered_objects)
		document.replace_object_order(self._after_order, mark_dirty=False)
		document.replace_object_order(self._before_order, mark_dirty=False)

	#============================================
	def redo(self) -> None:
		"""Apply the requested identity-validated object order and z values."""
		self._document.replace_object_order(self._after_order, mark_dirty=False)

	#============================================
	def undo(self) -> None:
		"""Restore the original identity-validated object order and z values."""
		self._document.replace_object_order(self._before_order, mark_dirty=False)


#============================================
class AddAtomMarkCommand(PySide6.QtGui.QUndoCommand):
	"""Add one atom-attached mark model and child graphics item."""

	#============================================
	def __init__(
			self,
			document: bkchem_qt.models.document.Document,
			mark_model: bkchem_qt.models.document_object.AtomMarkModel,
			mark_item: PySide6.QtWidgets.QGraphicsItem,
			parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			text: str = "Add Atom Mark",
			) -> None:
		"""Initialize an atomic atom-mark insertion."""
		super().__init__(text)
		self._document = document
		self._mark_model = mark_model
		self._mark_item = mark_item
		self._parent_atom_item = parent_atom_item

	#============================================
	def redo(self) -> None:
		"""Attach the mark model and projection to its atom."""
		self._document.add_mark(self._mark_model, mark_dirty=False)
		self._mark_item.setParentItem(self._parent_atom_item)

	#============================================
	def undo(self) -> None:
		"""Detach the mark projection and remove its persistent model."""
		scene = self._mark_item.scene()
		self._mark_item.setParentItem(None)
		if scene is not None:
			scene.removeItem(self._mark_item)
		self._document.remove_mark(self._mark_model, mark_dirty=False)

	#============================================
	def graphics_items(self) -> list:
		"""Return the mark item retained across undo states."""
		return [self._mark_item]


#============================================
class RemoveAtomMarkCommand(PySide6.QtGui.QUndoCommand):
	"""Remove one atom-attached mark while retaining it for undo."""

	#============================================
	def __init__(
			self,
			document: bkchem_qt.models.document.Document,
			mark_model: bkchem_qt.models.document_object.AtomMarkModel,
			mark_item: PySide6.QtWidgets.QGraphicsItem,
			parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			text: str = "Remove Atom Mark",
			) -> None:
		"""Initialize an atomic atom-mark removal."""
		super().__init__(text)
		self._document = document
		self._mark_model = mark_model
		self._mark_item = mark_item
		self._parent_atom_item = parent_atom_item

	#============================================
	def redo(self) -> None:
		"""Detach the mark projection and remove its persistent model."""
		scene = self._mark_item.scene()
		self._mark_item.setParentItem(None)
		if scene is not None:
			scene.removeItem(self._mark_item)
		self._document.remove_mark(self._mark_model, mark_dirty=False)

	#============================================
	def undo(self) -> None:
		"""Restore the mark model and attach its projection to the atom."""
		self._document.add_mark(self._mark_model, mark_dirty=False)
		self._mark_item.setParentItem(self._parent_atom_item)

	#============================================
	def graphics_items(self) -> list:
		"""Return the mark item retained across undo states."""
		return [self._mark_item]


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
	def __init__(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			molecule_model: bkchem_qt.models.molecule_model.MoleculeModel,
			atom_model: bkchem_qt.models.atom_model.AtomModel,
			atom_item: bkchem_qt.canvas.items.atom_item.AtomItem,
			text: str = "Add Atom",
			) -> None:
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
		self._fragments_before = molecule_model.fragment_snapshot()

	#============================================
	def redo(self) -> None:
		"""Add the atom to the molecule model and scene."""
		self._molecule_model.add_atom(self._atom_model)
		self._molecule_model.restore_fragment_snapshot(self._fragments_before)
		self._scene.addItem(self._atom_item)

	#============================================
	def undo(self) -> None:
		"""Remove the atom from the molecule model and scene."""
		self._scene.removeItem(self._atom_item)
		self._molecule_model.remove_atom(self._atom_model)

	#============================================
	def graphics_items(self) -> list:
		"""Return graphics retained by this command across undo states."""
		return [self._atom_item]


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
	def __init__(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			molecule_model: bkchem_qt.models.molecule_model.MoleculeModel,
			atom_model: bkchem_qt.models.atom_model.AtomModel,
			atom_item: bkchem_qt.canvas.items.atom_item.AtomItem,
			connected_bonds: list[tuple[
				bkchem_qt.models.bond_model.BondModel,
				bkchem_qt.canvas.items.bond_item.BondItem,
			]],
			text: str = "Remove Atom",
			) -> None:
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
		# Removing a bond clears its wrapper endpoints. Preserve them before
		# the command's first redo so undo can rebuild the OASA graph exactly.
		self._bond_endpoints = [
			(bond_model.atom1, bond_model.atom2)
			for bond_model, _bond_item in self._connected_bonds
		]
		self._fragments_before = molecule_model.fragment_snapshot()

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
		for (bond_model, bond_item), (atom1, atom2) in zip(
				self._connected_bonds, self._bond_endpoints, strict=True,
		):
			if atom1 is not None and atom2 is not None:
				self._molecule_model.add_bond(atom1, atom2, bond_model)
			self._scene.addItem(bond_item)
		self._molecule_model.restore_fragment_snapshot(self._fragments_before)

	#============================================
	def graphics_items(self) -> list:
		"""Return graphics retained by this command across undo states."""
		return [
			self._atom_item,
			*(bond_item for _bond_model, bond_item in self._connected_bonds),
		]


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
	def __init__(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			molecule_model: bkchem_qt.models.molecule_model.MoleculeModel,
			bond_model: bkchem_qt.models.bond_model.BondModel,
			bond_item: bkchem_qt.canvas.items.bond_item.BondItem,
			text: str = "Add Bond",
			) -> None:
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
		self._fragments_before = molecule_model.fragment_snapshot()
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
		self._molecule_model.restore_fragment_snapshot(self._fragments_before)
		self._scene.addItem(self._bond_item)

	#============================================
	def undo(self) -> None:
		"""Remove the bond from the molecule model and scene."""
		self._scene.removeItem(self._bond_item)
		self._molecule_model.remove_bond(self._bond_model)

	#============================================
	def graphics_items(self) -> list:
		"""Return graphics retained by this command across undo states."""
		return [self._bond_item]


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
	def __init__(
			self, scene: PySide6.QtWidgets.QGraphicsScene,
			molecule_model: bkchem_qt.models.molecule_model.MoleculeModel,
			bond_model: bkchem_qt.models.bond_model.BondModel,
			bond_item: bkchem_qt.canvas.items.bond_item.BondItem,
			text: str = "Remove Bond",
			) -> None:
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
		self._fragments_before = molecule_model.fragment_snapshot()

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
		self._molecule_model.restore_fragment_snapshot(self._fragments_before)
		self._scene.addItem(self._bond_item)

	#============================================
	def graphics_items(self) -> list:
		"""Return graphics retained by this command across undo states."""
		return [self._bond_item]


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
	def __init__(self, items_and_offsets: list, text: str = "Move Atoms") -> None:
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
		self._fragment_changes = self._linear_fragment_changes()

	#============================================
	def id(self) -> int:
		"""Return the merge ID for this command type.

		Returns:
			Integer merge identifier.
		"""
		return self._MERGE_ID

	#============================================
	def mergeWith(self, other: PySide6.QtGui.QUndoCommand) -> bool:
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
			self._apply_fragment_snapshots(after=True)
			return
		for atom_item, dx, dy in self._items_and_offsets:
			model = atom_item.atom_model
			model.x = model.x + dx
			model.y = model.y + dy
		self._apply_fragment_snapshots(after=True)

	#============================================
	def undo(self) -> None:
		"""Move atoms back by the negative of their offsets."""
		for atom_item, dx, dy in self._items_and_offsets:
			model = atom_item.atom_model
			model.x = model.x - dx
			model.y = model.y - dy
		self._apply_fragment_snapshots(after=False)

	#============================================
	def _linear_fragment_changes(self) -> list[tuple[object, tuple, tuple]]:
		"""Capture post-drag removal snapshots for stale linear fragments."""
		molecules = []
		for atom_item, _dx, _dy in self._items_and_offsets:
			molecule_model = getattr(atom_item.atom_model, "_molecule_model", None)
			if molecule_model is not None and molecule_model not in molecules:
				molecules.append(molecule_model)
		changes = []
		for molecule_model in molecules:
			before_fragments = molecule_model.fragment_snapshot()
			after_fragments = molecule_model.linear_fragment_snapshot_after_geometry({})
			if after_fragments != before_fragments:
				changes.append((molecule_model, before_fragments, after_fragments))
		return changes

	#============================================
	def _apply_fragment_snapshots(self, after: bool) -> None:
		"""Restore the lifecycle snapshot paired with this drag command."""
		for molecule_model, before_fragments, after_fragments in self._fragment_changes:
			fragments = after_fragments if after else before_fragments
			molecule_model.restore_fragment_snapshot(fragments)

	#============================================
	def graphics_items(self) -> list:
		"""Return graphics retained by this command across undo states."""
		return [
			atom_item
			for atom_item, _dx, _dy in self._items_and_offsets
		]


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
	def __init__(self, model: object, property_name: str, old_value: object,
					new_value: object, text: str = "Change Property") -> None:
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
