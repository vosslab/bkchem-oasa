"""Repair menu action registrations for BKChem-Qt."""

# Standard Library
import math

# local repo modules
import bkchem_qt.config.geometry_units
import bkchem_qt.models.molecule_model
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _resolve_target_bond_length_pt(app: object) -> float:
	"""Resolve canonical target bond length in scene-space points."""
	scene = getattr(app, "_scene", None)
	if scene is not None and hasattr(scene, "grid_spacing_pt"):
		return float(scene.grid_spacing_pt)
	return bkchem_qt.config.geometry_units.DEFAULT_BOND_LENGTH_PT


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
		target_molecule_id: str | None = None,
		) -> None:
	"""Normalize eligible ring structures through the authoritative backend."""
	_submit_geometry_repair(
		app, "normalize-rings", "Normalize ring structures",
		"Normalize ring structures is unavailable", target_molecule, target_molecule_id,
	)


#============================================
def _handle_straighten_bonds(
		app: object,
		target_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
		target_molecule_id: str | None = None,
		) -> None:
	"""Straighten durable terminal bonds through the authoritative backend."""
	_submit_geometry_repair(
		app, "straighten-bonds", "Straighten bonds", "Straighten bonds is unavailable",
		target_molecule, target_molecule_id,
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
