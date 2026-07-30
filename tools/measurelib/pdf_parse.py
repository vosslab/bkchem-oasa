"""PDF element collection for glyph-bond alignment measurement via pdfplumber."""

# Standard Library
import glob
import math
import pathlib

import pdfplumber

from measurelib.glyph_model import canonicalize_label_text, is_measurement_label
from measurelib.svg_parse import points_bbox


# Map PDF linecap integer codes to SVG-style linecap strings
PDF_LINECAP_MAP = {
	0: "butt",
	1: "round",
	2: "square",
}

# Proximity threshold for grouping adjacent chars into words
CHAR_GROUPING_THRESHOLD_FACTOR = 0.5


#============================================
def open_pdf_page(pdf_path: str) -> object:
	"""Open a PDF file with pdfplumber and return the first page.

	Args:
		pdf_path: path to PDF file.

	Returns:
		tuple of (page, pdf_object) where page is the first page and
		pdf_object is the open pdfplumber.PDF handle (caller should close).
	"""
	pdf_obj = pdfplumber.open(str(pdf_path))
	if not pdf_obj.pages:
		pdf_obj.close()
		raise ValueError(f"PDF has no pages: {pdf_path}")
	page = pdf_obj.pages[0]
	return page, pdf_obj


#============================================
def _flip_y(y_pdf: float, page_height: float) -> float:
	"""Flip Y coordinate from PDF space (origin bottom-left) to SVG space (origin top-left)."""
	return page_height - y_pdf


#============================================
def _curve_is_straight_line(curve: dict) -> bool:
	"""Return True when a pdfplumber curve is a straight line segment."""
	pts = curve.get("pts") or curve.get("points", [])
	return len(pts) == 2


#============================================
def collect_pdf_lines(page: object) -> list[dict]:
	"""Collect line primitives from one PDF page.

	Extracts from page.lines and straight-line page.curves.
	Returns dicts with keys matching svg_parse.collect_svg_lines output:
	{x1, y1, x2, y2, width, linecap}

	Y coordinates are flipped to SVG space (origin top-left).

	Args:
		page: pdfplumber page object.

	Returns:
		list of line primitive dicts.
	"""
	page_height = float(page.height)
	lines = []
	# collect from page.lines
	for line_obj in (page.lines or []):
		x1 = float(line_obj.get("x0", 0.0))
		y1_pdf = float(line_obj.get("y0", 0.0))
		x2 = float(line_obj.get("x1", 0.0))
		y2_pdf = float(line_obj.get("y1", 0.0))
		width = float(line_obj.get("linewidth", line_obj.get("width", 1.0)) or 1.0)
		linecap_raw = line_obj.get("stroke_linecap", line_obj.get("linecap", 0))
		linecap = PDF_LINECAP_MAP.get(int(linecap_raw or 0), "butt")
		lines.append({
			"x1": x1,
			"y1": _flip_y(y1_pdf, page_height),
			"x2": x2,
			"y2": _flip_y(y2_pdf, page_height),
			"width": width,
			"linecap": linecap,
		})
	# collect straight-line curves (2-point curves)
	for curve in (page.curves or []):
		if not _curve_is_straight_line(curve):
			continue
		pts = curve.get("pts") or curve.get("points", [])
		if len(pts) < 2:
			continue
		x1, y1_pdf = float(pts[0][0]), float(pts[0][1])
		x2, y2_pdf = float(pts[1][0]), float(pts[1][1])
		width = float(curve.get("linewidth", curve.get("width", 1.0)) or 1.0)
		linecap_raw = curve.get("stroke_linecap", curve.get("linecap", 0))
		linecap = PDF_LINECAP_MAP.get(int(linecap_raw or 0), "butt")
		lines.append({
			"x1": x1,
			"y1": _flip_y(y1_pdf, page_height),
			"x2": x2,
			"y2": _flip_y(y2_pdf, page_height),
			"width": width,
			"linecap": linecap,
		})
	return lines


