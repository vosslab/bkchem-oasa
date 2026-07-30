# Tk main/paper evaluation for Qt parity (2026-03-01)

## Purpose

This document evaluates how the Tk implementation centered on
[main.py](../../packages/bkchem-app/bkchem/main.py)
and [paper.py](../../packages/bkchem-app/bkchem/paper.py)
actually works, with the explicit goal of preserving the strongest behavior in
the Qt port.

The emphasis is not only "feature present/absent", but runtime contracts and
interaction seams that make Tk BKChem feel complete.


## Scope reviewed

Primary entry points:

- [main.py](../../packages/bkchem-app/bkchem/main.py)
- [paper.py](../../packages/bkchem-app/bkchem/paper.py)

Main submodules:

- [main_tabs.py](../../packages/bkchem-app/bkchem/main_lib/main_tabs.py)
- [main_modes.py](../../packages/bkchem-app/bkchem/main_lib/main_modes.py)
- [main_file_io.py](../../packages/bkchem-app/bkchem/main_lib/main_file_io.py)
- [main_chemistry_io.py](../../packages/bkchem-app/bkchem/main_lib/main_chemistry_io.py)

Paper submodules:

- [paper_events.py](../../packages/bkchem-app/bkchem/paper_lib/paper_events.py)
- [paper_selection.py](../../packages/bkchem-app/bkchem/paper_lib/paper_selection.py)
- [paper_zoom.py](../../packages/bkchem-app/bkchem/paper_lib/paper_zoom.py)
- [paper_cdml.py](../../packages/bkchem-app/bkchem/paper_lib/paper_cdml.py)
- [paper_properties.py](../../packages/bkchem-app/bkchem/paper_lib/paper_properties.py)
- [paper_layout.py](../../packages/bkchem-app/bkchem/paper_lib/paper_layout.py)
- [paper_factories.py](../../packages/bkchem-app/bkchem/paper_lib/paper_factories.py)
- [paper_transforms.py](../../packages/bkchem-app/bkchem/paper_lib/paper_transforms.py)
- [paper_id_manager.py](../../packages/bkchem-app/bkchem/paper_lib/paper_id_manager.py)

Supporting contracts used by main/paper:

- [mode_loader.py](../../packages/bkchem-app/bkchem/modes/mode_loader.py)
- [modes_lib.py](../../packages/bkchem-app/bkchem/modes/modes_lib.py)
- [config.py](../../packages/bkchem-app/bkchem/modes/config.py)
- [modes.yaml](../../packages/bkchem-app/bkchem_data/modes.yaml)
- [platform_menu.py](../../packages/bkchem-app/bkchem/platform_menu.py)
- [theme_manager.py](../../packages/bkchem-app/bkchem/theme_manager.py)
- [grid_overlay.py](../../packages/bkchem-app/bkchem/grid_overlay.py)


## System architecture summary

Tk BKChem is an event-driven app with one application orchestrator (`BKChem`)
and one active drawing document per tab (`chem_paper`), both composed from
mixins.

```text
BKChem (Tk root + app orchestration)
  |- main_lib.main_tabs        (tab lifecycle, paper switching)
  |- main_lib.main_modes       (mode/submode ribbon lifecycle)
  |- main_lib.main_file_io     (CDML + format import/export + recents)
  |- main_lib.main_chemistry_io(SMILES/InChI/peptide I/O)
  |- modes.* + modes.yaml      (tool behavior + toolbar structure)
  `- singleton_store.Store     (global app/logger/template/id managers)

chem_paper (Canvas + document/runtime model)
  |- paper_events      (mouse/key dispatch to current mode)
  |- paper_selection   (selection semantics and queries)
  |- paper_zoom        (view zoom + viewport centering)
  |- paper_cdml        (read/write package and id sandbox)
  |- paper_properties  (paper size, standard, theme-aware background)
  |- paper_layout      (align/mirror/clean/stack operations)
  |- paper_factories   (construct and deserialize top-level objects)
  |- paper_transforms  (screen<->real coordinate transforms)
  `- paper_id_manager  (canvas id to object registry)
```


## Main.py and main_lib strengths to preserve

## 1) Startup sequencing is deliberate and stable

`BKChem.initialize()` executes a strict order:

