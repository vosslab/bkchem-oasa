"""Options menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction

try:
	from bkchem import interactors
	from bkchem.singleton_store import Store
except ImportError:
	interactors = None
	Store = None


#============================================
def register_options_actions(registry, app) -> None:
	"""Register all Options menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing options and preferences methods.
	"""
	# set the default drawing style
	registry.register(MenuAction(
		id='options.standard',
		label_key='Standard',
		help_key='Set the default drawing style here',
		accelerator=None,
		handler=app.standard_values,
		enabled_when=None,
	))
	# set application language
	registry.register(MenuAction(
		id='options.language',
		label_key='Language',
		help_key='Set the language used after next restart',
		accelerator=None,
		handler=lambda: interactors.select_language(app.paper),
		enabled_when=None,
	))
	# configure message logging display
	registry.register(MenuAction(
		id='options.logging',
		label_key='Logging',
		help_key='Set how messages in BKChem are displayed to you',
		accelerator=None,
		handler=lambda: interactors.set_logging(app.paper, Store.logger),
		enabled_when=None,
	))
	# set path to InChI program
	registry.register(MenuAction(
		id='options.inchi_path',
		label_key='InChI program path',
		help_key='To use InChI in BKChem you must first give it a path to the InChI program here',
		accelerator=None,
		handler=interactors.ask_inchi_program_path,
		enabled_when=None,
	))
	# open preferences dialog
	registry.register(MenuAction(
		id='options.preferences',
		label_key='Preferences',
		help_key='Preferences',
		accelerator=None,
		handler=app.ask_preferences,
		enabled_when=None,
	))
