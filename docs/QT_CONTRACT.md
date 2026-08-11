# Qt ownership contract

This document is the PySide6 implementation contract for the frontend session
that consumes the behavioral boundary in
[CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md).
It separates stable session behavior from the current QObject implementation
mapping.

It does not define CDML grammar, authored-version requirements, schemas, or
validator conformance; see [CDML_FORMAT_SPEC.md](CDML_FORMAT_SPEC.md).

## Ownership

- The backend owns complete persistent CDML, chemistry semantics, durable IDs,
  canonical snapshots, revisions, and the saved-content baseline.
- Qt owns a tab's disposable projection, scene and item lifetimes, selection
  bridge, view state, gestures, dialogs, workers, and UI wiring.
- A Qt projection is never a persistence source. It is rebuilt only from an
  exact backend snapshot and never re-merges omitted XML or retained model
  state.
- During authoritative replacement, Qt requests the backend's revision-bound
  direct-root presentation description from its own document session. Snapshot
  rendering derives the same plain description and paper/layout observation
  from the exact snapshot it renders. The first direct-core paper/viewport
  attributes become plain `PaperModel` values; synchronized envelopes retain
  no root, header, paper, reaction, or external-data XML. Synchronized
  presentation models retain no presentation XML; records marked `display-only`
  remain renderable but expose no persistent frontend action address. Plain
  backend diagnostics drive unsupported-content warnings without giving Qt a
  preservation copy.
  Synchronized molecule projection also receives exact-revision plain fragment
  metadata and direct atom-mark observations. It hydrates ordinary fragment
  labels, display-only notices, normalized mark rendering facts, and mark
  deletion ordinals, then retains no direct `fragment` or atom-owned `mark`
  child XML, including foreign lookalikes, in a molecule source clone.
  Synchronized group labels consume the same-revision backend group facts and
  retain no group or incident group-bond XML; foreign, ambiguous, malformed,
  and richer groups remain display-only. Synchronized molecule/atom/bond
  projection consumes the same-revision backend core observation, retains no
  direct `atom` or `bond` source XML, and never turns an ID-less or ambiguous
  molecule/child into a persistent action address. A bond with duplicate or
  otherwise ambiguous atom endpoints is not hydrated.
  When both synchronized molecule-core and molecule-render observations are
  present, detached preparation requires exactly one portable batch for every
  hydrated atom or bond, matched by kind and direct molecule/child source
  position. Missing, duplicate, wrong-kind, foreign, or otherwise unassociated
  batches make preparation unavailable before Qt retires or installs a live
  scene. Therefore synchronized `AtomItem` and `BondItem` painting cannot
  reach the standalone OASA compatibility renderer; direct compatibility
  loading remains its explicit separate route. Each item consumes only the
  portable batch through `primitive_ops_painter`, or opaque standalone
  compatibility operations through `oasa_bridge` and `render_ops_painter`.
  The bridge alone materializes temporary OASA values and constructs legacy
  atom/bond depiction context; the painter alone dispatches and measures those
  legacy operation types. Qt items retain no OASA graph or operation-type
  dependency, while preserving their own QObject/QGraphicsItem lifetime and
  transient portable drag geometry.
- Qt creates provisional correlation tokens for candidates when needed, but it
  never allocates durable IDs. Backend acceptance consumes a token; Qt discards
  the accepted candidate and never resubmits that candidate or token.
- A compatibility projection may use private local linkage for an ID-less
  legacy atom or bond. Child-addressed mutations and durable child-selection
  restoration use only child IDs present in the authoritative backend snapshot.
  A root-only observation, such as Export SMILES, may resolve a selected
  ID-less child to its owning direct-root molecule when that molecule has a
  durable backend ID; the request contains that root ID only. An unavailable
  ID for the target addressed by an interaction makes that interaction inert.
- Chemistry Info is enabled only for one or more selected durable direct-root
  molecules in the current synchronized projection. Qt captures their ordered
  IDs and exact revision, then displays the backend's immutable per-molecule
  and combined formula, average and monoisotopic mass, elemental composition,
  and chemistry-graph counts in a selectable read-only dialog. It never derives
  chemistry from `AtomModel` symbols or reparses snapshot CDML; implicit
  hydrogens remain an OASA concern. No selection has an actionable prompt, and
  stale, unavailable, or unsupported observations have a recoverable warning.
  The action creates no command, revision, dirty transition, selection change,
  or reprojection.
- Chemistry Check and Oxidation Number capture one current synchronized
  revision and selected durable direct-root molecule IDs, then read one
  exact-revision backend atom-chemistry observation. They do not consult the
  transitional AtomModel chemistry carrier, create a command, alter dirty
  state, or reproject. Unavailable, stale, and display-only facts produce an
  explicit message. Oxidation values are labelled as OASA-derived
  electronegativity results rather than universal formal assignments.
- Expand Groups accepts one current plain implicit group with one exterior
  bond. Qt captures the group ID, owning molecule ID, and synchronized revision,
  then releases the group projection before submitting one backend transaction.
  The accepted snapshot replaces the projection and restores the backend-issued
  replacement atom selection. Other group types, zero or multiple attachments,
  rich target content, and legacy-isolated sessions are outside this operation's
  supported grammar.
- A direct-root persistent molecule-name edit captures one active synchronized
  session, its revision, one durable root ID, and the exact entered string.
  A changed authoritative result uses the accepted-snapshot, backend history,
  dirty-state, and reprojection path; an unchanged authoritative result is a
  successful no-op that preserves the live projection. Qt never changes a
  projection model name locally.
- Document Properties captures the registered synchronized session, immutable
  backend revision, OASA's raw first-direct-core-paper observation and
  backend-effective absent-paper defaults, plus OASA's plain paper catalog
  before opening its detached dialog. The dialog returns only
  explicit plain field intent; after acceptance Qt rechecks the captured
  session/view/scene/document aliases and submits an OASA paper patch. It
  never constructs a normalized `PaperModel`, a replacement paper XML node,
  or a complete-CDML candidate. An empty intent is an authoritative no-op and
  preserves raw compatibility attributes, absent fields, extensions, later
  paper records, and the live projection.
- Document Drawing Style captures the same exact active-session aliases and an
  OASA drawing-standard observation plus durable selected top-level keys. Its
  dialog owns only temporary controls, explicit changed scalars, scope, and the
  changed/all override-field choice. OASA atomically owns default inheritance,
  selected/all override materialization, validation, CDML mutation, dirty state,
  and revision history; the accepted snapshot replaces the Qt projection.
  Personal defaults are versioned plain application preferences. A valid saved
  value seeds a clean new backend document; it is never a second document store.

## Session-state model

The following are behavioral states of one live frontend document session.
Clean and dirty are orthogonal to synchronized projection: both describe the
same state with a different backend-content comparison. States below describe
persistent operations; view-only operations remain available only while their
referenced Qt objects exist. `DocumentSession` is the current implementation
name, recorded later only as a non-normative mapping.

