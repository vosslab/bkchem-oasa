"""Test that public native menus remain usable after enumeration."""


# Standard Library
import logging
import pathlib

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.file_actions
import bkchem_qt.actions.options_actions
import bkchem_qt.config.preferences
import bkchem_qt.dialogs.preferences_dialog


#============================================
def _menu_actions(menu: object) -> tuple:
	"""Return every public action in one menu and its cascades."""
	actions = []
	for action in menu.actions():
		actions.append(action)
		submenu = action.menu()
		if submenu is not None:
			actions.extend(_menu_actions(submenu))
	return tuple(actions)


#============================================
def _menu_tree_actions(menu_bar: object) -> tuple:
	"""Return every public action in the complete recursive menu tree."""
	actions = []
	for top_level_action in menu_bar.actions():
		menu = top_level_action.menu()
		if menu is None:
			continue
		actions.extend(_menu_actions(menu))
	return tuple(actions)


#============================================
def _menu_action(actions: tuple, label: str) -> object:
	"""Return one visible action from a previously enumerated menu tree."""
	for action in actions:
		if action.text().replace("&", "") == label:
			return action
	message = "Expected visible menu action was not found: %s" % label
	raise RuntimeError(message)


#============================================
def test_enumerated_menu_action_toggles_grid(
		main_window: object, qapp: object,
		) -> None:
	"""An enumerated public Toggle Grid action remains connected and usable."""
	menu_actions = _menu_tree_actions(main_window.menuBar())
	initial_visibility = main_window.scene.grid_visible
	qapp.processEvents()
	toggle_grid = _menu_action(menu_actions, "Toggle Grid")
	toggle_grid.trigger()
	qapp.processEvents()
	assert main_window.scene.grid_visible is not initial_visibility


#============================================
def test_recent_file_menu_entry_opens_selected_document(
		main_window: object, qapp: object, tmp_path: pathlib.Path,
		monkeypatch: object,
		) -> None:
	"""A refreshed visible Recent Files entry opens its selected CDML file."""
	source = tmp_path / "recent-document.cdml"
	source.write_text(
		'<cdml version="26.07"><molecule id="m1"><atom id="a1" name="C">'
		'<point x="1cm" y="1cm"/></atom></molecule></cdml>', encoding="utf-8",
	)
	warnings = []
	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox, "warning",
		lambda _parent, title, text: warnings.append((title, text)),
	)
	prefs = bkchem_qt.config.preferences.Preferences.instance()
	previous = prefs.value(
		bkchem_qt.config.preferences.Preferences.KEY_RECENT_FILES,
	)
	try:
		bkchem_qt.actions.file_actions.push_recent_file(str(source))
		main_window.refresh_recent_files_menu()
		entry = _menu_action(_menu_tree_actions(main_window.menuBar()), source.name)
		entry.trigger()
		qapp.processEvents()
		assert any(
			session.document.file_path == str(source)
			for session in main_window.sessions
		)
		assert not warnings
	finally:
		prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_RECENT_FILES, previous,
		)
		main_window.refresh_recent_files_menu()


#============================================
def test_options_menu_exposes_document_style_and_omits_inactive_preferences(
		main_window: object, qapp: object, monkeypatch: object,
		) -> None:
	"""Options exposes authoritative style while omitting inactive promises."""
	menu_actions = _menu_tree_actions(main_window.menuBar())
	labels = {
		action.text().replace("&", "")
		for action in menu_actions
		if not action.isSeparator()
	}
	assert "Document Drawing Style..." in labels
	assert not {"Language", "InChI program path"}.intersection(labels)

	prefs = bkchem_qt.config.preferences.Preferences.instance()
	previous_preference = prefs.value(
		bkchem_qt.config.preferences.Preferences.KEY_LOGGING_LEVEL,
	)
	previous_level = logging.getLogger().level
	monkeypatch.setattr(
		PySide6.QtWidgets.QInputDialog,
		"getItem",
		staticmethod(lambda *args: ("Debug", True)),
	)
	try:
		_menu_action(menu_actions, "Logging Level...").trigger()
		qapp.processEvents()
		logging.getLogger().setLevel(logging.ERROR)
		bkchem_qt.actions.options_actions.apply_saved_logging_level(prefs)
		assert (
			logging.getLogger().level == logging.DEBUG
			and prefs.value(
				bkchem_qt.config.preferences.Preferences.KEY_LOGGING_LEVEL,
			) == "Debug"
			and "future BKChem launches" in main_window.statusBar().currentMessage()
		)
	finally:
		prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_LOGGING_LEVEL,
			previous_preference,
		)
		logging.getLogger().setLevel(previous_level)


