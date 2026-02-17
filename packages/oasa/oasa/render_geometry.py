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

"""Geometry producer for shared Cairo/SVG drawing."""

# Standard Library
import dataclasses
import functools
import math
import re

# local repo modules
from . import geometry
from . import misc
from . import render_ops
from . import wedge_geometry

try:
	import cairo as _cairo
except ImportError:
	_cairo = None


VALID_ATTACH_SITES = ("core_center", "stem_centerline", "closed_center")
VALID_BOND_STYLES = (
	"single",
	"double",
	"triple",
	"dashed_hbond",
	"rounded_wedge",
	"hashed_wedge",
	"wavy",
)
BOND_LENGTH_PROFILE = {
	"single": 1.00,
	"double": 0.98,
	"triple": 0.96,
	"dashed_hbond": 1.08,
	"rounded_wedge": 1.00,
	"hashed_wedge": 1.00,
	"wavy": 1.00,
}
BOND_LENGTH_EXCEPTION_TAGS = (
	"EXC_OXYGEN_AVOID_UP",
	"EXC_RING_INTERIOR_CLEARANCE",
)

# Shared gap/perp spec for connector endpoint alignment.
# Gap: distance from connector endpoint to nearest glyph boundary.
# Perp: perpendicular distance from alignment center to connector line.
ATTACH_GAP_TARGET = 1.5
ATTACH_GAP_MIN = 1.3
ATTACH_GAP_MAX = 1.7
ATTACH_PERP_TOLERANCE = 0.07
# fraction of font_size used as the target gap between bond endpoint and glyph body
ATTACH_GAP_FONT_FRACTION = 0.058

# Ratio of wide-end width to narrow-end width for hashed (dashed-wedge)
# bonds.  Higher values produce a wider fan angle between the first and
# last hatch stroke.  Used by both standard OASA bond rendering and the
# Haworth sugar renderer.
HASHED_BOND_WEDGE_RATIO = 4.6

_OVAL_GLYPH_ELEMENTS = {"O", "C", "S"}
_RECT_GLYPH_ELEMENTS = {"N", "H"}
_SPECIAL_GLYPH_ELEMENTS = {"P"}


#============================================
def bond_length_profile() -> dict[str, float]:
	"""Return immutable-copy style-length profile ratios."""
	return dict(BOND_LENGTH_PROFILE)


#============================================
def _normalize_bond_style(bond_style: str) -> str:
	"""Normalize one bond-style selector to canonical style key."""
	if bond_style is None:
		raise ValueError("bond_style must not be None")
	normalized = str(bond_style).strip().lower()
	if normalized not in VALID_BOND_STYLES:
		raise ValueError(f"Invalid bond_style value: {bond_style!r}")
	return normalized


#============================================
def _normalize_exception_tag(exception_tag: str | None) -> str | None:
	"""Normalize one optional exception tag."""
	if exception_tag is None:
		return None
	normalized = str(exception_tag).strip()
	if normalized not in BOND_LENGTH_EXCEPTION_TAGS:
		raise ValueError(f"Invalid bond-length exception tag: {exception_tag!r}")
	return normalized


#============================================
def resolve_bond_length(
		base_length: float,
		bond_style: str,
		requested_length: float | None = None,
		exception_tag: str | None = None) -> float:
	"""Resolve one style-policy bond length with tagged exception enforcement."""
	base_value = float(base_length)
	if base_value < 0.0:
		raise ValueError(f"base_length must be >= 0.0, got {base_length!r}")
	style_key = _normalize_bond_style(bond_style)
	default_length = base_value * float(BOND_LENGTH_PROFILE[style_key])
	if requested_length is None:
		return default_length
	requested = float(requested_length)
	if requested < 0.0:
		raise ValueError(f"requested_length must be >= 0.0, got {requested_length!r}")
	if math.isclose(requested, default_length, abs_tol=1e-9):
		return requested
	tag = _normalize_exception_tag(exception_tag)
	if tag is None:
		raise ValueError(
			"Non-default bond length requires one exception tag from "
			f"{BOND_LENGTH_EXCEPTION_TAGS!r}"
		)
	if tag == "EXC_OXYGEN_AVOID_UP" and requested < (default_length - 1e-9):
		raise ValueError("EXC_OXYGEN_AVOID_UP may only lengthen relative to style default")
	if tag == "EXC_RING_INTERIOR_CLEARANCE" and requested > (default_length + 1e-9):
		raise ValueError("EXC_RING_INTERIOR_CLEARANCE may only shorten relative to style default")
	return requested


#============================================
@dataclasses.dataclass(frozen=True)
class GlyphAttachPrimitive:
	"""Analytic glyph primitive contract for element attach-site geometry."""
	symbol: str
	glyph_class: str
	span_x1: float
	span_x2: float
	y1: float
	y2: float
	core_center_x: float
	stem_centerline_x: float
	closed_center_x: float
	core_half_width: float
	stem_half_width: float
	closed_half_width: float

	def center_x(self, attach_site: str) -> float:
		"""Return centerline x for one attach site."""
		site = _normalize_attach_site(attach_site)
		if site == "core_center":
			return self.core_center_x
		if site == "stem_centerline":
			return self.stem_centerline_x
		if site == "closed_center":
			return self.closed_center_x
		raise ValueError(f"Unsupported attach_site value: {attach_site!r}")

	def half_width(self, attach_site: str) -> float:
		"""Return half-width x span for one attach site."""
		site = _normalize_attach_site(attach_site)
		if site == "core_center":
			return self.core_half_width
		if site == "stem_centerline":
			return self.stem_half_width
		if site == "closed_center":
			return self.closed_half_width
		raise ValueError(f"Unsupported attach_site value: {attach_site!r}")

	def site_box(self, attach_site: str) -> tuple[float, float, float, float]:
		"""Return attach site axis-aligned box."""
		center_x = self.center_x(attach_site)
		half_width = self.half_width(attach_site)
		return misc.normalize_coords(
			(
				center_x - half_width,
				self.y1,
				center_x + half_width,
				self.y2,
			)
		)

	def left_boundary_x(self, attach_site: str) -> float:
		"""Return left x boundary for one attach site."""
		center_x = self.center_x(attach_site)
		half_width = self.half_width(attach_site)
		return center_x - half_width

	def right_boundary_x(self, attach_site: str) -> float:
		"""Return right x boundary for one attach site."""
		center_x = self.center_x(attach_site)
		half_width = self.half_width(attach_site)
		return center_x + half_width


#============================================
@dataclasses.dataclass(frozen=True)
class BondRenderContext:
	molecule: object
	line_width: float
	bond_width: float
	wedge_width: float
	bold_line_width_multiplier: float
	bond_second_line_shortening: float = 0.0
	color_bonds: bool = False
	atom_colors: dict | None = None
	shown_vertices: set | None = None
	bond_coords: dict | None = None
	bond_coords_provider: object | None = None
	point_for_atom: object | None = None
	label_targets: dict | None = None
	attach_targets: dict | None = None
	attach_constraints: 'AttachConstraints | None' = None


