"""Compatibility behavior for retained Tk presentation background loading."""

# PIP3 modules
import pytest

# local repo modules
import bkchem.classes
import bkchem.graphics
import bkchem.id_manager
import bkchem.paper_lib.paper_cdml
import bkchem.singleton_store
import oasa.cdml_xml
import oasa.safe_xml


#============================================
@pytest.mark.parametrize(("object_class", "element_name", "children"), (
	(bkchem.classes.plus, "plus", '<point x="1cm" y="2cm"/>'),
	(
		bkchem.classes.text, "text",
		'<point x="1cm" y="2cm"/><ftext>Legacy note</ftext>',
	),
))
def test_explicit_transparent_background_overrides_inherited_standard(
		monkeypatch: pytest.MonkeyPatch, object_class: type,
		element_name: str, children: str,
		) -> None:
	"""An empty persistent attribute differs from an absent inherited value."""
	monkeypatch.setattr(bkchem.classes.Screen, "read_xml_point", lambda _point: (1, 2, 0))
	explicit = object.__new__(object_class)
	explicit.area_color = "#abcdef"
	missing = object.__new__(object_class)
	missing.area_color = "#abcdef"
	explicit_package = oasa.safe_xml.parse_dom_from_string(
		'<%s background-color="">%s</%s>' % (element_name, children, element_name),
	).documentElement
	missing_package = oasa.safe_xml.parse_dom_from_string(
		'<%s>%s</%s>' % (element_name, children, element_name),
	).documentElement

	explicit.read_package(explicit_package)
	missing.read_package(missing_package)

	assert explicit.area_color == ""
	assert missing.area_color == "#abcdef"


