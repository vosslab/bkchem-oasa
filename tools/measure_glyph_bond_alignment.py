#!/usr/bin/env python3
"""Measure bond-to-glyph alignment from existing SVG files without re-rendering."""

# Standard Library
import argparse
import datetime
import json
import math
import os
import pathlib
import subprocess
import sys

# Ensure the tools/ directory is on sys.path so that the measurelib
# subpackage can be imported when this file is loaded via
# importlib.util.spec_from_file_location().
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
	sys.path.insert(0, _TOOLS_DIR)

# Re-export every public name from measurelib submodules so that test code
# using importlib.util.spec_from_file_location("measure_glyph_bond_alignment", ...)
# continues to find all symbols at module level.
# The __all__ list tells pyflakes these imports are intentional re-exports.
__all__ = [
	"analyze_svg_file", "parse_args", "get_repo_root", "main",
	# constants
	"ALIGNMENT_DISTANCE_ZERO_EPSILON", "ALIGNMENT_INFINITE_LINE_FONT_TOLERANCE_FACTOR",
	"BOND_GLYPH_GAP_TOLERANCE", "BOND_GLYPH_INTERIOR_EPSILON",
	"CANONICAL_LATTICE_ANGLES",
	"DOUBLE_BOND_LENGTH_RATIO_MIN", "DOUBLE_BOND_PARALLEL_TOLERANCE_DEGREES",
	"DOUBLE_BOND_PERP_DISTANCE_MAX", "DOUBLE_BOND_PERP_DISTANCE_MIN",
	"DEFAULT_DIAGNOSTIC_SVG_DIR",
	"DEFAULT_CURRENT_RUNTIME_DIR",
	"DEFAULT_INPUT_GLOB", "DEFAULT_JSON_REPORT", "DEFAULT_TEXT_REPORT",
	"GLYPH_BOX_OVERLAP_EPSILON", "GLYPH_CURVED_CHAR_SET", "GLYPH_STEM_CHAR_SET",
	"HASHED_CARRIER_MAX_WIDTH", "HASHED_CARRIER_MIN_LENGTH",
	"HASHED_CARRIER_MIN_STROKES", "HASHED_PERPENDICULAR_TOLERANCE_DEGREES",
	"HASHED_SHARED_ENDPOINT_PARALLEL_TOLERANCE_DEGREES",
	"HASHED_STROKE_MAX_DISTANCE_TO_CARRIER",
	"HATCH_STROKE_MAX_LENGTH", "HATCH_STROKE_MAX_WIDTH",
	"HATCH_STROKE_MIN_LENGTH", "HATCH_STROKE_MIN_WIDTH",
	"HAWORTH_RING_MIN_PRIMITIVES", "HAWORTH_RING_SEARCH_RADIUS",
	"LATTICE_ANGLE_TOLERANCE_DEGREES", "LENGTH_ROUND_DECIMALS",
	"MAX_ENDPOINT_TO_LABEL_DISTANCE_FACTOR", "MIN_ALIGNMENT_DISTANCE_TOLERANCE",
	"MIN_BOND_LENGTH_FOR_ANGLE_CHECK", "MIN_CONNECTOR_LINE_WIDTH",
	"MULTI_CONNECTOR_GAP_RATIO_MAX", "SVG_FLOAT_PATTERN",
	"MATPLOTLIB_TEXTPATH_AVAILABLE",
	# new public names
	"alignment_score", "compact_float", "compact_sorted_values",
	"compact_value_counts", "display_float", "display_point",
	"group_length_append", "increment_counter", "length_stats",
	"line_endpoints", "line_length", "line_midpoint", "normalize_box",
	"point_distance_sq", "point_in_target_closed", "point_to_box_distance",
	"point_to_box_signed_distance", "point_to_ellipse_signed_distance",
	"point_to_glyph_primitive_signed_distance",
	"point_to_glyph_primitives_distance",
	"point_to_glyph_primitives_signed_distance",
	"point_to_target_distance", "point_to_target_signed_distance",
	"rounded_sorted_values", "rounded_value_counts", "safe_token",
	"angle_difference_degrees", "boxes_overlap_interior", "convex_hull",
	"distance_sq_segment_to_segment", "line_angle_degrees",
	"line_collinear_overlap_length", "line_intersection_point",
	"line_intersects_box_interior", "line_overlap_midpoint",
	"lines_nearly_parallel", "lines_share_endpoint",
	"nearest_canonical_lattice_angle", "nearest_lattice_angle_error",
	"on_segment", "orientation", "parallel_error_degrees",
	"point_to_infinite_line_distance", "point_to_segment_distance_sq",
	"points_close", "segment_distance_to_box_sq", "segments_intersect",
	"collect_svg_labels", "collect_svg_lines", "collect_svg_ring_primitives",
	"collect_svg_wedge_bonds", "local_tag_name", "node_is_overlay_group",
	"parse_float", "path_points", "points_bbox", "polygon_points",
	"resolve_svg_paths", "svg_number_tokens", "svg_tag_with_namespace",
	"visible_text",
	"all_endpoints_near_glyph_primitives", "all_endpoints_near_text_path",
	"canonicalize_label_text", "font_family_candidates",
	"glyph_char_advance", "glyph_char_vertical_bounds",
	"glyph_primitive_from_char", "glyph_primitives_bounds",
	"glyph_text_width", "is_measurement_label", "label_geometry_text",
	"label_svg_estimated_box", "label_svg_estimated_primitives",
	"label_text_path", "line_closest_endpoint_to_box",
	"line_closest_endpoint_to_target", "nearest_endpoint_to_box",
	"nearest_endpoint_to_glyph_primitives", "nearest_endpoint_to_text_path",
	"path_line_segments", "point_to_label_signed_distance",
	"point_to_text_path_signed_distance", "primitive_center",
	"optical_center_via_isolation_render",
	"canonical_cycle_key", "clustered_endpoint_graph", "cycle_node_pairs",
	"detect_haworth_base_ring", "detect_haworth_ring_from_line_cycles",
	"detect_haworth_ring_from_primitives", "empty_haworth_ring_detection",
	"find_candidate_cycles",
	"default_overlap_origin", "detect_double_bond_pairs", "detect_hashed_carrier_map",
	"is_hashed_carrier_candidate", "is_hatch_stroke_candidate",
	"overlap_origin", "quadrant_label", "ring_region_label",
	"count_bond_bond_overlaps", "count_bond_glyph_overlaps",
	"count_glyph_glyph_overlaps", "count_hatched_thin_conflicts",
	"count_lattice_angle_violations",
	"clip_infinite_line_to_bounds", "diagnostic_bounds",
	"diagnostic_color", "metric_alignment_center", "metric_endpoint",
	"select_alignment_primitive", "viewbox_bounds", "write_diagnostic_svg",
	"JSON_SUMMARY_EXCLUDE_KEYS", "format_stats_line",
	"json_summary_compact", "summary_stats", "text_report",
	"top_misses", "violation_summary",
	# backward-compatible underscore aliases
	"_alignment_score", "_compact_float", "_compact_sorted_values",
	"_compact_value_counts", "_display_float", "_display_point",
	"_group_length_append", "_increment_counter", "_length_stats",
	"_line_endpoints", "_line_length", "_line_midpoint", "_normalize_box",
	"_point_distance_sq", "_point_in_target_closed", "_point_to_box_distance",
	"_point_to_box_signed_distance", "_point_to_ellipse_signed_distance",
	"_point_to_glyph_primitive_signed_distance",
	"_point_to_glyph_primitives_distance",
	"_point_to_glyph_primitives_signed_distance",
	"_point_to_target_distance", "_point_to_target_signed_distance",
	"_rounded_sorted_values", "_rounded_value_counts", "_safe_token",
	"_angle_difference_degrees", "_boxes_overlap_interior", "_convex_hull",
	"_distance_sq_segment_to_segment", "_line_angle_degrees",
	"_line_collinear_overlap_length", "_line_intersection_point",
	"_line_intersects_box_interior", "_line_overlap_midpoint",
	"_lines_nearly_parallel", "_lines_share_endpoint",
	"_nearest_canonical_lattice_angle", "_nearest_lattice_angle_error",
	"_on_segment", "_orientation", "_parallel_error_degrees",
	"_point_to_infinite_line_distance", "_point_to_segment_distance_sq",
	"_points_close", "_segment_distance_to_box_sq", "_segments_intersect",
	"_collect_svg_labels", "_collect_svg_lines", "_collect_svg_ring_primitives",
	"_collect_svg_wedge_bonds", "_local_tag_name", "_node_is_overlay_group",
	"_parse_float", "_path_points", "_points_bbox", "_polygon_points",
	"_resolve_svg_paths", "_svg_number_tokens", "_svg_tag_with_namespace",
	"_visible_text",
	"_canonicalize_label_text", "_font_family_candidates",
	"_glyph_char_advance", "_glyph_char_vertical_bounds",
	"_glyph_primitive_from_char", "_glyph_primitives_bounds",
	"_glyph_text_width", "_is_measurement_label", "_label_geometry_text",
	"_label_svg_estimated_box", "_label_svg_estimated_primitives",
	"_label_text_path", "_line_closest_endpoint_to_box",
	"_line_closest_endpoint_to_target", "_nearest_endpoint_to_box",
	"_all_endpoints_near_glyph_primitives", "_all_endpoints_near_text_path",
	"_nearest_endpoint_to_glyph_primitives", "_nearest_endpoint_to_text_path",
	"_path_line_segments", "_point_to_label_signed_distance",
	"_point_to_text_path_signed_distance", "_primitive_center",
	"_optical_center_via_isolation_render",
	"_canonical_cycle_key", "_clustered_endpoint_graph", "_cycle_node_pairs",
	"_detect_haworth_base_ring", "_detect_haworth_ring_from_line_cycles",
	"_detect_haworth_ring_from_primitives", "_empty_haworth_ring_detection",
	"_find_candidate_cycles",
	"_default_overlap_origin", "_detect_double_bond_pairs", "_detect_hashed_carrier_map",
	"_is_hashed_carrier_candidate", "_is_hatch_stroke_candidate",
	"_overlap_origin", "_quadrant_label", "_ring_region_label",
	"_count_bond_bond_overlaps", "_count_bond_glyph_overlaps",
	"_count_glyph_glyph_overlaps", "_count_hatched_thin_conflicts",
	"_count_lattice_angle_violations",
	"_clip_infinite_line_to_bounds", "_diagnostic_bounds",
	"_diagnostic_color", "_metric_alignment_center", "_metric_endpoint",
	"_select_alignment_primitive", "_viewbox_bounds", "_write_diagnostic_svg",
	"_JSON_SUMMARY_EXCLUDE_KEYS", "_format_stats_line",
	"_json_summary_compact", "_summary_stats", "_text_report",
	"_top_misses", "_violation_summary",
]

