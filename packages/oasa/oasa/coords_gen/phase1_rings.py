"""Phase 1: Ring system placement for 2D coordinate generation.

Finds SSSR rings, groups them into ring systems, and places them using
regular polygon geometry with BFS ring-fusion expansion.
"""

from math import pi, cos, sin, atan2

from oasa import geometry
from oasa.coords_gen import helpers
from oasa.coords_gen import ring_templates


#============================================
def find_ring_systems(rings: list) -> list:
	"""Group SSSR rings that share atoms into ring systems.

	Args:
		rings: list of rings, each a list of atom objects.

	Returns:
		List of ring systems, each a list of rings (lists of atoms).
	"""
	if not rings:
		return []
	# build adjacency: ring i shares atoms with ring j
	ring_sets = [set(r) for r in rings]
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
		systems.append([rings[idx] for idx in system])
	return systems


#============================================
def place_ring_systems(gen, placed: set) -> set:
	"""Place all ring systems, returning updated placed set.

	Args:
		gen: CoordsGenerator2 instance.
		placed: set of already-placed atoms.

	Returns:
		Updated set of placed atoms.
	"""
	ring_systems = find_ring_systems(gen.rings)
	if not ring_systems:
		return placed

	# sort ring systems: largest first for best backbone
	ring_systems.sort(key=lambda rs: sum(len(r) for r in rs), reverse=True)

	# place the first (largest) system unconditionally
	placed = _place_ring_system(gen, ring_systems[0], placed)

	# remaining systems: place if anchored, defer if not
	for ring_system in ring_systems[1:]:
		all_ring_atoms = set()
		for ring in ring_system:
			all_ring_atoms.update(ring)
		anchor = _find_external_anchor(all_ring_atoms, placed)
		if anchor:
			placed = _place_ring_system(gen, ring_system, placed)
		else:
			gen.deferred_ring_systems.append(ring_system)
	return placed


#============================================
def place_deferred_ring_system(gen, ring_system: list, placed: set) -> set:
	"""Place a previously-deferred ring system now that an anchor exists.

	Called by Phase 2 when chain expansion reaches an atom adjacent to
	an unplaced ring system.

	Args:
		gen: CoordsGenerator2 instance.
		ring_system: list of rings in this system.
		placed: set of already-placed atoms.

	Returns:
		Updated set of placed atoms.
	"""
	return _place_ring_system(gen, ring_system, placed)


#============================================
def _place_ring_system(gen, ring_system: list, placed: set) -> set:
	"""Place a single ring system (list of rings sharing atoms).

	First tries template lookup for cage molecules (cubane, adamantane).
	Falls back to BFS from the largest ring outward to place fused rings.

	Args:
		gen: CoordsGenerator2 instance.
		ring_system: list of rings in this system.
		placed: set of already-placed atoms.

	Returns:
		Updated set of placed atoms.
	"""
	if not ring_system:
		return placed

	# collect all atoms in this ring system
	all_ring_atoms = set()
	for ring in ring_system:
		all_ring_atoms.update(ring)

	# try template placement if no atoms in this system already placed
	if not (all_ring_atoms & placed):
		if _try_template_placement(gen, all_ring_atoms, placed):
			placed.update(all_ring_atoms)
			# flag so Phase 5 can skip PCA for template-placed molecules
			gen.template_used = True
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
		first_sorted = gen.mol.sort_vertices_in_path(list(first_ring))
		if first_sorted is None:
			first_sorted = list(first_ring)
		size = len(first_sorted)
		radius = helpers.side_length_to_radius(gen.bond_length, size)

		# check if any ring atom has an already-placed neighbor outside this system
		anchor = _find_external_anchor(all_ring_atoms, placed)
		if anchor:
			# position ring system relative to placed neighbor
			ring_atom, placed_nb = anchor
			_place_polygon_anchored(
				gen, first_sorted, ring_atom, placed_nb, radius
			)
		else:
			# no external connections yet, place at origin
			coords = helpers.regular_polygon_coords(size, 0.0, 0.0, radius)
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
			_place_fused_ring(gen, ring, shared_with_placed, placed)
			placed.update(ring)
			ring_placed[i] = True
			changed = True

	return placed


#============================================
def _find_external_anchor(ring_atoms: set, placed: set) -> tuple:
	"""Find a ring atom with an already-placed neighbor outside the ring system.

	Args:
		ring_atoms: set of all atoms in this ring system.
		placed: set of already-placed atoms.

	Returns:
		Tuple (ring_atom, placed_neighbor) or None.
	"""
	for atom in ring_atoms:
		for nb in atom.neighbors:
			if nb in placed and nb not in ring_atoms:
				return (atom, nb)
	return None


