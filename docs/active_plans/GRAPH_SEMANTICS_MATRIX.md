# Graph Semantics Matrix

Method-by-method behavior contract for the OASA graph subsystem.
Covers `Graph` (undirected), `Digraph` (directed), `Vertex`, and `Edge`/`Diedge` classes.
Reference for rustworkx backend integration (Phase 0 deliverable).

Source files:
- [packages/oasa/oasa/graph/graph_lib.py](../../packages/oasa/oasa/graph/graph_lib.py)
- [packages/oasa/oasa/graph/digraph_lib.py](../../packages/oasa/oasa/graph/digraph_lib.py)
- [packages/oasa/oasa/graph/vertex_lib.py](../../packages/oasa/oasa/graph/vertex_lib.py)
- [packages/oasa/oasa/graph/edge_lib.py](../../packages/oasa/oasa/graph/edge_lib.py)
- [packages/oasa/oasa/graph/diedge_lib.py](../../packages/oasa/oasa/graph/diedge_lib.py)

---

## Notation key

- **Flushes cache**: method calls `self._flush_cache()` (clears `self._cache` dict).
- **Modifies properties_**: method writes to `Vertex.properties_` or `Edge.properties_`.
- **Uses temp disconnect**: method calls `temporarily_disconnect_edge` / `reconnect_temporarily_disconnected_edge(s)`.
- **Return type (OASA)**: returns OASA-specific objects (Vertex, Edge, Graph).
- **Return type (pure)**: returns plain Python types (int, bool, set, list, None).
- **rx equiv**: confirmed rustworkx 0.17.1 mapping from the plan.

---

## 1. Vertex class (`vertex_lib.py`)

| Method | Input types | Return type | Side effects | Behavior contract |
| --- | --- | --- | --- | --- |
| `__init__()` | none | None | Inits `properties_`, `value`, `_neighbors`, `_cache` | Creates empty vertex with no connections |
| `copy()` | none | Vertex | None | Shallow-copies `attrs_to_copy` (`value`) into new instance of same class |
| `add_neighbor(v, e)` | Vertex, Edge | None | Cleans cache; mutates `_neighbors[e] = v` | Adds edge->vertex mapping to neighbor dict |
| `remove_neighbor(v)` | Vertex | None | Cleans cache; mutates `_neighbors` | Removes first edge mapping to v; raises Exception if not found |
| `remove_edge_and_neighbor(e)` | Edge | None | Cleans cache; mutates `_neighbors` | Removes edge key from `_neighbors`; raises Exception if not found |
| `neighbors` (property) | none | list[Vertex] | None (read-only) | Returns vertices from `_neighbors` where `e.disconnected` is False |
| `get_neighbor_connected_via(e)` | Edge | Vertex | None | Direct dict lookup `_neighbors[e]`; KeyError if missing |
| `get_edge_leading_to(a)` | Vertex | Edge or None | None | Linear scan of `_neighbors` for vertex match |
| `degree` (property) | none | int | None | `len(self.neighbors)` -- filters disconnected edges |
| `get_neighbors_with_distance(d)` | int | list[Vertex] | None | Returns neighbors whose `properties_['d'] == d` |
| `get_neighbor_edge_pairs()` | none | generator of (Edge, Vertex) | None | Yields `(e, v)` from `_neighbors` where `e.disconnected` is False |
| `neighbor_edges` (property) | none | list[Edge] | None | Returns edges from `_neighbors` where `e.disconnected` is False |

---

## 2. Edge class (`edge_lib.py`)

