"""Test that ThemeManager toggle switches palette colors to match YAML values.

Verifies that apply_theme changes the QPalette Window color to match the
YAML gui.background value for each theme.

Usage:
	source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_qt_theme_toggle_runtime.py -v
"""

# PIP3 modules
import PySide6.QtGui


#============================================
def test_theme_toggle_changes_palette(qapp: object, theme_manager: object) -> None:
	"""Verify apply_theme switches palette Window color to match YAML values."""
	# apply dark theme and check palette
	theme_manager.apply_theme('dark')
	dark_bg = qapp.palette().color(
		PySide6.QtGui.QPalette.ColorRole.Window
	).name()
	assert dark_bg == '#2b2b2b', f'Expected #2b2b2b, got {dark_bg}'
	# switch to light and check
	theme_manager.apply_theme('light')
	light_bg = qapp.palette().color(
		PySide6.QtGui.QPalette.ColorRole.Window
	).name()
	assert light_bg == '#eaeaea', f'Expected #eaeaea, got {light_bg}'


#============================================
def test_theme_toggle_roundtrip(qapp: object, theme_manager: object) -> None:
	"""Verify dark -> light -> dark roundtrip preserves palette colors."""
	theme_manager.apply_theme('dark')
	theme_manager.apply_theme('light')
	theme_manager.apply_theme('dark')
	dark_bg = qapp.palette().color(
		PySide6.QtGui.QPalette.ColorRole.Window
	).name()
	assert dark_bg == '#2b2b2b', f'Roundtrip failed: expected #2b2b2b, got {dark_bg}'
