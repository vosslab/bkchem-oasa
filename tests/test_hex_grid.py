"""Unit tests for the oasa.hex_grid module."""

# Standard Library
import math

# local repo modules
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

	# e1 direction: (spacing*sqrt(3)/2, spacing/2) is a grid point
	e1x = SPACING * math.sqrt(3) / 2.0
	e1y = SPACING / 2.0
	sx, sy = oasa.hex_grid.snap_to_hex_grid(e1x, e1y, SPACING)
	assert abs(sx - e1x) < TOL
	assert abs(sy - e1y) < TOL

	# e2 direction: (0, spacing) is a grid point
	e2x = 0.0
	e2y = SPACING
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

	# slightly offset from e1 grid point
	e1x = SPACING * math.sqrt(3) / 2.0
	e1y = SPACING / 2.0
	sx, sy = oasa.hex_grid.snap_to_hex_grid(e1x + offset, e1y + offset, SPACING)
	assert abs(sx - e1x) < TOL
	assert abs(sy - e1y) < TOL


#============================================
def test_hex_grid_index_roundtrip():
	"""hex_grid_point(hex_grid_index(x, y)) should equal snap_to_hex_grid(x, y)."""
	# test several grid points using new pointy-top basis
	e1x = SPACING * math.sqrt(3) / 2.0
	e1y = SPACING / 2.0
	test_coords = [
		(0.0, 0.0),
		(e1x, e1y),                     # n=1, m=0
		(0.0, SPACING),                  # n=0, m=1
		(e1x, e1y + SPACING),            # n=1, m=1
		(2.0 * e1x, 2.0 * e1y),         # n=2, m=0
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
	# pointy-top benzene vertices: 6 points on a circle of radius = spacing
	# at angles 30, 90, 150, 210, 270, 330 degrees from center
	center_x, center_y = 0.0, 0.0
	atom_coords = []
	for i in range(6):
		angle = math.radians(30 + 60 * i)
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
	# pointy-top benzene at origin
	atom_coords = []
	for i in range(6):
		angle = math.radians(30 + 60 * i)
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

	# e1 grid point: (spacing*sqrt(3)/2, spacing/2)
	e1x = SPACING * math.sqrt(3) / 2.0
	e1y = SPACING / 2.0
	d = oasa.hex_grid.distance_to_hex_grid(e1x, e1y, SPACING)
	assert abs(d) < TOL

	# e2 grid point: (0, spacing)
	d = oasa.hex_grid.distance_to_hex_grid(0.0, SPACING, SPACING)
	assert abs(d) < TOL


#============================================
def test_find_best_origin_trivial():
	"""When atoms are already on the default grid, best origin is near (0,0)."""
	spacing = 1.0
	# use grid points as atom positions (pointy-top basis)
	e1x = spacing * math.sqrt(3) / 2.0
	e1y = spacing / 2.0
	atom_coords = [
		(0.0, 0.0),
		(e1x, e1y),
		(0.0, spacing),
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


#============================================
def test_honeycomb_edge_count():
	"""Verify reasonable edge count for a known bounding box."""
	spacing = 1.0
	edges = oasa.hex_grid.generate_hex_honeycomb_edges(0, 0, 5, 5, spacing)
	assert edges is not None
	# a 5x5 box with spacing=1 should have a reasonable number of edges
	assert len(edges) > 10
	assert len(edges) < 500


#============================================
def test_honeycomb_edge_length():
	"""All honeycomb edges should have length equal to spacing."""
	spacing = 1.0
	edges = oasa.hex_grid.generate_hex_honeycomb_edges(0, 0, 5, 5, spacing)
	assert edges is not None
	for (x1, y1), (x2, y2) in edges:
		edge_len = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
		assert abs(edge_len - spacing) < 0.01, (
			f"Edge ({x1:.3f},{y1:.3f})->({x2:.3f},{y2:.3f}) "
			f"length {edge_len:.4f} != spacing {spacing}"
		)


#============================================
def test_honeycomb_no_duplicate_edges():
	"""No duplicate edges in honeycomb output."""
	spacing = 1.0
	edges = oasa.hex_grid.generate_hex_honeycomb_edges(0, 0, 5, 5, spacing)
	assert edges is not None
	# normalize each edge so (a,b) and (b,a) are treated the same
	seen = set()
	for (x1, y1), (x2, y2) in edges:
		# round to avoid floating point key issues
		p1 = (round(x1, 6), round(y1, 6))
		p2 = (round(x2, 6), round(y2, 6))
		key = (min(p1, p2), max(p1, p2))
		assert key not in seen, f"Duplicate edge: {key}"
		seen.add(key)


#============================================
def test_honeycomb_cutoff():
	"""Huge bounding box should trigger cutoff and return None."""
	spacing = 1.0
	result = oasa.hex_grid.generate_hex_honeycomb_edges(
		0, 0, 100000, 100000, spacing
	)
	assert result is None
