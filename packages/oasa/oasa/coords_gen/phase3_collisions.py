"""Phase 3: Collision detection and resolution for 2D coordinate generation.

Detects atom overlaps and resolves them by flipping substituent subtrees
across bond axes or nudging atoms apart. Ring atoms are protected from
nudging to preserve ring geometry.
"""

from math import sqrt

from oasa.coords_gen import helpers
from oasa.graph.spatial_index import SpatialIndex, SMALL_MOLECULE_THRESHOLD


#============================================
def resolve_all_collisions(gen) -> None:
	"""Iteratively detect and resolve collisions.

	Args:
		gen: CoordsGenerator2 instance with mol, bond_length, ring_atoms.
	"""
	for iteration in range(10):
		collisions = _detect_collisions(gen)
		if not collisions:
			return
		_resolve_collisions(gen, collisions)


#============================================
def _detect_collisions(gen) -> list:
	"""Find pairs of non-bonded atoms that are too close.

	Uses a 2D spatial index (KD-tree) for molecules with 20+ atoms to
	avoid O(n^2) all-pairs scanning. Falls back to brute force for
	small molecules where the index overhead is not worthwhile.

	Args:
		gen: CoordsGenerator2 instance.

	Returns:
		List of (atom1, atom2, distance) tuples for colliding pairs.
	"""
	threshold = 0.45 * gen.bond_length
	collisions = []
	atoms = gen.mol.vertices

	# build coordinate list, skipping atoms without placed coordinates;
	# atom_for_idx maps spatial index positions back to atom objects
	coords = []
	atom_for_idx = []
	for a in atoms:
		if a.x is not None:
			atom_for_idx.append(a)
			coords.append((a.x, a.y))

	n = len(coords)
	if n < SMALL_MOLECULE_THRESHOLD:
		# brute force O(n^2) for small molecules where KD-tree overhead
		# would be more expensive than just checking all pairs
		for i in range(n):
			a1 = atom_for_idx[i]
			for j in range(i + 1, n):
				a2 = atom_for_idx[j]
				# bonded atoms can't collide by definition
				if a2 in a1.neighbors:
					continue
				d = helpers.point_dist(a1.x, a1.y, a2.x, a2.y)
				if d < threshold:
					collisions.append((a1, a2, d))
		return collisions

	# use KD-tree spatial index for larger molecules;
	# query_pairs returns only pairs within threshold distance,
	# then we filter out bonded pairs (topology check)
	index = SpatialIndex.build(coords)
	candidate_pairs = index.query_pairs(threshold)
	for i, j in candidate_pairs:
		a1 = atom_for_idx[i]
		a2 = atom_for_idx[j]
		# spatial index finds geometric neighbors; skip bonded atoms
		if a2 in a1.neighbors:
			continue
		d = helpers.point_dist(a1.x, a1.y, a2.x, a2.y)
		collisions.append((a1, a2, d))
	return collisions


#============================================
def _resolve_collisions(gen, collisions: list) -> None:
	"""Try to resolve detected collisions.

	Args:
		gen: CoordsGenerator2 instance.
		collisions: list of (atom1, atom2, distance) collision tuples.
	"""
	for a1, a2, dist in collisions:
		# try flipping substituent
		resolved = _try_flip_substituent(gen, a1)
		if not resolved:
			resolved = _try_flip_substituent(gen, a2)
		if not resolved:
			# nudge apart as last resort, but protect ring atoms
			_nudge_apart(gen, a1, a2)


#============================================
def _try_flip_substituent(gen, atom_obj) -> bool:
	"""Try reflecting atom and its subtree across the bond axis.

	Only flips atoms with exactly one placed neighbor (chain tips).
	Never flips ring atoms.

	Args:
		gen: CoordsGenerator2 instance.
		atom_obj: atom to try flipping.

	Returns:
		True if the flip reduced collisions.
	"""
	# never flip ring atoms
	if atom_obj in gen.ring_atoms:
		return False

	# only flip atoms with exactly one placed neighbor (chain tips)
	neighbors = atom_obj.neighbors
	if len(neighbors) != 1:
		return False

	parent = neighbors[0]
	# find parent's other neighbor to define the mirror axis
	parent_neighbors = [n for n in parent.neighbors if n != atom_obj]
	if not parent_neighbors:
		return False
	other = parent_neighbors[0]

	# get all atoms in the subtree rooted at atom_obj (away from parent)
	subtree = _get_subtree(atom_obj, parent)

	# count current collisions involving subtree
	before = _count_collisions_for_atoms(gen, subtree)
	if before == 0:
		return False

	# save coords
	saved = [(a, a.x, a.y) for a in subtree]

	# reflect across the parent-other axis
	for a in subtree:
		a.x, a.y = helpers.reflect_point(
			a.x, a.y, parent.x, parent.y, other.x, other.y
		)

	# count after
	after = _count_collisions_for_atoms(gen, subtree)

	if after >= before:
		# revert
		for a, x, y in saved:
			a.x = x
			a.y = y
		return False
	return True