#============================================
@dataclasses.dataclass(frozen=True)
class AttachConstraints:
	"""Shared attachment constraints for endpoint resolution and paint legality."""
	line_width: float = 0.0
	clearance: float = 0.0
	vertical_lock: bool = False
	direction_policy: str = "auto"
	target_gap: float = 0.0
	alignment_center: tuple[float, float] | None = None
	alignment_tolerance: float = ATTACH_PERP_TOLERANCE


#============================================
def make_attach_constraints(
		font_size: float | None = None,
		target_gap: float | None = None,
		alignment_tolerance: float = ATTACH_PERP_TOLERANCE,
		line_width: float = 0.0,
		clearance: float = 0.0,
		vertical_lock: bool = False,
		direction_policy: str = "auto",
		alignment_center: tuple[float, float] | None = None) -> AttachConstraints:
	"""Factory for AttachConstraints with three-tier gap resolution.

	Gap resolution priority:
		1. Explicit target_gap wins if provided.
		2. font_size * ATTACH_GAP_FONT_FRACTION if font_size provided.
		3. ATTACH_GAP_TARGET absolute default.

	Args:
		font_size: optional font size for font-relative gap computation.
		target_gap: explicit gap override; takes priority over font_size.
		alignment_tolerance: perpendicular tolerance, defaults to ATTACH_PERP_TOLERANCE.
		line_width: connector line width.
		clearance: extra clearance around target.
		vertical_lock: lock connector to vertical direction.
		direction_policy: direction policy string ("auto" or "line").
		alignment_center: optional alignment center point.

	Returns:
		AttachConstraints instance with resolved gap value.
	"""
	# three-tier gap resolution
	if target_gap is not None:
		resolved_gap = target_gap
	elif font_size is not None:
		resolved_gap = font_size * ATTACH_GAP_FONT_FRACTION
	else:
		resolved_gap = ATTACH_GAP_TARGET
	return AttachConstraints(
		target_gap=resolved_gap,
		alignment_tolerance=alignment_tolerance,
		line_width=line_width,
		clearance=clearance,
		vertical_lock=vertical_lock,
		direction_policy=direction_policy,
		alignment_center=alignment_center,
	)


#============================================
@dataclasses.dataclass(frozen=True)
class AttachTarget:
	"""Attachment target primitive used by shared endpoint resolution."""
	kind: str
	box: tuple[float, float, float, float] | None = None
	center: tuple[float, float] | None = None
	radius: float | None = None
	p1: tuple[float, float] | None = None
	p2: tuple[float, float] | None = None
	targets: tuple | None = None

	def centroid(self):
		"""Return centroid-like interior hint for this target primitive."""
		if self.kind == "box":
			if self.box is None:
				raise ValueError("Box attach target requires box coordinates")
			x1, y1, x2, y2 = misc.normalize_coords(self.box)
			return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
		if self.kind == "circle":
			if self.center is None:
				raise ValueError("Circle attach target requires center coordinates")
			return self.center
		if self.kind == "segment":
			if self.p1 is None or self.p2 is None:
				raise ValueError("Segment attach target requires p1 and p2")
			return ((self.p1[0] + self.p2[0]) / 2.0, (self.p1[1] + self.p2[1]) / 2.0)
		if self.kind == "composite":
			children = self.targets or ()
			if not children:
				raise ValueError("Composite attach target requires at least one child target")
			first_child = _coerce_attach_target(children[0])
			return first_child.centroid()
		raise ValueError(f"Unsupported attach target kind: {self.kind!r}")

	def contains(self, point, epsilon=0.0):
		"""Return True when point is in strict interior for this target."""
		if self.kind == "box":
			if self.box is None:
				raise ValueError("Box attach target requires box coordinates")
			x1, y1, x2, y2 = misc.normalize_coords(self.box)
			return (x1 + epsilon) < point[0] < (x2 - epsilon) and (y1 + epsilon) < point[1] < (y2 - epsilon)
		if self.kind == "circle":
			if self.center is None or self.radius is None:
				raise ValueError("Circle attach target requires center and radius")
			cx, cy = self.center
			distance = math.hypot(point[0] - cx, point[1] - cy)
			return distance < max(0.0, float(self.radius) - epsilon)
		if self.kind == "segment":
			return False
		if self.kind == "composite":
			return any(_coerce_attach_target(child).contains(point, epsilon=epsilon) for child in (self.targets or ()))
		raise ValueError(f"Unsupported attach target kind: {self.kind!r}")

	def boundary_intersection(self, bond_start, interior_hint=None, constraints=None):
		"""Resolve one boundary endpoint from bond_start toward this target."""
		return resolve_attach_endpoint(
			bond_start=bond_start,
			target=self,
			interior_hint=interior_hint,
			constraints=constraints,
		)


#============================================
@dataclasses.dataclass(frozen=True)
class LabelAttachPolicy:
	"""Runtime contract describing one label attachment policy."""
	attach_atom: str = "first"
	attach_element: str | None = None
	attach_site: str = "core_center"
	target_kind: str = "attach_box"


#============================================
@dataclasses.dataclass(frozen=True)
class LabelAttachContract:
	"""Resolved runtime contract for one label connector endpoint."""
	policy: LabelAttachPolicy
	full_target: AttachTarget
	attach_target: AttachTarget
	endpoint_target: AttachTarget
	allowed_target: AttachTarget


#============================================
def make_box_target(bbox: tuple[float, float, float, float]) -> AttachTarget:
	"""Construct one box attachment target."""
	return AttachTarget(kind="box", box=misc.normalize_coords(bbox))


#============================================
def make_circle_target(center: tuple[float, float], radius: float) -> AttachTarget:
	"""Construct one circle attachment target."""
	return AttachTarget(kind="circle", center=center, radius=float(radius))


#============================================
def make_segment_target(p1: tuple[float, float], p2: tuple[float, float]) -> AttachTarget:
	"""Construct one segment attachment target."""
	return AttachTarget(kind="segment", p1=p1, p2=p2)


#============================================
def make_composite_target(targets: list[AttachTarget] | tuple[AttachTarget, ...]) -> AttachTarget:
	"""Construct one ordered composite target with primary-to-fallback targets."""
	return AttachTarget(kind="composite", targets=tuple(targets))


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
def _bond_style_for_edge(edge) -> str:
	"""Map one render edge to the canonical bond-style policy key."""
	try:
		order = int(getattr(edge, "order", 1) or 1)
	except Exception:
		order = 1
	if order == 2:
		return "double"
	if order == 3:
		return "triple"
	type_text = str(getattr(edge, "type", "") or "").strip().lower()
	if type_text == "w":
		return "rounded_wedge"
	if type_text == "h":
		return "hashed_wedge"
	if type_text == "s":
		return "wavy"
	if type_text == "d":
		return "dashed_hbond"
	return "single"


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


