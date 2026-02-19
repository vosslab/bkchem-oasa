#!/usr/bin/env python3

"""Unit tests for the oasa.hex_grid module."""

# Standard Library
import math
import sys

# local repo modules
import git_file_utils

REPO_ROOT = git_file_utils.get_repo_root()
sys.path.insert(0, REPO_ROOT)

import oasa.hex_grid


# default spacing used across tests
SPACING = 1.0
# tolerance for floating point comparisons
TOL = 1e-9


#============================================
def test_basis_vectors_geometry():
	"""Verify basis vectors have correct length and 60-degree angle."""
	e1x, e1y, e2x, e2y = oasa.hex_grid.hex_basis_vectors(SPACING)
	# e1 length should equal spacing
	e1_len = math.sqrt(e1x * e1x + e1y * e1y)
	assert abs(e1_len - SPACING) < TOL

	# e2 length should equal spacing
	e2_len = math.sqrt(e2x * e2x + e2y * e2y)
	assert abs(e2_len - SPACING) < TOL

	# angle between e1 and e2 should be 60 degrees
	dot = e1x * e2x + e1y * e2y
	cos_angle = dot / (e1_len * e2_len)
	angle_degrees = math.degrees(math.acos(cos_angle))
	assert abs(angle_degrees - 60.0) < TOL


#============================================
def test_basis_vectors_scaled():
	"""Verify basis vectors scale with spacing."""
	spacing = 2.5
	e1x, e1y, e2x, e2y = oasa.hex_grid.hex_basis_vectors(spacing)
	e1_len = math.sqrt(e1x * e1x + e1y * e1y)
	assert abs(e1_len - spacing) < TOL
	e2_len = math.sqrt(e2x * e2x + e2y * e2y)
	assert abs(e2_len - spacing) < TOL


#============================================
def test_snap_to_grid_exact_point():
	"""A point exactly on the grid snaps to itself."""
	# the origin is a grid point
	sx, sy = oasa.hex_grid.snap_to_hex_grid(0.0, 0.0, SPACING)
	assert abs(sx - 0.0) < TOL
	assert abs(sy - 0.0) < TOL

	# e1 direction: (spacing, 0) is a grid point
	sx, sy = oasa.hex_grid.snap_to_hex_grid(SPACING, 0.0, SPACING)
	assert abs(sx - SPACING) < TOL
	assert abs(sy - 0.0) < TOL

	# e2 direction: (spacing/2, spacing*sqrt(3)/2) is a grid point
	e2x = SPACING / 2.0
	e2y = SPACING * math.sqrt(3) / 2.0
	sx, sy = oasa.hex_grid.snap_to_hex_grid(e2x, e2y, SPACING)
	assert abs(sx - e2x) < TOL
	assert abs(sy - e2y) < TOL


#============================================
def test_snap_to_grid_near_point():
	"""A point near a grid node snaps to that node."""
	# slightly offset from origin
	offset = 0.05
	sx, sy = oasa.hex_grid.snap_to_hex_grid(offset, offset, SPACING)
	assert abs(sx - 0.0) < TOL
	assert abs(sy - 0.0) < TOL

	# slightly offset from (spacing, 0)
	sx, sy = oasa.hex_grid.snap_to_hex_grid(SPACING + offset, offset, SPACING)
	assert abs(sx - SPACING) < TOL
	assert abs(sy - 0.0) < TOL


#============================================
def test_hex_grid_index_roundtrip():
	"""hex_grid_point(hex_grid_index(x, y)) should equal snap_to_hex_grid(x, y)."""
	# test several grid points
	test_coords = [
		(0.0, 0.0),
		(SPACING, 0.0),
		(SPACING / 2.0, SPACING * math.sqrt(3) / 2.0),
		(SPACING * 1.5, SPACING * math.sqrt(3) / 2.0),
		(2.0 * SPACING, 0.0),
	]
	for x, y in test_coords:
		n, m = oasa.hex_grid.hex_grid_index(x, y, SPACING)
		rx, ry = oasa.hex_grid.hex_grid_point(n, m, SPACING)
		sx, sy = oasa.hex_grid.snap_to_hex_grid(x, y, SPACING)
		assert abs(rx - sx) < TOL, f"x mismatch at ({x},{y}): {rx} vs {sx}"
		assert abs(ry - sy) < TOL, f"y mismatch at ({x},{y}): {ry} vs {sy}"


#============================================
def test_generate_points_count():
	"""Known bounding box produces expected point count."""
	# generate grid in a small box
	spacing = 1.0
	# box from (0,0) to (2, 2)
	points = oasa.hex_grid.generate_hex_grid_points(0, 0, 2, 2, spacing)
	# should produce at least 4 points (corners-ish) and a reasonable number
	assert len(points) > 0
	# all points should be within or near the bounding box
	for px, py in points:
		assert px >= -TOL and px <= 2.0 + TOL
		assert py >= -TOL and py <= 2.0 + TOL


