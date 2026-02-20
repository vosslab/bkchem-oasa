"""Phase 3: Collision detection and resolution for 2D coordinate generation.

Detects atom overlaps and resolves them by flipping substituent subtrees
across bond axes or nudging atoms apart. Ring atoms are protected from
nudging to preserve ring geometry.
"""

from math import sqrt

from oasa.coords_gen import helpers


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

	Args:
		gen: CoordsGenerator2 instance.

	Returns:
		List of (atom1, atom2, distance) tuples for colliding pairs.
	"""
	threshold = 0.45 * gen.bond_length
	collisions = []
	atoms = gen.mol.vertices
	n = len(atoms)
	for i in range(n):
		a1 = atoms[i]
		if a1.x is None:
			continue
		for j in range(i + 1, n):
			a2 = atoms[j]
			if a2.x is None:
				continue
			# skip bonded atoms
			if a2 in a1.neighbors:
				continue
			d = helpers.point_dist(a1.x, a1.y, a2.x, a2.y)
			if d < threshold:
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
	"""Count collisions involving any atom in atom_set.

	Args:
		gen: CoordsGenerator2 instance.
		atom_set: list of atoms to check.

	Returns:
		Number of collision pairs.
	"""
	threshold = 0.45 * gen.bond_length
	count = 0
	atom_set_s = set(atom_set)
	for a1 in atom_set:
		if a1.x is None:
			continue
		for a2 in gen.mol.vertices:
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
