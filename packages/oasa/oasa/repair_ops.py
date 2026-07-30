"""Pure repair algorithms for molecular geometry normalization.

All functions operate on OASA-compatible molecule objects (anything with
the standard vertex/edge interface: .atoms, .neighbors, .degree, .x, .y,
.get_smallest_independent_cycles()) and modify atom coordinates in-place.

No BKChem, GUI, or canvas code lives here.  This module sits alongside
coords_generator.py as pure graph-geometry operations.
"""

# Standard Library
import math
import collections

# local repo modules
import oasa.hex_grid


#============================================
def _get_ring_atoms(mol: object) -> set:
	"""Return all atoms that belong to at least one ring.

	Args:
		mol: An OASA-compatible molecule object.

	Returns:
		Set of atom objects that are part of a ring.
	"""
	ring_atoms = set()
	cycles = mol.get_smallest_independent_cycles()
	for cycle in cycles:
		ring_atoms.update(cycle)
	return ring_atoms


#============================================
def _collect_subtree(root: object, excluded_parent: object, already_visited: set) -> list:
	"""Collect all atoms in the subtree rooted at root, not crossing excluded_parent.

	This includes root itself plus all atoms reachable from root
	without going through already_visited nodes (except root).

	Args:
		root: Starting atom for subtree collection.
		excluded_parent: The parent atom not to traverse back to.
		already_visited: Set of atoms already visited in the main BFS.

	Returns:
		List of atom objects in the subtree.
	"""
	subtree = [root]
	sub_visited = {root, excluded_parent}
	sub_queue = collections.deque([root])
	while sub_queue:
		current = sub_queue.popleft()
		for neighbor in current.neighbors:
			if neighbor in sub_visited:
				continue
			# only follow neighbors not yet in BFS visited set
			if neighbor in already_visited:
				continue
			sub_visited.add(neighbor)
			subtree.append(neighbor)
			sub_queue.append(neighbor)
	return subtree


#============================================
def _collect_non_ring_subtree(root: object, excluded: object, ring_atoms: set) -> list:
	"""Collect all atoms in a subtree that are not ring atoms.

	Args:
		root: Starting atom.
		excluded: Atom not to traverse back to.
		ring_atoms: Set of ring atoms to avoid crossing into.

	Returns:
		List of non-ring atoms in the subtree (includes root).
	"""
	subtree = [root]
	visited = {root, excluded}
	queue = collections.deque([root])
	while queue:
		current = queue.popleft()
		for neighbor in current.neighbors:
			if neighbor in visited or neighbor in ring_atoms:
				continue
			visited.add(neighbor)
			subtree.append(neighbor)
			queue.append(neighbor)
	return subtree


#============================================
def _collect_angle_subtree(
		root: object, excluded_parent: object, already_visited: set, ring_atoms: set,
		) -> list:
	"""Collect movable angle-repair descendants without crossing a ring anchor.

	Args:
		root: Starting non-ring atom for the movable subtree.
		excluded_parent: Parent atom on the already-processed edge.
		already_visited: Atoms reached by the angle-repair BFS.
		ring_atoms: Fixed coordinate anchors in the molecule.

	Returns:
		List of non-ring, not-yet-visited atoms translated with ``root``.
	"""
	subtree = [root]
	visited = {root, excluded_parent}
	queue = collections.deque([root])
	while queue:
		current = queue.popleft()
		for neighbor in current.neighbors:
			if neighbor in visited or neighbor in already_visited or neighbor in ring_atoms:
				continue
			visited.add(neighbor)
			subtree.append(neighbor)
			queue.append(neighbor)
	return subtree


#============================================
def _get_non_ring_components(
		mol: object, ring_atoms: set[object],
		) -> list[tuple[list[object], set[object]]]:
	"""Return source-ordered non-ring components and their fixed ring anchors.

	Args:
		mol: An OASA-compatible molecule object.
		ring_atoms: Atoms whose coordinates are fixed by ring membership.

	Returns:
		Source-ordered component atoms paired with their adjacent ring atoms.
	"""
	components = []
	visited = set()
	for start in mol.atoms:
		if start in ring_atoms or start in visited:
			continue
		component_atoms = {start}
		anchors = set()
		visited.add(start)
		queue = collections.deque([start])
		while queue:
			atom = queue.popleft()
			for neighbor in atom.neighbors:
				if neighbor in ring_atoms:
					anchors.add(neighbor)
					continue
				if neighbor not in visited:
					visited.add(neighbor)
					component_atoms.add(neighbor)
					queue.append(neighbor)
		components.append((
			[atom for atom in mol.atoms if atom in component_atoms], anchors,
		))
	return components