#============================================
def vertex_is_shown(vertex):
	if vertex.properties_.get("label"):
		return True
	return vertex.symbol != "C" or vertex.charge != 0 or vertex.multiplicity != 1


#============================================
def vertex_label_text(vertex, show_hydrogens_on_hetero):
	label = vertex.properties_.get("label")
	if label:
		text = label
	else:
		text = vertex.symbol
		if show_hydrogens_on_hetero:
			if vertex.free_valency == 1:
				text += "H"
			elif vertex.free_valency > 1:
				text += "H%d" % vertex.free_valency
	# only append charge as text if no circled marks handle it
	if not vertex.properties_.get("marks"):
		if vertex.charge == 1:
			text += "+"
		elif vertex.charge == -1:
			text += "-"
		elif vertex.charge > 1:
			text += str(vertex.charge) + "+"
		elif vertex.charge < -1:
			text += str(vertex.charge)
	return text


#============================================
def _visible_label_text(text):
	return re.sub(r"<[^>]+>", "", text or "")


#============================================
def _visible_label_length(text):
	return max(1, len(_visible_label_text(text)))


#============================================
def _is_hydroxyl_render_text(text):
	"""Return True when visible text is one hydroxyl token."""
	visible = _visible_label_text(text)
	return visible in ("OH", "HO")


#============================================
def _is_chain_like_render_text(text):
	"""Return True for rendered chain-like carbon labels."""
	visible = _visible_label_text(text)
	if visible.startswith("CH"):
		return True
	# Left-anchored CH2OH labels can render as HOH2C while still attaching to C.
	return visible.endswith("C") and ("H2" in visible)


#============================================
def _text_char_advances(text, font_size, font_name):
	"""Return per-visible-character x advances for one formatted text value."""
	visible = _visible_label_text(text)
	if not visible:
		return []
	fallback = [font_size * 0.60] * len(visible)
	if _cairo is None:
		return fallback
	try:
		surface = _cairo.ImageSurface(_cairo.FORMAT_A8, 1, 1)
		context = _cairo.Context(surface)
		context.select_font_face(font_name or "sans-serif", 0, 0)
	except Exception:
		return fallback
	segments = render_ops._text_segments(str(text or ""))
	advances = []
	for chunk, tags in segments:
		segment_state = render_ops._segment_baseline_state(tags)
		segment_size = render_ops._segment_font_size(font_size, segment_state)
		context.set_font_size(segment_size)
		previous_advance = 0.0
		for index in range(len(chunk)):
			prefix = chunk[: index + 1]
			extents = context.text_extents(prefix)
			char_advance = max(0.0, float(extents.x_advance) - previous_advance)
			advances.append(char_advance)
			previous_advance = float(extents.x_advance)
	if len(advances) != len(visible):
		return fallback
	return advances


#============================================
def _text_ink_bearing_correction(text, font_size, font_name):
	"""Return (left_bearing, right_bearing) for the visible label text.

	The left bearing is the gap between the text origin and the first ink pixel.
	The right bearing is the gap between the last ink pixel and the advance end.
	These represent the amount by which sum(advances) overestimates ink width.
	"""
	visible = _visible_label_text(text)
	if not visible:
		return (0.0, 0.0)
	if _cairo is None:
		return (0.0, 0.0)
	try:
		surface = _cairo.ImageSurface(_cairo.FORMAT_A8, 1, 1)
		context = _cairo.Context(surface)
		context.select_font_face(font_name or "sans-serif", 0, 0)
	except Exception:
		return (0.0, 0.0)
	segments = render_ops._text_segments(str(text or ""))
	# Get left bearing of first segment's first character
	left_bearing = 0.0
	for chunk, tags in segments:
		if not chunk:
			continue
		segment_state = render_ops._segment_baseline_state(tags)
		segment_size = render_ops._segment_font_size(font_size, segment_state)
		context.set_font_size(segment_size)
		first_char = chunk[0]
		extents = context.text_extents(first_char)
		left_bearing = max(0.0, float(extents.x_bearing))
		break
	# Get right bearing of last segment's last character
	right_bearing = 0.0
	for chunk, tags in reversed(segments):
		if not chunk:
			continue
		segment_state = render_ops._segment_baseline_state(tags)
		segment_size = render_ops._segment_font_size(font_size, segment_state)
		context.set_font_size(segment_size)
		last_char = chunk[-1]
		extents = context.text_extents(last_char)
		# right_bearing = advance - left_bearing - ink_width
		char_right = float(extents.x_advance) - float(extents.x_bearing) - float(extents.width)
		right_bearing = max(0.0, char_right)
		break
	return (left_bearing, right_bearing)


#============================================
def _normalize_attach_site(attach_site):
	"""Normalize attach-site selector to one supported semantic value."""
	if attach_site is None:
		return "core_center"
	normalized = str(attach_site).strip().lower()
	# Backward-compat aliases while callers migrate to canonical names.
	alias_map = {
		"element_core": "core_center",
		"element_closed_center": "closed_center",
		"element_stem": "stem_centerline",
	}
	normalized = alias_map.get(normalized, normalized)
	if normalized not in VALID_ATTACH_SITES:
		raise ValueError(f"Invalid attach_site value: {attach_site!r}")
	return normalized


#============================================
def _glyph_class_for_symbol(symbol: str) -> str:
	"""Return canonical analytic glyph primitive class for one element symbol."""
	normalized = _normalize_element_symbol(symbol)
	if normalized in _OVAL_GLYPH_ELEMENTS:
		return "oval"
	if normalized in _RECT_GLYPH_ELEMENTS:
		return "rect"
	if normalized in _SPECIAL_GLYPH_ELEMENTS:
		return "special_p"
	return "rect"


#============================================
@functools.lru_cache(maxsize=512)
def _glyph_center_factor(symbol: str, font_name: str, font_size: float) -> float:
	"""Return normalized center factor within glyph x-advance."""
	if _cairo is None:
		return 0.5
	try:
		surface = _cairo.ImageSurface(_cairo.FORMAT_A8, 1, 1)
		context = _cairo.Context(surface)
		context.select_font_face(font_name or "sans-serif", 0, 0)
		context.set_font_size(float(font_size))
		extents = context.text_extents(symbol)
	except Exception:
		return 0.5
	advance = max(1e-6, float(extents.x_advance))
	center = float(extents.x_bearing) + (float(extents.width) * 0.5)
	factor = center / advance
	return min(1.0, max(0.0, factor))