#============================================
def _place_polygon_anchored(gen, ring_sorted: list, ring_atom,
	placed_nb, radius: float) -> None:
	"""Place a ring polygon so ring_atom is at correct distance from placed_nb.

	Positions the ring center away from placed_nb so the polygon opens
	outward, preventing overlap with the already-placed ring system.

	Args:
		gen: CoordsGenerator2 instance.
		ring_sorted: ordered list of atoms in the ring.
		ring_atom: atom in the ring connected to placed_nb.
		placed_nb: already-placed atom outside the ring.
		radius: circumscribed radius for the polygon.
	"""
	size = len(ring_sorted)
	# find index of ring_atom in the sorted ring
	ring_idx = 0
	for i, a in enumerate(ring_sorted):
		if a is ring_atom:
			ring_idx = i
			break

	# compute direction away from placed_nb's existing neighbors
	away_angle = _compute_away_angle(placed_nb, set(), gen.bond_length)

	# place ring_atom at bond_length from placed_nb in away direction
	target_x = placed_nb.x + gen.bond_length * cos(away_angle)
	target_y = placed_nb.y + gen.bond_length * sin(away_angle)

	# ring center goes further in the away direction from ring_atom
	cx = target_x + radius * cos(away_angle)
	cy = target_y + radius * sin(away_angle)

	# angle from center back to ring_atom (vertex 0 of our polygon)
	angle_to_v = atan2(target_y - cy, target_x - cx)

	# generate polygon vertices with vertex ring_idx at the target position
	coords = []
	for i in range(size):
		# offset by ring_idx so vertex ring_idx lands at target
		angle = angle_to_v + 2 * pi * (i - ring_idx) / size
		x = cx + radius * cos(angle)
		y = cy + radius * sin(angle)
		coords.append((x, y))

	for i, atom_obj in enumerate(ring_sorted):
		atom_obj.x, atom_obj.y = coords[i]


#============================================
def _compute_away_angle(atom, exclude_atoms: set,
	bond_length: float) -> float:
	"""Compute an angle pointing away from atom's placed neighbors.

	Args:
		atom: atom object with x, y coordinates.
		exclude_atoms: atoms to ignore when computing direction.
		bond_length: current bond length (unused but kept for interface).

	Returns:
		Angle in radians pointing away from existing neighbors.
	"""
	placed_nbs = [
		nb for nb in atom.neighbors
		if nb.x is not None and nb.y is not None and nb not in exclude_atoms
	]
	if placed_nbs:
		# circular mean of neighbor angles, then go opposite
		# naive arithmetic mean fails when angles straddle the
		# 0/2pi boundary (e.g., avg of 0 and 240deg gives 120deg
		# instead of correct 300deg)
		sum_cos = 0.0
		sum_sin = 0.0
		for nb in placed_nbs:
			a = helpers.angle_from_east(nb.x - atom.x, nb.y - atom.y)
			sum_cos += cos(a)
			sum_sin += sin(a)
		avg = atan2(sum_sin, sum_cos)
		return avg + pi
	# default: go right
	return 0.0


