"""Repair menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction

# these imports are needed for handler lambdas;
# they may not resolve in isolated test environments
try:
	from bkchem import repair_ops
except ImportError:
	repair_ops = None


#============================================
def register_repair_actions(registry, app) -> None:
	"""Register all Repair menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing paper and repair methods.
	"""
	# normalize all bond lengths to the standard length
	registry.register(MenuAction(
		id='repair.normalize_bond_lengths',
		label_key='Normalize bond lengths',
		help_key='Set all bonds to the standard bond length',
		accelerator=None,
		handler=lambda: repair_ops.normalize_bond_lengths(app.paper),
		enabled_when=None,
	))
	# snap every atom to the nearest hex grid point
	registry.register(MenuAction(
		id='repair.snap_to_hex_grid',
		label_key='Snap to hex grid',
		help_key='Move every atom to the nearest hex grid point',
		accelerator=None,
		handler=lambda: repair_ops.snap_to_hex_grid(app.paper),
		enabled_when=None,
	))
	# round non-ring bond angles to nearest 60-degree multiple
	registry.register(MenuAction(
		id='repair.normalize_bond_angles',
		label_key='Normalize bond angles',
		help_key='Round bond angles to nearest 60-degree multiple',
		accelerator=None,
		handler=lambda: repair_ops.normalize_bond_angles(app.paper),
		enabled_when=None,
	))
	# reshape rings to regular polygons
	registry.register(MenuAction(
		id='repair.normalize_rings',
		label_key='Normalize ring structures',
		help_key='Reshape each ring to a regular polygon',
		accelerator=None,
		handler=lambda: repair_ops.normalize_rings(app.paper),
		enabled_when=None,
	))
	# snap terminal bond angles to nearest 30-degree direction
	registry.register(MenuAction(
		id='repair.straighten_bonds',
		label_key='Straighten bonds',
		help_key='Snap terminal bonds to nearest 30-degree direction',
		accelerator=None,
		handler=lambda: repair_ops.straighten_bonds(app.paper),
		enabled_when=None,
	))
	# full coordinate regeneration
	registry.register(MenuAction(
		id='repair.clean_geometry',
		label_key='Clean up geometry',
		help_key='Full coordinate regeneration for selected or all molecules',
		accelerator=None,
		handler=lambda: repair_ops.clean_geometry(app.paper),
		enabled_when=None,
	))
