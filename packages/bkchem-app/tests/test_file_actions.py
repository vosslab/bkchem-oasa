"""Tests for File menu action registrations."""

# Standard Library
import types

# local repo modules
from bkchem.actions.action_registry import ActionRegistry
from bkchem.actions.file_actions import register_file_actions

# expected action IDs in registration order
EXPECTED_IDS = [
	'file.new',
	'file.save',
	'file.save_as',
	'file.save_as_template',
	'file.load',
	'file.load_same_tab',
	'file.properties',
	'file.close_tab',
	'file.exit',
]

# expected label keys keyed by action ID
EXPECTED_LABELS = {
	'file.new': 'New',
	'file.save': 'Save',
	'file.save_as': 'Save As...',
	'file.save_as_template': 'Save As Template',
	'file.load': 'Open',
	'file.load_same_tab': 'Open in same tab',
	'file.properties': 'Document Properties...',
	'file.close_tab': 'Close tab',
	'file.exit': 'Quit',
}


#============================================
def _make_mock_app():
	"""Create a mock application object with stub handler methods.

	Returns:
		A SimpleNamespace with all handler methods as no-op lambdas.
	"""
	app = types.SimpleNamespace()
	app.add_new_paper = lambda: None
	app.save_CDML = lambda: None
	app.save_as_CDML = lambda: None
	app.save_as_template = lambda: None
	app.load_CDML = lambda **kw: None
	app.change_properties = lambda: None
	app.close_current_paper = lambda: None
	app._quit = lambda: None
	return app


#============================================
def _build_registry():
	"""Build a registry populated with file actions using a mock app.

	Returns:
		A tuple of (registry, mock_app).
	"""
	app = _make_mock_app()
	registry = ActionRegistry()
	register_file_actions(registry, app)
	return registry, app


#============================================
def test_register_count():
	"""Verify exactly 9 file actions are registered."""
	registry, _ = _build_registry()
	all_actions = registry.all_actions()
	assert len(all_actions) == 9


#============================================
def test_action_ids():
	"""Verify all 9 expected action IDs are present."""
	registry, _ = _build_registry()
	all_actions = registry.all_actions()
	registered_ids = set(all_actions.keys())
	assert registered_ids == set(EXPECTED_IDS)


#============================================
def test_label_keys_exact():
	"""Verify label_key strings match exactly, especially 'Save As..' (two dots)."""
	registry, _ = _build_registry()
	for action_id, expected_label in EXPECTED_LABELS.items():
		action = registry.get(action_id)
		assert action.label_key == expected_label, (
			f"label_key mismatch for {action_id}: "
			f"expected {expected_label!r}, got {action.label_key!r}"
		)


#============================================
def test_all_enabled_when_none():
	"""Verify all 9 actions have enabled_when=None."""
	registry, _ = _build_registry()
	for action_id in EXPECTED_IDS:
		action = registry.get(action_id)
		assert action.enabled_when is None, (
			f"enabled_when should be None for {action_id}"
		)


#============================================
def test_handlers_callable():
	"""Verify all 9 actions have callable handlers."""
	registry, _ = _build_registry()
	for action_id in EXPECTED_IDS:
		action = registry.get(action_id)
		assert callable(action.handler), (
			f"handler should be callable for {action_id}"
		)
