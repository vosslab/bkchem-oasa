"""Behavioral tests for backend-authoritative exact CDML bond-type edits."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document


_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="2cm"/></atom><atom id="a2" name="O"><point x="3cm" y="4cm"/></atom><bond id="b1" start="a1" end="a2" type="w2" simple_double="1" center="no" auto_sign="1" vendor_keep="yes"><v:keep/></bond></molecule>
 <v:opaque id="x1"/><molecule id="m2"><atom id="a3" name="N"><point x="5cm" y="6cm"/></atom></molecule>
</cdml>
"""


#============================================
def _request(revision: int, bond_type: str) -> object:
	"""Create one exact-type request against the inline durable target."""
	return oasa.cdml_document.CDMLBondTypeEditRequest(revision, "m1", "b1", bond_type)


#============================================
def test_bond_type_edit_changes_only_type_character_and_preserves_content() -> None:
	"""A type change retains order, direction, attributes, children, and root order."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	result = session.set_bond_type(_request(session.revision, "h"))

	assert result.changed and 'type="h2"' in result.snapshot.cdml
	assert 'start="a1" end="a2"' in result.snapshot.cdml
	assert 'simple_double="1" center="no" auto_sign="1" vendor_keep="yes"' in result.snapshot.cdml
	assert "<v:keep/>" in result.snapshot.cdml and '<v:opaque id="x1"/>' in result.snapshot.cdml
	assert result.snapshot.cdml.index('id="m1"') < result.snapshot.cdml.index('id="x1"')


#============================================
def test_bond_type_edit_preserves_compatibility_hashed_spelling_for_h_noop() -> None:
	"""Legacy l/r remain lexical no-ops when requested as their semantic h type."""
	for compatibility_type in ("l1", "r1"):
		session = oasa.cdml_document.CDMLDocumentSession.load(
			_CDML.replace('type="w2"', 'type="%s"' % compatibility_type),
		)
		before = session.snapshot()
		result = session.set_bond_type(_request(before.revision, "h"))

		assert not result.changed and result.commit is None and result.snapshot == before


#============================================
def test_bond_type_edit_same_ordinary_type_is_a_history_free_noop() -> None:
	"""An exact ordinary type match retains its revision and no future history entry."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()
	result = session.set_bond_type(_request(before.revision, "w"))

	assert not result.changed and result.commit is None and result.snapshot == before
	with pytest.raises(oasa.cdml_document.CDMLRevisionUnavailableError):
		session.restore(target_revision=before.revision + 1, expected_revision=before.revision)


#============================================
def test_bond_type_edit_converts_haworth_and_compatibility_type_without_touching_order() -> None:
	"""q1 and l1 can become ordinary type spellings while retaining their order."""
	for current_type, requested_type, expected_type in (
			("q1", "a", "a1"), ("l1", "w", "w1"),
		):
		session = oasa.cdml_document.CDMLDocumentSession.load(
			_CDML.replace('type="w2"', 'type="%s"' % current_type),
		)
		result = session.set_bond_type(_request(session.revision, requested_type))

		assert result.changed and 'type="%s"' % expected_type in result.snapshot.cdml


#============================================
@pytest.mark.parametrize(
	"requested_type", ("q", "l", "r", "", "nn", "unknown"),
)
def test_bond_type_edit_rejects_nonordinary_requested_types_atomically(requested_type: str) -> None:
	"""Only one exact ordinary requested character can cross the edit boundary."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		session.set_bond_type(_request(before.revision, requested_type))

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize("current_type", ("q2", "l2", "r2", "n", "z1"))
def test_bond_type_edit_rejects_unsupported_current_spelling_atomically(current_type: str) -> None:
	"""Malformed and unsupported current spellings are never normalized by this edit."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		_CDML.replace('type="w2"', 'type="%s"' % current_type),
	)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		session.set_bond_type(_request(before.revision, "n"))

	assert session.snapshot() == before


#============================================
@pytest.mark.parametrize(
	"cdml_text, molecule_id, bond_id",
	(
		(_CDML, "missing_molecule", "b1"),
		(
			_CDML.replace(
				'<v:opaque id="x1"/>',
				'<fragment><molecule id="m_nested"/></fragment>',
			),
			"m_nested", "b1",
		),
		(
			_CDML.replace('<v:opaque id="x1"/>', '<v:molecule id="m_foreign"/>'),
			"m_foreign", "b1",
		),
		(
			_CDML.replace('<v:opaque id="x1"/>', '<arrow id="m_wrong"><point x="0cm" y="0cm"/></arrow>'),
			"m_wrong", "b1",
		),
		(_CDML, "m1", "missing_bond"),
		(
			_CDML.replace(
				'</molecule>\n <v:opaque',
				'<v:opaque><bond id="b_nested" start="a1" end="a2" type="w2"/></v:opaque></molecule>\n <v:opaque',
			),
			"m1", "b_nested",
		),
		(_CDML, "m1", "a1"),
		(_CDML.replace(' end="a2"', ''), "m1", "b1"),
		(_CDML.replace('end="a2"', 'end="a1"'), "m1", "b1"),
		(
			_CDML.replace(
				'<bond id="b1"',
				'<v:atom id="a_hidden" name="N"><v:point x="5cm" y="6cm"/></v:atom><bond id="b1"',
			).replace('end="a2"', 'end="a_hidden"'),
			"m1", "b1",
		),
	),
	ids=(
		"missing-direct-root-molecule", "nested-molecule", "foreign-molecule",
		"wrong-kind-molecule", "missing-bond", "nested-bond", "wrong-kind-bond",
		"missing-endpoint", "self-loop", "foreign-atom-endpoint",
	),
)
def test_bond_type_edit_rejects_noneditable_targets_and_endpoints_atomically(
		cdml_text: str, molecule_id: str, bond_id: str,
		) -> None:
	"""Only direct core molecule, bond, and distinct atom targets may be edited."""
	session = oasa.cdml_document.CDMLDocumentSession.load(cdml_text)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		session.set_bond_type(oasa.cdml_document.CDMLBondTypeEditRequest(
			before.revision, molecule_id, bond_id, "n",
		))

	assert session.snapshot() == before


#============================================
def test_bond_type_edit_checks_revision_before_noop_and_rejects_bad_target_atomically() -> None:
	"""A stale matching request and an independent order attribute cannot mutate state."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.set_bond_type(_request(before.revision + 1, "w"))

	independent = oasa.cdml_document.CDMLDocumentSession.load(
		_CDML.replace('type="w2"', 'type="w2" order="2"'),
	)
	independent_before = independent.snapshot()
	with pytest.raises(oasa.cdml_document.CDMLValidationError):
		independent.set_bond_type(_request(independent_before.revision, "n"))

	assert session.snapshot() == before and independent.snapshot() == independent_before
