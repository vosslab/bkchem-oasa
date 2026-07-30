# Plan: Backend-authoritative Draw mode

## Context

The backend-authority migration has moved native documents, selected
presentation actions, repair, insertion, whole-root Delete, and revision
history onto OASA snapshots. Draw mode remains a high-impact persistent gap:
it creates `MoleculeModel`, atoms, bonds, graphics items, and local undo
commands before OASA accepts anything.

Source comparison resolves the intended user behavior. The legacy Tk Draw
mode creates a new molecule with a two-atom bonded pair for every blank-canvas
click. The current Qt path also creates a pair, but reuses its first molecule
for later blank clicks. That changes top-level document structure and makes
the Qt projection both behaviorally incorrect and a hidden persistent owner.

This plan adds one bounded backend structural-edit grammar. It preserves the
existing CDML molecule, atom, point, and bond grammar from
[CDML_FORMAT_SPEC.md](../../CDML_FORMAT_SPEC.md), rather than redesigning the
format or creating a second document authority.

## Objectives

- Preserve the legacy blank-canvas gesture as a fresh top-level bonded pair.
- Make four completed Draw-mode gestures accepted only through an atomic OASA
  structural operation and canonical snapshot reprojection.
- Keep gesture interpretation, hit testing, snapping, previews, and Qt object
  lifetime in the frontend while keeping durable topology and IDs in OASA.
- Prove that rejected, stale, and accepted-but-unprojectable requests preserve
  the transaction and projection rules in
  [CDML_BACKEND_TO_FRONTEND_CONTRACT.md](../../CDML_BACKEND_TO_FRONTEND_CONTRACT.md).

## Design philosophy

This is a **Fix the design, not the symptom** slice. A Qt-side complete-CDML
candidate builder would make the frontend choose molecule structure, durable
IDs, and preservation behavior for an edited subtree. A narrow backend
operation instead applies plain gesture intent to a detached authoritative DOM
and uses the existing atomic commit path.

The grammar is deliberately smaller than generic graph editing. It covers the
known Draw-mode gestures and leaves topology-changing cases with different
semantics for later bounded designs. This follows **Long-term over short-term**
without treating a broad graph editor as a prerequisite.

- Evidence strategy for uncertain methods: compare the resulting canonical
  CDML and behavior against the observed Tk/Qt gesture paths, then run one
  backend-only operation test and one offscreen projection test before adding
  another structural gesture.

## Scope

- Add a backend-owned immutable structural-edit request and result grammar.
- Implement atomic creation of a fresh top-level bonded pair for a blank click.
- Implement atomic extension from one existing atom, same-molecule atom join,
  and backend-owned bond-tool application.
- Route the four completed Draw-mode gestures through `DocumentSession` and
  backend revision history.
- Retain Qt hit testing, grid and angle snapping, preview rendering, and
  post-acceptance selection through durable IDs.
- Update the two architecture contracts, focused tests, active status, and
  [CHANGELOG.md](../../CHANGELOG.md) when the executable behavior lands.

## Non-goals

- Build a generic graph-editing RPC or an all-purpose molecule XML editor.
- Merge molecules, merge overlapping atoms, or connect atoms across top-level
  molecules without an explicit structural grammar.
- Migrate Atom mode, templates, fragments, transforms, partial Delete, or Cut.
- Change the CDML 26.07 element grammar or introduce an XSD.
- Change the current scene-point coordinate system, grid policy, or visual
  Draw-mode defaults beyond moving persistence acceptance to OASA.

## Current state summary

### Progress record: 2026-07-29

M1 through M3 have implementation evidence: the backend accepts the four
bounded structural operations through its revisioned canonical-CDML path, the
session records accepted backend history before reprojection, and completed
Draw gestures submit only durable IDs and scalar intent after retiring their
preview. The slice remains limited to blank-canvas bonded-pair creation,
atom extension, same-molecule atom joining, and bond-tool application.

