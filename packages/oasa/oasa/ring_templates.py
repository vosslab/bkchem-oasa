"""Pre-computed 2D coordinate templates for common polycyclic ring systems.

Provides template matching for cage molecules (cubane, adamantane, norbornane)
that algorithmic ring-fusion approaches handle poorly. Templates give correct
2D layouts without algorithmic complexity.

Inspired by RDKit's TemplateSmiles.h (75 templates for common ring systems).
Cubane coordinates extracted from RDKit; others hand-tuned for clean layout.
"""

from math import sqrt


# ============================================
# Template storage
# ============================================

# list of registered template dicts, each with:
#   name: str -- human-readable name
#   n_atoms: int -- number of atoms in template
#   n_edges: int -- number of edges in template
#   degrees: tuple -- sorted degree sequence
#   adj: dict {int: set(int)} -- adjacency list (node indices 0..n-1)
#   coords: list of (x, y) tuples -- normalized to avg bond length ~1.0
_TEMPLATES = []


#============================================
def _normalize_coords(coords: list, adj: dict) -> list:
	"""Center coords at origin and scale to average bond length of 1.0.

	Args:
		coords: list of (x, y) coordinate tuples.
		adj: adjacency dict mapping node index to set of neighbor indices.

	Returns:
		List of (x, y) tuples centered at origin, scaled to unit bond length.
	"""
	n = len(coords)
	# center at origin
	cx = sum(x for x, y in coords) / n
	cy = sum(y for x, y in coords) / n
	centered = [(x - cx, y - cy) for x, y in coords]
	# compute average bond length across all edges
	lengths = []
	for i in range(n):
		for j in adj[i]:
			if j > i:
				dx = centered[i][0] - centered[j][0]
				dy = centered[i][1] - centered[j][1]
				lengths.append(sqrt(dx * dx + dy * dy))
	if not lengths:
		return centered
	avg_bl = sum(lengths) / len(lengths)
	if avg_bl < 1e-6:
		return centered
	# scale so average bond length = 1.0
	scaled = [(x / avg_bl, y / avg_bl) for x, y in centered]
	return scaled


#============================================
def _register(name: str, adj: dict, raw_coords: list) -> None:
	"""Register a ring system template.

	Args:
		name: human-readable template name.
		adj: adjacency dict {int: set(int)}, node indices 0..n-1.
		raw_coords: list of (x, y) tuples in template atom order.
	"""
	n = len(raw_coords)
	n_edges = sum(len(adj[i]) for i in range(n)) // 2
	degrees = tuple(sorted(len(adj[i]) for i in range(n)))
	coords = _normalize_coords(raw_coords, adj)
	_TEMPLATES.append({
		"name": name,
		"n_atoms": n,
		"n_edges": n_edges,
		"degrees": degrees,
		"adj": adj,
		"coords": coords,
	})


# ============================================
# Template definitions
# ============================================

# Cubane: C12C3C4C1C5C3C4C25
# 8 atoms, 12 edges, all degree 3
# Coordinates from RDKit TemplateSmiles.h line 90
_register("cubane", {
	0: {1, 4, 6}, 1: {0, 2, 5}, 2: {1, 3, 7}, 3: {2, 5, 6},
	4: {0, 5, 7}, 5: {1, 3, 4}, 6: {0, 3, 7}, 7: {2, 4, 6},
}, [
	(-4.87, 2.71), (-4.87, 4.42), (-3.16, 4.42), (-3.16, 2.71),
	(-3.89, 1.90), (-5.60, 1.90), (-5.60, 3.61), (-3.89, 3.61),
])

