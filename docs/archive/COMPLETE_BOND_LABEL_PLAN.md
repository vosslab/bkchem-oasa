# Complete bond-label attachment plan

Status: Closed (2026-02-10). This file is archived as the historical
source-of-record with recovery addendum closure evidence.

Define one attachment engine that handles all bond-to-label attachment in OASA
and BKChem, remove renderer-specific attachment exceptions, and make overlap
behavior deterministic across SVG, PNG, PDF, and BKChem canvas rendering.

Follow-on to
[docs/archive/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](../archive/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md),
which delivered shared bbox clipping but did not fully remove all specialized
attachment paths.

## Phase status

- [x] Phase A: Spec + engine + baseline matrix
- [x] Phase B: Migrate OASA renderers (molecular + Haworth)
  - [x] Phase B.1: Furanose side-chain stereography parity
- [x] Phase C: Migrate BKChem + decompose bond.py + delete compatibility code

## 2026-02-10 recovery addendum

This addendum preserves this file as the historical source of record while
documenting reopened closure work discovered after the original Phase C status
was marked complete.

Recovery status:
- R2 (BKChem duplicate draw-path deletion) is complete.
- R1 (Haworth endpoint text-branch policy removal) is complete.
- R3 (bbox-compatibility surface deletion guard) is complete.
- Release closure gate is complete: two consecutive full-suite runs are green.

Reopened closure gates:
- [x] Remove remaining Haworth text-branch endpoint policy in
  [packages/oasa/oasa/haworth/renderer.py](../../packages/oasa/oasa/haworth/renderer.py)
  (`text in ("OH", "HO")`, `_compute_hydroxyl_endpoint`, and related
  branch/fallback endpoint policy paths).
- [x] Keep removed bbox compatibility surfaces absent from production APIs/fields.
- [x] Enforce release closure by two consecutive full-suite green runs.

Execution checklist:
- Use the `R0 audit checklist commands (2026-02-10)` section below for exact
  grep/test commands for each deletion gate.
- Completed 2026-02-10 with DG-1/2/3 grep+test gates passing and two
  consecutive full-suite runs passing.

## R0 audit checklist commands (2026-02-10)

Concrete, copy-paste audit commands for R0 deletion/closure gates.

### Environment preflight

Run these first from repo root:

```bash
git rev-parse --show-toplevel
source source_me.sh
/opt/homebrew/opt/python@3.12/bin/python3.12 --version
```

Expected:
- repo root path prints
- `source_me.sh` loads without error
- Python reports `3.12.x`

### Deletion gate DG-1: BKChem duplicate draw geometry entry points

Goal:
- No legacy duplicated `_draw_*` geometry pipeline entry points remain active.

DG-1 grep commands:

```bash
rg -n 'def _draw_(n|h|d|w|a|s|b|o)[123]?\b|def _draw_(hashed|dash|second_line|wedge|adder|wavy|bold_central|dotted)\b' \
  packages/bkchem-app/bkchem/bond.py \
  packages/bkchem-app/bkchem/bond_drawing.py \
  packages/bkchem-app/bkchem/bond_render_ops.py
```

```bash
rg -n 'getattr\(.+_draw_|self\._draw_[a-z0-9_]+' \
  packages/bkchem-app/bkchem/bond.py \
  packages/bkchem-app/bkchem/bond_render_ops.py
```

Pass criteria:
- both commands return no matches for legacy per-type geometry draw paths

DG-1 test commands:

```bash
source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest \
  tests/test_phase_c_render_pipeline.py \
  tests/test_bkchem_round_wedge.py
```

Pass criteria:
- tests pass with no failures

### Deletion gate DG-2: Haworth endpoint text-branch policy removal

Goal:
- Endpoint legality is target/constraint driven, not label-text branch driven.

DG-2 grep commands:

```bash
rg -n 'text in \("OH", "HO"\)|_compute_hydroxyl_endpoint|str\(label\) == "CH\(OH\)CH2OH"' \
  packages/oasa/oasa/haworth/renderer.py
```

```bash
rg -n 'text in \("OH", "HO"\)' \
  packages/oasa/oasa/haworth/renderer_layout.py
```

Pass criteria:
- first command has no matches in endpoint policy paths
- second command has no matches for layout policy branches by label text

DG-2 test commands:

```bash
source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest \
  tests/test_haworth_renderer.py \
  tests/smoke/test_haworth_renderer_smoke.py
```

Pass criteria:
- strict Haworth unit and smoke suites pass without exemptions

### Deletion gate DG-3: removed compatibility surface names stay removed

Goal:
- Removed bbox-era compatibility APIs/fields do not reappear in production.

DG-3 grep commands:

```bash
rg -n 'clip_bond_to_bbox|label_bbox_from_text_origin|label_bbox\(|label_attach_bbox_from_text_origin|label_attach_bbox\(|bbox_center\(|attach_bboxes|label_bboxes|job_text_bbox\(|text_bbox\(' \
  packages/oasa/oasa \
  packages/bkchem-app/bkchem
```

Pass criteria:
- no matches in production paths

DG-3 test commands:

```bash
source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest \
  tests/test_attach_targets.py \
  tests/test_connector_clipping.py
```

Pass criteria:
- canary and attachment unit tests pass

### Release gate commands (run after DG-1/2/3 pass)

```bash
source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest
```

```bash
source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest
```

Pass criteria:
- two consecutive full-suite green runs

### Audit record template

Use this template in PR description or audit notes:

```text
R0 audit date:
Reviewer:

DG-1 grep: PASS/FAIL
DG-1 tests: PASS/FAIL

DG-2 grep: PASS/FAIL
DG-2 tests: PASS/FAIL

DG-3 grep: PASS/FAIL
DG-3 tests: PASS/FAIL

Release run #1: PASS/FAIL
Release run #2: PASS/FAIL

Open blockers:
- ...
```

## Bbox naming inventory (tracked for refactor)

This inventory is the explicit Phase B/C rename backlog for attachment-related
`bbox` naming. Keep this list updated as items are migrated or deleted.

- `packages/oasa/oasa/render_geometry.py`
  - Phase C removed legacy compatibility surface:
    `label_bbox*`, `label_attach_bbox*`, `clip_bond_to_bbox`,
    `bbox_center`, `BondRenderContext.label_bboxes`,
    `BondRenderContext.attach_bboxes`.
  - Remaining `bbox` names are rectangle-local internals only (for example
    local box tuples and helper argument names) and are not compatibility APIs.
- `packages/oasa/oasa/haworth/renderer.py`
  - Phase B migrated active attachment paths to target primitives and removed
    remaining renderer-local bbox attachment calls; no active
    `label_bbox*`/`label_attach_bbox*` attachment usage remains.
- `packages/oasa/oasa/haworth/renderer_layout.py`
  - Phase B added `job_text_target(...)` and `text_target(...)`.
  - Phase C removed compatibility wrappers `job_text_bbox(...)` and
    `text_bbox(...)`.
- `tests/smoke/test_haworth_renderer_smoke.py`
  - Phase B helper renames completed:
    `_label_target`, `_connector_target_for_label`,
    `_hydroxyl_half_token_targets`.
- `tests/test_label_bbox.py`
  - Retained as a geometry regression module; no removed compatibility API is
    called (canary assertions enforce deletion).

## Done checklist

- [x] All attachment endpoints route through one shared target API.
- [x] OASA molecular path has zero direct clipping exceptions.
- [x] Haworth path has zero attachment exceptions.
- [x] BKChem path has zero standalone attachment clipping logic.
- [x] No label-type-specific overlap bypass exists in tests.
- [x] Cross-backend endpoint parity gates pass.
- [x] Archive matrix smoke passes with strict overlap gates.
- [x] No bbox-named compatibility attachment APIs remain in production code.
- [x] `bond.py` decomposed into `bond.py` + 3 mixin modules
      (`bond_drawing.py`, `bond_display.py`, `bond_cdml.py`) while preserving
      current visual behavior.
