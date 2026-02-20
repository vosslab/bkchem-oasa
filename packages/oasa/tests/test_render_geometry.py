"""Unit tests for render_geometry gap, alignment, perpendicular, and cross-label helpers."""

# Standard Library
import math

# Third Party
import pytest

# local repo modules
from oasa.render_lib.data_types import AttachConstraints
from oasa.render_lib.data_types import ATTACH_GAP_FONT_FRACTION
from oasa.render_lib.data_types import ATTACH_GAP_TARGET
from oasa.render_lib.data_types import ATTACH_PERP_TOLERANCE
from oasa.render_lib.data_types import BondRenderContext
from oasa.render_lib.data_types import make_attach_constraints
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.data_types import make_circle_target
from oasa.render_lib.data_types import make_composite_target
from oasa.render_lib.attach_resolution import _correct_endpoint_for_alignment
from oasa.render_lib.attach_resolution import _min_distance_point_to_target_boundary
from oasa.render_lib.attach_resolution import _perpendicular_distance_to_line
from oasa.render_lib.attach_resolution import _retreat_to_target_gap
from oasa.render_lib.bond_ops import _avoid_cross_label_overlaps
from oasa.render_lib.bond_ops import _clip_to_target
from oasa.render_lib.bond_ops import _resolve_endpoint_with_constraints
from oasa.render_lib.bond_ops import build_bond_ops


#============================================
# _perpendicular_distance_to_line tests
#============================================

#============================================
def test_perpendicular_distance_point_on_line():
	# point on the line should have distance 0
	dist = _perpendicular_distance_to_line(
		(5.0, 5.0), (0.0, 0.0), (10.0, 10.0),
	)
	assert dist == pytest.approx(0.0, abs=1e-10)


#============================================
def test_perpendicular_distance_horizontal_line():
	# point (3, 5) above horizontal line y=0
	dist = _perpendicular_distance_to_line(
		(3.0, 5.0), (0.0, 0.0), (10.0, 0.0),
	)
	assert dist == pytest.approx(5.0, abs=1e-10)


#============================================
def test_perpendicular_distance_vertical_line():
	# point (7, 3) to the right of vertical line x=0
	dist = _perpendicular_distance_to_line(
		(7.0, 3.0), (0.0, 0.0), (0.0, 10.0),
	)
	assert dist == pytest.approx(7.0, abs=1e-10)


#============================================
def test_perpendicular_distance_diagonal():
	# point (1, 0) to line from (0,0) to (0,1) -- distance is 1
	dist = _perpendicular_distance_to_line(
		(1.0, 0.0), (0.0, 0.0), (0.0, 1.0),
	)
	assert dist == pytest.approx(1.0, abs=1e-10)


#============================================
def test_perpendicular_distance_degenerate_line():
	# degenerate line (start == end) falls back to euclidean distance
	dist = _perpendicular_distance_to_line(
		(3.0, 4.0), (0.0, 0.0), (0.0, 0.0),
	)
	assert dist == pytest.approx(5.0, abs=1e-10)


#============================================
def test_perpendicular_distance_negative_coords():
	# point (-3, 0) to horizontal line y=4 from (-10,4) to (10,4)
	dist = _perpendicular_distance_to_line(
		(-3.0, 0.0), (-10.0, 4.0), (10.0, 4.0),
	)
	assert dist == pytest.approx(4.0, abs=1e-10)


#============================================
def test_perpendicular_distance_45_degree_line():
	# point (0, 1) to 45-degree line from (0,0) to (1,1)
	# perpendicular distance = |0*1 - 1*1 + 0| / sqrt(2) ... using formula
	# cross product: |dy*(px-sx) - dx*(py-sy)| / length
	# = |1*(0-0) - 1*(1-0)| / sqrt(2) = 1/sqrt(2)
	dist = _perpendicular_distance_to_line(
		(0.0, 1.0), (0.0, 0.0), (1.0, 1.0),
	)
	assert dist == pytest.approx(1.0 / math.sqrt(2.0), abs=1e-10)


