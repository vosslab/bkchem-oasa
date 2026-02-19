"""Tests for the platform menu adapter."""

# Standard Library
import sys
import types
import unittest.mock


#============================================
class MockMenuBar:
	"""Mock for Pmw.MenuBar that records all calls."""

	def __init__(self, parent, balloon=None):
		self.calls = []

	def addmenu(self, name, help_text, side='left'):
		self.calls.append(('addmenu', name, help_text, side))

	def addmenuitem(self, menu, item_type, **kwargs):
		self.calls.append(('addmenuitem', menu, item_type, kwargs))

	def addcascademenu(self, menu, name, help_text, **kwargs):
		self.calls.append(('addcascademenu', menu, name, help_text, kwargs))

	def component(self, name):
		return MockMenu()

	def pack(self, **kwargs):
		pass


#============================================
class MockMainMenuBar(MockMenuBar):
	"""Mock for Pmw.MainMenuBar."""
	pass


#============================================
class MockMenu:
	"""Mock for Tk Menu widget."""

	def __init__(self):
		self.calls = []

	def entryconfigure(self, label, **kwargs):
		self.calls.append(('entryconfigure', label, kwargs))


#============================================
def _create_adapter(platform: str = 'linux'):
	"""Create a PlatformMenuAdapter with mocked dependencies.

	Args:
		platform: platform string to simulate ('darwin' or 'linux')

	Returns:
		tuple of (adapter, mock_menubar)
	"""
	# build mock Pmw module
	mock_pmw = types.ModuleType('Pmw')
	mock_menubar = MockMenuBar(None)
	mock_main_menubar = MockMainMenuBar(None)
	mock_pmw.MenuBar = lambda parent, balloon=None: mock_menubar
	mock_pmw.MainMenuBar = lambda parent, balloon=None: mock_main_menubar

	# build mock tkinter module with Frame and RAISED
	mock_tkinter = types.ModuleType('tkinter')
	mock_tkinter.Frame = lambda parent, **kw: types.SimpleNamespace(
		grid=lambda **kw: None
	)
	mock_tkinter.RAISED = 'raised'

	# build mock bkchem.bkchem_config module
	mock_config = types.ModuleType('bkchem.bkchem_config')
	mock_config.border_width = 2

	mock_parent = types.SimpleNamespace(configure=lambda **kw: None)
	mock_balloon = None
	mock_main_frame = types.SimpleNamespace()

	# patch sys.modules so imports inside platform_menu resolve to our mocks
	# do not replace 'bkchem' itself -- the real package __init__.py is empty
	patched_modules = {
		'Pmw': mock_pmw,
		'tkinter': mock_tkinter,
		'bkchem.bkchem_config': mock_config,
	}

	# remove cached platform_menu so it re-imports cleanly each time
	if 'bkchem.platform_menu' in sys.modules:
		del sys.modules['bkchem.platform_menu']

	with unittest.mock.patch.dict(sys.modules, patched_modules):
		with unittest.mock.patch('sys.platform', platform):
			from bkchem.platform_menu import PlatformMenuAdapter
			adapter = PlatformMenuAdapter(
				mock_parent, mock_balloon, main_frame=mock_main_frame
			)

	if platform == 'darwin':
		return adapter, mock_main_menubar
	return adapter, mock_menubar


#============================================
def test_macos_uses_main_menu_bar():
	"""On macOS, the adapter should use Pmw.MainMenuBar."""
	adapter, menubar = _create_adapter(platform='darwin')
	# MainMenuBar is a MockMainMenuBar instance
	assert isinstance(menubar, MockMainMenuBar)
	assert adapter._use_system_menubar is True


#============================================
def test_linux_uses_menu_bar():
	"""On Linux, the adapter should use Pmw.MenuBar."""
	adapter, menubar = _create_adapter(platform='linux')
	# MenuBar is a MockMenuBar but not MockMainMenuBar
	assert isinstance(menubar, MockMenuBar)
	assert adapter._use_system_menubar is False


#============================================
def test_add_menu_calls_addmenu():
	"""add_menu should call addmenu on the underlying menubar."""
	adapter, menubar = _create_adapter(platform='linux')
	adapter.add_menu('File', 'File operations', side='left')
	# find the addmenu call
	addmenu_calls = [c for c in menubar.calls if c[0] == 'addmenu']
	assert len(addmenu_calls) == 1
	assert addmenu_calls[0] == ('addmenu', 'File', 'File operations', 'left')


