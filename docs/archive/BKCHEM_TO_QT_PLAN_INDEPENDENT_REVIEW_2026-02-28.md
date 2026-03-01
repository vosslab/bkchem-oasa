# BKCHEM_TO_QT_PLAN Independent Review (2026-02-28)

## Review Scope
- Plan under review: `docs/active_plans/BKCHEM_TO_QT_PLAN.md`
- Review mode: Independent manager audit against plan gates, sequencing, and closure criteria
- Decision basis: Code evidence, tests, screenshots, and documentation alignment

## Findings (Severity-ranked)

### P1 - Core M3 conformance break: draw/edit/undo depend on `view.document`, but `ChemView` never exposes it
- Plan reference: `docs/active_plans/BKCHEM_TO_QT_PLAN.md:294`
- Evidence:
  - `packages/bkchem-qt.app/bkchem_qt/modes/draw_mode.py:365`
  - `packages/bkchem-qt.app/bkchem_qt/modes/draw_mode.py:380`
  - `packages/bkchem-qt.app/bkchem_qt/modes/edit_mode.py:410`
  - `packages/bkchem-qt.app/bkchem_qt/canvas/view.py:21`
  - `packages/bkchem-qt.app/bkchem_qt/main_window.py:68`
- Risk/impact: draw/create/delete/undo paths can no-op or diverge from document state
- Recommended corrective action: add explicit `ChemView.document` wiring and regression tests for click-draw plus undo/redo

### P1 - Main toolbar actions are effectively dead because callbacks look up `on_*` methods that do not exist
- Plan references:
  - `docs/active_plans/BKCHEM_TO_QT_PLAN.md:299`
  - `docs/active_plans/BKCHEM_TO_QT_PLAN.md:445`
- Evidence:
  - `packages/bkchem-qt.app/bkchem_qt/widgets/toolbar.py:100`
  - `packages/bkchem-qt.app/bkchem_qt/widgets/toolbar.py:112`
  - `packages/bkchem-qt.app/bkchem_qt/main_window.py:355`
- Risk/impact: UI appears complete but primary controls do nothing; severe UX regression vs Tk
- Recommended corrective action: connect toolbar actions to implemented handlers (`_on_*`) or add public wrappers

### P1 - Save/round-trip gate is not implemented
- Plan reference: `docs/active_plans/BKCHEM_TO_QT_PLAN.md:391`
- Evidence:
  - `packages/bkchem-qt.app/bkchem_qt/main_window.py:190` (Save action created but not wired)
  - `packages/bkchem-qt.app/bkchem_qt/io/cdml_io.py:70`
  - `packages/bkchem-qt.app/bkchem_qt/io/cdml_io.py:84` (`pass`)
- Risk/impact: no reliable persistence path; Milestone 5 exit criteria cannot be met
- Recommended corrective action: implement save action, CDML serialization, and reopen round-trip tests

### P2 - M4 interaction gates are unfulfilled: dialogs/context menu/template placement are mostly placeholders or unwired
- Plan reference: `docs/active_plans/BKCHEM_TO_QT_PLAN.md:353`
- Evidence:
  - `packages/bkchem-qt.app/bkchem_qt/modes/edit_mode.py:203`
  - `packages/bkchem-qt.app/bkchem_qt/actions/context_menu.py:34`
  - `packages/bkchem-qt.app/bkchem_qt/main_window.py:35` (import only)
  - `packages/bkchem-qt.app/bkchem_qt/modes/template_mode.py:121`
- Risk/impact: key interaction parity vs Tk is not present
- Recommended corrective action: wire real dialog invocation, context menu registration, and template placement mutations

### P2 - "All 18 modes functional" claim does not match code; several modes are explicit stubs
- Plan reference: `docs/active_plans/BKCHEM_TO_QT_PLAN.md:395`
- Evidence:
  - `packages/bkchem-qt.app/bkchem_qt/modes/vector_mode.py:44`
  - `packages/bkchem-qt.app/bkchem_qt/modes/bracket_mode.py:42`
  - `packages/bkchem-qt.app/bkchem_qt/modes/plus_mode.py:41`
  - `packages/bkchem-qt.app/bkchem_qt/modes/repair_mode.py:42`
  - `packages/bkchem-qt.app/bkchem_qt/modes/misc_mode.py:41`
