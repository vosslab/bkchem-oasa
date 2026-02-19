"""Smoke tests for Haworth ring layout and bond tagging."""

# Standard Library
import os

# Third Party
import pytest

import oasa
from oasa import haworth
from oasa import render_geometry
from oasa import render_ops
from oasa import render_out


#============================================
@pytest.fixture
def output_dir(request, tmp_path):
	if request.config.getoption("save"):
		return os.getcwd()
	return tmp_path


#============================================
def output_path(output_dir, filename):
	return os.path.join(str(output_dir), filename)


#============================================
def build_ring(size, oxygen_index=None):
	mol = oasa.Molecule()
	atoms = []
	for idx in range(size):
		symbol = 'C'
		if oxygen_index is not None and idx == oxygen_index:
			symbol = 'O'
		a = oasa.Atom(symbol=symbol)
		a.x = idx * 20
		a.y = 0
		mol.add_vertex(a)
		atoms.append(a)
	for idx in range(size):
		bond = oasa.Bond(order=1, type='n')
		v1 = atoms[idx]
		v2 = atoms[(idx + 1) % size]
		bond.vertices = (v1, v2)
		mol.add_edge(v1, v2, bond)
	return mol


#============================================
def test_haworth_pyranose_layout_and_tags():
	mol = build_ring(6)
	result = haworth.build_haworth(mol, mode="pyranose")
	assert len(result["ring_atoms"]) == 6
	front_types = [b.type for b in result["ring_bonds"] if b.type in ("w", "q")]
	assert front_types.count("w") == 2
	assert front_types.count("q") == 1
	y_vals = [a.y for a in result["ring_atoms"]]
	x_vals = [a.x for a in result["ring_atoms"]]
	assert max(y_vals) - min(y_vals) > 0
	assert max(x_vals) - min(x_vals) > 0


#============================================
def test_haworth_furanose_layout_and_tags():
	mol = build_ring(5)
	result = haworth.build_haworth(mol, mode="furanose")
	assert len(result["ring_atoms"]) == 5
	front_types = [b.type for b in result["ring_bonds"] if b.type in ("w", "q")]
	assert front_types.count("w") == 2
	assert front_types.count("q") == 1


#============================================
def test_haworth_places_oxygen_at_top():
	mol = build_ring(6, oxygen_index=0)
	result = haworth.build_haworth(mol, mode="pyranose")
	oxygen_atoms = [a for a in result["ring_atoms"] if a.symbol == 'O']
	assert len(oxygen_atoms) == 1
	oxygen = oxygen_atoms[0]
	min_y = min(a.y for a in result["ring_atoms"])
	assert abs(oxygen.y - min_y) < 0.0001


#============================================
def test_haworth_places_furanose_oxygen_at_top():
	mol = build_ring(5, oxygen_index=0)
	result = haworth.build_haworth(mol, mode="furanose")
	oxygen_atoms = [a for a in result["ring_atoms"] if a.symbol == 'O']
	assert len(oxygen_atoms) == 1
	oxygen = oxygen_atoms[0]
	min_y = min(a.y for a in result["ring_atoms"])
	assert abs(oxygen.y - min_y) < 0.0001


#============================================
def test_haworth_pyranose_oxygen_not_first():
	"""Test oxygen placement when oxygen is not at index 0."""
	mol = build_ring(6, oxygen_index=2)
	result = haworth.build_haworth(mol, mode="pyranose")
	oxygen_atoms = [a for a in result["ring_atoms"] if a.symbol == 'O']
	assert len(oxygen_atoms) == 1
	oxygen = oxygen_atoms[0]
	# Oxygen should still be at the top (minimum y)
	min_y = min(a.y for a in result["ring_atoms"])
	assert abs(oxygen.y - min_y) < 0.0001


#============================================
def test_haworth_furanose_oxygen_not_first():
	"""Test oxygen placement when oxygen is not at index 0."""
	mol = build_ring(5, oxygen_index=3)
	result = haworth.build_haworth(mol, mode="furanose")
	oxygen_atoms = [a for a in result["ring_atoms"] if a.symbol == 'O']
	assert len(oxygen_atoms) == 1
	oxygen = oxygen_atoms[0]
	# Oxygen should still be at the top (minimum y)
	min_y = min(a.y for a in result["ring_atoms"])
	assert abs(oxygen.y - min_y) < 0.0001


#============================================
def test_haworth_svg_smoke(output_dir):
	pyranose = _build_haworth_smoke_mol()
	svg_path = output_path(output_dir, "haworth_layout_smoke.svg")
	render_out.mol_to_output(pyranose, svg_path, format="svg")
	assert os.path.isfile(svg_path)
	assert os.path.getsize(svg_path) > 0
	with open(svg_path, "r", encoding="utf-8") as handle:
		svg_text = handle.read()
	assert "<path" in svg_text


#============================================
def test_haworth_cairo_smoke(output_dir):
	try:
		import cairo
		_ = cairo
	except ImportError:
		pytest.skip("pycairo is required for cairo smoke rendering")

	pyranose = _build_haworth_smoke_mol()
	_flip_y(pyranose)
	png_path = output_path(output_dir, "haworth_layout_smoke.png")
	render_out.mol_to_output(pyranose, png_path, format="png")
	assert os.path.isfile(png_path)
	assert os.path.getsize(png_path) > 0


