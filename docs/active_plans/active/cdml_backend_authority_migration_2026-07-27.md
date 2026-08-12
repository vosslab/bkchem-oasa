# Plan: CDML backend authority migration

## Current post-M6 ledger (2026-08-11)

This ledger is the current execution record. Earlier milestone prose below is
historical design and rollout evidence; where it differs from this ledger, this
ledger controls the active claim.

| Priority | Current outcome | Next durable decision |
| --- | --- | --- |
| P0 authority | OASA owns complete CDML, root-only insertion facts, revisions, history, immutable projection plans, and normalized effective presentation appearance. Synchronized Qt neither parses canonical CDML nor recreates drawing defaults. | Keep new persistent appearance behavior in OASA facts and consume only scalars in Qt. |
| P1 Qt usability | Release-selected classic behavior/action routes are complete: typed Arrow/Vector creation, direct Text editing, delivered Configure routes including bracket pairs, responsive 640/1024/1280 controls, and durable pair interaction use backend commits and replacement projections. | Keep literal Tk parity, template atom fusion, and a three-ring Qt adapter outside this release scope. |
| P2 Haworth and render | Direct two-ring Haworth remains the only Qt authoring profile. An explicit-declaration three-ring OASA API exists; all seven active Haworth layout overrides now converge on generic geometry. | Do not claim a three-ring Qt adapter or universal carbohydrate inference. Keep future render changes on shared geometry. |
| P3 retained Tk | Tk is deprecated retained reference software, not default packaging. Compatibility tests pass and it preserves complete marked bracket pairs without proximity inference; native launch is unproven on this host because plain Tk aborts first. | Make bounded regression/contract fixes only; re-probe on a functioning Tk host rather than rebuilding the product boundary around Tk. |
| P4 delivery | Source/pip, atomic screenshots, isolated-wheel round trips, glyph measurement, the complete four-root aggregate, and the independent audit pass. | Re-run the classified release receipts after material delivery changes. |

### Verification classification

- Permanent tests: backend transaction/authority laws, immutable-plan values,
  deterministic Qt adapters, retained-Tk compatibility, and semantic
  Haworth/render behavior.
- One-time release checks: complete four-root pytest aggregate, live screenshot gallery
  capture and visual inspection, retained-Tk manual smoke, isolated-wheel
  install/launch, glyph measurement, and independent multi-review audit.
- This plan intentionally avoids arbitrary count, timing, pixel, or private
  implementation gates. Each permanent test proves a stable user-visible or
  boundary behavior.

## Context

The migration began with OASA providing molecule-level CDML support while the
PySide6 frontend parsed, stored, merged, and serialized the complete document
envelope. That made Qt the actual persistent document owner even though the
frontend/backend boundary was described as CDML-only. OASA now implements the
complete-document authority. Release-selected persistent Qt action families
use that boundary, and Qt projection serialization stays out of
complete-document publication routes.

The settled architecture is stricter: OASA owns the authoritative complete
persistent CDML document. Qt owns only transient interaction state and
replaceable projections. If a molecule-only backend rewrite drops an arrow and
Qt restores that arrow afterward, Qt remains the hidden document owner.

The central persistence invariant is:

> A backend CDML round-trip must preserve every persistent object without Qt
> re-merging omitted content.

This plan supersedes the persistent-ownership work packages in the historical
[BKChem Qt completion plan](BKCHEM_QT_COMPLETION_PLAN_2026-07-27.md). Its
session-lifetime, rendering, chemistry, and packaging observations remain
historical evidence only; every persistent mutation must migrate through the
backend transaction boundary.

## Objectives

- Add an OASA complete-document CDML authority that preserves typed and opaque
  persistent content, order, IDs, references, namespaces, and unknown XML.
- Make complete-document CDML submission and canonical response the first
  persistent mutation protocol.
- Make Qt sessions project backend snapshots rather than own persistent
  document content.
- Prove the architecture first with an arrow vertical slice, then migrate every
  persistent action family.
- Move undo, redo, dirty state, Open, and Save onto backend revisions and
  snapshots.
- Remove Qt-side full-document authority and raw-XML re-merge after migration.

## Integration status (2026-08-03)

The dated M0--M6 notes below remain implementation history. The post-M6 ledger
above replaces their release status and separates enduring behavior tests from
one-time delivery evidence. The delivered Qt Haworth route remains the narrow
two-ring direct-oxygen drawing profile, not a general carbohydrate claim.

## Atom Align M0 implementation note (2026-07-30)

The existing BondAlign horizontal and vertical controls now have one narrow
backend-authoritative route. Qt submits a revision-bound immutable set of
durable `(molecule_id, atom_id)` targets and an exact `horizontal` or `vertical`
axis; OASA calculates the selected-set mean from authoritative direct core
points, treats equal parsed selected-axis coordinates as a no-op before DOM
mutation (preserving their compatible lexical spellings), and changes only the
corresponding direct point attribute otherwise. Changed coordinates retain the
established three-decimal-centimetre output form. Accepted changes use backend
history and canonical reprojection, including durable atom selection recovery;
Qt undo owns no part of this mutation. One target and canonical equality are
accepted no-ops. Unknown, stale, nested, opaque, malformed, duplicate, or
ID-less targets reject without a partial commit. Atom-local extensions remain
preserved because this operation validates only the targeted direct core atom
and point rather than applying a generic molecule rewrite. Mirror, inversion,
free rotation, object alignment, scale, and coordinate generation remain out
of scope; the corresponding unimplemented transform controls are absent from
the delivered Qt mode rather than being silently remapped. This M0 is accepted:
independent backend-authority, Qt-lifecycle, and test-quality reviews confirm
the bounded route and its focused acceptance proof.

## EditMode atom nudge M0 implementation note (2026-07-30)

Arrow-key nudging of selected atoms now uses the narrow `atom.translate`
operation. Qt sends only durable direct-root molecule/direct-core atom pairs and
the existing fixed 2.0-point delta through its session adapter; OASA validates
the complete immutable request against one authoritative snapshot and patches
only requested nonzero direct point coordinate axes using the established
points-to-centimetres conversion. A zero delta is lexical-preserving no-op. Accepted results own
backend history, dirty state, exact reprojection, and durable selection
restoration, with no Qt nudge undo command. Selected presentation items remain
ignored, while an ID-less atom or unavailable synchronized route makes the full
gesture inert. Atom-only mouse dragging, including its transient snapping and
axis-lock preview, is covered by the bounded slice below. Presentation-only
motion has its own completed bounded slice. Mixed atom/presentation dragging
now has its own one-operation authority route below; general transforms,
partial structural Delete, and bond property editing remain separate behavior.

## EditMode atom drag M0 implementation note (2026-07-30)

An atom-only EditMode mouse drag now shares the established revision-bound
`atom.translate` operation with arrow-key nudging. Qt retains responsive grid
snapping and axis-lock preview only until release, then captures durable
targets and one common final delta, restores the preview, releases its old
wrappers, and submits exactly once through the originating session. The
session reports backend, intentionally legacy-local, or temporarily
unavailable authority explicitly; an installed callback alone is not treated
as proof of backend authority. Backend acceptance owns revision history,
canonical reprojection, dirty state, and durable selection recovery. Missing
IDs, unequal deltas, rejection, stale state, and unavailable synchronized
projections leave the backend and Qt undo stack unchanged. Mixed atom/artwork
drags remain the established local macro; presentation-only movement is
completed in the bounded slice below.

## EditMode presentation drag M0 implementation note (2026-07-30)

A presentation-only EditMode mouse drag now completes through the
revision-bound `top-level.transform.apply` operation with mode `translate`.
At press, Qt freezes the originating session-owned callback and exact revision;
while the pointer moves, Qt owns only the transient grid-snapped and axis-locked
preview. On release, the mode verifies every selected wrapper belongs to the
current projection and names one supported durable direct-root presentation
object, derives one common final point delta, restores its preview, discards
its wrappers, and submits exactly once. OASA validates and translates the
authoritative CDML geometry, preserving opaque content. Accepted movement owns
backend history, dirty state, canonical reprojection, and durable selection
recovery, without a Qt move command. ID-less, foreign, unsupported, reshaped,
unequal-delta, unavailable, rejected, and stale gestures are inert after
preview restoration. Explicitly legacy-isolated documents retain their
existing local presentation move command.

## EditMode mixed drag M0 implementation note (2026-07-30)

Mixed selections of direct-core atoms and supported direct-root presentation
records now submit one revision-bound `selection.translate` request. Qt captures
the originating session callback and revision at press, displays a temporary
shared drag preview, and resolves the exact current selection again at release
in document source order. It restores the preview and drops the old wrappers
before one submission. OASA owns the atomic coordinate update, history, and
canonical snapshot; Qt restores selection only from durable IDs after
reprojection. Foreign, retired, ID-less, unsupported, reshaped, unequal-delta,
unavailable, stale, and rejected synchronized gestures are inert. A failed
accepted projection retries the exact current snapshot without resubmission.
Legacy-isolated and standalone canvases retain one local mixed move macro.

## Atom-only 2D Rotate M0 implementation note (2026-07-30)

Rotate now submits one revision-bound `atom.rotate` request after a transient
atom-only preview. The backend validates durable direct-root molecule/atom
targets, a finite scene-point center, and a finite radians value against its
current snapshot, then rotates only direct point `x`/`y` values in a detached
candidate while preserving z, opaque XML, and document order. Qt unwraps
incremental pointer angles across the branch cut, restores preview coordinates
before submission, and receives accepted state only through backend history and
canonical reprojection. The delivered mode exposes 2D only; mixed presentation
selection and general transforms remain separate capabilities.

## Exact bond-order M0 implementation note (2026-07-30)

The context-menu Set Bond Order action now submits one revision-bound
`bond.order.set` request with direct durable molecule/bond IDs and order 1, 2,
or 3. OASA verifies the direct-core bond and its endpoints, retains the
existing supported type character, and patches only the order digit, including
styled bonds such as `w2`. Haworth `q` remains `q1`. Matching semantic orders
are lexical-preserving no-ops; ambiguous legacy or malformed spellings,
independent order attributes, invalid targets, and stale revisions fail
atomically. Qt records only accepted backend history and restores the selected
bond from the fresh canonical projection; local bond property undo remains
outside this bounded route.

## Exact bond-type M0 implementation note (2026-07-30)

The context-menu Set Bond Type action now submits one revision-bound
`bond.type.set` request with direct durable molecule/bond IDs and an ordinary
type scalar. OASA preserves the order digit and all unrelated CDML while
changing only the exact type character. Current `q1` may convert to an ordinary
type; compatibility `l1`/`r1` are semantically hashed and therefore preserve
their lexical spelling for a request of `h`. Invalid requested values, malformed
current spellings, independent order attributes, invalid targets/endpoints, and
stale revisions fail atomically. Qt uses backend history, canonical reprojection,
and durable selection recovery without local undo; a failed accepted projection
retries only the accepted snapshot.

## Atomic bond-properties M0 implementation note (2026-07-30)

Bond Properties now submits one revision-bound `bond.properties.patch` with a
unique immutable set of explicitly changed fields. OASA validates the direct
molecule, bond, endpoints, independent-order ambiguity, every field grammar,
and the final combined type/order before it creates a candidate. A changed
multi-field patch creates exactly one revision and preserves all unmentioned
bond data plus opaque document content; canonical no-ops are history-free.
The detached dialog, context Properties, Object Configure, EditMode, and dock
order/type controls use a capability captured for their owning view/session, so
tab changes cannot redirect an accepted intent. Synchronized calls create no Qt
property undo. Accepted projections restore the direct durable bond selection;
if replacement fails, retry reprojects the exact accepted snapshot without a
second backend submission.

## Bond semantics reconciliation note (2026-07-30)

CDML 26.07 retains the legacy-compatible meanings `n` normal, `w` directed
solid wedge, `h` directed hashed wedge, `a` adder, `b` bold, `d` dashed, `o`
dotted, `s` wavy, and `q1` Haworth front edge. OASA now publishes those plain
frontend-neutral semantics and authorable-order rules while retaining `l`/`r`
as read-only compatibility aliases for `h`. Qt owns a separate presentation
choice source consumed by Draw, ribbon, property, dialog, and context-menu
surfaces; generic authoring excludes `q`, but existing Haworth records display
accurately. Exact backend-authoritative Set Type and missing `a`/`d`/`o` render
geometry remain explicit next slices rather than being hidden behind local UI
changes.

## Atomic atom-properties M0 implementation note (2026-07-30)

Atom Properties now has one revision-bound `atom.properties.patch` operation
for explicit chemistry and presentation fields. The backend validates all
plain field intent before detached candidate mutation, preserves non-target
CDML, and creates or updates only the direct core font when font intent is
present. Context Properties, Object Configure, EditMode, and PropertyDock
Symbol, Charge, and Show Label controls bind their intent to the owning
session before it submits; accepted edits use backend history and fresh durable
selection rather than Qt property undo.

## Plain Text Configure M0 implementation note (2026-08-02)

One durable direct-root plain Text now uses the revision-bound
`text.properties.patch` transaction. OASA validates the complete scalar intent,
direct-root target, direct point/font/ftext grammar, and rich-text exclusion
before detached mutation; accepted changes preserve opaque CDML and use backend
history, while semantic no-ops are history-free. Object Configure captures the
originating synchronized session, revision, Text ID, and exact capability
before TextDialog opens. Accepted state canonically reprojects and restores the
durable Text selection; disposal is typed unavailable and projection recovery
reuses only the accepted snapshot. This M0 covers plain content, family, size,
color, and optional background. This checkpoint predates completed plain Wavy
width/color Configure slice; Rich Text editing and broader Plus work remain
separate.

## Rich Text root-font M1 implementation note (2026-08-03)

Rich Text now carries complete immutable authored runs plus unique explicit
root-font changes for family, size, and color through `text.rich.patch`.
OASA validates the entire request before detached mutation, preserves absent
font attributes unless named, creates a namespaced core font immediately before
`ftext` only when needed, and keeps canonical no-ops history-free. The separate
modal editor captures its originating session, revision, Text ID, runs, and
visible root values before opening. Its run formats carry only authored styles,
so refreshed root family, size, and color inherit through the document default.
Plain Configure remains plain-only and directs selected authored Text to Edit
Rich Text. Inline fonts and root weight/style remain out of scope.

## Plain Wavy Configure M0 implementation note (2026-08-02)

One durable direct-root `<polyline style="wavy">` now uses the revision-bound
`wavy.properties.patch` transaction. OASA validates exact direct-root Wavy
identity, unambiguous direct core points, width and color intent, and existing
visible root values before detached mutation. Width and color semantic no-ops
remain history-free; accepted writes preserve geometry, spline, opaque content,
legacy color, and source order. Object Configure copies plain width/color,
captures the originating synchronized session, revision, Wavy ID, and exact
capability before WavyDialog opens, then submits once after wrappers leave
scope. Accepted state canonically reprojects, restores durable Wavy selection,
and uses accepted-snapshot-only projection retry. Geometry editing, spline
normalization, amplitude/wavelength, and Wavy inference remain out of scope.