#============================================
def validate_bond_angle_normalization_topology(mol: object) -> None:
	"""Reject movable components constrained by multiple fixed ring anchors.

	Angle normalization keeps every atom participating in an independent cycle
	fixed.  A connected component of the remaining graph may be translated from
	zero or one such anchor.  Two anchors constrain its coordinates from both
	sides, so the bounded rigid-subtree operation has no unambiguous legal move.

	Args:
		mol: An OASA-compatible molecule object.

	Raises:
		ValueError: A non-ring component is adjacent to multiple ring atoms.
	"""
	ring_atoms = _get_ring_atoms(mol)
	for _component, anchors in _get_non_ring_components(mol, ring_atoms):
		if len(anchors) > 1:
			raise ValueError(
				"bond-angle normalization does not support a non-ring component "
				"attached to multiple ring anchors",
			)


#============================================
def _snap_angle_to_60_slot(angle: float) -> int:
	"""Return nearest canonical 60-degree slot, with half slots rounding forward.

	An exact half slot advances toward the increasing-angle slot: 30 degrees
	selects 60 degrees, 90 degrees selects 120 degrees, and 330 degrees wraps
	to zero degrees.  The integer calculation keeps that authored rule stable
	across the circular zero/360-degree boundary.
	"""
	step = math.pi / 3.0
	scaled_slot = (angle % (2 * math.pi)) / step
	lower_slot = math.floor(scaled_slot)
	return int(lower_slot + (scaled_slot - lower_slot >= 0.5)) % 6


#============================================
def _slot_angle(slot: int) -> float:
	"""Return the radians for one canonical 60-degree slot index."""
	return (slot % 6) * math.pi / 3.0


#============================================
def _order_ring_atoms(ring_set: set, mol: object) -> list:
	"""Order ring atoms by walking bond connectivity.

	Given a set of atoms in a ring, return them in connected order
	by following bonds.

	Args:
		ring_set: Set of atom objects forming a ring.
		mol: The molecule containing these atoms.

	Returns:
		List of atoms in ring-walk order.
	"""
	ring_list = list(ring_set)
	if len(ring_list) <= 2:
		return ring_list
	# start from the first atom and walk neighbors that are in the ring
	ordered = [ring_list[0]]
	visited = {ring_list[0]}
	while len(ordered) < len(ring_list):
		current = ordered[-1]
		found_next = False
		for neighbor in current.neighbors:
			if neighbor in ring_set and neighbor not in visited:
				ordered.append(neighbor)
				visited.add(neighbor)
				found_next = True
				break
		if not found_next:
			break
	return ordered


#============================================
def _normalize_lengths_bfs(mol: object, bond_length: float) -> None:
	"""BFS-based bond length normalization for a single molecule.

	Picks the highest-degree atom as root and walks outward.  For
	each BFS edge the child atom is repositioned to be exactly
	bond_length away from its parent in the existing direction.

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Desired bond length.
	"""
	atoms = mol.atoms
	if len(atoms) < 2:
		return
	# identify ring atoms so we can skip ring closure edges
	ring_atoms = _get_ring_atoms(mol)
	# pick the root: highest degree atom
	root = max(atoms, key=lambda a: a.degree)
	visited = {root}
	queue = collections.deque([root])
	while queue:
		parent = queue.popleft()
		for neighbor in parent.neighbors:
			if neighbor in visited:
				continue
			visited.add(neighbor)
			# skip repositioning if both atoms are in a ring together
			# (ring geometry handled by normalize_rings)
			if parent in ring_atoms and neighbor in ring_atoms:
				queue.append(neighbor)
				continue
			# compute current direction from parent to neighbor
			dx = neighbor.x - parent.x
			dy = neighbor.y - parent.y
			dist = math.sqrt(dx * dx + dy * dy)
			if dist < 1e-6:
				# degenerate: atoms at same position, push east
				dx = bond_length
				dy = 0.0
			else:
				# scale direction vector to target length
				scale = bond_length / dist
				dx *= scale
				dy *= scale
			# shift the neighbor and everything beyond it
			shift_x = parent.x + dx - neighbor.x
			shift_y = parent.y + dy - neighbor.y
			# collect the subtree rooted at neighbor (excluding parent side)
			subtree = _collect_subtree(neighbor, parent, visited)
			for atom in subtree:
				atom.x += shift_x
				atom.y += shift_y
			queue.append(neighbor)


