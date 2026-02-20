"""Phase 4: Force-field refinement for 2D coordinate generation.

Simple steepest-descent refinement using a spring model with bond stretch,
angle bend, and non-bonded repulsion terms. Ring atoms receive reduced
forces to preserve ring geometry.
"""

from math import pi, sqrt, sin


#============================================
def force_refine(gen) -> None:
	"""Simple steepest-descent refinement using spring model.

	Energy terms:
	- Bond stretch: Hookean spring toward target bond length
	- Angle bend: penalty for deviation from ideal angles
	- Non-bonded repulsion: repulsive term for close non-bonded pairs

	Ring atoms receive reduced forces (pinned factor) to preserve geometry.

	Args:
		gen: CoordsGenerator2 instance with mol, bond_length, ring_atoms.
	"""
	if len(gen.mol.vertices) < 2:
		return

	k_bond = 1.0
	k_angle = 0.3
	k_repel = 0.5
	step_size = 0.05
	max_iters = 200
	converge_threshold = 1e-4
	# ring atoms get much smaller forces to preserve ring geometry
	ring_pin_factor = 0.05

	# precompute ideal angles per atom
	ideal_angles = _compute_ideal_angles(gen)

	# precompute non-bonded pairs (separated by 4+ bonds)
	# must exclude up to 3 bonds: in hexagonal rings, para atoms are 3
	# bonds apart at distance sqrt(3)*bond_length ~ 1.73, which falls
	# within the repulsion cutoff and would distort ring geometry
	bonded_or_close = {}
	for v in gen.mol.vertices:
		near = {v}
		near.update(v.neighbors)
		for n in v.neighbors:
			near.update(n.neighbors)
		# extend to 3 bonds
		near_copy = set(near)
		for n in near_copy:
			near.update(n.neighbors)
		bonded_or_close[v] = near

	for _iteration in range(max_iters):
		# compute gradients
		grad = {}
		for v in gen.mol.vertices:
			grad[v] = [0.0, 0.0]

		# bond stretch
		_apply_bond_stretch(gen, grad, k_bond, step_size)

		# angle bend
		_apply_angle_bend(gen, grad, ideal_angles, k_angle, step_size)

		# non-bonded repulsion
		_apply_repulsion(gen, grad, bonded_or_close, k_repel, step_size)

		# apply gradients with ring atom pinning and clamping
		max_grad = 0
		# clamp maximum step to prevent divergence
		max_step = 0.5 * gen.bond_length
		for v in gen.mol.vertices:
			if v.x is None:
				continue
			gx, gy = grad[v]
			# reduce force on ring atoms to preserve geometry
			if v in gen.ring_atoms:
				gx *= ring_pin_factor
				gy *= ring_pin_factor
			mag = sqrt(gx * gx + gy * gy)
			# clamp large gradients to prevent divergence
			if mag > max_step:
				gx *= max_step / mag
				gy *= max_step / mag
				mag = max_step
			if mag > max_grad:
				max_grad = mag
			v.x += gx
			v.y += gy

		if max_grad < converge_threshold:
			break


#============================================
def _compute_ideal_angles(gen) -> dict:
	"""Compute ideal bond angles for each atom.

	For ring atoms, uses the ring internal angle formula:
	ideal = pi * (n - 2) / n where n is the ring size.

	For non-ring atoms, uses standard hybridization angles.

	Args:
		gen: CoordsGenerator2 instance.

	Returns:
		Dict mapping atom -> ideal angle in radians.
	"""
	ideal_angles = {}
	# build ring size lookup for ring atoms
	ring_sizes = {}
	for ring in gen.rings:
		size = len(ring)
		for atom in ring:
			# use the largest ring this atom belongs to
			if atom not in ring_sizes or size > ring_sizes[atom]:
				ring_sizes[atom] = size

	for v in gen.mol.vertices:
		n_neighbors = len(v.neighbors)
		if n_neighbors <= 1:
			continue

		# ring atoms: use ring geometry
		if v in ring_sizes:
			ring_size = ring_sizes[v]
			ideal_angles[v] = pi * (ring_size - 2) / ring_size
			continue

		# non-ring atoms: use hybridization
		has_triple = any(e.order >= 3 for e in v.neighbor_edges)
		if has_triple:
			ideal_angles[v] = pi  # 180 degrees
		elif n_neighbors == 2:
			ideal_angles[v] = 2 * pi / 3  # 120 degrees
		elif n_neighbors == 3:
			ideal_angles[v] = 2 * pi / 3  # 120 degrees
		else:
			ideal_angles[v] = pi / 2  # 90 for 4+ neighbors

	return ideal_angles


#============================================
def _apply_bond_stretch(gen, grad: dict, k_bond: float,
	step_size: float) -> None:
	"""Apply bond stretch gradient to all edges.

	Args:
		gen: CoordsGenerator2 instance.
		grad: gradient dict to update in place.
		k_bond: bond spring constant.
		step_size: gradient step size.
	"""
	for b in gen.mol.edges:
		a1, a2 = b.vertices
		if a1.x is None or a2.x is None:
			continue
		dx = a1.x - a2.x
		dy = a1.y - a2.y
		d = sqrt(dx * dx + dy * dy)
		if d < 1e-8:
			continue
		dd = d - gen.bond_length
		# gradient of 0.5*k*(d-d0)^2
		gx = k_bond * dd * dx / d
		gy = k_bond * dd * dy / d
		grad[a1][0] -= gx * step_size
		grad[a1][1] -= gy * step_size
		grad[a2][0] += gx * step_size
		grad[a2][1] += gy * step_size


#============================================
def _apply_angle_bend(gen, grad: dict, ideal_angles: dict,
	k_angle: float, step_size: float) -> None:
	"""Apply angle bend gradient for ideal angles.

	Args:
		gen: CoordsGenerator2 instance.
		grad: gradient dict to update in place.
		ideal_angles: dict mapping atom -> ideal angle in radians.
		k_angle: angle spring constant.
		step_size: gradient step size.
	"""
	for v in gen.mol.vertices:
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
				# ideal distance between n1 and n2 at ideal angle
				ideal_dist = 2 * gen.bond_length * sin(ideal / 2)
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


#============================================
def _apply_repulsion(gen, grad: dict, bonded_or_close: dict,
	k_repel: float, step_size: float) -> None:
	"""Apply non-bonded repulsion gradient.

	Args:
		gen: CoordsGenerator2 instance.
		grad: gradient dict to update in place.
		bonded_or_close: dict mapping atom -> set of bonded/close atoms.
		k_repel: repulsion constant.
		step_size: gradient step size.
	"""
	atoms = gen.mol.vertices
	n_atoms = len(atoms)
	repel_dist = 1.8 * gen.bond_length
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
