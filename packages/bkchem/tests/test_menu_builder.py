"""Tests for the menu builder."""

# Standard Library
import os
import types
import tempfile

# local repo modules
from bkchem.menu_builder import MenuBuilder

# minimal YAML for testing
TEST_YAML = """
menus:
  - name: file
    label_key: "File"
    help_key: "File operations"
    side: "left"
    items:
      - action: file.new
      - action: file.save
      - separator: true
      - cascade: export
      - cascade: import
  - name: edit
    label_key: "Edit"
    help_key: "Edit operations"
    side: "left"
    items:
      - action: edit.undo
cascades:
  export:
    label_key: "Export"
    help_key: "Export the file"
  import:
    label_key: "Import"
    help_key: "Import a file"
"""


#============================================
class MockAction:
	"""Mock action for testing."""

	def __init__(self, action_id: str, label_key: str,
				 help_key: str, accelerator: str = None,
				 handler: object = None,
				 enabled_when: object = None):
		self.id = action_id
		self.label_key = label_key
		self.help_key = help_key
		self.accelerator = accelerator
		self.handler = handler
		self.enabled_when = enabled_when

	@property
	def label(self) -> str:
		return self.label_key

	@property
	def help_text(self) -> str:
		return self.help_key


#============================================
class MockRegistry:
	"""Mock action registry for testing."""

	def __init__(self, actions: list):
		self._actions = {a.id: a for a in actions}

	def get(self, action_id: str) -> MockAction:
		return self._actions[action_id]

	def __contains__(self, action_id: str) -> bool:
		return action_id in self._actions

	def all_actions(self) -> dict:
		return dict(self._actions)


#============================================
class MockAdapter:
	"""Mock platform menu adapter for testing."""

	def __init__(self):
		self.calls = []

	def add_menu(self, name: str, help_text: str, side: str = 'left'):
		self.calls.append(('add_menu', name, help_text, side))

	def add_command(self, menu_name: str, label: str,
					accel: str, help_text: str, command: object):
		self.calls.append(('add_command', menu_name, label))

	def add_separator(self, menu_name: str):
		self.calls.append(('add_separator', menu_name))

	def add_cascade(self, menu_name: str, cascade_name: str,
					help_text: str):
		self.calls.append(('add_cascade', menu_name, cascade_name))

	def add_command_to_cascade(self, cascade_name: str, label: str,
							   help_text: str, command: object):
		self.calls.append(
			('add_command_to_cascade', cascade_name, label)
		)

	def set_item_state(self, menu_name: str, label: str,
					   enabled: bool):
		self.calls.append(
			('set_item_state', menu_name, label, enabled)
		)


#============================================
def _noop():
	"""No-op handler for test actions."""
	pass


#============================================
def _make_registry() -> MockRegistry:
	"""Build a mock registry with test actions.

	Returns:
		MockRegistry with file.new, file.save, and edit.undo actions.
	"""
	actions = [
		MockAction("file.new", "New", "Create new file",
				   "Ctrl+N", _noop, None),
		MockAction("file.save", "Save", "Save current file",
				   "Ctrl+S", _noop, None),
		MockAction("edit.undo", "Undo", "Undo last action",
				   "Ctrl+Z", _noop, None),
	]
	return MockRegistry(actions)


#============================================
def _make_yaml_file() -> str:
	"""Write test YAML to a temporary file.

	Returns:
		path to the temporary YAML file
	"""
	f = tempfile.NamedTemporaryFile(
		mode='w', suffix='.yaml', delete=False,
	)
	f.write(TEST_YAML)
	f.close()
	return f.name


#============================================
def _build(registry: MockRegistry = None,
		   adapter: MockAdapter = None) -> tuple:
	"""Build a MenuBuilder with test fixtures.

	Args:
		registry: optional mock registry override
		adapter: optional mock adapter override

	Returns:
		tuple of (MenuBuilder, MockAdapter, yaml_path)
	"""
	yaml_path = _make_yaml_file()
	if registry is None:
		registry = _make_registry()
	if adapter is None:
		adapter = MockAdapter()
	builder = MenuBuilder(yaml_path, registry, adapter)
	return builder, adapter, yaml_path


#============================================
def test_build_creates_all_menus():
	"""Adapter add_menu called for each menu in YAML."""
	builder, adapter, yaml_path = _build()
	builder.build_menus()
	# clean up temp file
	os.unlink(yaml_path)
	# expect two add_menu calls (File and Edit)
	menu_calls = [c for c in adapter.calls if c[0] == 'add_menu']
	assert len(menu_calls) == 2
	menu_names = [c[1] for c in menu_calls]
	assert 'File' in menu_names
	assert 'Edit' in menu_names


#============================================
def test_build_creates_commands():
	"""Adapter add_command called for each registered action."""
	builder, adapter, yaml_path = _build()
	builder.build_menus()
	os.unlink(yaml_path)
	cmd_calls = [c for c in adapter.calls if c[0] == 'add_command']
	# file.new, file.save, edit.undo = 3 commands
	assert len(cmd_calls) == 3
	labels = [c[2] for c in cmd_calls]
	assert 'New' in labels
	assert 'Save' in labels
	assert 'Undo' in labels


