"""Canvas, scene, and view initialization for MainWindow."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.scene
import bkchem_qt.canvas.view
import bkchem_qt.config.geometry_units
import bkchem_qt.config.preferences
import bkchem_qt.themes.theme_loader
import bkchem_qt.canvas.items.render_ops_painter


#============================================
def setup_canvas(
		window: object, theme_manager: object, prefs: object, document: object,
		) -> tuple:
	"""Create the scene, view, and tab widget for the central area.

	Args:
		window: The MainWindow instance (used as parent and for tr()).
		theme_manager: ThemeManager for current theme lookup.
		prefs: Preferences singleton.
		document: The active Document instance.

	Returns:
		Tuple of (scene, view, tab_widget).
	"""
	scene, view = create_canvas(
		window, theme_manager, prefs, document,
	)

	# wrap the view in a tab widget for multi-document support
	tab_widget = PySide6.QtWidgets.QTabWidget(window)
	tab_widget.addTab(view, window.tr("Untitled"))
	window.setCentralWidget(tab_widget)

	return scene, view, tab_widget


#============================================
def create_canvas(
		view_parent: PySide6.QtWidgets.QWidget | None, theme_manager: object,
		prefs: object, document: object,
		owner: PySide6.QtCore.QObject | None = None,
		) -> tuple:
	"""Create one document's scene and tab-ready view without window wiring.

	This is the session-safe portion of :func:`setup_canvas`.  ``view_parent``
	is a QWidget because the view may be inserted directly into a QTabWidget.
	``owner`` is a QObject (normally a DocumentSession) that owns the scene;
	it deliberately need not be the widget parent.

	Args:
		view_parent: QWidget that initially parents the ChemView, or None.
		theme_manager: ThemeManager for current theme lookup.
		prefs: Preferences singleton.
		document: Document to wire to the new scene and view.
		owner: Optional QObject owner for the scene.

	Returns:
		Tuple of (scene, view).  The view is suitable as a QTabWidget page.
	"""
	theme = theme_manager.current_theme
	bond_length_pt = bkchem_qt.config.geometry_units.resolve_bond_length_pt(
		prefs
	)
	grid_snap_enabled = bool(prefs.value(
		bkchem_qt.config.preferences.Preferences.KEY_GRID_SNAP_ENABLED,
		True,
	))
	scene = bkchem_qt.canvas.scene.ChemScene(
		parent=owner if owner is not None else view_parent,
		theme_name=theme,
		grid_spacing_pt=bond_length_pt,
		grid_snap_enabled=grid_snap_enabled,
	)
	view = bkchem_qt.canvas.view.ChemView(scene, parent=view_parent)
	# wire the document so modes can access undo stack and molecules
	view.set_document(document)
	# wire scene into document for selection query forwarding
	document.set_scene(scene)

	# set initial viewport background from YAML theme
	surround = bkchem_qt.themes.theme_loader.get_canvas_surround(theme)
	view.set_background_color(surround)

	# apply chemistry and canvas colors from theme
	_apply_theme_colors(theme)
	return scene, view


#============================================
def _apply_theme_colors(theme: str) -> None:
	"""Apply chemistry and canvas colors from the YAML theme.

	Args:
		theme: Theme name string (e.g. 'light' or 'dark').
	"""
	# set default chemistry line color from YAML theme
	chem_colors = bkchem_qt.themes.theme_loader.get_chemistry_colors(theme)
	bkchem_qt.canvas.items.render_ops_painter.set_default_color(
		chem_colors["default_line"]
	)
	# set default area color for atom label background masking
	bkchem_qt.canvas.items.render_ops_painter.set_default_area_color(
		chem_colors["default_area"]
	)
	# set canvas interaction colors from YAML theme
	canvas_colors = bkchem_qt.themes.theme_loader.get_canvas_colors(theme)
	bkchem_qt.canvas.items.render_ops_painter.set_canvas_colors(canvas_colors)
	# set charge mark colors from YAML theme
	bkchem_qt.canvas.items.render_ops_painter.set_charge_colors({
		"plus": chem_colors["charge_plus"],
		"minus": chem_colors["charge_minus"],
	})
	# set the light theme sentinel for dark mode color remapping
	light_chem = bkchem_qt.themes.theme_loader.get_chemistry_colors("light")
	bkchem_qt.canvas.items.render_ops_painter.set_light_default_line(
		light_chem["default_line"]
	)
