"""Options menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def register_options_actions(registry, app) -> None:
	"""Register all Options menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# set the default drawing style
	registry.register(MenuAction(
		id='options.standard',
		label_key='Standard',
		help_key='Set the default drawing style here',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Standard: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# set the language used after next restart
	registry.register(MenuAction(
		id='options.language',
		label_key='Language',
		help_key='Set the language used after next restart',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Language: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# set how messages in BKChem are displayed
	registry.register(MenuAction(
		id='options.logging',
		label_key='Logging',
		help_key='Set how messages in BKChem are displayed to you',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Logging: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# set the path to the InChI program
	registry.register(MenuAction(
		id='options.inchi_path',
		label_key='InChI program path',
		help_key='To use InChI in BKChem you must first give it a path to the InChI program here',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"InChI program path: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# choose a color theme
	registry.register(MenuAction(
		id='options.theme',
		label_key='Theme',
		help_key='Choose a color theme',
		accelerator=None,
		handler=app._on_choose_theme,
		enabled_when=None,
	))

	# open the preferences dialog
	registry.register(MenuAction(
		id='options.preferences',
		label_key='Preferences',
		help_key='Preferences',
		accelerator=None,
		handler=app._on_preferences,
		enabled_when=None,
	))