#============================================
def _get_subtree(root, exclude) -> list:
	"""BFS to get all atoms reachable from root without passing through exclude.

	Args:
		root: starting atom.
		exclude: atom to block traversal through.

	Returns:
		List of atoms in the subtree.
	"""
	visited = {root, exclude}
	queue = [root]
	result = [root]
	while queue:
		v = queue.pop(0)
		for n in v.neighbors:
			if n not in visited:
				visited.add(n)
				queue.append(n)
				result.append(n)
	return result


#============================================
def _count_collisions_for_atoms(gen, atom_set: list) -> int:
	"""Count collisions involving any atom in atom_set vs all other atoms.

	Uses a spatial index for molecules with 20+ atoms to avoid
	scanning all vertices for each atom in the set.

	Args:
		gen: CoordsGenerator2 instance.
		atom_set: list of atoms to check.

	Returns:
		Number of collision pairs.
	"""
	threshold = 0.45 * gen.bond_length
	count = 0
	atom_set_s = set(atom_set)
	all_atoms = gen.mol.vertices
	n_all = len(all_atoms)

	if n_all < SMALL_MOLECULE_THRESHOLD:
		# brute force: check each atom_set member against every other atom
		for a1 in atom_set:
			if a1.x is None:
				continue
			for a2 in all_atoms:
				if a2 in atom_set_s:
					continue
				if a2.x is None:
					continue
				if a2 in a1.neighbors:
					continue
				d = helpers.point_dist(a1.x, a1.y, a2.x, a2.y)
				if d < threshold:
					count += 1
		return count

	# build spatial index from atoms NOT in atom_set;
	# this lets us do per-atom radius queries instead of scanning all vertices
	coords = []
	idx_to_atom = []
	for a in all_atoms:
		if a.x is not None and a not in atom_set_s:
			idx_to_atom.append(a)
			coords.append((a.x, a.y))

	if not coords:
		return 0

	# for each atom in the set, query the index for nearby non-set atoms
	index = SpatialIndex.build(coords)
	for a1 in atom_set:
		if a1.x is None:
			continue
		neighbors_indices = index.query_radius(a1.x, a1.y, threshold)
		for idx in neighbors_indices:
			a2 = idx_to_atom[idx]
			# skip bonded pairs (topology, not geometry)
			if a2 in a1.neighbors:
				continue
			count += 1
	return count


#============================================
def _nudge_apart(gen, a1, a2) -> None:
	"""Push two atoms apart by a small amount.

	Protects ring atoms: if both atoms are ring members, skip entirely.
	If one is a ring atom, only move the non-ring atom.

	Args:
		gen: CoordsGenerator2 instance.
		a1: first colliding atom.
		a2: second colliding atom.
	"""
	a1_is_ring = a1 in gen.ring_atoms
	a2_is_ring = a2 in gen.ring_atoms
	# skip if both are ring atoms -- preserve ring geometry
	if a1_is_ring and a2_is_ring:
		return

	dx = a2.x - a1.x
	dy = a2.y - a1.y
	d = sqrt(dx * dx + dy * dy)
	if d < 1e-6:
		# overlapping exactly: push in arbitrary direction
		dx, dy = 0.1, 0.0
		d = 0.1
	push = 0.2 * gen.bond_length
	nx = dx / d
	ny = dy / d

	if a1_is_ring:
		# only move a2
		a2.x += 2 * push * nx
		a2.y += 2 * push * ny
	elif a2_is_ring:
		# only move a1
		a1.x -= 2 * push * nx
		a1.y -= 2 * push * ny
	else:
		# move both
		a1.x -= push * nx
		a1.y -= push * ny
		a2.x += push * nx
		a2.y += push * ny