| Method | Input types | Return type | Side effects | Behavior contract |
| --- | --- | --- | --- | --- |
| `__init__(vs=[])` | list of 2 Vertex (optional) | None | Sets `_vertices`, `properties_`, `disconnected=False` | Creates edge, optionally connecting two vertices |
| `copy()` | none | Edge | None | Shallow-copies `attrs_to_copy` (`disconnected`) into new instance |
| `set_vertices(vs=[])` | list of 2 Vertex | None | Sets `_vertices` | Accepts exactly 2 vertices; both may be the same (ring perception) |
| `get_vertices()` | none | list[Vertex] | None | Returns `_vertices` list |
| `neighbor_edges` (property) | none | list[Edge] | None | Collects neighbor edges of both endpoint vertices, excluding self |
| `get_neighbor_edges2()` | none | (list[Edge], list[Edge]) | None | Returns two separate lists, one per endpoint |
| `disconnected` (property) | none | bool | None | Returns `_disconnected` flag |
| `disconnected` (setter) | bool | None | Sets `_disconnected` | Controls whether edge is treated as temporarily removed |

Note: `Edge.vertices` is accessed via `get_vertices()` and `set_vertices()`. The property name `vertices` is not defined; code accesses `e.vertices` via `e.get_vertices()` or directly `e._vertices`. Some call sites use `e.vertices` which resolves to `get_vertices` if aliased or to `_vertices` depending on context.

---

## 3. Diedge class (`diedge_lib.py`)

| Method | Input types | Return type | Side effects | Behavior contract |
| --- | --- | --- | --- | --- |
| `__init__(vs=[])` | list of 2 Vertex (optional) | None | Sets `vertices` (public list), `properties_` | Creates directed edge |
| `set_vertices(vs=[])` | list of 2 Vertex | None | Sets `self.vertices` | Exactly 2 vertices required |
| `get_vertices()` | none | list[Vertex] | None | Returns `self.vertices` |
| `neighbor_edges` (property) | none | list[Edge] | None | Same logic as Edge; collects from both endpoints |
| `get_neighbor_edges2()` | none | (list, list) | None | Same as Edge version |

Key difference from Edge: Diedge has no `disconnected` flag, no `copy()`, and stores vertices as public `self.vertices` (not `self._vertices`). This means Digraph does not support temporary disconnect semantics.

---

## 4. Graph class -- Mutation methods

| Method | Input types | Return type | Flushes cache | Uses temp disconnect | Modifies properties_ | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `add_vertex(v=None)` | Vertex or None | Vertex or None | YES | no | no | Appends to `self.vertices`; warns and returns None if duplicate; creates new if v is None | `g.add_node(data)` |
| `delete_vertex(v)` | Vertex | None | YES | no | no | Removes from `self.vertices` only; does NOT disconnect edges. Caller must disconnect first | `g.remove_node(idx)` |
| `remove_vertex(v)` | Vertex | None | YES (via disconnect) | no | no | Disconnects all edges to neighbors, then deletes vertex. Safe complete removal | `g.remove_node(idx)` |
| `add_edge(v1, v2, e=None)` | Vertex/int, Vertex/int, Edge(opt) | Edge or None | YES | no | no | Creates edge between v1,v2; updates both vertices' `_neighbors`; warns if vertex missing | `g.add_edge(u, v, data)` |
| `disconnect(v1, v2)` | Vertex, Vertex | Edge or None | YES | no | no | Removes edge between v1,v2; removes from both `_neighbors`; returns edge or None | `g.remove_edge(u, v)` |
| `disconnect_edge(e)` | Edge | None | YES | no | no | Removes edge from `self.edges`; removes from both endpoint `_neighbors` via `remove_edge_and_neighbor` | `g.remove_edge_from_index(idx)` |
| `insert_a_graph(gr)` | Graph | None | YES | no | no | Extends vertices and edges from another graph into self | no direct equiv |
| `connect_a_graph(gr, v1, v2, e=None)` | Graph, Vertex, Vertex, Edge(opt) | None | YES (via insert+add_edge) | no | no | Inserts graph then adds connecting edge | no direct equiv |

---

## 5. Graph class -- Temporary disconnect operations

