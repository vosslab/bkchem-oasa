"""Edit menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def register_edit_actions(registry, app) -> None:
	"""Register all Edit menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# undo last change
	registry.register(MenuAction(
		id='edit.undo',
		label_key='Undo',
		help_key='Revert the last change made',
		accelerator='(C-z)',
		handler=app.on_undo,
		enabled_when=None,
	))

	# redo last undo
	registry.register(MenuAction(
		id='edit.redo',
		label_key='Redo',
		help_key='Revert the last undo action',
		accelerator='(C-S-z)',
		handler=app.on_redo,
		enabled_when=None,
	))

	# cut selected objects to clipboard
	registry.register(MenuAction(
		id='edit.cut',
		label_key='Cut',
		help_key='Copy the selected objects to clipboard and delete them',
		accelerator='(C-k)',
		handler=app.on_cut,
		enabled_when=None,
	))

	# copy selected objects to clipboard
	registry.register(MenuAction(
		id='edit.copy',
		label_key='Copy',
		help_key='Copy the selected objects to clipboard',
		accelerator='(C-c)',
		handler=app.on_copy,
		enabled_when=None,
	))

	# paste clipboard contents onto paper
	registry.register(MenuAction(
		id='edit.paste',
		label_key='Paste',
		help_key='Paste the content of clipboard to current paper',
		accelerator='(C-v)',
		handler=app.on_paste,
		enabled_when=None,
	))

	# copy selection as SVG to system clipboard
	registry.register(MenuAction(
		id='edit.selected_to_svg',
		label_key='Copy as SVG',
		help_key='Create SVG for the selected objects and place it to the system clipboard',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Copy as SVG: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# select all objects on the paper
	registry.register(MenuAction(
		id='edit.select_all',
		label_key='Select All',
		help_key='Select everything on the paper',
		accelerator='(C-S-a)',
		handler=lambda: app.statusBar().showMessage(
			"Select All: not yet implemented", 3000
		),
		enabled_when=None,
	))
