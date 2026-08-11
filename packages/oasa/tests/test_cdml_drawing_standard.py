"""Behavior tests for authoritative CDML drawing standards."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.cdml_standard
import oasa.safe_xml


_STANDARD_CDML = """\
<cdml xmlns:v="urn:vendor">
 <v:standard line_color="#badbad"><v:keep /></v:standard>
 <standard line_width="0.1cm" font_size="20" font_family="Courier"
  line_color="#123" area_color="#ffffff" v:keep="yes">
  <v:extension value="untouched" />
  <bond width="0.2cm" wedge-width="3px" double-ratio="0.6" />
  <atom show_hydrogens="0" />
 </standard>
 <molecule id="m1">
  <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="a2" name="O" hydrogens="on"><point x="1cm" y="0cm" />
   <font size="9" color="#abcdef" />
  </atom>
  <bond id="b1" start="a1" end="a2" type="n1" />
 </molecule>
</cdml>
"""

_APPLICATION_CDML = """\
<cdml xmlns:v="urn:vendor" version="26.07">
 <standard line_width="1px" font_size="12" font_family="Helvetica"
  line_color="#112233" area_color="">
  <bond width="6px" wedge-width="5px" double-ratio="0.75" />
  <atom show_hydrogens="0" />
 </standard>
 <molecule id="m1">
  <atom id="a1" name="C"><point x="0cm" y="0cm" /></atom>
  <atom id="a2" name="O"><point x="1cm" y="0cm" /></atom>
  <bond id="b1" start="a1" end="a2" type="n1" />
 </molecule>
 <molecule id="m2">
  <atom id="a3" name="N"><point x="2cm" y="0cm" />
   <font family="Times" size="9" color="#abcdef" />
  </atom>
 </molecule>
 <text id="t1"><point x="0cm" y="2cm" />
  <font family="Times" size="10" color="#654321" /><ftext>Note</ftext>
 </text>
 <rect id="r1" x1="0cm" y1="3cm" x2="1cm" y2="4cm"
  width="2" line_color="#333333" area_color="#eeeeee" />
 <v:note id="vendor-record"><v:font color="#badbad" /></v:note>
</cdml>
"""


#============================================
def _query(session: object, revision: int | None = None) -> object:
	"""Observe one exact standard revision."""
	revision = session.revision if revision is None else revision
	return session.drawing_standard(oasa.cdml_standard.CDMLDrawingStandardQuery(revision))


#============================================
def _patch(session: object, changes: object, revision: int | None = None) -> object:
	"""Submit one drawing-standard patch, including malformed test values."""
	revision = session.revision if revision is None else revision
	request = oasa.cdml_standard.CDMLDrawingStandardPatch(revision, changes)
	return session.patch_drawing_standard(request)


#============================================
def _apply(
		session: object, changes: object, scope: str,
		root_ids: tuple[str, ...], override_fields: tuple[str, ...],
		) -> object:
	"""Submit one atomic standard-and-object application request."""
	request = oasa.cdml_standard.CDMLDrawingStandardApplication(
		session.revision, changes, scope, root_ids, override_fields,
	)
	return session.patch_drawing_standard(request)


#============================================
def _element_by_id(cdml: str, identifier: str) -> object:
	"""Return one exact element by durable ID from serialized test CDML."""
	document = oasa.safe_xml.parse_dom_from_string(cdml)
	matches = [
		element for element in document.getElementsByTagName("*")
		if element.getAttribute("id") == identifier
	]
	assert len(matches) == 1
	return matches[0]


#============================================
def _direct_standard(cdml: str) -> object:
	"""Return the first direct core standard from accepted CDML."""
	document = oasa.safe_xml.parse_dom_from_string(cdml)
	for child in document.documentElement.childNodes:
		if (
			child.nodeType == child.ELEMENT_NODE
			and (child.localName or child.tagName) == "standard"
			and child.namespaceURI in (None, "", oasa.cdml_document.CDML_NAMESPACE_URI)
		):
			return child
	raise ValueError("direct core standard is missing")


#============================================
def test_standard_observation_drives_only_inherited_projection_values() -> None:
	"""Backend projection resolves defaults while retaining explicit atom fields."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_STANDARD_CDML)
	standard = _query(session)
	core = session.projection_snapshot().molecule_core_observation.records[0]
	first, second = core.atoms
	bond, = core.bonds

	assert (
		standard.line_width, standard.font_size, standard.bond_width,
		standard.wedge_width, standard.double_ratio,
	) == pytest.approx((72.0 / 25.4, 20, 144.0 / 25.4, 3.0, 0.6), rel=1e-6)
	assert (standard.font_family, standard.line_color, standard.area_color) == (
		"Courier", "#112233", "#ffffff",
	)
	assert (
		first.font_family, first.font_size, first.line_color, first.show_hydrogens,
		second.font_size, second.line_color, second.show_hydrogens,
	) == ("Courier", 20, "#112233", False, 9, "#abcdef", True)
	assert (
		bond.line_width, bond.bond_width, bond.wedge_width, bond.double_ratio,
	) == pytest.approx((72.0 / 25.4, 144.0 / 25.4, 3.0, 0.6), rel=1e-6)
	assert (first.explicit_fields, second.explicit_fields) == (
		(), ("show_hydrogens", "font_size", "line_color"),
	)