#============================================
def _normalize_angles_bfs(mol: object, bond_length: float) -> None:
	"""Normalize each non-ring component from its deterministic fixed root.

	A ring-anchored component starts at its ring-adjacent atom, retaining its
	fixed incoming bond direction.  An unanchored component starts at its
	highest-degree source-order atom.  Both then distribute outgoing bonds to
	the nearest 60-degree slots.

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Fallback distance for a degenerate outgoing vector.
	"""
	atoms = mol.atoms
	if len(atoms) < 2:
		return
	ring_atoms = _get_ring_atoms(mol)
	for component, anchors in _get_non_ring_components(mol, ring_atoms):
		component_set = set(component)
		anchor = next(iter(anchors), None)
		if anchor is None:
			root = max(component, key=lambda atom: atom.degree)
			incoming_parent = None
		else:
			root = next(neighbor for neighbor in anchor.neighbors if neighbor in component_set)
			incoming_parent = anchor
		visited = {root}
		queue = collections.deque([(root, incoming_parent)])
		while queue:
			parent, incoming_parent = queue.popleft()
			children = [
				neighbor for neighbor in parent.neighbors
				if neighbor in component_set and neighbor not in visited
			]
			# Child order is the graph/CDML source order exposed by ``neighbors``.
			# It gives an authored, deterministic owner to a contested slot.
			# Fixed ring-anchor and incoming-edge directions reserve their nearest
			# slots before movable non-ring children are assigned.
			used_slots = set()
			if incoming_parent is not None:
				incoming_angle = math.atan2(
					incoming_parent.y - parent.y, incoming_parent.x - parent.x,
				)
				used_slots.add(_snap_angle_to_60_slot(incoming_angle))
			for neighbor in parent.neighbors:
				if neighbor not in ring_atoms:
					continue
				ring_angle = math.atan2(neighbor.y - parent.y, neighbor.x - parent.x)
				used_slots.add(_snap_angle_to_60_slot(ring_angle))
			for child in children:
				dx = child.x - parent.x
				dy = child.y - parent.y
				slot = _snap_angle_to_60_slot(math.atan2(dy, dx))
				for _attempt in range(6):
					if slot not in used_slots:
						break
					slot = (slot + 1) % 6
				else:
					raise ValueError("bond-angle normalization has no free 60-degree slot")
				used_slots.add(slot)
				snapped = _slot_angle(slot)
				# compute distance from parent to child
				dx = child.x - parent.x
				dy = child.y - parent.y
				dist = math.sqrt(dx * dx + dy * dy)
				if dist < 1e-6:
					dist = bond_length
				# reposition child at the snapped angle
				new_x = parent.x + dist * math.cos(snapped)
				new_y = parent.y + dist * math.sin(snapped)
				shift_x = new_x - child.x
				shift_y = new_y - child.y
				# Move only the non-ring portion of the unvisited subtree.  A ring
				# coordinate is an anchor even when the root is outside that ring.
				subtree = _collect_angle_subtree(child, parent, visited, ring_atoms)
				for atom in subtree:
					atom.x += shift_x
					atom.y += shift_y
				visited.add(child)
				queue.append((child, parent))


#============================================
def _normalize_rings_for_mol(mol: object, bond_length: float) -> None:
	"""Normalize all rings in a single molecule to regular polygons.

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Standard bond length.
	"""
	cycles = mol.get_smallest_independent_cycles()
	if not cycles:
		return
	# collect all ring atoms for later substituent repositioning
	all_ring_atoms = set()
	for cycle in cycles:
		all_ring_atoms.update(cycle)
	for cycle in cycles:
		ring_atoms = _order_ring_atoms(set(cycle), mol)
		n = len(ring_atoms)
		if n < 3:
			continue
		# compute the current centroid
		cx = sum(a.x for a in ring_atoms) / n
		cy = sum(a.y for a in ring_atoms) / n
		# radius for a regular polygon with side length = bond_length
		# side = 2 * R * sin(pi / N)  =>  R = side / (2 * sin(pi / N))
		radius = bond_length / (2 * math.sin(math.pi / n))
		# start angle: angle from centroid to first atom
		start_angle = math.atan2(ring_atoms[0].y - cy, ring_atoms[0].x - cx)
		# place atoms evenly around the circle
		# store old positions to compute shifts for substituents
		old_positions = {a: (a.x, a.y) for a in ring_atoms}
		for i, atom in enumerate(ring_atoms):
			angle = start_angle + 2 * math.pi * i / n
			atom.x = cx + radius * math.cos(angle)
			atom.y = cy + radius * math.sin(angle)
		# reposition substituents (non-ring neighbors) via shift
		for atom in ring_atoms:
			old_x, old_y = old_positions[atom]
			shift_x = atom.x - old_x
			shift_y = atom.y - old_y
			if abs(shift_x) < 1e-6 and abs(shift_y) < 1e-6:
				continue
			# move non-ring subtrees attached to this ring atom
			for neighbor in atom.neighbors:
				if neighbor in all_ring_atoms:
					continue
				subtree = _collect_non_ring_subtree(neighbor, atom, all_ring_atoms)
				for sub_atom in subtree:
					sub_atom.x += shift_x
					sub_atom.y += shift_y


