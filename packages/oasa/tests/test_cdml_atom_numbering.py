"""Behavioral tests for backend-owned CDML direct atom numbering."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document
import oasa.safe_xml


#============================================
BASE_CDML = """\
<cdml xmlns:vendor="urn:vendor">
 <vendor:note id="opaque_before" marker="keep">before</vendor:note>
 <molecule id="m_one">
  <atom id="a_numbered" name="C" number="4" show_number="yes" charge="1"><point x="0cm" y="0cm" /><vendor:payload marker="retain">payload</vendor:payload></atom>
  <atom id="a_hidden" name="N" number="8" show_number="no"><point x="1cm" y="0cm" /></atom>
  <atom id="a_legacy" name="O"><point x="2cm" y="0cm" /><mark type="atom_number" vendor:flag="preserve" /></atom>
  <fragment id="f_one"><atom id="a_nested" name="C"><point x="3cm" y="0cm" /></atom></fragment>
  <vendor:atom id="a_opaque" name="C"><point x="4cm" y="0cm" /></vendor:atom>
 </molecule>
 <vendor:molecule id="m_opaque"><atom id="a_hidden_root" name="C"><point x="5cm" y="0cm" /></atom></vendor:molecule>
 <vendor:note id="opaque_after" marker="keep">after</vendor:note>
</cdml>
"""


class _DerivedAtomNumberEditRequest(cdml_document.CDMLAtomNumberEditRequest):
	"""A runtime subtype used to prove the request boundary remains exact."""


#============================================
def _request(
		revision: object, molecule_id: object, atom_id: object, number: object, show_number: object,
		) -> object:
	"""Build one plain request, including deliberately invalid runtime shapes."""
	return cdml_document.CDMLAtomNumberEditRequest(
		expected_revision=revision,
		molecule_id=molecule_id,
		atom_id=atom_id,
		number=number,
		show_number=show_number,
	)


#============================================
def _state(session: cdml_document.CDMLDocumentSession) -> tuple[int, str]:
	"""Capture observable authoritative state for atomic-rejection checks."""
	snapshot = session.snapshot()
	return snapshot.revision, snapshot.cdml


#============================================
def _accepted_element(cdml_text: str, identifier: str) -> object:
	"""Inspect accepted content only after strict CDML parsing."""
	accepted = cdml_document.CDMLDocument.parse(cdml_text, validation="strict")
	dom = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	for element in dom.getElementsByTagName("*"):
		if element.getAttribute("id") == identifier:
			return element
	raise AssertionError(f"accepted CDML did not contain element {identifier}")


#============================================
def _direct_legacy_mark_xml(cdml_text: str) -> str:
	"""Return the preserved direct legacy mark after strict boundary parsing."""
	legacy = _accepted_element(cdml_text, "a_legacy")
	for child in legacy.childNodes:
		if getattr(child, "tagName", None) == "mark":
			return child.toxml()
	raise AssertionError("accepted CDML did not retain the direct legacy mark")


#============================================
def test_assignment_replaces_only_the_named_direct_atom_number_and_preserves_content() -> None:
	"""A direct replacement retains selected, unrelated, opaque, and source-order data."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	commit = session.set_atom_number(_request(session.revision, "m_one", "a_numbered", 21, False))
	target = _accepted_element(commit.cdml, "a_numbered")
	unrelated = _accepted_element(commit.cdml, "a_hidden")

	assert (
		target.getAttribute("number"), target.getAttribute("show_number"),
		target.getAttribute("charge"), 'vendor:payload marker="retain">payload</vendor:payload>' in target.toxml(),
	) == ("21", "no", "1", True)
	assert (
		unrelated.getAttribute("number"), unrelated.getAttribute("show_number"),
		'vendor:note id="opaque_before"' in commit.cdml,
		commit.cdml.index('id="opaque_before"') < commit.cdml.index('id="m_one"') < commit.cdml.index('id="opaque_after"'),
	) == ("8", "no", True, True)


#============================================
def test_clear_removes_both_number_fields_from_a_hidden_assignment() -> None:
	"""Clear removes the canonical number pair without changing the atom identity."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	commit = session.set_atom_number(_request(session.revision, "m_one", "a_hidden", None, None))
	target = _accepted_element(commit.cdml, "a_hidden")

	assert (target.getAttribute("number"), target.getAttribute("show_number"), target.getAttribute("id")) == ("", "", "a_hidden")


#============================================
def test_targeted_direct_legacy_mark_is_a_typed_atomic_compatibility_failure() -> None:
	"""A selected legacy mark rejects numbering without changing authoritative state."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLAtomNumberCompatibilityError):
		session.set_atom_number(_request(session.revision, "m_one", "a_legacy", 12, True))

	assert _state(session) == before


