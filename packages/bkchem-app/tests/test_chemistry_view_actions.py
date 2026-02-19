"""Tests for chemistry and view menu action registrations."""

# Standard Library
import sys
import types

# mock bkchem.interactors and bkchem.singleton_store before importing
# chemistry_actions, so the try/except import block picks up the mocks
_mock_interactors = types.ModuleType('bkchem.interactors')
_mock_interactors.compute_oxidation_number = lambda paper: None
_mock_interactors.ask_name_for_selected = lambda paper: None
_mock_interactors.ask_id_for_selected = lambda paper: None
_mock_interactors.create_fragment_from_selected = lambda paper: None
_mock_interactors.view_fragments = lambda paper: None
_mock_interactors.convert_selected_to_linear_fragment = lambda paper: None
sys.modules.setdefault('bkchem.interactors', _mock_interactors)

_mock_store_module = types.ModuleType('bkchem.singleton_store')
_mock_store = types.SimpleNamespace(
	pm=types.SimpleNamespace(has_preference=lambda k: True),
)
_mock_store_module.Store = _mock_store
sys.modules.setdefault('bkchem.singleton_store', _mock_store_module)

# local repo modules
from bkchem.actions import ActionRegistry
from bkchem.actions.chemistry_actions import register_chemistry_actions
from bkchem.actions.view_actions import register_view_actions


#============================================
def _make_mock_app():
	"""Build a mock app with attributes needed by chemistry and view actions.

	Returns:
		A SimpleNamespace mimicking the BKChem application object.
	"""
	paper = types.SimpleNamespace(
		display_info_on_selected=lambda: None,
		check_chemistry_of_selected=lambda: None,
		expand_groups=lambda: None,
		selected_mols=True,
		zoom_in=lambda: None,
		zoom_out=lambda: None,
		zoom_reset=lambda: None,
		zoom_to_fit=lambda: None,
		zoom_to_content=lambda: None,
	)
	app = types.SimpleNamespace(
		paper=paper,
		read_smiles=lambda: None,
		read_inchi=lambda: None,
		read_peptide_sequence=lambda: None,
		gen_smiles=lambda: None,
		gen_inchi=lambda: None,
	)
	return app


#============================================
def _build_chemistry_registry():
	"""Register chemistry actions and return the registry and app.

	Returns:
		A tuple of (ActionRegistry, mock app).
	"""
	app = _make_mock_app()
	registry = ActionRegistry()
	register_chemistry_actions(registry, app)
	return registry, app


#============================================
def _build_view_registry():
	"""Register view actions and return the registry and app.

	Returns:
		A tuple of (ActionRegistry, mock app).
	"""
	app = _make_mock_app()
	registry = ActionRegistry()
	register_view_actions(registry, app)
	return registry, app


#============================================
def test_chemistry_register_count():
	"""Verify exactly 14 chemistry actions are registered."""
	registry, _app = _build_chemistry_registry()
	actions = registry.all_actions()
	assert len(actions) == 14, f"Expected 14 chemistry actions, got {len(actions)}"


#============================================
def test_view_register_count():
	"""Verify exactly 5 view actions are registered."""
	registry, _app = _build_view_registry()
	actions = registry.all_actions()
	assert len(actions) == 5, f"Expected 5 view actions, got {len(actions)}"


#============================================
def test_chemistry_action_ids():
	"""Verify all 14 chemistry action IDs are present."""
	registry, _app = _build_chemistry_registry()
	expected_ids = {
		'chemistry.info',
		'chemistry.check',
		'chemistry.expand_groups',
		'chemistry.oxidation_number',
		'chemistry.read_smiles',
		'chemistry.read_inchi',
		'chemistry.read_peptide',
		'chemistry.gen_smiles',
		'chemistry.gen_inchi',
		'chemistry.set_name',
		'chemistry.set_id',
		'chemistry.create_fragment',
		'chemistry.view_fragments',
		'chemistry.convert_to_linear',
	}
	actual_ids = set(registry.all_actions().keys())
	assert actual_ids == expected_ids, f"ID mismatch: {actual_ids ^ expected_ids}"


#============================================
def test_view_action_ids():
	"""Verify all 5 view action IDs are present."""
	registry, _app = _build_view_registry()
	expected_ids = {
		'view.zoom_in',
		'view.zoom_out',
		'view.zoom_reset',
		'view.zoom_to_fit',
		'view.zoom_to_content',
	}
	actual_ids = set(registry.all_actions().keys())
	assert actual_ids == expected_ids, f"ID mismatch: {actual_ids ^ expected_ids}"


#============================================
def test_chemistry_enabled_when_types():
	"""Verify enabled_when values have the correct types for each action."""
	registry, _app = _build_chemistry_registry()
	actions = registry.all_actions()
	# string predicates for state-dependent actions
	assert actions['chemistry.info'].enabled_when == 'selected_mols'
	assert actions['chemistry.check'].enabled_when == 'selected_mols'
	assert actions['chemistry.expand_groups'].enabled_when == 'groups_selected'
	assert actions['chemistry.oxidation_number'].enabled_when == 'selected_atoms'
	assert actions['chemistry.gen_smiles'].enabled_when == 'selected_mols'
	assert actions['chemistry.set_name'].enabled_when == 'selected_mols'
	assert actions['chemistry.set_id'].enabled_when == 'one_mol_selected'
	assert actions['chemistry.create_fragment'].enabled_when == 'one_mol_selected'
	assert actions['chemistry.convert_to_linear'].enabled_when == 'selected_mols'
	# always-enabled actions (no predicate)
	assert actions['chemistry.read_smiles'].enabled_when is None
	assert actions['chemistry.read_inchi'].enabled_when is None
	assert actions['chemistry.read_peptide'].enabled_when is None
	assert actions['chemistry.view_fragments'].enabled_when is None
	# gen_inchi has a callable predicate (lambda checking Store and selection)
	assert callable(actions['chemistry.gen_inchi'].enabled_when)


#============================================
def test_view_all_enabled_when_none():
	"""Verify all 5 view actions have enabled_when=None (always enabled)."""
	registry, _app = _build_view_registry()
	actions = registry.all_actions()
	for action_id, action in actions.items():
		assert action.enabled_when is None, (
			f"{action_id} expected enabled_when=None, got {action.enabled_when!r}"
		)
