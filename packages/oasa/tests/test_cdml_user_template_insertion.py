"""Backend-only tests for insertion of serialized user-saved CDML templates."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_POINTS_PER_CM = 72.0 / 2.54
_BASE_CDML = '<cdml version="26.07"><text id="existing"><point x="0cm" y="0cm"/><ftext>x</ftext></text></cdml>'
_SAVED_TEMPLATE = """
<cdml xmlns:vendor="urn:vendor" version="26.07">
 <standard line_width="1px"/><paper type="A4" orientation="portrait"/>
 <molecule id="saved_root" name="saved">
  <atom id="saved_a" name="C"><point x="1cm" y="2cm"/><vendor:note id="opaque_note">keep</vendor:note></atom>
  <atom id="saved_b" name="O"><point x="3cm" y="4cm"/></atom>
  <bond id="saved_bond" start="saved_a" end="saved_b" type="n1"/>
 </molecule>
</cdml>
"""
_REPEATABLE_TEMPLATE = """
<cdml version="26.07"><molecule name="Reusable">
 <atom id="source_a" name="C"><point x="1cm" y="2cm"/></atom>
 <atom id="source_b" name="O"><point x="3cm" y="4cm"/></atom>
 <bond id="source_bond" start="source_a" end="source_b" type="n1"/>
</molecule></cdml>
"""


#============================================
def _local_name(element: object) -> str:
	"""Return one namespace-neutral element name from hardened parsed XML."""
	name = str(element.tag)
	return name.rsplit("}", 1)[-1]


#============================================
def _molecule_atom_points(cdml: str) -> dict[str, tuple[float, float]]:
	"""Return inserted direct atom points in PostScript scene coordinates."""
	root = oasa.safe_xml.parse_xml_string(cdml)
	molecule = next(element for element in root if _local_name(element) == "molecule")
	points = {}
	for atom in molecule:
		if _local_name(atom) != "atom":
			continue
		point = next(child for child in atom if _local_name(child) == "point")
		points[atom.attrib["id"]] = (
			float(point.attrib["x"].removesuffix("cm")) * _POINTS_PER_CM,
			float(point.attrib["y"].removesuffix("cm")) * _POINTS_PER_CM,
		)
	return points


#============================================
def _request(revision: int, template_cdml: str, anchor: tuple[float, float]) -> object:
	"""Build one immutable backend-only saved-template insertion request."""
	return oasa.cdml_document.CDMLUserTemplateInsertionRequest(
		revision, template_cdml, anchor, "Insert saved template",
	)


#============================================
def test_user_template_keeps_authored_scale_and_places_atom_centroid_at_anchor() -> None:
	"""One saved molecule translates to the click without 40-point normalization."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_BASE_CDML)
	commit = session.insert_user_template(_request(session.revision, _SAVED_TEMPLATE, (125.0, -35.0)))
	coordinates = tuple(_molecule_atom_points(commit.snapshot.cdml).values())
	centroid = tuple(math.fsum(axis) / len(coordinates) for axis in zip(*coordinates))
	assert centroid == pytest.approx((125.0, -35.0), abs=0.02)
	assert math.dist(*coordinates) == pytest.approx(80.17, abs=0.03)


#============================================
def test_user_template_freshens_known_ids_and_preserves_nested_extension_content() -> None:
	"""Recognized graph links remap while foreign nested XML remains literal content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_BASE_CDML)
	commit = session.insert_user_template(_request(session.revision, _SAVED_TEMPLATE, (0.0, 0.0)))
	document = oasa.cdml_document.CDMLDocument.parse(commit.snapshot.cdml, validation="strict")
	root = oasa.safe_xml.parse_xml_string(commit.snapshot.cdml)
	molecule = next(element for element in root if _local_name(element) == "molecule")
	atom_ids = {element.attrib["id"] for element in molecule if _local_name(element) == "atom"}
	bond = next(element for element in molecule if _local_name(element) == "bond")
	assert {bond.attrib["start"], bond.attrib["end"]} == atom_ids
	assert (
		molecule.attrib["id"] not in {"existing", "saved_root"}
		and document.find_by_id("opaque_note").raw_xml in commit.snapshot.cdml
	)


#============================================
def test_user_template_acceptance_advances_once_and_stays_dirty_from_saved_baseline() -> None:
	"""A repeatable saved template creates one revision after an independent save."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_BASE_CDML)
	saved_baseline = session.mark_saved(expected_revision=session.revision)
	commit = session.insert_user_template(
		_request(session.revision, _REPEATABLE_TEMPLATE, (0.0, 0.0)),
	)
	assert commit.snapshot.revision == saved_baseline.revision + 1
	assert session.is_dirty and commit.snapshot.cdml != saved_baseline.cdml


