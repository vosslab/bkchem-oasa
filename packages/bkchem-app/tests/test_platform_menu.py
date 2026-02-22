"""Tests for the platform menu adapter (native tkinter.Menu implementation)."""

# Standard Library
import sys

import tkinter
import pytest


#============================================
@pytest.fixture(scope="module")
def tk_root():
	"""Create a shared Tk root for all tests in this module."""
	root = tkinter.Tk()
	root.withdraw()
	yield root
	root.destroy()


#============================================
def test_adapter_creates_menubar(tk_root):
	"""PlatformMenuAdapter should create a tkinter.Menu and configure the parent."""
	from bkchem.platform_menu import PlatformMenuAdapter
	adapter = PlatformMenuAdapter(tk_root)
	assert isinstance(adapter._menubar, tkinter.Menu)


#============================================
def test_add_menu(tk_root):
	"""add_menu should register a named submenu."""
	from bkchem.platform_menu import PlatformMenuAdapter
	adapter = PlatformMenuAdapter(tk_root)
	adapter.add_menu('File', 'File operations')
	menu = adapter.get_menu_component('File')
	assert isinstance(menu, tkinter.Menu)


#============================================
def test_add_command(tk_root):
	"""add_command should add a command entry to the named menu."""
	from bkchem.platform_menu import PlatformMenuAdapter
	adapter = PlatformMenuAdapter(tk_root)
	adapter.add_menu('File', 'File operations')
	cmd = lambda: None
	# should not raise
	adapter.add_command('File', 'New', '(C-n)', 'Create new file', cmd)


#============================================
def test_add_separator(tk_root):
	"""add_separator should add a separator to the named menu."""
	from bkchem.platform_menu import PlatformMenuAdapter
	adapter = PlatformMenuAdapter(tk_root)
	adapter.add_menu('File', 'File operations')
	adapter.add_separator('File')


#============================================
def test_add_cascade(tk_root):
	"""add_cascade should create a submenu under the named parent menu."""
	from bkchem.platform_menu import PlatformMenuAdapter
	adapter = PlatformMenuAdapter(tk_root)
	adapter.add_menu('File', 'File operations')
	adapter.add_cascade('File', 'Export', 'Export operations')
	export_menu = adapter.get_menu_component('Export')
	assert isinstance(export_menu, tkinter.Menu)


#============================================
def test_add_command_to_cascade(tk_root):
	"""add_command_to_cascade should add a command to a cascade submenu."""
	from bkchem.platform_menu import PlatformMenuAdapter
	adapter = PlatformMenuAdapter(tk_root)
	adapter.add_menu('File', 'File operations')
	adapter.add_cascade('File', 'Export', 'Export operations')
	cmd = lambda: None
	adapter.add_command_to_cascade('Export', 'SVG', 'Export as SVG', cmd)


#============================================
def test_component_with_menu_suffix(tk_root):
	"""component() should strip '-menu' suffix for Pmw compatibility."""
	from bkchem.platform_menu import PlatformMenuAdapter
	adapter = PlatformMenuAdapter(tk_root)
	adapter.add_menu('File', 'File operations')
	menu_a = adapter.component('File-menu')
	menu_b = adapter.component('File')
	assert menu_a is menu_b


#============================================
def test_set_item_state(tk_root):
	"""set_item_state should call entryconfigure on the correct menu."""
	from bkchem.platform_menu import PlatformMenuAdapter
	adapter = PlatformMenuAdapter(tk_root)
	adapter.add_menu('File', 'File operations')
	cmd = lambda: None
	adapter.add_command('File', 'Save', '(C-s)', 'Save file', cmd)
	# should not raise
	adapter.set_item_state('File', 'Save', enabled=True)
	adapter.set_item_state('File', 'Save', enabled=False)


#============================================
def test_format_accelerator_ctrl():
	"""format_accelerator should convert (C-n) to platform-native format."""
	from bkchem.platform_menu import format_accelerator
	if sys.platform == 'darwin':
		result = format_accelerator('(C-n)')
		assert 'Command' in result
		assert 'N' in result
	else:
		result = format_accelerator('(C-n)')
		assert result == 'Ctrl+N'


#============================================
def test_format_accelerator_none():
	"""format_accelerator should return None for None input."""
	from bkchem.platform_menu import format_accelerator
	assert format_accelerator(None) is None


#============================================
def test_format_accelerator_passthrough():
	"""format_accelerator should pass through non-parenthesized strings."""
	from bkchem.platform_menu import format_accelerator
	assert format_accelerator('Ctrl+N') == 'Ctrl+N'


#============================================
def test_format_accelerator_display_unicode():
	"""format_accelerator_display should produce Unicode symbols on macOS."""
	from bkchem.platform_menu import format_accelerator_display
	result = format_accelerator_display('(C-S-z)')
	if sys.platform == 'darwin':
		assert '\u2318' in result
		assert '\u21e7' in result
		assert 'Z' in result
	else:
		assert result == 'Ctrl+Shift+Z'
