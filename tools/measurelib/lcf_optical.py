"""Letter center finder (LCF) optical center via isolation rendering."""

# Standard Library
import copy
import os
import subprocess
import tempfile
import xml.etree.ElementTree as StdET

# Third Party
import cv2
import defusedxml.ElementTree as SafeET
import numpy
import scipy.spatial

from measurelib.constants import CONNECTING_CURVED_ATOMS
from measurelib.util import compact_float
from measurelib.glyph_model import (
	glyph_char_advance,
	glyph_char_vertical_bounds,
	glyph_text_width,
)


# ============================================================================
# Ported from letter-center-finder repo (svg_parser, glyph_renderer, geometry)
# ============================================================================

_LCF_SVG_NS = "http://www.w3.org/2000/svg"
_LCF_WHITE = "#ffffff"
_LCF_STYLE_ATTRS = ('font-size', 'font-weight', 'font-family', 'font-style')
_LCF_POS_ATTRS = ('dx', 'dy')


#============================================
def _lcf_get_dimensions_from_root(root: object) -> dict:
	"""Extract viewBox and viewport dimensions from SVG root element."""
	viewbox_str = root.get('viewBox', '')
	width_str = root.get('width', '300').replace('px', '').strip()
	height_str = root.get('height', '300').replace('px', '').strip()
	width = float(width_str)
	height = float(height_str)
	if viewbox_str:
		parts = viewbox_str.split()
		vb = {
			'x': float(parts[0]),
			'y': float(parts[1]),
			'width': float(parts[2]),
			'height': float(parts[3]),
		}
	else:
		vb = {'x': 0.0, 'y': 0.0, 'width': width, 'height': height}
	return {
		'viewBox': vb,
		'viewport_width': width,
		'viewport_height': height,
	}


#============================================
def _lcf_get_svg_dimensions(svg_path: str) -> dict:
	"""Extract viewBox and viewport dimensions from SVG file."""
	tree = SafeET.parse(svg_path)
	root = tree.getroot()
	return _lcf_get_dimensions_from_root(root)


#============================================
def _lcf_parse_style_attribute(style: str) -> dict:
	"""Parse CSS style attribute into dict."""
	style_dict = {}
	for item in style.split(';'):
		item = item.strip()
		if ':' in item:
			key, value = item.split(':', 1)
			style_dict[key.strip()] = value.strip()
	return style_dict


#============================================
def _lcf_extract_chars_from_string(
		text: str,
		x: float,
		y: float,
		text_anchor: str,
		font_family: str,
		font_size: float,
		font_weight: str,
		fill: str,
		source_text: str,
		text_elem_index: int = 0,
		tspan_index: int | None = None) -> list:
	"""Extract all visible characters from a text string with proper positioning."""
	characters = []
	if not text:
		return characters
	text_width = glyph_text_width(text, font_size)
	tracking = max(0.0, font_size) * 0.04
	if text_anchor == 'middle':
		cursor_x = x - text_width * 0.5
	elif text_anchor == 'end':
		cursor_x = x - text_width
	else:
		cursor_x = x
	for i, char in enumerate(text):
		advance = glyph_char_advance(font_size, char)
		if char.isalnum():
			char_cx = cursor_x + advance * 0.5
			top_y, bottom_y = glyph_char_vertical_bounds(y, font_size, char)
			char_cy = (top_y + bottom_y) * 0.5
			characters.append({
				'character': char,
				'x': cursor_x,
				'y': y,
				'cx': char_cx,
				'cy': char_cy,
				'font_family': font_family,
				'font_size': font_size,
				'font_weight': font_weight,
				'fill_color': fill,
				'source_text': source_text,
				'char_index': i,
				'_text_elem_index': text_elem_index,
				'_tspan_index': tspan_index,
				'_char_offset': i,
			})
		if i < len(text) - 1:
			cursor_x += advance + tracking
		else:
			cursor_x += advance
	return characters


