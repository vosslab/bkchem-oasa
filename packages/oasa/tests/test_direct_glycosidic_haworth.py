"""Behavior tests for complete direct-glycosidic Haworth preparation."""

# Standard Library
import math

# Third Party
import pytest

# Local modules
import oasa.cdml
import oasa.cdml_document
import oasa.cdml_writer
import oasa.haworth.direct_glycosidic
import oasa.haworth.multiring_layout
import oasa.haworth.verified_sucrose
import oasa.smiles_lib


GLUCOSE_GLUCOSE_SMILES = "OCC1OC(OC2OC(CO)C(O)C(O)C2O)C(O)C(O)C1O"


#============================================
def _ring_style_facts(molecule: object) -> tuple[tuple[str, str | None], ...]:
	"""Return durable Haworth style facts for every styled bond."""
	facts = tuple(sorted(
		(bond.type, bond.properties_.get("haworth_position"))
		for bond in molecule.edges if "haworth_position" in bond.properties_
	))
	return facts


#============================================
def _molecule_state(molecule: object) -> tuple:
	"""Capture every mutable coordinate and durable bond value for atomicity checks."""
	state = (
		tuple((atom.x, atom.y) for atom in molecule.vertices),
		tuple(
			(
				tuple(molecule.vertices.index(atom) for atom in bond.vertices),
				bond.type,
				tuple(sorted(bond.properties_.items())),
			)
			for bond in molecule.edges
		),
	)
	return state


#============================================
def test_complete_six_six_preparation_has_clear_geometry_and_haworth_semantics() -> None:
	"""A generic direct 6+6 source becomes one complete durable depiction."""
	molecule = oasa.haworth.direct_glycosidic.prepare_direct_glycosidic_haworth(
		GLUCOSE_GLUCOSE_SMILES,
	)
	rings = molecule.get_smallest_independent_cycles()
	styles = _ring_style_facts(molecule)
	assert all(math.isfinite(atom.x) and math.isfinite(atom.y) for atom in molecule.vertices)
	assert sorted(len(ring) for ring in rings) == [6, 6]
	assert {("q", "front"), ("w", "front"), ("n", "back")} <= set(styles)


#============================================
def test_generic_six_five_source_and_authoritative_round_trip_preserve_haworth_records() -> None:
	"""A 6+5 input commits and reloads without losing complete depiction facts."""
	smiles = oasa.haworth.verified_sucrose.IDENTITY.isomeric_smiles.decode("ascii")
	molecule = oasa.haworth.direct_glycosidic.prepare_direct_glycosidic_haworth(smiles)
	before = _ring_style_facts(molecule)
	proposal = oasa.cdml_writer.molecules_to_insertion_proposal([molecule], token_stem="glyco")
	session = oasa.cdml_document.CDMLDocumentSession.load("<cdml />")
	accepted = session.insert_molecules(oasa.cdml_document.CDMLMoleculeInsertionRequest(
		expected_revision=session.revision, proposal_cdml=proposal,
	))
	oasa.cdml_document.CDMLDocument.parse(accepted.cdml, validation="strict")
	reloaded = next(oasa.cdml.read_cdml(accepted.cdml))
	assert sorted(len(ring) for ring in reloaded.get_smallest_independent_cycles()) == [5, 6]
	assert _ring_style_facts(reloaded) == before


#============================================
def test_stale_or_invalid_complete_geometry_rejection_does_not_partially_mutate() -> None:
	"""Plan identity and finite-coordinate failures leave the detached graph intact."""
	molecule = oasa.smiles_lib.text_to_mol(GLUCOSE_GLUCOSE_SMILES, calc_coords=1)
	plan = oasa.haworth.multiring_layout.plan_direct_glycosidic_disaccharide(molecule)
	molecule.vertices.reverse()
	before_stale = _molecule_state(molecule)
	with pytest.raises(ValueError, match="does not match"):
		oasa.haworth.direct_glycosidic.apply_direct_glycosidic_haworth(molecule, plan)
	assert _molecule_state(molecule) == before_stale
	molecule.vertices.reverse()
	molecule.vertices[0].x = float("nan")
	before_nonfinite = _molecule_state(molecule)
	with pytest.raises(ValueError, match="finite RDKit"):
		oasa.haworth.direct_glycosidic.apply_direct_glycosidic_haworth(molecule, plan)
	assert _molecule_state(molecule) == before_nonfinite


#============================================
@pytest.mark.parametrize("smiles", ("", "CCO"))
def test_invalid_input_is_a_typed_atomic_rejection(smiles: str) -> None:
	"""Malformed or unsupported public inputs receive one typed backend failure."""
	with pytest.raises(ValueError, match="Direct disaccharide Haworth"):
		oasa.haworth.direct_glycosidic.prepare_direct_glycosidic_haworth(smiles)