#============================================
def test_editing_another_atom_preserves_the_direct_legacy_mark_exactly() -> None:
	"""An unrelated number edit leaves legacy compatibility content untouched."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	before_mark = _direct_legacy_mark_xml(session.snapshot().cdml)
	commit = session.set_atom_number(_request(session.revision, "m_one", "a_numbered", 12, True))

	assert _direct_legacy_mark_xml(commit.cdml) == before_mark


#============================================
def test_nested_opaque_legacy_mark_does_not_block_the_direct_atom_number_edit() -> None:
	"""A non-direct legacy-looking mark remains opaque while its atom is numbered."""
	variant = """\
<cdml xmlns:vendor="urn:vendor">
 <vendor:note id="opaque_before" marker="keep">before</vendor:note>
 <molecule id="m_one">
  <atom id="a_numbered" name="C" number="4" show_number="yes" charge="1"><point x="0cm" y="0cm" /><vendor:legacy_wrapper marker="keep"><mark type="atom_number" vendor:flag="preserve" /></vendor:legacy_wrapper></atom>
  <atom id="a_hidden" name="N" number="8" show_number="no"><point x="1cm" y="0cm" /></atom>
  <atom id="a_legacy" name="O"><point x="2cm" y="0cm" /><mark type="atom_number" vendor:flag="preserve" /></atom>
  <fragment id="f_one"><atom id="a_nested" name="C"><point x="3cm" y="0cm" /></atom></fragment>
  <vendor:atom id="a_opaque" name="C"><point x="4cm" y="0cm" /></vendor:atom>
 </molecule>
 <vendor:molecule id="m_opaque"><atom id="a_hidden_root" name="C"><point x="5cm" y="0cm" /></atom></vendor:molecule>
 <vendor:note id="opaque_after" marker="keep">after</vendor:note>
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(variant)
	commit = session.set_atom_number(_request(session.revision, "m_one", "a_numbered", 12, True))
	target = _accepted_element(commit.cdml, "a_numbered")
	wrapper = next(child for child in target.childNodes if getattr(child, "tagName", None) == "vendor:legacy_wrapper")
	mark = next(child for child in wrapper.childNodes if getattr(child, "tagName", None) == "mark")

	assert (
		target.getAttribute("number"), target.getAttribute("show_number"),
		wrapper.getAttribute("marker"), mark.getAttribute("type"), mark.getAttribute("vendor:flag"),
	) == ("12", "yes", "keep", "atom_number", "preserve")


#============================================
def test_nested_core_legacy_mark_does_not_block_the_direct_atom_number_edit() -> None:
	"""A core ftext nesting does not turn its mark into a direct legacy mark."""
	variant = """\
<cdml>
 <molecule id="m_one">
  <atom id="a_numbered" name="C" number="4" show_number="yes"><ftext><mark type="atom_number" text="legacy label" draw_circle="yes" /></ftext><point x="0cm" y="0cm" /></atom>
 </molecule>
</cdml>
"""
	session = cdml_document.CDMLDocumentSession.load(variant)
	commit = session.set_atom_number(_request(session.revision, "m_one", "a_numbered", 12, True))
	target = _accepted_element(commit.cdml, "a_numbered")
	ftext = next(child for child in target.childNodes if getattr(child, "tagName", None) == "ftext")
	mark = next(child for child in ftext.childNodes if getattr(child, "tagName", None) == "mark")

	assert (
		target.getAttribute("number"), target.getAttribute("show_number"),
		mark.getAttribute("type"), mark.getAttribute("text"), mark.getAttribute("draw_circle"),
	) == ("12", "yes", "atom_number", "legacy label", "yes")


#============================================
@pytest.mark.parametrize("attempt", (
	object(),
	_DerivedAtomNumberEditRequest(0, "m_one", "a_numbered", 3, True),
	_request(True, "m_one", "a_numbered", 3, True),
	_request(0, "", "a_numbered", 3, True),
	_request(0, "m_one", "", 3, True),
	_request(0, "m_one", "a_numbered", True, True),
	_request(0, "m_one", "a_numbered", 0, True),
	_request(0, "m_one", "a_numbered", 3, 1),
	_request(0, "m_one", "a_numbered", None, True),
	_request(0, "m_one", "a_numbered", 3, None),
	_request(0, "m_one", "a_missing", 3, True),
	_request(0, "m_one", "f_one", 3, True),
	_request(0, "m_one", "a_nested", 3, True),
	_request(0, "m_one", "a_opaque", 3, True),
	_request(0, "m_opaque", "a_hidden_root", 3, True),
))
def test_invalid_number_requests_and_direct_target_boundaries_leave_state_unchanged(
		attempt: object,
		) -> None:
	"""Malformed values and non-direct targets are rejected before state changes."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLValidationError):
		session.set_atom_number(attempt)

	assert _state(session) == before


#============================================
def test_stale_number_request_never_replays_over_the_newer_authoritative_snapshot() -> None:
	"""An obsolete request cannot overwrite a later accepted number operation."""
	session = cdml_document.CDMLDocumentSession.load(BASE_CDML)
	request = _request(session.revision, "m_one", "a_numbered", 15, True)
	session.set_atom_number(request)
	before = _state(session)

	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.set_atom_number(request)

	assert _state(session) == before
