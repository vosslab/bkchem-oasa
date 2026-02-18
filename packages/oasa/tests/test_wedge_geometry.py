"""Tests for rounded wedge geometry helpers."""

# Standard Library
import math

import pytest

# local repo modules
from oasa import wedge_geometry


#============================================
def test_horizontal_wedge_corners():
	tip = (0.0, 0.0)
	base = (10.0, 0.0)
	geom = wedge_geometry.rounded_wedge_geometry(tip, base, 4.0, 0.0)
	# narrow end is near tip_point
	assert math.hypot(geom["narrow_left"][0] - tip[0], geom["narrow_left"][1] - tip[1]) < 1.0
	assert math.hypot(geom["narrow_right"][0] - tip[0], geom["narrow_right"][1] - tip[1]) < 1.0
	# wide end is near base_point
	assert math.hypot(geom["wide_left"][0] - base[0], geom["wide_left"][1] - base[1]) < 5.0
	assert math.hypot(geom["wide_right"][0] - base[0], geom["wide_right"][1] - base[1]) < 5.0
	# wide end is wider than narrow end
	narrow_width = math.hypot(geom["narrow_right"][0] - geom["narrow_left"][0], geom["narrow_right"][1] - geom["narrow_left"][1])
	wide_width = math.hypot(geom["wide_right"][0] - geom["wide_left"][0], geom["wide_right"][1] - geom["wide_left"][1])
	assert wide_width > narrow_width
	# corner_radius > 0 and path_commands non-empty
	assert geom["corner_radius"] > 0
	assert len(geom["path_commands"]) > 0


#============================================
def test_vertical_wedge_corners():
	tip = (0.0, 0.0)
	base = (0.0, 10.0)
	geom = wedge_geometry.rounded_wedge_geometry(tip, base, 4.0, 0.0)
	# narrow end is near tip_point
	assert math.hypot(geom["narrow_left"][0] - tip[0], geom["narrow_left"][1] - tip[1]) < 1.0
	assert math.hypot(geom["narrow_right"][0] - tip[0], geom["narrow_right"][1] - tip[1]) < 1.0
	# wide end is near base_point
	assert math.hypot(geom["wide_left"][0] - base[0], geom["wide_left"][1] - base[1]) < 5.0
	assert math.hypot(geom["wide_right"][0] - base[0], geom["wide_right"][1] - base[1]) < 5.0
	# wide end is wider than narrow end
	narrow_width = math.hypot(geom["narrow_right"][0] - geom["narrow_left"][0], geom["narrow_right"][1] - geom["narrow_left"][1])
	wide_width = math.hypot(geom["wide_right"][0] - geom["wide_left"][0], geom["wide_right"][1] - geom["wide_left"][1])
	assert wide_width > narrow_width
	# corner_radius > 0 and path_commands non-empty
	assert geom["corner_radius"] > 0
	assert len(geom["path_commands"]) > 0


#============================================
def test_wedge_area_invariance():
	length = 10.0
	narrow_width = 0.0
	wide_width = 4.0
	expected = wedge_geometry._compute_wedge_area(length, narrow_width, wide_width)
	for angle in (0, 45, 90, 135, 180, 225, 270, 315):
		rad = math.radians(angle)
		base = (length * math.cos(rad), length * math.sin(rad))
		geom = wedge_geometry.rounded_wedge_geometry((0.0, 0.0), base, wide_width, narrow_width)
		assert geom["area"] == pytest.approx(expected, rel=1e-6)


#============================================
def test_wedge_path_commands():
	geom = wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (10.0, 0.0), 4.0, 0.0)
	commands = geom["path_commands"]
	assert commands[0][0] == "M"
	assert commands[1][0] == "L"
	assert commands[2][0] == "ARC"
	assert commands[-1][0] == "Z"
	assert sum(1 for cmd, _payload in commands if cmd == "ARC") == 2


#============================================
def test_wedge_path_without_rounding():
	geom = wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (10.0, 0.0), 4.0, 0.0, corner_radius=0.0)
	commands = geom["path_commands"]
	assert sum(1 for cmd, _payload in commands if cmd == "ARC") == 0


#============================================
def test_wedge_input_validation():
	with pytest.raises(ValueError):
		wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (0.0, 0.0), 4.0, 0.0)
	with pytest.raises(ValueError):
		wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (1.0, 0.0), 0.0, 0.0)
	with pytest.raises(ValueError):
		wedge_geometry.rounded_wedge_geometry((0.0, 0.0), (1.0, 0.0), 4.0, -1.0)
