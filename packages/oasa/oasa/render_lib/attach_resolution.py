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

"""Endpoint resolution, paint legality, and retreat for render operations."""

# Standard Library
import math

# local repo modules
from oasa import geometry
from oasa import oasa_utils as misc
from oasa.render_lib.data_types import AttachConstraints
from oasa.render_lib.data_types import _coerce_attach_target
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.low_level_geometry import _box_center
from oasa.render_lib.low_level_geometry import _capsule_intersects_target
from oasa.render_lib.low_level_geometry import _circle_boundary_toward_target
from oasa.render_lib.low_level_geometry import _clip_line_to_box
from oasa.render_lib.low_level_geometry import _closest_point_on_segment
from oasa.render_lib.low_level_geometry import _expanded_box
from oasa.render_lib.low_level_geometry import _lattice_step_for_direction_policy
from oasa.render_lib.low_level_geometry import _line_circle_intersection
from oasa.render_lib.low_level_geometry import _line_intersection
from oasa.render_lib.low_level_geometry import _point_in_attach_target
from oasa.render_lib.low_level_geometry import _point_in_attach_target_closed
from oasa.render_lib.low_level_geometry import _ray_box_boundary_intersection
from oasa.render_lib.low_level_geometry import _ray_circle_boundary_intersection
from oasa.render_lib.low_level_geometry import _snapped_direction_unit
from oasa.render_lib.low_level_geometry import _vertical_circle_boundary
from oasa.render_lib.low_level_geometry import directional_attach_edge_intersection


#============================================
def resolve_attach_endpoint(
		bond_start,
		target,
		interior_hint=None,
		constraints=None):
	"""Resolve one bond endpoint against one attachment target."""
	resolved_target = _coerce_attach_target(target)
	if constraints is None:
		constraints = AttachConstraints()
	line_width = max(0.0, float(constraints.line_width))
	clearance = max(0.0, float(constraints.clearance))
	margin = clearance + (line_width / 2.0)
	if resolved_target.kind == "composite":
		children = resolved_target.targets or ()
		if not children:
			raise ValueError("Composite attach target must include at least one child target")
		last_error = None
		for child in children:
			try:
				return resolve_attach_endpoint(
					bond_start=bond_start,
					target=child,
					interior_hint=interior_hint,
					constraints=constraints,
				)
			except ValueError as error:
				last_error = error
				continue
		if last_error is not None:
			raise last_error
		raise ValueError("Composite attach target did not resolve any child target")
	if resolved_target.kind == "box":
		attach_bbox = _expanded_box(resolved_target.box, margin)
		hint = interior_hint if interior_hint is not None else _box_center(attach_bbox)
		if constraints.vertical_lock:
			vertical = _vertical_box_intersection(bond_start, attach_bbox, hint)
			if vertical is not None:
				return vertical
		return directional_attach_edge_intersection(
			bond_start=bond_start,
			attach_bbox=attach_bbox,
			attach_target=hint,
			direction_policy=constraints.direction_policy,
		)
	if resolved_target.kind == "circle":
		radius = max(0.0, float(resolved_target.radius) + margin)
		center = resolved_target.center
		hint = interior_hint if interior_hint is not None else center
		if constraints.vertical_lock:
			vertical = _vertical_circle_boundary(bond_start, center, radius, hint=hint)
			if vertical is not None:
				return vertical
		lattice_step = _lattice_step_for_direction_policy(constraints.direction_policy)
		if lattice_step is not None:
			dx = hint[0] - bond_start[0]
			dy = hint[1] - bond_start[1]
			snapped_direction = _snapped_direction_unit(dx, dy, lattice_step)
			if snapped_direction is not None:
				hit = _ray_circle_boundary_intersection(
					start=bond_start,
					center=center,
					radius=radius,
					direction=snapped_direction,
				)
				if hit is not None:
					return hit
		return _circle_boundary_toward_target(bond_start, center, radius, target=hint)
	if resolved_target.kind == "segment":
		p1 = resolved_target.p1
		p2 = resolved_target.p2
		hint = interior_hint if interior_hint is not None else (
			(p1[0] + p2[0]) / 2.0,
			(p1[1] + p2[1]) / 2.0,
		)
		if constraints.vertical_lock:
			candidate = _line_intersection(
				(bond_start[0], bond_start[1]),
				(bond_start[0], bond_start[1] + 1.0),
				p1,
				p2,
			)
			if candidate is not None:
				return _closest_point_on_segment(candidate, p1, p2)
		intersection = _line_intersection(bond_start, hint, p1, p2)
		if intersection is not None:
			return _closest_point_on_segment(intersection, p1, p2)
		return _closest_point_on_segment(hint, p1, p2)
	raise ValueError(f"Unsupported attach target kind: {resolved_target.kind!r}")