#============================================
def test_add_menu_side_ignored_on_macos():
	"""On macOS, addmenu should not pass the side argument."""
	adapter, menubar = _create_adapter(platform='darwin')
	adapter.add_menu('File', 'File operations', side='right')
	addmenu_calls = [c for c in menubar.calls if c[0] == 'addmenu']
	assert len(addmenu_calls) == 1
	# macOS call should use default side='left' (no explicit side passed)
	_call_name, name, help_text, side = addmenu_calls[0]
	assert name == 'File'
	assert help_text == 'File operations'
	# side should be the default 'left', not 'right'
	assert side == 'left'


#============================================
def test_add_command_calls_addmenuitem():
	"""add_command should call addmenuitem with type 'command'."""
	adapter, menubar = _create_adapter(platform='linux')
	# dummy command callable
	cmd = lambda: None
	adapter.add_command('File', 'New', 'Ctrl+N', 'Create new file', cmd)
	item_calls = [c for c in menubar.calls if c[0] == 'addmenuitem']
	assert len(item_calls) == 1
	assert item_calls[0][1] == 'File'
	assert item_calls[0][2] == 'command'
	kwargs = item_calls[0][3]
	assert kwargs['label'] == 'New'
	assert kwargs['accelerator'] == 'Ctrl+N'
	assert kwargs['statusHelp'] == 'Create new file'
	assert kwargs['command'] is cmd


#============================================
def test_add_separator():
	"""add_separator should call addmenuitem with type 'separator'."""
	adapter, menubar = _create_adapter(platform='linux')
	adapter.add_separator('File')
	item_calls = [c for c in menubar.calls if c[0] == 'addmenuitem']
	assert len(item_calls) == 1
	assert item_calls[0][1] == 'File'
	assert item_calls[0][2] == 'separator'


#============================================
def test_add_cascade():
	"""add_cascade should call addcascademenu with tearoff=0."""
	adapter, menubar = _create_adapter(platform='linux')
	adapter.add_cascade('Edit', 'Transform', 'Transform operations')
	cascade_calls = [c for c in menubar.calls if c[0] == 'addcascademenu']
	assert len(cascade_calls) == 1
	assert cascade_calls[0][1] == 'Edit'
	assert cascade_calls[0][2] == 'Transform'
	assert cascade_calls[0][3] == 'Transform operations'
	# verify tearoff=0 is in kwargs
	assert cascade_calls[0][4].get('tearoff') == 0


#============================================
def test_add_command_to_cascade():
	"""add_command_to_cascade should add a command to a cascade submenu."""
	adapter, menubar = _create_adapter(platform='linux')
	cmd = lambda: None
	adapter.add_command_to_cascade('Transform', 'Rotate', 'Rotate object', cmd)
	item_calls = [c for c in menubar.calls if c[0] == 'addmenuitem']
	assert len(item_calls) == 1
	assert item_calls[0][1] == 'Transform'
	assert item_calls[0][2] == 'command'
	kwargs = item_calls[0][3]
	assert kwargs['label'] == 'Rotate'
	assert kwargs['statusHelp'] == 'Rotate object'
	assert kwargs['command'] is cmd


#============================================
def test_set_item_state_enabled():
	"""set_item_state with enabled=True should set state to 'normal'."""
	adapter, menubar = _create_adapter(platform='linux')
	# patch component to return a stable mock for verification
	stable_mock = MockMenu()
	adapter._menubar.component = lambda name: stable_mock
	adapter.set_item_state('File', 'Save', enabled=True)
	assert len(stable_mock.calls) == 1
	assert stable_mock.calls[0] == (
		'entryconfigure', 'Save', {'state': 'normal'}
	)


#============================================
def test_set_item_state_disabled():
	"""set_item_state with enabled=False should set state to 'disabled'."""
	adapter, menubar = _create_adapter(platform='linux')
	stable_mock = MockMenu()
	adapter._menubar.component = lambda name: stable_mock
	adapter.set_item_state('Edit', 'Paste', enabled=False)
	assert len(stable_mock.calls) == 1
	assert stable_mock.calls[0] == (
		'entryconfigure', 'Paste', {'state': 'disabled'}
	)
