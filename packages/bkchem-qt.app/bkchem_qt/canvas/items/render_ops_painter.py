"""Qt-local canvas palette and interaction color state.

Portable render primitives are painted and measured by
``primitive_ops_painter``.  This module deliberately owns only Qt theme and
interaction colors, so no OASA operation class reaches a scene item.
"""

# PIP3 modules
import PySide6.QtGui


# -- default fallback color (updated at runtime by set_default_color) --
_default_color = PySide6.QtGui.QColor(0, 0, 0)

# -- default area/paper color for masking backgrounds behind atom labels --
_default_area_color = PySide6.QtGui.QColor(255, 255, 255)

# -- canvas interaction colors (selection, hover, preview) --
_canvas_colors = {"selection": "#3399ff", "hover": "#66bbff", "preview": "#888888"}

# -- charge mark colors --
_charge_colors = {"plus": "#3366ff", "minus": "#ff3333"}


#============================================
def set_default_color(hex_color: str) -> None:
	"""Update the Qt foreground color used for portable foreground roles."""
	global _default_color
	_default_color = PySide6.QtGui.QColor(hex_color)


#============================================
def set_default_area_color(hex_color: str) -> None:
	"""Update the Qt paper color used for portable document-background roles."""
	global _default_area_color
	_default_area_color = PySide6.QtGui.QColor(hex_color)


#============================================
def set_canvas_colors(colors: dict) -> None:
	"""Update the Qt-local selection, hover, and preview colors."""
	for key in ("selection", "hover", "preview"):
		if key in colors:
			_canvas_colors[key] = colors[key]


#============================================
def get_canvas_color(key: str) -> str:
	"""Return one Qt-local interaction color."""
	return _canvas_colors.get(key, "#888888")


#============================================
def set_charge_colors(colors: dict) -> None:
	"""Update the Qt-local charge-mark colors."""
	for key in ("plus", "minus"):
		if key in colors:
			_charge_colors[key] = colors[key]


#============================================
def get_charge_color(key: str) -> str:
	"""Return one Qt-local charge-mark color."""
	return _charge_colors.get(key, "#000000")


#============================================
def set_light_default_line(hex_color: str) -> None:
	"""Retain the theme-loader hook after portable-role migration.

	The historic light-line sentinel is now normalized by the backend bridge to
	the portable foreground role, so Qt does not need to interpret its color.
	"""
	if not hex_color:
		raise ValueError("light default line color must be nonempty")
