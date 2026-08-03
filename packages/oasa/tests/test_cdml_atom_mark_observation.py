"""Behavioral coverage for revision-bound atom-mark projection facts."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document as cdml_document


_CDML = """<cdml xmlns=\"http://www.freesoftware.fsf.org/bkchem/cdml\" xmlns:v=\"urn:v\">
<molecule id=\"m1\"><atom id=\"a1\" name=\"C\"><point x=\"10px\" y=\"20\"/>
<mark type=\"plus\" x=\"22px\" y=\"20\"/><v:mark type=\"plus\" x=\"0\" y=\"0\"/>
<mark type=\"plus\" x=\"34\" y=\"20\"/><mark type=\"atom_number\"/></atom></molecule></cdml>"""


#============================================
def test_atom_mark_observation_normalizes_editable_duplicate_geometry() -> None:
	"""Core duplicates have durable ordinals and unit-aware final rendering facts."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	observation = session.atom_mark_observation(
		cdml_document.CDMLAtomMarkObservationQuery(session.revision),
	)
	record = observation.records[2]

	assert record.disposition == "editable" and record.same_type_ordinal == 1
	assert (record.angle_degrees, record.radial_offset_pt, record.draw_circle) == (0.0, 24.0, True)


#============================================
def test_atom_mark_observation_keeps_foreign_and_legacy_marks_display_only() -> None:
	"""Lookalikes and legacy number marks remain readable but non-actionable."""
	session = cdml_document.CDMLDocumentSession.load(_CDML)
	observation = session.atom_mark_observation(
		cdml_document.CDMLAtomMarkObservationQuery(session.revision),
	)

	assert {record.disposition for record in observation.records} == {"editable", "display-only"}


#============================================
def test_atom_mark_observation_scopes_anonymous_child_to_its_root_position() -> None:
	"""An idless mark remains observable through its durable root, not an invented ID."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m1'><atom name='C'><point x='0cm' y='0cm'/>"
		"<mark type='plus'/></atom></molecule></cdml>", validation="compat",
	)
	record = document.atom_mark_observation(0).records[0]

	assert (
		record.mark_type == "plus" and record.disposition == "display-only"
		and (record.molecule_id, record.atom_id) == (None, None)
		and (record.molecule_source_position, record.atom_source_position) == (1, 1)
	)


#============================================
def test_atom_mark_observation_rejects_a_stale_revision_without_mutation() -> None:
	"""An exact observation cannot silently read a newer backend revision."""
	session = cdml_document.CDMLDocumentSession.load(
		_CDML.replace("10px\" y=\"20", "1cm\" y=\"2cm"),
	)
	session.apply_atom_mark(cdml_document.CDMLAtomMarkOperationRequest(
		session.revision, "m1", "a1", "add", "minus",
	))
	before = session.snapshot()

	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.atom_mark_observation(cdml_document.CDMLAtomMarkObservationQuery(0))
	assert session.snapshot() == before
