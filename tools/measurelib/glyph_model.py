"""Glyph shape and text path model for glyph-bond alignment measurement."""

# Standard Library
import math

from measurelib.constants import CONNECTING_ATOM_SET, GLYPH_CURVED_CHAR_SET, GLYPH_STEM_CHAR_SET
from measurelib.util import (
	line_length,
	normalize_box,
	point_to_box_distance,
	point_to_box_signed_distance,
	point_to_glyph_primitives_signed_distance,
	point_to_target_distance,
)
from measurelib.geometry import point_to_segment_distance_sq

try:
	from matplotlib.font_manager import FontProperties
	from matplotlib.path import Path as MplPath
	from matplotlib.textpath import TextPath
	from matplotlib.transforms import Affine2D
	MATPLOTLIB_TEXTPATH_AVAILABLE = True
except Exception:
	FontProperties = None
	MplPath = None
	TextPath = None
	Affine2D = None
	MATPLOTLIB_TEXTPATH_AVAILABLE = False


#============================================
# NOTE: is_measurement_label() decides WHICH labels get measured.
# The separate _select_key_letter() in analysis.py decides WHICH CHARACTER
# within a measured label is the bond alignment target.  Both skip standalone
# H differently: this function allows H-only labels; _select_key_letter()
# skips H in multi-character labels.  Change one, review the other.
def is_measurement_label(visible_text: str) -> bool:
	"""Return True for labels expected to own a bond connector endpoint."""
	text = str(visible_text or "")
	# extract only alphabetic characters
	alpha_chars = [ch for ch in text if ch.isalpha()]
	if not alpha_chars:
		return False
	# standalone H is measurable (but not H2, H3, etc.)
	if text.strip() == "H":
		return True
	# first or last letter must be a connecting atom (uppercase match only,
	# so lowercase r in "Br" does not match R)
	return (alpha_chars[0] in CONNECTING_ATOM_SET) \
		or (alpha_chars[-1] in CONNECTING_ATOM_SET)


#============================================
def canonicalize_label_text(visible_text: str) -> str:
	"""Return canonical label text for geometry targeting and grouping."""
	text = str(visible_text or "")
	normalized = text.replace("\u2082", "2").replace("\u2083", "3")
	if normalized in ("HOH2C", "H2COH", "C2HOH"):
		return "CH2OH"
	return normalized


#============================================
def label_geometry_text(label: dict) -> str:
	"""Return label text that matches displayed SVG glyph order for geometry."""
	return str(label.get("text_display") or label.get("text_raw") or label.get("text") or "")


#============================================
def font_family_candidates(font_name: str) -> list[str]:
	"""Return prioritized font-family candidates parsed from SVG font-family."""
	raw = str(font_name or "")
	parts = []
	for token in raw.split(","):
		clean = token.strip().strip("'").strip('"')
		if clean:
			parts.append(clean)
	if not parts:
		parts.append("sans-serif")
	parts.extend(["DejaVu Sans", "Arial", "sans-serif"])
	seen = set()
	unique = []
	for item in parts:
		key = item.lower()
		if key in seen:
			continue
		seen.add(key)
		unique.append(item)
	return unique


#============================================
def label_text_path(label: dict) -> object | None:
	"""Return transformed matplotlib text path for one SVG label when available."""
	if not MATPLOTLIB_TEXTPATH_AVAILABLE:
		return None
	text = label_geometry_text(label)
	if not text:
		return None
	font_size = max(1.0, float(label.get("font_size", 12.0)))
	families = font_family_candidates(str(label.get("font_name", "sans-serif")))
	try:
		prop = FontProperties(family=families)
		base_path = TextPath((0.0, 0.0), text, size=font_size, prop=prop)
	except Exception:
		return None
	bbox = base_path.get_extents()
	x = float(label.get("x", 0.0))
	y = float(label.get("y", 0.0))
	anchor = str(label.get("anchor", "start")).strip().lower()
	if anchor == "middle":
		tx = x - ((bbox.xmin + bbox.xmax) * 0.5)
	elif anchor == "end":
		tx = x - bbox.xmax
	else:
		tx = x - bbox.xmin
	ty = y
	try:
		# Matplotlib text path uses Y-up coordinates, while SVG uses Y-down.
		# Mirror across baseline before placing at SVG text origin.
		return base_path.transformed(Affine2D().scale(1.0, -1.0).translate(tx, ty))
	except Exception:
		return None


