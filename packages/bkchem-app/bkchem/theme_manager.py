"""Theme management for BKChem.

Loads per-file theme definitions from the ``themes/`` directory inside
``bkchem_data`` and provides accessors for GUI chrome, chemistry content,
paper background, and hex grid colors.  Each ``.yaml`` file in that
directory is one theme; the filename (without extension) is the theme key.
The active theme preference is persisted via Store.pm.
"""

# Standard Library
import glob
import os

import yaml

from bkchem import os_support


# module-level cache, loaded lazily on first use
_THEMES = None
_ACTIVE_THEME_NAME = None

# light theme defaults used for color comparison in map_chemistry_color
_LIGHT_DEFAULT_LINE = "#000"
_LIGHT_DEFAULT_AREA = "#ffffff"


#============================================
def _load_all_themes() -> dict:
	"""Scan the themes/ directory and load every .yaml file.

	Returns:
		dict: Mapping of theme key (filename stem) to theme dict.
	"""
	data_dir = os_support._get_bkchem_data_dir()
	themes_dir = os.path.join(data_dir, 'themes')
	themes = {}
	pattern = os.path.join(themes_dir, '*.yaml')
	for path in sorted(glob.glob(pattern)):
		key = os.path.splitext(os.path.basename(path))[0]
		with open(path, 'r') as fh:
			themes[key] = yaml.safe_load(fh)
	return themes


#============================================
def _get_themes() -> dict:
	"""Return the cached themes dict, loading on first call."""
	global _THEMES
	if _THEMES is None:
		_THEMES = _load_all_themes()
	return _THEMES


#============================================
def get_theme_names() -> list:
	"""Return sorted list of available theme keys.

	Returns:
		list: Theme key strings (e.g. ['dark', 'light']).
	"""
	return sorted(_get_themes().keys())


#============================================
def get_theme(name: str) -> dict:
	"""Return the full theme dict for the given name.

	Args:
		name: Theme key (e.g. 'light' or 'dark').

	Returns:
		dict: Theme definition with gui, chemistry, paper, grid sections.
	"""
	return _get_themes()[name]


#============================================
def get_active_theme_name() -> str:
	"""Return the name of the currently active theme.

	Checks the module-level override first, then the persisted
	preference, falling back to 'light'.

	Returns:
		str: Active theme name.
	"""
	global _ACTIVE_THEME_NAME
	if _ACTIVE_THEME_NAME is not None:
		return _ACTIVE_THEME_NAME
	# try loading from preferences
	try:
		from bkchem.singleton_store import Store
		if Store.pm is not None:
			saved = Store.pm.get_preference('theme')
			if saved and saved in _get_themes():
				_ACTIVE_THEME_NAME = saved
				return saved
	except Exception:
		pass
	_ACTIVE_THEME_NAME = 'light'
	return 'light'


#============================================
def set_active_theme(name: str) -> None:
	"""Set the active theme by name.

	Args:
		name: Theme key (filename stem from themes/ directory).
	"""
	global _ACTIVE_THEME_NAME
	_ACTIVE_THEME_NAME = name


#============================================
def get_active_theme() -> dict:
	"""Return the full dict for the currently active theme.

	Returns:
		dict: Active theme definition.
	"""
	return get_theme(get_active_theme_name())


#============================================
def get_color(key: str) -> str:
	"""Convenience accessor for a GUI color from the active theme.

	Args:
		key: Color key within the 'gui' section (e.g. 'background').

	Returns:
		str: Hex color string.
	"""
	theme = get_active_theme()
	return theme['gui'][key]


#============================================
def get_paper_color(key: str) -> str:
	"""Return a paper color from the active theme.

	Args:
		key: Color key within the 'paper' section (e.g. 'fill').

	Returns:
		str: Hex color string.
	"""
	theme = get_active_theme()
	return theme['paper'][key]


#============================================
def get_grid_color(key: str) -> str:
	"""Return a grid overlay color from the active theme.

	Args:
		key: Color key within the 'grid' section (e.g. 'line').

	Returns:
		str: Hex color string.
	"""
	theme = get_active_theme()
	return theme['grid'][key]


#============================================
def get_chemistry_color(key: str) -> str:
	"""Return a chemistry default color from the active theme.

	Args:
		key: Color key within the 'chemistry' section (e.g. 'default_line').

	Returns:
		str: Hex color string.
	"""
	theme = get_active_theme()
	return theme['chemistry'][key]


#============================================
def _normalize_hex(color: str) -> str:
	"""Normalize a hex color string to lowercase 6-digit form.

	Args:
		color: Hex color string (e.g. '#000', '#FFF', '#e0e0e0').

	Returns:
		str: Lowercase 6-digit hex (e.g. '#000000', '#ffffff').
	"""
	if not color or not color.startswith('#'):
		return color.lower() if color else color
	hex_part = color[1:]
	# expand 3-digit shorthand to 6-digit
	if len(hex_part) == 3:
		hex_part = hex_part[0]*2 + hex_part[1]*2 + hex_part[2]*2
	return '#' + hex_part.lower()


