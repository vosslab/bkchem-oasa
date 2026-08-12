"""Toolbar, ribbon, and dock widget initialization for MainWindow."""

# PIP3 modules
import yaml
import PySide6.QtCore

# local repo modules
import bkchem_qt.config.keybindings
import bkchem_qt.widgets.mode_toolbar
import bkchem_qt.widgets.edit_ribbon
import bkchem_qt.widgets.zoom_controls
import bkchem_qt.widgets.submode_ribbon
import bkchem_qt.widgets.property_dock
import bkchem_qt.widgets.icon_loader
import bkchem_qt.setup.mode_setup


#============================================
def setup_toolbars(
		window: object,
		mode_manager: object,
		document: object,
		theme_manager: object,
		) -> dict[str, object]:
	"""Create the mode toolbar, submode ribbon, edit ribbon, and property dock.

	Args:
		window: The MainWindow instance.
		mode_manager: Configured ModeManager with registered modes.
		document: The active Document instance.
		theme_manager: ThemeManager for current theme.

	Returns:
		Dict with keys: mode_toolbar, submode_ribbon, submode_toolbar,
		edit_ribbon, edit_ribbon_toolbar, zoom_controls, property_dock,
		undo_action, redo_action.
	"""
	# validate icon data directory before loading any icons
	bkchem_qt.widgets.icon_loader.validate_icon_paths()
	# sync icon_loader with the current theme
	bkchem_qt.widgets.icon_loader.set_theme(theme_manager.current_theme)

	# load modes.yaml for toolbar_order and icon mappings
	modes_yaml_path = bkchem_qt.setup.mode_setup.get_modes_yaml_path()
	if not modes_yaml_path.is_file():
		raise FileNotFoundError(
			f"modes.yaml not found: {modes_yaml_path}\n"
			"Reinstall the bkchem-qt package."
		)
	with open(modes_yaml_path, "r") as fh:
		modes_config = yaml.safe_load(fh) or {}

	toolbar_order = modes_config.get("toolbar_order", [])
	modes_defs = modes_config.get("modes", {})

	# mode selection toolbar - topmost horizontal toolbar row
	mode_toolbar = bkchem_qt.widgets.mode_toolbar.ModeToolbar(window)
	registered_modes = set(mode_manager.mode_names())

	# keybindings for shortcut tooltips
	keybindings = bkchem_qt.config.keybindings.DEFAULT_KEYBINDINGS

	for entry in toolbar_order:
		# separator marker in modes.yaml
		if entry == "---":
			mode_toolbar.add_separator_marker()
			continue
		# look up the mode definition for label and icon name
		mode_def = modes_defs.get(entry, {})
		label = mode_def.get("label", mode_def.get("name", entry))
		icon_name = mode_def.get("icon", entry)
		icon = bkchem_qt.widgets.icon_loader.get_icon(icon_name)
		# build tooltip with keyboard shortcut if available
		tooltip = label.capitalize()
		shortcut = keybindings.get(f"mode.{entry}", "")
		if shortcut:
			tooltip = f"{tooltip} ({shortcut})"
		# only add if the mode is registered in the mode manager
		if entry in registered_modes:
			mode_toolbar.add_mode(entry, label, tooltip=tooltip, icon=icon)

	mode_toolbar.set_active_mode("edit")
	mode_toolbar.add_compact_chooser()

	# add separator then Undo/Redo action buttons
	mode_toolbar.add_separator_marker(collapse_in_compact=False)
	undo_action = mode_toolbar.add_action_button(
		"undo", "Undo", tooltip="Undo last action",
		callback=window.on_undo,
	)
	undo_action.setEnabled(document.undo_stack.canUndo())
	redo_action = mode_toolbar.add_action_button(
		"redo", "Redo", tooltip="Redo last undone action",
		callback=window.on_redo,
	)
	redo_action.setEnabled(document.undo_stack.canRedo())

	# mode toolbar is the topmost toolbar row
	window.addToolBar(mode_toolbar)

	# submode ribbon on its own row below mode toolbar
	window.addToolBarBreak()
	submode_ribbon = bkchem_qt.widgets.submode_ribbon.SubModeRibbon(window)
	submode_toolbar = window.addToolBar(window.tr("Submode Ribbon"))
	submode_toolbar.addWidget(submode_ribbon)
	submode_toolbar.setMovable(False)

	# edit ribbon on its own row below submode ribbon
	window.addToolBarBreak()
	edit_ribbon = bkchem_qt.widgets.edit_ribbon.EditRibbon(window)
	edit_ribbon_toolbar = window.addToolBar(window.tr("Edit Ribbon"))
	edit_ribbon_toolbar.addWidget(edit_ribbon)
	edit_ribbon_toolbar.setMovable(False)

	# property dock on the right side for atom/bond editing
	property_dock = bkchem_qt.widgets.property_dock.PropertyDock(
		document, parent=window,
	)
	window.addDockWidget(
		PySide6.QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
		property_dock,
	)

	return {
		"mode_toolbar": mode_toolbar,
		"submode_ribbon": submode_ribbon,
		"submode_toolbar": submode_toolbar,
		"edit_ribbon": edit_ribbon,
		"edit_ribbon_toolbar": edit_ribbon_toolbar,
		"property_dock": property_dock,
		"undo_action": undo_action,
		"redo_action": redo_action,
	}
