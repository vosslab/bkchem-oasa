"""Shared utility helpers for glyph-bond alignment measurement."""

# Standard Library
import math
import re

from measurelib.constants import LENGTH_ROUND_DECIMALS


#============================================
def line_length(line: dict) -> float:
	"""Return Euclidean length for one line primitive."""
	return math.hypot(line["x2"] - line["x1"], line["y2"] - line["y1"])


#============================================
def length_stats(lengths: list[float]) -> dict:
	"""Return descriptive statistics for one list of line lengths."""
	if not lengths:
		return {
			"count": 0,
			"min": 0.0,
			"max": 0.0,
			"mean": 0.0,
			"median": 0.0,
			"stddev": 0.0,
			"coefficient_of_variation": 0.0,
		}
	count = len(lengths)
	sorted_lengths = sorted(lengths)
	if count % 2 == 1:
		median_value = sorted_lengths[count // 2]
	else:
		median_value = (sorted_lengths[count // 2 - 1] + sorted_lengths[count // 2]) / 2.0
	mean_value = sum(lengths) / float(count)
	variance = sum((value - mean_value) ** 2 for value in lengths) / float(count)
	stddev = math.sqrt(variance)
	coefficient = 0.0
	if mean_value > 0.0:
		coefficient = stddev / mean_value
	return {
		"count": count,
		"min": min(lengths),
		"max": max(lengths),
		"mean": mean_value,
		"median": median_value,
		"stddev": stddev,
		"coefficient_of_variation": coefficient,
	}


#============================================
def group_length_append(groups: dict[str, list[float]], key: str, value: float) -> None:
	"""Append one length into one grouped-length dictionary key."""
	if key not in groups:
		groups[key] = []
	groups[key].append(float(value))


#============================================
def alignment_score(distance_to_target: float | None, alignment_tolerance: float | None) -> float:
	"""Return normalized alignment score in [0, 1] from distance and tolerance."""
	if distance_to_target is None:
		return 0.0
	if alignment_tolerance is None or alignment_tolerance <= 0.0:
		return 0.0
	ratio = float(distance_to_target) / float(alignment_tolerance)
	return max(0.0, 1.0 - ratio)


#============================================
def compact_float(value: float | None) -> float | None:
	"""Return compact high-precision float for report readability."""
	if value is None:
		return None
	return float(f"{float(value):.12g}")


#============================================
def display_float(value: float | None, decimals: int = 3) -> float | None:
	"""Return rounded float for human-facing report data points."""
	if value is None:
		return None
	return round(float(value), int(decimals))


#============================================
def display_point(point: object, decimals: int = 3) -> object:
	"""Return rounded [x, y] point for human-facing report data points."""
	if point is None:
		return None
	if not isinstance(point, (list, tuple)) or len(point) != 2:
		return point
	return [display_float(point[0], decimals=decimals), display_float(point[1], decimals=decimals)]


#============================================
def safe_token(text: str) -> str:
	"""Return filesystem-safe token for one short label/debug string."""
	raw = str(text or "").strip()
	if not raw:
		return "unknown"
	safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
	return safe.strip("_") or "unknown"


#============================================
def compact_sorted_values(values: list[float]) -> list[float]:
	"""Return sorted compact-float values preserving high precision."""
	return sorted(compact_float(float(value)) for value in values)


#============================================
def compact_value_counts(values: list[float]) -> list[dict]:
	"""Return frequency table using compact-float keys (avoids coarse rounding)."""
	counts: dict[float, int] = {}
	for value in values:
		compact = compact_float(float(value))
		counts[compact] = int(counts.get(compact, 0)) + 1
	return [
		{
			"value": key,
			"count": counts[key],
		}
		for key in sorted(counts.keys())
	]


#============================================
def rounded_sorted_values(lengths: list[float], decimals: int = LENGTH_ROUND_DECIMALS) -> list[float]:
	"""Return sorted rounded length values (individual values retained)."""
	return sorted(round(float(value), decimals) for value in lengths)


#============================================
def rounded_value_counts(lengths: list[float], decimals: int = LENGTH_ROUND_DECIMALS) -> list[dict]:
	"""Return sorted frequency table for rounded length values."""
	counts: dict[float, int] = {}
	for value in lengths:
		rounded = round(float(value), decimals)
		counts[rounded] = int(counts.get(rounded, 0)) + 1
	return [
		{
			"length": key,
			"count": counts[key],
		}
		for key in sorted(counts.keys())
	]


#============================================
def normalize_box(box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
	"""Return normalized (x1, y1, x2, y2) with ascending corners."""
	x1, y1, x2, y2 = box
	return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


#============================================
def point_distance_sq(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
	"""Return squared Euclidean distance between two points."""
	dx = point_a[0] - point_b[0]
	dy = point_a[1] - point_b[1]
	return (dx * dx) + (dy * dy)


#============================================
def point_to_box_distance(point: tuple[float, float], box: tuple[float, float, float, float]) -> float:
	"""Return Euclidean distance from one point to one axis-aligned box."""
	x1, y1, x2, y2 = box
	px, py = point
	dx = 0.0
	dy = 0.0
	if px < x1:
		dx = x1 - px
	elif px > x2:
		dx = px - x2
	if py < y1:
		dy = y1 - py
	elif py > y2:
		dy = py - y2
	return math.hypot(dx, dy)


#============================================
def point_to_box_signed_distance(point: tuple[float, float], box: tuple[float, float, float, float]) -> float:
	"""Return signed point-to-box distance (negative means inside)."""
	x1, y1, x2, y2 = normalize_box(box)
	px, py = point
	if x1 <= px <= x2 and y1 <= py <= y2:
		inside_depth = min(px - x1, x2 - px, py - y1, y2 - py)
		return -max(0.0, inside_depth)
	return point_to_box_distance(point, box)


#============================================
def point_to_ellipse_signed_distance(
		point: tuple[float, float],
		cx: float,
		cy: float,
		rx: float,
		ry: float) -> float:
	"""Return signed distance from one point to one axis-aligned ellipse."""
	axis_x = max(1e-6, float(rx))
	axis_y = max(1e-6, float(ry))
	px = abs(float(point[0]) - float(cx))
	py = abs(float(point[1]) - float(cy))
	if px <= 1e-12 and py <= 1e-12:
		return -min(axis_x, axis_y)
	def _f(value: float) -> float:
		term_x = (axis_x * px / (value + (axis_x * axis_x))) ** 2
		term_y = (axis_y * py / (value + (axis_y * axis_y))) ** 2
		return term_x + term_y - 1.0
	level = ((px / axis_x) ** 2) + ((py / axis_y) ** 2)
	inside = level <= 1.0
	if inside:
		low = -min(axis_x * axis_x, axis_y * axis_y) + 1e-9
		high = 0.0
	else:
		low = 0.0
		high = max(axis_x * px, axis_y * py, 1.0)
		while _f(high) > 0.0:
			high *= 2.0
			if high > 1e12:
				break
	for _ in range(90):
		mid = (low + high) * 0.5
		value = _f(mid)
		if value > 0.0:
			low = mid
		else:
			high = mid
	t_value = (low + high) * 0.5
	closest_x = (axis_x * axis_x * px) / (t_value + (axis_x * axis_x))
	closest_y = (axis_y * axis_y * py) / (t_value + (axis_y * axis_y))
	distance = math.hypot(px - closest_x, py - closest_y)
	return -distance if inside else distance


#============================================
def point_to_glyph_primitive_signed_distance(point: tuple[float, float], primitive: dict) -> float:
	"""Return signed distance from one point to one estimated glyph primitive."""
	kind = str(primitive.get("kind", ""))
	if kind == "ellipse":
		return point_to_ellipse_signed_distance(
			point=point,
			cx=float(primitive.get("cx", 0.0)),
			cy=float(primitive.get("cy", 0.0)),
			rx=float(primitive.get("rx", 0.0)),
			ry=float(primitive.get("ry", 0.0)),
		)
	box = primitive.get("box")
	if box is None:
		return float("inf")
	return point_to_box_signed_distance(point, box)


#============================================
def point_to_glyph_primitives_signed_distance(point: tuple[float, float], primitives: list[dict]) -> float:
	"""Return signed distance from one point to union of glyph primitives."""
	if not primitives:
		return float("inf")
	distances = [point_to_glyph_primitive_signed_distance(point, primitive) for primitive in primitives]
	inside_distances = [distance for distance in distances if distance <= 0.0]
	if inside_distances:
		# For points inside union, keep the boundary-nearest negative depth.
		return max(inside_distances)
	return min(distances)


#============================================
def point_to_glyph_primitives_distance(point: tuple[float, float], primitives: list[dict]) -> float:
	"""Return non-negative gap from one point to union of glyph primitives."""
	signed_distance = point_to_glyph_primitives_signed_distance(point, primitives)
	if not math.isfinite(signed_distance):
		return float("inf")
	return max(0.0, signed_distance)


#============================================
def point_in_target_closed(
		point: tuple[float, float],
		target: object,
		tol: float = 1e-6) -> bool:
	"""Return True when one point is inside one attach target."""
	if target.kind == "box":
		x1, y1, x2, y2 = target.box
		return (x1 - tol) <= point[0] <= (x2 + tol) and (y1 - tol) <= point[1] <= (y2 + tol)
	if target.kind == "circle":
		cx, cy = target.center
		distance = math.hypot(point[0] - cx, point[1] - cy)
		return distance <= (float(target.radius) + tol)
	if target.kind == "composite":
		for child in target.targets or ():
			if point_in_target_closed(point, child, tol=tol):
				return True
		return False
	if target.kind == "segment":
		return False
	raise ValueError(f"Unsupported attach target kind: {target.kind!r}")


#============================================
def point_to_target_distance(point: tuple[float, float], target: object) -> float:
	"""Return minimal point distance to one attach target."""
	if target.kind == "box":
		return point_to_box_distance(point, target.box)
	if target.kind == "circle":
		cx, cy = target.center
		distance = math.hypot(point[0] - cx, point[1] - cy)
		return max(0.0, distance - float(target.radius))
	if target.kind == "composite":
		distances = [point_to_target_distance(point, child) for child in (target.targets or ())]
		if not distances:
			return float("inf")
		return min(distances)
	if target.kind == "segment":
		x1, y1 = target.p1
		x2, y2 = target.p2
		dx = x2 - x1
		dy = y2 - y1
		segment_len2 = (dx * dx) + (dy * dy)
		if segment_len2 <= 0.0:
			return math.hypot(point[0] - x1, point[1] - y1)
		t = ((point[0] - x1) * dx + (point[1] - y1) * dy) / segment_len2
		t = max(0.0, min(1.0, t))
		closest = (x1 + (t * dx), y1 + (t * dy))
		return math.hypot(point[0] - closest[0], point[1] - closest[1])
	raise ValueError(f"Unsupported attach target kind: {target.kind!r}")


#============================================
def point_to_target_signed_distance(point: tuple[float, float], target: object) -> float:
	"""Return signed point distance to one target (negative means inside)."""
	if target.kind == "box":
		x1, y1, x2, y2 = target.box
		if x1 <= point[0] <= x2 and y1 <= point[1] <= y2:
			inside_depth = min(
				point[0] - x1,
				x2 - point[0],
				point[1] - y1,
				y2 - point[1],
			)
			return -max(0.0, inside_depth)
		return point_to_box_distance(point, target.box)
	if target.kind == "circle":
		cx, cy = target.center
		return math.hypot(point[0] - cx, point[1] - cy) - float(target.radius)
	if target.kind == "composite":
		values = [point_to_target_signed_distance(point, child) for child in (target.targets or ())]
		if not values:
			return float("inf")
		if any(value <= 0.0 for value in values):
			return min(values)
		return min(values)
	if target.kind == "segment":
		x1, y1 = target.p1
		x2, y2 = target.p2
		dx = x2 - x1
		dy = y2 - y1
		segment_len2 = (dx * dx) + (dy * dy)
		if segment_len2 <= 0.0:
			return math.hypot(point[0] - x1, point[1] - y1)
		t = ((point[0] - x1) * dx + (point[1] - y1) * dy) / segment_len2
		t = max(0.0, min(1.0, t))
		closest = (x1 + (t * dx), y1 + (t * dy))
		return math.hypot(point[0] - closest[0], point[1] - closest[1])
	raise ValueError(f"Unsupported attach target kind: {target.kind!r}")


#============================================
def increment_counter(counter: dict[str, int], key: str) -> None:
	"""Increment one dictionary counter key."""
	counter[key] = int(counter.get(key, 0)) + 1


#============================================
def line_midpoint(line: dict) -> tuple[float, float]:
	"""Return midpoint of one line segment."""
	return (
		(line["x1"] + line["x2"]) * 0.5,
		(line["y1"] + line["y2"]) * 0.5,
	)


#============================================
def line_endpoints(line: dict) -> tuple[tuple[float, float], tuple[float, float]]:
	"""Return line endpoints as two point tuples."""
	return ((line["x1"], line["y1"]), (line["x2"], line["y2"]))