Generic graph editing, cross-molecule merging, overlap behavior, and unrelated
legacy structural actions remain separately scoped. M4 documentation close-out
is accepted for this bounded slice. Independent final review accepted the
focused evidence: 19 OASA structural tests passed; 13 offscreen Qt Draw
authority tests passed with `--kill-after 3`; and pyflakes plus `git diff
--check` were clean.

| Area | Evidence | Required correction |
| --- | --- | --- |
| OASA session | The backend owns atomic revisioned commit, insertion, repair, whole-root Delete, and the four bounded structural operations. | Preserve the narrow operation boundary for later structural work. |
| CDML grammar | `<molecule>`, `<atom>`, `<point>`, and `<bond>` already define the emitted records and durable references. | Emit the existing grammar with backend-issued IDs. |
| Qt session | The session dispatches immutable requests, records backend history, and reprojects accepted snapshots. | Retain this direct structural route as the only accepted path for the four gestures. |
| Qt Draw mode | The four completed gestures use a transient preview, one backend submission, and accepted-snapshot reprojection. | Keep unrelated legacy structural paths separately scoped. |
| Legacy behavior | A blank click calls `new_molecule()`, then creates an atom and one bonded neighbor. | Create a fresh top-level molecule for every blank-canvas bonded pair. |

## Architecture boundaries and ownership

### Backend structural grammar

The backend exposes one immutable `CDMLStructuralEditRequest` and one immutable
`CDMLStructuralEditResult`. The request contains an expected revision, a
structural kind, scalar coordinates, scalar bond settings, and existing durable
IDs. It contains no XML nodes, Qt objects, callbacks, models, or scene state.

The result wraps the existing immutable `CDMLCommit` and reports the durable
IDs created or updated by the operation. Direct operations allocate durable
IDs themselves, so `CDMLCommit.id_map` remains the existing provisional-token
mapping and may be empty for this grammar.

| Structural kind | Required plain request data | Backend effect | Result identity |
| --- | --- | --- | --- |
| `create-bonded-pair` | two finite scene-point positions, element, bond settings | Append one new direct-root molecule containing two atoms and one bond. | Molecule ID, two atom IDs, bond ID |
| `extend-atom` | direct-root molecule ID, source atom ID, endpoint, element, bond settings | Append one atom and one bond in the named molecule. | New atom ID, bond ID |
| `join-atoms` | direct-root molecule ID, two distinct atom IDs, bond settings | Append one bond between two existing atoms in the named molecule. | New bond ID |
| `apply-bond-tool` | direct-root molecule ID, bond ID, selected type/order/simple-double settings | Apply the established Draw-mode bond transition to one existing bond. | Updated bond ID |

For all four kinds, OASA clones the current authoritative document, validates
the request and editable targets, patches only the addressed core nodes,
validates the complete candidate, and commits it through the normal revision
path. Accepted work produces one new revision and canonical snapshot. Invalid
input, topology errors, and stale revisions leave document content, history,
saved baseline, and durable-ID allocation unchanged.

The first structural grammar accepts only direct editable core-CDML targets.
`join-atoms` requires both atoms to belong to the same direct-root molecule and
rejects a self-edge or a duplicate edge. `apply-bond-tool` reads the existing
authoritative bond state, applies the current selected type/order and
simple-double policy, and writes any endpoint order or depiction fields as
needed. The backend, rather than a `BondModel`, owns the transition.

### Frontend gesture boundary

Draw mode remains the owner of pointer interpretation. On press it captures a
durable hit target and scalar settings; on move it draws only a disposable
preview; on release it selects exactly one structural kind and submits once.
It uses its established snapping and placement calculation to provide final
scene-point coordinates, but it does not make persistent model, scene, or
undo mutations.

`DocumentSession` converts the immutable Qt-side request envelope into the
backend request, records accepted backend history, and installs only the
returned canonical snapshot. It preserves post-operation focus by the result's
durable IDs. A projection failure after acceptance retains the accepted backend
snapshot and uses only exact-current-snapshot reprojection, as specified by
[QT_CONTRACT.md](../../QT_CONTRACT.md).