#============================================
def test_separators_placed():
	"""Adapter add_separator called for separator items."""
	builder, adapter, yaml_path = _build()
	builder.build_menus()
	os.unlink(yaml_path)
	sep_calls = [c for c in adapter.calls if c[0] == 'add_separator']
	assert len(sep_calls) == 1
	# separator is in the File menu
	assert sep_calls[0][1] == 'File'


#============================================
def test_cascades_created():
	"""Adapter add_cascade called for cascade items."""
	builder, adapter, yaml_path = _build()
	builder.build_menus()
	os.unlink(yaml_path)
	cascade_calls = [
		c for c in adapter.calls if c[0] == 'add_cascade'
	]
	assert len(cascade_calls) == 2
	cascade_names = [c[2] for c in cascade_calls]
	assert 'Export' in cascade_names
	assert 'Import' in cascade_names


#============================================
def test_missing_action_skipped():
	"""Actions not in registry are silently skipped."""
	# registry with only file.new (missing file.save and edit.undo)
	registry = MockRegistry([
		MockAction("file.new", "New", "Create new", None, _noop, None),
	])
	builder, adapter, yaml_path = _build(registry=registry)
	builder.build_menus()
	os.unlink(yaml_path)
	cmd_calls = [c for c in adapter.calls if c[0] == 'add_command']
	# only file.new should appear
	assert len(cmd_calls) == 1
	assert cmd_calls[0][2] == 'New'


#============================================
def test_update_states_none_skipped():
	"""Actions with enabled_when=None are not passed to set_item_state."""
	builder, adapter, yaml_path = _build()
	builder.build_menus()
	os.unlink(yaml_path)
	# all test actions have enabled_when=None
	# create a dummy app object
	app = types.SimpleNamespace(paper=types.SimpleNamespace())
	builder.update_menu_states(app)
	state_calls = [
		c for c in adapter.calls if c[0] == 'set_item_state'
	]
	assert len(state_calls) == 0


#============================================
def test_update_states_callable():
	"""Callable predicate is evaluated and set_item_state called."""
	# create action with a callable enabled_when
	actions = [
		MockAction("file.new", "New", "Create new", None, _noop,
				   enabled_when=lambda: False),
	]
	registry = MockRegistry(actions)
	builder, adapter, yaml_path = _build(registry=registry)
	builder.build_menus()
	app = types.SimpleNamespace(paper=types.SimpleNamespace())
	builder.update_menu_states(app)
	os.unlink(yaml_path)
	state_calls = [
		c for c in adapter.calls if c[0] == 'set_item_state'
	]
	assert len(state_calls) == 1
	# should be disabled (predicate returns False)
	assert state_calls[0] == ('set_item_state', 'File', 'New', False)


#============================================
def test_update_states_string():
	"""String predicate is looked up on app.paper attribute."""
	actions = [
		MockAction("file.new", "New", "Create new", None, _noop,
				   enabled_when="has_selection"),
	]
	registry = MockRegistry(actions)
	builder, adapter, yaml_path = _build(registry=registry)
	builder.build_menus()
	# app.paper.has_selection = True
	paper = types.SimpleNamespace(has_selection=True)
	app = types.SimpleNamespace(paper=paper)
	builder.update_menu_states(app)
	os.unlink(yaml_path)
	state_calls = [
		c for c in adapter.calls if c[0] == 'set_item_state'
	]
	assert len(state_calls) == 1
	assert state_calls[0] == ('set_item_state', 'File', 'New', True)


#============================================
def test_plugin_slots_returned():
	"""get_plugin_slots returns dict with exporters and importers."""
	builder, adapter, yaml_path = _build()
	builder.build_menus()
	os.unlink(yaml_path)
	slots = builder.get_plugin_slots()
	assert 'exporters' in slots
	assert slots['exporters'] == 'Export'
	assert 'importers' in slots
	assert slots['importers'] == 'Import'


#============================================
def test_add_to_plugin_slot():
	"""add_to_plugin_slot adds command to cascade via adapter."""
	builder, adapter, yaml_path = _build()
	builder.build_menus()
	# add a plugin exporter
	builder.add_to_plugin_slot(
		'exporters', 'PDF export', 'Export as PDF', _noop,
	)
	os.unlink(yaml_path)
	cascade_cmd_calls = [
		c for c in adapter.calls
		if c[0] == 'add_command_to_cascade'
	]
	assert len(cascade_cmd_calls) == 1
	assert cascade_cmd_calls[0] == (
		'add_command_to_cascade', 'Export', 'PDF export',
	)


#============================================
def test_add_to_unknown_slot_ignored():
	"""Adding to a nonexistent slot does nothing."""
	builder, adapter, yaml_path = _build()
	builder.build_menus()
	# 'converters' is not a known slot
	builder.add_to_plugin_slot(
		'converters', 'Thing', 'Does stuff', _noop,
	)
	os.unlink(yaml_path)
	cascade_cmd_calls = [
		c for c in adapter.calls
		if c[0] == 'add_command_to_cascade'
	]
	assert len(cascade_cmd_calls) == 0
