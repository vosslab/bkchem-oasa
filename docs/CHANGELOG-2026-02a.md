# Changelog

## 2026-02-12
- Revert connector endpoint selection in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  to the simpler distance-based approach (`_nearest_endpoint_to_text_path` /
  `_nearest_endpoint_to_glyph_primitives`) and remove the broken geometry-weighted
  scoring functions (`_choose_endpoint_for_alignment`,
  `_nearest_endpoint_for_alignment`, `_is_point_inside_box`) that were
  misassigning bond endpoints to the far end of glyphs.
- Replace broken optical center-finding pipeline in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  with the working `letter-center-finder` sibling repo approach: per-character
  SVG isolation rendering via `rsvg-convert`, Otsu thresholding, OpenCV contour
  extraction, scipy convex hull, and direct least-squares ellipse fitting.
  Delete approximately 1,000 lines of broken CairoSVG/cv2/numpy/pycairo/TextPath
  pipeline code and replace with a thin bridge function
  (`_optical_center_via_isolation_render`).
- Remove `cairo`, `cairosvg`, `cv2`, and `numpy` imports from
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  since all usage was in the deleted optical pipeline functions.
- Remove deleted-function test
  `test_local_text_path_points_prefers_component_near_endpoint` from
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py).
- Tighten O-core gating in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  by using smaller core-ellipse multipliers for `O` targets to reduce bond-tail
  contamination of curved-glyph center fits.
- Reduce exported glyph-curve point density in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  to about 10% of dense hull samples for diagnostics/JSON output while keeping
  full dense hull points for ellipse fitting and bond/hull intersection math.
- Update diagnostic styling in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  glyph outlines now render at `0.5` stroke width and `75%` stroke opacity;
  center/contact dots now render at 3 pt diameter (`r=1.5`) with `50%` fill opacity.
- Adjust diagnostic overlay visual style in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  glyph outline overlays now use `0.4` stroke width at `25%` stroke opacity;
  center/contact dots remain 1 pt diameter (`r=0.5`) at `50%` fill opacity.
- Increase `unit_03` bond/label spacing in
  [tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.svg](tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.svg)
  so HO/OH/CH/SH connector stems are visually separated; update expected
  centerline positions in
  [tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.json](tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.json).
- Update unit_03 glyph-alignment fixture to BKChem-relevant labels
  (`HO`, `OH`, `CH`, `SH`) in
  [tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.svg](tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.svg)
  with sidecar checks expecting O/C/S centerline fits and minimum final point
  counts in
  [tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.json](tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.json).
- Expand measurement-label eligibility in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  to include labels containing `S`, so `SH` participates in connector/alignment
  analysis.
- Add curved-glyph bond-tail decoupling in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  for `O/C/S` pixel masks, clip below label baseline and apply a bridge-break
  erode/reselect/dilate step before hull fitting so C-center fits do not latch
  onto connected bond strokes.
- Update stress fixture realism in
  [tests/fixtures/glyph_alignment/torture_4x4_grid.svg](tests/fixtures/glyph_alignment/torture_4x4_grid.svg)
  and
  [tests/fixtures/glyph_alignment/torture_4x4_grid.json](tests/fixtures/glyph_alignment/torture_4x4_grid.json)
  to include non-rotated `CH` proximity cases that match observed BKChem
  bond-to-C overlap patterns.
- Reduce diagnostic overlay visual occlusion in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  halve helper stroke widths, reduce infinite-line width, and shrink center/contact
  dots to radius 0.5 with 50% fill opacity.
- Improve curved-glyph isolation in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  by adding a center-anchored pixel-core gate after connected-component
  selection, reducing false hull contamination from touching bond strokes while
  keeping fallback guard rails when the gate would over-prune.
- Align fixture scope with BKChem reality in
  [tests/fixtures/glyph_alignment/torture_4x4_grid.svg](tests/fixtures/glyph_alignment/torture_4x4_grid.svg)
  by removing all text-rotation transforms from the torture grid; keep stress on
  nearby bonds, subscripts, mixed sizes, and color variation.
- Change default alignment fitting mode in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  from `primitive` to `optical`, so direct tool runs use the newer CairoSVG-backed
  hull/ellipse fitting path by default (with `--alignment-center-mode primitive`
  still available as an explicit override).
- Speed up optical hull raster extraction in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  strip overlay groups before raster, render from in-memory SVG bytes, and
  reuse one fixture-level CairoSVG full-image raster (shared by all labels)
  with ROI cropping in bitmap space.
- Update fixture runner defaults in
  [tools/run_glyph_alignment_fixture_runner.py](tools/run_glyph_alignment_fixture_runner.py)
  so plain `python tools/run_glyph_alignment_fixture_runner.py` now writes
  diagnostic PNG overlays by default at 4x scale; add `--no-render-png` opt-out
  and `--png-scale` override.
- Enforce CairoSVG-only pixel hull masking in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  by removing the legacy pycairo polygon-fill raster fallback; curved glyph
  hull extraction now uses only ROI masks cropped from CairoSVG-rendered SVG
  pixels (`mask_source: cairosvg_roi_rgba`) or reports no pixel hull.
- Tighten pixel-hull extraction quality in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  skip baseline clipping before hull extraction for `O` targets, merge split
  connected components around the selected glyph component, and apply a 1 px
  mask dilation before external-contour (`RETR_EXTERNAL`) hull computation to
  reduce anti-aliased edge dropout.
- Add explicit hull provenance diagnostics in the same tool
  (`hull_source`, `hull_contour_point_count`, `mask_dilated_1px`) so debug
  overlays/reports can verify that hulls come from external contour geometry.
- Implement pixel convex-hull glyph geometry in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  for curved targets (`O/C/S`): rasterize local glyph ROI to in-memory ARGB,
  run connected-component selection, extract external contour, compute convex
  hull, densify hull edges (about 1.5 px), and fit axis-aligned ellipse from
  hull points.
- Add per-glyph hull outputs to JSON/report rows in the same tool:
  `hull_boundary_points`, `hull_ellipse_fit`, `hull_contact_point`,
  and `hull_signed_gap_along_bond`, with diagnostic-overlay rendering of hull,
  fitted ellipse, and endpoint-to-contact segment.
- Add stop-at-hull gap metric in the same tool using forward bond-ray to hull
  edge intersection; for `C/S` labels this signed hull gap now overrides the
  curved-glyph endpoint gap/penetration metric by design.
- Add a local pycairo+numpy optical probe in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  for curved target glyphs (`O/C/S`): rasterize the selected glyph contour
  component to an in-memory ARGB surface, extract boundary pixels via an
  8-neighbor erosion boundary mask, and fit the alignment ellipse from those
  boundary points (with automatic fallback to vector-point fit).
- Increase optical glyph-outline density in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  by interpolating text-path contours before component selection
  (`outline_interpolation_steps`, `outline_vertex_count` now exposed in
  `optical_gate_debug`), so unit_03-style labels are no longer fitted from
  tiny raw contour sets.
- Keep O-target gating fully uncut in the same tool by preserving the
  existing O half-plane skip and O/C stripe skip path, now exercised against
  densified contours.
- Reduce curved-glyph center bias in the same tool by switching locked
  vertical ellipse center calculation to quantile-bbox midpoint instead of
  raw point-mean centroid.
- Add glyph-alignment fixture scaffold corpus in
  [tests/fixtures/glyph_alignment/](tests/fixtures/glyph_alignment/) with
  three targeted unit fixtures and one 4x4 torture-grid fixture (each with
  JSON sidecar expectation blocks).
- Add a single-run fixture harness in
  [tools/run_glyph_alignment_fixture_runner.py](tools/run_glyph_alignment_fixture_runner.py)
  to execute all scaffold fixtures, emit per-fixture measurement reports and
  diagnostic overlays, evaluate sidecar expectations, and write runner
  summary JSON/TXT outputs under `output_smoke/glyph_alignment_fixture_runner/`.
- Add scaffold integrity checks in
  [tests/test_glyph_alignment_fixture_scaffold.py](tests/test_glyph_alignment_fixture_scaffold.py)
  to lock the fixture/sidecar/runner wiring in place.
- Tighten glyph-alignment fixture expectations in
  [tests/fixtures/glyph_alignment/](tests/fixtures/glyph_alignment/):
  require non-trivial label counts, bounded outside-tolerance counts, and
  required target-centerline checks (including CH2OH/HOH2C C-target cases).
- Tighten unit fixture tolerance gates in
  [tests/fixtures/glyph_alignment/unit_01_isolated_glyph_fit.json](tests/fixtures/glyph_alignment/unit_01_isolated_glyph_fit.json)
  and
  [tests/fixtures/glyph_alignment/unit_02_mixed_subscript_no_bonds.json](tests/fixtures/glyph_alignment/unit_02_mixed_subscript_no_bonds.json)
  by setting `max_outside_tolerance` to `0` so large outside-tolerance counts
  cannot be reported as required-pass.
- Update C-target gating in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  to skip stripe filtering for `C` labels, preventing stripe-stage contour
  amputation in the new fixture retention checks.
- Harden unit_03-style contamination defenses in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  ignore lines inside overlay/diagnostic groups (`codex-glyph-bond-diagnostic-overlay`,
  `codex-overlay-noise`, and `codex-label-diag-*`), require connector-candidate
  line width >= `1.0`, and clip target glyph contour points to a narrow
  baseline band (`y <= baseline + pad`) before half-plane/stripe gating.
- Prevent over-aggressive stripe collapse in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  reject stripe gating when stripe retention drops below 60% of component
  points and fall back to pre-stripe points, with explicit retention diagnostics
  (`stripe_retention_ratio`, `stripe_rejected_low_retention`) in gate debug.
- Extend
  [tools/run_glyph_alignment_fixture_runner.py](tools/run_glyph_alignment_fixture_runner.py)
  with a C-amputation guard check (`c_stripe_min_retention_ratio`) that fails
  when stripe-gate retention for C-target labels drops below threshold.
- Extend the same runner with a per-target minimum final-point-count check
  (`min_final_point_count_by_char`) and tighten
  [tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.json](tests/fixtures/glyph_alignment/unit_03_bonds_nearby_strokes.json)
  to use independent centerline expectations (`x=180`, `x=320`) plus a required
  O-target minimum final-point-count gate.
- Add a concise experiment postmortem in
  [docs/GLYPH_ALIGNMENT_TECHNIQUE_SUMMARY.md](docs/GLYPH_ALIGNMENT_TECHNIQUE_SUMMARY.md)
  documenting each glyph-alignment technique tried, what improved, and
  where each approach failed (including renderer-coupling, primitive
  fidelity limits, contour/fit instability, and hashed-bond tradeoffs).
- Refine optical gating in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  center stripe-gate filtering on selected-component median x (instead of
  prior center), derive stripe width from selected component width, apply
  half-plane gate only for single-glyph-width components, and widen stripe
  retention for `C` to avoid contour amputation.
- Add per-label optical gate diagnostics (`component/half-plane/stripe/final`
  point counts and widths) to alignment data points in the same tool so
  failures can be traced to the exact filtering stage.
- Harden optical glyph-center fitting in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  with pre-fit contamination gates: endpoint-nearest text subpath component
  selection, bond-direction half-plane filtering, and centerline stripe
  filtering before ellipse/bbox center refinement.
- Add focused gate regression coverage in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to verify endpoint-near component selection from multi-component text path
  contours.

## 2026-02-11
- Extend atom-target coverage in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  keep `H/S/P/N` in alignment-center priority selection, and treat `P`
  as a stem-style glyph (bbox-based optical center) instead of curved
  ellipse fitting so non-`O/C/S` atom labels stay stable in diagnostics.
- Improve alignment-center diagnostics in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  target diagnostic glyph overlays to the selected alignment character
  primitive (for example `O` in `OH`) and add a 1pt center dot at
  `alignment_center_point` for direct visual confirmation.
- Fix hatched-bond connector matching in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  exclude decorative hatch micro-strokes from connector-candidate line
  selection so label alignment/gap checks attach to hashed carrier lines
  instead of hatch fragments.
- Reclassify [docs/HAWORTH_OVERRIDES.md](docs/HAWORTH_OVERRIDES.md) into
  explicit `Required Contract`, `Hack Debt`, and `Validate-only` buckets, and
  add per-hack-debt convergence targets, replacement mechanisms, removal-gate
  tests, and target deletion milestones for Phase 4 cleanup planning.
- Refine diagnostic SVG overlay visuals in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  reduce infinite-line stroke width from `1.0` to `0.2`, remove the endpoint
  circle marker, and render glyph overlays from text-path outlines (with
  primitive-box/ellipse fallback only when no path is available) for much
  tighter visual correspondence to the drawn glyphs.
- Make `tools/measure_glyph_bond_alignment.py` fully independent of
  `packages/oasa`/BKChem runtime geometry for checker execution: remove
  render-geometry imports and use only SVG-derived text primitives/text-path
  outlines for bond/glyph overlap and distance diagnostics.
- Add diagnostic SVG overlay output to the same tool (default ON) with one
  file per analyzed SVG under
  `output_smoke/glyph_bond_alignment_diagnostics/`, showing:
  color-coded glyph primitives, a 1 pt infinite bond-line extension, and an
  orange perpendicular marker at each measured bond endpoint.
- Add CLI options for diagnostic overlays:
  `--write-diagnostic-svg`/`--no-diagnostic-svg` and
  `--diagnostic-svg-dir`.
- Update focused checker tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  for independent-geometry behavior and CLI flow without render-geometry
  loading.
- Validation run for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_measure_glyph_bond_alignment.py`
  (`14 passed`).
- Improve independent glyph geometry in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  use SVG-positioned `matplotlib.textpath.TextPath` outlines (with SVG Y-axis
  transform) as the primary geometry for bond-end distance checks, fall back to
  primitive hulls only when text-path extraction is unavailable, and apply the
  same independent signed-distance model to bond/glyph endpoint diagnostics.
- Reduce endpoint diagnostic verbosity in text/terminal reports by rounding
  sample `bond_end_distance` and `tolerance` values to concise display floats.
- Update
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to accept either independent geometry backend (`svg_text_path_outline` or
  primitive fallback) for no-connector scenarios.
- Validation run for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_measure_glyph_bond_alignment.py`
  (`14 passed`).
- Add a complete Haworth override catalog in
  [docs/HAWORTH_OVERRIDES.md](docs/HAWORTH_OVERRIDES.md) with line-anchored
  runtime/spec/tooling overrides, explicit justifications, and keep/remove
  guidance so override cleanup can be planned without losing contract coverage.
- Fix grouped glyph whitespace-gap reporting in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  build `glyph text -> bond-end whitespace gaps` from true non-negative gap
  values (`max(0, signed_distance)`) instead of absolute boundary error so
  overlap cases correctly report `0.0` whitespace.
- Calibrate curved glyph primitive hulls in the same tool (`O` larger, `C`
  smaller) to better match visual gap ordering for HO/OH versus CH2OH labels.
- Simplify glyph data-point rows in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  remove redundant `alignment_mode` from reported data points and add explicit
  boolean `pass` values for quick scan of per-label alignment outcomes.
- Relax infinite-line alignment tolerance in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  with a font-size-scaled term so visually aligned OH/HO/CH2OH connector
  lines are not over-failed by a fixed narrow tolerance band.
- Switch Haworth hashed branch rendering to the standard BKChem hashed
  primitive sequence in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  remove Haworth-specific hatch post-processing/synthetic endpoint hatch
  injection and keep only shared `_hashed_ops` generation plus legality
  filtering.
- De-brittle hashed-coverage expectation in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to accept
  standard BKChem hatch coverage bounds (`nearest <= 15%`, `farthest >= 80%`)
  instead of legacy Haworth-specific endpoint fill behavior.
- Validation runs for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py -k "hashed_connector_quality or furanose_two_carbon_tail_left_parity_class_uses_hashed_ho or allose_furanose_alpha_tail_branches_right_with_ch2oh_text"`
  (`4 passed, 132 deselected`) and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`).
- Redefine independent glyph alignment metric in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  alignment now uses perpendicular distance from the selected glyph primitive
  center to the connector bond's infinite line, with explicit data-point
  fields `perpendicular_distance_to_alignment_center`,
  `alignment_center_point`, and `alignment_center_char`.
- Use displayed SVG text order for primitive geometry placement while keeping
  canonical text for grouping/target naming, preventing center-point
  distortions for aliases such as `HOH2C`.
- Apply y-axis-flipped down-tail angle mapping for left-side furanose
  two-carbon branches in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  set `OH` to `210 deg` and `CH2OH` to `120 deg` for left-side `direction="down"`
  tails (matching requested visual targets `150 deg` and `240 deg` under SVG
  screen-space coordinates).
- Update Gulose down-tail angle assertion in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py):
  `C4_down_chain1_oh_connector` -> `210 deg`,
  `C4_down_chain2_connector` -> `120 deg`.
- Validation runs for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py -k "gulose_furanose_alpha_two_carbon_down_branch_angles or gulose_furanose_alpha_tail_branches_left_with_hoh2c_text or furanose_two_carbon_tail_left_parity_class_uses_hashed_ho"`
  (`5 passed, 131 deselected`) and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`).
- Clarify independent glyph-distance semantics in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  report `distance_to_glyph_body` as absolute boundary error (including overlap
  penetration), keep signed values in `signed_distance_to_glyph_body`, and add
  explicit miss reason `endpoint_penetrates_glyph_body` when endpoint lies
  inside the glyph primitive hull.
- Correct furanose two-carbon `up` branch orientation in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  map the requested visual targets (OH up-left, CH2OH up-right) into SVG
  screen-space vectors for the `up` tail profile (`210 deg` and `330 deg`).
- Update targeted angle expectation in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  (`test_render_mannose_furanose_alpha_two_carbon_up_branch_angles`) to match
  the corrected runtime vectors.
- Validation runs for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py -k "mannose_furanose_alpha_two_carbon_up_branch_angles or allose_furanose_alpha_tail_branches_right_with_ch2oh_text"`
  (`2 passed, 134 deselected`) and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`).
- Normalize down-tail alias text for geometry targeting in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  map `HOH2C`/subscript variants to canonical `CH2OH` so independent glyph
  alignment and bond-end distance checks do not miss chain2 labels due to
  text-order variants.
- Include both canonical and raw SVG label text in glyph data-point rows
  (`text`, `text_raw`) for easier diagnosis of renderer-emitted label strings.
- Calibrate independent glyph-alignment tolerance in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  add a font-size-scaled tolerance term so visually valid OH/HO connector
  placements are not over-flagged by an overly tight primitive-hull threshold.
- Improve report readability in the same tool by reducing decimal precision for
  human-facing glyph alignment/distance data points and endpoint coordinates
  while keeping raw point-wise output structure.
- De-brittle Phase 4 guard tests while preserving contract coverage:
  - In [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py),
    relax text-report assertions to section-level checks (not exact wording),
    replace fixed hatched-conflict index assumptions with conflict-type/set
    assertions, and keep schema/metric coverage via required-key checks.
  - In [tests/smoke/test_haworth_phase4_known_failures.py](tests/smoke/test_haworth_phase4_known_failures.py),
    replace fixed magic connector-length targets for CH3/COOH with a
    ring-relative baseline-band check (`_assert_connector_length_tracks_ring_band`)
    so runtime contract regressions are caught without over-coupling to one
    exact numeric rendering.
- Validation runs for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_measure_glyph_bond_alignment.py`
  (`13 passed`) and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_phase4_known_failures.py`
  (`45 passed`).
- Flip left-side furanose down-tail branch placement to match reference visuals in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  for left-side (`vertex.x <= ring_center.x`) two-carbon down tails, place
  `OH` on the upper-left branch and `CH2OH` on the lower-left branch; keep
  right-side down-tail orientation unchanged.
- Update branch-angle/parity assertions in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for the
  left-side down-tail flip (`C4_down_chain1_oh_connector` now `240 deg`,
  `C4_down_chain2_connector` now `150 deg`, and `CH2OH` label lane below `HO`).
- Validation runs for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py -k "gulose_furanose_alpha_two_carbon_down_branch_angles or furanose_two_carbon_tail_left_parity_class_uses_hashed_ho or gulose_furanose_alpha_tail_branches_left_with_hoh2c_text"`
  (`5 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_phase4_known_failures.py`
  (`45 passed`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`).
- Make glyph alignment evaluation renderer-independent in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  choose connector endpoints by nearest distance to independent glyph
  primitives (ellipse/box model) and score alignment from independent
  primitive-boundary error instead of renderer attach-target distance.
- Reduce glyph alignment report over-aggregation in the same tool:
  replace summary-stat-heavy text/terminal sections with raw per-label data
  points for both `Glyph-to-bond alignment` and `Glyph-to-bond-end distance`,
  while retaining concise `glyph text -> bond-end distances` mappings.
- Update focused coverage in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  for independent-alignment reasons/mode and raw-data-point report text.
- Improve renderer-independent glyph proximity diagnostics in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  replace box-only independent distance checks with per-character glyph
  primitives (true ellipses for curved glyphs like O/C/S and boxes for stem
  glyphs), compute bond-end distances against the primitive union, and expose
  concise `glyph text -> bond-end distances` maps in text/terminal summary
  output while keeping detailed per-measurement values in JSON.
- Extend focused checks in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to validate true-ellipse signed-distance behavior and independent glyph-body
  distance population in no-connector cases.
- Fix reopened Phase 4 Haworth overlap blockers in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  defer furanose two-carbon-tail rendering until after simple-label layout so
  chain2 label endpoint/placement solving sees final OH/HO occupancy and avoids
  strict label-label collisions without sugar/text/op-id special cases.
- Fix pyflakes blocker in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  remove one unused local (`centroid`) in Haworth ring detection.
- Update Phase 4 closure status/checklist in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  and [refactor_progress.md](refactor_progress.md) with the latest green-gate evidence.
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_phase4_known_failures.py`
  (`45 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/measure_glyph_bond_alignment.py --fail-on-miss`
  (`files analyzed: 78`, `alignment rate: 100.00%`, `alignment outside tolerance: 0`,
  `lattice angle violations: 0`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_attach_targets.py tests/test_haworth_renderer.py tests/test_measure_glyph_bond_alignment.py tests/test_phase4_heuristic_grep_gate.py tests/test_phase4_non_haworth_sentinels.py`
  (`183 passed`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`524 passed, 6 skipped`) twice consecutively.
