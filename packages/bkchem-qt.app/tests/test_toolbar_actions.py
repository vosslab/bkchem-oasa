"""Tests for Patch 2: Toolbar action naming -- all on_* methods resolve."""

# Standard Library
import subprocess
import sys
import textwrap


#============================================
def _check_subprocess_result(result):
	"""Assert subprocess completed successfully.

	Args:
		result: CompletedProcess from subprocess.run().
	"""
	if result.returncode != 0:
		msg = result.stdout + "\n" + result.stderr
		raise AssertionError(f"Subprocess failed (rc={result.returncode}):\n{msg}")


# all toolbar action names that toolbar.py looks up via getattr
_TOOLBAR_ACTION_NAMES = [
	"on_new",
	"on_open",
	"on_save",
	"on_undo",
	"on_redo",
	"on_cut",
	"on_copy",
	"on_paste",
	"on_zoom_in",
	"on_zoom_out",
	"on_reset_zoom",
	"on_toggle_grid",
]


#============================================
def test_all_toolbar_actions_resolve():
	"""All 12 getattr(main_window, 'on_*') resolve to callables."""
	names_str = repr(_TOOLBAR_ACTION_NAMES)
	script = textwrap.dedent(f"""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		names = {names_str}
		for name in names:
			attr = getattr(mw, name, None)
			assert attr is not None, f"MainWindow.{{name}} should exist"
			assert callable(attr), f"MainWindow.{{name}} should be callable"
		print("PASS: all %d toolbar actions resolve" % len(names))
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout


#============================================
def test_save_action_exists_and_has_shortcut():
	"""The Save menu action exists and has a keyboard shortcut."""
	script = textwrap.dedent("""\
		import sys
		import PySide6.QtWidgets
		app = PySide6.QtWidgets.QApplication(sys.argv)
		import bkchem_qt.main_window
		import bkchem_qt.themes.theme_manager
		tm = bkchem_qt.themes.theme_manager.ThemeManager(app)
		mw = bkchem_qt.main_window.MainWindow(tm)
		assert hasattr(mw, "_action_save"), "should have _action_save"
		assert hasattr(mw, "_on_save"), "should have _on_save method"
		assert callable(mw._on_save), "_on_save should be callable"
		# verify shortcut is set
		shortcut = mw._action_save.shortcut()
		assert not shortcut.isEmpty(), "save action should have a shortcut"
		print("PASS: save action exists with shortcut")
	""")
	result = subprocess.run(
		[sys.executable, "-c", script],
		capture_output=True, text=True, timeout=30,
	)
	_check_subprocess_result(result)
	assert "PASS" in result.stdout