### Mapping (milestones / workstreams -> components / patches)

| Milestone / Workstream | Component | Review boundary |
| --- | --- | --- |
| M1 / WS-D1 | OASA structural edit grammar and backend tests | Plain request, detached DOM patch, atomic commit |
| M2 / WS-D2 | Qt session adapter and revision history | Plain request translation and canonical reprojection |
| M3 / WS-D3 | Qt Draw-mode gesture controller | Transient interaction versus persistent submission |
| M4 / WS-D4 | Contracts, tests, and independent review | Behavioral parity and no-hidden-owner evidence |

## Milestone plan

| M | Title | Summary | Goal |
| --- | --- | --- | --- |
| M1 | Backend structural grammar | Add and prove the four OASA operations. | Atomic durable topology changes have one authoritative owner. |
| M2 | Session operation route | Bind the grammar to backend history and projection replacement. | Qt can submit structure without building a document candidate. |
| M3 | Draw-mode migration | Replace local persistent mutation for the four completed gestures. | User interaction preserves behavior while Qt remains a projection. |
| M4 | Contract and evidence close-out | Update contracts and run focused independent verification. | The delivered behavior and architectural claims agree. |

### Milestone M1: Backend structural grammar

- Status: accepted for the bounded Draw slice. Independent final review
  accepted the four operations with the focused OASA structural evidence.

- Depends on: none -- the behavioral target and persistent-owner rule are
  settled by source comparison and current contracts.
- Deliverables: immutable request/result values, detached-DOM helpers,
  `edit_structure()`, and backend-only operation tests.
- Workstreams: WS-D1.
- Entry criteria: existing `CDMLDocumentSession` commit and strict validation
  behavior remain green.
- Exit criteria:
  - Each structural kind returns an immutable canonical commit and durable
    result IDs.
  - A blank-pair request appends a new root molecule without modifying prior
    direct-root order or opaque content.
  - Rejected requests are typed and atomic.
- Parallel-plan ready: no -- max parallel doers: 1, because the backend public
  request grammar must settle before its only client is changed.

### Milestone M2: Session operation route

- Status: accepted for the bounded Draw slice. Independent final review
  accepted the direct operation route, backend history recording, and canonical
  reprojection.

- Depends on: WP-D1 -- the session adapter needs the published backend values.
- Deliverables: a `draw.structure` dispatcher key, direct backend executor,
  accepted history label, result handoff, and session-level tests.
- Workstreams: WS-D2.
- Entry criteria: M1 backend focused tests pass.
- Exit criteria:
  - Qt-facing payload data stays immutable and frontend-neutral at the backend
    boundary.
  - Session acceptance records one backend history entry before canonical
    reprojection.
  - Rejected and accepted-but-unprojectable results follow existing state
    transitions without a local retry.
- Parallel-plan ready: no -- max parallel doers: 1, because it consumes the
  just-settled request/result grammar.

### Milestone M3: Draw-mode migration

- Status: accepted for the bounded Draw slice. Independent final review
  accepted the preview-only completed gestures and their one-shot backend
  submissions.

- Depends on: WP-D2 -- Draw mode needs one tested session operation route.
- Deliverables: gesture capture, preview-only drawing, submission on completed
  gestures, result-ID focus restoration, and focused offscreen behavior tests.
- Workstreams: WS-D3.
- Entry criteria: M2 session tests pass with a real backend session.
- Exit criteria:
  - Blank click/release yields a fresh top-level bonded pair each time.
  - Atom click/drag extension, same-molecule join, and bond click use OASA.
  - The migrated branches create no local persistent `MoleculeModel`, bond,
    scene, or `QUndoStack` mutation before acceptance.
- Parallel-plan ready: no -- max parallel doers: 1, because event state and
  projection lifetime share one mode/session boundary.

### Milestone M4: Contract and evidence close-out

- Status: accepted for the bounded Draw slice. Contract and progress wording
  now reflects the independent final review: 19 OASA structural tests passed,
  13 offscreen Qt Draw authority tests passed with `--kill-after 3`, and
  pyflakes plus `git diff --check` were clean.

