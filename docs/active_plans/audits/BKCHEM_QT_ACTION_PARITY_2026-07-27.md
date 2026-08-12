# BKChem Qt action parity

This is the WP-E1 release-facing inventory. It records the current Qt delivery and
the frontend-neutral CDML boundary, using legacy behavior only as a feature reference.
It is based on the action registry, toolbar-mode configuration, implementation, and
pointed tests reconciled on 2026-08-11. Qt is the current release frontend;
the classic Tk frontend is deprecated but remains retained as a behavior reference.

Whole-window and worker pytest modules used during the rebuild were retired on
2026-08-11 under the permanent-test and fixture policy. Current application
evidence is the managed gallery plus the installed-wheel E2E; durable chemistry
and document semantics remain in OASA tests. The rows below are capability and
source-route dispositions, not a requirement to recreate deleted GUI matrices.

See the active [BKCHEM_QT_COMPLETION_PLAN_2026-07-27.md](../active/BKCHEM_QT_COMPLETION_PLAN_2026-07-27.md).
The exact-revision presentation, paper-layout, backend clipboard, fragment,
atom-mark, group, molecule-core, molecule-render, and aggregate projection
envelope observations are accepted. Synchronized molecule, atom, and bond
projection no longer retains raw molecule XML or an OASA graph as persistent
state.
This inventory does not claim that every historical CDML dialect is complete.

## Status and scope

| Code | Meaning |
| --- | --- |
| OK | Usable implementation with the stated evidence. |
| PART | Works only for chemistry objects, bypasses document state, or has a missing behavioral gate. |
| QUEUED | Registered or visible, but deliberately outside the release set until its listed dependency lands. |
| UNSUP | Explicitly unsupported for this release; keep visible only if the UI says so truthfully. |

`Undo` states whether the change creates backend revision navigation or a
deliberately isolated compatibility command. It is not a claim that a Qt stack
owns synchronized persistent history.
`CDML` states whether it survives the M3 full-document codec.  `Thread` is `worker`,
`GUI`, or `sync`; `sync` is a release risk for expensive OASA work.

### Supported release set

The supported set is: session/new/open/save/close; native CDML save/reopen for the
implemented document path; molecule draw, atom placement, templates, basic edit and
undo/redo; arrows, text, plus signs, brackets, vectors, and marks; mixed top-level
clipboard operations; presentation edit/delete/stacking; atom, bond, plain Text, plain
Plus, Wavy, Arrow, supported Rich Text editing, and current-document drawing defaults;
active-session keybindings;
capability-driven file import; asynchronous imports; Haworth and PubChem insertion;
and supported artifact export. The M6 audit ran, its findings were resolved,
and the source, installed, boundary, and audit gates are complete. The managed
README screenshot and reproducible capabilities
gallery provide retained application evidence. Finder integration, signing,
notarization, and DMG delivery are outside this source/pip release scope; they
are not missing projection decoding.

## Document and edit actions

| Action/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| `file.new` | `MainWindow._on_new` session | OK | clean session | yes | GUI | managed application gallery |
| `file.load` | `MainWindow._on_open` / session loader | OK | clean session | yes | worker for imports | installed application E2E |
| `file.load_same_tab` | `file_actions._load_same_tab` | OK | replaces clean session | yes | worker for imports | session behavior gate |
| `file.save` | `MainWindow._on_save` | OK | marks clean | yes | GUI | installed authoritative round trip |
| `file.save_as` | `MainWindow._on_save_as` | OK | marks clean | yes | GUI | document CDML session gate |
| `file.recovery_export` | backend snapshot publication | OK | no | exact current snapshot | GUI | accepted evidence recovery-export coverage |
| `file.close_tab` | `MainWindow.close_current_tab` | OK | n/a | n/a | GUI | session lifecycle gate |
| `file.exit` | `MainWindow.close` | OK | n/a | n/a | GUI | session teardown gate |
| `file.save_as_template` | exact admitted backend snapshot | OK | no | one eligible molecule | GUI | accepted evidence |
| `file.properties` | modal paper-properties dialog | OK | one paper snapshot command | paper CDML fields | GUI | focused paper-properties undo/save/reload gate |
| `edit.undo` | backend revision navigation through the Qt action adapter | OK | backend | yes | GUI | backend history source audit |
| `edit.redo` | backend revision navigation through the Qt action adapter | OK | backend | yes | GUI | backend history |
| `edit.cut` | backend extraction followed by one revision-bound delete | OK | backend | supported objects | GUI | clipboard source audit |
| `edit.copy` | exact atom/bond OASA fragment or top-level molecule/presentation CDML | OK | n/a | selected structures and supported roots | GUI | accepted evidence; top-level clipboard |
| `edit.paste` | backend insertion of a remapped top-level CDML fragment | OK | backend | supported objects | GUI | top-level clipboard |
| `edit.selected_to_svg` | captured backend snapshot plus durable selection IDs | OK | n/a | export only | GUI | accepted evidence; source projection is never serialized |
| `edit.select_all` | document-object scene selection | OK | n/a | n/a | GUI | object-stack action tests |
| Delete/Backspace | revision-bound structural, mark, or top-level delete | OK | backend | supported objects | GUI | structure-delete, mark-authority, and object-stack action tests |
| `edit.drag_presentation` | `EditMode` backend `translate` after transient preview | OK | backend | supported durable direct roots | GUI | focused presentation-drag authority coverage |