#============================================
def map_chemistry_color(stored_color: str, color_type: str = 'line') -> str:
	"""Return the display color for a chemistry object.

	If the stored color matches the light theme default for the given
	color_type, return the active theme's default instead. Otherwise
	return the stored color unchanged. This allows default-colored
	objects to follow the theme while explicitly colored objects
	stay as-is.

	Args:
		stored_color: The color stored on the object (from CDML or default).
		color_type: 'line' or 'area'.

	Returns:
		str: Display color string.
	"""
	if color_type == 'line':
		light_default = _LIGHT_DEFAULT_LINE
		theme_key = 'default_line'
	else:
		light_default = _LIGHT_DEFAULT_AREA
		theme_key = 'default_area'
	# compare normalized forms so '#000' matches '#000000'
	if _normalize_hex(stored_color) == _normalize_hex(light_default):
		return get_chemistry_color(theme_key)
	return stored_color


#============================================
def _hex_to_luminance(hex_color: str) -> float:
	"""Compute the relative luminance of a hex color string.

	Uses the sRGB luminance formula: 0.2126*R + 0.7152*G + 0.0722*B.

	Args:
		hex_color: hex color string (e.g. '#333333', '#e0e0e0').

	Returns:
		float: luminance in 0.0 (black) to 1.0 (white) range.
	"""
	normalized = _normalize_hex(hex_color)
	hex_part = normalized.lstrip('#')
	r = int(hex_part[0:2], 16) / 255.0
	g = int(hex_part[2:4], 16) / 255.0
	b = int(hex_part[4:6], 16) / 255.0
	luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
	return luminance


#============================================
def needs_icon_inversion() -> bool:
	"""Return True when toolbar icons need luminance inversion.

	Checks the active theme's toolbar background color luminance.
	If the luminance is below 0.5 (dark toolbar), icons should be
	inverted so dark-on-transparent strokes become visible.

	Returns:
		bool: True if icon luminance inversion is needed.
	"""
	theme = get_active_theme()
	toolbar_color = theme['gui']['toolbar']
	luminance = _hex_to_luminance(toolbar_color)
	return luminance < 0.5


#============================================
def configure_ttk_styles(style) -> None:
	"""Configure named ttk styles from the active theme's YAML colors.

	Sets up named styles for toolbar widgets so they inherit theme colors.
	Never configures base TButton/TRadiobutton globally; only named styles
	are modified.

	Args:
		style: ttk.Style instance (typically app._ttk_style)
	"""
	theme = get_active_theme()
	gui = theme['gui']
	toolbar_bg = gui['toolbar']
	toolbar_fg = gui.get('toolbar_fg', '#333333')
	active_bg = gui['active_mode']
	active_fg = gui.get('active_mode_fg', '#000000')
	hover_bg = gui['hover']
	press_bg = gui.get('button_active_bg', hover_bg)
	# toolbar toggle buttons (mode selection radiobuttons)
	style.configure('Toolbar.Toolbutton',
		background=toolbar_bg, foreground=toolbar_fg,
		relief='flat', borderwidth=1, padding=2,
	)
	style.map('Toolbar.Toolbutton',
		background=[
			('selected', active_bg),
			('active', hover_bg),
		],
		foreground=[
			('selected', active_fg),
		],
		relief=[
			('selected', 'groove'),
			('!selected', 'flat'),
		],
	)
	# toolbar action buttons (undo/redo)
	style.configure('Toolbar.TButton',
		background=toolbar_bg, foreground=toolbar_fg,
		relief='flat', borderwidth=1, padding=2,
	)
	style.map('Toolbar.TButton',
		background=[
			('pressed', press_bg),
			('active', hover_bg),
		],
	)
	# submode ribbon buttons (row layout)
	style.configure('Submode.TButton',
		background=toolbar_bg, foreground=toolbar_fg,
		relief='flat', borderwidth=1, padding=1,
	)
	style.map('Submode.TButton',
		background=[
			('pressed', press_bg),
			('active', hover_bg),
		],
	)
	# selected submode button
	style.configure('Selected.Submode.TButton',
		background=gui['grid_selected'], foreground=active_fg,
		relief='groove', borderwidth=1, padding=1,
	)
	style.map('Selected.Submode.TButton',
		background=[
			('active', gui['grid_selected']),
		],
	)
	# grid layout buttons (biomolecule template grid)
	grid_bg = gui.get('grid_deselected', toolbar_bg)
	grid_fg = gui.get('toolbar_fg', '#333333')
	style.configure('Grid.TButton',
		background=grid_bg, foreground=grid_fg,
		relief='raised', borderwidth=1, padding=1,
		font=('sans-serif', 9),
	)
	style.map('Grid.TButton',
		background=[
			('pressed', press_bg),
			('active', hover_bg),
		],
	)
	# selected grid button
	style.configure('Selected.Grid.TButton',
		background=gui['grid_selected'], foreground=active_fg,
		relief='sunken', borderwidth=1, padding=1,
		font=('sans-serif', 9),
	)
	style.map('Selected.Grid.TButton',
		background=[
			('active', gui['grid_selected']),
		],
	)
	# base ttk widget styles so all ttk.Frame / ttk.Label pick up theme bg
	style.configure('TFrame', background=gui['background'])
	style.configure('TLabel', background=gui['background'], foreground=toolbar_fg)
	# notebook and zoom variables
	tab_bg = gui.get('background', '#d9d9d9')
	tab_fg = gui.get('inactive_tab_fg', '#333333')
	active_tab_bg = gui.get('active_tab_bg', '#ffffff')
	active_tab_fg = gui.get('active_tab_fg', '#000000')
	# zoom control buttons and label
	style.configure('Zoom.TButton',
		background=tab_bg, foreground=toolbar_fg,
		relief='flat', borderwidth=1, padding=1,
	)
	style.map('Zoom.TButton',
		background=[
			('pressed', press_bg),
			('active', hover_bg),
		],
	)
	style.configure('Zoom.TLabel',
		background=tab_bg, foreground=toolbar_fg,
		relief='sunken', borderwidth=1, padding=1,
	)
	# scrollbar trough and slider
	style.configure('TScrollbar',
		background=tab_bg,
		troughcolor=gui.get('canvas_surround', tab_bg),
	)
	style.configure('TNotebook',
		background=tab_bg,
		borderwidth=0,
	)
	style.configure('TNotebook.Tab',
		background=tab_bg, foreground=tab_fg,
		padding=(8, 4),
	)
	style.map('TNotebook.Tab',
		background=[
			('selected', active_tab_bg),
			('active', hover_bg),
		],
		foreground=[
			('selected', active_tab_fg),
		],
	)