from measurelib.constants import (
	ALIGNMENT_DISTANCE_ZERO_EPSILON,
	ALIGNMENT_INFINITE_LINE_FONT_TOLERANCE_FACTOR,
	BOND_GLYPH_GAP_TOLERANCE,
	BOND_GLYPH_INTERIOR_EPSILON,
	CANONICAL_LATTICE_ANGLES,
	DOUBLE_BOND_LENGTH_RATIO_MIN,
	DOUBLE_BOND_PARALLEL_TOLERANCE_DEGREES,
	DOUBLE_BOND_PERP_DISTANCE_MAX,
	DOUBLE_BOND_PERP_DISTANCE_MIN,
	DEFAULT_DIAGNOSTIC_SVG_DIR,
	DEFAULT_CURRENT_RUNTIME_DIR,
	DEFAULT_INPUT_GLOB,
	DEFAULT_JSON_REPORT,
	DEFAULT_TEXT_REPORT,
	GLYPH_BOX_OVERLAP_EPSILON,
	GLYPH_CURVED_CHAR_SET,
	GLYPH_STEM_CHAR_SET,
	HASHED_CARRIER_MAX_WIDTH,
	HASHED_CARRIER_MIN_LENGTH,
	HASHED_CARRIER_MIN_STROKES,
	HASHED_PERPENDICULAR_TOLERANCE_DEGREES,
	HASHED_SHARED_ENDPOINT_PARALLEL_TOLERANCE_DEGREES,
	HASHED_STROKE_MAX_DISTANCE_TO_CARRIER,
	HATCH_STROKE_MAX_LENGTH,
	HATCH_STROKE_MAX_WIDTH,
	HATCH_STROKE_MIN_LENGTH,
	HATCH_STROKE_MIN_WIDTH,
	HAWORTH_RING_MIN_PRIMITIVES,
	HAWORTH_RING_SEARCH_RADIUS,
	LATTICE_ANGLE_TOLERANCE_DEGREES,
	LENGTH_ROUND_DECIMALS,
	MAX_ENDPOINT_TO_LABEL_DISTANCE_FACTOR,
	MIN_ALIGNMENT_DISTANCE_TOLERANCE,
	MIN_BOND_LENGTH_FOR_ANGLE_CHECK,
	MIN_CONNECTOR_LINE_WIDTH,
	MULTI_CONNECTOR_GAP_RATIO_MAX,
	SVG_FLOAT_PATTERN,
)
from measurelib.util import (
	alignment_score,
	compact_float,
	compact_sorted_values,
	compact_value_counts,
	display_float,
	display_point,
	group_length_append,
	increment_counter,
	length_stats,
	line_endpoints,
	line_length,
	line_midpoint,
	normalize_box,
	point_distance_sq,
	point_in_target_closed,
	point_to_box_distance,
	point_to_box_signed_distance,
	point_to_ellipse_signed_distance,
	point_to_glyph_primitive_signed_distance,
	point_to_glyph_primitives_distance,
	point_to_glyph_primitives_signed_distance,
	point_to_target_distance,
	point_to_target_signed_distance,
	rounded_sorted_values,
	rounded_value_counts,
	safe_token,
)
from measurelib.geometry import (
	angle_difference_degrees,
	boxes_overlap_interior,
	convex_hull,
	distance_sq_segment_to_segment,
	line_angle_degrees,
	line_collinear_overlap_length,
	line_intersection_point,
	line_intersects_box_interior,
	line_overlap_midpoint,
	lines_nearly_parallel,
	lines_share_endpoint,
	nearest_canonical_lattice_angle,
	nearest_lattice_angle_error,
	on_segment,
	orientation,
	parallel_error_degrees,
	point_to_infinite_line_distance,
	point_to_segment_distance_sq,
	points_close,
	segment_distance_to_box_sq,
	segments_intersect,
)
from measurelib.svg_parse import (
	collect_svg_labels,
	collect_svg_lines,
	collect_svg_ring_primitives,
	collect_svg_wedge_bonds,
	local_tag_name,
	node_is_overlay_group,
	parse_float,
	path_points,
	points_bbox,
	polygon_points,
	resolve_svg_paths,
	svg_number_tokens,
	svg_tag_with_namespace,
	visible_text,
)
from measurelib.glyph_model import (
	MATPLOTLIB_TEXTPATH_AVAILABLE,
	all_endpoints_near_glyph_primitives,
	all_endpoints_near_text_path,
	canonicalize_label_text,
	font_family_candidates,
	glyph_char_advance,
	glyph_char_vertical_bounds,
	glyph_primitive_from_char,
	glyph_primitives_bounds,
	glyph_text_width,
	is_measurement_label,
	label_geometry_text,
	label_svg_estimated_box,
	label_svg_estimated_primitives,
	label_text_path,
	line_closest_endpoint_to_box,
	line_closest_endpoint_to_target,
	nearest_endpoint_to_box,
	nearest_endpoint_to_glyph_primitives,
	nearest_endpoint_to_text_path,
	path_line_segments,
	point_to_label_signed_distance,
	point_to_text_path_signed_distance,
	primitive_center,
)
from measurelib.haworth_ring import (
	canonical_cycle_key,
	clustered_endpoint_graph,
	cycle_node_pairs,
	detect_haworth_base_ring,
	detect_haworth_ring_from_line_cycles,
	detect_haworth_ring_from_primitives,
	empty_haworth_ring_detection,
	find_candidate_cycles,
)
from measurelib.hatch_detect import (
	default_overlap_origin,
	detect_double_bond_pairs,
	detect_hashed_carrier_map,
	is_hashed_carrier_candidate,
	is_hatch_stroke_candidate,
	overlap_origin,
	quadrant_label,
	ring_region_label,
)
from measurelib.violations import (
	count_bond_bond_overlaps,
	count_bond_glyph_overlaps,
	count_glyph_glyph_overlaps,
	count_hatched_thin_conflicts,
	count_lattice_angle_violations,
)
from measurelib.diagnostic_svg import (
	clip_infinite_line_to_bounds,
	diagnostic_bounds,
	diagnostic_color,
	metric_alignment_center,
	metric_endpoint,
	select_alignment_primitive,
	viewbox_bounds,
	write_diagnostic_svg,
)
from measurelib.analysis import analyze_svg_file
from measurelib.reporting import (
	JSON_SUMMARY_EXCLUDE_KEYS,
	format_stats_line,
	json_summary_compact,
	summary_stats,
	text_report,
	top_misses,
	violation_summary,
)