#============================================
def _vertical_box_intersection(bond_start, attach_bbox, interior_hint):
	"""Return vertical-lock box boundary intersection, or None if unavailable."""
	x1, y1, x2, y2 = misc.normalize_coords(attach_bbox)
	start_x, start_y = bond_start
	if start_x < x1 or start_x > x2:
		return None
	hint_y = interior_hint[1]
	direction = hint_y - start_y
	candidates = [y1, y2]
	if abs(direction) <= 1e-12:
		candidates.sort(key=lambda value: abs(value - start_y))
	else:
		candidates.sort(
			key=lambda value: (
				((value - start_y) * direction) < 0.0,
				abs(value - start_y),
			)
	)
	return (start_x, candidates[0])


#============================================
def _target_to_box_list(target):
	"""Return list of box primitives for one target, or None if non-box exists."""
	resolved = _coerce_attach_target(target)
	if resolved.kind == "box":
		return [misc.normalize_coords(resolved.box)]
	if resolved.kind != "composite":
		return None
	boxes = []
	for child in (resolved.targets or ()):
		child_boxes = _target_to_box_list(child)
		if child_boxes is None:
			return None
		boxes.extend(child_boxes)
	return boxes


#============================================
def _subtract_box_by_box(source_box, cut_box):
	"""Subtract cut_box from source_box and return remaining box pieces."""
	sx1, sy1, sx2, sy2 = misc.normalize_coords(source_box)
	cx1, cy1, cx2, cy2 = misc.normalize_coords(cut_box)
	ix1 = max(sx1, cx1)
	iy1 = max(sy1, cy1)
	ix2 = min(sx2, cx2)
	iy2 = min(sy2, cy2)
	if ix1 >= ix2 or iy1 >= iy2:
		return [(sx1, sy1, sx2, sy2)]
	pieces = [
		(sx1, sy1, ix1, sy2),
		(ix2, sy1, sx2, sy2),
		(ix1, sy1, ix2, iy1),
		(ix1, iy2, ix2, sy2),
	]
	return [
		misc.normalize_coords(piece)
		for piece in pieces
		if (piece[2] - piece[0]) > 0.0 and (piece[3] - piece[1]) > 0.0
	]


#============================================
def _forbidden_minus_allowed_boxes(forbidden_box, allowed_boxes):
	"""Return pieces of forbidden_box that are outside allowed_boxes union."""
	pieces = [misc.normalize_coords(forbidden_box)]
	for allowed_box in allowed_boxes:
		next_pieces = []
		for piece in pieces:
			next_pieces.extend(_subtract_box_by_box(piece, allowed_box))
		pieces = next_pieces
		if not pieces:
			break
	return pieces


#============================================
def _validate_attachment_paint_box_regions(
		line_start,
		line_end,
		half_width,
		forbidden_boxes,
		allowed_boxes,
		epsilon):
	"""Validate connector paint using exact forbidden-minus-allowed box pieces."""
	for forbidden_box in forbidden_boxes:
		for piece in _forbidden_minus_allowed_boxes(forbidden_box, allowed_boxes):
			if _capsule_intersects_target(
					line_start,
					line_end,
					half_width,
					make_box_target(piece),
					epsilon):
				return False
	return True