#============================================
def _group_chars_into_words(chars: list[dict], page_height: float) -> list[dict]:
	"""Group adjacent character dicts into word-level label dicts.

	Characters are grouped when the horizontal gap between consecutive
	chars is less than half the font size. Each group becomes one label.

	Args:
		chars: list of pdfplumber char dicts.
		page_height: page height for Y-flip.

	Returns:
		list of label dicts with keys matching svg_parse.collect_svg_labels output.
	"""
	if not chars:
		return []
	# sort chars by vertical position (coarse) then horizontal position
	sorted_chars = sorted(chars, key=lambda c: (round(float(c.get("top", 0.0)), 1), float(c.get("x0", 0.0))))
	groups = []
	current_group = [sorted_chars[0]]
	for char_dict in sorted_chars[1:]:
		prev = current_group[-1]
		# check if same approximate line (vertical proximity)
		prev_top = float(prev.get("top", 0.0))
		curr_top = float(char_dict.get("top", 0.0))
		prev_size = float(prev.get("size", 12.0))
		curr_size = float(char_dict.get("size", 12.0))
		avg_size = (prev_size + curr_size) * 0.5
		vertical_gap = abs(curr_top - prev_top)
		# horizontal gap between end of previous char and start of current
		prev_right = float(prev.get("x1", prev.get("x0", 0.0)))
		curr_left = float(char_dict.get("x0", 0.0))
		horiz_gap = curr_left - prev_right
		# group if close enough
		if vertical_gap < avg_size * 0.6 and horiz_gap < avg_size * CHAR_GROUPING_THRESHOLD_FACTOR:
			current_group.append(char_dict)
		else:
			groups.append(current_group)
			current_group = [char_dict]
	groups.append(current_group)
	# convert groups to label dicts
	labels = []
	for group in groups:
		text_parts = []
		for char_dict in group:
			text_val = str(char_dict.get("text", ""))
			if text_val.strip():
				text_parts.append(text_val)
		raw_text = "".join(text_parts)
		if not raw_text.strip():
			continue
		# use first char position as anchor reference
		first_char = group[0]
		x = float(first_char.get("x0", 0.0))
		# use top of first char as the baseline reference position
		y_pdf = float(first_char.get("top", 0.0))
		font_size = max(float(c.get("size", 12.0)) for c in group)
		font_name = str(first_char.get("fontname", "sans-serif"))
		canonical = canonicalize_label_text(raw_text)
		labels.append({
			"text": canonical,
			"text_raw": raw_text,
			"text_display": raw_text,
			"canonical_text": canonical,
			"x": x,
			"y": _flip_y(y_pdf, page_height),
			"anchor": "start",
			"font_size": font_size,
			"font_name": font_name,
			"is_measurement_label": is_measurement_label(canonical),
		})
	return labels


#============================================
def collect_pdf_labels(page: object) -> list[dict]:
	"""Collect text labels from one PDF page with measurement eligibility tags.

	Groups adjacent characters into words by proximity.
	Returns dicts with keys matching svg_parse.collect_svg_labels output.

	Args:
		page: pdfplumber page object.

	Returns:
		list of label dicts.
	"""
	page_height = float(page.height)
	chars = page.chars or []
	return _group_chars_into_words(chars, page_height)


