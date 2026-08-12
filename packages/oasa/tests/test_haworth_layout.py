"""Smoke tests for Haworth ring layout and bond tagging."""

# Standard Library
import os

# Third Party
import pytest

import oasa
import oasa.atom_lib
import oasa.bond_lib
import oasa.cdml
import oasa.cdml_document
import oasa.cdml_writer
import oasa.molecule_lib
from oasa.haworth import layout as haworth_layout
from oasa.haworth import renderer as haworth_renderer
from oasa.haworth import renderer_layout as haworth_renderer_layout
from oasa.haworth.spec import HaworthSpec
from oasa.render_lib.data_types import BondRenderContext
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.bond_ops import build_bond_ops
from oasa import render_ops
from oasa import render_out


#============================================
@pytest.fixture
def output_dir(request: object, tmp_path: object) -> object:
	if request.config.getoption("save"):
		return os.getcwd()
	return tmp_path


#============================================
def output_path(output_dir: object, filename: object) -> object:
	return os.path.join(str(output_dir), filename)


#============================================
def build_ring(size: object, oxygen_index: object = None) -> object:
	mol = oasa.molecule_lib.Molecule()
	atoms = []
	for idx in range(size):
		symbol = 'C'
		if oxygen_index is not None and idx == oxygen_index:
			symbol = 'O'
		a = oasa.atom_lib.Atom(symbol=symbol)
		a.x = idx * 20
		a.y = 0
		mol.add_vertex(a)
		atoms.append(a)
	for idx in range(size):
		bond = oasa.bond_lib.Bond(order=1, type='n')
		v1 = atoms[idx]
		v2 = atoms[(idx + 1) % size]
		bond.vertices = (v1, v2)
		mol.add_edge(v1, v2, bond)
	return mol


#============================================
def test_haworth_pyranose_layout_and_tags() -> None:
	mol = build_ring(6)
	result = haworth_layout.build_haworth(mol, mode="pyranose")
	assert len(result["ring_atoms"]) == 6
	front_types = [b.type for b in result["ring_bonds"] if b.type in ("w", "q")]
	assert front_types.count("w") == 2
	assert front_types.count("q") == 1
	y_vals = [a.y for a in result["ring_atoms"]]
	x_vals = [a.x for a in result["ring_atoms"]]
	assert max(y_vals) - min(y_vals) > 0
	assert max(x_vals) - min(x_vals) > 0


#============================================
def test_haworth_furanose_layout_and_tags() -> None:
	mol = build_ring(5)
	result = haworth_layout.build_haworth(mol, mode="furanose")
	assert len(result["ring_atoms"]) == 5
	front_types = [b.type for b in result["ring_bonds"] if b.type in ("w", "q")]
	assert front_types.count("w") == 2
	assert front_types.count("q") == 1


#============================================
def test_scaled_haworth_label_target_matches_the_painted_scale() -> None:
	"""A selected smaller label reserves smaller connector and lane geometry."""
	job = {
		"vertex": (0.0, 0.0),
		"dx": 1.0,
		"dy": 0.0,
		"length": 20.0,
		"label": "OH",
		"anchor": "start",
		"direction": "up",
		"font_size": 12.0,
		"text_scale": 0.9,
	}
	scaled_target = haworth_renderer_layout.job_text_target(job, job["length"])
	full_target = haworth_renderer_layout.job_text_target(
		{**job, "text_scale": 1.0}, job["length"]
	)
	assert scaled_target.box is not None
	assert full_target.box is not None
	assert (scaled_target.box[2] - scaled_target.box[0]) < (full_target.box[2] - full_target.box[0])


#============================================
def _simple_layout_job(label: str) -> dict:
	"""Build one generic simple-label geometry request without ring metadata."""
	return {
		"carbon": 1,
		"direction": "up",
		"vertex": (0.0, 20.0),
		"dx": 0.0,
		"dy": -1.0,
		"length": 10.0,
		"label": label,
		"connector_width": 1.2,
		"font_size": 12.0,
		"font_name": "sans-serif",
		"anchor": "middle",
		"line_color": "#000",
		"label_color": "#000",
	}


#============================================
def test_simple_layout_uses_blocked_geometry_to_choose_a_longer_lane() -> None:
	"""Any simple label clears a blocked target by choosing the shortest legal lane."""
	job = _simple_layout_job("QX7")
	blocked = haworth_renderer_layout.job_text_target(job, job["length"])
	resolved = haworth_renderer_layout.resolve_hydroxyl_layout_jobs(
		[job], blocked_targets=(blocked,)
	)
	assert resolved[0]["length"] > job["length"]


#============================================
def test_simple_layout_scores_caller_presentations_without_token_policy() -> None:
	"""Caller-authored text and scale options are selected only by their geometry."""
	job = _simple_layout_job("ABCDEFGHI")
	job["label_candidates"] = ("ABCDEFGHI", "Q")
	job["text_scales"] = (1.0, 0.90)
	blocked = make_box_target((-30.0, -2.0, 30.0, 11.0))
	resolved = haworth_renderer_layout.resolve_hydroxyl_layout_jobs(
		[job], blocked_targets=(blocked,)
	)
	assert resolved[0]["label"] == "Q"
	assert resolved[0]["text_scale"] in (0.90, 1.0)