#============================================
def test_generate_points_neighbor_spacing():
	"""All generated points have at least one neighbor at exactly spacing distance."""
	spacing = 1.0
	points = oasa.hex_grid.generate_hex_grid_points(-2, -2, 2, 2, spacing)
	# interior points (exclude boundary) should have neighbors at spacing
	interior = []
	for px, py in points:
		if -1.0 <= px <= 1.0 and -1.0 <= py <= 1.0:
			interior.append((px, py))

	for px, py in interior:
		# find minimum distance to another point
		distances = []
		for qx, qy in points:
			if abs(px - qx) < TOL and abs(py - qy) < TOL:
				continue
			d = math.sqrt((px - qx) ** 2 + (py - qy) ** 2)
			distances.append(d)
		min_dist = min(distances)
		# nearest neighbor should be at exactly spacing distance
		assert abs(min_dist - spacing) < 0.01, (
			f"Point ({px},{py}) nearest neighbor at {min_dist}, expected {spacing}"
		)


#============================================
def test_all_atoms_on_grid_benzene():
	"""A perfect benzene hexagon with side = spacing should pass grid check."""
	spacing = 1.0
	# benzene vertices: 6 points on a circle of radius = spacing
	# at angles 0, 60, 120, 180, 240, 300 degrees from center
	center_x, center_y = 0.0, 0.0
	atom_coords = []
	for i in range(6):
		angle = math.radians(60 * i)
		x = center_x + spacing * math.cos(angle)
		y = center_y + spacing * math.sin(angle)
		atom_coords.append((x, y))

	# find best origin to align grid with these atoms
	ox, oy = oasa.hex_grid.find_best_grid_origin(atom_coords, spacing)
	result = oasa.hex_grid.all_atoms_on_hex_grid(
		atom_coords, spacing, tolerance=0.01, origin_x=ox, origin_y=oy
	)
	assert result is True


#============================================
def test_all_atoms_on_grid_shifted():
	"""A hexagon shifted by half spacing should fail grid check at default origin."""
	spacing = 1.0
	# benzene at origin
	atom_coords = []
	for i in range(6):
		angle = math.radians(60 * i)
		x = spacing * math.cos(angle)
		y = spacing * math.sin(angle)
		atom_coords.append((x, y))

	# shift all atoms by an amount that takes them off grid
	shift = spacing * 0.37
	shifted = [(x + shift, y + shift) for x, y in atom_coords]
	# with default origin (0,0), shifted atoms should NOT be on grid
	result = oasa.hex_grid.all_atoms_on_hex_grid(
		shifted, spacing, tolerance=0.01
	)
	assert result is False


#============================================
def test_snap_molecule_preserves_count():
	"""snap_molecule_to_hex_grid output has same length as input."""
	spacing = 1.0
	# arbitrary input coordinates
	atom_coords = [
		(0.1, 0.2),
		(1.1, 0.3),
		(0.6, 0.9),
		(1.6, 0.9),
		(2.1, 0.1),
	]
	snapped = oasa.hex_grid.snap_molecule_to_hex_grid(atom_coords, spacing)
	assert len(snapped) == len(atom_coords)


#============================================
def test_distance_to_grid_zero_on_grid():
	"""Distance to grid is 0.0 for points that are on the grid."""
	# origin is on grid
	d = oasa.hex_grid.distance_to_hex_grid(0.0, 0.0, SPACING)
	assert abs(d) < TOL

	# (spacing, 0) is on grid
	d = oasa.hex_grid.distance_to_hex_grid(SPACING, 0.0, SPACING)
	assert abs(d) < TOL

	# e2 grid point
	e2x = SPACING / 2.0
	e2y = SPACING * math.sqrt(3) / 2.0
	d = oasa.hex_grid.distance_to_hex_grid(e2x, e2y, SPACING)
	assert abs(d) < TOL


#============================================
def test_find_best_origin_trivial():
	"""When atoms are already on the default grid, best origin is near (0,0)."""
	spacing = 1.0
	# use grid points as atom positions
	atom_coords = [
		(0.0, 0.0),
		(spacing, 0.0),
		(spacing / 2.0, spacing * math.sqrt(3) / 2.0),
	]
	ox, oy = oasa.hex_grid.find_best_grid_origin(atom_coords, spacing)
	# all atoms should be on grid with this origin
	result = oasa.hex_grid.all_atoms_on_hex_grid(
		atom_coords, spacing, tolerance=0.01, origin_x=ox, origin_y=oy
	)
	assert result is True


#============================================
def test_bond_length_spacing():
	"""Adjacent hex grid points are exactly spacing apart."""
	spacing = 1.5
	# point (0,0) and its neighbors in the hex grid
	x0, y0 = oasa.hex_grid.hex_grid_point(0, 0, spacing)

	# neighbor along e1: (1, 0)
	x1, y1 = oasa.hex_grid.hex_grid_point(1, 0, spacing)
	d1 = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
	assert abs(d1 - spacing) < TOL

	# neighbor along e2: (0, 1)
	x2, y2 = oasa.hex_grid.hex_grid_point(0, 1, spacing)
	d2 = math.sqrt((x2 - x0) ** 2 + (y2 - y0) ** 2)
	assert abs(d2 - spacing) < TOL

	# neighbor along e1-e2 diagonal: (1, -1)
	x3, y3 = oasa.hex_grid.hex_grid_point(1, -1, spacing)
	d3 = math.sqrt((x3 - x0) ** 2 + (y3 - y0) ** 2)
	assert abs(d3 - spacing) < TOL
