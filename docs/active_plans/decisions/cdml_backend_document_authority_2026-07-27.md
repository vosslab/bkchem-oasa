# Decision: CDML backend document authority

## Status

Decided on 2026-07-27. This is an implementation constraint, not an open
architecture question.

## Decision

The OASA backend owns the authoritative complete persistent CDML document.
Qt owns only transient interaction state and graphical projections.
Persistent communication between the frontend and backend occurs exclusively
through CDML.

The first transaction protocol uses a complete candidate CDML document:

1. Qt completes a user gesture or accepted dialog edit.
2. Qt submits a complete candidate CDML document and expected backend revision.
3. The backend parses and validates the candidate atomically.
4. On success, the backend stores it and returns its canonical complete CDML
   plus a new revision.
5. Qt replaces its projection from that backend response.
6. On failure, the backend state and current Qt projection remain unchanged.

## Central persistence invariant

If the backend rewrites CDML but understands only molecules, every
non-molecular object is lost unless Qt restores it afterward. At that point Qt,
not the backend, remains the authoritative document owner.

Therefore:

> A backend CDML round-trip must preserve every persistent object without Qt
> re-merging omitted content.

The backend must preserve every persistent CDML object, whether typed or
opaque. An arrow does not need chemical semantics in OASA, but its element,
attributes, position, order, ID, references, and unknown children remain owned
by the backend document.

## Ownership

| Backend owns | Qt owns |
| --- | --- |
| Complete CDML document and revision | Session identity and backend connection |
| Molecules and chemistry semantics | Graphics items and rendering |
| Persistent presentation records | Selection, focus, hover, and handles |
| Object order, IDs, and references | In-progress gestures and previews |
| Paper/header and reaction data | Zoom, viewport, grid display, and active tool |
| Unknown XML and attributes | Dialogs, menus, and Qt object lifetime |

Qt projection models may cache backend data for display and editing. They are
replaceable projections, not persistent sources of truth.

## Consequences

- OASA needs a complete-document CDML API in addition to its molecule codec.
- Unknown elements and attributes are preserved, never silently ignored.
- Native Open loads CDML into the backend before Qt projects it.
- Save writes the current backend canonical snapshot unchanged by Qt, not a
  Qt-reconstructed envelope.
- Persistent edits commit CDML to the backend before Qt accepts them.
- Accepted backend snapshots are immutable. Commit and restore both create new
  monotonically increasing revisions; restore copies target content rather than
  moving the counter backward.
- Qt retains only revision-navigation entries and labels. Before a restore,
  the backend protects the immediate pre-restore revision for redo; each
  restore replaces that protection. A new committed edit clears Qt redo
  navigation and the redo protection without mutating retained backend
  snapshots.
- New and native-CDML sessions begin clean. Non-CDML import commits converted
  complete CDML into a clean blank session, leaving the result dirty and
  pathless. After a successful filesystem write, Qt calls
  `mark_saved(expected_revision)`. The backend retains canonical saved content
  and protects the exact saved revision from eviction. History capacity is at
  least three, so current, saved, and immediate pre-restore revisions remain
  restorable when distinct. Older nonprotected history may evict. Dirty state
  compares canonical content to saved content, not revision numbers; saved
  content restored into a new revision is clean.
- Qt supplies provisional correlation tokens only in the reserved form
  `__bkchem_new__<token>` in recognized ID declarations and known references.
  Each declaration token is unique; known references may repeat it. OASA
  rewrites only those recognized positions. The prohibition on stored or
  canonical provisional tokens applies only to those positions; matching opaque
  XML strings remain unchanged.
- The existing Qt full-document codec and persistent `Document` model are
  transitional projection/candidate builders until their authority moves to
  OASA.
- A Qt-side raw-XML merge cannot be the final preservation mechanism.

## First proof

The first backend-only test parses and serializes an inline document containing
a molecule, arrow, text object, group, reaction, paper data, and an unknown
namespaced node. It verifies their semantic order, IDs, references, and opaque
content without importing Qt.

The first vertical frontend proof adds an arrow, submits complete CDML to the
backend, receives canonical CDML, rebuilds the arrow projection, and saves the
backend snapshot. No Qt re-merge step is permitted.
