"""Repair menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def register_repair_actions(registry, app) -> None:
	"""Register all Repair menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# set all bonds to the standard bond length
	registry.register(MenuAction(
		id='repair.normalize_bond_lengths',
		label_key='Normalize bond lengths',
		help_key='Set all bonds to the standard bond length',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Normalize bond lengths: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# move every atom to the nearest hex grid point
	registry.register(MenuAction(
		id='repair.snap_to_hex_grid',
		label_key='Snap to hex grid',
		help_key='Move every atom to the nearest hex grid point',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Snap to hex grid: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# round bond angles to nearest 60-degree multiple
	registry.register(MenuAction(
		id='repair.normalize_bond_angles',
		label_key='Normalize bond angles',
		help_key='Round bond angles to nearest 60-degree multiple',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Normalize bond angles: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# reshape each ring to a regular polygon
	registry.register(MenuAction(
		id='repair.normalize_rings',
		label_key='Normalize ring structures',
		help_key='Reshape each ring to a regular polygon',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Normalize ring structures: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# snap terminal bonds to nearest 30-degree direction
	registry.register(MenuAction(
		id='repair.straighten_bonds',
		label_key='Straighten bonds',
		help_key='Snap terminal bonds to nearest 30-degree direction',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Straighten bonds: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# full coordinate regeneration for selected or all molecules
	registry.register(MenuAction(
		id='repair.clean_geometry',
		label_key='Clean up geometry',
		help_key='Full coordinate regeneration for selected or all molecules',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Clean up geometry: not yet implemented", 3000
		),
		enabled_when=None,
	))