#============================================
def validate_attachment_paint(
		line_start,
		line_end,
		line_width,
		forbidden_regions,
		allowed_regions=None,
		epsilon=0.5):
	"""Return True when connector paint does not penetrate forbidden interiors."""
	if allowed_regions is None:
		allowed_regions = []
	half_width = max(0.0, float(line_width)) / 2.0
	# Fast analytic path: when no allowed carve-outs are active, validate paint
	# by continuous capsule-vs-target checks to avoid sampling false negatives.
	if not allowed_regions:
		for region in forbidden_regions:
			if _capsule_intersects_target(line_start, line_end, half_width, region, epsilon):
				return False
		return True
	# Exact box-primitive path with carve-outs: detect forbidden-minus-allowed
	# penetration analytically so strict checks cannot miss narrow overlaps.
	forbidden_boxes = []
	allowed_boxes = []
	use_box_solver = True
	for region in forbidden_regions:
		boxes = _target_to_box_list(region)
		if boxes is None:
			use_box_solver = False
			break
		forbidden_boxes.extend(boxes)
	if use_box_solver:
		for region in allowed_regions:
			boxes = _target_to_box_list(region)
			if boxes is None:
				use_box_solver = False
				break
			allowed_boxes.extend(boxes)
	if use_box_solver and forbidden_boxes:
		return _validate_attachment_paint_box_regions(
			line_start=line_start,
			line_end=line_end,
			half_width=half_width,
			forbidden_boxes=forbidden_boxes,
			allowed_boxes=allowed_boxes,
			epsilon=epsilon,
		)
	# Fallback path with allowed carve-outs: keep explicit point checks so
	# forbidden-minus-allowed semantics stay identical to existing behavior.
	dx = line_end[0] - line_start[0]
	dy = line_end[1] - line_start[1]
	length = math.hypot(dx, dy)
	if length <= 1e-12:
		sample_points = [line_start]
	else:
		base_step = max(0.02, min(0.2, half_width * 0.25 if half_width > 0.0 else 0.05))
		steps = max(64, int(math.ceil(length / base_step)))
		sample_points = [
			(
				line_start[0] + (dx * (index / float(steps))),
				line_start[1] + (dy * (index / float(steps))),
			)
			for index in range(steps + 1)
		]
	offsets = [(0.0, 0.0)]
	if length > 1e-12 and half_width > 1e-12:
		nx = -dy / length
		ny = dx / length
		offsets.extend(
			[
				(nx * half_width, ny * half_width),
				(-nx * half_width, -ny * half_width),
				(nx * half_width * 0.5, ny * half_width * 0.5),
				(-nx * half_width * 0.5, -ny * half_width * 0.5),
			]
		)
	for base_point in sample_points:
		for ox, oy in offsets:
			point = (base_point[0] + ox, base_point[1] + oy)
			is_forbidden = any(
				_point_in_attach_target(point, region, epsilon=epsilon)
				for region in forbidden_regions
			)
			if not is_forbidden:
				continue
			is_allowed = any(
				_point_in_attach_target(point, region, epsilon=epsilon)
				for region in allowed_regions
			)
			if not is_allowed:
				return False
	return True


#============================================
def retreat_endpoint_until_legal(
		line_start,
		line_end,
		line_width,
		forbidden_regions,
		allowed_regions=None,
		epsilon=0.5,
		max_iterations=28):
	"""Retreat line_end toward line_start until attachment paint becomes legal."""
	if allowed_regions is None:
		allowed_regions = []

	def _endpoint_in_allowed(point):
		if not allowed_regions:
			return True
		return any(
			_point_in_attach_target_closed(point, region, epsilon=max(0.0, float(epsilon)))
			for region in allowed_regions
		)

	if validate_attachment_paint(
			line_start=line_start,
			line_end=line_end,
			line_width=line_width,
			forbidden_regions=forbidden_regions,
			allowed_regions=allowed_regions,
			epsilon=epsilon) and _endpoint_in_allowed(line_end):
		return line_end
	x_start, y_start = line_start
	x_end, y_end = line_end
	low = 0.0
	high = 1.0
	for _ in range(max(1, int(max_iterations))):
		mid = (low + high) * 0.5
		candidate = (
			x_start + ((x_end - x_start) * mid),
			y_start + ((y_end - y_start) * mid),
		)
		if validate_attachment_paint(
				line_start=line_start,
				line_end=candidate,
				line_width=line_width,
				forbidden_regions=forbidden_regions,
				allowed_regions=allowed_regions,
				epsilon=epsilon) and _endpoint_in_allowed(candidate):
			low = mid
		else:
			high = mid
	if low <= 1e-12:
		return line_start
	return (
		x_start + ((x_end - x_start) * low),
		y_start + ((y_end - y_start) * low),
	)