#============================================
def test_standard_colors_and_width_feed_authoritative_render_operations() -> None:
	"""Inherited drawing defaults reach visible backend paint primitives."""
	document = oasa.cdml_document.CDMLDocument.parse(
		"<cdml><standard line_width='2px' line_color='#123456' area_color='#fedcba'>"
		"<bond double-ratio='0.4'/></standard>"
		"<molecule id='m'><atom id='o' name='O'><point x='-1cm' y='0cm'/></atom>"
		"<atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='b' name='C'><point x='1cm' y='0cm'/></atom>"
		"<atom id='c' name='C'><point x='1.5cm' y='1cm'/></atom>"
		"<bond id='d' start='a' end='b' type='n2'/><bond id='e' start='b' end='c' "
		"type='n1'/></molecule></cdml>",
		validation="compat",
	)
	batches = document.molecule_render_observation(0).batches
	atom = next(batch for batch in batches if batch.identifier == "o")
	bond = next(batch for batch in batches if batch.identifier == "d")
	line_lengths = tuple(
		math.dist(operation.points[0], operation.points[1]) for operation in bond.operations
	)

	assert (atom.operations[0].fill, atom.operations[-1].fill) == ("#fedcba", "#123456")
	assert all(
		(operation.stroke, operation.stroke_width) == ("#123456", 2.0)
		for operation in bond.operations
	)
	assert line_lengths[1] / line_lengths[0] == pytest.approx(0.4)


#============================================
def test_standard_patch_preserves_extensions_and_uses_ordinary_history() -> None:
	"""A style patch changes only authored defaults and restores exactly."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_STANDARD_CDML)
	before = session.snapshot()
	changed = _patch(session, (
		("font_size", 18), ("line_color", "#445566"),
		("bond_width", 8.0), ("show_hydrogens", True),
	))
	standard = _direct_standard(changed.cdml)
	restored = session.restore(
		target_revision=before.revision, expected_revision=changed.revision,
	)

	assert (
		standard.getAttribute("font_size"), standard.getAttribute("line_color"),
		standard.getAttribute("v:keep"),
	) == ("18", "#445566", "yes")
	assert (
		standard.getElementsByTagName("v:extension")[0].getAttribute("value"),
		standard.getElementsByTagName("bond")[0].getAttribute("width"),
		standard.getElementsByTagName("atom")[0].getAttribute("show_hydrogens"),
	) == ("untouched", "0.282222cm", "1")
	assert restored.cdml == before.cdml


#============================================
def test_standard_patch_creation_is_noop_safe_and_stale_checked() -> None:
	"""Empty intent stays absent; changed intent creates one undoable standard."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<cdml xmlns:v="urn:vendor"><v:note /><molecule id="m1" /></cdml>',
	)
	before = session.snapshot()
	unchanged = _patch(session, ())
	changed = _patch(session, (("font_family", "Helvetica"),))

	assert unchanged.snapshot == before
	assert _direct_standard(changed.cdml).getAttribute("font_family") == "Helvetica"
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		_query(session, before.revision)


