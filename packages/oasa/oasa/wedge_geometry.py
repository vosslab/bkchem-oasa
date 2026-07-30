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

"""Pure geometry helpers for rounded wedge bonds."""

# Standard Library
import math


#============================================
def rounded_wedge_geometry(tip_point: object, base_point: object, wide_width: object,
		narrow_width: object = 0.0, corner_radius: object = None) -> dict:
	"""Compute rounded wedge geometry from endpoints.

	The wedge is directional: it expands from tip_point (narrow) to base_point
	(wide). Length and angle are derived from the endpoints.

	Rounded corners are applied at the wide end, keeping the wedge sides straight.

	Args:
		tip_point: (x, y) center of the narrow end.
		base_point: (x, y) center of the wide end.
		wide_width: Width at the wide end.
		narrow_width: Width at the narrow end (0.0 for pointed tip).
		corner_radius: Optional corner rounding radius at the wide end.

	Returns:
		dict: Geometry info, including corners, arc params, path commands, and area.
	"""
	_tx, _ty = tip_point
	_bx, _by = base_point
	dx = _bx - _tx
	dy = _by - _ty
	length = math.hypot(dx, dy)
	if length == 0:
		raise ValueError("tip_point and base_point must be different")
	if wide_width <= 0:
		raise ValueError("wide_width must be positive")
	if narrow_width < 0:
		raise ValueError("narrow_width must be non-negative")

	narrow_left, narrow_right, wide_left, wide_right, angle = _compute_wedge_corners(
		tip_point, base_point, wide_width, narrow_width
	)
	area = _compute_wedge_area(length, narrow_width, wide_width)
	path_info = rounded_wedge_path_from_corners(
		narrow_left,
		narrow_right,
		wide_left,
		wide_right,
		corner_radius=corner_radius,
	)
	corner_radius = path_info["corner_radius"]
	path_commands = path_info["commands"]
	return {
		"tip": tip_point,
		"base": base_point,
		"narrow_left": narrow_left,
		"narrow_right": narrow_right,
		"wide_left": wide_left,
		"wide_right": wide_right,
		"corner_radius": corner_radius,
		"length": length,
		"angle": angle,
		"path_commands": path_commands,
		"area": area,
	}


#============================================
def _compute_wedge_corners(tip_point: object, base_point: object, wide_width: object,
		narrow_width: object) -> tuple:
	_tx, _ty = tip_point
	_bx, _by = base_point
	dx = _bx - _tx
	dy = _by - _ty
	length = math.hypot(dx, dy)
	if length == 0:
		raise ValueError("tip_point and base_point must be different")
	ux = dx / length
	uy = dy / length
	px = -uy
	py = ux
	narrow_half = narrow_width / 2.0
	wide_half = wide_width / 2.0
	narrow_left = (_tx + px * narrow_half, _ty + py * narrow_half)
	narrow_right = (_tx - px * narrow_half, _ty - py * narrow_half)
	wide_left = (_bx + px * wide_half, _by + py * wide_half)
	wide_right = (_bx - px * wide_half, _by - py * wide_half)
	angle = math.atan2(dy, dx)
	return (narrow_left, narrow_right, wide_left, wide_right, angle)


#============================================
def _normalize_vector(dx: object, dy: object) -> object:
	length = math.hypot(dx, dy)
	if length == 0:
		return None
	return (dx / length, dy / length)


#============================================
def _angle_between(v1: object, v2: object) -> object:
	dot = v1[0] * v2[0] + v1[1] * v2[1]
	dot = max(-1.0, min(1.0, dot))
	return math.acos(dot)


#============================================
def _arc_angles_for_points(center: object, start: object, end: object) -> tuple:
	angle_start = math.atan2(start[1] - center[1], start[0] - center[0])
	angle_end = math.atan2(end[1] - center[1], end[0] - center[0])
	delta = angle_end - angle_start
	if delta <= -math.pi:
		delta += 2 * math.pi
	elif delta > math.pi:
		delta -= 2 * math.pi
	return angle_start, angle_start + delta


#============================================
def _compute_wedge_area(length: object, narrow_width: object, wide_width: object) -> object:
	return length * (narrow_width + wide_width) / 2.0


#============================================
def rounded_wedge_path_from_corners(narrow_left: object, narrow_right: object,
		wide_left: object, wide_right: object, corner_radius: object = None) -> dict:
	wide_width = math.hypot(wide_right[0] - wide_left[0], wide_right[1] - wide_left[1])
	if corner_radius is None:
		corner_radius = wide_width * 0.25
	corner_radius = min(corner_radius, wide_width / 2.0)
	corner_radius = _effective_corner_radius(
		corner_radius,
		narrow_left,
		narrow_right,
		wide_left,
		wide_right,
	)
	commands = _wedge_to_path_commands(
		narrow_left,
		narrow_right,
		wide_left,
		wide_right,
		corner_radius,
	)
	return {
		"commands": commands,
		"corner_radius": corner_radius,
		"wide_width": wide_width,
	}


#============================================
def _max_corner_radius(angle: object, edge_limit: object) -> object:
	if angle <= 0:
		return 0.0
	half = angle / 2.0
	tan_half = math.tan(half)
	if tan_half <= 0:
		return 0.0
	return edge_limit * tan_half