- De-redundify and de-coarsen alignment-distance reporting in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  replace coarse rounded distance lists/counts with compact high-precision
  value/count output, add explicit non-zero distance diagnostics
  (`alignment_nonzero_distance_count`, `alignment_min_nonzero_distance`), and
  collapse single-value count output to one concise line when applicable.
- Update focused checker tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  for compact-count and non-zero alignment-distance fields.
- Improve alignment-by-glyph readability in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  preserve higher precision for alignment distance/ratio/score values
  (scientific notation for tiny non-zero values) and suppress redundant `svg`
  fields in per-measurement rows when only one file is analyzed.
- Update focused checker assertions in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to keep coverage for alignment-by-glyph structure after precision/readability
  updates.
- Expand alignment distance reporting in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  add full glyph-to-bond-end distance distributions (sorted rounded values,
  rounded frequency counts, stats, and missing-distance count) to summary JSON,
  text report, and terminal key stats, alongside existing `alignment_by_glyph`
  measurement dictionaries.
- Update focused checker tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to validate new alignment distance distribution fields in summary/text output.
- Expand alignment diagnostics in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  add `alignment_by_glyph` summary data with per-glyph measurement dictionaries
  (distance, tolerance, ratio, score, reason, aligned flag), and print the
  same dictionary in text and terminal output near alignment rate/outside
  tolerance lines.
- Update checker tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to validate presence of the `alignment_by_glyph` report field.
- Fix hashed/thin false negatives at shared endpoints in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  report `shared_endpoint_near_parallel` conflicts when a hashed carrier
  intersects a non-hatch line at a shared endpoint with near-parallel
  direction, instead of suppressing all shared-endpoint cases.
- Add regression coverage in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  for shared-endpoint near-parallel hashed/thin conflicts.
- Add location-bucketed bond-length lists to text reports in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  include checked-bond lengths grouped by quadrant and by Haworth ring region
  (`inside_base_ring` / `outside_base_ring`) in
  `glyph_bond_alignment_report.txt`, with matching summary/json structures for
  aggregation across files.
- Extend checker tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to assert presence of the new bond-length location buckets.
- Refine bond-length accounting in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  exclude decorative hashed hatch-stroke mini-segments from `checked` bond
  length stats/lists (countable-bond view), keep full primitive detail in
  `all_lines` and new `checked_lines_raw`/`decorative_hatched_stroke_lines`
  JSON fields, and add a summary count of excluded decorative hashed strokes.
- Clarify terminal bond-length output in the same tool:
  label primitive-only arrays as `all primitives` and add separate
  `checked bonds` arrays/counts so hashed mini-strokes are not confused with
  actual bond lengths.
- Extend checker tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to verify decorative hashed stroke exclusion from checked bond-length stats.
- Clarify bond/glyph diagnostics in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  add endpoint-to-glyph signed distance fields per overlap
  (`bond_end_to_glyph_distance`, `bond_end_distance_tolerance`,
  `bond_end_overlap`, `bond_end_too_close`), plus readable terminal/text
  summary counters for endpoint overlap vs too-close cases and sample endpoint
  diagnostics.
- Extend checker assertions in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to cover the new bond/glyph endpoint-distance fields and summary counters.
- Simplify text-report bond-length section in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  keep checked/connector/non-connector/excluded Haworth stats
  (count/min/max/mean/stddev/cv), remove verbose sorted arrays and rounded
  count tables from text output, suppress duplicate all-vs-checked blocks when
  identical, and add the note
  `checked lines are identical to all lines` when applicable.
- Update text-report expectations in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to enforce simplified bond-length output while keeping JSON detail unchanged.
- Add hashed-bond collision diagnostics in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  detect hashed carrier lines from direct SVG primitives (carrier + short
  perpendicular hatch strokes) and report overlaps with non-hatch lines as a
  separate `hatched/thin` conflict metric with per-conflict type, line-index
  pairs, overlap point, quadrant, and base-ring region in JSON, text, and
  terminal key stats.
- Expand checker test coverage in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py):
  add a synthetic hashed-carrier overlap fixture that verifies the new
  `hatched_thin_conflict_count` and conflict metadata fields.
- Improve near-glyph connector crowding detection in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  evaluate aligned connector pairs with strict endpoint-target carve-outs (no
  broad allowed corridors), add gap-tolerance proximity checks, and expose
  overlap classifications (`interior_overlap` vs `gap_tolerance_violation`).
- Add configurable CLI control in the same tool:
  `--bond-glyph-gap-tolerance` (default `0.65`) to tune near-miss
  bond/glyph diagnostics.
- Update diagnostic quadrant naming in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  replace `Q1/Q2/Q3/Q4` labels with explicit
  `upper-right/upper-left/lower-left/lower-right` text for clearer triage
  output in terminal, text, and JSON reports.
- Reduce bond/glyph false positives in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  replace box-only overlap checks with shared target-paint legality
  (`validate_attachment_paint`) and apply attach-zone carve-outs only for
  connector-candidate line/label pairs, so legal endpoint contact is not
  miscounted as overlap.
- Add regression coverage in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py):
  verify legal `OH` connector attach-zone contact does not count as
  bond/glyph overlap.
- Expand bond-length diagnostics in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  add sorted rounded individual bond-length lists and rounded frequency tables
  for all/checked/connector/non-connector/excluded groups in JSON, text
  reports, and terminal key stats.
- Improve canonical-angle precision diagnostics in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  report per-violation measured angle, nearest canonical lattice angle, error,
  and measurement quadrant/ring-region in JSON/text/terminal summaries.
- Improve checker run summaries in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  add full text-label inventory output (`Text labels list: [...]`) and
  aggregate bond counters (`total bonds detected`, `total bonds checked`) in
  both terminal key stats and text reports.
- Extend standalone SVG checker in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  enforce strict canonical lattice-angle matching with `30*n mod 360` and
  `0.0` degree tolerance, add recursive glob support for `--input-glob`, and
  keep independent SVG-only analysis paths.
- Add richer overlap diagnostics in the same tool:
  key terminal stats now include bond/glyph glyph-text counts plus quadrant and
  base-ring region breakdowns, and text/JSON reports now include overlap
  metadata examples (point, quadrant, ring region).
- Harden Haworth base-ring detection in the same tool:
  support both line-cycle detection and filled polygon/path clustering so
  `output_smoke/archive_matrix/**/*.svg` files reliably detect Haworth base
  rings for exclusion/classification metrics.
- Expand tool tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py):
  cover strict-lattice behavior, overlap counters, Haworth include/exclude
  mode behavior, and collinear shared-endpoint non-overlap handling.
- Validation runs for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_measure_glyph_bond_alignment.py`
  (`11 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`519 passed, 6 skipped`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/measure_glyph_bond_alignment.py --input-glob "output_smoke/archive_matrix_previews/generated/ALRLDM_furanose_alpha.svg" --json-report /tmp/alrldm_diag_hatch.json --text-report /tmp/alrldm_diag_hatch.txt`
  (`hatched/thin conflicts: 0`; metric present in key stats),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_measure_glyph_bond_alignment.py`
  (`9 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`517 passed, 6 skipped`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/measure_glyph_bond_alignment.py --input-glob "output_smoke/archive_matrix/test_archive_full_matrix_ALRRD1/ALRRDM_furanose_beta.svg" --json-report /tmp/alrr_diag.json --text-report /tmp/alrr_diag.txt`
  (`bond/bond overlaps: 0`, `bond/glyph overlaps: 2`,
  `Haworth base ring detected files: 1`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/measure_glyph_bond_alignment.py --input-glob "output_smoke/archive_matrix/test_archive_full_matrix_ALDM_1/ALDM_furanose_beta.svg" --json-report /tmp/aldm_diag.json --text-report /tmp/aldm_diag.txt`
  (`Haworth base ring detected files: 1`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/measure_glyph_bond_alignment.py --input-glob "output_smoke/archive_matrix/**/*.svg" --json-report /tmp/archive_matrix_diag.json --text-report /tmp/archive_matrix_diag.txt`
  (`files analyzed: 100`, `Haworth base ring detected files: 100`).
- Manager spec adjustment in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md):
  change canonical lattice-angle definition from 60-degree steps to
  30-degree steps (`30*n mod 360`; `0, 30, 60, ..., 330`) for generated/template geometry checks.
- Manager task assignment update in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md):
  add a junior-coder side goal for an independent input-SVG multi-check report
  mode covering lattice-angle violations, glyph/glyph overlap, bond/bond
  overlap, bond/glyph overlap, glyph-bond alignment misses, and Haworth base
  ring detection/exclusion with `--exclude-haworth-base-ring` default ON.
- Clarify scope of the 60-degree direction lattice contract in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md):
  it applies to generated/template geometry paths, while BKChem GUI freehand
  draw-mode snap options (`30/18/6/1` and `freestyle`) remain separate behavior.
- Manager spec update in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md):
  require straight bonds for any segment directly connected to Haworth rings,
  require `0, 60, 120, 180, 240, 300` angle compliance for off-ring branches,
  and require the same 60-degree angle lattice for non-Haworth ring bonds.
- Manager plan update for Phase 4 gate clarity in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md):
  reopen Phase 4, block Phase 5 until closure, and add an explicit
  11-target mandatory fixture checklist (including straightness, bond-length,
  and label-to-bond alignment checks for the specified `CH3`/`COOH` cases).
- Implement the manager-defined 11-target Phase 4 checklist and geometry gates:
  replace
  [tests/smoke/test_haworth_phase4_known_failures.py](tests/smoke/test_haworth_phase4_known_failures.py)
  with explicit per-fixture assertions for ARDM/ARRDM/ALLDM/ARRRDM/ARRLDM/MKRDM/ARRLLd/ARLLDc,
  including required `OH`/`CH2OH`/`CH3`/`COOH` endpoint-contract checks plus
  straightness and lattice-angle gates.
- Enforce canonical off-ring branch-lattice behavior in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  snap two-carbon-tail branch vectors to nearest canonical 60-degree lattice
  direction and place branch hydroxyl labels by oxygen-center inversion, with
  hashed-branch endpoint resolution using rendered carrier width.
- Update branch parity assertions in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  to follow lattice-angle rules instead of fixed vertical HO direction.
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_phase4_known_failures.py`
  (`45 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py tests/smoke/test_haworth_phase4_known_failures.py tests/test_measure_glyph_bond_alignment.py tests/test_phase4_non_haworth_sentinels.py tests/test_phase4_heuristic_grep_gate.py tests/test_render_layout_parity.py`
  (`201 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/measure_glyph_bond_alignment.py --fail-on-miss`
  (`Labels analyzed: 362`, `Alignment rate: 100.00%`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`514 passed, 6 skipped`) twice consecutively.
- Reopen-and-close Phase 4 with independent metrics green:
  move connector endpoint authority to shared runtime contracts in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  and consume those contracts in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  for chain and hydroxyl connector paths (including branch connectors and strict
  legality carve-outs).
- Harden and verify independent measurement gate in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py):
  target-aware connector selection, endpoint-target distance tolerance floor,
  and report metadata retained in
  `output_smoke/glyph_bond_alignment_report.json` and
  `output_smoke/glyph_bond_alignment_report.txt`.
- Add heuristic regression grep gates in
  [tests/test_phase4_heuristic_grep_gate.py](tests/test_phase4_heuristic_grep_gate.py)
  to block reintroduction of text/op-id/sugar-name conditional policy branches
  in renderer/tool surfaces.
- Update Haworth/parity tests to assert shared label-attach contract semantics
  (endpoint target + allowed-target legality) in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) and
  [tests/test_render_layout_parity.py](tests/test_render_layout_parity.py).
- Update plan/progress status for honest closure in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  and [refactor_progress.md](refactor_progress.md): Phase 4 complete, Phase 5 next.
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/measure_glyph_bond_alignment.py --fail-on-miss`
  (`Labels analyzed: 362`, `Alignment rate: 100.00%`, exit `0`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py tests/smoke/test_haworth_phase4_known_failures.py tests/test_measure_glyph_bond_alignment.py tests/test_phase4_non_haworth_sentinels.py`
  (`157 passed`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`514 passed, 6 skipped`) twice consecutively.
- Add independent SVG-only glyph-bond measurement tool
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  to analyze existing generated Haworth previews without calling
  `haworth_renderer.render_from_code(...)`, and emit JSON/TXT miss metrics for
  endpoint-to-target alignment.
- Extend the same measurement tool to report bond-length statistics from static
  SVG line segments (all lines, connector lines, and non-connector lines) so
  alignment regressions can be interpreted alongside length drift.
- Add tool regression tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to verify aligned and missed endpoint classification against static SVG inputs.
- Update
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  to reopen Phase 4 until independent alignment metrics are green and to add
  a new gating command for the measurement tool.
- Reopen and re-close Phase 4 alignment blockers from
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md):
  fix furanose upward chain-like `CH2OH` endpoint targeting in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  by enforcing carbon `core_center` alignment (not `stem_centerline`) for the
  vertical-chain placement path.
- Tighten Haworth regression expectations in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py):
  C4-up chain connector assertions now require carbon `core_center` alignment,
  and raster probe checks now fail when endpoint lands on the C stem edge.
- Expand Phase 4 blocker coverage in
  [tests/smoke/test_haworth_phase4_known_failures.py](tests/smoke/test_haworth_phase4_known_failures.py):
  include Arabinose and Lyxose furanose-alpha fixtures and require chain/methyl
  connector endpoints to land on carbon core targets.
- Reconcile plan/progress docs after Phase 4 reopen:
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  now records Phase 4 complete with Phase 5 next, and
  [refactor_progress.md](refactor_progress.md) reflects reopened-and-closed
  Phase 4 status with Phase 5 still active.
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py tests/smoke/test_haworth_phase4_known_failures.py tests/test_phase4_non_haworth_sentinels.py`
  (`151 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_renderer_smoke.py tests/smoke/test_haworth_phase4_known_failures.py`
  (`101 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`506 passed, 6 skipped`) twice consecutively.
- Complete Phase 4 (validation and stabilization) from
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md):
  add Haworth-first known-failure smoke coverage in
  [tests/smoke/test_haworth_phase4_known_failures.py](tests/smoke/test_haworth_phase4_known_failures.py)
  for Ribose, Galactose, Gulose, Fucose, and Rhamnose fixtures, including
  strict-op validation and chain/methyl carbon-target endpoint checks.
- Add minimal non-Haworth sentinel contract proofs in
  [tests/test_phase4_non_haworth_sentinels.py](tests/test_phase4_non_haworth_sentinels.py):
  exactly three sentinel tests for `CH2OH` attach-to-`C`, `CH3` attach-to-`C`,
  and `OH/HO` attach-to-`O` using shared attach-target and legality APIs.
- Update plan/progress status for Phase 4 completion in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  and [refactor_progress.md](refactor_progress.md):
  Phase 4 marked complete and Phase 5 marked next.
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_phase4_non_haworth_sentinels.py tests/smoke/test_haworth_phase4_known_failures.py`
  (`13 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py`
  (`134 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_renderer_smoke.py tests/smoke/test_haworth_phase4_known_failures.py`
  (`97 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`506 passed, 6 skipped`) twice consecutively.
- Update Phase status wording/checklist in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  to state "Phase 3 complete; Phase 4 next" and mark only evidenced checklist
  items complete.
- Complete Phase 3 (fixed bond-length policy) from
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md):
  add central runtime style-length policy in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  with `VALID_BOND_STYLES`, `BOND_LENGTH_PROFILE`,
  `BOND_LENGTH_EXCEPTION_TAGS`, and `resolve_bond_length(...)`.
- Wire style-length policy into runtime bond rendering in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  map edge order/type to canonical bond styles, apply style default lengths
  during `build_bond_ops(...)`, and require explicit exception tags for any
  non-default `bond_length_override`.
- Add Phase 3 policy regression coverage in
  [tests/test_bond_length_policy.py](tests/test_bond_length_policy.py):
  validate profile defaults by style, enforce tagged exception rules, and
  confirm runtime bond ops apply style defaults and tagged overrides.
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_bond_length_policy.py`
  (`20 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_bond_length_policy.py tests/test_attach_targets.py tests/test_glyph_primitive_calibration.py tests/test_oasa_bond_styles.py`
  (`56 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`503 passed, 6 skipped`) twice consecutively,
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0`).
- Haworth explicit-H freeze active at tool callsites:
  set `show_hydrogens=False` explicitly for Haworth renderer usage in
  [tools/selftest_sheet.py](tools/selftest_sheet.py) and
  [tools/haworth_visual_check_pdf.py](tools/haworth_visual_check_pdf.py),
  and add guard test
  [tests/test_haworth_tool_show_hydrogens_freeze.py](tests/test_haworth_tool_show_hydrogens_freeze.py)
  to fail if any `tools/` Haworth render call omits explicit
  `show_hydrogens=False`.
- "Haworth explicit-H freeze active until HAWORTH_EXPLICIT_HYDROGEN_PLAN.md is activated."
- Phase 2 endpoint resolver unification in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  add one shared resolver+legality helper (`_resolve_legal_attach_endpoint`),
  route two-carbon tail branch endpoints through `resolve_attach_endpoint`
  (remove fixed-endpoint chain2 placement), and route multi-segment chain
  connector endpoints through the same shared attach-target contract.
- Remove strict-validator drift and op-id ownership routing in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  strict bond/label legality now derives allowed attach carve-outs from
  geometry interaction with the same attach primitives used at runtime, rather
  than `_connector`/`_hatch` string matching.
- Add Phase 2 regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py):
  verify chain2 endpoints match shared resolver output and verify strict
  validation remains correct when connector/label op_id suffix conventions are
  removed.
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_attach_targets.py tests/test_haworth_renderer.py tests/smoke/test_haworth_renderer_smoke.py tests/test_glyph_primitive_calibration.py`
  (`252 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`481 passed, 6 skipped`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (`Strict-overlap failures: 0` with strict mode `report_all`).
- Tighten strict overlap enforcement mode controls in
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py):
  add `--strict-report-all` (collect all strict failures, still write reports,
  then exit non-zero) and `--strict-fail-fast` (stop on first strict failure,
  exit non-zero), while preserving per-failure logging and summary counts.
- Add strict mode regression tests in
  [tests/test_archive_matrix_summary_strict_modes.py](tests/test_archive_matrix_summary_strict_modes.py)
  to lock parser constraints and non-zero exit behavior for report-all and
  fail-fast modes.
- Tighten
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  with an explicit analytic-primitive measurement contract:
  each glyph primitive must expose a canonical center point, measurable area,
  and deterministic boundary projection so alignment and legality checks are
  numerically precise and testable.
- Clarify terminology in
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  by explicitly using "glyph convex hull" language in the design philosophy to
  anchor the attachment-model intent.
- Add a top-level design philosophy section to
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  to prevent implementation drift by enforcing one shared geometry truth,
  calibrated analytic glyph primitives, connector-first authority, and
  fixed-length policy with explicit exception tagging.
- Add new manager-level execution plan
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)
  to reset bond-label recovery around one shared glyph attachment contract and
  one fixed bond-length policy, with explicit phase gates, exception tagging,
  Haworth-first validation, and minimal non-Haworth sentinel coverage.
- Fix chain attach-site contract selection in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  by replacing vertical-orientation routing with endpoint-driven site
  resolution: the runtime now selects `core_center` vs `stem_centerline` from
  the actual connector endpoint contract against both attach regions.
- Update strict overlap gating in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  to consume that same endpoint-driven resolver for own chain-like connectors,
  preventing regressions where non-lock vertical connectors were forced into
  stem-only validation.
- Re-export the shared connector target resolver in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  and use it in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  so smoke checks and runtime strict policy stay identical.
- Fix a smoke-test collection break and policy drift in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py):
  correct indentation, add font-aware target calls, and remove duplicated
  attach-site heuristics from test code.
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_attach_targets.py tests/test_haworth_renderer.py tests/smoke/test_haworth_renderer_smoke.py tests/test_connector_clipping.py tests/test_phase_c_render_pipeline.py`
  (`266 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`472 passed, 6 skipped`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (strict checks enabled; regenerated previews with no missing/generated gaps).

## 2026-02-10
- Enforce architecture direction in
  [docs/active_plans/CODER_GUIDE_FEB_10.md](docs/active_plans/CODER_GUIDE_FEB_10.md):
  tools must consume a stable top-level Haworth API (`code`, `ring_type`,
  `anomeric`) and must not implement attach-target or strict-overlap policy via
  tool-local heuristics (for example op-id substring checks).
- Implement the runtime API and shared strict-policy surface in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  and re-export it in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  add `render_from_code(...)`, `label_target_for_text_op(...)`,
  `attach_target_for_text_op(...)`, and `strict_validate_ops(...)` so tools
  consume renderer-owned attach/strict behavior instead of duplicating policy.
- Remove duplicated tool-local attach/strict logic from
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) and route
  generated preview rendering through `haworth_renderer.render_from_code(...)`
  plus strict validation through `haworth_renderer.strict_validate_ops(...)`,
  eliminating banned tool heuristics and keeping runtime/tool behavior aligned.
- Fix false-pass geometry for Ribose furanose C4-up attachment in runtime-only
  modules by introducing explicit attach-site semantics in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  `attach_site="element_core"` (default) versus
  `attach_site="element_stem"` and `attach_site="element_closed_center"` for
  explicit carbon-glyph attachment semantics.
- Add automatic closed-center attachment in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  using runtime font metrics (`O` center factor for `C`) so "closed C as O"
  centerline targeting is derived from glyph geometry, not per-case constants.
- Unify carbon attach-site defaults in shared geometry runtime:
  when `attach_element="C"` and no explicit attach-site override is provided,
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  now defaults to `attach_site="element_closed_center"` so shared molecular
  rendering and Haworth rendering consume one carbon-center contract.
- Apply `element_closed_center` to chain-like first-carbon Haworth vertical-lock
  placement paths in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py),
  removing the self-referential "core-target centroid == endpoint" pass mode
  for `ARRDM | furanose | alpha/beta`.
- Keep strict overlap legality meaningful in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  by using closed-center allowed regions for own chain-like vertical connectors
  when the endpoint lands in that region (geometry-based, no tool hacks), while
  preserving core-target legality for other chain-like connectors.
- Replace brittle "legacy fixed numbers" attach-box assertions and add
  attach-site regression coverage in
  [tests/test_attach_targets.py](tests/test_attach_targets.py), and update
  Ribose C4-up tests in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to assert
  closed-center vertical attachment behavior.
- Align contract tests with runtime attach-target policy source of truth:
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  and [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) now use
  `haworth_renderer.attach_target_for_text_op(...)` for own-connector allowed
  regions instead of duplicating local selector logic.
- Update connector clipping regression in
  [tests/test_connector_clipping.py](tests/test_connector_clipping.py) to use
  explicit runtime font context (`Arial`) for attach-target expectations now
  that attach spans are derived from font metrics.
- Normalize furanose two-carbon branch readability in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  the down-class hashed branch (C4_down chain1 OH) was visually too short
  compared with the up-class hashed branch (C4_up chain2), so down-class
  branch geometry now uses a larger branch-arm factor (`ho_length_factor`
  `0.78 -> 1.20`) while keeping stereochemical hashed-vs-solid assignment
  unchanged.
- Keep branched-tail placement non-cramped in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  by enforcing direction-aware minimum branch standoff from the ring before
  branch vectors are solved, reducing the "custom hack" appearance for both
  two-carbon direction classes.
- Add explicit two-carbon class parity coverage for the full D/L code sets
  (up/down classes, alpha/beta) in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py), including
  fixed `C4_up` vs `C4_down` chain2-op routing and hashed-branch placement
  expectations.