- [x] Documentation is updated for the Phase C cutover state.

## Core principles

Read this section first. Every design decision and migration rule below follows
from these six principles.

1. **Geometry defines legality, never label text or renderer identity.**
   A connector endpoint is legal or illegal based solely on the target shape
   (box, circle, segment) and its constraints. The engine never inspects
   whether the label says `OH`, `CH3`, or anything else, and never checks
   which renderer is calling it.

2. **Different behavior requires different inputs, not different branches.**
   Haworth needs vertical-only connectors for bottom-row hydroxyls and circle
   targets for oxygen. Those differences enter the engine as different
   `AttachTarget` and `AttachConstraints` values. The engine itself has zero
   renderer-aware or label-aware conditionals. If you find yourself writing
   `if renderer == ...` or `if text == ...` inside the engine, the design is
   wrong; push the distinction into the caller's target/constraint selection.

3. **Tests validate geometric invariants, not cosmetic appearance.**
   Overlap gates check painted geometry against target-derived forbidden
   regions. No test may exempt a label by its text content. No test may
   weaken a threshold to accommodate a specific renderer.

4. **No function, variable, or field should be named `bbox` unless it is
   exclusively an axis-aligned rectangle.**
   The current codebase calls everything `bbox` - including circles (Haworth
   oxygen), directional apertures, and polymorphic target lookups. This is
   wrong. A circle is not a bounding box. This plan introduces `AttachTarget`
   as the polymorphic type. Every `bbox`-named function, dict key, field, and
   test helper must be renamed or deleted. After Phase C, the word `bbox`
   must not appear in any attachment-related production code or test helper.
   If geometry flows through rectangle-named pipes while the actual shape is
   a circle, the code is lying about what it does.

5. **Additive migration with rollback path.**
   New API ships first. Old functions become thin wrappers that delegate to
   the new engine. Wrappers are removed only after all callers are migrated
   and gates are green. No migration step may break an existing caller.

6. **Canary tests prove the new path is active.**
   Removing a wrapper or compatibility path requires a test that would fail
   if the old code path were still running. This prevents a silent fallback
   where the wrapper is gone but some caller quietly gets a default that
   happens to work by accident.

## Background

### Why old plan fell short

The archived plan standardized bbox clipping and token intent (`first|last`),
but full unification is still incomplete:

- Haworth keeps specialized oxygen-target logic and slot constraints in
  [packages/oasa/oasa/haworth/renderer.py](../../packages/oasa/oasa/haworth/renderer.py).
- BKChem still computes attachment clipping in its own path using Tk metrics in
  [packages/bkchem-app/bkchem/bond.py](../../packages/bkchem-app/bkchem/bond.py).
- Some tests still rely on label-class-specific overlap exemptions instead of a
  unified legality contract.

Result: behavior drifts even when global tests pass.

### Blocking findings

These findings are explicitly in scope and must be resolved by the end of
Phase C:

- Hashed branch rendering still relies on a near-invisible carrier plus filtered
  hatch spans, which can look detached from the attached token.
- One overlap regression assertion is effectively non-protective
  (`overlap >= 0.0`) and must be replaced with the strict `epsilon = 0.5 px`
  penetration threshold defined in the strict overlap gate section below.
- Smoke overlap gates still exempt many own non-hydroxyl connectors, allowing
  regressions to pass.
- Documentation and changelog path references can drift and must be checked by
  release hygiene.

## Scope

In scope:
- OASA molecular rendering via
  [packages/oasa/oasa/render_geometry.py](../../packages/oasa/oasa/render_geometry.py).
- OASA Haworth schematic rendering via
  [packages/oasa/oasa/haworth/renderer.py](../../packages/oasa/oasa/haworth/renderer.py).
- BKChem attachment paths in
  [packages/bkchem-app/bkchem/bond.py](../../packages/bkchem-app/bkchem/bond.py) and
  related label-leader attachment callers.
- Shared geometry APIs and shared overlap test gates.
- Nomenclature migration from `bbox` to `target` across production and test
  code.
- Documentation updates for the final attachment contract.

Out of scope:
- General glyph-outline clipping for all fonts (token-level geometric
  approximation is sufficient for this plan).
- New chemistry semantics in CDML beyond existing optional `attach_atom`.

## Core production files

These are the production source files this plan expects to touch, with the
attachment-relevant functions in each. Test files are omitted.

### Primary targets (heavy changes)

**packages/oasa/oasa/render_geometry.py** (822 lines) - shared geometry
producer for Cairo/SVG drawing. Central module for this plan.

Current attachment functions:
- `BondRenderContext` dataclass - fields `label_bboxes`, `attach_bboxes`
  (both `dict | None`).
- `build_bond_ops(edge, start, end, context)` - main bond rendering; reads
  `context.attach_bboxes` / `context.label_bboxes`, calls
  `directional_attach_edge_intersection()` and `bbox_center()`.
- `label_bbox(x, y, text, anchor, font_size, font_name)` - axis-aligned bbox
  for a text label.
- `label_bbox_from_text_origin(...)` - same, from text-origin coords.
- `label_attach_bbox(x, y, text, ..., attach_atom)` - bbox for first/last
  attachable atom token within a label.
- `label_attach_bbox_from_text_origin(...)` - same, from text-origin coords.
- `clip_bond_to_bbox(bond_start, bond_end, bbox)` - clip bond_end to bbox
  edge via `geometry.intersection_of_line_and_rect()`.
- `bbox_center(bbox)` - center point of an axis-aligned bbox.
- `directional_attach_edge_intersection(bond_start, attach_bbox,
  attach_target)` - directional token-edge endpoint (horizontal/vertical
  dominant).
- `molecule_to_ops(mol, style, transform_xy)` - builds `label_bboxes` and
  `attach_bboxes` dicts, populates `BondRenderContext`.
- `_tokenized_atom_spans(text)` - helper tokenizing atom labels for
  first/last token bbox extraction.

**packages/oasa/oasa/haworth/renderer.py** (1,482 lines) - Haworth schematic
renderer. Contains all the inlined circle and hydroxyl attachment logic that
must move into the shared engine.

Current attachment functions:
- `_add_simple_label_ops(...)` - adds connector + label with extensive
  attachment logic; calls `label_attach_bbox_from_text_origin()`,
  `label_bbox_from_text_origin()`, `directional_attach_edge_intersection()`,
  and contains the inlined hydroxyl endpoint math.
- `_compute_hydroxyl_endpoint(...)` (nested closure) - computes oxygen center
  via `renderer_text.hydroxyl_oxygen_center()`, clips to circle boundary,
  applies vertical circle intersection for BR/BL/TL slots, enforces
  clearance.
- `_clip_to_circle_boundary(start, center, radius)` - ray-circle intersection
  returning boundary point.
- `_vertical_circle_intersection(vertex, center, radius)` - vertical-line
  circle intersection for slot-constrained connectors.
- `_enforce_hydroxyl_clearance(connector_end, vertex, oxygen_center,
  oxygen_radius, lock_vertical)` - retreats endpoint outside clearance
  radius.
- `_retreat_endpoint_until_clear(line_start, line_end, line_width,
  label_box)` - retreats endpoint until connector paint no longer penetrates
  label interior.
- `_clip_ring_edge_oxygen_endpoint(...)` - clips oxygen-side ring edge
  endpoint.
- `_clip_segment_endpoint_to_circle(start, end, center, radius)` - clips
  segment endpoint to circle boundary.
- `_add_furanose_two_carbon_tail_ops(...)` - branched sidechain rendering
  with attachment bboxes and `directional_attach_edge_intersection()` calls.
- Hardcoded label-string checks: `text in ("OH", "HO")` at multiple sites,
  `str(label) == "CH(OH)CH2OH"` for furanose two-carbon tail.

