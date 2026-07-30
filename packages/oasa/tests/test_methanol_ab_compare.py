"""A/B comparison test: methanol rendered with mask vs clipped bond.

Builds methanol (C-O) once and renders two explicit variants:
  A) baseline_masked_full_bond: full-length bond + label mask polygon
  B) clipped_unmasked: shortened bond from real label/attach targets, no mask

Comparisons use direct render-op assertions. This is OASA-level only
(GUI-agnostic) and deterministic.
"""

# Standard Library
import math
import os

# PIP3 modules
from lxml import etree
import pytest

# local repo modules
import file_utils
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
import oasa.render_ops
import oasa.safe_xml
from oasa import dom_extensions
from oasa import svg_out
from oasa.render_lib.bond_ops import build_bond_ops
from oasa.render_lib.data_types import BondRenderContext
from oasa.render_lib.data_types import make_attach_constraints
from oasa.render_lib.molecule_ops import build_label_attach_targets
from oasa.render_lib.molecule_ops import build_vertex_ops

# -- test constants --
_FONT_NAME = "Arial"
_FONT_SIZE = 16.0
_LINE_WIDTH = 2.0
_BOND_WIDTH = 6.0
_WEDGE_WIDTH = 6.0
_BACKGROUND_COLOR = "#ffffff"
_MIN_VISIBLE_BOND_LENGTH = 5.0
_OUTPUT_SVG_A = "methanol_A_mask.svg"
_OUTPUT_SVG_B = "methanol_B_clip.svg"
# methanol layout with positive-space offset for browser-friendly SVG display
_C_POS = (20.0, 20.0)
_O_POS = (60.0, 20.0)


#============================================
# Fixtures
#============================================

#============================================
@pytest.fixture
def methanol() -> object:
	"""Build a methanol molecule: C at (0,0), O at (40,0), single bond."""
	mol = oasa.molecule_lib.Molecule()
	c = oasa.atom_lib.Atom(symbol="C")
	c.x, c.y = _C_POS
	o = oasa.atom_lib.Atom(symbol="O")
	o.x, o.y = _O_POS
	mol.add_vertex(c)
	mol.add_vertex(o)
	bond = oasa.bond_lib.Bond(order=1, type="n")
	bond.vertices = (c, o)
	mol.add_edge(c, o, bond)
	return mol


#============================================
@pytest.fixture
def output_smoke_dir() -> object:
	"""Return repo-level output_smoke directory for deterministic SVG artifacts."""
	repo_root = file_utils.get_repo_root()
	out_dir = os.path.join(repo_root, "output_smoke")
	os.makedirs(out_dir, exist_ok=True)
	return out_dir


#============================================
@pytest.fixture
def variant_a_ops(methanol: object) -> object:
	"""Variant A: full-length bond + label mask (no clipping targets).

	BondRenderContext has empty targets so build_bond_ops draws the
	full center-to-center bond. build_vertex_ops emits a background
	mask polygon behind the O label.
	"""
	edge = list(methanol.edges)[0]
	c, o = edge.vertices
	start = (c.x, c.y)
	end = (o.x, o.y)
	# no clipping targets: bond goes full length
	context = BondRenderContext(
		molecule=None,
		line_width=_LINE_WIDTH,
		bond_width=_BOND_WIDTH,
		wedge_width=_WEDGE_WIDTH,
		bold_line_width_multiplier=1.2,
		bond_second_line_shortening=0.0,
		color_bonds=True,
		shown_vertices=set(),
		label_targets={},
		attach_targets={},
		attach_constraints=make_attach_constraints(font_size=_FONT_SIZE),
	)
	bond_ops = build_bond_ops(edge, start, end, context)
	# oxygen vertex ops with background mask
	oxygen_ops = build_vertex_ops(
		o,
		show_hydrogens_on_hetero=True,
		font_size=_FONT_SIZE,
		font_name=_FONT_NAME,
		background_color=_BACKGROUND_COLOR,
		draw_label_mask=True,
	)
	# carbon is hidden (no ops)
	carbon_ops = build_vertex_ops(
		c,
		show_hydrogens_on_hetero=True,
		font_size=_FONT_SIZE,
		font_name=_FONT_NAME,
		background_color=_BACKGROUND_COLOR,
		draw_label_mask=True,
	)
	return {
		"bond_ops": bond_ops,
		"oxygen_ops": oxygen_ops,
		"carbon_ops": carbon_ops,
		"all_ops": bond_ops + oxygen_ops + carbon_ops,
		"edge": edge,
	}


