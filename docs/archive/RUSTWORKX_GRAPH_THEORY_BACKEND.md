# Rustworkx Graph Theory Backend Plan

## Objective
Integrate `rustworkx` as an internal topology engine for OASA graph operations while preserving OASA as the chemistry and mutation authority.

## Design Philosophy
- OASA remains the source of truth for graph mutation semantics and chemistry meaning.
- Rustworkx is introduced as a mirrored backend plus optional algorithm engine.
- Behavior parity is mandatory before enabling swapped algorithms by default.
- Ring semantics, aromaticity decisions, and chemistry-specific behavior stay in OASA logic.
- This is a major-upgrade track: controlled breaking changes are acceptable when they simplify the graph backend and improve long-term correctness/maintainability.

## Scope
- OASA graph subsystem files:
  - `packages/oasa/oasa/graph/graph_lib.py`
  - `packages/oasa/oasa/graph/digraph_lib.py`
  - `packages/oasa/oasa/graph/vertex_lib.py`
  - `packages/oasa/oasa/graph/edge_lib.py`
  - `packages/oasa/oasa/graph/diedge_lib.py`
  - `packages/oasa/oasa/graph/__init__.py`
- New backend adapter module(s) under `packages/oasa/oasa/graph/`.
- New parity and backend-specific tests for graph algorithms.
- Dependency and docs updates needed to support feature-flagged backend selection.

## Non-goals
- Rewriting chemistry logic (aromaticity, ring semantics policy, bond typing).
- Making rustworkx the mutation authority.
- Removing `Vertex._neighbors` in this plan.
- Mandatory migration of maximum matching to rustworkx.
- Broad BKChem GUI refactors unrelated to OASA graph backend integration.

## Current State Summary
- OASA graph code is functional but legacy and partially self-identified as fragile in cycle/matching areas.
- Core graph mutations currently update OASA-native structures (`vertices`, `edges`, `Vertex._neighbors`).
- Several methods rely on temporary topology changes (`temporarily_disconnect_edge`, bridge stripping) and then reconnect.
- Existing direct tests for graph internals are limited; chemistry tests exercise graph behavior indirectly.
- Current low-hanging performance candidates are read-only algorithms:
  - `get_connected_components`
  - `path_exists`
  - `mark_vertices_with_distance_from`
  - `get_diameter`
  - `find_path_between` (with semantics guardrails)

## Phase -1 Benchmark Results (Completed)

Benchmarked on cholesterol (28 atoms, 31 bonds), N=500 iterations, Python 3.12, rustworkx 0.17.1.

### Timing comparison

| Algorithm | OASA (us) | rustworkx (us) | Speedup | Parity |
| --- | --- | --- | --- | --- |
| `get_smallest_independent_cycles` / `cycle_basis` | 1182.8 | 5.5 | **215x** | MATCH (4 cycles) |
| `get_diameter` / `distance_matrix` | 460.7 | 9.4 | **49x** | MATCH (diameter=15) |
| `is_connected` | 18.5 | 1.4 | **13x** | MATCH (True) |
| `find_path_between` / `dijkstra` | 21.4 | 2.0 | **11x** | path len 9 vs 8 (see note) |
| `get_connected_components` / `connected_components` | 18.2 | 2.1 | **8.7x** | MATCH (1 component) |
| `path_exists` / `has_path` | 16.5 | 2.0 | **8x** | MATCH (True) |
| `mark_vertices_with_distance_from` / `distance_matrix` | 16.3 | 9.5 | **1.7x** | MATCH (max_dist=15) |

### Bonus rustworkx algorithms (no OASA equivalent)

| Algorithm | rustworkx (us) | Notes |
| --- | --- | --- |
| `bridges` | 2.0 | 10 bridges found; replaces OASA per-edge disconnect-check loop |
| `articulation_points` | 1.5 | 9 cut vertices; Tarjan algorithm, no OASA equivalent |
| `max_weight_matching` | 15.3 | 13 pairs; Blossom V algorithm |