#============================================
@pytest.mark.parametrize(("template_cdml", "expected_name"), (
	(_REPEATABLE_TEMPLATE, "Reusable"),
	('<cdml><molecule name=" "><atom id="a"><point x="0cm" y="0cm"/></atom></molecule></cdml>', None),
))
def test_user_template_inspection_returns_catalog_label_or_none(
		template_cdml: str, expected_name: str | None,
		) -> None:
	"""Catalog inspection exposes only a usable saved-molecule display label."""
	inspection = oasa.cdml_document.inspect_user_template(template_cdml)
	assert inspection.display_name == expected_name


#============================================
def test_user_template_inspection_rejects_duplicate_literal_ids() -> None:
	"""A duplicate opaque literal ID is an ineligible template before insertion."""
	template_cdml = (
		'<cdml xmlns:vendor="urn:vendor"><molecule><atom id="same">'
		'<point x="0cm" y="0cm"/><vendor:note id="same"/></atom></molecule></cdml>'
	)
	with pytest.raises(oasa.cdml_document.CDMLUserTemplateInsertionError):
		oasa.cdml_document.inspect_user_template(template_cdml)


#============================================
@pytest.mark.parametrize("template_cdml", (
	'<cdml><molecule><atom id="a"><point x="0cm" y="0cm"/></atom><template atom="a"/></molecule></cdml>',
	'<cdml><molecule><atom id="a"><point x="0cm" y="0cm"/></atom></molecule><arrow/></cdml>',
	'<cdml><molecule><atom id="a"><point x="0cm" y="0cm"/></atom></molecule><molecule><atom id="b"><point x="1cm" y="1cm"/></atom></molecule></cdml>',
))
def test_ineligible_user_template_shapes_are_typed_and_inert(template_cdml: str) -> None:
	"""Markers and direct-root shapes outside the saved-template grammar do nothing."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_BASE_CDML)
	baseline = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLUserTemplateInsertionError):
		session.insert_user_template(_request(baseline.revision, template_cdml, (0.0, 0.0)))
	assert session.snapshot() == baseline


#============================================
def test_user_template_rejects_nonfinite_anchor_without_history_change() -> None:
	"""A nonfinite click cannot prepare or accept a saved template."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_BASE_CDML)
	baseline = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLUserTemplateInsertionError):
		session.insert_user_template(_request(baseline.revision, _SAVED_TEMPLATE, (float("nan"), 0.0)))
	assert session.snapshot() == baseline


#============================================
def test_repeated_template_with_literal_extension_id_is_typed_and_inert() -> None:
	"""Opaque IDs reserve document-wide names without changing extension semantics."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_BASE_CDML)
	first = session.insert_user_template(_request(session.revision, _SAVED_TEMPLATE, (0.0, 0.0)))
	with pytest.raises(oasa.cdml_document.CDMLUserTemplateInsertionError):
		session.insert_user_template(_request(first.snapshot.revision, _SAVED_TEMPLATE, (20.0, 0.0)))
	assert session.snapshot() == first.snapshot


#============================================
def test_stale_user_template_conflict_precedes_payload_parsing() -> None:
	"""An obsolete request rejects before its malformed frozen payload is inspected."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_BASE_CDML)
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.insert_user_template(_request(-1, "not CDML", (0.0, 0.0)))
	assert session.revision == 0
