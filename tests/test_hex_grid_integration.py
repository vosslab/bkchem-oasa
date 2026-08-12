"""Deterministic geometry tests for the oasa.hex_grid module."""

# Standard Library
import math

# local repo modules
import oasa.hex_grid

# tolerance for floating point comparisons
TOL = 1e-6


#============================================
def _benzene_coords(spacing: float, center_x: float = 0.0,
		center_y: float = 0.0) -> list:
	"""Build a perfect pointy-top benzene hexagon with given spacing.

	Args:
		spacing: Side length (bond length).
		center_x: X center of the hexagon.
		center_y: Y center of the hexagon.

	Returns:
		List of 6 (x, y) tuples.
	"""
	coords = []
	for i in range(6):
		angle = math.radians(30 + 60 * i)
		x = center_x + spacing * math.cos(angle)
		y = center_y + spacing * math.sin(angle)
		coords.append((x, y))
	return coords


#============================================
def _benzene_bond_pairs() -> list:
	"""Return bond index pairs for a 6-atom benzene ring.

	Returns:
		List of (i, j) tuples.
	"""
	return [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)]


#============================================
def test_benzene_on_hex_grid() -> None:
	"""A perfect benzene hexagon should lie on the hex grid."""
	spacing = 1.0
	coords = _benzene_coords(spacing)
	ox, oy = oasa.hex_grid.find_best_grid_origin(coords, spacing)
	result = oasa.hex_grid.all_atoms_on_hex_grid(
		coords, spacing, tolerance=0.01, origin_x=ox, origin_y=oy
	)
	assert result is True
	# bond lengths should also match spacing
	bonds = _benzene_bond_pairs()
	bond_result = oasa.hex_grid.all_bonds_on_hex_grid(
		coords, bonds, spacing, tolerance=0.01
	)
	assert bond_result is True


#============================================
def test_zigzag_chain_on_hex_grid() -> None:
	"""A zigzag chain of atoms on hex grid points should pass grid check."""
	spacing = 1.0
	# build a zigzag: alternating between e1 and e2-e1 directions
	# pointy-top e1 = (s*sqrt(3)/2, s/2), e2 = (0, s)
	# e2-e1 = (-s*sqrt(3)/2, s/2)
	e1x = spacing * math.sqrt(3) / 2.0
	e1y = spacing / 2.0
	coords = []
	x, y = 0.0, 0.0
	coords.append((x, y))
	for i in range(5):
		if i % 2 == 0:
			# step along e1
			x += e1x
			y += e1y
		else:
			# step along e2-e1 direction: (-s*sqrt(3)/2, s/2)
			x -= e1x
			y += e1y
		coords.append((x, y))
	# all points should already be on the grid at default origin
	result = oasa.hex_grid.all_atoms_on_hex_grid(
		coords, spacing, tolerance=0.01
	)
	assert result is True


#============================================
def test_snap_preserves_bond_lengths() -> None:
	"""After snapping, all neighbor distances should be multiples of spacing."""
	spacing = 1.0
	# slightly perturbed benzene
	coords = _benzene_coords(spacing)
	perturbed = [(x + 0.05, y - 0.03) for x, y in coords]
	ox, oy = oasa.hex_grid.find_best_grid_origin(perturbed, spacing)
	snapped = oasa.hex_grid.snap_molecule_to_hex_grid(
		perturbed, spacing, origin_x=ox, origin_y=oy
	)
	# check bond lengths match expected hex grid distances
	bonds = _benzene_bond_pairs()
	for i, j in bonds:
		x1, y1 = snapped[i]
		x2, y2 = snapped[j]
		d = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
		# distance should be spacing (nearest neighbor) within tolerance
		assert abs(d - spacing) < 0.01, (
			f"bond ({i},{j}) length {d:.4f} != spacing {spacing}"
		)


#============================================
def test_grid_points_cover_a4_page() -> None:
	"""A4-sized bounding box should produce a reasonable number of grid points."""
	# A4 in points: 595 x 842 (roughly)
	pts_per_cm = 72.0 / 2.54
	spacing_pts = 0.7 * pts_per_cm
	# A4 dimensions in points
	a4_width = 21.0 * pts_per_cm
	a4_height = 29.7 * pts_per_cm
	points = oasa.hex_grid.generate_hex_grid_points(
		0, 0, a4_width, a4_height, spacing_pts
	)
	# rough estimate: area / (hex cell area) = area / (sqrt(3)/2 * s^2)
	hex_cell_area = math.sqrt(3) / 2.0 * spacing_pts * spacing_pts
	expected_count = int(a4_width * a4_height / hex_cell_area)
	# should be within 50% of the estimate
	assert len(points) > expected_count * 0.5
	assert len(points) < expected_count * 1.5
	# all points should be within the bounding box
	for px, py in points:
		assert px >= -TOL and px <= a4_width + TOL
		assert py >= -TOL and py <= a4_height + TOL


#============================================
def test_find_best_origin_improves_fit() -> None:
	"""find_best_grid_origin should reduce total snap distance vs default origin."""
	spacing = 1.0
	# build benzene centered at (0.3, 0.3) so default origin is suboptimal
	coords = _benzene_coords(spacing, center_x=0.3, center_y=0.3)
	# total distance at default origin (0, 0)
	total_default = 0.0
	for x, y in coords:
		d = oasa.hex_grid.distance_to_hex_grid(x, y, spacing)
		total_default += d
	# total distance with best origin
	ox, oy = oasa.hex_grid.find_best_grid_origin(coords, spacing)
	total_best = 0.0
	for x, y in coords:
		d = oasa.hex_grid.distance_to_hex_grid(x, y, spacing, ox, oy)
		total_best += d
	# best origin should not be worse than default
	assert total_best <= total_default + TOL