### Parity notes
- All results match except `find_path_between`: OASA returned path length 9, rustworkx dijkstra returned length 8. OASA's BFS backtrack does not guarantee shortest path; rustworkx dijkstra does. This is a correctness improvement.
- Cycle count, diameter, component count, distance labels, and reachability all match exactly.

### Feasibility decision
- **GO.** Speedups of 8-215x on the exact algorithms flagged as fragile in OASA justify the integration.
- Cycle perception (215x) and diameter (49x) are the highest-value targets and are the hot paths for aromaticity detection and ring layout.
- `bridges()` and `articulation_points()` are free bonus algorithms that replace OASA's costly per-edge disconnect-check-reconnect pattern with proper Tarjan implementations.

## Dependency and Runtime Policy
- `rustworkx` is already installed (version 0.17.1) from PyPI binary wheels. No Rust toolchain required.
- Use `rustworkx.PyGraph(multigraph=False)` for chemistry graphs (at most one bond between two atoms).
- Pin minimum `rustworkx>=0.17.0` in `pip_requirements.txt`.
- Binary wheels are available for Python 3.9-3.13 on macOS, Linux, and Windows.

## Architecture Boundaries and Ownership

### OASA ownership (unchanged)
- Graph mutation semantics and temporary disconnect semantics.
- Chemistry-specific interpretation layers and ring policy.
- Public graph API shape and return types.

### Rustworkx ownership (new backend role)
- Fast execution for selected read-only topology algorithms.
- Internal node/edge indexing and traversal primitives.

### Adapter ownership
- A dedicated adapter module mediates all rustworkx usage.
- No direct rustworkx calls outside `graph_lib.py` / `digraph_lib.py` plus the adapter.

## Backend Model Specification

### Backend objects
- `Graph._rx`: `rustworkx.PyGraph`
- `Digraph._rx`: `rustworkx.PyDiGraph`

### Identity maps
- `v_to_i: dict[Vertex, int]`
- `i_to_v: dict[int, Vertex]`
- Optional edge identity mapping:
  - `e_to_key: dict[Edge, tuple[int, int, int]]` or similar stable key
  - `key_to_e: dict[tuple[int, int, int], Edge]`
- Index reuse handling (explicit policy):
  - Rustworkx node indices are not treated as stable forever.
  - On node deletion, remove both `v_to_i` and `i_to_v` entries immediately.
  - Never infer identity from positional list order.
  - After complex edit batches, prefer `_rebuild_rx_from_oasa()` to guarantee map/index consistency.

### Payload policy
- Node payload: `Vertex` object.
- Edge payload: lightweight immutable edge key (preferred).
- Rationale:
  - Supports stable lookups back into OASA edge objects.
  - Avoids coupling algorithm assumptions to mutable `Edge` payload behavior.

### Synchronization invariant
- After each committed OASA mutation, `_rx` and maps must represent equivalent active topology.
- For temporary disconnect or bulk/transient operations:
  - Either mirror each transient step in `_rx`, or
  - Mark backend invalid and force `_rebuild_rx_from_oasa()` before any backend read call.

## Phase Plan (Ordered, Dependency-aware)

## Phase -1: Baseline Benchmark and Feasibility Gate -- COMPLETED

See "Phase -1 Benchmark Results" section above. Decision: **GO.**

## Phase 0: Contracts and Test Infrastructure -- COMPLETED

Deliverables:
- [docs/active_plans/GRAPH_SEMANTICS_MATRIX.md](docs/active_plans/GRAPH_SEMANTICS_MATRIX.md) -- 60+ methods documented
- [packages/oasa/tests/graph_test_fixtures.py](packages/oasa/tests/graph_test_fixtures.py) -- 10 molecule fixtures
- [packages/oasa/tests/test_graph_parity.py](packages/oasa/tests/test_graph_parity.py) -- 95 parity tests
- [packages/oasa/tests/benchmark_graph_algorithms.py](packages/oasa/tests/benchmark_graph_algorithms.py) -- benchmark script

## Phase A: Algorithm Swaps -- COMPLETED