# Backward-compatible underscore aliases for test code that
# accesses these via tool_module._function_name.
_alignment_score = alignment_score
_compact_float = compact_float
_compact_sorted_values = compact_sorted_values
_compact_value_counts = compact_value_counts
_display_float = display_float
_display_point = display_point
_group_length_append = group_length_append
_increment_counter = increment_counter
_length_stats = length_stats
_line_endpoints = line_endpoints
_line_length = line_length
_line_midpoint = line_midpoint
_normalize_box = normalize_box
_point_distance_sq = point_distance_sq
_point_in_target_closed = point_in_target_closed
_point_to_box_distance = point_to_box_distance
_point_to_box_signed_distance = point_to_box_signed_distance
_point_to_ellipse_signed_distance = point_to_ellipse_signed_distance
_point_to_glyph_primitive_signed_distance = point_to_glyph_primitive_signed_distance
_point_to_glyph_primitives_distance = point_to_glyph_primitives_distance
_point_to_glyph_primitives_signed_distance = point_to_glyph_primitives_signed_distance
_point_to_target_distance = point_to_target_distance
_point_to_target_signed_distance = point_to_target_signed_distance
_rounded_sorted_values = rounded_sorted_values
_rounded_value_counts = rounded_value_counts
_safe_token = safe_token
_angle_difference_degrees = angle_difference_degrees
_boxes_overlap_interior = boxes_overlap_interior
_convex_hull = convex_hull
_distance_sq_segment_to_segment = distance_sq_segment_to_segment
_line_angle_degrees = line_angle_degrees
_line_collinear_overlap_length = line_collinear_overlap_length
_line_intersection_point = line_intersection_point
_line_intersects_box_interior = line_intersects_box_interior
_line_overlap_midpoint = line_overlap_midpoint
_lines_nearly_parallel = lines_nearly_parallel
_lines_share_endpoint = lines_share_endpoint
_nearest_canonical_lattice_angle = nearest_canonical_lattice_angle
_nearest_lattice_angle_error = nearest_lattice_angle_error
_on_segment = on_segment
_orientation = orientation
_parallel_error_degrees = parallel_error_degrees
_point_to_infinite_line_distance = point_to_infinite_line_distance
_point_to_segment_distance_sq = point_to_segment_distance_sq
_points_close = points_close
_segment_distance_to_box_sq = segment_distance_to_box_sq
_segments_intersect = segments_intersect
_collect_svg_labels = collect_svg_labels
_collect_svg_lines = collect_svg_lines
_collect_svg_ring_primitives = collect_svg_ring_primitives
_collect_svg_wedge_bonds = collect_svg_wedge_bonds
_local_tag_name = local_tag_name
_node_is_overlay_group = node_is_overlay_group
_parse_float = parse_float
_path_points = path_points
_points_bbox = points_bbox
_polygon_points = polygon_points
_resolve_svg_paths = resolve_svg_paths
_svg_number_tokens = svg_number_tokens
_svg_tag_with_namespace = svg_tag_with_namespace
_visible_text = visible_text
_canonicalize_label_text = canonicalize_label_text
_font_family_candidates = font_family_candidates
_glyph_char_advance = glyph_char_advance
_glyph_char_vertical_bounds = glyph_char_vertical_bounds
_glyph_primitive_from_char = glyph_primitive_from_char
_glyph_primitives_bounds = glyph_primitives_bounds
_glyph_text_width = glyph_text_width
_is_measurement_label = is_measurement_label
_label_geometry_text = label_geometry_text
_label_svg_estimated_box = label_svg_estimated_box
_label_svg_estimated_primitives = label_svg_estimated_primitives
_label_text_path = label_text_path
_line_closest_endpoint_to_box = line_closest_endpoint_to_box
_line_closest_endpoint_to_target = line_closest_endpoint_to_target
_nearest_endpoint_to_box = nearest_endpoint_to_box
_all_endpoints_near_glyph_primitives = all_endpoints_near_glyph_primitives
_all_endpoints_near_text_path = all_endpoints_near_text_path
_nearest_endpoint_to_glyph_primitives = nearest_endpoint_to_glyph_primitives
_nearest_endpoint_to_text_path = nearest_endpoint_to_text_path
_path_line_segments = path_line_segments
_point_to_label_signed_distance = point_to_label_signed_distance
_point_to_text_path_signed_distance = point_to_text_path_signed_distance
_primitive_center = primitive_center
#============================================
def optical_center_via_isolation_render(*args: object, **kwargs: object) -> object:
	"""Load the optional optical diagnostic only when an external caller needs it."""
	from measurelib.lcf_optical import optical_center_via_isolation_render as optical_measure
	result = optical_measure(*args, **kwargs)
	return result