## Atom-mark backend M0 implementation note (2026-07-30)

OASA now supplies the bounded `atom.mark.apply` operation for plus, minus,
radical, biradical, electronpair, dotted electronpair, and pz orbital. The
request carries only immutable revision, direct-root molecule and atom IDs,
exact add/remove intent, and exact mark type. OASA derives new mark geometry
from the authoritative direct atom point, appends an ID-less mark as the final
direct atom child, and atomically applies the declared charge or multiplicity
delta where applicable. Removal uses the first direct matching mark in
persistent child order; no match is a successful history-free no-op. The
operation preserves later duplicates, legacy residual state outside its own
delta, and all unrelated opaque CDML. Plus/minus validate only charge; radical
and biradical validate only multiplicity. The unaddressed scalar, including
legacy or incompatible text, remains verbatim; presentation-only marks retain
both scalars. The backend contract is complete; the
Qt MarkMode now consumes this contract through the session dispatcher.  Its
YAML type/action choices produce one revision-bound plain request; changed
results use backend history and canonical reprojection, while no-match removal
preserves the current projection and history.  The durable parent atom is the
only post-reprojection selection key; marks remain ID-less. Focused lifecycle
and selection coverage complete the bounded frontend slice.

Selected-mark Delete extends that boundary without inventing mark IDs: CDML
projection records each supported mark's zero-based same-type direct core-child
ordinal, and exactly one current bound MarkItem submits it with durable parent
IDs. Invalid, foreign, retired, mixed, ID-less, or ordinal-less synchronized
selections are inert. Accepted deletion has only backend history and canonical
reprojection; stale and validation outcomes are final, and recovery retries
only the accepted snapshot.

## Top-level transform backend M0 implementation note (2026-07-30)

OASA now provides the bounded `top-level.transform.apply` operation for
durable direct-root mixed-object alignment, scaling, horizontal or vertical
mirroring, and direct-root translation. Its plain frozen request carries only
revision, exact mode, selected root IDs, and the mode's documented scalar
intent: scale factors for scale or a finite point delta for translate. The
backend derives bounds, pivots, and
all affine coordinates from persistent CDML, validates every selected root
before detached mutation, preserves full-document content, and commits one
accepted revision only when canonical content changes. The Qt session adapter,
canonical durable selection bridge, and the nine visible Align/Object menu
routes are complete. Their router captures only immutable roots, revision, and
an exact registered-session capability; Scale validates that same capability
after modal acceptance. Canonical reprojection, backend history, typed stale
outcomes, and snapshot-only recovery own synchronized changes. The explicit
legacy-isolated state retains the prior local undo route for its local edits.

## Design philosophy

This is a clean ownership redesign under **Fix the design, not the symptom** and
**Long-term over short-term**. The plan rejects preserving the current split by
adding more Qt-side merge rules. Complete-document commits are intentionally
simpler than a second operation protocol: performance optimization follows
only after the authoritative boundary works.

Cleanup work does not authorize a further architecture redesign or scope
expansion. Preserve existing backend/frontend-agnostic contracts where they
exist or can remain without expanding the work. OASA/backend-facing APIs, data
models, serialization, and tests use plain immutable Python data, complete
CDML, and explicit request/response behavior; they do not acquire Qt,
`QObject`, graphics, or frontend-lifetime assumptions. Qt types stay in
frontend projections and adapters.

- Evidence strategy for uncertain methods: use backend-only semantic
  round-trips and one arrow end-to-end slice. Representation details may change
  when those tests expose a preservation or lifecycle defect; document
  authority itself is settled.

## Scope

- Implement a DOM-backed OASA `CDMLDocument` and revisioned
  `CDMLDocumentSession`.
- Preserve all persistent CDML nodes typed or opaque.
- Validate known IDs and references transactionally.
- Add complete-document load, snapshot, commit, and restore APIs.
- Add a Qt backend-session adapter and projection replacement lifecycle.
- Route Open, Save, arrow creation, and backend revision undo through the new
  boundary first.
- Classify each visible Qt capability family before M5 as a bounded required
  slice, an already-supported family needing the common commit route, or a
  deliberately unsupported/disabled capability removed from release claims.
- Migrate only the required and already-supported chemistry, fragment,
  template, numbering, import, PubChem, Haworth, and repair persistence
  families through the common backend route.
- Retire Qt full-document serialization and persistent raw-envelope ownership.
- Correct contracts, active plans, parity reports, changelog claims, and
  packaging evidence.
- Deliver Qt as the release-selected BKChem frontend. Retain deprecated Tk as
  legacy source and behavioral/fixture evidence, not the current packaging
  target, a release-parity requirement, or an architecture constraint.

## Non-goals

- Introduce a fragment or command RPC protocol in the first implementation;
  complete CDML is the protocol.
- Require chemical semantics for every presentation or vendor node; opaque
  backend ownership is valid.
- Promise byte-identical XML formatting; semantic order, namespaces, opaque
  subtrees, IDs, references, and values must survive.
- Remove or newly package the deprecated Tk frontend. Its code and CDML
  fixtures remain available for legacy behavior, migration evidence, and
  bounded contract or regression fixes.
- Deliver a browser, WASM backend, TypeScript, or SolidJS frontend. The
  frontend-neutral backend contract is sufficient for a future frontend
  without adding one to this migration.
- Redesign the Qt interface, tools, or visual style beyond changes required by
  projection replacement.
- Require open-ended legacy feature parity. Tk observations are decision
  evidence only; browser, WASM, TypeScript, SolidJS, and Tk delivery remain
  outside this migration.
- Make byte-, pixel-, or lexical-identity comparisons authority prerequisites.
- Publish a release before the backend-authority integration gate closes.

## Current state summary

| Area | Current behavior | Migration classification |
| --- | --- | --- |
| OASA CDML | Owns complete canonical CDML, typed/opaque records, validation, revisions, IDs, and history | Accepted backend authority |
| Qt CDML codec | Builds projections and explicit compatibility candidates; ordinary Save and Save As publish only backend snapshots | Projection/candidate code only |
| Qt `Document` | Replaceable projection cache; legacy-isolated compatibility state is not a release persistence route | No persistent authority in the release-selected set |
| Qt models/items | Disposable chemistry and presentation projections | Reuse without persistent authority |
| `DocumentSession` | Owns the private backend session plus tab/view/scene/workers and safe projection replacement | Accepted session/projection infrastructure |
| Qt undo commands | Qt actions adapt synchronized Undo/Redo to backend revision navigation; graphics commands remain legacy-isolated compatibility only | Backend history owns release-selected persistence |
| Full-document tests | Prove backend preservation plus Qt projection/save/reopen behavior | Accepted authority coverage |
| Package/version work | Qt-only package metadata, clean installation, and installed round-trip are accepted | Await only external frozen-release gates |

## Architecture boundaries and ownership

### Backend

`oasa.cdml_document.CDMLDocument` owns one complete parsed CDML tree and its
indexes. Typed chemistry is a projection of molecule elements; it is not the
source used to reconstruct the rest of the document. Unknown nodes remain
ordered opaque subtrees.

`oasa.cdml_document.CDMLDocumentSession` owns:

- current accepted `CDMLDocument`;
- monotonically increasing revision;
- bounded accepted revision history;
- atomic complete-document validation and commit;
- snapshot and restore.

The first public shape is:

```python
session = CDMLDocumentSession.load(cdml_text)
snapshot = session.snapshot()
commit = session.commit(
	expected_revision=snapshot.revision,
	complete_cdml=candidate_cdml,
)
restored = session.restore(
	target_revision=snapshot.revision,
	expected_revision=commit.revision,
)
```

Malformed XML, duplicate IDs, or unresolved known references reject without
changing the current document or revision. Unknown content never causes
rejection merely because it is unknown.

Accepted snapshots are immutable. Commit and restore both create a new,
monotonically increasing revision. Restore copies target content; it does not
move the counter backward. Before a restore, the backend protects its immediate
pre-restore revision for redo; each restore replaces that protection. A normal
accepted edit clears the redo protection and Qt redo navigation. History
capacity is at least three. It protects the current, exact saved, and immediate
pre-restore revisions when distinct, while older nonprotected history may
evict. New and native-CDML sessions begin clean. A non-CDML import begins from
a clean blank session, then commits converted complete CDML and is dirty and
pathless. Only after a successful filesystem write does Qt call
`mark_saved(expected_revision)`, which retains canonical saved content. Clean/
dirty compares canonical snapshot content with that saved content, so restoring
saved content becomes clean even at a new revision.

Candidates may use `__bkchem_new__<token>` only as a transaction-local
provisional correlation token in recognized editable node ID declarations and
known references. `<token>` matches `[A-Za-z][A-Za-z0-9_-]{0,63}`. Each valid
token is unique among recognized ID declarations; it may repeat in any number
of known reference positions. During strict atomic commit, OASA validates only
recognized token positions, allocates durable collision-free IDs, rewrites only
those declarations and references, and rejects dangling or invalid tokens.
The stored-snapshot and canonical-response prohibition applies only to those
recognized positions. Matching strings in opaque XML, unknown attributes,
elements, or text survive unchanged and are not provisional tokens.

### Frontend

`DocumentSession` owns the backend session handle/revision and the current Qt
projection. `Document`, `MoleculeModel`, `PresentationObject`, `PaperModel`,
`GroupModel`, and graphics items are replaceable projections/caches.

Qt may:

- preserve selection by stable backend-owned IDs across reprojection;
- own gesture previews until commit;
- build a complete candidate by cloning the backend snapshot and changing the
  targeted CDML node;
- display validation failures without changing the accepted projection.

Qt may not:

- save a document reconstructed from its projection;
- restore content omitted by a backend response;
- allocate or repair persistent IDs outside an explicit backend operation;
- treat retained raw XML as its own persistence store.

### Mapping (milestones / workstreams -> components / patches)

| Milestone / Workstream | Component | Review boundary |
| --- | --- | --- |
| M0 / WS-A | Contracts, decision record, first red authority test | Settled ownership and invariant |
| M1 / WS-B | `oasa/cdml_document.py`, backend tests | Complete-document preservation and validation |
| M2 / WS-C | Qt backend adapter and projection replacement | Session/revision/lifecycle boundary |
| M3 / WS-D | Arrow candidate commit and backend undo | First complete vertical slice |
| M4 / WS-E | Frozen operation seam and bounded presentation hypotheses | Evidence-led nonchemical slices only |
| M5 / WS-F | Bounded chemistry/actions/history migration | Required Qt capability slices use backend revisions. |
| M6 / WS-G | Authority retirement, Qt-only delivery, packaging, docs | Integrated release boundary |

## Milestone plan

| M | Title | Summary | Goal |
| --- | --- | --- | --- |
| M0 | Lock the contract | Correct docs and add the backend-only red test. | No implementation can claim Qt document authority. |
| M1 | Backend document core | Own, preserve, validate, commit, and restore complete CDML. | A backend-only round-trip loses nothing persistent. |
| M2 | Qt projection session | Load backend snapshots and safely replace Qt projections. | Qt becomes replaceable view state. |
| M3 | Arrow proof | Commit an arrow through complete CDML and backend revisions. | Prove Model B end to end on a nonchemical object. |
| M4 | Bounded presentation hypotheses | Freeze the generic seam and test the release-selected presentation, paper, and stacking routes. | Complete for the selected release set; excluded historical variants are not delivery claims. |
| M5 | Chemistry and history | Migrate the selected molecule, worker, and undo/redo slices. | Every declared release-selected persistent edit is a backend revision. |
| M6 | Retire the old authority | Retire Qt persistence authority and close evidence gates. | Source/install/boundary/audit gates pass; screenshot tracking and native launch receipt remain. |

### Milestone M0: Lock the contract

- Depends on: none -- ownership is already decided.
- Deliverables: decision record, corrected contracts, supersession notice,
  human guidance, and first backend authority test.
- Workstreams: WS-A.
- Entry criteria: settled Model B decision.
- Exit criteria:
  - No active contract says Qt serializes or owns the persistent envelope.
  - The first OASA-only complete-document test fails only because the backend
    API is not implemented.
  - `docs/CHANGELOG.md` records the architecture correction without claiming
    implementation completion.
- Parallel-plan ready: no -- max parallel doers: 1; contract wording and the
  first test establish one shared vocabulary.

### Milestone M1: Backend document core

- Depends on: WP-A1 -- the invariant and API vocabulary must be fixed.
- Deliverables: `CDMLDocument`, `CDMLDocumentSession`, typed/opaque records,
  ID/reference indexes, atomic commit, snapshots, restore, and backend tests.
- Workstreams: WS-B1 and WS-B2.
- Entry criteria: M0 test and decision record exist.
- Exit criteria:
  - Backend-only round-trip preserves the complete persistent fingerprint.
  - Invalid commits preserve the prior revision and CDML.
  - Serialization performs no implicit ID allocation, reordering, or
    molecule-only rewrite.
  - Independent review confirms arrows and unknown XML survive without Qt.
- Parallel-plan ready: serial API gate -- WP-B2 starts only after WP-B1 locks
  the record and document API. Validation/revision tests may be prepared, but
  no dependency-conflicting implementation proceeds concurrently.

### Milestone M2: Qt projection session

- Depends on: WP-B1 and WP-B2 -- Qt needs a stable backend API.
- Deliverables: backend adapter in `DocumentSession`, native Open/Save routing,
  candidate submission from an exact backend snapshot, safe projection
  replacement, and selection restoration by persistent ID.
- Workstreams: WS-C1 and WS-C2.
- Entry criteria: M1 integration gate passes.
- Status: accepted for backend-synchronized sessions. C1a/C1b/C1c and C2
  establish private backend sessions, backend-first native Open, guarded
  backend-snapshot Save, atomic projection replacement, and stable-ID selection
  restoration. Unmigrated Qt edits remain on the explicitly isolated legacy
  route; moving those action families is M3 through M5 work.
- Exit criteria:
  - Native Open loads backend first and projects its returned CDML.
  - Provenance-eligible Save writes the current backend canonical snapshot
    unchanged by Qt.
  - Reprojection disposes old Qt callbacks/items without a native crash.
  - A stale backend response cannot replace a newer or closed session.
- Parallel-plan ready: serial API gate -- WP-C2 starts only after WP-C1 locks
  the session adapter API. Lifecycle-test preparation may proceed, but no
  dependency-conflicting implementation proceeds concurrently.

### Milestone M3: Arrow proof

- Depends on: WP-C1 and WP-C2 -- the arrow needs commits and reprojection.
- Deliverables: transient arrow preview, CDML candidate mutation, atomic
  backend commit, canonical reprojection, backend revision undo/redo, and
  arrow save/reopen.
- Workstreams: WS-D.
- Entry criteria: M2 session gate passes.
- Status: accepted for the normal Arrow Mode vertical slice. The slice commits
  complete CDML, receives backend durable IDs, uses backend revision navigation,
  and saves/reopens canonical opaque-preserving CDML. It is the first accepted
  action, not completion of the presentation, chemistry, worker, or
  multi-action migration.
