# Plan: Backend-authoritative atom numbering

## Context

Before this slice, `MiscMode` assigned and cleared atom numbers by changing a
Qt `AtomModel` through a local undo command. That made a persistent CDML field
depend on projection state until a later serialization path happened to publish
it. The completed route has OASA accept the complete persistent change
atomically and Qt rebuild from the accepted snapshot.

The accepted `tmp/atom_numbering_baseline_2026-07-29.md` probe establishes
useful, limited facts. The current Qt model reads `number` and
`show_number` attributes; it serializes an assigned number with a visibility
attribute, removes both attributes when the number is cleared, and preserves a
hidden assigned number. It also removes a legacy `atom_number` mark on Qt
fragment serialization rather than translating that mark. The probe does not
measure pointer behavior or undo. The accepted M0 results, including the
gesture evidence, are recorded in
[atom_numbering_m0_decision_2026-07-29.md](../decisions/atom_numbering_m0_decision_2026-07-29.md).

The format already documents direct-atom `number` and `show_number`
attributes in [CDML_FORMAT_SPEC.md](../../CDML_FORMAT_SPEC.md). The first
implementation gate therefore evaluates a narrow mutation of existing CDML
before considering any grammar change.

## Objectives

- Make OASA the sole persistent owner of assigning, replacing, and clearing a
  positive number on one direct editable core atom.
- Use the frozen M0 visibility policy through canonical CDML, backend
  navigation, and Qt reprojection.
- Make Qt capture only durable molecule and atom IDs plus scalar edit intent,
  then project the accepted backend snapshot.