| Method | Input types | Return type | Flushes cache | Uses temp disconnect | Modifies properties_ | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `temporarily_disconnect_edge(e)` | Edge | Edge | YES | SELF | no (sets `e.disconnected=True`) | Moves edge from `self.edges` to `self.disconnected_edges`; sets `e.disconnected = True` | no equiv (adapter must invalidate/rebuild) |
| `reconnect_temporarily_disconnected_edge(e)` | Edge | None | YES | SELF | no (sets `e.disconnected=False`) | Asserts edge is in `disconnected_edges`; moves back to `self.edges`; clears flag | no equiv (adapter must rebuild) |
| `reconnect_temporarily_disconnected_edges()` | none | None | YES | SELF | no | Reconnects ALL disconnected edges at once | no equiv (adapter must rebuild) |
| `temporarily_strip_bridge_edges()` | none | None | YES (multiple) | YES (iterative) | YES (via `mark_vertices_with_distance_from`) | Strips degree-1 vertices' edges, then finds and strips bridges; repeats until stable | no equiv; use `rustworkx.bridges()` to find bridges without disconnect |

---

## 6. Graph class -- Connectivity and boolean queries

| Method | Input types | Return type | Flushes cache | Uses temp disconnect | Modifies properties_ | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `is_connected()` | none | bool | no | no | no (via `get_connected_components`) | Returns True if graph has exactly 1 connected component; short-circuits with edge count check | `rustworkx.is_connected(g)` |
| `is_tree()` | none | bool | no | no | no | Connected + `|V|-1 == |E|`; disconnected variant uses component count | no direct equiv |
| `is_cycle()` | none | bool | no | no | no | True if every vertex has degree exactly 2 | no direct equiv |
| `is_euler()` | none | bool | no | no | no | True if every vertex has even degree | no direct equiv |
| `contains_cycle()` | none | bool | no | no | no | `not self.is_tree()` -- assumes connected graph | `len(rustworkx.cycle_basis(g)) > 0` |
| `path_exists(a1, a2)` | Vertex, Vertex | bool | no | no | YES (`properties_['d']`) | Uses BFS distance marking then checks if `a2` has `'d'` property | `rustworkx.has_path(g, src, tgt)` |
| `is_edge_a_bridge(e)` | Edge | int (0 or 1) | YES (multiple) | YES | YES (`properties_['d']`) | Disconnects edge, counts reachable vertices before/after, reconnects. Returns 1 if bridge, 0 if not | `rustworkx.bridges(g)` (batch) |
| `is_edge_a_bridge_fast_and_dangerous(e)` | Edge | int (0 or 1) | depends | depends | YES (`e.properties_['bridge']`) | Caches bridge=1 on the edge; only safe if no edges added between calls | `rustworkx.bridges(g)` (batch) |

---

## 7. Graph class -- Connected components and subgraphs

| Method | Input types | Return type | Flushes cache | Uses temp disconnect | Modifies properties_ | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `get_connected_components()` | none | generator of set[Vertex] | no | no | no | BFS-based generator; yields sets of vertices for each component | `rustworkx.connected_components(g)` |
| `get_disconnected_subgraphs()` | none | list[Graph] | no | no | no | Calls `get_connected_components` then `get_induced_subgraph_from_vertices` for each; reuses original vertex/edge objects (dangerous) | no direct equiv |
| `get_induced_subgraph_from_vertices(vs)` | set/list of Vertex | Graph | YES (via add_vertex/add_edge) | no | no | Creates new graph with original vertices and edges (shallow); edges must connect vertices in vs | no direct equiv |
| `get_induced_copy_subgraph_from_vertices_and_edges(vertices, edges, add_back_links=False)` | iterable[Vertex], iterable[Edge], bool | Graph | YES (via add) | no | optionally (`properties_['original']`) | Deep-copies vertices and edges; optionally links copies back to originals | no direct equiv |
| `get_new_induced_subgraph(vertices, edges)` | iterable[Vertex], iterable[Edge] | Graph | YES (via add) | no | no | Creates new graph with copied vertices/edges; uses vertex index mapping for edge connections | no direct equiv |
| `get_pieces_after_edge_removal(e)` | Edge | list[set[Vertex]] | YES | YES | no | Temporarily disconnects edge, gets components, reconnects | no direct equiv |
| `get_size_of_pieces_after_edge_removal(e)` | Edge | list[int] | YES | no (uses full disconnect/reconnect) | no | Fully disconnects then reconnects edge; returns component sizes | no direct equiv |