#============================================
def _glyph_closed_center_factor(symbol: str, font_name: str, font_size: float) -> float:
	"""Return closed-center factor for one glyph symbol."""
	normalized = _normalize_element_symbol(symbol)
	if normalized == "C":
		return _glyph_center_factor("O", font_name, font_size)
	if normalized in ("O", "S"):
		return _glyph_center_factor(normalized, font_name, font_size)
	return _glyph_center_factor(normalized, font_name, font_size)


#============================================
def glyph_attach_primitive(
		symbol: str,
		span_x1: float,
		span_x2: float,
		y1: float,
		y2: float,
		font_size: float,
		font_name: str | None = None) -> GlyphAttachPrimitive:
	"""Build analytic glyph primitive for one element token span."""
	normalized = _normalize_element_symbol(symbol)
	glyph_class = _glyph_class_for_symbol(normalized)
	if normalized == "P" and glyph_class != "special_p":
		raise ValueError("Attach primitive contract requires explicit P special primitive")
	span_width = max(1e-6, span_x2 - span_x1)
	font_size = float(font_size)
	font_name = font_name or "sans-serif"
	core_factor = _glyph_center_factor(normalized, font_name, font_size)
	closed_factor = _glyph_closed_center_factor(normalized, font_name, font_size)
	stem_factor = 0.18
	core_half = max(font_size * 0.08, span_width * 0.16)
	stem_half = max(font_size * 0.06, span_width * 0.10)
	closed_half = core_half
	if glyph_class == "oval":
		stem_factor = 0.12
		core_half = max(font_size * 0.10, span_width * 0.20)
		stem_half = max(font_size * 0.05, span_width * 0.12)
		closed_half = max(font_size * 0.10, span_width * 0.20)
		if normalized == "C":
			# Keep historical core-center behavior for C while adding closed_center.
			core_factor = _glyph_center_factor("O", font_name, font_size)
	elif glyph_class == "special_p":
		# P is explicit special handling (stem + bowl); never generic fallback.
		stem_factor = 0.16
		core_half = max(font_size * 0.09, span_width * 0.18)
		stem_half = max(font_size * 0.05, span_width * 0.10)
		closed_half = max(font_size * 0.08, span_width * 0.16)
	core_center_x = span_x1 + (span_width * min(1.0, max(0.0, core_factor)))
	stem_center_x = span_x1 + (span_width * min(1.0, max(0.0, stem_factor)))
	closed_center_x = span_x1 + (span_width * min(1.0, max(0.0, closed_factor)))
	return GlyphAttachPrimitive(
		symbol=normalized,
		glyph_class=glyph_class,
		span_x1=span_x1,
		span_x2=span_x2,
		y1=y1,
		y2=y2,
		core_center_x=core_center_x,
		stem_centerline_x=stem_center_x,
		closed_center_x=closed_center_x,
		core_half_width=core_half,
		stem_half_width=stem_half,
		closed_half_width=closed_half,
	)


#============================================
def _label_text_origin(x, y, anchor, font_size, text_len):
	del text_len
	baseline_offset = font_size * 0.375
	start_offset = font_size * 0.3125
	if anchor == "start":
		return (x - start_offset, y + baseline_offset)
	return (x, y + baseline_offset)


#============================================
def _core_element_span_box(
		entry,
		span_x1,
		span_x2,
		font_size,
		glyph_char_width,
		attach_site,
		font_name):
	"""Return attach box bounds for one core element glyph span."""
	attach_site = _normalize_attach_site(attach_site)
	symbol = str(entry.get("symbol", ""))
	# Keep multi-letter core spans (for example Cl/Br) unchanged.
	if len(symbol) != 1:
		return (span_x1, span_x2)
	del glyph_char_width
	primitive = glyph_attach_primitive(
		symbol=symbol,
		span_x1=span_x1,
		span_x2=span_x2,
		y1=0.0,
		y2=1.0,
		font_size=font_size,
		font_name=font_name or "sans-serif",
	)
	site_box = primitive.site_box(attach_site)
	return (site_box[0], site_box[2])


#============================================
def _tokenized_atom_spans(text):
	"""Return decorated token spans for visible label text.

	Decorated spans include compact hydrogen/count suffixes (for example `CH2`)
	so existing first/last-token attachment behavior remains stable.
	"""
	return [entry["decorated_span"] for entry in _tokenized_atom_entries(text)]


#============================================
def _label_box_coords(x, y, text, anchor, font_size, font_name=None):
	"""Compute axis-aligned label box coordinates at one label anchor point."""
	text_len = _visible_label_length(text)
	char_advances = _text_char_advances(text, font_size, font_name or "sans-serif")
	if char_advances and len(char_advances) == text_len:
		box_width = sum(char_advances)
	else:
		box_width = font_size * 0.60 * text_len
	# Empirically calibrated against rsvg/Pango rendering of sans-serif at 12pt.
	# top_offset: ascent above baseline (calibrated: 8.8 / 12.0 = 0.733)
	# bottom_offset: descent below baseline (calibrated: 0.1 / 12.0 = 0.008)
	top_offset = -font_size * 0.733
	bottom_offset = font_size * 0.008
	text_x, text_y = _label_text_origin(x, y, anchor, font_size, text_len)
	if anchor == "start":
		x1 = text_x
		x2 = text_x + box_width
	elif anchor == "end":
		x1 = text_x - box_width
		x2 = text_x
	else:
		x1 = text_x - box_width / 2.0
		x2 = text_x + box_width / 2.0
	y1 = text_y + top_offset
	y2 = text_y + bottom_offset
	return misc.normalize_coords((x1, y1, x2, y2))


#============================================
def label_target(x, y, text, anchor, font_size, font_name=None):
	"""Compute one label attachment target at (x, y)."""
	return make_box_target(_label_box_coords(x, y, text, anchor, font_size, font_name=font_name))


#============================================
def label_target_from_text_origin(text_x, text_y, text, anchor, font_size, font_name=None):
	"""Compute one label attachment target from text-origin coordinates."""
	start_offset = font_size * 0.3125
	baseline_offset = font_size * 0.375
	label_x = text_x
	if anchor == "start":
		label_x = text_x + start_offset
	label_y = text_y - baseline_offset
	return label_target(label_x, label_y, text, anchor, font_size, font_name=font_name)


#============================================
def label_attach_target_from_text_origin(
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		attach_element=None,
		attach_site=None,
		font_name=None):
	"""Compute one token-attach target from text-origin coordinates."""
	start_offset = font_size * 0.3125
	baseline_offset = font_size * 0.375
	label_x = text_x
	if anchor == "start":
		label_x = text_x + start_offset
	label_y = text_y - baseline_offset
	return label_attach_target(
		label_x,
		label_y,
		text,
		anchor,
		font_size,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		font_name=font_name,
	)


