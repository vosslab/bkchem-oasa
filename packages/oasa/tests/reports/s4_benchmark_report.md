# S4 benchmark report: OASA vs rustworkx graph algorithms

## Assumptions

- All molecules are parsed from SMILES via `oasa.smiles_lib.text_to_mol()` with `calc_coords=0` for speed.
- `mol.remove_zero_order_bonds()` is called after parsing to clean up dot-separator bonds.
- rustworkx graph is built with `PyGraph(multigraph=False)` to match OASA simple-graph semantics.
- Timing uses `time.perf_counter()` with N=500 iterations per algorithm per molecule.
- OASA diameter cache is flushed before each iteration to prevent cache hits from skewing results.
- `distance_from` compares OASA single-source BFS vs rustworkx full distance matrix (slightly unfair to rustworkx, but rustworkx lacks a single-source BFS API).

## Decisions

- Chose three molecules spanning small to medium complexity: benzene (6 atoms), naphthalene (10 atoms), cholesterol (38 atoms).
- Parity checks verify result equivalence (component count, path length, diameter value, cycle count, BFS distances) rather than exact object identity.
- rustworkx-only algorithms (bridges, articulation points, max weight matching) are included to demonstrate capabilities OASA lacks.
- `dijkstra_shortest_paths` is used for rustworkx path-finding since it is the closest equivalent to OASA's `find_path_between`.

## Changed files

- [packages/oasa/tests/benchmark_graph_algorithms.py](packages/oasa/tests/benchmark_graph_algorithms.py) -- new benchmark script
- [packages/oasa/tests/reports/s4_benchmark_report.md](packages/oasa/tests/reports/s4_benchmark_report.md) -- this report

## Concrete next steps

- Use these speedup ratios to prioritize which OASA algorithms to delegate to rustworkx first (cycle_basis at 200x+ is the top candidate).
- Add larger molecules (e.g., insulin, a polymer chain) to stress-test scaling behavior.
- Integrate benchmark into CI as an optional performance regression check.
- Build the `RustworkxGraphBackend` adapter class that delegates the benchmarked algorithms.

## Validation performed

Pyflakes lint: clean, no warnings.

All 7 parity checks passed across all 3 molecules.

### Benchmark output (N=500, rustworkx 0.17.1)

```
Algorithm                           benzene    naphthalene    cholesterol
-------------------------------------------------------------------------
connected_components                   6.8x           8.7x          11.5x
is_connected                          10.6x          12.6x          17.7x
path_exists                            4.6x           8.2x           5.2x
distance_from                          2.0x           2.9x           1.7x
diameter                               7.2x          16.5x          56.1x
cycle_basis                          197.2x         233.3x         243.8x
find_path                              5.3x           8.5x           6.7x
bridges (rx only)                   0.5us          0.7us          3.1us
articulation_pts (rx only)          0.5us          0.6us          2.3us
max_weight_match (rx only)          2.5us          3.7us         23.4us
```

### Key findings

- **cycle_basis** shows the largest speedup at 197-244x across all molecules. This is the highest-priority algorithm to delegate.
- **diameter** scales dramatically with molecule size: 7x for benzene up to 56x for cholesterol, due to OASA's O(V^2) BFS-based approach.
- **is_connected** and **connected_components** show consistent 7-18x speedups.
- **distance_from** shows the smallest speedup (1.7-2.9x) because OASA does single-source BFS while rustworkx computes the full distance matrix.
- rustworkx provides **bridges**, **articulation_points**, and **max_weight_matching** which OASA lacks entirely, all running in under 25 microseconds even for cholesterol.