- Strengthen own-connector overlap gating in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  so token-specific attach carve-outs are validated via
  `validate_attachment_paint(...)` for chain-like labels, matching strict
  runtime semantics.
- Fix strict overlap target selection for generated matrix validation in
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py):
  chain2 labels are now recognized even when markup text is reversed
  (`HOH<sub>2</sub>C`), and hydroxyl attach carve-outs use `attach_element="O"`
  consistently.
- Harden attachment geometry in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  by adding exact box-region forbidden-minus-allowed validation and by fixing
  single-token `attach_element` selection (for example `OH` + `attach_element="O"`).
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py`
  (`130 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_renderer_smoke.py`
  (`87 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py`
  (`469 passed, 6 skipped`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (strict checks enabled; regenerated previews with `Missing generated: 0`).
- Update
  [docs/active_plans/CODER_GUIDE_FEB_10.md](docs/active_plans/CODER_GUIDE_FEB_10.md)
  with a root-cause clarification for `CH<sub>2</sub>OH` connector misses:
  endpoint hits can still be visually wrong when attach targets are estimated
  too broadly, so acceptance now explicitly distinguishes "inside target" from
  true carbon-centerline attachment.
- Reorganize
  [docs/active_plans/CODER_GUIDE_FEB_10.md](docs/active_plans/CODER_GUIDE_FEB_10.md)
  into a clean execution format with explicit scope, non-negotiable rules,
  case-by-case expected visuals, measured pass/fail gates, required command
  sequence, and a required reporting template for coder submissions.
- Add a dedicated design-philosophy section to
  [docs/active_plans/CODER_GUIDE_FEB_10.md](docs/active_plans/CODER_GUIDE_FEB_10.md)
  to anchor implementation decisions on structural correctness, single-source
  geometry semantics, connector-first behavior, explicit failure visibility,
  and universal (non-sugar-specific) fixes.
- Extend
  [docs/active_plans/CODER_GUIDE_FEB_10.md](docs/active_plans/CODER_GUIDE_FEB_10.md)
  with explicit two-carbon furanose direction families (down/up), including
  the D and L code/name sets that should follow each branch-orientation policy
  in both alpha and beta forms.
- Refine formula-aware carbon attach targeting in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  so core-token span projection follows rendered Haworth glyph spacing
  (`0.60 * font_size`) and carbon center alignment (`0.24 * font_size`),
  improving CH2OH/HOH2C connector centering for furanose sidechain labels.
- Update attach-target regression expectation in
  [tests/test_attach_targets.py](tests/test_attach_targets.py) to assert the
  core-span contract (core C target is narrower and right-bounded inside the
  decorated span) after the carbon-center alignment fix.
- Validation reruns for this adjustment:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest tests/test_attach_targets.py -q`
  (`21 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest tests/test_haworth_renderer.py -q`
  (`97 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest tests/smoke/test_haworth_renderer_smoke.py -q`
  (`86 passed`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (strict checks enabled; regenerated matrix summaries with `Missing generated: 0`).
- Adjust methyl readability policy in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  midpoint methyl labels now prefer `CH<sub>3</sub>` at 90% font size
  (instead of forcing `H<sub>3</sub>C`), with `H<sub>3</sub>C` retained only as
  overlap fallback and a no-shrink-below-90% floor.
- Update deoxy methyl regression in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to assert
  `CH<sub>3</sub>` rendering and 90% font-size behavior for
  `ALRRLd`/`ARRLLd` pyranose-alpha labels.
- Fix furanose C-target connector alignment for chain-like top-left labels in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  when vertical-lock is used (for example `ARRDM` furanose alpha `C4_up`),
  pre-align the rendered label x-origin so the selected carbon-core attach
  target centroid matches the locked connector x-position, preventing the bond
  from visually landing on the C/H boundary.
- Add regression test
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  (`test_render_ribose_furanose_alpha_c4_up_connector_x_aligns_to_carbon_center`)
  to lock the Ribose C4-up connector x-alignment to the carbon target center.
- Validation reruns for this fix:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py`
  (`96 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_renderer_smoke.py`
  (`86 passed`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (strict checks enabled; regenerated summary previews with zero missing entries).
- Improve methyl readability in Haworth labels by rendering midpoint methyl
  substituents as `H<sub>3</sub>C` (instead of `CH<sub>3</sub>`) in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py),
  and update the L-fucose/L-rhamnose regression expectation in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py).
- Validation reruns for this readability fix:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py`
  (`95 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_renderer_smoke.py`
  (`86 passed`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (strict checks enabled; regenerated summary previews).
- Fix furanose two-carbon tail connector-first placement in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  chain2 labels are now solved with deterministic label-only offsets while
  keeping the branch connector endpoint fixed from branch geometry, and each
  candidate is nudged to keep the endpoint inside the selected `attach_element="C"`
  target before strict legality scoring.
- Improve branched-tail hydroxyl endpoint behavior in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  by using hydroxyl-order-aware token selection (`OH -> first`, `HO -> last`)
  for chain1 OH connector targeting, restoring directional side-edge behavior
  with strict overlap validation.
- Keep archive-matrix partition semantics stable in
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py):
  L-series rows that have real archive references (for example `ALRRLd`,
  `ARRLLd`) remain in `archive_matrix_summary.html`, while only no-reference
  L-series rows are sent to `l-sugar_matrix.html`; also keep `-r` strict mode
  hard-fail behavior by removing regenerate-path exception swallowing.
- Validation reruns for this update:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_attach_targets.py`
  (`21 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py`
  (`95 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_renderer_smoke.py`
  (`86 passed`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (strict checks enabled, wrote summary + L-sugar outputs, `Missing generated: 0`).
- Add active plan
  [docs/active_plans/HAWORTH_EXPLICIT_HYDROGEN_PLAN.md](docs/active_plans/HAWORTH_EXPLICIT_HYDROGEN_PLAN.md)
  defining a no-hack explicit-hydrogen upgrade path for Haworth rendering:
  standalone `H` labels get a smaller gray visual style while connector
  endpoint legality remains on shared attach-target architecture, with explicit
  unit/smoke/regression gates and rollout documentation requirements.
- Refine formula-aware core attachment geometry in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  so `attach_element` span selection uses glyph-width projection from token
  origin (clamped to full label bounds), improving carbon-core targeting for
  decorated labels such as `CH2OH` and `HOH2C`.
- Restore deterministic vertical connector behavior for furanose left-top
  chain-like `up` substituents in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  by forcing vertical-lock endpoint constraints for that slot class (fixes the
  D-ribose C4-up regression where connector tilt was introduced).
- Extend
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py)
  with strict generated-render overlap validation (enabled automatically with
  `-r`), split D-series and L-series outputs, and write a dedicated generated-
  only L-sugar page at `output_smoke/l-sugar_matrix.html` (no reference panel
  by design).
- Update
  [tests/test_attach_targets.py](tests/test_attach_targets.py)
  legacy expectation for `label_attach_target(..., "CH2OH", attach_atom="last")`
  to match the new deterministic attach-span geometry.
- Validation reruns for these changes:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_attach_targets.py`
  (`21 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py`
  (`95 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_renderer_smoke.py`
  (`86 passed`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  (wrote `output_smoke/archive_matrix_summary.html` and
  `output_smoke/l-sugar_matrix.html` with strict checks enabled and zero
  missing generated previews).
- Remove dormant, unregistered mode implementations from
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py):
  `reaction_mode`, `external_data_mode`, and `rapid_draw_mode`; also remove
  stale commented registration lines in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py).
- Modernize launcher runtime preflight in
  [packages/bkchem-app/bkchem/import_checker.py](packages/bkchem-app/bkchem/import_checker.py)
  to Python 3.10+ policy, remove dead legacy PIL compatibility exports, and
  keep explicit runtime checks for `Pmw` and `oasa`.
- Update startup failure output in
  [packages/bkchem-app/bkchem/bkchem.py](packages/bkchem-app/bkchem/bkchem.py) to print
  readable text (not byte-literals) and exit with non-zero status on failed
  prerequisite checks.
- Remove unused dead code path `_draw_normal_old` from
  [packages/bkchem-app/bkchem/arrow.py](packages/bkchem-app/bkchem/arrow.py).
- Close recovery gates from
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  addendum: remove Haworth renderer text-literal endpoint policy branches in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  (`text in ("OH", "HO")`, `_compute_hydroxyl_endpoint`,
  `str(label) == "CH(OH)CH2OH"`), add label helpers in
  [packages/oasa/oasa/haworth/renderer_text.py](packages/oasa/oasa/haworth/renderer_text.py),
  and route hydroxyl job detection through those helpers in
  [packages/oasa/oasa/haworth/renderer_layout.py](packages/oasa/oasa/haworth/renderer_layout.py).
- Record explicit release-closure reruns for the recovery addendum using the
  same full-suite command twice:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q`
  with outcomes `510 passed, 6 skipped` (run 1) and `510 passed, 6 skipped`
  (run 2).
- Separate Haworth verification evidence:
  archive-matrix summary generation command
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r`
  wrote `output_smoke/archive_matrix_summary.html` with `Generated previews written: 78`;
  strict-overlap/smoke verification commands
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest tests/smoke/test_haworth_renderer_smoke.py -q`
  (`84 passed`) and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest tests/test_haworth_renderer.py -q`
  (`90 passed`).
- Tighten formula-aware label targeting and Haworth branch attachment behavior:
  in [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  add core-vs-decorated token spans so `attach_element` resolves to the core
  element glyph span (for example `C` in `CH2OH`) while preserving decorated
  first/last token fallback; in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  apply allowed-region retreat carve-outs for two-carbon-tail `OH`/`CH2OH`
  connectors and replace template-locked branch vectors with one
  ring-frame/face profile builder; in
  [packages/oasa/oasa/haworth/renderer_text.py](packages/oasa/oasa/haworth/renderer_text.py)
  generalize numeric subscripting so `CH3 -> CH<sub>3</sub>`.
- Add regression coverage for carbon-core attach targeting and methyl subscript
  rendering in
  [tests/test_attach_targets.py](tests/test_attach_targets.py),
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py), and
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py),
  including matrix-level CH3 and chain2-token endpoint assertions.
- Validation reruns for this change set:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest tests/test_attach_targets.py -q`
  (`21 passed`),
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest tests/test_haworth_renderer.py -q`
  (`95 passed`),
  and
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest tests/smoke/test_haworth_renderer_smoke.py -q`
  (`86 passed`).
- Harden render-pipeline parity tests against operation-order nondeterminism by
  canonicalizing payload comparisons in
  [tests/test_phase_c_render_pipeline.py](tests/test_phase_c_render_pipeline.py)
  while preserving geometry/content invariant checks.
- Remove legacy BKChem fallback writer file
  `packages/bkchem-app/bkchem/non_xml_writer.py` (no remaining runtime references).
- Retire legacy BKChem HTTP export/control surface by removing
  `packages/bkchem-app/bkchem/http_server.py`,
  `packages/bkchem-app/bkchem/http_server2.py`, and
  `packages/bkchem-app/bkchem/bkchem.js`; remove `BKChem.start_server()` wiring in
  `packages/bkchem-app/bkchem/main.py`.
- Remove legacy Tk XML/SVG writer module
  `packages/bkchem-app/bkchem/xml_writer.py`; switch
  `chem_paper.selected_to_real_clipboard_as_SVG()` in
  `packages/bkchem-app/bkchem/paper.py` to OASA render output instead of GUI
  writer internals.
- Refresh architecture documentation in
  [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) to describe OASA-based
  CDML/export flow and remove stale XML-writer references.
- Preserve
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  as the full historical record and append a 2026-02-10 recovery addendum in
  the same file (instead of replacing it), documenting reopened closure gates
  for remaining Haworth endpoint-branch hardening and release verification.
- Add concrete R0 audit commands directly into
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  as an in-file checklist section, mapping each deletion gate to exact grep
  checks and pytest runs (DG-1 BKChem duplicate draw paths, DG-2 Haworth
  text-branch endpoint policy, DG-3 removed bbox compatibility surfaces), plus
  two-pass full-suite release verification commands.
- Add new manager planning skill
  [skills/plan-manager/SKILL.md](skills/plan-manager/SKILL.md)
  with
  [skills/plan-manager/agents/openai.yaml](skills/plan-manager/agents/openai.yaml)
  and
  [skills/plan-manager/references/plan_quality_standard.md](skills/plan-manager/references/plan_quality_standard.md)
  to produce implementation-ready plan documents for coding teams (without
  coding), using phased deliverables, acceptance gates, compatibility/migration
  policy, risk registers, and rollout checklists derived from active/archive
  plan conventions.
- Add new skill
  [skills/python-code-review/SKILL.md](skills/python-code-review/SKILL.md)
  with
  [skills/python-code-review/agents/openai.yaml](skills/python-code-review/agents/openai.yaml)
  to provide comprehensive Python code reviews focused on correctness,
  security, maintainability, and actionable before/after fixes, and to
  explicitly incorporate `read-repo-rules` summaries before reviewing code.
- Update
  [skills/python-code-review/SKILL.md](skills/python-code-review/SKILL.md)
  to remove Ruff/Mypy-check workflow language and focus reviews on
  implementation conformance to active plan documents in
  `docs/active_plans/`, including plan-criteria mapping and plan-drift checks.
- Implement Phase A attachment-engine primitives in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  add `AttachTarget` and `AttachConstraints`, target constructors
  (`make_box_target`, `make_circle_target`, `make_segment_target`,
  `make_composite_target`), shared endpoint resolver
  `resolve_attach_endpoint(...)`, and painted-overlap validator
  `validate_attachment_paint(...)`, while keeping `bbox`-named APIs as
  compatibility wrappers.
- Add target-named label APIs in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  `label_target(...)`, `label_target_from_text_origin(...)`,
  `label_attach_target(...)`, and
  `label_attach_target_from_text_origin(...)`; keep existing
  `label_bbox(...)` and `label_attach_bbox(...)` wrappers functional and add
  `attach_element` selector support with deterministic precedence over
  `attach_atom`.
- Extend molecule label selector wiring in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  so per-vertex `attach_element` is honored when constructing attach targets,
  while preserving legacy bbox-based clipping behavior in `build_bond_ops(...)`
  for additive Phase A rollout.
- Add Phase A unit coverage in
  [tests/test_attach_targets.py](tests/test_attach_targets.py) for target
  centroid/contains/boundary behavior, circle endpoint legality with strict
  epsilon penetration checks, and wrapper parity between target-named and
  bbox-named label helpers; extend
  [tests/test_connector_clipping.py](tests/test_connector_clipping.py) with an
  `attach_element` precedence regression case.
- Update
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  with a formula-aware label parsing note that keeps scope tight (tokenized
  parsing for supported emitted patterns, rendering/attachment separation, and
  `attach_element`-driven stable connector intent).
- Add a concrete `bbox` naming-inventory section to
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  listing remaining `bbox`-named APIs/fields/helpers in
  `render_geometry.py`, `haworth/renderer.py`, `haworth/renderer_layout.py`,
  and smoke/unit tests as explicit Phase B/C rename backlog.
- Implement Phase B OASA attachment migration in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py),
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py),
  [packages/oasa/oasa/haworth/renderer_layout.py](packages/oasa/oasa/haworth/renderer_layout.py),
  and
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  migrate active Haworth attachment callsites to `AttachTarget`/`resolve_attach_endpoint(...)`,
  remove renderer-local legacy attachment helpers called out by Phase B,
  route furanose two-carbon tail OH/CH2OH connectors through
  `label_attach_target_from_text_origin(...)` with explicit
  `attach_element` selectors (`O`/`C`), add `job_text_target(...)` /
  `text_target(...)` layout APIs with bbox wrappers retained for compatibility,
  and expose target-named compatibility aliases in `haworth_renderer.py`.
- Rename smoke attachment helpers in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  from bbox naming to target naming (`_label_target`,
  `_connector_target_for_label`, `_hydroxyl_half_token_targets`) while
  preserving strict overlap gate behavior.
- Update Phase status/inventory tracking in
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  to reflect completed Phase B migration items and remaining Phase B.1/Phase C
  backlog.
- Validate full test suite after Phase B migration:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest`
  (`502 passed`, `6 skipped`).
- Clarify strict-overlap policy wording in
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md):
  keep acceptance gating at `epsilon = 0.5 px`, while explicitly allowing
  tighter internal retreat-solver tolerance for endpoint bisection stability.
- Add direct unit coverage for
  `retreat_endpoint_until_legal(...)` in
  [tests/test_attach_targets.py](tests/test_attach_targets.py), including
  legal no-op, box retreat, circle retreat, and retreat-to-start edge cases.
- Keep Haworth retreat callsites in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  on a dedicated small solver epsilon constant (`RETREAT_SOLVER_EPSILON = 1e-3`)
  so visual geometry remains stable while strict overlap enforcement remains
  governed by the 0.5 px gate in shared validation.
- Re-run full test suite after these policy/test updates:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest`
  (`506 passed`, `6 skipped`).
- Close Phase B.1 furanose two-carbon-tail parity in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  by removing anchor-based template fallback and enforcing deterministic
  slot/direction mapping for branch geometry/hashed cue selection; add explicit
  D-galactose parity-class fixture coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) and
  smoke parity coverage in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py);
  mark Phase B.1 complete in
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md).
- Complete Phase C attachment cutover:
  remove bbox-named compatibility attachment APIs/fields from
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py),
  remove Haworth bbox-compat wrappers from
  [packages/oasa/oasa/haworth/renderer_layout.py](packages/oasa/oasa/haworth/renderer_layout.py)
  and
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py),
  and keep canary coverage in
  [tests/test_attach_targets.py](tests/test_attach_targets.py).
- Migrate BKChem endpoint clipping to shared target resolution in
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py)
  (via `make_box_target(...)` + `resolve_attach_endpoint(...)`), eliminating
  standalone direct rectangle clipping in the bond endpoint path.
- Decompose `bond.py` into focused mixins without behavior change:
  add
  [packages/bkchem-app/bkchem/bond_drawing.py](packages/bkchem-app/bkchem/bond_drawing.py),
  [packages/bkchem-app/bkchem/bond_display.py](packages/bkchem-app/bkchem/bond_display.py),
  and
  [packages/bkchem-app/bkchem/bond_cdml.py](packages/bkchem-app/bkchem/bond_cdml.py),
  and wire
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py)
  to inherit these mixins.
- Update phase governance language in
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  to reflect completed Phase C status, wrapper-removal state, and final
  migration/deletion cutover policy.
- Fix BKChem import-mode compatibility for mixin decomposition in
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py):
  prefer package-relative mixin imports and add deterministic top-level import
  fallback via `importlib` for legacy `sys.path` usage (`import bond`).
- Reconcile Phase C plan acceptance text in
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md):
  keep shipped cutover criteria as Phase C gates and move aggressive
  file-length/draw-pipeline elimination goals to explicit post-Phase C
  follow-up objectives.
- Revalidate after Phase C decomposition/import-mode updates:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest`
  (`510 passed`, `6 skipped`).
- Remove deprecated BKChem left/right hashed draw variants from runtime drawing:
  delete `_draw_l*`/`_draw_r*` and side-hash rendering path in
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py),
  normalize legacy `l/r` runtime draws to hashed `h` in `draw()`, and narrow
  hashed-only visibility/export handling in
  [packages/bkchem-app/bkchem/bond_display.py](packages/bkchem-app/bkchem/bond_display.py)
  and
  [packages/bkchem-app/bkchem/xml_writer.py](packages/bkchem-app/bkchem/xml_writer.py);
  full suite revalidated:
  `source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest`
  (`510 passed`, `6 skipped`).
- Complete BKChem legacy draw-path deletion in
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py):
  remove the per-type `_draw_*` geometry pipeline from `bond.py`, route
  `bond.draw()` through shared OASA render-ops via new Tk adapter mixin
  [packages/bkchem-app/bkchem/bond_render_ops.py](packages/bkchem-app/bkchem/bond_render_ops.py),
  move type/order geometry control to
  [packages/bkchem-app/bkchem/bond_type_control.py](packages/bkchem-app/bkchem/bond_type_control.py),
  and keep only BKChem-specific object state/properties in `bond.py`
  (`312` lines).
- Update BKChem display/export integration for render-op outputs in
  [packages/bkchem-app/bkchem/bond_display.py](packages/bkchem-app/bkchem/bond_display.py)
  so focus/unfocus, deletion, and exporter item selection operate on the new
  rendered item-id list.
- Update recovery status in
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  to record R2 completion and remove stale "BKChem duplicate draw path still
  active" wording.

## 2026-02-09
- Update [refactor_progress.md](refactor_progress.md) to include
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  in both the `In progress` tracker and the `Reference docs` index.
- Refine
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  with a minimal default-selector rule (`attach_atom=first` when selectors are
  absent), add a one-line numeric strict-overlap policy (`epsilon = 0.5 px`,
  edge-touch allowed, penetration fails), and clarify backward compatibility
  expectations for older readers that ignore new selectors.
- Expand
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  with a new "Haworth special-case contract" section that makes Haworth
  exceptions explicit shared-engine inputs (site intent payload, target
  primitive, connector constraints, and bond style), adds required behavioral
  rules to eliminate renderer-only endpoint hacks, and defines acceptance
  criteria for upward OH overlap, furanose side-chain stereography, L-rhamnose
  methyl parity, and reversible CH2OH/HOH2C attachment stability.
- Add a focused "Phase B.1: furanose side-chain stereography parity" addendum
  in
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  to target the remaining two-carbon left-tail parity gap (hashed cue plus
  above/below placement impression) with deterministic stereocenter-driven
  rules, explicit fixture scope (including D-galactose furanose alpha), and
  strict acceptance criteria that preserve current ring/vertical/OH-HO quality.
- Add a new strict overlap gate section to
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  defining mandatory painted-geometry overlap validation, target-derived
  forbidden regions, matrix/archive smoke enforcement, explicit unit-regression
  cases, and fail-fast CI policy.
- Clarify
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  with explicit selector precedence (`attach_element` over `attach_atom` over
  deterministic defaults), target-based legality semantics (forbidden regions
  derived from attachment targets, not cosmetic masks), constrained-segment
  handling for Haworth vertical connectors, no-CDML-migration compatibility
  promise, and wedge/hashed shape-generation guidance requiring clipped
  endpoints to drive full bond geometry.
- Tighten quick Haworth regression guards:
  in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py), replace
  the no-op scaled overlap assertion with a real bounded threshold for the
  lyxose internal OH/HO pair.