| State | Entry condition | Permitted operations | Exit transition | Ordinary Save | Recovery Export | Close behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Synchronized projection | A current backend snapshot is installed as the live projection with matching provenance. The state is clean when current canonical content equals the saved baseline, otherwise dirty. | View and transient interaction; eligible complete-candidate commits; eligible backend navigation; exact-snapshot authoritative Save. | Accepted commit or restore begins reprojection; a Qt-local persistent mutation enters legacy-isolated; projection failure enters reprojection-required or projection-unavailable; disposal enters closed. | Eligible when provenance remains exact. Dirty sessions prompt before destructive replacement or close. | Eligible. It writes the exact current backend snapshot and changes no session or saved-baseline state. | Clean closes directly; dirty sessions offer Save, Discard, or Cancel. |
| Legacy/frontend-local isolated | A current Qt projection receives a persistent local mutation that has not become a backend commit. | Existing local UI and its local undo/redo route; discard confirmation. Backend commits, backend navigation, and authoritative Save are unavailable. | Confirmed discard performs exact current-backend reprojection and returns to synchronized; projection failure follows the reprojection states; disposal enters closed. | Not eligible. The user must use Recovery Export for exact backend-snapshot publication or discard the Qt-local edit. | Eligible. It writes the exact backend-owned snapshot and excludes, neither saves nor legitimizes, uncommitted Qt-local edits. | Close directly only when the backend snapshot is clean and no Qt-local edit is pending. Otherwise offer Recovery Export, Discard, or Cancel. Recovery Export preserves backend state only; it is never represented as saving Qt-local content. |
| Accepted but reprojection-required | The backend accepted a commit or restore, but Qt could not prepare the exact accepted/current snapshot. The previous live projection remains disposable display state, but is not synchronized. | Retry exact current-backend reprojection; reopen if available; normal close/discard decisions. No backend commit, backend navigation, or authoritative Save. | Successful exact retry reaches synchronized; repeated failure enters or remains projection-unavailable; disposal enters closed. | Not eligible. | Eligible. It writes the exact current backend snapshot and changes no session or saved-baseline state. | Close directly when the backend snapshot is clean. When it is dirty or unseen, offer Recovery Export, Discard, or Cancel; no retained projection state is a recovery source. |
| Projection unavailable | Retirement has begun and installation of the requested exact snapshot failed, leaving no live Qt document/projection. The backend session and exact current snapshot remain available. | Retry exact current-backend reprojection or reopen. No persistent action, ordinary Save, or reconstruction from retained Qt state is allowed. | A successful exact retry reaches synchronized; repeated failure remains projection-unavailable; disposal enters closed. | Not eligible. | Eligible. It writes the exact current backend snapshot and changes no session or saved-baseline state. | Close directly when the backend snapshot is clean. When it is dirty or unseen, offer Recovery Export, Discard, or Cancel without serializing or inferring state from Qt. |
| Disposed/closed | Tab removal or application shutdown has invalidated the session and started teardown. | None. Stale workers and callbacks must not deliver results or mutate Qt state. | Terminal. | Not eligible. | Not eligible. | Idempotent; no further prompt or operation is valid after disposal begins. |

### State invariants

- A synchronized dirty projection is still synchronized. Dirty means only that
  current canonical backend content differs from the saved canonical baseline.
- An accepted backend result is final even when projection fails. Qt discards
  the accepted candidate and its tokens; it retries only the exact current
  backend snapshot and never rolls back the backend to make an old projection
  usable.
- Exact reprojection reads the current backend snapshot. It may preserve
  selection through durable IDs, but it discards wrapper identities, hover,
  handles, previews, and locally retained persistent content.
- Ordinary authoritative Save writes the exact current snapshot and then marks
  that revision saved. It is unavailable outside synchronized provenance.
- Recovery Export is behaviorally distinct: it writes an exact backend
  snapshot and changes neither session state nor the saved baseline. The
  action is eligible for every live session with a backend snapshot, regardless
  of projection availability or synchronization.
- Visual artifact export captures one backend snapshot once. Page and content
  output remain eligible with a readable backend snapshot even when Qt
  reprojection is unavailable; Qt creates a disposable render projection only
  from that snapshot. Selected SVG additionally captures current interaction
  as durable IDs while a live projection exists. A missing selection bridge
  reports `selection-unavailable`; it never infers selection from old wrappers.
  Rendering failures and unsupported persistent visual coverage are explicit
  typed outcomes, and artifact export changes neither session state nor the
  saved baseline. Qt publishes a visual artifact only after the disposable
  render projection retires successfully. A retirement failure becomes a typed
  render failure with the coordinator or reaper diagnostic; a preceding render
  failure remains primary and records the cleanup diagnostic as extra detail.

## Persistent operation behavior

Native Open is backend-first. Qt validates and loads complete CDML into a
private backend session, prepares a detached projection from the canonical
snapshot, and installs the tab only after preparation succeeds. Same-tab
replacement rolls back the existing tab if late installation fails. Native
CDML is the ordinary save target; a non-CDML import remains pathless and dirty
until saved as native CDML.

For a backend-synchronized session, complete-CDML routes build a complete
candidate from the current backend snapshot, submit its expected revision, and
project only the accepted canonical response. Normal Arrow, creation-only plain
Text, creation-only Plus, creation-only Wavy, and plain root width/color Wavy
Configure are currently such routes.
Presentation-stack Bring to Front, Send to Back, and Swap on Stack are bounded
complete-candidate routes. Qt submits only a current revision, declared mode,
and durable IDs after every selected scene item proves to be the current
projection's exact binding for a supported, document-owned presentation root;
mixed chemistry, marks, handles, unsupported, ID-less, and foreign selections
are inert. The candidate reorders
only direct core-or-legacy presentation roots, preserves all other root records
and opaque content, and treats stale, invalid, or unchanged requests
atomically. Accepted changes use backend history and canonical reprojection;
Qt has no local object-stack command fallback.
The bounded structural Draw route is different: it submits one declared backend
operation with durable target IDs and scalar positions and bond settings, not a
frontend-built complete candidate.

Every frontend operation result carries a status, human-readable message, and
an optional plain failure kind. A rejected stale request reports
`revision-conflict`; rejected request-shape, target, and backend validation
failures report `validation`. Accepted, unchanged, unavailable, and projection
recovery results carry no failure kind. Frontend interaction code uses this
typed result to refresh the current backend projection rather than parsing an
error message or applying a local fallback.

MarkMode is a session client of the bounded `atom.mark.apply` operation.  Its
two public submode groups select one backend-supported mark type and explicit
`add` or `remove` action.  On a durable atom click, it captures the
session-owned revision and submits only that revision, the durable parent
molecule and atom IDs, action, and mark type.  The backend owns duplicate
child ordering, authored mark geometry, chemistry scalar changes, history, and
the accepted snapshot.  Qt restores selection only to the durable parent atom
after a changed accepted reprojection; ID-less targets and no-match removals
remain inert or accepted no-ops without local mark, undo, or projection state.