**packages/bkchem-app/bkchem/bond.py** (1,881 lines) - BKChem bond drawing class
with legacy Tk-metric clipping. This file is too large for a single module and
will be decomposed during Phase C. See the bond.py decomposition section below.

Current attachment functions:
- `_where_to_draw_from_and_to(self)` - computes bond endpoints; gets atom
  bboxes and calls `geometry.intersection_of_line_and_rect()` directly for
  clipping. This is the standalone clipping path that must migrate to the
  shared engine.

Current internal structure (92 methods, single `bond` class):
- Core model + properties (~350 lines): `__init__`, 13 property pairs,
  `read_standard_values`, `get_atoms`, `change_atoms`.
- Drawing infrastructure (~240 lines): `draw` dispatcher,
  `_where_to_draw_from_and_to`, `_polygon_bond_mask`, `_polygon_cap`,
  `_draw_second_line`, `_get_3dtransform_for_drawing`,
  `_create_*_with_transform` wrappers.
- Type-specific drawing (~810 lines): 46 `_draw_*` methods covering normal,
  hashed, dashed, wedge, zigzag, wavy, bold, Haworth, and dotted bond types.
- Display and interaction (~110 lines): `redraw`, `simple_redraw`, `focus`,
  `unfocus`, `select`, `unselect`, `move`, `delete`, `bbox`, `lift`,
  `transform`.
- Serialization (~180 lines): `read_package`, `post_read_analysis`,
  `get_package`.
- Type/order management (~160 lines): `toggle_type`, `switch_to_type`,
  `switch_to_order`, `_decide_distance_and_center`,
  `_compute_sign_and_center`, `get_exportable_items`.

### Secondary targets (moderate changes)

**packages/oasa/oasa/haworth/renderer_text.py** (213 lines) - text formatting
and positioning helpers for Haworth rendering. Provides the glyph-center
estimates used by the inlined circle math.

Current attachment functions:
- `hydroxyl_oxygen_center(text, anchor, text_x, text_y, font_size)` -
  approximate oxygen glyph center in OH/HO label.
- `hydroxyl_oxygen_radius(font_size)` - approximate oxygen glyph radius.
- `leading_carbon_center(text, anchor, text_x, text_y, font_size)` -
  approximate leading-carbon glyph center for C* labels.

Migration role: these functions **stay** but their role changes. Currently
their output is consumed by inlined circle math in `renderer.py`. After
Phase B, they become data suppliers for `AttachTarget` construction:
`hydroxyl_oxygen_center()` provides the `center` field and
`hydroxyl_oxygen_radius()` provides the `radius` field of
`AttachTarget(kind="circle", center=..., radius=...)`. The inlined math
that currently consumes these values is deleted (see Haworth helper
function dispositions table in the unified target contract section below).

**packages/oasa/oasa/haworth/renderer_layout.py** (366 lines) - hydroxyl
layout optimizer. Uses label bboxes for overlap penalty calculation.

Current attachment functions:
- `job_text_bbox(job, length)` - approximate text bbox for placement job via
  `label_bbox_from_text_origin()`.
- `text_bbox(text_x, text_y, text, anchor, font_size)` - shared label bbox
  from text geometry.
- `overlap_penalty(box, occupied_boxes, gap)` - summed overlap area.
- `hydroxyl_job_penalty(job, occupied, blocked_polygons, min_gap)` - overlap
  penalty using `job_text_bbox()`.

### Supporting files (light or no changes)

**packages/oasa/oasa/geometry.py** (600 lines) - low-level geometry.
- `intersection_of_line_and_rect(line, rect, round_edges)` - line-rect
  intersection used by `clip_bond_to_bbox()` and `bond.py`.
- `do_rectangles_intersect(rect1, rect2)` - rectangle overlap test.

**packages/oasa/oasa/misc.py** (233 lines) - miscellaneous utilities.
- `normalize_coords(coords)` - normalize `(x1, y1, x2, y2)` so min comes
  first. Used by every `bbox`-named function.

**packages/oasa/oasa/haworth/renderer_geometry.py** (166 lines) - pure
computational geometry for Haworth rendering.
- `intersection_area(box_a, box_b, gap)` - intersection area with gap.
- `point_in_box(point, box)` - point-in-bbox test.
- `box_overlaps_polygon(box, polygon)` - bbox-polygon intersection.

**packages/oasa/oasa/render_ops.py** (605 lines) - render op dataclasses
(`LineOp`, `TextOp`, `PathOp`, `PolygonOp`). No attachment logic today;
`AttachTarget` dataclass may live here or in `render_geometry.py`.

**packages/oasa/oasa/wedge_geometry.py** (281 lines) - rounded wedge bond
geometry. No attachment functions, but wedge path generation must consume the
clipped endpoint from `resolve_attach_endpoint()` so full painted shape
respects attachment legality.

## Unified target contract

### Target primitives

Add a shared `AttachTarget` abstraction in
[packages/oasa/oasa/render_geometry.py](../../packages/oasa/oasa/render_geometry.py)
or a dedicated helper module if that keeps responsibilities cleaner.

```python
@dataclasses.dataclass(frozen=True)
class AttachTarget:
    """Polymorphic attachment target for bond endpoint resolution."""
    kind: str                       # "box", "circle", "segment", "composite"
    # box fields (axis-aligned rectangle)
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    # circle fields
    center: tuple[float, float] | None = None
    radius: float = 0.0
    # segment fields (directional aperture)
    seg_start: tuple[float, float] | None = None
    seg_end: tuple[float, float] | None = None
    # composite fields (ordered list: primary, then fallbacks)
    children: tuple['AttachTarget', ...] = ()

    def centroid(self) -> tuple[float, float]: ...
    def contains(self, point: tuple[float, float]) -> bool: ...
    def boundary_intersection(
        self,
        ray_origin: tuple[float, float],
        ray_toward: tuple[float, float],
    ) -> tuple[float, float]: ...
```

Required primitive kinds:
- `box`: axis-aligned rectangle. Replaces bare `(x1, y1, x2, y2)` tuples.
- `circle`: center + radius. Replaces the ad-hoc oxygen circle logic currently
  inlined in `_compute_hydroxyl_endpoint()` and `_clip_to_circle_boundary()`.
- `segment`: narrow directional aperture for constrained token-edge entry.
- `composite`: ordered list of children with primary + fallback resolution.

### Constraints

```python
@dataclasses.dataclass(frozen=True)
class AttachConstraints:
    """Geometric constraints applied during endpoint resolution."""
    line_width: float = 0.0         # connector stroke width for clearance
    clearance: float = 0.0          # extra safety margin beyond boundary
    vertical_lock: bool = False     # preserve vertical-only endpoint movement
    direction_policy: str = "side"  # "side" or "vertical" for ambiguous entry
```

### Function name mapping

The table below shows every current `bbox`-named function and its replacement.
Phase A adds the new functions; Phases B and C migrate callers and delete the
old names.

| Current name | Replacement | Notes |
| --- | --- | --- |
| `label_bbox(x, y, text, ...)` | `label_target(x, y, text, ...) -> AttachTarget` | Returns `AttachTarget(kind="box", ...)` |
| `label_bbox_from_text_origin(...)` | `label_target_from_text_origin(...) -> AttachTarget` | Same, from text-origin coords |
| `label_attach_bbox(x, y, text, ..., attach_atom)` | `label_attach_target(x, y, text, ..., attach_atom) -> AttachTarget` | Attach-token subset target |
| `label_attach_bbox_from_text_origin(...)` | `label_attach_target_from_text_origin(...) -> AttachTarget` | Same, from text-origin coords |
| `clip_bond_to_bbox(bond_start, bond_end, bbox)` | `resolve_attach_endpoint(bond_start, target, ...)` | Polymorphic: box clips to rect edge, circle clips to circle boundary |
| `bbox_center(bbox)` | `AttachTarget.centroid()` | Method on the target, not a free function on tuples |
| `directional_attach_edge_intersection(bond_start, attach_bbox, attach_target)` | `resolve_attach_endpoint(bond_start, target, interior_hint, constraints)` | Subsumes directional logic via `direction_policy` constraint |
| `BondRenderContext.label_bboxes` | `BondRenderContext.label_targets: dict \| None` | `dict[vertex, AttachTarget]` |
| `BondRenderContext.attach_bboxes` | `BondRenderContext.attach_targets: dict \| None` | `dict[vertex, AttachTarget]` |

