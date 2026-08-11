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

"""Pure geometry functions for a pointy-top hexagonal grid.

Pointy-top hex grid with spacing s (= bond_length) uses two basis vectors:
  e1 = (s * sqrt(3)/2, s/2)   -- 30 degrees from horizontal
  e2 = (0, s)                 -- vertical (90 degrees)

Every grid point is n * e1 + m * e2 for integer n, m.
Bond directions align with organic chemistry convention:
  30, 90, 150, 210, 270, 330 degrees.
Snapping is O(1) per point: invert the basis matrix, then compare the four
lattice vertices around the fractional skew coordinates in Cartesian space.
"""

from math import cos, floor, isfinite, pi, sqrt, sin


#============================================
def hex_basis_vectors(spacing: float) -> tuple:
	"""Return the two basis vectors for a pointy-top hex grid.

	Args:
		spacing: Distance between adjacent grid points (bond length).

	Returns:
		Tuple (e1x, e1y, e2x, e2y) for the two basis vectors.
	"""
	e1x = spacing * sqrt(3.0) / 2.0
	e1y = spacing / 2.0
	e2x = 0.0
	e2y = spacing
	return (e1x, e1y, e2x, e2y)


#============================================
def hex_grid_index(x: float, y: float, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> tuple:
	"""Return the Euclidean-nearest displayed lattice vertex indices.

	Coordinates use the Cartesian frame of the canvas, with the grid origin at
	(origin_x, origin_y), e1 at 30 degrees, and e2 vertical.  Fractional
	coordinates are in that skew e1/e2 basis, so their components cannot be
	rounded independently.  The four lattice vertices enclosing the fractional
	coordinates are compared by squared Cartesian distance.  Exact distance
	ties use the lexicographically smallest (n, m), which is deterministic.

	Args:
		x: X coordinate to convert.
		y: Y coordinate to convert.
		spacing: Distance between adjacent grid points.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		Tuple (n, m) of integer grid indices.

	Raises:
		ValueError: If a canvas value is invalid or its fractional lattice
			coordinates are not representable as finite floats.
	"""
	# This public operation is for finite canvas geometry with positive spacing.
	canvas_values = (x, y, origin_x, origin_y, spacing)
	if not all(isfinite(value) for value in canvas_values):
		raise ValueError("hex grid coordinates, origin, and spacing must be finite")
	if spacing <= 0.0:
		raise ValueError("hex grid spacing must be greater than zero")
	# shift to origin-relative coordinates
	dx = x - origin_x
	dy = y - origin_y
	# invert the 2x2 basis matrix [[s*sqrt(3)/2, 0], [s/2, s]]
	# determinant = s*sqrt(3)/2 * s = s^2 * sqrt(3)/2
	# inverse = (1/det) * [[s, 0], [-s/2, s*sqrt(3)/2]]
	# simplifies to:
	#   n = dx / (s * sqrt(3)/2)
	#   m = (dy - n_frac * s/2) / s
	half_sqrt3 = sqrt(3.0) / 2.0
	# solve for fractional n first (from x component)
	n_frac = dx / (spacing * half_sqrt3)
	# solve for fractional m (subtract n contribution to y)
	m_frac = (dy - n_frac * spacing / 2.0) / spacing
	if not isfinite(n_frac) or not isfinite(m_frac):
		raise ValueError("hex grid coordinate-to-spacing ratio is not representable")
	# A lattice nearest point must be one of the four vertices enclosing the
	# fractional skew-basis coordinates.  Compare Cartesian squared distances
	# because the basis is skew and squared distance avoids square roots.
	n_floor = floor(n_frac)
	m_floor = floor(m_frac)
	candidates = []
	for n in (n_floor, n_floor + 1):
		for m in (m_floor, m_floor + 1):
			# For e1 and e2 of equal length with a 60-degree angle, the
			# dimensionless distance ordering is a^2 + b^2 + a*b.  The omitted
			# common spacing^2 factor cannot affect the winner and can overflow.
			delta_n = n - n_frac
			delta_m = m - m_frac
			distance_squared = (
				delta_n * delta_n + delta_m * delta_m + delta_n * delta_m
		)
			candidates.append((distance_squared, n, m))
	# Tuple ordering resolves equal squared distances by n, then m.
	_, n, m = min(candidates)
	return (n, m)


#============================================
def hex_grid_point(n: int, m: int, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> tuple:
	"""Convert hex grid indices to pixel coordinates.

	Args:
		n: Index along the e1 (30-degree) basis vector.
		m: Index along the e2 (vertical) basis vector.
		spacing: Distance between adjacent grid points.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		Tuple (x, y) of pixel coordinates.
	"""
	half_sqrt3 = sqrt(3.0) / 2.0
	px = origin_x + n * spacing * half_sqrt3
	py = origin_y + n * spacing / 2.0 + m * spacing
	return (px, py)


#============================================
def snap_to_hex_grid(x: float, y: float, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> tuple:
	"""Snap a point to the Euclidean-nearest displayed lattice vertex.

	The coordinate frame and deterministic exact-tie policy are defined by
	hex_grid_index(): Cartesian canvas coordinates are measured from the grid
	origin, and ties choose the lexicographically smallest lattice index.

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
		List of (x, y) tuples for each grid point in the rectangle,
		or None if the estimated point count exceeds the internal
		MAX_GRID_POINTS cutoff (too many dots for practical use).
	"""
	# maximum number of grid points before we bail out;
	# drawing more dots than this would be too slow for any UI
	MAX_GRID_POINTS = 5000

	half_sqrt3 = sqrt(3.0) / 2.0
	# e1 step in x is spacing * sqrt(3)/2
	e1_dx = spacing * half_sqrt3

	# estimate range of n values from x bounds
	n_min_est = int((x_min - origin_x) / e1_dx) - 1
	n_max_est = int((x_max - origin_x) / e1_dx) + 1

	# quick estimate of total points; bail out early if too many
	n_cols = n_max_est - n_min_est + 1
	avg_rows = int((y_max - y_min) / spacing) + 2
	if n_cols * avg_rows > MAX_GRID_POINTS:
		return None

	points = []
	for n in range(n_min_est, n_max_est + 1):
		# for this n, estimate range of m values from y bounds
		# y = origin_y + n * spacing/2 + m * spacing
		y_offset = n * spacing / 2.0
		m_min_est = int((y_min - origin_y - y_offset) / spacing) - 1
		m_max_est = int((y_max - origin_y - y_offset) / spacing) + 1
		for m in range(m_min_est, m_max_est + 1):
			px, py = hex_grid_point(n, m, spacing, origin_x, origin_y)
			# only include points inside the bounding box
			if x_min <= px <= x_max and y_min <= py <= y_max:
				points.append((px, py))
	return points


#============================================
def generate_hex_honeycomb_edges(x_min: float, y_min: float,
		x_max: float, y_max: float, spacing: float,
		origin_x: float = 0.0, origin_y: float = 0.0) -> list:
	"""Generate honeycomb line segments for a pointy-top hex grid.

	Each edge connects two adjacent grid points. The honeycomb pattern
	is produced by iterating over hexagon centers and drawing the top 3
	edges of each hexagon to avoid duplicates.

	Args:
		x_min: Left boundary of the rectangle.
		y_min: Top boundary of the rectangle.
		x_max: Right boundary of the rectangle.
		y_max: Bottom boundary of the rectangle.
		spacing: Distance between adjacent grid points.
		origin_x: X coordinate of the grid origin.
		origin_y: Y coordinate of the grid origin.

	Returns:
		List of ((x1, y1), (x2, y2)) tuples for each edge segment,
		or None if the estimated edge count exceeds the internal
		MAX_GRID_EDGES cutoff.
	"""
	MAX_GRID_EDGES = 8000

	# hexagon centers form a coarser lattice;
	# for pointy-top hexagons, centers are spaced:
	#   dx_center = spacing * sqrt(3) horizontally
	#   dy_center = spacing * 1.5 vertically
	# with odd rows offset by spacing * sqrt(3)/2
	dx_center = spacing * sqrt(3.0)
	dy_center = spacing * 1.5

	# expand bounding box by one spacing to catch border hexagons
	margin = spacing * 2.0
	x_lo = x_min - margin
	x_hi = x_max + margin
	y_lo = y_min - margin
	y_hi = y_max + margin

	# estimate row/col counts for cutoff check
	n_rows_est = int((y_hi - y_lo) / dy_center) + 2
	n_cols_est = int((x_hi - x_lo) / dx_center) + 2
	# each center produces 3 edges
	if n_rows_est * n_cols_est * 3 > MAX_GRID_EDGES:
		return None

	# pointy-top hexagon vertex angles: 30, 90, 150, 210, 270, 330 deg
	# vertices at distance = spacing from center
	vertex_angles = [pi / 6.0 + k * pi / 3.0 for k in range(6)]
	# precompute unit offsets for each vertex
	vertex_dx = [spacing * cos(a) for a in vertex_angles]
	vertex_dy = [spacing * sin(a) for a in vertex_angles]

	edges = []
	# iterate over hex center rows
	row_start = int((y_lo - origin_y) / dy_center) - 1
	row_end = int((y_hi - origin_y) / dy_center) + 1

	for row_idx in range(row_start, row_end + 1):
		cy = origin_y + row_idx * dy_center
		# odd rows are offset horizontally
		x_offset = (row_idx % 2) * dx_center / 2.0
		col_start = int((x_lo - origin_x - x_offset) / dx_center) - 1
		col_end = int((x_hi - origin_x - x_offset) / dx_center) + 1

		for col_idx in range(col_start, col_end + 1):
			cx = origin_x + x_offset + col_idx * dx_center
			# draw only top 3 edges (k=0,1,2) to avoid duplicates
			# edge k connects vertex k to vertex (k+1)%6
			for k in range(3):
				x1 = cx + vertex_dx[k]
				y1 = cy + vertex_dy[k]
				k2 = (k + 1) % 6
				x2 = cx + vertex_dx[k2]
				y2 = cy + vertex_dy[k2]
				# include edge only if both endpoints are in bounding box
				in1 = x_min <= x1 <= x_max and y_min <= y1 <= y_max
				in2 = x_min <= x2 <= x_max and y_min <= y2 <= y_max
				if in1 and in2:
					edges.append(((x1, y1), (x2, y2)))

	return edges


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
