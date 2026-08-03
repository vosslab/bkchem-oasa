"""Behavioral tests for atomic backend-owned mixed selection translation."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m1"><atom id="a1" name="C"><point x="72" y="2.000cm"/><mark type="plus" x="1.000cm" y="3cm"/><mark type="radical"/></atom><atom id="a2" name="O"><point x="4cm" y="5cm"/></atom><bond id="b1" start="a1" end="a2" type="n1"/></molecule>
 <arrow id="arrow1"><point x="6cm" y="2cm"/><point x="8cm" y="2cm"/></arrow><text id="text1"><point x="10cm" y="3cm"/><ftext>label</ftext></text><v:opaque id="keep" payload="unchanged"/>
</cdml>
"""


#============================================
def _request(
		revision: int, atom_targets: tuple = (("m1", "a1"),),
		presentation_root_ids: tuple = ("arrow1", "text1"), delta: tuple = (72.0, -36.0),
		) -> oasa.cdml_document.CDMLSelectionTranslateRequest:
	"""Build one exact mixed selection translation request."""
	return oasa.cdml_document.CDMLSelectionTranslateRequest(
		revision, atom_targets, presentation_root_ids, delta,
	)


#============================================
def _direct_geometry(
		cdml: str, identifier: str,
		) -> tuple[tuple[str, str], tuple[tuple[str, str], ...]]:
	"""Read direct point and mark geometry through the hardened CDML boundary."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for element in dom.getElementsByTagName("*"):
		if element.getAttribute("id") != identifier:
			continue
		points = tuple(
			(point.getAttribute("x"), point.getAttribute("y"))
			for point in element.childNodes
			if getattr(point, "tagName", None) == "point"
		)
		marks = tuple(
			(mark.getAttribute("x"), mark.getAttribute("y"))
			for mark in element.childNodes
			if getattr(mark, "tagName", None) == "mark"
		)
		return points, marks
	raise AssertionError("fixture object is absent: %s" % identifier)


#============================================
def test_mixed_selection_commits_one_revision_and_restores_exact_snapshots() -> None:
	"""One mixed commit has one revision and exact backend restore/redo history."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	original = session.snapshot()
	accepted = session.translate_selection(_request(original.revision))
	restored = session.restore(
		target_revision=original.revision, expected_revision=accepted.snapshot.revision,
	)
	redone = session.restore(
		target_revision=accepted.snapshot.revision, expected_revision=restored.revision,
	)

	assert accepted.changed and accepted.snapshot.revision == original.revision + 1
	assert (restored.cdml, redone.cdml) == (original.cdml, accepted.snapshot.cdml)


#============================================
def test_mixed_selection_moves_the_selected_atom_and_explicit_mark_geometry() -> None:
	"""The backend applies the common delta to the selected atom and explicit mark."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.translate_selection(_request(session.revision))
	expected_geometry = (
		(("5.080cm", "0.730cm"),),
		(("3.540cm", "1.730cm"), ("", "")),
	)

	assert _direct_geometry(result.snapshot.cdml, "a1") == expected_geometry


#============================================
def test_mixed_selection_moves_each_selected_presentation_root_geometry() -> None:
	"""The same backend transaction moves selected arrow and text roots together."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.translate_selection(_request(session.revision))
	actual_geometry = (
		_direct_geometry(result.snapshot.cdml, "arrow1"),
		_direct_geometry(result.snapshot.cdml, "text1"),
	)
	expected_geometry = (
		((("8.540cm", "0.730cm"), ("10.540cm", "0.730cm")), ()),
		((("12.540cm", "1.730cm"),), ()),
	)

	assert actual_geometry == expected_geometry