Synchronized projection obtains the matching exact-revision OASA atom-mark
observation with its presentation, paper, and fragment observations. Qt builds
marks only from normalized finite facts and plain deletion ordinals, then drops
all direct atom `mark` children from retained source clones. Standalone loading
continues to use the compatibility decoder and local undo behavior.

EditMode selected-mark Delete is a separate exact-selection route. It admits
only one current supported `MarkItem` bound to the current document with
durable parent molecule/atom IDs and a decoded same-type core-child ordinal.
It reduces that intent to plain values, releases its references to the selected
Qt wrappers, and submits a selector-bound `remove`; accepted replacement then
retires the old projection during canonical reprojection and restores the
parent atom selection through backend history. Foreign, retired, mixed,
ID-less, or ordinal-less synchronized selections are inert, and stale or
validation outcomes never fall through to Qt undo.

File > Document Properties captures one registered active session, its live
document, scene, view, backend revision, and the non-mode submission capability
before opening its detached dialog. After acceptance it rechecks that exact
session still owns the active aliases, then submits only dialog-owned paper
scalars. OASA's first-direct-core-paper patch changes only the supported
attributes and the accepted backend snapshot replaces the projection. A
canonical no-op does not replace the projection or create backend history.
Tab replacement, disposal, or loss of active ownership after dialog opening
makes the result unavailable; Qt never redirects it to another tab. Backend
undo restores paper state through the same canonical reprojection path.

Options > Document Drawing Style follows the same modal ownership rule. It
captures one synchronized session and revision, displays OASA's effective
defaults, and submits only changed plain values plus an explicit defaults,
selected, or all-object scope. Selected scope uses the durable top-level keys
captured before the dialog; changed/all chooses only which fields OASA
materializes as per-object overrides. Cancel and invalid input are inert. A tab
switch, disposal, or stale revision after the dialog opens cannot redirect the
request. Accepted backend history is the only document undo; the dialog and
the replaced Qt model never become a second standard owner. A separately
accepted personal-default choice writes versioned application settings only
after document acceptance. Present document defaults also author applicable
explicit values on later frontend presentation proposals.

The bounded Draw route covers four completed user gestures: releasing on blank
canvas creates a fresh bonded pair, extending from an existing atom adds its
bonded neighbor, joining two atoms in one molecule adds their bond, and using
the bond tool on an existing bond applies the selected bond settings. Qt
resolves hit targets to durable IDs and final scalar values, owns only an
ephemeral preview, retires and clears that preview before one submission, and
restores selection only from accepted result IDs after canonical reprojection.
Rejection is inert: the backend and current projection remain unchanged. An
accepted result remains final if projection fails; recovery may only reproject
the exact current backend snapshot.

Qt AtomMode and the active-view context-menu Set Element action submit the
same `atom.element.set` request for a different element on a clicked core atom.
Before submission, Qt resolves the clicked atom to durable molecule and atom
IDs and captures scalar source and replacement symbols. An accepted result
reprojects the authoritative backend snapshot and selects the replacement
through its durable atom ID. Same-symbol, inactive-view, and unaddressable
actions are inert, while a typed rejection retains the current snapshot and
projection. An accepted result remains final if projection fails: recovery uses
only an exact snapshot reprojection and never resubmits the earlier request.

The active-view context-menu Set Bond Order action submits one exact
`bond.order.set` request through the synchronized session. Qt captures only a
direct-root molecule durable ID, direct core bond durable ID, and order scalar;
it creates no property command and never mutates the projected bond model.
Matching order, inactive-view, and unaddressable interactions are inert.
Accepted changes use backend history and one canonical reprojection, restoring
the selected bond only through its durable ID. A projection failure leaves the
accepted backend result final; recovery reprojects the exact current snapshot
without resubmission. Draw-mode bond-tool cycling and type/property editing
remain separate action grammars.

The active-view context-menu Set Bond Type action submits one exact
`bond.type.set` request through the synchronized session. Each menu callback
captures only the direct-root molecule durable ID, direct core bond durable ID,
and ordinary type scalar from the shared bond-presentation choices; it never
retains a projected model or creates a local property command. The backend
decides matching and compatibility no-ops. Accepted changes use backend
history, canonical reprojection, and durable bond selection restoration. If
projection fails after acceptance, recovery reprojects only the accepted
current backend snapshot and never resubmits the earlier request. BondDialog
and PropertyDock type/property edits remain separate action grammars.

Bond Properties is one detached value-editor grammar across context Properties,
Object Configure, EditMode, and the PropertyDock order/type controls. The dialog
copies plain display values before it opens and returns only explicitly changed
plain fields. Before modal interaction, it freezes the owning registered
session, durable molecule/bond IDs, and snapshot revision. Its callback never
substitutes a later revision. PropertyDock performs that same capture per
control event rather than at dock binding. A stale result rejects atomically and
refreshes from authoritative projection without a local property command.
Accepted results use canonical reprojection and durable selection recovery; a
projection retry reuses only the accepted snapshot and never resubmits intent.

Atom Properties follows the same detached editor rule across context
Properties, Object Configure, EditMode, and the PropertyDock Symbol, Charge,
and Show Label controls. Each dialog freezes one direct-root molecule ID,
direct core atom ID, exact-session callback, and revision before it opens; each
dock event captures those values immediately before its own submission. The
callback submits that exact revision-bound `atom.properties.patch` with only
changed plain fields. A synchronized atom target that is unavailable, no longer
durable, or stale is inert after authoritative refresh; isolated documents keep
the established local undo fallback. Accepted synchronized edits use backend
history, canonical reprojection, durable atom selection restoration, and
snapshot-only retry.

Plain Text Configure is a synchronized-session-only detached editor for exactly
one selected current durable top-level Text. Before opening TextDialog, Qt
copies the current plain content, family, size, and color, then freezes the
originating registered session, revision, Text ID, and exact session-bound
capability. The dialog returns only immutable changed scalar fields, and the
callback submits that captured intent through `text.properties.patch`; tab
activation cannot redirect it, and disposal makes a retained capability typed
unavailable. Accepted changes use backend history, canonical reprojection, and
durable Text selection recovery. Projection retry uses only the exact accepted
snapshot and never submits the patch again. Qt owns the dialog and selection
interaction but creates no local Text property command.

