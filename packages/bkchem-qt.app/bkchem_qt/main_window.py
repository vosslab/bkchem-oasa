"""Main application window for BKChem-Qt."""

# Standard Library
import pathlib

# PIP3 modules
import yaml
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.scene
import bkchem_qt.canvas.view
from bkchem_qt.canvas.view import ZOOM_FACTOR_PER_NOTCH
import bkchem_qt.config.preferences
import bkchem_qt.widgets.status_bar
import bkchem_qt.widgets.mode_toolbar
import bkchem_qt.widgets.edit_ribbon
import bkchem_qt.widgets.toolbar
import bkchem_qt.widgets.icon_loader
import bkchem_qt.modes.mode_manager
import bkchem_qt.modes.template_mode
import bkchem_qt.modes.arrow_mode
import bkchem_qt.modes.text_mode
import bkchem_qt.modes.mark_mode
import bkchem_qt.modes.atom_mode
import bkchem_qt.modes.rotate_mode
import bkchem_qt.modes.bondalign_mode
import bkchem_qt.modes.bracket_mode
import bkchem_qt.modes.vector_mode
import bkchem_qt.modes.repair_mode
import bkchem_qt.modes.plus_mode
import bkchem_qt.modes.misc_mode
import bkchem_qt.actions.file_actions
import bkchem_qt.actions.context_menu
import bkchem_qt.io.cdml_io
import bkchem_qt.dialogs.about_dialog
import bkchem_qt.dialogs.preferences_dialog
import bkchem_qt.models.document
import bkchem_qt.io.export
import bkchem_qt.themes.palettes
import bkchem_qt.themes.theme_loader

# path to modes.yaml in the shared bkchem_data directory
_MODES_YAML_PATH = (
	pathlib.Path(__file__).resolve().parent.parent
	/ "bkchem_data" / "modes.yaml"
)


