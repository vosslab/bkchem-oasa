"""Theme-aware icon loader for BKChem-Qt.

Loads PNG icons from bkchem_data/pixmaps/ with theme-appropriate directory
selection (png/ for light, png-dark/ for dark). Caches loaded QIcon instances
and supports cache clearing on theme switch.
"""

# Standard Library
import pathlib

# PIP3 modules
import PySide6.QtGui

# resolve the pixmaps directory relative to the bkchem_qt package
_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent
_DATA_DIR = _PACKAGE_DIR.parent / "bkchem_data" / "pixmaps"

# icon cache: (name, theme) -> QIcon
_icon_cache = {}

# current theme name, set by set_theme()
_current_theme = "light"


#============================================
def validate_icon_paths() -> None:
	"""Verify that the icon data directory exists and contains icons.

	Raises:
		FileNotFoundError: If the pixmaps directory or icon subdirectories
			are missing.
	"""
	if not _DATA_DIR.is_dir():
		msg = f"Icon pixmaps directory not found: {_DATA_DIR}"
		msg += "\nCheck that the bkchem_data symlink is correct."
		raise FileNotFoundError(msg)
	png_dir = _DATA_DIR / "png"
	if not png_dir.is_dir():
		msg = f"Icon PNG directory not found: {png_dir}"
		raise FileNotFoundError(msg)
	# verify at least one icon exists
	png_files = list(png_dir.glob("*.png"))
	if len(png_files) == 0:
		msg = f"No PNG icons found in: {png_dir}"
		raise FileNotFoundError(msg)


#============================================
def set_theme(theme: str) -> None:
	"""Set the current icon theme.

	Args:
		theme: Theme name, 'dark' or 'light'.
	"""
	global _current_theme
	_current_theme = theme


#============================================
def reload_icons() -> None:
	"""Clear the icon cache so icons are reloaded from the current theme directory."""
	_icon_cache.clear()


#============================================
def get_icon(name: str) -> PySide6.QtGui.QIcon:
	"""Load a QIcon by name from the theme-appropriate pixmaps directory.

	For dark theme, looks in png-dark/ first, then falls back to png/.
	For light theme, looks in png/ only.
	Names are normalized to lowercase with .png extension appended.

	Args:
		name: Icon name without extension (e.g. 'edit', 'draw').

	Returns:
		QIcon with the loaded pixmap, or an empty QIcon if not found.
	"""
	# normalize the name
	name = name.lower().strip()
	cache_key = (name, _current_theme)
	if cache_key in _icon_cache:
		return _icon_cache[cache_key]

	# build the icon filename
	filename = name + ".png"

	# try theme-specific directory first for dark theme
	icon = PySide6.QtGui.QIcon()
	if _current_theme == "dark":
		dark_path = _DATA_DIR / "png-dark" / filename
		if dark_path.is_file():
			icon = PySide6.QtGui.QIcon(str(dark_path))
			_icon_cache[cache_key] = icon
			return icon

	# fall back to light theme directory
	light_path = _DATA_DIR / "png" / filename
	if light_path.is_file():
		icon = PySide6.QtGui.QIcon(str(light_path))

	_icon_cache[cache_key] = icon
	return icon


#============================================
def has_icon(name: str) -> bool:
	"""Check whether a named icon file exists in either theme directory.

	Args:
		name: Icon name without extension.

	Returns:
		True if the icon file exists in png/ or png-dark/.
	"""
	filename = name.lower().strip() + ".png"
	light_path = _DATA_DIR / "png" / filename
	dark_path = _DATA_DIR / "png-dark" / filename
	return light_path.is_file() or dark_path.is_file()
