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

"""Pure 2D computational geometry for render operations."""

# Standard Library
import math

# local repo modules
from oasa import geometry
from oasa import oasa_utils as misc
from oasa.render_lib.data_types import _coerce_attach_target


#============================================
def _closest_point_on_segment(point, p1, p2):
	"""Return closest clamped point on one line segment."""
	px, py = point
	x1, y1 = p1
	x2, y2 = p2
	dx = x2 - x1
	dy = y2 - y1
	denominator = (dx * dx) + (dy * dy)
	if denominator <= 1e-12:
		return p1
	t_value = ((px - x1) * dx + (py - y1) * dy) / denominator
	t_value = max(0.0, min(1.0, t_value))
	return (x1 + (dx * t_value), y1 + (dy * t_value))


#============================================
def _line_intersection(p1, p2, p3, p4):
	"""Return intersection point of two infinite lines, or None when parallel."""
	x1, y1 = p1
	x2, y2 = p2
	x3, y3 = p3
	x4, y4 = p4
	denominator = ((x1 - x2) * (y3 - y4)) - ((y1 - y2) * (x3 - x4))
	if abs(denominator) <= 1e-12:
		return None
	det1 = (x1 * y2) - (y1 * x2)
	det2 = (x3 * y4) - (y3 * x4)
	ix = ((det1 * (x3 - x4)) - ((x1 - x2) * det2)) / denominator
	iy = ((det1 * (y3 - y4)) - ((y1 - y2) * det2)) / denominator
	return (ix, iy)


#============================================
def _point_to_segment_distance_sq(point, seg_start, seg_end):
	"""Return squared distance from one point to one line segment."""
	px, py = point
	x1, y1 = seg_start
	x2, y2 = seg_end
	dx = x2 - x1
	dy = y2 - y1
	denominator = (dx * dx) + (dy * dy)
	if denominator <= 1e-12:
		return ((px - x1) * (px - x1)) + ((py - y1) * (py - y1))
	t_value = ((px - x1) * dx + (py - y1) * dy) / denominator
	t_value = max(0.0, min(1.0, t_value))
	closest_x = x1 + (dx * t_value)
	closest_y = y1 + (dy * t_value)
	return ((px - closest_x) * (px - closest_x)) + ((py - closest_y) * (py - closest_y))


#============================================
def _orientation(p1, p2, p3):
	"""Return orientation sign for ordered triplet of points."""
	value = ((p2[1] - p1[1]) * (p3[0] - p2[0])) - ((p2[0] - p1[0]) * (p3[1] - p2[1]))
	if abs(value) <= 1e-12:
		return 0
	return 1 if value > 0.0 else 2


#============================================
def _on_segment(p1, p2, q):
	"""Return True when q lies on segment p1-p2."""
	return (
		min(p1[0], p2[0]) - 1e-12 <= q[0] <= max(p1[0], p2[0]) + 1e-12
		and min(p1[1], p2[1]) - 1e-12 <= q[1] <= max(p1[1], p2[1]) + 1e-12
	)


#============================================
def _segments_intersect(p1, p2, q1, q2):
	"""Return True when two finite line segments intersect."""
	o1 = _orientation(p1, p2, q1)
	o2 = _orientation(p1, p2, q2)
	o3 = _orientation(q1, q2, p1)
	o4 = _orientation(q1, q2, p2)
	if o1 != o2 and o3 != o4:
		return True
	if o1 == 0 and _on_segment(p1, p2, q1):
		return True
	if o2 == 0 and _on_segment(p1, p2, q2):
		return True
	if o3 == 0 and _on_segment(q1, q2, p1):
		return True
	if o4 == 0 and _on_segment(q1, q2, p2):
		return True
	return False


#============================================
def _distance_sq_segment_to_segment(p1, p2, q1, q2):
	"""Return squared minimum distance between two finite line segments."""
	if _segments_intersect(p1, p2, q1, q2):
		return 0.0
	return min(
		_point_to_segment_distance_sq(p1, q1, q2),
		_point_to_segment_distance_sq(p2, q1, q2),
		_point_to_segment_distance_sq(q1, p1, p2),
		_point_to_segment_distance_sq(q2, p1, p2),
	)


