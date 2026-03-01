"""Help menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def register_help_actions(registry, app) -> None:
	"""Register all Help menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# show keyboard shortcut reference
	registry.register(MenuAction(
		id='help.keyboard_shortcuts',
		label_key='Keyboard Shortcuts',
		help_key='Show keyboard shortcut reference',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Keyboard Shortcuts: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# show general information about BKChem
	registry.register(MenuAction(
		id='help.about',
		label_key='About',
		help_key='General information about BKChem',
		accelerator=None,
		handler=app._on_about,
		enabled_when=None,
	))