#============================================
def _lcf_extract_characters_from_text_element(
		elem: object, ns: dict, text_elem_index: int) -> list:
	"""Extract all visible characters from text element including tspans."""
	characters = []
	base_x = float(elem.get('x', '0'))
	base_y = float(elem.get('y', '0'))
	base_font_family = elem.get('font-family', 'sans-serif')
	base_font_size = float(elem.get('font-size', '12'))
	base_font_weight = elem.get('font-weight', 'normal')
	base_fill = elem.get('fill', '#000000')
	base_text_anchor = elem.get('text-anchor', 'start')
	style = elem.get('style', '')
	if style:
		style_dict = _lcf_parse_style_attribute(style)
		base_font_family = style_dict.get('font-family', base_font_family)
		base_font_size = float(style_dict.get('font-size', str(base_font_size)).replace('px', ''))
		base_font_weight = style_dict.get('font-weight', base_font_weight)
		base_fill = style_dict.get('fill', base_fill)
		base_text_anchor = style_dict.get('text-anchor', base_text_anchor)
	source_text = StdET.tostring(elem, encoding='unicode', method='text').strip()
	direct_text = elem.text or ''
	characters.extend(_lcf_extract_chars_from_string(
		direct_text, base_x, base_y, base_text_anchor, base_font_family,
		base_font_size, base_font_weight, base_fill, source_text,
		text_elem_index=text_elem_index,
		tspan_index=None,
	))
	tspan_tag = f'{{{_LCF_SVG_NS}}}tspan'
	tspan_children = [child for child in elem if child.tag == tspan_tag]
	for tspan_idx, tspan in enumerate(tspan_children):
		tspan_x = float(tspan.get('x', str(base_x)))
		tspan_y = float(tspan.get('y', str(base_y)))
		tspan_font_family = tspan.get('font-family', base_font_family)
		tspan_font_size = float(tspan.get('font-size', str(base_font_size)))
		tspan_font_weight = tspan.get('font-weight', base_font_weight)
		tspan_fill = tspan.get('fill', base_fill)
		tspan_text_anchor = tspan.get('text-anchor', base_text_anchor)
		tspan_style = tspan.get('style', '')
		if tspan_style:
			style_dict = _lcf_parse_style_attribute(tspan_style)
			tspan_font_family = style_dict.get('font-family', tspan_font_family)
			tspan_font_size = float(style_dict.get('font-size', str(tspan_font_size)).replace('px', ''))
			tspan_font_weight = style_dict.get('font-weight', tspan_font_weight)
			tspan_fill = style_dict.get('fill', tspan_fill)
			tspan_text_anchor = style_dict.get('text-anchor', tspan_text_anchor)
		tspan_text = tspan.text or ''
		characters.extend(_lcf_extract_chars_from_string(
			tspan_text, tspan_x, tspan_y, tspan_text_anchor, tspan_font_family,
			tspan_font_size, tspan_font_weight, tspan_fill, source_text,
			text_elem_index=text_elem_index,
			tspan_index=tspan_idx,
		))
	return characters


#============================================
def _lcf_parse_svg_file(svg_path: str) -> list:
	"""Parse SVG and extract all visible characters with their metadata."""
	tree = SafeET.parse(svg_path)
	root = tree.getroot()
	ns = {'svg': _LCF_SVG_NS}
	characters = []
	text_elements = root.findall(f'.//{{{_LCF_SVG_NS}}}text')
	for text_idx, text_elem in enumerate(text_elements):
		chars_in_element = _lcf_extract_characters_from_text_element(
			text_elem, ns, text_idx
		)
		characters.extend(chars_in_element)
	return characters


#============================================
def _lcf_pixel_to_svg(
		pixel_x: float,
		pixel_y: float,
		svg_dims: dict,
		zoom: float = 1.0) -> tuple[float, float]:
	"""Convert pixel coordinates to SVG coordinates.

	Assumes preserveAspectRatio="xMidYMid meet" (SVG default).
	"""
	vb = svg_dims['viewBox']
	vp_w = svg_dims['viewport_width'] * zoom
	vp_h = svg_dims['viewport_height'] * zoom
	scale = min(vp_w / vb['width'], vp_h / vb['height'])
	rendered_w = vb['width'] * scale
	rendered_h = vb['height'] * scale
	offset_x = (vp_w - rendered_w) / 2.0
	offset_y = (vp_h - rendered_h) / 2.0
	sx = (pixel_x - offset_x) / scale + vb['x']
	sy = (pixel_y - offset_y) / scale + vb['y']
	return (sx, sy)