#============================================
def collect_pdf_ring_primitives(page: object) -> list[dict]:
	"""Collect filled polygon/path primitives for Haworth ring detection from PDF.

	Extracts filled curves and rects from the page.
	Returns dicts with keys matching svg_parse.collect_svg_ring_primitives output.

	Args:
		page: pdfplumber page object.

	Returns:
		list of ring primitive dicts with keys: kind, bbox, centroid.
	"""
	page_height = float(page.height)
	primitives = []
	# collect filled curves with more than 2 points
	for curve in (page.curves or []):
		fill = curve.get("fill")
		if fill is None:
			# also check non_stroking_color as pdfplumber fill indicator
			nsc = curve.get("non_stroking_color")
			if nsc is None:
				continue
		pts_raw = curve.get("pts") or curve.get("points", [])
		if len(pts_raw) < 3:
			continue
		points = [(float(p[0]), _flip_y(float(p[1]), page_height)) for p in pts_raw]
		bbox = points_bbox(points)
		if bbox is None:
			continue
		cx = (bbox[0] + bbox[2]) * 0.5
		cy = (bbox[1] + bbox[3]) * 0.5
		primitives.append({
			"kind": "curve",
			"bbox": bbox,
			"centroid": (cx, cy),
		})
	# collect filled rects
	for rect in (page.rects or []):
		fill = rect.get("fill")
		if fill is None:
			nsc = rect.get("non_stroking_color")
			if nsc is None:
				continue
		x0 = float(rect.get("x0", 0.0))
		y0_pdf = float(rect.get("y0", 0.0))
		x1 = float(rect.get("x1", 0.0))
		y1_pdf = float(rect.get("y1", 0.0))
		# flip both Y coords
		y0_svg = _flip_y(y0_pdf, page_height)
		y1_svg = _flip_y(y1_pdf, page_height)
		bbox = (min(x0, x1), min(y0_svg, y1_svg), max(x0, x1), max(y0_svg, y1_svg))
		cx = (bbox[0] + bbox[2]) * 0.5
		cy = (bbox[1] + bbox[3]) * 0.5
		primitives.append({
			"kind": "rect",
			"bbox": bbox,
			"centroid": (cx, cy),
		})
	return primitives


#============================================
def collect_pdf_wedge_bonds(page: object) -> list[dict]:
	"""Collect filled polygon elements that represent wedge/stereo bonds from PDF.

	Returns dicts with keys matching svg_parse.collect_svg_wedge_bonds output.

	Args:
		page: pdfplumber page object.

	Returns:
		list of wedge bond dicts with keys: points, bbox, spine_start, spine_end, fill.
	"""
	page_height = float(page.height)
	wedge_bonds = []
	for curve in (page.curves or []):
		# require fill
		fill = curve.get("fill")
		if fill is None:
			nsc = curve.get("non_stroking_color")
			if nsc is None:
				continue
		pts_raw = curve.get("pts") or curve.get("points", [])
		if len(pts_raw) < 3:
			continue
		points = [(float(p[0]), _flip_y(float(p[1]), page_height)) for p in pts_raw]
		bbox = points_bbox(points)
		if bbox is None:
			continue
		# find spine (longest axis) as the bond line equivalent
		max_dist_sq = 0.0
		spine_start = points[0]
		spine_end = points[1] if len(points) > 1 else points[0]
		for i in range(len(points)):
			for j in range(i + 1, len(points)):
				dx = points[j][0] - points[i][0]
				dy = points[j][1] - points[i][1]
				dist_sq = dx * dx + dy * dy
				if dist_sq > max_dist_sq:
					max_dist_sq = dist_sq
					spine_start = points[i]
					spine_end = points[j]
		spine_length = math.sqrt(max_dist_sq)
		# aspect ratio filter
		bbox_w = bbox[2] - bbox[0]
		bbox_h = bbox[3] - bbox[1]
		aspect_ratio = max(bbox_w, bbox_h) / max(0.01, min(bbox_w, bbox_h))
		if spine_length < 3.0 or aspect_ratio < 1.8:
			continue
		# represent fill as a simple string
		fill_str = "black"
		if isinstance(fill, (list, tuple)):
			fill_str = ",".join(str(c) for c in fill)
		elif fill is not None:
			fill_str = str(fill)
		wedge_bonds.append({
			"points": points,
			"bbox": bbox,
			"spine_start": spine_start,
			"spine_end": spine_end,
			"fill": fill_str,
		})
	return wedge_bonds


#============================================
def resolve_pdf_paths(repo_root: pathlib.Path, input_glob: str) -> list[pathlib.Path]:
	"""Resolve sorted PDF paths from one glob pattern.

	Args:
		repo_root: repository root path.
		input_glob: glob pattern string.

	Returns:
		sorted list of resolved PDF file paths.
	"""
	pattern = str(input_glob)
	if not pattern.startswith("/"):
		pattern = str(repo_root / pattern)
	paths = [pathlib.Path(raw).resolve() for raw in glob.glob(pattern, recursive=True)]
	return sorted(path for path in paths if path.is_file())