Deliverables:
- [packages/oasa/oasa/graph/rx_backend.py](packages/oasa/oasa/graph/rx_backend.py) -- RxBackend adapter (544 lines)
- [packages/oasa/tests/test_rx_backend.py](packages/oasa/tests/test_rx_backend.py) -- 48 adapter unit tests
- 8 algorithms swapped in `graph_lib.py`, legacy preserved as `_*_legacy` methods

### End-to-end speedup (old pure Python -> new adapter path, cholesterol)

| Algorithm | Old (us) | New (us) | Speedup |
| --- | --- | --- | --- |
| cycle_basis | 1182.8 | 7.1 | **167x** |
| diameter | 460.7 | 35.5 | **13x** |
| is_connected | 18.5 | 1.7 | **11x** |
| connected_components | 18.2 | 4.5 | **4x** |
| path_exists | 16.5 | 4.0 | **4x** |
| find_path | 21.4 | 6.7 | **3.2x** |
| distance_from | 16.3 | 10.7 | **1.5x** |

### Bugs fixed during integration
- `find_path_between` start==end edge case (dijkstra omits source when target==source)
- `get_diameter` cache check used truthiness (`if not d`) instead of identity (`if d is not None`), treating diameter=0 as cache miss
- `get_connected_components` changed from generator to list return (all callers compatible)

### Test results
- 143/143 parity + adapter tests pass
- 867/867 OASA tests pass
- 340/341 BKChem tests pass (1 pre-existing GUI failure)

## Phase 0: Baseline And Contracts
### Deliverables
- Backend semantics matrix doc (method-by-method expected behavior for undirected and directed APIs).
- Backend mode config definition (config-file driven; no env-var control).
- Test corpus definition for parity (acyclic, fused rings, bridged bicyclic, odd cycle, directed cases).

### Done checks
- Method semantics matrix reviewed and checked into docs.
- Backend mode config is implemented via config file and documented.
- Corpus fixtures exist and are deterministic.

## Phase A: Mirror Backend + Selective Read-only Swaps
### Deliverables
- New adapter module (for example `packages/oasa/oasa/graph/rx_backend.py`) with:
  - backend init/reset
  - add/remove node/edge mirror ops
  - fast full rebuild function `_rebuild_rx_from_oasa()`
  - conversion helpers index <-> vertex/edge
- Graph and Digraph mutation mirroring integrated:
  - `add_vertex`, `delete_vertex`, `add_edge`, `disconnect`, `disconnect_edge`, reconnect helpers.
- Backend invalidation/rebuild handling around transient topology methods.
- Swapped algorithms, prioritized by measured speedup:
  - `get_smallest_independent_cycles` -> `rustworkx.cycle_basis` (215x, highest value)
  - `get_diameter` -> `rustworkx.distance_matrix` (49x)
  - `is_connected` -> `rustworkx.is_connected` (13x)
  - `find_path_between` -> `rustworkx.dijkstra_shortest_paths` (11x, also fixes correctness)
  - `get_connected_components` -> `rustworkx.connected_components` (8.7x)
  - `path_exists` -> `rustworkx.has_path` (8x)
  - `mark_vertices_with_distance_from` -> `rustworkx.distance_matrix` (1.7x)
- New algorithms with no OASA equivalent (bonus):
  - `is_edge_a_bridge` -> `rustworkx.bridges` (replaces per-edge disconnect-check loop)
  - articulation point detection -> `rustworkx.articulation_points` (Tarjan, 1.5 us)

### Done checks
- With backend mode `legacy`: behavior unchanged from baseline.
- With backend mode `rustworkx`: parity suite green for all swapped methods.
- No direct rustworkx imports outside approved modules.
- Rebuild path exercised by tests for temporary disconnect workflows.

## Phase B: Hardening and Legacy Removal -- COMPLETED

### Code removed
- 8 `_*_legacy` algorithm methods (138 lines)
- `_gen_diameter_progress` generator (16 lines)
- `_get_width_from_vertex` helper (13 lines)
- `_mark_vertices_with_distance_from` private BFS impl (18 lines)
- Dead commented-out multi-thread diameter code (24 lines)
- **Total: 188 lines removed** from `graph_lib.py` (1517 -> 1329 lines, 12.4% reduction)

