"""Object menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def register_object_actions(registry, app) -> None:
	"""Register all Object menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# scale selected objects
	registry.register(MenuAction(
		id='object.scale',
		label_key='Scale',
		help_key='Scale selected objects',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Scale: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# lift selected objects to the top of the stack
	registry.register(MenuAction(
		id='object.bring_to_front',
		label_key='Bring to front',
		help_key='Lift selected objects to the top of the stack',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Bring to front: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# lower selected objects to the bottom of the stack
	registry.register(MenuAction(
		id='object.send_back',
		label_key='Send back',
		help_key='Lower the selected objects to the bottom of the stack',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Send back: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# reverse the ordering of selected objects on the stack
	registry.register(MenuAction(
		id='object.swap_on_stack',
		label_key='Swap on stack',
		help_key=(
			'Reverse the ordering of the selected objects on the stack'
		),
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Swap on stack: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# create a vertical-axis reflection of selected objects
	registry.register(MenuAction(
		id='object.vertical_mirror',
		label_key='Vertical mirror',
		help_key=(
			'Creates a reflection of the selected objects, the reflection'
			' axis is the common vertical axis of all the selected objects'
		),
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Vertical mirror: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# create a horizontal-axis reflection of selected objects
	registry.register(MenuAction(
		id='object.horizontal_mirror',
		label_key='Horizontal mirror',
		help_key=(
			'Creates a reflection of the selected objects, the reflection'
			' axis is the common horizontal axis of all the selected objects'
		),
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Horizontal mirror: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# configure properties of the selected object
	registry.register(MenuAction(
		id='object.configure',
		label_key='Configure',
		help_key=(
			'Set the properties of the object, such as color,'
			' font size etc.'
		),
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Configure: not yet implemented", 3000
		),
		enabled_when=None,
	))