#============================================
@pytest.fixture
def variant_b_ops(methanol: object) -> object:
	"""Variant B: clipped bond + no mask (real label/attach targets).

	build_label_attach_targets computes real targets for the O label,
	which build_bond_ops uses to shorten the bond endpoint. No background
	mask polygon is emitted.
	"""
	edge = list(methanol.edges)[0]
	c, o = edge.vertices
	start = (c.x, c.y)
	end = (o.x, o.y)
	# compute real clipping targets from both endpoint atoms
	shown_vertices, label_targets, attach_targets = build_label_attach_targets(
		vertices=edge.vertices,
		show_hydrogens_on_hetero=True,
		font_name=_FONT_NAME,
		font_size=_FONT_SIZE,
	)
	context = BondRenderContext(
		molecule=None,
		line_width=_LINE_WIDTH,
		bond_width=_BOND_WIDTH,
		wedge_width=_WEDGE_WIDTH,
		bold_line_width_multiplier=1.2,
		bond_second_line_shortening=0.0,
		color_bonds=True,
		shown_vertices=shown_vertices,
		label_targets=label_targets,
		attach_targets=attach_targets,
		attach_constraints=make_attach_constraints(font_size=_FONT_SIZE),
	)
	bond_ops = build_bond_ops(edge, start, end, context)
	# oxygen vertex ops without background mask
	oxygen_ops = build_vertex_ops(
		o,
		show_hydrogens_on_hetero=True,
		font_size=_FONT_SIZE,
		font_name=_FONT_NAME,
		background_color=None,
		draw_label_mask=False,
	)
	# carbon is hidden (no ops)
	carbon_ops = build_vertex_ops(
		c,
		show_hydrogens_on_hetero=True,
		font_size=_FONT_SIZE,
		font_name=_FONT_NAME,
		background_color=None,
		draw_label_mask=False,
	)
	return {
		"bond_ops": bond_ops,
		"oxygen_ops": oxygen_ops,
		"carbon_ops": carbon_ops,
		"all_ops": bond_ops + oxygen_ops + carbon_ops,
		"edge": edge,
		"shown_vertices": shown_vertices,
		"label_targets": label_targets,
		"attach_targets": attach_targets,
	}


#============================================
# Helper functions
#============================================

#============================================
def _find_bond_line_ops(ops: list) -> list:
	"""Return all LineOp instances from a list of render ops."""
	return [op for op in ops if isinstance(op, oasa.render_ops.LineOp)]


#============================================
def _find_mask_polygons(ops: list) -> list:
	"""Return PolygonOp instances that look like background mask rectangles.

	A mask polygon has fill set to the background color and is a 4-point
	rectangle behind the atom label.
	"""
	masks = []
	for op in ops:
		if not isinstance(op, oasa.render_ops.PolygonOp):
			continue
		# mask polygons have background color fill and 4 points
		if op.fill == _BACKGROUND_COLOR and len(op.points) == 4:
			masks.append(op)
	return masks


#============================================
def _rightmost_bond_x(bond_ops: list) -> float:
	"""Return the rightmost x coordinate among bond LineOps.

	For a horizontal C-O bond, this is the endpoint nearest the O atom.
	"""
	lines = _find_bond_line_ops(bond_ops)
	assert lines, "Expected at least one LineOp in bond ops"
	# for horizontal bonds, p2 is the rightmost endpoint
	return max(max(line.p1[0], line.p2[0]) for line in lines)


#============================================
def _line_length(p1: tuple, p2: tuple) -> float:
	"""Return Euclidean distance between two points."""
	return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


#============================================
def _max_bond_line_length(bond_ops: list) -> float:
	"""Return maximum rendered bond line length in one bond op list."""
	lines = _find_bond_line_ops(bond_ops)
	assert lines, "Expected at least one LineOp in bond ops"
	return max(_line_length(line.p1, line.p2) for line in lines)


#============================================
def _parse_svg(path: str) -> etree._ElementTree:
	"""Parse generated SVG with an isolated hardened lxml parser."""
	parser = etree.XMLParser(
		resolve_entities=False,
		no_network=True,
		load_dtd=False,
		dtd_validation=False,
		recover=False,
		huge_tree=False,
	)
	return etree.parse(path, parser)


#============================================
def _svg_line_lengths(document: etree._ElementTree) -> list:
	"""Extract <line> segment lengths from one SVG DOM document."""
	lengths = []
	for line in document.xpath("//svg:line", namespaces={"svg": "http://www.w3.org/2000/svg"}):
		x1 = float(line.attrib["x1"])
		y1 = float(line.attrib["y1"])
		x2 = float(line.attrib["x2"])
		y2 = float(line.attrib["y2"])
		lengths.append(_line_length((x1, y1), (x2, y2)))
	return lengths


