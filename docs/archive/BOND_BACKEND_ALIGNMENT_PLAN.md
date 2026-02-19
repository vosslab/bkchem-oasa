# Bond backend alignment plan

## Objective

Align BKChem and OASA bond semantics so bond types, attributes, and CDML
round-tripping share a single source of truth while keeping the BKChem GUI
responsible only for interaction and Tk rendering.

## Scope

- In scope: bond type semantics, CDML bond attributes, metadata preservation,
  and deterministic normalization rules shared by BKChem and OASA.
- Out of scope: UI redesign, new drawing tools, or template UX changes.
- GUI rendering parity (rounded wedges, Haworth front edge) is a follow-on step,
  not required for the initial alignment.

## Current state summary

- BKChem bond types include `n`, `w`, `h`, `a`, `b`, `d`, `o`, `s`, `q` in
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py).
- OASA bond types document `n`, `w`, `h`, `a`, `b`, `d`, `s`, `q` in
  [packages/oasa/oasa/bond.py](packages/oasa/oasa/bond.py).
- BKChem writes CDML bond attributes beyond OASA parsing
  (widths, center, auto_sign, equithick) in
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py).
- OASA CDML parsing reads `color` and `wavy_style` in
  [packages/oasa/oasa/cdml.py](packages/oasa/oasa/cdml.py).
- BKChem does not currently draw `q` in the GUI.
- Hashed bond direction depends on vertex ordering, not a side flag.

## Alignment plan

### Phase 0: Test harness and fixtures

Deliverables:
- Headless-ish BKChem render smoke harness that runs in CI.
- Curated fixture set checked in (start with the 6 files in this plan).

Pass criteria:
- All fixtures load and render with zero exceptions in current BKChem.
- BKChem load -> save -> reload succeeds on all fixtures.

### Phase 1: Canonical bond semantics in OASA

Deliverables:
- New helper module in OASA for bond type constants and normalization rules.
- Single canonical representation for hashed bonds (`type="h"` only).
- Deterministic vertex ordering rules for hashed and wedge bonds.
- Export a shared `canonicalize_bond_vertices(bond, layout_ctx)` helper that
  both BKChem and OASA must call.

Notes:
- Keep `wavy_style` and `line_color` on the bond object and in `properties_`.
- If needed, add optional `hash_phase` or `hash_offset` only to stabilize
  pattern alignment across backends.
- For wedge and hashed bonds, canonicalize vertices so v2 is the "front"
  endpoint based on layout geometry or ring traversal order.
- Do not change numeric formatting or geometry in this phase.

Pass criteria:
- Vertex ordering stability tests pass on wedge and hashed fixtures.
- No numeric formatting or geometry changes (diffs stay minimal).

### Phase 2: Shared CDML bond attribute helpers

Deliverables:
- OASA helper functions to read and write CDML bond attributes with stable
  ordering and consistent defaults.
- BKChem bond parsing and serialization use those helpers.
- Deterministic vertex ordering normalization on read for hashed and wedge
  bonds, written back out on save.

Rules:
- Preserve unknown attributes in `properties_` for round-tripping.
- Store BKChem-specific width attributes in `properties_` when OASA does not
  directly use them.
- Only serialize non-default attributes that were present on input unless
  explicitly set by the user.

Pass criteria:
- Round-trip invariants pass BKChem <-> OASA on `type`, `line_color`,
  `wavy_style`.
- Serialization policy test passes (do not emit defaults unless present).
- GUI smoke tests still pass (no crash).

### Phase 3: Metadata round-trip tests

Deliverables:
- Tests to confirm BKChem -> CDML -> OASA preserves bond metadata.
- Tests to confirm OASA -> CDML -> BKChem preserves bond metadata.
- Tests to confirm vertex ordering stays stable across load/save.
- Snapshot normalized attribute dicts, not raw XML ordering, unless a
  deterministic serializer is in place.

### Phase 4: Optional GUI parity

Deliverables:
- Add `q` rendering to the Tk canvas backend.
- Add rounded wedge rendering consistent with OASA render ops.
- Map hashed bond direction to deterministic vertex ordering rules.

This phase is explicitly optional and can be scheduled after Phase 3.

### Phase 5: Flip default and delete legacy paths

Deliverables:
- OASA-backed CDML path is the only supported serializer.

Pass criteria:
- Old BKChem CDML parsing and normalization code removed.

## Maintainability expansion beyond bonds

Use the same pattern: move one slice of semantics into a shared, pure OASA
module, and keep BKChem as a thin UI shell.

