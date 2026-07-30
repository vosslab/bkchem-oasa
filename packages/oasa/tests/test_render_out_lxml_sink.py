# SPDX-License-Identifier: LGPL-3.0-or-later

"""Focused coverage for render_out's controlled lxml SVG construction path."""

# Standard Library
import io
import math

# Third Party
from lxml import etree

# local repo modules
import oasa.smiles_lib
from oasa import safe_xml
from oasa import render_ops
from oasa import render_out


_SVG_NAMESPACE = "http://www.w3.org/2000/svg"


def _parse_controlled_svg(svg_text: object) -> object:
	"""Parse generated SVG with lxml's hardened no-network parser settings."""
	parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
	return etree.fromstring(str(svg_text).encode("utf-8"), parser=parser)


#============================================
def _local_names(element: object) -> object:
	"""Return direct child names without relying on serialized namespace syntax."""
	return [etree.QName(child).localname for child in element]


#============================================
def _graphic_semantics(element: object) -> object:
	"""Keep the legacy-facade comparison independent of XML spelling details."""
	return [
		(etree.QName(child).localname, dict(child.attrib))
		for child in element
	]


#============================================
def _all_operation_forms() -> object:
	"""Provide deliberately z-scrambled examples of every controlled graphic op."""
	return (
		render_ops.LineOp((1.0, 2.0), (3.0, 4.0), 2.0, cap="round", z=3),
		render_ops.PolygonOp(((0.0, 0.0), (2.0, 0.0), (1.0, 2.0)), "#abc", z=2),
		render_ops.CircleOp((4.0, 5.0), 1.5, "#fff", stroke="#123456", z=1),
		render_ops.PathOp(
			(("M", (0.0, 0.0)), ("L", (2.0, 2.0)),
			 ("ARC", (2.0, 2.0, 1.0, 0.0, math.pi)), ("Z", None)),
			fill="none",
			stroke="#000",
			z=0,
		),
	)


#============================================
def _lxml_svg_for_ops(ops: object) -> object:
	"""Build then harden-parse generated controlled SVG for behavior assertions."""
	root = render_out._ops_to_svg_document(ops, 20, 10)
	return _parse_controlled_svg(etree.tostring(root, encoding="unicode"))


#============================================
def test_lxml_svg_sink_emits_all_graphic_operations_in_z_order() -> None:
	"""Every graphical op is namespaced and ordered by its persistent z value."""
	root = _lxml_svg_for_ops(_all_operation_forms())
	assert (etree.QName(root).namespace, _local_names(root[0])) == (
		_SVG_NAMESPACE,
		["path", "circle", "polygon", "line"],
	)
	assert all(token in root[0][0].get("d", "") for token in ("M", "L", "A", "Z"))


#============================================
def test_lxml_svg_sink_escapes_simple_text_and_preserves_rich_text_structure() -> None:
	"""Text remains text while supported subscript and superscript stay structured."""
	root = _lxml_svg_for_ops(
		(
			render_ops.TextOp(1.0, 2.0, "Na & Cl", weight="bold", z=0),
			render_ops.TextOp(3.0, 4.0, "H<sub>2</sub>O<sup>+</sup>", font_size=12.0, z=1),
		),
	)
	texts = root[0].findall(f"{{{_SVG_NAMESPACE}}}text")
	assert (texts[0].text, texts[0].get("font-weight")) == ("Na & Cl", "bold")
	assert [(span.text, "font-size" in span.attrib, "dy" in span.attrib) for span in texts[1]] == [
		("H", False, False), ("2", True, True), ("O", False, True), ("+", True, True),
	]


#============================================
def test_lxml_sink_matches_the_legacy_minidom_semantics() -> None:
	"""The public legacy facade observes the same controlled SVG operation semantics."""
	legacy_document = safe_xml.parse_dom_from_string("<svg/>")
	legacy_root = legacy_document.documentElement
	render_ops.ops_to_svg(legacy_root, _all_operation_forms())
	legacy_svg = _parse_controlled_svg(legacy_document.toxml())
	lxml_svg = _lxml_svg_for_ops(_all_operation_forms())
	assert _graphic_semantics(legacy_svg) == _graphic_semantics(lxml_svg[0])


#============================================
def test_render_to_svg_supports_text_binary_and_file_targets(tmp_path: object) -> None:
	"""Public rendering writes parseable namespaced SVG through every supported target."""
	mol = oasa.smiles_lib.text_to_mol("CO")
	assert mol is not None
	text_target = io.StringIO()
	binary_target = io.BytesIO()
	file_target = tmp_path / "methanol.svg"
	render_out.render_to_svg(mol, text_target)
	render_out.render_to_svg(mol, binary_target)
	render_out.render_to_svg(mol, file_target)
	roots = (
		_parse_controlled_svg(text_target.getvalue()),
		_parse_controlled_svg(binary_target.getvalue().decode("utf-8")),
		_parse_controlled_svg(file_target.read_text(encoding="utf-8")),
	)
	assert all(
		etree.QName(root).namespace == _SVG_NAMESPACE
		and root.get("width") is not None
		and root.get("height") is not None
		for root in roots
	)
