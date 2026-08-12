# Plan: Backend-authoritative TemplateMode placement

## Context

The current PySide6 `TemplateMode` loads a system-template name from
`oasa.known_groups`, converts its SMILES into an OASA molecule, translates a
Qt `MoleculeModel` to the click position, and pushes an `AddMoleculeCommand`.
The persistent model, graphics projection, and local undo command are all
created before OASA accepts a document change. On an atom click, current Qt
uses only the clicked atom's coordinates and still adds a separate detached
molecule; it does not attach or fuse the template.

The legacy Tk mode is useful behavioral evidence, but it is not the delivered
frontend contract. Its atom and bond paths choose attachment geometry and may
append/fuse a template according to valency and template markers. That is a
different chemical operation from current Qt detached placement. This plan
preserves the current Qt behavior deliberately:

- a blank click inserts one separate template molecule anchored at the click;
- an atom click inserts one separate template molecule anchored at the clicked
  atom's position; and
- the clicked atom and its molecule remain unchanged.

It uses the existing OASA `molecule.insert` transaction rather than treating
that behavior as a partial implementation of legacy attachment.

## Objectives

- Make OASA own system-template SMILES resolution, molecule preparation,
  coordinate generation, CDML proposal generation, placement, durable-ID
  allocation, validation, and canonical acceptance.
- Make TemplateMode submit one immutable plain placement intent through the
  session and display only the accepted backend snapshot.
- Preserve the current blank-click and atom-anchor user behavior without
  changing the clicked source molecule.
- Establish the current visible system-template scale and anchor semantics by
  a deterministic comparison before moving that calculation into OASA; retain
  those finite user-visible semantics without imposing pixel equivalence.
- Make the delivered detached behavior clear in TemplateMode's user-facing
  hint and relevant docstrings: an atom click places a separate template at
  that atom's anchor rather than attaching or fusing chemistry.
- Reuse `CDMLMoleculeInsertionRequest`, `insert_molecules()`, backend
  revision history, and the established accepted-snapshot reprojection path.
