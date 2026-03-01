"""Tests for BKChem-Qt ActionRegistry and MenuAction.

Verifies the pure-Python menu action contract without requiring
PySide6 or a running Qt application.
"""

# Standard Library
import sys
import pathlib

# ensure the bkchem-qt.app package is importable
_qt_app_dir = pathlib.Path(__file__).resolve().parent.parent
if str(_qt_app_dir) not in sys.path:
	sys.path.insert(0, str(_qt_app_dir))

# local repo modules
import bkchem_qt.actions.action_registry


#============================================
def _make_action(
	action_id: str = "test.action",
	label_key: str = "Test Label",
	help_key: str = "Test help text",
	accelerator: str = None,
	handler: object = None,
	enabled_when: object = None,
) -> bkchem_qt.actions.action_registry.MenuAction:
	"""Create a MenuAction with sensible defaults for testing.

	Args:
		action_id: Unique action identifier.
		label_key: English label key.
		help_key: English help text key.
		accelerator: Keyboard shortcut string or None.
		handler: Callable or None.
		enabled_when: Callable, string, or None.

	Returns:
		A MenuAction instance.
	"""
	action = bkchem_qt.actions.action_registry.MenuAction(
		id=action_id,
		label_key=label_key,
		help_key=help_key,
		accelerator=accelerator,
		handler=handler,
		enabled_when=enabled_when,
	)
	return action


#============================================
class TestMenuAction:
	"""Tests for the MenuAction dataclass."""

	def test_construction_and_fields(self):
		"""MenuAction stores all fields correctly."""
		handler = lambda: None
		action = _make_action(
			action_id="file.save",
			label_key="Save",
			help_key="Save the current file",
			accelerator="(C-x C-s)",
			handler=handler,
			enabled_when="has_file",
		)
		assert action.id == "file.save"
		assert action.label_key == "Save"
		assert action.help_key == "Save the current file"
		assert action.accelerator == "(C-x C-s)"
		assert action.handler is handler
		assert action.enabled_when == "has_file"

	def test_label_property_returns_translated_key(self):
		"""The label property returns the label_key through _()."""
		action = _make_action(label_key="Open File")
		# without custom gettext, _() is identity
		assert action.label == "Open File"

	def test_help_text_property_returns_translated_key(self):
		"""The help_text property returns the help_key through _()."""
		action = _make_action(help_key="Open an existing file")
		assert action.help_text == "Open an existing file"

	def test_none_accelerator(self):
		"""MenuAction accepts None for accelerator."""
		action = _make_action(accelerator=None)
		assert action.accelerator is None

	def test_none_handler(self):
		"""MenuAction accepts None for handler (cascade menus)."""
		action = _make_action(handler=None)
		assert action.handler is None

	def test_none_enabled_when(self):
		"""MenuAction accepts None for enabled_when (always enabled)."""
		action = _make_action(enabled_when=None)
		assert action.enabled_when is None


#============================================
class TestActionRegistry:
	"""Tests for the ActionRegistry class."""

	def test_register_and_get(self):
		"""Registered actions are retrievable by ID."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(action_id="edit.undo")
		registry.register(action)
		retrieved = registry.get("edit.undo")
		assert retrieved is action

	def test_contains_registered_action(self):
		"""__contains__ returns True for registered action IDs."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(action_id="edit.redo")
		registry.register(action)
		assert "edit.redo" in registry

	def test_contains_missing_action(self):
		"""__contains__ returns False for unregistered action IDs."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		assert "nonexistent.action" not in registry

	def test_duplicate_id_raises_value_error(self):
		"""Registering a duplicate ID raises ValueError."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action1 = _make_action(action_id="file.open")
		action2 = _make_action(action_id="file.open")
		registry.register(action1)
		try:
			registry.register(action2)
			assert False, "Expected ValueError for duplicate ID"
		except ValueError as exc:
			assert "file.open" in str(exc)

	def test_get_missing_raises_key_error(self):
		"""Getting an unregistered ID raises KeyError."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		try:
			registry.get("missing.action")
			assert False, "Expected KeyError for missing ID"
		except KeyError:
			pass

	def test_all_actions_returns_copy(self):
		"""all_actions() returns a shallow copy of all registered actions."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action1 = _make_action(action_id="file.new")
		action2 = _make_action(action_id="file.save")
		registry.register(action1)
		registry.register(action2)
		all_acts = registry.all_actions()
		assert len(all_acts) == 2
		assert "file.new" in all_acts
		assert "file.save" in all_acts
		# verify it is a copy, not the internal dict
		all_acts["extra"] = "should not affect registry"
		assert "extra" not in registry

	def test_multiple_registrations(self):
		"""Multiple distinct actions can be registered and retrieved."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		ids = ["file.new", "file.open", "file.save", "edit.undo", "edit.redo"]
		for action_id in ids:
			registry.register(_make_action(action_id=action_id))
		for action_id in ids:
			assert action_id in registry
			assert registry.get(action_id).id == action_id


#============================================
class TestIsEnabled:
	"""Tests for ActionRegistry.is_enabled() with different predicate types."""

	def test_none_predicate_always_enabled(self):
		"""An action with enabled_when=None is always enabled."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(action_id="always.on", enabled_when=None)
		registry.register(action)
		# context does not matter when predicate is None
		result = registry.is_enabled("always.on", context=None)
		assert result is True

	def test_callable_predicate_returns_true(self):
		"""A callable predicate returning True enables the action."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(
			action_id="callable.true",
			enabled_when=lambda: True,
		)
		registry.register(action)
		result = registry.is_enabled("callable.true", context=None)
		assert result is True

	def test_callable_predicate_returns_false(self):
		"""A callable predicate returning False disables the action."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(
			action_id="callable.false",
			enabled_when=lambda: False,
		)
		registry.register(action)
		result = registry.is_enabled("callable.false", context=None)
		assert result is False

	def test_callable_predicate_truthy_value(self):
		"""A callable returning a truthy non-bool value enables the action."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(
			action_id="callable.truthy",
			enabled_when=lambda: "nonempty string",
		)
		registry.register(action)
		result = registry.is_enabled("callable.truthy", context=None)
		assert result is True

	def test_string_predicate_attribute_true(self):
		"""A string predicate checks the context attribute for truthiness."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(
			action_id="string.true",
			enabled_when="has_selection",
		)
		registry.register(action)

		# create a simple context object with has_selection = True
		class Context:
			has_selection = True
		result = registry.is_enabled("string.true", context=Context())
		assert result is True

	def test_string_predicate_attribute_false(self):
		"""A string predicate with falsy attribute disables the action."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(
			action_id="string.false",
			enabled_when="has_selection",
		)
		registry.register(action)

		# create a context with has_selection = False
		class Context:
			has_selection = False
		result = registry.is_enabled("string.false", context=Context())
		assert result is False

	def test_string_predicate_missing_attribute(self):
		"""A string predicate with missing attribute defaults to disabled."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(
			action_id="string.missing",
			enabled_when="nonexistent_attr",
		)
		registry.register(action)

		# context without the named attribute
		class Context:
			pass
		result = registry.is_enabled("string.missing", context=Context())
		assert result is False