Layout optimizer renames (renderer_layout.py - called 13+ times):

| Current name | Replacement | Notes |
| --- | --- | --- |
| `job_text_bbox(job, length)` | `job_text_target(job, length) -> AttachTarget` | Returns `AttachTarget(kind="box", ...)` for placement penalty |
| `text_bbox(text_x, text_y, text, anchor, font_size)` | `text_target(...) -> AttachTarget` | Shared label target from text geometry |

Test helper renames:

| Current name | Replacement |
| --- | --- |
| `_label_bbox(op)` | `_label_target(op)` |
| `_connector_bbox_for_label(label)` | `_connector_target_for_label(label)` |
| `_hydroxyl_half_token_bboxes(text, box)` | `_hydroxyl_half_token_targets(text, target)` |

### Core API

The two primary functions of the shared engine:

```python
def resolve_attach_endpoint(
    bond_start: tuple[float, float],
    target: AttachTarget,
    interior_hint: tuple[float, float] | None = None,
    constraints: AttachConstraints | None = None,
) -> tuple[float, float]:
    """Resolve connector endpoint to target boundary.

    Dispatches on target.kind:
    - box: directional edge intersection (current directional_attach_edge_intersection logic).
    - circle: ray-circle intersection (current _clip_to_circle_boundary logic).
    - segment: project onto segment with direction preservation.
    - composite: try children in order, return first valid intersection.

    When constraints.vertical_lock is True, endpoint x is locked to bond_start x
    (current _vertical_circle_intersection behavior for BR/BL/TL slots).
    """
```

```python
def validate_attachment_paint(
    line_start: tuple[float, float],
    line_end: tuple[float, float],
    line_width: float,
    forbidden_regions: list[AttachTarget],
    allowed_regions: list[AttachTarget] | None = None,
) -> bool:
    """Check that connector paint does not penetrate forbidden target interiors.

    Uses target.contains() with epsilon inset for each forbidden region.
    Returns True if paint is legal (boundary touch allowed, interior
    penetration > 0.5 px is illegal).
    """
```

`validate_attachment_paint(...)` must compute forbidden regions from attachment
targets and constraints, not from cosmetic text mask polygons.

### Compatibility wrappers (Phase A only)

During Phase A, the old functions become thin wrappers:

```python
def clip_bond_to_bbox(bond_start, bond_end, bbox):
    """Deprecated: use resolve_attach_endpoint with AttachTarget."""
    target = AttachTarget(kind="box", x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3])
    return resolve_attach_endpoint(bond_start, target)

def bbox_center(bbox):
    """Deprecated: use AttachTarget.centroid()."""
    target = AttachTarget(kind="box", x1=bbox[0], y1=bbox[1], x2=bbox[2], y2=bbox[3])
    return target.centroid()
```

These wrappers exist only to keep old callers working during migration.
No new caller may use them after Phase A. They are deleted in Phase C.

### Haworth oxygen: from inlined circle math to AttachTarget

The Haworth renderer currently inlines circle-boundary math in
`_compute_hydroxyl_endpoint()`, `_clip_to_circle_boundary()`, and
`_vertical_circle_intersection()` (renderer.py lines 445-480). This is the
most concrete example of why `bbox` naming is wrong: the oxygen target is a
circle, not a rectangle.

Migration path:
- Phase A: `_compute_hydroxyl_endpoint()` stays but internally constructs
  `AttachTarget(kind="circle", center=oxygen_center, radius=oxygen_radius)`.
- Phase B: The renderer builds the circle target and passes it to
  `resolve_attach_endpoint()` with `AttachConstraints(vertical_lock=True)` for
  BR/BL/TL slots. The inlined `_clip_to_circle_boundary()` and
  `_vertical_circle_intersection()` functions are deleted.
- Phase C: No Haworth-specific circle code remains; all circle clipping lives
  in `resolve_attach_endpoint()`.

### Haworth helper function dispositions

Every Haworth-specific attachment helper in `renderer.py` maps to a shared
engine replacement. This table is the authoritative list for Phase B deletion.

| Current function | Disposition | Replacement |
| --- | --- | --- |
| `_compute_hydroxyl_endpoint()` | Delete | Caller builds `AttachTarget(kind="circle")` from `renderer_text` helpers, passes to `resolve_attach_endpoint()` |
| `_clip_to_circle_boundary()` | Delete | `resolve_attach_endpoint()` with `AttachTarget(kind="circle")` |
| `_vertical_circle_intersection()` | Delete | `resolve_attach_endpoint()` with `AttachConstraints(vertical_lock=True)` |
| `_enforce_hydroxyl_clearance()` | Delete | `AttachConstraints(clearance=...)` passed to `resolve_attach_endpoint()` |
| `_retreat_endpoint_until_clear()` | Delete | `validate_attachment_paint()` + `AttachConstraints(clearance=...)` |
| `_clip_ring_edge_oxygen_endpoint()` | Delete | `resolve_attach_endpoint()` with circle target for oxygen endpoint |
| `_clip_segment_endpoint_to_circle()` | Delete | `resolve_attach_endpoint()` with circle target |
| `_add_simple_label_ops()` | Refactor | Stays but loses inlined endpoint math; calls `resolve_attach_endpoint()` instead |
| `_add_furanose_two_carbon_tail_ops()` | Refactor | Stays but uses `AttachTarget` + `resolve_attach_endpoint()` for branch endpoints |

### Token selector precedence

Token selection must be deterministic and renderer-independent:
- If `attach_element` is present, it wins.
- Else use `attach_atom="first|last"` (default `first` when missing).
- If neither selector is present, use minimal deterministic defaults:
  `attach_atom="first"` only; avoid label-specific implicit defaults.

### Formula-aware labels (tight scope)

To support stable attachment while allowing limited display flips, add a small
formula parser for attachment-relevant labels only. This is not a general
chemistry formatter.

Required scope:
- Supported token classes: element symbols, integer counts, optional trailing
  charge.
- Supported examples: `OH`/`HO`, `CH3`/`H3C`, `CH2OH`/`HOH2C`, `NH3+`/`H3N+`, `COOH`/`HOOC`.
- Do not attempt arbitrary grammar or full formula normalization.

Required outputs:
- `parse_formula(label) -> (tokens, charge, attach_default)` where `tokens` are
  element/count units and `attach_default` can provide stable element intent
  (for example `O` for hydroxyl class, `C` for methyl class).
- `render_formula(tokens, charge, style)` for markup only (`html`, later other
  backends as needed).

Required separation of concerns:
- Parsing/tokenization and markup rendering must be separate functions.
- Display canonicalization (for example `OH` vs `HO`, `CH3` vs `H3C`) must be
  explicit policy, not side effects of formatting.
- Attachment selection must use selector precedence and token intent, not first
  rendered character position.

Required charge rule:
- Treat `+`/`-` as charge only when suffix-positioned (end of label, with
  optional adjacent digits in the suffix).
- Document this as a strict parser contract for this phase.

Required deterministic behavior:
- If display order is flipped for readability, attachment target remains on the
  selected element token (`attach_element=O` or `attach_element=C`) so bond
  connectivity does not drift.
- Avoid duplicated formula formatter paths to prevent divergence across
  backends.

Plan statement:
- Labels that resemble molecular fragments are tokenized into
  element-count-charge form. Rendering may reorder tokens for style
  (`OH`/`HO`, `CH3`/`H3C`), but attachment uses tokenized element selectors so
  connectivity is stable.