#============================================
def _lcf_build_isolation_svg(svg_path: str, char_meta: dict) -> str:
	"""Build an SVG string where only the target character is visible."""
	tree = SafeET.parse(svg_path)
	root = tree.getroot()
	StdET.register_namespace('', _LCF_SVG_NS)
	new_root = StdET.Element(f'{{{_LCF_SVG_NS}}}svg')
	new_root.set('version', '1.1')
	for attr in ('width', 'height', 'viewBox', 'preserveAspectRatio'):
		val = root.get(attr)
		if val is not None:
			new_root.set(attr, val)
	vb_str = root.get('viewBox', '')
	if vb_str:
		parts = vb_str.split()
		vb_x, vb_y = float(parts[0]), float(parts[1])
		vb_w, vb_h = float(parts[2]), float(parts[3])
	else:
		vb_x, vb_y = 0.0, 0.0
		vb_w = float(root.get('width', '300').replace('px', ''))
		vb_h = float(root.get('height', '300').replace('px', ''))
	bg = StdET.SubElement(new_root, f'{{{_LCF_SVG_NS}}}rect')
	bg.set('x', str(vb_x - 50))
	bg.set('y', str(vb_y - 50))
	bg.set('width', str(vb_w + 100))
	bg.set('height', str(vb_h + 100))
	bg.set('fill', _LCF_WHITE)
	text_tag = f'{{{_LCF_SVG_NS}}}text'
	text_elements = root.findall(f'.//{text_tag}')
	text_idx = char_meta['_text_elem_index']
	target_text = text_elements[text_idx]
	text_copy = copy.deepcopy(target_text)
	_lcf_isolate_character(text_copy, char_meta)
	new_root.append(text_copy)
	svg_string = StdET.tostring(new_root, encoding='unicode', xml_declaration=True)
	return svg_string


#============================================
def _lcf_isolate_character(text_elem: object, char_meta: dict) -> None:
	"""Modify a text element in-place so only the target character is visible."""
	tspan_idx = char_meta.get('_tspan_index')
	char_offset = char_meta['_char_offset']
	original_fill = char_meta['fill_color']
	tspan_tag = f'{{{_LCF_SVG_NS}}}tspan'
	tspan_children = [child for child in text_elem if child.tag == tspan_tag]
	if tspan_idx is None:
		_lcf_isolate_in_direct_text(text_elem, char_offset, original_fill, tspan_tag)
		for tspan in tspan_children:
			tspan.set('fill', _LCF_WHITE)
	else:
		text_elem.set('fill', _LCF_WHITE)
		for i, tspan in enumerate(tspan_children):
			if i != tspan_idx:
				tspan.set('fill', _LCF_WHITE)
			else:
				tspan_text = tspan.text or ''
				if len(tspan_text) <= 1:
					tspan.set('fill', original_fill)
				else:
					_lcf_split_tspan_for_isolation(
						text_elem, tspan, char_offset, original_fill, tspan_tag
					)


#============================================
def _lcf_isolate_in_direct_text(
		text_elem: object, char_offset: int, fill: str, tspan_tag: str) -> None:
	"""Isolate a character from the text element's direct text content."""
	direct_text = text_elem.text or ''
	text_elem.text = None
	text_elem.set('fill', _LCF_WHITE)
	before = direct_text[:char_offset]
	target_char = direct_text[char_offset]
	after = direct_text[char_offset + 1:]
	existing_children = list(text_elem)
	for child in existing_children:
		text_elem.remove(child)
	if before:
		ts = StdET.SubElement(text_elem, tspan_tag)
		ts.text = before
		ts.set('fill', _LCF_WHITE)
	ts = StdET.SubElement(text_elem, tspan_tag)
	ts.text = target_char
	ts.set('fill', fill)
	if after:
		ts = StdET.SubElement(text_elem, tspan_tag)
		ts.text = after
		ts.set('fill', _LCF_WHITE)
	for child in existing_children:
		child.set('fill', _LCF_WHITE)
		text_elem.append(child)


