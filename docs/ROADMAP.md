# Roadmap

## Active planning sources
- [OASA-Wide_Glyph-Bond_Awareness.md](archive/OASA-Wide_Glyph-Bond_Awareness.md)
  glyph-bond alignment plan.
- [TODO_CODE.md](TODO_CODE.md) coding backlog.
- [TODO_REPO.md](TODO_REPO.md) repo and release backlog.

## Archived plans
- [HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  Haworth schematic renderer (core phases 1-5c complete, SMILES phases deferred).
- [RENDER_BACKEND_UNIFICATION.md](archive/RENDER_BACKEND_UNIFICATION.md)
  render ops unification plan.
- [ROUNDED_WEDGES_PLAN.md](archive/ROUNDED_WEDGES_PLAN.md)
  rounded wedge geometry plan.

## Near-term focus
- Release-selected classic behavior/action parity is complete. The authoritative
  action inventory has no `PART` or `QUEUED` release rows. Final audit, full
  suite, glyph, screenshot, and other one-time release evidence remain gates,
  not hidden feature-parity tasks.
- New persistent work extends an OASA-owned operation or immutable projection
  fact and proves its visible Qt route through focused save/reopen, undo, and
  recovery behavior. Tk remains runnable deprecated reference software, not a
  packaging default or a second persistence model.

## Completed foundations
- **Hexagonal grid alignment**: OASA owns nearest-vertex geometry, the shared
  origin-zero persistent Repair operation, and immutable display coordinates.
  Qt projects the matching overlay and uses the same lattice for interaction
  snapping. See [TRANSFORMATION_OPERATIONS.md](TRANSFORMATION_OPERATIONS.md)
  and the accepted WP-F5 disposition in the active backend-authority plan.
- **Glyph-bond alignment**: portable OASA rendering and the Qt projection share
  label attachment targets, including explicit carbon labels and complete
  topology.
- **Arrow Configure**: start/end heads, spline, width, and color now use a
  revision-bound OASA presentation operation with backend undo/redo through
  Qt, durable selection, save, and reopen behavior.
- **Geometric Configure**: rect, square, oval, circle, polygon, and ordinary
  polyline roots share one OASA-owned width/stroke/fill operation. Qt uses a
  detached accessible form with backend undo/redo, durable selection, and
  save/reopen behavior.
- **Plus font/background Configure**: a font chooser and accessible fill control
  submit detached intent to OASA. Child family plus root size/color are canonical;
  shared projection renders them through backend undo/redo and save/reopen.
- **Text background Configure**: the existing plain Text patch now owns optional
  fill intent; Qt supplies the same accessible positive fill interaction and
  canonical shared projection without a local persistence path.
- **Rectangular and Round Brackets**: one OASA operation owns proportional
  pair geometry, drawing-standard strokes, ID allocation, and atomic history;
  Qt exposes both classic submodes and renders spline polylines as curves.
- **Presentation insertion and ordering**: Arrow, Text, Plus, Wavy, Vector, and
  stack actions send only scalar intent. OASA owns CDML, normalized geometry,
  drawing-standard styling, IDs, ordering, atomic validation, and history.
- **Root facts and projection plans**: molecule insertion returns only durable
  direct-root facts, and synchronized Qt hydrates one immutable OASA plan
  without parsing canonical CDML.
- **Responsive Qt shell**: all registered modes remain reachable in the compact
  640/1024 layouts and the full 1280 layout; status and zoom controls remain
  usable without changing document state.
- **Durable brackets**: paired polylines persist explicit `bracket_pair` and
  `bracket_side` identity. OASA observes and patches a valid pair atomically;
  Qt derives transient pair selection, expands pair actions, and configures
  shared appearance through one backend commit; retained Tk preserves marked
  pairs.
- **Three-ring Haworth backend**: an explicit-declaration OASA API lays out
  linear or branched three-ring trees with no structural or stereochemical
  inference. Qt currently exposes only its direct two-ring profile.
- **Haworth render convergence**: connector and label layout now use shared
  geometry; the seven former active Haworth-specific override policies are
  removed from the active path.

## Declared exclusions and future capabilities

- Literal one-for-one Tk parity is intentionally not the product target. The
  release-selected action inventory, not legacy Canvas mechanics, defines Qt
  completion.
- The language picker, external InChI command path, Tk 3D behavior, legacy
  alignment variants, and Tk Canvas-specific mechanics are excluded from the
  delivered Qt product rather than incomplete parity rows.
- Template atom fusion and a three-ring Haworth Qt authoring adapter are
  declared future capabilities. The existing three-ring backend API remains
  separate from the bounded direct two-ring UI.
- Add dates and milestones once a release schedule is agreed.
