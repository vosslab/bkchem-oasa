# Glyph Alignment Fixture Scaffold

This folder contains scaffold fixtures for diagnosing glyph-center extraction and bond alignment:

- `unit_01_isolated_glyph_fit.svg`
- `unit_02_mixed_subscript_no_bonds.svg`
- `unit_03_bonds_nearby_strokes.svg`
- `torture_4x4_grid.svg`

Each SVG has a sidecar JSON file with optional checks:

- `min_labels_analyzed`
- `max_outside_tolerance`
- `target_centerlines`
- `c_stripe_min_retention_ratio`
- `min_final_point_count_by_char`

Runner command:

```bash
source source_me.sh && python3 tools/run_glyph_alignment_fixture_runner.py
```

Output directory (default):

- `output_smoke/glyph_alignment_fixture_runner/`

Hard-fail mode:

```bash
source source_me.sh && python3 tools/run_glyph_alignment_fixture_runner.py --fail-on-expectation
```
