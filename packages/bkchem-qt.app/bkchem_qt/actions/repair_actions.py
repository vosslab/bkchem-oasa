"""Repair menu action registrations for BKChem-Qt."""

# Standard Library
import math

# local repo modules
from oasa import repair_ops
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.config.geometry_units
import bkchem_qt.models.molecule_model
import bkchem_qt.undo.commands
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _resolve_target_bond_length_pt(app: object) -> float:
	"""Resolve canonical target bond length in scene-space points."""
	scene = getattr(app, "_scene", None)
	if scene is not None and hasattr(scene, "grid_spacing_pt"):
		return float(scene.grid_spacing_pt)
	return bkchem_qt.config.geometry_units.DEFAULT_BOND_LENGTH_PT


#============================================
def _get_target_mols_and_items(
		app: object,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		) -> list:
	"""Get molecules to operate on and their AtomItem mappings.

	Uses an explicit target when supplied, otherwise selected top-level
	molecules, and finally all document molecules. Builds a mapping from
	AtomModel identity to the
	corresponding AtomItem in the scene for each molecule.

	Args:
		app: The main BKChem-Qt application object.
		target_molecule: Optional molecule supplied by an interaction mode.

	Returns:
		List of (MoleculeModel, {AtomModel_id: AtomItem}) pairs.
		Empty list when no molecules are available.
	"""
	if target_molecule is not None:
		mols = [target_molecule]
	else:
		mols = [
			object_model for object_model in app.document.selected_top_level_objects
			if isinstance(
				object_model,
				bkchem_qt.models.molecule_model.MoleculeModel,
			)
		]
	if not mols:
		mols = app.document.molecules
	if not mols:
		return []
	# build AtomModel id -> AtomItem mapping from scene
	atom_item_map = {}
	for item in app._scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			atom_item_map[id(item.atom_model)] = item
	result = []
	for mol in mols:
		mol_items = {}
		for am in mol.atoms:
			ai = atom_item_map.get(id(am))
			if ai is not None:
				mol_items[id(am)] = ai
		result.append((mol, mol_items))
	return result


#============================================
class _RepairMoveAtomsCommand(bkchem_qt.undo.commands.MoveAtomsCommand):
	"""Keep one complete repair operation as one undo history entry."""

	#============================================
	def id(self) -> int:
		"""Disable drag-command merging for a discrete repair action."""
		return -1


#============================================
def _apply_moves_with_undo(
		app: object, items_and_offsets: list, description: str,
		) -> None:
	"""Push a MoveAtomsCommand to the undo stack for a batch of atom moves.

	The atoms have already been moved in-place before this call. The
	command records the offsets so undo can reverse them.

	Args:
		app: The main BKChem-Qt application object.
		items_and_offsets: List of (AtomItem, dx, dy) tuples.
		description: Text label for the undo history entry.
	"""
	if not items_and_offsets:
		return
	cmd = _RepairMoveAtomsCommand(
		items_and_offsets, text=description,
	)
	# first redo is skipped because atoms are already at new positions
	app.document.undo_stack.push(cmd)


#============================================
def _apply_oasa_repair(
		app: object, operation: object, description: str, success_message: str,
		needs_bond_length: bool = True,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		) -> None:
	"""Run one OASA repair operation and commit its coordinate delta once.

	The OASA bridge creates an isolated graph, so repair algorithms can move
	whole substituent subtrees without altering the live document until their
	complete result is available.  The bridge preserves atom order, which
	provides a stable one-to-one coordinate mapping back to the Qt wrappers.

	Args:
		app: Main window exposing the active document and scene.
		operation: OASA repair function operating on one molecule.
		description: Undo-stack label for this repair operation.
		success_message: Status-bar format string with one atom-count field.
		needs_bond_length: Whether ``operation`` takes the scene bond length.
		target_molecule: Optional molecule supplied by an interaction mode.
	"""
	targets = _get_target_mols_and_items(app, target_molecule)
	if not targets:
		app.statusBar().showMessage("No molecules to repair", 3000)
		return
	for mol_model, mol_items in targets:
		if len(mol_items) != len(mol_model.atoms):
			app.statusBar().showMessage(
				"Repair requires every target atom to be projected", 5000
			)
			return
	target_bond_length_pt = _resolve_target_bond_length_pt(app)
	all_offsets = []
	for mol_model, mol_items in targets:
		if not mol_model.atoms:
			continue
		oasa_mol = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(mol_model)
		if needs_bond_length:
			operation(oasa_mol, target_bond_length_pt)
		else:
			operation(oasa_mol)
		for atom_model, repaired_atom in zip(mol_model.atoms, oasa_mol.atoms):
			old_x = atom_model.x
			old_y = atom_model.y
			new_x = repaired_atom.x
			new_y = repaired_atom.y
			dx = new_x - old_x
			dy = new_y - old_y
			if abs(dx) < 0.01 and abs(dy) < 0.01:
				continue
			atom_model.x = new_x
			atom_model.y = new_y
			all_offsets.append((mol_items[id(atom_model)], dx, dy))
	_apply_moves_with_undo(app, all_offsets, description)
	message = success_message.format(len(all_offsets))
	app.statusBar().showMessage(message, 3000)