### Code added (new files)
- `rx_backend.py`: 544 lines (adapter module)
- `test_rx_backend.py`: 646 lines (adapter tests)
- `test_graph_parity.py`: 278 lines (parity tests)
- `graph_test_fixtures.py`: 338 lines (test corpus)
- `benchmark_graph_algorithms.py`: 570 lines (benchmark script)

### Net code change
- Production code: 544 added (adapter) - 188 removed (legacy) = **+356 net lines**
- Test code: +1832 lines (comprehensive test coverage for graph algorithms)

### Profiling results (end-to-end through adapter, cholesterol)

| Algorithm | Old pure Python (us) | New via adapter (us) | Speedup |
| --- | --- | --- | --- |
| cycle_basis | 1182.8 | 7.1 | **167x** |
| diameter | 460.7 | 35.5 | **13x** |
| is_connected | 18.5 | 1.7 | **11x** |
| connected_components | 18.2 | 4.5 | **4x** |
| path_exists | 16.5 | 4.0 | **4x** |
| find_path | 21.4 | 6.7 | **3.2x** |
| distance_from | 16.3 | 10.7 | **1.5x** |

### Decision record
- `find_path_between`: DONE in Phase A. Also a correctness fix (guarantees shortest path).
- Matching migration (Phase C): DEFERRED. `is_edge_a_bridge_fast_and_dangerous` still has 3 callers in `smiles_lib.py`; it delegates to the new `is_edge_a_bridge` (which now uses rustworkx bridges). No urgency to migrate matching separately.
- Directed semantics tests green in both backend modes.

## Phase C (Optional): Matching Migration
### Deliverables
- Conditional migration of `get_maximum_matching` to rustworkx implementation.
- Guardrails for multigraph/parallel-edge constraints and fallback path.

### Done checks
- Matching parity tests pass on coverage corpus and adversarial matching cases.
- Explicit fallback path remains available and tested.
- Decision note confirms retained or rolled back status.

## Parallel Execution Plan

### Concurrency model
- Use real parallel execution for independent planning, test, and benchmark streams.
- Serialize shared graph-core code edits in `graph_lib.py` and `digraph_lib.py`.
- Require each parallel stream to produce a file-backed report before synthesis.

### Stream set (independent first wave)
- Stream S1: Semantics contract matrix
  - Goal: lock method-by-method behavior contracts for `Graph` and `Digraph`.
  - Owns: semantics doc artifact and parity expectation tables.
  - Must not edit: production graph code.
- Stream S2: Corpus and fixtures
  - Goal: build deterministic parity/benchmark corpus (benzene, cholesterol, large natural product, directed cases).
  - Owns: fixture/test data files and fixture loader helpers.
  - Must not edit: backend adapter or graph mutation methods.
- Stream S3: Parity harness scaffolding
  - Goal: create dual-mode harness (`legacy` vs `rustworkx`) and assertion helpers.
  - Owns: test harness modules and test utility files.
  - Must not edit: production algorithm implementations.
- Stream S4: Phase -1 benchmark harness
  - Goal: implement deterministic timing scripts and reporting format.
  - Owns: benchmark scripts + benchmark report template.
  - Must not edit: production graph methods.

### Stream set (second wave after synthesis checkpoint)
- Stream S5: Adapter unit tests
  - Goal: validate map/index consistency, delete/index-reuse handling, and `_rebuild_rx_from_oasa()` correctness.
  - Owns: adapter-focused unit test files.
  - Depends on: adapter interface decisions from synthesis checkpoint.
- Stream S6: Mutation mirroring implementation
  - Goal: implement mirrored updates/invalidation hooks in graph mutation paths.
  - Owns: `graph_lib.py` and `digraph_lib.py` mutation-related sections.
  - Depends on: S1 semantics contracts and S5 test expectations.

