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

"""Render geometry sub-package -- backward-compatible re-exports."""

# --- data_types ---
from oasa.render_lib.data_types import ATTACH_GAP_FONT_FRACTION
from oasa.render_lib.data_types import ATTACH_GAP_MAX
from oasa.render_lib.data_types import ATTACH_GAP_MIN
from oasa.render_lib.data_types import ATTACH_GAP_TARGET
from oasa.render_lib.data_types import ATTACH_PERP_TOLERANCE
from oasa.render_lib.data_types import AttachConstraints
from oasa.render_lib.data_types import AttachTarget
from oasa.render_lib.data_types import BOND_LENGTH_EXCEPTION_TAGS
from oasa.render_lib.data_types import BOND_LENGTH_PROFILE
from oasa.render_lib.data_types import BondRenderContext
from oasa.render_lib.data_types import GlyphAttachPrimitive
from oasa.render_lib.data_types import HASHED_BOND_WEDGE_RATIO
from oasa.render_lib.data_types import LabelAttachContract
from oasa.render_lib.data_types import LabelAttachPolicy
from oasa.render_lib.data_types import VALID_ATTACH_SITES
from oasa.render_lib.data_types import VALID_BOND_STYLES
from oasa.render_lib.data_types import _OVAL_GLYPH_ELEMENTS
from oasa.render_lib.data_types import _RECT_GLYPH_ELEMENTS
from oasa.render_lib.data_types import _SPECIAL_GLYPH_ELEMENTS
from oasa.render_lib.data_types import _coerce_attach_target
from oasa.render_lib.data_types import _normalize_attach_site
from oasa.render_lib.data_types import _normalize_element_symbol
from oasa.render_lib.data_types import make_attach_constraints
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.data_types import make_circle_target
from oasa.render_lib.data_types import make_composite_target
from oasa.render_lib.data_types import make_segment_target

# --- bond_length_policy ---
from oasa.render_lib.bond_length_policy import _bond_style_for_edge
from oasa.render_lib.bond_length_policy import _normalize_bond_style
from oasa.render_lib.bond_length_policy import _normalize_exception_tag
from oasa.render_lib.bond_length_policy import bond_length_profile
from oasa.render_lib.bond_length_policy import resolve_bond_length

# --- glyph_model ---
from oasa.render_lib.glyph_model import _glyph_center_factor
from oasa.render_lib.glyph_model import _glyph_class_for_symbol
from oasa.render_lib.glyph_model import _glyph_closed_center_factor
from oasa.render_lib.glyph_model import glyph_attach_primitive

# --- low_level_geometry ---
from oasa.render_lib.low_level_geometry import _box_center
from oasa.render_lib.low_level_geometry import _capsule_intersects_target
from oasa.render_lib.low_level_geometry import _circle_boundary_toward_target
from oasa.render_lib.low_level_geometry import _clip_line_to_box
from oasa.render_lib.low_level_geometry import _closest_point_on_segment
from oasa.render_lib.low_level_geometry import _distance_sq_segment_to_segment
from oasa.render_lib.low_level_geometry import _expanded_box
from oasa.render_lib.low_level_geometry import _lattice_step_for_direction_policy
from oasa.render_lib.low_level_geometry import _line_circle_intersection
from oasa.render_lib.low_level_geometry import _line_intersection
from oasa.render_lib.low_level_geometry import _on_segment
from oasa.render_lib.low_level_geometry import _orientation
from oasa.render_lib.low_level_geometry import _point_in_attach_target
from oasa.render_lib.low_level_geometry import _point_in_attach_target_closed
from oasa.render_lib.low_level_geometry import _point_to_segment_distance_sq
from oasa.render_lib.low_level_geometry import _ray_box_boundary_intersection
from oasa.render_lib.low_level_geometry import _ray_circle_boundary_intersection
from oasa.render_lib.low_level_geometry import _resolve_direction_mode
from oasa.render_lib.low_level_geometry import _segment_distance_to_box_sq
from oasa.render_lib.low_level_geometry import _segments_intersect
from oasa.render_lib.low_level_geometry import _snapped_direction_unit
from oasa.render_lib.low_level_geometry import _vertical_circle_boundary
from oasa.render_lib.low_level_geometry import directional_attach_edge_intersection

