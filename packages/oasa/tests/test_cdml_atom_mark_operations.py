"""Behavioral tests for backend-owned direct atom-mark operations."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


BASE_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <!-- retained comment -->
 <v:before id="opaque_before" keep="yes"/>
 <molecule id="m1" v:flag="preserve"><atom id="a1" name="C" v:atom="keep">
 <point x="1cm" y="2cm" z="0cm"/>
 <mark type="plus" x="9cm" y="9cm" auto="0" size="7" v:first="keep"/>
 <mark type="plus" x="8cm" y="8cm" auto="0" size="8" v:later="keep"/>
 <v:atom_payload>retain</v:atom_payload></atom><atom id="a2" name="N">
 <point x="3cm" y="4cm"/></atom></molecule>
 <arrow id="arrow1" type="normal"/>
 <v:after id="opaque_after" keep="yes"/>
</cdml>
"""


#============================================
def _request(revision: object, action: object, mark_type: object) -> object:
	"""Build one plain request against the fixture's direct atom."""
	return cdml_document.CDMLAtomMarkOperationRequest(revision, "m1", "a1", action, mark_type)


#============================================
def _state(session: cdml_document.CDMLDocumentSession) -> tuple[int, str, bool, tuple[int, ...]]:
	"""Capture observable backend state for atomic-rejection checks."""
	snapshot = session.snapshot()
	return snapshot.revision, snapshot.cdml, snapshot.is_dirty, tuple(sorted(session._history))


#============================================
def _accepted_atom(cdml_text: str, identifier: str) -> object:
	"""Read one atom only after the owning CDML boundary accepted the source."""
	accepted = cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for element in dom.getElementsByTagName("*"):
		if element.getAttribute("id") == identifier:
			return element
	raise AssertionError("accepted CDML did not contain atom %s" % identifier)


#============================================
def _direct_marks(atom: object, mark_type: str) -> list[object]:
	"""Return direct core marks of one type in their preserved child order."""
	return [
		child for child in atom.childNodes
		if getattr(child, "tagName", None) == "mark" and child.getAttribute("type") == mark_type
	]


#============================================
@pytest.mark.parametrize(("mark_type", "attributes"), (
	("plus", {"x": "1.299cm", "y": "2.299cm", "size": "10", "draw_circle": "yes"}),
	("minus", {"x": "1.299cm", "y": "2.299cm", "size": "10", "draw_circle": "yes"}),
	("radical", {"x": "1.000cm", "y": "2.423cm", "size": "4"}),
	("biradical", {"x": "1.000cm", "y": "2.423cm", "size": "4"}),
	("electronpair", {"x": "0.577cm", "y": "2.000cm", "size": "10", "line_width": "2"}),
	("dotted_electronpair", {"x": "0.577cm", "y": "2.000cm", "size": "4"}),
	("pz_orbital", {"x": "1.000cm", "y": "2.000cm", "size": "40"}),
))
def test_add_authors_every_supported_mark_with_portable_direct_coordinates(
		mark_type: str, attributes: dict[str, str],
		) -> None:
	"""Each supported form gets one explicit backend-owned direct-child record."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	result = session.apply_atom_mark(_request(session.revision, "add", mark_type))
	mark = _direct_marks(_accepted_atom(result.snapshot.cdml, "a1"), mark_type)[-1]

	assert result.changed and result.action_result == "added" and result.commit is not None
	assert all(mark.getAttribute(name) == value for name, value in attributes.items())
	assert (mark.getAttribute("auto"), mark.getAttribute("type")) == ("0", mark_type)


#============================================
@pytest.mark.parametrize(("mark_type", "attribute", "after_add", "after_remove"), (
	("plus", "charge", "1", ""), ("minus", "charge", "-1", ""),
	("radical", "multiplicity", "2", ""), ("biradical", "multiplicity", "3", ""),
))
def test_chemical_marks_apply_and_reverse_only_their_declared_scalar_delta(
		mark_type: str, attribute: str, after_add: str, after_remove: str,
		) -> None:
	"""Charge and multiplicity changes are one atomic mark-operation effect."""
	marks = (
		'<mark type="plus" x="9cm" y="9cm" auto="0" size="7" v:first="keep"/>'
		'<mark type="plus" x="8cm" y="8cm" auto="0" size="8" v:later="keep"/>'
	)
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML.replace(marks, ""))
	added = session.apply_atom_mark(_request(session.revision, "add", mark_type))
	removed = session.apply_atom_mark(_request(session.revision, "remove", mark_type))

	assert _accepted_atom(added.snapshot.cdml, "a1").getAttribute(attribute) == after_add
	assert _accepted_atom(removed.snapshot.cdml, "a1").getAttribute(attribute) == after_remove


#============================================
def test_remove_uses_first_direct_match_and_retains_later_duplicate_data() -> None:
	"""ID-less compatible duplicates retain direct-child-order identity."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	result = session.apply_atom_mark(_request(session.revision, "remove", "plus"))
	marks = _direct_marks(_accepted_atom(result.snapshot.cdml, "a1"), "plus")

	assert result.action_result == "removed" and result.changed
	assert len(marks) == 1 and marks[0].getAttribute("v:later") == "keep"