# Adamantane: C1C2CC3CC1CC(C2)C3
# 10 atoms, 12 edges: 4 bridgeheads (degree 3) + 6 bridges (degree 2)
# Outer hexagon ring with 3 interior spokes meeting at center
# Hand-tuned 2D projection for non-overlapping layout
_register("adamantane", {
	0: {1, 5}, 1: {0, 2, 8}, 2: {1, 3}, 3: {2, 4, 9},
	4: {3, 5}, 5: {0, 4, 6}, 6: {5, 7}, 7: {6, 8, 9},
	8: {1, 7}, 9: {3, 7},
}, [
	(-0.50, 0.87), (-1.00, 0.00), (-0.50, -0.87),
	(0.50, -0.87), (1.00, 0.00), (0.50, 0.87),
	(0.25, 0.43), (0.00, 0.00), (-0.50, 0.00),
	(0.25, -0.43),
])

# Norbornane (bicyclo[2.2.1]heptane): C1CC2CCC1C2
# 7 atoms, 8 edges: 2 bridgeheads (degree 3) + 5 bridges (degree 2)
# Two fused 5-rings sharing 3 atoms with a bridge
_register("norbornane", {
	0: {1, 5}, 1: {0, 2}, 2: {1, 3, 6}, 3: {2, 4},
	4: {3, 5}, 5: {0, 4, 6}, 6: {2, 5},
}, [
	(0.00, 1.20), (0.80, 0.40), (0.80, -0.50),
	(0.00, -1.20), (-0.80, -0.50), (-0.80, 0.40),
	(0.00, -0.10),
])


# ============================================
# Graph isomorphism (backtracking with degree pruning)
# ============================================

#============================================
def _find_isomorphism(adj1: dict, adj2: dict, n: int) -> dict:
	"""Find a node mapping from adj1 to adj2 preserving adjacency.

	Uses backtracking with degree-based pruning. Efficient for small
	graphs (n <= ~15 atoms).

	Args:
		adj1: adjacency dict for graph 1 (node indices 0..n-1).
		adj2: adjacency dict for graph 2 (node indices 0..n-1).
		n: number of nodes (must be same for both graphs).

	Returns:
		Dict mapping graph1 node -> graph2 node, or None if not isomorphic.
	"""
	deg1 = {i: len(adj1[i]) for i in range(n)}
	deg2 = {i: len(adj2[i]) for i in range(n)}
	# process most constrained nodes first (highest degree)
	order = sorted(range(n), key=lambda i: -deg1[i])
	mapping = {}
	used = set()

	def backtrack(pos: int) -> bool:
		if pos == n:
			return True
		g1 = order[pos]
		g1_deg = deg1[g1]
		for g2 in range(n):
			if g2 in used:
				continue
			if deg2[g2] != g1_deg:
				continue
			# verify consistency with already-mapped neighbors
			ok = True
			for nb in adj1[g1]:
				if nb in mapping:
					if mapping[nb] not in adj2[g2]:
						ok = False
						break
			if not ok:
				continue
			mapping[g1] = g2
			used.add(g2)
			if backtrack(pos + 1):
				return True
			del mapping[g1]
			used.discard(g2)
		return False

	if backtrack(0):
		return dict(mapping)
	return None


# ============================================
# Public lookup API
# ============================================

#============================================
def find_template(n_atoms: int, adj: dict) -> tuple:
	"""Find a matching template for a ring system.

	Args:
		n_atoms: number of atoms in the ring system.
		adj: adjacency dict {int: set(int)} within the ring system.

	Returns:
		Tuple of (template_dict, mapping_dict) if found, None otherwise.
		mapping_dict maps ring system node index -> template node index.
	"""
	n_edges = sum(len(adj[i]) for i in range(n_atoms)) // 2
	degrees = tuple(sorted(len(adj[i]) for i in range(n_atoms)))
	# quick-filter candidates by atom/edge count and degree sequence
	for template in _TEMPLATES:
		if template["n_atoms"] != n_atoms:
			continue
		if template["n_edges"] != n_edges:
			continue
		if template["degrees"] != degrees:
			continue
		# full isomorphism check
		mapping = _find_isomorphism(adj, template["adj"], n_atoms)
		if mapping is not None:
			return (template, mapping)
	return None