1. Create base app state.
2. Create notebook and first paper.
3. Initialize singletons (template managers, id manager, logger).
4. Build menus and plugin format entries.
5. Initialize styles and apply GUI theme.
6. Build and activate modes/submodes.
7. Initialize status bar and event bindings.

This ordering prevents race conditions between mode creation, paper access, and
menu enable-state logic.

Qt implication:

- Keep a single deterministic startup pipeline. Do not let menus/modes/theme
  initialize opportunistically from constructors in random order.


## 2) Menu system behavior is richer than static actions

Key behavior in `init_menu()` plus `update_menu_after_selection_change()`:

- Menu entries carry state predicates (`selected`, `selected_mols`, callables).
- Enable/disable state updates on selection, clipboard, undo, redo events.
- Cascades are built dynamically (import/export registries, recent files).
- Platform-accelerator formatting is centralized in `PlatformMenuAdapter`.

Qt implication:

- Qt menu definitions must remain data-driven and support runtime state
  predicates, not just static `QAction.setEnabled(True/False)` at setup time.
- Accelerator display and key-sequence semantics should be normalized through
  one adapter layer as in Tk.


## 3) Modes are YAML-defined but runtime-aware

Toolbar and submodes are declared in
[modes.yaml](../../packages/bkchem-app/bkchem_data/modes.yaml),
loaded by [config.py](../../packages/bkchem-app/bkchem/modes/config.py),
instantiated by [mode_loader.py](../../packages/bkchem-app/bkchem/modes/mode_loader.py).

Strong behaviors:

- Group separators and ordering are YAML-driven (`toolbar_order` with `---`).
- Submode groups support row or grid layout.
- Dynamic mode groups (templates, biomolecule templates) are refreshed at
  runtime (`refresh_submode_buttons`).
- Mode switch tears down previous UI cleanly, then starts new mode.
- Edit pool visibility is per-mode (`show_edit_pool`), not global.

Qt implication:

- Keep the same declarative data model (`toolbar_order`, grouped submodes,
  dynamic groups, labels/tooltips/icons), and preserve dynamic rebuild logic.
- Avoid hardcoded per-mode UI sections in Qt window code.


## 4) Tab model is document-aware, not just widgets

`MainTabsMixin` tracks mapping between notebook tab id, frame, and `chem_paper`
instance (`_tab_name_2_frame`, `_tab_name_2_paper`), with guarded tab-change
handling to avoid re-entrant loops.

Strong behaviors:

- Prevent opening same file twice.
- Per-tab zoom controls integrated with paper zoom events.
- Proper unsaved-change close flow with save/cancel/close.
- Mode receives `on_paper_switch(old, new)` callbacks.

Qt implication:

- The active document must be a first-class object per tab, with one source of
  truth for tab<->document mapping and explicit switch callbacks.


## 5) File I/O behavior is practical and defensive

`MainFileIOMixin` does more than save/load:

- Extension-based save routing (`cdml`, `cdgz`, `svg`, `svgz`).
- Native-file open plus chemistry-format import by extension routing.
- CDML parsing supports gzip and namespace recovery.
- Import/export codecs are manifest-driven via `format_loader`.
- Import summary reports molecule/atom/bond counts.
- Recent-files list is maintained and reflected in menu cascade.

Qt implication:

- Preserve the routing and recovery behavior, not only the basic dialogs.
- Keep import/export manifest support and summary reporting.


## 6) Chemistry text I/O is integrated into draw/undo lifecycle

`MainChemistryIOMixin` (SMILES/InChI/peptide):

- Uses id sandbox during import to avoid id collisions.
- Converts through CDML elements then imports as normal objects.
- Immediately binds, draws, and records undo state.
- Validates peptide alphabet and reports clear user errors.

Qt implication:

- Qt chemistry import must pass through the same document insertion and undo
  pathways, not bypass them.


## 7) Theme switching is holistic

`theme_manager.apply_gui_theme(app)` updates:

- ttk styles, Tk palette, toolbar, submode widgets, tabs, status bar.
- per-paper canvas surround + paper background + grid redraw.
- icon recoloring and toolbar icon refresh.

Qt implication:

- Theme change must cover application chrome and drawing surface together.
- Avoid split behavior where only shell widgets switch but canvas/grid remains
  stale.


