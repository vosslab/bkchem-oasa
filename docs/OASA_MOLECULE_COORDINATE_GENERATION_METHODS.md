# OASA molecule coordinate generation methods

## Contract

This document is a **binding implementation contract**. Every phase, algorithm,
and data structure described here is a direct Python implementation of the
corresponding RDKit C++ code in `rdkit/Code/GraphMol/Depictor/`. RDKit's
`Compute2DCoords` is the gold standard for 2D molecular layout; this project
reimplements those same algorithms in pure Python so that OASA does not require
RDKit as a runtime dependency.

**Rules for contributors and AI agents:**

- Do not invent novel coordinate-generation algorithms. Every behavioral change
  must trace back to a specific RDKit function or code path.
- The "Key differences" sections document known deviations from RDKit. Reducing
  these gaps is always welcome; widening them requires explicit justification
  and approval.
- When fixing a layout bug, first determine how RDKit handles the same molecule.
  Implement that approach, not a custom workaround.
- The "Corresponding RDKit implementation" sections are the authoritative
  reference for what our code should do. Read the cited RDKit source before
  changing our implementation.

## Overview

2D coordinate generation assigns x,y positions to every atom in a molecule so
that a structure diagram can be rendered on screen or in an SVG/PNG export. The
goal is a layout that looks like a hand-drawn structural formula: rings are
regular polygons, chains extend in a zigzag, atoms do not overlap, and bond
lengths are uniform.

OASA implements this in [packages/oasa/oasa/coords_gen/](../packages/oasa/oasa/coords_gen/)
(the refactored four-phase pipeline) and the legacy monolith
[packages/oasa/oasa/coords_generator2.py](../packages/oasa/oasa/coords_generator2.py).
The pipeline directly implements RDKit's gold standard `Compute2DCoords`
algorithms in Python, without requiring RDKit as a runtime dependency.

The entry point for callers is `calculate_coords(mol, bond_length, force)`, which
matches the legacy `coords_generator` signature exactly. All internal phases are
invoked automatically in sequence.

---

## Algorithm phases

### Phase 1: Ring system placement

**What it does.**
Rings are the structural backbone of most molecules. They must be placed before
chains so that chain atoms can attach to known ring atom positions. Phase 1:

1. Finds the Smallest Set of Smallest Rings (SSSR) via `mol.get_smallest_independent_cycles()`.
2. Groups rings that share atoms into ring systems using BFS over a ring-adjacency
   graph (`_find_ring_systems`).
3. For each ring system, first attempts a template lookup (see the template system
   section below). If no template matches, it falls back to the algorithmic approach.
4. Algorithmic approach: sorts rings by size (largest first), places the largest
   ring as a regular polygon, then BFS-fuses each remaining ring onto the placed
   structure. Fusion handles three cases:
   - **Edge-fused** (2 shared atoms): reflects the new ring across the shared edge,
     placing new atoms on the opposite side from the already-placed ring.
   - **Spiro** (1 shared atom): places the new ring as a regular polygon centered
     in the open direction away from existing placed neighbors.
   - **Bridged** (3+ shared atoms): scales bond length to close the ring across
     the pre-placed bridge path.

**Our implementation.**
- Orchestrator: [packages/oasa/oasa/coords_gen/calculate.py](../packages/oasa/oasa/coords_gen/calculate.py) -- `place_ring_systems()`
- Ring system finder: `find_ring_systems()` in
  [packages/oasa/oasa/coords_gen/phase1_rings.py](../packages/oasa/oasa/coords_gen/phase1_rings.py)
- Ring system placement: `_place_ring_system()` in `phase1_rings.py`
- External anchor: `_find_external_anchor()` in `phase1_rings.py`
- Fused ring geometry: `_place_edge_fused_ring()`, `_place_spiro_ring()`,
  `_place_bridged_ring()` in `phase1_rings.py`
- Template first-pass: `_try_template_placement()` in `phase1_rings.py`

**Corresponding RDKit implementation.**
- `rdkit/Code/GraphMol/Depictor/EmbeddedFrag.cpp` -- `EmbeddedFrag::embedFrag()`,
  `EmbeddedFrag::updateEmbeddedRings()`, ring-fusing logic in
  `EmbeddedFrag::addNewRingToFused()`
- `rdkit/Code/GraphMol/Depictor/RDDepictor.cpp` -- top-level
  `RDDepict::compute2DCoords()` orchestrates SSSR, ring system grouping, and
  calls into `EmbeddedFrag`.

**Known deviations from RDKit (gaps to close).**
- RDKit performs additional CIP-rank-based atom ordering before ring placement;
  our approach uses path-sorted ring vertices from `sort_vertices_in_path()`.
- RDKit handles stereochemistry-aware ring orientation during phase 1; we defer
  stereo handling to phase 2 (chain placement).