def _label_attach_box_coords(
		x,
		y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		attach_element=None,
		attach_site=None,
		font_name=None):
	"""Compute box coordinates for one selected attachable atom token."""
	if attach_atom is None:
		attach_atom = "first"
	if attach_atom not in ("first", "last"):
		raise ValueError(f"Invalid attach_atom value: {attach_atom!r}")
	normalized_attach_element = None
	if attach_element is not None:
		if not isinstance(attach_element, str) or not attach_element.strip():
			raise ValueError(f"Invalid attach_element value: {attach_element!r}")
		normalized_attach_element = _normalize_element_symbol(attach_element)
	if attach_site is None:
		if normalized_attach_element == "C":
			attach_site = "closed_center"
		else:
			attach_site = "core_center"
	else:
		attach_site = _normalize_attach_site(attach_site)
	full_bbox = _label_box_coords(x, y, text, anchor, font_size, font_name=font_name)
	entries = _tokenized_atom_entries(text)
	if not entries:
		return full_bbox
	spans = [entry["decorated_span"] for entry in entries]
	selected_span = None
	selected_entry = None
	if normalized_attach_element is not None:
		# Formula-aware attachment: attach_element resolves to the core element
		# glyph span (for example just "C" in CH2OH), not the decorated token.
		matched = [entry for entry in entries if entry["symbol"] == normalized_attach_element]
		if matched:
			if attach_atom == "last":
				selected_entry = matched[-1]
			else:
				selected_entry = matched[0]
			selected_span = selected_entry["core_span"]
	if selected_span is None:
		if len(spans) <= 1:
			return full_bbox
		if attach_atom == "last":
			selected_span = spans[-1]
		else:
			selected_span = spans[0]
	start_index, end_index = selected_span
	visible_len = _visible_label_length(text)
	if visible_len <= 1:
		return full_bbox
	x1, y1, x2, y2 = full_bbox
	# Project token spans using the same segmented text metrics model that
	# render_ops uses for markup-aware text drawing.
	char_advances = _text_char_advances(text, font_size, font_name or "sans-serif")
	if len(char_advances) != visible_len:
		char_advances = [font_size * 0.60] * visible_len
	cumulative_advances = [0.0]
	for advance in char_advances:
		cumulative_advances.append(cumulative_advances[-1] + float(advance))
	glyph_width = cumulative_advances[-1]
	glyph_char_width = glyph_width / float(visible_len) if visible_len else (font_size * 0.60)
	text_x, _text_y = _label_text_origin(x, y, anchor, font_size, visible_len)
	if anchor == "start":
		glyph_x1 = text_x
	elif anchor == "end":
		glyph_x1 = text_x - glyph_width
	else:
		glyph_x1 = text_x - (glyph_width / 2.0)
	span_x1 = glyph_x1 + cumulative_advances[start_index]
	span_x2 = glyph_x1 + cumulative_advances[end_index]
	if selected_entry is not None:
		attach_x1, attach_x2 = _core_element_span_box(
			selected_entry,
			span_x1,
			span_x2,
			font_size,
			glyph_char_width,
			attach_site=attach_site,
			font_name=font_name or "sans-serif",
		)
	else:
		attach_x1 = span_x1
		attach_x2 = span_x2
	# Clamp to full label bbox so attach targets cannot escape label bounds.
	attach_x1 = min(max(attach_x1, x1), x2)
	attach_x2 = min(max(attach_x2, x1), x2)
	return misc.normalize_coords((attach_x1, y1, attach_x2, y2))


#============================================
def label_attach_target(
		x,
		y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		attach_element=None,
		attach_site=None,
		font_name=None):
	"""Compute one attach-token target within a label."""
	return make_box_target(
		_label_attach_box_coords(
			x,
			y,
			text,
			anchor,
			font_size,
			attach_atom=attach_atom,
			attach_element=attach_element,
			attach_site=attach_site,
			font_name=font_name,
		)
	)


#============================================
def default_label_attach_policy(text, chain_attach_site="core_center") -> LabelAttachPolicy:
	"""Return runtime-default attach policy for one rendered label text."""
	site = _normalize_attach_site(chain_attach_site)
	visible = _visible_label_text(text)
	if _is_hydroxyl_render_text(visible):
		attach_atom = "first" if visible == "OH" else "last"
		return LabelAttachPolicy(
			attach_atom=attach_atom,
			attach_element="O",
			attach_site="core_center",
			target_kind="oxygen_circle",
		)
	if _is_chain_like_render_text(visible):
		return LabelAttachPolicy(
			attach_atom="first",
			attach_element="C",
			attach_site=site,
			target_kind="label_box",
		)
	return LabelAttachPolicy(
		attach_atom="first",
		attach_element=None,
		attach_site="core_center",
		target_kind="attach_box",
	)


#============================================
def _resolve_label_attach_policy(
		text,
		attach_atom=None,
		attach_element=None,
		attach_site=None,
		chain_attach_site="core_center",
		target_kind=None):
	"""Resolve one explicit-or-default label attach policy."""
	default_policy = default_label_attach_policy(
		text=text,
		chain_attach_site=chain_attach_site,
	)
	resolved_atom = default_policy.attach_atom if attach_atom is None else attach_atom
	if resolved_atom not in ("first", "last"):
		raise ValueError(f"Invalid attach_atom value: {attach_atom!r}")
	resolved_element = default_policy.attach_element if attach_element is None else attach_element
	normalized_element = None
	if resolved_element is not None:
		normalized_element = _normalize_element_symbol(resolved_element)
	if attach_site is None:
		resolved_site = default_policy.attach_site
	else:
		resolved_site = _normalize_attach_site(attach_site)
	resolved_target_kind = default_policy.target_kind if target_kind is None else str(target_kind).strip().lower()
	if resolved_target_kind not in ("attach_box", "label_box", "oxygen_circle"):
		raise ValueError(f"Unsupported label endpoint target_kind: {target_kind!r}")
	return LabelAttachPolicy(
		attach_atom=resolved_atom,
		attach_element=normalized_element,
		attach_site=resolved_site,
		target_kind=resolved_target_kind,
	)


#============================================
def _oxygen_circle_target_from_attach_target(
		attach_target,
		font_size,
		line_width):
	"""Return hydroxyl O-centered circle target from one attach box."""
	x1, y1, x2, y2 = attach_target.box
	center = ((x1 + x2) * 0.5, (y1 + y2) * 0.5)
	base_radius = max(max(0.0, x2 - x1), max(0.0, y2 - y1)) * 0.5
	# Keep hydroxyl endpoint targeting near the glyph perimeter so connector
	# endpoints remain visually attached to the oxygen shape in matrix output.
	safety_margin = max(0.05, float(font_size) * 0.005)
	line_margin = max(0.0, float(line_width)) * 0.05
	radius = base_radius + line_margin + safety_margin
	return make_circle_target(center, radius)


#============================================
def _oxygen_allowed_target(full_target, endpoint_target):
	"""Return paint-allowed target for hydroxyl oxygen circles."""
	if full_target.kind != "box" or endpoint_target.kind != "circle":
		return endpoint_target
	return make_composite_target((endpoint_target, full_target))


