# Plan: Atom element backend authority

## Context

The completed Draw slice proves that a narrow persistent chemistry operation can
cross the Qt/OASA boundary as immutable plain data, commit a detached
authoritative CDML candidate, and replace the projection from the accepted
snapshot. AtomMode element substitution now follows that same
backend-authoritative route: its click supplies durable IDs and an element
scalar, and the accepted CDML snapshot supplies the replacement projection.

This next bounded slice migrates one user gesture only: click a direct editable
core atom in AtomMode and replace its current supported periodic-table element
with a different supported periodic-table element. It extends the
authoritative-operation pattern without turning AtomMode into a generic
atom-property editor.

## Objectives

- Make OASA the sole persistent owner of valid atom-element substitution.
- Submit an immutable request containing only expected revision, direct-root
  molecule ID, atom ID, and element symbol.
- Commit one detached authoritative candidate atomically and return the normal
  canonical `CDMLCommit`; the atom ID is already durable.
- Reproject Qt only from that accepted snapshot, preserving selection by the
  durable ID and using backend revision history for undo and redo.
- Preserve rejection and accepted-but-unprojectable behavior required by
  [CDML_BACKEND_TO_FRONTEND_CONTRACT.md](../../CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  and [QT_CONTRACT.md](../../QT_CONTRACT.md).

## Design philosophy

This is a **Fix the design, not the symptom** change. Replacing a Qt
`AtomModel` value and serializing later would perpetuate frontend ownership of
an authoritative chemistry edit. A narrow OASA request instead updates only
the named atom in a detached complete-CDML candidate, validates the whole
candidate, and uses the established revision transaction.

The grammar remains intentionally small. **Atomic task decomposition** keeps
one click, one backend operation, one history entry, and one canonical
reprojection independently testable. Additional atom properties need their
own behavior and preservation decisions.

## Scope

- AtomMode click on one direct editable core atom whose current CDML element
  is a supported periodic-table element.
- Substitute that atom with a different supported OASA periodic-table element.
- OASA request validation, direct-root molecule and direct atom resolution,
  detached candidate update, strict validation, atomic commit, and durable
  unchanged durable atom identity in the accepted commit.
- `DocumentSession` immutable request adapter, accepted backend history,
  canonical reprojection, and durable-ID selection restoration.
- Focused backend and offscreen Qt behavior tests.

## Non-goals

- Atom dialogs, generic property editing, charge, isotope, valency, or label
  changes.
- Coordinates, bond or topology changes, templates, fragments, or partial
  Delete.
- Same-element clicks, unsupported symbols, molecule creation, atom insertion,
  or ID allocation.
- A generic atom-edit RPC, frontend CDML candidates, or Qt-local persistent
  undo.

## Completion record

- `AtomMode.mouse_press()` reads the clicked atom's current symbol only to
  form a plain `atom.element.set` request. It does not make a persistent Qt
  property command; the accepted backend snapshot replaces the projection.
- Both `packages/bkchem-app/bkchem/modes/atom_mode.py` and
  `packages/bkchem-qt.app/bkchem_qt/modes/atom_mode.py` permit a selected
  valid element to replace any clicked editable atom with a different symbol;
  the backend operation keeps that established scope while making its
  persistence authoritative.
- OASA exposes `CDMLAtomElementEditRequest` and
  `CDMLDocumentSession.set_atom_element()`. The transaction validates the
  expected revision and direct targets, changes only `<atom name>`, strictly
  validates the detached complete-document candidate, and returns the normal
  immutable commit or a typed atomic rejection.
- `DocumentSession` accepts exactly the four plain request fields and matching
  durable target keys, records accepted backend history before projection, and
  recovers an accepted projection only from the exact current snapshot.
- The contracts and changelog describe this bounded route; the active
  migration plan records it without treating the wider M5 milestone as done.
- Independent backend, session-adapter, AtomMode, and contract reviews
  accepted the frozen slice. Focused evidence: 13 OASA substitution tests, 3
  session-adapter Atom cases, 4 offscreen AtomMode authority tests, and 1
  existing AtomMode setter interaction test passed.

## Architecture boundaries and ownership

| Layer | Owns | Must not own |
| --- | --- | --- |
| AtomMode | Hit test; selected element scalar; durable molecule/atom IDs; status and selection intent. | CDML mutation, persistent Qt command, durable-ID allocation, validation of chemistry semantics. |
| DocumentSession | Immutable plain envelope; capability/state gate; accepted revision history; canonical reprojection. | DOM patching, local persistent undo, reconstruction or merge of accepted CDML. |
| OASA | Immutable element-substitution request/result; direct target validation; detached candidate; strict validation; atomic commit and snapshot. | Qt models, scene objects, callbacks, projection state. |

### Request and result contract

Add the distinct immutable OASA request `CDMLAtomElementEditRequest`, with
exactly:

- `expected_revision: int`
- `molecule_id: str` for one direct-root core molecule
- `atom_id: str` for one direct editable atom in that molecule
- `element: str` for the selected replacement symbol

`CDMLDocumentSession.set_atom_element(request)` returns the normal immutable
`CDMLCommit`; no result-specific atom-ID field is needed. OASA accepts a
direct editable core atom whose current name is a supported periodic-table
element and a supported requested symbol different from that current name. It
changes only the target `<atom name>` attribute, preserving its durable ID,
coordinates, attached point, bonds, ordering, sibling attributes, opaque XML,
and all unrelated records. It performs no automatic valence, bond, or charge
repair.

Qt submits operation key `atom.element.set` with the same immutable
scalars and durable target keys `{("molecule", molecule_id), ("atom", atom_id)}`.
It captures IDs before submission, records no `ChangePropertyCommand`, and
uses the result's durable atom ID only after canonical reprojection. A stale or
invalid request leaves the backend revision, CDML, history, and live projection
unchanged. Once accepted, Qt treats the response as final; projection recovery
retries only the exact current backend snapshot.

## Files to modify

- `packages/oasa/oasa/cdml_document.py`: request value, narrow validation,
  detached candidate mutation, and `set_atom_element()`.
- `packages/oasa/tests/test_cdml_atom_element_substitution.py`: backend
  behavior, target restrictions, and atomic rejection evidence.
- `packages/bkchem-qt.app/bkchem_qt/models/document_session.py`: operation
  dispatcher, plain-payload adapter, OASA executor, and accepted-result path.
- `packages/bkchem-qt.app/bkchem_qt/modes/atom_mode.py`: replace the local
  property command with one state-gated submission and durable-ID follow-up.
- `packages/bkchem-qt.app/tests/test_atom_element_backend_authority.py`: one
  offscreen click-to-canonical-CDML behavior route and recovery/rejection facts.
- Existing focused session and interaction modules only where their former
  local-undo expectation is intentionally superseded.

## Approach

1. Establish backend grammar and tests.
   - Add `CDMLAtomElementEditRequest` beside the existing OASA operation
     values; reject non-integer revisions, missing IDs, non-direct targets,
     unsupported current or requested symbols, and same-element replacements.
   - Clone the authoritative complete document, resolve the direct-root
     molecule and direct atom, change only `<atom name>`, run strict
     complete-CDML validation, and commit at the supplied revision. Never
     perform auto valence, bond, or charge repair.
   - Return the normal `CDMLCommit`; retain the atom's already durable ID.

2. Bind the operation to `DocumentSession`.
   - Register `atom.element.set`; require exactly the four request
     fields and matching durable target keys.
   - Invoke the OASA executor directly, record accepted backend history before
     projection, and reuse the existing accepted/rejected/unavailable outcome
     semantics.
   - Add no complete-CDML candidate builder, local property command, or
     frontend-owned persistent fallback.

3. Migrate the AtomMode click.
   - Resolve the clicked AtomItem's durable atom and direct-root molecule IDs
     from the synchronized projection; capture only those IDs and the selected
     scalar element.
   - Submit exactly once when the source and replacement are supported and
     differ; on acceptance let projection replacement create new wrappers,
     then restore selection using the captured durable atom ID.
   - Leave blank clicks and excluded source/property cases unchanged except for
     truthful no-op or rejection status. Do not repurpose this route for the
     property dock or dialogs.

4. Independently review the frozen implementation.
   - Implementation reviewer: inspect the OASA request grammar, target
     isolation, complete-document preservation, and failure atomicity.
   - Qt reviewer: inspect captured IDs/scalars, no local `ChangePropertyCommand`,
     accepted-result finality, projection replacement, and backend undo/redo.
   - Test reviewer: inspect durable-CDML behavior rather than item counts,
     dataclass layouts, default values, or transient wrapper identity.

## Verification

Run only pointed checks after the associated code changes:

```bash
source source_me.sh && python3 -m pytest -q \
  packages/oasa/tests/test_cdml_atom_element_substitution.py

source source_me.sh && QT_QPA_PLATFORM=offscreen python3 -m pytest --kill-after 3 -q \
  packages/bkchem-qt.app/tests/test_qt_backend_session_adapter.py \
  packages/bkchem-qt.app/tests/test_atom_element_backend_authority.py

git diff --check
```

Backend evidence must show accepted canonical CDML retains the same molecule
and atom durable IDs while the target element changes from one supported
element to the requested different supported element. Rejection evidence must
compare the prior canonical CDML and revision with the unchanged backend result.
Qt evidence must show the click reprojects a fresh wrapper from the accepted
snapshot, preserves selection by durable ID, and navigates undo/redo through
backend revisions. Avoid collection counts, fixed defaults, and assertions over
implementation storage.

## Risk register

| Risk | Trigger | Mitigation |
| --- | --- | --- |
| Qt remains a hidden owner | A local command or model mutation occurs before acceptance. | Assert no local property command; inspect the click-to-session route. |
| Wrong target mutation | Nested, opaque, or foreign atom IDs resolve. | Use direct-root/direct-child OASA helpers and reject non-core targets. |
| Chemistry regression | An unsupported source or replacement silently changes CDML, or auto repair changes adjacent chemistry. | Exact source/replacement validation plus unchanged charge/bond/valence evidence. |
| Stale overwrite | Expected revision differs from current revision. | Reuse the existing pre-mutation revision check and unchanged-snapshot test. |
| Projection failure is treated as rollback | UI resubmits or rebuilds from old wrappers. | Reuse final-acceptance outcome and exact-current-snapshot recovery tests. |
| Scope creep | Dialog/property-dock edits begin using an under-specified operation. | Keep this operation private to AtomMode element substitution; plan future properties separately. |

## Settled decisions and delivery state

- OASA's canonical source and replacement field is `<atom name>` for this
  supported direct-core-atom route; no parallel element representation was
  introduced.
- A dedicated sibling atom-element executor keeps the request grammar explicit
  instead of broadening the structural executor into a generic atom-edit API.
- A rejected request reports the normal typed outcome/status and changes no
  backend or frontend persistent state. Same-element clicks are no-ops.
- The backend/frontend contract, Qt contract, active migration plan, and
  changelog have been updated with the verified behavior.
- This completed bounded-slice record remains in `docs/active_plans/active/`
  pending normal repository archival and delivery mechanics. It has not been
  moved or staged here.

## Remaining scope

This slice does not complete M5. Generic atom properties and dialogs, charge,
isotope, valency, topology, and other chemistry-edit families each need their
own backend operation, behavior decision, and evidence before migration.