#============================================
def _segment_distance_to_box_sq(seg_start, seg_end, box):
	"""Return squared minimum distance from one segment to one axis-aligned box."""
	x1, y1, x2, y2 = misc.normalize_coords(box)
	edges = (
		((x1, y1), (x2, y1)),
		((x2, y1), (x2, y2)),
		((x2, y2), (x1, y2)),
		((x1, y2), (x1, y1)),
	)
	start_inside = x1 <= seg_start[0] <= x2 and y1 <= seg_start[1] <= y2
	end_inside = x1 <= seg_end[0] <= x2 and y1 <= seg_end[1] <= y2
	if start_inside or end_inside:
		return 0.0
	for edge_start, edge_end in edges:
		if _segments_intersect(seg_start, seg_end, edge_start, edge_end):
			return 0.0
	distances = [
		_distance_sq_segment_to_segment(seg_start, seg_end, edge_start, edge_end)
		for edge_start, edge_end in edges
	]
	return min(distances)


#============================================
def _capsule_intersects_target(seg_start, seg_end, half_width, target, epsilon):
	"""Return True when one stroked segment (capsule) penetrates target interior."""
	resolved = _coerce_attach_target(target)
	if resolved.kind == "box":
		x1, y1, x2, y2 = misc.normalize_coords(resolved.box)
		inner_box = (x1 + epsilon, y1 + epsilon, x2 - epsilon, y2 - epsilon)
		if inner_box[0] >= inner_box[2] or inner_box[1] >= inner_box[3]:
			return False
		distance_sq = _segment_distance_to_box_sq(seg_start, seg_end, inner_box)
		return distance_sq < (half_width * half_width)
	if resolved.kind == "circle":
		effective_radius = max(0.0, float(resolved.radius) - epsilon)
		if effective_radius <= 0.0:
			return False
		distance_sq = _point_to_segment_distance_sq(resolved.center, seg_start, seg_end)
		radius_limit = half_width + effective_radius
		return distance_sq < (radius_limit * radius_limit)
	if resolved.kind == "segment":
		return False
	if resolved.kind == "composite":
		return any(
			_capsule_intersects_target(seg_start, seg_end, half_width, child, epsilon)
			for child in (resolved.targets or ())
		)
	raise ValueError(f"Unsupported attach target kind: {resolved.kind!r}")


#============================================
def _point_in_attach_target(point, target, epsilon=0.0):
	"""Return True when point is in strict interior of one target primitive."""
	resolved = _coerce_attach_target(target)
	return resolved.contains(point, epsilon=epsilon)


#============================================
def _point_in_attach_target_closed(point, target, epsilon=0.0):
	"""Return True when point is inside one target primitive (closed boundary)."""
	resolved = _coerce_attach_target(target)
	if resolved.kind == "box":
		x1, y1, x2, y2 = misc.normalize_coords(resolved.box)
		return (x1 - epsilon) <= point[0] <= (x2 + epsilon) and (y1 - epsilon) <= point[1] <= (y2 + epsilon)
	if resolved.kind == "circle":
		center_x, center_y = resolved.center
		distance = math.hypot(point[0] - center_x, point[1] - center_y)
		return distance <= (max(0.0, float(resolved.radius)) + epsilon)
	if resolved.kind == "segment":
		return False
	if resolved.kind == "composite":
		return any(
			_point_in_attach_target_closed(point, child, epsilon=epsilon)
			for child in (resolved.targets or ())
		)
	raise ValueError(f"Unsupported attach target kind: {resolved.kind!r}")