- Exit criteria:
  - Adding an arrow changes only transient Qt state before acceptance.
  - The backend response contains molecule, arrow, text, and unknown content.
  - Qt creates a new arrow projection from the response and performs no
    persistent re-merge.
  - Undo/redo restores backend revisions and reprojects without retaining old
    graphics wrappers.
- Parallel-plan ready: no -- max parallel doers: 1; this is the first
  end-to-end ownership proof across shared session and arrow files.

### Milestone M4: Bounded presentation hypotheses

- Depends on: WP-D1 -- the arrow proves the common transaction path.
- Status: complete for the release-selected presentation set. M4-0 supplies
  the immutable request/outcome boundary, backend revision history,
  construction-time mode discovery and clear, exact-session non-mode
  capability, and Arrow integration. The accepted Text, Plus, Wavy, Bracket,
  Vector, paper, translation, deletion, and stacking routes commit canonical
  CDML and reproject the backend result. Historical variants outside those
  bounded grammars remain explicitly unsupported rather than pending release
  work.
- Deliverables: small, evidence-led production hypotheses only: selected Text,
  Plus, Bracket, Vector, or Wavy creation one at a time; presentation-only
  configure/move/delete behind an explicit eligibility gate; Paper Properties
  through the frozen exact-session non-mode capability; and presentation-only
  stacking after durable targeting evidence.
- Workstreams: WS-E1, WS-E2, and WS-E3.
- Entry criteria: M3 arrow gate passes.
- Exit criteria:
  - M4-0 remains the shared seam. The release-selected presentation routes
    have observed call sites, bounded requests, canonical reprojection, and
    semantic preservation evidence.
  - Each later claimed route has one observed call site, a bounded complete-CDML
    candidate, canonical reprojection, a uniform outcome, and semantic
    preservation evidence.
  - Atom-attached marks are an M5 capability, not an M4 presentation route.
    OASA accepts the bounded `atom.mark.apply` add/remove operation using the
    durable parent molecule and atom IDs, exact mark type, and direct-child
    order for deterministic removal; mark IDs are not required for that
    completed backend contract. MarkMode routing, canonical projection,
    exact-session lifecycle, backend history, and parent-atom selection are
    accepted in M5. Mark move, configure, and broader Delete behavior are
    explicitly unsupported. Groups, reactions, external data, unknown XML,
    template markers, and unsupported envelope records retain their stated
    preservation-only or separately supported dispositions.
  - Mixed chemistry/presentation operations, template/group expansion,
    molecule/atom/bond/fragment work, and mixed clipboard/order are governed
    by their accepted M5 request grammars or remain explicitly unsupported.
- Parallel-plan ready: only after M4-0 -- max parallel doers: 2 for disjoint
  small hypotheses; stacking waits for durable presentation-target evidence.

### Milestone M5: Chemistry and history

- Depends on: accepted M4-0 infrastructure and pre-M5 WP-F0. A selected M4
  hypothesis is a dependency only when an M5 slice actually consumes its
  accepted artifact; unfinished M4 preserve-only routes do not block chemistry
  authority work.
- Status: complete for the release-selected chemistry, worker, and history
  set. WP-F0's independently accepted inventory fixes the bounded
  release dispositions below. The backend-only molecule-insertion prerequisite
  is accepted and Interactive SMILES, explicit PubChem Insert, and Haworth H6a
  use it through the backend session. Their shared producer-side placement
  seam is also accepted. Mixed top-level Paste is accepted through the separate
  bounded top-level-insertion operation. Implementation evidence also exists
  for the narrow Draw slice: blank-canvas bonded-pair creation, atom extension,
  same-molecule atom joining, and bond-tool application use one bounded
  backend structural operation and canonical reprojection. Independent final
  review accepted this bounded Draw slice: 19 OASA structural tests passed, 13
  offscreen Qt Draw authority tests passed with `--kill-after 3`, and pyflakes
  plus `git diff --check` were clean. Generic graph editing, cross-molecule
  merging, overlap behavior, and unrelated legacy structural actions remain
  separately scoped. AtomMode element substitution is also accepted as a
  bounded route: a click submits the expected revision, direct molecule and
  atom IDs, and a different supported element symbol to OASA; OASA atomically
  changes only the canonical `<atom name>` field, and Qt replaces the
  projection from the accepted snapshot. The focused evidence is 13 OASA
  atom-substitution tests, 3 session-adapter Atom cases, 4 offscreen AtomMode
  authority tests, and 1 existing AtomMode setter interaction test, with
  independent backend, session, mode, and contract reviews accepted. This
  slice does not migrate generic atom properties or dialogs. Detached
  system-template placement is also accepted as a bounded route: Qt submits
  only an exact catalog name, current revision, and finite anchor; OASA owns
  catalog resolution, SMILES/coordinate preparation, 40-point mean-bond
  scaling, centroid anchoring, detached proposal construction, durable IDs,
  and atomic canonical acceptance. Blank and atom-click placement each add a
  separate root molecule and do not attach or fuse the clicked source. The
  accepted root correlation maps provisional to durable identity for selection
  after canonical reprojection. Focused evidence covers OASA placement,
  low-level session validation and stale rejection, public offscreen
  TemplateMode authority/undo, cross-tab origin binding, disposal-safe retained
  actions, scale parity, and focused hygiene checks. Attachment, fusion,
  markers, user catalogs remain separately scoped. BioTemplate placement is complete
  for the packaged OASA catalog through the same backend-owned detached-
  insertion contract: Qt sends a catalog key, current revision, and finite
  scene anchor, while OASA resolves the packaged entry, prepares its geometry,
  accepts canonical insertion, and returns durable selection correlation.
  Focused coverage includes source-plus-opaque preservation, atom-area
  detached placement, cross-tab origin binding, disposed-port unavailability,
  and accepted-snapshot retry without preparation or commit replay. These completed
  consumers close the release-selected M5 action families. Generic graph
  editing, cross-molecule merging, attachment/fusion, and other historical
  variants remain explicitly unsupported rather than open M5 work.
- Deliverables: the required or already-supported structural, worker, and
  revision-history slices selected by WP-F0; excluded families are disabled or
  removed from current release claims.
- Workstreams: WS-F0 and the selected WS-F1 through WS-F8 slices.
- Entry criteria: WP-F0 records a disposition for every visible Qt capability
  family and the M4-0 transaction/lifetime seam remains intact.
- Exit criteria:
  - No declared required chemistry action accepts persistent Qt mutation before
    backend commit.
  - Workers return backend-ready CDML candidates or pure results used to build
    such candidates.
  - Undo stacks retain revision identifiers and labels, not graphics/model
    ownership.
  - Save/restore and dirty state derive from backend revisions.
- Parallel-plan ready: yes -- max parallel doers: 3; structural chemistry,
  asynchronous insert/repair flows, and history adapter are separate lanes
  after the transaction protocol is stable.

### Milestone M6: Retire the old authority

- Depends on: WP-F3, WP-G1, WP-G1a, WP-G1b, and every WP-F0-required slice --
  authority retirement and the bounded required capability set must close.
- Deliverables: deletion/reduction of Qt full-document serializer and raw merge,
  final contract/parity audit, historical behavior/fixture inventory, clean
  Qt package build and installed smoke, and documentation close-out.
- Workstreams: WS-G0, WS-G1, WS-G1a, WS-G1b, and WS-G2.
- Entry criteria: M5 integration gate passes.
- Status: historical M6 authority-retirement work is complete for the
  release-selected boundary. The P0 normalized-presentation-default finding
  is closed by immutable OASA appearance facts and scalar-only Qt consumers.
  Source, packaging/documentation, installation, installed round trips, managed
  screenshots, glyph measurement, the complete four-root pytest aggregate, and
  the corrected six-perspective audit pass. Native retained-Tk launch remains
  unproven on this host because plain Tk aborts before BKChem initialization; it
  is deprecated retained compatibility evidence, not the shipped Qt path. A
  post-closure modularity audit also moved projection delivery values into a
  dependency-light session port with public ownership checks and moved molecule
  wrapper construction out of File Actions into a dedicated canvas projection
  module. These cuts preserve the accepted backend contract while reducing
  Qt-internal lifecycle and layer coupling.
- Exit criteria:
  - `bkchem_qt.io.cdml_document_io` only adapts backend CDML to projections or
    is removed.
  - Qt cannot save or reconstruct a complete document independently.
  - Backend-only and Qt end-to-end authority suites pass.
  - The released package contains only the Qt frontend; it contains no legacy
    Tk/Tcl application, dependency, or console entry point.
  - Publishable package artifact/install claims have fresh evidence from the
    one-time named final release checks.
  - Independent multi-reviewer audit finds no hidden Qt document owner.
- Parallel-plan ready: yes -- max parallel doers: 2; code retirement/audit and
  packaging/docs validation are separate after migration.

## Workstream breakdown

### Workstream WS-A: Lock authority

- Goal: make the settled architecture impossible to misread.
- Owner: architect.
- Work packages: WP-A1.
- Interfaces:
  - Needs: human decision.
  - Provides: invariant, API vocabulary, and first red test.
- Review boundary, when modifying the repository: contracts and authority test.

### Workstream WS-B: Build backend document authority

- Goal: preserve and transact complete CDML inside OASA.
- Owner: expert_coder.
- Work packages: WP-B1, WP-B2.
- Interfaces:
  - Needs: WP-A1.
  - Provides: WP-B1 complete-document API, then WP-B2 validation/revision API.
- Sequencing: WP-B2 begins implementation only after WP-B1 publishes and locks
  its record/document API.
- Review boundary, when modifying the repository: OASA document module and
  backend-only tests.

### Workstream WS-C: Project backend snapshots in Qt

- Goal: retain safe sessions while replacing persistent authority.
- Owner: expert_coder.
- Work packages: WP-C1, WP-C2.
- Interfaces:
  - Needs: WP-B1 and WP-B2.
  - Provides: WP-C1 backend adapter, then WP-C2 safe reprojection.
- Sequencing: WP-C2 begins implementation only after WP-C1 publishes and locks
  its session adapter API.
- Review boundary, when modifying the repository: `DocumentSession`, file I/O
  adapter, projection lifecycle.

### Workstream WS-D: Prove one vertical edit

- Goal: make arrow persistence demonstrate Model B end to end.
- Owner: expert_coder.
- Work packages: WP-D1.
- Interfaces:
  - Needs: WP-C1 and WP-C2.
  - Provides: reusable commit/reproject/undo action pattern.
- Review boundary, when modifying the repository: arrow mode, candidate CDML,
  and backend revision adapter.

### Workstream WS-E: Test bounded nonchemical hypotheses

- Goal: consume the accepted M4-0 seam only for small, evidence-led
  presentation or paper hypotheses while preserving all other records.
- Owner: coder.
- Work packages: WP-E1, WP-E2, WP-E3.
- Interfaces:
  - Needs: WP-D1.
  - Provides: accepted or rejected evidence for one bounded route at a time;
    it does not provide envelope-editor or all-presentation completion.
- Review boundary, when modifying the repository: one selected route and its
  preservation boundary per patch.

### Workstream WS-F: Migrate chemistry and history

- Goal: use the pre-M5 capability disposition to make backend revisions
  authoritative for the required chemical edits and workers.
- Owner: release integrator for WP-F0; the matching feature owner for each
  selected slice.
- Work packages: WP-F0 and selected WP-F1 through WP-F8.
- Interfaces:
  - Needs: accepted M4-0 transaction/lifetime infrastructure and WP-F0
    capability dispositions.
  - Provides: a bounded release capability set plus its action and undo
    migration evidence.
- Review boundary, when modifying the repository: structural actions, worker
  flows, history adapter, and capability dispositions separately.

### Workstream WS-G: Close integration

- Goal: remove transitional authority and produce release evidence.
- Owner: integrator.
- Work packages: WP-G0, WP-G1, WP-G1a, WP-G1b, and WP-G2.
- Interfaces:
  - Needs: M5.
  - Provides: no-hidden-owner audit, Qt-only delivery evidence, and release
    validation.
- Review boundary, when modifying the repository: authority retirement versus
  packaging/docs.

## Work packages

### Work package WP-A1: Record and test the invariant

- Owner: architect.
- Touch points: CDML and Qt contracts, decision record, human guidance, first
  OASA authority test.
- Depends on: none.
- Acceptance criteria:
  - The central invariant appears verbatim in the decision and plan.
  - No current contract assigns persistent envelope authority to Qt.
  - The backend-only test contains molecular, presentation, and opaque content.
- Evidence or review, when useful:
  - Run targeted Markdown links and the single red authority test.
- Obvious follow-ons:
  - Hand the exact public API expectation to WP-B1.

### Work package WP-B1: Implement complete CDML storage and API

- Owner: expert_coder.
- Touch points: new `oasa/cdml_document.py`, package exports, focused tests.
- Depends on: WP-A1.
- Acceptance criteria:
  - Parse through the existing `oasa.safe_xml` secure helper backed by the
    existing OASA `defusedxml` dependency; add no runtime dependency.
  - Keep DOM and index code free of Qt imports.
  - Parse and serialize complete CDML without Qt imports.
  - Preserve top-level and nested node order plus opaque subtrees.
  - Expose records and molecule chemistry projections without rebuilding the
    envelope from molecules.
  - Treat tokens only in recognized ID declarations and known references; do
    not emit those recognized provisional positions in stored snapshots or
    canonical responses, while preserving matching opaque XML unchanged.
- Evidence or review, when useful:
  - Backend fingerprint round-trip and import-boundary checks.
- Obvious follow-ons:
  - Integrate transactional validation from WP-B2.

### Work package WP-B2: Implement validation and revisions

- Owner: expert_coder.
- Touch points: `oasa/cdml_document.py`, validation helpers, focused tests.
- Depends on: WP-A1 and the API-lock gate published by WP-B1.
- Acceptance criteria:
  - Commit is atomic under malformed XML, duplicate IDs, and unresolved known
    references.
  - Revision increments only after accepted changes.
  - Restore copies an accepted revision into a new monotonically increasing
    revision and returns its canonical CDML.
  - History capacity is at least three and protects current, exact saved, and
    immediate pre-restore revisions when distinct; each restore replaces redo
    protection, a normal edit clears it, and older nonprotected history may
    evict. `mark_saved(expected_revision)` is called only after a successful
    filesystem write and retains canonical saved content for clean comparison.
  - Strict commit validates provisional declarations uniquely among recognized
    ID fields, permits repeated known references, rewrites known positions only,
    and rejects dangling tokens.
- Evidence or review, when useful:
  - State-before/state-after rejection tests and independent review.
- Obvious follow-ons:
  - Publish stable API for Qt adapter.

### Work package WP-C1: Bind backend authority to Qt sessions

