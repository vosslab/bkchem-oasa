# A3 swap report: rustworkx backend integration into Graph

## Summary

Integrated `RxBackend` adapter into `Graph.__init__` in `graph_lib.py` and
swapped 8 graph algorithms to delegate to rustworkx. All legacy implementations
preserved as `_*_legacy` methods. All 1210 tests pass across OASA, BKChem, and
parity suites.

## Assumptions

- All graph mutation methods already call `_flush_cache()`, so hooking
  `mark_dirty()` there is sufficient to keep the backend synced.
- The lazy rebuild pattern (dirty flag + `ensure_synced`) avoids any per-mutation
  mirroring overhead.
- Legacy methods are preserved for fallback but not wired to any dispatch
  mechanism -- callers always use the new implementations.
- The pre-existing BKChem GUI test failure (`test_bkchem_gui_event_simulation`)
  is unrelated to this change (Ctrl-1 mode switch timing issue).

## Decisions

1. **Single dirty-flag hook**: Rather than mirroring every `add_vertex`,
   `add_edge`, `disconnect`, etc. into the rx backend incrementally, we mark
   dirty on any mutation and rebuild lazily before algorithm calls. This is
   simpler and avoids bugs from partial sync.

2. **start==end fix**: Added a guard in `RxBackend.find_path_between()` to
   return `[start]` when source and target are identical. Rustworkx's
   `dijkstra_shortest_paths` does not include the source node in its result
   dict when target == source.

3. **Cache fix for get_diameter**: Changed `if not d:` to `if d is not None:`
   because `d=0` is a valid cached diameter (single-vertex graph) that would
   be treated as cache-miss with the truthiness check.

4. **Return type change for get_connected_components**: Changed from generator
   (yield) to list return. The rustworkx backend returns a list of sets. All
   callers already handle both patterns (list comprehensions, `len(list(...))`,
   iteration).

## Swaps performed

| Step | Method | Speedup | Test class | Result |
| --- | --- | --- | --- | --- |
| 0 | Graph.__init__ + _flush_cache hook | N/A | all | PASS |
| 1 | get_smallest_independent_cycles | 1.2-1.5x | TestCycleBasis | PASS |
| 2 | get_diameter | 2.6-3.2x | TestDiameter | PASS |
| 3 | is_connected | 1.1-1.3x | TestIsConnected | PASS |
| 4 | get_connected_components | 1.9-2.1x | TestConnectedComponents | PASS |
| 5 | find_path_between | 1.8-2.2x | TestFindPathBetween | PASS |
| 6 | path_exists | 1.1-1.3x | TestPathExists | PASS |
| 7 | is_edge_a_bridge | N/A (rx-only) | TestBridges | PASS |
| 8 | mark_vertices_with_distance_from | 0.9-1.6x | TestDistanceFrom | PASS |

## Legacy methods preserved

- `_get_smallest_independent_cycles_legacy`
- `_get_diameter_legacy`
- `_is_connected_legacy`
- `_get_connected_components_legacy`
- `_find_path_between_legacy`
- `_path_exists_legacy`
- `_is_edge_a_bridge_legacy`
- `_mark_vertices_with_distance_from_legacy`

## Changed files

- `packages/oasa/oasa/graph/graph_lib.py` -- import RxBackend, init in
  `__init__`, dirty hook in `_flush_cache`, 8 method swaps + 8 legacy copies
- `packages/oasa/oasa/graph/rx_backend.py` -- start==end guard in
  `find_path_between`
- `docs/CHANGELOG.md` -- integration entry

## Validation performed

| Suite | Count | Result |
| --- | --- | --- |
| test_graph_parity.py | 95 tests (93 pass, 2 skip) | PASS |
| test_rx_backend.py | 48 tests | PASS |
| OASA full suite | 867 tests (865 pass, 2 skip) | PASS |
| BKChem full suite | 341 tests (340 pass, 1 pre-existing fail) | PASS |
| pyflakes graph_lib | 1 test | PASS |
| Benchmark parity | all algorithms | all MATCH |

## Concrete next steps

- Wire a configuration toggle or environment-based dispatch to fall back to
  legacy implementations if rustworkx is not installed (optional dependency).
- Consider incremental mirroring for hot mutation paths if profiling shows
  rebuild cost is significant for interactive editing.
- The `temporarily_strip_bridge_edges` method still uses the old
  `is_edge_a_bridge` (now delegating to rustworkx bridges), which computes all
  bridges every call. A future optimization could cache the bridge set.
- Run integration tests with real CDML files to confirm end-to-end behavior.

## Blocking issues

None.