# --- attach_resolution ---
from oasa.render_lib.attach_resolution import _correct_endpoint_for_alignment
from oasa.render_lib.attach_resolution import _forbidden_minus_allowed_boxes
from oasa.render_lib.attach_resolution import _min_distance_point_to_target_boundary
from oasa.render_lib.attach_resolution import _perpendicular_distance_to_line
from oasa.render_lib.attach_resolution import _retreat_to_target_gap
from oasa.render_lib.attach_resolution import _subtract_box_by_box
from oasa.render_lib.attach_resolution import _target_to_box_list
from oasa.render_lib.attach_resolution import _validate_attachment_paint_box_regions
from oasa.render_lib.attach_resolution import _vertical_box_intersection
from oasa.render_lib.attach_resolution import resolve_attach_endpoint
from oasa.render_lib.attach_resolution import retreat_endpoint_until_legal
from oasa.render_lib.attach_resolution import validate_attachment_paint

# --- label_geometry ---
from oasa.render_lib.label_geometry import _chain_attach_allowed_target
from oasa.render_lib.label_geometry import _core_element_span_box
from oasa.render_lib.label_geometry import _is_chain_like_render_text
from oasa.render_lib.label_geometry import _is_hydroxyl_render_text
from oasa.render_lib.label_geometry import _label_attach_box_coords
from oasa.render_lib.label_geometry import _label_box_coords
from oasa.render_lib.label_geometry import _label_text_origin
from oasa.render_lib.label_geometry import _oxygen_allowed_target
from oasa.render_lib.label_geometry import _oxygen_circle_target_from_attach_target
from oasa.render_lib.label_geometry import _resolve_label_attach_policy
from oasa.render_lib.label_geometry import _text_char_advances
from oasa.render_lib.label_geometry import _text_ink_bearing_correction
from oasa.render_lib.label_geometry import _tokenized_atom_entries
from oasa.render_lib.label_geometry import _tokenized_atom_spans
from oasa.render_lib.label_geometry import _visible_label_length
from oasa.render_lib.label_geometry import _visible_label_text
from oasa.render_lib.label_geometry import default_label_attach_policy
from oasa.render_lib.label_geometry import label_allowed_target_from_text_origin
from oasa.render_lib.label_geometry import label_attach_contract_from_text_origin
from oasa.render_lib.label_geometry import label_attach_target
from oasa.render_lib.label_geometry import label_attach_target_from_text_origin
from oasa.render_lib.label_geometry import label_target
from oasa.render_lib.label_geometry import label_target_from_text_origin
from oasa.render_lib.label_geometry import resolve_label_connector_endpoint_from_text_origin
from oasa.render_lib.label_geometry import vertex_is_shown
from oasa.render_lib.label_geometry import vertex_label_text

# --- bond_ops ---
from oasa.render_lib.bond_ops import _apply_bond_length_policy
from oasa.render_lib.bond_ops import _avoid_cross_label_overlaps
from oasa.render_lib.bond_ops import _clip_to_target
from oasa.render_lib.bond_ops import _context_attach_target_for_vertex
from oasa.render_lib.bond_ops import _double_bond_side
from oasa.render_lib.bond_ops import _edge_length_exception_tag
from oasa.render_lib.bond_ops import _edge_length_override
from oasa.render_lib.bond_ops import _edge_line_color
from oasa.render_lib.bond_ops import _edge_line_width
from oasa.render_lib.bond_ops import _edge_wavy_style
from oasa.render_lib.bond_ops import _hashed_ops
from oasa.render_lib.bond_ops import _line_ops
from oasa.render_lib.bond_ops import _point_for_atom
from oasa.render_lib.bond_ops import _resolve_edge_colors
from oasa.render_lib.bond_ops import _resolve_endpoint_with_constraints
from oasa.render_lib.bond_ops import _rounded_wedge_ops
from oasa.render_lib.bond_ops import _wave_points
from oasa.render_lib.bond_ops import _wavy_ops
from oasa.render_lib.bond_ops import build_bond_ops
from oasa.render_lib.bond_ops import haworth_front_edge_geometry
from oasa.render_lib.bond_ops import haworth_front_edge_ops

# --- molecule_ops ---
from oasa.render_lib.molecule_ops import _DEFAULT_STYLE
from oasa.render_lib.molecule_ops import _edge_points
from oasa.render_lib.molecule_ops import _render_edge_key
from oasa.render_lib.molecule_ops import _render_edge_priority
from oasa.render_lib.molecule_ops import _render_edges_in_order
from oasa.render_lib.molecule_ops import _resolve_style
from oasa.render_lib.molecule_ops import _resolved_vertex_label_layout
from oasa.render_lib.molecule_ops import _transform_bbox
from oasa.render_lib.molecule_ops import _transform_target
from oasa.render_lib.molecule_ops import build_vertex_ops
from oasa.render_lib.molecule_ops import molecule_to_ops


