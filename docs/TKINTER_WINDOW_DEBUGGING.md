# TKINTER WINDOW DEBUGGING

Lessons learned from debugging Tk Canvas zoom viewport drift in BKChem.

## The Bug

After zoom_out x3 + zoom_in x3, content bbox center shifted from
(1280, 960) to (815, 612) even though the scale correctly returned
to 4.0.  The zoom_to_content function became non-idempotent, producing
scale 1.0597 on the second call instead of the expected 4.0.

## Root Causes Found

### 1. Orphaned Canvas Items (atom.py -- primary cause)

For non-showing atoms (e.g. carbon in organic structures), the draw()
method called get_xy_on_paper() which creates a vertex_item, then
immediately created a separate self.item and set self.vertex_item =
self.item.  The vertex_item created by get_xy_on_paper() was orphaned
-- no reference kept, never deleted.

These orphaned items accumulated (6 per redraw for benzene), retained
stale canvas.scale() coordinates, and inflated the content bounding
box.

Fix: compute coordinates directly via real_to_canvas() instead of
calling get_xy_on_paper() in the non-showing atom path.

### 2. Stale bbox / vertex_item Coordinates (molecule.py -- secondary cause)

In molecule.redraw(), bonds were originally redrawn before atoms (for
z-ordering).  Bonds call atom.get_xy_on_paper() (reads vertex_item) and
atom.bbox() (reads canvas text item) for endpoint clipping.  After zoom,
vertex_items and text items hold stale pre-zoom coordinates until atoms
redraw.  For hidden atoms (e.g. carbon in benzene) this only affected
vertex_item positions, but for **shown** atoms with labels (N, O, R,
H3N, COOH) the stale bbox caused the endpoint clipping logic
(resolve_attach_endpoint) to produce wildly wrong attachment points,
drawing bonds as long diagonal lines.

An earlier fix pre-repositioned vertex_items at the top of redraw(),
but this only fixed position -- the bbox was still stale for shown atoms.

Fix: redraw atoms **first** so both vertex_items and canvas text items
are at correct positions, then redraw bonds, then lift atoms above
bonds to restore z-ordering:

```python
[o.redraw() for o in self.atoms]
for o in self.bonds:
    ...
for a in self.atoms:
    a.lift()
```

The lift() pass (defined in special_parents.py) raises atom canvas items
above bonds, restoring the atoms-on-top stacking that was previously
achieved by drawing atoms last.

### 3. Background Rectangle Drift (paper.py -- scale_all redesign)

self.background (the page rectangle) is NOT in self.stack, so
redraw_all() never touches it.  The old code called
canvas.scale('all', ox, oy, factor, factor) which scaled everything
(including the background) around the viewport center.  But
redraw_all() then overwrites all content positions from model coords,
effectively scaling from the canvas origin (0, 0).  The background,
having been scaled around the viewport center, diverged from the
redrawn content -- objects appeared to slide relative to the page.

Fix: remove canvas.scale('all', ...) entirely.  After redraw_all(),
explicitly reset the background via create_background() followed by
scale(background, 0, 0, scale, scale) to keep it aligned with the
redrawn content.

### 4. Tk xview moveto Inset Bug (paper.py -- centering precision)

_center_viewport_on_canvas() computes a fraction and calls
xview_moveto(frac) / yview_moveto(frac).  Internally, Tk computes
the new scroll origin as:

    xOrigin = scrollX1 - inset + round(frac * scrollWidth)

where inset = borderwidth + highlightthickness (default 3 in BKChem).
The -inset term means the viewport lands 3 pixels away from the
intended canvas point.  This caused a systematic ~3 px centering
error per zoom step, accumulating to >15 model-px drift over 8
zoom steps.

Fix: add +inset to the fraction formula:

    frac_x = (cx - canvas_w / 2 + inset - sr_x1) / sr_w

This compensates for Tk's internal -inset subtraction, reducing
per-step centering error from ~3 px to <0.1 px.

### 5. Viewport Centering After Scrollregion Update (paper.py -- minor)

update_scrollregion() changes the canvas-to-widget coordinate mapping.
After each zoom step, canvasx(winfo_width/2) returns a different canvas
coordinate, so the next zoom operates around a slightly different
origin.

Fix: add _center_viewport_on_canvas() helper and call it after
update_scrollregion() when center_on_viewport=True.  The helper
captures the model-space point at the viewport center before zooming,
then after redraw re-centers on that model point's new canvas position
(model_coord * new_scale).

## Debugging Techniques That Worked

### Track Canvas Item Counts

Add n_items = len(paper.find_all()) to each diagnostic snapshot.
A growing count reveals leaked canvas items immediately.

### Diff Item Sets Before/After

    items_before = set(self.find_all())
    # ... operation ...
    items_after = set(self.find_all())
    new_items = items_after - items_before

For each leaked item, log its type, tags, and coords to identify what
created it and whether it belongs to atoms, bonds, or other objects.

### Per-Step Snapshots

Instead of only capturing state at the start and end of a zoom
sequence, capture after every individual zoom step.  This reveals
whether drift accumulates linearly (suggesting a per-step leak) or
compounds exponentially.

### Write Debug Output to a File

When tests run in subprocesses (common for Tk tests to avoid display
issues), print statements go to the subprocess stdout/stderr which may
be captured.  Write debug output to /tmp/debug.txt instead.

## Key Tk Canvas Concepts

### canvas.scale(ALL, ox, oy, fx, fy)

Transforms all canvas item coordinates around point (ox, oy).  Items
at (ox, oy) stay fixed.  Does NOT modify Python object attributes --
only Tk-level item coordinates.

### vertex_item Pattern

BKChem uses invisible canvas items (zero-length lines) as position
caches for atoms.  get_xy_on_paper() reads from these items.  When
canvas.scale() moves them, any code reading from them gets stale
positions until the owning object redraws.

### scrollregion and canvasx/canvasy

The scrollregion defines the total scrollable area.  canvasx(pixel)
maps widget pixel coordinates to canvas coordinates based on the
current scroll position and scrollregion.  Changing the scrollregion
changes this mapping, which can cause viewport drift if the scroll
position is not adjusted.

### redraw() Ordering Matters

When object A reads position from object B during redraw, B must have
correct positions before A draws.  In BKChem, bonds read atom positions
via vertex_items and atom.bbox() for endpoint clipping against labels.
If atoms have not yet redrawn their canvas items, bonds get stale
coordinates and stale bboxes.  The solution is atoms-first redraw with
a lift pass to restore z-ordering (atoms above bonds).

## Native launch probe

The former native-window zoom matrices were implementation diagnostics. They
depended on sleeps, hardcoded scale ladders, and host Tk behavior, so they are
not permanent pytest coverage. To establish that the deprecated retained
application still launches on a functioning Tk host, run the bounded one-time
probe:

```sh
source source_me.sh && python3 tests/e2e/e2e_bkchem_tk_smoke.py
```

The probe starts Tk in an isolated child and reports a timeout, ordinary exit,
or terminating signal explicitly. Geometry investigation remains a manual
debugging task guided by the canvas invariants above.