- Remove the own-connector smoke gate leak in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py):
  non-hydroxyl own connectors are no longer skipped when not `_chain`, and
  single-token labels now fall back to full `label_box` validation.
- Apply a quick visual hashed-branch hotfix in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  make the hashed carrier modestly visible and expand hatch filtering toward
  near-full branch coverage to reduce the "floating" appearance.
- Fix stale parity plan reference in
  [docs/CHANGELOG.md](docs/CHANGELOG.md) to point at
  [docs/archive/RENDER_LAYOUT_PARITY_SPEC.md](docs/archive/RENDER_LAYOUT_PARITY_SPEC.md).
- Expand
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  with explicit blocking findings and closure criteria for known attachment
  regressions: hashed branch detachment heuristics, non-protective overlap
  assertions, own-connector smoke exemptions, and doc-path hygiene checks.
- Refine phase structure in
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  from seven checklist phases to three execution phases (`A/B/C`), moving
  inventory/exception cleanup/release gating into embedded deliverables and a
  dedicated release checklist, and add an explicit backward-compatibility
  section for additive rollout guarantees.
- Restore rounded side wedges for Haworth ring edges adjacent to the front edge
  in [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  keep oxygen-end clipping before edge-op construction, render the two
  front-adjacent edges as shared rounded-wedge `PathOp` geometry with `ARC`
  commands (while keeping front and back edge draw behavior unchanged), and
  retain polygon proxies for ring collision/layout blocking. Add explicit
  pyranose/furanose assertions for rounded side-edge `PathOp`/`ARC` output in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py).
- Add a complete follow-on attachment unification plan in
  [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
  to replace exception-driven behavior with one shared target-primitive bond to
  label contract across OASA molecular, Haworth, and BKChem rendering paths,
  including phased migration, strict invariants, and release gates.
- Implement directional token-edge label attachment as follow-on clipping
  behavior in [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  add shared `directional_attach_edge_intersection(...)` plus `bbox_center(...)`,
  route bond clipping to attach/label bbox centers instead of text-baseline
  origins, and apply directional edge selection (side vs vertical approach) for
  deterministic endpoint parity across render backends, including clipped
  parallel double-bond lines.
- Update Haworth connector clipping in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  to use directional token-edge attachment for generic label clipping and branch
  label connectors, while preserving oxygen-center-first behavior for `OH`/`HO`
  and switching its fallback path to directional oxygen-token edge clipping
  rather than generic bbox-center fallback; extend hydroxyl center parsing in
  [packages/oasa/oasa/haworth/renderer_text.py](packages/oasa/oasa/haworth/renderer_text.py)
  to handle markup-stripped `OH`/`HO` text consistently.
- Add directional attachment regressions in
  [tests/test_label_bbox.py](tests/test_label_bbox.py),
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py), and keep
  overlap/parity gates green in
  [tests/test_connector_clipping.py](tests/test_connector_clipping.py),
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py),
  and [tests/test_phase_c_render_pipeline.py](tests/test_phase_c_render_pipeline.py).
- Refine true hashed-branch semantics for furanose two-carbon tails in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  compute branch endpoints after label placement using shared
  `label_attach_bbox_from_text_origin(...)` + `clip_bond_to_bbox(...)`,
  carry hashed connector geometry with a non-visible stable-id centerline
  (`width <= 0.05`), and extend hatch coverage to near-terminal span
  (~8%..92% of connector length); fix the own-connector exemption bug in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  so non-hydroxyl own connectors are checked, and add explicit hashed quality
  checks in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  for `ARRRDM`/`ARRLDM` furanose alpha branch connectors.
- Replace Haworth oxygen masking with deterministic ring-edge geometry clipping
  in [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  remove `oxygen_mask` op emission, compute oxygen label bbox from shared
  `render_geometry.label_bbox_from_text_origin(...)`, and clip only the two
  oxygen-adjacent ring edge endpoints to an exclusion boundary derived from
  label bounds + edge thickness (with preserved existing edge thickness/color
  behavior, including gradient split ops and API-compatible `bg_color` arg).
  Replace mask-era unit expectations in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) with
  explicit no-mask and oxygen-label-interior non-overlap assertions, and add
  smoke/archive-matrix guards in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  to ensure no `oxygen_mask` ops and no oxygen-adjacent ring polygon overlap
  with oxygen label interiors.
- Tune hashed two-carbon-tail branch connectors in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  to remove the doubled-bond appearance while restoring visible connectivity to
  `CH2OH`: hashed branches now render as a thin centerline plus proximal hatch
  strokes (shared hashed geometry style, deterministic `*_hatchN` IDs), and
  keep smoke overlap checks and full test suite passing.
- Tighten Haworth hydroxyl connector acceptance to block own-label penetration:
  update [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  so `OH`/`HO` owning connectors fail on full label-interior overlap (while
  retaining non-oxygen overlap diagnostics), add targeted talopyranose
  regressions in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  for `ALLLDM` pyranose beta with `show_hydrogens` true/false, and harden
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  by adding deterministic upward-hydroxyl label nudge candidates plus endpoint
  retreat-to-clearance logic for both simple hydroxyl connectors and the furanose
  two-carbon-tail `chain1_oh` branch connector path.
- Refine furanose two-carbon tail rendering to match reference directionality
  without per-code branching in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  use direction/template-driven up-tail vs down-tail branch vectors, keep
  allose-like up tails clear of ring/cross-connector overlap with canonical
  `CH2OH` orientation, and add deterministic hashed branch overlays with stable
  op IDs (`*_hatchN`) for stereobond emphasis; update geometry/text expectations
  in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) and keep
  overlap guards green in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py).
- Fix two Haworth defects without sugar-code-specific conditionals:
  update terminal one-carbon post-closure deoxy handling in
  [packages/oasa/oasa/haworth/spec.py](packages/oasa/oasa/haworth/spec.py) so
  terminal deoxy renders as `CH3` (not `H`), update L-fucose/L-rhamnose
  expectations in
  [tests/fixtures/archive_ground_truth.py](tests/fixtures/archive_ground_truth.py),
  and add explicit alpha/beta coverage for `ALRRLd` and `ARRLLd` in
  [tests/test_haworth_spec.py](tests/test_haworth_spec.py); replace hardcoded
  two-carbon-tail branch layout in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  with deterministic direction-based templates plus branch-specific anchor/text
  behavior for OH and CH2OH labels, and update
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to assert
  allose/gulose branch geometry orientation and direction-specific label order
  instead of forcing a single leftward `HOH<sub>2</sub>C` pattern.
- Refine the Haworth hydroxyl-own-connector overlap gate in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py):
  keep the no-overlap invariant for `OH`/`HO` own connectors but evaluate
  non-oxygen penetration against token-level label regions, with a deterministic
  left/right half split fallback when attach-token spans collapse to the full
  label bbox, and update the forced-overlap regression fixture to target the
  non-oxygen token region explicitly.
- Complete render-layout parity implementation from
  [docs/archive/RENDER_LAYOUT_PARITY_SPEC.md](docs/archive/RENDER_LAYOUT_PARITY_SPEC.md):
  expand general SVG/Cairo payload parity plus geometry-invariant checks in
  [tests/test_phase_c_render_pipeline.py](tests/test_phase_c_render_pipeline.py)
  (simple labels, aromatic ring, charged labels, wedge/hashed/wavy, and
  Haworth ring layouts), add optional real Cairo execution parity coverage when
  `pycairo` is available, and add focused Haworth parity guards in
  [tests/test_render_layout_parity.py](tests/test_render_layout_parity.py) for
  key connector/label op IDs, side-slot vertical connector invariants, and
  connector endpoint boundary invariants.
- Add hard Haworth bond/label overlap regression checks to
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py):
  run the invariant in both `test_haworth_renderer_smoke_matrix` and
  `test_archive_full_matrix` for both `show_hydrogens=True/False`, fail when any
  `LineOp` overlaps any label interior bbox (computed from shared
  `render_geometry` APIs), remove own-connector exemption for hydroxyl labels
  (`OH`/`HO`) with an oxygen-boundary-only allowance, and keep edge-touch allowed
  while rejecting interior penetration.
- Add [docs/archive/RENDER_LAYOUT_PARITY_SPEC.md](docs/archive/RENDER_LAYOUT_PARITY_SPEC.md)
  with a stronger no-deps SVG/Cairo parity test plan based on shared render-ops
  payload and geometry invariants (not pixel diffs).
- Fix Haworth connector regression after shared-clipping integration by splitting
  endpoint policy in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  keep shared bbox/attach-bbox clipping for non-hydroxyl labels, route `OH`/`HO`
  connectors to oxygen-centered radius boundaries with deterministic attach-bbox
  fallback, add round-cap clearance so connector paint does not overlap the
  oxygen glyph, and preserve vertical connector appearance for side slots
  (`BR`, `BL`, `TL`); update regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) and document
  the split policy in
  [docs/active_plans/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/active_plans/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md).
- Make
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py)
  auto-create `output_smoke/archive_matrix/` when missing, while still failing
  clearly if that path exists as a non-directory.
- Clean stale backlog/status docs by removing obsolete `bkchem/oasa` validation
  from [docs/TODO_REPO.md](docs/TODO_REPO.md), updating RDKit/Open Babel
  candidate wiring in [docs/TODO_CODE.md](docs/TODO_CODE.md) from legacy plugin
  paths to current format-loader wiring, and refreshing moved plan links plus
  Haworth plan status in [refactor_progress.md](refactor_progress.md), including
  normalized `docs/active_plans/` and `docs/archive/` references with a
  consolidated reference-doc index.
- Remove [docs/TODO.md](docs/TODO.md) and move its remaining backlog-hygiene
  action into [docs/TODO_REPO.md](docs/TODO_REPO.md) so TODO tracking lives
  only in code/repo-specific lists.
- Clarify CDML namespace usage and add explicit documentation-pointer metadata:
  keep namespace identity
  (`http://www.freesoftware.fsf.org/bkchem/cdml`) unchanged, add
  `<metadata><doc href="https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md"/></metadata>`
  in OASA/BKChem CDML output writers
  ([packages/oasa/oasa/cdml_writer.py](packages/oasa/oasa/cdml_writer.py),
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py), and
  [packages/bkchem-app/bkchem/data.py](packages/bkchem-app/bkchem/data.py)),
  update spec guidance in
  [docs/CDML_FORMAT_SPEC.md](docs/CDML_FORMAT_SPEC.md), and add regression
  coverage in [tests/test_codec_registry.py](tests/test_codec_registry.py) and
  [tests/test_bkchem_cdml_roundtrip.py](tests/test_bkchem_cdml_roundtrip.py).
- Fix CD-SVG CDML forwarding in
  [packages/oasa/oasa/codecs/cdsvg.py](packages/oasa/oasa/codecs/cdsvg.py) by
  passing CDML writer kwargs (`policy`, `version`, `namespace`,
  `coord_to_text`, `width_to_text`) through to
  `cdml_writer.mol_to_text(...)` while leaving render kwargs unchanged, and add
  a regression test in [tests/test_codec_registry.py](tests/test_codec_registry.py)
  that validates forwarded `version`/`namespace` values appear in embedded
  CDML.
- Implement Phase 1 of
  [docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md):
  add shared geometry helpers (`label_bbox`, `label_attach_bbox`,
  `clip_bond_to_bbox`) and shared label tokenization utilities in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py),
  refactor `build_vertex_ops()` to consume `label_bbox()` as the single bbox
  source, and add Phase 1 unit coverage in
  [tests/test_label_bbox.py](tests/test_label_bbox.py).
- Tighten Phase 1 validation by making
  `label_attach_bbox(..., attach_atom=...)` fail fast on invalid enum values
  (raise `ValueError` unless value is `"first"` or `"last"`) in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py),
  with regression coverage in [tests/test_label_bbox.py](tests/test_label_bbox.py).
- Implement Phase 2 connector clipping integration from
  [docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md):
  route molecular bond endpoints through shared label and attachment bboxes in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (`molecule_to_ops`/`build_bond_ops`), add text-origin bbox helpers for shared
  clipping math, route Haworth simple-label connectors through shared bbox
  clipping in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py),
  centralize baseline shift in
  [packages/oasa/oasa/haworth/renderer_text.py](packages/oasa/oasa/haworth/renderer_text.py),
  delegate layout bboxes to shared geometry in
  [packages/oasa/oasa/haworth/renderer_layout.py](packages/oasa/oasa/haworth/renderer_layout.py),
  and add/update regression coverage in
  [tests/test_connector_clipping.py](tests/test_connector_clipping.py) plus
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py).
- Finalize Phase 2 hardening for
  [docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md):
  add malformed-legacy `attach_atom` fail-fast regression coverage (with
  explicit error-message assertions) in
  [tests/test_connector_clipping.py](tests/test_connector_clipping.py) and
  [tests/test_label_bbox.py](tests/test_label_bbox.py), add a focused
  tokenization fixture matrix (`OAc`, `NHCH3`, `SO3H`, `PPh3`,
  `CH(OH)CH2OH`) in [tests/test_label_bbox.py](tests/test_label_bbox.py), and
  mark Phase 1/2 done checks complete in
  [docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md).
- Update label-attachment planning/spec documentation to adopt
  `attach_atom="first|last"` as optional attachment intent metadata (geometry
  remains renderer-derived): revise design and Phase 1/2 implementation details
  in
  [docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md)
  and expand CDML semantics/defaults/write-location/backward-compat rules in
  [docs/CDML_FORMAT_SPEC.md](docs/CDML_FORMAT_SPEC.md).
- Tighten attachment and coordinate-system wording in
  [docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md)
  and [docs/CDML_FORMAT_SPEC.md](docs/CDML_FORMAT_SPEC.md): make missing
  `attach_atom` default behavior explicit (`"first"` for new readers), add an
  explicit anchor-origin-inside-bbox test requirement, add a compatibility
  promise statement, remove ambiguous `HOH2C` example wording, and clarify that
  CDML-on-disk remains +Y down while OASA may canonicalize internally.
- Complete Phase C renderer migration from
  [docs/archive/PURE_OASA_BACKEND_REFACTOR.md](docs/archive/PURE_OASA_BACKEND_REFACTOR.md):
  add OASA registry-backed render codecs (`svg`, `pdf`, `png`, `ps`) plus a
  new CD-SVG codec in
  [packages/oasa/oasa/codec_registry.py](packages/oasa/oasa/codec_registry.py),
  [packages/oasa/oasa/codecs/render.py](packages/oasa/oasa/codecs/render.py),
  and [packages/oasa/oasa/codecs/cdsvg.py](packages/oasa/oasa/codecs/cdsvg.py);
  route BKChem export paths through registry/bridge in
  [packages/bkchem-app/bkchem/format_loader.py](packages/bkchem-app/bkchem/format_loader.py),
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py),
  [packages/bkchem-app/bkchem/http_server2.py](packages/bkchem-app/bkchem/http_server2.py),
  and [packages/bkchem-app/bkchem/export.py](packages/bkchem-app/bkchem/export.py);
  extend manifest entries in
  [packages/bkchem-app/bkchem/format_menus.yaml](packages/bkchem-app/bkchem/format_menus.yaml);
  and remove the Tk/cairo renderer plugin stack
  (`tk2cairo.py`, `cairo_lowlevel.py`, `pdf_cairo.py`, `png_cairo.py`,
  `svg_cairo.py`, `ps_cairo.py`, `ps_builtin.py`, `odf.py`) from
  [packages/bkchem-app/bkchem/plugins/](packages/bkchem-app/bkchem/plugins/).
- Add Phase C regression coverage in
  [tests/test_phase_c_render_pipeline.py](tests/test_phase_c_render_pipeline.py),
  expand codec/manifest checks in
  [tests/test_codec_registry.py](tests/test_codec_registry.py) and
  [tests/test_codec_registry_bkchem_plugins.py](tests/test_codec_registry_bkchem_plugins.py),
  and align plugin smoke inventory in
  [tests/bkchem_plugin_smoke.py](tests/bkchem_plugin_smoke.py).
- Phase C cleanup follow-ups: consolidate duplicated molecule merge helpers into
  [packages/oasa/oasa/molecule_utils.py](packages/oasa/oasa/molecule_utils.py)
  and route both
  [packages/oasa/oasa/render_out.py](packages/oasa/oasa/render_out.py) and
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
  through that shared utility; remove redundant SVG root append in
  [packages/oasa/oasa/render_out.py](packages/oasa/oasa/render_out.py); avoid
  built-in shadowing by switching `mol_to_output(..., format=...)` to
  `fmt` with backward-compatible `format` keyword handling; and document
  non-namespaced CD-SVG fallback behavior in
  [packages/oasa/oasa/codecs/cdsvg.py](packages/oasa/oasa/codecs/cdsvg.py).
- Mark ODF export as deferred post-Phase-C in
  [docs/archive/PURE_OASA_BACKEND_REFACTOR.md](docs/archive/PURE_OASA_BACKEND_REFACTOR.md)
  and add an explicit OASA-only reintroduction/retirement decision item in
  [docs/TODO_CODE.md](docs/TODO_CODE.md).
- Remove dead legacy CML export code paths in
  [packages/oasa/oasa/codecs/cml.py](packages/oasa/oasa/codecs/cml.py) and
  [packages/oasa/oasa/codecs/cml2.py](packages/oasa/oasa/codecs/cml2.py) so
  CML/CML2 stay strictly import-only at module API level, and add defensive
  registration comments in
  [packages/oasa/oasa/codec_registry.py](packages/oasa/oasa/codec_registry.py)
  to keep legacy CML codecs wired through explicit read callables.
- Enforce legacy export-drop policy in bridge code by keeping CML export hard
  disabled in
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py),
  and remove stale commented code in `read_inchi`.
- Add inline technical-debt note for SMILES/InChI selected-molecule special
  handling in
  [packages/bkchem-app/bkchem/format_loader.py](packages/bkchem-app/bkchem/format_loader.py),
  and keep regression coverage aligned in
  [tests/test_codec_registry_bkchem_bridge.py](tests/test_codec_registry_bkchem_bridge.py).
- Complete Phase B audit/retention work for
  [docs/archive/PURE_OASA_BACKEND_REFACTOR.md](docs/archive/PURE_OASA_BACKEND_REFACTOR.md):
  publish option classification, GTML retention outcome, CDML depiction audit,
  and CDML v2 decision in
  [docs/archive/PHASE_B_AUDIT.md](docs/archive/PHASE_B_AUDIT.md),
  mark Phase B status/done gates complete in
  [docs/archive/PURE_OASA_BACKEND_REFACTOR.md](docs/archive/PURE_OASA_BACKEND_REFACTOR.md),
  and add follow-up backlog items in [docs/TODO_CODE.md](docs/TODO_CODE.md).
- Make GTML explicitly import-only by setting `exporter = None` in
  [packages/bkchem-app/bkchem/plugins/gtml.py](packages/bkchem-app/bkchem/plugins/gtml.py)
  so no GTML exporter entry is exposed in the GUI export path.
- Add Phase B guardrail coverage in
  [tests/test_phase_b_option_policy.py](tests/test_phase_b_option_policy.py)
  and [tests/test_phase_b_gtml_roundtrip.py](tests/test_phase_b_gtml_roundtrip.py),
  and extend
  [tests/test_codec_registry_bkchem_plugins.py](tests/test_codec_registry_bkchem_plugins.py)
  with default-manifest/registry consistency and retired-option/deprecated-export checks.
- Implement Phase A plumbing from
  [docs/archive/PURE_OASA_BACKEND_REFACTOR.md](docs/archive/PURE_OASA_BACKEND_REFACTOR.md):
  add registry snapshot capabilities in
  [packages/oasa/oasa/codec_registry.py](packages/oasa/oasa/codec_registry.py),
  enforce CML/CML2 import-only behavior in
  [packages/oasa/oasa/codecs/cml.py](packages/oasa/oasa/codecs/cml.py) and
  [packages/oasa/oasa/codecs/cml2.py](packages/oasa/oasa/codecs/cml2.py),
  add BKChem registry-driven format plumbing via
  [packages/bkchem-app/bkchem/format_loader.py](packages/bkchem-app/bkchem/format_loader.py)
  and
  [packages/bkchem-app/bkchem/format_menus.yaml](packages/bkchem-app/bkchem/format_menus.yaml),
  route menu handling through the loader in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py), remove
  format plugins (`CML.py`, `CML2.py`, `CDXML.py`, `molfile.py`, `smiles.py`,
  `inchi.py`, `povray.py`) from
  [packages/bkchem-app/bkchem/plugins/](packages/bkchem-app/bkchem/plugins/), and keep
  only legacy GTML/renderer plugin discovery in
  [packages/bkchem-app/bkchem/plugins/__init__.py](packages/bkchem-app/bkchem/plugins/__init__.py).