- Risk/impact: feature-parity and milestone completion claims are overstated
- Recommended corrective action: implement mode behaviors or formally de-scope and update gates/claims

### P2 - Async-heavy bridge design is not integrated into file/coord workflows
- Plan references:
  - `docs/active_plans/BKCHEM_TO_QT_PLAN.md:14`
  - `docs/active_plans/BKCHEM_TO_QT_PLAN.md:396`
- Evidence:
  - `packages/bkchem-qt.app/bkchem_qt/actions/file_actions.py:73` (sync read path)
  - `packages/bkchem-qt.app/bkchem_qt/bridge/worker.py:8` (workers exist but are not integrated)
- Risk/impact: large imports can block UI; design-philosophy mismatch
- Recommended corrective action: route parsing/coord conversion through worker pipeline with UI progress and apply-on-main-thread semantics

### P2 - Verification gate mismatch: planned test matrix and screenshot protocol are not satisfied by current evidence
- Plan references:
  - `docs/active_plans/BKCHEM_TO_QT_PLAN.md:210`
  - `docs/active_plans/BKCHEM_TO_QT_PLAN.md:280`
  - `docs/active_plans/BKCHEM_TO_QT_PLAN.md:339`
  - `docs/active_plans/BKCHEM_TO_QT_PLAN.md:417`
- Evidence:
  - Only `packages/bkchem-qt.app/tests/test_qt_gui_smoke.py` exists in Qt test dir
  - Smoke tests use `QWidget.grab()` and bypass core interaction paths
  - Screenshot parity mismatch is clear between:
    - `Qt_Screenshot.png`
    - `Tk_Screenshot.png`
- Risk/impact: completion claims are not backed by gate-quality evidence
- Recommended corrective action: add milestone-targeted tests and require side-by-side capture via `/Users/vosslab/nsh/easy-screenshot/run.sh` for milestone confirmation

### P3 - Documentation close-out is inconsistent with plan requirements
- Plan reference: `docs/active_plans/BKCHEM_TO_QT_PLAN.md:643`
- Evidence:
  - Qt package not reflected in `README.md`, `docs/INSTALL.md`, `docs/USAGE.md`, `docs/FILE_STRUCTURE.md`
  - Progress tracker stale: `refactor_progress.md:3`
- Risk/impact: manager visibility and release readiness assessment are unreliable
- Recommended corrective action: align status docs to actual gate state before any completion claim

## Open Questions and Unresolved Decisions
1. Should 2026-02-28 changelog milestone claims be downgraded to partial completion until hard gates pass?
2. What exact parity scenario should be canonical for screenshot gates (same file, zoom, grid, mode, and window size)?
3. Is dark mode still a hard default requirement, or is follow-system-theme now accepted policy?

## Test Gaps and Residual Risk
1. Runtime validation in this shell is blocked: `source source_me.sh && python3` resolves to Python 3.9.6 without `PySide6` and without `pytest`; planned Qt gate tests could not be executed in this environment.
2. Existing Qt smoke tests do not validate the core failing paths above (draw/edit/undo wiring, save round-trip, M4 interaction flows, async responsiveness).

## Screenshot Confirmation Requirement
Final milestone confirmation must include side-by-side captures via:
- `/Users/vosslab/nsh/easy-screenshot/run.sh`

Required evidence format:
1. Tk and Qt screenshots for the same molecule/document state
2. Same zoom level, mode, grid visibility, and comparable viewport framing
3. Stored with dated filenames and referenced in milestone closure notes

## Documentation Close-out Pass Result
- Status: Not passed

## Closure Recommendation
- Decision: Not complete

## Coder Action Directive (Execution-ready, prioritized)

### 1) Repair core draw/edit/undo document wiring
- Owner role: Coder
- File paths:
  - `packages/bkchem-qt.app/bkchem_qt/main_window.py`
  - `packages/bkchem-qt.app/bkchem_qt/canvas/view.py`
  - `packages/bkchem-qt.app/bkchem_qt/modes/draw_mode.py`
  - `packages/bkchem-qt.app/bkchem_qt/modes/edit_mode.py`
- Commands:
  - `source source_me.sh && python3 -m pytest packages/bkchem-qt.app/tests/test_modes.py -k "draw or edit or undo" -v`
