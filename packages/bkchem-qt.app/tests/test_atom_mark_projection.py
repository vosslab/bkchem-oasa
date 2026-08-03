"""Focused projection coverage for supported persistent CDML atom marks."""

# Standard Library
import contextlib
import math

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.io.cdml_document_io
import tests.graphics_test_retirement


_MARKS_CDML = """<cdml version="0.15">
<molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="2cm"/>
<mark type="plus" x="1.4cm" y="2cm" size="10" draw_circle="no"/>
<mark type="minus" x="1.5cm" y="2cm" size="10" draw_circle="yes"/>
<mark type="radical" x="1cm" y="2.2cm" size="4"/>
<mark type="biradical" x="1cm" y="2.3cm" size="4"/>
<mark type="electronpair" x="0.6cm" y="2cm" size="10" line_width="3"/>
<mark type="dotted_electronpair" x="0.5cm" y="2cm" size="4"/>
<mark type="pz_orbital" x="1cm" y="2cm" size="40"/>
</atom></molecule></cdml>"""


#============================================
def _project_supported_marks() -> tuple:
	"""Load CDML and return its atom-owned mark projections."""
	document = bkchem_qt.io.cdml_document_io.decode_compatibility_cdml_string(_MARKS_CDML)
	atom = document.molecules[0].atoms[0]
	atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom)
	items = tuple(
		bkchem_qt.canvas.document_projection.create_mark_item(mark, atom_item)
		for mark in document.marks
	)
	return document, atom_item, items


#============================================
@contextlib.contextmanager
def _project_marks_scene(
		qapp: PySide6.QtWidgets.QApplication,
		) -> object:
	"""Provide one explicitly retired scene for mark projection assertions."""
	document, atom_item, items = _project_supported_marks()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	scene.addItem(atom_item)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		yield atom_item, items, scene


#============================================
def test_cdml_marks_project_all_supported_semantic_kinds(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Every authored 26.07 atom mark is an atom-child projection."""
	with _project_marks_scene(qapp) as (atom_item, items, _scene):
		semantics = tuple(
			(item.mark_type, item.rendering_kind, item.parentItem() is atom_item,
				round(item.pos().x(), 3), round(item.pos().y(), 3), item.size)
			for item in items
		)
		assert semantics == (
			("plus", "charge", True, 11.339, 0.0, 10.0),
			("minus", "charge", True, 14.173, 0.0, 10.0),
			("radical", "dot", True, 0.0, 5.669, 4.0),
			("biradical", "perpendicular-dot-pair", True, 0.0, 8.504, 4.0),
			("electronpair", "perpendicular-line", True, -11.339, 0.0, 10.0),
			("dotted_electronpair", "perpendicular-dot-pair", True, -14.173, 0.0, 4.0),
			("pz_orbital", "figure-eight", True, 0.0, 0.0, 40.0),
		)


#============================================
def test_mark_projection_retains_charge_and_pair_display_semantics(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Circle and line settings produce distinct charge and lone-pair views."""
	with _project_marks_scene(qapp) as (_atom_item, items, _scene):
		by_type = {item.mark_type: item for item in items}
		assert (
			by_type["plus"].draw_circle,
			by_type["electronpair"].line_width,
			by_type["electronpair"].rendering_kind,
			by_type["dotted_electronpair"].rendering_kind,
		) == (False, 3.0, "perpendicular-line", "perpendicular-dot-pair")


#============================================
def test_anonymous_mark_remains_directly_selectable_before_any_command(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A child mark stays an ordinary selectable Qt interaction target."""
	with _project_marks_scene(qapp) as (_atom_item, items, scene):
		mark_item = items[0]
		mark_item.setSelected(True)
		assert scene.selectedItems() == [mark_item]


#============================================
def test_pz_orbital_projection_has_finite_nonempty_bounds(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A centered pz mark has a drawable figure-eight projection envelope."""
	with _project_marks_scene(qapp) as (_atom_item, items, _scene):
		pz_item = next(item for item in items if item.mark_type == "pz_orbital")
		bounds = pz_item.boundingRect()
		assert bounds.width() > 0.0 and all(
			math.isfinite(value)
			for value in (bounds.left(), bounds.top(), bounds.right(), bounds.bottom())
		)


#============================================
def test_unsupported_mark_remains_retained_without_qt_projection(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""An unimplemented persistent mark stays explicit unsupported content."""
	cdml = _MARKS_CDML.replace(
		'<mark type="pz_orbital" x="1cm" y="2cm" size="40"/>',
		'<mark type="text_mark" text="retained" x="1cm" y="2cm"/>',
	)
	document = bkchem_qt.io.cdml_document_io.decode_compatibility_cdml_string(cdml)
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		unsupported = document.unsupported_content
		assert len(document.marks) == 6 and "text_mark" in unsupported[0].raw_xml
