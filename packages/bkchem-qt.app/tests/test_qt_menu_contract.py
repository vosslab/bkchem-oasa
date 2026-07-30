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
import bkchem_qt.actions.menu_builder


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

	def test_construction_and_fields(self) -> None:
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

	def test_label_property_returns_translated_key(self) -> None:
		"""The label property returns the label_key through _()."""
		action = _make_action(label_key="Open File")
		# without custom gettext, _() is identity
		assert action.label == "Open File"

	def test_help_text_property_returns_translated_key(self) -> None:
		"""The help_text property returns the help_key through _()."""
		action = _make_action(help_key="Open an existing file")
		assert action.help_text == "Open an existing file"

	def test_none_accelerator(self) -> None:
		"""MenuAction accepts None for accelerator."""
		action = _make_action(accelerator=None)
		assert action.accelerator is None

	def test_none_handler(self) -> None:
		"""MenuAction accepts None for handler (cascade menus)."""
		action = _make_action(handler=None)
		assert action.handler is None

	def test_none_enabled_when(self) -> None:
		"""MenuAction accepts None for enabled_when (always enabled)."""
		action = _make_action(enabled_when=None)
		assert action.enabled_when is None


#============================================
class TestActionRegistry:
	"""Tests for the ActionRegistry class."""

	def test_register_and_get(self) -> None:
		"""Registered actions are retrievable by ID."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(action_id="edit.undo")
		registry.register(action)
		retrieved = registry.get("edit.undo")
		assert retrieved is action

	def test_contains_registered_action(self) -> None:
		"""__contains__ returns True for registered action IDs."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(action_id="edit.redo")
		registry.register(action)
		assert "edit.redo" in registry

	def test_contains_missing_action(self) -> None:
		"""__contains__ returns False for unregistered action IDs."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		assert "nonexistent.action" not in registry

	def test_duplicate_id_raises_value_error(self) -> None:
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

	def test_get_missing_raises_key_error(self) -> None:
		"""Getting an unregistered ID raises KeyError."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		try:
			registry.get("missing.action")
			assert False, "Expected KeyError for missing ID"
		except KeyError:
			pass

	def test_all_actions_returns_copy(self) -> None:
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

	def test_multiple_registrations(self) -> None:
		"""Multiple distinct actions can be registered and retrieved."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		ids = ["file.new", "file.open", "file.save", "edit.undo", "edit.redo"]
		for action_id in ids:
			registry.register(_make_action(action_id=action_id))
		for action_id in ids:
			assert action_id in registry
			assert registry.get(action_id).id == action_id

	def test_action_module_import_error_names_module(self, monkeypatch: object) -> None:
		"""An action import failure identifies the module that failed."""
		monkeypatch.setattr(
			bkchem_qt.actions.action_registry,
			"ACTION_REGISTRAR_MODULES",
			("bkchem_qt.actions.broken_actions",),
		)
		def raise_import_error(module_name: str) -> object:
			raise ImportError("deliberate missing dependency")
		monkeypatch.setattr(
			bkchem_qt.actions.action_registry.importlib,
			"import_module", raise_import_error,
		)
		try:
			bkchem_qt.actions.action_registry.register_all_actions(object())
			assert False, "Expected action module import failure"
		except bkchem_qt.actions.action_registry.ActionRegistrationError as exc:
			assert "bkchem_qt.actions.broken_actions" in str(exc)

	def test_registrar_failure_names_module_and_registrar(self, monkeypatch: object) -> None:
		"""A registrar exception preserves its manifest module context."""
		class _BrokenModule:
			def register_broken_actions(self, registry: object, app: object) -> None:
				raise ValueError("deliberate registration failure")

		monkeypatch.setattr(
			bkchem_qt.actions.action_registry,
			"ACTION_REGISTRAR_MODULES",
			("bkchem_qt.actions.broken_actions",),
		)
		monkeypatch.setattr(
			bkchem_qt.actions.action_registry.importlib,
			"import_module", lambda _module_name: _BrokenModule(),
		)

		try:
			bkchem_qt.actions.action_registry.register_all_actions(object())
			assert False, "Expected action registration failure"
		except bkchem_qt.actions.action_registry.ActionRegistrationError as exc:
			assert "bkchem_qt.actions.broken_actions" in str(exc)
			assert "register_broken_actions" in str(exc)


#============================================
class _FakeMenuAdapter:
	"""Minimal non-Qt adapter used to exercise YAML menu validation."""

	def add_menu(self, name: str, help_text: str, side: str) -> None:
		"""Accept a top-level menu without creating native UI state."""

	def add_command(
			self, menu_name: str, label: str, accelerator: str,
			help_text: str, handler: object, action_key: str,
			) -> None:
		"""Accept an action command without creating native UI state."""

	def add_separator(self, menu_name: str) -> None:
		"""Accept a menu separator without creating native UI state."""

	def add_cascade(
			self, menu_name: str, cascade_label: str, cascade_help: str,
			) -> None:
		"""Accept a cascade without creating native UI state."""


#============================================
def test_required_yaml_action_is_not_silently_omitted(tmp_path: pathlib.Path) -> None:
	"""A typo in a required YAML action prevents a partial menu startup."""
	menu_file = tmp_path / "menus.yaml"
	menu_file.write_text(
		"menus:\n"
		"  - label_key: File\n"
		"    help_key: File commands\n"
		"    items:\n"
		"      - action: file.typo\n",
	)
	registry = bkchem_qt.actions.action_registry.ActionRegistry()
	builder = bkchem_qt.actions.menu_builder.MenuBuilder(
		str(menu_file), registry, _FakeMenuAdapter(),
	)
	try:
		builder.build_menus()
		assert False, "Expected missing required action failure"
	except KeyError as exc:
		assert "file.typo" in str(exc)


#============================================
def test_preflight_reports_all_required_unregistered_actions(tmp_path: pathlib.Path) -> None:
	"""Preflight reports a stable complete list before native menu construction."""
	menu_file = tmp_path / "menus.yaml"
	menu_file.write_text(
		"menus:\n"
		"  - label_key: File\n"
		"    help_key: File commands\n"
		"    items:\n"
		"      - action: file.zeta\n"
		"      - action: file.alpha\n",
	)
	registry = bkchem_qt.actions.action_registry.ActionRegistry()

	try:
		bkchem_qt.actions.menu_builder.preflight_required_menu_actions(
			registry, str(menu_file),
		)
		assert False, "Expected required menu action preflight failure"
	except bkchem_qt.actions.menu_builder.MenuActionPreflightError as exc:
		assert str(exc) == (
			"Required menu actions are unregistered: file.alpha, file.zeta"
		)


#============================================
def test_optional_yaml_action_can_be_omitted(tmp_path: pathlib.Path) -> None:
	"""Explicitly optional YAML actions do not block a menu build."""
	menu_file = tmp_path / "menus.yaml"
	menu_file.write_text(
		"menus:\n"
		"  - label_key: File\n"
		"    help_key: File commands\n"
		"    items:\n"
		"      - action: file.plugin_action\n"
		"        optional: true\n",
	)
	registry = bkchem_qt.actions.action_registry.ActionRegistry()
	builder = bkchem_qt.actions.menu_builder.MenuBuilder(
		str(menu_file), registry, _FakeMenuAdapter(),
	)
	builder.build_menus()
	assert builder.get_plugin_slots() == {}


#============================================
class TestIsEnabled:
	"""Tests for ActionRegistry.is_enabled() with different predicate types."""

	def test_none_predicate_always_enabled(self) -> None:
		"""An action with enabled_when=None is always enabled."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(action_id="always.on", enabled_when=None)
		registry.register(action)
		# context does not matter when predicate is None
		result = registry.is_enabled("always.on", context=None)
		assert result is True

	def test_callable_predicate_returns_true(self) -> None:
		"""A callable predicate returning True enables the action."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(
			action_id="callable.true",
			enabled_when=lambda: True,
		)
		registry.register(action)
		result = registry.is_enabled("callable.true", context=None)
		assert result is True

	def test_callable_predicate_returns_false(self) -> None:
		"""A callable predicate returning False disables the action."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(
			action_id="callable.false",
			enabled_when=lambda: False,
		)
		registry.register(action)
		result = registry.is_enabled("callable.false", context=None)
		assert result is False

	def test_callable_predicate_truthy_value(self) -> None:
		"""A callable returning a truthy non-bool value enables the action."""
		registry = bkchem_qt.actions.action_registry.ActionRegistry()
		action = _make_action(
			action_id="callable.truthy",
			enabled_when=lambda: "nonempty string",
		)
		registry.register(action)
		result = registry.is_enabled("callable.truthy", context=None)
		assert result is True

	def test_string_predicate_attribute_true(self) -> None:
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

	def test_string_predicate_attribute_false(self) -> None:
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

	def test_string_predicate_missing_attribute(self) -> None:
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
