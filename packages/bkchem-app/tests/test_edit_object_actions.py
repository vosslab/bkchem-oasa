"""Tests for edit and object menu action registrations."""

# Standard Library
import types

# local repo modules
from bkchem.actions import ActionRegistry
from bkchem.actions.edit_actions import register_edit_actions
from bkchem.actions.object_actions import register_object_actions


#============================================
def _make_mock_app():
	"""Build a mock app with the attributes needed by edit and object actions.

	Returns:
		A SimpleNamespace mimicking the BKChem application object.
	"""
	um = types.SimpleNamespace(can_undo=lambda: True, can_redo=lambda: False)
	paper = types.SimpleNamespace(
		undo=lambda: None,
		redo=lambda: None,
		selected_to_clipboard=lambda **kw: None,
		paste_clipboard=lambda x: None,
		selected_to_real_clipboard_as_SVG=lambda: None,
		select_all=lambda: None,
		lift_selected_to_top=lambda: None,
		lower_selected_to_bottom=lambda: None,
		swap_selected_on_stack=lambda: None,
		swap_sides_of_selected=lambda *a: None,
		config_selected=lambda: None,
		align_selected=lambda d: None,
		um=um,
	)
	app = types.SimpleNamespace(
		paper=paper,
		scale=lambda: None,
		_clipboard=True,
	)
	return app


#============================================
def _build_edit_registry():
	"""Register edit actions and return the registry and app.

	Returns:
		A tuple of (ActionRegistry, mock app).
	"""
	app = _make_mock_app()
	registry = ActionRegistry()
	register_edit_actions(registry, app)
	return registry, app


#============================================
def _build_object_registry():
	"""Register object actions and return the registry and app.

	Returns:
		A tuple of (ActionRegistry, mock app).
	"""
	app = _make_mock_app()
	registry = ActionRegistry()
	register_object_actions(registry, app)
	return registry, app


#============================================
def test_edit_register_count():
	"""Verify exactly 7 edit actions are registered."""
	registry, _app = _build_edit_registry()
	actions = registry.all_actions()
	assert len(actions) == 7, f"Expected 7 edit actions, got {len(actions)}"


#============================================
def test_object_register_count():
	"""Verify exactly 7 object actions are registered."""
	registry, _app = _build_object_registry()
	actions = registry.all_actions()
	assert len(actions) == 7, f"Expected 7 object actions, got {len(actions)}"


#============================================
def test_edit_action_ids():
	"""Verify all 7 edit action IDs are present."""
	registry, _app = _build_edit_registry()
	expected_ids = {
		'edit.undo',
		'edit.redo',
		'edit.cut',
		'edit.copy',
		'edit.paste',
		'edit.selected_to_svg',
		'edit.select_all',
	}
	actual_ids = set(registry.all_actions().keys())
	assert actual_ids == expected_ids, f"ID mismatch: {actual_ids ^ expected_ids}"


#============================================
def test_object_action_ids():
	"""Verify all 7 object action IDs are present."""
	registry, _app = _build_object_registry()
	expected_ids = {
		'object.scale',
		'object.bring_to_front',
		'object.send_back',
		'object.swap_on_stack',
		'object.vertical_mirror',
		'object.horizontal_mirror',
		'object.configure',
	}
	actual_ids = set(registry.all_actions().keys())
	assert actual_ids == expected_ids, f"ID mismatch: {actual_ids ^ expected_ids}"


#============================================
def test_edit_enabled_when_types():
	"""Verify enabled_when values have the correct types for each edit action."""
	registry, _app = _build_edit_registry()
	actions = registry.all_actions()
	# undo and redo should have callable predicates
	assert callable(actions['edit.undo'].enabled_when)
	assert callable(actions['edit.redo'].enabled_when)
	# cut, copy, and svg should use the 'selected' string predicate
	assert actions['edit.cut'].enabled_when == 'selected'
	assert actions['edit.copy'].enabled_when == 'selected'
	assert actions['edit.selected_to_svg'].enabled_when == 'selected'
	# select_all is always enabled (None)
	assert actions['edit.select_all'].enabled_when is None
	# paste has a callable predicate checking clipboard
	assert callable(actions['edit.paste'].enabled_when)


#============================================
def test_object_enabled_when_types():
	"""Verify enabled_when values have the correct types for each object action."""
	registry, _app = _build_object_registry()
	actions = registry.all_actions()
	# scale, bring_to_front, send_back, configure use 'selected'
	assert actions['object.scale'].enabled_when == 'selected'
	assert actions['object.bring_to_front'].enabled_when == 'selected'
	assert actions['object.send_back'].enabled_when == 'selected'
	assert actions['object.configure'].enabled_when == 'selected'
	# swap_on_stack uses 'two_or_more_selected'
	assert actions['object.swap_on_stack'].enabled_when == 'two_or_more_selected'
	# mirrors use 'selected_mols'
	assert actions['object.vertical_mirror'].enabled_when == 'selected_mols'
	assert actions['object.horizontal_mirror'].enabled_when == 'selected_mols'
