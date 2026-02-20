"""Pre-computed 2D coordinate templates for common polycyclic ring systems.

Provides template matching for polycyclic molecules that algorithmic
ring-fusion approaches handle poorly. Templates give correct 2D layouts
without algorithmic complexity.

Templates are loaded from templates.smi (one CXSMILES per line) and
parsed at import time using oasa.smiles_lib.cxsmiles_to_mol(). This
builds the molecular graph and applies coordinates in one step, keeping
atom indices consistent with the coordinate block.

Template data comes from the RDKit molecular_templates repository:
  https://github.com/rdkit/molecular_templates
The templates.smi file is the upstream source format (one CXSMILES per
line, no blank lines). Do not edit by hand.
"""

# Standard Library
import os
from math import sqrt


# ============================================
# Template storage
# ============================================

# list of registered template dicts, each with:
#   name: str -- human-readable name (SMILES string)
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
# Load CXSMILES templates from .smi file
# ============================================

_smi_path = os.path.join(os.path.dirname(__file__), "templates.smi")
with open(_smi_path) as _f:
	# one CXSMILES per line, skip blank lines
	_CXSMILES_TEMPLATES = [line.strip() for line in _f if line.strip()]


# ============================================
# Parse CXSMILES at module load
# ============================================

def _mol_to_template_data(mol) -> tuple:
	"""Extract adjacency dict and coordinates from an OASA molecule.

	Args:
		mol: OASA molecule with x, y coordinates set on vertices.

	Returns:
		Tuple of (adj_dict, coords_list).
	"""
	n_atoms = len(mol.vertices)
	# build adjacency dict from molecule edges
	adj = {}
	for i in range(n_atoms):
		adj[i] = set()
	# map vertex objects to integer indices
	vtx_to_idx = {}
	for i, v in enumerate(mol.vertices):
		vtx_to_idx[v] = i
	for edge in mol.edges:
		a, b = edge.vertices
		i = vtx_to_idx[a]
		j = vtx_to_idx[b]
		adj[i].add(j)
		adj[j].add(i)
	# extract coordinates in vertex order
	coords = [(v.x, v.y) for v in mol.vertices]
	return (adj, coords)


# register all CXSMILES templates using proper CXSMILES parser
import oasa.smiles_lib
for _cxsmi in _CXSMILES_TEMPLATES:
	try:
		# parse CXSMILES: builds molecule graph and applies coordinates
		_mol = oasa.smiles_lib.cxsmiles_to_mol(_cxsmi)
		_smiles = _cxsmi[:_cxsmi.index(" |(")]
		_adj, _coords = _mol_to_template_data(_mol)
		_register(_smiles, _adj, _coords)
	except Exception:
		# skip templates OASA cannot parse
		pass


# ============================================
# Graph isomorphism (backtracking with degree pruning)
# ============================================

#============================================
def _wl_colors(adj: dict, n: int, rounds: int = 4) -> dict:
	"""Compute Weisfeiler-Leman node colors for pruning isomorphism search.

	Each node gets a color based on its local neighborhood structure.
	Nodes with different colors cannot be mapped to each other.

	Args:
		adj: adjacency dict for the graph (node indices 0..n-1).
		n: number of nodes.
		rounds: number of WL refinement rounds.

	Returns:
		Dict mapping node index to its WL color (a hashable value).
	"""
	# initial color = node degree
	color = {i: len(adj[i]) for i in range(n)}
	for _ in range(rounds):
		new_color = {}
		for i in range(n):
			# hash of (own color, sorted neighbor colors)
			nb_colors = tuple(sorted(color[nb] for nb in adj[i]))
			new_color[i] = hash((color[i], nb_colors))
		color = new_color
	return color


#============================================
def _find_isomorphism(adj1: dict, adj2: dict, n: int) -> dict:
	"""Find a node mapping from adj1 to adj2 preserving adjacency.

	Uses backtracking with Weisfeiler-Leman color pruning. WL colors
	encode local neighborhood structure so only structurally compatible
	nodes are considered as mapping candidates, avoiding O(n!) explosion
	on large macrocyclic graphs.

	Args:
		adj1: adjacency dict for graph 1 (node indices 0..n-1).
		adj2: adjacency dict for graph 2 (node indices 0..n-1).
		n: number of nodes (must be same for both graphs).

	Returns:
		Dict mapping graph1 node -> graph2 node, or None if not isomorphic.
	"""
	# compute WL colors for both graphs
	wl1 = _wl_colors(adj1, n)
	wl2 = _wl_colors(adj2, n)
	# quick rejection: color multisets must match
	if sorted(wl1.values()) != sorted(wl2.values()):
		return None
	# for each g1 node, precompute which g2 nodes have matching WL color
	candidates = {}
	for i in range(n):
		candidates[i] = [j for j in range(n) if wl2[j] == wl1[i]]
	# process most constrained nodes first (fewest candidates)
	order = sorted(range(n), key=lambda i: len(candidates[i]))
	mapping = {}
	used = set()

	def backtrack(pos: int) -> bool:
		if pos == n:
			return True
		g1 = order[pos]
		for g2 in candidates[g1]:
			if g2 in used:
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
