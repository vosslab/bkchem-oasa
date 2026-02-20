"""Tests for cubane 2D coordinate generation.

Verifies that cubane (C12C3C4C1C5C4C3C25) gets correct template-based
coordinates from coords_generator2. The correct SMILES encodes the Q3
hypercube graph (bipartite, 3-regular, 8 vertices, 12 edges).
"""

# Standard Library
import math

import oasa.smiles_lib
import oasa.coords_generator2 as cg2
import oasa.coords_gen.ring_templates as rt

CUBANE_SMILES = "C12C3C4C1C5C4C3C25"
# expected bond angles in the 2D cubane template (degrees from horizontal)
# TemplateSmiles.h coordinates are perspective 3D projections matching
# PubChem's cubane depiction (CID 19137). The layout has horizontal (0),
# vertical (90), and diagonal (~48 degree) cross-braces connecting the
# front and back rectangles of the perspective cube.
EXPECTED_ANGLES = {0.0, 48.0, 90.0}
ANGLE_TOLERANCE = 5.0


#============================================
def _make_cubane():
	"""Parse cubane SMILES and generate 2D coordinates."""
	mol = oasa.smiles_lib.text_to_mol(CUBANE_SMILES, calc_coords=False)
	cg2.calculate_coords(mol, bond_length=1.0, force=1)
	return mol


#============================================
def _build_adjacency(mol) -> dict:
	"""Build adjacency dict from molecule for graph analysis."""
	atom_to_idx = {}
	for i, atom in enumerate(mol.vertices):
		atom_to_idx[id(atom)] = i
	adj = {i: set() for i in range(len(mol.vertices))}
	for bond in mol.edges:
		a1, a2 = bond.vertices
		i = atom_to_idx[id(a1)]
		j = atom_to_idx[id(a2)]
		adj[i].add(j)
		adj[j].add(i)
	return adj


#============================================
def _template_bond_angles(mol) -> list:
	"""Get bond angles from the raw template coords (before PCA rotation).

	Returns list of (unsigned) angles in degrees from horizontal for each
	bond, using the template's original coordinate layout.
	"""
	# build adjacency and find the template match
	atom_to_idx = {}
	for i, atom in enumerate(mol.vertices):
		atom_to_idx[id(atom)] = i
	adj = {i: set() for i in range(len(mol.vertices))}
	for bond in mol.edges:
		a1, a2 = bond.vertices
		adj[atom_to_idx[id(a1)]].add(atom_to_idx[id(a2)])
		adj[atom_to_idx[id(a2)]].add(atom_to_idx[id(a1)])
	result = rt.find_template(len(mol.vertices), adj)
	assert result is not None, "cubane must match a template for angle test"
	template, mapping = result
	coords = template["coords"]
	# compute angles from template coords via mapping
	angles = []
	for bond in mol.edges:
		a1, a2 = bond.vertices
		i1 = atom_to_idx[id(a1)]
		i2 = atom_to_idx[id(a2)]
		t1 = mapping[i1]
		t2 = mapping[i2]
		dx = coords[t2][0] - coords[t1][0]
		dy = coords[t2][1] - coords[t1][1]
		angle = abs(math.degrees(math.atan2(dy, dx)))
		# normalize to 0..90 range
		if angle > 90.0:
			angle = 180.0 - angle
		angles.append(angle)
	return angles


#============================================
class TestCubaneCoordinates:
	def test_cubane_atom_count(self):
		"""Cubane has 8 atoms and 12 bonds."""
		mol = _make_cubane()
		assert len(mol.vertices) == 8
		assert len(mol.edges) == 12

	def test_cubane_template_match(self):
		"""ring_templates.find_template() returns a match for cubane."""
		mol = oasa.smiles_lib.text_to_mol(CUBANE_SMILES, calc_coords=False)
		adj = _build_adjacency(mol)
		result = rt.find_template(len(mol.vertices), adj)
		assert result is not None, "cubane should match a ring template"

	def test_cubane_bond_angles(self):
		"""Template bond angles must be ~0, ~48, or ~90 degrees.

		The cubane 2D template uses a rectangular grid with diagonal crosses.
		Tests the raw template coordinates (not the PCA-rotated output) so
		that Phase 5 PCA rotation cannot mask a broken template.
		"""
		mol = oasa.smiles_lib.text_to_mol(CUBANE_SMILES, calc_coords=False)
		angles = _template_bond_angles(mol)
		bad_bonds = []
		for angle in angles:
			# check if angle is close to any expected value
			match = False
			for expected in EXPECTED_ANGLES:
				if abs(angle - expected) <= ANGLE_TOLERANCE:
					match = True
					break
			if not match:
				bad_bonds.append(
					f"bond angle {angle:.1f} not near any of {EXPECTED_ANGLES}"
				)
		assert not bad_bonds, f"unexpected bond angles: {bad_bonds}"

	def test_cubane_no_long_diagonal_bonds(self):
		"""All bond lengths should be within 4x the shortest bond.

		The RDKit flat rectangular layout has two characteristic lengths:
		short vertical bonds (~0.75) and long horizontal connections
		(~2.25), giving a 3:1 ratio. If the algorithmic fallback produces
		even longer diagonal artifacts, this test catches it.
		"""
		mol = _make_cubane()
		lengths = []
		for bond in mol.edges:
			a1, a2 = bond.vertices
			d = math.sqrt((a1.x - a2.x) ** 2 + (a1.y - a2.y) ** 2)
			lengths.append(d)
		shortest = min(lengths)
		longest = max(lengths)
		ratio = longest / shortest
		assert ratio < 4.0, (
			f"bond length ratio {ratio:.2f} too large "
			f"(shortest={shortest:.3f}, longest={longest:.3f})"
		)

	def test_cubane_bipartite(self):
		"""Cubane molecular graph must be bipartite (Q3 hypercube property).

		This catches the wrong SMILES (C12C3C4C1C5C3C4C25) which produces
		a non-bipartite graph that is NOT cubane.
		"""
		mol = oasa.smiles_lib.text_to_mol(CUBANE_SMILES, calc_coords=False)
		adj = _build_adjacency(mol)
		# BFS 2-coloring to check bipartiteness
		n = len(mol.vertices)
		color = [-1] * n
		color[0] = 0
		queue = [0]
		while queue:
			node = queue.pop(0)
			for neighbor in adj[node]:
				if color[neighbor] == -1:
					color[neighbor] = 1 - color[node]
					queue.append(neighbor)
				elif color[neighbor] == color[node]:
					assert False, "cubane graph is NOT bipartite -- wrong SMILES?"
		# verify all nodes were visited (connected graph)
		assert all(c >= 0 for c in color), "cubane graph is not connected"