- Owner: expert_coder.
- Touch points: `document_session.py`, file actions, CDML adapter.
- Depends on: WP-B1 and WP-B2.
- Implementation status: accepted as C1a/C1b/C1c. Each tab has a private
  backend session with canonical authority and immutable snapshots, one-use
  non-aliasing native-CDML staging, and a monotonic projection-provenance
  witness. Native CDML Open is backend-first with atomic
  registration/replacement rollback. When the total provenance capability is
  true, Save publishes exact OASA CDML and marks only that backend revision
  saved; otherwise ordinary Save is unavailable and Recovery Export publishes
  the exact backend snapshot without changing session state. Action commits
  remain pending in later work packages.
- Acceptance criteria:
  - Each tab owns one backend document session and revision.
  - Open projects the backend response; eligible Save writes the backend
    snapshot without Qt reconstruction.
  - Candidate commits use expected revision and session request guards.
- Evidence or review, when useful:
  - Two-tab revision isolation and Save-source tests.
- Obvious follow-ons:
  - Connect successful commits to WP-C2 reprojection.

### Work package WP-C2: Replace projections safely

- Owner: expert_coder.
- Touch points: `DocumentSession`, document projection, scene disposal, focused
  lifecycle tests.
- Depends on: the API-lock gate published by WP-C1.
- Implementation status: accepted. Candidate and recovery projections are
  prepared from immutable backend snapshots. Old callbacks, graphics items,
  scene ownership, and document ownership are detached exhaustively even when
  an item cleanup hook raises. Failure installs only a backend-derived recovery
  projection or enters an explicit unavailable state that refuses persistent
  operations and can retry the current backend snapshot. Selection restoration
  uses durable IDs rather than old wrapper identities.
  An independently accepted 2026-08-02 repair extends that lifetime boundary
  to legacy graphics-owning undo commands and generic selection/model
  traversal: one captured-scene helper validates wrappers before scene, parent,
  selection, removal, attachment, reparenting, or target traversal calls. The
  ordinary no-parent sentinel ends traversal before wrapper access, and a stale
  or replaced projection becomes inert before it can mutate a replacement scene.
- Acceptance criteria:
  - Replace only model/item projections while retaining tab/view/session.
  - Dispose old callbacks/items before wrapper destruction.
  - Restore selection by backend-owned ID and discard hover/preview state.
- Evidence or review, when useful:
  - Repeated offscreen reprojection and stale-result teardown tests.
- Obvious follow-ons:
  - Expose one action-facing commit/reproject helper.

### Work package WP-D1: Commit arrows through CDML

- Owner: expert_coder.
- Touch points: arrow mode, CDML candidate helper, revision undo adapter, arrow
  integration tests.
- Depends on: WP-C1 and WP-C2.
- Implementation status: accepted. Arrow submits plain coordinates to a
  complete-CDML candidate builder; OASA atomically returns canonical state and
  durable IDs; and Qt replaces its disposable projection from that response.
  Registered menu, toolbar, and shortcuts use the same one-step backend
  navigation decision. Accepted-but-unprojectable state preserves the backend
  result while blocking Save/navigation until exact retry. Confirmed discard
  reprojects after legacy-local edits. Native Save and close/reopen preserve
  opaque CDML through the backend writer.
- Acceptance criteria:
  - Arrow preview remains frontend-only.
  - Release submits complete CDML and accepts only the backend response.
  - The candidate uses a provisional arrow correlation token and the backend
    returns its allocated durable arrow ID in canonical CDML.
  - Molecules, text, and opaque nodes survive without Qt re-merge.
  - Undo/redo restores backend revisions and creates fresh projections.
- Evidence or review, when useful:
  - Backend-only and Qt vertical tests plus independent lifecycle review.
- Obvious follow-ons:
  - Generalize the proven pattern for WP-E work packages.

### Work package WP-E1: Test selected presentation routes

- Owner: coder.
- Touch points: one selected Text, Plus, Bracket, Vector, or Wavy creation
  path at a time; presentation-only configure/move/delete only after an
  explicit eligibility gate; and focused tests.
- Depends on: WP-D1.
- Implementation status: normal plain Text creation and Configure, normal Plus
  creation and family plus root size/foreground/background Configure,
  normal Wavy, bounded Vector creation, rectangular/Round Bracket creation, and
  presentation-only EditMode translation are accepted. OASA-owned bracket and
  geometric-presentation requests construct bracket pairs and Vector roots;
  Qt retains only style/kind, gesture, selection, and preview state. Remaining
  accepted creation routes submit complete-CDML candidates. Every route receives
  backend-issued durable IDs and canonically reprojects. Wavy additionally
  has independent creation-only acceptance evidence in
  [wavy_public_tests_final_acceptance_2026_07_28.md](../audits/wavy_public_tests_final_acceptance_2026_07_28.md).
  Generic direct-root move and delete now cover durable Text. Rich Text editing
  and Wavy root width/color Configure are accepted bounded routes. Other
  operations, remaining Wavy editing, and bracket attachment/container semantics remain
  outside this bounded route.
- Acceptance criteria:
  - One selected presentation operation changes only its bounded target in a
    backend-owned operation or candidate, commits it, and reprojects the
    accepted response.
  - The completed presentation-only Move route submits only after the
    eligibility gate proves current supported durable direct-root bindings and
    one common translation delta. Configure and Delete remain separate
    operations; mixed chemistry/presentation paths return to M5 without an M4
    request.
  - Atom-attached mark add/remove is an accepted bounded M5 backend operation:
    durable parent molecule and atom IDs, exact type, and direct-child order
    define its deterministic operation identity even though CDML marks remain
    ID-less. Qt MarkMode routing and its canonical reprojection, lifecycle,
    backend-history, and parent-atom selection evidence are accepted M5 work.
    Mark move, configure, and broader Delete behavior retain separate deferred
    identity and operation-grammar decisions.
- Evidence or review, when useful:
  - One focused behavior/undo/save test for the selected route; another route
    is not claimed until the prior evidence is reviewed.
- Obvious follow-ons:
  - Retire only the graphics-owning persistent command replaced by an accepted
    route.

### Work package WP-E2: Test paper and preserve envelope records

- Owner: coder.
- Touch points: Paper Properties dialog/action through the frozen exact-session
  non-mode capability, its bounded explicit-field backend patch, and focused tests.
- Depends on: WP-D1.
- Implementation status: accepted. Document Properties captures one registered
  active session, revision, active aliases, and non-mode capability before its
  detached dialog opens, then rechecks that ownership after acceptance. The
  dialog returns only explicit plain field intent and submits it to OASA's
  revision-bound paper patch; it never builds a normalized paper model or a
  complete candidate. OASA changes only the first direct supported `paper`
  attributes, preserves paper extensions, viewport, headers, references, and
  opaque sibling records, and canonical-reprojects accepted state. Backend
  revision history owns paper undo; the former paper-local graphics command is
  retired. Canonical no-ops retain revision, history, dirty state, and the
  installed projection, while tab replacement after dialog acceptance is inert.
- Acceptance criteria:
  - Capture the exact-session non-mode capability before opening Paper
    Properties; stale, closed, or replaced tabs are unavailable before submit
    and never retarget another tab.
- The paper patch changes only explicitly selected established paper fields and preserves
    unrelated envelope records and references.
  - Groups, reactions, external data, unknown XML, template markers, and
    unsupported envelope records are preserve/project-only in M4. No generic
    envelope editor is claimed without a separately selected operation.
- Evidence or review, when useful:
  - One small mixed-document preservation check and one paper dialog/action
    behavior check; no edit-all-envelope test.
- Obvious follow-ons:
  - Retire only the paper-local command if this bounded route is accepted.

### Work package WP-E3: Test presentation-only stacking

- Owner: coder.
- Touch points: object-stack action, presentation-order candidate, durable
  presentation targeting evidence, and focused tests.
- Depends on: WP-D1, M4-0, and accepted WP-E1 durable presentation-target
  evidence.
- Acceptance criteria:
  - Submit a reorder candidate only after an all-presentation eligibility gate
    and durable canonical targets are established.
  - Preserve molecule and opaque sibling order. Mixed, molecule, atom-mark,
    clipboard, and chemistry ordering routes remain transitional/M5 and do not
    submit an M4 request.
- Evidence or review, when useful:
  - One behavior-based reorder/preservation check, not a clipboard or stack
    permutation matrix.
- Obvious follow-ons:
  - Retire only the accepted presentation-stack route.

- Implementation status: accepted on 2026-07-30 after independent authority
  and test-quality review. Bring to Front, Send to Back, and Swap on Stack run
  only when every selected scene
  item maps through its current projection binding to one supported,
  durable presentation root of the active document. The request carries the
  backend revision, declared mode, durable presentation IDs, and exact target
  keys; OASA preserves molecule, envelope, comments, and opaque root records.
  Invalid, stale, mixed, ID-less, mark, atom, and foreign
  selections are inert. Accepted results use backend history and canonical
  reprojection; the former local reorder command no longer owns these routes.
  Permanent ordering evidence lives in
  `packages/oasa/tests/test_cdml_presentation_insert.py`. The public Qt reorder
  walkthrough is one-time evidence; its shared-window pytest was retired.

### Work package WP-F0: Triage visible Qt capabilities

- Owner: release integrator with the relevant feature owner.
- Touch points: this plan, the active Qt capability inventory, visible Qt
  menus/actions, and one existing focused action/session test per supported
  family.
- Depends on: accepted M4-0 infrastructure; WP-E1, WP-E2, and WP-E3 inform
  the inventory only when their bounded evidence exists.
- Required behavior:
  - Before M5, classify every visible Qt capability family represented by
    WP-F4 through WP-F8 as exactly one of: required for the Qt-only release
    with a bounded owner and migration slice; already supported but needing
    the common complete-candidate commit route; or deliberately unsupported,
    disabled/removed from current Qt UI where needed, and removed from release
    claims.
  - Use Tk only as historical evidence for a disposition; it creates no parity,
    packaging, or delivery obligation.
- Success criteria:
  - The inventory has one bounded disposition and linked evidence row for each
    visible family, with no unresolved partial/unsupported release claim.
  - Only required slices may block M6; excluded families create no feature
    parity work.
- Validation:
  - Review each inventory row with its linked existing focused action/session
    test. This is a bounded inventory review, not a browser, Tk, or
    feature-by-feature matrix.

#### Accepted disposition record

The independent WP-F0 review accepted this inventory. Each material visible
WP-F4--WP-F8 family has one disposition. A is a required bounded migration
slice, B retains an already-supported backend-authoritative or pure route, and
C means UI and release-claim removal, not migration work. Tk remains historical
evidence only.

| Family | Disposition and owner/slice | Smallest validation |
| --- | --- | --- |
| RDKit coordinate generation and repair actions | A -- chemistry-backend engineer; WP-F4/WP-F1/F2 common candidate route | Accepted/rejected candidate changes one revision/projection or neither. |
| Canvas hex-grid snapping | B -- OASA geometry owner and Qt canvas consumer; WP-F5 | Retain pure nearest-vertex/origin-tab assertion. |
| Glyph/bond and group-connector page rendering | A -- rendering engineer; WP-F5 | Offscreen group label/connector and page-export semantic assertion. |
| Haworth layouts | A -- chemistry-backend engineer; WP-F6/WP-F2 | Multi-ring save/reopen plus backend undo; stale/cancelled delivery is inert. |
| PubChem lookup Insert | A -- integration engineer; WP-F7/WP-F2 | Offline accepted insertion, save/reopen, undo; failed/stale delivery is inert. |
| Native CDML Open/Save/Save As and Recovery Export | B -- document-session owner; existing route | Exact-snapshot and no-baseline-mutation/session-capture checks. |
| Save As Template | B -- Qt window/session delivery | Validated detached single-molecule templates publish exact backend snapshots to the explicit frontend-owned catalog directory without changing saved baseline; rescan updates all live sessions. |
| Non-native imports (Molfile, SDF, SMILES, CDXML, CML) | A -- import-export engineer; WP-F8/WP-F2 | Each declared converter atomically commits or leaves the origin tab unchanged. |
| Full-page SVG, PNG, and PDF export | B -- snapshot-render adapter | One immutable backend snapshot produces each artifact without session mutation. |
| Cropped SVG export | B -- snapshot-render adapter | Captured CDML paper crop metadata controls detached SVG bounds. |
| Copy as SVG | B -- snapshot-render adapter | Captured durable selection IDs resolve against the same backend snapshot. |
| Export SMILES | A -- chemistry-backend engineer; WP-F4/WP-F8 | Selected durable ID query represents the exact backend molecule without mutation. |
| Export InChI | A -- chemistry backend and Qt identifier action; completed | Exact-revision SMILES observation yields OASA InChI/InChIKey without mutation. |

**2026-07-30 repair progress.** Normalize Bond Lengths, Normalize Bond Angles,
Clean Geometry, and Snap to Hex Grid now use the revision-bound
backend-authoritative `geometry.repair` route. Qt sends the captured
live-session revision, durable selected direct-root molecule IDs, declared
kind, and finite-positive plain `target_spacing_pt` value; OASA validates every
target before one detached, atomic result. Normalize Bond Angles keeps ring
atoms fixed; supports each movable non-ring component with at most one ring
anchor; retains an anchored component's anchor edge at arbitrary depth; assigns
outgoing bonds in source order to nearest 60-degree slots; advances exact
half-slot ties and collisions; and rejects multiply anchored or no-free-slot
topologies atomically. Existing nondegenerate bond distances remain unchanged;
spacing supplies only degenerate outgoing vectors. Clean Geometry
deterministically regenerates direct core atom layouts, preserves each target's
source centroid, and patches only direct point `x`/`y`. Snap to Hex Grid
applies one shared origin-zero displayed hex lattice to every selected target
at that spacing and likewise changes only direct atom point coordinates. All
four preserve unknown, foreign, unselected, and opaque content; canonical
lexical no-ops create neither a revision nor history. Accepted results replace
Qt's disposable projection, retain selection through durable molecule IDs, and
use backend history, undo/redo, dirty state, and Save. If projection
replacement fails, recovery reprojects only the exact current backend snapshot.
Normalize Rings now uses the same revision-bound `geometry.repair` route from
both its Repair menu and its durable-ID Repair-mode click path. The backend
accepts a ring-free semantic no-op or one simple independent cycle with
uniquely anchored acyclic substituent components. A durable-ID ordered ring
walk preserves the ring centroid, creates a regular polygon at the requested
spacing, and translates each component with its anchor. Fused, bridged, spiro,
multi-cycle, malformed, duplicate-ID, and multi-anchor inputs reject atomically
before any target changes. Its accepted result uses backend history and exact
snapshot projection recovery, not a Qt undo command. Straighten Bonds now uses
the same revision-bound `geometry.repair` route from
both its Repair menu action and its durable-ID Repair-mode click path. OASA
implements the backend contract for
`straighten-bonds`: it validates every selected direct-root molecule before
detached mutation, moves only nondegenerate degree-one endpoints to canonical
30-degree slots, uses increasing-angle exact-half ties, fixes the lexically
smaller durable atom ID in a two-atom component, and preserves all other CDML
content. Its common finite-positive spacing value is intentionally unused.
Accepted Qt results replace the disposable projection, restore durable
selection, and use backend history; a no-op keeps the existing projection and
history, while retry uses only the exact accepted/current snapshot. Canvas drag snapping is a separate transient
interaction-preview behavior, not the persistent Repair action.