#============================================
def path_line_segments(path_obj: object) -> list[tuple[tuple[float, float], tuple[float, float]]]:
	"""Return piecewise-linear boundary segments from one matplotlib path."""
	if path_obj is None:
		return []
	try:
		linear = path_obj.interpolated(8)
	except Exception:
		linear = path_obj
	vertices = getattr(linear, "vertices", None)
	codes = getattr(linear, "codes", None)
	if vertices is None or len(vertices) < 2:
		return []
	segments = []
	if codes is None:
		for index in range(1, len(vertices)):
			p1 = (float(vertices[index - 1][0]), float(vertices[index - 1][1]))
			p2 = (float(vertices[index][0]), float(vertices[index][1]))
			segments.append((p1, p2))
		return segments
	sub_start = None
	prev = None
	for vertex, code in zip(vertices, codes):
		point = (float(vertex[0]), float(vertex[1]))
		if code == MplPath.MOVETO:
			sub_start = point
			prev = point
			continue
		if code == MplPath.LINETO:
			if prev is not None:
				segments.append((prev, point))
			prev = point
			continue
		if code == MplPath.CLOSEPOLY:
			if prev is not None and sub_start is not None:
				segments.append((prev, sub_start))
			prev = sub_start
			continue
	return segments


#============================================
def point_to_text_path_signed_distance(point: tuple[float, float], path_obj: object) -> float:
	"""Return signed distance from one point to one glyph text path."""
	if path_obj is None:
		return float("inf")
	segments = path_line_segments(path_obj)
	if not segments:
		return float("inf")
	min_distance_sq = float("inf")
	for seg_start, seg_end in segments:
		distance_sq = point_to_segment_distance_sq(point, seg_start, seg_end)
		if distance_sq < min_distance_sq:
			min_distance_sq = distance_sq
	distance = math.sqrt(max(0.0, min_distance_sq))
	inside = False
	try:
		inside = bool(path_obj.contains_point(point))
	except Exception:
		inside = False
	return -distance if inside else distance


#============================================
def point_to_label_signed_distance(point: tuple[float, float], label: dict) -> float:
	"""Return signed point distance to one label using best independent geometry."""
	text_path = label.get("svg_text_path")
	if text_path is not None:
		signed = point_to_text_path_signed_distance(point, text_path)
		if math.isfinite(signed):
			return signed
	primitives = label.get("svg_estimated_primitives", [])
	if primitives:
		signed = point_to_glyph_primitives_signed_distance(point, primitives)
		if math.isfinite(signed):
			return signed
	box = label.get("svg_estimated_box")
	if box is not None:
		return point_to_box_signed_distance(point, box)
	return float("inf")


