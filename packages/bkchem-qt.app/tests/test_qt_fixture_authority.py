"""Regression coverage for shared Qt fixture authority reset."""

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document
import bkchem_qt.models.document_session
import oasa.cdml_document

# local test modules
import tests.conftest


#============================================
def _draw_pair_request(
		session: bkchem_qt.models.document_session.DocumentSession, element: str,
		) -> bkchem_qt.models.document_session.PersistentOperationRequest:
	"""Return one plain backend Draw request for a fresh bonded pair."""
	return bkchem_qt.models.document_session.PersistentOperationRequest(
		"draw.structure", "Draw bonded pair",
		(
			("expected_revision", session.backend_snapshot.revision),
			("kind", "create-bonded-pair"),
			("source_position", (10.0, 20.0)),
			("target_position", (40.0, 20.0)),
			("element", element),
			("bond_type", "n"),
			("bond_order", 1),
			("simple_double", False),
		),
	)


#============================================
def _draw_result_ids(result: oasa.cdml_document.CDMLStructuralEditResult) -> frozenset[str]:
	"""Return every durable identifier created by one accepted Draw result."""
	identifiers = set(result.created_atom_ids + result.created_bond_ids)
	if result.created_molecule_id is not None:
		identifiers.add(result.created_molecule_id)
	return frozenset(identifiers)


#============================================
def _projected_draw_ids(document: bkchem_qt.models.document.Document) -> frozenset[str]:
	"""Return the Draw durable identifiers resolved by one live projection."""
	identifiers = set()
	for molecule in document.molecules:
		identifiers.add(molecule.mol_id)
		identifiers.update(atom.atom_id for atom in molecule.atoms if atom.atom_id)
		identifiers.update(bond.bond_id for bond in molecule.bonds if bond.bond_id)
	return frozenset(identifiers)


#============================================
def _projected_atom_symbols(document: bkchem_qt.models.document.Document) -> frozenset[str]:
	"""Return the element symbols visible through one live Draw projection."""
	return frozenset(
		atom.symbol for molecule in document.molecules for atom in molecule.atoms
	)


#============================================
def test_fixture_normalization_recreates_the_authoritative_blank_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A reset retires accepted state before the next backend Draw operation."""
	first_session = main_window._active_session
	first_outcome = first_session.submit_persistent_operation(
		_draw_pair_request(first_session, "N"),
	)
	assert first_outcome.status == "accepted" and first_outcome.structural_result is not None

	tests.conftest._normalize_main_window(main_window)
	second_session = main_window._active_session
	try:
		second_outcome = second_session.submit_persistent_operation(
			_draw_pair_request(second_session, "C"),
		)
		second_result = second_outcome.structural_result
		assert (
			second_session is not first_session
			and second_outcome.status == "accepted"
			and second_result is not None
			and second_session.backend_projection_synchronized
			and _projected_draw_ids(second_session.document) == _draw_result_ids(second_result)
		)
		assert (
			first_outcome.structural_result.commit.cdml != second_result.commit.cdml
			and "N" not in _projected_atom_symbols(second_session.document)
		)
	finally:
		tests.conftest._normalize_main_window(main_window)