#============================================
def _line_circle_intersection(start, end, center, radius):
	"""Return boundary intersection from segment start->end with one circle."""
	sx, sy = start
	ex, ey = end
	cx, cy = center
	dx = ex - sx
	dy = ey - sy
	a_value = (dx * dx) + (dy * dy)
	if a_value <= 1e-12:
		return None
	b_value = 2.0 * (((sx - cx) * dx) + ((sy - cy) * dy))
	c_value = ((sx - cx) ** 2) + ((sy - cy) ** 2) - (radius ** 2)
	discriminant = (b_value * b_value) - (4.0 * a_value * c_value)
	if discriminant < 0.0:
		return None
	sqrt_disc = math.sqrt(discriminant)
	t_candidates = sorted(
		[
			(-b_value - sqrt_disc) / (2.0 * a_value),
			(-b_value + sqrt_disc) / (2.0 * a_value),
		]
	)
	for t_value in t_candidates:
		if 0.0 <= t_value <= 1.0:
			return (sx + (dx * t_value), sy + (dy * t_value))
	return None


#============================================
def _ray_circle_boundary_intersection(start, center, radius, direction):
	"""Return first forward ray intersection with one circle boundary."""
	far_scale = max(4096.0, float(radius) * 256.0)
	far_point = (
		start[0] + (direction[0] * far_scale),
		start[1] + (direction[1] * far_scale),
	)
	return _line_circle_intersection(start, far_point, center, radius)


#============================================
def _circle_boundary_toward_target(start, center, radius, target=None):
	"""Return one circle boundary point from start toward target/center."""
	start_x, start_y = start
	center_x, center_y = center
	target_point = target or center
	intersect = _line_circle_intersection(start, target_point, center, radius)
	if intersect is not None:
		return intersect
	dx = center_x - start_x
	dy = center_y - start_y
	distance = math.hypot(dx, dy)
	if distance <= 1e-12:
		return (center_x + radius, center_y)
	return (
		center_x - ((dx / distance) * radius),
		center_y - ((dy / distance) * radius),
	)


#============================================
def _vertical_circle_boundary(start, center, radius, hint=None):
	"""Return circle boundary point on the vertical line through start.x."""
	start_x, start_y = start
	center_x, center_y = center
	delta_x = start_x - center_x
	squared = (radius * radius) - (delta_x * delta_x)
	if squared < 0.0:
		return None
	offset_y = math.sqrt(max(0.0, squared))
	candidates = [center_y - offset_y, center_y + offset_y]
	target_y = hint[1] if hint is not None else center_y
	direction = target_y - start_y
	if abs(direction) <= 1e-12:
		direction = center_y - start_y
	if direction >= 0.0:
		candidates.sort(key=lambda value: (value < start_y, abs(value - start_y)))
	else:
		candidates.sort(key=lambda value: (value > start_y, abs(value - start_y)))
	return (start_x, candidates[0])


#============================================
def _clip_line_to_box(bond_start, bond_end, bbox):
	"""Clip bond_end to bbox edge when bond_end lies inside bbox."""
	x1, y1, x2, y2 = misc.normalize_coords(bbox)
	end_x, end_y = bond_end
	is_inside = x1 <= end_x <= x2 and y1 <= end_y <= y2
	if not is_inside:
		return bond_end
	start_x, start_y = bond_start
	if start_x == end_x and start_y == end_y:
		return bond_end
	return geometry.intersection_of_line_and_rect(
		(start_x, start_y, end_x, end_y),
		(x1, y1, x2, y2),
	)


#============================================
def _box_center(bbox):
	"""Return center point of an axis-aligned bbox."""
	x1, y1, x2, y2 = misc.normalize_coords(bbox)
	return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


#============================================
def _expanded_box(bbox, margin):
	"""Return one bbox expanded by margin in all directions."""
	x1, y1, x2, y2 = misc.normalize_coords(bbox)
	return (x1 - margin, y1 - margin, x2 + margin, y2 + margin)


#============================================
def _resolve_direction_mode(direction_policy, dx, dy):
	"""Return directional mode: side or vertical."""
	if direction_policy == "vertical_preferred":
		return "vertical"
	if direction_policy == "side_preferred":
		return "side"
	return "side" if abs(dx) >= abs(dy) else "vertical"


#============================================
def _lattice_step_for_direction_policy(direction_policy):
	"""Return lattice snap step in degrees for one direction policy, if any."""
	if direction_policy == "auto":
		return 30.0
	return None