- Depends on: WP-D3 -- documentation must describe implemented behavior.
- Deliverables: contract wording, active-plan status, changelog record,
  focused tests, and independent behavioral review.
- Workstreams: WS-D4.
- Entry criteria: M3 pointed tests pass without a native Qt crash.
- Exit criteria:
  - The contract table names the structural operation and its typed failures.
  - Qt state rules identify the four gestures as backend-authoritative.
  - Independent review confirms blank-click top-level behavior and no
    frontend-side document reconstruction.
- Parallel-plan ready: yes -- max parallel doers: 2, because documentation
  review and independent behavioral audit can proceed after the code freezes.

## Workstream breakdown

### Workstream WS-D1: Own structural persistence

- Goal: make OASA the sole owner of durable Draw-mode topology changes.
- Owner: expert_coder.
- Work packages: WP-D1.
- Interfaces:
  - Needs: current CDML session commit/validation primitives.
  - Provides: immutable request/result types and `edit_structure()`.
- Review boundary, when modifying the repository: OASA-only behavior and
  no-PySide6 import boundary.

### Workstream WS-D2: Adapt the Qt session

- Goal: submit structural intent without making Qt a document writer.
- Owner: expert_coder.
- Work packages: WP-D2.
- Interfaces:
  - Needs: WP-D1 request/result grammar.
  - Provides: backend history, canonical reprojection, and durable result IDs.
- Review boundary, when modifying the repository: `DocumentSession` operation
  dispatch and state-machine conformance.

### Workstream WS-D3: Preserve Draw interaction

- Goal: make the user-visible gestures use the migrated session route.
- Owner: PySide6 engineer.
- Work packages: WP-D3.
- Interfaces:
  - Needs: WP-D2 session operation route.
  - Provides: preview-only gesture controller and offscreen behavior evidence.
- Review boundary, when modifying the repository: Draw-mode pointer handling,
  scene lifetime, and no-local-persistence invariant.

### Workstream WS-D4: Verify and document behavior

- Goal: record only behavior that the delivered route proves.
- Owner: reviewer.
- Work packages: WP-D4.
- Interfaces:
  - Needs: WP-D3 frozen implementation and test results.
  - Provides: independent assessment and documentation completion.
- Review boundary, when modifying the repository: contracts, focused tests,
  changelog wording, and active-plan status.

## Work packages

### Work package WP-D1: Implement structural edit operations

- Owner: expert_coder.
- Touch points: `packages/oasa/oasa/cdml_document.py`, a small backend-only
  structural helper if it reduces DOM complexity, and
  `packages/oasa/tests/test_cdml_structural_edit.py`.
- Depends on: none.
- Acceptance criteria:
  - Validate exact request fields, finite scene points, editable direct-root
    targets, supported normalized element symbols, and supported bond settings.
  - Allocate all created molecule, atom, and bond IDs against the complete
    document, including opaque ID declarations.
  - Serialize only new point values using the established scene-point to `cm`
    conversion and leave untouched XML as stored.
  - Return created or updated durable IDs separately from provisional-token
    mappings.
- Evidence or review, when useful:
  - Run the backend operation module and the existing backend authority module.
  - Ask a fresh reviewer to inspect target validation and atomic failure paths.
- Obvious follow-ons:
  - Publish the exact immutable request and result values to WP-D2.

### Work package WP-D2: Route structural edits through the session

- Owner: expert_coder.
- Touch points: `packages/bkchem-qt.app/bkchem_qt/models/document_session.py`
  and `packages/bkchem-qt.app/tests/test_qt_backend_session_adapter.py`.
- Depends on: WP-D1.
- Acceptance criteria:
  - Register `draw.structure` with a direct OASA executor rather than a
    complete-CDML candidate builder.
  - Keep `PersistentOperationRequest` data plain and immutable at the Qt
    adapter boundary.
  - Record one accepted backend history entry and project only the returned
    immutable snapshot.
  - Return accepted projection failure as final acceptance plus exact-snapshot
    recovery eligibility, never a candidate retry.