- RDKit's SSSR comes from `MolOps::findSSSR()`; ours comes from
  `mol.get_smallest_independent_cycles()`, an in-house implementation on the
  OASA graph.

---

### Phase 2: Chain and substituent placement

**What it does.**
After all ring atoms are placed, phase 2 BFS-expands outward to place every
remaining atom:

1. Starts the frontier from all atoms in the `placed` set (ring atoms plus the
   two-atom seed for acyclic molecules).
2. For each frontier atom `v`, places its unplaced neighbors:
   - **Single chain continuation** (one placed neighbor, one unplaced): places the
     new atom at 120 degrees from the incoming bond direction, with fallback to 180
     for triple bonds and cumulated double bonds. Checks the previous atom's other
     neighbor to maintain a trans-zigzag chain.
   - **Branched** (multiple unplaced neighbors): finds the largest angular gap
     among placed neighbors and distributes new atoms evenly within that gap.
3. Respects E/Z stereochemistry: if the target atom is listed in the stereo lookup,
   chooses the +/- branch angle to satisfy the `CisTransStereochemistry` constraint
   before the default zigzag logic.

**Our implementation.**
- Entry point: `place_chains()` called from `calculate.py`
- Chain atom placement: `_place_chain_atom()` in
  [packages/oasa/oasa/coords_gen/phase2_chains.py](../packages/oasa/oasa/coords_gen/phase2_chains.py)
- Branched placement: `_place_branched()` in `phase2_chains.py`
- Stereo angle selection: `_get_angle_at_side()` in `phase2_chains.py`

**Corresponding RDKit implementation.**
- `rdkit/Code/GraphMol/Depictor/EmbeddedFrag.cpp` -- `EmbeddedFrag::computeEmbedding()`
  and the chain/substituent spreading logic in `EmbeddedFrag::embedAtoms()`
- `rdkit/Code/GraphMol/Depictor/DepictUtils.cpp` -- `pickAtomCoords()` and
  `computeRingAngles()` for angle geometry.

**Known deviations from RDKit (gaps to close).**
- RDKit uses CIP-ranked atom ordering to decide which branch gets the preferred
  angle; we use neighbor iteration order with a stereo-first heuristic.
- RDKit handles square-planar and octahedral stereochemistry in this phase; our
  implementation handles only cis/trans (double bond) stereochemistry.
- RDKit applies a more sophisticated linear-chain detection (via atom ranking)
  before the zigzag heuristic; we detect linear geometry from bond order alone.

---

### Phase 3: Collision detection and resolution

**What it does.**
After initial placement, atoms from different parts of the molecule may overlap.
Phase 3 iterates up to 10 times, each pass:

1. **Detection**: scans all non-bonded atom pairs. Any pair closer than
   `0.45 * bond_length` is a collision.
2. **Flip attempt**: for each colliding atom that has exactly one placed neighbor
   (a chain tip), tries reflecting the atom and its full subtree across the bond
   axis (`_try_flip_substituent`). Uses BFS to collect the subtree and keeps the
   flip only if it reduces the collision count.
3. **Nudge apart**: if no flip resolves the collision, pushes the two atoms
   `0.2 * bond_length` apart along the line connecting them as a last resort.

**Our implementation.**
- Orchestrator: `resolve_all_collisions()` called from `calculate.py`
- Detection: `_detect_collisions()` in
  [packages/oasa/oasa/coords_gen/phase3_collisions.py](../packages/oasa/oasa/coords_gen/phase3_collisions.py)
- Flip: `_try_flip_substituent()` in `phase3_collisions.py`
- Subtree BFS: `_get_subtree()` in `phase3_collisions.py`
- Nudge: `_nudge_apart()` in `phase3_collisions.py`

**Corresponding RDKit implementation.**
- `rdkit/Code/GraphMol/Depictor/EmbeddedFrag.cpp` -- collision detection and
  resolution are embedded in `EmbeddedFrag::removeCollisionsBetweenFrags()` and
  `EmbeddedFrag::flipAboutBond()`.

**Known deviations from RDKit (gaps to close).**
- RDKit's collision resolution operates on whole embedded fragments and can
  rotate entire ring systems; our flip is limited to chain-tip subtrees.
- RDKit uses a more refined energy criterion for flip acceptance; we use a simple
  collision count comparison.
- RDKit handles inter-fragment collisions during multi-fragment layout; our nudge
  is intra-molecule only.

---

### Phase 4: Force-field refinement

**What it does.**
Phase 4 runs a steepest-descent minimization over up to 200 iterations using a
spring-model energy function with three terms:

- **Bond stretch**: Hookean spring driving each bond toward `bond_length`.
  Force constant `k_bond = 1.0`. Gradient: `k * (d - d0) * direction / d`.