#============================================
def test_remove_with_a_matching_mark_index_removes_that_exact_duplicate() -> None:
	"""One ordinal selects its same-type direct core child, not the first match."""
	session = cdml_document.CDMLDocumentSession.load(
		BASE_CDML.replace('name="C"', 'name="C" charge="2"'),
	)
	result = session.apply_atom_mark(cdml_document.CDMLAtomMarkOperationRequest(
		session.revision, "m1", "a1", "remove", "plus", 1,
	))
	marks = _direct_marks(_accepted_atom(result.snapshot.cdml, "a1"), "plus")

	assert result.changed and marks[0].getAttribute("v:first") == "keep"
	assert _accepted_atom(result.snapshot.cdml, "a1").getAttribute("charge") == "1"


#============================================
@pytest.mark.parametrize("matching_mark_index", (True, -1, 2))
def test_invalid_mark_selector_rejects_without_changing_authoritative_state(
		matching_mark_index: object,
		) -> None:
	"""Selected-mark removal validates exact nonnegative in-range ordinals atomically."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLAtomMarkOperationError):
		session.apply_atom_mark(cdml_document.CDMLAtomMarkOperationRequest(
			session.revision, "m1", "a1", "remove", "plus", matching_mark_index,
		))

	assert session.snapshot() == before
	with pytest.raises(cdml_document.CDMLRevisionUnavailableError):
		session.restore(target_revision=1, expected_revision=before.revision)


#============================================
def test_missing_direct_match_is_a_stale_checked_history_free_noop() -> None:
	"""A no-match removal reports unchanged without creating backend history."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	before = session.snapshot()
	result = session.apply_atom_mark(_request(before.revision, "remove", "radical"))

	assert not result.changed and result.action_result == "unchanged" and result.snapshot == before
	with pytest.raises(cdml_document.CDMLRevisionUnavailableError):
		session.restore(target_revision=1, expected_revision=before.revision)


#============================================
def test_missing_match_checks_revision_before_reporting_a_noop() -> None:
	"""A stale removal cannot hide behind its otherwise harmless absent match."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	session.apply_atom_mark(_request(session.revision, "add", "radical"))
	before = _state(session)

	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.apply_atom_mark(_request(0, "remove", "dotted_electronpair"))

	assert _state(session) == before


#============================================
def test_presentation_marks_leave_existing_scalar_state_and_legacy_mark_residuals_intact() -> None:
	"""Only a declared chemistry delta changes charge or multiplicity state."""
	cdml = BASE_CDML.replace('name="C"', 'name="C" charge="4" multiplicity="2"')
	session = cdml_document.CDMLDocumentSession.load(cdml)
	electronpair = session.apply_atom_mark(_request(session.revision, "add", "electronpair"))
	minus = session.apply_atom_mark(_request(session.revision, "add", "minus"))
	target = _accepted_atom(minus.snapshot.cdml, "a1")

	assert _accepted_atom(electronpair.snapshot.cdml, "a1").getAttribute("charge") == "4"
	assert (target.getAttribute("charge"), target.getAttribute("multiplicity")) == ("3", "2")


#============================================
@pytest.mark.parametrize(("mark_type", "scalar_text", "expected_scalars"), (
	("plus", 'multiplicity="legacy"', ("1", "legacy")),
	("radical", 'charge="legacy"', ("legacy", "2")),
	("electronpair", 'charge="legacy" multiplicity="0"', ("legacy", "0")),
))
def test_mark_delta_preserves_incompatible_unaddressed_scalar_bytes(
		mark_type: str, scalar_text: str, expected_scalars: tuple[str, str],
		) -> None:
	"""One bounded mark delta neither validates nor normalizes its residual scalar."""
	cdml_text = BASE_CDML.replace('name="C"', 'name="C" %s' % scalar_text)
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	result = session.apply_atom_mark(_request(session.revision, "add", mark_type))
	atom = _accepted_atom(result.snapshot.cdml, "a1")

	assert result.changed
	assert (atom.getAttribute("charge"), atom.getAttribute("multiplicity")) == expected_scalars


#============================================
@pytest.mark.parametrize(("scalar_text", "action", "mark_type"), (
	('charge="9"', "add", "plus"),
	('multiplicity="3"', "add", "radical"),
	('charge="10"', "add", "minus"),
	('charge="-10"', "remove", "plus"),
	('multiplicity="0"', "add", "radical"),
	('charge="legacy"', "add", "plus"),
))
def test_bound_and_legacy_scalar_rejections_preserve_authoritative_state(
		scalar_text: str, action: str, mark_type: str,
		) -> None:
	"""Existing scalar bounds and exact spellings reject before detached mutation."""
	cdml_text = BASE_CDML.replace('name="C"', 'name="C" %s' % scalar_text)
	session = cdml_document.CDMLDocumentSession.load(cdml_text)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLAtomMarkOperationError):
		session.apply_atom_mark(_request(session.revision, action, mark_type))

	assert _state(session) == before


#============================================
def test_atom_mark_operation_preserves_opaque_content_comments_attributes_and_order() -> None:
	"""An accepted add mutates only the direct target atom and its scalar meaning."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	result = session.apply_atom_mark(_request(session.revision, "add", "electronpair"))
	target = _accepted_atom(result.snapshot.cdml, "a1")

	assert (
		target.getAttribute("v:atom") == "keep"
		and "<v:atom_payload>retain</v:atom_payload>" in target.toxml()
	)
	assert (
		"<!-- retained comment -->" in result.snapshot.cdml
		and result.snapshot.cdml.index('id="opaque_before"') < result.snapshot.cdml.index('id="m1"')
		< result.snapshot.cdml.index('id="arrow1"') < result.snapshot.cdml.index('id="opaque_after"')
	)


