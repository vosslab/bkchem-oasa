"""Test that YAML-driven menu builder creates cascade submenus."""

# Standard Library
import os
import sys
import subprocess


#============================================
def test_file_menu_has_three_cascades():
	"""Verify Recent files, Export, and Import cascades exist under File."""
	code = '''
import PySide6.QtWidgets
app = PySide6.QtWidgets.QApplication([])
import bkchem_qt.themes.theme_manager
mgr = bkchem_qt.themes.theme_manager.ThemeManager(app)
mgr.apply_theme("light")
import bkchem_qt.main_window
win = bkchem_qt.main_window.MainWindow(mgr)
# access cascade names through the adapter's internal menu registry
# this avoids Qt object lifetime issues with temporary QAction wrappers
adapter = win._adapter
cascade_names = []
for name, menu in adapter._menus.items():
	# cascades are submenus that also appear as keys in _menus
	# check if this menu is a child of the File menu
	parent = menu.parent()
	if parent is not None:
		parent_title = getattr(parent, "title", lambda: "")()
		if parent_title.replace("&", "") == "File" or name in ("Recent files", "Export", "Import"):
			cascade_names.append(name)
# also verify using the MenuBuilder's cascade tracking
builder_cascades = win._menu_builder._cascade_names
print("BUILDER_CASCADES=" + "|".join(sorted(builder_cascades)))
print("ADAPTER_CASCADES=" + "|".join(sorted(cascade_names)))
assert "Recent files" in builder_cascades, f"Missing Recent files: {builder_cascades}"
assert "Export" in builder_cascades, f"Missing Export: {builder_cascades}"
assert "Import" in builder_cascades, f"Missing Import: {builder_cascades}"
print("PASS")
app.quit()
'''
	result = subprocess.run(
		[sys.executable, "-c", code],
		capture_output=True, text=True, timeout=30,
		cwd="packages/bkchem-qt.app",
		env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
	)
	assert result.returncode == 0, (
		f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
	)
	assert "PASS" in result.stdout
