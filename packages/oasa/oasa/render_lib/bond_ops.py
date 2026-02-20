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

"""Bond rendering: style ops and build_bond_ops()."""

# Standard Library
import math

# local repo modules
from oasa import geometry
from oasa import oasa_utils as misc
from oasa import render_ops
from oasa import wedge_geometry
from oasa.render_lib.data_types import AttachConstraints
from oasa.render_lib.data_types import _coerce_attach_target
from oasa.render_lib.bond_length_policy import _bond_style_for_edge
from oasa.render_lib.bond_length_policy import resolve_bond_length
from oasa.render_lib.low_level_geometry import _capsule_intersects_target
from oasa.render_lib.attach_resolution import _correct_endpoint_for_alignment
from oasa.render_lib.attach_resolution import _retreat_to_target_gap
from oasa.render_lib.attach_resolution import resolve_attach_endpoint
from oasa.render_lib.attach_resolution import retreat_endpoint_until_legal


#============================================
def haworth_front_edge_geometry(start, end, width, overlap=None, front_pad=None):
	x1, y1 = start
	x2, y2 = end
	d = math.hypot(x2 - x1, y2 - y1)
	if d == 0:
		return None
	dx = (x2 - x1) / d
	dy = (y2 - y1) / d
	if overlap is None:
		overlap = max(1.0, 0.25 * width)
	if front_pad is None:
		front_pad = max(overlap, 0.35 * width)
	x1 -= dx * front_pad
	y1 -= dy * front_pad
	x2 += dx * front_pad
	y2 += dy * front_pad
	cap_radius = width / 2.0
	x1 += dx * cap_radius
	y1 += dy * cap_radius
	x2 -= dx * cap_radius
	y2 -= dy * cap_radius
	normal = (-dy, dx)
	return (x1, y1), (x2, y2), normal, cap_radius


#============================================
def haworth_front_edge_ops(start, end, width, color):
	geom = haworth_front_edge_geometry(start, end, width)
	if not geom:
		return []
	(start, end, _normal, _cap_radius) = geom
	return [render_ops.LineOp(start, end, width=width, cap="round", color=color)]


#============================================
def _point_for_atom(context, atom):
	if context.point_for_atom:
		return context.point_for_atom(atom)
	return (atom.x, atom.y)


#============================================
def _edge_wavy_style(edge):
	return (getattr(edge, "wavy_style", None)
			or edge.properties_.get("wavy_style")
			or "sine")


#============================================
def _edge_line_color(edge):
	color = getattr(edge, "line_color", None)
	if not color:
		color = edge.properties_.get("line_color") or edge.properties_.get("color")
	return render_ops.color_to_hex(color)


#============================================
def _edge_line_width(edge, context):
	if edge.type == 'b':
		return context.line_width * context.bold_line_width_multiplier
	return context.line_width


#============================================
def _resolve_edge_colors(edge, context, has_shown_vertex):
	edge_color = _edge_line_color(edge)
	if edge_color:
		return edge_color, edge_color, False
	if context.color_bonds and context.atom_colors:
		v1, v2 = edge.vertices
		color1 = render_ops.color_to_hex(context.atom_colors.get(v1.symbol, (0, 0, 0))) or "#000"
		color2 = render_ops.color_to_hex(context.atom_colors.get(v2.symbol, (0, 0, 0))) or "#000"
		if has_shown_vertex and color1 != color2:
			return color1, color2, True
		return color1, color2, False
	return "#000", "#000", False


#============================================
def _line_ops(start, end, width, color1, color2, gradient, cap):
	if gradient and color1 and color2 and color1 != color2:
		mid = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
		return [
			render_ops.LineOp(start, mid, width=width, cap=cap, color=color1),
			render_ops.LineOp(mid, end, width=width, cap=cap, color=color2),
		]
	return [render_ops.LineOp(start, end, width=width, cap=cap, color=color1 or "#000")]