#============================================
def _refresh_toolbar_icons(app) -> None:
	"""Reconfigure all toolbar button images from the reloaded pixmap cache.

	Iterates through mode buttons via the app's mode-to-group mapping
	and the undo/redo buttons, reconfiguring each with the freshly
	loaded (and possibly recolored) icon.

	Args:
		app: The BKChem application instance.
	"""
	from bkchem import pixmaps
	# refresh mode buttons
	for mode_name in getattr(app, 'modes_sort', []):
		btn = app.get_mode_button(mode_name)
		if btn and mode_name in pixmaps.images:
			btn.configure(image=pixmaps.images[mode_name])
	# refresh undo/redo buttons
	if hasattr(app, '_undo_btn') and 'undo' in pixmaps.images:
		app._undo_btn.configure(image=pixmaps.images['undo'])
	if hasattr(app, '_redo_btn') and 'redo' in pixmaps.images:
		app._redo_btn.configure(image=pixmaps.images['redo'])


#============================================
def apply_gui_theme(app) -> None:
	"""Apply the active theme's GUI colors to the running application.

	Reconfigures the Tk palette, toolbar, buttons, separators,
	status bar, tabs, and edit pool.

	Args:
		app: The BKChem application (Tk root) instance.
	"""
	theme = get_active_theme()
	gui = theme['gui']

	# update ttk named styles from theme colors
	if hasattr(app, '_ttk_style'):
		configure_ttk_styles(app._ttk_style)

	# global Tk palette -- set both background and foreground so all plain
	# tkinter widgets (Frame, Label, etc.) pick up the theme colors
	app.tk_setPalette(
		"background", gui['background'],
		"foreground", gui.get('toolbar_fg', '#000000'),
		"insertBackground", gui['entry_insert_bg'],
	)
	app.option_add("*Entry*Background", gui['entry_bg'])
	app.option_add("*Entry*Foreground", gui['entry_fg'])

	# toolbar frame (row 1 of main_frame)
	_toolbar_bg = gui['toolbar']
	for child in app.main_frame.winfo_children():
		# toolbar is in grid row 1
		info = child.grid_info()
		if info and info.get('row') == 1:
			child.configure(bg=_toolbar_bg)
			# reconfigure toolbar buttons
			_recolor_toolbar_frame(child, gui)
			break

	# reload icons with correct theme coloring, then refresh button images.
	# keep old images alive in _old until new ones replace them on buttons,
	# otherwise Tk references to garbage-collected PhotoImages cause TclError.
	from bkchem import pixmaps
	_old_images = dict(pixmaps.images)
	pixmaps.reload_icons()
	_refresh_toolbar_icons(app)
	# re-invoke current mode to rebuild submode ribbon with fresh images
	current_mode = getattr(app, 'mode', None)
	if current_mode and not isinstance(current_mode, str):
		for tag, mode_obj in app.modes.items():
			if mode_obj is current_mode:
				app.change_mode(tag)
				break
	del _old_images

	# separator between toolbar and submode ribbon (row 2)
	for child in app.main_frame.winfo_children():
		info = child.grid_info()
		if info and info.get('row') == 2:
			child.configure(bg=gui['separator'])
			break

	# submode ribbon (row 3) -- labels and separators
	_recolor_subframe(app, gui)

	# edit pool entry colors
	if hasattr(app, 'editPool'):
		app.editPool.editPool.configure(
			disabledbackground=gui['background'],
			disabledforeground=gui['entry_disabled_fg'],
		)

	# active/inactive mode buttons (also recolors radio group hulls)
	_recolor_mode_buttons(app, gui)

	# tab highlights
	_recolor_tabs(app, gui)

	# status bar (row 7) -- recolor frame and child labels
	_bg = gui['background']
	_fg = gui.get('toolbar_fg', '#000000')
	for child in app.main_frame.winfo_children():
		info = child.grid_info()
		if info and info.get('row') == 7:
			child.configure(bg=_bg)
			for label in child.winfo_children():
				label.configure(bg=_bg, fg=_fg)
			break

	# canvas surround for each paper
	for paper in getattr(app, 'papers', []):
		paper.configure(background=gui['canvas_surround'])
		# paper background rectangle and hex grid
		_apply_paper_theme(paper, theme)

	# trigger redraw of chemistry content on all papers
	for paper in getattr(app, 'papers', []):
		for obj in paper.stack:
			obj.redraw()


