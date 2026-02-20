"""Pure repair algorithms for molecular geometry normalization.

All functions operate on OASA-compatible molecule objects (anything with
the standard vertex/edge interface: .atoms, .neighbors, .degree, .x, .y,
.get_smallest_independent_cycles()) and modify atom coordinates in-place.

No BKChem, GUI, or canvas code lives here.  This module sits alongside
coords_generator.py and coords_optimizer.py as pure graph-geometry
operations.
"""

# Standard Library
import math
import collections

# local repo modules
import oasa.hex_grid


#============================================
def _get_ring_atoms(mol) -> set:
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
def _collect_subtree(root, excluded_parent, already_visited: set) -> list:
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
def _collect_non_ring_subtree(root, excluded, ring_atoms: set) -> list:
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
def _snap_angle_to_60(angle: float) -> float:
	"""Round an angle (radians) to the nearest multiple of 60 degrees.

	Args:
		angle: Angle in radians.

	Returns:
		Nearest multiple of pi/3 (60 degrees) in radians.
	"""
	step = math.pi / 3.0
	# normalize to [0, 2*pi)
	angle = angle % (2 * math.pi)
	snapped = round(angle / step) * step
	return snapped % (2 * math.pi)


#============================================
def _order_ring_atoms(ring_set: set, mol) -> list:
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
def _normalize_lengths_bfs(mol, bond_length: float) -> None:
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
def _normalize_angles_bfs(mol, bond_length: float) -> None:
	"""BFS-based angle normalization for a single molecule.

	From the root atom outward, distribute outgoing bonds to the
	nearest 60-degree slots.

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Standard bond length (used for repositioning).
	"""
	atoms = mol.atoms
	if len(atoms) < 2:
		return
	ring_atoms = _get_ring_atoms(mol)
	# pick the root: highest degree atom
	root = max(atoms, key=lambda a: a.degree)
	visited = {root}
	queue = collections.deque([root])
	while queue:
		parent = queue.popleft()
		# collect unvisited neighbors that are NOT ring-bonded to parent
		children = []
		for neighbor in parent.neighbors:
			if neighbor in visited:
				continue
			# skip ring bonds (both atoms in a ring)
			if parent in ring_atoms and neighbor in ring_atoms:
				visited.add(neighbor)
				queue.append(neighbor)
				continue
			children.append(neighbor)
		if not children:
			continue
		# compute current angles from parent to each child
		child_angles = []
		for child in children:
			dx = child.x - parent.x
			dy = child.y - parent.y
			angle = math.atan2(dy, dx)
			child_angles.append((angle, child))
		# sort by current angle
		child_angles.sort(key=lambda pair: pair[0] % (2 * math.pi))
		# snap each angle to nearest 60-degree slot, avoiding collisions
		used_slots = set()
		for angle, child in child_angles:
			snapped = _snap_angle_to_60(angle)
			# resolve collision: try adjacent slots
			attempts = 0
			step = math.pi / 3.0
			while snapped in used_slots and attempts < 6:
				snapped = (snapped + step) % (2 * math.pi)
				attempts += 1
			used_slots.add(snapped)
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
			# move the entire subtree
			subtree = _collect_subtree(child, parent, visited)
			for atom in subtree:
				atom.x += shift_x
				atom.y += shift_y
			visited.add(child)
			queue.append(child)


#============================================
def _normalize_rings_for_mol(mol, bond_length: float) -> None:
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
def _straighten_bonds_for_mol(mol) -> None:
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
def normalize_bond_lengths(mol, bond_length: float) -> None:
	"""Set all bonds to the standard bond length using BFS.

	Walks the molecular graph from the highest-degree atom outward,
	adjusting each neighbor distance while preserving direction.
	Ring closure edges are left as-is (rings should be normalized
	separately).

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Desired bond length.
	"""
	_normalize_lengths_bfs(mol, bond_length)


#============================================
def normalize_bond_angles(mol, bond_length: float) -> None:
	"""Round non-ring bond angles to nearest 60-degree multiple.

	For each non-ring atom with degree >= 2, outgoing bond angles
	are rounded to the nearest 60-degree slot.  Collisions are
	resolved by shifting to the next available slot.  Ring bonds
	are left alone (handled by normalize_rings).

	Args:
		mol: An OASA-compatible molecule object.
		bond_length: Standard bond length (used for repositioning).
	"""
	_normalize_angles_bfs(mol, bond_length)


#============================================
def normalize_rings(mol, bond_length: float) -> None:
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
def straighten_bonds(mol) -> None:
	"""Snap terminal and chain bond angles to nearest 30-degree direction.

	For degree-1 atoms (terminals), the bond angle is adjusted to
	the nearest multiple of 30 degrees.

	Args:
		mol: An OASA-compatible molecule object.
	"""
	_straighten_bonds_for_mol(mol)


#============================================
def snap_to_hex_grid(mol, bond_length: float) -> None:
	"""Move every atom to the nearest hex grid point.

	Uses oasa.hex_grid.find_best_grid_origin to choose the optimal
	grid alignment, then snaps each atom.

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
	# snap all atoms to the hex grid
	snapped = oasa.hex_grid.snap_molecule_to_hex_grid(
		atom_coords, bond_length, origin_x, origin_y
	)
	for atom, (new_x, new_y) in zip(mol.atoms, snapped):
		atom.x = new_x
		atom.y = new_y