#============================================
def _rounded_wedge_ops(start, end, line_width, wedge_width, color):
	geom = wedge_geometry.rounded_wedge_geometry(start, end, wedge_width, line_width)
	return [render_ops.PathOp(commands=geom["path_commands"], fill=color or "#000")]


#============================================
def _hashed_ops(start, end, line_width, wedge_width, color1, color2, gradient):
	x1, y1 = start
	x2, y2 = end
	d = geometry.point_distance(x1, y1, x2, y2)
	if d == 0:
		return []
	# Unit vector along bond and perpendicular
	ux = (x2 - x1) / d
	uy = (y2 - y1) / d
	px = -uy
	py = ux
	step_size = max(2 * line_width, 0.4 * wedge_width)
	ns = round(d / step_size) or 1
	step_size = d / ns
	ops = []
	total = int(round(d / step_size)) + 1
	middle = max(1, total // 2)
	for i in range(1, total):
		t = i * step_size
		frac = t / d
		# Linearly interpolate half-width from line_width to wedge_width
		half_w = line_width / 2.0 + frac * (wedge_width / 2.0 - line_width / 2.0)
		# Center point on bond axis
		cx = x1 + ux * t
		cy = y1 + uy * t
		# Hash line perpendicular to bond axis
		hx1 = cx + px * half_w
		hy1 = cy + py * half_w
		hx2 = cx - px * half_w
		hy2 = cy - py * half_w
		color = color1
		if gradient and color2 and i >= middle:
			color = color2
		ops.append(render_ops.LineOp((hx1, hy1), (hx2, hy2),
				width=line_width, cap="butt", color=color))
	return ops


#============================================
def _wave_points(start, end, line_width, wedge_width, style):
	x1, y1 = start
	x2, y2 = end
	d = geometry.point_distance(x1, y1, x2, y2)
	if d == 0:
		return []
	dx = (x2 - x1) / d
	dy = (y2 - y1) / d
	px = -dy
	py = dx
	ref = max(wedge_width, line_width)
	amplitude = max(ref * 0.40, 1.0)
	wavelength = max(ref * 1.2, 6.0)
	# Use 4 sparse control points per wavelength (at 0, 0.25, 0.5, 0.75)
	# so Tk's B-spline smooth=1 creates genuinely smooth curves.
	# Overshoot amplitude by 1.5x to compensate for B-spline not passing
	# through control points.
	amp_ctrl = amplitude * 1.5
	n_waves = max(1, int(round(d / wavelength)))
	wl_actual = d / n_waves
	points = []
	for n in range(n_waves):
		for frac in (0.0, 0.25, 0.5, 0.75):
			t = (n + frac) * wl_actual
			if t > d:
				break
			phase = frac
			if style == "triangle":
				value = 2 * abs(2 * (phase - math.floor(phase + 0.5))) - 1
			elif style == "box":
				value = 1.0 if math.sin(2 * math.pi * phase) >= 0 else -1.0
			elif style == "half-circle":
				half = wl_actual / 2.0
				local = ((t % half) / half) if half > 0 else 0
				value = math.sqrt(max(0.0, 1 - (2 * local - 1) ** 2))
				if int(t / half) % 2 if half > 0 else False:
					value *= -1
			else:
				value = math.sin(2 * math.pi * phase)
			ox = px * amp_ctrl * value
			oy = py * amp_ctrl * value
			points.append((x1 + dx * t + ox, y1 + dy * t + oy))
	# Always include endpoint on the baseline
	points.append((x1 + dx * d, y1 + dy * d))
	return points


#============================================
def _wavy_ops(start, end, line_width, wedge_width, style, color):
	points = _wave_points(start, end, line_width, wedge_width, style)
	if len(points) < 2:
		return []
	commands = [("M", (points[0][0], points[0][1]))]
	for x, y in points[1:]:
		commands.append(("L", (x, y)))
	return [render_ops.PathOp(commands=tuple(commands), fill="none", stroke=color or "#000",
			stroke_width=line_width * 1.1, cap="round", join="round")]


#============================================
def _double_bond_side(context, v1, v2, start, end, has_shown_vertex):
	side = 0
	in_ring = False
	molecule = context.molecule
	if molecule:
		for ring in molecule.get_smallest_independent_cycles():
			if v1 in ring and v2 in ring:
				in_ring = True
				double_bonds = len([bond for bond in molecule.vertex_subgraph_to_edge_subgraph(ring) if bond.order == 2])
				for atom in ring:
					if atom is v1 or atom is v2:
						continue
					side += double_bonds * geometry.on_which_side_is_point(
						start + end, _point_for_atom(context, atom)
					)
	if not side:
		for atom in v1.neighbors + v2.neighbors:
			if atom is v1 or atom is v2:
				continue
			side += geometry.on_which_side_is_point(start + end, _point_for_atom(context, atom))
	if not side and (in_ring or not has_shown_vertex):
		if in_ring:
			side = 1
		else:
			if len(v1.neighbors) == 1 and len(v2.neighbors) == 1:
				side = 0
			elif len(v1.neighbors) < 3 and len(v2.neighbors) < 3 and molecule:
				side = sum(
					geometry.on_which_side_is_point(start + end, _point_for_atom(context, atom))
					for atom in molecule.vertices
					if atom is not v1 and atom is not v2
				)
				if not side:
					side = 1
	return side


#============================================
def _context_attach_target_for_vertex(context, vertex):
	"""Resolve attachment target for one vertex."""
	if context.attach_targets and vertex in context.attach_targets:
		return _coerce_attach_target(context.attach_targets[vertex])
	if context.label_targets and vertex in context.label_targets:
		return _coerce_attach_target(context.label_targets[vertex])
	return None


#============================================
def _clip_to_target(bond_start, target):
	"""Clip one endpoint to one target using default Phase B policy.

	Deprecated: superseded by _resolve_endpoint_with_constraints() which
	adds centerline correction, legality retreat, and target-gap retreat.
	"""
	if target is None:
		return bond_start
	return resolve_attach_endpoint(
		bond_start=bond_start,
		target=target,
		interior_hint=target.centroid(),
		constraints=AttachConstraints(direction_policy="auto"),
	)


#============================================
def _resolve_endpoint_with_constraints(bond_start, target, constraints=None, line_width=0.0):
	"""Resolve one bond endpoint using the full 4-step constraint pipeline."""
	if target is None:
		return bond_start
	if constraints is None:
		constraints = AttachConstraints(direction_policy="auto")

	# Step 1: boundary resolve
	endpoint = resolve_attach_endpoint(
		bond_start=bond_start, target=target,
		interior_hint=target.centroid(), constraints=constraints,
	)

	# Step 2: centerline correction
	alignment_center = constraints.alignment_center
	if alignment_center is None:
		alignment_center = target.centroid()
	endpoint = _correct_endpoint_for_alignment(
		bond_start=bond_start, endpoint=endpoint,
		alignment_center=alignment_center, target=target,
		tolerance=constraints.alignment_tolerance,
	)

	# Step 3: legality retreat (forbidden = target, no allowed sub-regions)
	endpoint = retreat_endpoint_until_legal(
		line_start=bond_start, line_end=endpoint,
		line_width=line_width, forbidden_regions=[target], allowed_regions=[],
	)

	# Step 4: target-gap retreat
	if constraints.target_gap > 0.0:
		endpoint = _retreat_to_target_gap(
			line_start=bond_start, legal_endpoint=endpoint,
			target_gap=constraints.target_gap, forbidden_regions=[target],
		)

	return endpoint


#============================================
def _edge_length_override(edge) -> float | None:
	"""Resolve optional explicit edge length override from attrs/properties."""
	override = getattr(edge, "bond_length_override", None)
	if override is not None:
		return float(override)
	properties = getattr(edge, "properties_", None) or {}
	override = properties.get("bond_length_override")
	if override is None:
		return None
	return float(override)


#============================================
def _edge_length_exception_tag(edge) -> str | None:
	"""Resolve optional edge length exception tag from attrs/properties."""
	tag = getattr(edge, "bond_length_exception_tag", None)
	if tag:
		return str(tag)
	properties = getattr(edge, "properties_", None) or {}
	tag = properties.get("bond_length_exception_tag")
	if tag is None:
		return None
	return str(tag)


#============================================
def _apply_bond_length_policy(edge, start, end):
	"""Apply style-length policy to one edge segment."""
	base_length = geometry.point_distance(start[0], start[1], end[0], end[1])
	if base_length <= 0.0:
		return start, end
	style_key = _bond_style_for_edge(edge)
	target_length = resolve_bond_length(
		base_length=base_length,
		bond_style=style_key,
		requested_length=_edge_length_override(edge),
		exception_tag=_edge_length_exception_tag(edge),
	)
	if math.isclose(target_length, base_length, abs_tol=1e-9):
		return start, end
	scale = target_length / base_length
	dx = end[0] - start[0]
	dy = end[1] - start[1]
	resolved_end = (start[0] + (dx * scale), start[1] + (dy * scale))
	return start, resolved_end


#============================================
def _avoid_cross_label_overlaps(start, end, half_width, own_vertices, label_targets, epsilon=0.5):
	"""Retreat bond endpoints away from non-own-vertex label targets.

	For each label target that is NOT owned by one of the bond's own vertices,
	check whether the stroked bond segment (capsule) penetrates the target.  If
	so, retreat the nearer endpoint via ``retreat_endpoint_until_legal``.

	Returns the (possibly shortened) ``(start, end)`` pair.
	"""
	if not label_targets:
		return start, end
	cross_targets = [
		t for v, t in label_targets.items()
		if v not in own_vertices
	]
	if not cross_targets:
		return start, end
	min_length = max(half_width * 4.0, 1.0)
	for target in cross_targets:
		if not _capsule_intersects_target(start, end, half_width, target, epsilon):
			continue
		seg_length = geometry.point_distance(start[0], start[1], end[0], end[1])
		if seg_length < min_length:
			break
		centroid = _coerce_attach_target(target).centroid()
		d_start = geometry.point_distance(centroid[0], centroid[1], start[0], start[1])
		d_end = geometry.point_distance(centroid[0], centroid[1], end[0], end[1])
		if d_end <= d_start:
			new_end = retreat_endpoint_until_legal(
				line_start=start, line_end=end, line_width=half_width * 2.0,
				forbidden_regions=[target], epsilon=epsilon,
			)
			if geometry.point_distance(start[0], start[1], new_end[0], new_end[1]) >= min_length:
				end = new_end
		else:
			new_start = retreat_endpoint_until_legal(
				line_start=end, line_end=start, line_width=half_width * 2.0,
				forbidden_regions=[target], epsilon=epsilon,
			)
			if geometry.point_distance(new_start[0], new_start[1], end[0], end[1]) >= min_length:
				start = new_start
	return start, end


#============================================
def build_bond_ops(edge, start, end, context):
	if start is None or end is None:
		return []
	v1, v2 = edge.vertices
	target_v1 = _context_attach_target_for_vertex(context, v1)
	target_v2 = _context_attach_target_for_vertex(context, v2)
	if target_v1 is not None:
		start = _resolve_endpoint_with_constraints(
			end, target_v1, constraints=context.attach_constraints,
			line_width=context.line_width)
	if target_v2 is not None:
		end = _resolve_endpoint_with_constraints(
			start, target_v2, constraints=context.attach_constraints,
			line_width=context.line_width)
	start, end = _apply_bond_length_policy(edge, start, end)
	edge_line_width = _edge_line_width(edge, context)
	if context.label_targets:
		start, end = _avoid_cross_label_overlaps(
			start, end,
			half_width=edge_line_width / 2.0,
			own_vertices={v1, v2},
			label_targets=context.label_targets,
		)
	has_shown_vertex = False
	if context.shown_vertices:
		has_shown_vertex = v1 in context.shown_vertices or v2 in context.shown_vertices
	color1, color2, gradient = _resolve_edge_colors(edge, context, has_shown_vertex)
	ops = []

	if edge.order == 1:
		if edge.type == 'w':
			haworth_front = edge.properties_.get("haworth_position") == "front"
			if haworth_front:
				overlap = max(1.0, 0.25 * context.wedge_width)
				d = geometry.point_distance(start[0], start[1], end[0], end[1])
				if d:
					dx = (end[0] - start[0]) / d
					dy = (end[1] - start[1]) / d
					end = (end[0] + dx * overlap, end[1] + dy * overlap)
			ops.extend(_rounded_wedge_ops(start, end, context.line_width,
					context.wedge_width, color1))
			return ops
		if edge.type == 'h':
			ops.extend(_hashed_ops(start, end, context.line_width, context.wedge_width,
					color1, color2, gradient))
			return ops
		if edge.type == 'q':
			ops.extend(haworth_front_edge_ops(start, end, context.wedge_width, color1))
			return ops
		if edge.type == 's':
			ops.extend(_wavy_ops(start, end, edge_line_width, context.wedge_width, _edge_wavy_style(edge), color1))
			return ops
		ops.extend(_line_ops(start, end, edge_line_width, color1, color2, gradient, cap="round"))
		return ops

	if edge.order == 2:
		# honor explicit center="yes" from CDML; skip geometric side detection
		if getattr(edge, "center", None):
			side = 0
		else:
			side = _double_bond_side(context, v1, v2, start, end, has_shown_vertex)
		if side:
			ops.extend(_line_ops(start, end, edge_line_width, color1, color2, gradient, cap="round"))
			x1, y1, x2, y2 = geometry.find_parallel(
				start[0], start[1], end[0], end[1], context.bond_width * misc.signum(side)
			)
			length = geometry.point_distance(x1, y1, x2, y2)
			if length and context.bond_second_line_shortening:
				if not context.shown_vertices or v2 not in context.shown_vertices:
					x2, y2 = geometry.elongate_line(x1, y1, x2, y2,
							-context.bond_second_line_shortening * length)
				if not context.shown_vertices or v1 not in context.shown_vertices:
					x1, y1 = geometry.elongate_line(x2, y2, x1, y1,
							-context.bond_second_line_shortening * length)
			if context.label_targets:
				(x1, y1), (x2, y2) = _avoid_cross_label_overlaps(
					(x1, y1), (x2, y2), half_width=edge_line_width / 2.0,
					own_vertices={v1, v2}, label_targets=context.label_targets,
				)
			ops.extend(_line_ops((x1, y1), (x2, y2), edge_line_width,
					color1, color2, gradient, cap="butt"))
			return ops
		for i in (1, -1):
			x1, y1, x2, y2 = geometry.find_parallel(
				start[0], start[1], end[0], end[1], i * context.bond_width * 0.5
			)
			if context.label_targets:
				(x1, y1), (x2, y2) = _avoid_cross_label_overlaps(
					(x1, y1), (x2, y2), half_width=edge_line_width / 2.0,
					own_vertices={v1, v2}, label_targets=context.label_targets,
				)
			ops.extend(_line_ops((x1, y1), (x2, y2), edge_line_width,
					color1, color2, gradient, cap="round"))
		return ops

	if edge.order == 3:
		ops.extend(_line_ops(start, end, edge_line_width, color1, color2, gradient, cap="round"))
		for i in (1, -1):
			x1, y1, x2, y2 = geometry.find_parallel(
				start[0], start[1], end[0], end[1], i * context.bond_width * 0.7
			)
			if context.label_targets:
				(x1, y1), (x2, y2) = _avoid_cross_label_overlaps(
					(x1, y1), (x2, y2), half_width=edge_line_width / 2.0,
					own_vertices={v1, v2}, label_targets=context.label_targets,
				)
			ops.extend(_line_ops((x1, y1), (x2, y2), edge_line_width,
					color1, color2, gradient, cap="butt"))
	return ops
