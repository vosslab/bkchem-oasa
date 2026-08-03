"""Behavioral tests for backend-owned one-bond implicit-group expansion."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_EXTERIOR_BOND = (
	'<bond id="b1" start="a1" end="g1" type="n1" custom="keep">'
	'<!-- retain --><v:keep/></bond>'
)
_TWO_ATTACHMENT_SUFFIX = (
	'</bond><atom id="a2" name="C"><point x="2cm" y="0cm"/></atom>'
	'<bond id="b2" start="a2" end="g1" type="n1"/></molecule>'
)
_COOH = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" '
	'xmlns:v="urn:vendor" version="26.07">'
	'<molecule id="m1">'
	'<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom>'
	'<group id="g1" name="COOH" group-type="implicit">'
	'<point x="1cm" y="0cm"/><font family="Helvetica" size="14"/>'
	'</group>' + _EXTERIOR_BOND + '</molecule>'
	'<v:opaque id="opaque-1"><v:child/></v:opaque>'
	'</cdml>'
)


#============================================
def _accepted_dom(cdml_text: str) -> object:
	"""Read accepted CDML only after its public strict parser boundary."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	return dom


#============================================
def _element_by_id(dom: object, identifier: str) -> object:
	"""Return one durable accepted element from a compatibility DOM."""
	for element in dom.getElementsByTagName("*"):
		if element.getAttribute("id") == identifier:
			return element
	raise AssertionError("accepted CDML is missing durable element: %s" % identifier)


#============================================
def _point(element: object) -> tuple[float, float]:
	"""Return one atom point in centimetres from accepted CDML."""
	point = next(child for child in element.childNodes if getattr(child, "tagName", None) == "point")
	coordinates = tuple(float(point.getAttribute(axis).removesuffix("cm")) for axis in ("x", "y"))
	return coordinates


#============================================
def _bond_angle(
		first: tuple[float, float], center: tuple[float, float],
		second: tuple[float, float],
		) -> float:
	"""Return the unsigned angle between two persistent bond vectors in degrees."""
	first_vector = (first[0] - center[0], first[1] - center[1])
	second_vector = (second[0] - center[0], second[1] - center[1])
	dot = first_vector[0] * second_vector[0] + first_vector[1] * second_vector[1]
	lengths = math.hypot(*first_vector) * math.hypot(*second_vector)
	angle = math.degrees(math.acos(max(-1.0, min(1.0, dot / lengths))))
	return angle


#============================================
def _has_preserved_cooh_topology(dom: object, result: object) -> bool:
	"""Return whether accepted CDML has the required COOH splice and preservation."""
	replacement = _element_by_id(dom, result.replacement_atom_id)
	exterior = _element_by_id(dom, "a1")
	exterior_bond = _element_by_id(dom, "b1")
	generated = tuple(_element_by_id(dom, identifier) for identifier in result.atom_ids)
	internal_bonds = tuple(_element_by_id(dom, identifier) for identifier in result.bond_ids)
	_element_by_id(dom, "opaque-1")
	bond_xml = exterior_bond.toxml()
	return all((
		not any(element.getAttribute("id") == "g1"
			for element in dom.getElementsByTagName("group")),
		_point(exterior) == (0.0, 0.0),
		_point(replacement) == (1.0, 0.0),
		{bond.getAttribute("type") for bond in internal_bonds} == {"n1", "n2"},
		tuple(sorted(atom.getAttribute("name") for atom in generated)) == ("C", "O", "O"),
		exterior_bond.getAttribute("start") == "a1",
		exterior_bond.getAttribute("end") == result.replacement_atom_id,
		exterior_bond.getAttribute("custom") == "keep",
		"retain" in bond_xml,
		"v:keep" in bond_xml,
	))


