# SPDX-License-Identifier: LGPL-3.0-or-later

"""Phase C coverage for render-ops and renderer parity."""

# Standard Library
import io
import json

# Third Party
import pytest

# local repo modules
import oasa
from oasa import haworth
from oasa import render_geometry
from oasa import render_ops
from oasa import render_out


#============================================
def _mol_from_smiles(smiles_text):
	mol = oasa.smiles.text_to_mol(smiles_text)
	assert mol is not None, f"Could not parse SMILES: {smiles_text}"
	oasa.coords_generator.calculate_coords(mol, bond_length=1.0, force=1)
	return mol


#============================================
def _single_bond(v1, v2, bond_type="n"):
	bond = oasa.bond(order=1, type=bond_type)
	bond.vertices = (v1, v2)
	return bond


#============================================
def _build_ring(size, oxygen_index=None):
	mol = oasa.molecule()
	atoms = []
	for idx in range(size):
		symbol = "C"
		if oxygen_index is not None and idx == oxygen_index:
			symbol = "O"
		atom = oasa.atom(symbol=symbol)
		atom.x = float(idx) * 20.0
		atom.y = 0.0
		mol.add_vertex(atom)
		atoms.append(atom)
	for idx in range(size):
		start_atom = atoms[idx]
		end_atom = atoms[(idx + 1) % size]
		mol.add_edge(start_atom, end_atom, _single_bond(start_atom, end_atom, bond_type="n"))
	return mol


#============================================
def _build_labeled_molecule():
	return _mol_from_smiles("CC(O)N")


#============================================
def _build_aromatic_molecule():
	return _mol_from_smiles("C1=CC=CC=C1")


#============================================
def _build_charged_molecule():
	mol = oasa.molecule()
	a1 = oasa.atom(symbol="N")
	a1.x = 0.0
	a1.y = 0.0
	a1.charge = 1
	a2 = oasa.atom(symbol="C")
	a2.x = 40.0
	a2.y = 0.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	mol.add_edge(a1, a2, _single_bond(a1, a2, bond_type="n"))
	return mol


#============================================
def _build_stereo_style_molecule():
	mol = oasa.molecule()
	a1 = oasa.atom(symbol="C")
	a1.x = 0.0
	a1.y = 0.0
	a2 = oasa.atom(symbol="C")
	a2.x = 24.0
	a2.y = 4.0
	a3 = oasa.atom(symbol="C")
	a3.x = -16.0
	a3.y = 20.0
	a4 = oasa.atom(symbol="C")
	a4.x = -16.0
	a4.y = -20.0
	for atom in (a1, a2, a3, a4):
		mol.add_vertex(atom)
	mol.add_edge(a1, a2, _single_bond(a1, a2, bond_type="w"))
	mol.add_edge(a1, a3, _single_bond(a1, a3, bond_type="h"))
	mol.add_edge(a1, a4, _single_bond(a1, a4, bond_type="s"))
	return mol


#============================================
def _build_haworth_molecule(mode):
	mol = _build_ring(6 if mode == "pyranose" else 5, oxygen_index=0)
	haworth.build_haworth(mol, mode=mode)
	return mol


#============================================
def _count_by_kind(payload):
	counts = {
		"line": 0,
		"text": 0,
		"path": 0,
		"polygon": 0,
	}
	for entry in payload:
		kind = entry.get("kind")
		if kind in counts:
			counts[kind] += 1
	return counts


#============================================
def _payload_points(payload):
	points = []
	for entry in payload:
		kind = entry.get("kind")
		if kind == "line":
			points.append(tuple(entry["p1"]))
			points.append(tuple(entry["p2"]))
			continue
		if kind == "polygon":
			for point in entry["points"]:
				points.append(tuple(point))
			continue
		if kind == "path":
			for command, command_points in entry.get("commands", []):
				if command == "Z" or not command_points:
					continue
				for index in range(0, len(command_points) - 1, 2):
					points.append((command_points[index], command_points[index + 1]))
			continue
		if kind == "text":
			points.append((entry["x"], entry["y"]))
			continue
		if kind == "circle":
			cx, cy = entry["center"]
			radius = entry["radius"]
			points.append((cx - radius, cy - radius))
			points.append((cx + radius, cy + radius))
	return points


#============================================
def _global_bbox(payload):
	points = _payload_points(payload)
	if not points:
		return None
	xs = [point[0] for point in points]
	ys = [point[1] for point in points]
	return (min(xs), min(ys), max(xs), max(ys))


#============================================
def _connector_endpoint_set(payload):
	label_ids = {
		entry["id"]
		for entry in payload
		if entry.get("kind") == "text" and "id" in entry
	}
	endpoints = set()
	for entry in payload:
		if entry.get("kind") != "line":
			continue
		op_id = entry.get("id", "")
		if not op_id.endswith("_connector"):
			continue
		label_id = op_id.replace("_connector", "_label")
		if label_id not in label_ids:
			continue
		p2 = tuple(entry["p2"])
		endpoints.add((op_id, p2[0], p2[1]))
	return endpoints


#============================================
def _text_tuple_set(payload):
	text_tuples = set()
	for entry in payload:
		if entry.get("kind") != "text":
			continue
		text_tuples.add(
			(
				entry["text"],
				entry["x"],
				entry["y"],
				entry["anchor"],
				entry["font_size"],
				entry["font_name"],
			)
		)
	return text_tuples


