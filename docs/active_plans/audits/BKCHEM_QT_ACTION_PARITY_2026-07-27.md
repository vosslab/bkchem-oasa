# BKChem Qt action parity

This is the WP-E1 release-facing inventory.  It compares the current Qt surface with
the legacy workflow shape, not a claim of full Tk parity.  It is based on the action
registry, toolbar-mode configuration, and pointed tests as checked on 2026-07-27.

See the active [BKCHEM_QT_COMPLETION_PLAN_2026-07-27.md](../active/BKCHEM_QT_COMPLETION_PLAN_2026-07-27.md).
M3 is substantially complete for the supported document model. This inventory
does not claim that every legacy CDML dialect or Tk workflow is complete.

## Status and scope

| Code | Meaning |
| --- | --- |
| OK | Usable implementation with the stated evidence. |
| PART | Works only for chemistry objects, bypasses document state, or has a missing behavioral gate. |
| QUEUED | Registered or visible, but deliberately outside the release set until its listed dependency lands. |
| UNSUP | Explicitly unsupported for this release; keep visible only if the UI says so truthfully. |

`Undo` states whether the change is command-backed and therefore marks the session dirty.
`CDML` states whether it survives the M3 full-document codec.  `Thread` is `worker`,
`GUI`, or `sync`; `sync` is a release risk for expensive OASA work.

### Supported release set

The supported set is: session/new/open/save/close; native CDML molecule and
supported-presentation-object save/reopen; molecule draw, atom placement,
templates, basic edit and undo/redo; creation of arrows, text, plus signs,
brackets, vectors, and marks; mixed top-level clipboard operations; presentation
edit/delete/stacking; Configure undo; active-session keybindings; capability-driven
file import; and asynchronous file import. Every other visible feature below is
PART, QUEUED, or UNSUP until it has a behavior test and the stated persistence/undo
contract.

## Document and edit actions

| Action/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| `file.new` | `MainWindow._on_new` session | OK | clean session | yes | GUI | [session tests](../../../packages/bkchem-qt.app/tests/test_document_sessions.py) |
| `file.load` | `MainWindow._on_open` / session loader | OK | clean session | yes | worker for imports | [import capabilities](../../../packages/bkchem-qt.app/tests/test_import_capabilities.py) |
| `file.load_same_tab` | `file_actions._load_same_tab` | OK | replaces clean session | yes | worker for imports | session behavior gate |
| `file.save` | `MainWindow._on_save` | OK | marks clean | yes | GUI | [document CDML session](../../../packages/bkchem-qt.app/tests/test_cdml_document_sessions.py) |
| `file.save_as` | `MainWindow._on_save_as` | OK | marks clean | yes | GUI | document CDML session gate |
| `file.close_tab` | `MainWindow.close_current_tab` | OK | n/a | n/a | GUI | session lifecycle gate |
| `file.exit` | `MainWindow.close` | OK | n/a | n/a | GUI | session teardown gate |
| `file.save_as_template` | molecule serializer only | PART | no | molecules only | GUI | presentation/template round-trip missing |
| `file.properties` | modal paper-properties dialog | OK | one paper snapshot command | paper CDML fields | GUI | focused paper-properties undo/save/reload gate |
| `edit.undo` | active `QUndoStack` | OK | yes | yes | GUI | [document wiring](../../../packages/bkchem-qt.app/tests/test_document_wiring.py) |
| `edit.redo` | active `QUndoStack` | OK | yes | yes | GUI | document wiring |
| `edit.cut` | top-level molecule/presentation CDML fragment | OK | one undo macro | supported objects | GUI | [top-level clipboard](../../../packages/bkchem-qt.app/tests/test_clipboard_top_level_objects.py) |
| `edit.copy` | top-level molecule/presentation CDML fragment | OK | n/a | supported objects | GUI | top-level clipboard |
| `edit.paste` | remapped top-level CDML fragment with placement offset | OK | one undo macro | supported objects | GUI | top-level clipboard |
| `edit.selected_to_svg` | selected scene chemistry | PART | n/a | export only | GUI | presentation/vector SVG gate missing |
| `edit.select_all` | document-object scene selection | OK | n/a | n/a | GUI | object-stack action tests |
| Delete/Backspace | `EditMode` object delete | OK | yes | supported objects | GUI | object-stack action tests |