- Preserve the transaction, saved-baseline, bounded-history, recovery, and
  typed-failure semantics already specified by
  [CDML_BACKEND_TO_FRONTEND_CONTRACT.md](../../CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  and [QT_CONTRACT.md](../../QT_CONTRACT.md).
- Apply the frozen M0 legacy `atom_number` mark policy before code changes.

## Design philosophy

This slice applies **Fix the design, not the symptom**. A later Qt
serialization of a local property change would preserve the hidden frontend
owner; a narrow backend operation makes canonical CDML the direct result of a
gesture. **Atomic task decomposition** keeps one direct atom and one number
edit small enough to validate without introducing a generic property protocol.

Under **Use the scientific method**, M0 records source and format evidence,
then freezes the request, visibility, and legacy semantics before
implementation. The resulting change favors
**Design for adaptability**: a future batch renumber or property editor can
gain a separate operation without widening this gesture's contract.

## Scope

- Define and implement one revision-bound backend operation for a direct core
  molecule and one direct editable core atom.
- Assign or replace that atom's number with a positive integer and explicit
  boolean visibility, or clear it with the frozen `(None, None)` pair.
- Validate durable target IDs, request shape, positive-number range, current
  revision, target eligibility, and complete-CDML preservation before atomic
  acceptance.
- Route the completed `MiscMode` Number and Clear Numbers gestures through a
  session request carrying only plain scalar data and durable target IDs.
- Reuse canonical accepted-snapshot reprojection, backend history, dirty
  state, undo/redo navigation, and exact-snapshot recovery.
- Add focused backend, session, and offscreen Qt behavior evidence plus an
  independent implementation review.
- Record the accepted behavior in the contracts, active migration plan, and
  changelog after implementation passes review.

## Non-goals

- Implement batch renumbering, automatic sequence allocation, or a generic
  property dialog.
- Change bonds, coordinates, chemistry semantics, atom identity, topology,
  or source molecule membership.
- Extend numbering to markers, queries, groups, text, or other object kinds.
- Retain the existing CDML 26.07 grammar and version for this operation.
- Convert, delete, duplicate, or migrate a direct legacy `atom_number` mark.
- Ordinary load, round-trip, and unrelated edits preserve a direct legacy
  `atom_number` mark. A direct numbering edit targeted at its marked atom
  returns typed compatibility failure with no mutation.
- Reuse a Qt-local persistent undo command or frontend-generated complete
  document as a fallback.

## Current state summary

| Evidence source | Observed fact | Planning consequence |
| --- | --- | --- |
| Atom-numbering probes | Visible and hidden values survive current Qt behavior; clearing removes both serialized fields. | M0 freezes an explicit boolean visibility scalar. |
| Atom-numbering probes | A legacy `atom_number` mark is preserved by the backend but removed by the current fragment writer. | M0 freezes typed rejection for a targeted number edit. |
| `MiscMode` source | Current gestures mutate a projection through a local undo command. | Migrate the persistent write, not merely the final serializer. |
| CDML format | Direct atom `number` and `show_number` are documented attributes. | Start with a narrowly scoped attribute mutation; no new element is presumed. |
| Existing backend operations | Direct-target operations already use expected revisions, detached candidates, strict validation, and canonical commits. | Reuse that atomic transaction design with a new narrow request. |

The probe's next-number result and source reading are useful compatibility
inputs, not an implementation promise. This plan does not treat them as proof
of click-counter or undo behavior.

## Architecture boundaries and ownership

| Layer | Owns | Boundary behavior |
| --- | --- | --- |
| OASA document service | Request validation; direct target resolution; detached candidate mutation; complete-CDML validation; atomic commit; canonical snapshot and history. | Receives immutable revision, durable IDs, `number`, and `show_number`. Returns the ordinary accepted snapshot or typed failure. |
| Qt session | Capability and stale-revision gate; immutable request construction; accepted history recording; canonical reprojection; durable selection intent. | Sends no Qt object, graphics item, local command, or complete document for this operation. |
| `MiscMode` | Hit test; durable target lookup from a synchronized projection; user-facing status; transient sequence display. | Captures frozen M0 scalars, submits once, and treats accepted state as final. |
| Qt projection | Atom labels, selection, hover, and wrapper lifetime. | Is disposable and derives its number display only from the accepted backend snapshot. |

### Mapping (milestones / workstreams -> components / patches)

| Milestone / Workstream | Component | Review boundary |
| --- | --- | --- |
| M0 / WS-A | Number and legacy compatibility decision record | Evidence sufficiency and exact request semantics |
| M1 / WS-B | OASA number operation and backend tests | Target isolation, preservation, and atomic failure |
| M2 / WS-C | Session adapter and MiscMode gestures | Plain-data boundary and projection authority |
| M3 / WS-D | Focused tests and documentation | User-visible behavior and independent review |

## Milestone plan

| M | Title | Summary | Goal |
| --- | --- | --- | --- |
| M0 | Choose bounded semantics | Complete: [frozen decision](../decisions/atom_numbering_m0_decision_2026-07-29.md) records request shape, visibility, and legacy compatibility. | M1 has one unambiguous implementation handoff. |
| M1 | Commit the direct atom edit | Complete: one direct-atom operation and focused backend evidence. | One accepted edit changes only its named direct atom. |
| M2 | Route the Qt gestures | Complete: Number and Clear Numbers submit the session operation. | Qt captures intent and reprojects canonical state. |
| M3 | Prove and document delivery | Complete: focused behavior checks, independent review, and durable records. | The slice is evidenced without expanding M5. |

## Completion receipt

- M0 froze the direct-atom request, visibility, compatibility, and transient
  candidate rules before implementation.
- M1 focused verification:
  `source source_me.sh && python3 -W error -m pytest -q packages/oasa/tests/test_cdml_atom_numbering.py`
  reports `22 passed`.
- M2 focused verification:
  `source source_me.sh && QT_QPA_PLATFORM=offscreen python3 -W error -m pytest --kill-after 3 -q packages/bkchem-qt.app/tests/test_persistent_atom_numbering.py`
  reports `7 passed`.
- Fresh backend and Qt reviews accepted the direct-target, atomic-failure,
  backend-history, snapshot-derived candidate, and exact-reprojection rules.
- M3 records the delivered behavior in the durable contracts. The plan remains
  active only until the broader migration manager performs normal closure.

### Milestone M0: Choose bounded semantics (complete)

- Decision record: [atom_numbering_m0_decision_2026-07-29.md](../decisions/atom_numbering_m0_decision_2026-07-29.md).
- Result: `atom.number.set` uses `expected_revision`, `molecule_id`, `atom_id`,
  `number: int | None`, and `show_number: bool | None`; it has no action
  field. Assignment/replacement is a positive non-bool integer plus boolean;
  clear is exactly `(None, None)`.
- M1 handoff: direct legacy `atom_number` marks receive typed compatibility
  failure, and current CDML 26.07 attributes remain adequate.

### Milestone M1: Commit the direct atom edit (complete)

- Depends on: complete M0 decision record.
- Deliverables: one immutable OASA request/result route and focused backend
  tests.
- Workstreams: WS-B.
- Entry criteria: M1 implements exactly
  `atom.number.set(expected_revision, molecule_id, atom_id, number: int | None,
  show_number: bool | None)`. It has no action field; assignment/replacement
  and clear use the frozen M0 pairs.
- Exit criteria: a valid request changes only the selected direct atom's
  selected number fields; stale, invalid, nested, unknown, or wrong-kind
  targets leave canonical content and revision unchanged.
- Parallel-plan ready: no -- one request grammar and mutator share a contract.

### Milestone M2: Route the Qt gestures (complete)

- Depends on: M1 -- the frontend adapter binds to the accepted backend shape.
- Deliverables: one session operation and completed Number/Clear Numbers
  gesture routes.
- Workstreams: WS-C.
- Entry criteria: M1 backend behavior is independently reviewed.
- Exit criteria: each supported click sends one immutable request, makes no
  local persistent mutation, and displays only the accepted canonical result.
- Parallel-plan ready: no -- gesture behavior depends on the final backend
  request and should remain serial with the adapter.

### Milestone M3: Prove and document delivery (complete)

- Depends on: M2 -- tests and documentation describe delivered behavior.
- Deliverables: pointed verification receipts, fresh backend and Qt reviews,
  and scoped documentation updates.
- Workstreams: WS-D.
- Receipt: focused OASA and offscreen Qt atom-number tests pass; fresh backend
  and Qt reviews accept the bounded authority and recovery behavior.
- Exit criteria: durable records describe only the direct-atom operation, with
  no claim about batch numbering or legacy conversion.
- Parallel-plan ready: yes -- test review and documentation review have no
  shared code ownership after the implementation patch is frozen.

## Workstream breakdown

### Workstream WS-A: Record number and legacy semantics (complete)

- Goal: provide the M1-ready M0 decision from accepted evidence.
- Owner: architect.
- Work packages: WP-A1.
- Needs: the accepted probe, CDML format vocabulary, current parser/writer
  behavior, and the backend/frontend contracts.
- Provides: exact request semantics for WS-B and WS-C.
- Review boundary: decision evidence only; no production mutation.

### Workstream WS-B: Implement backend transaction (complete)

- Goal: make the direct atom mutation authoritative and atomic.
- Owner: expert_coder.
- Work packages: WP-B1.
- Needs: WP-A1.
- Provides: frozen request grammar and OASA acceptance path for WS-C.
- Review boundary: OASA CDML operation and backend-only tests.

### Workstream WS-C: Bind session and gestures (complete)

- Goal: replace the local persistent numbering path with canonical reprojection.
- Owner: coder.
- Work packages: WP-C1.
- Needs: WP-B1.
- Provides: user gesture behavior and session-level outcomes for WS-D.
- Review boundary: Qt-only adapter, mode, and offscreen behavior tests.

### Workstream WS-D: Verify and record (complete)

- Goal: independently validate behavior and publish only accepted facts.
- Owner: reviewer.
- Work packages: WP-D1, WP-D2.
- Needs: WP-B1, WP-C1.
- Provides: acceptance or blocking findings, then durable documentation.
- Review boundary: one reviewer examines backend authority and another Qt
  lifecycle/behavior; documentation follows their acceptance.

## Work packages

### WP-A1: Record exact number, visibility, and legacy behavior (complete)

- Owner: architect.
- Touch points: the accepted probe; `misc_mode.py`; CDML parser and fragment
  behavior; [CDML_FORMAT_SPEC.md](../../CDML_FORMAT_SPEC.md); contracts.
- Depends on: none.
- Decision: [atom_numbering_m0_decision_2026-07-29.md](../decisions/atom_numbering_m0_decision_2026-07-29.md)
  freezes the nullable-pair grammar, explicit visibility scalar, typed legacy
  compatibility failure, and frontend-only transient sequence behavior.
- Evidence or review: accepted evidence enters complete CDML through the
  owning boundary before compatibility inspection and remains scoped to the
  documented observations.
- Obvious follow-ons: hand the exact immutable request to WP-B1.

### WP-B1: Add the OASA direct-atom number operation (complete)

- Owner: expert_coder.
- Touch points: `packages/oasa/oasa/cdml_document.py` and one focused OASA
  test module beside the existing atom-element operation tests.
- Depends on: complete WP-A1 decision record.
- Acceptance criteria:
  - Add `atom.number.set(expected_revision, molecule_id, atom_id,
    number: int | None, show_number: bool | None)` with the frozen M0
    assignment/replacement and clear pairs.
  - Resolve only one direct-root core molecule and one direct editable atom.
  - Clone the authoritative complete document, update only the selected
    documented number and visibility attributes, run strict validation, and
    accept through the normal revision transaction.
  - Preserve every unselected record, durable ID, source order, unrelated atom
    attribute, opaque extension, and selected atom chemistry field.
  - Return typed atomic failures for malformed scalar shapes, nonpositive
    assignment, stale revision, missing target, and non-direct or wrong-kind
    target.
- Evidence or review: backend tests begin complete-CDML inputs at the owning
  hardened CDML boundary and assert semantic preservation rather than XML
  formatting or collection counts.
- Obvious follow-ons: expose the accepted request to WP-C1.

### WP-C1: Submit the session request from MiscMode (complete)

- Owner: coder.
- Touch points: `packages/bkchem-qt.app/bkchem_qt/models/document_session.py`,
  `packages/bkchem-qt.app/bkchem_qt/modes/misc_mode.py`, and focused Qt tests.
- Depends on: WP-B1 -- frozen backend request grammar.
- Acceptance criteria:
  - Register one immutable session operation with exactly the backend request
    scalars and matching durable target keys.
  - Resolve the clicked synchronized projection to durable molecule and atom
    IDs, submit exactly once, and use no local persistent undo command or
    model write.
  - Update status and any retained transient sequence display from the frozen
    M0 policy and an accepted/rejected outcome.
  - Install only the accepted canonical snapshot, restore selection by the
    durable atom ID where appropriate, and keep accepted commits final when
    projection installation fails.
  - Recover only by reprojection of the exact current backend snapshot; never
    resubmit an accepted number request.
- Evidence or review: offscreen tests cover an assignment/replacement and a
  clear gesture, a typed rejection, and accepted-then-reprojection recovery
  without relying on Qt wrapper identity or item counts.
- Obvious follow-ons: hand focused receipts to WP-D1 and WP-D2.

### WP-D1: Independently review authority and behavior (complete)

- Owner: reviewer.
- Touch points: frozen WP-B1/WP-C1 patch and focused evidence.
- Depends on: WP-B1, WP-C1.
- Acceptance criteria:
  - Verify backend-facing inputs and outputs contain only backend-owned plain
    data and canonical CDML state.
  - Verify accepted commits are recorded before projection and remain final
    through projection failure.
  - Verify the legacy policy matches the M0 decision and that no code expands
    scope to other number-bearing CDML records.
- Evidence or review: return ACCEPT or BLOCK with file and behavior evidence.
- Obvious follow-ons: ACCEPT releases WP-D2; BLOCK returns the smallest
  corrective work package to its original owner.

### WP-D2: Update durable records (complete)

- Owner: integrator.
- Touch points: backend/frontend contract, Qt contract, active migration plan,
  this plan's completion record, and `docs/CHANGELOG.md`.
- Depends on: WP-D1 -- accepted implementation facts only.
- Acceptance criteria:
  - Describe the behavior in ownership and transaction terms rather than
    current Python implementation names.
  - Record the frozen visibility and legacy policy, direct-atom scope, and
    recovery semantics.
  - Record the narrower M5 progress without claiming batch numbering or
    generic property editing is complete.
- Evidence or review: pointed Markdown-link and whitespace checks pass.
- Obvious follow-ons: archive this active plan through normal repository
  closure mechanics when the broader manager closes the slice.

## Acceptance criteria and gates

- M0 semantics gate: complete. The
  [M0 decision record](../decisions/atom_numbering_m0_decision_2026-07-29.md)
  freezes the number domain, request shape, visibility rule, and legacy policy.
- Backend gate: complete. An accepted assignment or clear changes only the requested
  direct atom in canonical CDML; every rejected request leaves current
  snapshot, revision, and history unchanged.
- Session gate: complete. A non-Qt client can submit the selected serialized request and
  receive an accepted snapshot or typed failure without importing PySide6.
- Qt gate: complete. The Number and Clear Numbers gestures submit durable IDs and
  scalar intent, rebuild from the accepted snapshot, and use backend
  undo/redo/dirty behavior.
- Recovery gate: complete. After an accepted commit, a forced projection installation
  failure allows exact-current-snapshot reprojection only; candidate
  resubmission is never a recovery path.
- Independent review gate: complete. Fresh backend and Qt reviewers accept the
  frozen behavior before documentation records it as delivered.

## Test and verification strategy

Focused tests follow [PYTEST_STYLE.md](../../PYTEST_STYLE.md): inline safe
CDML inputs, owning hardened CDML ingress, no network, no timing, and a small
number of behavioral assertions per test.

```bash
source source_me.sh && python3 -W error -m pytest -q \
  packages/oasa/tests/test_cdml_atom_numbering.py

source source_me.sh && QT_QPA_PLATFORM=offscreen python3 -W error -m pytest --kill-after 3 -q \
  packages/bkchem-qt.app/tests/test_persistent_atom_numbering.py

git diff --check -- \
  packages/oasa/oasa/cdml_document.py \
  packages/oasa/tests/test_cdml_atom_numbering.py \
  packages/bkchem-qt.app/bkchem_qt/models/document_session.py \
  packages/bkchem-qt.app/bkchem_qt/modes/misc_mode.py \
  packages/bkchem-qt.app/tests/test_persistent_atom_numbering.py
```

The final commands are selected after files exist; their behavior, not their
filenames, is the gate. The accepted M0 compatibility experiment remains
historical evidence; M1 promotes stable required behavior to focused tests.

## Risk register

| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| Visibility drift | A clear or replacement changes whether a number is visible unexpectedly. | M1 does not write the supplied M0 boolean. | Expert coder | Assert the explicit serialized result in focused backend tests. |
| Legacy-content loss | An edit drops or duplicates an `atom_number` mark. | M1 reaches a targeted direct legacy mark. | Expert coder | Return the frozen typed compatibility failure before mutation. |
| Qt remains hidden owner | A local command or model field changes before backend acceptance. | Gesture test passes without a session request. | Coder | Make the session request the only persistent gesture path and inspect it independently. |
| Wrong target mutation | A nested, opaque, query, or group record is edited. | Target resolution uses a broad ID search. | Expert coder | Reuse direct-root/direct-child helpers and reject every other target. |
| Counter scope creep | An unmeasured automatic sequence rule becomes backend behavior. | The implementation derives a number without M0 evidence. | Architect | Require an explicit positive number until a dedicated sequence experiment supports more. |
| Projection failure masks acceptance | UI sends the request again after a successful commit. | A forced installation fault performs another backend mutation. | Coder | Reuse exact-snapshot retry and test finality. |

## Documentation close-out requirements

- Active plan / progress tracker: add a concise completion record to this
  plan and classify the bounded slice in the broad migration plan.
- Contract records: update
  [CDML_BACKEND_TO_FRONTEND_CONTRACT.md](../../CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  and [QT_CONTRACT.md](../../QT_CONTRACT.md) only with accepted behavior.
- Format record: update [CDML_FORMAT_SPEC.md](../../CDML_FORMAT_SPEC.md) only
  if M0 proves its existing attribute semantics are insufficient.
- `docs/CHANGELOG.md` entry: record the delivered authority boundary and the
  legacy compatibility outcome after acceptance.
- Archive / closure notes: move this plan only through the repository's normal
  closure process after the manager accepts M3.

## Patch plan and reporting format

- Patch 1: complete M0 decision evidence; use the frozen request, visibility,
  and legacy policy for implementation.
- Patch 2: M1 OASA request, transaction, and focused backend tests.
- Patch 3: M2 session adapter, MiscMode route, and focused offscreen tests.
- Patch 4: M3 independent reviews and accepted documentation updates.

Each report states the work-package ID, touched files, focused commands and
outcomes, remaining risks, and whether the next package is unblocked. It uses
`ACCEPT` or `BLOCK` for independent review results.

## Follow-up boundary

The frozen M0 record leaves batch renumbering, automatic sequence allocation,
marker/query/group/text numbering, and a generic property editor for separate
evidence and plans.
