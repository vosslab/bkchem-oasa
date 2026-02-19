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

"""Hex grid dot overlay for the BKChem canvas.

Draws a pattern of dots at hex grid positions so the user can
visually align atoms and bonds to the grid.
"""

import oasa.hex_grid
from bkchem.singleton_store import Screen


#============================================
class HexGridOverlay:
	"""Manages a hexagonal grid dot overlay on a Tk Canvas.

	The overlay draws small dots at hex grid positions within the
	visible canvas area. Dots are tagged so they stay below chemistry
	content and are excluded from file exports.

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
		"""Draw hex grid dots covering the visible canvas area.

		Computes the visible region in model coordinates, generates
		hex grid points with oasa.hex_grid, then draws each point
		as a small oval on the canvas.
		"""
		canvas = self._canvas
		scale = canvas._scale

		# visible region in canvas coordinates
		cx0 = canvas.canvasx(0)
		cy0 = canvas.canvasy(0)
		vis_w = canvas.winfo_width()
		vis_h = canvas.winfo_height()

		# convert to model coordinates by dividing by scale
		model_x_min = cx0 / scale
		model_y_min = cy0 / scale
		model_x_max = (cx0 + vis_w) / scale
		model_y_max = (cy0 + vis_h) / scale

		# generate hex grid points in model space
		points = oasa.hex_grid.generate_hex_grid_points(
			model_x_min, model_y_min,
			model_x_max, model_y_max,
			self._spacing_px,
		)

		# dot radius in canvas coords (1 pixel at current scale)
		r = 1.0 * scale

		# draw each dot as a tiny oval
		for mx, my in points:
			# model coords -> canvas coords
			sx = mx * scale
			sy = my * scale
			canvas.create_oval(
				sx - r, sy - r, sx + r, sy + r,
				fill="#AADDCC", outline="",
				tags=("no_export", "hex_grid"),
			)

		# keep grid dots below all chemistry content
		canvas.tag_lower("hex_grid")

	#============================================
	def _clear_dots(self) -> None:
		"""Remove all hex grid dots from the canvas."""
		self._canvas.delete("hex_grid")
