# Changelog

## 2026-08-11

### Behavior or Interface Changes

- New Qt tabs start in Draw mode, use OASA paper defaults, and frame after
  layout; first Draw creates backend structure. Chemistry Info reads exact OASA
  composition, Numbering avoids reparsing, and Drawing Style supports atomic
  selected/all overrides plus clean defaults. OASA codecs now preserve classic
  CD-SVG as complete imported documents. The macOS builder independently checks
  direct/offscreen and native LaunchServices routes with separate receipts.

### Fixes and Maintenance

- Added first-use guidance; aligned templates, Recent Files, and modal-warning
  tests. Linear cleanup owns metadata; classic bond CDML owns imports. Private
  graph aliases are gone; dialogs emit detached intent, and deprecated Tk stays.
  Complete topology supplies Qt rendering; carbon glyphs share bond targets.
  Hex-grid/contract laws guard coupling; Arrow Configure now commits through OASA.
- Corrected the indentation gate for Python 3.12 multiline f-strings; embedded
  XML and other text tokens are not source-code indentation.
- Restored registry-aware release tooling after its split: changelog commits
  parse the canonical assignment, the public facade remains, requirement
  suffixes survive, and releases update all package manifests.
- Added exact non-growth ceilings for oversized active files. Historical
  archives are excluded; current debt may shrink but cannot grow.

## 2026-08-03

### Behavior or Interface Changes

- Reconciled the stable backend/frontend contracts with the accepted authority
  implementation: complete CDML, immutable snapshots and revisions, final
  atomic commits, consumed provisional tokens, independent saved baselines,
  exact-snapshot recovery, and state-neutral Recovery Export remain behavioral
  guarantees rather than Qt or Python implementation details.

- Completed the CDML 26.07 documentation for hardened lxml complete-document
  parsing, opaque preservation, portable render observations, and the bounded
  direct-glycosidic Haworth profile. The supported two-ring C/O drawing route
  persists `q`/`w`/`n` and `haworth_position` records without claiming
  alpha/beta or tetrahedral semantics.

- Updated Qt-only installation, usage, architecture, file-layout, migration,
  and action-parity documentation. Copy SVG, chemistry observations/imports,
  preferences/logging, transforms and repair, templates, projection envelopes,
  Haworth/PubChem, import/export, installed-wheel, clean-install, and direct
  frozen-bundle evidence now have their current dispositions.

### Decisions and Failures

- Kept source and pip installation as the delivered application paths. The
  direct frozen-bundle lifecycle result remains useful diagnostic evidence,
  while native LaunchServices, DMG, signing, and notarization belong to a
  separate future delivery project rather than this release gate.

### Fixes and Maintenance

- Ran a fresh six-perspective independent audit of the authority boundary.
  Updated the Arrow authority E2E to consume the extracted
  projection-lifecycle module, reserved accepted terminology for final backend
  commits, repaired a stale historical-plan link, and removed a syscall-default
  assertion that duplicated implementation rather than user-visible behavior.

- Reconciled the Qt action-parity inventory with the implemented revision
  ownership. Synchronized clipboard changes, Delete, presentation stacking,
  repair operations, drawing modes, atom marks and numbering, and persistent
  drawing-object insertion use backend history; Qt-local undo remains an
  explicitly isolated compatibility behavior rather than the release route.

- Removed stale Qt-contract language that described Normalize Rings as a local
  Repair exception. Its supported simple-ring behavior is backend-authoritative;
  unsupported multi-cycle topology is a typed atomic failure without a Qt-local
  mutation or undo fallback.

- Replaced the personal-path and AppleScript Qt screenshot launcher with a
  tracked, bounded documentation catalog. Fresh isolated Qt processes capture
  complete-document, persistent-drawing-object, and verified-sucrose Haworth
  scenarios at 1280x800 beneath repository paths and retire each projection
  through the production lifecycle boundary.

- Simplified the frozen-app smoke to one direct, bounded executable run with
  retained stdout, stderr, and an app-owned completion receipt. Host
  LaunchServices registration is no longer conflated with application
  lifecycle correctness.

