"""Shared geometry helper functions for the 2D coordinate generator."""

from math import pi, sqrt, sin, cos, atan2


#============================================
def deg_to_rad(deg: float) -> float:
	"""Convert degrees to radians."""
	return pi * deg / 180.0


#============================================
def rad_to_deg(rad: float) -> float:
	"""Convert radians to degrees."""
	return 180.0 * rad / pi


#============================================
def point_dist(x1: float, y1: float, x2: float, y2: float) -> float:
	"""Euclidean distance between two points."""
	return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


#============================================
def angle_from_east(dx: float, dy: float) -> float:
	"""Angle in radians from east, always positive [0, 2*pi)."""
	a = atan2(dy, dx)
	if a < 0:
		a += 2 * pi
	return a


#============================================
def normalize_angle(a: float) -> float:
	"""Normalize angle to [0, 2*pi)."""
	while a < 0:
		a += 2 * pi
	while a >= 2 * pi:
		a -= 2 * pi
	return a


#============================================
def regular_polygon_coords(n: int, cx: float, cy: float,
	radius: float) -> list:
	"""Return n (x, y) tuples for a regular polygon centered at (cx, cy).

	First vertex is placed at the top (north) for even-sized rings
	so that the bottom edge is horizontal, matching chemical convention.
	"""
	# start angle: for even n, offset so bottom edge is horizontal
	if n % 2 == 0:
		start = pi / 2 + pi / n
	else:
		start = pi / 2
	coords = []
	for i in range(n):
		angle = start + 2 * pi * i / n
		x = cx + radius * cos(angle)
		y = cy + radius * sin(angle)
		coords.append((x, y))
	return coords


#============================================
def side_length_to_radius(side_length: float, n: int) -> float:
	"""Convert polygon side length to circumscribed radius."""
	# side = 2 * R * sin(pi/n)
	return side_length / (2 * sin(pi / n))


#============================================
def midpoint(x1: float, y1: float, x2: float, y2: float) -> tuple:
	"""Return midpoint between two points."""
	return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


#============================================
def reflect_point(px: float, py: float,
	ax: float, ay: float, bx: float, by: float) -> tuple:
	"""Reflect point (px, py) across line through (ax, ay)-(bx, by)."""
	dx = bx - ax
	dy = by - ay
	# avoid division by zero for degenerate lines
	d2 = dx * dx + dy * dy
	if d2 < 1e-12:
		return (px, py)
	t = ((px - ax) * dx + (py - ay) * dy) / d2
	# foot of perpendicular
	fx = ax + t * dx
	fy = ay + t * dy
	# reflected point
	rx = 2 * fx - px
	ry = 2 * fy - py
	return (rx, ry)
