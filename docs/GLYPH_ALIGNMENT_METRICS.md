# Glyph alignment metrics

This document defines the three distance metrics reported by the glyph-bond
alignment checker (`tools/measure_glyph_bond_alignment.py`) and shown in
diagnostic SVG overlays.

## Quick reference

| Metric | Full name | What it measures |
| --- | --- | --- |
| `gap` | Bond-end gap | Distance from bond tip to glyph body, along the bond |
| `perp` | Perpendicular offset | Sideways distance from glyph center to the bond line |
| `err` | Alignment error | Value used for the pass/fail decision (currently equals `perp`) |

## Diagram

The ASCII diagram below shows a bond approaching the letter "O" in a label
such as "OH".  The bond endpoint is marked `*`, and the glyph center is the
middle of the "O".

```
                        bond line (infinite)
           - - - - - - - - - - - * ------> - - - - - - -
                                 |         .
                          gap    |         .  perp
                                 |         .
                              +-----+      .
                              |     |      .
                              |  O  | . . .X (glyph center)
                              |     |
                              +-----+
                           (glyph body)
```

- `gap` is measured **along** the bond direction, from the bond endpoint `*`
  to the nearest point on the glyph body boundary.
- `perp` is measured **perpendicular** to the bond direction, from the glyph
  center `X` to the infinite line through the bond.

## Metric details

### gap (bond-end gap)

- **Definition:** signed distance from the bond endpoint to the nearest point
  on the glyph body (ellipse fit or convex hull), measured along the bond
  direction.
- **Positive value:** the bond stops before reaching the glyph -- there is a
  visible gap between the bond tip and the letter.
- **Negative value:** the bond penetrates into the glyph -- the line overlaps
  with the letter.
- **Zero:** the bond tip touches the glyph boundary exactly.
- **Ideal:** a small positive value (typically 1.3-1.7 SVG units) so the bond
  visually connects to the letter without overlapping it.
- **Source field:** `endpoint_signed_distance_to_glyph_body` or
  `hull_signed_gap_along_bond` (preferred for curved glyphs such as C or S).

### perp (perpendicular offset)

- **Definition:** perpendicular distance from the glyph alignment center to
  the infinite line defined by the connector bond.
- **Always non-negative** (absolute distance).
- **What it reveals:** whether the bond is aimed at the correct character.  A
  large perp value means the bond line, if extended, would miss the target
  atom character.
- **Ideal:** as close to zero as possible.
- **Source field:** `endpoint_perpendicular_distance_to_alignment_center`.

### err (alignment error)

- **Definition:** the single value compared against the alignment tolerance to
  decide pass or fail.
- **Current implementation:** equals `perp`.  A label is marked "aligned" when
  `err <= 0.07` (the `MIN_ALIGNMENT_DISTANCE_TOLERANCE` constant).
- **Source field:** `endpoint_alignment_error`.

## Alignment target selection

The alignment center is not the center of the whole label string.  It is the
center of the **target atom character** -- the first chemically relevant atom
letter in the label, selected by priority order: C, O, N, S, P, then H.

Examples:

| Label | Target character | Why |
| --- | --- | --- |
| OH | O | O appears before H in priority |
| HO | O | Same label reversed; O still wins |
| CH2OH | C | C is highest priority |
| NH2 | N | N before H |

## Diagnostic SVG overlays

Each label in a diagnostic SVG shows:

- A **dashed ellipse or polygon** around the glyph body model.
- A **thin blue line** extending the connector bond to the SVG edges.
- An **orange crosshair** at the bond endpoint.
- An **annotation box** pushed toward the nearest SVG edge, connected by a
  dashed leader line, containing the label name and all three metric values.

Color coding:

- **Green/teal:** label passes alignment check (`err <= 0.07`).
- **Red/orange:** label fails alignment check (`err > 0.07`).

## Related files

- [GLYPH_ALIGNMENT_TECHNIQUE_SUMMARY.md](GLYPH_ALIGNMENT_TECHNIQUE_SUMMARY.md) --
  history of techniques tried and remaining challenges.
- `tools/measurelib/analysis.py` -- metric computation.
- `tools/measurelib/diagnostic_svg.py` -- diagnostic overlay generation.
- `tools/measurelib/constants.py` -- tolerance values.