#============================================
def test_preferences_action_applies_supported_display_settings(
		main_window: object, qapp: object, monkeypatch: object,
		) -> None:
	"""The visible Preferences action applies accepted display settings now."""
	prefs = bkchem_qt.config.preferences.Preferences.instance()
	keys = (
		bkchem_qt.config.preferences.Preferences.KEY_GRID_VISIBLE,
		bkchem_qt.config.preferences.Preferences.KEY_GRID_SNAP_ENABLED,
		bkchem_qt.config.preferences.Preferences.KEY_BOND_LENGTH_PT,
	)
	previous = tuple(prefs.value(key) for key in keys)

	def accept_with_supported_values(_parent: object) -> bool:
		"""Supply the accepted values produced by the preferences dialog."""
		prefs.set_value(keys[0], False)
		prefs.set_value(keys[1], False)
		prefs.set_value(keys[2], 52.0)
		return True

	monkeypatch.setattr(
		bkchem_qt.dialogs.preferences_dialog.PreferencesDialog,
		"show_preferences",
		staticmethod(accept_with_supported_values),
	)
	try:
		_menu_action(
			_menu_tree_actions(main_window.menuBar()), "Preferences",
		).trigger()
		qapp.processEvents()
		assert (
			not main_window.scene.grid_visible
			and not main_window.scene.grid_snap_enabled
			and "Preferences saved" in main_window.statusBar().currentMessage()
		)
	finally:
		for key, value in zip(keys, previous):
			prefs.set_value(key, value)
		main_window._apply_geometry_preferences()
		main_window._apply_view_preferences()


#============================================
def test_preferences_rejects_conflicting_shortcut_before_persisting(
		main_window: object, qapp: object, monkeypatch: object,
		) -> None:
	"""A visible Preferences Apply rejects a shortcut that would break startup."""
	dialog = bkchem_qt.dialogs.preferences_dialog.PreferencesDialog(main_window)
	prefs = bkchem_qt.config.preferences.Preferences.instance()
	previous_draw = prefs.value("keybindings/mode.draw")
	table = dialog.findChild(PySide6.QtWidgets.QTableWidget)
	if table is None:
		raise RuntimeError("Preferences dialog did not create a shortcuts table")
	edit_sequence = ""
	for row in range(table.rowCount()):
		if table.item(row, 0).text() == "mode.edit":
			edit_sequence = table.item(row, 1).text()
	if not edit_sequence:
		raise RuntimeError("Preferences dialog did not expose the edit mode shortcut")
	for row in range(table.rowCount()):
		if table.item(row, 0).text() == "mode.draw":
			table.item(row, 1).setText(edit_sequence)
	warnings = []
	monkeypatch.setattr(
		PySide6.QtWidgets.QMessageBox,
		"warning",
		staticmethod(lambda *args: warnings.append(args[2])),
	)
	buttons = dialog.findChild(PySide6.QtWidgets.QDialogButtonBox)
	if buttons is None:
		raise RuntimeError("Preferences dialog did not create an Apply button")
	buttons.button(
		PySide6.QtWidgets.QDialogButtonBox.StandardButton.Apply,
	).click()
	qapp.processEvents()
	assert (
		warnings
		and "different shortcut" in warnings[0]
		and prefs.value("keybindings/mode.draw") == previous_draw
	)


#============================================
def test_preferences_explains_when_shortcut_edits_apply(
		main_window: object,
		) -> None:
	"""Preferences presents the delivered next-launch shortcut timing."""
	dialog = bkchem_qt.dialogs.preferences_dialog.PreferencesDialog(main_window)
	labels = dialog.findChildren(PySide6.QtWidgets.QLabel)
	assert any("next time you start BKChem" in label.text() for label in labels)