#============================================
def _lcf_split_tspan_for_isolation(
		text_elem: object, tspan: object, char_offset: int, fill: str, tspan_tag: str) -> None:
	"""Split a multi-character tspan to isolate one character."""
	tspan_text = tspan.text or ''
	before = tspan_text[:char_offset]
	target_char = tspan_text[char_offset]
	after = tspan_text[char_offset + 1:]
	style_attrs = {}
	for attr in _LCF_STYLE_ATTRS:
		val = tspan.get(attr)
		if val is not None:
			style_attrs[attr] = val
	pos_attrs = {}
	for attr in _LCF_POS_ATTRS:
		val = tspan.get(attr)
		if val is not None:
			pos_attrs[attr] = val
	children = list(text_elem)
	idx = children.index(tspan)
	tail = tspan.tail
	text_elem.remove(tspan)
	replacements = []
	is_first = True
	if before:
		ts = StdET.Element(tspan_tag)
		ts.text = before
		ts.set('fill', _LCF_WHITE)
		for k, v in style_attrs.items():
			ts.set(k, v)
		if is_first:
			for k, v in pos_attrs.items():
				ts.set(k, v)
			is_first = False
		replacements.append(ts)
	ts = StdET.Element(tspan_tag)
	ts.text = target_char
	ts.set('fill', fill)
	for k, v in style_attrs.items():
		ts.set(k, v)
	if is_first:
		for k, v in pos_attrs.items():
			ts.set(k, v)
		is_first = False
	replacements.append(ts)
	if after:
		ts = StdET.Element(tspan_tag)
		ts.text = after
		ts.set('fill', _LCF_WHITE)
		for k, v in style_attrs.items():
			ts.set(k, v)
		replacements.append(ts)
	if tail and replacements:
		replacements[-1].tail = tail
	for i, ts in enumerate(replacements):
		text_elem.insert(idx + i, ts)


#============================================
def _lcf_render_svg_string(svg_string: str, zoom: int = 10) -> numpy.ndarray:
	"""Render an SVG string to a grayscale numpy array via rsvg-convert."""
	with tempfile.NamedTemporaryFile(suffix='.svg', mode='w', delete=False) as svg_f:
		svg_f.write(svg_string)
		svg_tmp = svg_f.name
	png_tmp = svg_tmp.replace('.svg', '.png')
	try:
		cmd = [
			'rsvg-convert',
			f'--zoom={zoom}',
			'-o', png_tmp,
			svg_tmp,
		]
		result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
		if result.returncode != 0:
			raise RuntimeError(f"rsvg-convert failed: {result.stderr}")
		image = cv2.imread(png_tmp, cv2.IMREAD_GRAYSCALE)
		if image is None:
			raise RuntimeError(f"Failed to read rendered PNG: {png_tmp}")
		return image
	finally:
		if os.path.exists(svg_tmp):
			os.unlink(svg_tmp)
		if os.path.exists(png_tmp):
			os.unlink(png_tmp)


#============================================
def _lcf_render_isolated_glyph(svg_path: str, char_meta: dict, zoom: int = 10) -> numpy.ndarray:
	"""Render a single character from the SVG in isolation via rsvg-convert."""
	isolation_svg = _lcf_build_isolation_svg(svg_path, char_meta)
	image = _lcf_render_svg_string(isolation_svg, zoom)
	return image


#============================================
def _lcf_extract_binary_mask(glyph_image: numpy.ndarray) -> numpy.ndarray:
	"""Convert grayscale rendered image to binary mask using Otsu thresholding."""
	_, binary = cv2.threshold(
		glyph_image, 0, 255,
		cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
	)
	kernel = numpy.ones((3, 3), numpy.uint8)
	binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
	return binary