#============================================
def _chain_attach_allowed_target(
		full_target,
		attach_target):
	"""Return paint-allowed target corridors for chain-like C attachment."""
	if full_target.kind != "box" or attach_target.kind != "box":
		return attach_target
	full_x1, full_y1, full_x2, full_y2 = full_target.box
	attach_x1, attach_y1, attach_x2, attach_y2 = attach_target.box
	targets = [attach_target]
	if full_x1 < attach_x1:
		targets.append(make_box_target((full_x1, attach_y1, attach_x1, attach_y2)))
	if attach_x2 < full_x2:
		targets.append(make_box_target((attach_x2, attach_y1, full_x2, attach_y2)))
	if full_y1 < attach_y1:
		targets.append(make_box_target((attach_x1, full_y1, attach_x2, attach_y1)))
	if attach_y2 < full_y2:
		targets.append(make_box_target((attach_x1, attach_y2, attach_x2, full_y2)))
	if len(targets) == 1:
		return attach_target
	return make_composite_target(tuple(targets))


#============================================
def label_allowed_target_from_text_origin(
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		line_width=0.0,
		attach_atom=None,
		attach_element=None,
		attach_site=None,
		chain_attach_site="core_center",
		target_kind=None,
		font_name=None):
	"""Resolve one paint-allowed label target from text-origin inputs."""
	contract = label_attach_contract_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		line_width=line_width,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		chain_attach_site=chain_attach_site,
		target_kind=target_kind,
		font_name=font_name,
	)
	return contract.allowed_target


#============================================
def label_attach_contract_from_text_origin(
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		line_width=0.0,
		attach_atom=None,
		attach_element=None,
		attach_site=None,
		chain_attach_site="core_center",
		target_kind=None,
		font_name=None):
	"""Resolve full runtime attach contract for one label at text origin."""
	policy = _resolve_label_attach_policy(
		text=text,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		chain_attach_site=chain_attach_site,
		target_kind=target_kind,
	)
	full_target = label_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		font_name=font_name,
	)
	attach_target = label_attach_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		attach_atom=policy.attach_atom,
		attach_element=policy.attach_element,
		attach_site=policy.attach_site,
		font_name=font_name,
	)
	endpoint_target = attach_target
	if policy.target_kind == "label_box":
		# Full-box bond trimming: use the entire label bounding box
		# for both endpoint and paint-allowed targets.
		endpoint_target = full_target
	elif policy.target_kind == "oxygen_circle":
		endpoint_target = _oxygen_circle_target_from_attach_target(
			attach_target=attach_target,
			font_size=font_size,
			line_width=line_width,
		)
	allowed_target = endpoint_target
	if policy.target_kind == "label_box":
		allowed_target = full_target
	elif policy.target_kind == "oxygen_circle":
		allowed_target = _oxygen_allowed_target(
			full_target=full_target,
			endpoint_target=endpoint_target,
		)
	elif (
			policy.target_kind == "attach_box"
			and policy.attach_element == "C"
			and endpoint_target.kind == "box"
			and full_target.kind == "box"
	):
		allowed_target = _chain_attach_allowed_target(
			full_target=full_target,
			attach_target=endpoint_target,
		)
	return LabelAttachContract(
		policy=policy,
		full_target=full_target,
		attach_target=attach_target,
		endpoint_target=endpoint_target,
		allowed_target=allowed_target,
	)


#============================================
def resolve_label_connector_endpoint_from_text_origin(
		bond_start,
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		line_width=0.0,
		constraints=None,
		epsilon=0.5,
		attach_atom=None,
		attach_element=None,
		attach_site=None,
		chain_attach_site="core_center",
		target_kind=None,
		font_name=None):
	"""Resolve one connector endpoint via the shared label attach contract."""
	contract = label_attach_contract_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		line_width=line_width,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		chain_attach_site=chain_attach_site,
		target_kind=target_kind,
		font_name=font_name,
	)
	if constraints is None:
		constraints = AttachConstraints()
	endpoint = resolve_attach_endpoint(
		bond_start=bond_start,
		target=contract.endpoint_target,
		interior_hint=contract.endpoint_target.centroid(),
		constraints=constraints,
	)
	# Label-box mode skips automatic alignment toward the attach-atom
	# centroid (the caller already positioned the text via anchor_x_offset
	# or _align_text_origin_*). An explicit alignment_center in
	# constraints is still honoured (used by chain ops for collinearity).
	if contract.policy.target_kind == "label_box":
		alignment_center = constraints.alignment_center
	else:
		alignment_center = constraints.alignment_center
		if alignment_center is None:
			alignment_center = contract.attach_target.centroid()
	if alignment_center is not None:
		endpoint = _correct_endpoint_for_alignment(
			bond_start=bond_start,
			endpoint=endpoint,
			alignment_center=alignment_center,
			target=contract.endpoint_target,
			tolerance=constraints.alignment_tolerance,
		)
	endpoint = retreat_endpoint_until_legal(
		line_start=bond_start,
		line_end=endpoint,
		line_width=line_width,
		forbidden_regions=[contract.full_target],
		allowed_regions=[contract.allowed_target],
		epsilon=epsilon,
	)
	if constraints.target_gap > 0.0:
		endpoint = _retreat_to_target_gap(
			line_start=bond_start,
			legal_endpoint=endpoint,
			target_gap=constraints.target_gap,
			forbidden_regions=[contract.endpoint_target],
		)
		# When endpoint_target is already the full label box (label_box
		# mode), the second retreat is redundant -- skip it.
		if contract.policy.target_kind != "label_box":
			# After retreating from the endpoint atom, the bond may still be
			# too close to the full label box (e.g. the bond over "HOH2C"
			# clears the C glyph but passes above the "2" subscript).
			# Apply a minimum gap from the full label using the base gap
			# constant, not the (possibly larger) connector-specific target.
			full_text_min_gap = ATTACH_GAP_TARGET
			full_gap = _min_distance_point_to_target_boundary(
				endpoint, contract.full_target,
			)
			if full_gap < full_text_min_gap:
				endpoint = _retreat_to_target_gap(
					line_start=bond_start,
					legal_endpoint=endpoint,
					target_gap=full_text_min_gap,
					forbidden_regions=[contract.full_target],
				)
	return endpoint, contract


#============================================
def _normalize_element_symbol(symbol: str) -> str:
	"""Normalize one element symbol to canonical letter case."""
	text = str(symbol).strip()
	if len(text) == 1:
		return text.upper()
	return text[0].upper() + text[1:].lower()


