"""Focused geometry coverage for native adder, dashed, and dotted bonds."""

# Standard Library
import itertools
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.bond_lib
import oasa.cdml_bond_io
import oasa.render_ops
from oasa.render_lib.bond_ops import _apply_bond_length_policy
from oasa.render_lib.bond_ops import build_bond_ops
from oasa.render_lib.data_types import BondRenderContext


#============================================
class _Atom:
	"""Small edge endpoint with the geometry fields used by bond rendering."""

	def __init__(self) -> None:
		self.neighbors = []
		self.symbol = "C"


#============================================
def _bond(
		bond_type: str, order: int = 1, center: bool | None = None,
		simple_double: bool = True, double_ratio: float = 0.75,
		equithick: bool = False,
		) -> oasa.bond_lib.Bond:
	"""Build one positioned render edge with explicit depiction choices."""
	edge = oasa.bond_lib.Bond(order=order, type=bond_type)
	edge.vertices = (_Atom(), _Atom())
	edge.center = center
	edge.simple_double = int(simple_double)
	edge.double_length_ratio = double_ratio
	edge.equithick = int(equithick)
	return edge


#============================================
def _context() -> BondRenderContext:
	"""Return stable display metrics for direct bond-op geometry tests."""
	return BondRenderContext(
		molecule=None,
		line_width=2.0,
		bond_width=6.0,
		wedge_width=10.0,
		bold_line_width_multiplier=1.2,
	)


#============================================
def _segment_length(start: tuple[float, float], end: tuple[float, float]) -> float:
	"""Return Euclidean length for one render-op segment."""
	return math.hypot(end[0] - start[0], end[1] - start[1])


#============================================
def _path_baseline(path: oasa.render_ops.PathOp) -> tuple[float, float, float]:
	"""Return start y, end y, and endpoint length for an adder path."""
	start = path.commands[0][1]
	end = path.commands[-1][1]
	return start[1], end[1], _segment_length(start, end)


#============================================
def _operation_lane_y(operation: object) -> float:
	"""Return the horizontal baseline shared by one horizontal render operation."""
	if isinstance(operation, oasa.render_ops.PathOp):
		return operation.commands[0][1][1]
	if isinstance(operation, oasa.render_ops.LineOp):
		return operation.p1[1]
	if isinstance(operation, oasa.render_ops.CircleOp):
		return operation.center[1]
	raise TypeError(f"Unexpected styled operation: {operation!r}")


#============================================
def _styled_lanes(operations: list[object]) -> list[tuple[float, list[object]]]:
	"""Group horizontal primitives by lane without depending on their density."""
	lanes: list[tuple[float, list[object]]] = []
	for operation in sorted(operations, key=_operation_lane_y):
		lane_y = _operation_lane_y(operation)
		if lanes and math.isclose(lane_y, lanes[-1][0], abs_tol=1e-6):
			lanes[-1][1].append(operation)
		else:
			lanes.append((lane_y, [operation]))
	return lanes


#============================================
def _lane_is_styled(lane: list[object], bond_type: str) -> bool:
	"""Recognize style semantics without fixing dash or dot tessellation."""
	if bond_type == "a":
		return all(isinstance(operation, oasa.render_ops.PathOp) for operation in lane)
	if bond_type == "o":
		return all(isinstance(operation, oasa.render_ops.CircleOp) for operation in lane)
	segments = sorted(
		(operation for operation in lane if isinstance(operation, oasa.render_ops.LineOp)),
		key=lambda operation: operation.p1[0],
	)
	return any(
		following.p1[0] > previous.p2[0]
		for previous, following in zip(segments, segments[1:])
	)


#============================================
def _assert_styled_lane_matrix(
		lanes: list[tuple[float, list[object]]], bond_type: str, order: int,
		center: bool, simple_double: bool,
		) -> None:
	"""Verify semantic lane placement and style selection for one depiction."""
	assert len(lanes) == order
	if order == 1:
		assert lanes[0][0] == pytest.approx(0.0)
		assert _lane_is_styled(lanes[0][1], bond_type)
		return
	if order == 2 and center:
		assert lanes[0][0] == pytest.approx(-lanes[1][0])
		assert all(_lane_is_styled(lane, bond_type) for _y, lane in lanes)
		return
	axis = next((lane for lane in lanes if math.isclose(lane[0], 0.0, abs_tol=1e-6)))
	outer_lanes = [lane for lane in lanes if lane is not axis]
	assert _lane_is_styled(axis[1], bond_type)
	if order == 2:
		assert len(outer_lanes) == 1 and outer_lanes[0][0] != pytest.approx(0.0)
		assert _lane_is_styled(outer_lanes[0][1], bond_type) is not simple_double
		return
	assert outer_lanes[0][0] == pytest.approx(-outer_lanes[1][0])
	assert all(_lane_is_styled(lane, bond_type) is not simple_double
		for _y, lane in outer_lanes)


#============================================
@pytest.mark.parametrize(
	("bond_type", "primitive"),
	(
		("a", oasa.render_ops.PathOp),
		("d", oasa.render_ops.LineOp),
		("o", oasa.render_ops.CircleOp),
	),
)
def test_native_styled_single_bonds_emit_their_own_primitives(
		bond_type: str, primitive: type,
		) -> None:
	"""Each selected style reaches a native non-placeholder primitive family."""
	ops = build_bond_ops(
		_bond(bond_type), (0.0, 0.0), (24.0, 0.0), _context(),
	)
	assert ops
	if bond_type == "d":
		assert _lane_is_styled(ops, bond_type)
	else:
		assert all(isinstance(op, primitive) for op in ops)


