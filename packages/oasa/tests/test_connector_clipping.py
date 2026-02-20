"""Connector clipping tests for molecule_to_ops."""

# Standard Library
import math

# Third Party
import pytest

# local repo modules
import oasa
from oasa import render_ops
from oasa.render_lib.label_geometry import label_attach_target
from oasa.render_lib.label_geometry import label_target
from oasa.render_lib.molecule_ops import molecule_to_ops


#============================================
def _make_two_atom_mol(
		*,
		left_symbol="C",
		right_symbol="O",
		right_charge=0,
		right_label=None,
		right_attach_atom=None,
		right_attach_element=None,
		bond_order=1,
		bond_type="n",
):
	mol = oasa.Molecule()
	left = oasa.Atom(symbol=left_symbol)
	left.x = 0.0
	left.y = 0.0
	right = oasa.Atom(symbol=right_symbol)
	right.x = 40.0
	right.y = 0.0
	right.charge = int(right_charge)
	if right_label is not None:
		right.properties_["label"] = right_label
	if right_attach_atom is not None:
		right.properties_["attach_atom"] = right_attach_atom
	if right_attach_element is not None:
		right.properties_["attach_element"] = right_attach_element
	mol.add_vertex(left)
	mol.add_vertex(right)
	bond = oasa.Bond(order=bond_order, type=bond_type)
	bond.vertices = (left, right)
	mol.add_edge(left, right, bond)
	return mol, left, right


#============================================
def _line_ops(ops):
	return [op for op in ops if isinstance(op, render_ops.LineOp)]


#============================================
def _first_line(ops):
	lines = _line_ops(ops)
	assert lines
	return lines[0]


#============================================
def _path_ops(ops):
	return [op for op in ops if isinstance(op, render_ops.PathOp)]


#============================================
def _path_draw_points(path_op):
	points = []
	for command, payload in path_op.commands:
		if command in ("M", "L") and payload is not None:
			points.append(payload)
	return points


#============================================
def _point_not_inside_bbox(point, bbox):
	"""Return True if the point is NOT strictly inside the bbox."""
	x, y = point
	x1, y1, x2, y2 = bbox
	return x <= x1 or x >= x2 or y <= y1 or y >= y2


#============================================
def test_bond_clipped_to_shown_vertex():
	mol, _left, right = _make_two_atom_mol(right_symbol="O")
	ops = molecule_to_ops(mol, style={"font_size": 16.0})
	line = _first_line(ops)
	assert line.p2 != pytest.approx((right.x, right.y))
	full_bbox = label_target(right.x, right.y, "O", "middle", 16.0).box
	assert _point_not_inside_bbox(line.p2, full_bbox)
	assert math.hypot(line.p2[0] - line.p1[0], line.p2[1] - line.p1[1]) > 0


#============================================
def test_bond_not_clipped_to_hidden_vertex():
	mol, _left, right = _make_two_atom_mol(right_symbol="C")
	ops = molecule_to_ops(mol, style={"font_size": 16.0})
	line = _first_line(ops)
	assert line.p2 == pytest.approx((right.x, right.y))


#============================================
def test_double_bond_clipped():
	mol, _left, right = _make_two_atom_mol(right_symbol="O", bond_order=2)
	ops = molecule_to_ops(mol, style={"font_size": 16.0})
	lines = _line_ops(ops)
	assert len(lines) == 2
	full_bbox = label_target(right.x, right.y, "O", "middle", 16.0).box
	for line in lines:
		assert line.p2 != pytest.approx((right.x, right.y))
		assert _point_not_inside_bbox(line.p2, full_bbox)
		assert math.hypot(line.p2[0] - line.p1[0], line.p2[1] - line.p1[1]) > 0


#============================================
def test_clipped_endpoint_on_bbox_edge():
	mol, _left, right = _make_two_atom_mol(right_symbol="O")
	ops = molecule_to_ops(mol, style={"font_size": 16.0})
	line = _first_line(ops)
	assert line.p2 != pytest.approx((right.x, right.y))
	full_bbox = label_target(right.x, right.y, "O", "middle", 16.0).box
	assert _point_not_inside_bbox(line.p2, full_bbox)