#============================================
def _straighten_bonds_for_mol(mol: object) -> None:
	"""Straighten terminal bonds in a single molecule.

	For each degree-1 atom, snap the bond to its neighbor to the
	nearest 30-degree multiple.

	Args:
		mol: An OASA-compatible molecule object.
	"""
	for atom in mol.atoms:
		if atom.degree != 1:
			continue
		# this is a terminal atom
		neighbor = atom.neighbors[0]
		dx = atom.x - neighbor.x
		dy = atom.y - neighbor.y
		dist = math.sqrt(dx * dx + dy * dy)
		if dist < 1e-6:
			continue
		# current angle from neighbor to atom
		angle = math.atan2(dy, dx)
		# snap to nearest 30-degree (pi/6) multiple
		step = math.pi / 6.0
		snapped = round(angle / step) * step
		# reposition the terminal atom
		atom.x = neighbor.x + dist * math.cos(snapped)
		atom.y = neighbor.y + dist * math.sin(snapped)


#============================================
def normalize_bond_lengths(mol: object, bond_length: float) -> None:
	"""Normalize eligible non-ring bonds while preserving ring geometry.

	Walks the molecular graph from the highest-degree atom outward,
	adjusting eligible neighbor distances while preserving direction. Ring
	geometry and ring closure edges remain unchanged.

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Desired bond length.
	"""
	_normalize_lengths_bfs(mol, bond_length)


#============================================
def normalize_bond_angles(mol: object, bond_length: float) -> None:
	"""Round non-ring bond angles to nearest 60-degree multiple.

	Ring atoms remain fixed anchors.  Each supported non-ring component has at
	most one ring anchor; multiply anchored components raise ``ValueError``.
	Outgoing bonds use source order, reserve fixed and incoming directions, and
	advance to the next free 60-degree slot when their nearest slot is occupied.

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Fallback distance for a degenerate outgoing vector.

	Raises:
		ValueError: The topology has no unambiguous supported angle repair.
	"""
	validate_bond_angle_normalization_topology(mol)
	_normalize_angles_bfs(mol, bond_length)


#============================================
def normalize_rings(mol: object, bond_length: float) -> None:
	"""Reshape each ring to a regular polygon centered on its centroid.

	Detects rings via get_smallest_independent_cycles(), then places
	ring atoms evenly on a circle with radius derived from the
	bond length.  Substituents are repositioned via BFS from ring
	atoms outward.

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Standard bond length.
	"""
	_normalize_rings_for_mol(mol, bond_length)


#============================================
def straighten_bonds(mol: object) -> None:
	"""Snap terminal and chain bond angles to nearest 30-degree direction.

	For degree-1 atoms (terminals), the bond angle is adjusted to
	the nearest multiple of 30 degrees.

	Args:
		mol: An OASA-compatible molecule object.
	"""
	_straighten_bonds_for_mol(mol)


#============================================
def snap_to_hex_grid(mol: object, bond_length: float) -> None:
	"""Move every atom to the nearest hex grid point.

	Uses oasa.hex_grid.find_best_grid_origin to choose the optimal
	grid alignment, then snaps each atom.  After snapping, translates
	the molecule so the result aligns with the displayed (0,0) grid.

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Hex grid spacing (typically the standard bond length).
	"""
	atom_coords = [(a.x, a.y) for a in mol.atoms]
	if len(atom_coords) < 1:
		return
	# find best grid origin for this molecule
	origin_x, origin_y = oasa.hex_grid.find_best_grid_origin(
		atom_coords, bond_length
	)
	# snap all atoms to the best-fit grid
	snapped = oasa.hex_grid.snap_molecule_to_hex_grid(
		atom_coords, bond_length, origin_x, origin_y
	)
	# translate so snapped coords align with the displayed (0,0) grid;
	# find nearest (0,0) grid point to the best-fit origin and shift
	# the molecule by the difference
	aligned_ox, aligned_oy = oasa.hex_grid.snap_to_hex_grid(
		origin_x, origin_y, bond_length
	)
	shift_x = aligned_ox - origin_x
	shift_y = aligned_oy - origin_y
	for atom, (new_x, new_y) in zip(mol.atoms, snapped):
		atom.x = new_x + shift_x
		atom.y = new_y + shift_y
