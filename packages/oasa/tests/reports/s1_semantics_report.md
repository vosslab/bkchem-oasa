# S1 Semantics Contract Matrix Report

Stream S1 deliverable for the rustworkx graph backend integration (Phase 0).

## Assumptions

- All public methods in `graph_lib.py`, `digraph_lib.py`, `vertex_lib.py`, `edge_lib.py`, and `diedge_lib.py` are in scope.
- Private methods prefixed with `_` are documented when they are called by public methods or have significant side effects.
- Module-level free functions in `graph_lib.py` (e.g., `is_ring_end_vertex`, `get_path_down_to`) are out of scope for the matrix but noted where relevant.
- The rustworkx API mapping is based on version 0.17.1 as confirmed in the plan document.
- "Flushes cache" means the method directly calls `self._flush_cache()`, not transitively through other methods.

## Decisions

- Grouped methods into 14 categories: Mutation, Temporary disconnect, Connectivity/boolean, Components/subgraphs, Paths/distance, Cycles, Matching, Subgraph conversion, Factory, Copy, Cache, I/O, Private helpers, and Digraph-specific.
- Documented `properties_` side effects as a dedicated section because these are the primary coupling point between OASA algorithms and the rustworkx adapter layer. Any rustworkx swap must either replicate or avoid these side effects.
- Flagged 7 known bugs/issues found during review.
- Documented thread safety concerns that affect multi-threaded usage (currently unused but relevant for future work).

## Concrete next steps

1. Fix `Digraph.create_edge()` to return `Diedge()` instead of `Edge()` (bug found during review).
2. Remove debug `print()` statements from `Digraph.get_diameter()`.
3. Stream S2 (corpus/fixtures) can use this matrix to identify which methods need parity testing.
4. Stream S3 (parity harness) should test `properties_['d']` side effects explicitly for methods that use distance marking.
5. The adapter layer must handle `_flush_cache()` semantics -- every method that flushes the OASA cache must also invalidate the rustworkx backend mirror.
6. The `path_exists` and `find_path_between` methods are high-value swap candidates because the rustworkx versions avoid `properties_['d']` side effects entirely.

## Changed files

| File | Change type |
| --- | --- |
| `docs/active_plans/GRAPH_SEMANTICS_MATRIX.md` | Created (main deliverable) |
| `packages/oasa/tests/reports/s1_semantics_report.md` | Created (this report) |

No production code was modified.

## Validation performed

- Read all 5 source files completely (graph_lib.py: 1437 lines, digraph_lib.py: 149 lines, vertex_lib.py: 135 lines, edge_lib.py: 83 lines, diedge_lib.py: 59 lines).
- Cross-referenced every public method against the rustworkx API mapping in the plan document.
- Verified cache flush calls by searching for `_flush_cache` in graph_lib.py.
- Verified `properties_` writes by searching for `properties_[` assignments across all files.
- Confirmed Digraph override behavior by comparing `add_edge` signatures (one-way vs two-way neighbor addition).
- Confirmed `Diedge` lacks `disconnected` attribute, meaning temporary disconnect methods are incompatible with Digraph.
- No automated tests were run (this is a documentation-only deliverable with no code changes).

Validation status: PASS.
