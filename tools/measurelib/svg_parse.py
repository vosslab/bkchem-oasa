"""SVG element collection for glyph-bond alignment measurement."""

# Standard Library
import glob
import math
import pathlib
import re

from measurelib.constants import SVG_FLOAT_PATTERN
from measurelib.glyph_model import canonicalize_label_text, is_measurement_label


#============================================
def local_tag_name(tag: str) -> str:
	"""Return local XML tag name without namespace prefix."""
	if "}" in tag:
		return tag.rsplit("}", 1)[-1]
	return tag


#============================================
def parse_float(raw_value: str | None, default_value: float) -> float:
	"""Parse one SVG numeric attribute with a default fallback."""
	if raw_value is None:
		return float(default_value)
	try:
		return float(str(raw_value).strip())
	except ValueError:
		return float(default_value)


#============================================
def visible_text(text_node: object) -> str:
	"""Return SVG text content with whitespace removed."""
	text_value = "".join(str(part) for part in text_node.itertext())
	return re.sub(r"\s+", "", text_value or "")


#============================================
def svg_number_tokens(text_value: str) -> list[float]:
	"""Return all float-like numeric tokens parsed from one SVG attribute string."""
	return [float(token) for token in SVG_FLOAT_PATTERN.findall(str(text_value or ""))]


#============================================
def points_bbox(points: list[tuple[float, float]]) -> tuple[float, float, float, float] | None:
	"""Return bbox for a point list, or None when list is empty."""
	if not points:
		return None
	x_values = [point[0] for point in points]
	y_values = [point[1] for point in points]
	return (min(x_values), min(y_values), max(x_values), max(y_values))


#============================================
def polygon_points(points_text: str) -> list[tuple[float, float]]:
	"""Parse SVG polygon points string into coordinate tuples."""
	points = []
	coordinates = svg_number_tokens(points_text)
	for index in range(0, len(coordinates) - 1, 2):
		points.append((coordinates[index], coordinates[index + 1]))
	return points


#============================================
def path_points(path_d: str) -> list[tuple[float, float]]:
	"""Parse SVG path coordinate numbers into point tuples (heuristic)."""
	coordinates = svg_number_tokens(path_d)
	points = []
	for index in range(0, len(coordinates) - 1, 2):
		points.append((coordinates[index], coordinates[index + 1]))
	return points


#============================================
def node_is_overlay_group(node: object) -> bool:
	"""Return True when one SVG node is an overlay/diagnostic group to ignore."""
	if local_tag_name(str(node.tag)) != "g":
		return False
	node_id = str(node.get("id") or "").strip().lower()
	if not node_id:
		return False
	if node_id in {"codex-glyph-bond-diagnostic-overlay", "codex-overlay-noise"}:
		return True
	return node_id.startswith("codex-label-diag-")


#============================================
def collect_svg_lines(svg_root: object) -> list[dict]:
	"""Collect line primitives from one SVG root."""
	lines = []
	def walk(node: object, overlay_excluded: bool) -> None:
		excluded_here = overlay_excluded or node_is_overlay_group(node)
		if (not excluded_here) and local_tag_name(str(node.tag)) == "line":
			lines.append(
				{
					"x1": parse_float(node.get("x1"), 0.0),
					"y1": parse_float(node.get("y1"), 0.0),
					"x2": parse_float(node.get("x2"), 0.0),
					"y2": parse_float(node.get("y2"), 0.0),
					"width": parse_float(node.get("stroke-width"), 1.0),
					"linecap": str(node.get("stroke-linecap") or "butt").strip().lower(),
				}
			)
		for child in list(node):
			walk(child, excluded_here)
	walk(svg_root, False)
	return lines