#============================================
def test_simple_label_selection_matches_vertical_painted_geometry() -> None:
	"""A vertical presentation candidate stays clear after its final alignment."""
	spec = HaworthSpec(
		ring_type="furanose",
		anomeric="alpha",
		substituents={
			"C1_up": "OH", "C1_down": "H",
			"C2_up": "CH3", "C2_down": "H",
			"C3_up": "OH", "C3_down": "H",
			"C4_up": "H", "C4_down": "H",
		},
		carbon_count=4,
		title="generic-placement",
	)
	first = haworth_renderer.render(spec)
	second = haworth_renderer.render(spec)
	assert first == second
	haworth_renderer.strict_validate_ops(first, "generic-placement")


#============================================
def test_furanose_branch_labels_use_generic_clear_geometry() -> None:
	"""A real two-carbon tail has deterministic, non-overlapping label paint."""
	first = haworth_renderer.render_from_code("ARLRDM", "furanose", "alpha")
	second = haworth_renderer.render_from_code("ARLRDM", "furanose", "alpha")
	assert first == second
	haworth_renderer.strict_validate_ops(first, "ARLRDM")


#============================================
def test_haworth_places_oxygen_at_top() -> None:
	mol = build_ring(6, oxygen_index=0)
	result = haworth_layout.build_haworth(mol, mode="pyranose")
	oxygen_atoms = [a for a in result["ring_atoms"] if a.symbol == 'O']
	assert len(oxygen_atoms) == 1
	oxygen = oxygen_atoms[0]
	min_y = min(a.y for a in result["ring_atoms"])
	assert abs(oxygen.y - min_y) < 0.0001


#============================================
def test_haworth_places_furanose_oxygen_at_top() -> None:
	mol = build_ring(5, oxygen_index=0)
	result = haworth_layout.build_haworth(mol, mode="furanose")
	oxygen_atoms = [a for a in result["ring_atoms"] if a.symbol == 'O']
	assert len(oxygen_atoms) == 1
	oxygen = oxygen_atoms[0]
	min_y = min(a.y for a in result["ring_atoms"])
	assert abs(oxygen.y - min_y) < 0.0001


#============================================
def test_haworth_pyranose_oxygen_not_first() -> None:
	"""Test oxygen placement when oxygen is not at index 0."""
	mol = build_ring(6, oxygen_index=2)
	result = haworth_layout.build_haworth(mol, mode="pyranose")
	oxygen_atoms = [a for a in result["ring_atoms"] if a.symbol == 'O']
	assert len(oxygen_atoms) == 1
	oxygen = oxygen_atoms[0]
	# Oxygen should still be at the top (minimum y)
	min_y = min(a.y for a in result["ring_atoms"])
	assert abs(oxygen.y - min_y) < 0.0001


#============================================
def test_haworth_furanose_oxygen_not_first() -> None:
	"""Test oxygen placement when oxygen is not at index 0."""
	mol = build_ring(5, oxygen_index=3)
	result = haworth_layout.build_haworth(mol, mode="furanose")
	oxygen_atoms = [a for a in result["ring_atoms"] if a.symbol == 'O']
	assert len(oxygen_atoms) == 1
	oxygen = oxygen_atoms[0]
	# Oxygen should still be at the top (minimum y)
	min_y = min(a.y for a in result["ring_atoms"])
	assert abs(oxygen.y - min_y) < 0.0001


#============================================
def test_haworth_svg_smoke(output_dir: object) -> None:
	pyranose = _build_haworth_smoke_mol()
	svg_path = output_path(output_dir, "haworth_layout_smoke.svg")
	render_out.mol_to_output(pyranose, svg_path, format="svg")
	assert os.path.isfile(svg_path)
	assert os.path.getsize(svg_path) > 0
	with open(svg_path, "r", encoding="utf-8") as handle:
		svg_text = handle.read()
	assert "<path" in svg_text


#============================================
def test_haworth_cairo_smoke(output_dir: object) -> None:
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
def test_haworth_front_edge_and_wedges() -> None:
	pyranose = build_ring(6)
	result = haworth_layout.build_haworth(pyranose, mode="pyranose")
	_assert_front_edge_and_wedges(result)

	furanose = build_ring(5)
	result = haworth_layout.build_haworth(furanose, mode="furanose")
	_assert_front_edge_and_wedges(result)