#============================================
def _svg_text_values(document: etree._ElementTree) -> list:
	"""Extract visible text content from <text> nodes in one SVG DOM document."""
	values = []
	for node in document.xpath("//svg:text", namespaces={"svg": "http://www.w3.org/2000/svg"}):
		values.append("".join(node.itertext()))
	return values


#============================================
def _dump_svg(ops: list, out_path: str, width: int = 100, height: int = 40) -> None:
	"""Optional debug helper: serialize ops to SVG file for visual inspection."""
	svg_text = (
		'<svg xmlns="http://www.w3.org/2000/svg" version="1.0" '
		f'width="{width}" height="{height}" />'
	)
	document = oasa.safe_xml.parse_dom_from_string(svg_text)
	root = document.documentElement
	group = dom_extensions.elementUnder(root, "g")
	oasa.render_ops.ops_to_svg(group, ops)
	text = svg_out.pretty_print_svg(document.toxml("utf-8"))
	with open(out_path, "w", encoding="utf-8") as f:
		f.write(text)


#============================================
# Tests
#============================================

#============================================
def test_methanol_ab_endpoint_shortening(variant_a_ops: object, variant_b_ops: object) -> None:
	"""Variant B bond endpoint is shorter than variant A (clipped at label)."""
	end_x_a = _rightmost_bond_x(variant_a_ops["bond_ops"])
	end_x_b = _rightmost_bond_x(variant_b_ops["bond_ops"])
	# variant A goes to approximately O center (40.0)
	assert end_x_a == pytest.approx(_O_POS[0], abs=1.0), (
		f"Variant A bond endpoint should reach O center, got {end_x_a}"
	)
	# variant B should be noticeably shorter (clipped before label)
	assert end_x_b < end_x_a, (
		f"Variant B endpoint ({end_x_b:.2f}) should be shorter than "
		f"variant A ({end_x_a:.2f})"
	)
	# the shortening should be meaningful (at least a few pixels for font_size=16)
	min_shortening = 3.0
	assert (end_x_a - end_x_b) > min_shortening, (
		f"Bond shortening ({end_x_a - end_x_b:.2f}) should be at least "
		f"{min_shortening} pixels"
	)
	# both variants must still render a visible bond segment
	max_len_a = _max_bond_line_length(variant_a_ops["bond_ops"])
	max_len_b = _max_bond_line_length(variant_b_ops["bond_ops"])
	assert max_len_a > _MIN_VISIBLE_BOND_LENGTH, (
		f"Variant A max line length ({max_len_a:.2f}) is too short"
	)
	assert max_len_b > _MIN_VISIBLE_BOND_LENGTH, (
		f"Variant B max line length ({max_len_b:.2f}) is too short"
	)


#============================================
def test_methanol_ab_mask_presence_difference(variant_a_ops: object, variant_b_ops: object) -> None:
	"""Variant A has a mask polygon behind O label; variant B does not."""
	masks_a = _find_mask_polygons(variant_a_ops["oxygen_ops"])
	masks_b = _find_mask_polygons(variant_b_ops["oxygen_ops"])
	assert len(masks_a) >= 1, (
		"Variant A should have at least one mask polygon behind O label"
	)
	assert len(masks_b) == 0, (
		"Variant B should have no mask polygons (clipping replaces masking)"
	)


#============================================
def test_methanol_ab_endpoint_not_inside_label_target(variant_b_ops: object) -> None:
	"""Variant B bond endpoint is outside the O atom label target boundary.

	build_bond_ops falls back to label_targets when attach_targets is
	empty (single-token labels like bare "O" without subscripted H count).
	The bond endpoint should stop outside the label bounding box.
	"""
	label_targets = variant_b_ops["label_targets"]
	edge = variant_b_ops["edge"]
	_, o = edge.vertices
	# oxygen should have a label target in variant B
	assert o in label_targets, (
		"Oxygen should have a label target in variant B"
	)
	target = label_targets[o]
	# find the bond endpoint nearest the O atom
	lines = _find_bond_line_ops(variant_b_ops["bond_ops"])
	assert lines, "Expected at least one LineOp"
	# the endpoint is the rightmost point for this horizontal bond
	end_x = _rightmost_bond_x(variant_b_ops["bond_ops"])
	# use line p1/p2 y coordinate (should be ~0 for horizontal bond)
	end_y = 0.0
	for line in lines:
		# pick the y from the rightmost point
		if line.p2[0] >= line.p1[0]:
			end_y = line.p2[1]
		else:
			end_y = line.p1[1]
	end_point = (end_x, end_y)
	# endpoint should NOT be inside the label target
	is_inside = target.contains(end_point, epsilon=0.0)
	assert not is_inside, (
		f"Variant B bond endpoint {end_point} should be outside "
		f"the O label target, but contains() returned True"
	)