#============================================
def test_charged_label_clipping():
	mol_neutral, _left, _right = _make_two_atom_mol(right_symbol="N", right_charge=0)
	mol_charged, _left_c, right_charged = _make_two_atom_mol(right_symbol="N", right_charge=1)
	neutral_ops = molecule_to_ops(mol_neutral, style={"font_size": 16.0})
	charged_ops = molecule_to_ops(mol_charged, style={"font_size": 16.0})
	neutral_line = _first_line(neutral_ops)
	charged_line = _first_line(charged_ops)
	assert neutral_line.p2 != pytest.approx((40.0, 0.0))
	assert charged_line.p2 != pytest.approx((40.0, 0.0))
	charged_bbox = label_target(right_charged.x, right_charged.y, "N+", "start", 16.0).box
	assert _point_not_inside_bbox(charged_line.p2, charged_bbox)
	assert math.hypot(charged_line.p2[0] - charged_line.p1[0], charged_line.p2[1] - charged_line.p1[1]) > 0


#============================================
def test_wedge_bond_clipped():
	mol, _left, right = _make_two_atom_mol(right_symbol="O", bond_type="w")
	ops = molecule_to_ops(mol, style={"font_size": 16.0})
	paths = _path_ops(ops)
	assert paths
	points = _path_draw_points(paths[0])
	assert points
	max_x = max(point[0] for point in points)
	assert max_x < right.x


#============================================
def test_multi_atom_label_attach_first():
	mol, _left, right = _make_two_atom_mol(
		right_symbol="C",
		right_label="CH2OH",
		right_attach_atom="first",
	)
	ops = molecule_to_ops(mol, style={"font_size": 16.0})
	line = _first_line(ops)
	assert line.p2 != pytest.approx((right.x, right.y))
	full_bbox = label_target(right.x, right.y, "CH2OH", "start", 16.0).box
	assert _point_not_inside_bbox(line.p2, full_bbox)
	assert math.hypot(line.p2[0] - line.p1[0], line.p2[1] - line.p1[1]) > 0


#============================================
def test_multi_atom_label_attach_last():
	mol, _left, right = _make_two_atom_mol(
		right_symbol="C",
		right_label="CH2OH",
		right_attach_atom="last",
	)
	ops = molecule_to_ops(mol, style={"font_size": 16.0})
	line = _first_line(ops)
	assert line.p2 != pytest.approx((right.x, right.y))
	attach_bbox = label_attach_target(
		right.x, right.y, "CH2OH", "start", 16.0, attach_atom="last", font_name="Arial"
	).box
	assert _point_not_inside_bbox(line.p2, attach_bbox)
	assert math.hypot(line.p2[0] - line.p1[0], line.p2[1] - line.p1[1]) > 0


#============================================
def test_multi_atom_label_attach_default_first_when_missing():
	mol_default, _left, _right = _make_two_atom_mol(
		right_symbol="C",
		right_label="CH2OH",
		right_attach_atom=None,
	)
	mol_first, _left_first, _right_first = _make_two_atom_mol(
		right_symbol="C",
		right_label="CH2OH",
		right_attach_atom="first",
	)
	default_ops = molecule_to_ops(mol_default, style={"font_size": 16.0})
	first_ops = molecule_to_ops(mol_first, style={"font_size": 16.0})
	assert _first_line(default_ops).p2 == pytest.approx(_first_line(first_ops).p2)


#============================================
def test_multi_atom_label_attach_element_overrides_attach_atom_first():
	mol, _left, right = _make_two_atom_mol(
		right_symbol="C",
		right_label="CH2OH",
		right_attach_atom="last",
		right_attach_element="C",
	)
	ops = molecule_to_ops(mol, style={"font_size": 16.0})
	line = _first_line(ops)
	assert line.p2 != pytest.approx((right.x, right.y))
	attach_bbox = label_attach_target(
		right.x, right.y, "CH2OH", "start", 16.0,
		attach_atom="last", attach_element="C", font_name="Arial",
	).box
	assert _point_not_inside_bbox(line.p2, attach_bbox)
	assert math.hypot(line.p2[0] - line.p1[0], line.p2[1] - line.p1[1]) > 0


#============================================
def test_malformed_attach_atom_hard_fails_with_clear_error():
	# Legacy malformed CDML should fail fast instead of silently defaulting.
	mol, _left, _right = _make_two_atom_mol(
		right_symbol="C",
		right_label="CH2OH",
		right_attach_atom="frist",
	)
	with pytest.raises(ValueError, match=r"Invalid attach_atom value: 'frist'"):
		molecule_to_ops(mol, style={"font_size": 16.0})
