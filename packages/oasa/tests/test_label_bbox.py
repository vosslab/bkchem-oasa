"""Unit tests for label bbox and clipping helpers in render_geometry."""

# Third Party
import pytest

# local repo modules
import oasa
from oasa import render_geometry
from oasa import render_ops


#============================================
def _make_vertex(symbol="O", label=None, anchor=None, x=0.0, y=0.0):
	vertex = oasa.Atom(symbol=symbol)
	vertex.x = float(x)
	vertex.y = float(y)
	if label is not None:
		vertex.properties_["label"] = label
	if anchor is not None:
		vertex.properties_["label_anchor"] = anchor
	return vertex


#============================================
def _point_in_bbox(point, bbox):
	x, y = point
	x1, y1, x2, y2 = bbox
	return x1 <= x <= x2 and y1 <= y <= y2


#============================================
def _bbox_contains(inner, outer):
	return (
		outer[0] <= inner[0] <= inner[2] <= outer[2]
		and outer[1] <= inner[1] <= inner[3] <= outer[3]
	)


#============================================
def _is_on_box_edge(point, box, tol=1e-6):
	x, y = point
	x1, y1, x2, y2 = box
	on_x = abs(x - x1) <= tol or abs(x - x2) <= tol
	on_y = abs(y - y1) <= tol or abs(y - y2) <= tol
	in_x = x1 - tol <= x <= x2 + tol
	in_y = y1 - tol <= y <= y2 + tol
	return (on_x and in_y) or (on_y and in_x)


#============================================
def _clip_to_box(bond_start, bond_end, box):
	end_x, end_y = bond_end
	x1, y1, x2, y2 = box
	if not (x1 <= end_x <= x2 and y1 <= end_y <= y2):
		return bond_end
	return render_geometry.resolve_attach_endpoint(
		bond_start=bond_start,
		target=render_geometry.make_box_target(box),
		interior_hint=bond_end,
		constraints=render_geometry.AttachConstraints(direction_policy="line"),
	)


#============================================
def _first_polygon_op(ops):
	for op in ops:
		if isinstance(op, render_ops.PolygonOp):
			return op
	return None


#============================================
def _tokens_from_text(text):
	visible = render_geometry._visible_label_text(text)
	spans = render_geometry._tokenized_atom_spans(text)
	return [visible[start:end] for start, end in spans]


#============================================
def test_label_bbox_single_char_middle():
	bbox = render_geometry.label_target(10.0, 20.0, "O", "middle", 16.0).box
	x1, y1, x2, y2 = bbox
	assert x1 < x2
	assert y1 < y2
	assert (x2 - x1) > 0.0
	assert (y2 - y1) > 0.0
	# origin (10, 20) should be inside the box for middle anchor
	assert x1 <= 10.0 <= x2
	assert y1 <= 20.0 <= y2


#============================================
def test_label_bbox_multi_char_start():
	bbox = render_geometry.label_target(10.0, 8.0, "OH", "start", 12.0).box
	x1, y1, x2, y2 = bbox
	assert x1 < x2
	assert y1 < y2
	assert (x2 - x1) > 0.0
	assert (y2 - y1) > 0.0
	# origin (10, 8) should be inside the box for start anchor
	assert x1 <= 10.0 <= x2
	assert y1 <= 8.0 <= y2


#============================================
def test_label_bbox_anchor_matrix():
	for anchor in ("start", "middle", "end"):
		for text in ("O", "OH", "CH2OH", "NH3+", "Cl"):
			x1, y1, x2, y2 = render_geometry.label_target(5.0, 7.0, text, anchor, 16.0).box
			assert x1 < x2
			assert y1 < y2
			assert (x2 - x1) > 0.0
			assert (y2 - y1) > 0.0


#============================================
def test_label_bbox_origin_inside_bbox_for_anchor_matrix():
	for anchor in ("start", "middle", "end"):
		vertex = _make_vertex(symbol="C", label="CH2OH", anchor=anchor, x=30.0, y=40.0)
		ops = render_geometry.build_vertex_ops(vertex, font_size=16.0)
		text_ops = [op for op in ops if isinstance(op, render_ops.TextOp)]
		assert len(text_ops) == 1
		origin = (text_ops[0].x, text_ops[0].y)
		bbox = render_geometry.label_target(30.0, 40.0, "CH2OH", anchor, 16.0).box
		assert _point_in_bbox(origin, bbox)


