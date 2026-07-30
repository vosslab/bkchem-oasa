"""Behavioral tests for backend-authoritative direct atom translation."""

# Standard Library
import re

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m1"><atom id="a1" name="C"><point x="1.000cm" y="2cm"/><v:keep/></atom><atom id="a2" name="O"><point x="3cm" y="4cm"/></atom><bond id="b1" start="a1" end="a2" type="w1"/></molecule>
 <v:opaque id="opaque1" marker="preserve"/><molecule id="m2"><atom id="a3" name="N"><point x="5cm" y="6cm"/></atom></molecule>
</cdml>
"""

_TARGET_BOUNDARY_CDML = """\
<cdml xmlns:v="urn:vendor" version="26.07">
 <molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="2cm"/></atom><atom name="H"><point x="3cm" y="4cm"/></atom><fragment><atom id="a_nested" name="N"><point x="5cm" y="6cm"/></atom></fragment><v:atom id="a_opaque" name="O"><point x="7cm" y="8cm"/></v:atom></molecule>
</cdml>
"""


#============================================
def _request(
		revision: int, targets: tuple = (("m1", "a1"), ("m1", "a2")),
		delta: tuple = (2.0, -3.0),
		) -> object:
	"""Build one direct-atom translation request for the inline CDML fixture."""
	return oasa.cdml_document.CDMLAtomTranslateRequest(revision, targets, delta)


#============================================
def _coordinates(cdml_text: str, atom_ids: tuple[str, ...]) -> tuple[tuple[float, float], ...]:
	"""Read accepted coordinate values after the public CDML parser validates them."""
	document = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	coordinates = []
	for atom_id in atom_ids:
		record = document.find_by_id(atom_id)
		if record is None:
			raise AssertionError("fixture atom is absent from accepted CDML: %s" % atom_id)
		values = dict(re.findall(r'\b([xy])="([^"]+)"', record.raw_xml))
		coordinates.append(tuple(
			float(values[axis].removesuffix("cm")) for axis in ("x", "y")
		))
	return tuple(coordinates)


#============================================
def _accepted_point_attributes(cdml_text: str, atom_id: str) -> tuple[str, str]:
	"""Read one accepted atom point after the hardened CDML boundary."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for atom in dom.getElementsByTagName("atom"):
		if atom.getAttribute("id") == atom_id:
			point = next(
				child for child in atom.childNodes if getattr(child, "tagName", None) == "point"
			)
			return point.getAttribute("x"), point.getAttribute("y")
	raise AssertionError("accepted CDML did not contain fixture atom: %s" % atom_id)


#============================================
def _accepted_root_names(cdml_text: str) -> tuple[str, ...]:
	"""Read preserved direct-root order after strict CDML acceptance."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	root = oasa.safe_xml.parse_dom_from_string(accepted.serialize()).documentElement
	return tuple(
		child.tagName for child in root.childNodes if getattr(child, "tagName", None) is not None
	)


#============================================
def test_atom_translation_patches_only_target_points_and_preserves_opaque_content() -> None:
	"""One multi-atom nudge changes coordinates without rebuilding persistent CDML."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.translate_atoms(_request(session.revision))
	coordinates = _coordinates(result.snapshot.cdml, ("a1", "a2", "a3"))

	assert result.changed and coordinates == ((1.071, 1.894), (3.071, 3.894), (5.0, 6.0))
	assert '<v:keep/>' in result.snapshot.cdml and 'marker="preserve"' in result.snapshot.cdml