Plain Plus Configure is a synchronized-session-only detached editor for exactly
one selected current durable top-level Plus. Its helper frame copies only the
visible root size and color, then freezes the originating session, revision,
Plus ID, exact capability, and immutable dialog changes. Every selected
PresentationObject and graphics wrapper leaves scope before submission and
canonical reprojection. The callback submits once through
`plus.properties.patch`; tab activation cannot redirect it, and session close
makes a retained capability typed unavailable. Accepted changes use backend
history, restore selection by durable Plus ID, and create no Qt undo command.
Projection recovery uses only the accepted current snapshot. A missing root
size projects as the historical value 14, while newly created Plus signs keep
their authored size 18. Family, background color, child-font semantics, rich
or ambiguous Plus records remain separate slices.

Plain Wavy Configure is a synchronized-session-only detached editor for exactly
one selected current durable top-level `<polyline style="wavy">`. Before opening
WavyDialog, Qt copies only visible plain root width and color, then freezes the
originating session, revision, Wavy ID, and exact capability. The dialog returns
only immutable changed scalar fields; all disposable projection wrappers leave
scope before its single `wavy.properties.patch` submission. Accepted changes use
backend history, canonical reprojection, and durable Wavy selection recovery,
with no Qt property command. Tab activation cannot redirect the callback;
origin disposal returns typed unavailability. Projection recovery reuses only
the accepted authoritative snapshot and never resubmits the candidate.

Atom Align submits only one exact `horizontal` or `vertical` axis and an
immutable tuple of durable `(molecule_id, atom_id)` pairs to a session-owned
adapter. The session captures its current backend snapshot and revision,
constructs the ordinary immutable persistent-operation request, and submits
it. The mode has no snapshot access or callback-owner introspection, and no Qt
object crosses this boundary. A selected non-atom is ignored; if any selected
atom lacks both durable IDs, the complete gesture is inert. Accepted changes
use backend history and canonical reprojection; Qt has no alignment undo owner.

Normalize Bond Angles, Normalize Rings, and Straighten Bonds are revision-bound
geometry-repair routes shared by the Repair menu and Repair-mode selection/click
interaction.
Qt captures only the originating synchronized session, its current backend
revision, durable direct-root molecule IDs, the declared
`normalize-bond-angles`, `normalize-rings`, or `straighten-bonds` kind, and a
finite positive scene spacing. It releases the clicked and selected projection
wrappers before submission; the accepted backend snapshot replaces the
disposable projection.
A changed result uses backend history, dirty state, undo/redo, and canonical
reprojection. A no-op leaves the installed projection and backend history
unchanged. An unavailable, ID-less, stale, invalid, or rejected route is
inert. If projection installation fails after acceptance, the result remains
final and retry reprojects only the exact current backend snapshot; Qt never
resubmits the prior repair intent or reconstructs it from old wrappers.
Normalize Rings accepts only a simple durable-ID ordered ring and uniquely
anchored acyclic substituents. Unsupported multi-cycle or ambiguous topology
reports the backend's typed failure without a Qt-local undo route.

EditMode arrow-key nudging submits one exact finite two-value scene-point delta
and an immutable tuple of selected durable `(molecule_id, atom_id)` pairs to a
session-owned atom-translation adapter. Selected non-atom presentation items
remain ignored. If any selected atom lacks either durable ID, or the synchronized
session adapter is unavailable, the whole gesture is inert with a bounded status
message. A changed result uses backend history and canonical reprojection and
restores selected atoms only by durable IDs; Qt creates no local nudge undo
command. An accepted result remains final when projection fails, and retry
reprojects only the exact current backend snapshot without resubmitting the
translation.

EditMode atom-only mouse dragging uses the same `atom.translate` grammar after
Qt has supplied its transient snapped and axis-locked preview. On release, the
mode captures immutable durable molecule/atom targets and one shared final
scene-point delta, restores every preview atom to its captured start geometry,
clears the drag's Qt wrappers, and submits exactly once through the originating
session callback. An accepted result is installed only by canonical
reprojection and backend history; no Qt move command is created. A missing
durable address, unequal selected-atom deltas, rejection, stale result, or
temporarily unavailable synchronized projection restores the preview and
creates no local command. Intentionally legacy-isolated documents retain the
existing local atom-drag undo route.

EditMode mixed atom/presentation mouse dragging uses one revision-bound
`selection.translate` operation. At press, Qt freezes the originating session,
its revision, and a session-owned callback after the current wrappers prove to
be direct-core durable atoms plus supported direct-root presentation records.
The scene provides only a shared snapped preview. At release, Qt resolves the
current selection again in document source order, requires one finite common
delta for every atom and presentation geometry, restores the preview, drops
the old wrappers, and submits exactly once. Accepted changes use backend
history and canonical reprojection with durable atom and presentation
selection recovery. An unavailable, foreign, ID-less, unsupported, reshaped,
unequal-delta, stale, or rejected synchronized drag is inert after preview
restoration. Intentionally legacy-isolated and standalone canvases retain one
local mixed move macro. Retry after an accepted projection failure reprojects
only the current backend snapshot and never resubmits the drag.

EditMode presentation-only mouse dragging uses revision-bound
`top-level.transform.apply` with mode `translate`. At press, the originating
session supplies and freezes its authority, exact backend revision, and
session-owned callback. The Qt scene supplies a transient snapped and
axis-locked preview only. At release, the mode proves each selected item is a
current supported durable presentation binding, derives one shared finite
scene-point delta, restores the preview, clears the old wrappers, and submits
only the frozen revision, durable presentation root IDs, and delta. An accepted
result uses backend history and canonical reprojection with durable selection
recovery; Qt creates no move command. An ID-less, foreign, unsupported,
reshaped, unequal-delta, unavailable, rejected, or stale gesture restores the
preview and creates no local command. An intentionally legacy-isolated session
retains the pre-existing local presentation move command. Recovery after an
accepted commit reprojects only the exact current backend snapshot and never
resubmits the earlier drag candidate.

Rotate is a bounded atom-only 2D persistent route. Qt captures durable selected
atom addresses, the finite scene-point center, and transient original geometry.
It accumulates normalized incremental `atan2` deltas for a stable sweep across
the `-pi`/`pi` boundary, restores its preview at release, then submits one
`atom.rotate` request through the originating session. Accepted state uses
backend history and canonical reprojection with durable selection recovery;
Qt creates no transform undo command. Missing durable identity, unavailable or
rejected authority, an exact zero sweep, cancellation, and presentation-only
selection are inert. Projection recovery reprojects only the accepted current
snapshot and never resubmits the earlier rotation candidate.