- Acceptance check:
  - Drawing creates atoms/bonds, delete works, Ctrl+Z/Ctrl+Shift+Z replay correctly

### 2) Wire main toolbar actions to real handlers
- Owner role: Coder
- File paths:
  - `packages/bkchem-qt.app/bkchem_qt/widgets/toolbar.py`
  - `packages/bkchem-qt.app/bkchem_qt/main_window.py`
- Commands:
  - `source source_me.sh && python3 -m pytest packages/bkchem-qt.app/tests/test_qt_gui_smoke.py -k "launch or mode_cycling" -v`
- Acceptance check:
  - Toolbar New/Open/Save/Undo/Redo trigger implemented behavior

### 3) Implement save and CDML round-trip gate
- Owner role: Coder
- File paths:
  - `packages/bkchem-qt.app/bkchem_qt/io/cdml_io.py`
  - `packages/bkchem-qt.app/bkchem_qt/main_window.py`
- Commands:
  - `source source_me.sh && python3 -m pytest packages/bkchem-qt.app/tests/test_io.py -k "cdml and roundtrip" -v`
- Acceptance check:
  - Open-edit-save-reopen preserves molecule graph and coordinates

### 4) Complete M4 interaction wiring
- Owner role: Coder
- File paths:
  - `packages/bkchem-qt.app/bkchem_qt/modes/edit_mode.py`
  - `packages/bkchem-qt.app/bkchem_qt/actions/context_menu.py`
  - `packages/bkchem-qt.app/bkchem_qt/main_window.py`
  - `packages/bkchem-qt.app/bkchem_qt/modes/template_mode.py`
- Commands:
  - `source source_me.sh && python3 -m pytest packages/bkchem-qt.app/tests/test_modes.py -k "double_click or context or template" -v`
- Acceptance check:
  - Double-click opens dialogs; right-click context menus open and act; template mode mutates scene/document

### 5) Resolve mode stubs or formally de-scope
- Owner role: Coder
- File paths:
  - `packages/bkchem-qt.app/bkchem_qt/modes/vector_mode.py`
  - `packages/bkchem-qt.app/bkchem_qt/modes/bracket_mode.py`
  - `packages/bkchem-qt.app/bkchem_qt/modes/plus_mode.py`
  - `packages/bkchem-qt.app/bkchem_qt/modes/repair_mode.py`
  - `packages/bkchem-qt.app/bkchem_qt/modes/misc_mode.py`
- Commands:
  - `source source_me.sh && python3 -m pytest packages/bkchem-qt.app/tests/test_modes.py -k "vector or bracket or plus or repair or misc" -v`
- Acceptance check:
  - Each mode either performs its declared operation or is explicitly re-scoped in plan/changelog

### 6) Integrate async workers into heavy operations
- Owner role: Coder
- File paths:
  - `packages/bkchem-qt.app/bkchem_qt/bridge/worker.py`
  - `packages/bkchem-qt.app/bkchem_qt/actions/file_actions.py`
  - relevant import/coord entry points
- Commands:
  - `source source_me.sh && python3 -m pytest packages/bkchem-qt.app/tests/test_io.py -k async -v`
- Acceptance check:
  - Heavy import/coord generation runs off UI thread with progress, no UI freeze

### 7) Enforce screenshot parity gate before milestone closure
- Owner role: Reviewer
- File paths:
  - `docs/active_plans/BKCHEM_TO_QT_PLAN.md`
  - `Qt_Screenshot.png`
  - `Tk_Screenshot.png`
- Commands:
  - `/Users/vosslab/nsh/easy-screenshot/run.sh -A "BKChem-Qt" -t "BKChem-Qt" -f Qt_parity.png`
  - `/Users/vosslab/nsh/easy-screenshot/run.sh -A "BKChem" -t "BKChem" -f Tk_parity.png`
- Acceptance check:
  - Same molecule, same zoom/grid/mode, parity judged against plan gate and attached to closure evidence

### 8) Reconcile documentation with actual status
- Owner role: Release manager
- File paths:
  - `docs/CHANGELOG.md`
  - `refactor_progress.md`
  - `README.md`
  - `docs/INSTALL.md`
  - `docs/USAGE.md`
  - `docs/FILE_STRUCTURE.md`
- Commands:
  - documentation update pass + attach gate command transcripts
- Acceptance check:
  - No completion claim remains without passing gate evidence