#============================================
def _lcf_extract_contour_points(binary_mask: numpy.ndarray) -> numpy.ndarray:
	"""Extract outer contour points from binary glyph mask."""
	contours, _ = cv2.findContours(
		binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
	)
	if len(contours) == 0:
		raise ValueError("No contours found in binary mask")
	largest_contour = max(contours, key=cv2.contourArea)
	points = largest_contour.reshape(-1, 2)
	return points


#============================================
def _lcf_compute_convex_hull(points: numpy.ndarray) -> dict:
	"""Compute convex hull of a point set using scipy."""
	if len(points) < 3:
		raise ValueError("Need at least 3 points to compute convex hull")
	hull = scipy.spatial.ConvexHull(points)
	hull_vertices = points[hull.vertices]
	perimeter = 0.0
	n_verts = len(hull_vertices)
	for i in range(n_verts):
		p1 = hull_vertices[i]
		p2 = hull_vertices[(i + 1) % n_verts]
		perimeter += numpy.linalg.norm(p2 - p1)
	return {
		'vertices': hull_vertices,
		'area': float(hull.volume),
		'perimeter': float(perimeter),
	}


#============================================
def _lcf_fallback_ellipse_fit(points: numpy.ndarray) -> dict:
	"""Fallback ellipse fit using bounding box when least-squares fails."""
	cx = float(numpy.mean(points[:, 0]))
	cy = float(numpy.mean(points[:, 1]))
	semi_x = float((numpy.max(points[:, 0]) - numpy.min(points[:, 0])) / 2.0)
	semi_y = float((numpy.max(points[:, 1]) - numpy.min(points[:, 1])) / 2.0)
	major_axis = max(semi_x, semi_y)
	minor_axis = min(semi_x, semi_y)
	if major_axis > 0:
		eccentricity = numpy.sqrt(1.0 - (minor_axis / major_axis) ** 2)
	else:
		eccentricity = 0.0
	return {
		'center': [cx, cy],
		'semi_x': semi_x,
		'semi_y': semi_y,
		'major_axis': major_axis,
		'minor_axis': minor_axis,
		'area': float(numpy.pi * semi_x * semi_y),
		'eccentricity': float(eccentricity),
	}


#============================================
def _lcf_fit_axis_aligned_ellipse(points: numpy.ndarray) -> dict:
	"""Fit an axis-aligned ellipse using direct least-squares."""
	if len(points) < 5:
		raise ValueError("Need at least 5 points to fit ellipse")
	x = points[:, 0].astype(float)
	y = points[:, 1].astype(float)
	design = numpy.column_stack([x**2, y**2, x, y])
	rhs = -numpy.ones(len(x))
	result, _, _, _ = numpy.linalg.lstsq(design, rhs, rcond=None)
	a_coeff, b_coeff, c_coeff, d_coeff = result
	if a_coeff <= 0 or b_coeff <= 0:
		return _lcf_fallback_ellipse_fit(points)
	cx = -c_coeff / (2.0 * a_coeff)
	cy = -d_coeff / (2.0 * b_coeff)
	r_val = c_coeff**2 / (4.0 * a_coeff) + d_coeff**2 / (4.0 * b_coeff) - 1.0
	if r_val <= 0:
		return _lcf_fallback_ellipse_fit(points)
	semi_x = numpy.sqrt(r_val / a_coeff)
	semi_y = numpy.sqrt(r_val / b_coeff)
	major_axis = max(semi_x, semi_y)
	minor_axis = min(semi_x, semi_y)
	if major_axis > 0:
		eccentricity = numpy.sqrt(1.0 - (minor_axis / major_axis) ** 2)
	else:
		eccentricity = 0.0
	return {
		'center': [float(cx), float(cy)],
		'semi_x': float(semi_x),
		'semi_y': float(semi_y),
		'major_axis': float(major_axis),
		'minor_axis': float(minor_axis),
		'area': float(numpy.pi * semi_x * semi_y),
		'eccentricity': float(eccentricity),
	}


