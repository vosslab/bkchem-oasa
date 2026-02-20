#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program
#
#--------------------------------------------------------------------------

"""Glyph attach primitives and Cairo font metrics for element symbols."""

# Standard Library
import functools

# local repo modules
from oasa.render_lib.data_types import GlyphAttachPrimitive
from oasa.render_lib.data_types import _OVAL_GLYPH_ELEMENTS
from oasa.render_lib.data_types import _RECT_GLYPH_ELEMENTS
from oasa.render_lib.data_types import _SPECIAL_GLYPH_ELEMENTS
from oasa.render_lib.data_types import _normalize_element_symbol

try:
	import cairo as _cairo
except ImportError:
	_cairo = None


#============================================
def _glyph_class_for_symbol(symbol: str) -> str:
	"""Return canonical analytic glyph primitive class for one element symbol."""
	normalized = _normalize_element_symbol(symbol)
	if normalized in _OVAL_GLYPH_ELEMENTS:
		return "oval"
	if normalized in _RECT_GLYPH_ELEMENTS:
		return "rect"
	if normalized in _SPECIAL_GLYPH_ELEMENTS:
		return "special_p"
	return "rect"


#============================================
@functools.lru_cache(maxsize=512)
def _glyph_center_factor(symbol: str, font_name: str, font_size: float) -> float:
	"""Return normalized center factor within glyph x-advance."""
	if _cairo is None:
		return 0.5
	try:
		surface = _cairo.ImageSurface(_cairo.FORMAT_A8, 1, 1)
		context = _cairo.Context(surface)
		context.select_font_face(font_name or "sans-serif", 0, 0)
		context.set_font_size(float(font_size))
		extents = context.text_extents(symbol)
	except Exception:
		return 0.5
	advance = max(1e-6, float(extents.x_advance))
	center = float(extents.x_bearing) + (float(extents.width) * 0.5)
	factor = center / advance
	return min(1.0, max(0.0, factor))


#============================================
def _glyph_closed_center_factor(symbol: str, font_name: str, font_size: float) -> float:
	"""Return closed-center factor for one glyph symbol."""
	normalized = _normalize_element_symbol(symbol)
	if normalized == "C":
		return _glyph_center_factor("O", font_name, font_size)
	if normalized in ("O", "S"):
		return _glyph_center_factor(normalized, font_name, font_size)
	return _glyph_center_factor(normalized, font_name, font_size)


#============================================
def glyph_attach_primitive(
		symbol: str,
		span_x1: float,
		span_x2: float,
		y1: float,
		y2: float,
		font_size: float,
		font_name: str | None = None) -> GlyphAttachPrimitive:
	"""Build analytic glyph primitive for one element token span."""
	normalized = _normalize_element_symbol(symbol)
	glyph_class = _glyph_class_for_symbol(normalized)
	if normalized == "P" and glyph_class != "special_p":
		raise ValueError("Attach primitive contract requires explicit P special primitive")
	span_width = max(1e-6, span_x2 - span_x1)
	font_size = float(font_size)
	font_name = font_name or "sans-serif"
	core_factor = _glyph_center_factor(normalized, font_name, font_size)
	closed_factor = _glyph_closed_center_factor(normalized, font_name, font_size)
	stem_factor = 0.18
	core_half = max(font_size * 0.08, span_width * 0.16)
	stem_half = max(font_size * 0.06, span_width * 0.10)
	closed_half = core_half
	if glyph_class == "oval":
		stem_factor = 0.12
		core_half = max(font_size * 0.10, span_width * 0.20)
		stem_half = max(font_size * 0.05, span_width * 0.12)
		closed_half = max(font_size * 0.10, span_width * 0.20)
		if normalized == "C":
			# Keep historical core-center behavior for C while adding closed_center.
			core_factor = _glyph_center_factor("O", font_name, font_size)
	elif glyph_class == "special_p":
		# P is explicit special handling (stem + bowl); never generic fallback.
		stem_factor = 0.16
		core_half = max(font_size * 0.09, span_width * 0.18)
		stem_half = max(font_size * 0.05, span_width * 0.10)
		closed_half = max(font_size * 0.08, span_width * 0.16)
	core_center_x = span_x1 + (span_width * min(1.0, max(0.0, core_factor)))
	stem_center_x = span_x1 + (span_width * min(1.0, max(0.0, stem_factor)))
	closed_center_x = span_x1 + (span_width * min(1.0, max(0.0, closed_factor)))
	return GlyphAttachPrimitive(
		symbol=normalized,
		glyph_class=glyph_class,
		span_x1=span_x1,
		span_x2=span_x2,
		y1=y1,
		y2=y2,
		core_center_x=core_center_x,
		stem_centerline_x=stem_center_x,
		closed_center_x=closed_center_x,
		core_half_width=core_half,
		stem_half_width=stem_half,
		closed_half_width=closed_half,
	)
