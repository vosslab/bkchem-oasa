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
- Close task-level Qt usability gaps against retained classic behavior without
  reintroducing frontend persistence. The next Configure family is the
  remaining vector/shape stroke and fill surface; each accepted editor needs
  OASA history, dirty state, save/reopen, and recovery evidence.

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

## Known gaps
- Full classic feature parity is not complete. Object Configure covers atoms,
  bonds, Text, Plus, Wavy, and Arrow, but remaining vector and geometric-shape
  stroke/fill editors are not yet exposed through the synchronized Qt route.
- Add dates and milestones once a release schedule is agreed.
