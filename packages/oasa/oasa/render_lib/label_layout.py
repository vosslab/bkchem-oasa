#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Small deterministic label-placement choices for schematic renderers.

This module intentionally knows only geometry.  Callers decide their own
text aliases and semantics, then offer a finite set of already-authored
presentations.  The stable candidate key makes equal geometry reproducible
without making label spelling or producer identity part of layout policy.
"""

# Standard Library
import dataclasses
import math

# local repo modules
from oasa.render_lib.attach_resolution import validate_attachment_paint
from oasa.render_lib.data_types import ATTACH_GAP_TARGET
from oasa.render_lib.data_types import AttachConstraints
from oasa.render_lib.data_types import AttachTarget
from oasa.render_lib.data_types import LabelAttachContract
from oasa.render_lib.label_geometry import resolve_label_connector_endpoint_from_text_origin


#============================================
@dataclasses.dataclass(frozen=True)
class LabelPlacementCandidate:
	"""One caller-authored, finite label placement option."""
	text: str
	anchor: str
	font_scale: float
	nominal_origin: tuple[float, float]
	connector_start: tuple[float, float]
	attach_contract: LabelAttachContract
	constraints: AttachConstraints
	candidate_key: tuple[int, int, int]
	font_size: float
	font_name: str = "sans-serif"


#============================================
@dataclasses.dataclass(frozen=True)
class LabelPlacementResult:
	"""One scored label placement without producer-specific metadata."""
	text: str
	anchor: str
	origin: tuple[float, float]
	font_scale: float
	connector_end: tuple[float, float]
	candidate_key: tuple[int, int, int]


#============================================
def choose_label_placement(
		candidates: tuple[LabelPlacementCandidate, ...],
		occupied_targets: tuple[AttachTarget, ...] = (),
		blocked_targets: tuple[AttachTarget, ...] = (),
		blocked_polygons: tuple[tuple[tuple[float, float], ...], ...] = (),
		connector_width: float = 0.0,
		minimum_gap: float = ATTACH_GAP_TARGET) -> LabelPlacementResult:
	"""Select the best finite candidate by geometry and a stable key.

	The chooser is deliberately local: it makes one placement decision against
	already occupied geometry.  Callers that place multiple labels retain their
	semantic ordering and feed each chosen target into the next invocation.
	"""
	if not candidates:
		raise ValueError("Label placement requires at least one candidate")
	if minimum_gap < 0.0:
		raise ValueError("Label placement minimum gap must be nonnegative")
	ordered = sorted(candidates, key=lambda candidate: candidate.candidate_key)
	scored = [
		_score_candidate(
			candidate=candidate,
			occupied_targets=occupied_targets,
			blocked_targets=blocked_targets,
			blocked_polygons=blocked_polygons,
			connector_width=connector_width,
			minimum_gap=minimum_gap,
		)
		for candidate in ordered
	]
	best_score, best_result = min(scored, key=lambda entry: entry[0])
	del best_score
	return best_result


#============================================
def label_target_overlap_score(
		targets: tuple[AttachTarget, ...],
		minimum_gap: float = 0.0) -> float:
	"""Return pairwise geometric overlap for an already-authored label set."""
	if minimum_gap < 0.0:
		raise ValueError("Label target overlap minimum gap must be nonnegative")
	return sum(
		_target_overlap(left, right, minimum_gap)
		for index, left in enumerate(targets)
		for right in targets[index + 1:]
	)


#============================================
def _score_candidate(
		candidate: LabelPlacementCandidate,
		occupied_targets: tuple[AttachTarget, ...],
		blocked_targets: tuple[AttachTarget, ...],
		blocked_polygons: tuple[tuple[tuple[float, float], ...], ...],
		connector_width: float,
		minimum_gap: float) -> tuple[tuple[float, ...], LabelPlacementResult]:
	"""Return a geometry-only score and resolved candidate result."""
	font_size = candidate.font_size * candidate.font_scale
	policy = candidate.attach_contract.policy
	end, contract = resolve_label_connector_endpoint_from_text_origin(
		bond_start=candidate.connector_start,
		text_x=candidate.nominal_origin[0],
		text_y=candidate.nominal_origin[1],
		text=candidate.text,
		anchor=candidate.anchor,
		font_size=font_size,
		line_width=connector_width,
		constraints=candidate.constraints,
		attach_atom=policy.attach_atom,
		attach_element=policy.attach_element,
		attach_site=policy.attach_site,
		target_kind=policy.target_kind,
		font_name=candidate.font_name,
	)
	result = LabelPlacementResult(
		text=candidate.text,
		anchor=candidate.anchor,
		origin=candidate.nominal_origin,
		font_scale=candidate.font_scale,
		connector_end=end,
		candidate_key=candidate.candidate_key,
	)
	label_target = contract.full_target
	blocked_overlap = sum(_target_overlap(label_target, target) for target in blocked_targets)
	occupied_overlap = sum(_target_overlap(label_target, target, minimum_gap) for target in occupied_targets)
	polygon_overlap = sum(
		1.0 for polygon in blocked_polygons if _box_overlaps_polygon(label_target.box, polygon)
	)
	connector_blocked = sum(
		1.0
		for target in blocked_targets
		if not validate_attachment_paint(
			line_start=candidate.connector_start,
			line_end=end,
			line_width=connector_width,
			forbidden_regions=[target],
			epsilon=0.0,
		)
	)
	connector_polygons = sum(
		1.0
		for polygon in blocked_polygons
		if _segment_hits_polygon(candidate.connector_start, end, polygon)
	)
	displacement = math.hypot(
		candidate.nominal_origin[0] - candidate.connector_start[0],
		candidate.nominal_origin[1] - candidate.connector_start[1],
	)
	score = (
		polygon_overlap + connector_polygons,
		blocked_overlap + connector_blocked,
		occupied_overlap,
		1.0 - candidate.font_scale,
		displacement,
		float(candidate.candidate_key[0]),
		float(candidate.candidate_key[1]),
		float(candidate.candidate_key[2]),
	)
	return score, result


#============================================
def _target_overlap(
		target_a: AttachTarget,
		target_b: AttachTarget,
		gap: float = 0.0) -> float:
	"""Return conservative box overlap for label occupancy scoring."""
	if target_a.box is None or target_b.box is None:
		return 0.0
	half_gap = gap * 0.5
	ax1, ay1, ax2, ay2 = target_a.box
	bx1, by1, bx2, by2 = target_b.box
	width = min(ax2 + half_gap, bx2 + half_gap) - max(ax1 - half_gap, bx1 - half_gap)
	height = min(ay2 + half_gap, by2 + half_gap) - max(ay1 - half_gap, by1 - half_gap)
	if width <= 0.0 or height <= 0.0:
		return 0.0
	area = width * height
	return area


#============================================
def _box_overlaps_polygon(
		box: tuple[float, float, float, float] | None,
		polygon: tuple[tuple[float, float], ...]) -> bool:
	"""Return whether a box and polygon overlap without renderer dependencies."""
	if box is None:
		return False
	x1, y1, x2, y2 = box
	corners = ((x1, y1), (x2, y1), (x2, y2), (x1, y2))
	if any(_point_in_polygon(corner, polygon) for corner in corners):
		return True
	if any(x1 <= point[0] <= x2 and y1 <= point[1] <= y2 for point in polygon):
		return True
	return any(
		_segment_intersects(edge_start, edge_end, corners[index], corners[(index + 1) % 4])
		for index, (edge_start, edge_end) in enumerate(_polygon_edges(polygon))
		for index in range(4)
	)


#============================================
def _segment_hits_polygon(
		start: tuple[float, float],
		end: tuple[float, float],
		polygon: tuple[tuple[float, float], ...]) -> bool:
	"""Return whether a connector enters a blocked polygon."""
	if _point_in_polygon(start, polygon) or _point_in_polygon(end, polygon):
		return True
	return any(_segment_intersects(start, end, edge_start, edge_end) for edge_start, edge_end in _polygon_edges(polygon))


#============================================
def _polygon_edges(polygon: tuple[tuple[float, float], ...]) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
	"""Return closed polygon edges."""
	if len(polygon) < 3:
		raise ValueError("Blocked polygon requires at least three points")
	edges = tuple((polygon[index], polygon[(index + 1) % len(polygon)]) for index in range(len(polygon)))
	return edges


#============================================
def _point_in_polygon(point: tuple[float, float], polygon: tuple[tuple[float, float], ...]) -> bool:
	"""Return whether a point lies in a polygon by ray casting."""
	x_value, y_value = point
	inside = False
	for start, end in _polygon_edges(polygon):
		if (start[1] > y_value) == (end[1] > y_value):
			continue
		intersect_x = start[0] + ((y_value - start[1]) * (end[0] - start[0]) / (end[1] - start[1]))
		if intersect_x >= x_value:
			inside = not inside
	return inside


#============================================
def _segment_intersects(
		first_start: tuple[float, float],
		first_end: tuple[float, float],
		second_start: tuple[float, float],
		second_end: tuple[float, float]) -> bool:
	"""Return whether two closed finite segments intersect."""
	def _cross(origin: tuple[float, float], first: tuple[float, float], second: tuple[float, float]) -> float:
		return ((first[0] - origin[0]) * (second[1] - origin[1])) - ((first[1] - origin[1]) * (second[0] - origin[0]))

	first_a = _cross(first_start, first_end, second_start)
	first_b = _cross(first_start, first_end, second_end)
	second_a = _cross(second_start, second_end, first_start)
	second_b = _cross(second_start, second_end, first_end)
	return ((first_a >= 0.0 >= first_b) or (first_a <= 0.0 <= first_b)) and ((second_a >= 0.0 >= second_b) or (second_a <= 0.0 <= second_b))