### Serialized algorithm swap lane (single owner)
- Swap algorithms one at a time, ordered by value (measured speedup):
  1. `get_smallest_independent_cycles` -> `cycle_basis` (215x, highest value, ring perception hot path)
  2. `get_diameter` -> `distance_matrix` (49x)
  3. `is_connected` -> `is_connected` (13x)
  4. `find_path_between` -> `dijkstra_shortest_paths` (11x, also a correctness fix)
  5. `get_connected_components` -> `connected_components` (8.7x)
  6. `path_exists` -> `has_path` (8x)
  7. `is_edge_a_bridge` -> `bridges` (replaces per-edge disconnect loop with Tarjan)
  8. `mark_vertices_with_distance_from` -> `distance_matrix` (1.7x, lowest priority)
- Entry gate for each swap:
  - prior swapped method parity green in both backend modes.
  - regression gate green for targeted suite.
- Exit gate for each swap:
  - parity harness green on full corpus.
  - no directed semantics regressions.

### Parallel checkpoints and pass/fail criteria
- Checkpoint P1 (after S1-S4):
  - Pass: contracts, corpus, harness, and benchmark artifacts exist and validate.
  - Fail: any missing artifact or nondeterministic benchmark output.
- Checkpoint P2 (after S5+S6):
  - Pass: adapter tests green; mutation mirroring/invalidation tests green.
  - Fail: stale backend state detected after temporary disconnect/reconnect workflows.
- Checkpoint P3 (after serialized swaps):
  - Pass: all enabled swaps satisfy parity + regression gates.
  - Fail: any API behavior mismatch between modes.

## Per-phase Acceptance Gates

### Gate 1: Unit gate
- Adapter tests pass for map consistency, rebuild correctness, and invalidation behavior.

### Gate 2: Integration gate
- Graph API parity tests pass in both modes for swapped methods.

### Gate 3: Regression gate
- Existing OASA/BKChem regression suites pass in legacy and rustworkx modes during transition.
- Targeted graph-heavy suites pass in rustworkx mode.

### Gate 4: Release gate
- For the major-upgrade release, rustworkx mode is the default after parity + profiling sign-off.
- Release note includes breaking-change details and backend behavior constraints.

## Verification Strategy

### Deterministic parity checks (required)
- Compare outputs of legacy vs rustworkx for each swapped method:
  - connected components (as vertex sets)
  - reachability/path existence
  - per-vertex distance labels (`properties_['d']`)
  - diameter value
  - cycle count and cycle sizes from independent cycle basis
  - bridge edge identification
  - path output contract (note: rustworkx dijkstra guarantees shortest path; OASA does not)

### Known semantic differences (acceptable)
- `find_path_between`: OASA BFS backtrack may return non-shortest paths. Rustworkx dijkstra guarantees shortest. This is a correctness improvement, not a regression. Tests should accept equal-or-shorter paths from rustworkx.

### Topology stress corpus (required)
- Tree graphs
- Single cycle and fused cycles
- Bridged bicyclic structures
- Odd cycle cases
- Graphs with temporary disconnect/reconnect sequences
- Directed graph cases covering current OASA semantics

### Safety checks (required)
- Backend rebuild invoked after explicit invalidation points.
- No stale map entries after node/edge deletion.
- Cache invalidation behavior mirrors existing `_flush_cache` semantics.

## Migration and Compatibility Policy
- Controlled breaking changes are allowed as part of the major upgrade.
- Runtime switch between legacy and rustworkx modes remains during stabilization.
- If parity fails for any method, method stays on legacy implementation.
- Legacy algorithm paths are removed after stabilization gates are met and release sign-off is complete.

## Risk Register

| Risk | Impact | Trigger | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Backend staleness after transient topology edits | High correctness risk | Temporary disconnect methods called without rebuild/sync | Enforce invalidation + `_rebuild_rx_from_oasa()` before backend read | Graph backend implementer |
| Directed semantics drift | High behavior risk | Rustworkx call chosen with wrong connectivity notion | Lock method semantics in tests before swap | Graph backend implementer |
| Edge identity mismatch | Medium correctness risk | Parallel or repeated edge scenarios | Use immutable edge keys and map lookups, not implicit position assumptions | Graph backend implementer |
| Hidden chemistry coupling via graph internals | Medium correctness risk | Ring/aromatic code accidentally switched | Keep chemistry/ring policy methods on OASA path in this plan | OASA chemistry maintainer |
| Feature creep into high-risk refactor | Medium schedule risk | Attempt to remove `_neighbors` early | Explicitly out of scope, manager gate for any scope expansion | Plan owner |
| Performance gain below expectation | **Resolved** | Phase -1 benchmark confirmed 8-215x speedups | N/A | N/A |