#============================================
def _recolor_toolbar_frame(frame, gui: dict) -> None:
	"""Reconfigure all widgets in the toolbar frame to match theme.

	Args:
		frame: The toolbar Frame widget.
		gui: The gui section of the active theme.
	"""
	toolbar_bg = gui['toolbar']
	for child in frame.winfo_children():
		wclass = child.winfo_class()
		# skip ttk widgets -- they are styled via configure_ttk_styles()
		if wclass.startswith('T') and wclass in ('TRadiobutton', 'TButton'):
			continue
		if wclass == 'Frame':
			# separator frames between groups
			if child.cget('width') == 1:
				child.configure(bg=gui['group_separator'])
			else:
				child.configure(bg=toolbar_bg)
				# recurse into sub-frames
				_recolor_toolbar_frame(child, gui)
		elif wclass == 'Button':
			child.configure(background=toolbar_bg, activebackground=toolbar_bg)


#============================================
def _recolor_subframe(app, gui: dict) -> None:
	"""Recolor submode ribbon labels and separators.

	Args:
		app: The BKChem application instance.
		gui: The gui section of the active theme.
	"""
	for widget in getattr(app, '_sub_extra_widgets', []):
		if not widget.winfo_exists():
			continue
		wclass = widget.winfo_class()
		if wclass == 'Label':
			widget.configure(fg=gui['group_label_fg'])
		elif wclass == 'Frame' and widget.cget('width') == 1:
			widget.configure(bg=gui['group_separator'])


#============================================
def _recolor_mode_buttons(app, gui: dict) -> None:
	"""Recolor toolbar mode buttons for active/inactive state.

	For ttk buttons (when _mode_var exists), styling is handled
	declaratively via configure_ttk_styles() and the StringVar state.
	For classic tk buttons, applies explicit background/relief changes.

	Args:
		app: The BKChem application instance.
		gui: The gui section of the active theme.
	"""
	# ttk toolbar buttons are styled via configure_ttk_styles() and
	# the StringVar -- no manual recoloring needed
	if hasattr(app, '_mode_var'):
		return


#============================================
def _recolor_tabs(app, gui: dict) -> None:
	"""Recolor notebook tabs for active/inactive state.

	With ttk.Notebook, tab colors are handled declaratively via
	style maps configured in configure_ttk_styles().  This function
	is a no-op for ttk notebooks.

	Args:
		app: The BKChem application instance.
		gui: The gui section of the active theme.
	"""
	# ttk.Notebook handles tab coloring via TNotebook.Tab style maps
	pass


#============================================
def _apply_paper_theme(paper, theme: dict) -> None:
	"""Apply paper background and hex grid colors from the theme.

	Args:
		paper: A chem_paper canvas instance.
		theme: The full active theme dict.
	"""
	# paper background rectangle
	if hasattr(paper, 'background') and paper.background:
		paper.itemconfig(
			paper.background,
			fill=theme['paper']['fill'],
			outline=theme['paper']['outline'],
		)
	# hex grid overlay
	if hasattr(paper, '_hex_grid_overlay') and paper._hex_grid_overlay:
		paper._hex_grid_overlay.redraw()
