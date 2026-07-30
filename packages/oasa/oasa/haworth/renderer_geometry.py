#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Pure computational geometry helpers for Haworth rendering."""

# Standard Library
import math


#============================================
def normalize_vector(dx: float, dy: float) -> tuple[float, float]:
	"""Normalize one direction vector."""
	magnitude = math.hypot(dx, dy)
	if magnitude == 0:
		return (0.0, 0.0)
	return (dx / magnitude, dy / magnitude)


#============================================
def edge_polygon(
		p1: tuple[float, float],
		p2: tuple[float, float],
		thickness_at_p1: float,
		thickness_at_p2: float) -> tuple[tuple[float, float], ...]:
	"""Compute a 4-point polygon for one edge with optional taper."""
	x1, y1 = p1
	x2, y2 = p2
	length = math.hypot(x2 - x1, y2 - y1)
	if length == 0:
		return (p1, p1, p1, p1)
	nx = -(y2 - y1) / length
	ny = (x2 - x1) / length
	half1 = thickness_at_p1 / 2.0
	half2 = thickness_at_p2 / 2.0
	return (
		(x1 + nx * half1, y1 + ny * half1),
		(x1 - nx * half1, y1 - ny * half1),
		(x2 - nx * half2, y2 - ny * half2),
		(x2 + nx * half2, y2 + ny * half2),
	)


#============================================
def intersection_area(
		box_a: tuple[float, float, float, float],
		box_b: tuple[float, float, float, float],
		gap: float = 0.0) -> float:
	"""Return intersection area after expanding each box by half the required gap."""
	half_gap = gap / 2.0
	ax0 = box_a[0] - half_gap
	ay0 = box_a[1] - half_gap
	ax1 = box_a[2] + half_gap
	ay1 = box_a[3] + half_gap
	bx0 = box_b[0] - half_gap
	by0 = box_b[1] - half_gap
	bx1 = box_b[2] + half_gap
	by1 = box_b[3] + half_gap
	overlap_w = min(ax1, bx1) - max(ax0, bx0)
	overlap_h = min(ay1, by1) - max(ay0, by0)
	if overlap_w <= 0.0 or overlap_h <= 0.0:
		return 0.0
	return overlap_w * overlap_h


#============================================
def point_in_box(
		point: tuple[float, float],
		box: tuple[float, float, float, float]) -> bool:
	"""Return True when one point lies inside one bbox."""
	return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


#============================================
def rect_corners(box: tuple[float, float, float, float]) -> list[tuple[float, float]]:
	"""Return rectangle corners in clockwise order."""
	return [
		(box[0], box[1]),
		(box[2], box[1]),
		(box[2], box[3]),
		(box[0], box[3]),
	]


#============================================
def point_in_polygon(
		point: tuple[float, float],
		polygon: tuple[tuple[float, float], ...]) -> bool:
	"""Return True when point is inside polygon using ray-casting."""
	x_value, y_value = point
	inside = False
	count = len(polygon)
	for index in range(count):
		x1, y1 = polygon[index]
		x2, y2 = polygon[(index + 1) % count]
		intersects = ((y1 > y_value) != (y2 > y_value))
		if not intersects:
			continue
		denominator = y2 - y1
		if abs(denominator) < 1e-9:
			continue
		x_intersect = x1 + ((y_value - y1) * (x2 - x1) / denominator)
		if x_intersect >= x_value:
			inside = not inside
	return inside


#============================================
def segments_intersect(
		a1: tuple[float, float],
		a2: tuple[float, float],
		b1: tuple[float, float],
		b2: tuple[float, float]) -> bool:
	"""Return True when two closed line segments intersect."""
	def _cross(p1: object, p2: object, p3: object) -> object:
		return ((p2[0] - p1[0]) * (p3[1] - p1[1])) - ((p2[1] - p1[1]) * (p3[0] - p1[0]))

	def _on_segment(p1: object, p2: object, p3: object) -> object:
		return (
			min(p1[0], p2[0]) - 1e-9 <= p3[0] <= max(p1[0], p2[0]) + 1e-9
			and min(p1[1], p2[1]) - 1e-9 <= p3[1] <= max(p1[1], p2[1]) + 1e-9
		)

	d1 = _cross(a1, a2, b1)
	d2 = _cross(a1, a2, b2)
	d3 = _cross(b1, b2, a1)
	d4 = _cross(b1, b2, a2)
	if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
		return True
	if abs(d1) < 1e-9 and _on_segment(a1, a2, b1):
		return True
	if abs(d2) < 1e-9 and _on_segment(a1, a2, b2):
		return True
	if abs(d3) < 1e-9 and _on_segment(b1, b2, a1):
		return True
	if abs(d4) < 1e-9 and _on_segment(b1, b2, a2):
		return True
	return False


#============================================
def box_overlaps_polygon(
		box: tuple[float, float, float, float],
		polygon: tuple[tuple[float, float], ...]) -> bool:
	"""Return True when one bbox intersects one polygon."""
	for point in polygon:
		if point_in_box(point, box):
			return True
	for corner in rect_corners(box):
		if point_in_polygon(corner, polygon):
			return True
	rect_points = rect_corners(box)
	rect_edges = [
		(rect_points[0], rect_points[1]),
		(rect_points[1], rect_points[2]),
		(rect_points[2], rect_points[3]),
		(rect_points[3], rect_points[0]),
	]
	for index in range(len(polygon)):
		edge_start = polygon[index]
		edge_end = polygon[(index + 1) % len(polygon)]
		for rect_start, rect_end in rect_edges:
			if segments_intersect(edge_start, edge_end, rect_start, rect_end):
				return True
	return False
