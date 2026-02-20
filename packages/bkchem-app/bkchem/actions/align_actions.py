"""Align menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction


#============================================
def register_align_actions(registry, app) -> None:
	"""Register all Align menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing paper alignment methods.
	"""
	# align tops of selected objects
	registry.register(MenuAction(
		id='align.top',
		label_key='Top',
		help_key='Align the tops of selected objects',
		accelerator='(C-a C-t)',
		handler=lambda: app.paper.align_selected('t'),
		enabled_when='two_or_more_selected',
	))
	# align bottoms of selected objects
	registry.register(MenuAction(
		id='align.bottom',
		label_key='Bottom',
		help_key='Align the bottoms of selected objects',
		accelerator='(C-a C-b)',
		handler=lambda: app.paper.align_selected('b'),
		enabled_when='two_or_more_selected',
	))
	# align left sides of selected objects
	registry.register(MenuAction(
		id='align.left',
		label_key='Left',
		help_key='Align the left sides of selected objects',
		accelerator='(C-a C-l)',
		handler=lambda: app.paper.align_selected('l'),
		enabled_when='two_or_more_selected',
	))
	# align right sides of selected objects
	registry.register(MenuAction(
		id='align.right',
		label_key='Right',
		help_key='Align the rights sides of selected objects',
		accelerator='(C-a C-r)',
		handler=lambda: app.paper.align_selected('r'),
		enabled_when='two_or_more_selected',
	))
	# align horizontal centers of selected objects
	registry.register(MenuAction(
		id='align.center_h',
		label_key='Center horizontally',
		help_key='Align the horizontal centers of selected objects',
		accelerator='(C-a C-h)',
		handler=lambda: app.paper.align_selected('h'),
		enabled_when='two_or_more_selected',
	))
	# align vertical centers of selected objects
	registry.register(MenuAction(
		id='align.center_v',
		label_key='Center vertically',
		help_key='Align the vertical centers of selected objects',
		accelerator='(C-a C-v)',
		handler=lambda: app.paper.align_selected('v'),
		enabled_when='two_or_more_selected',
	))