- Prove rejected and accepted-but-unprojectable placement has the transaction
  behavior required by
  [CDML_BACKEND_TO_FRONTEND_CONTRACT.md](../../CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  and [QT_CONTRACT.md](../../QT_CONTRACT.md).

## Design philosophy

This is a **Fix the design, not the symptom** migration. Replacing the local
`AddMoleculeCommand` with a later serialization step would leave Qt as the
hidden owner of a persistent template molecule. The durable fix moves the
SMILES-to-CDML proposal and placement calculation to OASA, then commits that
proposal through the existing complete-document insertion transaction.

**Atomic task decomposition** keeps detached placement distinct from template
attachment. That delivers the existing Qt gesture through the correct owner
now, while leaving a future attachment/fusion operation free to establish its
own chemistry, valency, marker, and cross-molecule invariants from evidence.

The implementation should first run a small deterministic preparation
experiment with representative system-template SMILES at two anchors. It
must record the current Qt rule: `oasa_mol_to_qt_mol()` applies a 40-point
average-bond-length scale before centroid translation. Compare finite anchor
and resulting canonical CDML coordinate facts, then move the resulting finite
scale/anchor behavior into the OASA helper. The experiment informs the helper
without changing the settled ownership boundary or requiring pixel-equivalent
rendering.

## Scope

- The current system-template catalog, supplied to TemplateMode as immutable
  names through the session boundary.
- One detached molecule insertion per accepted blank or atom click.
- OASA-owned resolution of the selected template name to SMILES, OASA molecule
  parsing and coordinate generation, measured placement-scale preparation,
  deterministic translation to a finite CDML scene-point anchor, and detached
  molecule-only proposal serialization.
- The existing OASA `CDMLMoleculeInsertionRequest` and `insert_molecules()`
  commit path, including provisional-token consumption and returned durable
  `CDMLCommit.id_map`.
- A `DocumentSession` `template.insert` adapter that prepares the proposal in
  OASA and delegates acceptance to the existing `molecule-insertion` executor.
- TemplateMode hit testing, plain intent capture, status reporting, durable
  post-acceptance selection, backend undo/redo, and canonical projection
  replacement.
- Focused backend, session, and offscreen Qt behavior tests.

## Non-goals

- Atom or bond attachment, template fusion, valency resolution, overlap
  handling, atom merging, or cross-molecule topology changes.
- Legacy Tk bond-click behavior, template-marker editing, template-marker
  export, or generation of user-editable attachment markers.
- BioTemplateMode, user-template sources, categories, YAML template catalog
  expansion, or Save as Template.
- A generic template RPC, a frontend-built CDML proposal, a Qt-local
  persistent undo command, or a frontend-owned durable ID allocator.
- Changing the CDML 26.07 element grammar, visual template choices, grid
  policy, or general import behavior.

## Observed behavior and settled compatibility decision

| Source | Blank click | Atom click | Bond click | Decision for this slice |
| --- | --- | --- | --- | --- |
| Current Qt `TemplateMode` | Builds a detached Qt molecule at the click and pushes local `AddMoleculeCommand`. | Reads the atom's coordinates, then builds the same detached Qt molecule. | No TemplateMode bond attachment route. | Preserve blank and atom-anchor detached placement through OASA. |
| Legacy Tk `template_mode` | Transforms and appends a template molecule. | Chooses attachment geometry from valency/neighbors and can append/fuse. | Uses bond geometry and template-marker rules. | Treat as future attachment reference, not parity required by this operation. |

The successful atom-anchor result contains an additional direct-root molecule.
It does not add a bond to the clicked atom, edit the clicked atom, mutate its
source molecule, or create marker records. The atom source is used only to
derive the anchor position from a synchronized projection before submission.

TemplateMode's visible status hint and relevant docstrings must describe this
same delivered behavior precisely: clicking an atom places a separate template
at that atom's anchor. They must not describe the detached operation as
attaching or fusing. A focused Qt behavior assertion will confirm that the
atom-anchor result is detached placement; true legacy attachment/fusion stays
deferred with the other chemistry-changing operations.

## Architecture boundaries and ownership

| Layer | Owns | Supplies at the boundary | Does not own |
| --- | --- | --- | --- |
| TemplateMode | Current system-template name, hit test, click scene point, atom-anchor detection, transient status/selection intent. | Immutable template name and finite anchor point through its named session action. | Revision capture, SMILES parsing, proposal XML, persistent models/items, local undo, durable allocation. |
| DocumentSession | State/capability gate, current-revision capture, exact request validation, OASA helper invocation, backend-history recording, canonical projection replacement. | A frozen `PersistentOperationRequest` and accepted/rejected outcome. | DOM patching, Qt template molecule construction, document reconstruction. |
| OASA preparation | System template lookup, SMILES parse, coordinate generation, centering/translation, proposal serialization. | A frozen detached molecule proposal and nonpersistent label/result metadata. | PySide6 values, scene items, frontend callbacks, projection lifetime. |
| OASA insertion session | Complete-document clone, proposal import, strict validation, durable IDs, atomic accepted snapshot. | Existing immutable `CDMLCommit` with canonical CDML and `id_map`. | Qt scene/model/undo state. |

### Plain preparation, request, and result behavior

Introduce one frontend-neutral OASA preparation value such as
`CDMLTemplatePlacementRequest` with exactly:

- `template_name: str` - an exact key in the current OASA system-template
  catalog;
- `anchor: tuple[float, float]` - finite CDML/PostScript scene-point
  coordinates; and
- `token_stem: str` - a request-local valid provisional-ID stem supplied by
  the session.

The helper returns a frozen `CDMLPreparedMoleculeInsertion` containing only
the complete detached `proposal_cdml` and optional nonpersistent diagnostic
metadata needed by the caller. It resolves `template_name` inside OASA, parses
the mapped SMILES, generates OASA coordinates, translates the generated
molecule centroid to `anchor`, and serializes it with
`cdml_writer.molecules_to_insertion_proposal()`. The proposal contains no Qt
objects and no reference to an anchor atom. A missing catalog name, invalid
SMILES, empty prepared molecule, invalid anchor, or serialization failure is
a typed OASA preparation failure and leaves the document unchanged.

`DocumentSession` exposes the Qt-facing operation key `template.insert` with
an exact immutable payload:

```text
expected_revision: int
template_name: str
anchor: tuple[float, float]
```

For an atom anchor, TemplateMode captures the synchronized projected coordinate
before submission. The canonical persistent request remains the three scalars
above, with empty `target_keys` for the inserted molecule-only transaction. The
session reads one snapshot, verifies that its revision equals
`expected_revision`, invokes the OASA preparation helper, builds the existing
`CDMLMoleculeInsertionRequest(expected_revision, proposal_cdml, label)`, and
uses the existing `molecule-insertion` executor exactly once.

On acceptance, the normal `CDMLCommit` is final: its canonical complete CDML,
revision, and provisional-to-durable `id_map` identify the inserted molecule
and its records. The session records backend history before projection. Qt
replaces its projection from that exact accepted snapshot and may select the
inserted molecule by durable ID. It never resubmits a proposal after
acceptance. A projection failure retains the final accepted snapshot and the
public retry path reprojects that exact snapshot only.

## Files likely involved

- `packages/oasa/oasa/cdml_document.py`: reuse existing insertion request and
  transaction; add a narrowly named plain template-placement preparation API
  only if its natural home is the CDML boundary.
- `packages/oasa/oasa/cdml_writer.py`: reuse or extend the detached
  molecule-to-proposal serializer without changing persistent-document
  ownership.
- A small OASA template-preparation module beside the existing chemistry/CDML
  helpers, if separating catalog resolution and SMILES preparation keeps
  `cdml_document.py` focused on session transactions.
- `packages/oasa/tests/test_cdml_template_placement.py`: backend-only
  preparation, position, proposal, insertion preservation, and typed-failure
  facts.
- `packages/bkchem-qt.app/bkchem_qt/models/document_session.py`: exact
  `template.insert` adapter and delegation to the existing insertion executor.
- `packages/bkchem-qt.app/bkchem_qt/modes/template_mode.py`: replace local
  `MoleculeModel`/graphics/undo placement with one session-owned submission.
- `packages/bkchem-qt.app/tests/test_user_template_catalog.py`: retain only the
  deterministic plain catalog contract.
- Whole-window placement and backend-history integration are one-time
  application evidence. Their implementation-era shared-window pytest modules
  were retired under the permanent-test and fixture policy.

## Implementation sequence

1. [x] Measure and lock OASA preparation semantics.
   - Choose representative stable system-template SMILES and compare the
     current Qt conversion at two finite scene anchors in a small deterministic
     test or probe. Capture the existing 40-point average-bond-length scaling
     performed by `oasa_mol_to_qt_mol()` before centroid translation.
   - Establish finite anchor and centroid facts from canonical CDML, then move
     the resulting scale and anchor rule into the OASA helper. Preserve
     user-visible template-scale semantics rather than demanding pixel
     equivalence.
   - Assert the proposal is a complete detached CDML document with provisional
     IDs and no source-document nodes.

2. [x] Implement and validate the OASA preparation boundary.
   - Add frozen plain request/result values and a narrow OASA function that
     owns catalog lookup, SMILES conversion, coordinate generation, placement,
     and proposal serialization.
   - Reuse `CDMLDocumentSession.insert_molecules()` for acceptance rather than
     duplicating validation, namespace preservation, durable allocation, or
     revision logic.
   - Prove unknown/presentation content and root order survive acceptance,
     while malformed inputs and stale insertion requests are atomic.

3. [x] Bind `template.insert` to the existing session insertion route.
   - Require the exact three plain payload fields, a current expected revision,
     finite anchor, known name, and no persistent mutation target keys.
   - Prepare once through OASA, pass the immutable proposal to the existing
     `CDMLMoleculeInsertionRequest`, record accepted backend history, and
     install only the returned canonical snapshot.
   - Return current typed unavailable/rejected/accepted outcomes and preserve
     the existing no-resubmission rule after acceptance.

4. [x] Migrate TemplateMode's completed detached gestures.
   - Retain the existing template selection and hit-test UI.
   - Replace attach/fuse wording in the TemplateMode status hint and relevant
     docstrings with precise detached-placement language before the route is
     delivered.
   - On blank click, capture the scene point; on atom click, capture that
     atom's projected coordinate and durable source identity. Submit one
     `template.insert` request instead of constructing a `MoleculeModel`,
     graphics items, or `AddMoleculeCommand`.
   - On acceptance, restore selection only from durable IDs in the canonical
     result/projection. On rejection, retain the current projection and report
     the operation outcome.

5. [x] Validate lifecycle behavior and review the boundary.
   - Use a narrowly injected one-time projection-install failure after a real
     accepted operation. Assert that backend canonical CDML and revision remain
     accepted/final, then use the public `retry_current_backend_projection()`
     path to restore the projection without another backend call.
   - Have an independent OASA review inspect preparation ownership and
     insertion reuse, and an independent PySide6 review inspect no local
     persistent template mutation, durable identity capture, and disposal-safe
     recovery.

6. [x] Update durable documentation only after code and independent review pass.
   - Then update the CDML and Qt contracts, the active migration plan, and
     `docs/CHANGELOG.md` to describe only the accepted detached placement
     behavior. This planning document makes no completion claim before that
     evidence exists.

## Verification

Run the permanent backend and plain catalog checks after related changes.
Whole-window placement, history, and recovery remain one-time application
evidence rather than shared-window pytest fixtures:

```bash
source source_me.sh && python3 -m pytest -q \
  packages/oasa/tests/test_cdml_template_placement.py \
  packages/bkchem-qt.app/tests/test_user_template_catalog.py

git diff --check
```

Tests follow [PYTEST_STYLE.md](../../PYTEST_STYLE.md): each asserts one
observable contract fact, uses no network, avoids fixture or storage-shape
assertions, and proves canonical CDML/state behavior rather than item counts
or wrapper identity. The atom-anchor test compares the source molecule and
atom canonical facts before and after insertion, while proving one separate
inserted molecule appears at the anchor. The implementation-time retry probe
observed the accepted snapshot and rebuilt projection rather than coordinator
internals; it was retired instead of being kept as permanent lifecycle wiring.
The preparation test compares finite scale/anchor behavior against the
measured current Qt rule without a pixel-equivalence gate. The managed
application walkthrough checks that delivered atom-anchor behavior remains
detached placement and that user-facing wording and persistent behavior stay
aligned.

## Acceptance record

The detached system-template placement slice is accepted as a bounded M5
implementation record. The backend resolves an exact system-template name,
prepares detached CDML geometry at the requested finite anchor, commits once,
and returns canonical complete CDML with durable-ID correlation. TemplateMode
submits one plain intent and owns only interaction and projection state. Its
blank and atom-click gestures create a separate root molecule; atom anchoring
does not attach or fuse chemistry.

The pure-model two-anchor comparison established the 40-point mean-bond scale
and centroid-to-anchor rule without a pixel-equivalence requirement. Accepted
root provisional IDs map to durable IDs for post-reprojection selection. The
public retry proof retains that accepted snapshot and its mapped selection
intent while making OASA preparation fail if retry attempts to replay the
accepted placement.

Pointed evidence covers OASA placement, low-level session validation and stale
rejection, public offscreen TemplateMode authority/undo, cross-tab origin
binding, disposal-safe retained actions, scale parity, and focused lint,
Markdown, import-boundary, and whitespace checks. The acceptance tests use
public session/mode/projection behavior rather than private callback, executor,
or projection-installer details. This does not claim resolution of unrelated
native Qt crash reports or completion of M5. Attachment/fusion, template
markers, BioTemplate, and user catalogs remain deferred below.

## Success conditions

- [x] A blank click and an atom click each produce one accepted backend revision
  containing a newly inserted separate template molecule.
- [x] The template molecule is positioned at the intended finite CDML scene-point
  anchor using OASA-owned SMILES preparation and measured placement-scale
  semantics equivalent to current user-visible Qt behavior.
- [x] An atom-anchor insertion leaves the clicked atom, its molecule, their bonds,
  and all unrelated persistent content canonically unchanged.
- [x] The inserted template's durable records originate in the OASA proposal and
  are available after canonical reprojection; Qt retains no parallel document
  representation or local persistent undo command for the gesture.
- [x] Rejection, malformed plain input, unknown template, preparation failure,
  stale revision, and projection failure satisfy the existing atomicity and
  accepted-finality rules.
- [x] Backend undo/redo navigates the accepted insertion revision, and a discarded
  Qt projection can be rebuilt from the authoritative current snapshot.
- [x] Focused backend and offscreen Qt tests pass without native Qt lifecycle
  failures; contracts and changelog change only after independent acceptance.
- [x] TemplateMode's visible hint and relevant docstrings accurately say that an
  atom click places a detached molecule at the atom anchor, and a focused
  behavior test confirms that result.

## Risk register

| Risk | Trigger | Mitigation and evidence |
| --- | --- | --- |
| Qt remains the hidden persistent owner | TemplateMode builds models/items or pushes `AddMoleculeCommand` before acceptance. | Replace that branch with one immutable session submission; test canonical backend change precedes fresh projection. |
| Placement drifts from current Qt behavior | OASA and Qt use different coordinate conversion, 40-point average-bond-length scale, or centering rules. | Deterministic representative-template comparison records finite scale and anchor facts, then establishes one OASA rule without a pixel-equivalence gate. |
| UI promises attachment that does not occur | A hint or docstring calls detached atom anchoring "attach" or "fuse." | Update wording with the migration and assert the atom-anchor result remains one detached inserted molecule; defer real attachment semantics. |
| Atom click accidentally fuses chemistry | New insertion changes the source atom/molecule or creates a joining bond. | Source-preservation fingerprint plus separate-root molecule assertion. |
| Preparation bypasses the transaction | A helper edits a live document or allocates durable IDs. | Keep preparation detached and reuse `insert_molecules()` for every accepted change. |
| Stale or rejected intent changes document state | The helper consumes tokens or a session retries against a newer snapshot. | Existing revision check, rejected-state comparison, and one-shot accepted-call test. |
| Projection failure is mistaken for rollback | Qt constructs a replacement locally or replays the request. | Assert final backend snapshot; recover only with the public current-snapshot retry. |
| Attachment scope leaks in | Legacy valency, bond, marker, or template-manager behavior becomes coupled to detached placement. | Keep the exact current Qt gesture contract; create a separate evidence-led plan before attachment implementation. |

## Deferred decisions

- Attachment/fusion semantics, bond anchoring, template-marker persistence,
  valency handling, and cross-molecule merging require a distinct backend
  operation and independent behavioral comparison.
- BioTemplate and user-template catalog sources require their own catalog and
  persistence decisions after this system-template route is accepted.
- The final public location/name of the OASA preparation helper follows the
  small preparation experiment and code review; its behavior and plain-data
  boundary are fixed by this plan.
