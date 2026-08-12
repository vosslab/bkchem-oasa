#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Hydroxyl layout optimizer for Haworth rendering."""

# Standard Library
import math

from oasa.haworth.renderer_config import (
	RING_SLOT_SEQUENCE,
	VALID_DIRECTIONS,
	VALID_ANCHORS,
	REQUIRED_SIMPLE_JOB_KEYS,
	HYDROXYL_LAYOUT_CANDIDATE_FACTORS,
	HYDROXYL_LAYOUT_INTERNAL_CANDIDATE_FACTORS,
	HYDROXYL_LAYOUT_MIN_GAP_FACTOR,
	HYDROXYL_RING_COLLISION_PENALTY,
	INTERNAL_PAIR_OVERLAP_AREA_THRESHOLD,
	INTERNAL_PAIR_LABEL_SCALE,
	INTERNAL_PAIR_LANE_Y_TOLERANCE_FACTOR,
	INTERNAL_PAIR_MIN_H_GAP_FACTOR,
)
from oasa.haworth import renderer_geometry as _geom
from oasa.haworth import renderer_text as _text
from oasa.render_lib.data_types import AttachTarget
from oasa.render_lib.label_layout import LabelPlacementCandidate
from oasa.render_lib.label_layout import choose_label_placement
from oasa.render_lib.label_geometry import connector_constraints_from_direction
from oasa.render_lib.label_geometry import align_text_origin_to_attach_centerline
from oasa.render_lib.label_geometry import label_attach_contract_from_text_origin
from oasa.render_lib.label_geometry import label_target_from_text_origin


#============================================
def _ring_slot_sequence(ring_type: str) -> tuple[str, ...]:
	"""Return canonical carbon-slot order for one ring type."""
	try:
		return RING_SLOT_SEQUENCE[ring_type]
	except KeyError as error:
		raise ValueError("Unsupported ring_type '%s'" % ring_type) from error


#============================================
def validate_simple_job(job: dict) -> None:
	"""Validate one simple-label layout job for deterministic processing."""
	missing = [key for key in REQUIRED_SIMPLE_JOB_KEYS if key not in job]
	if missing:
		raise ValueError("Simple label job missing required keys: %s" % ", ".join(missing))
	if job["direction"] not in VALID_DIRECTIONS:
		raise ValueError("Simple label job has invalid direction '%s'" % job["direction"])
	if job["anchor"] not in VALID_ANCHORS:
		raise ValueError("Simple label job has invalid anchor '%s'" % job["anchor"])
	if "ring_type" in job or "slot" in job:
		if "ring_type" not in job or "slot" not in job:
			raise ValueError("Simple label job must include both ring_type and slot together")
		ring_type = job["ring_type"]
		slot = job["slot"]
		slot_sequence = _ring_slot_sequence(ring_type)
		if slot not in slot_sequence:
			raise ValueError(
				"Simple label job has slot '%s' not valid for ring_type '%s'" % (slot, ring_type)
			)


#============================================
def job_is_hydroxyl(job: dict) -> bool:
	"""Return True when one simple-label job renders as OH/HO."""
	text = _text.format_label_text(job["label"], anchor=job["anchor"])
	return _text.is_hydroxyl_render_text(text)


#============================================
def job_is_internal_hydroxyl(job: dict) -> bool:
	"""Return True for hydroxyl labels drawn into the ring interior."""
	if job.get("direction") != "up":
		return False
	ring_type = job.get("ring_type")
	slot = job.get("slot")
	if ring_type == "pyranose":
		return slot in ("BR", "BL")
	if ring_type == "furanose":
		return slot in ("BR", "BL")
	return False


#============================================
def job_can_flip_internal_anchor(job: dict) -> bool:
	"""Return True when internal hydroxyl candidates may flip HO/OH anchor side."""
	if not job_is_internal_hydroxyl(job):
		return False
	return job.get("ring_type") == "furanose"