## Canvas, object, and view actions

| Action/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| `view.zoom_in` | `MainWindow.on_zoom_in` | OK | n/a | n/a | GUI | managed application gallery |
| `view.zoom_out` | `MainWindow.on_zoom_out` | OK | n/a | n/a | GUI | zoom controls |
| `view.zoom_reset` | `MainWindow.on_reset_zoom` | OK | n/a | n/a | GUI | zoom controls |
| `view.zoom_to_fit` | `MainWindow.on_zoom_to_fit` | OK | n/a | n/a | GUI | zoom controls |
| `view.zoom_to_content` | `MainWindow.on_zoom_to_content` | OK | n/a | n/a | GUI | zoom controls |
| `insert.biomolecule_template` | `BioTemplateMode` submits OASA `biotemplate.insert` | OK | backend | detached molecule root | GUI | accepted evidence |
| `align.top` | backend mixed-root transform | OK | backend | supported roots | GUI | transform source audit plus OASA operation tests |
| `align.bottom` | backend mixed-root transform | OK | backend | supported roots | GUI | transform action authority |
| `align.left` | backend mixed-root transform | OK | backend | supported roots | GUI | transform action authority |
| `align.right` | backend mixed-root transform | OK | backend | supported roots | GUI | transform action authority |
| `align.center_h` | backend mixed-root transform | OK | backend | supported roots | GUI | transform action authority |
| `align.center_v` | backend mixed-root transform | OK | backend | supported roots | GUI | transform action authority |
| `object.scale` | backend mixed-root Scale dialog | OK | backend | supported roots | GUI | transform action authority |
| `object.bring_to_front` | revision-bound presentation-stack reorder | OK | backend | supported objects | GUI | OASA presentation-order tests |
| `object.send_back` | revision-bound presentation-stack reorder | OK | backend | supported objects | GUI | object-stack actions |
| `object.swap_on_stack` | revision-bound presentation-stack reorder | OK | backend | supported objects | GUI | object-stack actions |
| `object.vertical_mirror` | backend mixed-root transform | OK | backend | supported roots | GUI | transform action authority |
| `object.horizontal_mirror` | backend mixed-root transform | OK | backend | supported roots | GUI | transform action authority |
| `object.configure` | atom/bond, plain Text, Plus, Wavy, Arrow, and geometric property dialogs | OK | backend synchronized; local isolated chemistry compatibility route | supported scalar fields | GUI | property-authority tests; geometric stroke/fill, Text background, and Plus font/background use OASA history and projection |
| `object.edit_rich_text` | revision-bound `text.rich.patch` modal flow | OK | backend | supported direct-root Text `ftext` | GUI | accepted evidence; unsupported attributed markup remains visible and preservation-only |

## Chemistry and repair actions