- **Angle bend**: penalty for deviation from ideal bond angles. Ideal angles are
  precomputed per atom: 180 degrees for triple-bond atoms, 120 degrees for sp2 and
  most sp3 atoms, 90 degrees for atoms with 4 or more neighbors. The penalty is
  applied as a distance spring between the two neighbor atoms at the ideal
  separation `2 * bond_length * sin(ideal/2)`. Force constant `k_angle = 0.3`.
- **Non-bonded repulsion**: repulsive `k/d^2` force for non-bonded pairs closer
  than `1.8 * bond_length`. Force constant `k_repel = 0.5`. Pairs separated by
  fewer than 3 bonds are excluded.

Convergence is declared when the maximum gradient magnitude falls below `1e-4`.

**Our implementation.**
- Entry point: `force_refine()` called from `calculate.py`
- Full implementation: `_force_refine()` in
  [packages/oasa/oasa/coords_gen/phase4_refinement.py](../packages/oasa/oasa/coords_gen/phase4_refinement.py)

**Corresponding RDKit implementation.**
- `rdkit/Code/GraphMol/Depictor/RDDepictor.cpp` -- `RDDepict::compute2DCoords()`
  applies a post-processing coordinate refinement via `ForceField` machinery from
  `GraphMol/ForceFields/`.
- `rdkit/Code/GraphMol/Depictor/DepictUtils.cpp` -- angle utility functions
  support the energy terms.

**Known deviations from RDKit (gaps to close).**
- RDKit uses a full MMFF-style force field with proper angle terms; our
  implementation approximates angle bends via neighbor-distance springs, which is
  simpler to implement without a full force-field library.
- RDKit locks ring atom positions during refinement to preserve ring geometry;
  our implementation moves all atoms including ring atoms.
- RDKit's step size schedule decreases over iterations; we use a fixed
  `step_size = 0.05` throughout.

---

## Spatial index acceleration

**What it does.**
Phase 3 (collision detection) and Phase 4 (force-field repulsion) both scan
all atom pairs to find close neighbors. For molecules with 20+ atoms, a 2D
spatial index (KD-tree) replaces these O(n^2) scans with O(n log n + nm)
queries, where m is the small number of actual neighbors within the search
radius.

**How it works.**
A recursive median-split KD-tree alternates x/y split axes at each level.
Leaf nodes (up to 16 points) use brute-force distance checks. Two query
operations are supported:

- `query_radius(x, y, r)`: find all points within distance r of (x, y).
- `query_pairs(r)`: find all point pairs within distance r of each other.

The index is rebuilt from scratch each pass (Phase 3) or every 10 iterations
(Phase 4). No incremental insert/delete is needed because coordinates change
in bulk during optimization.

For molecules with fewer than 20 atoms, the code falls back to brute-force
loops since the KD-tree overhead is not worthwhile at small sizes.

**Our implementation.**
- Spatial index: [packages/oasa/oasa/graph/spatial_index.py](../packages/oasa/oasa/graph/spatial_index.py)
- Integration in Phase 3: `_detect_collisions()` and
  `_count_collisions_for_atoms()` in
  [packages/oasa/oasa/coords_gen/phase3_collisions.py](../packages/oasa/oasa/coords_gen/phase3_collisions.py)
- Integration in Phase 4: `_apply_repulsion()` and `force_refine()` in
  [packages/oasa/oasa/coords_gen/phase4_refinement.py](../packages/oasa/oasa/coords_gen/phase4_refinement.py)
- Benchmark: [tools/benchmark_spatial_index.py](../tools/benchmark_spatial_index.py)

**Performance.**
Standalone radius queries show 2x speedup at 200 points and 5.5x at 1000
points. The threshold for using the spatial index (20 atoms) is chosen so
that the KD-tree overhead never makes small molecules slower.

---

## Template system

**Why templates exist.**
The BFS ring-fusion algorithm in phase 1 works well for simple fused systems
(naphthalene, steroids) but fails for cage molecules like cubane and adamantane.
In a cage, three or more rings share atoms in a way that makes the "place on the
opposite side" rule geometrically inconsistent: any assignment of remaining atoms
produces overlaps or incorrect bond lengths.

Templates bypass this problem entirely by storing a pre-computed, hand-verified
2D projection for each cage topology.

**How template matching works.**

1. `_try_template_placement()` builds the adjacency graph for the ring system
   (using only bonds between ring atoms, ignoring substituents).
2. It calls `find_template(n_atoms, adj)` in
   [packages/oasa/oasa/coords_gen/ring_templates.py](../packages/oasa/oasa/coords_gen/ring_templates.py).
3. `find_template` filters candidates by atom count, edge count, and sorted degree
   sequence (a fast O(1) fingerprint that eliminates most mismatches).