## Paper.py and paper_lib strengths to preserve

## 1) `chem_paper` is the document runtime, not only a canvas

`chem_paper` owns:

- Top-level object stack (`self.stack`).
- Selection list and selection semantics.
- Undo manager.
- Canvas-id/object registry.
- Paper properties and standards.
- Clipboard integration.
- Hex grid state and snap settings.

Qt implication:

- Qt needs a real document object with this authority. A view/scene-only design
  without document contracts causes mode, undo, save/load, and selection drift.


## 2) Event-to-mode dispatch is clean and centralized

`PaperEventsMixin` routes mouse and key input to the active mode:

- `mouse_down`, `mouse_drag`, `mouse_up`, `mouse_down2`, `mouse_down3`.
- Focus enter/leave transitions over objects while dragging.
- platform-specific wheel/shortcut bindings for zoom.
- grid toggles and snap toggles bound to keyboard shortcuts.

Qt implication:

- Preserve one dispatch layer from view events to mode interface. Hidden direct
  calls from UI actions into object internals should be avoided.


## 3) Selection semantics are domain-aware

`PaperSelectionMixin`:

- Normalizes selection to top-level containers (atom/bond -> molecule).
- Supports mode/menu predicates (`selected_mols`, `groups_selected`, etc.).
- Deletes mixed object types with appropriate per-type cleanup.
- Emits selection-changed events used by menus and status.

Qt implication:

- Qt selection must retain chemistry-aware semantics, not generic item
  selection only.


## 4) Undo boundaries are intentional

`paper.start_new_undo_record()` calls:

- `before_undo_record` (checks/normalization),
- `undo_manager.start_new_record`,
- `after_undo_record` (scrollregion updates).

Operations across modes/import/layout end with explicit undo boundaries.

Qt implication:

- Undo stack operations must align with user actions and document cleanup, not
  ad-hoc command pushes.


## 5) Zoom behavior is document-centric and user-friendly

`PaperZoomMixin` includes:

- bounded zoom range,
- center-preserving zoom in/out,
- `zoom_reset`,
- `zoom_to_fit`,
- `zoom_to_content` (excludes background and hex grid items),
- viewport recentering with inset correction.

Qt implication:

- Preserve content-aware zoom and center stability. This is one of the biggest
  UX parity markers versus a simplistic scene scale.


## 6) CDML read/write pipeline is robust

`PaperCDMLMixin`:

- transforms legacy CDML versions forward,
- parses paper + viewport + standard sections,
- loads all objects through object factory path,
- applies id sandbox and id regeneration,
- supports external-data blocks,
- computes cropping bbox excluding non-content overlays.

Qt implication:

- Qt must keep this pipeline logic intact to avoid roundtrip breakage and id
  collisions.


## 7) Layout and cleanup tooling is substantial

`PaperLayoutMixin` covers:

- align, mirror, stack ordering,
- geometry cleaning and overlap handling,
- group expansion,
- object configuration dialogs,
- deep cleanup (`mrproper`) for tab close.

Qt implication:

- Retain these as real operations, not placeholders. They are part of why Tk
  feels feature-complete.


## 8) Hex grid implementation is practical

`grid_overlay.HexGridOverlay`:

- draws honeycomb edges and vertex dots over paper bounds only,
- excludes export via `no_export` tag,
- stays between paper background and chemistry layers,
- redraws on zoom/theme/paper size changes,
- snap toggle is independent from visibility toggle.

Qt implication:

- Keep dot visibility and snap as separate controls, and preserve the layering
  and export exclusion behavior.


## Critical runtime contracts for Qt parity

These contracts should be treated as non-negotiable in Qt:

1. There is a concrete current document object with paper-like API.
2. Active mode operates against that document object.
3. Mode switch rebuilds submode UI and starts mode startup hook.
4. Submodes can be dynamic and refresh in place.
5. Menu enabled state is predicate-driven off current document selection/undo.
6. Undo/redo availability reflects real document undo stack.
7. Per-tab documents are isolated and switched via explicit callbacks.
8. CDML read/write flows through shared object factories and id management.
9. Clipboard copy/paste of chemistry objects uses document serialization path.
10. Import (SMILES/InChI/peptide/formats) inserts into document and records undo.
11. Zoom events update both visible status and per-tab controls.
12. Zoom-to-content excludes non-content overlays/background.
13. Theme switching updates both chrome and drawing surface.
14. Hex grid show/snap are separate toggles with persistent behavior.
15. Preferences and recents persist and reload consistently.