#============================================
def test_haworth_front_edge_and_wedges():
	pyranose = build_ring(6)
	result = haworth.build_haworth(pyranose, mode="pyranose")
	_assert_front_edge_and_wedges(result)

	furanose = build_ring(5)
	result = haworth.build_haworth(furanose, mode="furanose")
	_assert_front_edge_and_wedges(result)


#============================================
def _assert_front_edge_and_wedges(result):
	ring_bonds = result["ring_bonds"]
	front_bonds = [bond for bond in ring_bonds if bond.type == "q"]
	assert len(front_bonds) == 1
	front_bond = front_bonds[0]
	front_mid_y = (front_bond.vertices[0].y + front_bond.vertices[1].y) / 2.0
	mid_ys = [(bond.vertices[0].y + bond.vertices[1].y) / 2.0 for bond in ring_bonds]
	assert front_mid_y >= max(mid_ys) - 0.0001
	front_vertices = set(front_bond.vertices)
	wedge_bonds = [bond for bond in ring_bonds if bond.type == "w"]
	assert len(wedge_bonds) == 2
	for bond in wedge_bonds:
		v1, v2 = bond.vertices
		assert v2 in front_vertices
		assert v2.y >= v1.y


#============================================
def _build_haworth_smoke_mol():
	pyranose = build_ring(6, oxygen_index=0)
	haworth.build_haworth(pyranose, mode="pyranose")

	furanose = build_ring(5, oxygen_index=0)
	haworth.build_haworth(furanose, mode="furanose")
	max_x = max(atom.x for atom in pyranose.vertices)
	min_x = min(atom.x for atom in pyranose.vertices)
	offset = (max_x - min_x) + 50.0
	for atom in furanose.vertices:
		atom.x += offset
	pyranose.insert_a_graph(furanose)
	return pyranose


#============================================
def _flip_y(mol):
	for atom in mol.vertices:
		atom.y = -atom.y


#============================================
def test_haworth_substituent_orientation_ops_alpha():
	mol = build_ring(6, oxygen_index=2)
	layout = haworth.build_haworth(mol, mode="pyranose")
	ring_atoms = layout["ring_atoms"]
	anomeric_atom, reference_atom = _find_haworth_reference_atoms(ring_atoms)
	an_sub, an_bond = _add_substituent(mol, anomeric_atom, "O")
	ref_sub, ref_bond = _add_substituent(mol, reference_atom, "C")
	haworth.place_substituents(mol, ring_atoms, series="D", stereo="alpha", bond_length=30)
	_assert_substituent_direction(anomeric_atom, an_sub, an_bond, expect="down")
	_assert_substituent_direction(reference_atom, ref_sub, ref_bond, expect="up")


#============================================
def test_haworth_substituent_orientation_ops_beta():
	mol = build_ring(6, oxygen_index=2)
	layout = haworth.build_haworth(mol, mode="pyranose")
	ring_atoms = layout["ring_atoms"]
	anomeric_atom, reference_atom = _find_haworth_reference_atoms(ring_atoms)
	an_sub, an_bond = _add_substituent(mol, anomeric_atom, "O")
	ref_sub, ref_bond = _add_substituent(mol, reference_atom, "C")
	haworth.place_substituents(mol, ring_atoms, series="L", stereo="beta", bond_length=30)
	_assert_substituent_direction(reference_atom, ref_sub, ref_bond, expect="down")
	_assert_substituent_direction(anomeric_atom, an_sub, an_bond, expect="down")


#============================================
def _find_haworth_reference_atoms(ring_atoms):
	oxygen_index = None
	for idx, atom in enumerate(ring_atoms):
		if atom.symbol == "O":
			oxygen_index = idx
			break
	if oxygen_index is None:
		raise ValueError("Ring oxygen was not found for substituent placement")
	ring_size = len(ring_atoms)
	anomeric_index = (oxygen_index + 1) % ring_size
	reference_index = (oxygen_index - 1) % ring_size
	return ring_atoms[anomeric_index], ring_atoms[reference_index]


#============================================
def _add_substituent(mol, ring_atom, symbol):
	sub = oasa.Atom(symbol=symbol)
	sub.x = ring_atom.x
	sub.y = ring_atom.y
	mol.add_vertex(sub)
	bond = oasa.Bond(order=1, type="n")
	bond.vertices = (ring_atom, sub)
	mol.add_edge(ring_atom, sub, bond)
	return sub, bond


#============================================
def _assert_substituent_direction(ring_atom, sub_atom, bond, expect):
	context = render_geometry.BondRenderContext(
		molecule=None,
		line_width=2.0,
		bond_width=6.0,
		wedge_width=6.0,
		bold_line_width_multiplier=1.2,
		bond_second_line_shortening=0.0,
		color_bonds=False,
		atom_colors=None,
		shown_vertices=set(),
		bond_coords=None,
		bond_coords_provider=None,
		point_for_atom=None,
	)
	start = (ring_atom.x, ring_atom.y)
	end = (sub_atom.x, sub_atom.y)
	ops = render_geometry.build_bond_ops(bond, start, end, context)
	line_ops = [op for op in ops if isinstance(op, render_ops.LineOp)]
	if not line_ops:
		raise AssertionError("Expected LineOp for substituent bond")
	dy = line_ops[0].p2[1] - line_ops[0].p1[1]
	if expect == "up":
		assert dy < 0
	else:
		assert dy > 0