#============================================
def _tokenized_atom_entries(text):
	"""Return atom token entries with core/decorated span information.

	Each entry exposes:
	- `core_span`: element-symbol-only span (for example `C` in `CH2`)
	- `decorated_span`: element plus compact suffix decoration span
	  (for example `CH2`)
	"""
	visible_text = _visible_label_text(text)
	entries = []
	length = len(visible_text)
	index = 0
	while index < length:
		char = visible_text[index]
		if not char.isupper():
			index += 1
			continue
		core_start = index
		index += 1
		if index < length and visible_text[index].islower():
			index += 1
		core_end = index
		symbol = visible_text[core_start:core_end]
		decorated_end = core_end
		# Optional atom count directly after the symbol, e.g. O3.
		while decorated_end < length and visible_text[decorated_end].isdigit():
			decorated_end += 1
		has_explicit_count = decorated_end > core_end
		# Condensed hydrogens belong to the decorated token unless this atom
		# already had an explicit numeric count (e.g. O3H should tokenize as O3 + H).
		if symbol != "H" and not has_explicit_count and decorated_end < length and visible_text[decorated_end] == "H":
			decorated_end += 1
			while decorated_end < length and visible_text[decorated_end].isdigit():
				decorated_end += 1
		# Optional trailing charge on terminal tokens, e.g. NH3+.
		if decorated_end < length and visible_text[decorated_end] in "+-":
			charge_end = decorated_end + 1
			while charge_end < length and visible_text[charge_end].isdigit():
				charge_end += 1
			if charge_end == length:
				decorated_end = charge_end
		entries.append(
			{
				"symbol": symbol,
				"core_span": (core_start, core_end),
				"decorated_span": (core_start, decorated_end),
			}
		)
		index = max(index, decorated_end)
	return entries


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
def _ray_circle_boundary_intersection(start, center, radius, direction):
	"""Return first forward ray intersection with one circle boundary."""
	far_scale = max(4096.0, float(radius) * 256.0)
	far_point = (
		start[0] + (direction[0] * far_scale),
		start[1] + (direction[1] * far_scale),
	)
	return _line_circle_intersection(start, far_point, center, radius)


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


#============================================
def _coerce_attach_target(target):
	"""Normalize attach target inputs into AttachTarget objects."""
	if isinstance(target, AttachTarget):
		return target
	raise ValueError(f"Unsupported attach target: {target!r}")


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


#============================================
def _resolved_vertex_label_layout(vertex, show_hydrogens_on_hetero, font_size, font_name):
	if not vertex_is_shown(vertex):
		return None
	text = vertex_label_text(vertex, show_hydrogens_on_hetero)
	if not text:
		return None
	label_anchor = vertex.properties_.get("label_anchor")
	auto_anchor = label_anchor is None
	if label_anchor is None:
		label_anchor = "start"
	text_len = _visible_label_length(text)
	if auto_anchor and text_len == 1:
		label_anchor = "middle"
	bbox = label_target(
		vertex.x,
		vertex.y,
		text,
		label_anchor,
		font_size,
		font_name=font_name,
	).box
	text_origin = _label_text_origin(vertex.x, vertex.y, label_anchor, font_size, text_len)
	return {
		"text": text,
		"anchor": label_anchor,
		"text_len": text_len,
		"bbox": bbox,
		"text_origin": text_origin,
	}


#============================================
def _transform_bbox(bbox, transform_xy):
	if transform_xy is None:
		return bbox
	x1, y1, x2, y2 = bbox
	tx1, ty1 = transform_xy(x1, y1)
	tx2, ty2 = transform_xy(x2, y2)
	return misc.normalize_coords((tx1, ty1, tx2, ty2))


#============================================
def _transform_target(target, transform_xy):
	"""Return one attachment target transformed by transform_xy."""
	resolved = _coerce_attach_target(target)
	if transform_xy is None:
		return resolved
	if resolved.kind == "box":
		return make_box_target(_transform_bbox(resolved.box, transform_xy))
	if resolved.kind == "circle":
		center = transform_xy(resolved.center[0], resolved.center[1])
		edge = transform_xy(resolved.center[0] + float(resolved.radius), resolved.center[1])
		radius = geometry.point_distance(center[0], center[1], edge[0], edge[1])
		return make_circle_target(center, radius)
	if resolved.kind == "segment":
		p1 = transform_xy(resolved.p1[0], resolved.p1[1])
		p2 = transform_xy(resolved.p2[0], resolved.p2[1])
		return make_segment_target(p1, p2)
	if resolved.kind == "composite":
		return make_composite_target([_transform_target(child, transform_xy) for child in (resolved.targets or ())])
	raise ValueError(f"Unsupported attach target kind: {resolved.kind!r}")


#============================================
def build_vertex_ops(vertex, transform_xy=None, show_hydrogens_on_hetero=False,
		color_atoms=True, atom_colors=None, font_name="Arial", font_size=16):
	layout = _resolved_vertex_label_layout(
		vertex,
		show_hydrogens_on_hetero=show_hydrogens_on_hetero,
		font_size=font_size,
		font_name=font_name,
	)
	if layout is None:
		return []

	def transform_point(x, y):
		if transform_xy:
			return transform_xy(x, y)
		return (x, y)

	ops = []
	text = layout["text"]
	label_anchor = layout["anchor"]
	x1, y1, x2, y2 = layout["bbox"]
	x, y = layout["text_origin"]
	center_x = (x1 + x2) / 2.0

	if vertex.multiplicity in (2, 3):
		center = transform_point(center_x, y - 17)
		ops.append(render_ops.CircleOp(
			center=center,
			radius=3,
			fill="#000",
			stroke="#fff",
			stroke_width=1.0,
		))
		if vertex.multiplicity == 3:
			center = transform_point(center_x, y + 5)
			ops.append(render_ops.CircleOp(
				center=center,
				radius=3,
				fill="#000",
				stroke="#fff",
				stroke_width=1.0,
			))

	points = (
		transform_point(x1, y1),
		transform_point(x2, y1),
		transform_point(x2, y2),
		transform_point(x1, y2),
	)
	ops.append(render_ops.PolygonOp(
		points=points,
		fill="#fff",
		stroke="#fff",
		stroke_width=1.0,
	))

	if color_atoms and atom_colors:
		color = render_ops.color_to_hex(atom_colors.get(vertex.symbol, (0, 0, 0))) or "#000"
	else:
		color = "#000"

	text_x, text_y = transform_point(x, y)
	ops.append(render_ops.TextOp(
		x=text_x,
		y=text_y,
		text=text,
		font_size=font_size,
		font_name=font_name,
		anchor=label_anchor,
		weight="bold",
		color=color,
	))

	# render circled charge marks (plus/minus) when present
	for mark_data in vertex.properties_.get("marks", []):
		mark_type = mark_data["type"]
		mx, my = transform_point(mark_data["x"], mark_data["y"])
		# scale mark proportionally with font_size (standard_size=10 at font_size=16)
		radius = font_size * 5.0 / 16.0
		inset = font_size * 2.0 / 16.0
		# CPK convention: plus=blue, minus=red
		if mark_type == "plus":
			mark_color = "#0000ff"
		else:
			mark_color = "#ff0000"
		# circle outline
		ops.append(render_ops.CircleOp(
			center=(mx, my),
			radius=radius,
			fill=None,
			stroke=mark_color,
			stroke_width=1.0,
		))
		# horizontal line (both plus and minus)
		ops.append(render_ops.LineOp(
			p1=(mx - radius + inset, my),
			p2=(mx + radius - inset, my),
			width=1.0,
			color=mark_color,
		))
		# vertical line (plus only)
		if mark_type == "plus":
			ops.append(render_ops.LineOp(
				p1=(mx, my - radius + inset),
				p2=(mx, my + radius - inset),
				width=1.0,
				color=mark_color,
			))

	return ops