### Shared core boundaries

Define small OASA modules that BKChem imports:
- `cdml_io.py`: parse CDML into OASA objects and serialize back. No Tk, no
  rendering.
- `normalize.py`: canonical rules (vertex ordering, defaults emission policy,
  color normalization).
- `render_ops.py`: geometry and ops for rendering (already exists).

BKChem remains responsible for:
- event handling, selection, editing UI, and Tk canvas drawing.

### Next layers after bonds

#### Atom representation and labels

Shared parsing and serialization for:
- element, isotope, charge, radical
- explicit hydrogens, aromatic flags
- label text rules

#### Coordinates and transforms

Shared reading and writing of:
- atom positions, bond midpoints
- global scaling and page transforms

### Architecture enforcement tests

Tests should enforce "thin BKChem" without pixel diffs:
- Import boundary test: BKChem modules should not import OASA renderers, only
  `cdml_io` and `normalize`.
- Round-trip invariants: BKChem load/save uses OASA serializer.
- Minimal GUI smoke: open fixtures, render, no crash.

### Deletion gate

Maintainability only improves when legacy paths are removed:
- Keep OASA-backed CDML serialization as the only supported path.
- Remove legacy BKChem CDML parsing and normalization code once coverage is
  sufficient.

## Risks

- Deterministic vertex ordering is now the only source of hashed and wedge
  directionality, so nondeterminism on CDML read will flip stereochemistry or
  hashed appearance.
- GUI output drift: Phase 4 is required for visual parity but not for CDML
  correctness.

## Acceptance criteria

- Bond metadata round-trips without loss across BKChem and OASA for `type`,
  `line_color`, and `wavy_style`.
- CDML output ordering is deterministic for bond attributes.
- Hashed and wedge bond vertex ordering is deterministic after load/save.
- No BKChem GUI logic is moved into OASA; only shared semantics and CDML helpers
  are centralized.

## Test strategy

### GUI no-crash smoke tests

Goal: load and render curated CDML files without exceptions.

Approach:
- Run BKChem in a headless-ish mode (withdraw the root window).
- Load CDML, build internal objects, trigger canvas draw.
- Assert no exceptions during load or render.

Fixture set (5 to 10 files):
- `basic_types.cdml` (n, b, d, a)
- `stereo.cdml` (wedge + hashed)
- `aromatic.cdml` (aromatic ring)
- `wavy_color.cdml` (wavy + line_color + wavy_style)
- `bkchem_widths.cdml` (BKChem-only attributes: widths, equithick, auto_sign)
- `haworth.cdml` (if available)

### Round-trip invariants (attribute dict level)

Assertions:
- BKChem load -> save preserves `type`, `line_color`, `wavy_style`.
- Unknown attributes survive in `properties_`.
- The serialization policy is honored (only emit non-default attributes that
  were present on input unless explicitly set by the user).
- OASA load -> save preserves the same invariants.
- BKChem -> CDML -> OASA -> CDML -> BKChem preserves the same invariants.

### Vertex ordering stability tests

Fixtures:
- One wedge bond.
- One hashed bond.
- One ring bond with known traversal context.

Assertions:
- `canonicalize_bond_vertices(bond, layout_ctx)` produces stable ordering.
- After save and reload, the bond still has the same ordered endpoints.
- For wedge and hashed bonds, v2 is the "front" endpoint by the explicit rule.

### Visual smoke without pixel diffs

Approach:
- Generate SVG via OASA for the same fixtures.
- Assert presence/counts of primitives:
  - Wedge uses a filled path.
  - Hashed uses repeated segments.
  - Wavy uses a path with the expected class or style.

### Additional GUI risk categories

#### Atom labels and text layout

Goal: prevent common GUI regressions in labels, fonts, and text anchoring.

Smoke tests:
- Load and render fixtures with: "Cl", "NH4+", "13C", "O-", "Fe2+", "beta-D-Glc".
- Assert no crash.
- Round-trip: text strings and charge fields survive CDML read and write.

#### Coordinates and transforms

Goal: catch flips, scaling errors, or coordinate translation drift.

Smoke tests:
- Fixture with nontrivial coordinates, a rotated bond, and a ring.
- Assert bounding box stays within expected page window.
- Assert number of drawn ops is stable for the fixture.

### Golden fixture suite size

- Keep a small curated suite of 10 to 20 CDML fixtures.
- For each fixture, run:
  - BKChem: load + render no crash.
  - BKChem: save and reload no crash.
  - OASA: export SVG no crash.
  - Attribute dict invariants.
