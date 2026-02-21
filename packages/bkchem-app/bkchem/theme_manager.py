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
def apply_gui_theme(app) -> None:
	"""Apply the active theme's GUI colors to the running application.

	Reconfigures the Tk palette, toolbar, buttons, separators,
	status bar, tabs, and edit pool.

	Args:
		app: The BKChem application (Tk root) instance.
	"""
	theme = get_active_theme()
	gui = theme['gui']

	# global Tk palette
	app.tk_setPalette(
		"background", gui['background'],
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

	# radio group hull backgrounds
	for radio in getattr(app, '_radio_groups', []):
		radio.configure(hull_background=gui['toolbar'])

	# active/inactive mode buttons
	_recolor_mode_buttons(app, gui)

	# tab highlights
	_recolor_tabs(app, gui)

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
		if wclass == 'Frame':
			# separator frames between groups
			if child.cget('width') == 1:
				child.configure(bg=gui['group_separator'])
			else:
				child.configure(bg=toolbar_bg)
				# recurse into Pmw hull frames
				_recolor_toolbar_frame(child, gui)
		elif wclass == 'Button':
			child.configure(
				background=toolbar_bg,
				activebackground=gui['button_active_bg'],
			)


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

	Args:
		app: The BKChem application instance.
		gui: The gui section of the active theme.
	"""
	toolbar_bg = gui['toolbar']
	active_mode_color = gui['active_mode']
	active_hl = gui['active_mode_highlight']
	current_mode = getattr(app, 'mode', None)
	# get the mode tag for the current mode
	if current_mode and not isinstance(current_mode, str):
		current_tag = None
		for tag, mode_obj in app.modes.items():
			if mode_obj is current_mode:
				current_tag = tag
				break
	else:
		current_tag = current_mode

	for btn_name in getattr(app, 'modes_sort', []):
		btn = app.get_mode_button(btn_name)
		if not btn:
			continue
		if btn_name == current_tag:
			btn.configure(
				background=active_mode_color,
				activebackground=gui['button_active_bg'],
				highlightbackground=active_hl,
				highlightcolor=active_hl,
			)
		else:
			btn.configure(
				background=toolbar_bg,
				activebackground=gui['button_active_bg'],
			)
	# update stored defaults for hover/leave handlers
	app._btn_default_bg = toolbar_bg


#============================================
def _recolor_tabs(app, gui: dict) -> None:
	"""Recolor notebook tabs for active/inactive state.

	Args:
		app: The BKChem application instance.
		gui: The gui section of the active theme.
	"""
	if not hasattr(app, 'notebook') or not hasattr(app, 'papers'):
		return
	for i, paper in enumerate(app.papers):
		if paper is app.paper:
			app.notebook.tab(i).configure(
				background=gui['active_tab_bg'],
				fg=gui['active_tab_fg'],
			)
		else:
			app.notebook.tab(i).configure(
				background=gui['background'],
				fg=gui['inactive_tab_fg'],
			)


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
	if hasattr(paper, '_hex_grid'):
		paper._hex_grid.redraw()