## Haworth special-case contract

Haworth special behavior is in scope for this plan, but it must be expressed as
contract inputs to the shared engine, not as renderer-only endpoint hacks.

### Required intent model

Define a small per-substituent intent payload for Haworth attachment calls:

- `site_id`: deterministic position id (`C1_up`, `C3_down`, etc.).
- `label_text`: rendered text token stream.
- `attach_selector`: `attach_element` or `attach_atom` selector.
- `target_shape`: one of shared primitives (`box`, `circle`, `segment`,
  `composite`).
- `connector_constraint`: optional `AttachConstraints` instance (`vertical_lock`,
  directional preference, slot lane).
- `bond_style`: `plain`, `wedge`, `hashed`, or `wavy`.

### Required behavioral rules

- No per-sugar-name renderer conditionals for attachment endpoints.
- Haworth vertical-only behavior is implemented by
  `AttachConstraints(vertical_lock=True)` passed to `resolve_attach_endpoint()`,
  not by inlined `_vertical_circle_intersection()` calls.
- Oxygen-targeted attachment (`OH`/`HO`) is represented by
  `AttachTarget(kind="circle", ...)` + selector, not hardcoded string branches
  in endpoint math.
- Two-carbon tail stereography is represented by `bond_style` plus constrained
  branch vector policy, then clipped through shared target logic.
- Rounded wedge and hashed rendering must consume the clipped label-end
  endpoint so full painted geometry obeys overlap legality.

### Known special cases that must be covered

- Upward regular hydroxyl connectors (current dominant overlap source).
- Furanose left/right two-carbon side-chain stereography parity.
- L-rhamnose terminal methyl visibility/placement parity.
- CH2OH/HOH2C reversible text orientation with stable attachment target.

### Acceptance criteria for Haworth contract completion

- Haworth attachment paths contain zero renderer-specific endpoint exceptions.
- All Haworth special-case behavior is configured through the shared intent
  payload and `AttachTarget`/`AttachConstraints` values.
- Strict overlap gate passes without label text exemptions.
- Archive matrix parity cases for side-chain stereography and methyl placement
  are green.

## Migration phases

### Phase A: Spec + engine + baseline matrix

Deliverables:
- Inventory all production attachment entry points (OASA molecular, Haworth,
  BKChem bonds, leader lines) and current special fallbacks.
- Commit baseline matrix fixtures for known regressions (Talose overlap,
  Allose/Gulose hashed branch issues, L-rhamnose methyl, two-carbon tail
  endpoints).
- Implement `AttachTarget` dataclass with `centroid()`, `contains()`, and
  `boundary_intersection()` methods for `box` and `circle` kinds.
- Implement `AttachConstraints` dataclass.
- Implement `resolve_attach_endpoint()` with box and circle dispatch.
- Implement `validate_attachment_paint()`.
- Add `label_target()`, `label_target_from_text_origin()`,
  `label_attach_target()`, `label_attach_target_from_text_origin()` as the
  new `AttachTarget`-returning functions.
- Wrap existing `bbox`-named functions as thin compatibility wrappers that
  delegate to the new implementations.
- Define token selector precedence and deterministic default selector rules.
- Keep all old entry points functional through wrappers.

Files:
- [packages/oasa/oasa/render_geometry.py](../../packages/oasa/oasa/render_geometry.py)
- new helper module if needed (for example
  `packages/oasa/oasa/attachment_geometry.py`)

Tests:
- Add one shared fixture source used by unit and smoke tests.
- Add unit tests for each primitive and constraint combination.
- Verify deterministic behavior across vertical, horizontal, diagonal entries.
- Add circle-target legality tests: endpoint on circle boundary and epsilon past
  endpoint enters forbidden interior while segment up to endpoint stays legal.
- Verify that old `bbox`-named wrappers produce identical results to the new
  `target`-named functions for all-box cases (wrapper parity tests).
- Require a test-clean baseline for targeted attachment suites before migration
  coding starts.

Key deliverable:
- `AttachTarget`, `AttachConstraints`, `resolve_attach_endpoint()`, and
  `validate_attachment_paint()` exist and are tested. Wrappers bridge old
  `bbox` callers. Baseline fixture matrix is committed.

### Phase B: Migrate OASA renderers (molecular + Haworth)

Deliverables:
- Migrate `build_bond_ops()` to use `AttachTarget` objects from
  `context.attach_targets` / `context.label_targets` instead of raw bbox
  tuples from `context.attach_bboxes` / `context.label_bboxes`.
- Replace `bbox_v1`/`bbox_v2` local variables in `build_bond_ops()` with
  `target_v1`/`target_v2` typed as `AttachTarget | None`.
- Replace calls to `directional_attach_edge_intersection()` with calls to
  `resolve_attach_endpoint()`.
- Replace calls to `bbox_center()` with `target.centroid()`.
- Replace `BondRenderContext.label_bboxes` / `.attach_bboxes` fields with
  `.label_targets` / `.attach_targets` typed as `dict | None`.
- Migrate `molecule_to_ops()` (render_geometry.py lines 765-804): this is
  the primary callsite that builds `label_bboxes` and `attach_bboxes` dicts
  and passes them to `BondRenderContext`. Must become `label_targets` and
  `attach_targets` dicts with `AttachTarget` values.
- Replace Haworth-specific endpoint exceptions with shared target primitives:
  oxygen attachment becomes `AttachTarget(kind="circle", center=...,
  radius=...)` with `AttachConstraints(vertical_lock=True)` for BR/BL/TL
  slots. Token attachments become `AttachTarget(kind="box", ...)` with
  appropriate `direction_policy`.
- Delete all 7 Haworth-inlined attachment helpers (see Haworth helper
  function dispositions table): `_compute_hydroxyl_endpoint()`,
  `_clip_to_circle_boundary()`, `_vertical_circle_intersection()`,
  `_enforce_hydroxyl_clearance()`, `_retreat_endpoint_until_clear()`,
  `_clip_ring_edge_oxygen_endpoint()`, `_clip_segment_endpoint_to_circle()`.
  Their behavior is now in `resolve_attach_endpoint()` via
  `AttachTarget(kind="circle")` + `AttachConstraints`.
- Rename layout optimizer functions in `renderer_layout.py`:
  `job_text_bbox()` to `job_text_target()`, `text_bbox()` to
  `text_target()` (see layout optimizer renames table).
- Rename smoke test helpers: `_label_bbox()` to `_label_target()`,
  `_connector_bbox_for_label()` to `_connector_target_for_label()`,
  `_hydroxyl_half_token_bboxes()` to `_hydroxyl_half_token_targets()`.
- Route Haworth special cases via the intent payload (selector, target,
  constraints, bond style) so behavior is declarative and testable.
- Remove label-specific overlap exemptions in production and tests. Existing
  fixtures that currently pass via exemption must still pass, but via
  target-geometry legality, not label-text bypass.
- Replace hashed branch fallback heuristics with target-resolved hashed endpoint
  behavior that remains visibly attached without a near-invisible carrier hack.
- For rounded wedge and hashed bonds, generate final geometry from the clipped
  label-end endpoint so the full shape respects attachment legality (not just a
  centerline approximation).
- Replace the non-protective `overlap >= 0.0` assertion with the strict
  `epsilon = 0.5 px` penetration threshold.

Files:
- [packages/oasa/oasa/render_geometry.py](../../packages/oasa/oasa/render_geometry.py)
- [packages/oasa/oasa/haworth/renderer.py](../../packages/oasa/oasa/haworth/renderer.py)
- [packages/oasa/oasa/haworth/renderer_text.py](../../packages/oasa/oasa/haworth/renderer_text.py)
- [packages/oasa/oasa/haworth/renderer_layout.py](../../packages/oasa/oasa/haworth/renderer_layout.py)
- [tests/test_connector_clipping.py](../../tests/test_connector_clipping.py)
- [tests/test_haworth_renderer.py](../../tests/test_haworth_renderer.py)
- [tests/smoke/test_haworth_renderer_smoke.py](../../tests/smoke/test_haworth_renderer_smoke.py)
- [tests/test_phase_c_render_pipeline.py](../../tests/test_phase_c_render_pipeline.py)

