"""Behavioral tests for backend-authoritative direct atom alignment."""

# Standard Library
import re

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="1cm"/><v:keep/></atom><atom id="a2" name="O"><point x="2cm" y="3cm"/></atom><bond id="b1" start="a1" end="a2" type="w1"/></molecule>
 <v:opaque value="preserve"/><molecule id="m2"><atom id="a3" name="N"><point x="5cm" y="5cm"/></atom></molecule>
</cdml>
"""


#============================================
def _request(revision: int, axis: str = "horizontal", targets: tuple = (("m1", "a1"), ("m2", "a3"))) -> object:
	"""Build one alignment request against the fixture's direct core atoms."""
	return oasa.cdml_document.CDMLAtomAlignRequest(revision, axis, targets)


#============================================
def _centimeters(value: str) -> float:
	"""Return one fixture coordinate expressed in the CDML centimeter unit."""
	if not value.endswith("cm"):
		raise ValueError("fixture coordinate is not in centimeters")
	return float(value.removesuffix("cm"))


#============================================
def _atom_coordinates(cdml_text: str, atom_ids: tuple[str, ...]) -> tuple[tuple[float, float], ...]:
	"""Read fixture atom coordinates through the public CDML document boundary."""
	document = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	coordinates = []
	for atom_id in atom_ids:
		record = document.find_by_id(atom_id)
		if record is None:
			raise AssertionError("fixture atom is absent from parsed CDML: %s" % atom_id)
		values = dict(re.findall(r'\b([xy])="([^"]+)"', record.raw_xml))
		try:
			coordinates.append(tuple(_centimeters(values[axis]) for axis in ("x", "y")))
		except (KeyError, ValueError) as error:
			raise AssertionError("fixture atom has non-centimeter coordinates: %s" % atom_id) from error
	return tuple(coordinates)


#============================================
def test_atom_align_changes_only_requested_axis_across_root_molecules() -> None:
	"""Horizontal and vertical requests retain unrelated atom and bond content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	horizontal = session.align_atoms(_request(session.revision))
	vertical = session.align_atoms(_request(horizontal.snapshot.revision, "vertical"))
	horizontal_coordinates = _atom_coordinates(horizontal.snapshot.cdml, ("a1", "a3"))
	vertical_coordinates = _atom_coordinates(vertical.snapshot.cdml, ("a1", "a3"))
	document = oasa.cdml_document.CDMLDocument.parse(vertical.snapshot.cdml, validation="strict")
	root_order = tuple(record.local_name for record in document.objects())

	assert horizontal.changed and horizontal_coordinates == ((1.0, 3.0), (5.0, 3.0))
	assert vertical.changed and vertical_coordinates == ((3.0, 3.0), (3.0, 3.0))
	assert (
		'<v:keep/>' in vertical.snapshot.cdml
		and 'type="w1"' in vertical.snapshot.cdml
		and 'v:opaque' in vertical.snapshot.cdml
		and root_order == ("molecule", "opaque", "molecule")
	)


#============================================
def test_atom_align_preserves_extensions_and_noop_history() -> None:
	"""A canonical no-op preserves revision while atom-local extensions survive."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.align_atoms(_request(session.revision, targets=(("m1", "a1"),)))

	assert not result.changed and result.commit is None
	assert session.snapshot().revision == 0 and '<v:keep/>' in session.snapshot().cdml


#============================================
@pytest.mark.parametrize("axis", ("horizontal", "vertical"))
def test_atom_align_semantic_mean_noop_preserves_lexical_coordinates(axis: str) -> None:
	"""Equal parsed coordinates do not normalize compatible CDML spellings."""
	coordinates = 'x="1cm" y="3cm"' if axis == "horizontal" else 'x="3cm" y="1cm"'
	other = 'x="2cm" y="3.000cm"' if axis == "horizontal" else 'x="3.000cm" y="2cm"'
	cdml = (
		'<cdml version="26.07"><molecule id="m1">'
		'<atom id="a1" name="C"><point %s/></atom>'
		'<atom id="a2" name="O"><point %s/></atom>'
		'<bond id="b1" start="a1" end="a2" type="w1"/>'
		'</molecule></cdml>'
	) % (coordinates, other)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	before = session.snapshot()
	result = session.align_atoms(_request(before.revision, axis, (("m1", "a1"), ("m1", "a2"))))

	assert not result.changed and result.commit is None
	assert session.snapshot() == before and session.snapshot().revision == before.revision


#============================================
def test_atom_align_three_equal_coordinates_skip_mean_and_preserve_snapshot() -> None:
	"""Three equal parsed coordinates leave differently spelled CDML untouched."""
	cdml = (
		'<cdml version="26.07"><molecule id="m1">'
		'<atom id="a1" name="C"><point x="1cm" y="0.1cm"/></atom>'
		'<atom id="a2" name="C"><point x="2cm" y="0.10cm"/></atom>'
		'<atom id="a3" name="C"><point x="3cm" y="0.100cm"/></atom>'
		'</molecule></cdml>'
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	before = session.snapshot()
	result = session.align_atoms(_request(before.revision, targets=(
		("m1", "a1"), ("m1", "a2"), ("m1", "a3"),
	)))

	assert not result.changed and result.commit is None
	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize(
	"request_builder",
	(
		lambda revision: _request(revision, targets=(("m1", "missing"),)),
		lambda revision: _request(revision, targets=(("m1", "a1"), ("m1", "a1"))),
		lambda revision: _request(revision, "diagonal"),
		lambda revision: oasa.cdml_document.CDMLAtomAlignRequest(revision, "horizontal", (("m1", "a1", "extra"),)),
	),
)
def test_atom_align_rejection_is_atomic(request_builder: object) -> None:
	"""Malformed, duplicate, or unavailable targets cannot partially commit."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLDocumentError):
		session.align_atoms(request_builder(before.revision))
	assert session.snapshot() == before


#============================================
def test_atom_align_stale_and_restore_use_backend_history() -> None:
	"""The revision fence and restore history own persisted alignment state."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	original = session.snapshot()
	result = session.align_atoms(_request(original.revision))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.align_atoms(_request(original.revision, "vertical"))
	restored = session.restore(
		target_revision=original.revision, expected_revision=result.snapshot.revision,
	)

	assert restored.revision > result.snapshot.revision
	assert restored.cdml == session.snapshot().cdml == original.cdml


#============================================
def test_atom_align_rejects_nested_or_opaque_atom_targets_without_mutation() -> None:
	"""Only direct core root molecules and their direct core atoms are addressable."""
	nested = _CDML.replace('<molecule id="m2">', '<fragment><molecule id="m2">')
	nested = nested.replace('</molecule>\n</cdml>', '</molecule></fragment>\n</cdml>')
	opaque = _CDML.replace('<molecule id="m2">', '<v:wrapper><molecule id="m2">')
	opaque = opaque.replace('</molecule>\n</cdml>', '</molecule></v:wrapper>\n</cdml>')
	for text in (nested, opaque):
		session = oasa.cdml_document.CDMLDocumentSession.load(text)
		before = session.snapshot()
		with pytest.raises(oasa.cdml_document.CDMLValidationError):
			session.align_atoms(_request(before.revision))
		assert session.snapshot() == before