Top-level transform session support and the delivered Align/Object menu routes
use the backend-authoritative `top-level.transform.apply` grammar. Its plain
request carries an exact mode, revision, canonical mixed molecule/presentation
root keys, and only the mode's documented scalar intent: scale factors for
`scale` or a finite point delta for `translate`. The selection bridge resolves selected atom, bond,
group, and mark projections to their owning direct-root molecule and accepts
only registered current-projection roots: copied model metadata on a foreign
wrapper is not membership. The session also checks every frontend root category
against the exact authoritative snapshot before backend submission, rejecting
an entire incomplete, foreign, or category-mismatched selection. Changed
acceptance records backend history and replaces the projection before restoring
only durable direct-root keys; no-op, stale, and invalid requests are atomic
and create no Qt undo command. Align Top/Bottom/Left/Right/Center
horizontally/Center vertically map to `align-top`, `align-bottom`,
`align-left`, `align-right`, `align-center-x`, and `align-center-y`; Object
Scale and the two mirrors map to `scale`, `mirror-vertical`, and
`mirror-horizontal`. Scale captures session, revision, root keys, and its
exact capability before its modal dialog opens. After dialog acceptance it
submits only while the originating session remains registered, active, and
owns every app alias. A same-session intervening commit is submitted as stale;
tab change, replacement, or disposal is inert. The explicit `legacy_isolated`
state alone retains the existing Qt-local transform undo path. If installation
fails after acceptance, retry projects only the exact current snapshot.

Rectangular Bracket creates exactly two top-level `polyline` records through
one immutable `bracket.add` request carrying normalized finite bounds. Qt owns
only its selected-atom union or transient drag preview; the session builds the
complete candidate, and accepted pairs use backend history and canonical
reprojection without a Qt undo macro. Restored selection contains only the
previously selected durable atoms, never the new polylines.

Number and Clear Numbers each submit one revision-bound atom-number intent for
one direct core atom. Before submission, Qt captures only durable molecule and
atom IDs plus scalar number and visibility intent from a synchronized
projection. Assignment or replacement sends a positive integer and explicit
visibility; Clear sends the exact `(null, null)` pair. Clear on an unnumbered
atom is an interaction no-op. Qt has no persistent local number mutation or
undo owner for either gesture. Its next displayed candidate is transient
presentation state derived after every outcome or reprojection from the current
exact-revision molecule-core observation, including hidden values. Qt does not
reparse snapshot CDML; nested, opaque, and foreign lookalikes do not participate.
The backend does not supply an allocator. Accepted edits use the existing
backend history,
dirty-state, undo/redo, Save, and Recovery Export rules. A typed rejection
leaves the current snapshot and projection unchanged. An accepted result
remains final if projection fails: recovery reprojects only the exact current
backend snapshot and never resubmits the earlier intent. Wavy behavior remains
outside this bounded operation.

For template placement, TemplateMode submits one exact selected system-template
name and finite scene anchor to its named session action. The session captures
the current revision and creates the `template.insert` intent. Catalog names
enter through the session boundary; no
frontend-owned catalog fallback participates in the persistent operation. A
blank click anchors one separate root molecule at the click, while an atom
click uses the projected atom item's scene position to anchor the same
detached result at the atom coordinate without
attaching, fusing, editing, or bonding to the source molecule. The backend
resolves the name, prepares the geometry, and commits the canonical document
atomically. After reprojection, the frontend restores selection only by mapping
the accepted inserted-root provisional identifier to its backend-issued durable
ID. A missing, dangling, or wrong-kind result correlation reports
`selection-unavailable` and clears that selection rather than reusing a prior
projection object. An accepted result remains final if projection fails;
exact-snapshot retry retains a valid durable selection correlation and never
resubmits the earlier intent. Template attachment, fusion, markers, and
non-system catalogs remain separate capabilities.

Biomolecule placement follows the same session-owned transaction shape through
`biotemplate.insert`. The Qt mode receives immutable OASA catalog descriptors,
retains only the selected catalog key, and submits that key with the current
revision and finite scene anchor. Category and label rendering are frontend
projection concerns. The backend prepares and commits one detached molecule
through the ordinary insertion route; atom clicks supply coordinates only and
never attach or fuse a source molecule. Rejected or unavailable synchronized
requests leave Qt scene state unchanged, while projection recovery uses the
accepted snapshot without resubmitting the consumed placement.

User-template catalog delivery is a frontend-owned, Qt-free filesystem boundary:
one explicitly configured directory is scanned nonrecursively into an immutable
snapshot of opaque filename-derived keys, labels, and exact accepted CDML text.
The catalog calls OASA only through its pure inspection bridge, reports plain
per-source scan failures without preventing neighboring entries, and never
retains paths or file handles for later insertion. Each explicit rescan replaces
the disposable catalog snapshot; directory creation, selection, dialogs, and
session insertion remain separate Qt wiring.

MainWindow owns the configured directory, scan cadence, status presentation,
and the active-mode ribbon refresh. It scans before constructing the initial
session, passes the same immutable entry tuple to every later New, Open,
same-tab replacement, and import session, and replaces every live session's
catalog on an explicit rescan. Programmatic rescans remain nonmodal and report
a concise status summary; File > Refresh User Templates additionally presents
every typed skipped filename/reason while retaining every admitted neighbor.
The application bootstrap explicitly supplies `~/.bkchem/templates` for the
product window; a window constructed without a directory owns an empty catalog
and disables catalog refresh and Save As Template.

Save As Template first captures and admits the active exact backend snapshot.
Only after admission does MainWindow create its configured directory and open
the native dialog. A target without a suffix gains `.cdml`; every supplied
suffix must be exactly lowercase `.cdml`, and the resulting target must be a
direct child of that directory. After the dialog returns, the originating session must still be the
active registered recovery-export session, and its unchanged current snapshot
is admitted again before exact snapshot publication. A successful publication
does not alter session revision, history, dirty state, or saved baseline, then
explicitly rescans every live session. Recovery Export remains the general
arbitrary-path exact-snapshot workflow.

UserTemplateMode is the corresponding frontend-only gesture client. It receives
only an immutable tuple of plain catalog descriptors, retains only unique
nonblank opaque keys and nonblank labels, and renders the YAML-declared single
Template group. An explicit empty catalog remains an inert empty state. A
catalog replacement retains its selected key when present, otherwise selects
the first deterministic key or no key. Clicks submit only the selected key and
a finite scene-point anchor through the mode's session-owned callback; they
never read catalog paths or CDML, inspect template payloads, import OASA, or
attach/fuse with scene content. The owner explicitly rebuilds an active ribbon
after catalog replacement; the mode does not reach into MainWindow or ribbons.

Each DocumentSession receives a copied immutable catalog snapshot and owns its
private opaque-key-to-exact-CDML delivery mapping. `user-template.insert`
contains only the expected backend revision, a catalog key, and a finite anchor;
it has no durable target keys. The session rejects stale revisions before key
resolution, resolves the key only from its own frozen mapping, and passes the
exact saved CDML and label to OASA's dedicated atomic insertion transaction.
Replacing a session catalog updates only that session's mode descriptors and
mapping, retaining a surviving selected key without changing backend revision,
history, dirty state, or projection. Accepted placement records backend history
before disposable projection delivery. A projection failure leaves the accepted
snapshot final, and retry reads only that snapshot; it never reuses a catalog
entry or resubmits the consumed placement. Session teardown clears the mode's
action capability, so a retained callback reports typed unavailability.