_optical_center_via_isolation_render = optical_center_via_isolation_render
_canonical_cycle_key = canonical_cycle_key
_clustered_endpoint_graph = clustered_endpoint_graph
_cycle_node_pairs = cycle_node_pairs
_detect_haworth_base_ring = detect_haworth_base_ring
_detect_haworth_ring_from_line_cycles = detect_haworth_ring_from_line_cycles
_detect_haworth_ring_from_primitives = detect_haworth_ring_from_primitives
_empty_haworth_ring_detection = empty_haworth_ring_detection
_find_candidate_cycles = find_candidate_cycles
_default_overlap_origin = default_overlap_origin
_detect_double_bond_pairs = detect_double_bond_pairs
_detect_hashed_carrier_map = detect_hashed_carrier_map
_is_hashed_carrier_candidate = is_hashed_carrier_candidate
_is_hatch_stroke_candidate = is_hatch_stroke_candidate
_overlap_origin = overlap_origin
_quadrant_label = quadrant_label
_ring_region_label = ring_region_label
_count_bond_bond_overlaps = count_bond_bond_overlaps
_count_bond_glyph_overlaps = count_bond_glyph_overlaps
_count_glyph_glyph_overlaps = count_glyph_glyph_overlaps
_count_hatched_thin_conflicts = count_hatched_thin_conflicts
_count_lattice_angle_violations = count_lattice_angle_violations
_clip_infinite_line_to_bounds = clip_infinite_line_to_bounds
_diagnostic_bounds = diagnostic_bounds
_diagnostic_color = diagnostic_color
_metric_alignment_center = metric_alignment_center
_metric_endpoint = metric_endpoint
_select_alignment_primitive = select_alignment_primitive
_viewbox_bounds = viewbox_bounds
_write_diagnostic_svg = write_diagnostic_svg
_JSON_SUMMARY_EXCLUDE_KEYS = JSON_SUMMARY_EXCLUDE_KEYS
_format_stats_line = format_stats_line
_json_summary_compact = json_summary_compact
_summary_stats = summary_stats
_text_report = text_report
_top_misses = top_misses
_violation_summary = violation_summary


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments for alignment analysis."""
	parser = argparse.ArgumentParser(
		description="Measure bond endpoint alignment against glyph attach targets from existing SVG files.",
	)
	parser.add_argument(
		"-i",
		"--input-glob",
		dest="input_glob",
		type=str,
		default=DEFAULT_INPUT_GLOB,
		help=(
			"Glob pattern for existing SVG files. Omit it to render the bounded "
			"current Haworth corpus through OASA's controlled lxml SVG writer."
		),
	)
	parser.add_argument(
		"-j",
		"--json-report",
		dest="json_report",
		type=str,
		default=DEFAULT_JSON_REPORT,
		help="Output path for JSON report.",
	)
	parser.add_argument(
		"-t",
		"--text-report",
		dest="text_report",
		type=str,
		default=DEFAULT_TEXT_REPORT,
		help="Output path for text summary report.",
	)
	parser.add_argument(
		"--diagnostic-svg-dir",
		dest="diagnostic_svg_dir",
		type=str,
		default=DEFAULT_DIAGNOSTIC_SVG_DIR,
		help="Output directory for diagnostic SVG overlays (one file per input SVG).",
	)
	parser.add_argument(
		"-f",
		"--fail-on-miss",
		dest="fail_on_miss",
		action="store_true",
		help="Exit non-zero when any label has no connector or misses attach target.",
	)
	parser.add_argument(
		"-p",
		"--pass-on-miss",
		dest="fail_on_miss",
		action="store_false",
		help="Always exit zero, even when misses are detected.",
	)
	parser.add_argument(
		"--exclude-haworth-base-ring",
		dest="exclude_haworth_base_ring",
		action="store_true",
		help="Exclude detected Haworth base-ring template geometry from checks (default: on).",
	)
	parser.add_argument(
		"--include-haworth-base-ring",
		dest="exclude_haworth_base_ring",
		action="store_false",
		help="Include detected Haworth base-ring template geometry in checks.",
	)
	parser.add_argument(
		"--write-diagnostic-svg",
		dest="write_diagnostic_svg",
		action="store_true",
		help="Write diagnostic SVG overlays (default: on).",
	)
	parser.add_argument(
		"--no-diagnostic-svg",
		dest="write_diagnostic_svg",
		action="store_false",
		help="Disable diagnostic SVG overlay output.",
	)
	parser.add_argument(
		"--write-diagnostic-png",
		dest="write_diagnostic_png",
		action="store_true",
		help="Write diagnostic PNG set (ROI and full overlays) when optical mode is used (default: on).",
	)
	parser.add_argument(
		"--no-diagnostic-png",
		dest="write_diagnostic_png",
		action="store_false",
		help="Disable diagnostic PNG set output.",
	)
	parser.add_argument(
		"--bond-glyph-gap-tolerance",
		dest="bond_glyph_gap_tolerance",
		type=float,
		default=BOND_GLYPH_GAP_TOLERANCE,
		help=(
			"Additional gap tolerance for bond/glyph proximity diagnostics; "
			"larger values flag near-miss crowding as violations."
		),
	)
	parser.set_defaults(fail_on_miss=False)
	parser.set_defaults(exclude_haworth_base_ring=True)
	parser.set_defaults(write_diagnostic_svg=True)
	parser.set_defaults(write_diagnostic_png=True)
	return parser.parse_args()


#============================================
def get_repo_root() -> pathlib.Path:
	"""Return repository root using git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=False,
	)
	if result.returncode != 0:
		raise RuntimeError("Could not detect repo root via git rev-parse --show-toplevel")
	return pathlib.Path(result.stdout.strip())