#============================================
def _has_attachment_geometry(dom: object, result: object) -> bool:
	"""Return whether detached COOH layout kept trigonal geometry and bond scale."""
	replacement = _element_by_id(dom, result.replacement_atom_id)
	exterior = _element_by_id(dom, "a1")
	internal_bonds = tuple(_element_by_id(dom, identifier) for identifier in result.bond_ids)
	carbon_neighbors = tuple(
		_element_by_id(dom, bond.getAttribute("end"))
		if bond.getAttribute("start") == result.replacement_atom_id
		else _element_by_id(dom, bond.getAttribute("start"))
		for bond in internal_bonds
	)
	attachment_angles = tuple(
		_bond_angle(_point(exterior), _point(replacement), _point(neighbor))
		for neighbor in carbon_neighbors
	)
	internal_lengths = tuple(
		math.dist(_point(replacement), _point(neighbor))
		for neighbor in carbon_neighbors
	)
	exterior_length = math.dist(_point(exterior), _point(replacement))
	return (
		all(105.0 <= angle <= 135.0 for angle in attachment_angles)
		and all(math.isclose(exterior_length, length, rel_tol=0.02)
			for length in internal_lengths)
	)


#============================================
def test_implicit_group_preserves_authoritative_geometry_and_bond_content() -> None:
	"""COOH replaces one group without rebuilding surrounding persistent content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_COOH)
	result = session.expand_implicit_group(
		oasa.cdml_document.CDMLImplicitGroupExpandRequest(session.revision, "m1", "g1"),
	)
	dom = _accepted_dom(result.snapshot.cdml)

	assert _has_preserved_cooh_topology(dom, result)
	assert _has_attachment_geometry(dom, result)


#============================================
@pytest.mark.parametrize("name", ("CH3", "H3CO"))
def test_implicit_group_expansion_accepts_both_attachment_formula_directions(name: str) -> None:
	"""The parser uses start valency first and end valency when that is required."""
	cdml = _COOH.replace("COOH", name).replace('<font family="Helvetica" size="14"/>', "")
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	result = session.expand_implicit_group(
		oasa.cdml_document.CDMLImplicitGroupExpandRequest(session.revision, "m1", "g1"),
	)
	replacement = _element_by_id(_accepted_dom(result.snapshot.cdml), result.replacement_atom_id)

	assert replacement.getAttribute("name") == "C"


#============================================
@pytest.mark.parametrize(("source", "replacement"), (
	('<font family="Helvetica" size="14"/>', '<v:rich/>'),
	(_EXTERIOR_BOND, ''),
	('</bond></molecule>', _TWO_ATTACHMENT_SUFFIX),
	('name="COOH"', 'name="???"'),
	('x="1cm" y="0cm"', 'x="0cm" y="0cm"'),
))
def test_implicit_group_rejects_unsupported_source_atomically(
		source: str, replacement: str,
		) -> None:
	"""Unsupported persistent grammar and chemistry cannot produce a partial commit."""
	cdml = _COOH.replace(source, replacement, 1)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLImplicitGroupExpandError):
		session.expand_implicit_group(
			oasa.cdml_document.CDMLImplicitGroupExpandRequest(before.revision, "m1", "g1"),
		)

	assert session.snapshot() == before


#============================================
def test_implicit_group_reserves_removed_id_and_restores_backend_history() -> None:
	"""One accepted replacement has collision-safe records and normal backend undo/redo."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_COOH)
	result = session.expand_implicit_group(
		oasa.cdml_document.CDMLImplicitGroupExpandRequest(session.revision, "m1", "g1"),
	)
	undone = session.restore(target_revision=0, expected_revision=result.snapshot.revision)
	redone = session.restore(
		target_revision=result.snapshot.revision, expected_revision=undone.snapshot.revision,
	)
	undone_group = _element_by_id(_accepted_dom(undone.snapshot.cdml), "g1")

	assert "g1" not in result.atom_ids + result.bond_ids and result.snapshot.is_dirty
	assert undone_group.getAttribute("name") == "COOH" and redone.snapshot.cdml == result.snapshot.cdml


#============================================
def test_implicit_group_rejects_stale_request_without_changing_baseline_or_history() -> None:
	"""A stale operation remains an atomic typed backend failure."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_COOH)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.expand_implicit_group(
			oasa.cdml_document.CDMLImplicitGroupExpandRequest(before.revision + 1, "m1", "g1"),
		)

	assert session.snapshot() == before
