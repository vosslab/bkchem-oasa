"""Tests for Align, Insert, Options, Help, and Plugins menu actions."""

# Standard Library
import sys
import types

# mock interactors and Store before importing options_actions
mock_interactors = types.ModuleType('bkchem.interactors')
mock_interactors.select_language = lambda paper: None
mock_interactors.set_logging = lambda paper, logger: None
mock_interactors.ask_inchi_program_path = lambda: None
sys.modules['bkchem.interactors'] = mock_interactors

mock_store_module = types.ModuleType('bkchem.singleton_store')
mock_store = types.SimpleNamespace(logger=None)
mock_store_module.Store = mock_store
sys.modules['bkchem.singleton_store'] = mock_store_module

# local repo modules
from bkchem.actions import ActionRegistry
from bkchem.actions.align_actions import register_align_actions
from bkchem.actions.insert_actions import register_insert_actions
from bkchem.actions.options_actions import register_options_actions
from bkchem.actions.help_actions import register_help_actions
from bkchem.actions.plugins_actions import register_plugins_actions

# expected action IDs per menu
ALIGN_IDS = [
	'align.top',
	'align.bottom',
	'align.left',
	'align.right',
	'align.center_h',
	'align.center_v',
]

OPTIONS_IDS = [
	'options.standard',
	'options.language',
	'options.logging',
	'options.inchi_path',
	'options.preferences',
]


#============================================
def _make_mock_app():
	"""Create a mock application object with stub handler methods.

	Returns:
		A SimpleNamespace mimicking the BKChem application object.
	"""
	paper = types.SimpleNamespace(align_selected=lambda d: None)
	app = types.SimpleNamespace(
		paper=paper,
		insert_biomolecule_template=lambda: None,
		standard_values=lambda: None,
		ask_preferences=lambda: None,
		about=lambda: None,
	)
	return app


#============================================
def _build_registry(*registrars):
	"""Build a registry populated by the given registrar functions.

	Args:
		*registrars: One or more register functions to call.

	Returns:
		A tuple of (registry, mock_app).
	"""
	app = _make_mock_app()
	registry = ActionRegistry()
	for registrar in registrars:
		registrar(registry, app)
	return registry, app


#============================================
def test_align_register_count():
	"""Verify exactly 6 align actions are registered."""
	registry, _ = _build_registry(register_align_actions)
	all_actions = registry.all_actions()
	assert len(all_actions) == 6


#============================================
def test_align_all_two_or_more_selected():
	"""Verify all 6 align actions require two_or_more_selected."""
	registry, _ = _build_registry(register_align_actions)
	for action_id in ALIGN_IDS:
		action = registry.get(action_id)
		assert action.enabled_when == 'two_or_more_selected', (
			f"enabled_when mismatch for {action_id}"
		)


#============================================
def test_align_action_ids():
	"""Verify all 6 expected align action IDs are present."""
	registry, _ = _build_registry(register_align_actions)
	all_actions = registry.all_actions()
	registered_ids = set(all_actions.keys())
	assert registered_ids == set(ALIGN_IDS)


#============================================
def test_insert_register_count():
	"""Verify exactly 1 insert action is registered."""
	registry, _ = _build_registry(register_insert_actions)
	all_actions = registry.all_actions()
	assert len(all_actions) == 1


#============================================
def test_options_register_count():
	"""Verify exactly 5 options actions are registered."""
	registry, _ = _build_registry(register_options_actions)
	all_actions = registry.all_actions()
	assert len(all_actions) == 5


#============================================
def test_options_action_ids():
	"""Verify all 5 expected options action IDs are present."""
	registry, _ = _build_registry(register_options_actions)
	all_actions = registry.all_actions()
	registered_ids = set(all_actions.keys())
	assert registered_ids == set(OPTIONS_IDS)


#============================================
def test_help_register_count():
	"""Verify exactly 1 help action is registered."""
	registry, _ = _build_registry(register_help_actions)
	all_actions = registry.all_actions()
	assert len(all_actions) == 1


#============================================
def test_plugins_register_count():
	"""Verify exactly 0 plugins actions are registered."""
	registry, _ = _build_registry(register_plugins_actions)
	all_actions = registry.all_actions()
	assert len(all_actions) == 0


#============================================
def test_label_keys_exact():
	"""Spot check critical label keys across menus."""
	# check align labels
	registry, _ = _build_registry(register_align_actions)
	assert registry.get('align.top').label_key == 'Top'
	assert registry.get('align.center_h').label_key == 'Center horizontally'
	assert registry.get('align.center_v').label_key == 'Center vertically'
	# check insert label
	registry, _ = _build_registry(register_insert_actions)
	assert registry.get('insert.biomolecule_template').label_key == 'Biomolecule template'
	# check options labels
	registry, _ = _build_registry(register_options_actions)
	assert registry.get('options.standard').label_key == 'Standard'
	assert registry.get('options.inchi_path').label_key == 'InChI program path'
	assert registry.get('options.preferences').label_key == 'Preferences'
	# check help label
	registry, _ = _build_registry(register_help_actions)
	assert registry.get('help.about').label_key == 'About'
