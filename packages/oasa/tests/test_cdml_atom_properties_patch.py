"""Behavioral tests for atomic backend-authoritative atom-properties patches."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document


_CDML = """
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m1"><atom id="a1" name="C" vendor_keep="yes"><point x="1cm" y="2cm"/><ftext>keep</ftext><v:keep/></atom></molecule><v:opaque id="x1"/>
</cdml>
"""


#============================================
def _patch(revision: int, changes: tuple[tuple[str, object], ...]) -> object:
	"""Build direct durable intent against the inline atom."""
	return oasa.cdml_document.CDMLAtomPropertiesPatch(revision, "m1", "a1", changes)


#============================================
def test_atom_properties_patch_commits_all_dialog_fields_once_and_preserves_content() -> None:
	"""One accepted dialog intent commits once without disturbing opaque content."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.patch_atom_properties(_patch(session.revision, (
		("element", "O"), ("charge", -1), ("valency", 2), ("isotope", 18),
		("multiplicity", 2), ("show", True), ("show_hydrogens", True),
		("font_size", 15), ("line_color", "#A0B1c2"),
	)))

	assert result.changed and result.snapshot.revision == 1
	assert 'name="O"' in result.snapshot.cdml and 'charge="-1"' in result.snapshot.cdml
	assert 'hydrogens="on"' in result.snapshot.cdml and 'color="#a0b1c2"' in result.snapshot.cdml
	assert '<ftext>keep</ftext><v:keep/><font size="15" color="#a0b1c2"/>' in result.snapshot.cdml
	assert 'vendor_keep="yes"' in result.snapshot.cdml and '<v:opaque id="x1"/>' in result.snapshot.cdml


#============================================
def test_atom_properties_patch_clears_explicit_defaults_without_materializing_others() -> None:
	"""Default-valued intent removes documented optional attributes atomically."""
	cdml = _CDML.replace('name="C"', 'name="C" charge="2" isotope="13" multiplicity="3"')
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	result = session.patch_atom_properties(_patch(session.revision, (
		("charge", 0), ("isotope", None), ("multiplicity", 1),
	)))

	assert result.changed
	assert 'charge=' not in result.snapshot.cdml and 'isotope=' not in result.snapshot.cdml
	assert 'multiplicity=' not in result.snapshot.cdml and 'show=' not in result.snapshot.cdml


#============================================
def test_atom_properties_patch_noop_is_history_free_and_keeps_font_absent() -> None:
	"""Canonical equality keeps an accepted no-op snapshot and history unchanged."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = session.patch_atom_properties(_patch(before.revision, (("element", "C"),)))

	assert not result.changed and result.snapshot == before and '<font' not in before.cdml
	with pytest.raises(oasa.cdml_document.CDMLRevisionUnavailableError):
		session.restore(target_revision=1, expected_revision=before.revision)


#============================================
def test_atom_properties_patch_rejects_stale_or_non_direct_target_atomically() -> None:
	"""Stale and nested targets leave the authoritative snapshot unmodified."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	committed = session.patch_atom_properties(_patch(session.revision, (("charge", 1),)))
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.patch_atom_properties(_patch(0, (("charge", 2),)))
	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		session.patch_atom_properties(
			oasa.cdml_document.CDMLAtomPropertiesPatch(before.revision, "m1", "x1", (("charge", 2),)),
		)

	assert committed.changed and session.snapshot() == before


#============================================
def test_atom_properties_patch_updates_one_direct_font_without_losing_extensions() -> None:
	"""A direct font patch keeps its unrelated attributes and atom content intact."""
	cdml = _CDML.replace(
		'<ftext>keep</ftext>',
		'<font family="Courier" size="11" vendor_keep="yes"/><ftext>keep</ftext>',
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	result = session.patch_atom_properties(_patch(session.revision, (("font_size", 15),)))

	assert result.changed and 'family="Courier" size="15" vendor_keep="yes"' in result.snapshot.cdml
	assert '<ftext>keep</ftext><v:keep/>' in result.snapshot.cdml


#============================================
@pytest.mark.parametrize("changes", (
	(("charge", True),), (("element", "Xx"),), (("show", 1),),
	(("charge", 1), ("charge", 2)),
))
def test_atom_properties_patch_rejects_invalid_intent_before_mutation(
		changes: tuple[tuple[str, object], ...],
		) -> None:
	"""Unsupported scalar intent is a typed atomic failure."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLAtomPropertiesPatchError):
		session.patch_atom_properties(_patch(before.revision, changes))

	assert session.snapshot() == before


#============================================
def test_atom_properties_patch_rejects_hostile_field_and_multiple_direct_fonts() -> None:
	"""The boundary rejects hostile fields and ambiguous direct typed fonts."""
	class HostileField:
		"""Raise if membership attempts user-defined equality."""
		def __eq__(self, other: object) -> bool:
			raise RuntimeError("must remain inside typed boundary")

	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLAtomPropertiesPatchError):
		session.patch_atom_properties(_patch(before.revision, ((HostileField(), "C"),)))
	assert session.snapshot() == before

	with_fonts = _CDML.replace('<ftext>keep</ftext>', '<font size="12"/><font color="#000000"/>')
	font_session = oasa.cdml_document.CDMLDocumentSession.load(with_fonts)
	font_before = font_session.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLAtomPropertiesPatchError):
		font_session.patch_atom_properties(_patch(font_session.revision, (("font_size", 13),)))

	assert font_session.snapshot() == font_before
	with pytest.raises(oasa.cdml_document.CDMLRevisionUnavailableError):
		font_session.restore(target_revision=1, expected_revision=font_before.revision)