#============================================
@pytest.mark.parametrize("attempt", (
	object(),
	cdml_document.CDMLAtomMarkOperationRequest(True, "m1", "a1", "add", "plus"),
	cdml_document.CDMLAtomMarkOperationRequest(0, "", "a1", "add", "plus"),
	cdml_document.CDMLAtomMarkOperationRequest(0, "m1", "", "add", "plus"),
	cdml_document.CDMLAtomMarkOperationRequest(0, "m1", "a1", "toggle", "plus"),
	cdml_document.CDMLAtomMarkOperationRequest(0, "m1", "a1", "add", "text_mark"),
	cdml_document.CDMLAtomMarkOperationRequest(0, "m1", "nested", "add", "plus"),
))
def test_invalid_or_unsupported_mark_requests_leave_authoritative_state_unchanged(
		attempt: object,
		) -> None:
	"""Request shapes and unsupported target geometry reject before state changes."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.apply_atom_mark(attempt)

	assert _state(session) == before


#============================================
def test_missing_or_nested_coordinate_geometry_rejects_without_partial_mark_state() -> None:
	"""Only one usable direct atom point can supply authored mark coordinates."""
	for variant in (
		BASE_CDML.replace('<point x="3cm" y="4cm"/>', ""),
		BASE_CDML.replace('<point x="3cm" y="4cm"/>', '<point x="3cm" y="4cm"/><point x="5cm" y="6cm"/>'),
		BASE_CDML.replace('<point x="3cm" y="4cm"/>', '<point x="not-a-coordinate" y="4cm"/>'),
	):
		session = cdml_document.CDMLDocumentSession.load(variant)
		before = _state(session)

		with pytest.raises(cdml_document.CDMLAtomMarkOperationError):
			session.apply_atom_mark(cdml_document.CDMLAtomMarkOperationRequest(
				session.revision, "m1", "a2", "add", "plus",
			))

		assert _state(session) == before


#============================================
def test_nested_atom_target_cannot_be_addressed_as_a_direct_atom_mark_target() -> None:
	"""A compatible nested atom remains outside the bounded direct-target grammar."""
	cdml = BASE_CDML.replace(
		'</molecule>',
		'<fragment id="fragment1"><atom id="nested" name="C"><point x="0cm" y="0cm"/>'
		'</atom></fragment></molecule>',
	)
	session = cdml_document.CDMLDocumentSession.load(cdml)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.apply_atom_mark(cdml_document.CDMLAtomMarkOperationRequest(
			session.revision, "m1", "nested", "add", "plus",
		))

	assert _state(session) == before


#============================================
def test_opaque_atom_target_cannot_be_addressed_as_a_direct_atom_mark_target() -> None:
	"""Foreign atom-shaped XML remains opaque rather than becoming a mark target."""
	cdml = BASE_CDML.replace(
		'</molecule>',
		'<v:atom id="opaque_atom" name="C"><point x="0cm" y="0cm"/></v:atom></molecule>',
	)
	session = cdml_document.CDMLDocumentSession.load(cdml)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.apply_atom_mark(cdml_document.CDMLAtomMarkOperationRequest(
			session.revision, "m1", "opaque_atom", "add", "plus",
		))

	assert _state(session) == before


#============================================
def test_stale_mark_request_does_not_replay_after_an_accepted_mark() -> None:
	"""An obsolete candidate cannot repeat a completed persistent mark action."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	request = _request(session.revision, "add", "radical")
	session.apply_atom_mark(request)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.apply_atom_mark(request)

	assert _state(session) == before
