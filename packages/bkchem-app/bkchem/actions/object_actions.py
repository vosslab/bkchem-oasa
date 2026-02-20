"""Object menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction


#============================================
def register_object_actions(registry, app) -> None:
	"""Register all Object menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing paper and scale access.
	"""
	# scale selected objects
	registry.register(MenuAction(
		id='object.scale',
		label_key='Scale',
		help_key='Scale selected objects',
		accelerator=None,
		handler=app.scale,
		enabled_when='selected',
	))
	# lift selected objects to top of stack
	registry.register(MenuAction(
		id='object.bring_to_front',
		label_key='Bring to front',
		help_key='Lift selected objects to the top of the stack',
		accelerator='(C-o C-f)',
		handler=lambda: app.paper.lift_selected_to_top(),
		enabled_when='selected',
	))
	# lower selected objects to bottom of stack
	registry.register(MenuAction(
		id='object.send_back',
		label_key='Send back',
		help_key='Lower the selected objects to the bottom of the stack',
		accelerator='(C-o C-b)',
		handler=lambda: app.paper.lower_selected_to_bottom(),
		enabled_when='selected',
	))
	# reverse ordering of selected objects on the stack
	registry.register(MenuAction(
		id='object.swap_on_stack',
		label_key='Swap on stack',
		help_key='Reverse the ordering of the selected objects on the stack',
		accelerator='(C-o C-s)',
		handler=lambda: app.paper.swap_selected_on_stack(),
		enabled_when='two_or_more_selected',
	))
	# vertical mirror reflection
	registry.register(MenuAction(
		id='object.vertical_mirror',
		label_key='Vertical mirror',
		help_key=(
			'Creates a reflection of the selected objects, the reflection axis '
			'is the common vertical axis of all the selected objects'
		),
		accelerator=None,
		handler=lambda: app.paper.swap_sides_of_selected(),
		enabled_when='selected_mols',
	))
	# horizontal mirror reflection
	registry.register(MenuAction(
		id='object.horizontal_mirror',
		label_key='Horizontal mirror',
		help_key=(
			'Creates a reflection of the selected objects, the reflection axis '
			'is the common horizontal axis of all the selected objects'
		),
		accelerator=None,
		handler=lambda: app.paper.swap_sides_of_selected('horizontal'),
		enabled_when='selected_mols',
	))
	# configure selected object properties
	registry.register(MenuAction(
		id='object.configure',
		label_key='Configure',
		help_key='Set the properties of the object, such as color, font size etc.',
		accelerator='Mouse-3',
		handler=lambda: app.paper.config_selected(),
		enabled_when='selected',
	))
