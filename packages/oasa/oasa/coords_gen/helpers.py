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


#============================================
class Transform2D:
	"""2D rigid-body transformation (rotation + translation).

	Matches RDKit's RDGeom::Transform2D semantics for clean ring placement.
	Encapsulates rotation and translation so all ring atoms can be
	transformed in a single pass without accumulating floating-point error.
	"""

	def __init__(self):
		# rotation matrix components: [[cos, -sin], [sin, cos]]
		self._cos_a = 1.0
		self._sin_a = 0.0
		# translation
		self._tx = 0.0
		self._ty = 0.0
		# scale factor
		self._scale = 1.0

	#============================================
	def set_transform_two_points(self, ref1: tuple, ref2: tuple,
		src1: tuple, src2: tuple) -> None:
		"""Compute transform mapping src1->ref1 and src2->ref2.

		Computes rotation, scale, and translation that maps the source
		edge (src1, src2) onto the reference edge (ref1, ref2).

		Args:
			ref1: (x, y) target position for first point.
			ref2: (x, y) target position for second point.
			src1: (x, y) source position for first point.
			src2: (x, y) source position for second point.
		"""
		# compute rotation angle and scale
		ref_dx = ref2[0] - ref1[0]
		ref_dy = ref2[1] - ref1[1]
		src_dx = src2[0] - src1[0]
		src_dy = src2[1] - src1[1]
		ref_angle = atan2(ref_dy, ref_dx)
		src_angle = atan2(src_dy, src_dx)
		angle = ref_angle - src_angle
		self._cos_a = cos(angle)
		self._sin_a = sin(angle)
		# compute scale
		ref_len = sqrt(ref_dx * ref_dx + ref_dy * ref_dy)
		src_len = sqrt(src_dx * src_dx + src_dy * src_dy)
		if src_len > 1e-12:
			self._scale = ref_len / src_len
		else:
			self._scale = 1.0
		# compute translation: ref1 = scale * rotate(src1) + (tx, ty)
		rotated_x = self._scale * (
			self._cos_a * src1[0] - self._sin_a * src1[1]
		)
		rotated_y = self._scale * (
			self._sin_a * src1[0] + self._cos_a * src1[1]
		)
		self._tx = ref1[0] - rotated_x
		self._ty = ref1[1] - rotated_y

	#============================================
	def set_transform_rotate(self, center: tuple, angle: float) -> None:
		"""Set rotation about center by angle radians.

		Args:
			center: (x, y) center of rotation.
			angle: rotation angle in radians (counter-clockwise positive).
		"""
		self._cos_a = cos(angle)
		self._sin_a = sin(angle)
		self._scale = 1.0
		# rotation about center: T = center + R * (p - center)
		# so tx = cx - R*cx, ty = cy - R*cy
		cx, cy = center
		self._tx = cx - (self._cos_a * cx - self._sin_a * cy)
		self._ty = cy - (self._sin_a * cx + self._cos_a * cy)

	#============================================
	def transform_point(self, x: float, y: float) -> tuple:
		"""Apply transform to a point, return (x', y').

		Args:
			x: source x coordinate.
			y: source y coordinate.

		Returns:
			Tuple (x', y') of transformed coordinates.
		"""
		rx = self._scale * (self._cos_a * x - self._sin_a * y) + self._tx
		ry = self._scale * (self._sin_a * x + self._cos_a * y) + self._ty
		return (rx, ry)


#============================================
def canonicalize_orientation(mol) -> None:
	"""Rotate molecule coordinates so the principal axis aligns with x.

	Uses PCA on the 2D covariance matrix of atom positions.
	Matches the behavior of RDKit's canonicalizeOrientation() which
	aligns the major variance axis horizontally for consistent display.

	Args:
		mol: OASA molecule object with x, y coordinates set on vertices.
	"""
	atoms = mol.vertices
	n = len(atoms)
	if n < 2:
		return
	# compute centroid
	cx = sum(a.x for a in atoms) / n
	cy = sum(a.y for a in atoms) / n
	# compute 2x2 covariance matrix
	sxx = 0.0
	sxy = 0.0
	syy = 0.0
	for a in atoms:
		dx = a.x - cx
		dy = a.y - cy
		sxx += dx * dx
		sxy += dx * dy
		syy += dy * dy
	# find eigenvector of the larger eigenvalue using the quadratic formula
	# eigenvalues of [[sxx, sxy], [sxy, syy]]:
	#   lambda = ((sxx+syy) +/- sqrt((sxx-syy)^2 + 4*sxy^2)) / 2
	diff = sxx - syy
	discriminant = sqrt(diff * diff + 4.0 * sxy * sxy)
	# larger eigenvalue
	lambda_max = (sxx + syy + discriminant) / 2.0
	# eigenvector for lambda_max: (sxy, lambda_max - sxx) or (lambda_max - syy, sxy)
	# use the form that avoids near-zero components
	evx = sxy
	evy = lambda_max - sxx
	ev_len = sqrt(evx * evx + evy * evy)
	if ev_len < 1e-12:
		# covariance is diagonal; check which axis has more variance
		if sxx >= syy:
			# already aligned with x
			return
		# need 90 degree rotation
		evx = 0.0
		evy = 1.0
		ev_len = 1.0
	# normalize eigenvector
	evx /= ev_len
	evy /= ev_len
	# rotation angle to align eigenvector with x-axis
	cos_a = evx
	sin_a = evy
	# rotate all atoms: new_x = cos_a*(x-cx) + sin_a*(y-cy), etc.
	for a in atoms:
		dx = a.x - cx
		dy = a.y - cy
		a.x = cos_a * dx + sin_a * dy + cx
		a.y = -sin_a * dx + cos_a * dy + cy
