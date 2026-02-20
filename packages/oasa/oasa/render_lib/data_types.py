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

"""Dataclasses, constants, and factory functions for render geometry."""

# Standard Library
import dataclasses
import math

# local repo modules
from oasa import oasa_utils as misc


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
		# late import to avoid circular dependency with attach_resolution
		from oasa.render_lib.attach_resolution import resolve_attach_endpoint
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
def _coerce_attach_target(target):
	"""Normalize attach target inputs into AttachTarget objects."""
	if isinstance(target, AttachTarget):
		return target
	raise ValueError(f"Unsupported attach target: {target!r}")


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
def _normalize_element_symbol(symbol: str) -> str:
	"""Normalize one element symbol to canonical letter case."""
	text = str(symbol).strip()
	if len(text) == 1:
		return text.upper()
	return text[0].upper() + text[1:].lower()