#============================================
def _effective_corner_radius(corner_radius: object, narrow_left: object, narrow_right: object,
		wide_left: object, wide_right: object) -> object:
	if corner_radius <= 0:
		return 0.0
	base_dx = wide_right[0] - wide_left[0]
	base_dy = wide_right[1] - wide_left[1]
	base_len = math.hypot(base_dx, base_dy)
	if base_len == 0:
		return 0.0
	base_dir = _normalize_vector(base_dx, base_dy)
	base_dir_rev = (-base_dir[0], -base_dir[1])
	side_left = _normalize_vector(narrow_left[0] - wide_left[0], narrow_left[1] - wide_left[1])
	side_right = _normalize_vector(narrow_right[0] - wide_right[0], narrow_right[1] - wide_right[1])
	if not base_dir or not side_left or not side_right:
		return 0.0
	base_limit = base_len / 2.0
	left_limit = min(base_limit, math.hypot(narrow_left[0] - wide_left[0], narrow_left[1] - wide_left[1]))
	right_limit = min(base_limit, math.hypot(narrow_right[0] - wide_right[0], narrow_right[1] - wide_right[1]))
	left_angle = _angle_between(side_left, base_dir)
	right_angle = _angle_between(base_dir_rev, side_right)
	max_left = _max_corner_radius(left_angle, left_limit)
	max_right = _max_corner_radius(right_angle, right_limit)
	return min(corner_radius, max_left, max_right)


#============================================
def _corner_fillet(corner: object, dir1: object, dir2: object, radius: object) -> object:
	if radius <= 0:
		return None
	angle = _angle_between(dir1, dir2)
	if angle <= 0:
		return None
	tan_half = math.tan(angle / 2.0)
	if tan_half == 0:
		return None
	offset = radius / tan_half
	tangent1 = (corner[0] + dir1[0] * offset, corner[1] + dir1[1] * offset)
	tangent2 = (corner[0] + dir2[0] * offset, corner[1] + dir2[1] * offset)
	bisector = _normalize_vector(dir1[0] + dir2[0], dir1[1] + dir2[1])
	if not bisector:
		return None
	center_distance = radius / math.sin(angle / 2.0)
	center = (corner[0] + bisector[0] * center_distance, corner[1] + bisector[1] * center_distance)
	angle_start, angle_end = _arc_angles_for_points(center, tangent1, tangent2)
	return (tangent1, tangent2, center, radius, angle_start, angle_end)


#============================================
def _wedge_to_path_commands(narrow_left: object, narrow_right: object, wide_left: object,
		wide_right: object, corner_radius: object) -> tuple:
	if corner_radius <= 0:
		commands = [
			("M", (narrow_left[0], narrow_left[1])),
			("L", (wide_left[0], wide_left[1])),
			("L", (wide_right[0], wide_right[1])),
			("L", (narrow_right[0], narrow_right[1])),
			("Z", None),
		]
		return tuple(commands)
	base_dir = _normalize_vector(wide_right[0] - wide_left[0], wide_right[1] - wide_left[1])
	if not base_dir:
		return tuple([
			("M", (narrow_left[0], narrow_left[1])),
			("L", (wide_left[0], wide_left[1])),
			("L", (wide_right[0], wide_right[1])),
			("L", (narrow_right[0], narrow_right[1])),
			("Z", None),
		])
	base_dir_rev = (-base_dir[0], -base_dir[1])
	side_left = _normalize_vector(narrow_left[0] - wide_left[0], narrow_left[1] - wide_left[1])
	side_right = _normalize_vector(narrow_right[0] - wide_right[0], narrow_right[1] - wide_right[1])
	if not side_left or not side_right:
		return tuple([
			("M", (narrow_left[0], narrow_left[1])),
			("L", (wide_left[0], wide_left[1])),
			("L", (wide_right[0], wide_right[1])),
			("L", (narrow_right[0], narrow_right[1])),
			("Z", None),
		])
	left = _corner_fillet(wide_left, side_left, base_dir, corner_radius)
	right = _corner_fillet(wide_right, base_dir_rev, side_right, corner_radius)
	if not left or not right:
		commands = [
			("M", (narrow_left[0], narrow_left[1])),
			("L", (wide_left[0], wide_left[1])),
			("L", (wide_right[0], wide_right[1])),
			("L", (narrow_right[0], narrow_right[1])),
			("Z", None),
		]
		return tuple(commands)
	left_side, left_base, left_center, left_radius, left_a1, left_a2 = left
	right_base, right_side, right_center, right_radius, right_a1, right_a2 = right
	commands = [
		("M", (narrow_left[0], narrow_left[1])),
		("L", (left_side[0], left_side[1])),
		("ARC", (left_center[0], left_center[1], left_radius, left_a1, left_a2)),
		("L", (right_base[0], right_base[1])),
		("ARC", (right_center[0], right_center[1], right_radius, right_a1, right_a2)),
		("L", (right_side[0], right_side[1])),
		("L", (narrow_right[0], narrow_right[1])),
		("Z", None),
	]
	return tuple(commands)
