#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program

#--------------------------------------------------------------------------

"""Pure geometry functions for a flat-top hexagonal grid.

Flat-top hex grid with spacing s (= bond_length) uses two basis vectors:
  e1 = (s, 0)                      -- horizontal
  e2 = (s/2, s * sqrt(3)/2)        -- 60 degrees from horizontal

Every grid point is n * e1 + m * e2 for integer n, m.
Snapping is O(1) per point: invert the basis matrix, round to nearest
integers, convert back.
"""

from math import sqrt


#============================================
def hex_basis_vectors(spacing: float) -> tuple:
	"""Return the two basis vectors for a flat-top hex grid.

	Args:
		spacing: Distance between adjacent grid points (bond length).

	Returns:
		Tuple (e1x, e1y, e2x, e2y) for the two basis vectors.
	"""
	e1x = spacing
	e1y = 0.0
	e2x = spacing / 2.0
	e2y = spacing * sqrt(3.0) / 2.0
	return (e1x, e1y, e2x, e2y)


#============================================
def hex_grid_index(x: float, y: float, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> tuple:
	"""Convert pixel coordinates to hex grid indices (n, m).

	Uses the inverse of the basis matrix to find the closest
	integer grid indices.

	Args:
		x: X coordinate to convert.
		y: Y coordinate to convert.
		spacing: Distance between adjacent grid points.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		Tuple (n, m) of integer grid indices.
	"""
	# shift to origin-relative coordinates
	dx = x - origin_x
	dy = y - origin_y
	# invert the 2x2 basis matrix [[s, s/2], [0, s*sqrt(3)/2]]
	# determinant = s * s * sqrt(3) / 2
	# inverse = (1/det) * [[s*sqrt(3)/2, -s/2], [0, s]]
	# simplifies to:
	#   m = dy / (s * sqrt(3) / 2)
	#   n = (dx - m * s / 2) / s
	half_sqrt3 = sqrt(3.0) / 2.0
	# solve for fractional m first
	m_frac = dy / (spacing * half_sqrt3)
	# solve for fractional n
	n_frac = (dx - m_frac * spacing / 2.0) / spacing
	# round to nearest integers
	n = round(n_frac)
	m = round(m_frac)
	return (n, m)


#============================================
def hex_grid_point(n: int, m: int, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> tuple:
	"""Convert hex grid indices to pixel coordinates.

	Args:
		n: Index along the e1 (horizontal) basis vector.
		m: Index along the e2 (60-degree) basis vector.
		spacing: Distance between adjacent grid points.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		Tuple (x, y) of pixel coordinates.
	"""
	half_sqrt3 = sqrt(3.0) / 2.0
	px = origin_x + n * spacing + m * spacing / 2.0
	py = origin_y + m * spacing * half_sqrt3
	return (px, py)


#============================================
def snap_to_hex_grid(x: float, y: float, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> tuple:
	"""Snap a point to the nearest hex grid point.

	Args:
		x: X coordinate to snap.
		y: Y coordinate to snap.
		spacing: Distance between adjacent grid points.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		Tuple (snapped_x, snapped_y) of the nearest grid point.
	"""
	# find the closest grid indices
	n, m = hex_grid_index(x, y, spacing, origin_x, origin_y)
	# convert back to pixel coordinates
	snapped = hex_grid_point(n, m, spacing, origin_x, origin_y)
	return snapped


#============================================
def generate_hex_grid_points(x_min: float, y_min: float,
		x_max: float, y_max: float, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> list:
	"""Generate all hex grid points within a bounding rectangle.

	Args:
		x_min: Left boundary of the rectangle.
		y_min: Top boundary of the rectangle.
		x_max: Right boundary of the rectangle.
		y_max: Bottom boundary of the rectangle.
		spacing: Distance between adjacent grid points.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		List of (x, y) tuples for each grid point in the rectangle.
	"""
	half_sqrt3 = sqrt(3.0) / 2.0
	# estimate range of m values from y bounds
	m_min_est = int((y_min - origin_y) / (spacing * half_sqrt3)) - 1
	m_max_est = int((y_max - origin_y) / (spacing * half_sqrt3)) + 1
	points = []
	for m in range(m_min_est, m_max_est + 1):
		# for this m, estimate range of n values from x bounds
		x_offset = m * spacing / 2.0
		n_min_est = int((x_min - origin_x - x_offset) / spacing) - 1
		n_max_est = int((x_max - origin_x - x_offset) / spacing) + 1
		for n in range(n_min_est, n_max_est + 1):
			px, py = hex_grid_point(n, m, spacing, origin_x, origin_y)
			# only include points inside the bounding box
			if x_min <= px <= x_max and y_min <= py <= y_max:
				points.append((px, py))
	return points


#============================================
def distance_to_hex_grid(x: float, y: float, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> float:
	"""Calculate the distance from a point to the nearest hex grid point.

	Args:
		x: X coordinate of the point.
		y: Y coordinate of the point.
		spacing: Distance between adjacent grid points.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		Euclidean distance to the nearest grid point.
	"""
	sx, sy = snap_to_hex_grid(x, y, spacing, origin_x, origin_y)
	dist = sqrt((x - sx)**2 + (y - sy)**2)
	return dist


#============================================
def all_atoms_on_hex_grid(atom_coords: list, spacing: float,
		tolerance: float = 0.01, origin_x: float = 0.0,
		origin_y: float = 0.0) -> bool:
	"""Check whether all atom coordinates lie on hex grid points.

	Args:
		atom_coords: List of (x, y) tuples for atom positions.
		spacing: Distance between adjacent grid points.
		tolerance: Maximum allowed distance from a grid point.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		True if every atom is within tolerance of a grid point.
	"""
	for coord in atom_coords:
		x, y = coord
		dist = distance_to_hex_grid(x, y, spacing, origin_x, origin_y)
		if dist > tolerance:
			return False
	return True


#============================================
def all_bonds_on_hex_grid(atom_coords: list, bond_pairs: list,
		spacing: float, tolerance: float = 0.01) -> bool:
	"""Check whether all bond lengths match the hex grid spacing.

	Args:
		atom_coords: List of (x, y) tuples for atom positions.
		bond_pairs: List of (i, j) index pairs into atom_coords.
		spacing: Expected bond length (grid spacing).
		tolerance: Maximum allowed deviation from expected length.

	Returns:
		True if every bond length is within tolerance of the spacing.
	"""
	for pair in bond_pairs:
		i, j = pair
		x1, y1 = atom_coords[i]
		x2, y2 = atom_coords[j]
		bond_len = sqrt((x2 - x1)**2 + (y2 - y1)**2)
		if abs(bond_len - spacing) > tolerance:
			return False
	return True


#============================================
def snap_molecule_to_hex_grid(atom_coords: list, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> list:
	"""Snap all atom coordinates to the nearest hex grid points.

	Args:
		atom_coords: List of (x, y) tuples for atom positions.
		spacing: Distance between adjacent grid points.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		List of (x, y) tuples snapped to the hex grid.
	"""
	snapped = []
	for coord in atom_coords:
		x, y = coord
		sx, sy = snap_to_hex_grid(x, y, spacing, origin_x, origin_y)
		snapped.append((sx, sy))
	return snapped


#============================================
def find_best_grid_origin(atom_coords: list, spacing: float) -> tuple:
	"""Find the grid origin that minimizes total snap distance.

	Tries each atom as a candidate origin and picks the one that
	minimizes the sum of distances from all atoms to their nearest
	grid points.

	Args:
		atom_coords: List of (x, y) tuples for atom positions.
		spacing: Distance between adjacent grid points.

	Returns:
		Tuple (origin_x, origin_y) for the best grid origin.
	"""
	if not atom_coords:
		return (0.0, 0.0)
	best_origin = (0.0, 0.0)
	best_total = None
	# try each atom as a candidate origin
	for candidate in atom_coords:
		ox, oy = candidate
		total = 0.0
		for coord in atom_coords:
			x, y = coord
			dist = distance_to_hex_grid(x, y, spacing, ox, oy)
			total += dist
		if best_total is None or total < best_total:
			best_total = total
			best_origin = (ox, oy)
	return best_origin


#============================================
# simple assert examples
#============================================

# hex_grid_point: origin grid point (0,0) should be at the origin
result = hex_grid_point(0, 0, 1.0)
assert result == (0.0, 0.0), f"expected (0.0, 0.0), got {result}"

# hex_grid_point: (1,0) should be one spacing to the right
result = hex_grid_point(1, 0, 1.0)
assert result == (1.0, 0.0), f"expected (1.0, 0.0), got {result}"

# snap_to_hex_grid: a point at the origin should snap to (0,0)
result = snap_to_hex_grid(0.0, 0.0, 1.0)
assert result == (0.0, 0.0), f"expected (0.0, 0.0), got {result}"

# snap_to_hex_grid: a point near (1,0) should snap to (1,0)
result = snap_to_hex_grid(1.01, 0.01, 1.0)
assert result == (1.0, 0.0), f"expected (1.0, 0.0), got {result}"

# hex_grid_point with custom origin
result = hex_grid_point(0, 0, 1.0, origin_x=5.0, origin_y=10.0)
assert result == (5.0, 10.0), f"expected (5.0, 10.0), got {result}"