---

## 8. Graph class -- Path and distance methods

| Method | Input types | Return type | Flushes cache | Uses temp disconnect | Modifies properties_ | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mark_vertices_with_distance_from(v)` | Vertex | int (max distance) | no | no | YES (`properties_['d']`) | BFS from v; sets `properties_['d']` on each reachable vertex; cleans old 'd' first; returns max distance | `rustworkx.distance_matrix(g)` (row extraction) |
| `clean_distance_from_vertices()` | none | None | no | no | YES (deletes `properties_['d']`) | Removes 'd' key from all vertex `properties_` | no equiv needed |
| `mark_edges_with_distance_from(e1)` | Edge | None | no | no | YES (`e.properties_['dist']`) | BFS on edges; sets `properties_['dist']` on each reachable edge | no direct equiv |
| `find_path_between(start, end, dont_go_through=[])` | Vertex, Vertex, list(opt) | list[Vertex] or None | no | no | YES (`properties_['d']`) | BFS distance from start, then backtracks from end. Does NOT guarantee shortest path. Returns None if no path avoiding excluded items | `rustworkx.dijkstra_shortest_paths(g, src, target=tgt)` (guarantees shortest) |
| `get_path_between_edges(e1, e2)` | Edge, Edge | list[Edge] or None | no | no | YES (`e.properties_['dist']`) | Uses edge distance marking then backtracks from e2 to e1 | no direct equiv |
| `sort_vertices_in_path(path, start_from=None)` | list[Vertex], Vertex(opt) | list[Vertex] or None | no | no | no | Sorts vertices into traversal order along a path/cycle; finds endpoint with degree 1 in subpath | no direct equiv |
| `get_diameter()` | none | int | no (reads/sets cache) | no | YES (`properties_['d']`) | Computes max of all single-source BFS distances; caches result as `"diameter"` | `rustworkx.distance_matrix(g)` + `numpy.max` |

---

## 9. Graph class -- Cycle perception methods

| Method | Input types | Return type | Flushes cache | Uses temp disconnect | Modifies properties_ | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `get_smallest_independent_cycles()` | none | list[set[Vertex]] | no | no | no (delegates) | Converts edge-based cycles to vertex sets via `edge_subgraph_to_vertex_subgraph` | `rustworkx.cycle_basis(g)` |
| `get_smallest_independent_cycles_e()` | none | set[frozenset[Edge]] | YES (multiple) | YES (heavy) | YES (`properties_['d']`) | Core ring perception algorithm (Gasteiger/Engel). Strips bridges, finds degree-2 paths, BFS for smallest cycles. Complex multi-pass with temporary disconnects | `rustworkx.cycle_basis(g)` |
| `get_smallest_independent_cycles_dangerous_and_cached()` | none | list[set[Vertex]] | no | no | no | Returns cached result from `self._cache['cycles']`; computes on first call | `rustworkx.cycle_basis(g)` |
| `get_all_cycles()` | none | set[frozenset[Vertex]] | YES (via deep_copy) | YES (on copy) | YES (on copy, `properties_['original']`) | Hanser/Jauffret/Kaufmann algorithm via P-graph. Deep copies graph, strips bridges, generates path-graph, removes vertices to find all rings | `rustworkx.simple_cycles()` (DiGraph only); no undirected equiv |
| `get_all_cycles_e()` | none | list[set[Edge]] | depends | depends | depends | Converts vertex cycles to edge cycles via `vertex_subgraph_to_edge_subgraph` | same limitation as above |
| `get_all_cycles_old()` | none | list[set[Vertex]] | YES | YES | YES | Old algorithm using bridge stripping then DFS from each vertex | same limitation |
| `get_all_cycles_e_old()` | none | set[frozenset[Edge]] | YES | YES | YES | Edge variant of old all-cycles with bridge stripping | same limitation |
| `get_all_cycles_e_oldest()` | none | set[frozenset[Edge]] | no | no | no | Simplest variant: DFS from non-leaf vertices | same limitation |
| `get_almost_all_cycles_e()` | none | set[frozenset[Edge]] | no | no | YES (`properties_['d']`) | Imperfect cycle finder using ring endpoints; sometimes misses rings | same limitation |

### Private cycle helpers

| Method | Input types | Return type | Notes |
| --- | --- | --- | --- |
| `_get_cycles_for_vertex(v, to_reach, processed)` | Vertex, Vertex, set | list[set[Edge]] | Recursive DFS; finds all cycles passing through v back to to_reach |
| `_get_smallest_cycle_for_vertex(v, to_reach, came_from, went_through)` | Vertex, Vertex, Edge, list | generator | BFS generator yielding None or single smallest cycle per depth level |
| `_get_smallest_cycles_for_vertex(v, to_reach, came_from, went_through)` | Vertex, Vertex, Edge, list | generator | BFS generator yielding None or list of smallest cycles per depth level; 10000-step safety limit |
| `_get_p_graph()` | none | Graph | Creates deep copy, strips bridges, adds `properties_['original']` links |
| `_p_graph_remove(v, pgraph)` (static) | Vertex, Graph | set[frozenset[Vertex]] | Removes vertex from P-graph; detects loops as rings; creates new path edges |

---

## 10. Graph class -- Matching methods

| Method | Input types | Return type | Flushes cache | Uses temp disconnect | Modifies properties_ | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `get_maximum_matching()` | none | (dict[Vertex, Vertex], int) | no | no | YES (on alt_tree copies) | Augmenting path algorithm; returns mate dict and count of unmatched vertices | `rustworkx.max_weight_matching(g, max_cardinality=True)` |
| `get_initial_matching()` | none | (dict[Vertex, Vertex/0], int) | no | no | no | Greedy matching; dict maps vertex to mate or 0 | no direct equiv |
| `find_augmenting_path_from(start, mate)` | Vertex, dict | list[Vertex] or None | no | no | YES (`properties_['original']` on alt tree) | Builds alternating tree via BFS; finds exposed vertex reachable from start | no direct equiv |
| `update_matching_using_augmenting_path(path, mate)` | list[Vertex], dict | dict | no | no | no | Swaps matched/unmatched along path; asserts even-length path | no direct equiv |

---

## 11. Graph class -- Subgraph conversion utilities

| Method | Input types | Return type | Flushes cache | Uses temp disconnect | Modifies properties_ | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `vertex_subgraph_to_edge_subgraph(cycle)` | set[Vertex] | set[Edge] | no | no | no | Finds all edges connecting vertices within the given set | no direct equiv |
| `edge_subgraph_to_vertex_subgraph(cycle)` | set[Edge] | set[Vertex] | no | no | no | Collects all endpoint vertices from the given edges | no direct equiv |
| `defines_connected_subgraph_e(edges)` | set[Edge] | bool | YES (via subgraph) | no | no | Creates induced subgraph from edges; tests connectivity | no direct equiv |
| `defines_connected_subgraph_v(vertices)` | set[Vertex] | bool | YES (via subgraph) | no | no | Creates induced subgraph from vertices; tests connectivity | no direct equiv |

---

## 12. Graph class -- Factory methods

| Method | Input types | Return type | Flushes cache | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- |
| `create_vertex()` | none | Vertex | no | Returns new `Vertex()` instance; subclasses override to create typed vertices | N/A (adapter layer) |
| `create_edge()` | none | Edge | no | Returns new `Edge()` instance; subclasses override to create typed edges | N/A (adapter layer) |
| `create_graph()` | none | Graph | no | Returns new instance of `self.__class__()`; preserves subclass type | N/A (adapter layer) |

---

## 13. Graph class -- Copy methods

| Method | Input types | Return type | Flushes cache | Modifies properties_ | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- | --- | --- |
| `copy()` | none | Graph | no | no | Shallow copy: new graph, same vertex and edge objects. Edges re-added via `add_edge` | no direct equiv |
| `deep_copy()` | none | Graph | no | no | Deep copy: new graph, new vertex and edge objects created via `v.copy()`/`e.copy()`. Index-based mapping preserves topology | no direct equiv |

---

## 14. Graph class -- Cache methods

| Method | Input types | Return type | Behavior contract |
| --- | --- | --- | --- |
| `_flush_cache()` | none | None | Resets `self._cache` to empty dict. Called by all mutation methods |
| `_set_cache(name, value)` | str, any | None | Stores value under name if `self.uses_cache` is True |
| `_get_cache(name)` | str | any or None | Returns cached value or None |

Cache is only used by `get_diameter()` currently. The `uses_cache` class variable defaults to True.

---

## 15. Graph class -- I/O and debug methods

| Method | Input types | Return type | Behavior contract | rx equiv |
| --- | --- | --- | --- | --- |
| `dump_simple_text_file(f)` | file-like | None | Writes vertex count + edge list (as vertex index pairs) | no equiv |
| `read_simple_text_file(f)` | file-like | None | Reads vertex count + edge list; populates graph | no equiv |
| `_read_file(name)` | str (path) | None | Debug method; reads hardcoded format from file | no equiv |
| `_print_mate(mate)` | dict | None | Debug print of matching | no equiv |

---

## 16. Graph class -- Private helpers

| Method | Input types | Return type | Behavior contract |
| --- | --- | --- | --- |
| `_get_vertex_index(v)` | Vertex or int | int or None | If v is int and valid index, returns v; otherwise returns `self.vertices.index(v)` or None |
| `_mark_vertices_with_distance_from(v)` | Vertex | int | Core BFS implementation; sets `properties_['d']` on reachable vertices; returns max distance |
| `_gen_diameter_progress()` | none | generator of int | Yields increasing diameter values during computation |
| `_get_width_from_vertex(v)` | Vertex | int | Returns BFS depth from v (eccentricity) |
| `_get_some_cycles()` | none | generator | Incomplete cycle finder using ring start/end points |
| `_get_all_ring_end_points()` | none | generator of set[Vertex] | Finds vertices at cycle endpoints based on distance labels |
| `_get_all_ring_start_points()` | none | generator of set[Vertex] | Finds vertices at cycle start points based on distance labels |

---

## 17. Digraph-specific methods and overrides

Digraph inherits from Graph. It overrides or adds the following methods.

| Method | Override or new | Input types | Return type | Behavior contract | Difference from Graph |
| --- | --- | --- | --- | --- | --- |
| `add_edge(v1, v2, e=None)` | OVERRIDE | Vertex/int, Vertex/int, Diedge(opt) | Diedge or None | Only adds v2 as neighbor of v1 (directed); does NOT add v1 as neighbor of v2 | Graph adds both directions |
| `get_diameter()` | OVERRIDE | none | int | BFS from each vertex; prints path to stdout (debug code remains) | Graph version uses cache; Digraph does not |
| `get_connected_components()` | OVERRIDE | none | generator of set[Vertex] | Uses WEAK connectivity: considers edges in both directions by scanning all edges for cross-component links | Graph uses undirected BFS only |
| `get_random_longest_path_numbered(start, end)` | NEW | Vertex, Vertex | list[Vertex] | Backtracks from end to start using distance labels; checks directed neighbor relationship | Not present in Graph |
| `get_graphviz_text_dump()` | NEW | none | str | Generates GraphViz DOT format text for digraph visualization | Not present in Graph |
| `create_edge()` | INHERITED (not overridden) | none | Edge | BUG: Digraph inherits Graph's `create_edge` which returns `Edge()`, not `Diedge()`. The `edge_class = Diedge` attribute is defined but not used by `create_edge` | Should return `Diedge()` |

### Digraph semantic differences summary

1. **Directed edges**: `add_edge` creates one-way neighbor links (v1 -> v2 only).
2. **Weak connectivity**: `get_connected_components` treats directed edges as undirected for component detection.
3. **No temporary disconnect support**: `Diedge` has no `disconnected` attribute, so `temporarily_disconnect_edge` and related methods will fail on Digraph.
4. **No cache on diameter**: Digraph's `get_diameter` does not use `_set_cache`/`_get_cache`.
5. **Debug output**: Digraph's `get_diameter` contains `print()` calls that should be removed.

---

## 18. rustworkx equivalence summary

### Methods with confirmed rustworkx mapping

| OASA method | rustworkx function | Speedup | Semantics note |
| --- | --- | --- | --- |
| `get_smallest_independent_cycles` | `rustworkx.cycle_basis(g)` | 215x | Returns list of node-index lists; must map back to Vertex sets |
| `get_diameter` | `rustworkx.distance_matrix(g)` + `numpy.max` | 49x | No direct diameter function; compute from distance matrix |
| `is_connected` | `rustworkx.is_connected(g)` | 13x | Direct bool; same semantics |
| `find_path_between` | `rustworkx.dijkstra_shortest_paths(g, src, target=tgt)` | 11x | Guarantees shortest path; OASA does not (correctness improvement) |
| `get_connected_components` | `rustworkx.connected_components(g)` | 8.7x | Returns list of sets of node indices; must map to Vertex sets |
| `path_exists` | `rustworkx.has_path(g, src, tgt)` | 8x | Direct bool; OASA version writes to `properties_['d']` as side effect |
| `is_edge_a_bridge` | `rustworkx.bridges(g)` | N/A (batch) | rustworkx returns all bridges at once via Tarjan; replaces per-edge disconnect loop |
| `mark_vertices_with_distance_from` | `rustworkx.distance_matrix(g)` | 1.7x | Row extraction for single-source; must still write to `properties_['d']` |
| `contains_cycle` | `len(rustworkx.cycle_basis(g)) > 0` | N/A | Derived from cycle_basis |
| `get_maximum_matching` | `rustworkx.max_weight_matching(g, max_cardinality=True)` | N/A | Blossom V; optional Phase C swap |

### Methods with no rustworkx equivalent

| OASA method | Reason | Adapter strategy |
| --- | --- | --- |
| `temporarily_disconnect_edge` | No transient topology concept | Invalidate backend; rebuild before next read |
| `reconnect_temporarily_disconnected_edge(s)` | Same as above | Trigger rebuild |
| `temporarily_strip_bridge_edges` | Uses temporary disconnect iteratively | Use `rustworkx.bridges()` to identify bridges; strip in OASA layer |
| `get_all_cycles` (undirected) | `rustworkx.simple_cycles()` is DiGraph-only | Build from cycle_basis or convert to DiGraph |
| `sort_vertices_in_path` | Pure-Python path ordering | Keep in OASA; no performance benefit |
| `get_induced_subgraph_from_vertices` | Complex subgraph with shared objects | Keep in OASA |
| Factory methods (`create_vertex/edge/graph`) | OASA-specific polymorphism | Keep in OASA |
| Copy methods (`copy/deep_copy`) | OASA-specific object copying | Keep in OASA |

### Bonus rustworkx algorithms (no OASA equivalent)

| rustworkx function | Use case | Notes |
| --- | --- | --- |
| `rustworkx.bridges(g)` | All bridges at once | Replaces OASA's per-edge disconnect-check loop |
| `rustworkx.articulation_points(g)` | Cut vertex detection | Tarjan algorithm; 1.5 us on cholesterol |

---

## 19. Side effect inventory: `properties_` modifications

Methods that write to `Vertex.properties_`:

| Method | Key written | Scope | Cleanup method |
| --- | --- | --- | --- |
| `mark_vertices_with_distance_from` | `'d'` | All reachable vertices | `clean_distance_from_vertices()` |
| `_mark_vertices_with_distance_from` | `'d'` | All reachable vertices | `clean_distance_from_vertices()` |
| `path_exists` | `'d'` | All reachable vertices (via mark) | NOT cleaned by caller |
| `find_path_between` | `'d'` | All reachable vertices (via mark) | NOT cleaned by caller |
| `get_diameter` | `'d'` | All vertices (via mark, per source) | NOT cleaned by caller |
| `is_edge_a_bridge` | `'d'` | All reachable vertices (via mark, 2x) | NOT cleaned by caller |
| `get_induced_copy_subgraph_from_vertices_and_edges` | `'original'` | Copied vertices/edges (optional) | No cleanup |
| `find_augmenting_path_from` | `'original'` | Alt-tree copy vertices | No cleanup (temp graph) |
| `_get_p_graph` | `'original'` | P-graph copy vertices | No cleanup (temp graph) |
| `is_edge_a_bridge_fast_and_dangerous` | `'bridge'` on Edge | Single edge | No cleanup |
| `get_almost_all_cycles_e` | `'d'` | All vertices (via mark) | `clean_distance_from_vertices()` |

Methods that write to `Edge.properties_`:

| Method | Key written | Scope |
| --- | --- | --- |
| `mark_edges_with_distance_from` | `'dist'` | All reachable edges |
| `is_edge_a_bridge_fast_and_dangerous` | `'bridge'` | Single edge |

---

## 20. Cache flush inventory

Every method that calls `_flush_cache()`:

| Method | Category |
| --- | --- |
| `add_vertex` | Mutation |
| `delete_vertex` | Mutation |
| `add_edge` | Mutation |
| `disconnect` | Mutation |
| `disconnect_edge` | Mutation |
| `insert_a_graph` | Mutation |
| `temporarily_disconnect_edge` | Temp ops |
| `reconnect_temporarily_disconnected_edge` | Temp ops |
| `reconnect_temporarily_disconnected_edges` | Temp ops |

Note: `remove_vertex` does not directly call `_flush_cache()` but triggers it via `disconnect` and `delete_vertex`.

---

## 21. Thread safety concerns

- `mark_vertices_with_distance_from` writes to shared `Vertex.properties_['d']` -- not thread safe.
- The commented-out `get_diameter_multi_thread` method acknowledges this issue but was never completed.
- All temporary disconnect operations are stateful and not thread safe.
- Cache operations are not thread safe.

---

## 22. Known bugs and issues

1. **Digraph `create_edge` bug**: Returns `Edge()` instead of `Diedge()`. The `edge_class = Diedge` attribute is never consulted.
2. **`find_path_between` non-shortest**: BFS backtrack does not guarantee shortest path. Known issue; rustworkx dijkstra is a correctness improvement.
3. **`path_exists` side effect**: Writes to `properties_['d']` on all reachable vertices without cleanup.
4. **`get_diameter` debug print**: Digraph version contains `print("path")` and per-vertex print statements.
5. **`get_all_cycles_e_oldest`**: Uses vertices with degree > 1 but does not strip bridges; may produce incomplete results.
6. **`is_edge_a_bridge` returns int**: Returns 0/1 instead of bool. Inconsistent with `is_connected()` which returns bool.
7. **`Edge.vertices` access pattern**: Mix of `e.vertices`, `e.get_vertices()`, and `e._vertices` across codebase.