#============================================
class MainWindow(PySide6.QtWidgets.QMainWindow):
	"""Main application window with menus, canvas, toolbar, and status bar.

	Args:
		theme_manager: ThemeManager instance for toggling themes.
	"""

	#============================================
	def __init__(self, theme_manager, parent: PySide6.QtWidgets.QWidget = None):
		"""Initialize the main window with all UI components.

		Args:
			theme_manager: ThemeManager instance for theme toggling.
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self._theme_manager = theme_manager
		self._prefs = bkchem_qt.config.preferences.Preferences.instance()
		self._document = bkchem_qt.models.document.Document(self)

		self.setWindowTitle(self.tr("BKChem-Qt"))
		self.resize(1200, 800)

		# build the UI components
		self._setup_canvas()
		self._setup_mode_system()
		self._setup_menus()
		self._setup_toolbars()
		self._setup_status_bar()
		self._connect_signals()

	#============================================
	@property
	def document(self):
		"""The active document."""
		return self._document

	#============================================
	@property
	def scene(self):
		"""The active graphics scene."""
		return self._scene

	#============================================
	@property
	def view(self):
		"""The active graphics view."""
		return self._view

	#============================================
	def _setup_canvas(self) -> None:
		"""Create the scene, view, and tab widget for the central area."""
		theme = self._theme_manager.current_theme
		self._scene = bkchem_qt.canvas.scene.ChemScene(
			parent=self, theme_name=theme,
		)
		self._view = bkchem_qt.canvas.view.ChemView(self._scene, parent=self)
		# wire the document so modes can access undo stack and molecules
		self._view.set_document(self._document)

		# set initial viewport background from YAML theme
		surround = bkchem_qt.themes.theme_loader.get_canvas_surround(theme)
		self._view.set_background_color(surround)

		# wrap the view in a tab widget for multi-document support
		self._tab_widget = PySide6.QtWidgets.QTabWidget(self)
		self._tab_widget.addTab(self._view, self.tr("Untitled"))
		self.setCentralWidget(self._tab_widget)

	#============================================
	def _setup_mode_system(self) -> None:
		"""Create and register all interaction modes."""
		self._mode_manager = bkchem_qt.modes.mode_manager.ModeManager(
			self._view, parent=self
		)
		# register additional modes beyond the default edit/draw
		self._mode_manager.register_mode(
			"template",
			bkchem_qt.modes.template_mode.TemplateMode(self._view),
		)
		self._mode_manager.register_mode(
			"arrow",
			bkchem_qt.modes.arrow_mode.ArrowMode(self._view),
		)
		self._mode_manager.register_mode(
			"text",
			bkchem_qt.modes.text_mode.TextMode(self._view),
		)
		self._mode_manager.register_mode(
			"rotate",
			bkchem_qt.modes.rotate_mode.RotateMode(self._view),
		)
		self._mode_manager.register_mode(
			"mark",
			bkchem_qt.modes.mark_mode.MarkMode(self._view),
		)
		self._mode_manager.register_mode(
			"atom",
			bkchem_qt.modes.atom_mode.AtomMode(self._view),
		)
		self._mode_manager.register_mode(
			"align",
			bkchem_qt.modes.bondalign_mode.BondAlignMode(self._view),
		)
		self._mode_manager.register_mode(
			"bracket",
			bkchem_qt.modes.bracket_mode.BracketMode(self._view),
		)
		self._mode_manager.register_mode(
			"vector",
			bkchem_qt.modes.vector_mode.VectorMode(self._view),
		)
		self._mode_manager.register_mode(
			"repair",
			bkchem_qt.modes.repair_mode.RepairMode(self._view),
		)
		self._mode_manager.register_mode(
			"plus",
			bkchem_qt.modes.plus_mode.PlusMode(self._view),
		)
		self._mode_manager.register_mode(
			"misc",
			bkchem_qt.modes.misc_mode.MiscMode(self._view),
		)
		# connect the mode manager to the view for event dispatch
		self._view.set_mode_manager(self._mode_manager)

	#============================================
	def _setup_menus(self) -> None:
		"""Create the menu bar from YAML menu structure and action registry."""
		from bkchem_qt.actions.action_registry import register_all_actions
		from bkchem_qt.actions.platform_menu import PlatformMenuAdapter
		from bkchem_qt.actions.menu_builder import MenuBuilder
		# register all per-menu action modules
		self._registry = register_all_actions(self)
		# create the Qt menu adapter wrapping QMenuBar
		self._adapter = PlatformMenuAdapter(self)
		# locate menus.yaml in the shared bkchem_data directory
		yaml_path = str(
			pathlib.Path(__file__).resolve().parent.parent
			/ "bkchem_data" / "menus.yaml"
		)
		# build all menus from YAML structure
		self._menu_builder = MenuBuilder(
			yaml_path, self._registry, self._adapter,
		)
		self._menu_builder.build_menus()
		# populate the Export cascade with export handlers
		export_cascade_label = "Export"
		self._adapter.add_command_to_cascade(
			export_cascade_label, "Export SVG...",
			"Export the current document as SVG",
			self._on_export_svg,
		)
		self._adapter.add_command_to_cascade(
			export_cascade_label, "Export PNG...",
			"Export the current document as PNG",
			self._on_export_png,
		)
		self._adapter.add_command_to_cascade(
			export_cascade_label, "Export PDF...",
			"Export the current document as PDF",
			self._on_export_pdf,
		)
		# backward compatibility aliases for existing code references
		self._action_save = self._adapter.get_action("File", "Save")
		self._action_open = self._adapter.get_action("File", "Open")
		self._action_new = self._adapter.get_action("File", "New")
		self._action_exit = self._adapter.get_action("File", "Quit")
		self._action_undo = self._adapter.get_action("Edit", "Undo")
		self._action_redo = self._adapter.get_action("Edit", "Redo")
		self._action_toggle_theme = self._adapter.get_action("Options", "Theme")
		self._action_about = self._adapter.get_action("Help", "About")
		# grid toggle is not in menus.yaml (it is a view feature)
		# create it as a standalone checkable action
		view_menu = self._adapter.get_menu_component("View")
		if view_menu is not None:
			view_menu.addSeparator()
			self._action_toggle_grid = view_menu.addAction(
				self.tr("Toggle &Grid")
			)
			self._action_toggle_grid.setCheckable(True)
			self._action_toggle_grid.setChecked(self._scene.grid_visible)
			self._action_toggle_grid.triggered.connect(self._on_toggle_grid)

	#============================================
	def _setup_menus_legacy(self) -> None:
		"""Create the menu bar and all menu actions (legacy manual approach).

		Retained for reference. Use _setup_menus() for the YAML-driven version.
		"""
		menubar = self.menuBar()

		# -- File menu --
		file_menu = menubar.addMenu(self.tr("&File"))

		self._action_new = file_menu.addAction(self.tr("&New"))
		self._action_new.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.New)
		self._action_new.triggered.connect(self._on_new)

		self._action_open = file_menu.addAction(self.tr("&Open..."))
		self._action_open.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Open)
		self._action_open.triggered.connect(self._on_open)

		self._action_save = file_menu.addAction(self.tr("&Save"))
		self._action_save.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Save)
		self._action_save.triggered.connect(self._on_save)

		file_menu.addSeparator()

		# export submenu
		export_menu = file_menu.addMenu(self.tr("&Export"))
		self._action_export_svg = export_menu.addAction(self.tr("Export &SVG..."))
		self._action_export_svg.triggered.connect(self._on_export_svg)
		self._action_export_png = export_menu.addAction(self.tr("Export &PNG..."))
		self._action_export_png.triggered.connect(self._on_export_png)
		self._action_export_pdf = export_menu.addAction(self.tr("Export P&DF..."))
		self._action_export_pdf.triggered.connect(self._on_export_pdf)

		file_menu.addSeparator()

		self._action_exit = file_menu.addAction(self.tr("E&xit"))
		self._action_exit.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Quit)
		self._action_exit.triggered.connect(self.close)

		# -- Edit menu --
		edit_menu = menubar.addMenu(self.tr("&Edit"))

		self._action_undo = edit_menu.addAction(self.tr("&Undo"))
		self._action_undo.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Undo)
		self._action_undo.triggered.connect(self._document.undo_stack.undo)

		self._action_redo = edit_menu.addAction(self.tr("&Redo"))
		self._action_redo.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Redo)
		self._action_redo.triggered.connect(self._document.undo_stack.redo)

		edit_menu.addSeparator()

		self._action_preferences = edit_menu.addAction(self.tr("&Preferences..."))
		self._action_preferences.triggered.connect(self._on_preferences)

		# -- View menu --
		view_menu = menubar.addMenu(self.tr("&View"))

		self._action_toggle_grid = view_menu.addAction(self.tr("Toggle &Grid"))
		self._action_toggle_grid.setCheckable(True)
		self._action_toggle_grid.setChecked(self._scene.grid_visible)
		self._action_toggle_grid.triggered.connect(self._on_toggle_grid)

		# theme toggle with text reflecting current state
		if self._theme_manager.current_theme == "dark":
			theme_label = self.tr("Switch to &Light Mode")
		else:
			theme_label = self.tr("Switch to &Dark Mode")
		self._action_toggle_theme = view_menu.addAction(theme_label)
		self._action_toggle_theme.triggered.connect(self._on_toggle_theme)

		view_menu.addSeparator()

		self._action_reset_zoom = view_menu.addAction(self.tr("&Reset Zoom"))
		self._action_reset_zoom.setShortcut(
			PySide6.QtGui.QKeySequence(self.tr("Ctrl+0"))
		)
		self._action_reset_zoom.triggered.connect(self._view.reset_zoom)

		# -- Insert menu (stub) --
		menubar.addMenu(self.tr("&Insert"))

		# -- Align menu (stub) --
		menubar.addMenu(self.tr("&Align"))

		# -- Object menu (stub) --
		menubar.addMenu(self.tr("&Object"))

		# -- Chemistry menu (stub) --
		menubar.addMenu(self.tr("C&hemistry"))

		# -- Options menu (stub) --
		menubar.addMenu(self.tr("&Options"))

		# -- Help menu --
		help_menu = menubar.addMenu(self.tr("&Help"))

		self._action_about = help_menu.addAction(self.tr("&About"))
		self._action_about.triggered.connect(self._on_about)

	#============================================
	def _setup_toolbars(self) -> None:
		"""Create the main toolbar, mode toolbar, and edit ribbon.

		The mode toolbar is placed horizontally after the main toolbar,
		using the toolbar_order from modes.yaml for mode sequencing and
		separator placement. Icons are loaded from pixmaps via icon_loader.
		"""
		# validate icon data directory before loading any icons
		bkchem_qt.widgets.icon_loader.validate_icon_paths()
		# sync icon_loader with the current theme
		bkchem_qt.widgets.icon_loader.set_theme(self._theme_manager.current_theme)

		# main action toolbar (file/edit/view buttons)
		self._main_toolbar = bkchem_qt.widgets.toolbar.MainToolbar(self)
		self._main_toolbar.setup_actions(self)
		self.addToolBar(self._main_toolbar)

		# load modes.yaml for toolbar_order and icon mappings
		if not _MODES_YAML_PATH.is_file():
			raise FileNotFoundError(
				f"modes.yaml not found: {_MODES_YAML_PATH}\n"
				"Check that the bkchem_data symlink is correct."
			)
		with open(_MODES_YAML_PATH, "r") as fh:
			modes_config = yaml.safe_load(fh) or {}

		toolbar_order = modes_config.get("toolbar_order", [])
		modes_defs = modes_config.get("modes", {})

		# mode selection toolbar - horizontal on top (after main toolbar)
		self._mode_toolbar = bkchem_qt.widgets.mode_toolbar.ModeToolbar(self)
		registered_modes = set(self._mode_manager.mode_names())

		for entry in toolbar_order:
			# separator marker in modes.yaml
			if entry == "---":
				self._mode_toolbar.add_separator_marker()
				continue
			# look up the mode definition for label and icon name
			mode_def = modes_defs.get(entry, {})
			label = mode_def.get("label", mode_def.get("name", entry))
			icon_name = mode_def.get("icon", entry)
			icon = bkchem_qt.widgets.icon_loader.get_icon(icon_name)
			tooltip = label.capitalize()
			# only add if the mode is registered in the mode manager
			# (some yaml modes like biotemplate/usertemplate may not be registered yet)
			if entry in registered_modes:
				self._mode_toolbar.add_mode(entry, label, tooltip=tooltip, icon=icon)
			elif entry == "bondalign" and "align" in registered_modes:
				# modes.yaml calls it bondalign, mode_manager registers it as align
				self._mode_toolbar.add_mode("align", label, tooltip=tooltip, icon=icon)

		self._mode_toolbar.set_active_mode("edit")
		# force mode toolbar onto its own row below the main toolbar
		self.addToolBarBreak()
		self.addToolBar(self._mode_toolbar)

		# edit ribbon on its own row below mode toolbar
		self.addToolBarBreak()
		self._edit_ribbon = bkchem_qt.widgets.edit_ribbon.EditRibbon(self)
		ribbon_toolbar = self.addToolBar(self.tr("Edit Ribbon"))
		ribbon_toolbar.addWidget(self._edit_ribbon)
		ribbon_toolbar.setMovable(False)

	#============================================
	def _setup_status_bar(self) -> None:
		"""Create and install the status bar."""
		self._status_bar = bkchem_qt.widgets.status_bar.StatusBar(self)
		self.setStatusBar(self._status_bar)

	#============================================
	def _connect_signals(self) -> None:
		"""Wire all signals between components."""
		# view signals -> status bar
		self._view.mouse_moved.connect(self._status_bar.update_coords)
		self._view.zoom_changed.connect(self._status_bar.update_zoom)

		# mode toolbar -> mode manager
		self._mode_toolbar.mode_selected.connect(self._mode_manager.set_mode)
		self._mode_manager.mode_changed.connect(self._mode_toolbar.set_active_mode)
		self._mode_manager.mode_changed.connect(self._status_bar.update_mode)

		# edit ribbon -> draw mode
		self._edit_ribbon.element_changed.connect(self._on_element_changed)
		self._edit_ribbon.bond_order_changed.connect(self._on_bond_order_changed)
		self._edit_ribbon.bond_type_changed.connect(self._on_bond_type_changed)

		# theme changes -> icon refresh and menu text update
		self._theme_manager.theme_changed.connect(self._on_theme_changed)

	# ------------------------------------------------------------------
	# Public toolbar action methods (used by widgets/toolbar.py via getattr)
	# ------------------------------------------------------------------

	#============================================
	def on_new(self) -> None:
		"""Public wrapper for toolbar New button."""
		self._on_new()

	#============================================
	def on_open(self) -> None:
		"""Public wrapper for toolbar Open button."""
		self._on_open()

	#============================================
	def on_save(self) -> None:
		"""Public wrapper for toolbar Save button."""
		self._on_save()

	#============================================
	def on_undo(self) -> None:
		"""Public wrapper for toolbar Undo button."""
		self._document.undo_stack.undo()

	#============================================
	def on_redo(self) -> None:
		"""Public wrapper for toolbar Redo button."""
		self._document.undo_stack.redo()

	#============================================
	def on_cut(self) -> None:
		"""Cut: not yet implemented."""
		self.statusBar().showMessage(self.tr("Cut: not yet implemented"), 3000)

	#============================================
	def on_copy(self) -> None:
		"""Copy: not yet implemented."""
		self.statusBar().showMessage(self.tr("Copy: not yet implemented"), 3000)

	#============================================
	def on_paste(self) -> None:
		"""Paste: not yet implemented."""
		self.statusBar().showMessage(self.tr("Paste: not yet implemented"), 3000)

	#============================================
	def on_zoom_in(self) -> None:
		"""Zoom in on the canvas."""
		self._view.scale(ZOOM_FACTOR_PER_NOTCH, ZOOM_FACTOR_PER_NOTCH)
		self._view._zoom_percent *= ZOOM_FACTOR_PER_NOTCH
		self._view.zoom_changed.emit(self._view._zoom_percent)

	#============================================
	def on_zoom_out(self) -> None:
		"""Zoom out on the canvas."""
		factor = 1.0 / ZOOM_FACTOR_PER_NOTCH
		self._view.scale(factor, factor)
		self._view._zoom_percent *= factor
		self._view.zoom_changed.emit(self._view._zoom_percent)

	#============================================
	def on_reset_zoom(self) -> None:
		"""Reset zoom to 100%."""
		self._view.reset_zoom()

	#============================================
	def on_toggle_grid(self) -> None:
		"""Toggle grid visibility from toolbar."""
		current = self._scene.grid_visible
		self._on_toggle_grid(not current)
		# keep the menu action checkmark in sync
		self._action_toggle_grid.setChecked(not current)

	# ------------------------------------------------------------------
	# Private action handlers
	# ------------------------------------------------------------------

	#============================================
	def _on_new(self) -> None:
		"""Create a new empty document, prompting to save if dirty."""
		# check for unsaved changes before clearing
		if self._document.dirty:
			reply = PySide6.QtWidgets.QMessageBox.question(
				self,
				self.tr("Unsaved Changes"),
				self.tr("Save changes before creating a new document?"),
				(PySide6.QtWidgets.QMessageBox.StandardButton.Save
				 | PySide6.QtWidgets.QMessageBox.StandardButton.Discard
				 | PySide6.QtWidgets.QMessageBox.StandardButton.Cancel),
				PySide6.QtWidgets.QMessageBox.StandardButton.Save,
			)
			if reply == PySide6.QtWidgets.QMessageBox.StandardButton.Cancel:
				return
			if reply == PySide6.QtWidgets.QMessageBox.StandardButton.Save:
				self._on_save()
		self._scene.clear()
		self._scene._build_paper()
		self._scene._build_grid()
		self._document = bkchem_qt.models.document.Document(self)
		# re-wire so modes access the new document
		self._view.set_document(self._document)
		self._tab_widget.setTabText(0, self.tr("Untitled"))

	#============================================
	def _on_open(self) -> None:
		"""Open a file via file dialog."""
		bkchem_qt.actions.file_actions.open_file(self)

	#============================================
	def _on_save(self) -> None:
		"""Save the current document to a CDML file.

		If the document has a file path, saves directly. Otherwise
		prompts for a save location via file dialog.
		"""
		file_path = self._document.file_path
		if not file_path:
			file_path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
				self, self.tr("Save CDML File"), "",
				self.tr("CDML Files (*.cdml);;All Files (*)"),
			)[0]
			if not file_path:
				return
		bkchem_qt.io.cdml_io.save_cdml_file(file_path, self._document)
		self._document.file_path = file_path
		self._document.dirty = False
		self._tab_widget.setTabText(0, self._document.title())
		self.statusBar().showMessage(
			self.tr("Saved: %s") % file_path, 3000,
		)

	#============================================
	def _on_export_svg(self) -> None:
		"""Export scene to SVG."""
		path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Export SVG"), "", self.tr("SVG Files (*.svg)")
		)[0]
		if path:
			bkchem_qt.io.export.export_svg(self._scene, path)

	#============================================
	def _on_export_png(self) -> None:
		"""Export scene to PNG."""
		path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Export PNG"), "", self.tr("PNG Files (*.png)")
		)[0]
		if path:
			bkchem_qt.io.export.export_png(self._scene, path)

	#============================================
	def _on_export_pdf(self) -> None:
		"""Export scene to PDF."""
		path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Export PDF"), "", self.tr("PDF Files (*.pdf)")
		)[0]
		if path:
			bkchem_qt.io.export.export_pdf(self._scene, path)

	#============================================
	def _on_toggle_grid(self, checked: bool) -> None:
		"""Toggle the grid visibility on the scene.

		Args:
			checked: Whether the grid action is checked.
		"""
		self._scene.set_grid_visible(checked)
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_VISIBLE, checked
		)

	#============================================
	def _on_toggle_theme(self) -> None:
		"""Toggle between dark and light themes."""
		self._theme_manager.toggle_theme()

	#============================================
	def _on_theme_changed(self, theme_name: str) -> None:
		"""Handle a theme change by refreshing icons and updating menu text.

		Args:
			theme_name: The new theme name ('dark' or 'light').
		"""
		# update icon_loader theme and clear cache
		bkchem_qt.widgets.icon_loader.set_theme(theme_name)
		bkchem_qt.widgets.icon_loader.reload_icons()

		# refresh toolbar icons from new theme
		self._main_toolbar.refresh_icons()

		# refresh mode toolbar icons
		modes_config = {}
		if _MODES_YAML_PATH.is_file():
			with open(_MODES_YAML_PATH, "r") as fh:
				modes_config = yaml.safe_load(fh) or {}
		modes_defs = modes_config.get("modes", {})
		for name, action in self._mode_toolbar._actions.items():
			# look up the icon name from modes.yaml
			mode_def = modes_defs.get(name, {})
			icon_name = mode_def.get("icon", name)
			icon = bkchem_qt.widgets.icon_loader.get_icon(icon_name)
			self._mode_toolbar.update_action_icon(name, icon)

		# update canvas viewport and paper/grid colors from YAML theme
		bkchem_qt.themes.theme_loader.clear_cache()
		surround = bkchem_qt.themes.theme_loader.get_canvas_surround(theme_name)
		self._view.set_background_color(surround)
		self._scene.apply_theme(theme_name)

		# theme menu text is static ("Theme") since it toggles

	#============================================
	def _on_preferences(self) -> None:
		"""Show the preferences dialog."""
		bkchem_qt.dialogs.preferences_dialog.PreferencesDialog.show_preferences(self)

	#============================================
	def _on_about(self) -> None:
		"""Show the About dialog."""
		bkchem_qt.dialogs.about_dialog.AboutDialog.show_about(self)

	#============================================
	def _on_element_changed(self, symbol: str) -> None:
		"""Forward element change from ribbon to draw mode.

		Args:
			symbol: New element symbol.
		"""
		mode = self._mode_manager.current_mode
		if hasattr(mode, 'current_element'):
			mode.current_element = symbol

	#============================================
	def _on_bond_order_changed(self, order: int) -> None:
		"""Forward bond order change from ribbon to draw mode.

		Args:
			order: New bond order.
		"""
		mode = self._mode_manager.current_mode
		if hasattr(mode, 'current_bond_order'):
			mode.current_bond_order = order

	#============================================
	def _on_bond_type_changed(self, bond_type: str) -> None:
		"""Forward bond type change from ribbon to draw mode.

		Args:
			bond_type: New bond type character.
		"""
		mode = self._mode_manager.current_mode
		if hasattr(mode, 'current_bond_type'):
			mode.current_bond_type = bond_type

	#============================================
	def restore_geometry(self) -> None:
		"""Restore window geometry from saved preferences.

		Only restores window size and position, not toolbar state,
		because toolbar layout changes between versions would conflict
		with stale saved state.
		"""
		geometry = self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_WINDOW_GEOMETRY
		)
		if geometry is not None:
			self.restoreGeometry(geometry)

	#============================================
	def closeEvent(self, event: PySide6.QtGui.QCloseEvent) -> None:
		"""Save window geometry and state before closing.

		Args:
			event: The close event.
		"""
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_WINDOW_GEOMETRY,
			self.saveGeometry(),
		)
		super().closeEvent(event)
