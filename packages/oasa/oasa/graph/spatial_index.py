"""2D spatial index for fast radius queries on atom coordinates.

Build from a list of (x, y) points. Query for all points within
radius r of a given point, or all close pairs within radius r.

Implementation: recursive median-split KD-tree alternating x/y axes.
Leaf nodes hold up to LEAF_SIZE points and use brute-force search.

This is not a general-purpose KD-tree library. It supports only:
- query_radius(x, y, r): find all points within distance r of (x, y)
- query_pairs(r): find all point pairs within distance r of each other

Rebuild-per-pass, no incremental insert/delete. Euclidean 2D only.
"""


# minimum atom count to justify building a KD-tree;
# below this threshold callers should use brute force
SMALL_MOLECULE_THRESHOLD = 20

# maximum points in a leaf node before splitting
LEAF_SIZE = 16


#============================================
class SpatialIndex:
	"""2D spatial index for fast radius queries on atom coordinates.

	Build from a list of (x, y) tuples. Query for all points within
	radius r of a given point, or all close pairs within radius r.

	Attributes:
		_points: flat list of (x, y) tuples, indexed by original order.
		_root: tree root node (tuple structure).
	"""

	def __init__(self, points: list, root: tuple):
		"""Initialize with pre-built tree.

		Args:
			points: list of (x, y) tuples.
			root: pre-built tree root node.
		"""
		self._points = points
		self._root = root

	#============================================
	@classmethod
	def build(cls, points: list) -> 'SpatialIndex':
		"""Build index from list of (x, y) tuples.

		Args:
			points: list of (x, y) coordinate tuples.

		Returns:
			SpatialIndex instance ready for queries.
		"""
		n = len(points)
		if n == 0:
			# empty tree: leaf with no indices
			return cls(points, (None, None, None, []))
		indices = list(range(n))
		root = _build_node(points, indices, 0)
		return cls(points, root)

	#============================================
	def query_radius(self, x: float, y: float, r: float) -> list:
		"""Return indices of all points within distance r of (x, y).

		Args:
			x: query x coordinate.
			y: query y coordinate.
			r: search radius.

		Returns:
			List of integer indices into the original points list.
		"""
		result = []
		r2 = r * r
		_query_radius_node(self._root, self._points, x, y, r, r2, result)
		return result

	#============================================
	def query_pairs(self, r: float) -> list:
		"""Return all (i, j) pairs with i < j within distance r.

		Args:
			r: search radius.

		Returns:
			List of (i, j) tuples where i < j and distance <= r.
		"""
		pairs = []
		r2 = r * r
		points = self._points
		n = len(points)
		for i in range(n):
			xi, yi = points[i]
			# find all neighbors within radius
			neighbors = []
			_query_radius_node(
				self._root, points, xi, yi, r, r2, neighbors
			)
			# only keep pairs where j > i to avoid duplicates
			for j in neighbors:
				if j > i:
					pairs.append((i, j))
		return pairs


#============================================
def _build_node(points: list, indices: list, depth: int) -> tuple:
	"""Recursively build a KD-tree node.

	Args:
		points: full list of (x, y) tuples.
		indices: subset of indices to partition.
		depth: current tree depth (determines split axis).

	Returns:
		Tree node tuple: leaf or internal node.
	"""
	if len(indices) <= LEAF_SIZE:
		# leaf node: (None, None, None, indices_list)
		return (None, None, None, list(indices))

	# split axis alternates: 0=x, 1=y
	axis = depth % 2

	# sort indices by coordinate on split axis
	indices_sorted = sorted(indices, key=lambda idx: points[idx][axis])
	mid = len(indices_sorted) // 2
	split_value = points[indices_sorted[mid]][axis]

	# partition into left (<=) and right (>) halves
	left_indices = indices_sorted[:mid]
	right_indices = indices_sorted[mid:]

	# handle degenerate case where all points have same coordinate
	if not left_indices:
		return (None, None, None, list(indices))

	left_child = _build_node(points, left_indices, depth + 1)
	right_child = _build_node(points, right_indices, depth + 1)

	# internal node: (axis, split_value, left_child, right_child)
	return (axis, split_value, left_child, right_child)


#============================================
def _query_radius_node(node: tuple, points: list,
	x: float, y: float, r: float, r2: float, result: list) -> None:
	"""Recursively search tree for points within radius.

	Args:
		node: current tree node.
		points: full list of (x, y) tuples.
		x: query x coordinate.
		y: query y coordinate.
		r: search radius.
		r2: r squared (precomputed to avoid sqrt).
		result: list to append matching indices to.
	"""
	axis = node[0]

	if axis is None:
		# leaf node: brute-force check all indices
		for idx in node[3]:
			px, py = points[idx]
			dx = px - x
			dy = py - y
			if dx * dx + dy * dy <= r2:
				result.append(idx)
		return

	split_value = node[1]
	query_coord = x if axis == 0 else y
	diff = query_coord - split_value

	# determine near and far sides
	if diff <= 0:
		near_child = node[2]  # left
		far_child = node[3]   # right
	else:
		near_child = node[3]  # right
		far_child = node[2]   # left

	# always search near side
	_query_radius_node(near_child, points, x, y, r, r2, result)

	# only search far side if the splitting plane is within radius
	if abs(diff) <= r:
		_query_radius_node(far_child, points, x, y, r, r2, result)


#============================================
def brute_force_pairs(points: list, r: float) -> list:
	"""Brute-force all-pairs within radius (for small molecules or testing).

	Args:
		points: list of (x, y) tuples.
		r: search radius.

	Returns:
		List of (i, j) tuples where i < j and distance <= r.
	"""
	pairs = []
	r2 = r * r
	n = len(points)
	for i in range(n):
		xi, yi = points[i]
		for j in range(i + 1, n):
			xj, yj = points[j]
			dx = xi - xj
			dy = yi - yj
			if dx * dx + dy * dy <= r2:
				pairs.append((i, j))
	return pairs


#============================================
def brute_force_radius(points: list, x: float, y: float, r: float) -> list:
	"""Brute-force radius query (for small molecules or testing).

	Args:
		points: list of (x, y) tuples.
		x: query x coordinate.
		y: query y coordinate.
		r: search radius.

	Returns:
		List of integer indices within distance r of (x, y).
	"""
	result = []
	r2 = r * r
	for i in range(len(points)):
		px, py = points[i]
		dx = px - x
		dy = py - y
		if dx * dx + dy * dy <= r2:
			result.append(i)
	return result
