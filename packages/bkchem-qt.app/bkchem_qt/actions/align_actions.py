"""Align menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def register_align_actions(registry, app) -> None:
	"""Register all Align menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# align the tops of selected objects
	registry.register(MenuAction(
		id='align.top',
		label_key='Top',
		help_key='Align the tops of selected objects',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Align top: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# align the bottoms of selected objects
	registry.register(MenuAction(
		id='align.bottom',
		label_key='Bottom',
		help_key='Align the bottoms of selected objects',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Align bottom: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# align the left sides of selected objects
	registry.register(MenuAction(
		id='align.left',
		label_key='Left',
		help_key='Align the left sides of selected objects',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Align left: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# align the right sides of selected objects
	registry.register(MenuAction(
		id='align.right',
		label_key='Right',
		help_key='Align the right sides of selected objects',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Align right: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# align the horizontal centers of selected objects
	registry.register(MenuAction(
		id='align.center_h',
		label_key='Center horizontally',
		help_key='Align the horizontal centers of selected objects',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Align center horizontally: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# align the vertical centers of selected objects
	registry.register(MenuAction(
		id='align.center_v',
		label_key='Center vertically',
		help_key='Align the vertical centers of selected objects',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Align center vertically: not yet implemented", 3000
		),
		enabled_when=None,
	))
