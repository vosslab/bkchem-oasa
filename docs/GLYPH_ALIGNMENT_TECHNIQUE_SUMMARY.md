# Glyph Alignment Technique Summary (What We Tried and Where It Failed)

## Goal
Build a renderer-independent input-SVG checker that can flag bond/glyph issues and provide diagnostics that match visual judgment.

## Working Definitions (current)
- Alignment metric: perpendicular distance from selected glyph center to the infinite line defined by the connector bond segment.
- Gap/overlap metric: signed distance from connector endpoint to independent glyph body model.
- Target glyph for alignment: first relevant atom character by priority (`C`, `O`, `N`, `S`, `P`, `H`) in canonicalized text.

## Chronological Technique Log

### 1) Renderer attach-target distance (rejected)
- Idea: use renderer attach targets as truth.
- What worked: numerically stable.
- Why it failed: circular for QA; could report near-perfect while visual output was clearly wrong.

### 2) Whole-label bbox distance (rejected)
- Idea: use one bbox for full text node.
- What worked: simple and fast.
- Why it failed: chemically wrong target; bond should align to atom glyph (`O` or `C`), not full string.

### 3) Per-glyph primitive model (ellipse/box)
- Idea: estimate per-character primitives from text metrics.
- What worked: enabled atom-level diagnostics, per-label reports, and independent distance checks.
- Why it failed: metric approximation drift under kerning/subscripts and mixed labels (`CH2OH`).

### 4) Text canonicalization (`HOH2C` -> `CH2OH`)
- Idea: normalize string variants before target-character selection.
- What worked: fixed selector failures on reversed tail-chain emission.
- Why it failed: only fixes token identity; does not improve geometric center quality.

### 5) Local text-path contour extraction
- Idea: use local contour points near selected primitive center.
- What worked: more shape-aware than pure primitive boxes/ellipses.
- Why it failed: sparse sampling and imperfect subpath selection caused unstable fits.

### 6) Convex hull / local hull attempts
- Idea: derive body from local hull of contour points.
- What worked: robust containment when point set was clean.
- Why it failed: hull amplifies contamination; stray points from neighboring glyphs inflate hull.

### 7) Gating stack for contamination control
- Added:
  - component selection by nearest subpath,
  - baseline clipping (`y <= baseline + pad`),
  - half-plane gate from bond direction,
  - stripe gate plus retention fallback.
- What worked: reduced obvious contamination and added explainable gate-debug traces.
- Why it failed: over-gating amputated curved glyph contours in hard cases (especially `C`, then `O`).

### 8) Curved-glyph gate relaxations
- Changes:
  - skip half-plane for `O`,
  - skip stripe for `O` and `C`,
  - retain stripe fallback logic for other chars.
- What worked: removed major contour-amputation failure mode for curved chars.
- Why it failed: center drift persisted even with cleaner point sets.

### 9) Dense contour interpolation (recent)
- Change: interpolate text path before gating/component extraction.
- Observed improvement (unit_03):
  - from tiny component sets (historically ~17) to `component_point_count=306`,
  - `outline_vertex_count=849`.
- Why it still failed: centerline delta remained about `2.22 px` vs required tolerance `1.08 px`.

### 10) Axis-locked ellipse fit refinements
- Changes:
  - lock major axis vertical for curved chars,
  - use quantile-bbox center to reduce mean-centroid bias.
- What worked: less orientation jitter and cleaner overlays.
- Why it failed: did not materially remove the persistent ~2.1-2.2 px rightward drift on unit_03 `OH`.

### 11) pycairo + numpy local pixel-boundary probe (recent)
- Change:
  - rasterize selected local component to in-memory ARGB surface,
  - extract boundary pixels by 8-neighbor erosion mask,
  - fit ellipse from boundary pixels (fallback to vector fit).
- Observed in unit_03:
  - `pixel_boundary_point_count=1044`,
  - alignment center around `x=182.137` and `x=322.137` for expected `180`, `320`.
- Why it still failed:
  - despite dense boundary points, centerline delta stayed ~`2.137 px`,
  - indicates persistent coordinate/target-reference mismatch, not merely sparse sampling.

### 12) Hashed-bond handling
- Change: detect hashed carrier, exclude decorative hatch micro-strokes from checked bond lengths.
- What worked: removed false mini-bond length artifacts.
- Tradeoff/failure: can hide some hatched/thin conflict overlaps if conflict logic uses filtered subsets.

## Fixture Evidence Snapshot (latest)
- Fixture runner (`tests/fixtures/glyph_alignment`):
  - `Fixtures total: 4`
  - `Fixtures with required failures: 4`
  - `Total required failures: 10`
- `unit_03_bonds_nearby_strokes`:
  - `labels analyzed: 2`
  - `alignment outside tolerance: 0` (tool-level)
  - `required failures: 2` (strict centerline expectations)
  - centerline failures:
    - expected `180.0`, actual `182.137...`, delta `2.137...`, tol `1.08`
    - expected `320.0`, actual `322.137...`, delta `2.137...`, tol `1.08`

## Main Failure Themes That Remain
- Center definition mismatch:
  - geometric fit center is stable, but not matching expected visual/fixture centerline.
- Reference-frame mismatch risk:
  - local extraction and fit may be internally consistent while offset from expected centerline prior.
- Mixed objective conflict:
  - checker currently reports pass/fail by tolerance large enough for practical alignment,
  - fixture centerline checks intentionally tighter and catch residual drift.

## Practical Current State
- Controlled OASA SVG exports retain stable operation IDs, declared
  connector-to-label ownership, and composite-stroke ownership.
- The default one-time command renders a bounded current furanose+pyranose
  corpus through lxml, then validates each declared visible connector reaches
  its own glyph without overlap. It does not need an archive preview corpus.
- This identity gate deliberately does not reuse a heuristic glyph-center or
  lattice-angle threshold for Haworth branches. Those remain diagnostics for
  unannotated third-party SVGs, where no renderer-owned relation exists.
- The permanent tests use small lxml SVGs to prove a declared association wins
  over an unrelated nearby line and that a declared distant endpoint fails.

```bash
source source_me.sh && python3 tools/measure_glyph_bond_alignment.py --fail-on-miss
```

## Recommended Next Direction
- Move to full-image pixel reference for centerline truth (not local subpath-only), using existing render path where available.
- Keep current vector+pixel local method as fallback and diagnostic cross-check, not sole authority.
- Add explicit "center source" field in reports (`primitive`, `local_vector`, `local_pixel`, future `global_pixel`) to compare modes directly.