#============================================
def _snapped_direction_unit(dx, dy, step_degrees):
	"""Return unit direction snapped to nearest lattice angle step."""
	if abs(dx) <= 1e-12 and abs(dy) <= 1e-12:
		return None
	angle_degrees = math.degrees(math.atan2(dy, dx))
	snapped_angle = round(angle_degrees / step_degrees) * step_degrees
	radians = math.radians(snapped_angle)
	return (math.cos(radians), math.sin(radians))


#============================================
def _ray_box_boundary_intersection(start, direction, box):
	"""Return first forward ray intersection with one axis-aligned box boundary."""
	x1, y1, x2, y2 = misc.normalize_coords(box)
	start_x, start_y = start
	dir_x, dir_y = direction
	candidates = []
	if abs(dir_x) > 1e-12:
		for edge_x in (x1, x2):
			t_value = (edge_x - start_x) / dir_x
			if t_value <= 1e-12:
				continue
			y_value = start_y + (dir_y * t_value)
			if (y1 - 1e-9) <= y_value <= (y2 + 1e-9):
				candidates.append((t_value, edge_x, y_value))
	if abs(dir_y) > 1e-12:
		for edge_y in (y1, y2):
			t_value = (edge_y - start_y) / dir_y
			if t_value <= 1e-12:
				continue
			x_value = start_x + (dir_x * t_value)
			if (x1 - 1e-9) <= x_value <= (x2 + 1e-9):
				candidates.append((t_value, x_value, edge_y))
	if not candidates:
		return None
	candidates.sort(key=lambda item: item[0])
	_closest_t, hit_x, hit_y = candidates[0]
	return (hit_x, hit_y)


#============================================
def directional_attach_edge_intersection(
		bond_start,
		attach_bbox,
		attach_target,
		direction_policy="auto"):
	"""Return directional token-edge endpoint from bond_start toward attach_target.

	Horizontal-dominant approaches terminate on left/right token edges, while
	vertical-dominant approaches terminate on top/bottom edges.
	"""
	x1, y1, x2, y2 = misc.normalize_coords(attach_bbox)
	target_x, target_y = attach_target
	if not (x1 <= target_x <= x2 and y1 <= target_y <= y2):
		target_x, target_y = _box_center((x1, y1, x2, y2))
	start_x, start_y = bond_start
	dx = target_x - start_x
	dy = target_y - start_y
	abs_dx = abs(dx)
	abs_dy = abs(dy)
	if abs_dx <= 1e-12 and abs_dy <= 1e-12:
		return (target_x, target_y)
	if direction_policy == "line":
		return _clip_line_to_box((start_x, start_y), (target_x, target_y), (x1, y1, x2, y2))
	lattice_step = _lattice_step_for_direction_policy(direction_policy)
	if lattice_step is not None:
		snapped_direction = _snapped_direction_unit(dx, dy, lattice_step)
		if snapped_direction is not None:
			hit = _ray_box_boundary_intersection(
				start=(start_x, start_y),
				direction=snapped_direction,
				box=(x1, y1, x2, y2),
			)
			if hit is not None:
				return hit
	mode = _resolve_direction_mode(direction_policy, abs_dx, abs_dy)
	if mode == "side":
		if abs_dx <= 1e-12:
			return _clip_line_to_box((start_x, start_y), (target_x, target_y), (x1, y1, x2, y2))
		edge_x = x1 if dx > 0.0 else x2
		t_value = (edge_x - start_x) / dx
		y_value = start_y + (dy * t_value)
		y_value = min(max(y_value, y1), y2)
		return (edge_x, y_value)
	if abs_dy <= 1e-12:
		return _clip_line_to_box((start_x, start_y), (target_x, target_y), (x1, y1, x2, y2))
	edge_y = y1 if dy > 0.0 else y2
	t_value = (edge_y - start_y) / dy
	x_value = start_x + (dx * t_value)
	x_value = min(max(x_value, x1), x2)
	return (x_value, edge_y)