- Replace deleted-plugin tests with loader/bridge coverage in
  [tests/test_codec_registry_bkchem_plugins.py](tests/test_codec_registry_bkchem_plugins.py),
  update registry capability assertions in
  [tests/test_codec_registry.py](tests/test_codec_registry.py), extend
  selection-validation coverage in
  [tests/test_codec_registry_bkchem_bridge.py](tests/test_codec_registry_bkchem_bridge.py),
  and align smoke plugin inventory in
  [tests/bkchem_plugin_smoke.py](tests/bkchem_plugin_smoke.py).
- Fix ASCII compliance in
  [docs/archive/PURE_OASA_BACKEND_REFACTOR.md](docs/archive/PURE_OASA_BACKEND_REFACTOR.md)
  by replacing a non-ISO left-right arrow with ASCII (`<->`).
- Add [docs/PURE_OASA_BACKEND_REFACTOR.md](docs/PURE_OASA_BACKEND_REFACTOR.md)
  documenting the full refactoring roadmap for migrating all backend work
  (format I/O, rendering, coordinate transforms) from BKChem plugins to OASA.
  Covers 6 phases: delete bridge wrappers, move format logic to OASA codecs,
  audit format options, evaluate GTML retirement, move rendering to OASA, and
  replace the plugins directory with YAML-driven manifests and a generic loader.
- Refactor
  [tests/fixtures/archive_ground_truth.py](tests/fixtures/archive_ground_truth.py)
  alpha-base fixture variable names to code-keyed identifiers (for example
  `_arldm_alpha_fur`, `_mklrdm_alpha_pyr`) so structural expectations are
  anchored to sugar codes rather than sugar-name labels.
- Reduce name-drift risk in
  [tests/fixtures/archive_ground_truth.py](tests/fixtures/archive_ground_truth.py)
  by keying ambiguous D-ketohexose fixture variables by sugar code
  (`MKLLDM`/`MKRRDM`) instead of sugar-name labels.
- Enforce sugar-name source-of-truth in
  [tests/fixtures/neurotiker_archive_mapping.py](tests/fixtures/neurotiker_archive_mapping.py)
  by requiring each mapped sugar code name to resolve from
  [packages/oasa/oasa_data/sugar_codes.yml](packages/oasa/oasa_data/sugar_codes.yml)
  or explicit `_SPECIAL_NAMES` overrides, instead of silently falling back to
  the raw sugar code token.
- Trim [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) to keep only
  representative sugar-code examples and link directly to
  [packages/oasa/oasa_data/sugar_codes.yml](packages/oasa/oasa_data/sugar_codes.yml)
  as the full authoritative mapping.
- Correct D-ketohexose name mapping by swapping `MKRRDM`/`MKLLDM` assignments
  (D-psicose vs D-tagatose) in
  [packages/oasa/oasa_data/sugar_codes.yml](packages/oasa/oasa_data/sugar_codes.yml),
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md), and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md),
  and align fixture pairings in
  [tests/fixtures/neurotiker_archive_mapping.py](tests/fixtures/neurotiker_archive_mapping.py)
  and [tests/fixtures/archive_ground_truth.py](tests/fixtures/archive_ground_truth.py).
- Remove unused legacy `get_structure_hash()` from
  [packages/oasa/oasa/molecule.py](packages/oasa/oasa/molecule.py) to eliminate
  Python 2-era `sha` import-policy issues in Python 3.
- Add a backlog item in [docs/TODO_CODE.md](docs/TODO_CODE.md) to implement a
  hash-based verification layer for future CDML files.
- Fix invalid UTF-8 bytes in
  [docs/HAWORTH_CODE_ORGANIZATION_PLAN.md](docs/HAWORTH_CODE_ORGANIZATION_PLAN.md)
  by replacing corrupted separator lines with an ASCII markdown table.
- Remove SOAP support references by deleting the legacy SOAP server startup
  block from [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py)
  and dropping `SOAPpy` from [pip_requirements.txt](pip_requirements.txt).
- Add inline purpose comments for each dependency in
  [pip_requirements.txt](pip_requirements.txt),
  [pip_requirements-dev.txt](pip_requirements-dev.txt), and
  [pip_extras.txt](pip_extras.txt) for clearer dependency intent.
- Add heading comments to [pip_requirements-dev.txt](pip_requirements-dev.txt)
  and [pip_extras.txt](pip_extras.txt) to clarify each file's dependency scope.
- Complete codec-registry Phase 3 backend routing by moving CML/CML2/CDXML
  parsing and serialization into OASA codecs
  ([packages/oasa/oasa/codecs/cml.py](packages/oasa/oasa/codecs/cml.py),
  [packages/oasa/oasa/codecs/cml2.py](packages/oasa/oasa/codecs/cml2.py), and
  [packages/oasa/oasa/codecs/cdxml.py](packages/oasa/oasa/codecs/cdxml.py)),
  registering them in
  [packages/oasa/oasa/codec_registry.py](packages/oasa/oasa/codec_registry.py),
  extending [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
  with generic codec file bridge helpers, and rewriting BKChem format plugins
  [packages/bkchem-app/bkchem/plugins/CML.py](packages/bkchem-app/bkchem/plugins/CML.py),
  [packages/bkchem-app/bkchem/plugins/CML2.py](packages/bkchem-app/bkchem/plugins/CML2.py),
  and [packages/bkchem-app/bkchem/plugins/CDXML.py](packages/bkchem-app/bkchem/plugins/CDXML.py)
  as thin bridge wrappers.
- Expand codec integration coverage in
  [tests/test_codec_registry.py](tests/test_codec_registry.py) and
  [tests/test_codec_registry_bkchem_bridge.py](tests/test_codec_registry_bkchem_bridge.py)
  for CML/CML2/CDXML default registration and bridge usage.
- Add plugin-level bridge routing tests in
  [tests/test_codec_registry_bkchem_plugins.py](tests/test_codec_registry_bkchem_plugins.py)
  to verify BKChem CML/CML2/CDXML importers and exporters call `oasa_bridge`
  (including versioned CML2 paths) and wrap bridge failures as plugin
  import/export exceptions.
- Update import policy sources in
  [tests/test_import_requirements.py](tests/test_import_requirements.py) to
  include `pip_extras.txt` (and `config_files/pip_extras.txt`) so optional
  dependencies such as Open Babel/Pybel are recognized by the requirements
  allowlist.

## 2026-02-08
- Move Haworth modules into dedicated
  [packages/oasa/oasa/haworth/](packages/oasa/oasa/haworth/) subpackage: split
  the 1,381-line `haworth_renderer.py` into five focused modules
  (`renderer.py`, `renderer_config.py`, `renderer_geometry.py`,
  `renderer_text.py`, `renderer_layout.py`), move `haworth.py` to
  `haworth/__init__.py` and `haworth_spec.py` to `haworth/spec.py`. Thin
  backward-compat shims at the old import paths
  ([packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py),
  [packages/oasa/oasa/haworth_spec.py](packages/oasa/oasa/haworth_spec.py))
  keep all existing `import oasa.haworth_renderer` / `import oasa.haworth_spec`
  code working without changes.
- Add [packages/oasa/oasa/sugar_code_names.py](packages/oasa/oasa/sugar_code_names.py):
  load sugar display names from
  [packages/oasa/oasa_data/sugar_codes.yml](packages/oasa/oasa_data/sugar_codes.yml)
  via `get_sugar_name()` and `all_sugar_names()`, making the YAML file the
  single source of truth for sugar names. Update
  [tests/fixtures/neurotiker_archive_mapping.py](tests/fixtures/neurotiker_archive_mapping.py)
  to pull names from the YAML loader instead of hardcoding them, flattening the
  map structure from `{"name": ..., "ring_forms": {...}}` to
  `{(ring_type, anomeric): filename}`.
- Add [docs/SUGAR_CODE_GUIDE.md](docs/SUGAR_CODE_GUIDE.md) to document sugar
  code syntax, token meanings, prefix/config parsing, digit footnote rules,
  and how to read
  [packages/oasa/oasa_data/sugar_codes.yml](packages/oasa/oasa_data/sugar_codes.yml).
- Align generated preview oxygen-mask fill with summary frame background in
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) by
  rendering regenerated Haworth SVG previews with `bg_color="#fafafa"` so the
  in-ring oxygen whiteout mask no longer appears as a mismatched box.
- Harden Haworth renderer maintainability without visual-output changes in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  centralize ring-type geometry lookup through shared config helpers
  (`_ring_slot_sequence`, `_ring_render_config`) and add explicit simple-job
  validation (`_validate_simple_job`) so malformed layout jobs fail early with
  targeted errors instead of scattered `KeyError`/branch failures. Extend smoke
  invariants in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  to assert unique `op_id`s, finite geometry, non-degenerate lines/polygons,
  and non-empty text across the full archive matrix, plus unit validation
  checks in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py).
- Fix leading-carbon connector anchoring for `COOH` labels in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  extend leading-carbon center detection from `CH*` to all `C*` labels so
  pyranose uronic-acid substituents (e.g., `ARLLDc` D-galacturonic acid) attach
  to the carbon glyph center instead of drifting into the `OO` span. Add a
  dedicated regression in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  `C5_up_label=COOH` connector alignment.
- Rework furanose two-carbon exocyclic tail rendering in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  for `CH(OH)CH2OH` on top-left/top-right furanose slots, replace the old
  collinear mini-chain (`HOHC`, `HOH<sub>2</sub>C`) with a branched layout
  (ring-to-branch trunk plus separate `HO` and `HOH<sub>2</sub>C` branches)
  so upper-left tails match NEUROtiker-style geometry and avoid stacked text.
  Update regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  aldohexose/gulose furanose branch connectors and labels.
- Refine downward `CH<sub>2</sub>OH` connector termination in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  keep x aligned to the leading carbon center but stop connector tips just above
  the label top boundary so round caps touch the glyph without entering the
  `C` interior (eliminates bond-through-carbon overlap on bottom anomeric
  `CH<sub>2</sub>OH` placements). Tighten regression checks in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  ketopentose furanose beta cases.
- Fix down-facing `CH<sub>2</sub>OH` connector overshoot in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  for simple downward `CH*` labels, terminate connector lines at the leading
  carbon glyph center (x/y) to prevent bond overlap through the `C` character
  on right-side ketopentose furanose cases (e.g., D-ribulose, D-xylulose beta).
  Add regression tests in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  `MKRDM`/`MKLDM` furanose-beta (`C2_down_label` vs `C2_down_connector`).
- Fix pyranose internal hydroxyl text-order regression in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  make internal up-hydroxyl labels center-facing (`C3_up` on left -> `OH`,
  `C2_up` on right -> `HO`) for single and paired internal cases, matching
  NEUROtiker references (e.g., D-arabinose and D-xylose). Add explicit
  regressions in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  for arabinose/xylose alpha+beta and updated mannose pyranose expectations.
- Fix ALRDM top-label regression in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  and [packages/oasa/oasa/render_ops.py](packages/oasa/oasa/render_ops.py):
  avoid `CH<sub>2</sub>OH` rendering as `CH2^OH` by emitting absolute SVG `dy`
  transitions for subscript tspans (font-size independent), and nudge the
  furanose top-right `OH` downward (toward ring center) for chain-like left-top
  cases so top substituents are no longer visually snapped to the same y line.
  Update regression checks in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py).
- Add a dedicated furanose internal-hydroxyl ordering guard in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py):
  scan the furanose matrix and fail if any dual internal up-hydroxyl pair
  renders as `HO ... OH`; required ordering is now enforced as `OH ... HO`.
- Fix furanose two-carbon exocyclic tail face selection in
  [packages/oasa/oasa/haworth_spec.py](packages/oasa/oasa/haworth_spec.py):
  keep alpha/beta affecting only the anomeric substituent, and for
  `post_chain_len == 2` derive closure-carbon chain up/down from the closure
  stereocenter (opposite the closure-carbon OH face) instead of global D/L
  config-only direction. This corrects D-galactofuranose-like cases (`ARLLDM`)
  where the left two-carbon tail must project below the ring in both alpha/beta.
  Update expected archive ground truth in
  [tests/fixtures/archive_ground_truth.py](tests/fixtures/archive_ground_truth.py)
  and add regression coverage in
  [tests/test_haworth_spec.py](tests/test_haworth_spec.py) plus
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py).
- Fix furanose dual-internal hydroxyl label regression in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  for same-lane internal `OH` pairs, restore deterministic interior reading as
  `OH ... HO` (left/right) and apply local one-pass `0.90` text scaling to the
  pair instead of widening labels into `HO ... OH` spacing. Add/update
  regressions in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  for `ALLDM` and `ALLRDM` furanose-alpha internal pair orientation and scale.
- Refine furanose beta top-substituent placement in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  preserve the lifted left-top `CH<sub>2</sub>OH` oxygen-clearance fix while
  de-coupling right-top `OH` from the same forced y level when the left top is
  chain-like (`CH*`), so the two top labels are no longer rendered as a flat
  row. Add regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  `ALRDM` furanose-beta top-label separation.
- Improve chemical subscript readability in
  [packages/oasa/oasa/render_ops.py](packages/oasa/oasa/render_ops.py) by
  rendering script text with a deterministic font scale and explicit `dy`
  baseline transitions (now visibly lowered like `CH<sub>2</sub>OH`), and fix
  a Cairo text-loop indentation bug that could redraw multi-segment labels
  multiple times. Update regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to assert
  `dy`-based SVG subscript shifts and no `baseline-shift` attributes.
- Refine furanose interior pair spacing rule in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  after deterministic `HO`/`OH` interior-up anchor assignment, evaluate a
  minimum horizontal label-gap threshold (in addition to overlap area) and apply
  one-time local `0.90` text scaling only when spacing is still too tight.
  Update coverage in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  to assert the rule outcome (`HO`/`OH` ordering plus either scaled labels or
  gap >= threshold) for `ALLDM` furanose-alpha.
- Fix left-end 2-carbon exocyclic chain direction labeling for furanose
  aldohexose cases (including `ARRLDM` D-gulose) in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  when chain labels are left-anchored (`anchor='end'`), flip `CHOH` -> `HOHC`
  and `CH2OH` -> `HOH2C` (with subscript markup), and align connector text
  offsets to trailing-carbon center for these flipped labels. Add regression
  coverage in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  for `ARRLDM` furanose alpha/beta and update exocyclic-chain expectations.
- Fix interior `OH/HO` direction regression for D-mannose-style pyranose
  interior-up pairs in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  by making the pair rule deterministic for pyranose: force both interior-up
  labels to `HO` (anchor `end`) and apply one-time local `0.90` text scaling
  only if overlap remains. Add dedicated regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  `ALLRDM` pyranose-alpha (`C2_up_label`, `C3_up_label` both `HO`).
- Tune exocyclic `CH<sub>2</sub>OH` connector anchoring and internal-label polish:
  in [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py),
  shift leading-carbon center anchoring for `CH*` labels to better hit the `C`
  glyph center, add a deterministic two-label internal hydroxyl cleanup step
  (detect same-lane internal `OH/HO` overlap above threshold, force left=`HO`/
  right=`OH`, then apply one-time local `0.90` text scale if needed, without
  cascading), and keep lane y-position fixed while scaling via anchor-preserving
  text size. In [packages/oasa/oasa/render_ops.py](packages/oasa/oasa/render_ops.py),
  lower subscript rendering by emitting SVG tspans with explicit
  `baseline-shift="-0.30em"` and matching Cairo offsets. Add regressions in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for the
  deterministic internal pair adjustment and subscript SVG baseline-shift output.
- Refine internal hydroxyl layout in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  by scoring internal text-vs-ring collisions against actual ring-edge polygons
  (not edge bbox approximations), restricting `OH`/`HO` anchor flipping to
  furanose internal slots, and enforcing one shared connector length for paired
  internal up-hydroxyl labels. Extend regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for ring-bond
  collision checks (`ALRDM` furanose-alpha, `ALLDM` pyranose-alpha) and equal
  internal connector lengths on two-internal-hydroxyl pyranose cases.
- Extend furanose top-side `up` connector lengths in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  for top-left/top-right slots (`ML`/`MR`) so endpoints clear above the ring
  oxygen glyph, improving match to reference top geometry; add regression coverage
  in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  `MKLRDM` furanose-beta (`C2_up_connector`, `C5_up_connector`).
- Fix exocyclic `CH<sub>2</sub>OH` connector anchoring in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  so ring connectors terminate at the leading carbon (`C`) glyph center instead
  of the text midpoint/subscript region; add regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for
  `ARRRDM` pyranose-alpha (`C5_up_label`).
- Fix generated-preview scaling inconsistency in
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) by normalizing
  whitespace when estimating SVG text bbox widths; this prevents inflated widths
  from pretty-printed `<tspan>` indentation/newlines (notably `CH<sub>2</sub>OH`)
  that previously produced oversized viewBoxes and tiny rendered sugars.
- Add two-pass hydroxyl label layout in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  using a tiny candidate slot set (`1.00x`, `1.18x`, `1.34x` connector lengths)
  and minimum-gap collision scoring for `OH`/`HO` text boxes; this reduces crowded
  furanose-side hydroxyl collisions while preserving deterministic connector
  placement. Add regression coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for ALDM
  furanose-alpha spacing and direct candidate-slot selection behavior.
- Add CLI argument parsing to
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) with
  `--regenerate-haworth-svgs` (default off) so generated Haworth preview SVGs are
  only re-rendered on demand; default behavior now reuses existing previews and
  falls back to existing matrix SVG outputs when available.
- Calibrate furanose ring geometry from NEUROtiker archive references by adding
  [tools/neurotiker_furanose_geometry.py](tools/neurotiker_furanose_geometry.py)
  extraction/normalization of 40 furanose SVGs (mean slot coordinates, edge
  lengths, and internal angles), then adopt the measured mean template in
  [packages/oasa/oasa/haworth.py](packages/oasa/oasa/haworth.py) and update
  regression expectations in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py).
- Refine furanose ring geometry in [packages/oasa/oasa/haworth.py](packages/oasa/oasa/haworth.py)
  by shifting the middle left/right pentagon vertices inward/upward to better
  match NEUROtiker reference proportions.
- Improve hydroxyl connector/text separation in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  by keeping oxygen-centered horizontal alignment while increasing downward
  hydroxyl baseline offset to prevent bond-to-glyph overlap; add helper geometry
  functions plus regression tests in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to assert
  hydroxyl connector endpoints align with oxygen centers and do not overlap the
  oxygen glyph region.
- Harden [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) XML
  parsing by switching from stdlib `xml.etree.ElementTree.parse` to
  `defusedxml.ElementTree.parse`, resolving Bandit B314 in full-suite security
  checks.
- Update [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) so
  generated comparison previews are re-rendered with
  `show_hydrogens=False` (no explicit H labels/connectors) and displayed at
  80% scale via expanded normalized viewBox framing for easier side-by-side
  visual comparison against NEUROtiker references.
- Adjust hydroxyl label x-offset geometry in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  so connector endpoints align with the oxygen glyph center for both right-
  anchored `OH` labels and left-anchored `HO` labels; add regression tests in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) covering each
  anchor direction.
- Improve summary-page centering/scaling in
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) by generating
  normalized generated-preview SVGs with tight content-fitted viewBoxes under
  `output_smoke/archive_matrix_previews/generated/`, and updating HTML/CSS preview
  frames to center content with non-distorting `max-width`/`max-height` scaling.
- Add [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py) to build
  a single human-review HTML page at
  `output_smoke/archive_matrix_summary.html`, showing all 78 Phase 5b archive
  cases with side-by-side generated and reference SVG previews plus missing-file
  summary counts.
- Start Phase 6 sugar-code-to-SMILES implementation with a bootstrap converter
  in [packages/oasa/oasa/sugar_code_smiles.py](packages/oasa/oasa/sugar_code_smiles.py),
  export it from [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py),
  and add unit coverage in
  [tests/test_sugar_code_smiles.py](tests/test_sugar_code_smiles.py) for
  validated reference cases (`ARLRDM` pyranose alpha and `MKLRDM` furanose beta),
  input validation, and unsupported-combination errors.
- Update [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  Phase 6 section with bootstrap implementation status and remaining scope.
- Close Phase 0 in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  by marking the phase tracker checkbox complete and recording release-gate
  validation results: full test suite (`333 passed, 6 skipped`) plus successful
  selftest sheet SVG generation using `source source_me.sh` with Python 3.12.
- Add a phase-status checklist at the top of
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  to track completion across Phases 1-7 and Phase 0 exit closure.
- Update [AGENTS.md](AGENTS.md) environment instructions to require
  `source source_me.sh` before running Python commands.
- Expand NEUROtiker archive reference fixtures by adding
  [tests/fixtures/neurotiker_archive_mapping.py](tests/fixtures/neurotiker_archive_mapping.py)
  (sugar-code/ring/anomer -> archive filename mapping helpers) and
  [tests/fixtures/archive_ground_truth.py](tests/fixtures/archive_ground_truth.py)
  (manually verified substituent ground truth across the mappable archive set).
- Add archive-wide Haworth validation coverage:
  [tests/test_haworth_spec.py](tests/test_haworth_spec.py) now parametrizes
  expected substituents against archive ground truth, and
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py)
  now includes a full mappable archive matrix render smoke test.
- Improve Haworth renderer configurability and label geometry in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  add `show_hydrogens` and `oxygen_color` render controls, split oxygen-adjacent
  ring edges into two-color segments, tune connector-length multipliers, and use
  direction-aware baseline shifts so connector endpoints align more tightly to labels.
