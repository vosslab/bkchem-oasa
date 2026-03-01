"""Load theme colors from shared YAML theme files in bkchem_data/themes/.

The Tk and Qt versions share the same YAML theme files so colors stay
in sync. Each YAML file defines four color layers: gui, chemistry,
paper, and grid.
"""

# Standard Library
import pathlib

# PIP3 modules
import yaml

# path to the shared themes directory via the bkchem_data symlink
_THEMES_DIR = (
	pathlib.Path(__file__).resolve().parent.parent.parent
	/ "bkchem_data" / "themes"
)

# cached theme data keyed by theme name
_THEME_CACHE = {}


#============================================
def _load_theme(name: str) -> dict:
	"""Load and cache a theme YAML file.

	Args:
		name: Theme name ('dark' or 'light'), matching the YAML filename.

	Returns:
		Parsed theme dictionary with gui, chemistry, paper, grid sections.

	Raises:
		FileNotFoundError: If the theme YAML file does not exist.
	"""
	if name in _THEME_CACHE:
		return _THEME_CACHE[name]
	yaml_path = _THEMES_DIR / f"{name}.yaml"
	if not yaml_path.is_file():
		msg = f"Theme file not found: {yaml_path}"
		raise FileNotFoundError(msg)
	with open(yaml_path, "r") as fh:
		data = yaml.safe_load(fh) or {}
	_THEME_CACHE[name] = data
	return data


#============================================
def get_paper_color(theme_name: str) -> str:
	"""Return the paper fill color for the given theme.

	Args:
		theme_name: 'dark' or 'light'.

	Returns:
		CSS hex color string for the paper rectangle.
	"""
	data = _load_theme(theme_name)
	return data.get("paper", {}).get("fill", "#ffffff")


#============================================
def get_paper_outline(theme_name: str) -> str:
	"""Return the paper outline color for the given theme.

	Args:
		theme_name: 'dark' or 'light'.

	Returns:
		CSS hex color string for the paper border.
	"""
	data = _load_theme(theme_name)
	return data.get("paper", {}).get("outline", "#000000")


#============================================
def get_grid_colors(theme_name: str) -> dict:
	"""Return grid overlay colors for the given theme.

	Args:
		theme_name: 'dark' or 'light'.

	Returns:
		Dict with keys 'line', 'dot_fill', 'dot_outline'.
	"""
	data = _load_theme(theme_name)
	grid = data.get("grid", {})
	colors = {
		"line": grid.get("line", "#E8E8E8"),
		"dot_fill": grid.get("dot_fill", "#BFE5D9"),
		"dot_outline": grid.get("dot_outline", "#CCCCCC"),
	}
	return colors


#============================================
def get_canvas_surround(theme_name: str) -> str:
	"""Return the canvas surround (viewport background) color.

	Args:
		theme_name: 'dark' or 'light'.

	Returns:
		CSS hex color string for the area outside the paper.
	"""
	data = _load_theme(theme_name)
	return data.get("gui", {}).get("canvas_surround", "#1e1e1e")


#============================================
def get_chemistry_colors(theme_name: str) -> dict:
	"""Return default chemistry drawing colors.

	Args:
		theme_name: 'dark' or 'light'.

	Returns:
		Dict with keys 'default_line' and 'default_area'.
	"""
	data = _load_theme(theme_name)
	chem = data.get("chemistry", {})
	colors = {
		"default_line": chem.get("default_line", "#000000"),
		"default_area": chem.get("default_area", "#ffffff"),
	}
	return colors


#============================================
def get_gui_colors(theme_name: str) -> dict:
	"""Return GUI chrome colors for the given theme.

	Args:
		theme_name: 'dark' or 'light'.

	Returns:
		Dict with all gui section keys from the YAML file.
	"""
	data = _load_theme(theme_name)
	return data.get("gui", {})


#============================================
def clear_cache() -> None:
	"""Clear the cached theme data, forcing a reload on next access."""
	_THEME_CACHE.clear()