- Added `CAPABILITIES.md` as the visual current-capability guide and corrected
  Content zoom to include every document-backed presentation projection, so
  vectors and bracket polylines remain visible alongside molecular content.

- Kept the capabilities screenshot block idempotent by limiting its managed
  content to image embeds while retaining the architectural explanations in
  the surrounding page. Rephrased frontend-neutral CDML payloads as immutable
  ordered sequences and records rather than Python tuple types.

- Extracted projection lifecycle delivery from the tab session into a focused,
  dependency-light module. Stale delivery now checks a public session ownership
  query instead of reaching through `DocumentSession` private state. Focused
  session-adapter cleanup now uses the production disposal boundary directly,
  so an intentionally dirty recovery state cannot block a test on a modal.

- Moved molecule graphics construction and failure cleanup from File Actions
  into a dedicated canvas projection module. Synchronized hydration, native and
  imported document installation, and action-driven insertion now share that
  public frontend projection boundary without an IO-to-actions import.

- Updated troubleshooting to direct current users to the supported PySide6
  launch path and to identify the retained Tk package as contributor reference
  material rather than a runnable delivery workflow.

- Clarified that historical Tk-only format routes remain contributor reference
  evidence and impose no shipping or compatibility requirement.

- Added visible direct-glycosidic Haworth action coverage through the accepted
  dialog, session-owned worker, authoritative commit, canonical reprojection,
  and backend undo/redo. Focused geometry coverage now asserts durable
  structural and Haworth semantics rather than tuned clearance or wedge counts.

- Hardened user-template catalog admission against path replacement: each
  candidate now opens relative to the scan's directory descriptor with
  no-follow and nonblocking flags, validates that opened descriptor as a
  regular file, then decodes that exact descriptor.

- Kept each admitted user-template descriptor under explicit catalog ownership
  until its read path completes, so wrapper-construction and read failures
  close the same verified descriptor deterministically.

- Retired the unused molecule-only Qt CDML loader and its ambiguous aliases.
  Standalone callers now use the explicitly named complete-CDML compatibility
  decoder, while synchronized sessions continue to rebuild only from backend
  projection snapshots.

- Routed accepted PubChem molecule proposals through the shared immutable
  molecule-insertion request builder, keeping PubChem, SMILES, and Haworth on
  one validated request grammar before their authoritative backend commit.

- Retired the broken root Tk screenshot command after the Qt-only launcher
  transition. The retained Tk package remains historical source and fixture
  evidence, while the supported screenshot workflow is PySide6-only.

- Restored executable mode for the standalone Qt icon renderer so its
  canonical Python shebang and direct-command interface remain aligned.

- Repaired the indentation gate's multiline f-string recognition and normalized
  affected Qt and OASA continuation indentation to tabs without changing behavior.

- Corrected structural clipboard coverage to preserve a selected atom's
  compatible opaque extension through backend extraction and Paste. A
  genuinely unsupported core child remains a typed, atomic extraction failure.

- Repaired the backend operation table so every declared operation remains in
  one scannable table and its projection-snapshot invariant appears after the
  complete operation list.

- Corrected the action-parity inventory to cite the authoritative SMILES export
  behavior test and to describe only the delivered mode routes as release
  claims.

- Reconciled final M6 release documentation after six independent reviews. The
  plan records completed source, installed, boundary, and audit gates; their
  material findings corrected status drift, fragile tests, scoped style,
  release documentation, legacy paths, and ownership comments. The managed
  screenshot catalog is tracked, while frozen native distribution remains a
  separately scoped delivery project.

- Retired the dead Qt full-document loaded-document installation helper. Native
  and imported documents now enter through their staged backend-snapshot routes;
  the removed helper was not an alternate persistence or installation path.

- Removed implementation-class names from the stable backend contract's
  structural-delete and mixed-selection failure descriptions; durable request
  values and typed failure categories remain the interface.

- Reframed Qt delivery and release-metadata tests around supported command and
  public-version behavior, so unrelated utility entry points and private
  source-layout details no longer make release policy tests brittle.
