"""Behavior tests for revision-bound portable molecule render batches."""

import pytest

from oasa import cdml_document
from oasa import render_ops


#============================================
def test_public_render_normalization_returns_offset_portable_primitives() -> None:
	"""Compatibility render operations cross the public boundary as plain facts."""
	operations = (render_ops.LineOp((12.0, 4.0), (20.0, 4.0), 2.0, color="#123456"),)
	primitives = cdml_document.normalize_render_operations(operations, (10.0, 0.0))

	assert primitives[0].kind == "line" and primitives[0].points == ((2.0, 4.0), (10.0, 4.0))


#============================================
@pytest.mark.parametrize("offset", (
	(float("inf"), 0.0), (True, 0.0), (0.0,), [0.0, 0.0],
))
def test_public_render_normalization_rejects_invalid_offset(offset: object) -> None:
	"""Invalid transient coordinates fail through the typed backend boundary."""
	with pytest.raises(cdml_document.CDMLMoleculeRenderObservationError):
		cdml_document.normalize_render_operations((), offset)


#============================================
@pytest.mark.parametrize("operation", (
	render_ops.LineOp((0.0,), (1.0, 1.0), 1.0),
	render_ops.PathOp((("M", (0.0,)),), None),
	object(),
))
def test_public_render_normalization_rejects_malformed_or_unknown_operation(
		operation: object,
		) -> None:
	"""The public boundary reports one typed error before returning any batch."""
	with pytest.raises(cdml_document.CDMLMoleculeRenderObservationError):
		cdml_document.normalize_render_operations((operation,))


#============================================
def test_render_observation_keeps_idless_records_addressed_by_source_position() -> None:
	"""Legacy ID-less atom and bond batches retain their direct child positions."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='b' name='O'><point x='1cm' y='0cm'/></atom>"
		"<bond start='a' end='b' type='n1'/><atom name='N'><point x='2cm' y='0cm'/></atom></molecule></cdml>", validation="compat",
	)
	batches = document.molecule_render_observation(0).batches
	assert any(batch.kind == "bond" and batch.source_position == 3 for batch in batches)
	assert not next(batch for batch in batches if batch.source_position == 4).actionable


#============================================
def test_render_observation_does_not_shift_past_an_invalid_middle_record() -> None:
	"""A preservation-only middle atom cannot misassociate a later accepted atom."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='bad' name='Xx'><point x='1cm' y='0cm'/></atom>"
		"<atom id='b' name='O'><point x='2cm' y='0cm'/></atom>"
		"<bond start='a' end='b' type='n1'/></molecule></cdml>", validation="compat",
	)
	batches = document.molecule_render_observation(0).batches
	accepted_atom = next(batch for batch in batches if batch.kind == "atom" and batch.source_position == 3)
	assert accepted_atom.operations[-1].text_runs[0][0] == "O"


#============================================
def test_render_observation_ignores_foreign_and_nested_atom_lookalikes() -> None:
	"""Direct source positions keep a real atom distinct from XML lookalikes."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml xmlns:foreign='urn:foreign'><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/><foreign:atom id='nested' name='N'/></atom>"
		"<foreign:atom id='outer' name='Cl'/><atom id='b' name='O'><point x='2cm' y='0cm'/></atom>"
		"<bond start='a' end='b' type='n1'/></molecule></cdml>", validation="compat",
	)
	batch = next(batch for batch in document.molecule_render_observation(0).batches if batch.kind == "atom" and batch.source_position == 3)
	assert batch.operations[-1].text_runs[0][0] == "O"


#============================================
def test_render_observation_leaves_ambiguous_duplicate_atom_bond_unpainted() -> None:
	"""Duplicate atom IDs cannot select an arbitrary bond endpoint for painting."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='a' name='N'><point x='1cm' y='0cm'/></atom>"
		"<atom id='b' name='O'><point x='2cm' y='0cm'/></atom>"
		"<bond start='a' end='b' type='n1'/></molecule></cdml>", validation="compat",
	)
	assert all(batch.kind != "bond" for batch in document.molecule_render_observation(0).batches)


#============================================
def test_render_observation_distinguishes_default_and_authored_black_colors() -> None:
	"""Theme-neutral defaults stay distinct from an authored black bond color."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C' show='yes'><point x='0cm' y='0cm'/></atom>"
		"<atom id='b' name='O'><point x='1cm' y='0cm'/></atom>"
		"<bond id='default' start='a' end='b' type='n1'/><bond id='black' start='a' end='b' type='n1' color='#000000'/></molecule></cdml>", validation="compat",
	)
	batches = document.molecule_render_observation(0).batches
	default = next(batch.operations[0] for batch in batches if batch.identifier == "default")
	authored = next(batch.operations[0] for batch in batches if batch.identifier == "black")
	assert (default.stroke, default.stroke_role) == (None, "foreground")
	assert (authored.stroke, authored.stroke_role) == ("#000000", None)


#============================================
def test_render_observation_never_makes_duplicate_bond_ids_actionable() -> None:
	"""Distinct direct bonds with one repeated ID remain visible but inert."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='b' name='O'><point x='1cm' y='0cm'/></atom><atom id='c' name='N'><point x='2cm' y='0cm'/></atom>"
		"<bond id='same' start='a' end='b' type='n1'/><bond id='same' start='b' end='c' type='n1'/></molecule></cdml>", validation="compat",
	)
	bonds = [batch for batch in document.molecule_render_observation(0).batches if batch.kind == "bond"]
	assert any(batch.source_position == 4 for batch in bonds)
	assert all(not batch.actionable for batch in bonds)


#============================================
def test_render_observation_rejects_stale_query_without_mutation() -> None:
	"""A stale render query fails before it can prepare a new observation."""
	session = cdml_document.CDMLDocumentSession.load("<cdml/>")
	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.molecule_render_observation(cdml_document.CDMLMoleculeRenderObservationQuery(1))
	assert session.revision == 0
