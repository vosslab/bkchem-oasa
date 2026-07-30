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

## Session-state model

The following are behavioral states of one live `DocumentSession`. Clean and
dirty are orthogonal to synchronized projection: both describe the same state
with a different backend-content comparison. States below describe persistent
operations; view-only operations remain available only while their referenced
Qt objects exist.

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
Text, creation-only Plus, and creation-only Wavy are currently such routes.
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

Atom Align submits only one exact `horizontal` or `vertical` axis and an
immutable tuple of durable `(molecule_id, atom_id)` pairs to a session-owned
adapter. The session captures its current backend snapshot and revision,
constructs the ordinary immutable persistent-operation request, and submits
it. The mode has no snapshot access or callback-owner introspection, and no Qt
object crosses this boundary. A selected non-atom is ignored; if any selected
atom lacks both durable IDs, the complete gesture is inert. Accepted changes
use backend history and canonical reprojection; Qt has no alignment undo owner.

Normalize Bond Angles is a revision-bound geometry-repair route shared by the
Repair menu and Repair-mode selection/click interaction. Qt captures only the
originating synchronized session, its current backend revision, durable
direct-root molecule IDs, the `normalize-bond-angles` kind, and a finite
positive scene spacing. It releases the clicked and selected projection
wrappers before submission; the accepted backend snapshot replaces the
disposable projection. A changed result uses backend history, dirty state,
undo/redo, and canonical reprojection. A no-op leaves the installed projection
and backend history unchanged. An unavailable, ID-less, stale, invalid, or
rejected route is inert. If projection installation fails after acceptance,
the result remains final and retry reprojects only the exact current backend
snapshot; Qt never resubmits the prior repair intent or reconstructs it from
old wrappers. Normalize Rings and Straighten Bonds remain local Qt repair
routes with their existing local undo behavior; they are not clients of this
backend operation.

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
existing local atom-drag undo route, while mixed atom/presentation and
presentation-only drags retain their existing local macro behavior.

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
authoritative snapshot's direct core atom number fields, including hidden
values; nested, opaque, and foreign lookalikes do not participate. The backend
does not supply an allocator. Accepted edits use the existing backend history,
dirty-state, undo/redo, Save, and Recovery Export rules. A typed rejection
leaves the current snapshot and projection unchanged. An accepted result
remains final if projection fails: recovery reprojects only the exact current
backend snapshot and never resubmits the earlier intent. Wavy behavior remains
outside this bounded operation.

For template placement, the frontend submits one `template.insert` intent with
an exact selected system-template name, the current revision, and a finite
scene anchor. Catalog names enter through the session boundary; no
frontend-owned catalog fallback participates in the persistent operation. A
blank click anchors one separate root molecule at the click, while an atom
click anchors the same detached result at the atom coordinate without
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

Text configure, move, delete, and rich-text operations; Plus configure, move,
delete, background or font customization, and other operations; Wavy configure,
move, delete, and other presentation editing; plus other persistent action
families retain their current transitional limits and must not be represented as
backend-authoritative merely because they update a Qt model.

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
Normalize Rings and Straighten Bonds remain local Repair actions with their
existing local undo behavior.

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
This bounded operation does not define partial atom/bond deletion, atom-mark
structural deletion, unsupported selection handling beyond its inert outcome,
or mixed move/configure behavior; those families require their own explicit
operation grammars.

Whole-root Delete is backend-authoritative when the current selection maps
completely to supported durable direct roots. Qt submits only the current
revision and immutable root IDs, records the accepted backend history entry,
and replaces the projection from the returned snapshot. Partial atom/bond,
atom-mark, unsupported, and mixed incomplete selections retain the documented
legacy-isolated structural Delete route until their own explicit operation
grammar is delivered.

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
further failure. This teardown is idempotent.

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
native-process diagnostic; the macOS builder evaluates its LaunchServices
result, receipt, and captured fatal diagnostics as separate observations.

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
page, invalidate requests and join workers, dispose live and undo-retained
graphics callbacks, clear the undo stack and scene, then queue detached roots
for deletion. This sequence is required because Python garbage collection is
not a safe replacement for QObject and graphics callback teardown.

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
- `SessionProjectionLifecyclePort` binds one delivery generation to one live
  `DocumentSession`. It returns closed typed `installed`,
  `preparation-unavailable`, `installation-failed`, or `session-unavailable`
  results with their terminal replacement phase; stale delivery returns before
  notice delivery and cannot update another tab.
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