#============================================
def nearest_endpoint_to_text_path(
		lines: list[dict],
		line_indexes: list[int],
		path_obj: object) -> tuple[tuple[float, float] | None, float | None, int | None, float | None]:
	"""Return nearest endpoint to one text path across candidate lines."""
	best_endpoint = None
	best_distance = float("inf")
	best_far_distance = float("-inf")
	best_length = float("-inf")
	best_line_index = None
	best_signed_distance = None
	for line_index in line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		p1 = (line["x1"], line["y1"])
		p2 = (line["x2"], line["y2"])
		s1 = point_to_text_path_signed_distance(p1, path_obj)
		s2 = point_to_text_path_signed_distance(p2, path_obj)
		if not math.isfinite(s1) or not math.isfinite(s2):
			continue
		d1 = abs(s1)
		d2 = abs(s2)
		if d1 <= d2:
			endpoint = p1
			distance = d1
			signed_distance = s1
			far_distance = d2
		else:
			endpoint = p2
			distance = d2
			signed_distance = s2
			far_distance = d1
		seg_length = line_length(line)
		if (
				distance < best_distance
				or (
					math.isclose(distance, best_distance, abs_tol=1e-9)
					and far_distance > best_far_distance
				)
				or (
					math.isclose(distance, best_distance, abs_tol=1e-9)
					and math.isclose(far_distance, best_far_distance, abs_tol=1e-9)
					and seg_length > best_length
				)
		):
			best_endpoint = endpoint
			best_distance = distance
			best_far_distance = far_distance
			best_length = seg_length
			best_line_index = line_index
			best_signed_distance = signed_distance
	if best_endpoint is None:
		return None, None, None, None
	return best_endpoint, best_distance, best_line_index, best_signed_distance


#============================================
def line_closest_endpoint_to_box(line: dict, box: tuple[float, float, float, float]) -> tuple[tuple[float, float], float]:
	"""Return line endpoint and distance closest to one target box."""
	p1 = (line["x1"], line["y1"])
	p2 = (line["x2"], line["y2"])
	d1 = point_to_box_distance(p1, box)
	d2 = point_to_box_distance(p2, box)
	if d1 <= d2:
		return p1, d1
	return p2, d2


#============================================
def nearest_endpoint_to_box(
		lines: list[dict],
		line_indexes: list[int],
		box: tuple[float, float, float, float]) -> tuple[tuple[float, float] | None, float | None, int | None]:
	"""Return nearest endpoint to one box across candidate lines."""
	best_endpoint = None
	best_distance = float("inf")
	best_far_distance = float("-inf")
	best_length = float("-inf")
	best_line_index = None
	for line_index in line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		p1 = (line["x1"], line["y1"])
		p2 = (line["x2"], line["y2"])
		d1 = point_to_box_distance(p1, box)
		d2 = point_to_box_distance(p2, box)
		if d1 <= d2:
			endpoint = p1
			distance = d1
			far_distance = d2
		else:
			endpoint = p2
			distance = d2
			far_distance = d1
		seg_length = line_length(line)
		if (
				distance < best_distance
				or (
					math.isclose(distance, best_distance, abs_tol=1e-9)
					and far_distance > best_far_distance
				)
				or (
					math.isclose(distance, best_distance, abs_tol=1e-9)
					and math.isclose(far_distance, best_far_distance, abs_tol=1e-9)
					and seg_length > best_length
				)
		):
			best_endpoint = endpoint
			best_distance = distance
			best_far_distance = far_distance
			best_length = seg_length
			best_line_index = line_index
	if best_endpoint is None:
		return None, None, None
	return best_endpoint, best_distance, best_line_index


#============================================
def nearest_endpoint_to_glyph_primitives(
		lines: list[dict],
		line_indexes: list[int],
		primitives: list[dict]) -> tuple[tuple[float, float] | None, float | None, int | None, float | None]:
	"""Return nearest endpoint to glyph primitive union across candidate lines."""
	best_endpoint = None
	best_distance = float("inf")
	best_far_distance = float("-inf")
	best_length = float("-inf")
	best_line_index = None
	best_signed_distance = None
	for line_index in line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		p1 = (line["x1"], line["y1"])
		p2 = (line["x2"], line["y2"])
		s1 = point_to_glyph_primitives_signed_distance(p1, primitives)
		s2 = point_to_glyph_primitives_signed_distance(p2, primitives)
		if not math.isfinite(s1) or not math.isfinite(s2):
			continue
		d1 = max(0.0, s1)
		d2 = max(0.0, s2)
		if d1 <= d2:
			endpoint = p1
			distance = abs(s1)
			signed_distance = s1
			far_distance = abs(s2)
		else:
			endpoint = p2
			distance = abs(s2)
			signed_distance = s2
			far_distance = abs(s1)
		seg_length = line_length(line)
		if (
				distance < best_distance
				or (
					math.isclose(distance, best_distance, abs_tol=1e-9)
					and far_distance > best_far_distance
				)
				or (
					math.isclose(distance, best_distance, abs_tol=1e-9)
					and math.isclose(far_distance, best_far_distance, abs_tol=1e-9)
					and seg_length > best_length
				)
		):
			best_endpoint = endpoint
			best_distance = distance
			best_far_distance = far_distance
			best_length = seg_length
			best_line_index = line_index
			best_signed_distance = signed_distance
	if best_endpoint is None:
		return None, None, None, None
	return best_endpoint, best_distance, best_line_index, best_signed_distance


