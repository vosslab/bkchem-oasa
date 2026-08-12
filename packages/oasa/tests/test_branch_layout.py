"""Behavior tests for frame-relative branch fan geometry."""

# Standard Library
import math

# local repo modules
from oasa.render_lib.branch_layout import branch_fan_layout


#============================================
def test_branch_fan_preserves_supplied_arm_lengths() -> None:
	"""The reusable fan keeps each caller-authored arm distance."""
	points = branch_fan_layout(
		origin=(0.0, 0.0),
		stem_unit=(1.0, 0.0),
		branch_angles=(60.0, -60.0),
		lengths=(10.0, 14.0),
		reflection_options=(1,),
		collision_score=lambda candidate: 0.0,
	)
	distances = tuple(math.hypot(point[0], point[1]) for point in points)
	assert distances == (10.0, 14.0)


#============================================
def test_branch_fan_selects_the_caller_safe_reflection() -> None:
	"""Reflection choice follows only the supplied geometry score."""
	points = branch_fan_layout(
		origin=(0.0, 0.0),
		stem_unit=(1.0, 0.0),
		branch_angles=(45.0,),
		lengths=(10.0,),
		reflection_options=(-1, 1),
		collision_score=lambda candidate: 1.0 if candidate[0][1] > 0.0 else 0.0,
	)
	assert points[0][1] < 0.0


#============================================
def test_branch_fan_selects_a_clearer_caller_length_candidate() -> None:
	"""A generic score can select finite arm scales without semantic knowledge."""
	points = branch_fan_layout(
		origin=(0.0, 0.0),
		stem_unit=(1.0, 0.0),
		branch_angles=(0.0, 90.0),
		lengths=(10.0, 10.0),
		reflection_options=(1,),
		collision_score=lambda candidate: abs(candidate[1][1] - 14.0),
		length_scale_options=((1.0, 1.0), (1.0, 1.4)),
	)
	assert abs(points[1][0]) < 1e-12
	assert points[1][1] == 14.0