| Action/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| `chemistry.info` | exact-revision molecular-composition dialog | OK | no mutation | authoritative roots | GUI | accepted evidence; implicit hydrogens, exact masses, combined selection, and recovery states |
| `chemistry.check` | exact-revision atom-chemistry observation | OK | n/a | n/a | GUI | accepted evidence |
| `chemistry.expand_groups` | revision-bound OASA group expansion | OK | backend | molecule | GUI | accepted evidence, accepted evidence, and accepted evidence; synchronized groups use OASA observations |
| `chemistry.oxidation_number` | exact-revision OASA-derived observation/display | OK | n/a | n/a | GUI | accepted evidence |
| `chemistry.read_smiles` | immutable proposal through session-owned worker | OK | backend | molecule | worker | accepted evidence; delivery is origin-bound and cancellation-safe |
| `chemistry.read_inchi` | immutable proposal through session-owned worker | OK | backend | molecule | worker | accepted evidence; external executable availability is a typed capability outcome |
| `chemistry.read_peptide` | immutable proposal through session-owned worker | OK | backend | molecule | worker | accepted evidence; delivery is origin-bound and cancellation-safe |
| `chemistry.gen_smiles` | exact-revision backend SMILES observation | OK | n/a | n/a | GUI | accepted evidence; selected durable molecule only |
| `chemistry.gen_inchi` | OASA standard InChI/InChIKey from exact-revision SMILES observation | OK | n/a | n/a | GUI | accepted evidence; no external executable or document mutation |
| `chemistry.set_name` | revision-bound molecule-name patch | OK | backend | molecule | GUI | accepted evidence and accepted evidence |
| `chemistry.create_fragment` | backend ordinary-fragment metadata operation | OK | backend | molecule metadata | GUI | accepted evidence |
| `chemistry.view_fragments` | backend observation/delete operation | OK | backend delete | molecule metadata | GUI | accepted evidence; plain display-only notices |
| `chemistry.convert_to_linear` | backend `linear-form.convert` deterministic 10-point path and narrow metadata | OK | backend | molecule | GUI | accepted evidence; origin-bound Qt action uses canonical reprojection |
| `repair.normalize_bond_lengths` | backend `geometry.repair` | OK | backend | molecule | GUI | OASA geometry-repair tests |
| `repair.snap_to_hex_grid` | backend `geometry.repair` | OK | backend | molecule | GUI | repair action |
| `repair.normalize_bond_angles` | backend `geometry.repair` | OK | backend | molecule | GUI | repair action |
| `repair.normalize_rings` | backend `geometry.repair` | OK | backend | molecule | GUI | simple-ring durable-ID menu and Repair-mode route; multi-cycle topology is typed unsupported |
| `repair.straighten_bonds` | backend `geometry.repair` | OK | backend | molecule | GUI | durable-ID menu and Repair-mode route |
| `repair.clean_geometry` | coordinate regeneration | OK | backend | molecule | sync | accepted evidence and session-adapter coverage; measured synchronous 100-atom p95 is below 62 ms, so worker migration is not a current release gate |
| `insert.haworth_*` | session-owned Haworth preparation and insertion | OK | backend | detached molecule root | worker | accepted evidence; declared multi-ring and fixed sucrose paths are covered separately in OASA Haworth tests |
| `insert.pubchem` | bounded PubChem lookup and insertion | OK | backend | detached molecule root | worker | accepted evidence, accepted evidence, and accepted evidence; tests use an offline transport seam |

## Options and help actions

| Action/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| `options.standard` | backend-owned drawing-style, scope, and personal-default dialog | OK | backend | standard and object CDML | GUI | accepted evidence and accepted evidence; defaults, selected/all overrides, clean new-document preferences, reprojection, and undo |
| `options.language` | omitted from the shipped menu | UNSUP | n/a | n/a | GUI | locale files are retained compatibility data; the delivered Qt application has no language-selection action |
| `options.logging` | logging settings dialog | OK | n/a | preferences | GUI | accepted evidence proves persisted level and immediate application |
| `options.inchi_path` | obsolete external executable preference | UNSUP | no | n/a | GUI | bundled RDKit owns standard InChI generation, so the delivered interface intentionally needs no executable path |
| `options.theme` | theme chooser | OK | n/a | preferences | GUI | one-time application walkthrough |
| `options.preferences` | main preferences dialog | OK | no | preferences | GUI | active keybinding configuration is shared with the manager |
| `help.keyboard_shortcuts` | registry shortcut table | OK | n/a | n/a | GUI | source inventory |
| `help.about` | about dialog | OK | n/a | n/a | GUI | GUI smoke coverage |

## Modes and mode wiring

