"""File menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction


#============================================
def register_file_actions(registry, app) -> None:
	"""Register all File menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem application object providing handler methods.
	"""
	# create a new file in a new tab
	registry.register(MenuAction(
		id='file.new',
		label_key='New',
		help_key='Create a new file in a new tab',
		accelerator='(C-x C-n)',
		handler=app.add_new_paper,
		enabled_when=None,
	))
	# save the current file
	registry.register(MenuAction(
		id='file.save',
		label_key='Save',
		help_key='Save the file',
		accelerator='(C-x C-s)',
		handler=app.save_CDML,
		enabled_when=None,
	))
	# save under a different name
	registry.register(MenuAction(
		id='file.save_as',
		label_key='Save As..',
		help_key='Save the file under different name',
		accelerator='(C-x C-w)',
		handler=app.save_as_CDML,
		enabled_when=None,
	))
	# save as a template file
	registry.register(MenuAction(
		id='file.save_as_template',
		label_key='Save As Template',
		help_key='Save the file as template, certain criteria must be met for this to work',
		accelerator=None,
		handler=app.save_as_template,
		enabled_when=None,
	))
	# open a file in a new tab
	registry.register(MenuAction(
		id='file.load',
		label_key='Load',
		help_key='Load (open) a file in a new tab',
		accelerator='(C-x C-f)',
		handler=app.load_CDML,
		enabled_when=None,
	))
	# open a file replacing the current tab
	registry.register(MenuAction(
		id='file.load_same_tab',
		label_key='Load to the same tab',
		help_key='Load a file replacing the current one',
		accelerator=None,
		handler=lambda: app.load_CDML(replace=1),
		enabled_when=None,
	))
	# document properties dialog
	registry.register(MenuAction(
		id='file.properties',
		label_key='File properties',
		help_key='Set the papers size and other properties of the document',
		accelerator=None,
		handler=app.change_properties,
		enabled_when=None,
	))
	# close the current tab
	registry.register(MenuAction(
		id='file.close_tab',
		label_key='Close tab',
		help_key='Close the current tab, exit when there is only one tab',
		accelerator='(C-x C-t)',
		handler=app.close_current_paper,
		enabled_when=None,
	))
	# exit the application
	registry.register(MenuAction(
		id='file.exit',
		label_key='Exit',
		help_key='Exit BKChem',
		accelerator='(C-x C-c)',
		handler=app._quit,
		enabled_when=None,
	))