A backend-only timing pass (five warm-ups and 31 samples after session load)
measured changed-operation p95 values of 0.810 ms for ethanol, 3.737 ms for
phenanthrene, and 14.707 ms for a 60-atom n-hexacontane. That supports the
synchronous M0 without claiming a GUI latency guarantee. Any asynchronous tier
requires later measurements of representative multi-molecule documents through
Qt projection and rendering rather than a worker protocol inferred from layout
time alone.

**2026-07-29 progress.** The non-native Open replacement slice stages every
advertised worker-backed Molfile, SDF, file-SMILES, CDXML, and CML source as a
strict complete backend CDML document. The receiving session is pathless and
backend-dirty against the empty-document saved baseline until authoritative
CDML Save. Interactive SMILES, InChI, and peptide now share the separate
revision-bound `molecule.insert` proposal route: OASA prepares positioned
plain CDML, the captured session commits atomically, and Qt rebuilds only from
the accepted snapshot. The legacy graph-to-Qt-model/local-undo text-import
delivery is no longer an active visible action path.

**2026-07-30 Export SMILES completion.** OASA provides the frontend-neutral
revision-bound `query_molecule_smiles` observation for one direct-root durable
molecule ID. It decodes the authoritative current record through the existing
CDML/RDKit chemistry path and returns an immutable revision-tagged canonical
isomeric SMILES value without a commit, candidate, CDML rewrite, history entry,
or saved-state change. Invalid, stale, missing, nested, opaque, and wrong-kind
targets reject atomically; a direct-root record without a supported conversion
has one typed unavailable result. Qt now captures one active synchronized
session, current backend revision, and one durable direct-root molecule ID from
canonical top-level selection order, then consumes only that observation result.
It neither converts a Qt molecule nor changes projection, history, or dirty
state. Unsupported no, multiple, mixed, or presentation selection and typed
unavailable, stale, or out-of-sync outcomes remain frontend-local warnings.

**2026-07-30 legacy projection identity repair.** Compatibility-loaded
ID-less core atoms and bonds retain exact backend CDML while Qt assigns only
private model/source linkage needed to render them. That linkage never becomes
a durable child-selection key or child-targeted mutation ID. A root-only
observation can nevertheless resolve an ID-less selected atom, bond, or mark
to its owning backend-issued direct-root molecule ID, so Export SMILES observes
only the durable root without fabricating a child ID. Backend-issued core IDs
continue to drive normal child selection, Draw, AtomMode, context-menu,
template, and numbering routes. A backend ID-normalization transaction remains
outside this bounded projection/session repair.
Child actionability additionally requires one unique durable direct-root
molecule ID; duplicate or otherwise ambiguous atom endpoints remain display-only
and never hydrate a visible bond by choosing one duplicate.

**2026-08-11 Export InChI completion.** The projection-derived adapter remains
retired. Qt now exposes `chemistry.gen_inchi` for one exact-revision durable
molecule selection, obtains canonical SMILES only from OASA's document query,
and asks OASA's RDKit codec for standard InChI and InChIKey scalar facts.
Clipboard and dialog presentation remain frontend-owned while the observation
leaves revision, history, dirty state, projection, and selection unchanged.
Bundled RDKit means no external executable or path preference is required.

**2026-07-30 molecule display names.** Set molecule name is now a revision-bound
backend operation for one direct-root durable molecule ID and exact string
value. It replaces or clears only `molecule@name`, preserves whitespace, and
uses accepted backend snapshots for Qt undo, dirty state, and reprojection.
An exact same-result response is a successful authoritative no-op: Qt retains
the installed projection and preserves history, revision, dirty state, and
Save eligibility. The visible Set molecule ID action is retired because durable
IDs remain backend-owned identity rather than editable presentation data.

The common A blocker is the complete-CDML candidate/commit/reproject route for
Qt-local structural changes. Independent B and rendering/query/export lanes do
not wait for molecule insertion unless their own slice declares that dependency.

#### Accepted M5 insertion evidence and next slice

The following bounded slices are accepted as implementation evidence. They do
not complete M5 or authorize unrelated persistent action families.

**Top-level insertion.** OASA document authority accepts a complete supported
top-level CDML fragment at an expected revision, validates it detached,
allocates fresh durable IDs, rewrites fragment-local references, translates
persistent geometry, and commits once. Rejected or stale work changes neither
snapshot nor history; accepted mixed content preserves order and is returned as
the canonical immutable snapshot. Focused
`packages/oasa/tests/test_cdml_top_level_insertion.py`,
`test_cdml_molecule_insertion.py`, and `test_cdml_document_authority.py`
passed 111 tests in 0.47s. The correctness review is
`tmp/authority_m5/backend_top_level_insertion_acceptance_v3.md`. The existing
new regression file must be included in the delivered change set.

**Detached system-template placement.** A frontend submits one exact
backend-catalog name, expected revision, and finite scene anchor. OASA
resolves and prepares the system template, applies the measured 40-point
mean-bond and centroid-to-anchor placement rule, creates a detached
molecule-only proposal, and accepts it through the existing atomic insertion
path. Blank and atom-click gestures each create a separate direct-root
molecule; atom anchoring does not mutate, bond to, attach, or fuse the source
molecule. The accepted provisional root-to-durable ID mapping is the only
post-reprojection selection source. Exact-snapshot retry preserves valid
durable selection correlation without replaying the placement. Pointed evidence
covers OASA placement, low-level session validation and stale rejection,
public offscreen TemplateMode authority/undo, cross-tab origin binding,
disposal-safe retained actions, scale parity, and focused hygiene checks.
Attachment/fusion, markers, and user catalogs remain separately scoped.
The 2026-08-03 evidence gate keeps system-template atom attachment out of this
migration: the current `Me` catalog entry is the one-atom SMILES `C`, whereas
the legacy attachment path used different marked CDML templates and depended
on Tk canvas overlap merging. Turning `Me` into a retained-target C-C insertion
would therefore be a new product operation with its own explicit gesture,
topology, valence, geometry, and identity contract, not completion of the
detached placement route.
BioTemplate placement is complete for the
packaged OASA catalog as a separate-root insertion; it has no attachment or
fusion behavior. Its authority evidence proves source and opaque-root
preservation, atom-area event anchoring, durable selected-root correlation,
cross-tab origin binding, lifecycle unavailability, and exact-snapshot retry.

**Mixed top-level Paste.** Qt reads raw clipboard CDML, captures and rechecks
one live session, submits one top-level insertion request, records accepted
history before projection, and reprojects only the accepted snapshot. A
rejected request is inert; an accepted projection failure recovers only by
exact snapshot reprojection; active-menu and context-menu eligibility require
both clipboard data and session capability. Copy remains a non-mutating Qt
clipboard adapter.

**Whole-root Cut.** Qt resolves the active projection selection through the
same canonical top-level resolver as Copy, captures only ordered durable
direct-root `(kind, id)` data, publishes the fragment first, then sends one
revision-bound `top-level.delete` request through the exact originating
session. A clipboard-delivery tab change cannot redirect that capability to
another tab. Accepted Cut uses backend history, dirty state, canonical
reprojection, and snapshot-only recovery; unavailable, stale, ID-less,
foreign, unsupported, or rejected synchronized targets remain document-inert
after clipboard publication. The request freezes its expected revision before
publication, so a callback commit yields a stale outcome rather than deleting
from its changed snapshot; a callback isolation transition keeps the
synchronized Cut unavailable. Legacy-isolated documents retain their local Cut
grammar only when their originating projection, persistent generation, and
selection remain current after publication. This bounded route leaves partial
structural Delete, atom-mark semantics, unsupported selection families, and
mixed move/configure behavior for their own operation grammars. Focused
clipboard coverage validates mixed molecule/presentation deletion,
opaque-sibling preservation, backend undo/redo, failure inertness, exact-tab
binding, callback staleness, and isolation handling.
The implementation-era clipboard adapter suite was retired after acceptance.
OASA semantics remain permanent; native clipboard behavior is one-time evidence.

**Backend-owned whole-root clipboard extraction.** OASA now supplies one
revision-bound read-only query for unique durable direct roots. It resolves
only insertion-supported roots in canonical source order, clones the complete
selected subtrees with namespace context, and proves the detached result through
the existing top-level Paste preparation path. Synchronized whole-root Copy and
Cut now publish that OASA result rather than reconstructing a fragment from Qt
models; Cut freezes its delete capability and revision before native clipboard
publication. Unsupported, ambiguous, stale, ID-less, or insertion-invalid
content remains typed and read-only. This completes only the bounded
whole-root clipboard authority seam; broader clipboard and action-family
migration remains open.

**Partial structural Cut M0.** OASA now exposes a read-only revision-bound
structural-fragment extraction query for one eligible direct-root molecule.
It validates the structural-delete source grammar, then sends a detached clone
through the complete shared Paste preparation and acceptance path while
preserving the exact returned source-order fragment. It closes selected bonds
over endpoints and rejects disconnected, missing, or insertion-unsupported
selections without state/history mutation. Qt resolves every selected wrapper
through the current disposable-projection APIs before reading durable fields;
mixed structural/presentation, mark, foreign, ID-less, multi-molecule, and
unsupported selections are inert rather than promoting to whole-root Cut. Qt
publishes the returned raw fragment before submitting the frozen explicit
`structure.delete` request to the captured origin session. Endpoint closure is
clipboard-only. Partial structural Copy now uses the same read-only OASA
extraction query without the Delete request: it freezes only revision and
plain durable IDs, publishes the returned CDML after wrappers leave scope, and
keeps backend/Qt history and projection unchanged. Invalid structural Copy
preserves prior clipboard content, while legitimate root, mixed, and
multi-molecule Copy keeps the established top-level route. Rich/template
structures and broader Cut semantics remain separate decisions.

**PubChem lookup Insert.** PubChem is independently accepted as one bounded
WP-F7/WP-F2 consumer; this does not complete M5 or WP-F6. Its worker performs
backend-owned preparation and returns frozen display facts plus a frozen
`PreparedMoleculeInsertion`, without creating Qt document, undo, scene, or
graphics state. Explicit Insert submits one immutable `molecule.insert`
operation to the captured origin session. OASA parses the molecule-only
proposal, composes the complete candidate, and atomically commits it through
`CDMLDocumentSession.insert_molecules()`.

The accepted callback recovers a projection failure only by exact reprojection
of the accepted/current backend snapshot; it clears the accepted proposal and
cannot submit it again. Origin-session, request-token, revision,
registered-session, disposal, and dialog-state fences prevent a tab switch,
stale result, or closed session from receiving the operation. Backend history
owns accepted undo/redo and Qt undo remains empty. Terminal worker delivery is
window-owned: `MainWindow` releases the worker through a registered live
session when one exists and otherwise retires it directly, so queued completion
never dereferences a retired source session. Acceptance evidence is recorded in
`tmp/authority_m5/pubchem_backend_authority_final_acceptance_v6.md`, with the
terminal lifetime correction and test-teardown evidence in
`tmp/authority_m5/pubchem_worker_terminal_lifetime_correction_v3.md` and
`tmp/authority_m5/pubchem_terminal_test_teardown_fix_v5.md`.

**Worker retirement clarification.** Session-wide request tokens now
invalidate delivery across all asynchronous import families in one session.
Tab replacement and close transfer invalidated workers and GUI relays to
MainWindow rather than joining native work. Application shutdown obtains its
save/recovery/discard approvals before entering a Qt event-loop drain, which
retains those workers until `QThread.finished`; interruption is therefore
truthful delivery cancellation rather than preemption. Clean Geometry remains
synchronous pending a separate measured experiment.

**Clean Geometry measurement decision.** The production public path on a
ring-plus-tail representative measured end-to-end p95 of 16.279, 27.886,
43.821, and 61.631 ms for 10, 30, 60, and 100 atoms respectively (three warmups
and 15 samples; 100-atom maximum 61.631 ms), with no Qt lifetime anomaly.
Current evidence does not justify an asynchronous redesign. Revisit chemically
diverse, fused, and multi-molecule inputs only after a user-visible stall or
approximately 100 ms p95 evidence.

**Haworth H6a and shared insertion placement.** H6a is independently accepted
for the existing monosaccharide pyranose and furanose actions only; it does
not complete WP-F6. Each action captures its originating session, expected
revision, request token, live grid spacing, and paper-center anchor before
worker preparation. The worker emits one frozen plain
`PreparedMoleculeInsertion`, and the captured live session submits it once via
`molecule.insert`. The accepted proposal is consumed before any projection
recovery. Backend history owns undo/redo; accepted or current canonical CDML
is the only projection-recovery source.

The shared OASA placement boundary applies one collective detached-graph
transform before proposal serialization for Haworth H6a, Interactive SMILES,
and explicit PubChem Insert. Qt captures only a built-in finite float and a
two-float tuple before a worker starts. Bonded and disconnected proposals are
scaled by their collective real-bond mean and centered at that anchor; atom-only
proposals are anchored without inventing a bond. Thus accepted canonical CDML,
rather than a Qt repair, contains final scene-scale geometry. The backend
placement operation is finite, typed, and atomic: it covers aggregate `1e308`
inputs, subnormal values, huge built-in integers, and late nonrepresentable
outputs with `ValueError` and no partial graph mutation.

H6a persists `q`, `w`, `n`, and `haworth_position` through proposal, commit,
reload, and backend undo. The independently accepted evidence is
`tmp/authority_m5/haworth_backend_insert_final_acceptance_v4.md` and
`tmp/authority_m5/shared_insertion_geometry_final_acceptance_v6.md`, with the
producer audit and numeric corrections in
`tmp/authority_m5/authoritative_insert_geometry_audit_v1.md`,
`tmp/authority_m5/shared_authoritative_insertion_geometry_review_v2.md`,
`tmp/authority_m5/shared_insertion_geometry_overflow_correction_v3.md`, and
`tmp/authority_m5/shared_insertion_geometry_numeric_boundary_correction_v5.md`.
The final focused OASA placement/insertion subset passed 23 tests with 10
deselected, and the serial offscreen SMILES, PubChem, and Haworth modules
passed 41 tests without a native crash.

**Directed wedge endpoint prerequisite.** CDML 26.07 now treats serialized
`w1` and `h1` `start`/`end` references as authoritative directed depiction
endpoints: `start` is the narrow tip and `end` is the wide base. Normal OASA
CDML decoding preserves that order. Geometry canonicalization remains an
explicit construction or version-scoped legacy-migration choice, never an
implicit authoritative-decode repair. Independent generic, reflected Haworth,
strict-session, and fixed-sucrose evidence accepted this behavior. It resolves
the H6b wedge round-trip prerequisite, but it does not complete H6b, WP-F6, or
M5. Acceptance is recorded in
`tmp/authority_m5/cdml_directed_wedge_endpoints_final_acceptance_v2.md` and
`tmp/authority_m5/directed_wedge_acceptance_record_v1.md`.