Tests:
- OASA endpoint parity across SVG/PDF/PNG must pass.
- Archive matrix must pass without label-specific exemptions.
- Add strict own-connector legality tests based only on target geometry.
- Add explicit hashed-branch attachment tests that fail on detached/floating
  terminal appearance.

Key deliverable:
- OASA has zero attachment exceptions, Haworth oxygen and token attachments are
  expressed as `AttachTarget` instances, `BondRenderContext` uses `target` field
  names, test helpers use `target` naming, and matrix smoke tests pass with
  strict overlap checks.

### Phase B.1 addendum: furanose side-chain stereography parity

This addendum is a focused parity task within Phase B.

#### Objective

Close the largest remaining visual/semantic gap vs reference outputs:
furanose two-carbon left-side chain stereography (hashed cue and above/below
placement impression).

#### Scope

In scope:
- Furanose two-carbon side-chain branch rendering in
  [packages/oasa/oasa/haworth/renderer.py](../../packages/oasa/oasa/haworth/renderer.py)
- Related parity tests in
  [tests/test_haworth_renderer.py](../../tests/test_haworth_renderer.py)
  and
  [tests/smoke/test_haworth_renderer_smoke.py](../../tests/smoke/test_haworth_renderer_smoke.py)

Out of scope:
- Reverting current OH/HO readability improvements.
- Per-sugar hardcoded special cases.

#### Required implementation rules

- Derive branch style and placement from one deterministic stereocenter rule
  for this side-chain class.
- Do not use per-code exceptions.
- Ensure hashed/dashed cue appears when expected by the parity class.
- Ensure side-chain branch vector and terminal label lane produce the expected
  above/below visual impression.
- Keep branch endpoints target-resolved (attachment legality still applies).

#### Required fixtures

Start with explicit known gap fixtures, including:
- D-galactose furanose alpha
- neighboring furanose two-carbon-tail cases in the same parity class

#### Acceptance criteria

- Ring geometry and bold-face edge conventions remain unchanged.
- Vertical substituent cleanliness remains unchanged.
- OH/HO collision improvements remain intact.
- Furanose left-side two-carbon tail hashed/plane cue matches expected parity
  class across the fixture set.
- Matrix smoke plus strict overlap gate remain green.

### Phase C: Migrate BKChem + delete compatibility code

Deliverables:
- Replace BKChem direct clipping path with shared target-resolution adapter.
- Keep BKChem font-metric placement if needed, but endpoint resolution must be
  shared and deterministic under adapter rules.
- Decompose `bond.py` (1,881 lines) into focused modules (see decomposition
  plan below).
- Remove dead compatibility branches and duplicated helpers. A function is dead
  if no production code path calls it after Phase C migration, verified by
  coverage analysis or grep across the full tree.
- Delete all `bbox`-named functions: `clip_bond_to_bbox()`, `bbox_center()`,
  `label_bbox()`, `label_bbox_from_text_origin()`, `label_attach_bbox()`,
  `label_attach_bbox_from_text_origin()`. All callers must use `AttachTarget`
  APIs by this point.
- Delete the `label_bboxes` / `attach_bboxes` fields from `BondRenderContext`.
- Remove test exemptions based on label class or renderer.
- Keep only contract-based legality checks.
- Add fail-fast CI gates for overlap and parity.
- Remove remaining blanket own-connector exemptions from smoke gates (except for
  explicitly modeled allowed target apertures).

Files:
- [packages/bkchem-app/bkchem/bond.py](../../packages/bkchem-app/bkchem/bond.py) (split
  into multiple files)
- BKChem leader-line modules that currently clip directly.

Tests:
- Add BKChem vs OASA endpoint equivalence fixtures for representative cases.
- Keep existing BKChem round/wedge and CDML roundtrip tests green.
- Full test suite must pass with no exception bypass flags.
- Add canary tests that fail if any removed wrapper is still being called
  (proving callers actually use the new path).

Key deliverable:
- BKChem endpoints are resolved via shared engine, standalone clipping paths are
  removed, all `bbox`-named APIs and fields are deleted, `bond.py` is
  decomposed into focused modules, and exception branches are gone.

### bond.py decomposition

Phase C is the right time to decompose `bond.py` because we are already
modifying its clipping path and touching its drawing infrastructure.
Decomposing during the same phase avoids a second destabilization pass later.

#### Render ops architecture (why this works)

OASA's render ops (`LineOp`, `PathOp`, `PolygonOp`, `TextOp` in
`render_ops.py`) are abstract drawing instructions with no backend
dependency. `build_bond_ops()` produces a list of render ops;
Cairo/SVG/PNG painters consume them to draw. The key insight for BKChem
migration is that a Tk canvas is just another consumer - a thin adapter
can convert `LineOp` to `canvas.create_line()`, `PolygonOp` to
`canvas.create_polygon()`, etc. This is why eliminating the duplicated
pipeline is feasible: BKChem does not need its own geometry, only its
own final paint call.

#### Why bond.py is 1,881 lines

Approximately 50% of `bond.py` (~900 lines, 46 `_draw_*` methods) is a **Tk
canvas rendering pipeline that duplicates geometry already in OASA's
`render_geometry.py`**. Both implement the same wedge, hashed, dashed, wavy,
bold, and dotted algorithms - `bond.py` outputs Tk canvas items via
`self.paper.create_line()`, while `render_geometry.py` outputs abstract
`LineOp`/`PathOp`/`PolygonOp` objects. The duplication is nearly line-for-line. Concrete example: `_draw_hashed()`
(bond.py:627) vs `_hashed_ops()` (render_geometry.py:150) - both call
`geometry.find_parallel()` to compute parallel offset lines, both iterate
to create hatch marks at the same intervals with the same width tapering.
Similarly, both call `wedge_geometry.rounded_wedge_geometry()` for wedge
shapes. bond.py has 17 calls to `geometry.find_parallel()` vs OASA's 5,
all computing the same offset geometry for the same bond types.

The other ~50% is genuinely BKChem-specific and cannot be replaced:
- UI interaction: select, focus, move, lift, delete, transform (~250 lines).
- Bond type toggling and double-bond auto-positioning (~310 lines).
- CDML serialization with `Store.id_manager` and paper coords (~130 lines).
- Properties, init, atom management (~300 lines).

#### Bond type inventory

The original upstream BKChem had 29 `_draw_*` methods for 8 bond types. We
added 14 methods for 3 new types (`s`, `q`, `l`/`r`) during Haworth Stage 2
work. The `l`/`r` types were an experimental Haworth approach that never went
anywhere - their order 2/3 methods are stubs that just delegate to `_draw_n2`
/ `_draw_n3`, they appear in zero CDML files, and they are not in the BKChem
UI mode list.

| Type | Char | Origin | In OASA `build_bond_ops()` | In BKChem UI modes | In CDML files | Action |
| --- | --- | --- | --- | --- | --- | --- |
| Normal | `n` | Upstream BKChem | Yes | Yes | Yes (dominant) | Keep |
| Wedge (out) | `w` | Upstream BKChem | Yes | Yes | Yes | Keep |
| Hashed (into) | `h` | Upstream BKChem | Yes | Yes | Yes | Keep |
| Wavy | `s` | Added for Haworth | Yes | No | 1 fixture | Keep |
| Haworth front | `q` | Added for Haworth | Yes | No | No | Keep |
| Adder (zigzag) | `a` | Upstream BKChem | No | Yes | 1 fixture | Keep, add to OASA |
| Bold | `b` | Upstream BKChem | Partial | Yes | 1 fixture | Keep, finish in OASA |
| Dashed | `d` | Upstream BKChem | No | Yes | 1 fixture | Keep, add to OASA |
| Dotted | `o` | Upstream BKChem | No | Yes | 1 fixture | Keep, add to OASA |
| Left-hashed | `l` | Added for Haworth | No | No | No | **Remove** |
| Right-hashed | `r` | Added for Haworth | No | No | No | **Remove** |