#============================================
@pytest.mark.parametrize(
	("delta", "expected"),
	(
		((2.0, 0.0), ("2.611cm", "2.000cm")),
		((0.0, 2.0), ("72", "2.071cm")),
	),
)
def test_single_atom_translation_preserves_the_untouched_axis_lexically(
		delta: tuple[float, float], expected: tuple[str, str],
		) -> None:
	"""A one-axis nudge changes only its requested coordinate attribute."""
	cdml = (
		'<cdml version="26.07"><molecule id="m1">'
		'<atom id="a1" name="C"><point x="72" y="2.000cm"/></atom>'
		'</molecule></cdml>'
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	result = session.translate_atoms(_request(session.revision, targets=(("m1", "a1"),), delta=delta))

	assert result.changed and _accepted_point_attributes(result.snapshot.cdml, "a1") == expected


#============================================
def test_atom_translation_preserves_root_order_and_atom_extension_content() -> None:
	"""A durable target changes without rebuilding root or atom extension content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.translate_atoms(_request(session.revision, targets=(("m1", "a1"),)))

	assert (
		result.changed
		and _accepted_root_names(result.snapshot.cdml) == ("molecule", "v:opaque", "molecule")
		and '<v:keep/>' in result.snapshot.cdml
		and 'marker="preserve"' in result.snapshot.cdml
	)


#============================================
def test_atom_translation_zero_delta_preserves_lexical_snapshot_and_history() -> None:
	"""A numeric zero nudge leaves compatible coordinate spellings untouched."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = session.translate_atoms(_request(before.revision, delta=(-0.0, 0.0)))

	assert not result.changed and result.commit is None
	assert session.snapshot() == before and 'x="1.000cm"' in session.snapshot().cdml


#============================================
def test_atom_translation_sub_resolution_delta_preserves_snapshot_and_history() -> None:
	"""A finite point delta that rounds unchanged at CDML's three decimals is a no-op."""
	cdml = (
		'<cdml version="26.07"><molecule id="m1">'
		'<atom id="a1" name="C"><point x="1.000cm" y="2.000cm"/></atom>'
		'</molecule></cdml>'
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	before = session.snapshot()
	before_history = dict(session._history)
	result = session.translate_atoms(
		_request(before.revision, targets=(("m1", "a1"),), delta=(0.000001, 0.0)),
	)

	assert not result.changed and result.commit is None
	assert (
		result.snapshot == before
		and session.snapshot() == before
		and session._history == before_history
	)


#============================================
@pytest.mark.parametrize(
	"attempt",
	(
		lambda revision: object(),
		lambda revision: _request(revision, targets=(("m1", "a1"), ("m1", "a1"))),
		lambda revision: _request(revision, targets=(("m1", "missing"),)),
		lambda revision: _request(revision, delta=(float("nan"), 0.0)),
	),
)
def test_atom_translation_invalid_requests_are_atomic(attempt: object) -> None:
	"""Malformed, duplicate, missing, and nonfinite requests cannot partially move atoms."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLDocumentError):
		session.translate_atoms(attempt(before.revision))

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize(
	"invalid_target",
	(("m1", "a_nested"), ("m1", "a_opaque"), ("m1", "idless")),
)
def test_atom_translation_valid_first_target_and_ineligible_later_target_are_atomic(
		invalid_target: tuple[str, str],
		) -> None:
	"""A later nested, opaque, or ID-less target cannot move an earlier atom."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_TARGET_BOUNDARY_CDML)
	before = session.snapshot()
	request = _request(before.revision, targets=(("m1", "a1"), invalid_target))
	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		session.translate_atoms(request)

	assert session.snapshot() == before


#============================================
def test_atom_translation_stale_request_and_backend_restore_preserve_snapshots() -> None:
	"""Revision fencing and backend history own persisted nudge state."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	original = session.snapshot()
	translated = session.translate_atoms(_request(original.revision))
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.translate_atoms(_request(original.revision, delta=(2.0, 0.0)))
	restored = session.restore(
		target_revision=original.revision, expected_revision=translated.snapshot.revision,
	)
	redone = session.restore(
		target_revision=translated.snapshot.revision, expected_revision=restored.revision,
	)

	assert restored.cdml == original.cdml and redone.cdml == translated.snapshot.cdml