- Evidence or review, when useful:
  - Run the pointed session adapter test with injected projection failure.
- Obvious follow-ons:
  - Expose a small result-to-selection helper for WP-D3.

### Work package WP-D3: Migrate Draw-mode gestures

- Owner: PySide6 engineer.
- Touch points: `packages/bkchem-qt.app/bkchem_qt/modes/draw_mode.py`,
  `packages/bkchem-qt.app/tests/test_draw_backend_authority.py`, and only the
  existing focused GUI-event/interactions tests whose old local assumption is
  replaced.
- Depends on: WP-D2.
- Acceptance criteria:
  - Capture a pointer gesture and draw a preview without persistent model,
    graphics, or undo ownership changes.
  - Submit `create-bonded-pair` for every blank click/release, even when prior
    molecules exist.
  - Submit `extend-atom` for a completed atom-to-empty gesture and
    `join-atoms` for a completed same-molecule atom-to-atom gesture.
  - Submit `apply-bond-tool` for a completed bond click and focus the returned
    durable target after canonical reprojection.
- Evidence or review, when useful:
  - Run serial offscreen behavior tests and stop for teardown investigation if
    the native process crashes.
- Obvious follow-ons:
  - Remove migrated call paths to local structural helper methods while keeping
    still-unmigrated modes isolated.

### Work package WP-D4: Close contracts and review evidence

- Owner: reviewer.
- Touch points: [CDML_BACKEND_TO_FRONTEND_CONTRACT.md](../../CDML_BACKEND_TO_FRONTEND_CONTRACT.md),
  [QT_CONTRACT.md](../../QT_CONTRACT.md), this active plan, and
  [CHANGELOG.md](../../CHANGELOG.md).
- Depends on: WP-D3.
- Acceptance criteria:
  - Describe the behavior in backend snapshots, revisions, atomic operations,
    durable IDs, and typed failures rather than Qt implementation classes.
  - State that accepted structural candidates cannot be submitted again and
    exact snapshot reprojection is the only post-acceptance recovery.
  - Update the active migration status without calling unrelated structural
    action families complete.
- Evidence or review, when useful:
  - Run pointed Markdown-link checking and an independent source/test review.
- Obvious follow-ons:
  - Return future structural actions to a new bounded operation design.

## Acceptance criteria and gates

- Per-patch gate: focused behavior evidence, `git diff --check`, and one
  changelog entry when executable behavior changes.
- Backend operation gate: every accepted kind produces one canonical backend
  revision and returns only backend-owned immutable values.
- Blank-pair gate: two blank-canvas gestures create two distinct top-level
  molecules, each with a bond joining its two newly allocated atom IDs.
- Preservation gate: unrelated root/molecule ordering, attributes, and opaque
  XML remain semantically unchanged after each accepted operation.
- Atomicity gate: invalid element, bond setting, coordinate, target, duplicate
  edge, and stale-revision requests leave the prior snapshot exactly unchanged.
- Projection gate: a successful backend acceptance remains final if projection
  replacement fails; recovery reads only the accepted/current snapshot.
- Ownership gate: migrated Draw-mode paths carry only durable IDs and scalars
  across the boundary and own no local persistent undo mutation.
- Independent review gate: accepted. A fresh reviewer verified the top-level
  blank-click rule and the no-Qt-document-reconstruction property, with 19
  OASA structural tests and 13 offscreen Qt Draw authority tests passing.

## Test and verification strategy

- Add `packages/oasa/tests/test_cdml_structural_edit.py` with inline complete
  CDML inputs that first enter through `CDMLDocumentSession`; use the owning
  hardened CDML parser for structural inspection.
- Assert durable bond endpoints, document order, preserved opaque content, and
  typed atomic failure rather than brittle object counts or raw DOM behavior.
- Extend the existing session adapter module with one backend request/revision
  scenario and one accepted-projection-failure scenario.