4. For any candidate that passes the fingerprint check, it runs a full graph
   isomorphism via backtracking with degree-sorted node ordering
   (`_find_isomorphism`). This returns a node-to-node mapping if the molecule
   matches the template topology.
5. Template coordinates are scaled by `bond_length` and applied to the molecule
   atoms via the isomorphism mapping.

**Coordinate normalization.**
All templates are stored with coordinates centered at the origin and scaled so
that the average bond length across all template edges equals 1.0
(`_normalize_coords`). At apply time, the stored coordinates are multiplied by
the caller's `bond_length`.

**Current templates.**

| Template | Atoms | Edges | Degree sequence | Source |
| --- | --- | --- | --- | --- |
| cubane | 8 | 12 | all degree 3 | RDKit TemplateSmiles.h |
| adamantane | 10 | 12 | 4x degree 3, 6x degree 2 | hand-tuned |
| norbornane | 7 | 8 | 2x degree 3, 5x degree 2 | hand-tuned |

**RDKit comparison.**
RDKit's template system is in `rdkit/Code/GraphMol/Depictor/TemplateSmiles.h`
(96 SMILES-encoded templates) and `rdkit/Code/GraphMol/Depictor/Templates.cpp`
(matching logic). RDKit matches by SMILES substructure search and then aligns
coordinates via rigid-body superposition. Our system uses graph isomorphism
directly on the adjacency graph, which is simpler but requires exact topological
equality (no partial template matching). The cubane coordinates in our system are
extracted directly from RDKit's `TemplateSmiles.h` line 90.

---

## Testing strategy

**Pytest unit tests.**
[packages/oasa/tests/test_coords_generator2.py](../packages/oasa/tests/test_coords_generator2.py)
covers the coordinate generator with molecule classes parsed from SMILES:

- Single atom, single bond, linear chains, branched molecules, ring systems.
- Verifies every atom receives non-None x,y coordinates.
- Checks bond length uniformity (all bonds within tolerance of the target length).
- Checks minimum non-bonded separation to catch gross overlaps.
- Exercises template path via cubane SMILES.

Run with:
```
source source_me.sh && python -m pytest packages/oasa/tests/test_coords_generator2.py
```

**Visual comparison against RDKit.**
[tools/coords_comparison.py](../tools/coords_comparison.py) builds a side-by-side
HTML gallery for a fixed list of test SMILES. For each molecule it renders:

- OASA legacy `coords_generator` output.
- OASA `coords_generator2` (four-phase pipeline) output.
- RDKit `Compute2DCoords` output (when RDKit is available).

The gallery output goes to `output_smoke/coords_comparison.html` and is used for
visual regression checking when the coordinate algorithm changes. This is a
manual review tool, not an automated pass/fail test.

Run with:
```
source source_me.sh && python3 tools/coords_comparison.py
```

**Pyflakes lint.**
```
source source_me.sh && python -m pytest tests/test_pyflakes_code_lint.py
```

---

## File map

| Our file | RDKit file | Responsibility |
| --- | --- | --- |
| [coords_gen/calculate.py](../packages/oasa/oasa/coords_gen/calculate.py) | `RDDepictor.cpp` | Orchestrator, phase sequencing |
| [coords_gen/phase1_rings.py](../packages/oasa/oasa/coords_gen/phase1_rings.py) | `EmbeddedFrag.cpp` | Ring system placement |
| [coords_gen/phase2_chains.py](../packages/oasa/oasa/coords_gen/phase2_chains.py) | `EmbeddedFrag.cpp` | Chain and substituent placement |
| [coords_gen/phase3_collisions.py](../packages/oasa/oasa/coords_gen/phase3_collisions.py) | `EmbeddedFrag.cpp` | Collision detection and resolution |
| [coords_gen/phase4_refinement.py](../packages/oasa/oasa/coords_gen/phase4_refinement.py) | `RDDepictor.cpp` | Force-field refinement |
| [coords_generator2.py](../packages/oasa/oasa/coords_generator2.py) (legacy) | `RDDepictor.cpp` | Monolithic version of the same pipeline |
| [coords_gen/helpers.py](../packages/oasa/oasa/coords_gen/helpers.py) | `DepictUtils.cpp` | Geometry utilities (angles, distances, reflection) |
| [coords_gen/ring_templates.py](../packages/oasa/oasa/coords_gen/ring_templates.py) | `Templates.cpp` + `TemplateSmiles.h` | Pre-computed templates for cage molecules |
| [graph/spatial_index.py](../packages/oasa/oasa/graph/spatial_index.py) | (no RDKit equivalent) | 2D KD-tree for radius queries in Phase 3/4 |

RDKit source is under `rdkit/Code/GraphMol/Depictor/` in the repo root.