Standalone Text creation, direct-root move, direct-root delete, and plain
Configure are backend-authoritative. Creation uses the complete-candidate
route; move and delete use the generic durable-root operations; Configure uses
the bounded plain property patch above. Object > Edit Rich Text is a separate
authored-run operation: it captures one origin session, revision, durable Text
ID, immutable runs, visible root font values, and callback before its modal
dialog, then submits one `text.rich.patch`. Its frontend-only dialog permits
bold, italic, subscript, superscript, and explicit root family, size, and color
changes; an untouched dialog sends no root changes. A supported Text projection
applies root font and color before inserting authored-only `QTextCharFormat`
runs through `QTextCursor`. Legacy/direct-child ftext markup, comments, processing
instructions, and foreign content retain backend raw XML, render recursive
character data through plain text, and leave rich editing unavailable. Accepted
reprojection restores durable selection from the backend snapshot; unavailable
and stale outcomes are typed, and retry never resubmits the accepted patch.
Plus root size/color Configure and Wavy root width/color Configure are
backend-authoritative through their bounded plain patches. Plus family,
background color, child-font semantics, rich Plus, and other presentation
operation families retain their current transitional limits.

Normalize Bond Lengths, Normalize Bond Angles, Clean Geometry, and Snap to Hex
Grid are backend-authoritative Repair routes. Qt captures the live session,
resolves only durable selected direct-root molecule IDs, and submits the
captured revision, repair kind, and finite-positive plain `target_spacing_pt`
value. The accepted backend snapshot replaces the disposable projection, and
Qt restores the durable molecule selection from that fresh projection. Bond
length, angle-slot, layout, centroid, hex-lattice, coordinate-patching, and
atomic target-validation semantics remain backend behavior. A changed repair
uses backend history for undo and redo, dirty state, canonical reprojection,
and authoritative Save; a canonical no-op creates neither a Qt undo command
nor a backend history entry. Once accepted, a result remains final if
projection replacement fails: recovery performs only exact-snapshot
reprojection of the current backend snapshot and never resubmits or locally
reconstructs the repair. Canvas drag snapping remains transient interaction
preview behavior, separate from the persistent Snap to Hex Grid Repair action.
Normalize Rings uses the same backend-authoritative route for its documented
simple-ring subset. Fused, bridged, spiro, multiple-cycle, and ambiguous ring
topologies return a typed atomic failure; Qt does not create a local repair or
local undo fallback for an unsupported topology.

Partial structural Copy is a read-only backend-authoritative clipboard route.
For an exact current selection of durable direct atoms and bonds from one
eligible molecule, Qt captures only the origin revision and source-ordered
plain molecule, atom, and bond IDs. It then releases projection wrappers,
asks OASA to extract the revision-bound fragment, and publishes that returned
CDML. Selected bonds include their endpoint atoms in the copied fragment. Copy
does not change backend history, dirty state, Qt undo, or the projection. A
foreign, stale, ID-less, malformed, or disconnected structural selection is
unavailable and preserves the existing clipboard; it never falls back to a
whole molecule. Legitimate presentation-root, whole-root, mixed, and
multi-molecule structural selections retain the existing top-level clipboard
route. Native clipboard publication is a callback boundary: no origin session
or wrapper is observed after it begins, so a callback may activate another tab
or close the origin.

Synchronized whole-root Copy follows the same read-only ownership rule. Qt
uses one narrow projection frame only to resolve canonical durable direct-root
IDs and the exact backend revision. It releases projection wrappers, requests
the detached source-ordered fragment from OASA, then publishes only the returned
CDML. Synchronized whole-root Cut freezes its origin-bound delete capability
and request before the same query and publication path. Clipboard publication
may activate another tab or mutate the origin; it cannot redirect the captured
capability, and a changed source revision rejects the frozen delete. A failed
query or publication leaves authoritative state unchanged. Neither synchronized
whole-root route asks `ClipboardManager` to inspect retained Qt XML.

Mixed top-level Paste is a backend-authoritative persistent operation. Qt reads
raw CDML from the clipboard, captures one live target session, and rechecks
that same session before submission. The backend validates the fragment,
allocates fresh durable IDs, rewrites fragment-local references, applies the
scene-point translation, and atomically returns the canonical snapshot. Qt
records accepted history before projection and projects only that snapshot. An
accepted Paste remains final if projection fails: recovery retries exact current
snapshot reprojection and never resubmits the clipboard candidate. Paste is
available only when both usable clipboard CDML and the captured session's
persistent-operation capability are present. Copy remains a Qt clipboard
adapter with no persistent mutation.

Whole-root Cut is a backend-authoritative persistent operation. Qt resolves
the active projection's selected atom, bond, or mark to its owning direct-root
molecule and accepts direct supported presentation roots in canonical document
order. It retains only immutable root kind/ID data, publishes the complete
selected CDML fragment first, then submits one revision-bound `top-level.delete`
request labelled Cut through the captured session capability. The capability
stays bound to the originating registered session if a clipboard callback
activates another tab. Missing, stale, ID-less, foreign, unsupported, rejected,
or temporarily unavailable synchronized targets leave backend state and Qt
undo history unchanged; the already published clipboard fragment remains the
intentional external side effect. The synchronized request freezes its expected
revision before clipboard publication, so a callback commit is rejected as
stale rather than deleting from the changed snapshot; a callback transition to
legacy isolation is unavailable and never selects a Qt-local fallback.
Acceptance uses backend history and canonical reprojection, and its recovery
retries only the current accepted snapshot. A Cut that starts intentionally
legacy-isolated retains local undo only after publication confirms the same
active registered projection, persistent generation, and canonical selection.
Partial structural Cut is separately bounded. For an exact current selection
of durable direct atoms and bonds from one eligible molecule, Qt freezes the
origin session, revision, explicit deletion IDs, and session capability, asks
OASA for a read-only connected fragment with bond-endpoint closure, then
publishes that raw fragment before submitting the original `structure.delete`.
Closure atoms make the clipboard valid but are not implicit deletion targets.
Clipboard failure leaves the document unchanged; a callback revision change
makes the frozen delete stale while retaining the useful clipboard data. Mixed,
mark, foreign, ID-less, multi-molecule, opaque, and disconnected structural
selections are unavailable and never fall back to root or local Cut. Every
selected wrapper must first prove membership in the current disposable
projection before Qt reads its atom or bond model. OASA proves the raw fragment
through the same complete Paste preparation and acceptance route on a detached
clone; that proof never rewrites the published source-order fragment. Partial
Copy uses the separate read-only structural route above.

Whole-root Delete proves a complete current selection of supported durable
direct roots before it selects an authority. A synchronized session supplies
one captured revision and accepts the backend request with immutable root IDs,
records backend history, and replaces the projection from the returned
snapshot. A legacy-isolated or standalone session follows the existing local
Remove-command undo route. An unavailable synchronized session is inert and
does not convert the gesture into a local mutation.