## How this maps to observed Qt failures

The current failing Qt tests and user-observed regressions are consistent with
missing contracts above:

- `document wiring` failures map to contracts 1, 2, 7.
- `cdml roundtrip` failures map to contracts 8, 10.
- `interaction` failures map to contracts 2, 3, 4, 10.
- `menu build/cascade` failures map to contract 5.
- toolbar action failures map to contracts 3, 5, 6.
- "mode selected but submodes not shown" maps to contracts 3, 4.
- "theme menu toggles directly instead of chooser" maps to contract 13.
- "hex grid feels different" maps to contract 14.


## Preserve exactly vs improve with Qt

Preserve exactly:

- YAML mode/submode model and ordering.
- Document-centric mode dispatch and undo boundaries.
- CDML + id sandbox import/export behavior.
- Selection predicates used by menus and actions.
- Per-tab document lifecycle and close/save guard flow.
- Zoom-to-fit/content semantics and status synchronization.
- Hex grid visibility/snap decoupling.

Improve in Qt (without changing behavior contracts):

- Smooth slider-driven zoom alongside existing buttons.
- Better HiDPI rendering and antialiasing.
- Stronger automated GUI smoke tests with real button presses.
- Clearer status hints and accessible action text.
- Stricter conformance tests for menu predicates and mode wiring.


## Recommended parity milestones with screenshot evidence

Each milestone should be accepted only with tests and screenshots.

Milestone 1: document and mode wiring restored

- Gate:
  - document wiring tests pass.
  - draw/edit/template operations execute through current document.
- Screenshot:
  - Qt: mode switch to draw with submode ribbon visible.
  - Qt: place atom/bond and show status mode/coords update.

Milestone 2: menu and action conformance restored

- Gate:
  - menu build/cascade/action tests pass.
  - predicate-based enable/disable verified in UI.
- Screenshot:
  - Qt File/Edit/View menus expanded, with expected enabled/disabled states.

Milestone 3: CDML and import/export roundtrip restored

- Gate:
  - CDML roundtrip tests pass.
  - open/save/import workflows usable via UI actions.
- Screenshot:
  - Qt load existing molecule, save, reopen with preserved structure.

Milestone 4: theme and grid parity restored

- Gate:
  - theme chooser UX present (not one-click toggle).
  - dark/light YAML themes applied to chrome and canvas.
  - grid show/snap behavior consistent with Tk expectations.
- Screenshot:
  - Qt light + dark screenshots with visible canvas, grid, toolbar, and status.

Milestone 5: zoom controls parity plus slider extension

- Gate:
  - -, +, 100%, Fit, Content functional.
  - slider integrated and synchronized with zoom label/status.
- Screenshot:
  - Qt at 100%, zoomed-in, fit, and content-centered states.


## Screenshot commands

Repo wrappers:

- `./take_tk_screenshot.sh`
- `./take_qt_screenshot.sh`

Direct tool usage with explicit filename (recommended for gate artifacts):

- `~/nsh/easy-screenshot/run.sh -A Python -t BKChem -f output_smoke/tk_main_parity.png`
- `~/nsh/easy-screenshot/run.sh -A Python -t BKChem-Qt -f output_smoke/qt_main_parity.png`

Use deterministic filenames so milestone evidence can be compared over time.


## Suggested immediate implementation order for Qt

1. Re-establish a concrete document contract (`view.document` equivalent and
   mode wiring through it).
2. Rebuild mode/submode runtime lifecycle to match Tk (including dynamic
   submode refresh).
3. Fix menu action registry integration with predicate-based state updates.
4. Repair CDML roundtrip path via shared document/object serialization logic.
5. Close theme chooser and hex grid parity gaps.
6. Finalize zoom controls (buttons plus slider) with screenshot-confirmed UX.


## Final note

Tk BKChem's strength is not a single feature. It is the coherence between
menus, modes, document model, and paper operations. Qt parity requires
preserving that coherence first, then layering visual and usability upgrades.
