"""Behavioral tests for authoritative CDML molecular summary queries."""

# Standard Library
import dataclasses

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_document
import oasa.cdml_molecule_summary


_TWO_MOLECULE_CDML = """\
<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" xmlns:v="urn:vendor" version="26.07">
 <molecule id="methane" name="Methane">
  <atom id="c1" name="C"><point x="0cm" y="0cm" /></atom>
  <v:atom id="hidden" name="O"><v:point x="9cm" y="9cm" /></v:atom>
 </molecule>
 <molecule id="water" name="Water">
  <atom id="o1" name="O"><point x="2cm" y="0cm" /></atom>
 </molecule>
</cdml>
"""


#============================================
def _query(revision: object, molecule_ids: object) -> object:
	"""Build a query, including deliberately invalid runtime shapes."""
	return oasa.cdml_molecule_summary.CDMLMoleculeSummaryQuery(
		revision, molecule_ids,
	)


#============================================
def test_summary_includes_implicit_hydrogens_and_exact_backend_mass() -> None:
	"""A projected carbon becomes backend-authoritative methane chemistry."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_TWO_MOLECULE_CDML)
	before = session.snapshot()

	observation = session.molecule_summary(_query(0, ("methane",)))
	record = observation.records[0]

	assert (
		observation.revision == 0
		and record.molecule_id == "methane"
		and record.name == "Methane"
		and record.atom_count == 1
		and record.bond_count == 0
		and record.chemistry.formula == "CH4"
		and record.chemistry.element_counts == (("C", 1), ("H", 4))
		and record.chemistry.molecular_weight == pytest.approx(16.0423)
		and record.chemistry.monoisotopic_mass == pytest.approx(16.03130012)
		and sum(percent for _symbol, percent in record.chemistry.mass_percentages)
		== pytest.approx(100.0)
		and observation.aggregate == record.chemistry
		and session.snapshot() == before
	)


#============================================
def test_batch_summary_preserves_request_order_and_combines_formulas() -> None:
	"""Multiple selections share one revision and one aggregate composition."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_TWO_MOLECULE_CDML)

	observation = session.molecule_summary(_query(0, ("water", "methane")))

	assert (
		tuple(record.molecule_id for record in observation.records)
		== ("water", "methane")
		and tuple(record.chemistry.formula for record in observation.records)
		== ("H2O", "CH4")
		and observation.aggregate.formula == "CH6O"
		and observation.aggregate.element_counts == (("C", 1), ("H", 6), ("O", 1))
		and observation.aggregate.molecular_weight == pytest.approx(34.0575)
		and observation.aggregate.monoisotopic_mass == pytest.approx(34.04186480)
	)


#============================================
@pytest.mark.parametrize("molecule_ids", [(), ["methane"], ("methane", "methane"), ("",)])
def test_summary_rejects_ambiguous_batch_shapes(molecule_ids: object) -> None:
	"""The query boundary accepts only a nonempty tuple of unique durable IDs."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_TWO_MOLECULE_CDML)

	with pytest.raises(oasa.cdml_molecule_summary.CDMLMoleculeSummaryError):
		session.molecule_summary(_query(0, molecule_ids))


#============================================
def test_stale_or_unsupported_summary_fails_without_session_changes() -> None:
	"""Failed observations cannot change authoritative content or dirty state."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_TWO_MOLECULE_CDML)
	before = session.snapshot()

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		session.molecule_summary(_query(1, ("methane",)))
	with pytest.raises(oasa.cdml_molecule_summary.CDMLMoleculeSummaryError):
		session.molecule_summary(_query(0, ("methane", "missing")))

	assert session.snapshot() == before


#============================================
def test_summary_result_is_deeply_immutable_plain_data() -> None:
	"""Frontends receive scalar tuples rather than mutable OASA graph objects."""
	session = oasa.cdml_document.CDMLDocumentSession.load(_TWO_MOLECULE_CDML)
	observation = session.molecule_summary(_query(0, ("methane",)))

	with pytest.raises(dataclasses.FrozenInstanceError):
		observation.records[0].name = "Changed"
	assert observation.records[0].chemistry.element_counts == (("C", 1), ("H", 4))
