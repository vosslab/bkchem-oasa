"""Insert menu action registrations for BKChem."""

# local repo modules
from bkchem.actions import MenuAction


#============================================
def register_insert_actions(registry, app) -> None:
	"""Register all Insert menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing insert methods.
	"""
	# insert a biomolecule template into the drawing
	registry.register(MenuAction(
		id='insert.biomolecule_template',
		label_key='Biomolecule template',
		help_key='Insert a biomolecule template into the drawing',
		accelerator=None,
		handler=app.insert_biomolecule_template,
		enabled_when=None,
	))