#============================================
def _place_fused_ring(gen, ring: list, shared_atoms: set,
	placed: set) -> None:
	"""Place a ring that shares atoms with already-placed atoms.

	Handles edge-fused (2 shared), spiro (1 shared), and
	bridged (3+ shared) cases.

	Args:
		gen: CoordsGenerator2 instance.
		ring: list of atoms in the ring.
		shared_atoms: atoms shared with already-placed rings.
		placed: set of all placed atoms.
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
		_place_spiro_ring(gen, ring, shared_list[0], placed)
	elif n_shared == 2:
		# edge-fused: two shared atoms forming a shared edge
		_place_edge_fused_ring(gen, ring, shared_list, placed)
	else:
		# bridged or multi-fused: 3+ shared atoms
		_place_bridged_ring(gen, ring, already_placed, placed)


#============================================
def _place_spiro_ring(gen, ring: list, shared_atom, placed: set) -> None:
	"""Place a ring connected via a single spiro atom.

	Generates a perfect regular polygon centered so that vertex 0
	coincides exactly with the spiro atom, oriented away from
	existing placed atoms.

	Args:
		gen: CoordsGenerator2 instance.
		ring: list of atoms in the ring.
		shared_atom: the single shared spiro atom.
		placed: set of all placed atoms.
	"""
	v = shared_atom
	ring_sorted = gen.mol.sort_vertices_in_path(list(ring), start_from=v)
	if ring_sorted is None:
		ring_sorted = list(ring)
		# ensure v is first
		if v in ring_sorted:
			ring_sorted.remove(v)
			ring_sorted.insert(0, v)
	size = len(ring_sorted)

	radius = helpers.side_length_to_radius(gen.bond_length, size)

	# find angle away from existing neighbors of the spiro atom
	placed_neighbors = [a for a in v.neighbors if a in placed and a not in ring]
	if placed_neighbors:
		# circular mean of placed neighbor angles, go opposite
		sum_cos = 0.0
		sum_sin = 0.0
		for n in placed_neighbors:
			a = helpers.angle_from_east(n.x - v.x, n.y - v.y)
			sum_cos += cos(a)
			sum_sin += sin(a)
		avg = atan2(sum_sin, sum_cos)
		away_angle = avg + pi
	else:
		away_angle = pi / 2

	# place polygon center at radius distance from v in the away direction
	cx = v.x + radius * cos(away_angle)
	cy = v.y + radius * sin(away_angle)

	# angle from center back to the spiro atom (vertex 0)
	angle_to_v = atan2(v.y - cy, v.x - cx)

	# generate polygon vertices starting from the angle that points to v
	# this guarantees vertex 0 is exactly at (v.x, v.y)
	coords = []
	for i in range(size):
		angle = angle_to_v + 2 * pi * i / size
		x = cx + radius * cos(angle)
		y = cy + radius * sin(angle)
		coords.append((x, y))

	# assign coordinates; skip the spiro atom (vertex 0 = v)
	for j, atom_obj in enumerate(ring_sorted):
		if atom_obj is v:
			continue
		atom_obj.x, atom_obj.y = coords[j]


#============================================
def _place_edge_fused_ring(gen, ring: list, shared_list: list,
	placed: set) -> None:
	"""Place a ring sharing an edge (2 atoms) with placed atoms.

	Uses Transform2D to generate a perfect polygon and align it
	so the shared edge matches the already-placed atoms.

	Args:
		gen: CoordsGenerator2 instance.
		ring: list of atoms in the ring.
		shared_list: the two shared atoms.
		placed: set of all placed atoms.
	"""
	v1, v2 = shared_list[0], shared_list[1]
	ring_sorted = gen.mol.sort_vertices_in_path(list(ring), start_from=v1)
	if ring_sorted is None:
		ring_sorted = list(ring)

	ring_size = len(ring)

	# find v2's position in ring_sorted (v1 is at index 0)
	v2_idx = None
	for i, a in enumerate(ring_sorted):
		if a is v2:
			v2_idx = i
			break

	# determine which side of the shared edge the existing ring is on
	side = 0
	for a in placed:
		if a in (v1, v2):
			continue
		if a.x is None or a.y is None:
			continue
		s = geometry.on_which_side_is_point(
			(v1.x, v1.y, v2.x, v2.y), (a.x, a.y)
		)
		side += s

	# generate perfect polygon at origin
	radius = helpers.side_length_to_radius(gen.bond_length, ring_size)
	poly = helpers.regular_polygon_coords(ring_size, 0.0, 0.0, radius)

	# map polygon edge to the shared edge (v1, v2)
	# v1 is ring_sorted[0] -> poly[0]
	# v2 is ring_sorted[v2_idx] -> poly[v2_idx]
	# the shared edge in the polygon is poly[0]-poly[v2_idx]
	transform = helpers.Transform2D()
	transform.set_transform_two_points(
		(v1.x, v1.y), (v2.x, v2.y),
		poly[0], poly[v2_idx]
	)

	# apply transform to all polygon vertices
	transformed = [transform.transform_point(x, y) for x, y in poly]

	# check if the ring is on the wrong side; if so, reflect
	tcx = sum(x for x, y in transformed) / ring_size
	tcy = sum(y for x, y in transformed) / ring_size
	ring_side = geometry.on_which_side_is_point(
		(v1.x, v1.y, v2.x, v2.y), (tcx, tcy)
	)
	# ring should be on opposite side of existing atoms
	if ring_side != 0 and side != 0 and ring_side * side > 0:
		# reflect all transformed coords across the shared edge
		transformed = [
			helpers.reflect_point(x, y, v1.x, v1.y, v2.x, v2.y)
			for x, y in transformed
		]

	# assign only unplaced atoms; skip v1 and v2 to preserve shared edge
	for i, atom_obj in enumerate(ring_sorted):
		if atom_obj is v1 or atom_obj is v2:
			continue
		atom_obj.x, atom_obj.y = transformed[i]


#============================================
def _place_bridged_ring(gen, ring: list, already_placed: list,
	placed: set) -> None:
	"""Place a ring with 3+ shared atoms (bridged system).

	Args:
		gen: CoordsGenerator2 instance.
		ring: list of atoms in the ring.
		already_placed: atoms in this ring that already have coords.
		placed: set of all placed atoms.
	"""
	to_place = [a for a in ring if a.x is None or a.y is None]
	if not to_place:
		return

	# sort already-placed atoms into a path
	sorted_back = gen.mol.sort_vertices_in_path(already_placed)
	if not sorted_back:
		# fall back: just spread atoms evenly
		sorted_back = already_placed

	to_place_sorted = gen.mol.sort_vertices_in_path(to_place)
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
	ca = helpers.deg_to_rad(
		180 - (overall_angle - blocked_angle - n_to_place * da) / 2
	)
	if side > 0:
		ca = -ca
	ca += helpers.angle_from_east(v1.x - v2.x, v1.y - v2.y)

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
		x += gen.bond_length * cos(angle)
		y += gen.bond_length * sin(angle)
		angle += helpers.deg_to_rad(ext_angle)

	# scale bond length to close the ring
	target_dist = helpers.point_dist(v1.x, v1.y, v2.x, v2.y)
	actual_dist = helpers.point_dist(v1.x, v1.y, x, y)
	if actual_dist > 1e-6:
		bl = gen.bond_length * target_dist / actual_dist
	else:
		bl = gen.bond_length

	# actual placement
	angle = ca
	x, y = v1.x, v1.y
	for atom_obj in to_place_sorted:
		x += bl * cos(angle)
		y += bl * sin(angle)
		atom_obj.x = x
		atom_obj.y = y
		angle += helpers.deg_to_rad(ext_angle)


#============================================
def _try_template_placement(gen, ring_atoms: set, placed: set) -> bool:
	"""Try to place ring system atoms using a pre-computed template.

	Builds the adjacency graph for the ring system (only intra-ring bonds)
	and looks up a matching template. If found, assigns template coordinates
	scaled to the current bond_length.

	Args:
		gen: CoordsGenerator2 instance.
		ring_atoms: set of atom objects in the ring system.
		placed: set of already-placed atoms.

	Returns:
		True if a template was matched and coordinates applied.
	"""
	atoms = list(ring_atoms)
	n = len(atoms)
	# build adjacency within ring system only
	atom_to_idx = {}
	for i, a in enumerate(atoms):
		atom_to_idx[a] = i
	adj = {}
	for i, a in enumerate(atoms):
		adj[i] = set()
		for nb in a.neighbors:
			if nb in atom_to_idx:
				adj[i].add(atom_to_idx[nb])
	# look up matching template
	result = ring_templates.find_template(n, adj)
	if result is None:
		return False
	template, mapping = result
	coords = template["coords"]

	# compute raw positions scaled to bond_length
	raw_positions = {}
	for i, atom_obj in enumerate(atoms):
		template_idx = mapping[i]
		x, y = coords[template_idx]
		raw_positions[atom_obj] = (x * gen.bond_length, y * gen.bond_length)

	# check if any atom has an already-placed neighbor outside the ring system
	anchor = _find_external_anchor(ring_atoms, placed)
	if anchor:
		# position template relative to placed neighbor
		ring_atom, placed_nb = anchor
		rx, ry = raw_positions[ring_atom]
		# target position for ring_atom
		away_angle = _compute_away_angle(placed_nb, ring_atoms, gen.bond_length)
		target_x = placed_nb.x + gen.bond_length * cos(away_angle)
		target_y = placed_nb.y + gen.bond_length * sin(away_angle)
		# translate all positions
		offset_x = target_x - rx
		offset_y = target_y - ry
		for atom_obj in atoms:
			ox, oy = raw_positions[atom_obj]
			atom_obj.x = ox + offset_x
			atom_obj.y = oy + offset_y
	else:
		# no anchor, place at raw positions (centered near origin)
		for atom_obj in atoms:
			atom_obj.x, atom_obj.y = raw_positions[atom_obj]

	return True