__all__ = [
	# constants
	"ATTACH_GAP_FONT_FRACTION",
	"ATTACH_GAP_MAX",
	"ATTACH_GAP_MIN",
	"ATTACH_GAP_TARGET",
	"ATTACH_PERP_TOLERANCE",
	"BOND_LENGTH_EXCEPTION_TAGS",
	"BOND_LENGTH_PROFILE",
	"HASHED_BOND_WEDGE_RATIO",
	"VALID_ATTACH_SITES",
	"VALID_BOND_STYLES",
	"_DEFAULT_STYLE",
	"_OVAL_GLYPH_ELEMENTS",
	"_RECT_GLYPH_ELEMENTS",
	"_SPECIAL_GLYPH_ELEMENTS",
	# classes
	"AttachConstraints",
	"AttachTarget",
	"BondRenderContext",
	"GlyphAttachPrimitive",
	"LabelAttachContract",
	"LabelAttachPolicy",
	# public functions
	"bond_length_profile",
	"build_bond_ops",
	"build_vertex_ops",
	"default_label_attach_policy",
	"directional_attach_edge_intersection",
	"glyph_attach_primitive",
	"haworth_front_edge_geometry",
	"haworth_front_edge_ops",
	"label_allowed_target_from_text_origin",
	"label_attach_contract_from_text_origin",
	"label_attach_target",
	"label_attach_target_from_text_origin",
	"label_target",
	"label_target_from_text_origin",
	"make_attach_constraints",
	"make_box_target",
	"make_circle_target",
	"make_composite_target",
	"make_segment_target",
	"molecule_to_ops",
	"resolve_attach_endpoint",
	"resolve_bond_length",
	"resolve_label_connector_endpoint_from_text_origin",
	"retreat_endpoint_until_legal",
	"validate_attachment_paint",
	"vertex_is_shown",
	"vertex_label_text",
	# private functions (tests access these)
	"_apply_bond_length_policy",
	"_avoid_cross_label_overlaps",
	"_bond_style_for_edge",
	"_box_center",
	"_capsule_intersects_target",
	"_chain_attach_allowed_target",
	"_circle_boundary_toward_target",
	"_clip_line_to_box",
	"_clip_to_target",
	"_closest_point_on_segment",
	"_coerce_attach_target",
	"_context_attach_target_for_vertex",
	"_core_element_span_box",
	"_correct_endpoint_for_alignment",
	"_distance_sq_segment_to_segment",
	"_double_bond_side",
	"_edge_length_exception_tag",
	"_edge_length_override",
	"_edge_line_color",
	"_edge_line_width",
	"_edge_points",
	"_edge_wavy_style",
	"_expanded_box",
	"_forbidden_minus_allowed_boxes",
	"_glyph_center_factor",
	"_glyph_class_for_symbol",
	"_glyph_closed_center_factor",
	"_hashed_ops",
	"_is_chain_like_render_text",
	"_is_hydroxyl_render_text",
	"_label_attach_box_coords",
	"_label_box_coords",
	"_label_text_origin",
	"_lattice_step_for_direction_policy",
	"_line_circle_intersection",
	"_line_intersection",
	"_line_ops",
	"_min_distance_point_to_target_boundary",
	"_normalize_attach_site",
	"_normalize_bond_style",
	"_normalize_element_symbol",
	"_normalize_exception_tag",
	"_on_segment",
	"_orientation",
	"_oxygen_allowed_target",
	"_oxygen_circle_target_from_attach_target",
	"_perpendicular_distance_to_line",
	"_point_for_atom",
	"_point_in_attach_target",
	"_point_in_attach_target_closed",
	"_point_to_segment_distance_sq",
	"_ray_box_boundary_intersection",
	"_ray_circle_boundary_intersection",
	"_render_edge_key",
	"_render_edge_priority",
	"_render_edges_in_order",
	"_resolve_direction_mode",
	"_resolve_edge_colors",
	"_resolve_endpoint_with_constraints",
	"_resolve_label_attach_policy",
	"_resolve_style",
	"_resolved_vertex_label_layout",
	"_retreat_to_target_gap",
	"_rounded_wedge_ops",
	"_segment_distance_to_box_sq",
	"_segments_intersect",
	"_snapped_direction_unit",
	"_subtract_box_by_box",
	"_target_to_box_list",
	"_text_char_advances",
	"_text_ink_bearing_correction",
	"_tokenized_atom_entries",
	"_tokenized_atom_spans",
	"_transform_bbox",
	"_transform_target",
	"_validate_attachment_paint_box_regions",
	"_vertical_box_intersection",
	"_vertical_circle_boundary",
	"_visible_label_length",
	"_visible_label_text",
	"_wave_points",
	"_wavy_ops",
]