#============================================
def test_retained_text_writer_keeps_explicit_transparency(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A legacy save cannot turn an explicit transparent Text background into inheritance."""
	monkeypatch.setattr(
		bkchem.classes.Screen, "px_to_text_with_unit",
		lambda _coordinates: ("1cm", "2cm"),
	)
	annotation = object.__new__(bkchem.classes.text)
	annotation._id_enabled__id = "text1"
	annotation.x, annotation.y = 1, 2
	annotation.area_color = ""
	annotation.font_size = 12
	annotation.font_family = "Arial"
	annotation.line_color = "#000000"
	annotation.xml_ftext = "Legacy note"
	annotation.paper = type("Paper", (), {"standard": bkchem.classes.standard()})()
	document = oasa.safe_xml.parse_dom_from_string("<cdml/>")
	package = annotation.get_package(document)

	assert package.hasAttribute("background-color")
	assert package.getAttribute("background-color") == ""


#============================================
def test_retained_plus_reads_and_writes_direct_font_family(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The deprecated frontend preserves the same direct Plus family contract."""
	monkeypatch.setattr(bkchem.classes.Screen, "read_xml_point", lambda _point: (1, 2, 0))
	monkeypatch.setattr(
		bkchem.classes.Screen, "px_to_text_with_unit",
		lambda _coordinates: ("1cm", "2cm"),
	)
	symbol = object.__new__(bkchem.classes.plus)
	symbol._id_enabled__id = "plus1"
	symbol.font_family = "helvetica"
	symbol.font_size = 14
	symbol.line_color = "#000"
	symbol.area_color = "#ffffff"
	symbol.paper = type("Paper", (), {"standard": bkchem.classes.standard()})()
	package = oasa.safe_xml.parse_dom_from_string(
		'<plus xmlns:v="urn:vendor"><point x="1cm" y="2cm"/>'
		'<v:extra><font family="Wrong"/></v:extra><font family="Courier"/></plus>',
	).documentElement

	symbol.read_package(package)
	written = symbol.get_package(oasa.safe_xml.parse_dom_from_string("<cdml/>"))
	fonts = [
		child for child in written.childNodes
		if child.nodeType == child.ELEMENT_NODE and child.tagName == "font"
	]

	assert symbol.font_family == "Courier"
	assert len(fonts) == 1 and fonts[0].getAttribute("family") == "Courier"


#============================================
def _read_retained_polyline(source: bytes) -> bkchem.graphics.polyline:
	"""Build a headless retained-Tk polyline from lxml-authorized CDML."""
	document = oasa.cdml_xml.parse_cdml_dom(source)
	polyline = object.__new__(bkchem.graphics.polyline)
	polyline.read_package(document.documentElement)
	if not document.documentElement.hasAttribute("line_color"):
		polyline.line_color = "#000000"
	return polyline


#============================================
def _write_retained_polyline(polyline: bkchem.graphics.polyline) -> object:
	"""Serialize one headless retained-Tk polyline through its normal writer."""
	document = oasa.cdml_xml.parse_cdml_dom(b"<cdml/>")
	package = polyline.get_package(document)
	return package


#============================================
def _finish_retained_read(
		monkeypatch: pytest.MonkeyPatch, polylines: list[bkchem.graphics.polyline],
		) -> None:
	"""Run the real sandbox finalizer with an isolated live ID manager."""
	legacy_manager = bkchem.id_manager.id_manager()
	monkeypatch.setattr(bkchem.singleton_store.Store, "id_manager", bkchem.id_manager.id_manager())
	mixin = object.__new__(bkchem.paper_lib.paper_cdml.PaperCDMLMixin)
	mixin._old_id_manager = legacy_manager
	mixin.onread_id_sandbox_finish(apply_to=polylines)


#============================================
def test_retained_tk_round_trip_rewrites_complete_bracket_pair(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A marked pair keeps its relationship while normal Tk IDs are freshly allocated."""
	left = _read_retained_polyline(
		b'<polyline id="legacy-left" bracket_pair="legacy-left" bracket_side="left"/>',
	)
	right = _read_retained_polyline(
		b'<polyline id="legacy-right" bracket_pair="legacy-left" bracket_side="right"/>',
	)
	_finish_retained_read(monkeypatch, [left, right])
	written_left = _write_retained_polyline(left)
	written_right = _write_retained_polyline(right)

	assert written_left.getAttribute("bracket_pair") == written_left.getAttribute("id") == written_right.getAttribute("bracket_pair")


#============================================
def test_retained_tk_copy_of_complete_bracket_pair_gets_its_own_left_id(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Copying both marked members cannot retain a cross-document pair reference."""
	left = _read_retained_polyline(
		b'<polyline id="original-left" bracket_pair="original-left" bracket_side="left"/>',
	)
	right = _read_retained_polyline(
		b'<polyline id="original-right" bracket_pair="original-left" bracket_side="right"/>',
	)
	_finish_retained_read(monkeypatch, [left, right])
	old_left_id = left.id
	copied_left = _read_retained_polyline(_write_retained_polyline(left).toxml().encode())
	copied_right = _read_retained_polyline(_write_retained_polyline(right).toxml().encode())
	_finish_retained_read(monkeypatch, [copied_left, copied_right])
	written_left = _write_retained_polyline(copied_left)
	written_right = _write_retained_polyline(copied_right)

	assert written_left.getAttribute("bracket_pair") == written_left.getAttribute("id") == written_right.getAttribute("bracket_pair")
	assert written_left.getAttribute("id") != old_left_id


#============================================
def test_retained_tk_preserves_lone_bracket_marker_as_invalid_content(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A lone marker remains literal instead of becoming a guessed relationship."""
	lone = _read_retained_polyline(
		b'<polyline id="lone-left" bracket_pair="lone-left" bracket_side="left"/>',
	)
	_finish_retained_read(monkeypatch, [lone])
	written = _write_retained_polyline(lone)

	assert written.getAttribute("bracket_pair") == "lone-left"


#============================================
def test_retained_tk_unmarked_polyline_stays_independent(
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Legacy ordinary polylines do not acquire bracket metadata during a save."""
	polyline = _read_retained_polyline(b'<polyline id="ordinary"/>')
	_finish_retained_read(monkeypatch, [polyline])
	written = _write_retained_polyline(polyline)

	assert not written.hasAttribute("bracket_pair")