Source for "In BKChem UI modes" column: `modes.py:756` defines the bond type
submodes as `['normal','wedge','hashed','adder','bbold','dash','dotted']`.
Types not in this list (`s`, `q`, `l`, `r`) are not user-selectable.

OASA `build_bond_ops()` expansion required: add `d` (dashed), `o` (dotted),
`a` (adder/zigzag), and finish `b` (bold). This is ~150 lines of new geometry
code, reusing the identical math currently in bond.py's `_draw_dash`,
`_draw_dotted`, `_draw_adder`, and `_draw_bold_central`.

BKChem-specific context fields to add to `BondRenderContext`:
- `equithick: bool` - uniform-width hash/adder lines (applies to `h` and `a`).
- `simple_double: bool` - whether double bond second line uses same style.
- `double_length_ratio: float` - second line length ratio.
- `draw_start_hatch: bool` - skip first hash line when atom has occupied
  valency (derived from `atom.show` + `atom.occupied_valency`).
- `draw_end_hatch: bool` - same for end atom.

**`simple_double` dispatch pattern.** In bond.py, order-2/3 draw methods
choose between `_draw_second_line()` and the type-specific method (e.g.,
`_draw_hashed` for `h2`/`h3`, `_draw_wedge` for `w2`/`w3`) based on
`self.simple_double`. This pattern appears 6 times (at bond.py lines 588,
606, 916, 934, 1054, 1072). The OASA `build_bond_ops()` expansion must
replicate this dispatch: when `context.simple_double` is True, order-2/3
bonds draw a plain parallel line; when False, they draw the type-specific
variant. This is the most complex BKChem-specific behavior to port.

**`_draw_second_line()` note.** This method (~50 lines starting at
bond.py:815) is listed under "Drawing infrastructure" in the internal
structure breakdown, not under "Type-specific drawing." However, it is
also eliminated by the render ops migration because OASA's
`build_bond_ops()` already handles double/triple bond geometry for the
types it supports. After Step 2 expands OASA coverage, `_draw_second_line()`
has no remaining callers and is deleted with the other `_draw_*` methods
in Step 3.

#### Strategy: eliminate the duplicated pipeline, then split

Rather than just splitting 1,881 lines into mixin files (which preserves the
duplication), the decomposition has four steps:

**Step 1: Delete `l`/`r` bond types and their 9 methods** (`_draw_l1`,
`_draw_l2`, `_draw_l3`, `_draw_r1`, `_draw_r2`, `_draw_r3`,
`_draw_side_hashed`, plus the `l`/`r` references in `toggle_type` and
`get_exportable_items`). These were a Haworth experiment that produced no
CDML files, no UI mode entries, and no downstream usage. Remove the type
characters from `oasa.bond` as well.

**Step 2: Expand OASA `build_bond_ops()` to handle `d`, `o`, `a`, `b`.**
Add ~150 lines porting the identical geometry from bond.py's `_draw_dash`,
`_draw_dotted`, `_draw_adder`, `_draw_bold_central`. Add `equithick`,
`simple_double`, `double_length_ratio`, and hatch start/end skip fields to
`BondRenderContext`.

**Step 3: Replace the remaining ~37 `_draw_*` methods with OASA render ops +
thin Tk adapter.** The `draw()` method calls `render_geometry.build_bond_ops()`
to get abstract render ops, then a new `_render_ops_to_tk_canvas()` method
(~50 lines) converts them to Tk canvas items. This eliminates ~800 lines of
duplicated geometry and makes BKChem bond rendering use the exact same code
path as SVG/PDF/Cairo export. Net result: bond.py drops from ~1,880 to ~980
lines.

Remaining BKChem-specific rendering features (3D transform, paper coordinate
conversion) are handled in the thin Tk adapter as pre/post-processing around
the render ops call.

**Step 4: Split the remaining ~1,030 lines into focused modules.**

Target file structure:

| New file | Contents | ~Lines |
| --- | --- | --- |
| `bond.py` | `bond` class definition, `__init__`, properties, atom management, type/order management (`toggle_type`, `switch_to_*`, `_compute_sign_and_center`, `_decide_distance_and_center`), `read_standard_values` | ~500 |
| `bond_drawing.py` | `BondDrawingMixin`: `draw` dispatcher (now calls `build_bond_ops()` + `_render_ops_to_tk_canvas()`), `_render_ops_to_tk_canvas()`, `_where_to_draw_from_and_to` (migrated to `resolve_attach_endpoint()`), `_polygon_bond_mask`, `_polygon_cap`, `_get_3dtransform_for_drawing` | ~200 |
| `bond_display.py` | `BondDisplayMixin`: `redraw`, `simple_redraw`, `visible_items`, `focus`/`unfocus`, `select`/`unselect`, `move`, `delete`, `lift`, `transform` | ~110 |
| `bond_cdml.py` | `BondSerializationMixin`: `read_package`, `post_read_analysis`, `get_package`, `get_exportable_items` | ~220 |

After decomposition, `bond.py` becomes:

```python
from .bond_drawing import BondDrawingMixin
from .bond_display import BondDisplayMixin
from .bond_cdml import BondSerializationMixin

class bond(
    meta_enabled, line_colored, drawable, with_line,
    interactive, child_with_paper,
    BondDrawingMixin, BondDisplayMixin, BondSerializationMixin,
    oasa.bond,
):
    ...
```

There is no `bond_draw_types.py` - the `_draw_*` methods and their helpers
(`_draw_hashed`, `_draw_dash`, `_draw_adder`, `_draw_wavy`, `_draw_dotted`,
`_draw_side_hashed`, `_rounded_wedge_polygon`, `_arc_points`,
`_path_commands_to_polygon`) are deleted entirely. The `l`/`r` methods are
deleted with no replacement; the rest are replaced by `build_bond_ops()` +
the thin Tk adapter.

#### Rules for the decomposition

- Use `git mv` for the initial split to preserve blame history where possible.
- Each mixin module must be independently importable (no circular imports).
- No mixin may import from `bond.py` (dependency flows one way: `bond.py`
  imports the mixins).
- All existing tests must pass without modification to test imports (the
  `bond` class stays in `bond.py` and its public interface is unchanged).
- `_compute_sign_and_center` and `_decide_distance_and_center` stay in
  `bond.py` since they are core geometry logic called by both drawing and
  type management methods.
- `_where_to_draw_from_and_to` moves to `bond_drawing.py` and is migrated to
  use `resolve_attach_endpoint()` in the same change.
- The thin Tk adapter (`_render_ops_to_tk_canvas()`) must produce visually
  identical output to the old `_draw_*` methods for all bond types. Add
  visual regression fixtures before the migration.

#### Acceptance criteria

- Bond types `l` (left-hashed) and `r` (right-hashed) are deleted from
  `oasa.bond`, `bond.py`, and any remaining references.
- `build_bond_ops()` handles all 9 surviving bond types (`n`, `w`, `h`, `s`,
  `q`, `a`, `b`, `d`, `o`) including `equithick` and `simple_double` behavior.
- All `_draw_*` methods and their helpers are deleted from `bond.py`.
- `draw()` calls `build_bond_ops()` -> `_render_ops_to_tk_canvas()`.
- BKChem bond rendering uses the same geometry code path as SVG/PDF export.
- No file in `packages/bkchem-app/bkchem/` exceeds ~500 lines.
- All existing BKChem tests pass.

## Strict overlap gate

This gate is mandatory for Phase B and Phase C completion.

### Canonical validator

