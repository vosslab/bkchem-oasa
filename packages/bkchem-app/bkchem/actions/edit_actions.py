"""Edit menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction


#============================================
def register_edit_actions(registry, app) -> None:
	"""Register all Edit menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing paper and clipboard access.
	"""
	# undo last change
	registry.register(MenuAction(
		id='edit.undo',
		label_key='Undo',
		help_key='Revert the last change made',
		accelerator='(C-z)',
		handler=lambda: app.paper.undo(),
		enabled_when=lambda: app.paper.um.can_undo(),
	))
	# redo last undo
	registry.register(MenuAction(
		id='edit.redo',
		label_key='Redo',
		help_key='Revert the last undo action',
		accelerator='(C-S-z)',
		handler=lambda: app.paper.redo(),
		enabled_when=lambda: app.paper.um.can_redo(),
	))
	# cut selected objects to clipboard
	registry.register(MenuAction(
		id='edit.cut',
		label_key='Cut',
		help_key='Copy the selected objects to clipboard and delete them',
		accelerator='(C-k)',
		handler=lambda: app.paper.selected_to_clipboard(delete_afterwards=1),
		enabled_when='selected',
	))
	# copy selected objects to clipboard
	registry.register(MenuAction(
		id='edit.copy',
		label_key='Copy',
		help_key='Copy the selected objects to clipboard',
		accelerator='(C-c)',
		handler=lambda: app.paper.selected_to_clipboard(),
		enabled_when='selected',
	))
	# paste from clipboard
	registry.register(MenuAction(
		id='edit.paste',
		label_key='Paste',
		help_key='Paste the content of clipboard to current paper',
		accelerator='(C-v)',
		handler=lambda: app.paper.paste_clipboard(None),
		enabled_when=lambda: app._clipboard,
	))
	# export selection as SVG to system clipboard
	registry.register(MenuAction(
		id='edit.selected_to_svg',
		label_key='Copy as SVG',
		help_key='Create SVG for the selected objects and place it to the system clipboard',
		accelerator=None,
		handler=lambda: app.paper.selected_to_real_clipboard_as_SVG(),
		enabled_when='selected',
	))
	# select everything on the paper
	registry.register(MenuAction(
		id='edit.select_all',
		label_key='Select All',
		help_key='Select everything on the paper',
		accelerator='(C-S-a)',
		handler=lambda: app.paper.select_all(),
		enabled_when=None,
	))