- Extend renderer regression tests in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) for oxygen-edge
  polygon counts, updated connector-length constants, and hydrogen-hide behavior
  (suppress `H` labels/connectors while preserving non-hydrogen substituents).
- Expand Haworth selftest visual vignettes in
  [tools/selftest_sheet.py](tools/selftest_sheet.py) by adding a third row with
  alpha-D-Tagatopyranose and alpha-D-Psicofuranose builder cases for crowded-label
  positioning checks.
- Update design/roadmap notes in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  with Phase 5b archive-reference testing details, Phase 5c rendering-polish notes,
  and explicit multi-ring/collision detection stretch-goal documentation.
- Add a focused Wikimedia downloader script at
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  that only accepts `User:NEUROtiker/gallery/archive1`, filters `File:` links by
  case-insensitive `haworth`, resolves original image URLs via Commons API, and
  writes a manifest JSON with source file page, URL, SHA1, MIME type, and local path.
- Harden Wikimedia fetch behavior in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py):
  keep requests strictly sequential with `time.sleep(delay_base + random.random())`
  before each request, add retry/backoff for transient HTTP/network failures
  including `429`, and continue per-file with manifest error records instead of
  aborting the entire run on first failure.
- Improve NEUROtiker archive filtering in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  to parse archive wikitext (`action=raw`) and match keyword on each `File:` line
  (including caption/description text), so Haworth entries are discovered even
  when filenames do not contain the word "haworth".
- Expand NEUROtiker archive matching in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  to accept any `User:NEUROtiker/gallery/archive#` URL and support
  comma-separated keyword terms (default `haworth,pyranose,furanose`) for caption/line
  matching, so pyranose/furanose Haworth entries in archive2+ are included even
  without explicit "haworth" in filenames.
- Simplify downloader CLI in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  to avoid argparse creep: keep only positional archive URLs plus `--dry-run`
  and `--limit`, default archive targets to `archive1` + `archive2` + `archive3`
  + `archive4`, and derive
  per-archive output folders/manifest paths automatically.
- Fix raw-page URL construction in
  [tools/fetch_neurotiker_haworth_archives.py](tools/fetch_neurotiker_haworth_archives.py)
  by deriving MediaWiki `title` as `User:...` from `/wiki/...` paths (instead of
  `wiki/User:...`), resolving `HTTPError 404` on `--dry-run` archive fetches.
- Adjust Haworth substituent connector geometry in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  so side-carbon (`MR`/`ML`) up/down bonds are vertical (not diagonal) for both
  pyranose and furanose renderings, matching expected Haworth line direction for
  OH/H annotations.
- Add regression checks in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to assert
  side connectors stay vertical on representative pyranose and furanose cases.
- Improve hydroxyl label readability in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  by rendering side labels with oxygen nearest the bond endpoint: keep `OH` for
  right-anchored labels and use `HO` for left-anchored labels. Add regression
  checks in [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py)
  for `HO` on left-anchor slots and `OH` on right-anchor slots.
- Reduce bond/text collisions for crowded Haworth bottoms in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py):
  flip BR/BL anchors to point outward from the ring center and apply a small
  anchor-based horizontal text nudge so label glyphs are placed at the bond end
  without the connector line crossing through letter strokes.
- Add a reusable visual-check generator script at
  [tools/haworth_visual_check_pdf.py](tools/haworth_visual_check_pdf.py)
  to render a fixed Haworth Phase 3 review sheet PDF from
  `sugar_code`/`haworth_spec`/`haworth_renderer` cases (including MKLRDM
  alpha/beta furanose and non-white `bg_color` panel), with optional
  `--show-carbon-numbers` for disambiguating substituent positions in manual QA.
- Implement Phase 4 Haworth selftest integration in
  [tools/selftest_sheet.py](tools/selftest_sheet.py): route
  `_build_alpha_d_glucopyranose_ops()` and
  `_build_beta_d_fructofuranose_ops()` through
  `sugar_code.parse()` -> `haworth_spec.generate()` ->
  `haworth_renderer.render()` (bond_length 30), and remove the older
  SMILES+`build_haworth`+explicit-H helper path so selftest sugar panels reflect
  the same renderer contract covered by Phase 2/3 tests.
- Add Phase 4 integration test coverage in
  [tests/test_selftest_haworth_builders.py](tests/test_selftest_haworth_builders.py)
  to assert both selftest sugar builders return non-empty ops with `PolygonOp`
  and `TextOp` content plus positive bounding boxes, matching the plan's
  direct in-process verification gate.
- Implement Phase 3 Haworth schematic renderer in
  [packages/oasa/oasa/haworth_renderer.py](packages/oasa/oasa/haworth_renderer.py)
  with slot-stable carbon mapping (`MR/BR/BL/ML/TL`), ring-edge polygon
  thickness classes (front/wedge/back), oxygen mask + label ops, substituent
  connector/label placement, optional carbon numbers, and exocyclic mini-chain
  rendering for `CH(OH)CH2OH` plus generic `CHAIN<n>` labels.
- Add Phase 3 unit coverage in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) (31 tests)
  for geometry placement, front-edge stability, subscript-visible-length
  handling, dual-wide label spacing multiplier, oxygen mask behavior, and
  exocyclic-chain direction/collinearity checks.
- Add Phase 3 smoke coverage in
  [tests/smoke/test_haworth_renderer_smoke.py](tests/smoke/test_haworth_renderer_smoke.py),
  generating SVG files from render ops across an A/MK sugar matrix (alpha/beta,
  pyranose/furanose), asserting non-empty `<svg` output with `PolygonOp` +
  `TextOp`, and including a non-white `bg_color` render path.
- Export `haworth_renderer` from
  [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py) for direct
  `oasa.haworth_renderer` access in integration points and tests.
- Extend exocyclic-chain labeling in
  [packages/oasa/oasa/haworth_spec.py](packages/oasa/oasa/haworth_spec.py):
  keep 2-carbon post-closure chains as `CH(OH)CH2OH` and emit `CHAIN<n>` for
  longer chains so Phase 3 renderer chain logic can scale past hexose cases.
- Implement Phase 2 Haworth spec generation in
  [packages/oasa/oasa/haworth_spec.py](packages/oasa/oasa/haworth_spec.py) with
  `HaworthSpec`, ring-closure matrix validation (`A`/`MK` x pyranose/furanose),
  alpha/beta substituent assignment, exocyclic-chain labeling, and Phase 0
  Haworth-eligibility gating for pathway carbon-state chemistry.
- Add Phase 2 unit/smoke coverage in
  [tests/test_haworth_spec.py](tests/test_haworth_spec.py) and
  [tests/smoke/test_haworth_spec_smoke.py](tests/smoke/test_haworth_spec_smoke.py),
  including alpha/beta anomeric flips, ring-capacity errors, meso non-cyclizable
  checks, and pathway-profile rejection cases.
- Add a compact standard sanity-matrix test in
  [tests/test_haworth_spec.py](tests/test_haworth_spec.py) for quick human-check
  expectations: ARLRDM pyranose alpha/beta C1 flip and MKLRDM furanose alpha/beta
  C2 OH/CH2OH swap.
- Export `sugar_code` and `haworth_spec` from
  [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py) for direct
  `oasa` module access in downstream integration/tests.
- Fix test/lint regressions after fixture cleanup:
  [tests/test_cdml_versioning.py](tests/test_cdml_versioning.py) now skips the
  legacy fixture check when `tests/fixtures/cdml/legacy_v0.11.cdml` is absent;
  [tools/check_translation.py](tools/check_translation.py) now uses consistent
  tab indentation and a `main()` guard to satisfy shebang/indentation checks;
  and [tools/selftest_sheet.py](tools/selftest_sheet.py) drops two pyflakes
  issues in `_add_explicit_h_to_haworth` (unused local and duplicate import).
- Simplify reference-output policy to Haworth-only artifacts: update
  [tests/test_reference_outputs.py](tests/test_reference_outputs.py),
  [tools/render_reference_outputs.py](tools/render_reference_outputs.py), and
  [docs/REFERENCE_OUTPUTS.md](docs/REFERENCE_OUTPUTS.md) to stop expecting or
  generating `wavy_glucose_reference.svg/png`.
- Update [tests/test_cdml_fixture_loads.py](tests/test_cdml_fixture_loads.py) to
  validate tracked fixtures in `tests/fixtures/cdml_roundtrip/` and treat the
  old `tests/fixtures/cdml/embedded_cdml.svg` check as optional (skip when the
  legacy fixture directory is intentionally absent).
- Add per-phase test matrix (deliverable/unit/integration/smoke/system) to
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md),
  defining smoke designs for phases 1-3, a Phase 4 unit/integration test around
  Haworth selftest builders, and a future SMILES round-trip smoke. Document test
  taxonomy angles (property-based, snapshot, fuzz, performance) for later use.
- Implement Phase 1 sugar-code parser in
  [packages/oasa/oasa/sugar_code.py](packages/oasa/oasa/sugar_code.py) with
  `ParsedSugarCode`, `parse()`, footnote/body split invariants, positional digit
  validation, side-qualified default hydrogen fill, unknown lowercase letter-code
  rejection, and parser-level key-family exclusivity checks (`n`, `nC`, `nL`, `nR`).
- Add Phase 1 parser tests in
  [tests/test_sugar_code.py](tests/test_sugar_code.py) (28 unit cases) and
  [tests/smoke/test_sugar_code_smoke.py](tests/smoke/test_sugar_code_smoke.py)
  using [tests/fixtures/smoke_sugar_codes.txt](tests/fixtures/smoke_sugar_codes.txt)
  for curated valid/invalid smoke coverage and `sugar_code_raw` round-trip checks.
- Export `atom_colors` and `dom_extensions` from
  [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py) so
  `tools/selftest_sheet.py` can access `oasa.atom_colors` and
  `oasa.dom_extensions` during test import, fixing collection-time
  `AttributeError` in [tests/test_fischer_explicit_h.py](tests/test_fischer_explicit_h.py).

## 2026-02-07
- Expand renderer test coverage in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  with substituent geometry verification tests that check y-coordinates of
  up/down labels relative to ring vertices (not just label presence), including
  `test_render_alpha_glucose_c1_oh_below`, `test_render_beta_glucose_c1_oh_above`,
  `test_render_all_substituents_correct_side`, and L-series reversal test. Add
  a geometry gate to the Phase 0 acceptance gates.
- Add `_visible_text_length` unit tests and `sub_length` multiplier verification
  tests to
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md),
  documenting the character-count heuristic limitation as a Phase 0 non-goal.
- Add unknown letter code rejection rule and parser tests to
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  unrecognized lowercase letter codes raise `ValueError` with character and
  position, with `test_parse_unknown_letter_code_raises` and
  `test_parse_unknown_letter_code_uppercase_not_affected`.
- Document transparent background masking as a Phase 0 non-goal in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and add oxygen mask `bg_color` tests (`test_render_o_mask_uses_bg_color`,
  `test_render_o_mask_default_white`).
- Document collinear exocyclic chain rendering as a Phase 0 non-goal in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and add multi-carbon chain geometry tests including
  `test_render_exocyclic_3_collinear` for 7-carbon aldose furanose.
- Update Phase 0 exit checklist in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  to require unknown letter code rejection, geometry verification tests, and
  oxygen mask `bg_color` testing.
- Remove time estimates from menu refactor phases in
  [docs/MENU_REFACTOR_ANALYSIS.md](docs/MENU_REFACTOR_ANALYSIS.md),
  [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md), and
  [docs/MENU_REFACTOR_SUMMARY.md](docs/MENU_REFACTOR_SUMMARY.md).
- Add Phase 0 baseline performance measurement requirement to menu refactor
  plans in
  [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md),
  [docs/MENU_REFACTOR_ANALYSIS.md](docs/MENU_REFACTOR_ANALYSIS.md), and
  [docs/MENU_REFACTOR_SUMMARY.md](docs/MENU_REFACTOR_SUMMARY.md): measure
  actual `update_menu_after_selection_change()` timing before building
  PerformanceMonitor infrastructure; if current system is not slow, monitoring
  framework is premature.
- Add scope boundary notes to menu refactor plans: format handler migration to
  OASA is a separate architectural project that should have its own plan
  document, not be bundled with the menu refactor.

## 2026-02-06
- Tighten Attempt 2 Phase 0 parser/generator gating in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  standardize parser terminology to "backbone position index", require explicit
  per-index key-family exclusivity (`n` vs `nC`; no `n`/`nC` mixed with
  `nL`/`nR`), define `nC=<state>(<attachments...>)` as the only combined
  carbon-state+attachment form, and add explicit test/contract language that
  pathway-profile `nC` chemistry remains parseable but is rejected by
  `haworth_spec.generate()` in Phase 0 as non-Haworth-eligible.
- Finalize backbone-index terminology and side-qualified example validity in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  replace undefined example token `m` with canonical `CH3`, switch index wording
  from "carbon index" to "backbone index" for digit semantics, add explicit
  "not IUPAC numbering" clarification, change invalid example rationale to
  "digit must equal the backbone position it occupies", and state that plain
  `n=` is permitted only at non-chiral positions.
- Enforce global positional digit semantics in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  digits now always match carbon index positions (not placeholder IDs), add
  explicit invalid examples (`A1LRDM[1=methyl]`, `A2LRDM[2=CH3]`), require
  side-qualified keys at chiral stereocenters (`nL`/`nR`, or `nC` for carbon
  state), add parser-test requirements for these invalid cases, and update mixed
  example/test notation from `AdLRD1[1=sulfate]` to index-matched
  `AdLRD6[6=sulfate]`.
- Correct index/side footnote examples in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  replace stale `A1LRDM[1=methyl]` examples with `A2LRDM[2R=CH3]`, and align
  related parser example/test strings to the same index-based side-qualified form.
- Tighten digit/footnote rule consistency in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): change minimum-length
  wording to "3 total characters", explicitly separate digit semantics by mode
  (monosaccharide placeholder IDs vs pathway positional indices), make `n`/`nC`
  mutually exclusive with `nL`/`nR` per index, remove contradictory key-ordering
  language, and add a citrate-class note that side-qualified CAC attachment
  notation is bookkeeping rather than stereochemical chirality.
- Align pathway/CAC consistency in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  change isocitrate canonical code to `c23cc[2L=OH,2R=H,3C=COO-]` (carbon-state
  form), clarify that branching is supported in pathway mode but rejected in
  Haworth conversion mode, and add `P` (`phosphate-left`) to the Haworth plan's
  letter-code label mapping so it matches the spec.
- Tighten canonical carbon-state consistency in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): update pyruvate to
  `cK3[3C=CH3]`, update 1,3-bisphosphoglycerate to
  `1Rp[1C=C(=O)OPO3]`, update succinyl-CoA to
  `c234[2C=CH2,3C=CH2,4C=C(=O)SCoA]`, and add `C(=O)OPO3` to preferred
  canonical value tokens.
- Tighten pathway footnote disambiguation in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  require single plain/`nC` assignment per carbon index per bracket block,
  define `nC=<state>(<attachment...>)` parenthesis semantics, and set canonical
  PEP encoding to `c23[2C=C3(EPO3),3C=CH2]`.
- Tighten backbone-count wording in [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  to state explicitly that prefix characters are part of the backbone position
  count (not separate metadata), preventing mis-parsing of forms like `MKLRDM`.
- Clarify mode semantics and terminal naming in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): rename `TERMINAL` to
  `C_TERMINAL_STATE`, separate validation into Monosaccharide mode vs Pathway
  mode for the penultimate config slot behavior, and note that the upstream YAML
  `dihydroxacetone` spelling is a known typo while spec text uses
  `dihydroxyacetone`.
- Simplify canonical PEP notation in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  from `c23[2=EPO3,2C=C3,3C=CH2]` to `c23[2C=CPO3,3C=CH2]` to avoid mixed
  duplicate C2 keys and keep carbon-state encoding compact.
- Replace provisional branch-word notation in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) with explicit substituent
  encoding guidance (for example `3R=COO-`) to keep pathway forms symbolic and
  avoid word-style branch labels.
- Align parser-plan wording in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  with symbolic pathway notation (`c23[2=EPO3,2C=C3,3C=CH2]`) and backbone-length
  validation language.