#============================================
def _min_distance_point_to_target_boundary(point, target):
	"""Return minimum distance from point to the boundary of one attach target."""
	resolved = _coerce_attach_target(target)
	if resolved.kind == "box":
		x1, y1, x2, y2 = misc.normalize_coords(resolved.box)
		px, py = point
		dx = max(x1 - px, 0.0, px - x2)
		dy = max(y1 - py, 0.0, py - y2)
		if dx > 0.0 or dy > 0.0:
			return math.hypot(dx, dy)
		return min(px - x1, x2 - px, py - y1, y2 - py)
	if resolved.kind == "circle":
		cx, cy = resolved.center
		radius = max(0.0, float(resolved.radius))
		return abs(math.hypot(point[0] - cx, point[1] - cy) - radius)
	if resolved.kind == "composite":
		distances = [
			_min_distance_point_to_target_boundary(point, child)
			for child in (resolved.targets or ())
		]
		return min(distances) if distances else 0.0
	return 0.0


#============================================
def _retreat_to_target_gap(line_start, legal_endpoint, target_gap, forbidden_regions):
	"""Retreat legal_endpoint further toward line_start to achieve target_gap.

	Iterates up to 4 times to handle diagonal approach angles where
	retreating along the bond axis produces less perpendicular gap than
	the retreat distance.  Converges in 2-3 iterations for typical cases.
	"""
	if target_gap <= 0.0:
		return legal_endpoint
	sx, sy = line_start
	ex, ey = legal_endpoint
	dx = ex - sx
	dy = ey - sy
	length = math.hypot(dx, dy)
	if length <= 1e-12:
		return legal_endpoint
	if not forbidden_regions:
		# no geometry to re-measure against; single retreat by target_gap
		retreat_fraction = target_gap / length
		if retreat_fraction >= 1.0:
			return line_start
		return (ex - (dx * retreat_fraction), ey - (dy * retreat_fraction))
	# iterate: re-measure gap after each retreat to handle diagonal approach
	# angles where retreat distance != gap distance
	for _ in range(4):
		current_gap = min(
			_min_distance_point_to_target_boundary((ex, ey), region)
			for region in forbidden_regions
		)
		if current_gap >= target_gap:
			break
		needed = target_gap - current_gap
		retreat_fraction = needed / length
		if retreat_fraction >= 1.0:
			return line_start
		ex = ex - (dx * retreat_fraction)
		ey = ey - (dy * retreat_fraction)
	return (ex, ey)


#============================================
def _perpendicular_distance_to_line(point, line_start, line_end):
	"""Return perpendicular distance from point to the infinite line through start/end."""
	px, py = point
	sx, sy = line_start
	ex, ey = line_end
	dx = ex - sx
	dy = ey - sy
	length_sq = (dx * dx) + (dy * dy)
	if length_sq <= 1e-24:
		return math.hypot(px - sx, py - sy)
	return abs(((dy * (px - sx)) - (dx * (py - sy)))) / math.sqrt(length_sq)


#============================================
def _correct_endpoint_for_alignment(bond_start, endpoint, alignment_center, target, tolerance):
	"""Adjust endpoint so bond line passes through alignment_center."""
	perp_dist = _perpendicular_distance_to_line(alignment_center, bond_start, endpoint)
	if perp_dist <= tolerance:
		return endpoint
	resolved = _coerce_attach_target(target)
	sx, sy = bond_start
	cx, cy = alignment_center
	dx = cx - sx
	dy = cy - sy
	if abs(dx) <= 1e-12 and abs(dy) <= 1e-12:
		return endpoint
	if resolved.kind == "box":
		bbox = misc.normalize_coords(resolved.box)
		corrected = _clip_line_to_box((sx, sy), (cx, cy), bbox)
		if corrected is not None and corrected != (cx, cy):
			return corrected
		corrected = geometry.intersection_of_line_and_rect(
			(sx, sy, cx, cy), bbox,
		)
		if corrected is not None:
			return corrected
	elif resolved.kind == "circle":
		center = resolved.center
		radius = max(0.0, float(resolved.radius))
		hit = _line_circle_intersection((sx, sy), (cx, cy), center, radius)
		if hit is not None:
			return hit
	elif resolved.kind == "composite":
		# collect candidates from all children, pick lowest perp error
		candidates = []
		for child in (resolved.targets or ()):
			try:
				result = _correct_endpoint_for_alignment(
					bond_start, endpoint, alignment_center, child, tolerance,
				)
				if result != endpoint:
					candidates.append(result)
			except ValueError:
				continue
		if candidates:
			# score: (perp error to centerline, deviation from original endpoint)
			ex, ey = endpoint
			best = min(
				candidates,
				key=lambda c: (
					_perpendicular_distance_to_line(alignment_center, bond_start, c),
					math.hypot(c[0] - ex, c[1] - ey),
				),
			)
			return best
	return endpoint
