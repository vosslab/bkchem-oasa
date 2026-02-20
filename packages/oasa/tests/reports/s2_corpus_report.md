# S2 corpus report: graph test fixtures

## Assumptions

- OASA molecules are the source of truth; rustworkx graphs are built as mirrors
- Node payloads are OASA Vertex (Atom) objects; edge payloads are OASA Edge (Bond) objects
- `calc_coords=False` is acceptable for fixtures where coordinate generation fails
  (bridged bicyclic and steroid skeleton hit a known `geometry.line_length()` bug in
  `coords_generator.py` line 401)
- Expected values (cycle_count, diameter, etc.) are verified against OASA and rustworkx
  independently in downstream parity tests, not in the fixture module itself
- `oasa.smiles_lib.text_to_mol()` followed by `mol.remove_zero_order_bonds()` is the
  canonical SMILES parsing pipeline

## Decisions

- Each fixture is a plain function (`make_*()`) returning a dict rather than a pytest
  fixture decorator, so the module can be imported from any test file without pytest
  coupling
- `build_rx_from_oasa(mol)` is a standalone helper for ad-hoc conversions outside the
  ten pre-built fixtures
- The disconnected graph is built manually since SMILES always produces connected
  molecules
- `get_all_fixtures()` returns all ten fixtures as a list for parametrized test iteration
- Two molecules (steroid_skeleton, bridged_bicyclic) use `calc_coords=False` to work
  around a pre-existing coords_generator bug; this does not affect graph topology

## Concrete next steps

- Downstream parity tests should import `graph_test_fixtures` and compare OASA graph
  algorithm results against equivalent `rustworkx` function results
- Key parity targets: `is_connected`, `num_connected_components`, cycle detection,
  shortest path / diameter, bridge detection
- When the `rustworkx` graph backend is integrated into OASA, the `build_rx_from_oasa`
  helper can serve as the reference implementation for the conversion layer

## Changed files

- `packages/oasa/tests/graph_test_fixtures.py` -- new fixture module (10 molecules)
- `packages/oasa/tests/validate_fixtures.py` -- temporary validation script (can be deleted)
- `packages/oasa/tests/reports/s2_corpus_report.md` -- this report

## Validation performed

All ten `make_*()` functions were invoked and verified:

| Molecule | Atoms | Bonds | RX nodes | RX edges | Connected | Status |
| --- | --- | --- | --- | --- | --- | --- |
| benzene | 6 | 6 | 6 | 6 | YES | OK |
| bridged_bicyclic | 7 | 8 | 7 | 8 | YES | OK |
| caffeine | 14 | 15 | 14 | 15 | YES | OK |
| cholesterol | 28 | 31 | 28 | 31 | YES | OK |
| cyclopentane | 5 | 5 | 5 | 5 | YES | OK |
| disconnected | 4 | 2 | 4 | 2 | NO | OK |
| hexane | 6 | 5 | 6 | 5 | YES | OK |
| naphthalene | 10 | 11 | 10 | 11 | YES | OK |
| single_atom | 1 | 0 | 1 | 0 | YES | OK |
| steroid_skeleton | 17 | 20 | 17 | 20 | YES | OK |

Additional checks:
- `get_all_fixtures()` returns exactly 10 fixtures
- `build_rx_from_oasa()` works standalone on an ethane molecule
- OASA vertex/edge counts match rustworkx node/edge counts for all fixtures
- OASA `is_connected()` matches `rustworkx.is_connected()` for all fixtures
- Identity maps (`v_to_i`, `i_to_v`) have correct cardinality for all fixtures