H6b is accepted for one named `verified_sucrose_haworth_v2` preset. OASA owns
the immutable CID 5988 source identity, role-keyed fixed coordinates, and
directed q/w/n depiction; it validates them before one detached-graph mutation.
Qt captures only source-session/revision/token and plain placement values, then
uses the existing frozen `PreparedMoleculeInsertion` and one `molecule.insert`
commit. Commit/reload preserves the fixed depiction within CDML quantization
tolerance, and backend undo/redo restores authoritative snapshots. Current
OASA/CDML does not recover generic tetrahedral stereochemical records, so this
remains one fixed deterministic Haworth depiction. Fused, spiro, indirect, and
arbitrary disaccharide inputs remain out of scope. Implementation evidence is
`tmp/authority_m5/h6b_verified_sucrose_preset_implementation_v1.md`.

Delete now has one bounded durable grammar for complete selected direct-root
molecules and supported presentation records, and whole-root Cut uses that
grammar through the bounded clipboard route above. Partial structure,
atom-mark, and unsupported/mixed Delete selections retain their separate
transitional scope until their operation semantics define bonds, components,
marks, and ordering.

**Partial structural Delete evidence.** Current Qt `EditMode` partial deletion
is a legacy-local projection mutation: its backend snapshot remains unchanged
and the result is isolated from backend authority. The retained deterministic
probe is `tmp/partial_structural_delete_probe.py`. It observes that deleting a
terminal atom removes that atom and its incident bond while retaining one
molecule; deleting a central atom leaves its disconnected surviving atoms in
that same molecule; and deleting a bond retains its atoms, including the
observed orphan-cleanup gap. Unrelated direct-root presentation content
survives the local projection mutation. Legacy Tk instead cleans orphan atoms
and splits components. A durable backend grammar therefore waits for an
explicit decision on isolated atoms, disconnected-component root and order
semantics, references, and mixed selections.

**Partial structural Delete decision (2026-07-30).** OASA now supplies the
frontend-neutral `structure.delete` authority slice for one durable direct-root
core molecule. It removes selected direct atoms/bonds plus incident bonds,
retains unselected isolated atoms, and reports source-ordered removals and
components with one accepted canonical snapshot. Components follow earliest
surviving direct-atom order; one retains the original root, while split roots
use collision-safe backend molecule IDs reserved against the complete
pre-delete document and appear immediately after it. A recognized reaction
reference permits only a one-component result. Invalid topology, unsupported
molecule content, malformed or ambiguous targets, reaction split/removal, and
stale requests remain atomically inert. Qt now routes exact current-projection
partial atom/bond selections from one durable molecule through this operation.
It releases its references to wrappers before submission, records accepted
backend history before canonical reprojection, clears deleted selection, and
never resubmits accepted intent after projection failure. Synchronized
unavailable, ID-less, foreign, multi-molecule, mark, presentation, mixed, or
unsupported structural selections are inert; exact eligible selected marks use
the dedicated atom-mark operation above. Only intentionally legacy-isolated or
standalone canvases retain local undo. Partial Cut, multi-molecule structural
deletion, and wider molecule grammar remain separate capabilities.

Broad lxml conversion is a separate low-priority parser-maintenance track, not
an M5 authority slice.

### Lxml boundary decision (2026-07-28)

Complete CDML remains authorized by hardened lxml parsing plus lexical
compatibility-DOM storage. The prefix-shadowing composition experiment showed
that lxml cross-tree composition can change an opaque attribute's namespace
meaning; retaining the lexical DOM is semantic preservation, not a
byte-equivalence requirement. OASA CDML tests now use the public hardened
boundary, and no direct native XML parser call in the named OASA production or
test inputs represents an unresolved security issue. This does not claim that
all native XML imports are gone.

Two bounded format-specific lxml slices are accepted:

- `render_out` constructs and serializes only fresh, controlled SVG through
  lxml. One render-operation walker supplies both thin lxml and minidom
  adapters, so SVG semantics have one owner. The legacy `svg_out` mutable
  minidom facade and callback protocol remain unchanged.
- External CDXML input uses a fresh hardened lxml parser that rejects every
  DOCTYPE/DTD before traversal. It retains the existing narrow,
  case-sensitive CDXML molecule-import behavior and returns OASA chemistry
  values rather than lxml nodes. CDXML export remains controlled minidom.

The remaining work is deliberate, low-priority format-specific maintenance,
not M5 completion:

- `cdml_writer` can produce fresh lxml strings experimentally, but production
  use waits for one immutable ordered record builder and pre-emission ID plan
  feeding both minidom and lxml sinks. The current element API remains a
  minidom compatibility boundary.
- `svg_out` has an additive callback-free lxml path demonstrated by experiment;
  `render_out` now supplies that controlled-output use case. The public,
  mutable minidom facade remains until callers deliberately opt into a new API.
- `cdml_xml` retains its lxml authorization gate plus lexical minidom sidecar
  because the QName experiment proves the sidecar necessary for opaque
  cross-tree preservation. `dom_extensions` remains the minidom compatibility
  layer.

This is not a new milestone, browser-work scope, or a stable contract/spec
change.

### Work package WP-F1: Migrate structural chemistry

- Owner: expert_coder.
- Touch points: atom/bond/molecule/fragment/group expansion/linear/template/
  numbering actions and focused tests.
- Depends on: WP-F0 and the accepted M4-0 seam; no M4 preserve-only route is
  a chemistry dependency.
- Accepted prerequisite: OASA accepts a complete molecule-only proposal CDML
  at a captured expected revision, atomically appends detached proposal
  molecules, and returns canonical state with durable-ID/token semantics. An
  OASA-only provisional serializer supplies the proposal without exposing graph
  IDs. Interactive SMILES, PubChem, Haworth, file imports, and repair consume
  this seam through accepted release-selected M5 routes. Historical consumers
  outside the inventory remain explicitly unsupported.
- Acceptance criteria:
  - Persistent chemistry and depiction fields change only after backend commit.
  - Implicit-group expansion M0 accepts one direct implicit group with one
    exterior bond. OASA creates attachment-aware detached geometry, splices it
    into a candidate, and accepts one canonical atomic snapshot; Qt then
    reprojects that response and never mutates durable group or graph state.
    Builtin, explicit, rich, zero-attachment, and multi-attachment groups are
    later operations.
- Evidence or review, when useful:
  - Delete/undo/redo and CDML semantic round-trip through backend.
- Obvious follow-ons:
  - Remove local graph-authority fallbacks.

#### Completed ordinary fragment metadata slice

#### Completed direct atom-mark observation slice

#### Completed direct group observation slice

- Exact-revision OASA group observation now supplies synchronized Qt and
  snapshot rendering with visible label/style facts, selectable durable
  addresses only when unambiguous, and exact implicit-expansion eligibility.
  Synchronized molecule source clones remove every direct local-name group and
  its incident group bond, including foreign lookalikes; standalone loading
  retains its compatibility decoder. Molecule/atom/bond projection decoding is
  the remaining WP-G1 boundary.

- Exact-revision OASA atom-mark observation now provides synchronized Qt and
  snapshot rendering with normalized display facts and unambiguous deletion
  ordinals. Direct atom source clones remove every local-name `mark` child
  after hydration, including foreign lookalikes; standalone compatibility
  loading retains its old decoder. Molecule, atom, and bond decoding remain
  the WP-G1 projection boundary.

- `fragment.create` and `fragment.delete` now use revision-bound OASA
  operations for the narrow ordinary `explicit`/`implicit` grammar. The
  backend allocates fragment IDs and preserves richer imported fragments as
  read-only content.
- Exact-revision OASA fragment observation now supplies synchronized Qt and
  snapshot rendering with plain ordinary eligibility and read-only notices.
  Synchronized molecule source clones retain no direct fragment XML. Molecule,
  atom, and bond decoding remain the next WP-G1 projection boundary.

#### Completed linear-form conversion slice

- `linear-form.convert` accepts only expected revision, a durable direct-root
  molecule ID, and ordered selected direct atom IDs. OASA derives the path,
  owns fixed 10-point geometry, explicit-mark and uniquely anchored external
  component translation, hydrogen display, collision-free narrow metadata, and
  semantic no-op detection. Qt submits one origin-bound plain request and uses
  backend history plus canonical reprojection; local macros remain legacy-only.

### Work package WP-F2: Migrate asynchronous chemistry

- Owner: expert_coder.
- Touch points: imports, text chemistry, PubChem, Haworth, repair/clean workers,
  session tokens, and focused tests.
- Depends on: WP-F0 and the accepted M4-0 seam; no M4 preserve-only route is
  a worker dependency.
- Acceptance criteria:
  - Workers perform pure preparation and submit complete CDML candidates.
  - Stale/closed results cannot commit or create Qt projections.
- Evidence or review, when useful:
  - Event-driven worker, origin-tab, rejection, and teardown tests.
- Obvious follow-ons:
  - Delete direct `AddMoleculeCommand` delivery paths.

### Work package WP-F3: Move undo and dirty state to revisions

- Owner: expert_coder.
- Touch points: backend history, Qt undo adapter, title/clean state, focused
  tests.
- Depends on: WP-D1 and migrated action labels.
- Acceptance criteria:
  - Qt retains revision IDs and labels only.
  - Undo/redo call backend restore, which creates new revisions and fresh
    projections; the backend protects the immediate pre-restore revision for
    redo, replaces that protection on each restore, and clears it on a normal
    accepted edit.
  - Clean/dirty compares canonical content to saved baseline, not
    revision-number equality; a new edit after undo clears Qt redo navigation
    without changing retained backend snapshots.
- Evidence or review, when useful:
  - Multi-tab history isolation and graphics-wrapper lifetime review.
- Obvious follow-ons:
  - Remove graphics-owning persistent commands after their action migrates.

### Work package WP-F4: Deliver RDKit-backed chemistry decisions

- Owner: chemistry-backend engineer.
- Touch points: OASA coordinate-generation and chemistry-operation adapters,
  declared package dependency metadata, Qt preparation callers, and focused
  OASA tests.
- Depends on: WP-F0, WP-F1, and the complete-CDML candidate path.
- Required behavior:
  - Treat RDKit as the required shipped dependency declared in
    `packages/oasa/pyproject.toml` and `pip_requirements.txt`; declared
    coordinate-generation and chemistry operations are pure backend requests
    and results, with no Qt type crossing this boundary.
  - Apply a successful result only through an atomic backend CDML commit;
    bounded operations may construct their detached canonical candidate inside
    OASA rather than exposing it to Qt.
  - Reject malformed input or an unsupported operation with a typed, atomic
    failure that leaves the backend revision unchanged.
- Success criteria:
  - Every declared supported operation has deterministic input, typed failure,
    and a CDML persistence path.
  - Package metadata and normal shipped behavior agree that RDKit is required;
    no optional-dependency normal path or version matrix is introduced.
- Validation:
  - Focused backend operation, malformed/unsupported-operation atomicity, and
    Qt candidate-commit tests, plus a package dependency metadata check.

### Work package WP-F5: Correct owned rendering defects and evaluate sharing

- Owner: rendering engineer.
- Touch points: OASA render-operation builders and geometry helpers, Qt scene
  render consumers, glyph/bond fixtures, and focused geometry tests.
- Depends on: WP-F0 and WP-F1; a persistent rendering preference may use an
  accepted WP-E1 candidate path only where that route has its own evidence.
- Required behavior:
  - Correct known glyph/bond endpoint and hex-grid defects in their owning
    geometry consumer without making scene items part of OASA APIs.
  - Run a small comparison of one representative glyph/bond and one hex-grid
    case across existing consumers. Introduce a shared render-operation
    representation only if it demonstrates a correctness divergence that
    cannot be fixed at the owning layer; record that decision separately.
- Success criteria:
  - Known owned defects meet documented geometric tolerances.
  - Any shared representation is justified by the bounded divergence evidence,
    not assumed as an authority prerequisite.
- Validation:
  - Focused backend geometry test and offscreen Qt projection assertion. Do
    not require universal render IR adoption or pixel equivalence across every
    renderer or export format.

### Work package WP-F6: Complete Haworth SMILES and multi-ring slices

- Owner: chemistry-backend engineer.
- Touch points: OASA Haworth/SMILES parsers and layout planners, Qt Haworth
  actions/workers, CDML candidate helpers, and focused chemistry tests.
- Depends on: WP-F0, WP-F2, and WP-F4 where a shared chemistry adapter is
  required by the disposition.
- Required behavior:
  - Support the declared Haworth SMILES ring forms and multi-ring/glycosidic
    layouts as detached backend proposals.
  - Worker delivery remains frontend-local; its accepted persistent result is
    a complete CDML candidate committed by OASA.
- Bounded sequence:
  - H6a migrates the current monosaccharide pyranose and furanose routes only.
    Preparation produces a frozen plain `PreparedMoleculeInsertion`; it
    captures origin session, expected revision, and request token, then uses
    the common `molecule.insert` commit/reprojection route. Acceptance
    preserves `haworth_position`, `q`, and `w` through commit, reload, and
    backend undo.
  - H6b implements the one production `verified_sucrose_haworth_v2` fixed
    direct-glycosidic depiction. Its exact source identity and fixed geometry
    are backend-owned; it uses the H6a worker/commit/reprojection route.
    Fused, spiro, indirect, and arbitrary disaccharide inputs remain out of
    scope.
- Accepted bounded slice:
  - H6a is accepted for the current pyranose and furanose actions. It uses the
    frozen captured-session/revision/token proposal and one atomic
    `molecule.insert` commit, consumes accepted proposals, uses backend
    history, and recovers only by exact current-snapshot reprojection. Its
    common pre-serialization placement operation makes canonical CDML carry
    scene-scale Haworth coordinates and durable q/w/n/`haworth_position`
    annotations. The named fixed sucrose preset and the bounded direct-
    glycosidic two-ring profile are accepted; broader carbohydrate semantics
    remain explicitly outside the release set.
- Success criteria:
  - Each supported multi-ring input has deterministic Haworth depiction,
    coordinates, and durable CDML persistence after insertion; current
    OASA/CDML does not claim recovered tetrahedral stereochemical records.
  - Parse, layout, cancellation, and commit failures leave the session
    unchanged.
- Validation:
  - Focused OASA SMILES/layout fixtures plus offscreen origin-tab,
    cancellation, persistence, and undo tests.

### Work package WP-F7: Complete PubChem lookup and insertion

- Owner: integration engineer.
- Touch points: OASA PubChem transport/lookup modules, Qt lookup worker and
  insertion action, session tokens, and focused offline transport tests.
- Depends on: WP-F0, WP-F2, and WP-F4 when the disposition retains lookup.
- Required behavior:
  - Keep request construction, parsing, and typed backend errors independent
    of Qt; keep worker lifetime and UI delivery in Qt.
  - Insert only an OASA-prepared, complete-CDML candidate into the originating
    live session after explicit user action.
- Success criteria:
  - Lookup failure, cancellation, stale delivery, and malformed response make
    no persistent change.
  - Accepted insertion survives save/reopen and backend revision undo/redo.
- Validation:
  - Injected-transport backend tests and pointed offscreen worker/session/
    persistence tests with no real network access.