#============================================
def all_endpoints_near_glyph_primitives(
		lines: list[dict],
		line_indexes: list[int],
		primitives: list[dict],
		search_limit: float) -> list[dict]:
	"""Return all bond endpoints within search distance of glyph primitives.

	Each result dict contains the endpoint, its signed distance to the glyph
	body, the line index, and the approach side relative to the glyph center.

	Args:
		lines: full list of SVG line primitives.
		line_indexes: candidate line indexes to check.
		primitives: glyph primitives for the label.
		search_limit: maximum unsigned distance to consider.

	Returns:
		list of dicts with keys: endpoint, signed_distance, line_index, side.
	"""
	if not primitives:
		return []
	# compute glyph center x for left/right classification
	bounds = glyph_primitives_bounds(primitives)
	if bounds is None:
		return []
	label_cx = (bounds[0] + bounds[2]) * 0.5
	results = []
	for line_index in line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		p1 = (line["x1"], line["y1"])
		p2 = (line["x2"], line["y2"])
		s1 = point_to_glyph_primitives_signed_distance(p1, primitives)
		s2 = point_to_glyph_primitives_signed_distance(p2, primitives)
		if not math.isfinite(s1) or not math.isfinite(s2):
			continue
		d1 = max(0.0, s1)
		d2 = max(0.0, s2)
		# pick the closer endpoint of this line
		if d1 <= d2:
			endpoint = p1
			signed_distance = s1
			distance = abs(s1)
		else:
			endpoint = p2
			signed_distance = s2
			distance = abs(s2)
		if distance > search_limit:
			continue
		# classify approach side
		ep_x = float(endpoint[0])
		side = "right" if ep_x > label_cx else "left"
		results.append({
			"endpoint": endpoint,
			"signed_distance": signed_distance,
			"distance": distance,
			"line_index": line_index,
			"side": side,
		})
	return results


#============================================
def all_endpoints_near_text_path(
		lines: list[dict],
		line_indexes: list[int],
		path_obj: object,
		label_center_x: float,
		search_limit: float) -> list[dict]:
	"""Return all bond endpoints within search distance of a text path.

	Args:
		lines: full list of SVG line primitives.
		line_indexes: candidate line indexes to check.
		path_obj: matplotlib text path object.
		label_center_x: x-coordinate of label center for left/right classification.
		search_limit: maximum unsigned distance to consider.

	Returns:
		list of dicts with keys: endpoint, signed_distance, line_index, side.
	"""
	if path_obj is None:
		return []
	results = []
	for line_index in line_indexes:
		if line_index < 0 or line_index >= len(lines):
			continue
		line = lines[line_index]
		p1 = (line["x1"], line["y1"])
		p2 = (line["x2"], line["y2"])
		s1 = point_to_text_path_signed_distance(p1, path_obj)
		s2 = point_to_text_path_signed_distance(p2, path_obj)
		if not math.isfinite(s1) or not math.isfinite(s2):
			continue
		d1 = abs(s1)
		d2 = abs(s2)
		if d1 <= d2:
			endpoint = p1
			signed_distance = s1
			distance = d1
		else:
			endpoint = p2
			signed_distance = s2
			distance = d2
		if distance > search_limit:
			continue
		ep_x = float(endpoint[0])
		side = "right" if ep_x > label_center_x else "left"
		results.append({
			"endpoint": endpoint,
			"signed_distance": signed_distance,
			"distance": distance,
			"line_index": line_index,
			"side": side,
		})
	return results


