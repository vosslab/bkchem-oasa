"""Help menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction


#============================================
def register_help_actions(registry, app) -> None:
	"""Register all Help menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing the about dialog.
	"""
	# show general information about BKChem
	registry.register(MenuAction(
		id='help.about',
		label_key='About',
		help_key='General information about BKChem',
		accelerator=None,
		handler=app.about,
		enabled_when=None,
	))