- Accepted bounded slice:
  - PubChem Lookup Insert is independently accepted. Backend-only preparation
    returns a frozen molecule proposal; the captured origin session commits it
    atomically through `molecule.insert`, exact-snapshot recovery follows any
    projection failure, and backend undo/redo owns accepted history. Window-
    owned terminal delivery never dereferences a retired source session. This
    accepts WP-F7's PubChem consumer. Other historical capability families
    retain their explicit inventory dispositions rather than open M5 work.

### Work package WP-F8: Define supported import and export paths

- Owner: import-export engineer.
- Touch points: OASA import converters and render/export operations, Qt file
  actions, package capability metadata, and focused format tests.
- Depends on: WP-F0, WP-F2, WP-F5, and WP-F7 where a WP-F0-required input or
  output family shares those operations.
- Required behavior:
  - Keep `.cdml` as the only native Save and Save As document path. Start from
    the formats actually exposed by Qt: import converts an input into a
    backend complete-CDML candidate, while export consumes an exact canonical
    backend snapshot without mutating the session or saved baseline.
  - Give excluded exposed formats one concise reason and remove or disable
    their release claim; do not inventory every historical Tk menu item.
  - The bounded Recovery Export path is implemented as exact backend-snapshot
    publication with no session or saved-baseline mutation. Its focused action
    and close tests cover projection-unavailable liveness, exact-session close,
    and publication-neutral durability uncertainty. Ordinary
    `write_backend_snapshot` remains Save and marks saved; broader WP-F8
    import/export coverage remains pending.
- Success criteria:
  - Each declared input family either commits its candidate atomically or
    leaves the session unchanged; each declared output family proves it reads
    the exact canonical snapshot without session mutation.
  - Native Save routing, the implemented Recovery Export path, and all release
    claims preserve the `.cdml` authority boundary.
- Validation:
  - One converter atomic-rejection/round-trip test per declared input family,
    one non-mutating export test per declared output family, a Qt native-save
    routing test, and focused Recovery Export no-mutation/action-state tests.

### Work package WP-G0: Deliver the Qt-only release

- Owner: release integrator.
- Touch points: `packages/bkchem-app/pyproject.toml`,
  `packages/bkchem-qt.app/pyproject.toml`, `devel/build_qt_app.py`,
  `devel/qt_bundle_plan.py`, release scripts, package tests, `README.md`,
  `docs/INSTALL.md`, and `docs/USAGE.md`.
- Depends on: WP-G1 for early package preparation, which is non-release
  evidence only. Publishable Qt-only delivery and current-user documentation
  additionally depend on WP-G1a, WP-G1b, and the M6 authority gate.
- Required behavior:
  - Ship `bkchem-qt` as the release application. Exclude the deprecated Tk
    application, Tcl/Tk collection, and legacy `bkchem` entry point from
    release artifacts and current-user instructions; retain their source.
  - Keep the Qt app builder experimental until controlled native-build evidence
    supports a release artifact. The active path makes no DMG claim.
  - Retain legacy source and CDML fixtures only as non-shipped behavioral
    evidence; do not remove them merely to make a package scan pass.
- Success criteria:
  - Clean artifacts and installation metadata contain no legacy application,
    Tk module, Tcl/Tk resource, or legacy console entry point.
  - README, install, usage, and release material describe the Qt application
    and no longer require two frontend releases to coexist.
- Validation:
  - Early offline build and artifact inspection may establish non-release
    preparation evidence. Run the source-isolated Qt install/launch smoke,
    static package-entry-point check, and pointed Markdown link tests only as
    part of the named M6 release checks after boundary and capability closure.

#### Frozen action-registration startup boundary

The experimental frozen Qt bundle uses one immutable ordered action-registrar
manifest as the common runtime and PyInstaller hidden-import authority. Startup
loads every registrar from that manifest and preflights all required
`menus.yaml` keys before constructing native menus. This makes source and
frozen action availability one testable contract; a manifest import,
registration, or required-key failure is typed and names its exact cause. The
boundary is preparation evidence only and does not establish a deliverable
bundle until the retained native build, inspection, smoke, and clean-install
gates succeed.

### Work package WP-G1a: Enforce the frontend composition boundary

- Owner: architecture integrator, with chemistry-backend engineer support.
- Touch points: `packages/bkchem-qt.app/bkchem_qt/bridge/`, session adapters,
  models, actions, modes, OASA public exports, and focused AST/import tests.
- Depends on: WP-C2 and WP-F1; add checks incrementally without hiding an
  unmigrated persistent path.
- Required behavior:
  - Name the allowed Qt-to-OASA entry points: the OASA CDML document session,
    public chemistry/render/import result APIs, and the Qt bridge/session
    adapter that converts their plain data into projections.
  - Reject Qt imports of legacy `bkchem` or `tkinter`, frontend inheritance
    from OASA chemistry classes, and direct private OASA graph access.
  - Reject PySide6 imports and Qt-valued request/result data in backend-facing
    modules. Any temporary exception is documented with removal owner and must
    reach zero before release.
- Success criteria:
  - Backend-facing interfaces exchange only backend-owned types and serialized
    document data; Qt projections remain disposable and rebuildable from a
    backend snapshot.
  - The static exception list is empty at M6 release closure.
- Validation:
  - Deterministic AST/import-boundary tests, a headless serialized-client test,
    and a projection-disposal/rebuild test.
- Completed bounded import-result retirement: file workers now deliver only
  immutable `PreparedCompleteCDML` or `None`; the obsolete graph-valued reader
  and relay conversion path are removed. AtomModel live-OASA ownership and
  renderer cleanup remain later WP-G1a slices; BondModel is now scalar-only.

- Independently accepted WP-G1a decoder boundary: synchronized hydration
  receives one frozen backend projection snapshot envelope containing all seven
  exact-revision observations and uses separately named hydrator/prepared-projection APIs. Both entry
  points require complete portable render coverage before they create a Qt
  document. The named compatibility CDML string/file decoders retain standalone
  raw parsing and rendering, while `DocumentSession` and snapshot rendering
  use only the synchronized route. Focused behavior verifies missing or
  cross-revision facts reject before replacement and compatibility fallbacks
  remain unavailable to synchronized staging and painting.

- Accepted WP-G1a paint seam: exact-revision molecule render observations
  carry portable primitive batches for synchronized atom/bond painting. The
  bounded implementation now uses source-order association, transient
  Qt-local drag transforms, closed primitive validation, and focused semantic
  tests. Independent acceptance also verified conservative Qt bounds,
  foreign/nested-lookalike exclusion, duplicate-ID inertness, exact-revision
  rejection, and the Qt-free OASA import boundary. Live OASA ownership inside
  AtomModel remains the next WP-G1a boundary; BondModel is now scalar-only.

- Independently accepted WP-G1a render-batch gate: synchronized detached
  projection now requires one and only one portable atom or bond batch for
  every hydrated core child, keyed by exact direct molecule/child source
  position and kind. Missing, duplicate, wrong-kind, foreign, and ambiguous
  coverage fails before live scene retirement or installation, so synchronized
  item painting cannot fall back to temporary OASA rendering. The named
  standalone compatibility load/render route remains available; broader
  renderer retirement is still separate work.

- Independently accepted: the bounded `MoleculeModel` topology slice
  replaces its retained OASA molecule and graph-object-keyed maps with ordered
  Qt atom/bond wrappers and endpoint relationships. Its connectivity and
  independent-cycle queries now operate on projection topology; the historical
  cycle-query name remains compatible without promising a canonical SSSR. OASA
  values materialize only in bridge conversion. Legacy bond painting borrows
  the current Qt endpoints for one synchronous compatibility calculation and
  releases them immediately, including after a rendering failure. AtomModel
  still retains its transitional OASA value; its cleanup and the legacy
  renderer retirement remain later WP-G1a work. BondModel is scalar-only.

- Independently accepted: the bounded BondModel scalar slice removes
  the retained OASA Bond from the Qt projection. Bond IDs, chemistry,
  endpoints, Haworth metadata, effective depiction values, and exact authored
  CDML-field presence are scalar Qt state. The bridge materializes a fresh
  OASA Bond only for one synchronous legacy rendering/export calculation and
  discards it afterwards. Exact-revision core hydration installs its record
  directly, preserving source-position association and ID eligibility.
  Focused acceptance covers public OASA-to-Qt-to-OASA depiction behavior,
  bounded legacy-render failure recovery, portable exact-revision rendering,
  retained durable-ID context-menu order/type commits across reprojection,
  backend properties commits, and the AST import boundary. AtomModel's
  transitional OASA atom remains the explicit next WP-G1a
  chemistry-observation prerequisite.

- Independently accepted: Qt-free exact-revision backend chemistry
  observations derive atom valency, implicit-hydrogen, atomic number,
  OASA-derived oxidation, molecular formula, average/monoisotopic mass, and
  elemental composition from complete direct molecule graphs using durable
  IDs. Chemistry Check and Oxidation Number consume atom facts; Chemistry Info
  consumes one ordered batch with per-molecule and combined facts. All leave
  history, dirty state, selection, and projection untouched. Plain backend
  display facts keep user-facing results independent of stale projection
  chemistry. AtomModel's later removal remains separate; BondModel is
  scalar-only.

- Independently accepted WP-G1a slice: AtomModel now stores
  only scalar identity, chemistry, coordinates, depiction presence, numbering,
  and backend binding facts. Numbering derives its next transient candidate
  from exact-revision molecule-core facts rather than Qt parsing snapshot CDML.
  The named bridge alone creates temporary OASA graphs for standalone export,
  painting, and compatibility chemistry; synchronized Chemistry Check and Oxidation
  remain exact-revision backend observations.
  The later aggregate acceptance records the remaining renderer/import
  composition evidence for this work package.

- Independently accepted WP-G1a renderer boundary: the bounded standalone
  renderer boundary now makes `AtomItem` and `BondItem` pure Qt consumers of
  either exact backend portable batches or opaque compatibility operations.
  `oasa_bridge` owns one-shot atom/bond materialization, per-endpoint clipping
  targets, and legacy bond context construction; `render_ops_painter` owns
  legacy paint dispatch and behavior-level bounds/text measurement. Focused
  endpoint-mask, styled/aromatic/wavy, atom-label/charge, raised-render
  recovery, portable-preview, and static import-boundary checks pass. This preserves the
  separately named standalone compatibility route and does not retire it.

- Independently accepted WP-G1a text-layout and codec-boundary cleanup: OASA exposes immutable,
  frontend-neutral legacy text-layout runs for the isolated compatibility
  painter. The Qt painter uses those public baseline/font-scale values while
  retaining Qt-local measurement and drawing; malformed legacy markup keeps
  its literal-text fallback. The format bridge now relies on the public codec
  lookup to initialize codecs. This bounded cleanup leaves synchronized
  portable painting unchanged. Independently accepted: the Haworth
  inactive-origin projection blocker exposes atom font sizes through
  molecule-core observations only as positive integers. Fractional,
  non-decimal, non-positive, and otherwise malformed compatibility values
  stay preserved source content with a display-only diagnostic. The later
  aggregate acceptance records the composition and projection-disposal
  evidence required to close WP-G1a.

- Independently accepted: synchronized molecule
  hydration leaves compatibility-only raw molecule XML unset. Public
  whole-root Copy/Cut continues to query the exact backend snapshot, and the
  backend now treats foreign molecule descendants as literal persistent content
  while translating only recognized CDML geometry during insertion. The
  separately named compatibility decoder remains the sole raw-XML producer
  for legacy-isolated clipboard/export handling; that builder rejects a
  synchronized molecule deterministically.

- Independently accepted WP-G1a aggregate closure: the backend now returns one
  immutable projection snapshot envelope containing the canonical CDML snapshot
  and all rendering observations from one document state. Qt sessions and
  snapshot rendering consume that envelope as a unit, so a same-revision
  snapshot cannot be combined with independently obtained observations. The
  envelope rejects missing, mistyped, and cross-revision facts before Qt model
  or scene construction. Focused headless authority, synchronized hydration,
  compatibility, and projection-disposal evidence passes; the static exception
  list is empty. WP-G1a is complete. M6 remains active for its separate
  authority-retirement, clean-install, and release gates.

### Work package WP-G1b: Record the Qt-only capability disposition

- Owner: release integrator.
- Touch points: `docs/active_plans/audits/BKCHEM_QT_ACTION_PARITY_2026-07-27.md`,
  this plan, Qt menus/actions, and focused capability tests.
- Depends on: WP-F0 and each WP-F0-required capability slice.
- Required behavior:
  - Verify the pre-M5 disposition: every visible Qt capability is either a
    required bounded slice, already supported but routed through the common
    candidate commit path, or deliberately unsupported/disabled and absent
    from release claims.
  - Use Tk only as behavioral evidence for a capability decision; never as a
    compatibility, packaging, or release-completeness requirement.
- Success criteria:
  - The active inventory has no unresolved partial/unsupported release claim;
    only the required slices block M6.
  - Every required persistent capability identifies its backend commit,
    revision/undo, and CDML round-trip coverage.
- Validation:
  - Independent inventory review and pointed action/session tests for each
    newly declared supported family.

### Work package WP-G1: Retire Qt document authority

- Owner: integrator.
- Touch points: Qt CDML serializer, raw merge, persistent DTO ownership,
  contracts, parity report, authority audit.
- Depends on: WP-F3 and every WP-F0-required slice.
- Acceptance criteria:
  - Qt cannot independently save a complete document.
  - No Qt model owns unknown XML, canonical object order, or persistent IDs.
- Evidence or review, when useful:
  - Static authority scan and independent multi-reviewer audit.
- Completed bounded evidence: OASA now publishes a revision-bound, Qt-free
  direct-root presentation description for supported drawable roots. Qt
  rebuilds synchronized presentation models from those values without raw
  presentation XML; snapshot rendering follows the same route. The bounded
  paper/header projection follow-on is also complete: an exact-revision OASA
  paper/layout observation supplies first direct-core paper/viewport facts and
  absent-paper defaults to live and detached projections, while synchronized
  Qt envelopes retain no root/header/paper/reaction/external-data XML. This
  retires paper/header/reaction retention only. Accepted fragment, direct
  atom-mark, group, and molecule-core observations now rebuild synchronized
  Qt state from one matching backend revision and remove their persistent XML
  from retained projection sources. The later WP-G1a aggregate acceptance
  closes the Qt composition and import-cleanup boundary around those disposable
  models.

- Obvious follow-ons:
  - Delete obsolete tests or recast them as projection tests.

### Work package WP-G2: Revalidate distribution and documentation

- Owner: integrator.
- Touch points: package artifacts, install/usage/architecture docs, changelog,
  active plans.
- Depends on: WP-G0, WP-G1, WP-G1a, and WP-G1b.
- Acceptance criteria:
  - Wheels contain the backend document module and Qt adapter.
  - A source-isolated installed smoke opens, projects, edits, saves, and
    reopens the arrow proof.
  - Documentation describes backend authority without Qt-envelope language.
  - Final M6 validation follows the pointed checks. Permanent evidence includes
    `packages/oasa/tests/test_cdml_document_authority.py`, backend operations,
    contract laws, deterministic plain Qt adapters, and Markdown links.
    Whole-window, worker, clipboard, screenshot, artifact, and isolated-install
    checks remain explicit one-time or E2E evidence.