## Canvas, object, and view actions

| Action/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| `view.zoom_in` | `MainWindow.on_zoom_in` | OK | n/a | n/a | GUI | [zoom controls](../../../packages/bkchem-qt.app/tests/test_zoom_controls.py) |
| `view.zoom_out` | `MainWindow.on_zoom_out` | OK | n/a | n/a | GUI | zoom controls |
| `view.zoom_reset` | `MainWindow.on_reset_zoom` | OK | n/a | n/a | GUI | zoom controls |
| `view.zoom_to_fit` | `MainWindow.on_zoom_to_fit` | OK | n/a | n/a | GUI | zoom controls |
| `view.zoom_to_content` | `MainWindow.on_zoom_to_content` | OK | n/a | n/a | GUI | zoom controls |
| `insert.biomolecule_template` | switches `biotemplate` mode | OK | placement command | molecule | GUI | [interactions](../../../packages/bkchem-qt.app/tests/test_interactions.py) |
| `align.top` | atom-item offsets | PART | yes | molecules only | GUI | generic presentation transform command needed |
| `align.bottom` | atom-item offsets | PART | yes | molecules only | GUI | generic presentation transform command needed |
| `align.left` | atom-item offsets | PART | yes | molecules only | GUI | generic presentation transform command needed |
| `align.right` | atom-item offsets | PART | yes | molecules only | GUI | generic presentation transform command needed |
| `align.center_h` | atom-item offsets | PART | yes | molecules only | GUI | generic presentation transform command needed |
| `align.center_v` | atom-item offsets | PART | yes | molecules only | GUI | generic presentation transform command needed |
| `object.scale` | atom-item scaling dialog | PART | direct/chemistry path | molecules only | GUI | generic presentation transform command needed |
| `object.bring_to_front` | document-object stacking command | OK | yes | supported objects | GUI | [object-stack actions](../../../packages/bkchem-qt.app/tests/test_document_object_stack.py) |
| `object.send_back` | document-object stacking command | OK | yes | supported objects | GUI | object-stack actions |
| `object.swap_on_stack` | document-object stacking command | OK | yes | supported objects | GUI | object-stack actions |
| `object.vertical_mirror` | atom positions | PART | direct | molecules only | GUI | generic transform command needed |
| `object.horizontal_mirror` | atom positions | PART | direct | molecules only | GUI | generic transform command needed |
| `object.configure` | shared item property dialog | OK | one undo macro | supported objects | GUI | [Configure undo](../../../packages/bkchem-qt.app/tests/test_object_configure_undo.py) |

## Chemistry and repair actions

