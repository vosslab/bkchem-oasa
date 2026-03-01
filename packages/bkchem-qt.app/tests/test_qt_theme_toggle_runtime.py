"""Test that ThemeManager toggle switches palette colors to match YAML values.

Each test spawns an isolated subprocess with a QApplication to verify that
apply_theme changes the QPalette Window color to match the YAML gui.background
value for each theme.

Usage:
	source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_qt_theme_toggle_runtime.py -v
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

# environment with offscreen Qt platform for headless testing
_ENV = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}


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
	# skip if no display server is available
	if "cannot open display" in combined.lower():
		pytest.skip("No display available for Qt tests")
	if "could not connect to display" in combined.lower():
		pytest.skip("No display available for Qt tests")
	if "this application failed to start" in combined.lower():
		pytest.skip("No display available for Qt tests")
	raise AssertionError(
		f"Subprocess failed (rc={result.returncode}).\n{combined}"
	)


#============================================
def test_theme_toggle_changes_palette():
	"""Verify apply_theme switches palette Window color to match YAML values."""
	code = (
		"import PySide6.QtWidgets\n"
		"import PySide6.QtGui\n"
		"app = PySide6.QtWidgets.QApplication([])\n"
		"import bkchem_qt.themes.theme_manager\n"
		"mgr = bkchem_qt.themes.theme_manager.ThemeManager(app)\n"
		"mgr.apply_theme('dark')\n"
		"dark_bg = app.palette().color(\n"
		"    PySide6.QtGui.QPalette.ColorRole.Window\n"
		").name()\n"
		"assert dark_bg == '#2b2b2b', (\n"
		"    f'Expected #2b2b2b, got {dark_bg}'\n"
		")\n"
		"mgr.apply_theme('light')\n"
		"light_bg = app.palette().color(\n"
		"    PySide6.QtGui.QPalette.ColorRole.Window\n"
		").name()\n"
		"assert light_bg == '#eaeaea', (\n"
		"    f'Expected #eaeaea, got {light_bg}'\n"
		")\n"
		"print('PASS')\n"
		"app.quit()\n"
	)
	result = subprocess.run(
		[sys.executable, "-c", code],
		capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
		cwd=_CWD,
		env=_ENV,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_theme_toggle_roundtrip():
	"""Verify dark -> light -> dark roundtrip preserves palette colors."""
	code = (
		"import PySide6.QtWidgets\n"
		"import PySide6.QtGui\n"
		"app = PySide6.QtWidgets.QApplication([])\n"
		"import bkchem_qt.themes.theme_manager\n"
		"mgr = bkchem_qt.themes.theme_manager.ThemeManager(app)\n"
		"# apply dark, then light, then dark again\n"
		"mgr.apply_theme('dark')\n"
		"mgr.apply_theme('light')\n"
		"mgr.apply_theme('dark')\n"
		"dark_bg = app.palette().color(\n"
		"    PySide6.QtGui.QPalette.ColorRole.Window\n"
		").name()\n"
		"assert dark_bg == '#2b2b2b', (\n"
		"    f'Roundtrip failed: expected #2b2b2b, got {dark_bg}'\n"
		")\n"
		"print('PASS')\n"
		"app.quit()\n"
	)
	result = subprocess.run(
		[sys.executable, "-c", code],
		capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT,
		cwd=_CWD,
		env=_ENV,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout
