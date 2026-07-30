# Backend code review

## Scope

Recent backend-facing changes reviewed here:
- [selftest_sheet.py](../../tools/selftest_sheet.py)
- [render_ops.py](../../packages/oasa/oasa/render_ops.py)
- [render_out.py](../../packages/oasa/oasa/render_out.py)
- [svg_out.py](../../packages/oasa/oasa/svg_out.py)

## Overall quality

The recent refactor aligns the selftest with the "ops first" plan and removes
backend-specific assembly in the sheet. That is a good architectural move.
However, the new molecule-to-ops logic duplicates renderer behavior in a local
helper and will drift unless it becomes a shared, tested pipeline. Text ops are
now supported in both SVG and Cairo, but measurement and anchoring remain
approximate and are not covered by targeted tests.

## Findings (ordered by severity)

### High

- Molecule rendering logic is duplicated in the selftest and can drift from the
  real renderers. The helper `_build_molecule_ops()` re-implements vertex label
  layout, background geometry, and atom coloring instead of using a shared
  molecule-to-ops pipeline. This is a direct maintenance risk and can silently
  desynchronize the selftest from the actual renderer outputs. See
  [selftest_sheet.py](../../tools/selftest_sheet.py)
  lines 688-776.

### Medium

- Text layout measurements are heuristic and not tied to renderer metrics. The
  bbox math uses `len(text) * font_size * 0.6` for TextOp width, which can
  under- or over-estimate widths and cause layout drift across backends or
  fonts. This affects vignette layout determinism whenever text ops are part of
  the bbox. See [selftest_sheet.py](../../tools/selftest_sheet.py)
  lines 115-135.
- Cairo text anchoring ignores font bearings. `ops_to_cairo()` uses
  `text_extents().width` for anchor adjustment but does not account for
  `x_bearing`, which can misalign text for fonts with negative bearings. See
  [render_ops.py](../../packages/oasa/oasa/render_ops.py)
  lines 515-528.

### Low

- Text ops are not covered by snapshot or painter-specific tests. The existing
  ops snapshot test does not include TextOp instances, so new regressions in
  `ops_to_svg()` or `ops_to_cairo()` for text would not be detected. See
  [render_ops.py](../../packages/oasa/oasa/render_ops.py)
  lines 395-407 and 515-528.

## Recommended next steps

1. Extract a shared molecule-to-ops pipeline (for example in a new module under
   `packages/oasa/oasa/`) and call it from both selftest and any renderer
   backends that need ops. That removes the duplication in `_build_molecule_ops`
   and enforces the "generate once, paint twice" goal.
2. Add a text measurement helper for ops-level layout, even if it is a simple
   Cairo-based measure function guarded behind capability checks. Use it for
   `ops_bbox()` so the selftest layout is consistent with backend metrics.
3. Add a small ops snapshot fixture that includes at least one TextOp and
   validate both SVG and Cairo output paths. This ensures the new text support
   does not regress silently.