| Action/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| `chemistry.info` | formula/weight dialog | OK | n/a | n/a | GUI | action registry and OASA model path |
| `chemistry.check` | selected-molecule validation | OK | n/a | n/a | GUI | behavior test still missing |
| `chemistry.expand_groups` | group expansion | PART | chemistry path | molecule | GUI | group fidelity and undo gate missing |
| `chemistry.oxidation_number` | OASA calculation/display | OK | n/a | n/a | GUI | behavior test still missing |
| `chemistry.read_smiles` | text input to OASA molecule | PART | command path | molecule | sync | worker and cancellation gate missing |
| `chemistry.read_inchi` | text input to OASA molecule | PART | command path | molecule | sync | external executable/worker gate missing |
| `chemistry.read_peptide` | sequence to OASA molecule | PART | command path | molecule | sync | worker and cancellation gate missing |
| `chemistry.gen_smiles` | selected OASA molecule | OK | n/a | n/a | GUI | behavior test still missing |
| `chemistry.gen_inchi` | selected OASA molecule | PART | n/a | n/a | sync | configured executable and behavior gate missing |
| `chemistry.set_name` | molecule model field | PART | direct | molecule | GUI | property command and CDML test needed |
| `chemistry.set_id` | molecule model field | PART | direct | molecule | GUI | property command and CDML test needed |
| `chemistry.create_fragment` | status-message handler | UNSUP | no | no | GUI | explicit release decision required before enabling |
| `chemistry.view_fragments` | status-message handler | UNSUP | no | no | GUI | explicit release decision required before enabling |
| `chemistry.convert_to_linear` | selected unbranched path to glyph-safe `linear_form` metadata | OK | one macro | molecule | GUI | [linear form action](../../../packages/bkchem-qt.app/tests/test_linear_form_actions.py) |
| `repair.normalize_bond_lengths` | OASA repair operation + undo macro | OK | yes | molecule | GUI | [repair action](../../../packages/bkchem-qt.app/tests/test_repair_actions.py) |
| `repair.snap_to_hex_grid` | OASA repair operation + undo macro | OK | yes | molecule | GUI | repair action |
| `repair.normalize_bond_angles` | OASA repair operation + undo macro | OK | yes | molecule | GUI | repair action |
| `repair.normalize_rings` | OASA repair operation + undo macro | OK | yes | molecule | GUI | repair action |
| `repair.straighten_bonds` | OASA repair operation + undo macro | OK | yes | molecule | GUI | repair action |
| `repair.clean_geometry` | coordinate regeneration | PART | yes | molecule | sync | worker, cancellation, and OASA-parity gate missing |

## Options and help actions

| Action/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| `options.standard` | standard settings dialog | PART | no | preferences only | GUI | document-standard contract missing |
| `options.language` | language settings dialog | OK | n/a | preferences | GUI | preference behavior gate missing |
| `options.logging` | logging settings dialog | OK | n/a | preferences | GUI | preference behavior gate missing |
| `options.inchi_path` | InChI path settings dialog | PART | no | preferences | GUI | validate executable before use |
| `options.theme` | theme chooser | OK | n/a | preferences | GUI | [theme chooser](../../../packages/bkchem-qt.app/tests/test_theme_chooser.py) |
| `options.preferences` | main preferences dialog | OK | no | preferences | GUI | active keybinding configuration is shared with the manager |
| `help.keyboard_shortcuts` | registry shortcut table | OK | n/a | n/a | GUI | [keybinding manager](../../../packages/bkchem-qt.app/tests/test_keybinding_manager.py) |
| `help.about` | about dialog | OK | n/a | n/a | GUI | GUI smoke coverage |

## Modes and mode wiring

| Mode/capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| edit | `EditMode` selection and object delete | OK | yes | supported objects | GUI | object-stack action tests |
| draw | `DrawMode` atom/bond construction | OK | yes | molecule | GUI | [document wiring](../../../packages/bkchem-qt.app/tests/test_document_wiring.py) |
| atom | `AtomMode` element placement | OK | yes | molecule | GUI | [interactions](../../../packages/bkchem-qt.app/tests/test_interactions.py) |
| template | `TemplateMode` placement | PART | yes | molecule | GUI | advertised atom fusion only overlaps; attachment gate needed |
| biotemplate | `BiotemplateMode` placement | OK | yes | molecule | GUI | interactions and [mode parity](../../../packages/bkchem-qt.app/tests/test_mode_submode_parity.py) |
| usertemplate | YAML-configured template mode | PART | yes | molecule | GUI | manager/persistence breadth still needs a behavior gate |
| mark | `MarkMode` with atom mark model | OK | yes | yes | GUI | [presentation persistence](../../../packages/bkchem-qt.app/tests/test_presentation_mode_persistence.py) |
| arrow | `ArrowMode` presentation object | OK | yes | yes | GUI | presentation persistence |
| plus | `PlusMode` presentation object | OK | yes | yes | GUI | presentation persistence |
| text | `TextMode` presentation object | OK | yes | yes | GUI | presentation persistence |
| bracket | `BracketMode` paired polylines | OK | yes | yes | GUI | presentation persistence |
| vector | `VectorMode` shapes/polylines | OK | yes | yes | GUI | presentation persistence |
| rotate | `RotateMode` atom-only 2D rotation | PART | backend | direct atoms | GUI | `atom.rotate`; mixed objects and transforms remain separate |
| bondalign | `BondAlignMode` direct atom moves | PART | no | molecule only | GUI | undo and transform behavior gate needed |
| repair | `RepairMode` invokes repair actions | PART | see repair rows | molecule | GUI | OASA-parity and worker gates missing |
| misc numbering | atom-number labels | OK | command | yes | GUI | `numbering` ribbon key dispatches to model-owned numbering |
| misc wavy line | presentation polyline | OK | command | yes | GUI | transient drag preview; editable CDML `polyline` round trip |
| file-actions ribbon | new/open/save/save-as dispatch | OK | as action | as action | GUI/worker | toolbar action resolution test |