#============================================
def test_label_bbox_visible_length_strips_tags():
	plain = render_geometry.label_target(0.0, 0.0, "CH2OH", "start", 16.0).box
	with_markup = render_geometry.label_target(0.0, 0.0, "CH<sub>2</sub>OH", "start", 16.0).box
	assert plain[0] == pytest.approx(with_markup[0])
	assert plain[1] == pytest.approx(with_markup[1])
	assert with_markup[2] <= plain[2]
	assert plain[3] == pytest.approx(with_markup[3])


#============================================
def test_label_bbox_matches_vertex_ops_mask():
	vertex = _make_vertex(symbol="C", label="OH", anchor="start", x=12.0, y=15.0)
	ops = render_geometry.build_vertex_ops(vertex, font_size=16.0)
	polygon = _first_polygon_op(ops)
	assert polygon is not None
	bbox = render_geometry.label_target(12.0, 15.0, "OH", "start", 16.0).box
	x1, y1, x2, y2 = bbox
	expected_points = (
		(x1, y1),
		(x2, y1),
		(x2, y2),
		(x1, y2),
	)
	for actual_point, expected_point in zip(polygon.points, expected_points):
		assert actual_point == pytest.approx(expected_point)


#============================================
def test_label_attach_bbox_single_atom_same_as_label_bbox():
	for symbol in ("O", "N", "Cl"):
		full_bbox = render_geometry.label_target(0.0, 0.0, symbol, "middle", 16.0).box
		first_bbox = render_geometry.label_attach_target(
			0.0, 0.0, symbol, "middle", 16.0, attach_atom="first"
		).box
		last_bbox = render_geometry.label_attach_target(
			0.0, 0.0, symbol, "middle", 16.0, attach_atom="last"
		).box
		assert first_bbox == pytest.approx(full_bbox)
		assert last_bbox == pytest.approx(full_bbox)


#============================================
def test_label_attach_bbox_multi_atom_first():
	full_bbox = render_geometry.label_target(0.0, 0.0, "CH2OH", "start", 12.0).box
	first_bbox = render_geometry.label_attach_target(
		0.0, 0.0, "CH2OH", "start", 12.0, attach_atom="first"
	).box
	assert first_bbox[0] == pytest.approx(full_bbox[0])
	assert first_bbox[2] < full_bbox[2]


#============================================
def test_label_attach_bbox_multi_atom_last():
	full_bbox = render_geometry.label_target(0.0, 0.0, "CH2OH", "start", 12.0).box
	last_bbox = render_geometry.label_attach_target(
		0.0, 0.0, "CH2OH", "start", 12.0, attach_atom="last"
	).box
	assert last_bbox[2] <= full_bbox[2]
	assert last_bbox[0] > full_bbox[0]


#============================================
def test_label_attach_bbox_within_label_bbox():
	cases = (
		("O", "middle"),
		("CH2OH", "start"),
		("CH2OH", "middle"),
		("CH2OH", "end"),
		("NH3+", "start"),
		("OAc", "start"),
	)
	for text, anchor in cases:
		full_bbox = render_geometry.label_target(0.0, 0.0, text, anchor, 16.0).box
		for attach_atom in ("first", "last"):
			attach_bbox = render_geometry.label_attach_target(
				0.0, 0.0, text, anchor, 16.0, attach_atom=attach_atom
			).box
			assert _bbox_contains(attach_bbox, full_bbox)


#============================================
def test_label_attach_bbox_invalid_attach_atom_raises():
	with pytest.raises(ValueError, match=r"Invalid attach_atom value: 'frist'"):
		render_geometry.label_attach_target(
			0.0, 0.0, "CH2OH", "start", 16.0, attach_atom="frist"
		).box