Add one canonical strict validator in
[tests/smoke/test_haworth_renderer_smoke.py](../../tests/smoke/test_haworth_renderer_smoke.py):

- `assert_no_bond_label_overlap_strict(ops, context)`
- No label-text exemptions (`OH`, `HO`, etc.).
- No own-connector exemptions except explicitly modeled target apertures.

### Geometry basis

Legality must be checked against painted geometry and target-based forbidden
regions:

- `LineOp`: use stroke radius (`width / 2`) against forbidden-region interior.
- `PathOp` (wedge) and `PolygonOp` bond shapes: validate the full painted shape
  envelope, not centerline approximations only.
- Forbidden regions come from attachment targets (`AttachTarget` instances with
  `contains()` checks), not cosmetic masks.

### Per-label legality rules

- Endpoint may terminate on target boundary.
- Connector paint may not enter strict forbidden interior (epsilon inset).
- Add epsilon sanity checks so boundary math remains deterministic.
- Numeric policy: edge touch is legal, and any penetration greater than
  `epsilon = 0.5 px` into forbidden interior is a hard failure.
- This `epsilon = 0.5 px` threshold replaces the current non-protective
  `overlap >= 0.0` assertion.
- Endpoint-retreat search may use a tighter numeric tolerance internally for
  binary-search stability, but acceptance/failure decisions must remain tied to
  the strict gate threshold above (`epsilon = 0.5 px`).

### Smoke/system enforcement

The strict validator must run for:

- matrix smoke render checks with `show_hydrogens=True`
- matrix smoke render checks with `show_hydrogens=False`
- full archive matrix checks

Failure messages must include:
- case id
- bond op id
- label op id
- overlap metric (distance/penetration value)

### Unit/regression coverage

Add targeted strict-gate tests in
[tests/test_haworth_renderer.py](../../tests/test_haworth_renderer.py):

- forced overlap fails
- edge-touch passes
- legal own-connector aperture case passes
- non-aperture own-connector penetration fails

### CI policy

Strict overlap tests are fail-fast release gates and cannot be optional.

## Regression prevention

### Test plan matrix

| Area | Test files | Gate |
| --- | --- | --- |
| Shared primitives | `tests/test_label_bbox.py`, new primitive tests | unit |
| OASA molecular | `tests/test_connector_clipping.py` | unit/integration |
| Haworth geometry | `tests/test_haworth_renderer.py` | unit/regression |
| Haworth matrix | `tests/smoke/test_haworth_renderer_smoke.py` | smoke/system |
| Backend parity | `tests/test_phase_c_render_pipeline.py`, `tests/test_render_layout_parity.py` | integration |
| BKChem parity | existing BKChem tests + new endpoint fixtures | integration/regression |

### Canary test policy

Every wrapper removal or compatibility path deletion must be accompanied by a
canary test that would fail if the old code path were still active. This
prevents silent fallback to removed defaults and proves the new `AttachTarget`
path is actually exercised.

Example: when `clip_bond_to_bbox()` is deleted in Phase C, a test must verify
that `build_bond_ops()` calls `resolve_attach_endpoint()` and that the result
is an `AttachTarget`-derived endpoint, not a raw tuple from the old wrapper.

### Exemption removal rule

When a label-text or renderer-specific exemption is removed from a test gate,
the fixtures that previously passed via that exemption must still pass. If they
fail, the fix is in the attachment engine (better target geometry), not in
restoring the exemption. This prevents "remove exemptions" from being
interpreted as "make those tests fail."

Example: the smoke gate currently exempts hydroxyl own-connectors via
`_is_hydroxyl_label(text)`. When that exemption is removed, every hydroxyl
fixture that previously passed must still pass because
`AttachTarget(kind="circle")` provides the correct boundary and the connector
paints legally within it. If a fixture starts failing, the circle radius or
clearance is wrong, not the gate.

### In-progress migration guard

During Phases B and C, callers are being moved from old APIs to new ones.
To prevent regressions during this window:
- Each migrated caller gets a dedicated regression fixture committed before
  the migration change, so any behavioral drift is caught immediately.
- Wrapper parity tests (Phase A) remain active and green until the wrapper is
  deleted. If a wrapper produces different results than the direct
  `AttachTarget` path, the migration is wrong.
- During migration phases, prefer "migrate first, delete later".
  Final Phase C cutover is allowed to migrate remaining callers and delete
  wrappers in one change if canary tests prove wrapper removal and full gates
  are green.

### Risk management

- Use additive API first; do not break existing callers in Phase A.
- Migrate OASA first, then BKChem, with green gates between phases.
- Keep rollback path by preserving wrappers until late Phase C.
- Avoid refactoring attachment and unrelated rendering logic in same PR.

## Code cleanup rules

### Dead code criterion

A function, branch, or helper is dead if no production code path calls it after
migration, verified by coverage analysis or full-tree grep. Dead code is
deleted, not commented out or renamed with an underscore prefix.

### Naming cleanup

After Phase C, bbox-named compatibility attachment APIs must not remain.
Rectangle-local internals may keep box/bbox variable naming where the shape is
strictly axis-aligned and not polymorphic. The function name mapping table in
the unified target contract section remains the authoritative rename list for
public/migration surfaces.

### Compatibility wrapper lifecycle

Wrappers exist only during migration. Each wrapper must:
- Route internally to the new `AttachTarget` engine.
- Emit no new callers after Phase A.
- Be deleted in Phase C with a canary test proving no caller depends on it.

## Backward compatibility

- `clip_bond_to_bbox(...)` and other bbox-named compatibility wrappers were
  deleted in Phase C; canary tests assert their absence.
- Existing `attach_atom="first|last"` behavior remains valid.
- Optional element-based attachment selectors are additive and do not break old
  inputs.
- Any caller without new metadata follows deterministic defaults.
- No CDML migration is required for existing files.
- Older readers that ignore new selectors may show slightly different visual
  attachment points, but structure and chemistry semantics remain unchanged.

## Release checklist (not a phase)

- `pytest tests/`
- archive matrix smoke
- selftest sheet generation
- endpoint parity checks across render backends
- two consecutive release cycles with zero bond-label regressions
- docs/changelog path validation for moved or archived plan/spec files
- confirm no `bbox`-named production APIs remain (Phase C exit)
- confirm all wrappers deleted and canary tests green

## Documentation updates required

When Phase C is complete:
- Archive
  [docs/archive/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](../archive/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md)
  as historical baseline.
- Update
  [docs/CDML_FORMAT_SPEC.md](../CDML_FORMAT_SPEC.md)
  to reflect finalized attachment contract semantics.
- Add final behavior notes to
  [docs/CODE_ARCHITECTURE.md](../CODE_ARCHITECTURE.md)
  and
  [docs/FILE_STRUCTURE.md](../FILE_STRUCTURE.md)
  if module boundaries change.

## Out-of-scope large files (noted for future plans)

This plan touches `bond.py` (1,880 lines) and `haworth/renderer.py`
(1,481 lines) because they contain attachment logic. Several other BKChem
files exceed 1,500 lines and would benefit from decomposition, but are
unrelated to bond-label attachment and must not be mixed into this plan:

- `packages/bkchem-app/bkchem/modes.py` (2,753 lines) - UI event handlers.
- `packages/bkchem-app/bkchem/paper.py` (1,882 lines) - canvas management.
- `packages/bkchem-app/bkchem/main.py` (1,546 lines) - application startup.

Each deserves its own decomposition plan. The `bond.py` decomposition in this
plan demonstrates the pattern (identify duplication, eliminate it, then split
the remainder into focused modules) that can be applied to the others.

Large OASA-only files (`graph/graph.py`, `inchi_key.py`) are out of scope
entirely - they are internal to OASA, do not touch attachment or rendering,
and have no BKChem crossover. InChI key cleanup is tracked in
[docs/TODO_CODE.md](../TODO_CODE.md).