The mode manager registers the advertised document modes. The core drawing and
presentation modes have persistence tests; transform-oriented modes and some
submode variants remain PART until their command and persistence behavior is covered.

## Formats, keys, and asynchronous work

| Capability | Qt implementation | Status | Undo | CDML | Thread | Evidence or missing gate |
| --- | --- | --- | --- | --- | --- | --- |
| Native CDML open/save | document codec and session loader | OK pending M3 root gate | clean/save | yes | GUI | [document round-trip](../../../packages/bkchem-qt.app/tests/test_qt_backend_session_adapter.py) |
| OASA format import | capability registry drives actions and dialogs | OK | clean/new document | imported molecule | worker | [import capabilities](../../../packages/bkchem-qt.app/tests/test_import_capabilities.py) |
| SDF import | capability registry maps molfile reader | OK | clean/new document | imported molecule | worker | import capabilities |
| SVG import | open dialog advertises SVG | PART | n/a | n/a | GUI | [test rejects it as chemistry import](../../../packages/bkchem-qt.app/tests/test_import_capabilities.py) |
| SVG/PNG/PDF export | scene rendering export | PART | n/a | export only | GUI | presentation/document completeness gate missing |
| Import menu cascade | generated from capabilities | OK | n/a | n/a | GUI | import capabilities |
| Action module discovery | contextual registration diagnostics | OK | n/a | n/a | GUI | [menu contract](../../../packages/bkchem-qt.app/tests/test_qt_menu_contract.py) |
| Menu YAML lookup | contextual unknown-action diagnostics | OK | n/a | n/a | GUI | menu contract |
| Default shortcuts | active-session `KeybindingManager` | OK | n/a | n/a | GUI | keybinding manager |
| File-import worker | session-owned parse/project worker | OK | clean/new document | imported molecule | worker | [worker lifecycle](../../../packages/bkchem-qt.app/tests/test_worker_lifecycle.py) |
| Chemistry text imports | handlers call OASA directly | PART | command path | molecule | sync | use session-owned worker and cancellation |
| Geometry cleanup | repair action calls coordinate work directly | PART | command path | molecule | sync | use session-owned worker and cancellation |
| Package data/runtime layout | package-owned menus, modes, themes, icons, and OASA data | OK build audit | n/a | n/a | n/a | wheel audit; installed-launch gate remains M5 |

## Prioritized non-overlapping slices

1. Transform family: align, scale, mirrors, rotate, and bond alignment on command-backed
   molecule and presentation models.
2. Mode truthfulness: complete behavior coverage for usertemplate, wavy-line, and all
   visible transform/misc submode values.
3. Template attachment: implement actual atom fusion or change the advertised interaction.
4. Worker jobs: move SMILES/InChI/peptide and cleanup work to session-owned cancellable jobs.
5. Fragments and linear conversion: either implement them as document operations or keep
   them explicitly unsupported.
6. Compatibility and packaging: add representative legacy/Tk CDML samples, resolve the
   prefix-qualified core-CDML limitation, then verify installed package data and launch in M5.

These slices do not overlap at the data-model boundary.  Complete them only after the M3
root gate establishes that presentation objects can be saved and reopened safely.