#============================================
def collect_svg_labels(svg_root: object) -> list[dict]:
	"""Collect text labels from one SVG root with measurement eligibility tags."""
	labels = []
	for node in svg_root.iter():
		if local_tag_name(str(node.tag)) != "text":
			continue
		label_visible_text = visible_text(node)
		if not label_visible_text:
			continue
		canonical_text = canonicalize_label_text(label_visible_text)
		labels.append(
			{
				"text": canonical_text,
				"text_raw": label_visible_text,
				"text_display": label_visible_text,
				"canonical_text": canonical_text,
				"x": parse_float(node.get("x"), 0.0),
				"y": parse_float(node.get("y"), 0.0),
				"anchor": str(node.get("text-anchor") or "start"),
				"font_size": parse_float(node.get("font-size"), 12.0),
				"font_name": str(node.get("font-family") or "sans-serif"),
				"is_measurement_label": is_measurement_label(canonical_text),
			}
		)
	return labels


#============================================
def collect_svg_ring_primitives(svg_root: object) -> list[dict]:
	"""Collect filled polygon/path primitives usable for Haworth ring detection."""
	primitives = []
	for node in svg_root.iter():
		tag_name = local_tag_name(str(node.tag))
		if tag_name not in ("polygon", "path"):
			continue
		fill_value = str(node.get("fill") or "").strip().lower()
		if fill_value in ("", "none", "transparent"):
			continue
		points: list[tuple[float, float]] = []
		if tag_name == "polygon":
			points = polygon_points(str(node.get("points") or ""))
		elif tag_name == "path":
			points = path_points(str(node.get("d") or ""))
		bbox = points_bbox(points)
		if bbox is None:
			continue
		cx = (bbox[0] + bbox[2]) * 0.5
		cy = (bbox[1] + bbox[3]) * 0.5
		primitives.append(
			{
				"kind": tag_name,
				"bbox": bbox,
				"centroid": (cx, cy),
				"points": tuple(points),
			}
		)
	return primitives


#============================================
def collect_svg_wedge_bonds(svg_root: object) -> list[dict]:
	"""Collect filled polygon elements that represent wedge/stereo bonds."""
	wedge_bonds = []
	for node in svg_root.iter():
		tag_name = local_tag_name(str(node.tag))
		if tag_name != "polygon":
			continue
		fill = str(node.get("fill") or "").strip().lower()
		if fill in ("", "none", "transparent"):
			continue
		points = polygon_points(str(node.get("points") or ""))
		if len(points) < 3:
			continue
		bbox = points_bbox(points)
		if bbox is None:
			continue
		# Wedge bonds are narrow parallelogram-like shapes.
		# Compute spine (longest axis) as the bond line equivalent.
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
		# Filter out shapes that are too small or too square to be wedge bonds.
		bbox_w = bbox[2] - bbox[0]
		bbox_h = bbox[3] - bbox[1]
		aspect_ratio = max(bbox_w, bbox_h) / max(0.01, min(bbox_w, bbox_h))
		if spine_length < 3.0 or aspect_ratio < 1.8:
			continue
		wedge_bonds.append({
			"points": points,
			"bbox": bbox,
			"spine_start": spine_start,
			"spine_end": spine_end,
			"fill": fill,
		})
	return wedge_bonds


#============================================
def resolve_svg_paths(repo_root: pathlib.Path, input_glob: str) -> list[pathlib.Path]:
	"""Resolve sorted SVG paths from one glob pattern."""
	pattern = str(input_glob)
	if not pattern.startswith("/"):
		pattern = str(repo_root / pattern)
	paths = [pathlib.Path(raw).resolve() for raw in glob.glob(pattern, recursive=True)]
	return sorted(path for path in paths if path.is_file())


#============================================
def svg_tag_with_namespace(svg_root: object, local_name: str) -> str:
	"""Return namespaced tag when the parsed SVG root has one."""
	root_tag = str(svg_root.tag)
	if root_tag.startswith("{") and "}" in root_tag:
		namespace = root_tag[1:].split("}", 1)[0]
		return f"{{{namespace}}}{local_name}"
	return local_name
