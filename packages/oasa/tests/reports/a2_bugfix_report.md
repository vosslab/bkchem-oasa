# A2 bugfix report

Phase A bug fixes for 3 issues found during Phase 0 review.

## Assumptions

- `Digraph.create_edge()` should match the class's `edge_class = Diedge` declaration,
  consistent with how `Graph.create_edge()` returns `Edge()` matching `edge_class = Edge`.
- Debug print statements in `get_diameter()` are leftover development artifacts, not
  intentional logging.
- Norbornane (C1CC2CCC1C2) is a bridged bicyclic where every edge participates in at
  least one cycle, so it has 0 graph-theoretic bridges. Both OASA and rustworkx confirm
  this.

## Decisions

- Added `create_edge()` override to `Digraph` rather than modifying the parent class to
  use `self.edge_class()`, to keep the fix minimal and avoid changing `Graph` behavior.
- Removed all three print-related lines from `get_diameter()` (the "path" label, the
  loop printing vertices). Kept the `best_path.reverse()` call since it may be used by
  callers who access the path via vertex properties.
- Changed only `has_bridges` in `make_bridged_bicyclic()`. No `bridge_count` key existed
  in that fixture's expected dict, so no additional change was needed.

## Changed files

- [packages/oasa/oasa/graph/digraph_lib.py](packages/oasa/oasa/graph/digraph_lib.py):
  Added `create_edge()` returning `Diedge()`. Removed 3 debug print lines from
  `get_diameter()`.
- [packages/oasa/tests/graph_test_fixtures.py](packages/oasa/tests/graph_test_fixtures.py):
  Changed `has_bridges` from `True` to `False` in `make_bridged_bicyclic()`.
- [docs/CHANGELOG.md](docs/CHANGELOG.md): Documented all three fixes.

## Validation performed

- Digraph import and `create_edge()` type check: returns `Diedge` (PASS)
- Pyflakes lint on `digraph_lib.py`: PASS
- Pyflakes lint on `graph_test_fixtures.py`: PASS (clean, no output)
- Bridge parity tests (`test_graph_parity.py -k bridge`): 17 passed, 1 pre-existing
  failure (cholesterol bridge gap, unrelated to this fix)
- No digraph-specific test files exist yet (0 collected with `-k digraph`)

## Concrete next steps

- Consider adding unit tests for `Digraph.create_edge()` and `get_diameter()` to prevent
  regressions.
- The cholesterol bridge parity test failure (OASA=12, rx=10, gap=2 exceeds tolerance of
  1) is pre-existing and unrelated to these fixes. It should be investigated separately.

## Blocking issues

None.