#============================================
def line_closest_endpoint_to_target(
		line: dict, target: object) -> tuple[tuple[float, float], float, float]:
	"""Return nearest endpoint, nearest distance, and far-end distance for one target."""
	p1 = (line["x1"], line["y1"])
	p2 = (line["x2"], line["y2"])
	d1 = point_to_target_distance(p1, target)
	d2 = point_to_target_distance(p2, target)
	if d1 <= d2:
		return p1, d1, d2
	return p2, d2, d1


#============================================
def glyph_char_advance(font_size: float, char: str) -> float:
	"""Return estimated horizontal advance for one glyph character."""
	size = max(1.0, float(font_size))
	if not char:
		return size * 0.55
	if char.isspace():
		return size * 0.30
	upper = char.upper()
	if upper in ("I", "L", "1"):
		return size * 0.38
	if upper in ("W", "M"):
		return size * 0.82
	if upper in GLYPH_CURVED_CHAR_SET:
		return size * 0.62
	if upper in GLYPH_STEM_CHAR_SET:
		return size * 0.58
	if char.isdigit():
		return size * 0.52
	if char.islower():
		return size * 0.50
	return size * 0.56


#============================================
def glyph_char_vertical_bounds(
		baseline_y: float,
		font_size: float,
		char: str) -> tuple[float, float]:
	"""Return estimated top/bottom y bounds for one character primitive."""
	size = max(1.0, float(font_size))
	upper = char.upper()
	if char.isdigit():
		# Digits in formulas are often drawn smaller/lower (subscript-like).
		local_baseline = baseline_y + (size * 0.22)
		return (local_baseline - (size * 0.52), local_baseline + (size * 0.18))
	if char.islower():
		return (baseline_y - (size * 0.60), baseline_y + (size * 0.22))
	if upper in ("C", "O", "S", "Q", "G", "D"):
		return (baseline_y - (size * 0.78), baseline_y + (size * 0.16))
	return (baseline_y - (size * 0.80), baseline_y + (size * 0.20))


#============================================
def glyph_text_width(text: str, font_size: float) -> float:
	"""Return estimated full text width from per-character advances."""
	if not text:
		return max(1.0, float(font_size)) * 0.75
	advances = [glyph_char_advance(font_size, char) for char in text]
	tracking = max(0.0, float(font_size)) * 0.04
	return sum(advances) + (tracking * float(max(0, len(advances) - 1)))


#============================================
def glyph_primitive_from_char(
		char: str,
		char_index: int,
		left_x: float,
		right_x: float,
		top_y: float,
		bottom_y: float) -> dict:
	"""Build one estimated glyph primitive from one character box."""
	upper = char.upper()
	width = max(0.2, right_x - left_x)
	height = max(0.2, bottom_y - top_y)
	if upper in GLYPH_CURVED_CHAR_SET:
		# Tune curved glyph hulls so O-like labels are less under-sized and
		# C-like labels do not over-expand into apparent whitespace gaps.
		if upper == "C":
			rx_factor = 0.35
			ry_factor = 0.43
		elif upper in ("O", "Q"):
			rx_factor = 0.47
			ry_factor = 0.53
		else:
			rx_factor = 0.43
			ry_factor = 0.49
		rx = max(0.3, width * rx_factor)
		ry = max(0.3, height * ry_factor)
		return {
			"kind": "ellipse",
			"char": char,
			"char_index": char_index,
			"cx": (left_x + right_x) * 0.5,
			"cy": (top_y + bottom_y) * 0.5,
			"rx": rx,
			"ry": ry,
		}
	inset_x = width * 0.12
	inset_y = height * 0.05
	return {
		"kind": "box",
		"char": char,
		"char_index": char_index,
		"box": (
			left_x + inset_x,
			top_y + inset_y,
			right_x - inset_x,
			bottom_y - inset_y,
		),
	}


