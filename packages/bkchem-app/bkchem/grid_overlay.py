#--------------------------------------------------------------------------
#     This file is part of BKChem - a chemical drawing program
#     Copyright (C) 2002-2009 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file gpl.txt in the
#     main directory of the program

#--------------------------------------------------------------------------

"""Hex grid overlay for the BKChem canvas.

Draws a honeycomb line pattern with dots at hex grid vertex positions
so the user can visually align atoms and bonds to the grid.
"""

import oasa.hex_grid
from bkchem import theme_manager
from bkchem.singleton_store import Screen


#============================================
class HexGridOverlay:
	"""Manages a hexagonal grid overlay on a Tk Canvas.

	The overlay draws faint honeycomb lines and small dots at hex grid
	positions within the visible canvas area. Items are tagged so they
	stay below chemistry content and are excluded from file exports.

	Args:
		canvas: The BKChem chem_paper canvas instance.
		spacing_cm: Grid spacing as a string with unit suffix
			(e.g. '0.7cm').
	"""

	#============================================
	def __init__(self, canvas, spacing_cm: str = '0.7cm') -> None:
		"""Initialize the overlay in hidden state.

		Args:
			canvas: The BKChem chem_paper canvas.
			spacing_cm: Grid spacing with unit suffix.
		"""
		self._canvas = canvas
		self._spacing_px = Screen.any_to_px(spacing_cm)
		self._visible = False

	#============================================
	def show(self) -> None:
		"""Show the hex grid overlay on the canvas."""
		if self._visible:
			return
		self._visible = True
		self._draw_dots()

	#============================================
	def hide(self) -> None:
		"""Hide the hex grid overlay from the canvas."""
		if not self._visible:
			return
		self._visible = False
		self._clear_dots()

	#============================================
	@property
	def visible(self) -> bool:
		"""Whether the grid overlay is currently displayed."""
		return self._visible

	#============================================
	def toggle(self) -> None:
		"""Toggle grid overlay visibility."""
		if self._visible:
			self.hide()
		else:
			self.show()

	#============================================
	def redraw(self) -> None:
		"""Redraw the grid overlay if it is currently visible.

		Call this after zoom or scroll changes so the dots
		cover the new visible area.
		"""
		if not self._visible:
			return
		self._clear_dots()
		self._draw_dots()

	#============================================
	def update_spacing(self, spacing_cm: str) -> None:
		"""Change the grid spacing and redraw if visible.

		Args:
			spacing_cm: New spacing with unit suffix (e.g. '0.7cm').
		"""
		self._spacing_px = Screen.any_to_px(spacing_cm)
		# redraw only redraws when visible
		self.redraw()

	#============================================
	def _draw_dots(self) -> None:
		"""Draw hex grid honeycomb lines and dots covering the paper area.

		First pass draws faint honeycomb line segments, second pass draws
		dots on top. Uses the paper rectangle bounds (not the viewport) so
		items only appear on the white paper, not on the gray canvas
		background.  This also avoids the MAX_GRID_POINTS cutoff
		when zoomed far out and prevents the partial-fill bug when
		winfo_width/Height return 1 before the widget is mapped.
		"""
		canvas = self._canvas
		scale = canvas._scale

		# paper size in mm stored in _paper_properties
		paper_props = canvas._paper_properties
		size_x_mm = paper_props.get('size_x', 0)
		size_y_mm = paper_props.get('size_y', 0)
		if size_x_mm <= 0 or size_y_mm <= 0:
			return

		# paper bounds in model coordinates (px) -- origin is (0,0)
		model_x_min = 0.0
		model_y_min = 0.0
		model_x_max = Screen.mm_to_px(size_x_mm)
		model_y_max = Screen.mm_to_px(size_y_mm)

		# first pass: draw honeycomb lines
		edges = oasa.hex_grid.generate_hex_honeycomb_edges(
			model_x_min, model_y_min,
			model_x_max, model_y_max,
			self._spacing_px,
		)
		if edges is not None:
			for (x1, y1), (x2, y2) in edges:
				# model coords -> canvas coords
				sx1 = x1 * scale
				sy1 = y1 * scale
				sx2 = x2 * scale
				sy2 = y2 * scale
				canvas.create_line(
					sx1, sy1, sx2, sy2,
					fill=theme_manager.get_grid_color('line'), width=0.375,
					tags=("no_export", "hex_grid"),
				)

		# second pass: draw dots on top of lines
		# generate hex grid points in model space;
		# returns None if the paper would produce too many dots
		points = oasa.hex_grid.generate_hex_grid_points(
			model_x_min, model_y_min,
			model_x_max, model_y_max,
			self._spacing_px,
		)
		if points is not None:
			# dot radius in canvas coords (1 pixel at current scale)
			r = 1.0 * scale
			# draw each dot as a tiny oval
			for mx, my in points:
				# model coords -> canvas coords
				sx = mx * scale
				sy = my * scale
				canvas.create_oval(
					sx - r, sy - r, sx + r, sy + r,
					fill=theme_manager.get_grid_color('dot_fill'),
					outline=theme_manager.get_grid_color('dot_outline'),
					width=0.375,
					tags=("no_export", "hex_grid"),
				)

		# keep grid above the white paper background but below chemistry;
		# tag_lower would push grid below the paper rectangle, hiding it
		if hasattr(canvas, 'background') and canvas.background:
			canvas.tag_raise("hex_grid", canvas.background)

	#============================================
	def _clear_dots(self) -> None:
		"""Remove all hex grid items from the canvas."""
		self._canvas.delete("hex_grid")
