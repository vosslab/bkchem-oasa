# Atom numbering M0 decision

Date: 2026-07-29

## Status and scope

M0 is complete. This record freezes the implementation handoff for M1. It is
planning and evidence documentation, not a durable public-contract claim until
implementation and review establish delivered behavior.

## Operation and request

M1 implements one bounded `atom.number.set` operation for exactly one direct
core atom of one direct-root molecule. Its immutable request fields are:

| Field | Value |
| --- | --- |
| `expected_revision` | Current backend revision |
| `molecule_id` | Durable direct-root molecule ID |
| `atom_id` | Durable direct core atom ID |
| `number` | `int | None` |
| `show_number` | `bool | None` |

Assignment or replacement uses a positive non-bool integer for `number` and
an explicit boolean for `show_number`. Clear is exactly `(None, None)`. Every
mixed, null, or otherwise invalid pair is typed invalid input. The operation
uses the durable-ID, direct-core, and revision constraints of existing OASA
atomic operations.

## Persistent backend result

For assignment, OASA writes exactly decimal `number` and `show_number="yes"`
or `show_number="no"` from the supplied boolean in a detached candidate. It
does not infer visibility, allocate a sequence, require uniqueness, or alter
another persistent field. Clear removes both attributes.

Existing CDML 26.07 grammar and version remain sufficient. Strict request
validation is narrower than legacy-compatible stored text. Invalid, stale,
target, and compatibility outcomes are atomic and leave the snapshot,
revision, history, and saved baseline unchanged.

## Qt compatibility and M2 handoff

Current evidence shows that Misc activation chooses one more than the highest
assigned number, including hidden values. Valid Number clicks consume
successive candidates. The historical local implementation left its transient
counter advanced after Clear; that observation is not a delivered invariant.

Visible replacement remains visible and hidden replacement remains hidden. M2
captures the desired boolean from synchronized projection state and submits
only scalars and durable IDs. A newly unnumbered atom keeps its existing
current default of `True` when M2 captures that intent.

OASA persists supplied scalar intent only and never allocates automatic
numbers. After a backend outcome or reprojection, M2 derives any next
transient candidate from the current authoritative snapshot. It does not retry
an accepted request or retain a stale projection wrapper.

## Legacy atom-number marks

Ordinary backend document load, round-trip, and edits to other records preserve
a direct `<mark type="atom_number">` unchanged. A number edit targeting a
direct core atom bearing that exact direct legacy mark returns a typed
compatibility failure. It leaves the mark and number fields unchanged, without
mutation, migration, deletion, or duplication.

The accepted preservation experiment shows that an unrelated authoritative
edit retains the mark, current attributes, and opaque content. The current Qt
fragment serializer drops that mark. Typed rejection preserves the compatible
form and avoids a dual-label ambiguity. A future conversion requires its own
designed and validated operation.

## Evidence and limits

- `tmp/atom_numbering_baseline_2026-07-29.md` records current Qt model and
  fragment behavior.
- `tmp/atom_numbering_qt_gesture_baseline_2026-07-29.md` records
  fixture-backed current gesture and visibility behavior.
- `tmp/atom_numbering_legacy_backend_roundtrip.md` records preservation
  through an unrelated authoritative backend edit.

This decision record contains the durable summaries. The local, intentionally
untracked M0 artifacts above are provenance only.

The fixture-backed gesture records are historical, one-time evidence. Their
temporary test sources were intentionally removed after safe fixture-owned
execution, so they are not durable regression coverage.

M0 does not prove the future backend implementation, persistence, undo,
revision behavior, or broader GUI parity.

## Preserved boundary

This slice excludes batch renumbering, generic property editing, numbering of
groups, text, queries, or marks, an automatic allocation service, legacy
conversion, and a schema change.