#============================================
def test_selected_standard_application_is_atomic_and_undoable() -> None:
	"""Changed values become overrides only below captured durable roots."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_APPLICATION_CDML)
	before = session.snapshot()
	commit = _apply(
		session, (("font_size", 18), ("line_color", "#445566")),
		"selected", ("m1",), ("font_size", "line_color"),
	)
	first = _element_by_id(commit.cdml, "a1")
	second_molecule_atom = _element_by_id(commit.cdml, "a3")
	selected_bond = _element_by_id(commit.cdml, "b1")
	text = _element_by_id(commit.cdml, "t1")
	restored = session.restore(
		target_revision=before.revision, expected_revision=commit.revision,
	)

	assert (
		first.getElementsByTagName("font")[0].getAttribute("size"),
		first.getElementsByTagName("font")[0].getAttribute("color"),
		selected_bond.getAttribute("color"),
	) == ("18", "#445566", "#445566")
	assert (
		second_molecule_atom.getElementsByTagName("font")[0].getAttribute("size"),
		text.getElementsByTagName("font")[0].getAttribute("color"),
	) == ("9", "#654321")
	assert restored.cdml == before.cdml


#============================================
def test_all_values_application_materializes_applicable_object_styles() -> None:
	"""All-value scope updates molecule and presentation records in one revision."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_APPLICATION_CDML)
	fields = (
		"line_width", "font_size", "font_family", "line_color", "area_color",
		"bond_width", "wedge_width", "double_ratio", "show_hydrogens",
	)
	commit = _apply(
		session,
		(("line_width", 3.0), ("font_size", 16), ("font_family", "Courier"),
			("line_color", "#224466"), ("area_color", "#ddeeff"),
			("bond_width", 8.0), ("wedge_width", 7.0),
			("double_ratio", 0.5), ("show_hydrogens", True)),
		"all", (), fields,
	)
	atom = _element_by_id(commit.cdml, "a3")
	bond = _element_by_id(commit.cdml, "b1")
	text = _element_by_id(commit.cdml, "t1")
	rect = _element_by_id(commit.cdml, "r1")
	vendor = _element_by_id(commit.cdml, "vendor-record")

	assert (
		atom.getAttribute("hydrogens"),
		atom.getElementsByTagName("font")[0].getAttribute("family"),
		atom.getElementsByTagName("font")[0].getAttribute("size"),
	) == ("on", "Courier", "16")
	assert (
		bond.getAttribute("line_width"), bond.getAttribute("bond_width"),
		bond.getAttribute("wedge_width"), bond.getAttribute("double_ratio"),
		bond.getAttribute("color"),
	) == ("3", "8", "7", "0.5", "#224466")
	assert (
		text.getAttribute("background-color"),
		text.getElementsByTagName("font")[0].getAttribute("family"),
		rect.getAttribute("width"), rect.getAttribute("line_color"),
		rect.getAttribute("area_color"),
	) == ("#ddeeff", "Courier", "3", "#224466", "#ddeeff")
	assert vendor.getElementsByTagName("v:font")[0].getAttribute("color") == "#badbad"


#============================================
@pytest.mark.parametrize(("scope", "root_ids", "fields"), (
	("defaults", ("m1",), ()),
	("defaults", (), ("font_size",)),
	("selected", (), ("font_size",)),
	("selected", ("missing",), ("font_size",)),
	("all", ("m1",), ("font_size",)),
))
def test_invalid_standard_application_is_atomic(
		scope: str, root_ids: tuple[str, ...], fields: tuple[str, ...],
		) -> None:
	"""Invalid scope/target combinations cannot partially update a standard."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_APPLICATION_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_standard.CDMLDrawingStandardError):
		_apply(session, (("font_size", 18),), scope, root_ids, fields)

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("changes", (
	[],
	(("font_size", True),),
	(("line_color", "black"),),
	(("double_ratio", 0.0),),
	(("bond_width", float("nan")),),
	(("show_hydrogens", 1),),
	(("font_size", 12), ("font_size", 13)),
	(("unknown", 1),),
))
def test_invalid_standard_patch_is_atomic(changes: object) -> None:
	"""Malformed standard intent cannot change snapshot or history."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_STANDARD_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_standard.CDMLDrawingStandardError):
		_patch(session, changes)

	assert session.snapshot() == before
