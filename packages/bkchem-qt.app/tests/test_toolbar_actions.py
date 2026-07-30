"""Tests for Patch 2: Toolbar action naming -- all on_* methods resolve."""


# all action method names used by menu action registrations
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
def test_all_toolbar_actions_resolve(main_window: object) -> None:
	"""All 12 getattr(main_window, 'on_*') resolve to callables."""
	for name in _TOOLBAR_ACTION_NAMES:
		attr = getattr(main_window, name, None)
		assert attr is not None, f"MainWindow.{name} should exist"
		assert callable(attr), f"MainWindow.{name} should be callable"


#============================================
def test_save_action_exists_and_has_shortcut(main_window: object) -> None:
	"""The Save menu action exists and has a keyboard shortcut."""
	assert hasattr(main_window, "_action_save"), "should have _action_save"
	assert hasattr(main_window, "_on_save"), "should have _on_save method"
	assert callable(main_window._on_save), "_on_save should be callable"
	# verify shortcut is set
	shortcut = main_window._action_save.shortcut()
	assert not shortcut.isEmpty(), "save action should have a shortcut"