#============================================
@pytest.mark.parametrize(
	("text", "expected_tokens"),
	(
		("OAc", ["O", "Ac"]),
		("NHCH3", ["NH", "CH3"]),
		("SO3H", ["S", "O3", "H"]),
		("PPh3", ["P", "Ph3"]),
		("CH(OH)CH2OH", ["CH", "OH", "CH2", "OH"]),
	),
)
def test_tokenized_atom_spans_fixture_matrix(text, expected_tokens):
	assert _tokens_from_text(text) == expected_tokens


#============================================
def test_attach_bbox_first_last_ch2oh():
	for anchor in ("start", "middle", "end"):
		first_bbox = render_geometry.label_attach_target(
			0.0, 0.0, "CH2OH", anchor, 16.0, attach_atom="first"
		).box
		last_bbox = render_geometry.label_attach_target(
			0.0, 0.0, "CH2OH", anchor, 16.0, attach_atom="last"
		).box
		assert first_bbox[0] < last_bbox[0]
		assert first_bbox[2] <= last_bbox[2]


#============================================
def test_directional_attach_edge_intersection_prefers_side_edge_for_side_approach():
	attach_bbox = (0.0, 0.0, 10.0, 10.0)
	attach_target = (6.0, 9.0)
	bond_start = (-20.0, 8.0)
	endpoint = render_geometry.directional_attach_edge_intersection(
		bond_start=bond_start,
		attach_bbox=attach_bbox,
		attach_target=attach_target,
	)
	assert _is_on_box_edge(endpoint, attach_bbox, tol=1e-6)
	assert endpoint[0] == pytest.approx(attach_bbox[0], abs=1e-6)
	assert endpoint[1] < (attach_bbox[3] - 1e-6)


#============================================
def test_directional_attach_edge_intersection_prefers_vertical_edge_for_vertical_approach():
	attach_bbox = (0.0, 0.0, 10.0, 10.0)
	attach_target = (6.0, 9.0)
	bond_start = (5.5, -20.0)
	endpoint = render_geometry.directional_attach_edge_intersection(
		bond_start=bond_start,
		attach_bbox=attach_bbox,
		attach_target=attach_target,
	)
	assert _is_on_box_edge(endpoint, attach_bbox, tol=1e-6)
	assert endpoint[1] == pytest.approx(attach_bbox[1], abs=1e-6)


#============================================
def test_clip_bond_inside_bbox():
	clipped = _clip_to_box((-5.0, 5.0), (5.0, 5.0), (0.0, 0.0, 10.0, 10.0))
	assert clipped == pytest.approx((0.0, 5.0))


#============================================
def test_clip_bond_outside_bbox():
	clipped = _clip_to_box((-5.0, 5.0), (-1.0, 5.0), (0.0, 0.0, 10.0, 10.0))
	assert clipped == pytest.approx((-1.0, 5.0))


#============================================
def test_clip_bond_vertical():
	clipped = _clip_to_box((5.0, -5.0), (5.0, 5.0), (0.0, 0.0, 10.0, 10.0))
	assert clipped == pytest.approx((5.0, 0.0))


#============================================
def test_clip_bond_horizontal():
	clipped = _clip_to_box((15.0, 5.0), (5.0, 5.0), (0.0, 0.0, 10.0, 10.0))
	assert clipped == pytest.approx((10.0, 5.0))


#============================================
def test_clip_bond_diagonal():
	clipped = _clip_to_box((-5.0, -5.0), (5.0, 5.0), (0.0, 0.0, 10.0, 10.0))
	assert clipped == pytest.approx((0.0, 0.0))


#============================================
def test_clips_to_attach_bbox_not_full_bbox():
	full_bbox = render_geometry.label_target(0.0, 0.0, "CH2OH", "start", 10.0).box
	attach_bbox = render_geometry.label_attach_target(
		0.0, 0.0, "CH2OH", "start", 10.0, attach_atom="first"
	).box
	inside_y = (attach_bbox[1] + attach_bbox[3]) / 2.0
	bond_start = (60.0, inside_y)
	bond_end = ((attach_bbox[0] + attach_bbox[2]) / 2.0, inside_y)
	full_clip = _clip_to_box(bond_start, bond_end, full_bbox)
	attach_clip = _clip_to_box(bond_start, bond_end, attach_bbox)
	assert attach_clip[0] < full_clip[0]
	assert _point_in_bbox(attach_clip, attach_bbox)