#============================================
def _submit_geometry_repair(
		app: object, kind: str, label: str, unavailable_message: str,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		target_molecule_id: str | None = None,
		) -> None:
	"""Submit one immutable geometry repair through its owning session.

	The helper converts projection state to durable molecule identifiers before
	calling the synchronous backend boundary.  It intentionally drops all Qt
	projection wrappers before that call because an accepted commit replaces the
	complete projection.
	"""
	if target_molecule is not None and target_molecule_id is not None:
		raise ValueError("Geometry repair accepts one target representation")
	session = getattr(app, "_active_session", None)
	document = getattr(app, "document", None)
	scene = getattr(app, "_scene", None)
	view = getattr(app, "_view", None)
	if (
		session is None
		or document is None
		or scene is None
		or view is None
		or session.is_disposed
		or session.document is not document
		or session.scene is not scene
		or session.view is not view
	):
		app.statusBar().showMessage(unavailable_message, 5000)
		return
	if target_molecule_id is not None:
		molecule_ids = (target_molecule_id,)
	elif target_molecule is not None:
		molecule_ids = (target_molecule.mol_id,)
	else:
		selected = tuple(
			object_model for object_model in document.selected_top_level_objects
			if isinstance(object_model, bkchem_qt.models.molecule_model.MoleculeModel)
		)
		molecules = selected or tuple(document.molecules)
		molecule_ids = tuple(molecule.mol_id for molecule in molecules)
		del selected
		del molecules
	if (
		not molecule_ids
		or any(not isinstance(identifier, str) or not identifier for identifier in molecule_ids)
		or len(set(molecule_ids)) != len(molecule_ids)
	):
		app.statusBar().showMessage(
			"%s needs backend-identified molecules" % label, 5000,
		)
		return
	target_spacing_pt = _resolve_target_bond_length_pt(app)
	if not math.isfinite(target_spacing_pt) or target_spacing_pt <= 0:
		app.statusBar().showMessage("Geometry repair needs a finite grid spacing", 5000)
		return
	snapshot = session.backend_snapshot
	try:
		submit = app.persistent_operation_capability_for(session)
	except ValueError:
		app.statusBar().showMessage(unavailable_message, 5000)
		return
	from bkchem_qt.models.document_session import PersistentOperationRequest
	request = PersistentOperationRequest(
		"geometry.repair", label,
		(
			("expected_revision", snapshot.revision),
			("molecule_ids", molecule_ids),
			("kind", kind),
			("target_spacing_pt", target_spacing_pt),
		),
		frozenset(("molecule", identifier) for identifier in molecule_ids),
	)
	# The request and capability are plain/durable.  Release every old Qt
	# projection wrapper before accepting a replacement projection.
	del target_molecule
	del document
	del scene
	del view
	outcome = submit(request)
	app.statusBar().showMessage(outcome.message, 5000)


#============================================
def _handle_clean_geometry(
		app: object,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		target_molecule_id: str | None = None,
		) -> None:
	"""Submit clean geometry through the authoritative backend session."""
	_submit_geometry_repair(
		app, "clean-geometry", "Clean up geometry", "Clean geometry is unavailable",
		target_molecule, target_molecule_id,
	)


