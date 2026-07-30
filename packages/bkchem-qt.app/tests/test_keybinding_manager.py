"""Behavior tests for the BKChem-Qt shortcut authority."""

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.config.keybindings


#============================================
def test_mode_shortcut_selects_the_session_active_at_activation(
		main_window: object,
		) -> None:
	"""A mode key changes the selected tab, not the tab active at setup."""
	first_session = main_window._active_session
	second_session = main_window._create_session(activate=True)
	main_window._keybinding_manager._shortcuts["mode.draw"].activated.emit()
	assert second_session.mode_manager.current_mode is second_session.mode_manager._modes["draw"]
	main_window._tab_widget.setCurrentIndex(0)
	main_window._keybinding_manager._shortcuts["mode.draw"].activated.emit()
	assert first_session.mode_manager.current_mode is first_session.mode_manager._modes["draw"]


#============================================
def test_duplicate_shortcut_is_rejected_without_replacing_the_binding(
		main_window: object,
		) -> None:
	"""A conflicting preference fails loudly and leaves the live mapping intact."""
	manager = main_window._keybinding_manager
	original = manager.get_binding("file.new")
	with pytest.raises(bkchem_qt.config.keybindings.KeybindingConflictError):
		manager.set_binding("file.new", manager.get_binding("file.load"))
	assert manager.get_binding("file.new") == original