Partial atom/bond Delete has a separate bounded authority route. After
complete-root eligibility fails, Qt accepts only an exact current-projection
selection of durable atoms and bonds from one direct-root molecule. It
canonicalizes atom and bond IDs in molecule source order, releases the
disposable wrappers, and submits one captured revision plus immutable molecule,
atom, and bond IDs through `structure.delete`. Accepted state records backend
history before canonical reprojection, clears the deleted selection by default,
and creates no Qt undo command. A stale or validation rejection is final. An
accepted projection failure also remains final: retry projects exactly the
current backend snapshot and never resubmits the deletion intent.

A synchronized ID-less, foreign, retired, duplicate, multi-molecule, mark,
presentation, mixed atom/presentation, unsupported, or temporarily unavailable
partial structural Delete is inert and never falls through to local mutation.
An exact eligible selected mark instead uses the dedicated selected-mark route
above. An inactive session-owned context-menu origin is likewise inert. An
intentionally legacy-isolated session or genuinely standalone canvas retains
the existing local Remove-command undo route. Partial Cut, multi-molecule
structural deletion, and molecule grammars outside the bounded backend
operation remain separate capabilities.

Context menus are transient frontend projections. A synchronized atom or bond
menu freezes only its originating session plus durable molecule/object IDs and
plain requested values; its Properties and Set Element callbacks resolve the
current model from that session's current document only when the action is
triggered. A same-tab canonical reprojection therefore cannot leave the menu
holding a retired AtomModel or BondModel. If the originating session is no
longer active, live, and current, the action is inert rather than redirecting
to another tab or a local mutation. Explicitly legacy-isolated and standalone
menus use the local route and perform the same late durable lookup where it is
available. Delete and bond order/type callbacks likewise retain only their
plain session-bound request data across the popup event loop.

Backend undo/redo restores backend revisions and then performs canonical
reprojection. Qt keeps navigation intent, not persistent graphics ownership,
for the backend-supported route. Local persistent actions use local history
only while legacy-isolated; confirmed discard followed by exact reprojection is
required before backend Save or backend navigation resumes.

## Save and publication behavior

Authoritative Save requires all of the following:

- a live document, scene, view, and projection coordinator;
- a projection installed from the exact current backend snapshot;
- matching backend and Qt dirty state; and
- no later local persistent mutation.

It publishes the exact immutable backend snapshot with same-directory atomic
replacement, then calls the backend saved-baseline operation. A failure before
target replacement leaves both target and baseline unchanged. A failure after
replacement but before baseline marking is reported as a partial external
result: the target may contain canonical CDML while the backend remains dirty.
After publication and baseline marking succeed, title, recent-file, and status
bookkeeping cannot recast the Save as failed.

No Qt projection serializer is a complete-document publication route. A
Save-ineligible session must use Recovery Export for exact backend-snapshot
publication or discard its Qt-local edit before authoritative Save resumes.
Qt may construct only bounded selected-object proposal fragments for backend
operations such as Paste. Those fragments never include complete document
headers, paper state, or unrelated persistent records, and they cannot publish
or establish a saved baseline.

## Fragment metadata behavior

Create Fragment captures one synchronized session, revision, molecule ID, and
ordered durable atom/bond IDs before its dialogs open. Its dialog returns only
plain name and type values; the captured capability submits one
`fragment.create` request to the backend. View Fragments observes the current
projection and captures the session, revision, molecule ID, and selected
fragment ID before deletion. The captured capability submits one
`fragment.delete` request. Accepted fragment snapshots reproject normally;
fragment metadata has no graphics projection and does not own Qt undo state.
An unavailable captured session produces a typed inert outcome. Rich imported
fragment records and backend-generated linear forms are plain read-only notices;
Qt retains no synchronized fragment XML, properties, or unknown child XML.
Standalone compatibility loading keeps its local legacy retention behavior.
Convert to Linear
Form captures one origin session/revision plus source-ordered durable atom IDs
(expanding selected bonds to endpoints), releases projection wrappers, and
submits one `linear-form.convert` request. OASA owns path order, fixed 10-point
geometry, hydrogen display, generated metadata, history, and reprojection.

## QObject lifetime and thread affinity

`DocumentSession` owns one tab's backend handle, `Document`, scene, view, mode
manager, request generation, and worker set. `MainWindow` owns session
registration, active-session aliases, global actions, and orderly tab removal.
Active-only signal connections are disconnected before a switch, replacement,
or close, then rebound after the replacement aliases and property dock are
valid. Inactive sessions retain only their own title and model-to-item links.

All Qt object construction and projection installation run on the GUI thread.
Workers perform pure backend preparation only. A worker result may act only
when its originating session is live and its request token is current. Newer
requests, replacement, tab close, and application shutdown invalidate prior
tokens; stale result and error callbacks neither construct Qt models nor show
dialogs.

Synchronized CDML hydration has one backend-owned input: a frozen projection
snapshot envelope containing one canonical snapshot plus presentation, paper,
fragment, atom-mark, group, molecule-core, and molecule-render facts from
that exact backend state. Qt consumes the complete backend result as a unit;
it never combines separately obtained observations with a snapshot. The
envelope rejects a missing, mistyped, or cross-revision fact before constructing
a Qt document, graphics item, or scene. The named
synchronized hydrator and prepared-projection route may inspect the exact CDML
snapshot only to associate positions and frontend-neutral diagnostics; they do
not decode a missing molecule through OASA, parse raw presentation content, or
invoke compatibility item rendering. `DocumentSession` staging/retry and
snapshot rendering use only that route. Explicit compatibility CDML string and
file decoders retain standalone raw molecule conversion, source XML,
presentation parsing, optional coordinate scaling, and local rendering; their
legacy aliases accept no synchronized observations.
Both synchronized entry points require complete portable render coverage before
they produce a Qt document, so native staging cannot defer a compatibility
renderer fallback until graphics-item construction.

Worker retirement is a frontend-only signal and ownership contract. A worker
progresses from `running` to `delivery-invalidated` when its request token is
invalidated and `requestInterruption()` is made, then to `retiring` when its
opaque callable returns, and finally to `finished` through `QThread.finished`.
The terminal delivery outcomes are `completed`, `failed`, and
`delivery-cancelled`. `delivery-cancelled` suppresses result and error
delivery; it does not claim that OASA, RDKit, or transport work was preempted.
The session-wide import token intentionally means a newer asynchronous import
supersedes delivery from every earlier asynchronous import family in that
session. Family-scoped tokens are a separate product decision.

Tab close and same-tab replacement invalidate tokens and transfer every live
worker plus its GUI-thread relay to MainWindow's retirement ownership. The
disposed session may therefore return through ordinary event processing while
native work completes. MainWindow keeps each worker and relay strongly owned
until its queued `finished` slot releases it exactly once. No stale result,
error, projection, mutation, or dialog delivery is permitted after that fence.

