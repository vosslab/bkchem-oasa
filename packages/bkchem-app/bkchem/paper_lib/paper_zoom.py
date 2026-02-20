"""Zoom and scale mixin methods for BKChem paper."""

import math

from oasa.transform_lib import Transform


ZOOM_FACTOR = 1.2
ZOOM_MIN = 0.1
ZOOM_MAX = 10.0


class PaperZoomMixin:
	"""Zoom and scale helpers extracted from paper.py."""

	def scale_selected( self, ratio_x, ratio_y, scale_font=1, fix_centers=0, scale_bond_width=False):
		top_levels, unique = self.selected_to_unique_top_levels()
		ratio = math.sqrt( ratio_x*ratio_y) # ratio for operations where x and y can't be distinguished (font size etc.)
		tr = Transform()
		tr.set_scaling_xy( ratio_x, ratio_y)
		for o in top_levels:
			if fix_centers:
				bbox = o.bbox()
				x0 = (bbox[0] + bbox[2])/2
				y0 = (bbox[1] + bbox[3])/2
			self.scale_object( o, tr, ratio, scale_font=scale_font, scale_bond_width=scale_bond_width)
			if fix_centers:
				self.center_object( o, x0, y0)

		# the final things
		if top_levels:
			self.add_bindings()
			self.start_new_undo_record()


	def scale_object( self, o, tr, ratio, scale_font=1, scale_bond_width=False):
		"""scale_font now also refers to scaling of marks"""
		if o.object_type == 'molecule':
			o.transform( tr)
			if scale_font:
				[i.scale_font( ratio) for i in o.atoms]
				[i.redraw() for i in o.atoms if i.show]
			if scale_font:
				for a in o.atoms:
					for m in a.marks:
						m.size *= ratio
						m.redraw()
			if scale_bond_width:
				for e in o.edges:
					e.bond_width *= ratio
					e.redraw()
			for frag in o.fragments:
				if frag.type == "linear_form":
					frag.properties['bond_length'] = round( frag.properties['bond_length'] * ratio)
					o.check_linear_form_fragment( frag)
		if o.object_type in ('arrow','polygon','polyline'):
			for i in o.points:
				x, y = tr.transform_xy( i.x, i.y)
				i.move_to( x, y)
			o.redraw()
		if o.object_type == 'text':
			x, y = tr.transform_xy( o.x, o.y)
			o.move_to( x, y)
			if scale_font:
				o.scale_font( ratio)
			o.redraw()
		if o.object_type == 'plus':
			x, y = tr.transform_xy( o.x, o.y)
			o.move_to( x, y)
			if scale_font:
				o.scale_font( ratio)
			o.redraw()
		elif o.object_type in ('rect', 'oval'):
			coords = tr.transform_4( o.coords)
			o.resize( coords)
			o.redraw()
			o.unselect()
			o.select()

	def scale_all( self, scale, center_on_viewport=False):
		"""Scale canvas, used to zoom in and out of the frame.
	should not affect the *actual* size of the objects."""
		new_scale = self._scale * scale
		new_scale = max(ZOOM_MIN, min(ZOOM_MAX, new_scale))
		actual_factor = new_scale / self._scale
		if actual_factor == 1.0:
			return
		if center_on_viewport:
			# Capture the model-space point at the viewport center;
			# model coordinates are invariant across zoom levels.
			ox = self.canvasx(self.winfo_width() / 2)
			oy = self.canvasy(self.winfo_height() / 2)
			mx = ox / self._scale
			my = oy / self._scale
		self._scale = new_scale
		# Redraw all content from model coordinates at the new scale.
		self.redraw_all()
		# Reset the page background to its nominal size, then scale
		# from the origin so it stays aligned with the redrawn content.
		self.create_background()
		if self._scale != 1.0:
			self.scale(self.background, 0, 0, self._scale, self._scale)
		self.lower(self.background)
		# Clear hex grid before scroll region calc so dots do not
		# inflate bbox(ALL); redraw after scrollregion is set.
		if self._hex_grid_overlay and self._hex_grid_overlay.visible:
			self._hex_grid_overlay._clear_dots()
		# Flush deferred Tk layout (text metrics, etc.) so that
		# bbox(ALL) and the subsequent viewport centering are accurate.
		self.update_idletasks()
		self.update_scrollregion()
		# redraw hex grid overlay at new zoom level;
		# skip at low zoom (<50%) where the visible model area is huge
		# and drawing thousands of dots would be very slow
		if self._hex_grid_overlay and self._hex_grid_overlay.visible:
			if self._scale >= 0.5:
				self._hex_grid_overlay.redraw()
			else:
				self._hex_grid_overlay._clear_dots()
		# Re-center viewport so the same model point stays at viewport center
		if center_on_viewport:
			self._center_viewport_on_canvas(mx * self._scale, my * self._scale)
		self.event_generate('<<zoom-changed>>')

	def zoom_in(self):
		if self._scale < ZOOM_MAX:
			self.scale_all(ZOOM_FACTOR, center_on_viewport=True)

	def zoom_out(self):
		if self._scale > ZOOM_MIN:
			self.scale_all(1.0 / ZOOM_FACTOR, center_on_viewport=True)

	def zoom_reset(self):
		if self._scale != 1.0:
			self.scale_all(1.0 / self._scale)

	def zoom_to_fit(self):
		"""Scale so all content fits in the visible window."""
		bbox = self.bbox('all')
		if not bbox:
			return
		x1, y1, x2, y2 = bbox
		content_w = x2 - x1
		content_h = y2 - y1
		if content_w <= 0 or content_h <= 0:
			return
		canvas_w = self.winfo_width()
		canvas_h = self.winfo_height()
		fit_scale = min(canvas_w / content_w, canvas_h / content_h) * 0.9
		self.scale_all(fit_scale)

	def _content_bbox(self):
		"""Return bbox of drawn content only, excluding the page background
		and non-content overlays like the hex grid."""
		items = list(self.find_all())
		if self.background in items:
			items.remove(self.background)
		# exclude hex grid dots from content bbox
		hex_items = set(self.find_withtag("hex_grid"))
		if hex_items:
			items = [i for i in items if i not in hex_items]
		if not items:
			return None
		return self.list_bbox(items)

	def _center_viewport_on_canvas(self, cx, cy):
		"""Scroll so that canvas point (cx, cy) is at the viewport center.

		Tk's ``xview moveto`` internally subtracts the canvas inset
		(borderwidth + highlightthickness) from the computed origin::

		    xOrigin = scrollX1 - inset + round(frac * scrollWidth)

		The fraction must therefore include a ``+inset`` correction so
		that ``canvasx(winfo_width/2)`` lands on *cx* after scrolling.
		"""
		sr = self.cget('scrollregion').split()
		if len(sr) != 4:
			return
		sr_x1, sr_y1, sr_x2, sr_y2 = (float(v) for v in sr)
		sr_w = sr_x2 - sr_x1
		sr_h = sr_y2 - sr_y1
		if sr_w <= 0 or sr_h <= 0:
			return
		canvas_w = self.winfo_width()
		canvas_h = self.winfo_height()
		inset = int(self.cget('borderwidth')) + int(self.cget('highlightthickness'))
		frac_x = (cx - canvas_w / 2 + inset - sr_x1) / sr_w
		frac_y = (cy - canvas_h / 2 + inset - sr_y1) / sr_h
		self.xview_moveto(max(0.0, min(1.0, frac_x)))
		self.yview_moveto(max(0.0, min(1.0, frac_y)))

	def zoom_to_content(self):
		"""Reset zoom, scale to fit content (max 400%), and center viewport."""
		# Reset to 1.0 so bbox gives real coordinates
		if self._scale != 1.0:
			self.scale_all(1.0 / self._scale)
		bbox = self._content_bbox()
		if not bbox:
			return
		x1, y1, x2, y2 = bbox
		content_w = x2 - x1
		content_h = y2 - y1
		if content_w <= 0 or content_h <= 0:
			return
		canvas_w = self.winfo_width()
		canvas_h = self.winfo_height()
		# Scale to fit with 10% margin, capped at 4.0 (400%)
		fit_scale = min(canvas_w / content_w, canvas_h / content_h) * 0.9
		fit_scale = min(fit_scale, 4.0)
		if fit_scale != 1.0:
			self.scale_all(fit_scale)
		# Center viewport on content
		self.update_idletasks()
		bbox2 = self._content_bbox()
		if bbox2:
			cx = (bbox2[0] + bbox2[2]) / 2
			cy = (bbox2[1] + bbox2[3]) / 2
			self._center_viewport_on_canvas(cx, cy)