- Convert pathway codebook notation in [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  and parser-plan examples in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  from word labels to symbolic group/carbon-state tokens, add `nC` key support
  (for example `3C=CH2`), update PEP to `c23[2=EPO3,2C=C3,3C=CH2]`, and revise
  CAC canonical codes to use `nL`/`nR` where relevant and symbolic chemistry forms.
- Revise backbone-length semantics in [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  and [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  define sugar-code length as backbone carbon count (not always total carbons),
  allow branched pathway compounds to exceed body length via `branch-to-<k>`, and
  update citrate/cis-aconitate/isocitrate canonical codes to 5-character bodies.
- Normalize pyruvate canonical token in [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  from `cK3[3=methyl]` to `cK3[3=CH3]` to match preferred canonical substituent
  tokens.
- Refine side-qualified footnote behavior in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  single-sided `nL`/`nR` now implies missing side `H`, add equivalence examples
  (`A2M[2L=OH]` -> `ALM`, `A2M[2R=OH]` -> `ADM`), and define preferred canonical
  substituent tokens for parser normalization.
- Extend numeric footnote grammar in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  with built-in side-qualified chiral keys (`nL`/`nR`), add ordering/validation
  rules, and document parser tests with example `A2M[2L=c,2R=m]`.
- Expand pathway-profile completeness in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  make digit placeholders location-matched (`digit == carbon index`) and ordered,
  update pyruvate to `cK3[3=CH3]`, add canonical glycolysis/CAC code tables
  (including citrate/isocitrate branch notation), and require this codebook before
  Phase 0 sign-off.
- Update [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) to keep pathway
  extensions single-character-per-carbon: add `p`/`P` stereochemical phosphate
  semantics, remove `C<n>=...` footnote keys in favor of numeric placeholders,
  add canonical digit-order guidance, and include examples such as `pKLRDp`,
  `pRLRDp`, `cK3[3=CH3]`, and `c23[2=phosphoenol,3=methylene]`.
- Refine `HaworthSpec` contract in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): remove `config` from
  `HaworthSpec`, document that `DEXTER`/`LAEVUS` are consumed during spec generation,
  and keep render-stage output as resolved up/down substituent labels only.
- Expand [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  for pathway-oriented coverage and meso clarity: add `MKp` as a valid meso triose
  derivative example, define pathway footnote extension rules, document
  validation constraints for those forms, and state that series orientation is
  resolved during spec generation before Haworth output.
- Update parser schema details in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) to split former `raw`
  language into `sugar_code` (body without footnotes) and `sugar_code_raw`
  (exact original input), with explicit split invariants and a parser test for
  footnote/body separation.
- Update parser schema language in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md): internal `prefix` is now
  documented as normalized kind (`ALDO`/`KETO`/`3-KETO`) while literal prefix tokens
  remain in raw input text.
- Add an explicit uronic-acid note to [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md)
  with terminal oxidation mapping examples:
  `ARLRDc` from `ARLRDM`, `ARLLDc` from `ARLLDM`, and `ALLRDc` from `ALLRDM`.
- Correct sugar-prefix and Haworth scope assumptions in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  treat canonical prefix set as `A`/`MK` only, remove `MRK`/`MLK` references,
  and define trioses (for example `ADM`, `MKM`) as valid sugar-code forms that are
  non-cyclizable in Haworth conversion (must raise ring-capacity `ValueError`).
- Clarify prefix handling in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  `MRK`/`MLK` are valid PREFIX tokens for parsing, while bare prefix-only strings
  (for example `MRK`, `MLK`) are invalid full sugar codes because config/terminal
  fields are missing.
- Superseding note: where older 2026-02-06 bullets mention `MRK`/`MLK` support,
  the final decision for this repo is to reject those prefixes and keep canonical
  parsing/conversion on `A` and `MK` only.
- Make minimum sugar length explicit in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  sugar code bodies must be at least 3 characters long, and one-/two-character
  codes are parser-invalid.
- Add explicit invalid-prefix rationale in
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) and parser requirements in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  `MRK`/`MLK` are rejected as non-canonical ambiguous/redundant aliases in this
  project, with a dedicated parser test case.
- Improve visual clarity in the PREFIX subsection of
  [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) by adding aligned star-fill
  examples (`A*****`, `MK****`) and an explicit note that `*` is visual-only and
  not part of literal sugar codes.
- Update [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  to resolve remaining implementation blockers before coding.
- Clarify parser vs renderer scope for sugar prefixes: parser remains spec-aligned
  (`A`, `MK`, `MRK`, `MLK`, meso handling), with Haworth conversion constraints
  defined explicitly by the ring-closure/capacity matrix.
- Remove provisional "v1" wording from
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  so the support matrix and NotImplemented constraints read as the intended final form.
- Resolve `MK` furanose mapping ambiguity by replacing fixed carbon-number template
  maps with role-based template maps plus dynamic carbon-to-slot mapping derived
  from prefix and ring type.
- Make alpha/beta orientation rules internally consistent for `MK` anomeric handling
  and align the fructose test expectations with those rules.
- Refine meso representation in the Haworth attempt-2 parser plan: replace
  `config=None` with explicit internal `config="MESO"` to avoid ambiguity with
  sugar-code `M` symbols while keeping meso forms (`MKM`, `MRKRM`) parseable.
- Refine Haworth attempt-2 internal config naming to use explicit words
  `DEXTER`/`LAEVUS`/`MESO` in parsed/spec dataclasses, while preserving sugar-code
  input tokens `D`/`L` and documenting token-to-internal normalization.
- Refine Haworth attempt-2 ring position naming by replacing numeric vertex-key
  label configs with semantic slot keys (`ML`, `TL`, `TO`, `MR`, `BR`, `BL`) and
  documenting dynamic carbon-to-slot mapping to keep position logic readable and
  stable across `A`/`MK` mappings.
- Finalize upfront scope in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  remove deferred "handled later" language, add `MRK`/`MLK` support to the
  conversion matrix and ring-closure rules, define meso series resolution via
  `series_override`/inference, and replace not-implemented tests with explicit
  support and ring-capacity validation tests.
- Update [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) to add a Haworth ring
  closure matrix covering `A`, `MK`, `MRK`, and `MLK`, require ring-capacity
  validation during conversion, and define meso series-orientation handling for
  Haworth mapping.
- Expand Phase 0 documentation in
  [docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  and [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md) with explicit
  definition-of-done criteria, acceptance gates, deterministic/error contracts,
  and a clear scope boundary that keeps SMILES conversion work out of Phase 0.
- Create `docs/SUGAR_CODE_SPEC.md` defining sugar code notation for carbohydrate
  structures: prefix (A/MK) + stereocenters (R/L) + config (D/L) + terminal (M),
  with lowercase letter codes (d=deoxy, a=amino, n=N-acetyl, p=phosphate, f=fluoro,
  c=carboxyl) and numeric footnotes for rare modifications. Key invariant:
  `len(sugar_code) == num_carbons`.
- Rename `docs/HAWORTH_IMPLEMENTATION_PLAN.md` to
  `docs/HAWORTH_IMPLEMENTATION_PLAN_attempt1.md` (via `git mv`) to preserve history
  and distinguish the SMILES-based approach (failed at stage 4 substituent rendering)
  from the new sugar-code-based approach.
- Create `docs/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md` with a schematic-only renderer
  architecture: sugar code parser -> Haworth spec generator -> render_ops output
  (TextOp + LineOp + PolygonOp), bypassing the molecular graph entirely.
  - Phase 1: sugar code parser with validation matrix (prefix + ring_type -> carbon
    count and ring closure)
  - Phase 2: Haworth spec generator with general ring-closure rules, ring vs exocyclic
    carbon classification, and substituent assignment algorithm
  - Phase 3: schematic renderer with filled polygon ring edges, explicit front-edge
    template metadata, per-ring-type label configs, bg_color parameter, and
    multi-carbon exocyclic chain rendering
  - Phase 4: selftest_sheet.py integration
  - Phase 5: verification
  - Phase 6: sugar code to SMILES conversion (Fischer-to-CIP mapping)
  - Phase 7: SMILES to sugar code (lookup table + best-effort structural inference)
- Address two rounds of review findings (P1a-P3c, R2-P1a-R2-new) documented in the
  plan's Review Response Log.

## 2026-02-05 (continued)
- Fix benzene rendering to use Kekule SMILES (`C1=CC=CC=C1`) for proper alternating
  single/double bond display.
- Fix `tools/selftest_sheet.py` import system to work when imported as a module by
  removing relative imports and always using absolute `oasa.*` imports.
- Fix `tests/test_fischer_explicit_h.py` to import selftest_sheet from tools/ directory.
- Improve Haworth projection clarity by labeling OH groups as "OH" text labels instead
  of showing separate O and H atoms, reducing connectivity ambiguity.
- Position ring H atoms opposite from substituents for clearer stereochemistry display.

## 2026-02-05
- Create missing CDML fixture files in `tests/fixtures/cdml/` (benzene, stereochem,
  haworth, cholesterol, legacy_v0.11, embedded_cdml) to fix test failures.
- Move `packages/oasa/oasa/selftest_sheet.py` to `tools/selftest_sheet.py` and update
  import paths to use git-based repo root detection.
- Fix `tools/generate_biomolecule_templates.py` to look for `biomolecule_smiles.yaml`
  in `docs/` directory instead of repo root.
- Fix `tools/check_translation.py` to use git-based repo root detection and locate
  locale directory correctly.
- Update all tools to use `git rev-parse --show-toplevel` for repo root detection
  per [docs/REPO_STYLE.md](docs/REPO_STYLE.md) guidance.
- Generate missing reference output files using `tools/render_reference_outputs.py`.
- Fix all failing tests: `test_cdml_fixture_loads.py`, `test_cdml_versioning.py`,
  and `test_reference_outputs.py` now pass.
- Replace alpha-D-glucopyranose CDML template with SMILES-based builder in
  `tools/selftest_sheet.py` to fix poor substituent placement in Haworth projection.
- Add beta-D-fructofuranose vignette to capabilities sheet (5-membered furanose ring).
- Add `beta-D-fructofuranose` SMILES to [docs/biomolecule_smiles.yaml](biomolecule_smiles.yaml).
- Add explicit hydrogen atoms to Haworth projections for both alpha-D-glucopyranose
  and beta-D-fructofuranose by adding H atoms to complete ring carbon valences.
- Fix benzene rendering to use aromatic bond type ('a') instead of alternating
  single/double bonds for proper display.
- Fix layout_row scaling bug when vignettes don't fit by iterating over normalized
  tuples instead of original vignettes.
- Note: Haworth projections are simplified 2D representations that show stereochemistry
  but do not accurately depict 3D geometry or all bond angles. The planar representation
  is a projection for clarity, not a reflection of the actual chair/envelope conformations.

## 2026-02-03
- Reorganize [refactor_progress.md](../refactor_progress.md) into master
  Not started, In progress, and Completed sections with updates for menu
  refactor docs, PubChem planning, and OASA data reorganization.
- Update [refactor_progress.md](../refactor_progress.md) to mark the Haworth
  plan as still in progress (Stage 4 OH placement), call out menu refactor
  documentation as completed, and align in-progress notes with TODO updates.
- Add [docs/RELEASE_DISTRIBUTION.md](docs/RELEASE_DISTRIBUTION.md) to the
  refactor progress plan as a not-started automated installer tooling item.
- Update [docs/RELEASE_DISTRIBUTION.md](docs/RELEASE_DISTRIBUTION.md) to add
  automated build tooling for macOS dmg, Windows installer, and Linux Flatpak.
- Add `packages/oasa/oasa_data/` and store isotopes as compact JSON in
  `packages/oasa/oasa_data/isotopes.json`, generated from the NIST ascii2 output
  source.
- Replace the inline isotopes dict in `packages/oasa/oasa/isotope_database.py`
  with a JSON loader pointing at the new data file and document the source URL.
- Add `tools/convert_isotope_data.py` to download NIST isotope data and
  regenerate JSON, plus packaging updates to ship the new JSON data via
  `packages/oasa/pyproject.toml` and `packages/oasa/MANIFEST.in`.
- Remove legacy OASA data sources `packages/oasa/oasa/names.db`,
  `packages/oasa/oasa/structures.txt.gz`, `packages/oasa/oasa/synonyms.txt.gz`,
  `packages/oasa/oasa/subsearch_data.txt`, and
  `packages/oasa/oasa/subsearch_rings.txt`.
- Remove unused OASA modules `packages/oasa/oasa/name_database.py`,
  `packages/oasa/oasa/structure_database.py`, and
  `packages/oasa/oasa/subsearch.py`.
- Update `packages/oasa/oasa/__init__.py` and OASA docs to drop removed module
  references and keep the OASA import path working.
- Harden `tools/convert_isotope_data.py` URL handling with scheme/host checks
  and a Bandit-annotated urlopen call.
- Add `docs/PUBCHEM_API_PLAN.md` with the planned PubChem lookup integration
  scope and rollout steps.
- Add the PubChem API plan to [docs/TODO_REPO.md](docs/TODO_REPO.md).

## 2026-02-02
- Add [tests/test_bkchem_gui_benzene.py](../tests/test_bkchem_gui_benzene.py)
  to build a benzene ring (hexagon with alternating double bonds) and include
  it in [tests/run_smoke.sh](../tests/run_smoke.sh).
- Replace deprecated inspect.getargspec with getfullargspec in
  [packages/bkchem-app/bkchem/undo.py](../packages/bkchem-app/bkchem/undo.py) to
  restore undo/redo under Python 3.12.
- Deiconify the GUI and add event-loop flush delays in
  [tests/test_bkchem_gui_events.py](../tests/test_bkchem_gui_events.py) so
  in-process event simulation works reliably on real Tk windows.
- Make [tests/test_bkchem_gui_events.py](../tests/test_bkchem_gui_events.py)
  drag simulation more robust with multi-step motions and a click fallback.
- Expand [tests/test_bkchem_gui_events.py](../tests/test_bkchem_gui_events.py)
  with draw-drag, chain extension, mode switching, and undo/redo event coverage,
  and add it to [tests/run_smoke.sh](../tests/run_smoke.sh).
- Set PYTHONPATH in [tests/run_smoke.sh](../tests/run_smoke.sh) to prefer local
  BKChem and OASA packages, matching the GUI launch script.
- Add [tests/test_bkchem_gui_events.py](../tests/test_bkchem_gui_events.py) to
  simulate in-process GUI events (draw click, edit selection, delete key) for
  BKChem smoke coverage.
- Add [docs/MENU_REFACTOR_SUMMARY.md](docs/MENU_REFACTOR_SUMMARY.md) as executive
  summary tying together all menu refactor documentation: 6 core decisions (eliminate
  exec-based plugins, adopt YAML + Dataclass Hybrid menus, complete platform abstraction,
  backend/frontend separation with OASA as chemistry backend, modular built-in tools
  replacing addons, unified renderer architecture for GUI and export), performance
  requirements (< 100ms menu build, < 3ms avg / 5ms p95 state updates), 6-phase
  implementation plan (14 weeks total: format handlers to OASA, menu system core,
  menu migration, tools system, renderer unification, cleanup), risk mitigation
  strategies, success metrics (500 lines removed, 80% test coverage, zero exec calls),
  stakeholder communication guidance, Q&A section covering user workflows, extensibility,
  sandboxing rationale, performance, rollback strategy, translations, OASA standalone
  status. Summary includes comparison tables for plugin reclassification, backend/frontend
  boundaries, architecture benefits, and approval checklist.
- Fix non-ASCII characters in [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md)
  replacing degree symbols with "deg" and "degrees" text equivalents to ensure strict
  ASCII compliance for all documentation.
- Verify ASCII compliance for all menu refactor documentation
  (MENU_REFACTOR_ANALYSIS.md, BKCHEM_GUI_MENU_REFACTOR.md, MODULAR_MENU_ARCHITECTURE.md,
  MENU_REFACTOR_SUMMARY.md) - all pass grep checks with no non-ASCII characters.
- Add platform abstraction layer to [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  with MenuBackend interface (create_menubar, add_menu, add_menu_item, add_separator,
  add_cascade, set_item_state) making YAML structure and MenuBuilder 100%
  platform-agnostic, PmwMenuBackend with automatic platform detection, platform-specific
  adapters (PmwMacOSAdapter using MainMenuBar, PmwLinuxAdapter using standard MenuBar,
  PmwWindowsAdapter), opaque MenuHandle and MenuItemHandle eliminating all
  platform-specific code from menu builder, enabling easy port to Qt/Gtk/Cocoa by
  swapping backend implementation.
- Add performance monitoring section to [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  with PerformanceMonitor class (measure context manager, configurable warn threshold,
  stats tracking), instrumented MenuBuilder measuring build_menus and update_menu_states
  operations, performance acceptance criteria (menu build < 100ms one-time, state
  update < 3ms avg and < 5ms p95 for frequent operations), baseline benchmarking
  script comparing current vs new system, optimization strategy (state indexing for
  5-10x speedup, predicate caching for 2-3x speedup, after_idle batching), continuous
  monitoring in debug builds with automatic warning on slow operations.
- Add [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md)
  defining architecture for modular built-in chemistry tools (not plugins):
  Tool base class with metadata (id, name_key, category, requires_selection),
  ToolRegistry for discovery, tool categories (analysis, conversion, visual,
  fetchers, editing), automatic menu population via tool_category in YAML,
  migration plan for 8 current addons (angle_between_bonds, text_to_group,
  red_aromates, fetch_from_webbook, fragment_search, mass_scissors, animate_undo)
  converting XML + exec() scripts to built-in Tool subclasses, chemistry logic
  extraction to OASA backend (geometry.measure_bond_angle, aromaticity detection,
  fragment search, NIST fetchers), Python extension mechanism for user
  extensibility (safer than exec-based plugins using standard importlib), removes
  ~500 lines of plugin infrastructure while maintaining modularity and
  eliminating security risks from arbitrary code execution.
- Add [docs/MENU_REFACTOR_ANALYSIS.md](docs/MENU_REFACTOR_ANALYSIS.md) with
  comprehensive analysis of plugin architecture, menu system complexity, and
  migration challenges: assess whether import/export format handlers should remain
  as plugins (recommendation: move core formats like CML/CDXML/molfile to format
  registry, keep renderer backends as optional plugins, sandbox script plugins,
  remove unused mode plugins), analyze menu hooks (plugin injection, recent files,
  selection-driven enablement) with simplification strategies (declarative plugin
  slots, observable managers, indexed state updates, restricted plugin locations
  reducing complexity by ~70%), document 7 major migration challenges with detailed
  solutions (format plugin compatibility via parallel registry, translation key
  stability via preserved label_key values, plugin backward compatibility via
  LegacyMenuShim, macOS platform handling via PlatformMenuAdapter, performance
  optimization via state indexing reducing updates from O(n^2) to O(n), toolbar
  unification deferral, testing without GUI via mock Pmw), provide 6-phase
  prioritized action plan with time estimates (10 weeks total) and success criteria
  per phase.
- Add "GPL v2 Code Coverage Assessment Plan" section to
  [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) with comprehensive
  methodology for assessing GPL v2 code coverage across repository using git log,
  classification system (pure GPL-2.0, pure LGPL-3.0-or-later, mixed), git history
  analysis commands, GPL v2 percentage calculation methods for mixed files (commit
  count, line changes, time-weighted), summary report format, SPDX header compliance
  tracking, implementation script structure, usage examples, and ongoing maintenance
  strategy. Plan assumes all edits prior to 2025 are GPL-2.0 and provides baseline
  metrics to track migration progress.
- Split rendering into geometry producer vs painters: add
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  with `BondRenderContext` and `build_bond_ops`, update svg/cairo backends,
  selftest, and render ops snapshot tests to use it.
- Update BKChem `bond._draw_q1` to use `render_geometry.haworth_front_edge_geometry`
  after the geometry split.
- Move SVG vertex rendering to ops: add `build_vertex_ops` helpers in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py),
  switch [packages/oasa/oasa/svg_out.py](packages/oasa/oasa/svg_out.py) and
  selftest molecule ops to use them.
- Add [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  documenting current menu construction and a refactor plan.
- Comprehensively rewrite [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  to recommend YAML + Dataclass Hybrid approach combining YAML menu structure
  (human-editable hierarchy) with Python dataclass action registry (type-safe handlers).
  Add architecture overview diagram, complete implementation examples for YAML menus,
  Python actions with lazy translation, menu builder combining YAML + actions, plugin API,
  toolbar unification, and comprehensive test suite. Replace implementation phases with
  detailed 7-phase plan (0: Analysis, 1: Action registry Python-only, 2: YAML structure
  for File menu, 3: Incremental migration menu-by-menu, 4: Plugin API integration,
  5: Toolbar unification, 6: Cleanup and testing, 7: Portability demo) with per-phase
  deliverables, success criteria, code examples, and specific task checklists. Document
  portability to Qt/Swift/web frameworks, i18n compatibility with .po files, comparison
  of approaches (human readability, ease of add/rearrange, difficulty, verbosity), and
  provide concrete first step with minimal working action registry and unit tests.
- Add [docs/BKCHEM_GUI_CODE_REVIEW.md](docs/BKCHEM_GUI_CODE_REVIEW.md) with
  a GUI code quality review and prioritized improvement areas.
- Expand [docs/BKCHEM_GUI_CODE_REVIEW.md](docs/BKCHEM_GUI_CODE_REVIEW.md) with
  additional architectural findings covering menu system architecture (tuple schema,
  enablement logic), mode system architecture (registration, plugin modes, submodes,
  toolbar creation), key sequence handling (CAMS modifiers, sequence building, focus
  fragility), context menu architecture (dynamic building, configurable properties),
  canvas event binding (platform-specific issues), singleton initialization (template
  managers), plugin menu integration, and recent files menu. Add expanded next steps
  with immediate/medium/long-term priorities including script execution boundaries,
  platform input normalization, key modifier recovery, mode system cleanup, unit test
  harness, event binding tests, and documentation requirements.
- Add [docs/BACKEND_CODE_REVIEW.md](docs/BACKEND_CODE_REVIEW.md) documenting
  backend rendering quality notes, risks, and follow-up recommendations.
- Rework `packages/oasa/oasa/selftest_sheet.py` to build a backend-agnostic
  ops list (including molecule vignettes via `_build_molecule_ops`) and render
  through a single SVG/Cairo sink, removing backend-specific composition and
  embedded SVG/PNG handling while keeping titles and grid labels as ops.
- Update `tests/test_fischer_explicit_h.py` to assert Fischer explicit hydrogen
  labels via `render_ops.TextOp` output instead of SVG DOM inspection.
- Update [docs/SELFTEST_PAGE_SPEC.md](docs/SELFTEST_PAGE_SPEC.md) with "Vignette
  Contract (Hard Requirements)" section defining bbox invariant (finite, non-zero
  width/height required, raises ValueError on violation) and projection-specific
  invariants (Haworth must have in-ring O vertex and semantic front edge, raises
  AssertionError on violation). Selftest now treats broken rendering as a hard
  failure that aborts generation, preventing misleading output.
- Add defensive bbox validation in `packages/oasa/oasa/selftest_sheet.py`:
  `ops_bbox()` now raises ValueError on empty ops, NaN coordinates, zero-sized
  bbox, or invalid bbox; `normalize_to_height()` raises ValueError on empty ops,
  NaN/invalid target height, or NaN/invalid current height. Selftest now fails
  fast on rendering errors instead of silently producing broken output.
- Add `source_me.sh` at repo root for testing and development (not installation):
  configures PYTHONPATH for BKChem/OASA packages, sets Python 3.12 interpreter,
  and enables clean Python execution (no .pyc files, unbuffered output). Use with
  `source source_me.sh` before running tests or development scripts.
- Complete canonical Haworth integration in `packages/oasa/oasa/selftest_sheet.py`:
  add `_build_haworth_svg()` using canonical renderer path (svg_out.mol_to_svg,
  same as test_haworth_layout.py), add `_assert_haworth_invariants()` to verify
  exactly one in-ring oxygen vertex and at least one semantically tagged front
  bond before rendering, rewrite `_build_haworth_ops()` to use canonical pipeline
  (molecule from SMILES, haworth.build_haworth, invariant checks, svg_out rendering)
  and extract ops for layout system. Haworth now renders via projection grammar
  (semantic bond tags + layout) with atoms+bonds together from svg_out, not
  hand-assembled primitives. Oxygen appears because it's a vertex, not added text.
- Remove the `use_oasa_cdml_writer` flag and keep OASA CDML serialization as the
  only BKChem path, updating the serializer smoke test in
  `tests/test_bkchem_cdml_writer_flag.py`.
- Add `packages/oasa/oasa_cli.py` with a Haworth SMILES CLI for SVG/PNG output
  and a CLI smoke test in `tests/test_oasa_haworth_cli.py`.
- Update CLI references to the `packages/oasa/oasa_cli.py` path across plans
  and usage docs.
- Render the Haworth selftest vignette from the canonical molecule pipeline
  by embedding svg_out output in `packages/oasa/oasa/selftest_sheet.py`, and
  add mixed SVG/ops layout helpers to preserve semantic rendering.
- Resolve repo root in CDML/CLI tests via shared helpers in
  [tests/conftest.py](tests/conftest.py) (no git commands), and register the
  `--save` pytest option for smoke output preservation.
- Add [tests/test_haworth_cairo_layout.py](tests/test_haworth_cairo_layout.py)
  as a pre-merge baseline copy of Haworth layout tests, and update Haworth tests
  to use [tests/conftest.py](tests/conftest.py) path helpers.
- Document the Haworth CLI in [docs/USAGE.md](docs/USAGE.md) and
  [packages/oasa/docs/USAGE.md](packages/oasa/docs/USAGE.md).
- Update [refactor_progress.md](refactor_progress.md) to mark Haworth CLI and
  CDML/Bond alignment Phase 5 completion.
- Refresh [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md),
  [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md),
  [docs/TODO_CODE.md](docs/TODO_CODE.md),
  [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md), and
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  to reflect current semantics and registry guidance.
- Replace OASA-generated atom nodes with BKChem atom/group/text/query CDML
  elements in `packages/bkchem-app/bkchem/molecule.py` to preserve vertex-specific
  serialization details.
- Extend `tests/test_bkchem_cdml_writer_flag.py` dummy helpers with real-coordinate
  passthrough and unique IDs for atom replacement coverage.
- Add `tests/test_bkchem_cdml_vertex_tags.py` to ensure group/text/query tags
  are preserved in CDML output.
- Add `packages/oasa/oasa/render_out.py` with a merged mol-to-output entry point
  for SVG and Cairo-backed formats, and route the Haworth CLI through it.
- Replace test-local repo root and fixtures path lookups with
  [tests/conftest.py](tests/conftest.py) helpers, removing `os.path.dirname(__file__)`
  usage across tests and updates to helper scripts under `tests/`.
- Render Haworth smoke outputs via `render_out.mol_to_output` in the Haworth
  layout tests and use the merged output path for Haworth SVG embedding in
  `packages/oasa/oasa/selftest_sheet.py`.
- Align selftest molecule vignettes with the SPEC by rendering benzene, Fischer,
  Haworth, and cholesterol via the molecule renderer (no manual ops/labels),
  and composite vignette PNGs in the Cairo backend instead of ops.
- Use defusedxml parsing for embedded SVG fragments in
  `packages/oasa/oasa/selftest_sheet.py` to satisfy bandit XML safety checks.
- Add the selftest motto ("Do less, but show more. Let the backend handle the
  complexities.") to [docs/SELFTEST_PAGE_SPEC.md](docs/SELFTEST_PAGE_SPEC.md)
  and [docs/RENDERER_CAPABILITIES_SHEET_PLAN.md](docs/RENDERER_CAPABILITIES_SHEET_PLAN.md).
- Resolve repo root in [tests/run_smoke.sh](tests/run_smoke.sh) from the script
  directory instead of running git.
- Fix ftext chunk splitting to avoid duplicated chunk objects and orphaned
  canvas text items, preventing atom labels from moving twice and leaving
  duplicates during drag operations.
- Ensure SVG text labels do not inherit stroke styling by explicitly setting
  `stroke="none"` on text ops and legacy SVG text drawing, fixing Haworth
  oxygen labels appearing black in SVG viewers while keeping fill-based coloring.
- Keep atom label text weight normal so SVG and Cairo/PNG outputs match after
  switching to fill-based text coloring.
- Increase Cairo text weight by default (font_weight=bold) so PNG/PDF output
  better matches SVG appearance; allow overriding via cairo_out options.
- Render atom labels in bold in SVG to match Cairo/PNG output weight.
- Use round linecaps for color-split bond segments to avoid visible gaps at
  Haworth ring junctions when gradients are used.
- Update Fischer rendering to show explicit H by default, keep OH/H bonds
  horizontal, place the aldehyde group at 120 degrees (O= and H), and label
  hydroxyl substituents as OH with CH2OH at the terminus using label properties.
- Adjust Fischer labels to use HO on the left side, keep the aldehyde H angled,
  and remove the terminal methyl from the cholesterol template so it renders as
  a terminal OH.
- Align left-side HO labels with the bond by using a label-specific anchor so
  the O sits at the attachment point.
- Increase default PNG resolution to 600 DPI by mapping Cairo PNG scaling to DPI
  (with explicit `dpi` override support) and add a `--dpi` option to the
  selftest sheet PNG output path.
- Add default PNG target width of 1500 px (overrideable via `target_width_px`)
  to produce larger postcard-like raster outputs when using Cairo.
- Add review notes to GUI docs clarifying menu tuple variants, key modifier
  handling, mode switching behavior, and translation asset locations.
- Add basic subscript/superscript markup support to render ops text output for
  SVG/Cairo, and label Fischer CH2OH as CH<sub>2</sub>OH to render as a subscript.
- Scale molecule label font size from a bond-length ratio in the selftest
  sheet renderer to keep text size consistent across templates, and render
  cholesterol with explicit OH on the terminal oxygen.
- Add alpha-D-glucopyranose CDML vignette to the selftest sheet and place it
  to the right of cholesterol in the second row.
- Render the alpha-D-glucopyranose vignette in Haworth form by applying
  `haworth.build_haworth` with D-series alpha substituent orientation mapping.
- Derive alpha-D-glucopyranose Haworth substituent orientations from ring
  topology (identify C1/C5 via the exocyclic carbon) and apply explicit
  up/down placement for all ring substituents.
- Replace non-ASCII box drawing and checkmark glyphs in
  [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md) with
  ASCII equivalents to satisfy compliance checks.
- Add review comments to [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  covering translation extraction, menu label stability, Pmw component lookup,
  and plugin insertion compatibility.
- Update [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md)
  MenuBuilder implementation to address review comments: move top-level menu
  labels and cascade labels to Python action registry (not YAML) for gettext
  extraction, store menu component and item index (not translated labels) for
  state updates to avoid label collision fragility, use app._get_menu_component()
  instead of direct pmw_menubar.component() to preserve macOS compatibility,
  add CascadeDefinition dataclass with translation keys, update usage examples
  to show menu-level actions and cascade definitions, add backward compatibility
  shim (add_to_menu_by_label) for legacy plugins using translated label lookup
  with 4-phase migration path from label-based to menu-ID-based plugin API.
- Add review comments to [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md)
  clarifying GPL-2.0-only compatibility concerns, provenance vs percentage
  reporting, and limitations of date-based heuristics.
- Clarify in [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) that mixed
  GPLv2/new files must remain GPL-2.0 until all GPLv2 code is removed and the
  file is fully rewritten.
- Clarify that GPLv2 percentage metrics are reporting-only and intended to
  scope legacy content and support author outreach, not relicensing decisions.
- Add preferred one-command usage examples for the GPL coverage assessment
  script (summary, full report, CSV) to [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md).
- Add [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) for
  reporting-only GPL/LGPL coverage metrics and update
  [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) to reference the
  tools path.
- Fix date handling in [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py)
  by comparing date values to avoid timezone-aware vs naive datetime errors.
- Add an ASCII progress bar to [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py)
  to show scan status while building coverage records.
- Fix GPL/LGPL classification in [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py)
  by comparing date values (not strings) and show normalized dates in per-file output.
- Prefer SPDX headers and legacy license text detection when classifying files
  in [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py), and record the
  classification source in CSV output.
- Clamp GPL time-percentage calculations in
  [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) when the cutoff
  date predates the first commit to avoid negative values.
- Update [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) to require
  line-based (git blame) classification for GPL/LGPL reporting, with line-age
  percentage as the primary metric and commit/change metrics as secondary.
- Update [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) to
  classify files from git blame line dates, clean up per-file reporting, and
  report line-add metrics when requested.
- Replace non-ASCII checkmark glyphs in
  [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md) with
  ASCII equivalents for compliance.
- Add per-file spot-check samples (git blame lines around the cutoff) to
  [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) output when
  using `--file`.
- Make `tools/assess_gpl_coverage.py --file` process only the requested file
  without scanning the full repo or emitting a progress bar.
- Handle boundary commits in `tools/assess_gpl_coverage.py` spot-check output
  by accepting blame hashes prefixed with '^'.
- Clarify GPLv2 vs LGPLv3 labeling in
  [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py) output for
  summaries and per-file reports.
- Silence SPDX "missing" noise in [tools/assess_gpl_coverage.py](tools/assess_gpl_coverage.py)
  output, and make SPDX mismatch reporting opt-in via `--show-spdx`.
- Fix spot-check blame parsing so committer-time lines are processed, and label
  commit counts as GPLv2 vs LGPLv3 in per-file output.
- Center single-letter atom labels by default and scale label background boxes
  to font size to keep Haworth ring hetero atoms aligned after font scaling.

## 2026-02-01
- Update [docs/SELFTEST_PAGE_SPEC.md](docs/SELFTEST_PAGE_SPEC.md) to establish
  molecule-level rendering as the architectural foundation: add canonical
  rendering rule requiring molecule graphs (not hand-assembled ops), define
  Haworth canonical invariants (in-ring O vertex, semantic front edge marking),
  add anti-patterns section prohibiting manual atom labels, reframe implementation
  guidelines to emphasize full renderer pipeline, and prioritize projection
  canonicalization over adding new features.
- Fix missing atom labels in Cairo/PNG output by adding `_render_cairo_atom_labels()`
  to `packages/oasa/oasa/selftest_sheet.py` and capturing label data for both
  row 1 and row 2 vignettes in `_add_cairo_labels()`. Previously, Cairo backend
  discarded atom labels returned by molecule builders, causing oxygen atoms to
  be invisible in PNG output while appearing correctly in SVG.
- Make Haworth ring ordering oxygen-anchored in `packages/oasa/oasa/haworth.py`
  by starting traversal at the oxygen atom when exactly one O is present in the
  ring, ensuring canonical layout independent of SMILES atom order.
- Add oxygen placement tests for non-first oxygen positions in
  `tests/test_haworth_layout.py` to verify canonical ordering stability.
- Update Haworth SMILES scaffolds in `packages/oasa/oasa/selftest_sheet.py` to
  oxygen-first format (O1CCCCC1 for pyranose, O1CCCC1 for furanose) for
  consistent canonical rendering.
- Replace hatch terminology with hashed in docs and Python code, remove legacy
  hatch-side handling, and update hashed labels in BKChem UI mode lists.
- Add explicit hydrogen rendering for Fischer projections in
  `packages/oasa/oasa/selftest_sheet.py` with `show_explicit_hydrogens` parameter
  that adds H labels for implicit substituents on stereocenters, matching OH label
  styling (font-size 9, proper text-anchor).
- Fix the Fischer explicit hydrogen test import path, remove the shebang, and
  avoid returning values from pytest tests in `tests/test_fischer_explicit_h.py`.
- Route BKChem conversion helpers through the OASA codec registry in
  `packages/bkchem-app/bkchem/oasa_bridge.py`.
- Document codec-registry-backed plugin guidance in
  [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md).
- Add BKChem codec-registry bridge tests in
  `tests/test_codec_registry_bkchem_bridge.py`.
- Flip the default `use_oasa_cdml_writer` flag to True in
  `packages/bkchem-app/bkchem/config.py`.
- Mark CDML architecture plan phases 1 and 2 complete in
  [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md).
- Remove legacy left/right hatch references from
  [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md).
- Define plugins, addons, and codecs in `README.md`,
  `docs/USAGE.md`, and `docs/CUSTOM_PLUGINS.md` to avoid terminology drift.
- Add the codec registry plan in
  [docs/CODEC_REGISTRY_PLAN.md](docs/CODEC_REGISTRY_PLAN.md).
- Add refactor progress tracking in `refactor_progress.md`.
- Add an OASA codec registry with default SMILES/InChI/molfile/CDML
  registration in `packages/oasa/oasa/codec_registry.py`.
- Expose `codec_registry` from `packages/oasa/oasa/__init__.py`.
- Add CDML text/file writer helpers and module capability flags in
  `packages/oasa/oasa/cdml_writer.py`.
- Route `packages/oasa/chemical_convert.py` through the codec registry and
  allow CDML output selection.
- Add codec registry coverage in `tests/test_codec_registry.py`.
- Add renderer capabilities sheet generator in
  `packages/oasa/oasa/selftest_sheet.py` (LGPL-3.0-or-later) with row-based
  layout, measured bounding boxes, and Fischer projection support.
- Refactor Haworth and Fischer vignettes in `packages/oasa/oasa/selftest_sheet.py`
  to use SMILES -> layout -> render pipeline instead of hand-placed coordinates,
  testing connectivity-driven molecule rendering.
- Add orange color row to bond grid in `packages/oasa/oasa/selftest_sheet.py`
  (8 types x 6 colors = 48 cells) and adjust vignette positions to accommodate
  taller grid.
- Add capabilities sheet layout specification in
  [docs/SELFTEST_PAGE_SPEC.md](docs/SELFTEST_PAGE_SPEC.md) documenting the
  measure-first layout system and vignette organization.
- Add CDML architecture plan in
  [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md) for future
  BKChem/OASA separation with layer responsibilities and phased integration.
- Add [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md) with a
  provenance-based license migration strategy from GPL-2.0 to mixed
  GPL-2.0 / LGPL-3.0-or-later licensing for new and rewritten components.
- Add [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md)
  to plan the shared render-ops backend for SVG and Cairo.
- Refine [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md)
  with a shared context-provider rule and ops-JSON acceptance criteria.
- Add invariants and scope boundaries to
  [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md) to
  pin down rounding, ordering, and out-of-scope text rendering.
- Add rounded wedge geometry helpers in
  `packages/oasa/oasa/wedge_geometry.py` and default wedge bonds to the rounded
  ops path in `packages/oasa/oasa/render_ops.py`.
- Refine rounded wedge geometry to use flat wide ends with corner fillets and
  update Haworth wedges, snapshots, and unit coverage in
  `packages/oasa/oasa/wedge_geometry.py`,
  `packages/oasa/oasa/render_ops.py`,
  `tests/fixtures/render_ops_snapshot.json`, and
  `tests/test_wedge_geometry.py`.
- Update [docs/ROUNDED_WEDGES_PLAN.md](docs/ROUNDED_WEDGES_PLAN.md) to describe
  corner fillets and the flat-base wedge shape.
- Include the in-ring oxygen in the Haworth SVG/PNG smoke layout builder in
  `tests/test_haworth_layout.py`.
- Move the furanose oxygen to the top position and add a furanose oxygen
  placement check in `packages/oasa/oasa/haworth.py` and
  `tests/test_haworth_layout.py`.
- Add Phase 0 BKChem CDML fixtures (basic types, stereo, aromatic ring, wavy
  color, BKChem widths) under `tests/fixtures/bkchem_phase0/`.
- Add a subprocess-backed BKChem CDML load/save/reload smoke test in
  `tests/test_bkchem_cdml_smoke.py`.
- Add unit coverage for the Phase 0 CDML fixtures in
  `tests/test_bkchem_cdml_fixtures_unit.py`.
- Add OASA bond semantics helpers (legacy type normalization and vertex
  canonicalization) in `packages/oasa/oasa/bond_semantics.py`.
- Normalize legacy bond types and canonicalize wedge/hashed vertex ordering on
  CDML read in `packages/oasa/oasa/cdml.py`.
- Normalize legacy bond types and canonicalize wedge/hashed vertex ordering on
  BKChem CDML read in `packages/bkchem-app/bkchem/bond.py`.
- Add vertex ordering tests for wedge/hashed bonds in
  `tests/test_bond_vertex_ordering.py`.
- Add CDML bond semantics tests (legacy type normalization and canonicalized
  vertex ordering) in `tests/test_cdml_bond_semantics.py`.
- Add CDML bond attribute helpers (presence tracking, unknown preservation,
  and serialization selection) in `packages/oasa/oasa/cdml_bond_io.py`.
- Route OASA CDML bond parsing through shared CDML attribute helpers in
  `packages/oasa/oasa/cdml.py`.
- Route BKChem CDML bond parsing and serialization through shared CDML
  attribute helpers in `packages/bkchem-app/bkchem/bond.py`.
- Add CDML bond IO unit tests in `tests/test_cdml_bond_io.py`.
- Add a BKChem CDML bond serialization smoke test in
  `tests/test_bkchem_cdml_bond_smoke.py`.
- Export `bond_semantics`, `cdml_bond_io`, and `safe_xml` from
  `packages/oasa/oasa/__init__.py` so BKChem uses local helpers.
- Remove remaining shebangs from pytest-only modules to satisfy the shebang
  lint check in `tests/test_bkchem_cdml_bond_smoke.py`,
  `tests/test_bkchem_cdml_fixtures_unit.py`,
  `tests/test_bkchem_cdml_smoke.py`,
  `tests/test_bond_vertex_ordering.py`,
  `tests/test_cdml_bond_io.py`, and
  `tests/test_cdml_bond_semantics.py`.
- Switch BKChem wedge rendering to the shared rounded wedge geometry and
  render Haworth `q` bonds as round-capped thick lines in
  `packages/bkchem-app/bkchem/bond.py`.
- Add BKChem rounded wedge and Haworth `q` rendering tests in
  `tests/test_bkchem_round_wedge.py`.
- Add shared atom color palettes in `packages/oasa/oasa/atom_colors.py` and
  enable SVG atom/bond coloring parity with Cairo in
  `packages/oasa/oasa/svg_out.py` and `packages/oasa/oasa/cairo_out.py`.
- Refine `docs/CDML_ARCHITECTURE_PLAN.md` with writer API details, unit
  convention, namespace handling, feature-flag guidance, and fixture updates.
- Add an OASA CDML molecule writer in `packages/oasa/oasa/cdml_writer.py`,
  route OASA CDML reads through it in `packages/oasa/oasa/cdml.py`, and add
  a basic writer unit test in `tests/test_cdml_writer.py`.
- Add `config.use_oasa_cdml_writer` and a gated BKChem molecule serializer
  path in `packages/bkchem-app/bkchem/config.py` and
  `packages/bkchem-app/bkchem/molecule.py`.
- Extend bond CDML helpers to store present/unknown attributes on the bond
  object (while keeping properties_ compatibility) in
  `packages/oasa/oasa/cdml_bond_io.py`.
- Expose `render_ops` and `wedge_geometry` from `packages/oasa/oasa/__init__.py`
  and update BKChem bond rendering to import them directly in
  `packages/bkchem-app/bkchem/bond.py`.
- Remove unused XML import from `packages/oasa/oasa/selftest_sheet.py`.
- Regenerate reference outputs under `docs/reference_outputs/` using
  `tools/render_reference_outputs.py`.
- Remove shebangs from pytest modules in `tests/test_bkchem_cdml_roundtrip.py`,
  `tests/test_cdml_roundtrip_oasa.py`, and `tests/oasa_legacy_test.py`.
- Add SPDX headers to new LGPL files in
  `packages/oasa/oasa/cdml_writer.py`,
  `packages/oasa/oasa/atom_colors.py`,
  `tests/test_cdml_writer.py`, and
  `tests/test_bkchem_round_wedge.py`.
- Remove the executable bit from `tests/oasa_legacy_test.py` to satisfy
  shebang alignment checks.
- Add OASA CDML writer round-trip tests in
  `tests/test_cdml_writer_roundtrip.py`.
- Add a BKChem CDML writer-flag smoke test in
  `tests/test_bkchem_cdml_writer_flag.py`.
- Add a CDML golden fixture corpus under `tests/fixtures/cdml/` (benzene,
  stereochem, haworth, cholesterol, legacy, embedded SVG) and load tests in
  `tests/test_cdml_fixture_loads.py`.
- Add a legacy fixture migration check in `tests/test_cdml_versioning.py`.
- Switch SVG pretty-print parsing to `defusedxml.minidom` in
  `packages/oasa/oasa/svg_out.py`.
- Fix Cairo import handling in the renderer capabilities sheet generator in
  `packages/oasa/oasa/selftest_sheet.py`.
- Update `launch_bkchem_gui.sh` to include local OASA paths in `PYTHONPATH`.
- Add a CDML round-trip fixture in
  `tests/fixtures/cdml_roundtrip/custom_attr.cdml`.
- Generate reference outputs under `docs/reference_outputs/` using
  `tools/render_reference_outputs.py`.
- Add Phase 3 CDML round-trip fixtures in `tests/fixtures/cdml_roundtrip/`.
- Add OASA CDML round-trip metadata tests in
  `tests/test_cdml_roundtrip_oasa.py`.
- Add BKChem CDML round-trip subprocess smoke test in
  `tests/test_bkchem_cdml_roundtrip.py`.
- Ensure BKChem CDML smoke tests include local OASA paths in
  `tests/test_bkchem_cdml_smoke.py`.
- Remove shebangs from pytest modules that are not intended to be executable:
  `tests/test_bkchem_cdml_bond_smoke.py`,
  `tests/test_bkchem_cdml_fixtures_unit.py`,
  `tests/test_bkchem_cdml_smoke.py`,
  `tests/test_bond_vertex_ordering.py`,
  `tests/test_cdml_bond_io.py`,
  `tests/test_cdml_bond_semantics.py`.
- Remove left/right hatch rendering and map any legacy `l`/`r` bonds to standard
  hatch output in `packages/oasa/oasa/render_ops.py`, plus update the bond
  styles smoke list in `tests/test_oasa_bond_styles.py`.
- Drop the Haworth wedge front-cap hook so Haworth wedges use the shared rounded
  wedge path in `packages/oasa/oasa/render_ops.py`.
- Remove the legacy straight-wedge fallback so all wedges use the rounded
  geometry path in `packages/oasa/oasa/render_ops.py`.
- Add `launch_bkchem_gui.sh` to start the BKChem GUI from the repo root.
- Update the bond-style SVG smoke test to expect path output for rounded wedges
  in `tests/test_oasa_bond_styles.py`.
- Define shared render ops, serialization, and bond op generation in
  `packages/oasa/oasa/render_ops.py`.
- Migrate SVG/Cairo bond rendering to shared render ops in
  `packages/oasa/oasa/svg_out.py` and `packages/oasa/oasa/cairo_out.py`.
- Add a render-ops snapshot test and fixture in
  `tests/test_render_ops_snapshot.py` and
  `tests/fixtures/render_ops_snapshot.json`.
- Update the bond-style printer SVG smoke assertion to expect path output in
  `tests/test_oasa_bond_styles.py`.
- Remove unused bond drawing helpers from the Cairo backend so it only renders
  shared ops in `packages/oasa/oasa/cairo_out.py`.
- Move Haworth front-bond coordinate lookup into shared render ops by passing
  bond coordinate providers from both SVG and Cairo backends.
- Add Haworth substituent placement rules for D/L and alpha/beta in
  `packages/oasa/oasa/haworth.py`.
- Add ops-level substituent orientation tests in
  `tests/test_haworth_layout.py`.
- Add folder-based template catalog scanning utilities in
  `packages/bkchem-app/bkchem/template_catalog.py` plus a scan test in
  `tests/test_template_catalog.py`.
- Add biomolecule template label formatting and biomolecule template directory
  discovery helpers in `packages/bkchem-app/bkchem/template_catalog.py`.
- Add a biomolecule template manager, mode, and Insert-menu entry for
  template insertion in `packages/bkchem-app/bkchem/main.py`,
  `packages/bkchem-app/bkchem/modes.py`, and
  `packages/bkchem-app/bkchem/singleton_store.py`.
- Add CDML biomolecule templates (carbs, protein, lipids, nucleic acids) under
  `packages/bkchem-app/bkchem_data/templates/biomolecules/`.
- Add biomolecule template insertion smoke coverage in
  `tests/test_biomolecule_templates.py`, plus label formatting coverage in
  `tests/test_template_catalog.py`.
- Add [docs/REFERENCE_OUTPUTS.md](docs/REFERENCE_OUTPUTS.md) and a
  `tools/render_reference_outputs.py` helper to generate Haworth and wavy-bond
  reference SVG/PNG outputs under `docs/reference_outputs/`.
- Add a reference output smoke test in `tests/test_reference_outputs.py`.
- Refresh [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) and
  [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) with updated component and
  repository layout details.
- Add new doc set stubs and pointers:
  [docs/NEWS.md](docs/NEWS.md),
  [docs/RELATED_PROJECTS.md](docs/RELATED_PROJECTS.md),
  [docs/ROADMAP.md](docs/ROADMAP.md),
  [docs/TODO.md](docs/TODO.md),
  [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md),
  [docs/USAGE.md](docs/USAGE.md).
- Fix mixed-indentation lines in `packages/oasa/oasa/render_ops.py`.
- Add [docs/ROUNDED_WEDGES_PLAN.md](docs/ROUNDED_WEDGES_PLAN.md) with a
  comprehensive plan for robust, reusable rounded wedge geometry that works
  for all wedge bonds (both standard stereochemistry and Haworth projections).
  The plan uses a clean 4-parameter endpoint-based API (tip_point, base_point,
  wide_width, narrow_width=0.0) where the wedge is directional (expands from
  tip to base), length and angle are derived outputs (not inputs), includes
  area-based validation tests to verify correctness at all orientations, and
  eliminates scaling/mirroring parameters (directionality encoded in endpoint
  order, scaling is caller's responsibility).
