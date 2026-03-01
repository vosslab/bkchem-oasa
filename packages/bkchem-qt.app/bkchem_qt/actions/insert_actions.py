"""Insert menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def register_insert_actions(registry, app) -> None:
	"""Register all Insert menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# insert a biomolecule template into the drawing
	registry.register(MenuAction(
		id='insert.biomolecule_template',
		label_key='Biomolecule template',
		help_key='Insert a biomolecule template into the drawing',
		accelerator=None,
		handler=lambda: app._mode_manager.set_mode("biotemplate"),
		enabled_when=None,
	))
