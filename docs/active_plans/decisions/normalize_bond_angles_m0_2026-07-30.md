# Normalize bond angles decision

Date: 2026-07-30

## Decision

Normalize Bond Angles is implemented as a backend-authoritative, revision-bound
geometry repair. Its immutable request names nonempty unique durable direct-root
molecule IDs and a finite positive spacing. The backend validates every target
on a detached complete-document candidate and either accepts one exact snapshot
or returns a typed atomic failure. A lexical no-op returns the current snapshot
without a new revision or history entry.

The operation changes only the `x` and `y` attributes of direct core atom
points. It preserves every other persistent record and attribute, including
opaque and foreign content, top-level presentation records, atom-local
extensions, identifiers, references, and source order.

## Geometry behavior

- Ring atoms are fixed.
- Every movable non-ring connected component has zero or one adjacent fixed
  ring anchor. A component with multiple ring anchors is a typed atomic
  failure.
- An anchored component retains both its ring anchor and the adjacent
  anchor-to-component edge, including when the movable component extends to
  arbitrary depth.
- Outgoing children are processed in their authored source order. Each is
  assigned its nearest 60-degree slot. An exact represented half-slot tie
  advances toward the increasing-angle slot.
- Incoming and fixed-ring directions reserve their nearest slots. A colliding
  outgoing child advances through successive slots. A parent with no free slot
  is a typed atomic failure.
- Nondegenerate parent-child distances are preserved. Requested spacing is
  used only to construct a degenerate outgoing vector.

The Repair menu and Repair-mode selection/click routes are durable-ID clients:
they submit the current session revision, target IDs, kind, and spacing, then
discard old Qt projection wrappers before the accepted snapshot is projected.
Backend history owns accepted undo/redo and dirty state. An installation failure
after acceptance remains an accepted result; recovery retries only exact current
snapshot reprojection. Normalize Rings and Straighten Bonds remain local Qt
routes with their established local undo behavior.

## Measured evidence retained

All coordinates below are PostScript points after CDML `cm` conversion.

| Case | Input observation | Output observation |
| --- | --- | --- |
| Branched acyclic | Root `(0, 0)`, branch `(39.997, 20.013)`, descendant `(72.000, 39.997)` | The branch snaps to `(44.724, 0)` and its descendant translates to `(63.589, 32.675)`. Nondegenerate bond lengths remain `39.997`, `44.724`, and `37.730` points. |
| Three-membered ring plus substituent | Ring coordinates form a 40-point triangle; substituent begins at `(-29.991, 20.013)` with a leaf | Ring coordinates remain unchanged. The substituent snaps to `(-18.027, 31.224)` and its leaf translates by the identical vector to `(-38.030, 65.869)`; bond lengths remain unchanged. |
| Degenerate outgoing bonds | Two root children begin at `(0, 0)` | With 40-point spacing, children become `(40, 0)` and `(20, 34.641)`. Spacing is a degenerate-vector fallback, not general bond-length normalization. |
| Incoming-edge collision | Root `(0, 0)`, child parent `(39.997, 0)`, grandchild at the 160-degree, 40-point direction | The incoming direction is reserved, so the grandchild advances to the next free 60-degree slot instead of occupying the root coordinate. |

Complete-CDML preservation evidence included a branched molecule, an unchanged
top-level arrow, and an atom-local extension. The accepted repair altered only
the selected direct atom-point coordinates; the arrow points and extension
content survived unchanged.