- Add one Draw-mode authority module that drives press/move/release in an
  offscreen Qt session and observes canonical backend CDML plus fresh
  projections. Keep direct geometry-helper tests in their existing module.
- Run only the changed focused modules during development:

```bash
source source_me.sh && python3 -W error -m pytest \
  packages/oasa/tests/test_cdml_structural_edit.py \
  packages/oasa/tests/test_cdml_document_authority.py

source source_me.sh && QT_QPA_PLATFORM=offscreen python3 -W error -m pytest \
  --kill-after 3 \
  packages/bkchem-qt.app/tests/test_qt_backend_session_adapter.py \
  packages/bkchem-qt.app/tests/test_draw_backend_authority.py
```

- Run the existing backend import-boundary assertion and pointed Markdown-link
  test only after those focused modules pass. Each pytest remains offline,
  deterministic, and free of sleeps, network access, large fixtures, and
  subprocess round trips.

## Risk register

| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| Qt local mutation remains reachable | High | A migrated gesture calls local atom/bond or undo helpers. | WP-D3 | Use request recording and canonical snapshot assertions. |
| Cross-molecule topology is silently changed | High | Join resolves atoms in different root molecules. | WP-D1 | Reject it atomically until a separate merge grammar exists. |
| Bond-cycle behavior drifts | Medium | Existing selected type/order produces different CDML. | WP-D1/WP-D3 | Pin representative normal, double, and directed-style transitions. |
| Projection teardown crashes | High | Offscreen test exits with a native failure. | WP-D3 | Run serially, inspect retirement ownership, then correct the lifecycle design. |
| Scope expands into generic editing | Medium | A new gesture needs targets or semantics outside the four kinds. | manager | Write a separate bounded operation plan before implementation. |
| Contracts overclaim completion | Medium | Docs say all structural editing is authoritative. | WP-D4 | Name only the four delivered gestures and their exclusions. |

## Documentation close-out requirements

- Active plan / progress tracker: update this plan and the M5 status in
  [cdml_backend_authority_migration_2026-07-27.md](cdml_backend_authority_migration_2026-07-27.md).
- `docs/CHANGELOG.md` entry: record the four delivered backend-authoritative
  Draw-mode operations and no broader graph-editing claim.
- Contracts: update the backend operation table and Qt persistent-operation
  behavior after the code and focused evidence agree.
- Archive / closure notes: all four gates and the independent review are
  complete for this bounded slice. Keep the plan active while its explicit
  non-goals remain separately scoped in the broader migration.

## Patch plan and reporting format

- Patch 1: OASA structural request/result, atomic DOM patching, and backend
  operation tests.
- Patch 2: `DocumentSession` direct executor, backend history, and exact
  reprojection tests.
- Patch 3: Draw-mode transient gesture controller and offscreen behavior tests.
- Patch 4: contracts, changelog, active-plan status, and independent review.

Each patch report states the changed persistent owner, the focused evidence,
the still-isolated local paths, and the next dependency.

## Resolved decisions

- The blank-canvas product is a two-atom bonded pair in a new top-level
  molecule, not a single atom and not a component appended to an older molecule.
- The first operation family contains `create-bonded-pair`, `extend-atom`,
  `join-atoms`, and `apply-bond-tool`.
- OASA issues all new durable IDs; direct structural results report those IDs
  separately from candidate provisional-token mappings.
- The backend operation commits a detached complete-CDML candidate internally;
  Qt does not construct or publish that candidate.
- Same-molecule joins are included; cross-molecule merge and overlap handling
  require their own semantics.

## Open questions and decisions needed

- Manager/subagent decision procedure:
  - Decision owner or dedicated class: backend implementer with an independent
    reviewer.
  - Evidence and decision rule: retain existing Draw-mode semantics when the
    source comparison identifies them; choose internal DOM-helper placement
    only if focused atomicity and preservation tests remain equivalent.
- Non-blocking follow-up: evaluate partial structural Delete, atom overlap
  merge, and cross-molecule joining only through separately scoped operation
  designs after this slice reaches its acceptance gate.