Application shutdown first obtains all Save, Recovery Export, or Discard
approvals. It then enters `draining`, invalidates and adopts every live
worker, and retains the QApplication, MainWindow, and relays until all workers
have emitted `finished`, after which MainWindow is `ready` to complete session
and window deletion. When a programmatic `QApplication.quit()` has already
returned from its outer loop, a nested Qt event-loop drain preserves queued
completion delivery. Graceful shutdown duration is the remaining native work;
force termination is outside this contract. Clean Geometry is synchronous by
current implementation choice; any asynchronous redesign requires separate
performance evidence.

Before native QObject destruction, disposal disconnects model/item callbacks,
including callbacks retained by undo commands, while Python wrappers are still
valid. One Qt-side graphics-retirement coordinator receives either a known-live
scene or explicit detached roots: the live scene clears its own remaining
contents once, while detached trees are released child-before-parent. The
coordinator checks native wrapper validity at that boundary and does not infer
ownership from an item after retirement may have begun. It then clears undo
ownership and QObject parent links in a controlled order. Session teardown
advances monotonically from callback detachment through scene retirement to
queued QObject roots; Python wrapper references are released only after those
roots are queued. Session roots are retained until Qt emits `destroyed`,
avoiding unsafe parent-cascade destruction through stale Shiboken wrappers.
If explicit retirement of an already-detached root reports a native failure,
the coordinator transfers that root and its diagnostic to a session record
before the transition-local coordinator is released. The MainWindow reaper
then retains that record through its controlled terminal-resolution pass. That
pass releases an already-invalid wrapper without another native call, and
otherwise checks validity immediately before the coordinator's explicit native
deletion boundary. A record remains retained when that boundary reports a
further failure. This teardown is idempotent. The native-wrapper boundary
treats Qt's ordinary ``None`` parent result as a terminal traversal outcome,
not as a valid wrapper; selection queries likewise return no items from an
invalid scene before making a native call.

Temporary export projections follow the same frontend-only ownership behavior:
their known scene roots and explicitly detached construction roots retire
child-before-parent through the coordinator, then a temporary-scene reaper
retains the scene and any failed detached root until ordinary Qt deferred-delete
delivery confirms resolution. Export output does not depend on that disposable
projection after painter completion. This graceful path requires a live Qt
event loop and makes no claim about external termination or interpreter
finalization.

Application termination uses that same ordered boundary even when the Qt event
loop ends programmatically without delivering a window-close event. After an
event-loop return, the application asks the MainWindow to obtain the ordinary
Save, Discard, or Cancel decisions and, once approved, retires every live
session through its coordinator and reaper before returning to Python. Cancel
keeps the window live and resumes its event loop. External force termination,
native aborts, and interpreter finalization remain outside this graceful
shutdown contract.

A controlled frozen-app smoke may request a caller-owned completion receipt.
The receipt contains only the fixed schema and zero exit code, and is written
atomically only after QApplication and MainWindow initialization, normal timer
event-loop exit, and this controlled retirement boundary all succeed. It is
not written for a failed lifecycle result and it does not conceal a later
native-process diagnostic. The macOS builder validates two independent launch
routes. Direct execution uses the offscreen Qt platform and evaluates process
status, app-owned receipt, and captured fatal diagnostics. Native execution
uses `/usr/bin/open -n -W`, removes any inherited offscreen override, and
requires its own app-owned receipt. A pass proves local LaunchServices startup,
normal event-loop exit, and retirement; it does not claim signing,
notarization, persistent Finder registration, or DMG delivery.

## Close and replacement

New creates an independent tab without prompting about the old tab. Same-tab
Open, tab close, and application close do not leave any live session unable to
close. A synchronized clean session closes directly; a synchronized dirty
session offers Save, Discard, or Cancel. Where authoritative Save is
ineligible, a clean backend snapshot may close directly. A dirty or unseen
backend snapshot instead offers Recovery Export, Discard, or Cancel.

Legacy-isolated close separately considers pending Qt-local content. If either
the backend snapshot is dirty or unseen, or Qt-local edits are pending, its
prompt offers Recovery Export, Discard, or Cancel. Recovery Export writes only
the exact backend snapshot; it does not save, include, or legitimize Qt-local
edits. Each selected publication path authorizes the destructive step only
after its required write succeeds;
cancellation or write failure stops the operation. Application close obtains
each approval before disposing any tab.

Replacement and close detach active-only signals, remove and reparent the tab
page, invalidate requests, transfer workers to MainWindow retirement, dispose
live and undo-retained graphics callbacks, clear the undo stack and scene, then
queue detached roots for deletion. This sequence is required because Python
garbage collection is not a safe replacement for QObject and graphics callback
teardown.

## Current implementation mapping

This section is descriptive and non-normative. It records the current PySide6
mapping, not required type names for another compliant frontend.

- `bkchem_qt.models.document_session.DocumentSession` tracks synchronization,
  local isolation, projection errors, the current projected snapshot, and the
  backend-navigation witness.
- `can_write_authoritative_snapshot` is the current total provenance predicate.
  `write_backend_snapshot()` is ordinary authoritative Save: it publishes then
  calls `mark_saved`; it is not Recovery Export.
- `can_recovery_export` and `export_backend_snapshot()` are the current
  projection-independent Recovery Export adapter. `MainWindow` exposes the one
  `file.recovery_export` action and uses document-free close facts for
  Save-ineligible sessions; the close-choice method is replaceable in focused
  tests so it does not require a real modal event loop.
- `bkchem_qt.models.projection_lifecycle` contains the dependency-light
  projection result values and session-bound delivery port. The port binds one
  delivery generation to one live `DocumentSession` through its public
  ownership query rather than session-private state. It returns closed typed
  `installed`, `preparation-unavailable`, `installation-failed`, or
  `session-unavailable` results with their terminal replacement phase; stale
  delivery returns before notice delivery and cannot update another tab.
  `MainWindow` consumes those notices only for the emitting active session and
  owns aliases, signal wiring, and the property dock rather than session state.
- `replace_projection_from_backend_snapshot()` prepares only the requested
  current backend snapshot before retiring the old projection. Preparation
  failure preserves a retained display only as unusable and never as a recovery
  source; installation failure after retirement leaves no projection. Retry
  prepares only the exact current backend snapshot and never resubmits an
  accepted intent.
- `MainWindow` implements backend-first Open, guarded Save, user confirmation,
  active-session signal wiring, and deterministic delayed teardown.
- `PreparedNativeCDML`, `PersistentActionOutcome`, and request tokens are
  current implementation values. They do not cross the backend boundary.
- `PresentationObject.formatted_text_runs` and `display_text` are disposable
  frontend projection values. The former contains only supported immutable
  plain runs; the latter is safe character data even for preservation-only
  ftext. Neither is a persistent owner or a recovery source.