#============================================
@pytest.mark.parametrize(
	("bond_type", "order", "center", "simple_double"),
	tuple(itertools.product(
		("a", "d", "o"), (1, 2, 3), (False, True), (False, True),
	)),
)
def test_styled_lane_style_and_placement_matrix(
		bond_type: str, order: int, center: bool, simple_double: bool,
		) -> None:
	"""Every a/d/o order uses the shared centered and simple-double lane rules."""
	ops = build_bond_ops(
		_bond(bond_type, order, center, simple_double),
		(0.0, 0.0), (20.0, 0.0), _context(),
	)
	_assert_styled_lane_matrix(
		_styled_lanes(ops), bond_type, order, center, simple_double,
	)


#============================================
def test_double_ratio_shortens_only_the_added_uncentered_lane() -> None:
	"""The styled axis remains full while its added plain lane is centered."""
	ops = build_bond_ops(
		_bond("a", 2, False, True, double_ratio=0.5),
		(0.0, 0.0), (20.0, 0.0), _context(),
	)
	path = next(op for op in ops if isinstance(op, oasa.render_ops.PathOp))
	line = next(op for op in ops if isinstance(op, oasa.render_ops.LineOp))
	axis_length = _path_baseline(path)[2]
	assert _segment_length(line.p1, line.p2) == pytest.approx(axis_length * 0.5)
	assert (line.p1[0] + line.p2[0]) / 2.0 == pytest.approx(axis_length / 2.0)


#============================================
def test_centered_double_ignores_ratio_and_keeps_full_styled_lanes() -> None:
	"""Centered doubles have equal full-length styled flanking lanes."""
	ops = build_bond_ops(
		_bond("a", 2, True, True, double_ratio=0.25),
		(0.0, 0.0), (20.0, 0.0), _context(),
	)
	lengths = [_path_baseline(op)[2] for op in ops]
	assert lengths[0] == pytest.approx(lengths[1])
	assert all(length > 0.0 for length in lengths)


#============================================
def test_adder_equithick_selects_constant_instead_of_tapered_amplitude() -> None:
	"""Adder amplitude grows from the tip unless equal thickness is selected."""
	tapered = build_bond_ops(
		_bond("a", equithick=False), (0.0, 0.0), (24.0, 0.0), _context(),
	)[0]
	constant = build_bond_ops(
		_bond("a", equithick=True), (0.0, 0.0), (24.0, 0.0), _context(),
	)[0]
	tapered_amplitudes = [abs(command[1][1]) for command in tapered.commands[1:-1]]
	constant_amplitudes = [abs(command[1][1]) for command in constant.commands[1:-1]]
	assert tapered_amplitudes[0] < tapered_amplitudes[-1]
	assert constant_amplitudes == pytest.approx([constant_amplitudes[0]] * len(constant_amplitudes))


#============================================
@pytest.mark.parametrize("bond_type", ("d", "o"))
def test_equithick_does_not_change_dash_or_dot_geometry(bond_type: str) -> None:
	"""The adder-only thickness choice is inert for dash and dot families."""
	regular = build_bond_ops(
		_bond(bond_type, 3, simple_double=False, equithick=False),
		(0.0, 0.0), (24.0, 0.0), _context(),
	)
	equithick = build_bond_ops(
		_bond(bond_type, 3, simple_double=False, equithick=True),
		(0.0, 0.0), (24.0, 0.0), _context(),
	)
	assert regular == equithick


#============================================
@pytest.mark.parametrize("bond_type", ("a", "d", "o"))
@pytest.mark.parametrize("order", (1, 2, 3))
def test_zero_length_styled_bonds_are_empty(bond_type: str, order: int) -> None:
	"""Coincident normalized endpoints never create a primitive artifact."""
	ops = build_bond_ops(
		_bond(bond_type, order), (4.0, 5.0), (4.0, 5.0), _context(),
	)
	assert ops == []


#============================================
@pytest.mark.parametrize("order", (1, 2, 3))
def test_dashed_and_normal_orders_share_endpoint_length_policy(order: int) -> None:
	"""Ordinary dashed chemistry uses the matching normal order profile."""
	normal = _apply_bond_length_policy(
		_bond("n", order), (0.0, 0.0), (10.0, 0.0),
	)
	dashed = _apply_bond_length_policy(
		_bond("d", order), (0.0, 0.0), (10.0, 0.0),
	)
	normal_length = _segment_length(normal[0], normal[1])
	dashed_length = _segment_length(dashed[0], dashed[1])
	assert dashed_length == pytest.approx(normal_length)


#============================================
def test_absent_simple_double_resolves_to_one_without_explicit_presence() -> None:
	"""The effective default remains separate from lexical attribute presence."""
	edge = _bond("d", 2)
	del edge.simple_double
	oasa.cdml_bond_io.set_cdml_bond_explicit_fields(edge, set())
	depiction = oasa.cdml_bond_io.resolve_bond_depiction(edge)
	assert depiction.simple_double is True
	assert "simple_double" not in depiction.explicit_fields
