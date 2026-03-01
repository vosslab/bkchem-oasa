"""Chemistry menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def register_chemistry_actions(registry, app) -> None:
	"""Register all Chemistry menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# display summary info on selected molecules
	registry.register(MenuAction(
		id='chemistry.info',
		label_key='Info',
		help_key='Display summary formula and other info on all selected molecules',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Info: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# check if selected objects have chemical meaning
	registry.register(MenuAction(
		id='chemistry.check',
		label_key='Check chemistry',
		help_key='Check if the selected objects have chemical meaning',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Check chemistry: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# expand all selected groups to their structures
	registry.register(MenuAction(
		id='chemistry.expand_groups',
		label_key='Expand groups',
		help_key='Expand all selected groups to their structures',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Expand groups: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# compute and display oxidation number
	registry.register(MenuAction(
		id='chemistry.oxidation_number',
		label_key='Compute oxidation number',
		help_key='Compute and display the oxidation number of selected atoms',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Compute oxidation number: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# import a SMILES string as structure
	registry.register(MenuAction(
		id='chemistry.read_smiles',
		label_key='Import SMILES',
		help_key='Import a SMILES string and convert it to structure',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Import SMILES: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# import an InChI string as structure
	registry.register(MenuAction(
		id='chemistry.read_inchi',
		label_key='Import InChI',
		help_key='Import an InChI string and convert it to structure',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Import InChI: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# import a peptide amino acid sequence as structure
	registry.register(MenuAction(
		id='chemistry.read_peptide',
		label_key='Import Peptide Sequence',
		help_key='Import a peptide amino acid sequence and convert it to structure',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Import Peptide Sequence: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# export SMILES for the selected structure
	registry.register(MenuAction(
		id='chemistry.gen_smiles',
		label_key='Export SMILES',
		help_key='Export SMILES for the selected structure',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Export SMILES: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# export InChI for the selected structure
	registry.register(MenuAction(
		id='chemistry.gen_inchi',
		label_key='Export InChI',
		help_key='Export an InChI for the selected structure by calling the InChI program',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Export InChI: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# set the name of the selected molecule
	registry.register(MenuAction(
		id='chemistry.set_name',
		label_key='Set molecule name',
		help_key='Set the name of the selected molecule',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Set molecule name: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# set the ID of the selected molecule
	registry.register(MenuAction(
		id='chemistry.set_id',
		label_key='Set molecule ID',
		help_key='Set the ID of the selected molecule',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Set molecule ID: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# create a fragment from the selected part of the molecule
	registry.register(MenuAction(
		id='chemistry.create_fragment',
		label_key='Create fragment',
		help_key='Create a fragment from the selected part of the molecule',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Create fragment: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# show already defined fragments
	registry.register(MenuAction(
		id='chemistry.view_fragments',
		label_key='View fragments',
		help_key='Show already defined fragments',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"View fragments: not yet implemented", 3000
		),
		enabled_when=None,
	))

	# convert selected part of chain to linear fragment
	registry.register(MenuAction(
		id='chemistry.convert_to_linear',
		label_key='Convert selection to linear form',
		help_key='Convert selected part of chain to linear fragment',
		accelerator=None,
		handler=lambda: app.statusBar().showMessage(
			"Convert selection to linear form: not yet implemented", 3000
		),
		enabled_when=None,
	))