## Rollout and Release Checklist
- [x] Phase -1 benchmark and feasibility decision completed. GO decision on 2026-02-19.
- [x] Phase 0 deliverables merged. Semantics matrix, fixtures, parity harness, benchmark script.
- [x] Phase A complete. 8 algorithms swapped to rustworkx via RxBackend adapter. 143 parity tests pass, 867 OASA tests pass, 340/341 BKChem tests pass (1 pre-existing GUI failure).
- [x] Parity and regression gates green. All parity checks MATCH across 10 molecules.
- [x] Profiling report: cycle_basis 167x faster, diameter 13x, is_connected 11x end-to-end through adapter.
- [x] Phase B complete. 188 lines of legacy code removed. graph_lib.py reduced 12.4%.
- [x] Decision logged: matching migration deferred (Phase C optional, no urgency).

## Documentation Close-out Requirements
- Update `docs/CHANGELOG.md` with each completed phase summary.
- Maintain this active plan status with gate outcomes per phase.
- If project is paused or completed, archive final version to `docs/archive/` with closure notes.
- Add backend usage and flag details to docs that describe runtime configuration.

## Rustworkx API Mapping Reference

Confirmed mapping from OASA graph methods to `rustworkx` 0.17.1 functions.

### Graph construction
- `rustworkx.PyGraph(multigraph=False)` for undirected chemistry graphs.
- `rustworkx.PyDiGraph()` for directed graphs.
- `g.add_node(data)` returns int node index.
- `g.add_edge(u, v, data)` returns int edge index.
- `g.remove_node(idx)` removes node and all incident edges.
- `g.remove_edge(u, v)` or `g.remove_edge_from_index(idx)`.

### Read-only algorithms

| OASA method | rustworkx function | Notes |
| --- | --- | --- |
| `get_smallest_independent_cycles` | `rustworkx.cycle_basis(g)` | Returns list of node-index lists |
| `get_diameter` | `rustworkx.distance_matrix(g)` + `numpy.max` | No direct diameter function |
| `is_connected` | `rustworkx.is_connected(g)` | Direct bool |
| `find_path_between` | `rustworkx.dijkstra_shortest_paths(g, src, target=tgt)` | Guarantees shortest |
| `get_connected_components` | `rustworkx.connected_components(g)` | Returns list of sets of node indices |
| `path_exists` | `rustworkx.has_path(g, src, tgt)` | Direct bool |
| `mark_vertices_with_distance_from` | `rustworkx.distance_matrix(g)` | Row extraction for single-source |
| `is_edge_a_bridge` | `rustworkx.bridges(g)` | Returns all bridges at once (Tarjan) |
| `contains_cycle` | `len(rustworkx.cycle_basis(g)) > 0` | No direct single function |
| (no equivalent) | `rustworkx.articulation_points(g)` | Cut vertex detection (Tarjan) |
| `get_maximum_matching` | `rustworkx.max_weight_matching(g, max_cardinality=True)` | Blossom V algorithm |

### Key gap: temporary disconnect/reconnect
- No rustworkx equivalent. Must be handled by adapter layer via edge removal/re-addition or backend invalidation and rebuild.

### Key gap: `get_all_cycles` for undirected graphs
- `rustworkx.simple_cycles()` only works on `PyDiGraph`. For undirected graphs, `cycle_basis()` returns the minimum basis (matching `get_smallest_independent_cycles`). Full cycle enumeration would require building from the basis or converting to a directed graph.

## Open Questions and Decisions Needed
1. What exact directed semantics should each Digraph method preserve (weak vs strong where ambiguous)?
2. What minimum molecule/topology corpus is required for sign-off beyond benzene/cholesterol/large-natural-product baseline?
3. Should matching migration be approved only after measured hotspot evidence?
4. What rustworkx version pinning policy should be used for release branches? (Proposed: `>=0.17.0` based on confirmed API.)