#============================================
def best_equal_internal_hydroxyl_length(
		internal_jobs: list[dict],
		occupied: list[tuple[float, float, float, float]],
		blocked_polygons: list[tuple[tuple[float, float], ...]],
		min_gap: float) -> float:
	"""Select one shared internal hydroxyl length with minimal overlap penalty."""
	base_lengths = [job["length"] for job in internal_jobs]
	candidate_lengths = set(base_lengths)
	base_max = max(base_lengths)
	for factor in HYDROXYL_LAYOUT_INTERNAL_CANDIDATE_FACTORS:
		candidate_lengths.add(base_max * factor)
	ordered_candidates = sorted(candidate_lengths)
	best_length = ordered_candidates[0]
	best_penalty = float("inf")
	for length in ordered_candidates:
		candidate_occupied = list(occupied)
		total_penalty = 0.0
		for job in internal_jobs:
			candidate = dict(job)
			candidate["length"] = length
			total_penalty += hydroxyl_job_penalty(
				candidate,
				candidate_occupied,
				blocked_polygons,
				min_gap,
			)
			candidate_occupied.append(job_text_target(candidate, candidate["length"]).box)
		if total_penalty < best_penalty:
			best_penalty = total_penalty
			best_length = length
		if total_penalty <= 0.0:
			break
	return best_length


#============================================
def hydroxyl_candidate_jobs(job: dict, allow_anchor_flip: bool = False) -> list[dict]:
	"""Build a tiny candidate set for hydroxyl placement search."""
	candidates = []
	anchor_candidates = [job["anchor"]]
	if allow_anchor_flip:
		if job["anchor"] == "start":
			anchor_candidates.append("end")
		elif job["anchor"] == "end":
			anchor_candidates.append("start")
	if allow_anchor_flip:
		factors = HYDROXYL_LAYOUT_INTERNAL_CANDIDATE_FACTORS
	else:
		factors = HYDROXYL_LAYOUT_CANDIDATE_FACTORS
	for anchor in anchor_candidates:
		for factor in factors:
			candidate = dict(job)
			candidate["anchor"] = anchor
			candidate["length"] = job["length"] * factor
			candidates.append(candidate)
	return candidates


#============================================
def job_end_point(job: dict, length: float | None = None) -> tuple[float, float]:
	"""Return connector endpoint for one job."""
	if length is None:
		length = job["length"]
	return (
		job["vertex"][0] + (job["dx"] * length),
		job["vertex"][1] + (job["dy"] * length),
	)


#============================================
def internal_pair_overlap_area(left_job: dict, right_job: dict) -> float:
	"""Compute overlap area between two internal hydroxyl label boxes."""
	left_box = job_text_target(left_job, left_job["length"]).box
	right_box = job_text_target(right_job, right_job["length"]).box
	return _geom.intersection_area(left_box, right_box, gap=0.0)


#============================================
def internal_pair_horizontal_gap(left_job: dict, right_job: dict) -> float:
	"""Return horizontal box gap between left/right internal pair labels."""
	left_box = job_text_target(left_job, left_job["length"]).box
	right_box = job_text_target(right_job, right_job["length"]).box
	return right_box[0] - left_box[2]


#============================================
def resolve_internal_hydroxyl_pair_overlap(jobs: list[dict]) -> None:
	"""Apply one deterministic local fix for overlapping internal OH/HO pairs."""
	internal_indices = [
		index
		for index, job in enumerate(jobs)
		if job_is_internal_hydroxyl(job) and job_is_hydroxyl(job)
	]
	if len(internal_indices) < 2:
		return
	lane_tolerance = jobs[internal_indices[0]]["font_size"] * INTERNAL_PAIR_LANE_Y_TOLERANCE_FACTOR
	sorted_indices = sorted(
		internal_indices,
		key=lambda index: job_end_point(jobs[index])[1],
	)
	groups = []
	current_group = []
	current_lane = None
	for index in sorted_indices:
		lane_y = job_end_point(jobs[index])[1]
		if not current_group:
			current_group = [index]
			current_lane = lane_y
			continue
		if abs(lane_y - current_lane) <= lane_tolerance:
			current_group.append(index)
			continue
		groups.append(current_group)
		current_group = [index]
		current_lane = lane_y
	if current_group:
		groups.append(current_group)
	for group in groups:
		if len(group) != 2:
			continue
		left_index, right_index = sorted(
			group,
			key=lambda index: job_end_point(jobs[index])[0],
		)
		left_job = dict(jobs[left_index])
		right_job = dict(jobs[right_index])
		ring_type = left_job.get("ring_type")
		if ring_type == "pyranose" and right_job.get("ring_type") == "pyranose":
			# Keep interior pyranose hydroxyls center-facing: OH ... HO.
			left_job["anchor"] = "start"
			right_job["anchor"] = "end"
		elif ring_type == "furanose" and right_job.get("ring_type") == "furanose":
			# Keep classic interior reading order (OH ... HO) and use
			# small local label scaling instead of widening the pair.
			left_job["anchor"] = "start"
			right_job["anchor"] = "end"
			left_job["text_scale"] = INTERNAL_PAIR_LABEL_SCALE
			right_job["text_scale"] = INTERNAL_PAIR_LABEL_SCALE
		else:
			left_job["anchor"] = "end"
			right_job["anchor"] = "start"
		if ring_type != "furanose" or right_job.get("ring_type") != "furanose":
			overlap = internal_pair_overlap_area(left_job, right_job)
			min_h_gap = left_job["font_size"] * INTERNAL_PAIR_MIN_H_GAP_FACTOR
			h_gap = internal_pair_horizontal_gap(left_job, right_job)
			if overlap > INTERNAL_PAIR_OVERLAP_AREA_THRESHOLD or h_gap < min_h_gap:
				left_job["text_scale"] = INTERNAL_PAIR_LABEL_SCALE
				right_job["text_scale"] = INTERNAL_PAIR_LABEL_SCALE
		jobs[left_index] = left_job
		jobs[right_index] = right_job