- Independently accepted installed-wheel runner: the dedicated
  `tests/e2e/e2e_installed_qt_authoritative_roundtrip.py` starts one
  QApplication-owned deadline, verifies installed OASA and Qt origins, uses
  native Open plus the public Arrow operation and authoritative Save, closes
  and reopens the saved tab, and drains production QObject retirement. Its
  caller-owned paths must be fresh locations beneath repo `tmp/`; its atomic
  receipt truthfully records completion, timeout, Python exception, or
  semantic failure without environment contents or source-tree imports. The
  two-session stage exercises supported non-final tab retirement, and then the
  runner closes the remaining clean sole tab through `close_session_at(0)`, so
  it cannot mask that production close branch. Two fresh retained isolated-venv
  executions completed without a native crash. This is isolated-wheel evidence
  only; controlled PyInstaller build, inspection, smoke, and clean-install
  gates remain required for M6.
- Evidence or review, when useful:
  - Run that named list once after pointed development checks pass; it is not
    routine repository-wide pytest, a new giant fixture, a networked pytest,
    or an exhaustive compatibility matrix. Run crash-prone Qt lifecycle checks
    serially and stop for teardown investigation after a native crash.
- Obvious follow-ons:
  - Archive superseded plans after release closure.

## Acceptance criteria and gates

- Per-patch gate: one authority boundary, pointed tests, `git diff --check`,
  changelog entry, and independent review.
- Backend authority gate: backend-only complete-document round-trip preserves
  every persistent fingerprint without importing Qt.
- Atomicity gate: rejected commit leaves revision and canonical CDML unchanged.
- Projection gate: accepted response creates fresh Qt projections and no old
  persistent model identity survives as authority.
- No-re-merge gate: the backend response already contains opaque and
  nonmolecular content before Qt sees it.
- History gate: undo/redo restores immutable backend snapshot content into new
  revisions, not mutable Qt objects or a decremented revision counter.
- Lifecycle gate: repeated projection replacement and session close produce no
  native PySide6 crash.
- Composition gate: backend-facing requests and results contain only
  backend-owned plain data or CDML; no legacy import, Qt type, OASA private
  graph access, or frontend subclassing exception remains at release.
- Capability gate: WP-F0 and the active inventory give every visible Qt family
  a required, already-supported/common-route, or unsupported/disabled
  disposition; only required slices block M6.
- Release gate: no current code path can save a Qt-reconstructed complete CDML
  document independently of the backend.
- Qt-only delivery gate: release artifacts and current-user documentation name
  only `bkchem-qt`, with legacy source/fixtures retained solely as evidence.

## Test and verification strategy

- Put backend authority tests under
  `packages/oasa/tests/test_cdml_document_authority.py`.
- Use one inline mixed CDML document with prefix-qualified core nodes,
  molecule/group bonds, arrow, text, plus, bracket/vector, reaction, paper, and
  unknown namespaced content.
- Compare semantic persistent fingerprints: ordered local names, stable IDs,
  known references, and normalized opaque subtrees. Do not require byte
  identity or fixed collection sizes.
- Test rejected malformed and dangling-reference candidates against unchanged
  prior snapshot/revision.
- Test provisional `__bkchem_new__<token>` allocation, known-reference rewrite,
  rejection of dangling tokens, and absence of tokens from recognized stored
  positions while matching opaque XML remains unchanged.
- Test restore creates a new revision, restoring saved content is clean, redo
  can restore the immediate pre-restore revision, later restores replace that
  protection, normal edits clear it, and evicted nonprotected revisions reject
  cleanly.
- Permanently test Qt projection replacement with fresh wrapper identities and
  stable backend IDs. Verify selected-item restoration in the managed GUI
  walkthrough, where the real scene and native wrapper lifecycle are present.
- Use `QT_QPA_PLATFORM=offscreen` and `--kill-after 3` for pointed Qt tests.
- Keep pytest offline, under one second, free of sleeps and real subprocesses,
  with no more than two meaningful assertions per test.
- Stop after any native crash and inspect teardown before another Qt run.
- Use only the selected slice's existing pointed module or E2E command during
  development. The named M6 checks run once after those slices pass; they do
  not authorize routine repository-wide pytest, networked tests, giant shared
  fixtures, or exhaustive compatibility/version matrices.
- Run the multi-reviewer audit skill before release claims.

## Migration and compatibility policy

- Keep the current Qt codec only as transitional projection/candidate
  infrastructure until its backend replacement passes equivalent tests.
- Never patch a backend response with data from the old Qt projection.
- Preserve unknown CDML content in backend-owned opaque records.
- Keep legacy CDML fixtures and observed behavior from the deprecated Tk
  frontend as migration and regression evidence; Qt is the delivered frontend.
- Enable the backend-authoritative route by complete action families; do not
  mix backend revision history and graphics-owning persistent undo within one
  migrated family.
- Treat `26.07` as the implemented authored-current CDML profile and `26.02` as
  a compatible predecessor. OASA writer defaults, the retained legacy
  transformer registry, and focused authoring/preservation cases and tests are
  wired;
  the structurally no-op `26.02` -> `26.07` edge changes only root version.
  Complete-document loading preserves declared supported-old and unknown-future
  root values unless that transformer is explicitly invoked.

### In-progress CDML 26.07 completion package

The bounded format-completion package makes the established document grammar
precise without redesigning CDML. It is in progress and does not claim final
independent acceptance.

- [CDML_FORMAT_SPEC.md](../../CDML_FORMAT_SPEC.md) defines conservative
  authored grammar and compatibility preservation: existing drawing records,
  direct-child order, IDs, references, rich text, Haworth bond semantics, and
  authored geometry minima.
- The Qt-free conformance API, CLI, and semantic corpus live in
  `packages/oasa/oasa/cdml_conformance.py`, `tools/cdml_conformance.py`, and
  `docs/cdml_conformance/cdml_26_07_manifest.json`. They expose only `compat`
  and `authored-26.07`; transaction/session validity remains the backend
  contract rather than a conformance profile.
- The corpus tests semantic XML preservation, including opaque namespaces. It
  does not impose byte identity; exact bytes remain Recovery Export behavior.
- No new XSD belongs to this package. A later, separate experiment may propose
  one only after the corpus shows a structural diagnostic benefit that exceeds
  its maintenance cost.
- Bracket/vector containers, visual layers/pages/groups, a generic scene graph,
  JSON/browser replacement, and CML/CDXML migration remain outside 26.07.

## Risk register

| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| Hidden Qt authority survives | High | Qt merge/save can restore omitted content | WP-G1 | Static scan plus no-re-merge integration test |
| Opaque XML loss | High | Unknown subtree changes/disappears | WP-B1 | DOM-backed storage and semantic opaque fingerprint |
| Stale complete-document commit | High | Revision mismatch overwrites newer edit | WP-B2/WP-C1 | Expected revision and atomic rejection |
| Projection teardown crash | High | Invalid Shiboken wrapper during replacement | WP-C2 | Narrow disposal path and isolated offscreen lifecycle test |
| ID/reference corruption | High | Duplicate or dangling known reference | WP-B2 | Backend indexes and atomic validation |
| Slow whole-document commits | Medium | Measured UI latency exceeds acceptable interaction | WP-D1 | Measure after correctness; optimize without changing protocol |
| Mixed undo authorities | High | Qt command and backend history diverge | WP-F3 | One authority per migrated family; revision-only end state |
| Capability scope expands into parity | High | A visible partial feature becomes an unbounded release blocker | WP-F0 | Required/common-route/unsupported disposition before M5 |
| Changelog/plan overclaim | Medium | Docs call transitional path complete | WP-G2 | Evidence-backed wording and independent audit |

## Rollout and release checklist

- [x] Correct active contracts and record the settled decision.
- [x] Land the backend-only complete-document authority test.
- [x] Implement and independently review `CDMLDocumentSession`.
- [x] Route native Open through backend snapshots with atomic rollback.
- [x] Gate backend-snapshot Save on exact projection provenance while retaining
  an explicit transitional route for unmigrated Qt edits.
- [x] Route each release-selected persistent action family through its bounded
  backend request or complete candidate commit and canonical reprojection.
- [x] Pass the arrow commit/reproject/undo vertical slice.
- [x] Accept M4-0 generic request/outcome, history, mode lifetime, exact-tab
  non-mode capability, and Arrow integration; no new editor is accepted by it.
- [x] Complete selected M4 presentation, paper, and stacking routes.
- [x] Route drawing defaults, selected/all object overrides, and clean personal
  defaults through OASA observation, atomic history, and canonical reprojection.
  - [x] Accept the first bounded WP-E1 hypothesis: normal plain Text creation
    submits scalar intent to OASA, receives a backend-issued ID, and canonically
    reprojects without Qt-authored XML.
  - [x] Accept plain Text Configure for one durable direct root through a
    revision-bound explicit property patch, backend history, canonical
    reprojection, optional background, durable selection, and snapshot-only retry. Generic
    move and delete already cover durable Text.
  - [x] Accept the bounded Rich Text M0: OASA owns one direct-root Text's
    formatted CDML 26.07 run patch, canonical authored markup, atomic history,
    and preservation-only rejection for legacy/direct ftext markup and foreign
    ftext content. Qt now consumes supported runs as disposable cursor-format
    projections and supplies separate Object > Edit Rich Text with captured
    origin/revision/ID capability, one atomic backend patch, durable selection,
    typed stale/unavailable outcomes, and snapshot-only retry. Family, size,
    color, atom labels, legacy migration, and broader text grammar
    were retained as separate work at this checkpoint.
  - [x] Accept Rich Text root-font M1: the same atomic request now carries
    unique explicit family, size, and color intent while untouched root fields
    remain absent or unchanged. Qt captures visible root values before its
    dialog, applies only authored run styles in disposable projections, and
    inherits refreshed root family, size, and color. Noncanonical persisted
    colors remain visible but preservation-only. Inline fonts, root weight and
    style, atom labels, legacy migration, and broader text grammar
    remain separate work.
  - [x] Accept the second bounded WP-E1 hypothesis: normal Plus creation sends
    position intent to OASA, receives a backend-issued ID, and canonically
    reprojects. Plain direct-root Plus Configure patches child family plus root
    size/foreground/background through origin-bound history, durable selection,
    and snapshot-only retry. Retained child size/color never override the root;
    broader operations remain pending.
  - [x] Accept the third bounded WP-E1 hypothesis: normal Wavy creation sends
    endpoints to OASA; creation and Configure record backend history/dirty state,
    reproject, and use authoritative Save; the accepted evidence remains in
    [wavy_public_tests_final_acceptance_2026_07_28.md](../audits/wavy_public_tests_final_acceptance_2026_07_28.md).
    Arrow patches heads/spline/width/color through the same origin-bound family.
    Geometric roots share one width/stroke/fill operation with undo/reopen proof.
- [x] Migrate every release-selected chemistry and worker family.
- [x] Record the independently accepted WP-F0 capability dispositions before
  M5; close only the required RDKit, rendering, Haworth, PubChem, and
  import/export slices.
- [x] Replace release-selected persistent Qt undo ownership with backend
  revisions; the Qt action/stack adapter projects revision navigation.
- [x] Remove Qt full-document authority and raw re-merge from release paths.
- [x] Enforce the frontend composition boundary with no release exceptions.
- [x] Produce Qt-only package metadata and current-user documentation.
- [x] Complete the M6 source gate: authority, lifecycle, capability, and
  documentation checks pass with the accepted backend/Qt boundary.
- [x] Complete the M6 installed gate: clean dependency-isolated installation
  and installed authoritative round-trip pass.
- [x] Complete the M6 delivery/boundary gate: Qt-only package inspection plus
  direct lifecycle and native Qt LaunchServices smoke passes.
- [x] Run the fresh six-perspective M6 audit; pass the complete four-root aggregate,
  managed screenshots, controlled glyph alignment, and isolated-wheel
  authoritative round trips. Resolve its boundary findings through P0/P4.
- [x] Add the managed README screenshot PNG to version control so its retained
  Markdown reference is a release-valid asset.
- [x] Require independent app-owned receipts for direct lifecycle and native
  launch routes; keep signing, notarization, and DMG delivery out of scope.

## Documentation close-out requirements

- Active plan / progress tracker: keep milestone status in this document and
  leave the supersession warning in the prior completion plan.
- `docs/CHANGELOG.md`: distinguish the ownership decision, transitional
  adapters, implemented backend authority, and final retirement.
- Contracts: keep
  `CDML_BACKEND_TO_FRONTEND_CONTRACT.md`, `QT_CONTRACT.md`, and
  `HUMAN_GUIDANCE.md` synchronized.
- Architecture docs: refresh `docs/CODE_ARCHITECTURE.md` and
  `docs/FILE_STRUCTURE.md` after M3 stabilizes the real component names.
- Archive / closure notes: move superseded plans with `git mv` only after the
  repository permits index writes and the release gate closes.

## Patch plan and reporting format

- Patch 1: decision, corrected contracts, and first backend authority test.
- Patch 2: complete-document storage/preservation API.
- Patch 3: validation, revisions, atomic commit, and restore.
- Patch 4: Qt backend session plus projection replacement.
- Patch 5: arrow vertical slice and revision undo.
- Patch 6: frozen M4-0 seam plus selected presentation, paper, and
  presentation-stack hypotheses; preservation-only records remain unedited.
- Patch 7: chemistry/workers/history migration.
- Patch 8: Qt authority retirement, package proof, and documentation close-out.
- Each patch report states the authority boundary changed, pointed evidence,
  independent review, transitional paths still present, and next dependency.

## Resolved decisions

- Backend authority covers the complete persistent CDML document.
- Unknown persistent content is backend-owned opaque data.
- Complete-document CDML is the initial mutation protocol.
- Qt reprojects the backend response and never re-merges omitted content.
- Qt owns transient interaction state only.
- Backend revisions are the persistent undo/dirty source of truth.
- Snapshots are immutable; restore creates a new increasing revision with copied
  target content, and clean state uses canonical saved-baseline content.
- `__bkchem_new__<token>` is the only provisional correlation-token syntax.
  OASA, not Qt, allocates durable IDs and rewrites recognized declarations and
  known references.
- The arrow is the first vertical proof.

## Open questions and decisions needed

- Manager/subagent decision procedure:
  - Decision owner or dedicated class: backend implementer and independent
    reviewer.
  - Evidence and decision rule: choose internal DOM/index details that pass the
    preservation, atomicity, and performance gates; no option may weaken the
    settled ownership rule.
- Non-blocking follow-up: choose a bounded backend history capacity above the
  required minimum of three after measuring representative complete-document
  memory use. Evicted nonprotected revisions cannot be restored; current,
  exact saved, and immediate pre-restore revisions remain available when
  distinct.
