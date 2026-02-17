#!/usr/bin/env python3
"""Three-layer 2D coordinate generator for OASA molecules.

Produces RDKit-quality 2D coordinates without the RDKit dependency.
Uses ring system assembly, chain layout, collision resolution, and
force-field refinement.

Same interface as coords_generator: calculate_coords(mol, bond_length, force).
"""

from math import pi, sqrt, sin, cos, atan2

from . import geometry


#============================================
def _deg_to_rad(deg: float) -> float:
	return pi * deg / 180.0


#============================================
def _rad_to_deg(rad: float) -> float:
	return 180.0 * rad / pi


#============================================
def _point_dist(x1: float, y1: float, x2: float, y2: float) -> float:
	return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


#============================================
def _angle_from_east(dx: float, dy: float) -> float:
	"""Angle in radians from east, always positive [0, 2*pi)."""
	a = atan2(dy, dx)
	if a < 0:
		a += 2 * pi
	return a


#============================================
def _normalize_angle(a: float) -> float:
	"""Normalize angle to [0, 2*pi)."""
	while a < 0:
		a += 2 * pi
	while a >= 2 * pi:
		a -= 2 * pi
	return a


#============================================
def _regular_polygon_coords(n: int, cx: float, cy: float,
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
def _side_length_to_radius(side_length: float, n: int) -> float:
	"""Convert polygon side length to circumscribed radius."""
	# side = 2 * R * sin(pi/n)
	return side_length / (2 * sin(pi / n))


#============================================
def _midpoint(x1: float, y1: float, x2: float, y2: float) -> tuple:
	return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


#============================================
def _reflect_point(px: float, py: float,
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
class CoordsGenerator2:
	"""Three-layer 2D coordinate generator.

	Phase 1: Ring system placement (fused ring assembly)
	Phase 2: Chain and substituent placement (BFS outward)
	Phase 3: Collision detection and resolution
	Phase 4: Force-field refinement (spring model)
	"""

	def __init__(self, bond_length: float = 1.0):
		self.bond_length = bond_length

	#============================================
	def calculate_coords(self, mol, bond_length: float = 1.0,
		force: int = 0) -> None:
		"""Main entry point. Same signature as coords_generator.

		Args:
			mol: OASA molecule object.
			bond_length: target bond length; 0 keeps current; -1 derives from
				existing coords.
			force: if truthy, recalculate all coordinates.
		"""
		self.mol = mol
		# handle bond_length parameter
		if bond_length > 0:
			self.bond_length = bond_length
		elif bond_length < 0:
			# derive from existing coords
			bls = []
			for b in mol.edges:
				a1, a2 = b.vertices
				if a1.x is not None and a2.x is not None:
					bls.append(_point_dist(a1.x, a1.y, a2.x, a2.y))
			if bls:
				self.bond_length = sum(bls) / len(bls)

		# check if all coords already present
		atms_with_coords = set(
			a for a in mol.vertices if a.x is not None and a.y is not None
		)
		if len(atms_with_coords) == len(mol.vertices) and not force:
			return

		if force:
			for a in mol.vertices:
				a.x = None
				a.y = None
			atms_with_coords = set()

		# build stereochemistry lookup
		self.stereo = {}
		for st in mol.stereochemistry:
			if st.__class__.__name__ == "cis_trans_stereochemistry":
				for a in (st.references[0], st.references[-1]):
					self.stereo[a] = self.stereo.get(a, []) + [st]

		# get SSSR rings
		self.rings = mol.get_smallest_independent_cycles()

		# placed tracks atoms with coordinates
		placed = set(atms_with_coords)

		# Phase 1: ring system placement
		placed = self._place_ring_systems(placed)

		# if no rings, seed a 2-atom backbone
		if not placed and len(mol.vertices) >= 2:
			a1 = mol.vertices[0]
			a2 = a1.neighbors[0]
			a1.x, a1.y = 0.0, 0.0
			a2.x, a2.y = self.bond_length, 0.0
			placed.add(a1)
			placed.add(a2)
		elif not placed and len(mol.vertices) == 1:
			a = mol.vertices[0]
			a.x, a.y = 0.0, 0.0
			a.z = 0
			placed.add(a)

		# Phase 2: chain and substituent placement
		self._place_chains(placed)

		# ensure z is set
		for v in mol.vertices:
			if v.z is None:
				v.z = 0

		# Phase 3: collision resolution
		self._resolve_all_collisions()

		# Phase 4: force-field refinement
		self._force_refine()

	# ======================================================
	# Phase 1: Ring system placement
	# ======================================================

	#============================================
	def _find_ring_systems(self) -> list:
		"""Group SSSR rings that share atoms into ring systems.

		Returns a list of ring systems, each a list of rings (sets of atoms).
		"""
		if not self.rings:
			return []
		# build adjacency: ring i shares atoms with ring j
		ring_sets = [set(r) for r in self.rings]
		n = len(ring_sets)
		visited = [False] * n
		systems = []
		for i in range(n):
			if visited[i]:
				continue
			# BFS to find connected ring cluster
			system = [i]
			visited[i] = True
			queue = [i]
			while queue:
				cur = queue.pop(0)
				for j in range(n):
					if not visited[j] and ring_sets[cur] & ring_sets[j]:
						visited[j] = True
						queue.append(j)
						system.append(j)
			systems.append([self.rings[idx] for idx in system])
		return systems

	#============================================
	def _place_ring_systems(self, placed: set) -> set:
		"""Place all ring systems, returning updated placed set."""
		ring_systems = self._find_ring_systems()
		if not ring_systems:
			return placed

		# sort ring systems: largest first for best backbone
		ring_systems.sort(key=lambda rs: sum(len(r) for r in rs), reverse=True)

		for ring_system in ring_systems:
			placed = self._place_ring_system(ring_system, placed)
		return placed

	#============================================
	def _place_ring_system(self, ring_system: list, placed: set) -> set:
		"""Place a single ring system (list of rings sharing atoms).

		Uses BFS from the largest ring outward to place fused rings.
		"""
		if not ring_system:
			return placed

		# sort rings by size descending, start with largest
		ring_system_sorted = sorted(ring_system, key=len, reverse=True)

		# ring adjacency within this system
		ring_sets = [set(r) for r in ring_system_sorted]
		n = len(ring_sets)

		# find which rings already have all coords placed
		ring_placed = [False] * n
		for i, rs in enumerate(ring_sets):
			if rs <= placed:
				ring_placed[i] = True

		# if none placed, place the largest ring as regular polygon
		if not any(ring_placed):
			first_ring = ring_system_sorted[0]
			first_sorted = self.mol.sort_vertices_in_path(list(first_ring))
			if first_sorted is None:
				first_sorted = list(first_ring)
			size = len(first_sorted)
			radius = _side_length_to_radius(self.bond_length, size)
			coords = _regular_polygon_coords(size, 0.0, 0.0, radius)
			for atom_obj, (x, y) in zip(first_sorted, coords):
				atom_obj.x = x
				atom_obj.y = y
			placed.update(first_sorted)
			ring_placed[0] = True

		# BFS from placed rings to fuse unplaced ones
		changed = True
		while changed:
			changed = False
			for i in range(n):
				if ring_placed[i]:
					continue
				# check if this ring shares atoms with any placed ring
				shared_with_placed = ring_sets[i] & placed
				if not shared_with_placed:
					continue
				# place this ring
				ring = ring_system_sorted[i]
				self._place_fused_ring(ring, shared_with_placed, placed)
				placed.update(ring)
				ring_placed[i] = True
				changed = True

		return placed

	#============================================
	def _place_fused_ring(self, ring: list, shared_atoms: set,
		placed: set) -> None:
		"""Place a ring that shares atoms with already-placed atoms.

		Handles edge-fused (2 shared), spiro (1 shared), and
		bridged (3+ shared) cases.
		"""
		ring_set = set(ring)
		to_place = [a for a in ring if a.x is None or a.y is None]
		already_placed = [a for a in ring if a not in to_place]

		if not to_place:
			return

		shared_list = list(shared_atoms & ring_set)
		n_shared = len(shared_list)

		if n_shared == 1:
			# spiro junction: one shared atom
			self._place_spiro_ring(ring, shared_list[0], placed)
		elif n_shared == 2:
			# edge-fused: two shared atoms forming a shared edge
			self._place_edge_fused_ring(ring, shared_list, placed)
		else:
			# bridged or multi-fused: 3+ shared atoms
			self._place_bridged_ring(ring, already_placed, placed)

	#============================================
	def _place_spiro_ring(self, ring: list, shared_atom, placed: set) -> None:
		"""Place a ring connected via a single spiro atom."""
		v = shared_atom
		ring_sorted = self.mol.sort_vertices_in_path(list(ring), start_from=v)
		if ring_sorted is None:
			ring_sorted = list(ring)
			# ensure v is first
			if v in ring_sorted:
				ring_sorted.remove(v)
				ring_sorted.insert(0, v)
		size = len(ring_sorted)

		# find angle away from existing neighbors
		placed_neighbors = [a for a in v.neighbors if a in placed and a not in ring]
		if placed_neighbors:
			# average angle of placed neighbors, go opposite
			angles = [_angle_from_east(n.x - v.x, n.y - v.y)
				for n in placed_neighbors]
			avg = sum(angles) / len(angles)
			away_angle = avg + pi
		else:
			away_angle = pi / 2

		# place as regular polygon with first vertex at v
		radius = _side_length_to_radius(self.bond_length, size)
		# center is at distance radius from v in the "away" direction
		cx = v.x + radius * cos(away_angle)
		cy = v.y + radius * sin(away_angle)

		coords = _regular_polygon_coords(size, cx, cy, radius)
		# find the coord closest to v and rotate accordingly
		best_idx = 0
		best_dist = 1e18
		for i, (px, py) in enumerate(coords):
			d = _point_dist(px, py, v.x, v.y)
			if d < best_dist:
				best_dist = d
				best_idx = i

		# assign coordinates, skip the shared atom
		for j, atom_obj in enumerate(ring_sorted):
			if atom_obj == v:
				continue
			idx = (best_idx + j) % size
			atom_obj.x, atom_obj.y = coords[idx]

	#============================================
	def _place_edge_fused_ring(self, ring: list, shared_list: list,
		placed: set) -> None:
		"""Place a ring sharing an edge (2 atoms) with placed atoms."""
		v1, v2 = shared_list[0], shared_list[1]
		ring_sorted = self.mol.sort_vertices_in_path(list(ring), start_from=v1)
		if ring_sorted is None:
			ring_sorted = list(ring)

		# remove v1, v2 from to-place list
		to_place = [a for a in ring_sorted if a not in (v1, v2)]
		# ensure v1 connects to first of to_place
		if to_place and v1 not in to_place[0].neighbors:
			v1, v2 = v2, v1

		ring_size = len(ring)

		# determine which side of the shared edge the existing ring is on
		side = 0
		for a in placed:
			if a in (v1, v2):
				continue
			s = geometry.on_which_side_is_point(
				(v1.x, v1.y, v2.x, v2.y), (a.x, a.y)
			)
			side += s

		# compute the ring angle and direction
		ca = _angle_from_east(v1.x - v2.x, v1.y - v2.y)
		da = _deg_to_rad(180 - 180.0 * (ring_size - 2) / ring_size)
		# draw on opposite side of existing atoms
		if side > 0:
			da = -da

		# generate coords by walking from v1
		angle = ca + da
		x, y = v1.x, v1.y
		for atom_obj in to_place:
			x += self.bond_length * cos(angle)
			y += self.bond_length * sin(angle)
			atom_obj.x = x
			atom_obj.y = y
			angle += da

	#============================================
	def _place_bridged_ring(self, ring: list, already_placed: list,
		placed: set) -> None:
		"""Place a ring with 3+ shared atoms (bridged system)."""
		to_place = [a for a in ring if a.x is None or a.y is None]
		if not to_place:
			return

		# sort already-placed atoms into a path
		sorted_back = self.mol.sort_vertices_in_path(already_placed)
		if not sorted_back:
			# fall back: just spread atoms evenly
			sorted_back = already_placed

		to_place_sorted = self.mol.sort_vertices_in_path(to_place)
		if not to_place_sorted:
			to_place_sorted = to_place

		# v1 and v2 are endpoints of the placed path
		v1 = sorted_back[0]
		v2 = sorted_back[-1]
		# ensure v1 connects to first of to_place
		if to_place_sorted and v1 not in to_place_sorted[0].neighbors:
			v1, v2 = v2, v1

		ring_size = len(ring)
		n_back = len(sorted_back)
		n_to_place = len(to_place_sorted)

		# compute internal angle for the full ring
		da = 180.0 * (ring_size - 2) / ring_size

		# determine side
		side = sum(
			geometry.on_which_side_is_point(
				(v1.x, v1.y, v2.x, v2.y), (a.x, a.y)
			)
			for a in sorted_back if a not in (v1, v2)
		)

		# compute connection angle
		blocked_angle = (n_back - 2) * 180.0 if n_back > 2 else 0
		overall_angle = (ring_size - 2) * 180.0
		ca = _deg_to_rad(180 - (overall_angle - blocked_angle - n_to_place * da) / 2)
		if side > 0:
			ca = -ca
		ca += _angle_from_east(v1.x - v2.x, v1.y - v2.y)

		ext_angle = 180 - da
		# check direction to ensure ring progresses toward v2
		if len(sorted_back) >= 2:
			v3 = sorted_back[1]
			if geometry.on_which_side_is_point(
				(v1.x, v1.y, v3.x, v3.y), (v2.x, v2.y)
			) < 0:
				ext_angle = -ext_angle

		# dry run to compute scaling
		angle = ca
		x, y = v1.x, v1.y
		for _ in range(n_to_place + 1):
			x += self.bond_length * cos(angle)
			y += self.bond_length * sin(angle)
			angle += _deg_to_rad(ext_angle)

		# scale bond length to close the ring
		target_dist = _point_dist(v1.x, v1.y, v2.x, v2.y)
		actual_dist = _point_dist(v1.x, v1.y, x, y)
		if actual_dist > 1e-6:
			bl = self.bond_length * target_dist / actual_dist
		else:
			bl = self.bond_length

		# actual placement
		angle = ca
		x, y = v1.x, v1.y
		for atom_obj in to_place_sorted:
			x += bl * cos(angle)
			y += bl * sin(angle)
			atom_obj.x = x
			atom_obj.y = y
			angle += _deg_to_rad(ext_angle)

	# ======================================================
	# Phase 2: Chain and substituent placement
	# ======================================================

	#============================================
	def _place_chains(self, placed: set) -> None:
		"""BFS outward from placed atoms to place all remaining atoms."""
		frontier = list(placed)
		while frontier:
			next_frontier = []
			for v in frontier:
				# check if all done
				if all(a.x is not None for a in self.mol.vertices):
					return
				new_atoms = self._place_atom_neighbors(v, placed)
				placed.update(new_atoms)
				next_frontier.extend(new_atoms)
			frontier = next_frontier

	#============================================
	def _place_atom_neighbors(self, v, placed: set) -> list:
		"""Place unplaced neighbors of atom v. Returns newly placed atoms."""
		to_go = [a for a in v.neighbors if a.x is None or a.y is None]
		if not to_go:
			return []

		done = [a for a in v.neighbors if a in placed]

		if len(done) == 1 and len(to_go) == 1:
			# simple chain continuation
			return self._place_chain_atom(v, done[0], to_go[0])
		elif len(done) == 1 and len(to_go) >= 2:
			# handle stereochemistry first if present
			stereo_atoms = [t for t in to_go if t in self.stereo]
			if stereo_atoms:
				result = self._place_chain_atom(v, done[0], stereo_atoms[0])
				placed.update(result)
				# recurse for remaining
				return result + self._place_atom_neighbors(v, placed)
			else:
				# place first atom as chain, then recurse
				result = self._place_chain_atom(v, done[0], to_go[0])
				placed.update(result)
				if len(to_go) > 1:
					return result + self._place_atom_neighbors(v, placed)
				return result
		else:
			# branched: multiple done neighbors; use angular gap
			return self._place_branched(v, done, to_go)

	#============================================
	def _place_chain_atom(self, v, prev, target) -> list:
		"""Place a single chain atom continuing from prev -> v -> target."""
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

		angle = _angle_from_east(prev.x - v.x, prev.y - v.y)

		# try to maintain trans zigzag by checking prev's other neighbor
		placed = False

		# stereochemistry (E/Z)
		if target in self.stereo:
			stereos = [st for st in self.stereo[target]
				if not None in st.get_other_end(target).coords[:2]]
			if stereos:
				st = stereos[0]
				d2 = st.get_other_end(target)
				relation = -1 if st.value == st.OPPOSITE_SIDE else 1
				angle_to_add = self._get_angle_at_side(
					v, prev, d2, relation, angle_to_add, angle
				)
				placed = True

		if not placed:
			prev_neighbors = prev.neighbors
			if len(prev_neighbors) == 2:
				d2 = prev_neighbors[0] if prev_neighbors[0] != v else prev_neighbors[1]
				if d2.x is not None and d2.y is not None:
					# maintain trans zigzag
					angle_to_add = self._get_angle_at_side(
						v, prev, d2, -1, angle_to_add, angle
					)

		an = angle + _deg_to_rad(angle_to_add)
		target.x = v.x + self.bond_length * cos(an)
		target.y = v.y + self.bond_length * sin(an)
		return [target]

	#============================================
	def _get_angle_at_side(self, v, d, d2, relation: int,
		attach_angle: float, angle: float) -> float:
		"""Choose +/- attach_angle to match desired stereochemical side."""
		if attach_angle == 180:
			return attach_angle
		side = geometry.on_which_side_is_point(
			(d.x, d.y, v.x, v.y), (d2.x, d2.y)
		)
		an = angle + _deg_to_rad(attach_angle)
		x = v.x + self.bond_length * cos(an)
		y = v.y + self.bond_length * sin(an)
		new_side = geometry.on_which_side_is_point(
			(d.x, d.y, v.x, v.y), (x, y)
		)
		if relation * side == new_side:
			return attach_angle
		return -attach_angle

	#============================================
	def _place_branched(self, v, done: list, to_go: list) -> list:
		"""Place multiple unplaced neighbors of v using largest angular gap."""
		# compute angles to all placed neighbors
		angles = [_angle_from_east(a.x - v.x, a.y - v.y) for a in done]
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
			atom_obj.x = v.x + self.bond_length * cos(an)
			atom_obj.y = v.y + self.bond_length * sin(an)
		return to_go

	# ======================================================
	# Phase 3: Collision detection and resolution
	# ======================================================

	#============================================
	def _detect_collisions(self) -> list:
		"""Find pairs of non-bonded atoms that are too close."""
		threshold = 0.45 * self.bond_length
		collisions = []
		atoms = self.mol.vertices
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
				d = _point_dist(a1.x, a1.y, a2.x, a2.y)
				if d < threshold:
					collisions.append((a1, a2, d))
		return collisions

	#============================================
	def _resolve_all_collisions(self) -> None:
		"""Iteratively detect and resolve collisions."""
		for iteration in range(10):
			collisions = self._detect_collisions()
			if not collisions:
				return
			self._resolve_collisions(collisions)

	#============================================
	def _resolve_collisions(self, collisions: list) -> None:
		"""Try to resolve detected collisions."""
		for a1, a2, dist in collisions:
			# try flipping substituent
			resolved = self._try_flip_substituent(a1)
			if not resolved:
				resolved = self._try_flip_substituent(a2)
			if not resolved:
				# nudge apart as last resort
				self._nudge_apart(a1, a2)

	#============================================
	def _try_flip_substituent(self, atom_obj) -> bool:
		"""Try reflecting atom and its subtree across the bond axis.

		Returns True if the flip reduced collisions.
		"""
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
		subtree = self._get_subtree(atom_obj, parent)

		# count current collisions involving subtree
		before = self._count_collisions_for_atoms(subtree)
		if before == 0:
			return False

		# save coords
		saved = [(a, a.x, a.y) for a in subtree]

		# reflect across the parent-other axis
		for a in subtree:
			a.x, a.y = _reflect_point(
				a.x, a.y, parent.x, parent.y, other.x, other.y
			)

		# count after
		after = self._count_collisions_for_atoms(subtree)

		if after >= before:
			# revert
			for a, x, y in saved:
				a.x = x
				a.y = y
			return False
		return True

	#============================================
	def _get_subtree(self, root, exclude) -> list:
		"""BFS to get all atoms reachable from root without passing through exclude."""
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
	def _count_collisions_for_atoms(self, atom_set: list) -> int:
		"""Count collisions involving any atom in atom_set."""
		threshold = 0.45 * self.bond_length
		count = 0
		atom_set_s = set(atom_set)
		for a1 in atom_set:
			if a1.x is None:
				continue
			for a2 in self.mol.vertices:
				if a2 in atom_set_s:
					continue
				if a2.x is None:
					continue
				if a2 in a1.neighbors:
					continue
				d = _point_dist(a1.x, a1.y, a2.x, a2.y)
				if d < threshold:
					count += 1
		return count

	#============================================
	def _nudge_apart(self, a1, a2) -> None:
		"""Push two atoms apart by a small amount."""
		dx = a2.x - a1.x
		dy = a2.y - a1.y
		d = sqrt(dx * dx + dy * dy)
		if d < 1e-6:
			# overlapping exactly: push in arbitrary direction
			dx, dy = 0.1, 0.0
			d = 0.1
		# push each atom 0.2 * bond_length in opposite directions
		push = 0.2 * self.bond_length
		nx = dx / d
		ny = dy / d
		a1.x -= push * nx
		a1.y -= push * ny
		a2.x += push * nx
		a2.y += push * ny

	# ======================================================
	# Phase 4: Force-field refinement
	# ======================================================

	#============================================
	def _force_refine(self) -> None:
		"""Simple steepest-descent refinement using spring model.

		Energy terms:
		- Bond stretch: Hookean spring toward target bond length
		- Angle bend: penalty for deviation from ideal angles
		- Non-bonded repulsion: repulsive term for close non-bonded pairs
		"""
		if len(self.mol.vertices) < 2:
			return

		k_bond = 1.0
		k_angle = 0.3
		k_repel = 0.5
		step_size = 0.05
		max_iters = 200
		converge_threshold = 1e-4

		# precompute ideal angles per atom
		ideal_angles = {}
		for v in self.mol.vertices:
			n_neighbors = len(v.neighbors)
			if n_neighbors <= 1:
				continue
			# check for triple bonds
			has_triple = any(e.order >= 3 for e in v.neighbor_edges)
			# check for double bonds
			has_double = any(e.order == 2 for e in v.neighbor_edges)
			if has_triple:
				ideal_angles[v] = pi  # 180 degrees
			elif has_double and n_neighbors == 2:
				ideal_angles[v] = 2 * pi / 3  # 120 degrees
			elif n_neighbors == 2:
				ideal_angles[v] = 2 * pi / 3  # 120 degrees
			elif n_neighbors == 3:
				ideal_angles[v] = 2 * pi / 3  # 120 degrees
			else:
				ideal_angles[v] = pi / 2  # 90 for 4+ neighbors

		# precompute non-bonded pairs (separated by 3+ bonds)
		bonded_or_close = {}
		for v in self.mol.vertices:
			near = {v}
			near.update(v.neighbors)
			for n in v.neighbors:
				near.update(n.neighbors)
			bonded_or_close[v] = near

		for _iteration in range(max_iters):
			# compute gradients
			grad = {}
			for v in self.mol.vertices:
				grad[v] = [0.0, 0.0]

			# bond stretch
			for b in self.mol.edges:
				a1, a2 = b.vertices
				if a1.x is None or a2.x is None:
					continue
				dx = a1.x - a2.x
				dy = a1.y - a2.y
				d = sqrt(dx * dx + dy * dy)
				if d < 1e-8:
					continue
				dd = d - self.bond_length
				# gradient of 0.5*k*(d-d0)^2
				gx = k_bond * dd * dx / d
				gy = k_bond * dd * dy / d
				grad[a1][0] -= gx * step_size
				grad[a1][1] -= gy * step_size
				grad[a2][0] += gx * step_size
				grad[a2][1] += gy * step_size

			# angle bend
			for v in self.mol.vertices:
				if v not in ideal_angles:
					continue
				neighbors_list = list(v.neighbors)
				n_neigh = len(neighbors_list)
				ideal = ideal_angles[v]
				for i in range(n_neigh):
					for j in range(i + 1, n_neigh):
						n1 = neighbors_list[i]
						n2 = neighbors_list[j]
						if n1.x is None or n2.x is None:
							continue
						# use distance-based angle penalty (same as coords_optimizer)
						# ideal distance between n1 and n2 at ideal angle
						ideal_dist = 2 * self.bond_length * sin(ideal / 2)
						dx = n1.x - n2.x
						dy = n1.y - n2.y
						d = sqrt(dx * dx + dy * dy)
						if d < 1e-8:
							continue
						dd = d - ideal_dist
						gx = k_angle * dd * dx / d
						gy = k_angle * dd * dy / d
						grad[n1][0] -= gx * step_size
						grad[n1][1] -= gy * step_size
						grad[n2][0] += gx * step_size
						grad[n2][1] += gy * step_size

			# non-bonded repulsion
			atoms = self.mol.vertices
			n_atoms = len(atoms)
			repel_dist = 1.8 * self.bond_length
			for i in range(n_atoms):
				a1 = atoms[i]
				if a1.x is None:
					continue
				for j in range(i + 1, n_atoms):
					a2 = atoms[j]
					if a2.x is None:
						continue
					if a2 in bonded_or_close.get(a1, set()):
						continue
					dx = a1.x - a2.x
					dy = a1.y - a2.y
					d2 = dx * dx + dy * dy
					if d2 > repel_dist * repel_dist:
						continue
					d = sqrt(d2)
					if d < 1e-8:
						continue
					# repulsive force: k/d^2
					force = k_repel / (d * d)
					gx = force * dx / d
					gy = force * dy / d
					grad[a1][0] += gx * step_size
					grad[a1][1] += gy * step_size
					grad[a2][0] -= gx * step_size
					grad[a2][1] -= gy * step_size

			# apply gradients and check convergence
			max_grad = 0
			for v in self.mol.vertices:
				if v.x is None:
					continue
				gx, gy = grad[v]
				mag = sqrt(gx * gx + gy * gy)
				if mag > max_grad:
					max_grad = mag
				v.x += gx
				v.y += gy

			if max_grad < converge_threshold:
				break


#============================================
def calculate_coords(mol, bond_length: float = 1.0, force: int = 0) -> None:
	"""Module-level convenience function matching coords_generator signature."""
	g = CoordsGenerator2(bond_length=bond_length)
	g.calculate_coords(mol, bond_length=bond_length, force=force)
