"""Behavioral tests for backend-authoritative direct atom rotation."""

# Standard Library
import math
import re

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document


_CDML = """\
<cdml xmlns:v="urn:vendor" version="26.07"><molecule id="m1"><atom id="a1" name="C"><point x="2cm" y="0cm" z="7cm"/><v:keep/></atom><atom id="a2" name="O"><point x="0cm" y="2cm"/></atom><fragment><atom id="nested" name="N"><point x="1cm" y="1cm"/></atom></fragment></molecule><v:opaque id="opaque1" marker="keep"/><molecule id="m2"><atom id="a3" name="N"><point x="3cm" y="3cm"/></atom></molecule></cdml>
"""


#============================================
def _request(revision: int, targets: tuple = (("m1", "a1"),), center: tuple = (0.0, 0.0), angle: float = math.pi / 2) -> object:
	"""Build one plain immutable rotation request for the inline document."""
	return oasa.cdml_document.CDMLAtomRotateRequest(revision, targets, center, angle)


#============================================
def _point(cdml_text: str, atom_id: str) -> tuple[str, str, str | None]:
	"""Read one accepted point's lexical attributes through the CDML boundary."""
	document = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	record = document.find_by_id(atom_id)
	if record is None:
		raise AssertionError("accepted CDML omitted fixture atom")
	match = re.search(r'<point x="([^"]+)" y="([^"]+)"(?: z="([^"]+)")?', record.raw_xml)
	if match is None:
		raise AssertionError("accepted CDML omitted fixture point")
	return match.group(1), match.group(2), match.group(3)


#============================================
def test_atom_rotation_turns_scene_point_coordinates_and_preserves_z_and_opaque_content() -> None:
	"""A quarter turn converts scene center once and changes only target x/y."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.rotate_atoms(_request(session.revision, center=(72.0, 0.0)))

	assert result.changed and _point(result.snapshot.cdml, "a1") == ("2.540cm", "-0.540cm", "7cm")
	assert _point(result.snapshot.cdml, "a2")[:2] == ("0cm", "2cm") and 'marker="keep"' in result.snapshot.cdml


#============================================
def test_atom_rotation_exact_zero_is_a_lexical_noop_and_restore_owns_history() -> None:
	"""Zero validates revision then preserves snapshots; accepted turns restore exactly."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	no_change = session.rotate_atoms(_request(before.revision, angle=-0.0))
	rotated = session.rotate_atoms(_request(before.revision))
	restored = session.restore(
		target_revision=before.revision, expected_revision=rotated.snapshot.revision,
	)

	assert not no_change.changed and no_change.snapshot == before
	assert restored.cdml == before.cdml


#============================================
@pytest.mark.parametrize(
	"center, angle",
	(
		((0.0, 0.0), math.tau),
		((56.69291338582677, 0.0), math.pi / 2),
		((0.0, 0.0), 0.00001),
	),
)
def test_atom_rotation_canonical_noops_do_not_allocate_history(
		center: tuple[float, float], angle: float,
		) -> None:
	"""Full turns, fixed centers, and sub-resolution moves retain one snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = session.rotate_atoms(_request(before.revision, center=center, angle=angle))

	assert (result.changed, result.commit, result.snapshot) == (False, None, before)
	assert tuple(session._history) == (before.revision,)


#============================================
def test_atom_rotation_preserves_the_lexical_axis_that_is_canonically_unchanged() -> None:
	"""A changed rotation writes only the axis that differs at authored precision."""
	cdml = _CDML.replace('x="2cm" y="0cm"', 'x="2cm" y="1.0004cm"')
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	result = session.rotate_atoms(
		_request(session.revision, center=(0.0, 28.346456692913385), angle=math.pi),
	)

	assert _point(result.snapshot.cdml, "a1") == ("-2.000cm", "1.0004cm", "7cm")


#============================================
@pytest.mark.parametrize(
	"request_factory",
	(
		lambda revision: object(),
		lambda revision: _request(revision, targets=(("m1", "a1"), ("m1", "a1"))),
		lambda revision: _request(revision, targets=(("m1", "a1"), ("m1", "nested"))),
		lambda revision: _request(revision, targets=[("m1", "a1")]),
		lambda revision: _request(revision, targets=(("m1", "a1"),), center=[0.0, 0.0]),
		lambda revision: _request(revision, targets=(("m1", "a1"),), center=(0.0, 0.0), angle=True),
		lambda revision: _request(revision, center=(float("nan"), 0.0)),
		lambda revision: _request(revision, angle=float("inf")),
	),
)
def test_atom_rotation_invalid_requests_are_atomic(request_factory: object) -> None:
	"""Malformed targets and nonfinite values leave revision and snapshot unchanged."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLDocumentError):
		session.rotate_atoms(request_factory(before.revision))

	assert session.snapshot() == before


#============================================
def test_atom_rotation_stale_request_is_atomic() -> None:
	"""A stale valid rotation cannot overwrite a later accepted snapshot."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	session.rotate_atoms(_request(before.revision))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.rotate_atoms(_request(before.revision))

	assert session.revision == before.revision + 1
