"""Tests for the ThemeChooserDialog and theme apply/cancel flows."""

# local repo modules
import bkchem_qt.dialogs.theme_chooser_dialog


#============================================
def test_theme_dialog_lists_themes(main_window: object) -> None:
	"""Create a ThemeChooserDialog and verify themes are listed."""
	dialog = bkchem_qt.dialogs.theme_chooser_dialog.ThemeChooserDialog(
		"light", parent=main_window,
	)
	count = dialog._list_widget.count()
	assert count > 0, (
		f"theme list should have entries, got {count}"
	)


#============================================
def test_theme_dialog_preselects_current(main_window: object) -> None:
	"""Create dialog with current='light' and verify it is preselected."""
	dialog = bkchem_qt.dialogs.theme_chooser_dialog.ThemeChooserDialog(
		"light", parent=main_window,
	)
	current_item = dialog._list_widget.currentItem()
	assert current_item is not None, (
		"a theme should be preselected"
	)
	assert current_item.text() == "light", (
		f"expected 'light' preselected, got {current_item.text()!r}"
	)


#============================================
def test_theme_apply_changes_theme(main_window: object, monkeypatch: object) -> None:
	"""Monkeypatch choose_theme to return opposite theme, verify change."""
	tm = main_window._theme_manager
	# determine target theme (opposite of current)
	current = tm.current_theme
	if current == "dark":
		target = "light"
	else:
		target = "dark"

	# monkeypatch the static choose_theme to return the target
	monkeypatch.setattr(
		bkchem_qt.dialogs.theme_chooser_dialog.ThemeChooserDialog,
		"choose_theme",
		staticmethod(lambda parent, cur: target),
	)
	# call the handler that opens the dialog
	main_window._on_choose_theme()
	assert tm.current_theme == target, (
		f"expected theme to change to {target!r}, "
		f"got {tm.current_theme!r}"
	)


#============================================
def test_theme_cancel_no_change(main_window: object, monkeypatch: object) -> None:
	"""Monkeypatch choose_theme to return None, verify no change."""
	tm = main_window._theme_manager
	original = tm.current_theme

	# monkeypatch the static choose_theme to return None (cancel)
	monkeypatch.setattr(
		bkchem_qt.dialogs.theme_chooser_dialog.ThemeChooserDialog,
		"choose_theme",
		staticmethod(lambda parent, cur: None),
	)
	# call the handler that opens the dialog
	main_window._on_choose_theme()
	assert tm.current_theme == original, (
		f"theme should remain {original!r} after cancel, "
		f"got {tm.current_theme!r}"
	)