#============================================
def _handle_normalize_bond_lengths(
		app: object,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		target_molecule_id: str | None = None,
		) -> None:
	"""Normalize durable molecules through the authoritative backend session."""
	_submit_geometry_repair(
		app, "normalize-bond-lengths", "Normalize bond lengths",
		"Normalize bond lengths is unavailable", target_molecule, target_molecule_id,
	)


#============================================
def _handle_snap_to_hex_grid(
		app: object,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		target_molecule_id: str | None = None,
		) -> None:
	"""Snap durable molecules to the backend-owned hexagonal grid."""
	_submit_geometry_repair(
		app, "snap-to-hex-grid", "Snap to hex grid", "Snap to hex grid is unavailable",
		target_molecule, target_molecule_id,
	)


#============================================
def _handle_normalize_bond_angles(
		app: object,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		target_molecule_id: str | None = None,
		) -> None:
	"""Normalize durable molecules through the authoritative backend session."""
	_submit_geometry_repair(
		app, "normalize-bond-angles", "Normalize bond angles",
		"Normalize bond angles is unavailable", target_molecule, target_molecule_id,
	)


#============================================
def _handle_normalize_rings(
		app: object,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		) -> None:
	"""Normalize rings with OASA while retaining attached substituents."""
	_apply_oasa_repair(
		app, repair_ops.normalize_rings, "Normalize ring structures",
		"Normalized rings for {} atoms", target_molecule=target_molecule,
	)


#============================================
def _handle_straighten_bonds(
		app: object,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		) -> None:
	"""Straighten terminal bonds with OASA's shared repair algorithm."""
	_apply_oasa_repair(
		app, repair_ops.straighten_bonds, "Straighten bonds",
		"Straightened {} terminal bonds", needs_bond_length=False,
		target_molecule=target_molecule,
	)


#============================================
def register_repair_actions(registry: object, app: object) -> None:
	"""Register all Repair menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# predicate: true when the document has any molecules to repair
	def has_molecules() -> bool:
		"""Check whether the document contains any molecules."""
		return app.document is not None and bool(app.document.molecules)

	# set all bonds to the standard bond length
	registry.register(MenuAction(
		id='repair.normalize_bond_lengths',
		label_key='Normalize bond lengths',
		help_key='Set all bonds to the standard bond length',
		accelerator=None,
		handler=lambda: _handle_normalize_bond_lengths(app),
		enabled_when=has_molecules,
	))

	# move every atom to the nearest hex grid point
	registry.register(MenuAction(
		id='repair.snap_to_hex_grid',
		label_key='Snap to hex grid',
		help_key='Move every atom to the nearest hex grid point',
		accelerator=None,
		handler=lambda: _handle_snap_to_hex_grid(app),
		enabled_when=has_molecules,
	))

	# round bond angles to nearest 60-degree multiple
	registry.register(MenuAction(
		id='repair.normalize_bond_angles',
		label_key='Normalize bond angles',
		help_key='Round bond angles to nearest 60-degree multiple',
		accelerator=None,
		handler=lambda: _handle_normalize_bond_angles(app),
		enabled_when=has_molecules,
	))

	# reshape each ring to a regular polygon
	registry.register(MenuAction(
		id='repair.normalize_rings',
		label_key='Normalize ring structures',
		help_key='Reshape each ring to a regular polygon',
		accelerator=None,
		handler=lambda: _handle_normalize_rings(app),
		enabled_when=has_molecules,
	))

	# snap terminal bonds to nearest 30-degree direction
	registry.register(MenuAction(
		id='repair.straighten_bonds',
		label_key='Straighten bonds',
		help_key='Snap terminal bonds to nearest 30-degree direction',
		accelerator=None,
		handler=lambda: _handle_straighten_bonds(app),
		enabled_when=has_molecules,
	))

	# full coordinate regeneration for selected or all molecules
	registry.register(MenuAction(
		id='repair.clean_geometry',
		label_key='Clean up geometry',
		help_key='Full coordinate regeneration for selected or all molecules',
		accelerator=None,
		handler=lambda: _handle_clean_geometry(app),
		enabled_when=has_molecules,
	))