#============================================
# _retreat_to_target_gap tests
#============================================

#============================================
def test_retreat_zero_gap_returns_endpoint():
	# target_gap=0 should return the endpoint unchanged
	result = _retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), 0.0, [],
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_retreat_negative_gap_returns_endpoint():
	# negative target_gap should return the endpoint unchanged
	result = _retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), -1.0, [],
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_retreat_gap_already_satisfied():
	# endpoint is 5 units from the box boundary, target_gap=2
	# box from (12, -5) to (20, 5), endpoint at (10, 0) -> distance to box = 2
	box = make_box_target((12.0, -5.0, 20.0, 5.0))
	result = _retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), 2.0, [box],
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_retreat_gap_needs_retreat():
	# box from (11, -5) to (20, 5), endpoint at (10, 0) -> distance to box = 1
	# target_gap=3, so need to retreat by 2 units
	box = make_box_target((11.0, -5.0, 20.0, 5.0))
	result = _retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), 3.0, [box],
	)
	# endpoint should move toward start (x < 10) but not past it (x > 0)
	assert result[0] < 10.0, "endpoint should have retreated toward start"
	assert result[0] > 0.0, "endpoint should not retreat past start"
	assert result[1] == pytest.approx(0.0, abs=1e-10)


#============================================
def test_retreat_gap_vertical_direction():
	# vertical bond: start=(5,0), endpoint=(5,10), box at (3,12) to (7,20)
	# distance from (5,10) to box boundary = 2 (y direction)
	# target_gap=4, need to retreat 2 units
	box = make_box_target((3.0, 12.0, 7.0, 20.0))
	result = _retreat_to_target_gap(
		(5.0, 0.0), (5.0, 10.0), 4.0, [box],
	)
	# endpoint should stay on the vertical line (x == 5)
	assert result[0] == pytest.approx(5.0, abs=1e-10)
	# endpoint should move toward start (y < 10) but not past it (y > 0)
	assert result[1] < 10.0, "endpoint should have retreated toward start"
	assert result[1] > 0.0, "endpoint should not retreat past start"


#============================================
def test_retreat_gap_no_forbidden_regions():
	# no forbidden regions: current_gap=0, so retreat by full target_gap
	result = _retreat_to_target_gap(
		(0.0, 0.0), (10.0, 0.0), 2.0, [],
	)
	assert result[0] == pytest.approx(8.0, abs=1e-10)
	assert result[1] == pytest.approx(0.0, abs=1e-10)


#============================================
def test_retreat_gap_excessive_retreat_clamps_to_start():
	# target gap exceeds bond length -- should clamp to line_start
	box = make_box_target((3.0, -1.0, 5.0, 1.0))
	result = _retreat_to_target_gap(
		(0.0, 0.0), (2.0, 0.0), 100.0, [box],
	)
	assert result == pytest.approx((0.0, 0.0), abs=1e-10)


#============================================
def test_retreat_gap_degenerate_zero_length():
	# start == endpoint: should return endpoint unchanged
	result = _retreat_to_target_gap(
		(5.0, 5.0), (5.0, 5.0), 1.0, [],
	)
	assert result == pytest.approx((5.0, 5.0), abs=1e-10)


#============================================
def test_retreat_gap_diagonal_approach_converges():
	# bond approaches a box corner at ~45 degrees; single-pass retreat
	# under-corrects because retreat distance != perpendicular gap.
	# The iterative loop should converge to the target gap.
	# box from (10, 10) to (20, 20), bond from (0, 0) toward (10, 10)
	box = make_box_target((10.0, 10.0, 20.0, 20.0))
	target_gap = 3.0
	# start endpoint just outside the box corner at 45 degrees
	# distance from (9, 9) to box corner (10,10) = sqrt(2) ~ 1.414
	start = (0.0, 0.0)
	endpoint = (9.0, 9.0)
	result = _retreat_to_target_gap(
		start, endpoint, target_gap, [box],
	)
	# verify the achieved gap meets the target
	achieved_gap = _min_distance_point_to_target_boundary(
		result, box,
	)
	assert achieved_gap >= target_gap - 0.01, (
		f"achieved gap {achieved_gap:.4f} should be >= target {target_gap} - 0.01"
	)
	# verify endpoint stayed on the 45-degree line (x == y)
	assert result[0] == pytest.approx(result[1], abs=1e-6)
	# verify endpoint moved toward start
	assert result[0] < 9.0, "endpoint should have retreated"
	assert result[0] > 0.0, "endpoint should not retreat past start"


