"""Chemistry menu action registrations for BKChem."""

# local repo modules
from bkchem.actions.action_registry import MenuAction

# these imports are needed for handler lambdas;
# they may not resolve in isolated test environments
try:
	from bkchem import interactors
	from bkchem.singleton_store import Store
except ImportError:
	interactors = None
	Store = None


#============================================
def register_chemistry_actions(registry, app) -> None:
	"""Register all Chemistry menu actions.

	Args:
		registry: The ActionRegistry to register actions with.
		app: The application object providing paper and chemistry methods.
	"""
	# display summary info on selected molecules
	registry.register(MenuAction(
		id='chemistry.info',
		label_key='Info',
		help_key='Display summary formula and other info on all selected molecules',
		accelerator='(C-o C-i)',
		handler=lambda: app.paper.display_info_on_selected(),
		enabled_when='selected_mols',
	))
	# check chemical validity of selection
	registry.register(MenuAction(
		id='chemistry.check',
		label_key='Check chemistry',
		help_key='Check if the selected objects have chemical meaning',
		accelerator='(C-o C-c)',
		handler=lambda: app.paper.check_chemistry_of_selected(),
		enabled_when='selected_mols',
	))
	# expand group abbreviations to full structures
	registry.register(MenuAction(
		id='chemistry.expand_groups',
		label_key='Expand groups',
		help_key='Expand all selected groups to their structures',
		accelerator='(C-o C-e)',
		handler=lambda: app.paper.expand_groups(),
		enabled_when='groups_selected',
	))
	# compute and show oxidation numbers for selected atoms
	registry.register(MenuAction(
		id='chemistry.oxidation_number',
		label_key='Compute oxidation number',
		help_key='Compute and display the oxidation number of selected atoms',
		accelerator=None,
		handler=lambda: interactors.compute_oxidation_number(app.paper),
		enabled_when='selected_atoms',
	))
	# read a SMILES string and convert to structure
	registry.register(MenuAction(
		id='chemistry.read_smiles',
		label_key='Read SMILES',
		help_key='Read a SMILES string and convert it to structure',
		accelerator=None,
		handler=app.read_smiles,
		enabled_when=None,
	))
	# read an InChI string and convert to structure
	registry.register(MenuAction(
		id='chemistry.read_inchi',
		label_key='Read InChI',
		help_key='Read an InChI string and convert it to structure',
		accelerator=None,
		handler=app.read_inchi,
		enabled_when=None,
	))
	# read a peptide amino acid sequence and convert to structure
	registry.register(MenuAction(
		id='chemistry.read_peptide',
		label_key='Read Peptide Sequence',
		help_key='Read a peptide amino acid sequence and convert it to structure',
		accelerator=None,
		handler=app.read_peptide_sequence,
		enabled_when=None,
	))
	# generate SMILES for selected structure
	registry.register(MenuAction(
		id='chemistry.gen_smiles',
		label_key='Generate SMILES',
		help_key='Generate SMILES for the selected structure',
		accelerator=None,
		handler=app.gen_smiles,
		enabled_when='selected_mols',
	))
	# generate InChI for selected structure using external program
	registry.register(MenuAction(
		id='chemistry.gen_inchi',
		label_key='Generate InChI',
		help_key=(
			'Generate an InChI for the selected structure by calling '
			'the InChI program'
		),
		accelerator=None,
		handler=app.gen_inchi,
		enabled_when=lambda: (
			Store.pm.has_preference("inchi_program_path")
			and app.paper.selected_mols
		),
	))
	# set the name of the selected molecule
	registry.register(MenuAction(
		id='chemistry.set_name',
		label_key='Set molecule name',
		help_key='Set the name of the selected molecule',
		accelerator=None,
		handler=lambda: interactors.ask_name_for_selected(app.paper),
		enabled_when='selected_mols',
	))
	# set the ID of the selected molecule
	registry.register(MenuAction(
		id='chemistry.set_id',
		label_key='Set molecule ID',
		help_key='Set the ID of the selected molecule',
		accelerator=None,
		handler=lambda: interactors.ask_id_for_selected(app.paper),
		enabled_when='one_mol_selected',
	))
	# create a fragment from selected part of molecule
	registry.register(MenuAction(
		id='chemistry.create_fragment',
		label_key='Create fragment',
		help_key='Create a fragment from the selected part of the molecule',
		accelerator=None,
		handler=lambda: interactors.create_fragment_from_selected(app.paper),
		enabled_when='one_mol_selected',
	))
	# show already defined fragments
	registry.register(MenuAction(
		id='chemistry.view_fragments',
		label_key='View fragments',
		help_key='Show already defined fragments',
		accelerator=None,
		handler=lambda: interactors.view_fragments(app.paper),
		enabled_when=None,
	))
	# convert selected chain to linear fragment form
	registry.register(MenuAction(
		id='chemistry.convert_to_linear',
		label_key='Convert selection to linear form',
		help_key=(
			'Convert selected part of chain to linear fragment. '
			'The selected chain must not be split.'
		),
		accelerator=None,
		handler=lambda: interactors.convert_selected_to_linear_fragment(app.paper),
		enabled_when='selected_mols',
	))