#============================================
def test_mixed_selection_preserves_opaque_unselected_content_and_untouched_axis_spelling() -> None:
	"""A one-axis movement preserves untouched spelling and unrelated XML."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.translate_selection(_request(
		session.revision, presentation_root_ids=("arrow1",), delta=(72.0, 0.0),
	))

	assert _direct_geometry(result.snapshot.cdml, "a1") == (
		(("5.080cm", "2.000cm"),), (("3.540cm", "3cm"), ("", "")),
	)
	assert '<v:opaque id="keep" payload="unchanged"/>' in result.snapshot.cdml


#============================================
@pytest.mark.parametrize("delta", ((0.0, -0.0), (0.000001, 0.0)))
def test_zero_and_canonical_noop_validate_every_target_without_history(
		delta: tuple[float, float],
		) -> None:
	"""Zero and sub-resolution requests retain exact CDML after validation."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = session.translate_selection(_request(before.revision, delta=delta))

	assert not result.changed
	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize(
	"request_builder",
	(
		lambda revision: object(),
		lambda revision: _request(revision, atom_targets=(("m1", "a1"), ("m1", "a1"))),
		lambda revision: _request(revision, presentation_root_ids=("arrow1", "arrow1")),
		lambda revision: _request(revision, atom_targets=(("m1", "arrow1"),)),
		lambda revision: _request(revision, delta=(False, 0.0)),
		lambda revision: _request(revision, delta=(float("inf"), 0.0)),
	),
)
def test_request_grammar_rejects_ambiguous_or_nonfinite_input_atomically(
		request_builder: object,
		) -> None:
	"""Exact grammar rejects malformed durable intent before candidate mutation."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLSelectionTranslateError):
		session.translate_selection(request_builder(before.revision))

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("root_id", ("m1", "a1", "keep", "missing"))
def test_wrong_nested_opaque_and_missing_presentation_roots_are_atomic(root_id: str) -> None:
	"""Only direct supported presentation roots participate in this operation."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLSelectionTranslateError):
		session.translate_selection(_request(before.revision, presentation_root_ids=(root_id,)))

	assert session.snapshot() == before


#============================================
def test_late_malformed_mark_rejects_before_history_or_candidate_commit() -> None:
	"""A later selected malformed mark rolls back and consumes no revision."""
	malformed = _CDML.replace(
		'<atom id="a2" name="O"><point x="4cm" y="5cm"/></atom>',
		'<atom id="a2" name="O"><point x="4cm" y="5cm"/><mark type="plus" x="4cm"/></atom>',
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(malformed)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLSelectionTranslateError):
		session.translate_selection(_request(
		before.revision, atom_targets=(("m1", "a1"), ("m1", "a2")),
	))
	assert session.snapshot() == before
	accepted = session.translate_selection(_request(before.revision))

	assert accepted.changed and accepted.snapshot.revision == before.revision + 1


#============================================
def test_two_atoms_in_one_molecule_move_in_one_mixed_commit() -> None:
	"""Unique atom pairs may deliberately share a direct-root molecule ID."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.translate_selection(_request(
		session.revision, atom_targets=(("m1", "a1"), ("m1", "a2")),
	))

	assert result.changed
	assert _direct_geometry(result.snapshot.cdml, "a2")[0] == (("6.540cm", "3.730cm"),)


#============================================
@pytest.mark.parametrize(
	"atom_target", (("missing-molecule", "missing-atom"), ("m1", "missing-atom")),
)
def test_missing_atom_targets_raise_the_operation_specific_error(
		atom_target: tuple[str, str],
		) -> None:
	"""Missing molecule and atom IDs retain the selection operation error type."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLSelectionTranslateError):
		session.translate_selection(_request(before.revision, atom_targets=(atom_target,)))

	assert session.snapshot() == before


#============================================
def test_stale_selection_translation_preserves_the_accepted_snapshot() -> None:
	"""An older mixed request cannot overwrite one accepted authoritative edit."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	original = session.snapshot()
	session.translate_selection(_request(original.revision))
	accepted = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.translate_selection(_request(original.revision, delta=(36.0, 0.0)))

	assert session.snapshot() == accepted