#============================================
def generate_current_haworth_corpus(repo_root: pathlib.Path) -> list[pathlib.Path]:
	"""Render the bounded current Haworth gate corpus through controlled lxml SVG."""
	from lxml import etree
	from oasa import render_ops
	from oasa.haworth import renderer

	output_dir = repo_root / DEFAULT_CURRENT_RUNTIME_DIR
	output_dir.mkdir(parents=True, exist_ok=True)
	paths = []
	for ring_type in ("furanose", "pyranose"):
		ops = renderer.render_from_code("ARLRDM", ring_type, "alpha")
		root = etree.Element(
			"{http://www.w3.org/2000/svg}svg",
			nsmap={None: "http://www.w3.org/2000/svg"},
			attrib={
				"version": "1.1",
				"width": "260",
				"height": "260",
				"viewBox": "-90 -90 180 180",
				"preserveAspectRatio": "xMidYMid meet",
			},
		)
		group = etree.SubElement(root, "{http://www.w3.org/2000/svg}g")
		render_ops.ops_to_lxml_svg(group, ops)
		path = output_dir / f"ARLRDM_{ring_type}_alpha.svg"
		path.write_bytes(etree.tostring(root, encoding="utf-8", xml_declaration=True))
		paths.append(path)
	return paths


#============================================
def print_summary(file_summary: dict, file_top_misses: list[dict]) -> None:
	"""Print concise alignment summary to stdout."""
	alignment_pct = file_summary["alignment_rate"] * 100.0
	print(f"{'Files analyzed:':<42}{file_summary['files_analyzed']:>6}")
	print(f"{'Labels analyzed:':<42}{file_summary['labels_analyzed']:>6}")
	print(
		f"{'  Aligned:':<42}{file_summary['aligned_labels']:>6}"
		f"  ({alignment_pct:.1f}%)"
	)
	print(
		f"{'Bonds (detected / checked):':<42}"
		f"{file_summary['total_bonds_detected']:>6} / {file_summary['total_bonds_checked']}"
	)
	print()
	# violation summary -- only print nonzero categories
	violation_total = (
		file_summary.get("alignment_outside_tolerance_count", 0)
		+ file_summary.get("lattice_angle_violation_count", 0)
		+ file_summary.get("glyph_glyph_overlap_count", 0)
		+ file_summary.get("bond_bond_overlap_count", 0)
		+ file_summary.get("bond_glyph_overlap_count", 0)
		+ file_summary.get("hatched_thin_conflict_count", 0)
	)
	print(f"{'Violations:':<42}{violation_total:>6}")
	if violation_total > 0:
		violation_items = [
			("  Alignment outside tolerance", "alignment_outside_tolerance_count"),
			("  Lattice angle violations", "lattice_angle_violation_count"),
			("  Glyph/glyph overlaps", "glyph_glyph_overlap_count"),
			("  Bond/bond overlaps", "bond_bond_overlap_count"),
			("  Bond/glyph overlaps", "bond_glyph_overlap_count"),
			("  Hatched/thin conflicts", "hatched_thin_conflict_count"),
		]
		for label, key in violation_items:
			count = file_summary.get(key, 0)
			if count > 0:
				print(f"{label + ':':<42}{count:>6}")
	print()
	# top misses -- show at most 3
	if file_top_misses:
		print("Top misses:")
		for item in file_top_misses[:3]:
			dist = item["distance"]
			dist_text = "inf" if math.isinf(dist) else f"{dist:.3f}"
			svg_name = pathlib.Path(str(item["svg"])).stem
			print(
				f"  {svg_name:<28}  label={item['text']:<6}"
				f"  reason={item['reason']:<30}  dist={dist_text}"
			)
		remaining = len(file_top_misses) - 3
		if remaining > 0:
			print(f"  ... and {remaining} more (see text report)")
	# per-label alignment stats
	label_stats = file_summary.get("alignment_label_type_stats", {})
	if label_stats:
		def _fmt_triple(stats: dict) -> str:
			if stats.get("count", 0) == 0:
				return "(none)"
			return f"{stats['mean']:.2f}/{stats['stddev']:.2f}/{stats['median']:.2f}"
		print(f"Per-label alignment:  {'bond_end_gap(a/s/m)':>21}  {'perp_offset(a/s/m)':>20}")
		# ALL row
		total_ct = file_summary.get("labels_analyzed", 0)
		total_al = file_summary.get("aligned_labels", 0)
		total_rate = file_summary.get("alignment_rate", 0.0) * 100.0
		all_gap = file_summary.get("glyph_to_bond_end_signed_distance_stats", {})
		all_aln = file_summary.get("alignment_distance_stats", {})
		print(
			f"  {'ALL':<8} {total_al:>3}/{total_ct:<3} ({total_rate:>5.1f}%)"
			f"  {_fmt_triple(all_gap):>18}  {_fmt_triple(all_aln):>20}"
		)
		for label_text in sorted(label_stats.keys()):
			entry = label_stats[label_text]
			count = entry["count"]
			aligned_ct = entry["aligned_count"]
			rate = entry["alignment_rate"] * 100.0
			gap_s = entry.get("gap_distance_stats", {})
			align_s = entry.get("alignment_distance_stats", {})
			print(
				f"  {label_text:<8} {aligned_ct:>3}/{count:<3} ({rate:>5.1f}%)"
				f"  {_fmt_triple(gap_s):>18}  {_fmt_triple(align_s):>20}"
			)
		print()


