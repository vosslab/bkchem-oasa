"""Backward-compat shim -- real code lives in oasa.haworth.renderer.

Preserves the old ``import oasa.haworth_renderer`` interface by importing all
public constants, functions, and private helpers from the new subpackage so
that existing call sites (tests, tools) keep working without edits.
"""

from oasa.haworth import renderer_config as _cfg
from oasa.haworth import renderer_geometry as _geom
from oasa.haworth import renderer_text as _text
from oasa.haworth import renderer_layout as _layout
from oasa.haworth import renderer as _renderer

# -- public API ---------------------------------------------------------------
render = _renderer.render
render_from_code = _renderer.render_from_code
carbon_slot_map = _renderer.carbon_slot_map
label_target_for_text_op = _renderer.label_target_for_text_op
attach_target_for_text_op = _renderer.attach_target_for_text_op
strict_validate_ops = _renderer.strict_validate_ops

# -- constants ----------------------------------------------------------------
PYRANOSE_SLOTS = _cfg.PYRANOSE_SLOTS
FURANOSE_SLOTS = _cfg.FURANOSE_SLOTS
PYRANOSE_SLOT_INDEX = _cfg.PYRANOSE_SLOT_INDEX
FURANOSE_SLOT_INDEX = _cfg.FURANOSE_SLOT_INDEX
PYRANOSE_FRONT_EDGE_SLOT = _cfg.PYRANOSE_FRONT_EDGE_SLOT
FURANOSE_FRONT_EDGE_SLOT = _cfg.FURANOSE_FRONT_EDGE_SLOT
PYRANOSE_FRONT_EDGE_INDEX = _cfg.PYRANOSE_FRONT_EDGE_INDEX
FURANOSE_FRONT_EDGE_INDEX = _cfg.FURANOSE_FRONT_EDGE_INDEX
RING_SLOT_SEQUENCE = _cfg.RING_SLOT_SEQUENCE
PYRANOSE_SLOT_LABEL_CONFIG = _cfg.PYRANOSE_SLOT_LABEL_CONFIG
FURANOSE_SLOT_LABEL_CONFIG = _cfg.FURANOSE_SLOT_LABEL_CONFIG
RING_RENDER_CONFIG = _cfg.RING_RENDER_CONFIG
CARBON_NUMBER_VERTEX_WEIGHT = _cfg.CARBON_NUMBER_VERTEX_WEIGHT
OXYGEN_COLOR = _cfg.OXYGEN_COLOR
HYDROXYL_GLYPH_WIDTH_FACTOR = _cfg.HYDROXYL_GLYPH_WIDTH_FACTOR
HYDROXYL_O_X_CENTER_FACTOR = _cfg.HYDROXYL_O_X_CENTER_FACTOR
HYDROXYL_O_Y_CENTER_FROM_BASELINE = _cfg.HYDROXYL_O_Y_CENTER_FROM_BASELINE
HYDROXYL_O_RADIUS_FACTOR = _cfg.HYDROXYL_O_RADIUS_FACTOR
LEADING_C_X_CENTER_FACTOR = _cfg.LEADING_C_X_CENTER_FACTOR
HYDROXYL_LAYOUT_CANDIDATE_FACTORS = _cfg.HYDROXYL_LAYOUT_CANDIDATE_FACTORS
HYDROXYL_LAYOUT_INTERNAL_CANDIDATE_FACTORS = _cfg.HYDROXYL_LAYOUT_INTERNAL_CANDIDATE_FACTORS
HYDROXYL_LAYOUT_MIN_GAP_FACTOR = _cfg.HYDROXYL_LAYOUT_MIN_GAP_FACTOR
HYDROXYL_RING_COLLISION_PENALTY = _cfg.HYDROXYL_RING_COLLISION_PENALTY
INTERNAL_PAIR_OVERLAP_AREA_THRESHOLD = _cfg.INTERNAL_PAIR_OVERLAP_AREA_THRESHOLD
INTERNAL_PAIR_LABEL_SCALE = _cfg.INTERNAL_PAIR_LABEL_SCALE
INTERNAL_PAIR_LANE_Y_TOLERANCE_FACTOR = _cfg.INTERNAL_PAIR_LANE_Y_TOLERANCE_FACTOR
INTERNAL_PAIR_MIN_H_GAP_FACTOR = _cfg.INTERNAL_PAIR_MIN_H_GAP_FACTOR
FURANOSE_TOP_UP_CLEARANCE_FACTOR = _cfg.FURANOSE_TOP_UP_CLEARANCE_FACTOR
VALID_DIRECTIONS = _cfg.VALID_DIRECTIONS
VALID_ANCHORS = _cfg.VALID_ANCHORS
REQUIRED_SIMPLE_JOB_KEYS = _cfg.REQUIRED_SIMPLE_JOB_KEYS

# -- private helpers (used by test code) --------------------------------------
_normalize_vector = _geom.normalize_vector
_edge_polygon = _geom.edge_polygon
_intersection_area = _geom.intersection_area
_point_in_box = _geom.point_in_box
_rect_corners = _geom.rect_corners
_point_in_polygon = _geom.point_in_polygon
_segments_intersect = _geom.segments_intersect
_box_overlaps_polygon = _geom.box_overlaps_polygon

_chain_labels = _text.chain_labels
_is_chain_like_label = _text.is_chain_like_label
_format_label_text = _text.format_label_text
_format_chain_label_text = _text.format_chain_label_text
_apply_subscript_markup = _text.apply_subscript_markup
_anchor_x_offset = _text.anchor_x_offset
_leading_carbon_anchor_offset = _text.leading_carbon_anchor_offset
_trailing_carbon_anchor_offset = _text.trailing_carbon_anchor_offset
_hydroxyl_oxygen_radius = _text.hydroxyl_oxygen_radius
_leading_carbon_center = _text.leading_carbon_center
_hydroxyl_oxygen_center = _text.hydroxyl_oxygen_center
_visible_text_length = _text.visible_text_length

_validate_simple_job = _layout.validate_simple_job
_resolve_hydroxyl_layout_jobs = _layout.resolve_hydroxyl_layout_jobs
_job_is_hydroxyl = _layout.job_is_hydroxyl
_job_is_internal_hydroxyl = _layout.job_is_internal_hydroxyl
_job_can_flip_internal_anchor = _layout.job_can_flip_internal_anchor
_best_equal_internal_hydroxyl_length = _layout.best_equal_internal_hydroxyl_length
_hydroxyl_candidate_jobs = _layout.hydroxyl_candidate_jobs
_job_end_point = _layout.job_end_point
_internal_pair_overlap_area = _layout.internal_pair_overlap_area
_internal_pair_horizontal_gap = _layout.internal_pair_horizontal_gap
_resolve_internal_hydroxyl_pair_overlap = _layout.resolve_internal_hydroxyl_pair_overlap
_job_text_target = _layout.job_text_target
_text_target = _layout.text_target
_overlap_penalty = _layout.overlap_penalty
_hydroxyl_job_penalty = _layout.hydroxyl_job_penalty
_attach_target_for_connector = _renderer._attach_target_for_connector