#============================================
def job_is_internal_group(job: dict) -> bool:
	"""Return True for non-hydrogen labels whose connector points inward."""
	if str(job.get("label", "")) == "H":
		return False
	center = job.get("ring_center")
	if center is None:
		return job_is_internal_hydroxyl(job)
	vertex = job["vertex"]
	end_point = job_end_point(job, job["length"])
	start_distance = math.hypot(vertex[0] - center[0], vertex[1] - center[1])
	end_distance = math.hypot(end_point[0] - center[0], end_point[1] - center[1])
	return end_distance < (start_distance - 1e-6)


#============================================
def resolve_internal_group_scaling(jobs: list[dict]) -> None:
	"""Scale all internal labels to 90% when more than one internal group exists."""
	internal_indices = [
		index
		for index, job in enumerate(jobs)
		if job_is_internal_group(job)
	]
	if len(internal_indices) < 2:
		return
	for index in internal_indices:
		job = dict(jobs[index])
		scale = float(job.get("text_scale", 1.0))
		job["text_scale"] = min(scale, INTERNAL_PAIR_LABEL_SCALE)
		jobs[index] = job


#============================================
def job_text_target(job: dict, length: float) -> AttachTarget:
	"""Approximate text target for one simple-label placement job."""
	end_x, end_y = job_end_point(job, length)
	text = _text.format_label_text(job["label"], anchor=job["anchor"])
	draw_font_size = job["font_size"] * float(job.get("text_scale", 1.0))
	text_x = end_x + _text.anchor_x_offset(text, job["anchor"], draw_font_size)
	text_y = end_y + _text.baseline_shift(job["direction"], draw_font_size, text)
	return label_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=job["anchor"],
		font_size=draw_font_size,
		font_name=job.get("font_name"),
	)


#============================================
def text_target(
		text_x: float,
		text_y: float,
		text: str,
		anchor: str,
		font_size: float) -> AttachTarget:
	"""Return one shared label target from text geometry fields."""
	return label_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
	)


#============================================
def overlap_penalty(
		box: tuple[float, float, float, float],
		occupied_boxes: list[tuple[float, float, float, float]],
		gap: float) -> float:
	"""Return summed overlap area against occupied boxes with required minimum gap."""
	total = 0.0
	for other in occupied_boxes:
		area = _geom.intersection_area(box, other, gap)
		if area > 0.0:
			total += area
	return total


#============================================
def hydroxyl_job_penalty(
		job: dict,
		occupied: list[tuple[float, float, float, float]],
		blocked_polygons: list[tuple[tuple[float, float], ...]],
		min_gap: float) -> float:
	"""Return overlap penalty for one hydroxyl job against occupied boxes."""
	box = job_text_target(job, job["length"]).box
	penalty = overlap_penalty(box, occupied, min_gap)
	if job_is_internal_hydroxyl(job):
		for polygon in blocked_polygons:
			if _geom.box_overlaps_polygon(box, polygon):
				penalty += HYDROXYL_RING_COLLISION_PENALTY
	return penalty