# ============================================================================
# End of ported letter-center-finder functions
# ============================================================================

_LCF_CHAR_CACHE: dict[str, list[dict]] = {}


#============================================
def optical_center_via_isolation_render(
		label: dict,
		center: tuple[float, float] | None,
		center_char: str | None,
		svg_path: str,
		gate_debug: dict | None = None) -> tuple[tuple[float, float] | None, str | None]:
	"""Find optical glyph center using per-character SVG isolation rendering.

	Renders the target character in isolation via rsvg-convert, extracts
	the contour, computes convex hull, and fits an axis-aligned ellipse
	to determine the optical center.  Errors propagate (no silent fallback).
	"""
	if center is None or not center_char:
		return center, center_char
	target = str(center_char).upper()
	# Get parsed characters (cached per SVG file)
	if svg_path not in _LCF_CHAR_CACHE:
		_LCF_CHAR_CACHE[svg_path] = _lcf_parse_svg_file(svg_path)
	all_chars = _LCF_CHAR_CACHE[svg_path]
	# Match: same character, closest to primitive center
	matches = [c for c in all_chars if c["character"] == target]
	if not matches:
		return center, center_char
	best = min(matches, key=lambda c: (c["cx"] - center[0]) ** 2 + (c["cy"] - center[1]) ** 2)
	svg_dims = _lcf_get_svg_dimensions(svg_path)
	zoom = 10
	# Render isolated glyph
	glyph_image = _lcf_render_isolated_glyph(svg_path, best, zoom)
	binary_mask = _lcf_extract_binary_mask(glyph_image)
	contour_points = _lcf_extract_contour_points(binary_mask)
	hull_result = _lcf_compute_convex_hull(contour_points)
	# Curved glyphs (C, O, S, ...) get ellipse fitting; stem glyphs (N, H, R, ...)
	# use bounding-box center of the convex hull.
	fit_points = hull_result["vertices"]
	use_ellipse = (target in CONNECTING_CURVED_ATOMS) and (len(fit_points) >= 5)
	if use_ellipse:
		ellipse = _lcf_fit_axis_aligned_ellipse(fit_points)
		pixel_cx, pixel_cy = ellipse["center"]
		pixel_rx = ellipse["semi_x"]
		pixel_ry = ellipse["semi_y"]
	else:
		# Bounding-box center for stem glyphs or too few hull points.
		xs = [float(p[0]) for p in fit_points]
		ys = [float(p[1]) for p in fit_points]
		pixel_cx = (min(xs) + max(xs)) * 0.5
		pixel_cy = (min(ys) + max(ys)) * 0.5
		pixel_rx = (max(xs) - min(xs)) * 0.5
		pixel_ry = (max(ys) - min(ys)) * 0.5
	# Map pixel center to SVG coordinates
	svg_cx, svg_cy = _lcf_pixel_to_svg(pixel_cx, pixel_cy, svg_dims, zoom)
	# Map semi-axes to SVG units
	vb = svg_dims["viewBox"]
	vp_w = svg_dims["viewport_width"] * zoom
	scale = min(vp_w / vb["width"], svg_dims["viewport_height"] * zoom / vb["height"])
	svg_rx = pixel_rx / scale
	svg_ry = pixel_ry / scale
	# Populate gate_debug for downstream metrics and diagnostics
	if gate_debug is not None:
		gate_debug["pipeline"] = "optical_isolation_render"
		gate_debug["component_point_count"] = int(len(contour_points))
		gate_debug["hull_point_count"] = int(len(hull_result["vertices"]))
		gate_debug["ellipse_fit"] = {
			"cx": compact_float(float(svg_cx)),
			"cy": compact_float(float(svg_cy)),
			"rx": compact_float(float(svg_rx)),
			"ry": compact_float(float(svg_ry)),
			"angle_deg": 0.0,
		}
	return (float(svg_cx), float(svg_cy)), center_char
