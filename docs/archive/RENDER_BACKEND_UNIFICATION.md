# Render backend unification

## Objective
- Generate geometry and styling decisions once, then paint through SVG and Cairo.
- Remove Haworth-specific drawing logic from renderer backends.
- Keep this plan aligned with `HAWORTH_IMPLEMENTATION_PLAN.md`.

## Guiding rules
- Layout and bond styling generate geometry once.
- Renderers only paint primitives.
- No Haworth-specific logic in `svg_out.py` or `cairo_out.py`.
- Deterministic ordering, rounding, and z order rules.

## Phase 0: Inventory and invariants
- List the primitives needed for Haworth rendering today.
- Define the coordinate system, units, and y axis direction.
- Document z order and stroke semantics (cap, join, miter limit).
- Define determinism rules (stable ordering, rounding policy).
- Deliverable: this document updated with the invariants table.

### Invariants

| Topic | Decision |
| --- | --- |
| Coordinate system | Final screen space after all transforms. |
| Axis direction | +Y is down (SVG/Cairo default). |
| Units | SVG user units and Cairo device units are treated as pixels. |
| Ordering | Sorted by op.z, then original insertion order. |
| Rounding | Snapshot JSON rounds to 3 decimal places (`round_digits=3`). |
| Caps | Lines default to `butt` unless explicitly set. |
| Joins | Joins default to renderer defaults unless explicitly set. |
| Miter limit | Use renderer defaults unless a dedicated op field is added. |
| Color encoding | Ops serialize colors to normalized lowercase hex. |

## Scope boundaries and non-goals
- In scope: bond geometry, Haworth styles, and ops-layer drift protection.
- Out of scope (for now): text/labels, atom symbol layout, and font rendering.
- Follow-on: add a TextOp once bond ops are stable, so label rendering can be
  unified without backend-specific layout drift.

## Phase 1: Common render ops spec
- Define a minimal intermediate format that is pure data.
- Minimum ops for Haworth:
  - Line(p1, p2, stroke_width, cap, join, color, z, id)
  - Polygon(points, fill, stroke, stroke_width, z, id)
  - Path(segments, fill, stroke, stroke_width, cap, join, z, id)
  - Circle(center, r, fill, stroke, stroke_width, z, id)
- All points are in final screen coordinates.
- No implicit defaults; every op is explicit.
- Path segments must include Arc for rounded wedges.
- Deliverable: a `render_ops.py` data model plus JSON serialization for tests.

## Phase 2: Haworth geometry producer
- Choose one module to generate Haworth ops (for example `haworth_render.py`).
- Haworth front edges are Lines with round caps, not rectangle polygons.
- Wedges are Paths with an arc at the wide end, not circles.
- Deliverable: Haworth layout produces ops only, no backend calls.

## Phase 3: Thin painters
- Implement `render_ops_to_svg(ops)` and `render_ops_to_cairo(ops, ctx)`.
- Painters support only ops, caps, joins, fills, and strokes.
- No bond type branching inside the painters.
- Renderers may pass a shared context or provider object, but it must be
  identical for SVG and Cairo and must not branch on bond types or Haworth
  properties.
- Deliverable: `svg_out.py` and `cairo_out.py` call the op painters.

## Phase 4: Tests to prevent drift
- Add golden tests at the ops layer with JSON snapshots.
- Define strict ordering so snapshots are stable across runs.
- Add minimal rendering tests:
  - SVG output parses and includes expected primitives.
  - Cairo output renders without exceptions.

## Acceptance criteria
- Ops JSON matches between SVG and Cairo for the same molecule, style, and
  rounding (ordering and z included).
- Haworth smoke images match within tolerance between SVG and Cairo.
- Adding a new Haworth style changes only op generation, not both backends.

## Migration notes
- Gate the new path behind a single flag in both backends (same default).
- Switch the Haworth smoke tests to the new pipeline.
- Remove Haworth-specific backend code once:
  - ops snapshots are stable, and
  - SVG/Cairo smoke outputs match expectations in CI.
