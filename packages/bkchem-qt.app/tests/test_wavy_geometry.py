"""Focused contracts for bounded Qt-free Wavy geometry."""

# Standard Library
import fractions
import numbers

# PIP3 modules
import pytest

# local repo modules
import bkchem_qt.wavy_geometry


#============================================
def test_wavy_points_retain_exact_endpoints() -> None:
	"""Normal geometry preserves its completed gesture endpoints."""
	points = bkchem_qt.wavy_geometry.wavy_points((0, 0), (24, 0))

	assert (points[0], points[-1]) == ((0.0, 0.0), (24.0, 0.0))


#============================================
def test_wavy_points_alternate_along_the_drag_normal() -> None:
	"""A short horizontal gesture has the expected first zigzag offset."""
	points = bkchem_qt.wavy_geometry.wavy_points((0, 0), (24, 0))

	assert points[1] == (12.0, 4.0)


#============================================
def test_wavy_points_zero_length_is_a_no_op() -> None:
	"""An unchanged finite gesture creates no persistent geometry."""
	points = bkchem_qt.wavy_geometry.wavy_points((2, 3), (2, 3))

	assert points == ()


#============================================
@pytest.mark.parametrize("start, end", [
	((0, 0), (float("nan"), 0)),
	((0, 0), (True, 0)),
	((0, 0), [1, 2]),
	((0, 0), (fractions.Fraction(10 ** 1000), 0)),
	((-1e308, 0), (1e308, 0)),
	((0, 0), (49159, 0)),
])
def test_wavy_points_reject_invalid_or_unbounded_geometry(
		start: tuple[numbers.Real, numbers.Real],
		end: tuple[numbers.Real, numbers.Real] | list[numbers.Real],
		) -> None:
	"""Malformed, nonfinite, extreme, and oversized inputs fail before output."""
	with pytest.raises(ValueError):
		bkchem_qt.wavy_geometry.wavy_points(start, end)
