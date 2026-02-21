"""Help menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction


#============================================
def _show_keyboard_shortcuts(app) -> None:
	"""Open the keyboard shortcuts reference dialog.

	Args:
		app: The main BKChem application object.
	"""
	from bkchem import dialogs
	dialogs.keyboard_shortcuts_dialog(app)


#============================================
def register_help_actions(registry, app) -> None:
	"""Register all Help menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing the about dialog.
	"""
	# show keyboard shortcuts reference
	registry.register(MenuAction(
		id='help.keyboard_shortcuts',
		label_key='Keyboard Shortcuts',
		help_key='Show keyboard shortcut reference',
		accelerator=None,
		handler=lambda: _show_keyboard_shortcuts(app),
		enabled_when=None,
	))
	# show general information about BKChem
	registry.register(MenuAction(
		id='help.about',
		label_key='About',
		help_key='General information about BKChem',
		accelerator=None,
		handler=app.about,
		enabled_when=None,
	))
