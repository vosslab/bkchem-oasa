# OASA-wide gap and perpendicular spec plan

## Goal

Bring connector endpoint spacing and aim into the same spec everywhere:

- Gap spec: `1.3 <= gap <= 1.7`
- Perpendicular spec: `perp <= 0.07`

This plan explicitly targets shared OASA and BKChem rendering paths, not
Haworth-only fixes.

## Pre-implementation baseline (2026-02-14)

Measured with:

`source source_me.sh && python3 tools/measure_glyph_bond_alignment.py --no-diagnostic-svg --no-diagnostic-png`

Current results from `output_smoke/glyph_bond_alignment_report.txt`:

- Files analyzed: 78
- Labels analyzed: 362
- Aligned: `0/362`
- Reasons: `gap_out_of_range=272`, `gap_and_perp_out_of_range=74`,
  `perp_out_of_range=16`
- Per-label summary:
  - `OH`: gap `1.37/0.60/0.79`, perp `9.64/3.40/12.68`
  - `HO`: gap `1.30/0.55/0.79`, perp `14.63/13.63/12.74`
  - `CH2OH`: gap `1.70/0.58/2.03`, perp `17.04/11.88/13.56`

## What is broken now

- `packages/oasa/oasa/render_geometry.py` uses a wide alignment correction
  tolerance (`max(line_width * 0.5, 0.25)`), which is far looser than spec.
- Only Haworth code paths pass `target_gap` into `AttachConstraints`.
- Generic OASA and BKChem bond drawing paths still clip with `_clip_to_target()`
  and do not enforce shared gap/perp targeting.
- Composite attach targets use fallback behavior that can miss the intended
  attach centerline for multi-token labels.

## Scope

- In scope:
  - `packages/oasa/oasa/render_geometry.py`
  - `packages/oasa/oasa/haworth/renderer.py`
  - `packages/oasa/oasa/cairo_out.py`
  - `packages/oasa/oasa/svg_out.py`
  - `packages/bkchem-app/bkchem/bond_render_ops.py`
  - `packages/bkchem-app/bkchem/bond_drawing.py`
  - measurement and acceptance tooling under `tools/` and targeted tests
- Out of scope:
  - New label text semantics
  - Font-design-specific manual kerning hacks
  - Haworth-only hardcoded geometry exceptions

## Execution strategy

1. Make one source of truth for gap/perp spec in shared geometry.
2. Route all endpoint clipping through one shared constrained endpoint helper.
3. Fix composite-target endpoint selection for centerline aiming.
4. Apply the same constraints through OASA and BKChem consumers.
5. Keep Haworth as one consumer, not a special-case engine.

## Phase 0: lock baseline and gate harness [COMPLETE]

### Changes

- Add `tools/gap_perp_gate.py` to run measurement and emit one compact JSON
  with per-label and reason counts.
- Add fixture buckets so gates can run on:
  - Haworth corpus (current 78 SVG set)
  - OASA generic render corpus (non-Haworth molecules rendered via
    `render_geometry.molecule_to_ops`)
  - BKChem render-ops corpus

### Acceptance gate

- Gate script reproduces current baseline exactly before any runtime change.
- New test: `tests/test_gap_perp_gate.py`.

## Phase 1: shared spec constants and constraints [COMPLETE]

### Changes

- Define shared rendering spec constants in `render_geometry.py`:
  - `ATTACH_GAP_TARGET = 1.5`
  - `ATTACH_GAP_MIN = 1.3`
  - `ATTACH_GAP_MAX = 1.7`
  - `ATTACH_PERP_TOLERANCE = 0.07`
- Extend `AttachConstraints` with explicit `alignment_tolerance`.
- Remove the hardcoded tolerance expression from
  `resolve_label_connector_endpoint_from_text_origin()` and use
  `constraints.alignment_tolerance`.

### Acceptance gate

- Existing render_geometry unit tests pass.
- New tests verify no hidden fallback to old tolerance.

## Phase 2: one endpoint solver for all bond clipping [COMPLETE]

### Changes

- Add `_resolve_endpoint_with_constraints()` in `render_geometry.py` that does:
  - boundary resolve
  - centerline correction
  - legality retreat
  - target-gap retreat
- Replace direct `_clip_to_target()` calls in `build_bond_ops()` (single, double,
  triple) with `_resolve_endpoint_with_constraints()`.
- When available, use `context.attach_targets` for alignment centers; otherwise
  use `context.label_targets` centroid fallback.

### Acceptance gate

- Bond endpoints for generic OASA/BKChem now report non-trivial gap/perp metrics.
- No regression in bond-length guards or cross-label avoidance tests.

## Phase 3: composite target alignment fix [COMPLETE]

### Changes

- Replace "first child that changes endpoint" behavior in
  `_correct_endpoint_for_alignment()` for composite targets.
- Add scoring for candidate intersections:
  - minimize perpendicular error to desired centerline
  - keep endpoint on valid boundary
  - minimize deviation from original resolved endpoint
- Use best candidate deterministically.

### Acceptance gate

- New targeted tests for CH2OH/HO-like composite targets.
- `perp_out_of_range` count decreases materially on Haworth corpus.

## Phase 4: consumer adoption (OASA and BKChem) [COMPLETE]

### Changes

- `molecule_to_ops()` style accepts endpoint-spec overrides but defaults to
  shared constants.
- `cairo_out.py` and `svg_out.py` feed style values consistently into
  `BondRenderContext`.
- `bond_render_ops.py` and `bond_drawing.py` use the same shared constraint
  profile and avoid local one-off clipping logic.

### Acceptance gate

- OASA generic corpus and BKChem corpus both produce measurable gap/perp
  improvements, not only Haworth.
- No functional regression in non-label bond drawing.

## Phase 5: remove Haworth-only tuning path [COMPLETE]

### Changes

- Move Haworth `target_gap` and alignment tolerance setup to shared profile
  helper in `render_geometry.py`.
- Keep Haworth renderer as a consumer override point only for explicit style
  requests, not default behavior.
- Delete or deprecate duplicate Haworth-only constants when equivalent shared
  constants exist.

### Acceptance gate

- Haworth renders match or improve prior gap/perp metrics.
- Behavior still configurable through style/constraints, not label-text hacks.

## Phase 6: final spec gate and closeout

### Hard pass criteria

- Gap:
  - For high-volume labels (`OH`, `HO`, `CH2OH`), median gap in `[1.3, 1.7]`
  - For all labels, no systematic drift outside gap bounds
- Perp:
  - For high-volume labels, median perp `<= 0.07`
  - `perp_out_of_range` reduced to `0` on gated corpora
- Alignment:
  - `aligned_count == labels_analyzed`
  - `no_connector_count == 0`
- Safety:
  - No increase in bond/bond overlaps
  - No increase in bond/glyph overlaps

### Verification commands

```bash
source source_me.sh && python3 -m pytest tests/test_render_geometry.py -q
source source_me.sh && python3 -m pytest tests/test_measure_glyph_bond_alignment.py -q
source source_me.sh && python3 -m pytest tests/test_gap_perp_gate.py -q
source source_me.sh && python3 tools/gap_perp_gate.py
```

## Risks and mitigation

- Risk: stricter constraints shorten bonds too aggressively.
  - Mitigation: preserve existing minimum-bond-length guards and add tests.
- Risk: font variance shifts measured centers.
  - Mitigation: use median and percentile gates, not only means.
- Risk: BKChem legacy path diverges from render-ops path.
  - Mitigation: migrate both paths to one constraint helper and compare outputs.

## Definition of done

- Shared endpoint logic enforces gap/perp spec by default.
- OASA and BKChem consumers use that shared logic.
- Haworth-specific behavior is reduced to consumer configuration, not geometry
  hacks.
- All phase gates are green with reproducible command output.
