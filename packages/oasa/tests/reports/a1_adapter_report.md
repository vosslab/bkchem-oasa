# A1 adapter report: RxBackend

## Assumptions

- rustworkx 0.17.1 is the target version; all API calls tested against it.
- `Edge` objects use `get_vertices()` (not a `.vertices` property) at the graph layer; subclasses like `Bond` may add a property alias.
- OASA `Graph.edges` contains only active (non-disconnected) edges; `disconnected_edges` is a separate set.
- `find_path_between` returns path in end-to-start order, matching OASA convention.
- `distance_from` must write `properties_['d']` as a side effect per the semantics matrix contract.

## Decisions

- **rustworkx.bridges() bug workaround**: rustworkx 0.17.1 `bridges()` misses edges connected to degree-1 nodes at the DFS root (node index 0). The adapter supplements the result by checking all degree-1 nodes and adding their single edge to the bridge set.
- **dijkstra_shortest_paths source inclusion**: rustworkx `dijkstra_shortest_paths` does not include the source node in its result dict when it has distance 0. The adapter injects `{source: [source]}` into the result.
- **Node/edge payload**: OASA Vertex and Edge objects are stored as payload data in the PyGraph nodes and edges, enabling direct identity mapping.
- **Lazy sync via dirty flag**: The adapter only rebuilds when `_dirty=True`, checked before every algorithm call via `ensure_synced()`. Mutations set `_dirty=True`.
- **dont_go_through support**: `find_path_between` builds a temporary filtered PyGraph excluding specified vertices/edges rather than post-filtering, ensuring correctness for arbitrary exclusion sets.
- **numpy dependency**: `get_diameter` uses `rustworkx.distance_matrix()` which returns a numpy ndarray. numpy is already a project dependency.

## Changed files

- `packages/oasa/oasa/graph/rx_backend.py` -- new file, RxBackend adapter class
- `packages/oasa/tests/test_rx_backend.py` -- new file, 48 unit tests

## Concrete next steps

1. Wire `RxBackend` into `Graph.__init__` so it auto-creates a backend instance.
2. Hook `Graph._flush_cache` to call `backend.mark_dirty()`.
3. Swap individual Graph algorithm methods to delegate to `self._rx_backend` (start with `is_connected`, `get_connected_components`).
4. Add toggle mechanism (class variable or env flag) to switch between OASA-native and rustworkx algorithms for A/B correctness testing.
5. Consider caching `distance_matrix` results in the backend to avoid recomputation when `get_diameter` and `distance_from` are called in sequence.

## Validation performed

- 48/48 pytest tests pass (`packages/oasa/tests/test_rx_backend.py`).
- pyflakes lint clean on both `rx_backend.py` and `test_rx_backend.py`.
- Tests cover: init, mirror ops (add/remove node/edge), rebuild, lazy sync, all 9 algorithm delegates, invalidation, index conversion helpers.
- Algorithm tests use molecule fixtures (benzene, hexane, naphthalene, disconnected, single atom) from `graph_test_fixtures.py`.
