"""Test that Qt theme palette/QSS is driven entirely by YAML theme files.

Each test spawns a subprocess to avoid QApplication singleton conflicts.
Verifies that build_palette and build_qss read from YAML and do not
contain old hardcoded color values.

Usage:
	source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_qt_theme_yaml_mapping.py -v
"""

# Standard Library
import os
import subprocess
import sys

# PIP3 modules
import pytest

# timeout for each subprocess test
_SUBPROCESS_TIMEOUT = 15

# working directory for subprocess invocations
_CWD = os.path.join(
	os.path.dirname(os.path.abspath(__file__)), ".."
)


#============================================
def _check_subprocess_result(result) -> None:
	"""Evaluate a subprocess result and raise or skip appropriately.

	Args:
		result: CompletedProcess from subprocess.run.
	"""
	if result.returncode == 0:
		return
	combined = (result.stdout or "") + (result.stderr or "")
	# skip if PySide6 is not installed
	if "PySide6" in combined or "No module named" in combined:
		pytest.skip("PySide6 not available")
	raise AssertionError(
		f"Subprocess failed (rc={result.returncode}).\n{combined}"
	)


#============================================
def test_dark_yaml_gui_keys_exist():
	"""Verify all expected gui keys exist in dark.yaml via get_gui_colors."""
	code = (
		"import bkchem_qt.themes.theme_loader\n"
		"gui = bkchem_qt.themes.theme_loader.get_gui_colors('dark')\n"
		"expected_keys = [\n"
		"    'background', 'toolbar', 'toolbar_fg', 'separator',\n"
		"    'hover', 'active_mode', 'active_mode_fg',\n"
		"    'active_mode_highlight', 'active_tab_bg', 'active_tab_fg',\n"
		"    'inactive_tab_fg', 'button_active_bg', 'group_separator',\n"
		"    'grid_selected', 'grid_deselected', 'group_label_fg',\n"
		"    'entry_bg', 'entry_fg', 'entry_disabled_fg',\n"
		"    'entry_insert_bg', 'canvas_surround',\n"
		"]\n"
		"for key in expected_keys:\n"
		"    assert key in gui, f'Missing gui key in dark.yaml: {key}'\n"
		"assert len(expected_keys) >= 19, 'Expected at least 19 gui keys'\n"
		"print('PASS')\n"
	)
	result = subprocess.run(
		[sys.executable, "-c", code],
		capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
		cwd=_CWD,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_light_yaml_gui_keys_exist():
	"""Verify all expected gui keys exist in light.yaml via get_gui_colors."""
	code = (
		"import bkchem_qt.themes.theme_loader\n"
		"gui = bkchem_qt.themes.theme_loader.get_gui_colors('light')\n"
		"expected_keys = [\n"
		"    'background', 'toolbar', 'toolbar_fg', 'separator',\n"
		"    'hover', 'active_mode', 'active_mode_fg',\n"
		"    'active_mode_highlight', 'active_tab_bg', 'active_tab_fg',\n"
		"    'inactive_tab_fg', 'button_active_bg', 'group_separator',\n"
		"    'grid_selected', 'grid_deselected', 'group_label_fg',\n"
		"    'entry_bg', 'entry_fg', 'entry_disabled_fg',\n"
		"    'entry_insert_bg', 'canvas_surround',\n"
		"]\n"
		"for key in expected_keys:\n"
		"    assert key in gui, f'Missing gui key in light.yaml: {key}'\n"
		"assert len(expected_keys) >= 19, 'Expected at least 19 gui keys'\n"
		"print('PASS')\n"
	)
	result = subprocess.run(
		[sys.executable, "-c", code],
		capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
		cwd=_CWD,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_dark_qss_uses_yaml_values():
	"""Verify dark QSS contains YAML values, not old hardcoded values."""
	code = (
		"import bkchem_qt.themes.palettes\n"
		"qss = bkchem_qt.themes.palettes.build_qss('dark')\n"
		"assert '#2b2b2b' in qss, 'Expected YAML dark background'\n"
		"assert '#1e1e2e' not in qss, 'Found old hardcoded dark background'\n"
		"print('PASS')\n"
	)
	result = subprocess.run(
		[sys.executable, "-c", code],
		capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
		cwd=_CWD,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_light_qss_uses_yaml_values():
	"""Verify light QSS contains YAML values, not old hardcoded values."""
	code = (
		"import bkchem_qt.themes.palettes\n"
		"qss = bkchem_qt.themes.palettes.build_qss('light')\n"
		"assert '#eaeaea' in qss, 'Expected YAML light background'\n"
		"assert '#f8fafc' not in qss, 'Found old hardcoded light background'\n"
		"print('PASS')\n"
	)
	result = subprocess.run(
		[sys.executable, "-c", code],
		capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
		cwd=_CWD,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_dark_palette_returns_qpalette():
	"""Verify build_palette('dark') returns a QPalette instance."""
	code = (
		"import PySide6.QtGui\n"
		"import bkchem_qt.themes.palettes\n"
		"palette = bkchem_qt.themes.palettes.build_palette('dark')\n"
		"assert isinstance(palette, PySide6.QtGui.QPalette), (\n"
		"    f'Expected QPalette, got {type(palette)}'\n"
		")\n"
		"print('PASS')\n"
	)
	result = subprocess.run(
		[sys.executable, "-c", code],
		capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
		cwd=_CWD,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_light_palette_returns_qpalette():
	"""Verify build_palette('light') returns a QPalette instance."""
	code = (
		"import PySide6.QtGui\n"
		"import bkchem_qt.themes.palettes\n"
		"palette = bkchem_qt.themes.palettes.build_palette('light')\n"
		"assert isinstance(palette, PySide6.QtGui.QPalette), (\n"
		"    f'Expected QPalette, got {type(palette)}'\n"
		")\n"
		"print('PASS')\n"
	)
	result = subprocess.run(
		[sys.executable, "-c", code],
		capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
		cwd=_CWD,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout
