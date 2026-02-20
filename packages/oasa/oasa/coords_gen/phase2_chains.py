"""Phase 2: Chain and substituent placement for 2D coordinate generation.

BFS outward from placed atoms (ring systems or seed backbone) to place
all remaining atoms using zigzag chain geometry and angular gap filling.
"""

from math import pi, cos, sin

from oasa import geometry
from oasa.coords_gen import helpers
from oasa.coords_gen import phase1_rings


#============================================
def place_chains(gen, placed: set) -> None:
	"""BFS outward from placed atoms to place all remaining atoms.

	When chain expansion reaches an atom adjacent to a deferred ring
	system, triggers placement of that ring system via Phase 1 and
	adds its atoms to the frontier for further expansion.

	Args:
		gen: CoordsGenerator2 instance.
		placed: set of already-placed atoms.
	"""
	frontier = list(placed)
	while frontier:
		next_frontier = []
		for v in frontier:
			# check if all done
			if all(a.x is not None for a in gen.mol.vertices):
				return
			new_atoms = _place_atom_neighbors(gen, v, placed)
			placed.update(new_atoms)
			# trigger deferred ring systems reached by chain expansion
			triggered = _trigger_deferred_ring_systems(gen, new_atoms, placed)
			placed.update(triggered)
			next_frontier.extend(new_atoms)
			next_frontier.extend(triggered)
		frontier = next_frontier


#============================================
def _trigger_deferred_ring_systems(gen, new_atoms: list,
	placed: set) -> list:
	"""Check if newly-placed atoms have neighbors in deferred ring systems.

	When a chain atom is placed adjacent to an atom belonging to a
	deferred ring system, triggers placement of that ring system via
	Phase 1 and returns the newly-placed ring atoms.

	Args:
		gen: CoordsGenerator2 instance.
		new_atoms: list of atoms just placed by chain expansion.
		placed: set of all placed atoms.

	Returns:
		List of atoms placed by triggered ring systems.
	"""
	membership = getattr(gen, 'ring_system_membership', {})
	deferred = getattr(gen, 'deferred_ring_systems', [])
	if not deferred or not membership:
		return []
	triggered_atoms = []
	for atom in new_atoms:
		for nb in atom.neighbors:
			if nb not in placed and nb in membership:
				ring_system = membership[nb]
				if ring_system not in deferred:
					continue
				# snapshot placed set before ring placement
				before = set(placed)
				# place the deferred ring system now that an anchor exists
				phase1_rings.place_deferred_ring_system(
					gen, ring_system, placed
				)
				# collect newly placed ring atoms
				for ring in ring_system:
					for ra in ring:
						if ra not in before and ra in placed:
							triggered_atoms.append(ra)
				deferred.remove(ring_system)
	return triggered_atoms


#============================================
def _place_atom_neighbors(gen, v, placed: set) -> list:
	"""Place unplaced neighbors of atom v. Returns newly placed atoms.

	Args:
		gen: CoordsGenerator2 instance.
		v: atom to expand from.
		placed: set of already-placed atoms.

	Returns:
		List of newly placed atoms.
	"""
	to_go = [a for a in v.neighbors if a.x is None or a.y is None]
	if not to_go:
		return []

	done = [a for a in v.neighbors if a in placed]

	if len(done) == 1 and len(to_go) == 1:
		# simple chain continuation
		return _place_chain_atom(gen, v, done[0], to_go[0])
	elif len(done) == 1 and len(to_go) >= 2:
		# handle stereochemistry first if present
		stereo_atoms = [t for t in to_go if t in gen.stereo]
		if stereo_atoms:
			result = _place_chain_atom(gen, v, done[0], stereo_atoms[0])
			placed.update(result)
			# recurse for remaining
			return result + _place_atom_neighbors(gen, v, placed)
		else:
			# place first atom as chain, then recurse
			result = _place_chain_atom(gen, v, done[0], to_go[0])
			placed.update(result)
			if len(to_go) > 1:
				return result + _place_atom_neighbors(gen, v, placed)
			return result
	else:
		# branched: multiple done neighbors; use angular gap
		return _place_branched(gen, v, done, to_go)


#============================================
def _place_chain_atom(gen, v, prev, target) -> list:
	"""Place a single chain atom continuing from prev -> v -> target.

	Args:
		gen: CoordsGenerator2 instance.
		v: current atom (already placed).
		prev: previous atom in chain (already placed).
		target: atom to place.

	Returns:
		List containing the newly placed target atom.
	"""
	# determine bond angle
	angle_to_add = 120.0
	bond = v.get_edge_leading_to(target)

	# triple bonds -> linear
	if 3 in [e.order for e in v.neighbor_edges]:
		angle_to_add = 180.0

	# cumulated double bonds -> linear
	if bond.order == 2:
		prev_bond = v.get_edge_leading_to(prev)
		if prev_bond.order == 2:
			angle_to_add = 180.0

	angle = helpers.angle_from_east(prev.x - v.x, prev.y - v.y)

	# try to maintain trans zigzag by checking prev's other neighbor
	atom_placed = False

	# stereochemistry (E/Z)
	if target in gen.stereo:
		stereos = [st for st in gen.stereo[target]
			if not None in st.get_other_end(target).coords[:2]]
		if stereos:
			st = stereos[0]
			d2 = st.get_other_end(target)
			relation = -1 if st.value == st.OPPOSITE_SIDE else 1
			angle_to_add = _get_angle_at_side(
				gen, v, prev, d2, relation, angle_to_add, angle
			)
			atom_placed = True

	if not atom_placed:
		prev_neighbors = prev.neighbors
		if len(prev_neighbors) == 2:
			d2 = prev_neighbors[0] if prev_neighbors[0] != v else prev_neighbors[1]
			if d2.x is not None and d2.y is not None:
				# maintain trans zigzag
				angle_to_add = _get_angle_at_side(
					gen, v, prev, d2, -1, angle_to_add, angle
				)

	an = angle + helpers.deg_to_rad(angle_to_add)
	target.x = v.x + gen.bond_length * cos(an)
	target.y = v.y + gen.bond_length * sin(an)
	return [target]


#============================================
def _get_angle_at_side(gen, v, d, d2, relation: int,
	attach_angle: float, angle: float) -> float:
	"""Choose +/- attach_angle to match desired stereochemical side.

	Args:
		gen: CoordsGenerator2 instance.
		v: central atom.
		d: reference atom for side determination.
		d2: atom whose side we compare against.
		relation: 1 for same side, -1 for opposite side.
		attach_angle: absolute angle value in degrees.
		angle: base angle in radians.

	Returns:
		Signed attach_angle (positive or negative degrees).
	"""
	if attach_angle == 180:
		return attach_angle
	side = geometry.on_which_side_is_point(
		(d.x, d.y, v.x, v.y), (d2.x, d2.y)
	)
	an = angle + helpers.deg_to_rad(attach_angle)
	x = v.x + gen.bond_length * cos(an)
	y = v.y + gen.bond_length * sin(an)
	new_side = geometry.on_which_side_is_point(
		(d.x, d.y, v.x, v.y), (x, y)
	)
	if relation * side == new_side:
		return attach_angle
	return -attach_angle


#============================================
def _place_branched(gen, v, done: list, to_go: list) -> list:
	"""Place multiple unplaced neighbors of v using largest angular gap.

	Args:
		gen: CoordsGenerator2 instance.
		v: atom with multiple neighbors to place.
		done: already-placed neighbors of v.
		to_go: unplaced neighbors of v.

	Returns:
		List of newly placed atoms.
	"""
	# compute angles to all placed neighbors
	angles = [helpers.angle_from_east(a.x - v.x, a.y - v.y) for a in done]
	angles.sort()
	# find the largest angular gap
	gaps = []
	for i in range(len(angles)):
		next_angle = angles[(i + 1) % len(angles)]
		prev_angle = angles[i]
		gap = next_angle - prev_angle
		if gap <= 0:
			gap += 2 * pi
		gaps.append((gap, prev_angle))

	# pick the largest gap
	largest_gap, gap_start = max(gaps, key=lambda x: x[0])

	# distribute to_go atoms evenly in the gap
	n = len(to_go)
	step = largest_gap / (n + 1)
	for i, atom_obj in enumerate(to_go):
		an = gap_start + step * (i + 1)
		atom_obj.x = v.x + gen.bond_length * cos(an)
		atom_obj.y = v.y + gen.bond_length * sin(an)
	return to_go