| Mode/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| edit | `EditMode` selection plus revision-bound atom, presentation, and mixed movement and deletion | OK | backend/local isolated | supported objects | GUI | atom, presentation, and mixed-selection drag authority |
| draw | `DrawMode` atom/bond construction | OK | backend | molecule | GUI | source audit plus installed application E2E |
| atom | `AtomMode` element placement | OK | backend | molecule | GUI | source audit plus installed application E2E |
| template | `TemplateMode` detached placement | OK | backend | detached molecule root | GUI | template authority/placement tests; atom fusion is explicitly outside the delivered detached-placement capability |
| biotemplate | `BioTemplateMode` catalog-key placement | OK | backend | detached molecule root | GUI | OASA biomolecule placement tests plus one-time walkthrough |
| usertemplate | explicit catalog-key template mode | OK | backend | detached molecule root | GUI | accepted evidence, accepted evidence, accepted evidence, and accepted evidence |
| mark | `MarkMode` submits a revision-bound atom-mark operation | OK | backend | yes | GUI | OASA atom-mark tests |
| arrow | `ArrowMode` submits OASA endpoint intent, never XML | OK | backend | yes | GUI | OASA Arrow tests plus managed gallery |
| plus | `PlusMode` submits OASA position intent, never XML | OK | backend | yes | GUI | OASA Plus tests plus managed gallery |
| text | `TextMode` submits OASA position/content intent, never XML | OK | backend | yes | GUI | OASA Text tests plus managed gallery |
| bracket | rectangular/round `BracketMode` submits one OASA-owned insertion request | OK | backend | yes | GUI | OASA bracket tests plus managed gallery |
| vector | `VectorMode` submits OASA geometric insertion intent, never XML | OK | backend | yes | GUI | OASA geometric tests plus managed gallery |
| rotate | `RotateMode` atom-only 2D rotation | OK | backend | direct atoms | GUI | accepted evidence and backend rotate operation tests |
| bondalign | `BondAlignMode` direct atom moves | OK | backend | molecule | GUI | accepted evidence and backend alignment tests |
| repair | `RepairMode` invokes declared backend repair actions | OK | backend | molecule | GUI | accepted evidence and focused backend geometry tests |
| misc numbering | revision-bound atom-number operation plus exact-revision candidate facts | OK | backend | yes | GUI | accepted evidence |
| misc wavy line | OASA endpoint insertion after transient drag preview | OK | backend | yes | GUI | accepted evidence |
| file-actions ribbon | new/open/save/save-as dispatch | OK | as action | as action | GUI/worker | toolbar action resolution test |

The mode manager registers the advertised document modes. The table records
the delivered routes and their evidence; deeper historical submode variants are
not release claims unless they appear as a supported row.

## Formats, keys, and asynchronous work

| Capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| Native CDML open/save | complete backend snapshot envelope and session loader | OK | clean/save | yes | GUI | aggregate envelope/hydration and round-trip authority tests |
| OASA format import | capability registry drives actions and dialogs | OK | clean/new document | imported molecule | worker | format-bridge tests plus installed application E2E |
| SDF import | capability registry maps molfile reader | OK | clean/new document | imported molecule | worker | import capabilities |
| CD-SVG import | OASA complete-document codec extracts one embedded CDML root from `.svg`, `.svgz`, or `.cdsvg` | OK | backend import baseline | yes | worker | accepted evidence; plain rendered SVG remains explicitly non-editable |
| SVG/PNG/PDF export | disposable snapshot-render projection | OK | n/a | export only | GUI | accepted evidence; unavailable projection is a typed export failure rather than Qt-model serialization |
| Import menu cascade | generated from capabilities | OK | n/a | n/a | GUI | import capabilities |
| Action module discovery | contextual registration diagnostics | OK | n/a | n/a | GUI | installed application startup |
| Menu YAML lookup | contextual unknown-action diagnostics | OK | n/a | n/a | GUI | menu contract |
| Default shortcuts | active-session `KeybindingManager` | OK | n/a | n/a | GUI | keybinding manager |
| File-import worker | session-owned parse/project worker | OK | clean/new document | imported molecule | worker | one-time installed application E2E |
| Chemistry text imports | immutable preparation bridge and origin-bound worker | OK | backend | molecule | worker | chemistry action bridge and worker lifecycle tests |
| Geometry cleanup | repair action calls coordinate work directly | OK | backend | molecule | sync | accepted latency evidence keeps the bounded synchronous path under the current release budget |
| Package data/runtime layout | package-owned menus, modes, themes, icons, and OASA data | OK build audit | n/a | n/a | n/a | wheel inspection plus independent direct-lifecycle and native LaunchServices receipts; signing/notarization remain separate |

## Resolved and dispositioned slices

1. **Template attachment disposition.** The delivered TemplateMode is authoritative
   detached placement. Atom fusion/attachment requires a future declared backend
   operation and is absent from the release claim.
2. **Standard parity.** Document defaults, selected/all explicit overrides,
   personal-default storage, new-document seeding, and future presentation
   styling are complete; bundled RDKit needs no external-InChI path.

The projection envelope and top-level clipboard extraction remain accepted
backend queries. The M6 integration, packaging, current-user documentation,
and retained lifecycle evidence described by the active plan are complete.