#============================================
def main() -> None:
	"""Run SVG alignment measurement and write reports."""
	args = parse_args()
	repo_root = get_repo_root()
	if args.input_glob:
		svg_paths = resolve_svg_paths(repo_root, args.input_glob)
		input_description = args.input_glob
	else:
		svg_paths = generate_current_haworth_corpus(repo_root)
		input_description = f"controlled current runtime: {DEFAULT_CURRENT_RUNTIME_DIR}"
	if not svg_paths:
		raise RuntimeError(f"No SVG files matched input_glob: {args.input_glob!r}")
	diagnostic_svg_dir = pathlib.Path(args.diagnostic_svg_dir)
	if not diagnostic_svg_dir.is_absolute():
		diagnostic_svg_dir = (repo_root / diagnostic_svg_dir).resolve()
	file_reports = [
		analyze_svg_file(
			path,
			exclude_haworth_base_ring=args.exclude_haworth_base_ring,
			bond_glyph_gap_tolerance=args.bond_glyph_gap_tolerance,
			write_diagnostic_svg=bool(args.write_diagnostic_svg),
			diagnostic_svg_dir=diagnostic_svg_dir,
		)
		for path in svg_paths
	]
	file_summary = summary_stats(file_reports)
	file_top_misses = top_misses(file_reports, limit=20)
	# -- build JSON report with compact summary and debug section --
	json_report = {
		"schema_version": 2,
		"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
		"input_glob": input_description,
		"alignment_center_mode": "optical",
		"exclude_haworth_base_ring": bool(args.exclude_haworth_base_ring),
		"bond_glyph_gap_tolerance": float(args.bond_glyph_gap_tolerance),
		"summary": json_summary_compact(file_summary),
		"violation_summary": violation_summary(file_summary, file_top_misses),
		"top_misses": file_top_misses,
		"debug": {
			"repo_root": str(repo_root),
			"full_summary": file_summary,
			"files": file_reports,
		},
	}
	file_text_report = text_report(
		summary=file_summary,
		top_misses=file_top_misses,
		input_glob=input_description,
		exclude_haworth_base_ring=bool(args.exclude_haworth_base_ring),
	)
	json_report_path = pathlib.Path(args.json_report)
	text_report_path = pathlib.Path(args.text_report)
	if not json_report_path.is_absolute():
		json_report_path = (repo_root / json_report_path).resolve()
	if not text_report_path.is_absolute():
		text_report_path = (repo_root / text_report_path).resolve()
	json_report_path.parent.mkdir(parents=True, exist_ok=True)
	text_report_path.parent.mkdir(parents=True, exist_ok=True)
	json_report_path.write_text(json.dumps(json_report, indent=2), encoding="utf-8")
	text_report_path.write_text(file_text_report, encoding="utf-8")
	# -- concise console output --
	print(f"Wrote JSON report: {json_report_path}")
	print(f"Wrote text report: {text_report_path}")
	if args.write_diagnostic_svg:
		print(f"Wrote diagnostic SVGs to: {diagnostic_svg_dir}")
		# Print individual diagnostic SVG path for single-file runs
		if len(svg_paths) == 1:
			for report in file_reports:
				diag = report.get("diagnostic_svg")
				if diag:
					print(f"Diagnostic SVG: file://{diag}")
	print()
	print_summary(file_summary, file_top_misses)
	if args.fail_on_miss and (file_summary["missed_labels"] > 0 or file_summary["labels_without_connector"] > 0):
		raise SystemExit(2)


if __name__ == "__main__":
	main()
