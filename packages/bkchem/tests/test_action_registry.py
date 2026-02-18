"""Tests for the action registry core."""

# local repo modules
from bkchem.actions import MenuAction, ActionRegistry


#============================================
def _make_action(
	action_id: str = "test.action",
	label_key: str = "Test",
	help_key: str = "A test action",
	accelerator: str = None,
	handler: object = None,
	enabled_when: object = None,
) -> MenuAction:
	"""Helper to build a MenuAction with sensible defaults.

	Args:
		action_id: Unique action identifier.
		label_key: English label key.
		help_key: English help text key.
		accelerator: Keyboard shortcut or None.
		handler: Callable handler or None.
		enabled_when: Enable predicate or None.

	Returns:
		A MenuAction instance.
	"""
	action = MenuAction(
		id=action_id,
		label_key=label_key,
		help_key=help_key,
		accelerator=accelerator,
		handler=handler,
		enabled_when=enabled_when,
	)
	return action


#============================================
def test_register_and_get():
	"""Register a MenuAction, retrieve it, and verify all fields."""
	registry = ActionRegistry()
	# create a handler function for testing
	handler = lambda: None
	action = _make_action(
		action_id="file.save",
		label_key="Save",
		help_key="Save the file",
		accelerator="(C-x C-s)",
		handler=handler,
		enabled_when=None,
	)
	registry.register(action)
	# retrieve and verify
	result = registry.get("file.save")
	assert result.id == "file.save"
	assert result.label_key == "Save"
	assert result.help_key == "Save the file"
	assert result.accelerator == "(C-x C-s)"
	assert result.handler is handler
	assert result.enabled_when is None


#============================================
def test_duplicate_id_raises():
	"""Registering the same action ID twice raises ValueError."""
	registry = ActionRegistry()
	action1 = _make_action(action_id="edit.undo")
	action2 = _make_action(action_id="edit.undo", label_key="Undo Again")
	registry.register(action1)
	raised = False
	try:
		registry.register(action2)
	except ValueError:
		raised = True
	assert raised, "Expected ValueError for duplicate action ID"


#============================================
def test_contains():
	"""Verify __contains__ for registered and unregistered IDs."""
	registry = ActionRegistry()
	action = _make_action(action_id="view.zoom")
	registry.register(action)
	# registered ID should be found
	assert "view.zoom" in registry
	# unregistered ID should not be found
	assert "view.pan" not in registry


#============================================
def test_all_actions():
	"""Register 3 actions and verify all_actions returns all 3."""
	registry = ActionRegistry()
	ids = ["file.new", "file.open", "file.close"]
	for action_id in ids:
		action = _make_action(action_id=action_id)
		registry.register(action)
	# get the full dict
	all_dict = registry.all_actions()
	assert len(all_dict) == 3
	for action_id in ids:
		assert action_id in all_dict


#============================================
def test_is_enabled_none():
	"""Action with enabled_when=None is always enabled."""
	registry = ActionRegistry()
	action = _make_action(action_id="always.on", enabled_when=None)
	registry.register(action)
	# context can be anything; result should be True
	result = registry.is_enabled("always.on", context=None)
	assert result is True


#============================================
def test_is_enabled_callable():
	"""Action with callable predicate returns its boolean result."""
	registry = ActionRegistry()
	# predicate that returns True
	action_true = _make_action(
		action_id="cond.true",
		enabled_when=lambda: True,
	)
	registry.register(action_true)
	assert registry.is_enabled("cond.true", context=None) is True
	# predicate that returns False
	action_false = _make_action(
		action_id="cond.false",
		enabled_when=lambda: False,
	)
	registry.register(action_false)
	assert registry.is_enabled("cond.false", context=None) is False


#============================================
def test_is_enabled_string():
	"""Action with string predicate checks attribute on context."""
	registry = ActionRegistry()
	action = _make_action(
		action_id="cond.str",
		enabled_when="has_selection",
	)
	registry.register(action)

	# context with the attribute set to True
	class TrueCtx:
		has_selection = True

	assert registry.is_enabled("cond.str", context=TrueCtx()) is True

	# context with the attribute set to False
	class FalseCtx:
		has_selection = False

	assert registry.is_enabled("cond.str", context=FalseCtx()) is False

	# context missing the attribute entirely
	class MissingCtx:
		pass

	assert registry.is_enabled("cond.str", context=MissingCtx()) is False


#============================================
def test_label_and_help_properties():
	"""Verify .label and .help_text call the _() translator."""
	action = _make_action(
		label_key="Open",
		help_key="Open a file",
	)
	# with default _() identity function, label should match key
	assert action.label == "Open"
	assert action.help_text == "Open a file"
