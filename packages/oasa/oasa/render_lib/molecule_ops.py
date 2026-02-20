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

"""Vertex rendering and molecule_to_ops()."""

# local repo modules
from oasa import geometry
from oasa import oasa_utils as misc
from oasa import render_ops
from oasa.render_lib.data_types import ATTACH_GAP_TARGET
from oasa.render_lib.data_types import ATTACH_PERP_TOLERANCE
from oasa.render_lib.data_types import BondRenderContext
from oasa.render_lib.data_types import HASHED_BOND_WEDGE_RATIO
from oasa.render_lib.data_types import _coerce_attach_target
from oasa.render_lib.data_types import make_attach_constraints
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.data_types import make_circle_target
from oasa.render_lib.data_types import make_composite_target
from oasa.render_lib.data_types import make_segment_target
from oasa.render_lib.label_geometry import _label_text_origin
from oasa.render_lib.label_geometry import _tokenized_atom_spans
from oasa.render_lib.label_geometry import _visible_label_length
from oasa.render_lib.label_geometry import label_attach_target
from oasa.render_lib.label_geometry import label_target
from oasa.render_lib.label_geometry import vertex_is_shown
from oasa.render_lib.label_geometry import vertex_label_text
from oasa.render_lib.bond_ops import build_bond_ops


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