#============================================
def test_reflected_haworth_wedges_keep_front_endpoints_after_cdml_authority() -> None:
	"""A reflected real Haworth layout retains its directed wedge depiction."""
	molecule = build_ring(6, oxygen_index=2)
	haworth_layout.build_haworth(molecule, mode="pyranose")
	_flip_y(molecule)
	for index, atom in enumerate(molecule.vertices, start=1):
		atom.id = f"haworth_a{index}"
	writer_cdml = oasa.cdml_writer.mol_to_text(molecule)
	oasa.cdml_document.CDMLDocument.parse(writer_cdml, validation="strict")
	writer_reloaded = next(oasa.cdml.read_cdml(writer_cdml))
	proposal = oasa.cdml_writer.molecules_to_insertion_proposal(
		[writer_reloaded], token_stem="reflected_haworth",
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<cdml version="26.07" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml"/>',
	)
	accepted = session.insert_molecules(
		oasa.cdml_document.CDMLMoleculeInsertionRequest(
			expected_revision=session.revision,
			proposal_cdml=proposal,
			label="Reflected Haworth",
		),
	)
	oasa.cdml_document.CDMLDocument.parse(accepted.cdml, validation="strict")
	authoritative_reloaded = next(oasa.cdml.read_cdml(accepted.cdml))
	assert (
		_wedges_end_at_haworth_front(writer_reloaded),
		_wedges_end_at_haworth_front(authoritative_reloaded),
	) == (True, True)


#============================================
def _wedges_end_at_haworth_front(molecule: object) -> bool:
	"""Return whether every Haworth wedge base ends at a q-front vertex."""
	front_vertices = {
		vertex
		for bond in molecule.edges
		if bond.type == "q"
		for vertex in bond.vertices
	}
	wedge_bonds = [bond for bond in molecule.edges if bond.type == "w"]
	return bool(wedge_bonds) and all(
		bond.vertices[1] in front_vertices for bond in wedge_bonds
	)


#============================================
def _assert_front_edge_and_wedges(result: object) -> None:
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
def _build_haworth_smoke_mol() -> object:
	pyranose = build_ring(6, oxygen_index=0)
	haworth_layout.build_haworth(pyranose, mode="pyranose")

	furanose = build_ring(5, oxygen_index=0)
	haworth_layout.build_haworth(furanose, mode="furanose")
	max_x = max(atom.x for atom in pyranose.vertices)
	min_x = min(atom.x for atom in pyranose.vertices)
	offset = (max_x - min_x) + 50.0
	for atom in furanose.vertices:
		atom.x += offset
	pyranose.insert_a_graph(furanose)
	return pyranose


#============================================
def _flip_y(mol: object) -> None:
	for atom in mol.vertices:
		atom.y = -atom.y


#============================================
def test_haworth_substituent_orientation_ops_alpha() -> None:
	mol = build_ring(6, oxygen_index=2)
	layout = haworth_layout.build_haworth(mol, mode="pyranose")
	ring_atoms = layout["ring_atoms"]
	anomeric_atom, reference_atom = _find_haworth_reference_atoms(ring_atoms)
	an_sub, an_bond = _add_substituent(mol, anomeric_atom, "O")
	ref_sub, ref_bond = _add_substituent(mol, reference_atom, "C")
	haworth_layout.place_substituents(mol, ring_atoms, series="D", stereo="alpha", bond_length=30)
	_assert_substituent_direction(anomeric_atom, an_sub, an_bond, expect="down")
	_assert_substituent_direction(reference_atom, ref_sub, ref_bond, expect="up")


#============================================
def test_haworth_substituent_orientation_ops_beta() -> None:
	mol = build_ring(6, oxygen_index=2)
	layout = haworth_layout.build_haworth(mol, mode="pyranose")
	ring_atoms = layout["ring_atoms"]
	anomeric_atom, reference_atom = _find_haworth_reference_atoms(ring_atoms)
	an_sub, an_bond = _add_substituent(mol, anomeric_atom, "O")
	ref_sub, ref_bond = _add_substituent(mol, reference_atom, "C")
	haworth_layout.place_substituents(mol, ring_atoms, series="L", stereo="beta", bond_length=30)
	_assert_substituent_direction(reference_atom, ref_sub, ref_bond, expect="down")
	_assert_substituent_direction(anomeric_atom, an_sub, an_bond, expect="down")


#============================================
def _find_haworth_reference_atoms(ring_atoms: object) -> object:
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
def _add_substituent(mol: object, ring_atom: object, symbol: object) -> object:
	sub = oasa.atom_lib.Atom(symbol=symbol)
	sub.x = ring_atom.x
	sub.y = ring_atom.y
	mol.add_vertex(sub)
	bond = oasa.bond_lib.Bond(order=1, type="n")
	bond.vertices = (ring_atom, sub)
	mol.add_edge(ring_atom, sub, bond)
	return sub, bond


#============================================
def _assert_substituent_direction(ring_atom: object, sub_atom: object, bond: object, expect: object) -> None:
	context = BondRenderContext(
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
	ops = build_bond_ops(bond, start, end, context)
	line_ops = [op for op in ops if isinstance(op, render_ops.LineOp)]
	if not line_ops:
		raise AssertionError("Expected LineOp for substituent bond")
	dy = line_ops[0].p2[1] - line_ops[0].p1[1]
	if expect == "up":
		assert dy < 0
	else:
		assert dy > 0