#============================================
def resolve_hydroxyl_layout_jobs(
		jobs: list[dict],
		blocked_targets: tuple[AttachTarget, ...] = (),
		blocked_polygons: list[tuple[tuple[float, float], ...]] | None = None) -> list[dict]:
	"""Resolve finite label candidates through the shared geometry chooser.

	The historic name remains as a compatibility entry point.  It now accepts
	any simple Haworth label without inspecting ring type, slot, or label token
	for collision policy.  Haworth has already selected the semantic label and
	direction; this adapter offers universally useful anchor, scale, and lane
	candidates to the frontend-neutral chooser.
	"""
	if not jobs:
		return []
	for job in jobs:
		validate_simple_job(job)
	occupied = []
	resolved = []
	polygons = tuple(blocked_polygons or ())
	for job_index, job in enumerate(jobs):
		candidates, candidate_jobs = _placement_candidates_for_job(job, job_index)
		result = choose_label_placement(
			candidates=tuple(candidates),
			occupied_targets=tuple(occupied),
			blocked_targets=blocked_targets,
			blocked_polygons=polygons,
			connector_width=job["connector_width"],
			minimum_gap=job["font_size"] * HYDROXYL_LAYOUT_MIN_GAP_FACTOR,
		)
		chosen_job = candidate_jobs[result.candidate_key]
		resolved.append(chosen_job)
		occupied.append(job_text_target(chosen_job, chosen_job["length"]))
	return resolved


#============================================
def _placement_candidates_for_job(
		job: dict,
		job_index: int) -> tuple[list[LabelPlacementCandidate], dict[tuple[int, int, int], dict]]:
	"""Build geometry candidates without a Haworth semantic special case."""
	anchors = [job["anchor"]]
	if job["anchor"] == "start":
		anchors.append("end")
	elif job["anchor"] == "end":
		anchors.append("start")
	factors = HYDROXYL_LAYOUT_CANDIDATE_FACTORS
	candidates = []
	candidate_jobs = {}
	label_candidates = tuple(job.get("label_candidates", (job["label"],)))
	text_scales = tuple(job.get("text_scales", (job.get("text_scale", 1.0),)))
	if not label_candidates or not all(isinstance(label, str) and label for label in label_candidates):
		raise ValueError("Simple label candidates must be a nonempty tuple of text values")
	if not text_scales or not all(0.90 <= float(scale) <= 1.0 for scale in text_scales):
		raise ValueError("Simple label scales must be within the readable 0.90 to 1.00 range")
	for anchor_index, anchor in enumerate(anchors):
		for factor_index, factor in enumerate(factors):
			for label_index, candidate_label in enumerate(label_candidates):
				for scale_index, text_scale in enumerate(text_scales):
					candidate_job = dict(job)
					candidate_job["anchor"] = anchor
					candidate_job["length"] = job["length"] * factor
					candidate_job["label"] = candidate_label
					candidate_job["text_scale"] = float(text_scale)
					text = _text.format_label_text(candidate_label, anchor=anchor)
					end_x, end_y = job_end_point(candidate_job, candidate_job["length"])
					font_size = candidate_job["font_size"] * candidate_job["text_scale"]
					text_x = end_x + _text.anchor_x_offset(text, anchor, font_size)
					text_y = end_y + _text.baseline_shift(candidate_job["direction"], font_size, text)
					is_chain_like = _text.is_chain_like_label(str(candidate_label))
					if abs(candidate_job["dx"]) <= 1e-9 and abs(candidate_job["dy"]) > 1e-9:
						text_x, text_y = align_text_origin_to_attach_centerline(
							text_x=text_x,
							text_y=text_y,
							text=text,
							anchor=anchor,
							font_size=font_size,
							target_center_x=candidate_job["vertex"][0],
							attach_element="C" if is_chain_like else None,
							attach_site="core_center" if is_chain_like else None,
							chain_attach_site="core_center",
							font_name=candidate_job["font_name"],
						)
					contract = label_attach_contract_from_text_origin(
						text_x=text_x,
						text_y=text_y,
						text=text,
						anchor=anchor,
						font_size=font_size,
						font_name=candidate_job["font_name"],
					)
					presentation_index = ((factor_index * len(label_candidates) + label_index)
						* len(text_scales)) + scale_index
					key = (job_index, anchor_index, presentation_index)
					candidates.append(
						LabelPlacementCandidate(
							text=text,
							anchor=anchor,
							font_scale=candidate_job["text_scale"],
							nominal_origin=(text_x, text_y),
							connector_start=candidate_job["vertex"],
							attach_contract=contract,
							constraints=connector_constraints_from_direction(
								direction=(candidate_job["dx"], candidate_job["dy"]),
								font_size=font_size,
							),
							candidate_key=key,
							font_size=candidate_job["font_size"],
							font_name=candidate_job["font_name"],
						)
					)
					candidate_jobs[key] = candidate_job
	return candidates, candidate_jobs
