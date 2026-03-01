"""Test that YAML-driven menu builder creates all 10 menus."""

# Standard Library
import os
import sys
import subprocess


#============================================
def test_menu_bar_has_ten_menus():
	"""Verify 10 top-level menus are created from menus.yaml."""
	code = '''
import PySide6.QtWidgets
app = PySide6.QtWidgets.QApplication([])
import bkchem_qt.themes.theme_manager
mgr = bkchem_qt.themes.theme_manager.ThemeManager(app)
mgr.apply_theme("light")
import bkchem_qt.main_window
win = bkchem_qt.main_window.MainWindow(mgr)
menubar = win.menuBar()
menus = []
for action in menubar.actions():
	if action.menu() is not None:
		menus.append(action.text().replace("&", ""))
print("MENU_COUNT=" + str(len(menus)))
print("MENUS=" + "|".join(menus))
# expect at least 10 menus from YAML
assert len(menus) >= 10, f"Expected 10+ menus, got {len(menus)}: {menus}"
# verify YAML order for the first 10
expected = ["File", "Edit", "Insert", "Align", "Object",
            "View", "Chemistry", "Repair", "Options", "Help"]
for i, name in enumerate(expected):
	assert menus[i] == name, f"Menu {i}: expected {name!r}, got {menus[i]!r}"
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