#============================================
# _correct_endpoint_for_alignment tests
#============================================

#============================================
def test_correct_alignment_already_aligned():
	# bond from (0,0) to (10,0), alignment center at (10,0) -- on the line
	box = make_box_target((8.0, -2.0, 12.0, 2.0))
	result = _correct_endpoint_for_alignment(
		(0.0, 0.0), (10.0, 0.0), (10.0, 0.0), box, 0.5,
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_correct_alignment_within_tolerance():
	# bond from (0,0) to (10,0), alignment center at (10, 0.1) -- within tolerance
	box = make_box_target((8.0, -2.0, 12.0, 2.0))
	result = _correct_endpoint_for_alignment(
		(0.0, 0.0), (10.0, 0.0), (10.0, 0.1), box, 0.5,
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_correct_alignment_off_axis_corrects():
	# bond from (0,0) to (10,0), alignment center at (10, 5) -- off axis
	# correction should redirect toward alignment center and hit box boundary
	box = make_box_target((8.0, -2.0, 12.0, 8.0))
	result = _correct_endpoint_for_alignment(
		(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), box, 0.5,
	)
	# the corrected endpoint should be on the box boundary
	# and the line from (0,0) through result should pass closer to (10,5)
	assert result != pytest.approx((10.0, 0.0), abs=1e-2)
	# verify the correction moved the endpoint
	perp = _perpendicular_distance_to_line(
		(10.0, 5.0), (0.0, 0.0), result,
	)
	# the corrected line should pass much closer to alignment center
	assert perp < 1.0


#============================================
def test_correct_alignment_circle_target():
	# bond from (0,0) to (10,0), alignment center at (10, 3)
	# circle target centered at (10,3) radius 2
	circle = make_circle_target((10.0, 3.0), 2.0)
	result = _correct_endpoint_for_alignment(
		(0.0, 0.0), (10.0, 0.0), (10.0, 3.0), circle, 0.5,
	)
	# should correct to point toward the circle center
	assert result != pytest.approx((10.0, 0.0), abs=1e-2)
	# result should be on or near the circle boundary
	dx = result[0] - 10.0
	dy = result[1] - 3.0
	dist_from_center = math.hypot(dx, dy)
	assert dist_from_center == pytest.approx(2.0, abs=0.5)


#============================================
def test_correct_alignment_coincident_start_center():
	# bond_start == alignment_center: should return endpoint unchanged
	box = make_box_target((8.0, -2.0, 12.0, 2.0))
	result = _correct_endpoint_for_alignment(
		(10.0, 0.0), (10.0, 0.0), (10.0, 0.0), box, 0.5,
	)
	assert result == pytest.approx((10.0, 0.0), abs=1e-10)


#============================================
def test_composite_alignment_picks_best_perp():
	"""Two children both produce corrections; the one with lower perp error wins."""
	bond_start = (0.0, 0.0)
	endpoint = (10.0, 0.0)
	alignment_center = (9.0, 2.0)
	tolerance = 0.01

	circle_target = make_circle_target((10.0, 3.0), 2.0)
	box_target = make_box_target((7.0, 0.0, 11.0, 4.0))

	# circle-only result for comparison
	circle_result = _correct_endpoint_for_alignment(
		bond_start, endpoint, alignment_center, circle_target, tolerance,
	)

	# composite: circle first, box second
	composite = make_composite_target([circle_target, box_target])
	result = _correct_endpoint_for_alignment(
		bond_start, endpoint, alignment_center, composite, tolerance,
	)

	# result should have lower or equal perp error compared to circle-only
	result_perp = _perpendicular_distance_to_line(
		alignment_center, bond_start, result,
	)
	circle_perp = _perpendicular_distance_to_line(
		alignment_center, bond_start, circle_result,
	)
	assert result_perp <= circle_perp


#============================================
def test_composite_alignment_already_aligned():
	"""Alignment center on bond line -- endpoint returned unchanged with composite."""
	bond_start = (0.0, 5.0)
	endpoint = (7.0, 5.0)
	alignment_center = (8.0, 5.0)
	tolerance = 0.07

	circle_target = make_circle_target((8.0, 5.0), 1.5)
	box_target = make_box_target((6.0, 3.5, 9.0, 6.5))
	composite = make_composite_target([circle_target, box_target])

	result = _correct_endpoint_for_alignment(
		bond_start, endpoint, alignment_center, composite, tolerance,
	)
	assert result == pytest.approx(endpoint)


#============================================
def test_composite_alignment_single_child_match():
	"""Only one child produces a correction; that single candidate is used."""
	bond_start = (0.0, 0.0)
	endpoint = (10.0, 0.0)
	alignment_center = (9.0, 2.0)
	tolerance = 0.01

	# box far away -- no intersection with centerline, returns endpoint unchanged
	far_box = make_box_target((50.0, 50.0, 55.0, 55.0))
	# circle near alignment_center -- produces valid correction
	near_circle = make_circle_target((10.0, 3.0), 2.0)

	# circle-only result for comparison
	circle_result = _correct_endpoint_for_alignment(
		bond_start, endpoint, alignment_center, near_circle, tolerance,
	)

	composite = make_composite_target([far_box, near_circle])
	result = _correct_endpoint_for_alignment(
		bond_start, endpoint, alignment_center, composite, tolerance,
	)
	assert result == pytest.approx(circle_result)


#============================================
def test_composite_alignment_no_children_match():
	"""Composite where no child produces a changed endpoint -- returns unchanged."""
	bond_start = (0.0, 0.0)
	endpoint = (10.0, 0.0)
	alignment_center = (9.0, 2.0)
	tolerance = 0.01

	# both circles far away -- centerline misses both, so no intersection
	far_circle1 = make_circle_target((50.0, 50.0), 1.0)
	far_circle2 = make_circle_target((-40.0, 30.0), 0.5)

	composite = make_composite_target([far_circle1, far_circle2])
	result = _correct_endpoint_for_alignment(
		bond_start, endpoint, alignment_center, composite, tolerance,
	)
	assert result == endpoint


#============================================
# _avoid_cross_label_overlaps tests
#============================================

class _FakeVertex:
	"""Minimal vertex stand-in for dict-key identity in label_targets."""
	def __init__(self, name):
		self.name = name
	def __repr__(self):
		return f"_FakeVertex({self.name!r})"


#============================================
def test_cross_label_no_cross_targets():
	# only own-vertex targets present -- endpoints unchanged
	v1 = _FakeVertex("A")
	v2 = _FakeVertex("B")
	box_a = make_box_target((0.0, -2.0, 2.0, 2.0))
	label_targets = {v1: box_a}
	result = _avoid_cross_label_overlaps(
		(0.0, 0.0), (20.0, 0.0), half_width=0.5,
		own_vertices={v1, v2}, label_targets=label_targets,
	)
	assert result[0] == pytest.approx((0.0, 0.0), abs=1e-10)
	assert result[1] == pytest.approx((20.0, 0.0), abs=1e-10)


#============================================
def test_cross_label_own_target_excluded():
	# own vertex's box sits on the bond path but must be ignored
	v1 = _FakeVertex("A")
	v2 = _FakeVertex("B")
	box_on_path = make_box_target((8.0, -2.0, 12.0, 2.0))
	label_targets = {v1: box_on_path}
	result = _avoid_cross_label_overlaps(
		(0.0, 0.0), (20.0, 0.0), half_width=0.5,
		own_vertices={v1, v2}, label_targets=label_targets,
	)
	assert result[0] == pytest.approx((0.0, 0.0), abs=1e-10)
	assert result[1] == pytest.approx((20.0, 0.0), abs=1e-10)


#============================================
def test_cross_label_near_end_retreats_end():
	# cross-label box near the end of a horizontal bond
	v1 = _FakeVertex("A")
	v2 = _FakeVertex("B")
	v3 = _FakeVertex("C")
	box_c = make_box_target((16.0, -3.0, 22.0, 3.0))
	label_targets = {v1: make_box_target((-2.0, -1.0, 0.0, 1.0)),
		v3: box_c}
	result = _avoid_cross_label_overlaps(
		(0.0, 0.0), (20.0, 0.0), half_width=0.5,
		own_vertices={v1, v2}, label_targets=label_targets,
	)
	# end should retreat; start should stay
	assert result[0] == pytest.approx((0.0, 0.0), abs=1e-10)
	assert result[1][0] < 17.0  # retreated before the box


#============================================
def test_cross_label_near_start_retreats_start():
	# cross-label box near the start of a horizontal bond
	v1 = _FakeVertex("A")
	v2 = _FakeVertex("B")
	v3 = _FakeVertex("C")
	box_c = make_box_target((-2.0, -3.0, 4.0, 3.0))
	label_targets = {v3: box_c}
	result = _avoid_cross_label_overlaps(
		(0.0, 0.0), (20.0, 0.0), half_width=0.5,
		own_vertices={v1, v2}, label_targets=label_targets,
	)
	# start should retreat toward end; end stays
	assert result[0][0] > 3.0  # retreated past the box
	assert result[1] == pytest.approx((20.0, 0.0), abs=1e-10)


#============================================
def test_cross_label_no_intersection():
	# cross-label box far from bond path -- no retreat
	v1 = _FakeVertex("A")
	v2 = _FakeVertex("B")
	v3 = _FakeVertex("C")
	box_c = make_box_target((50.0, 50.0, 60.0, 60.0))
	label_targets = {v3: box_c}
	result = _avoid_cross_label_overlaps(
		(0.0, 0.0), (20.0, 0.0), half_width=0.5,
		own_vertices={v1, v2}, label_targets=label_targets,
	)
	assert result[0] == pytest.approx((0.0, 0.0), abs=1e-10)
	assert result[1] == pytest.approx((20.0, 0.0), abs=1e-10)


#============================================
def test_cross_label_min_length_guard():
	# short bond with cross-label on path -- should not collapse below min length
	v1 = _FakeVertex("A")
	v2 = _FakeVertex("B")
	v3 = _FakeVertex("C")
	half_width = 0.5
	# bond only 3 units long, box covers the whole path
	box_c = make_box_target((-1.0, -3.0, 4.0, 3.0))
	label_targets = {v3: box_c}
	result = _avoid_cross_label_overlaps(
		(0.0, 0.0), (3.0, 0.0), half_width=half_width,
		own_vertices={v1, v2}, label_targets=label_targets,
	)
	# min_length = max(half_width * 4.0, 1.0) = 2.0
	# bond is 3.0 which is >= min_length, but after retreat it should not go below 2.0
	result_length = math.hypot(result[1][0] - result[0][0], result[1][1] - result[0][1])
	assert result_length >= 2.0 - 1e-6


#============================================
# shared spec constants and constraints (Phase 1) tests
#============================================

#============================================
def test_attach_constraints_default_alignment_tolerance():
	"""Default AttachConstraints should use ATTACH_PERP_TOLERANCE."""
	constraints = AttachConstraints()
	assert constraints.alignment_tolerance == ATTACH_PERP_TOLERANCE
	assert constraints.alignment_tolerance == 0.07


#============================================
def test_attach_constraints_custom_alignment_tolerance():
	"""AttachConstraints should accept a custom alignment_tolerance."""
	constraints = AttachConstraints(alignment_tolerance=0.5)
	assert constraints.alignment_tolerance == 0.5


#============================================
def test_alignment_correction_uses_constraints_tolerance():
	"""_correct_endpoint_for_alignment behavior changes with tolerance."""
	# bond from (0,0) to (10,0), alignment center at (10, 0.5)
	# perp distance from (10, 0.5) to the line y=0 is 0.5
	box = make_box_target((8.0, -2.0, 12.0, 2.0))
	bond_start = (0.0, 0.0)
	endpoint = (10.0, 0.0)
	alignment_center = (10.0, 0.5)
	# loose tolerance (1.0 > 0.5): no correction needed
	ep_loose = _correct_endpoint_for_alignment(
		bond_start, endpoint, alignment_center, box, 1.0,
	)
	assert ep_loose == pytest.approx(endpoint, abs=1e-10)
	# tight tolerance (0.1 < 0.5): correction fires
	ep_tight = _correct_endpoint_for_alignment(
		bond_start, endpoint, alignment_center, box, 0.1,
	)
	assert ep_tight != pytest.approx(endpoint, abs=1e-2)
	# the corrected endpoint should aim closer to alignment center
	perp_after = _perpendicular_distance_to_line(
		alignment_center, bond_start, ep_tight,
	)
	assert perp_after < 0.5


#============================================
def test_no_hardcoded_tolerance_fallback():
	"""Default alignment_tolerance uses the module constant ATTACH_PERP_TOLERANCE,
	not the old max(line_width * 0.5, 0.25) expression."""
	constraints = AttachConstraints(line_width=2.0)
	# alignment_tolerance should equal the module-level constant
	assert constraints.alignment_tolerance == pytest.approx(
		ATTACH_PERP_TOLERANCE
	)
	# and it should NOT be the old line-width-derived formula
	assert constraints.alignment_tolerance != max(2.0 * 0.5, 0.25)


#============================================
# make_attach_constraints factory tests (Phase 5)
#============================================

#============================================
def test_make_attach_constraints_default_absolute_gap():
	"""No args returns ATTACH_GAP_TARGET as the gap."""
	constraints = make_attach_constraints()
	assert constraints.target_gap == ATTACH_GAP_TARGET
	assert constraints.alignment_tolerance == ATTACH_PERP_TOLERANCE


#============================================
def test_make_attach_constraints_font_relative_gap():
	"""font_size arg computes font-relative gap via ATTACH_GAP_FONT_FRACTION."""
	constraints = make_attach_constraints(font_size=12.0)
	expected_gap = 12.0 * ATTACH_GAP_FONT_FRACTION
	assert constraints.target_gap == pytest.approx(expected_gap)


#============================================
def test_make_attach_constraints_explicit_gap_overrides_font():
	"""Explicit target_gap takes priority over font_size."""
	constraints = make_attach_constraints(
		font_size=12.0, target_gap=5.0,
	)
	assert constraints.target_gap == 5.0


#============================================
def test_make_attach_constraints_passthrough_fields():
	"""All fields are forwarded correctly to AttachConstraints."""
	center = (1.0, 2.0)
	constraints = make_attach_constraints(
		line_width=2.5,
		clearance=0.3,
		vertical_lock=True,
		direction_policy="line",
		alignment_center=center,
		alignment_tolerance=0.5,
	)
	assert constraints.line_width == 2.5
	assert constraints.clearance == 0.3
	assert constraints.vertical_lock is True
	assert constraints.direction_policy == "line"
	assert constraints.alignment_center == center
	assert constraints.alignment_tolerance == 0.5


#============================================
def test_make_attach_constraints_matches_haworth_gap():
	"""Haworth calling convention: explicit target_gap overrides font-relative gap."""
	# Haworth renderer now passes target_gap=ATTACH_GAP_TARGET explicitly
	font_size = 12.0
	constraints = make_attach_constraints(
		font_size=font_size, target_gap=ATTACH_GAP_TARGET,
	)
	assert constraints.target_gap == ATTACH_GAP_TARGET


#============================================
# _resolve_endpoint_with_constraints tests (Phase 2)
#============================================

#============================================
def test_resolve_endpoint_none_target():
	"""None target returns bond_start unchanged."""
	result = _resolve_endpoint_with_constraints(
		(5.0, 3.0), None,
	)
	assert result == pytest.approx((5.0, 3.0), abs=1e-10)


#============================================
def test_resolve_endpoint_matches_clip_to_target():
	"""Default constraints produce identical results to _clip_to_target()
	for axis-aligned bonds (direction snapping preserves the angle)."""
	box = make_box_target((8.0, -2.0, 12.0, 2.0))
	cases = [
		((0.0, 0.0), "horizontal"),
		((10.0, -20.0), "vertical"),
	]
	for bond_start, label in cases:
		old = _clip_to_target(bond_start, box)
		new = _resolve_endpoint_with_constraints(bond_start, box)
		assert new == pytest.approx(old, abs=1e-10), f"mismatch for {label} bond"


#============================================
def test_resolve_endpoint_alignment_correction():
	"""Explicit alignment_center triggers centerline correction."""
	box = make_box_target((8.0, -2.0, 12.0, 8.0))
	bond_start = (0.0, 0.0)
	# with alignment_center at (10, 5): endpoint should correct toward (10, 5)
	constraints = AttachConstraints(
		direction_policy="auto",
		alignment_center=(10.0, 5.0),
		alignment_tolerance=0.07,
	)
	ep_corrected = _resolve_endpoint_with_constraints(
		bond_start, box, constraints=constraints,
	)
	# the corrected line should pass closer to (10, 5)
	perp = _perpendicular_distance_to_line(
		(10.0, 5.0), bond_start, ep_corrected,
	)
	assert perp < 1.0


#============================================
def test_resolve_endpoint_gap_retreat():
	"""target_gap > 0 creates a gap between endpoint and target."""
	box = make_box_target((8.0, -2.0, 12.0, 2.0))
	bond_start = (0.0, 0.0)
	constraints = AttachConstraints(
		direction_policy="auto",
		target_gap=2.0,
	)
	ep = _resolve_endpoint_with_constraints(
		bond_start, box, constraints=constraints,
	)
	# endpoint should be further from the box than without gap
	ep_no_gap = _resolve_endpoint_with_constraints(bond_start, box)
	assert ep[0] < ep_no_gap[0]  # retreated toward start (leftward)


#============================================
def test_resolve_endpoint_legality_retreat():
	"""Endpoint inside target gets retreated out with nonzero line_width."""
	# box covers the endpoint area; with line_width > 0 the stroke footprint
	# extends inside the box, triggering legality retreat.
	box = make_box_target((7.0, -3.0, 13.0, 3.0))
	bond_start = (0.0, 0.0)
	ep_thin = _resolve_endpoint_with_constraints(
		bond_start, box, line_width=0.0,
	)
	ep_wide = _resolve_endpoint_with_constraints(
		bond_start, box, line_width=4.0,
	)
	# wider line should retreat more (or at least not advance)
	assert ep_wide[0] <= ep_thin[0] + 1e-10


#============================================
def test_build_bond_ops_triple_clips_offsets():
	"""Triple bond offset lines respect label targets."""
	v1 = _FakeVertex("A")
	v2 = _FakeVertex("B")
	box_b = make_box_target((18.0, -3.0, 24.0, 3.0))

	class FakeEdge:
		order = 3
		type = 'n'
		vertices = (v1, v2)
		properties_ = {}

	context = BondRenderContext(
		molecule=None,
		line_width=1.0,
		bond_width=3.0,
		wedge_width=4.0,
		bold_line_width_multiplier=1.0,
		bond_second_line_shortening=0.0,
		label_targets={v2: box_b},
	)
	ops = build_bond_ops(
		FakeEdge(), (0.0, 0.0), (20.0, 0.0), context,
	)
	# should have 3 line ops (center + 2 offsets)
	from oasa import render_ops
	line_ops = [op for op in ops if isinstance(op, render_ops.LineOp)]
	assert len(line_ops) == 3
	# offset lines (indices 1 and 2) should have their v2-end clipped
	# (p2[0] should be < 20.0 because of the label box)
	for op in line_ops[1:]:
		x2 = op.p2[0]
		assert x2 < 20.0, f"offset line end {x2} not clipped by label target"