#============================================
def test_methanol_ab_both_have_text_ops(variant_a_ops: object, variant_b_ops: object) -> None:
	"""Both variants render the oxygen label as TextOps."""
	text_ops_a = [op for op in variant_a_ops["oxygen_ops"]
		if isinstance(op, oasa.render_ops.TextOp)]
	text_ops_b = [op for op in variant_b_ops["oxygen_ops"]
		if isinstance(op, oasa.render_ops.TextOp)]
	assert len(text_ops_a) >= 1, "Variant A should have at least one TextOp for O label"
	assert len(text_ops_b) >= 1, "Variant B should have at least one TextOp for O label"
	# the text content should be the same in both variants
	texts_a = sorted(op.text for op in text_ops_a)
	texts_b = sorted(op.text for op in text_ops_b)
	assert texts_a == texts_b, (
		f"Both variants should render the same label text: A={texts_a}, B={texts_b}"
	)


#============================================
def test_methanol_ab_carbon_hidden(variant_a_ops: object, variant_b_ops: object) -> None:
	"""Carbon vertex produces no render ops in either variant (it is hidden)."""
	assert len(variant_a_ops["carbon_ops"]) == 0, (
		"Carbon should have no render ops in variant A"
	)
	assert len(variant_b_ops["carbon_ops"]) == 0, (
		"Carbon should have no render ops in variant B"
	)


#============================================
def test_methanol_ab_shown_vertices(variant_b_ops: object) -> None:
	"""Variant B correctly identifies O as a shown vertex (C is hidden)."""
	shown = variant_b_ops["shown_vertices"]
	edge = variant_b_ops["edge"]
	c, o = edge.vertices
	assert o in shown, "Oxygen should be in shown_vertices"
	assert c not in shown, "Carbon should NOT be in shown_vertices"


#============================================
def test_methanol_ab_svg_output_smoke(variant_a_ops: object, variant_b_ops: object, output_smoke_dir: object) -> None:
	"""Write canonical methanol A/B smoke SVGs and assert structural correctness."""
	path_a = os.path.join(output_smoke_dir, _OUTPUT_SVG_A)
	path_b = os.path.join(output_smoke_dir, _OUTPUT_SVG_B)
	_dump_svg(variant_a_ops["all_ops"], path_a)
	_dump_svg(variant_b_ops["all_ops"], path_b)
	# verify files were written and are non-empty
	assert os.path.getsize(path_a) > 0
	assert os.path.getsize(path_b) > 0
	with open(path_a, encoding="utf-8") as handle:
		svg_text_a = handle.read()
	with open(path_b, encoding="utf-8") as handle:
		svg_text_b = handle.read()
	assert svg_text_a != svg_text_b, "A and B SVG outputs should differ"
	document_a = _parse_svg(path_a)
	document_b = _parse_svg(path_b)
	line_lengths_a = _svg_line_lengths(document_a)
	line_lengths_b = _svg_line_lengths(document_b)
	assert line_lengths_a, "Variant A SVG must contain at least one <line>"
	assert line_lengths_b, "Variant B SVG must contain at least one <line>"
	assert max(line_lengths_a) > _MIN_VISIBLE_BOND_LENGTH, (
		"Variant A SVG line length is degenerate"
	)
	assert max(line_lengths_b) > _MIN_VISIBLE_BOND_LENGTH, (
		"Variant B SVG line length is degenerate"
	)
	assert max(line_lengths_b) < max(line_lengths_a), (
		"Variant B SVG line should be shorter than variant A"
	)
	text_values_a = _svg_text_values(document_a)
	text_values_b = _svg_text_values(document_b)
	assert "OH" in text_values_a, "Variant A SVG should include OH label text"
	assert "OH" in text_values_b, "Variant B SVG should include OH label text"
	polygons_a = document_a.xpath("//svg:polygon", namespaces={"svg": "http://www.w3.org/2000/svg"})
	polygons_b = document_b.xpath("//svg:polygon", namespaces={"svg": "http://www.w3.org/2000/svg"})
	assert len(polygons_a) >= 1, "Variant A SVG should include a label mask polygon"
	assert len(polygons_b) == 0, "Variant B SVG should not include mask polygons"
