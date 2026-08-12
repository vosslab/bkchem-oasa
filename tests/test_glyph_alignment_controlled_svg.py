"""Behavior tests for controlled SVG glyph-bond association."""

# Standard Library
import importlib.util
import pathlib

# Third Party
from lxml import etree


#============================================
def _load_tool() -> object:
	"""Load the executable measurement module through its public file path."""
	repo_root = pathlib.Path(__file__).resolve().parents[1]
	tool_path = repo_root / "tools" / "measure_glyph_bond_alignment.py"
	spec = importlib.util.spec_from_file_location("measure_glyph_alignment_test", tool_path)
	if spec is None or spec.loader is None:
		raise RuntimeError("Could not load glyph alignment measurement tool")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


#============================================
def _write_controlled_svg(path: pathlib.Path, start_x: float, endpoint_x: float) -> None:
	"""Write one lxml-controlled connector and its declared target label."""
	namespace = "http://www.w3.org/2000/svg"
	root = etree.Element(
		f"{{{namespace}}}svg",
		nsmap={None: namespace},
		attrib={"width": "120", "height": "120", "viewBox": "-20 -20 120 120"},
	)
	etree.SubElement(
		root,
		f"{{{namespace}}}line",
		attrib={
			"x1": str(start_x), "y1": "0", "x2": str(endpoint_x), "y2": "0",
			"stroke": "#000", "stroke-width": "1.2",
			"data-oasa-op-id": "bond_connector",
			"data-oasa-attachment-target": "group_label",
		},
	)
	label = etree.SubElement(
		root,
		f"{{{namespace}}}text",
		attrib={
			"x": "0", "y": "0", "font-size": "12", "text-anchor": "start",
			"data-oasa-op-id": "group_label",
		},
	)
	label.text = "OH"
	path.write_bytes(etree.tostring(root, encoding="utf-8", xml_declaration=True))


#============================================
def test_controlled_svg_uses_declared_connector_not_nearest_unrelated_line(tmp_path: pathlib.Path) -> None:
	"""A declared connector is accepted despite a closer unrelated paint stroke."""
	tool = _load_tool()
	svg_path = tmp_path / "controlled.svg"
	_write_controlled_svg(svg_path, -10.0, 8.0)
	report = tool.analyze_svg_file(svg_path)
	assert report["aligned_count"] == 1


#============================================
def test_controlled_svg_rejects_a_declared_connector_that_misses_its_label(tmp_path: pathlib.Path) -> None:
	"""Operation identity does not hide a declared bond endpoint far from its label."""
	tool = _load_tool()
	svg_path = tmp_path / "miss.svg"
	_write_controlled_svg(svg_path, 70.0, 80.0)
	report = tool.analyze_svg_file(svg_path)
	assert report["missed_count"] + report["no_connector_count"] == 1
