# Render Layout Parity Test Spec (No New Dependencies)

## Goal

Add stronger automated checks that SVG and Cairo backends render the same
content geometry from the same render-ops input, without adding new
dependencies and without image/pixel diffing.

## Scope

- In scope:
  - Verify backend parity through render-ops invariants and backend-call capture.
  - Validate parity for generic molecule rendering and Haworth rendering.
  - Keep tests deterministic and fast in `pytest`.
- Out of scope:
  - PNG-vs-SVG visual/pixel similarity scoring.
  - Screenshot-based regression harnesses.
  - New external tools for rasterization or perceptual diff.

## Existing baseline

- Existing parity guard:
  `test_phase_c_render_pipeline.py`
  currently verifies both backends receive equal serialized ops payloads in one
  mocked pipeline path.
- Existing backend smoke checks confirm outputs are generated, but do not
  deeply assert parity semantics.

## Design constraints

1. No new dependencies.
2. Tests must run with current local setup; Cairo-only tests may be skipped when
   `pycairo` is unavailable.
3. Assertions must compare semantic content (geometry, text placement, style
   fields) rather than pixels.
4. Tests must use existing public helpers where possible.

## Test strategy

### Layer 1: Pipeline parity (mocked backend sinks)

Expand parity tests around `render_out` to capture ops passed to:

- `render_ops.ops_to_svg(...)`
- `_render_cairo(...)`

For each sample molecule/case, assert normalized ops payloads are identical.

Normalization rules:

- Use `render_ops.ops_to_json_dict(..., round_digits=3)`.
- Compare full serialized payloads, not only counts.

Cases:

- Simple atom/bond molecule with shown labels.
- Wedge/hashed/wavy style molecule.
- Haworth pyranose and furanose molecule samples.

### Layer 2: Geometry-invariant parity

For captured ops (before painter), assert shared invariants:

- identical op counts by type (`LineOp`, `TextOp`, `PathOp`, `PolygonOp`);
- identical global bbox for all geometry-bearing ops;
- identical connector endpoint sets for labeled connectors;
- identical text tuple set:
  `(text, x, y, anchor, font_size, font_name)`.

These checks catch drift even if future serialization order changes.

### Layer 3: Haworth-specific parity guard

Add focused Haworth parity checks for known regression areas:

- side-slot connector verticality invariants;
- connector endpoint-on-label-boundary invariants;
- preserved op IDs for key connector/label pairs.

Use representative sugars from archive mapping matrix:

- one aldopyranose;
- one ketohexofuranose;
- one case with dense hydroxyl layout.

## Implementation plan

### Phase A: Extend existing parity test module

Modify:

- `test_phase_c_render_pipeline.py`

Add:

- helper to capture ops payload from both sinks across multiple molecules;
- parametrized parity matrix over molecule fixtures;
- invariant-based assertions in addition to strict payload equality.

### Phase B: Haworth parity test module

Create:

- `test_render_layout_parity.py`

Add:

- Haworth case builder helpers using existing sugar/haworth generation path;
- capture-and-compare tests for SVG/Cairo sink payload parity;
- explicit assertions for connector and label invariants.

### Phase C: Optional Cairo execution parity

When `pycairo` is available, execute both backend entry points and assert no
exceptions plus equal captured ops payloads.

If Cairo is unavailable:

- skip with explicit reason;
- keep mocked parity checks active.

## Acceptance criteria

- Parity tests fail if any backend receives different ops payload for the same
  molecule input.
- Haworth regression class ("connector geometry drift") is covered by dedicated
  parity assertions.
- No new dependencies are introduced.
- Test runtime remains lightweight (unit/integration tier, not system visual).

## Non-goals and rationale

- No PNG-vs-SVG pixel comparison:
  - requires rasterization/tooling not present by default;
  - exceeds no-deps requirement;
  - semantic render-ops parity is sufficient for renderer-content consistency.
