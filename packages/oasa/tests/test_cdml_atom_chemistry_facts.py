"""Behavior tests for revision-bound complete-graph atom chemistry facts."""

import pytest

from oasa import cdml_document


#============================================
def test_atom_chemistry_facts_use_the_complete_direct_cc_graph() -> None:
	"""A C-C bond consumes one valency and supplies three implicit H per carbon."""
	session = cdml_document.CDMLDocumentSession.load(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='b' name='C'><point x='1cm' y='0cm'/></atom>"
		"<bond id='e' start='a' end='b' type='n1'/></molecule></cdml>",
	)
	facts = session.atom_chemistry_facts(
		cdml_document.CDMLAtomChemistryFactsQuery(session.revision),
	)
	assert {(record.occupied_valency, record.free_valency, record.hydrogen_count)
		for record in facts.records} == {(1, 3, 3)}
	assert all(record.disposition == "usable" for record in facts.records)


#============================================
def test_atom_chemistry_facts_use_connected_graph_for_oxidation() -> None:
	"""C-C-O receives the existing OASA electronegativity-derived values."""
	session = cdml_document.CDMLDocumentSession.load(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<atom id='b' name='C'><point x='1cm' y='0cm'/></atom>"
		"<atom id='o' name='O'><point x='2cm' y='0cm'/></atom>"
		"<bond id='e1' start='a' end='b' type='n1'/><bond id='e2' start='b' end='o' type='n1'/>"
		"</molecule></cdml>",
	)
	facts = session.atom_chemistry_facts(
		cdml_document.CDMLAtomChemistryFactsQuery(session.revision),
	)
	assert {record.atom_id: record.oxidation_number for record in facts.records} == {
		"a": -3, "b": -1, "o": -2,
	}


#============================================
def test_atom_chemistry_facts_keep_malformed_direct_graph_display_only() -> None:
	"""Malformed endpoints never produce chemistry from a guessed association."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml><molecule id='m'><atom id='a' name='C'><point x='0cm' y='0cm'/></atom>"
		"<bond id='e' start='a' end='missing' type='n1'/></molecule></cdml>",
		validation="compat",
	)
	facts = document.atom_chemistry_facts(0)
	assert facts.records[0].disposition == "display-only"
	assert facts.records[0].free_valency is None


#============================================
def test_atom_chemistry_facts_keep_foreign_root_association_display_only() -> None:
	"""A foreign direct-root lookalike cannot shift a later core association."""
	document = cdml_document.CDMLDocument.parse(
		"<cdml xmlns:foreign='urn:foreign'><foreign:molecule id='foreign'>"
		"<foreign:atom id='a' name='C'/></foreign:molecule><molecule id='m'>"
		"<atom id='c' name='C'><point x='0cm' y='0cm'/></atom></molecule></cdml>",
		validation="compat",
	)
	facts = document.atom_chemistry_facts(0)
	assert {(record.molecule_id, record.disposition) for record in facts.records} == {
		("foreign", "display-only"), ("m", "usable"),
	}


#============================================
def test_atom_chemistry_facts_reject_stale_without_changing_history() -> None:
	"""A stale read-only query leaves the authoritative snapshot untouched."""
	session = cdml_document.CDMLDocumentSession.load("<cdml/>")
	before = session.snapshot()
	with pytest.raises(cdml_document.CDMLRevisionConflictError):
		session.atom_chemistry_facts(cdml_document.CDMLAtomChemistryFactsQuery(1))
	assert session.snapshot() == before