#============================================
def label_svg_estimated_primitives(label: dict) -> list[dict]:
	"""Return renderer-independent glyph primitives derived from SVG text attrs."""
	font_size = max(1.0, float(label.get("font_size", 12.0)))
	text = label_geometry_text(label)
	if not text:
		return []
	text_width = glyph_text_width(text, font_size)
	x = float(label.get("x", 0.0))
	y = float(label.get("y", 0.0))
	anchor = str(label.get("anchor", "start")).strip().lower()
	if anchor == "middle":
		cursor_x = x - (text_width * 0.5)
	elif anchor == "end":
		cursor_x = x - text_width
	else:
		cursor_x = x
	tracking = font_size * 0.04
	primitives = []
	for char_index, char in enumerate(text):
		advance = glyph_char_advance(font_size, char)
		top_y, bottom_y = glyph_char_vertical_bounds(
			baseline_y=y,
			font_size=font_size,
			char=char,
		)
		primitive = glyph_primitive_from_char(
			char=char,
			char_index=char_index,
			left_x=cursor_x,
			right_x=cursor_x + advance,
			top_y=top_y,
			bottom_y=bottom_y,
		)
		primitives.append(primitive)
		cursor_x += advance + tracking
	return primitives


#============================================
def glyph_primitives_bounds(primitives: list[dict]) -> tuple[float, float, float, float] | None:
	"""Return one union bounds box for one glyph primitive list."""
	if not primitives:
		return None
	x_values = []
	y_values = []
	for primitive in primitives:
		kind = str(primitive.get("kind", ""))
		if kind == "box":
			box = primitive.get("box")
			if box is None:
				continue
			x1, y1, x2, y2 = normalize_box(box)
			x_values.extend([x1, x2])
			y_values.extend([y1, y2])
		elif kind == "ellipse":
			cx = float(primitive.get("cx", 0.0))
			cy = float(primitive.get("cy", 0.0))
			rx = max(0.0, float(primitive.get("rx", 0.0)))
			ry = max(0.0, float(primitive.get("ry", 0.0)))
			x_values.extend([cx - rx, cx + rx])
			y_values.extend([cy - ry, cy + ry])
	if not x_values or not y_values:
		return None
	return (min(x_values), min(y_values), max(x_values), max(y_values))


#============================================
def primitive_center(primitive: dict) -> tuple[float, float] | None:
	"""Return center point for one glyph primitive."""
	kind = str(primitive.get("kind", ""))
	if kind == "ellipse":
		return (
			float(primitive.get("cx", 0.0)),
			float(primitive.get("cy", 0.0)),
		)
	if kind == "box":
		box = primitive.get("box")
		if box is None:
			return None
		x1, y1, x2, y2 = normalize_box(box)
		return ((x1 + x2) * 0.5, (y1 + y2) * 0.5)
	return None


#============================================
def label_svg_estimated_box(label: dict) -> tuple[float, float, float, float]:
	"""Return renderer-independent estimated glyph-union box from text primitives."""
	primitives = label_svg_estimated_primitives(label)
	box = glyph_primitives_bounds(primitives)
	if box is not None:
		return box
	font_size = max(1.0, float(label.get("font_size", 12.0)))
	text = label_geometry_text(label)
	estimated_width = glyph_text_width(text, font_size)
	x = float(label.get("x", 0.0))
	y = float(label.get("y", 0.0))
	anchor = str(label.get("anchor", "start")).strip().lower()
	if anchor == "middle":
		x1 = x - (estimated_width * 0.5)
		x2 = x + (estimated_width * 0.5)
	elif anchor == "end":
		x1 = x - estimated_width
		x2 = x
	else:
		x1 = x
		x2 = x + estimated_width
	return normalize_box((x1, y - (font_size * 0.80), x2, y + (font_size * 0.20)))
