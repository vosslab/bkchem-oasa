# Phase 4: Cross-Label Bond Collision Avoidance

## Context

Bonds connecting atoms A-B currently only clip endpoints against their own-vertex labels. A bond may freely pass through atom C's label box. The measurement tool reports **195 bond/glyph overlaps** (171 gap_tolerance_violation + 24 interior_overlap) across 78 SVGs. Phase 4 adds cross-label collision detection and endpoint retreat to `build_bond_ops()`, using existing infrastructure (`_capsule_intersects_target`, `retreat_endpoint_until_legal`).

**Acceptance target**: bond/glyph overlaps < 50, no new alignment misses, no gap/perp regressions.

---

## Critical Files

| File | Role |
|------|------|
| `packages/oasa/oasa/render_geometry.py` (2703 lines) | Core implementation -- add helper, integrate into `build_bond_ops()` |
| `tests/test_render_geometry.py` | Unit tests for new function |
| `docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md` | Update Phase 4 status |

## Existing Functions to Reuse (all in render_geometry.py)

| Function | Lines | Purpose |
|----------|-------|---------|
| `_capsule_intersects_target(seg_start, seg_end, half_width, target, epsilon)` | 1900-1924 | Checks if stroked line penetrates target interior |
| `retreat_endpoint_until_legal(line_start, line_end, line_width, forbidden_regions, ...)` | 2238-2291 | Binary-search retreat of `line_end` toward `line_start` |
| `_coerce_attach_target(target)` | (utility) | Normalizes target to `AttachTarget` |
| `make_box_target(bbox)` | 311-313 | Constructs box `AttachTarget` -- used in tests |
| `_edge_line_width(edge, context)` | (utility) | Computes line width for an edge |

No new fields needed on `BondRenderContext` -- `context.label_targets` (line 209) already maps every shown vertex to its `AttachTarget`. We read it directly in `build_bond_ops()`.

---

## Implementation Steps

### Step 1: Add `_avoid_cross_label_overlaps()` function

**Location**: After `_apply_bond_length_policy()` (line 647), before `build_bond_ops()` (line 651).

```python
def _avoid_cross_label_overlaps(start, end, half_width, own_vertices, label_targets, epsilon=0.5):
```

**Algorithm**:
1. Collect non-own targets: `[t for v, t in label_targets.items() if v not in own_vertices]`
2. Compute minimum bond length guard: `max(half_width * 4.0, 1.0)`
3. For each cross target that `_capsule_intersects_target(start, end, half_width, target, epsilon)` returns True:
   - Compute target centroid
   - If centroid is closer to `end`: retreat `end` toward `start` via `retreat_endpoint_until_legal(line_start=start, line_end=end, ..., forbidden_regions=[target])`
   - If centroid is closer to `start`: retreat `start` toward `end` via `retreat_endpoint_until_legal(line_start=end, line_end=start, ..., forbidden_regions=[target])`
   - Enforce minimum bond length guard -- skip retreat if result would be too short
4. Return `(start, end)`

### Step 2: Integrate into `build_bond_ops()` main bond line

**Location**: Between `_apply_bond_length_policy` (line 661) and the `has_shown_vertex` check (line 662).

Move `edge_line_width = _edge_line_width(edge, context)` up from line 666 to line 662, then insert:

```python
start, end = _apply_bond_length_policy(edge, start, end)
edge_line_width = _edge_line_width(edge, context)          # moved up from line 666
if context.label_targets:
    start, end = _avoid_cross_label_overlaps(
        start, end,
        half_width=edge_line_width / 2.0,
        own_vertices={v1, v2},
        label_targets=context.label_targets,
    )
has_shown_vertex = False
```

Remove the original `edge_line_width = _edge_line_width(edge, context)` at old line 666.

### Step 3: Apply to double bond parallel lines

**3a**: After own-target clipping at lines 710-713 (asymmetric double bond), add:
```python
if context.label_targets:
    (x1, y1), (x2, y2) = _avoid_cross_label_overlaps(
        (x1, y1), (x2, y2), half_width=edge_line_width / 2.0,
        own_vertices={v1, v2}, label_targets=context.label_targets,
    )
```

**3b**: Same pattern after lines 721-724 (symmetric double bond parallel lines).

### Step 4: Apply to triple bond parallel lines

After `geometry.find_parallel` at lines 732-734, before `_line_ops`, add the same avoidance call on `(x1,y1), (x2,y2)`.

### Step 5: No changes needed for wedge/hashed/wavy bonds

These bond types use the already-adjusted `start, end` from Step 2. Wedge front-overlap extension (lines 672-678) intentionally extends past the avoidance point -- this is a visual stacking feature, not a bug.

### Step 6: Unit tests

Add to `tests/test_render_geometry.py` (6 new tests):

1. **No cross targets** -- endpoints unchanged
2. **Own-target excluded** -- own vertex box on path, no retreat
3. **Cross target near end** -- end retreats, start unchanged
4. **Cross target near start** -- start retreats, end unchanged
5. **No intersection** -- distant box, no retreat
6. **Minimum length guard** -- short bond with mid-path box, bond not over-shortened

Use `render_geometry.make_box_target(bbox)` for target construction. Use `FakeVertex` class pattern for vertex identity.

---

## Design Decisions

1. **No new `BondRenderContext` field**: `context.label_targets` already has all vertex->target mappings. Avoids modifying the frozen dataclass.

2. **Closer-endpoint retreat**: Target centroid determines which endpoint to shorten. When the label is near the end, `retreat_endpoint_until_legal(start, end, ...)` retreats end. When near the start, swap roles: `retreat_endpoint_until_legal(end, start, ...)` retreats start.

3. **Minimum bond length guard** (`half_width * 4.0`): Prevents bonds from collapsing when surrounded by labels. A visible short bond is better than a vanished one.

4. **Sequential cross-target processing**: Each target is checked and retreated in sequence. If a bond intersects two cross-labels, both retreats apply. Min-length guard prevents cascading over-shortening.

5. **Epsilon = 0.5**: Matches the existing epsilon used throughout `validate_attachment_paint` and `retreat_endpoint_until_legal`.

---

## Verification

```bash
# Unit tests (existing + new)
source source_me.sh && python3 -m pytest tests/test_render_geometry.py -x -v

# Pyflakes
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -x -q

# Measure overlap count (target: < 50, from 195)
source source_me.sh && python3 tools/measure_glyph_bond_alignment.py \
    -i "output_smoke/archive_matrix_previews/generated/*.svg"

# Verify no alignment regression (must remain 362/362 = 100%)
# Verify gap/perp stats not degraded vs baseline:
#   CH2OH gap=1.54/0.54  perp=0.15/0.12
#   HO    gap=1.08/0.55  perp=0.08/0.15
#   OH    gap=1.15/0.60  perp=0.03/0.00

# Full test suite
source source_me.sh && python3 -m pytest tests/ -x -q
```

After verification, update plan document Phase 4 status and commit.