#============================================
def _assert_payload_invariants_equal(svg_payload, cairo_payload):
	assert _count_by_kind(svg_payload) == _count_by_kind(cairo_payload)
	svg_bbox = _global_bbox(svg_payload)
	cairo_bbox = _global_bbox(cairo_payload)
	if svg_bbox is not None and cairo_bbox is not None:
		assert svg_bbox == pytest.approx(cairo_bbox, abs=0.5)
	else:
		assert svg_bbox == cairo_bbox
	svg_ids = {entry[0] for entry in _connector_endpoint_set(svg_payload)}
	cairo_ids = {entry[0] for entry in _connector_endpoint_set(cairo_payload)}
	assert svg_ids == cairo_ids
	assert _text_tuple_set(svg_payload) == _text_tuple_set(cairo_payload)


#============================================
def _canonical_payload(payload):
	return sorted(json.dumps(entry, sort_keys=True) for entry in payload)


#============================================
def _capture_render_out_payloads(monkeypatch, mol, **render_kwargs):
	captured = {}

	def _capture_svg(_parent, ops):
		captured["svg"] = render_ops.ops_to_json_dict(ops, round_digits=3)

	def _capture_cairo(ops, _output_target, _fmt, _width, _height, _options):
		captured["cairo"] = render_ops.ops_to_json_dict(ops, round_digits=3)

	monkeypatch.setattr(render_out.render_ops, "ops_to_svg", _capture_svg)
	monkeypatch.setattr(render_out, "_render_cairo", _capture_cairo)
	render_out.render_to_svg(mol, io.StringIO(), **render_kwargs)
	render_out.render_to_png(mol, io.BytesIO(), scaling=1.0, **render_kwargs)
	assert "svg" in captured
	assert "cairo" in captured
	return captured["svg"], captured["cairo"]


#============================================
def test_molecule_to_ops_fixture_smiles_non_empty():
	fixtures = (
		"C1=CC=CC=C1",  # benzene
		"CC(O)C(=O)O",  # lactic acid
		"NCC(=O)O",  # glycine
		"C1CCCCC1",  # cyclohexane
		"Cn1cnc2n(C)c(=O)n(C)c(=O)c12",  # caffeine
	)
	for smiles_text in fixtures:
		mol = _mol_from_smiles(smiles_text)
		ops = render_geometry.molecule_to_ops(mol)
		assert ops, smiles_text
		assert any(isinstance(op, render_ops.LineOp) for op in ops), smiles_text


#============================================
def test_molecule_to_ops_includes_charge_and_stereo_geometry():
	mol = oasa.molecule()
	a1 = oasa.atom(symbol="N")
	a1.x = 0.0
	a1.y = 0.0
	a1.charge = 1
	a2 = oasa.atom(symbol="C")
	a2.x = 40.0
	a2.y = 0.0
	a3 = oasa.atom(symbol="C")
	a3.x = 12.0
	a3.y = 40.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	mol.add_vertex(a3)
	mol.add_edge(a1, a2, _single_bond(a1, a2, bond_type="w"))
	mol.add_edge(a1, a3, _single_bond(a1, a3, bond_type="h"))
	ops = render_geometry.molecule_to_ops(mol, style={"show_carbon_symbol": True})
	assert any(isinstance(op, render_ops.PolygonOp) for op in ops)
	assert any(isinstance(op, render_ops.TextOp) and "+" in op.text for op in ops)


#============================================
@pytest.mark.parametrize(
	"builder,render_kwargs",
	(
		(_build_labeled_molecule, {"show_carbon_symbol": True}),
		(_build_aromatic_molecule, {"show_carbon_symbol": True}),
		(_build_charged_molecule, {"show_carbon_symbol": True}),
		(_build_stereo_style_molecule, {"show_carbon_symbol": True}),
		(_build_haworth_molecule, {"mode": "pyranose"}),
		(_build_haworth_molecule, {"mode": "furanose"}),
	),
	ids=(
		"simple_shown_labels",
		"aromatic_ring",
		"charged_label",
		"wedge_hashed_wavy",
		"haworth_pyranose",
		"haworth_furanose",
	),
)
def test_svg_and_cairo_paths_receive_same_ops_payload(builder, render_kwargs, monkeypatch):
	if builder is _build_haworth_molecule:
		mol = builder(render_kwargs["mode"])
		svg_payload, cairo_payload = _capture_render_out_payloads(
			monkeypatch,
			mol,
			show_carbon_symbol=True,
		)
	else:
		mol = builder()
		svg_payload, cairo_payload = _capture_render_out_payloads(
			monkeypatch,
			mol,
			**render_kwargs,
		)
	assert _canonical_payload(svg_payload) == _canonical_payload(cairo_payload)
	_assert_payload_invariants_equal(svg_payload, cairo_payload)


#============================================
def test_render_out_executes_svg_and_cairo_paths_when_pycairo_available(monkeypatch):
	try:
		import cairo
		_ = cairo
	except ImportError:
		pytest.skip("pycairo is required for execution-parity test")

	mol = _build_haworth_molecule("pyranose")
	captured = {}
	original_svg = render_out.render_ops.ops_to_svg
	original_cairo = render_out.render_ops.ops_to_cairo

	def _capture_and_draw_svg(parent, ops):
		captured["svg"] = render_ops.ops_to_json_dict(ops, round_digits=3)
		return original_svg(parent, ops)

	def _capture_and_draw_cairo(context, ops):
		captured["cairo"] = render_ops.ops_to_json_dict(ops, round_digits=3)
		return original_cairo(context, ops)

	monkeypatch.setattr(render_out.render_ops, "ops_to_svg", _capture_and_draw_svg)
	monkeypatch.setattr(render_out.render_ops, "ops_to_cairo", _capture_and_draw_cairo)
	render_out.render_to_svg(mol, io.StringIO(), show_carbon_symbol=True)
	render_out.render_to_png(mol, io.BytesIO(), scaling=1.0, show_carbon_symbol=True)
	assert _canonical_payload(captured["svg"]) == _canonical_payload(captured["cairo"])
	_assert_payload_invariants_equal(captured["svg"], captured["cairo"])