_DEFAULT_STYLE = {
	"line_width": 2.0,
	"bond_width": 6.0,
	"wedge_width": 2.0 * HASHED_BOND_WEDGE_RATIO,
	"bold_line_width_multiplier": 1.2,
	"bond_second_line_shortening": 0.0,
	"color_atoms": True,
	"color_bonds": True,
	"atom_colors": None,
	"show_hydrogens_on_hetero": False,
	"font_name": "Arial",
	"font_size": 16.0,
	"show_carbon_symbol": False,
	"attach_gap_target": ATTACH_GAP_TARGET,
	"attach_perp_tolerance": ATTACH_PERP_TOLERANCE,
}


#============================================
def _resolve_style(style):
	resolved = dict(_DEFAULT_STYLE)
	if style:
		resolved.update(style)
	return resolved


#============================================
def _render_edge_key(edge):
	"""Return canonical unordered render key for one bond edge."""
	v1, v2 = edge.vertices
	id1 = id(v1)
	id2 = id(v2)
	if id1 <= id2:
		return (id1, id2)
	return (id2, id1)


#============================================
def _render_edge_priority(edge):
	"""Return deterministic priority for duplicate bond-edge collapse."""
	try:
		order = int(getattr(edge, "order", 1) or 1)
	except Exception:
		order = 1
	type_text = str(getattr(edge, "type", "") or "")
	# Keep wedged/hashed/wavy style bonds over plain lines when duplicates exist.
	type_rank = 1 if type_text in ("w", "h", "s", "q") else 0
	aromatic_rank = 1 if bool(getattr(edge, "aromatic", 0)) else 0
	return (order, type_rank, aromatic_rank, -id(edge))


#============================================
def _render_edges_in_order(mol):
	"""Yield canonical non-duplicated edges for one molecule render pass."""
	ordered_keys = []
	chosen = {}
	for edge in mol.edges:
		key = _render_edge_key(edge)
		if key not in chosen:
			ordered_keys.append(key)
			chosen[key] = edge
			continue
		if _render_edge_priority(edge) > _render_edge_priority(chosen[key]):
			chosen[key] = edge
	for key in ordered_keys:
		yield chosen[key]


#============================================
def _edge_points(mol, transform_xy):
	points = {}
	for edge in _render_edges_in_order(mol):
		v1, v2 = edge.vertices
		if transform_xy:
			points[edge] = (transform_xy(v1.x, v1.y), transform_xy(v2.x, v2.y))
		else:
			points[edge] = ((v1.x, v1.y), (v2.x, v2.y))
	return points


#============================================
def molecule_to_ops(mol, style=None, transform_xy=None):
	"""Convert one molecule into a render-ops list for SVG/Cairo painters."""
	if mol is None:
		return []
	used_style = _resolve_style(style)
	shown_vertices = set()
	for vertex in mol.vertices:
		if used_style["show_carbon_symbol"] and vertex.symbol == "C":
			shown_vertices.add(vertex)
		elif vertex_is_shown(vertex):
			shown_vertices.add(vertex)
	bond_coords = _edge_points(mol, transform_xy=transform_xy)
	label_targets = {}
	attach_targets = {}
	for vertex in shown_vertices:
		layout = _resolved_vertex_label_layout(
			vertex,
			show_hydrogens_on_hetero=bool(used_style["show_hydrogens_on_hetero"]),
			font_size=float(used_style["font_size"]),
			font_name=str(used_style["font_name"]),
		)
		if layout is None:
			continue
		label_target_obj = label_target(
			vertex.x,
			vertex.y,
			layout["text"],
			layout["anchor"],
			float(used_style["font_size"]),
			font_name=str(used_style["font_name"]),
		)
		label_target_obj = _transform_target(label_target_obj, transform_xy)
		label_targets[vertex] = label_target_obj
		if len(_tokenized_atom_spans(layout["text"])) <= 1:
			continue
		attach_mode = vertex.properties_.get("attach_atom", "first")
		attach_element = vertex.properties_.get("attach_element")
		attach_site = vertex.properties_.get("attach_site")
		attach_target_obj = label_attach_target(
			vertex.x,
			vertex.y,
			layout["text"],
			layout["anchor"],
			float(used_style["font_size"]),
			attach_atom=attach_mode,
			attach_element=attach_element,
			attach_site=attach_site,
			font_name=str(used_style["font_name"]),
		)
		attach_target_obj = _transform_target(attach_target_obj, transform_xy)
		attach_targets[vertex] = attach_target_obj
	attach_constraints = make_attach_constraints(
		target_gap=float(used_style["attach_gap_target"]),
		alignment_tolerance=float(used_style["attach_perp_tolerance"]),
		line_width=float(used_style["line_width"]),
	)
	context = BondRenderContext(
		molecule=mol,
		line_width=float(used_style["line_width"]),
		bond_width=float(used_style["bond_width"]),
		wedge_width=float(used_style["wedge_width"]),
		bold_line_width_multiplier=float(used_style["bold_line_width_multiplier"]),
		bond_second_line_shortening=float(used_style["bond_second_line_shortening"]),
		color_bonds=bool(used_style["color_bonds"]),
		atom_colors=used_style["atom_colors"],
		shown_vertices=shown_vertices,
		bond_coords=bond_coords,
		bond_coords_provider=bond_coords.get,
		point_for_atom=(lambda a: transform_xy(a.x, a.y)) if transform_xy else None,
		label_targets=label_targets,
		attach_targets=attach_targets,
		attach_constraints=attach_constraints,
	)
	ops = []
	for edge in _render_edges_in_order(mol):
		start, end = bond_coords[edge]
		ops.extend(build_bond_ops(edge, start, end, context))
	for vertex in mol.vertices:
		vertex_ops = build_vertex_ops(
			vertex,
			transform_xy=transform_xy,
			show_hydrogens_on_hetero=bool(used_style["show_hydrogens_on_hetero"]),
			color_atoms=bool(used_style["color_atoms"]),
			atom_colors=used_style["atom_colors"],
			font_name=str(used_style["font_name"]),
			font_size=float(used_style["font_size"]),
		)
		ops.extend(vertex_ops)
	return ops
