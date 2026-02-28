# BKChem PySide6 Frontend Rewrite - Implementation Plan

## Context

BKChem is a 2D molecular structure editor currently built on Tkinter (~25,760 lines across 89 Python files). The chemistry backend (OASA) is already separated via composition and a bridge layer. This plan creates a new parallel package `packages/bkchem-qt.app/` that reimplements the entire GUI using PySide6 (v6.10.2, already installed), targeting feature parity with the Tk app. Both packages coexist and share the OASA backend unchanged.

The user wants to push more work to the OASA backend where possible while keeping the Qt GUI responsive. This means using Qt threading (QThread/signals) or QRunnable for any OASA operations that could block (coordinate generation, file parsing, format conversion).

## Design Philosophy

- **QGraphicsView/Scene** as the canvas - atoms, bonds, graphics are `QGraphicsItem` subclasses with native hit testing, transforms, z-ordering, and selection
- **Composition over inheritance** - Qt model objects own OASA objects (`has-a`), never inherit from them
- **OASA untouched** - all chemistry stays in `packages/oasa/`; the Qt app imports it the same way the Tk app does
- **Async-heavy bridge** - OASA operations (coord generation, file I/O, format conversion) run off the main thread via `QThread` + signals to keep the UI responsive
- **Command pattern undo** - `QUndoStack` replaces the Tk snapshot system
- **Dark mode default** - modern scientific application look with `#1e1e2e` background, `#7c3aed` violet primary, white canvas
- **SVG icons** - Lucide icon set for general UI + custom chemistry-specific icons

## Scope

**In scope:** Full feature parity with the Tk app including all 18+ drawing modes, templates (system/bio/user), file I/O (CDML, SVG, MOL/SDF/SMILES/InChI/CML/CDXML import, SVG/PNG/PDF export), dialogs, undo/redo, context menus, marks, preferences, keyboard shortcuts, macOS integration.

**Not in scope:** New chemistry features, OASA modifications, mobile/web ports, QML.

## Architecture Boundaries and Ownership

```
packages/oasa/              # Chemistry backend (UNCHANGED)
packages/bkchem-app/         # Existing Tkinter frontend (UNCHANGED)
packages/bkchem-qt.app/      # NEW PySide6 frontend
  bkchem_qt/
    __init__.py              # Empty per repo style
    app.py                   # QApplication entry point
    main_window.py           # QMainWindow with menus, toolbars, status bar
    canvas/
      scene.py               # QGraphicsScene (molecule scene)
      view.py                # QGraphicsView (viewport, zoom, pan)
      items/
        atom_item.py          # QGraphicsItem for atoms
        bond_item.py          # QGraphicsItem for bonds
        arrow_item.py         # QGraphicsItem for arrows
        graphics_item.py      # QGraphicsItem for vector graphics (rect, oval, polygon)
        mark_item.py          # QGraphicsItem for marks (charge, radical, electron pair)
        text_item.py          # Rich text QGraphicsItem
    models/
      molecule_model.py       # has-a oasa.Molecule, emits QObject signals
      atom_model.py           # has-a oasa.Atom
      bond_model.py           # has-a oasa.Bond
      document.py             # Document model (molecule list, dirty state, file path)
    modes/
      base_mode.py            # Abstract mode interface
      config.py               # YAML mode definitions loader (reuse bkchem_data/modes.yaml)
      mode_loader.py          # build_all_modes() factory
      draw_mode.py            # Draw atoms and bonds
      edit_mode.py            # Select, move, delete, copy/paste
      template_mode.py        # Apply templates (system, bio, user)
      rotate_mode.py          # 2D/3D rotation
      arrow_mode.py           # Draw reaction arrows
      text_mode.py            # Add text annotations
      mark_mode.py            # Add/remove marks
      atom_mode.py            # Atom-specific editing
      bondalign_mode.py       # Alignment/mirror/invert
      bracket_mode.py         # Bracket insertion
      misc_mode.py            # Numbering, wavy lines
      plus_mode.py            # Plus symbol
      vector_mode.py          # Vector graphics (rect, oval, polygon)
      repair_mode.py          # Geometry normalization
    dialogs/
      atom_dialog.py          # Atom properties
      bond_dialog.py          # Bond properties
      scale_dialog.py         # Scale factor
      text_dialog.py          # Text properties
      arrow_dialog.py         # Arrow properties
      preferences.py          # Full preferences dialog
      about_dialog.py         # About dialog
    actions/
      file_actions.py         # File menu (new, open, save, export, recent files)
      edit_actions.py         # Edit menu (undo, redo, cut, copy, paste, select all)
      view_actions.py         # View menu (zoom, grid, dark/light mode)
      chemistry_actions.py    # Chemistry menu (SMILES, InChI, MOL import)
      object_actions.py       # Object menu (align, distribute, group)
      help_actions.py         # Help menu (about, shortcuts)
    io/
      cdml_io.py              # CDML open/save (reuses OASA CDML parser)
      format_bridge.py        # OASA codec registry integration for all chemistry formats
      export.py               # SVG (QSvgGenerator), PNG (QImage), PDF (QPrinter)
    widgets/
      toolbar.py              # Main toolbar with SVG icons
      mode_toolbar.py         # Mode selection toolbar with submodes
      edit_ribbon.py          # Context-sensitive edit pool (element entry, bond type)
      status_bar.py           # Status bar (coords, mode, zoom %)
      color_picker.py         # Color selection widget
      periodic_table.py       # Element picker popup
    themes/
      theme_manager.py        # Dark/light theme switching via QSS
      palettes.py             # QPalette color definitions
    config/
      preferences.py          # QSettings-based prefs persistence
      keybindings.py          # QShortcut keyboard shortcuts
    bridge/
      oasa_bridge.py          # Adapted OASA bridge for Qt model objects
      worker.py               # QThread workers for async OASA operations
    resources/
      icons/                  # SVG icons (Lucide set)
      themes/                 # QSS theme stylesheets
    undo/
      commands.py             # QUndoCommand subclasses
  tests/
    test_models.py            # Model wrapper unit tests
    test_cdml_load.py         # CDML loading tests
    test_undo.py              # Undo/redo tests
    test_modes.py             # Mode state machine tests
    test_io.py                # Format import/export tests
    test_export.py            # SVG/PNG/PDF export tests
  pyproject.toml              # Package metadata with PySide6 dependency
  cli.py                      # Entry point script
```

### Component-to-milestone mapping

| Component | Milestone | Patches |
| --- | --- | --- |
| `app.py`, `main_window.py`, `pyproject.toml`, `cli.py` | M1 | P1-P3 |
| `canvas/scene.py`, `canvas/view.py`, `config/preferences.py` | M1 | P4-P5 |
| `canvas/items/atom_item.py`, `canvas/items/bond_item.py` | M2 | P6-P7 |
| `models/*`, `bridge/oasa_bridge.py` | M2 | P8-P9 |
| `io/cdml_io.py`, `actions/file_actions.py` (open only) | M2 | P10 |
| `modes/base_mode.py`, `modes/config.py`, `modes/mode_loader.py` | M3 | P11 |
| `modes/edit_mode.py`, `modes/draw_mode.py` | M3 | P12-P13 |
| `undo/commands.py`, `actions/edit_actions.py` | M3 | P14 |
| `widgets/mode_toolbar.py`, `widgets/edit_ribbon.py` | M3 | P15 |
| `dialogs/atom_dialog.py`, `dialogs/bond_dialog.py` | M4 | P16-P17 |
| `dialogs/scale_dialog.py`, `dialogs/text_dialog.py`, `dialogs/arrow_dialog.py` | M4 | P18 |
| `canvas/items/arrow_item.py`, `canvas/items/text_item.py` | M4 | P19 |
| `modes/template_mode.py`, template manager integration | M4 | P20 |
| Context menu system | M4 | P21 |
| `io/cdml_io.py` (save), `io/format_bridge.py` | M5 | P22-P23 |
| `io/export.py` (SVG/PNG/PDF) | M5 | P24 |
| `canvas/items/mark_item.py`, marks system | M5 | P25 |
| Remaining modes (rotate, repair, bracket, vector, etc.) | M5 | P26 |
| `bridge/worker.py` async OASA operations | M5 | P27 |
| `themes/`, `config/keybindings.py` | M6 | P28-P29 |
| `dialogs/preferences.py`, `widgets/toolbar.py` polish | M6 | P30-P31 |
| `resources/icons/`, macOS integration, packaging | M6 | P32-P33 |
| Feature parity audit + final fixes | M6 | P34 |

---

## Milestone 1: Application Shell and Canvas Foundation

**Objective:** Runnable PySide6 app with QGraphicsView canvas, zoom, pan, grid, and proper packaging.

**Depends on:** None (greenfield)

**Entry criteria:** PySide6 importable (`python3 -c "import PySide6"`)

**Exit criteria:**
- `source source_me.sh && python -m bkchem_qt` launches a window
- QMainWindow with menu bar (File, Edit, View, Object, Chemistry, Help), toolbar placeholder, status bar
- QGraphicsView with mouse wheel zoom (cursor-centered), middle-click pan, Ctrl+0 reset
- Grid overlay togglable via View menu
- Window geometry persists via QSettings
- Dark theme applied by default
- pyflakes clean

### Workstream 1.1: Package scaffold and app shell

**Goal:** Create `packages/bkchem-qt.app/` with Python packaging and runnable entry point

**Owner:** Coder A

**Work packages:**
- WP-1.1.1: Create `pyproject.toml` - PySide6 dependency, version `26.02a1` synced with repo, `[project.scripts] bkchem-qt = "bkchem_qt.cli:main"`
- WP-1.1.2: Create `bkchem_qt/__init__.py` (empty docstring only), `bkchem_qt/__main__.py`, `cli.py` (argparse launcher with `-v`, `-h`, file args), `app.py` (QApplication subclass)
- WP-1.1.3: Update `source_me.sh` to add `packages/bkchem-qt.app` to PYTHONPATH
- WP-1.1.4: Add PySide6 to `pip_requirements.txt`

**Touch points:** `packages/bkchem-qt.app/`, `source_me.sh`, `pip_requirements.txt`

**Acceptance:** `source source_me.sh && python -m bkchem_qt --help` prints usage

### Workstream 1.2: Main window and canvas (parallelizable)

**Goal:** QMainWindow with menus, QGraphicsView canvas, status bar, dark theme

**Owner:** Coder A (sequential after 1.1)

**Work packages:**
- WP-1.2.1: `main_window.py` - QMainWindow with menu bar stubs, empty toolbar area, QTabWidget for documents
- WP-1.2.2: `widgets/status_bar.py` - custom status bar showing mouse coords, current mode, zoom %
- WP-1.2.3: `canvas/view.py` - QGraphicsView with wheel zoom (cursor-centered), middle-click pan, Ctrl+0 reset, coord reporting to status bar
- WP-1.2.4: `canvas/scene.py` - QGraphicsScene with configurable background, optional grid overlay, snap-to-grid
- WP-1.2.5: `config/preferences.py` - QSettings wrapper (window geometry, recent files, grid on/off, theme)
- WP-1.2.6: `themes/theme_manager.py` - dark/light QSS theme with palette from design spec, `themes/palettes.py`

**Touch points:** `bkchem_qt/main_window.py`, `bkchem_qt/canvas/`, `bkchem_qt/widgets/`, `bkchem_qt/themes/`, `bkchem_qt/config/`

**Acceptance:** Window launches with menus, canvas zooms/pans, grid toggles, dark theme, settings persist

### Verification (Milestone 1)

```bash
source source_me.sh && python -m bkchem_qt
# Visual: window with dark theme, menus, canvas, status bar
# Interact: wheel zoom, middle-click pan, Ctrl+0 reset, View > Grid toggle
source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/ -v
source source_me.sh && python -m pytest tests/test_pyflakes_code_lint.py -k bkchem_qt
```

**Screenshot verification:** `/Users/vosslab/nsh/easy-screenshot/run.sh`

---

## Milestone 2: Molecule Display (Read-Only)

**Objective:** Load CDML files and render molecules as interactive QGraphicsItems with correct atom labels, bond types, and colors.

**Depends on:** M1-WP-1.2.3, M1-WP-1.2.4 (canvas must exist)

**Entry criteria:** M1 exits clean

**Exit criteria:**
- File > Open loads `.cdml` / `.svg` files via QFileDialog
- Molecules display with correct atom labels (element symbols, charges, hydrogens)
- Single/double/triple/wedge/hashed/aromatic bonds render correctly
- Atoms and bonds are individually selectable QGraphicsItems with hover highlight
- All existing CDML test files display without errors
- Side-by-side screenshot comparison with Tk version passes visual inspection

### Workstream 2.1: Chemistry model wrappers

**Goal:** Qt-side composition wrappers around OASA objects with QObject signals

**Owner:** Coder A

**Work packages:**
- WP-2.1.1: `models/atom_model.py` - has-a `oasa.atom_lib.Atom`, exposes symbol/charge/coords/valency/isotope, emits `property_changed` signal
- WP-2.1.2: `models/bond_model.py` - has-a `oasa.bond_lib.Bond`, exposes order/type/vertices/aromatic
- WP-2.1.3: `models/molecule_model.py` - has-a `oasa.molecule_lib.Molecule`, manages atom/bond model collections, delegates graph algorithms, factory methods create Qt model types
- WP-2.1.4: `models/document.py` - holds list of molecule_models + arrows + graphics, dirty flag, file path, undo stack reference

**Touch points:** `bkchem_qt/models/`

**Interfaces needed:** Model objects emit Qt signals when properties change; items listen

### Workstream 2.2: QGraphicsItems (parallel with 2.1 after interface agreement)

**Goal:** Visual atom and bond items using QPainter

**Owner:** Coder B

**Work packages:**
- WP-2.2.1: `canvas/items/atom_item.py` - QGraphicsItem rendering element symbol via QPainter, show/hide logic, hydrogen label positioning (center-first/center-last), selection highlight, hover effect, position change notification for bond updates
- WP-2.2.2: `canvas/items/bond_item.py` - QGraphicsItem rendering single/double/triple bonds as lines, wedge as filled triangle, hashed as parallel lines, aromatic as dashed inner line, endpoint tracking, selection highlight
- WP-2.2.3: Port bond rendering geometry from OASA `render_ops` system (`LineOp`, `PolygonOp`, `PathOp`) to QPainter calls - reuse `render_lib.bond_ops.build_bond_ops()` and `render_lib.molecule_ops.build_vertex_ops()` output

**Touch points:** `bkchem_qt/canvas/items/`

**Key reuse:** OASA's `render_lib` produces render ops (LineOp, PolygonOp, PathOp, TextOp) that translate directly to `QPainter.drawLine()`, `QPainter.drawPolygon()`, `QPainter.drawPath()`, `QPainter.drawText()` calls. This means the rendering geometry is computed by OASA (backend), and the Qt frontend only translates ops to QPainter calls.

### Workstream 2.3: Bridge and CDML loading

**Goal:** Load CDML files into the Qt scene via bridge layer

**Owner:** Coder A (after 2.1)

**Work packages:**
- WP-2.3.1: `bridge/oasa_bridge.py` - adapted from `packages/bkchem-app/bkchem/oasa_bridge.py`, creates Qt model objects instead of Tk objects. Key functions: `oasa_mol_to_qt_mol()`, `oasa_atom_to_qt_atom()`, `oasa_bond_to_qt_bond()`
- WP-2.3.2: `io/cdml_io.py` - CDML file reader using OASA's CDML parser, creates model objects, adds QGraphicsItems to scene, handles coordinate conversion (CDML cm -> scene units)
- WP-2.3.3: Wire File > Open to QFileDialog + CDML loader in `actions/file_actions.py`

**Touch points:** `bkchem_qt/bridge/`, `bkchem_qt/io/`, `bkchem_qt/actions/`

### Verification (Milestone 2)

```bash
source source_me.sh && python -m bkchem_qt testfile.svg
# Visual: molecules display correctly with atom labels, bond types, colors
# Compare with Tk version: /Users/vosslab/nsh/easy-screenshot/run.sh
source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_cdml_load.py -v
source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_models.py -v
```

---

## Milestone 3: Core Interaction (Edit + Draw + Undo)

**Objective:** Users can select/move/delete atoms and bonds (edit mode), draw new molecules (draw mode), and undo/redo all operations.

**Depends on:** M2 (items must be displayable and selectable)

**Entry criteria:** M2 exits clean

**Exit criteria:**
- Edit mode: click-select, Shift+click multi-select, rubber-band select, move, Delete key, copy/paste
- Draw mode: click empty -> new atom, click atom -> start bond, drag atom-to-empty -> new atom+bond, drag atom-to-atom -> new bond
- Undo/redo via Ctrl+Z / Ctrl+Shift+Z with QUndoStack
- Mode switching via mode toolbar with icons and tooltips
- Element entry field and bond type selector in edit ribbon

### Workstream 3.1: Mode framework

**Goal:** Abstract mode system with event dispatch

**Owner:** Coder A

**Work packages:**
- WP-3.1.1: `modes/base_mode.py` - abstract base: `mouse_press/release/move(pos, button, modifiers)`, `key_press/release(key, modifiers)`, `activate()/deactivate()`, `cursor` property
- WP-3.1.2: `modes/config.py` - load mode definitions from `bkchem_data/modes.yaml` (reuse existing YAML)
- WP-3.1.3: Mode dispatcher in `canvas/view.py` - converts QMouseEvent/QKeyEvent to mode method calls with scene coordinates
- WP-3.1.4: `widgets/mode_toolbar.py` - toolbar with mode buttons, SVG icons, tooltips, emits mode-change signal
- WP-3.1.5: `widgets/edit_ribbon.py` - context-sensitive ribbon showing element entry, bond type selector, angle step, etc. based on current mode's submodes

### Workstream 3.2: Edit and draw modes (parallel after 3.1.1 interface)

**Goal:** Two essential interactive modes

**Owner:** Coder B

**Work packages:**
- WP-3.2.1: `modes/edit_mode.py` - click select (itemAt), Shift+click multi-select, rubber-band (QGraphicsView built-in), drag to move, Delete key, Ctrl+C/V copy/paste via QMimeData
- WP-3.2.2: `modes/draw_mode.py` - click empty -> create atom (current element from edit ribbon), click existing atom -> start bond, drag -> preview bond, release on empty -> new atom+bond, release on atom -> bond between, submode: element/bond type from edit ribbon

### Workstream 3.3: Undo system (parallel with 3.2)

**Goal:** QUndoStack-based undo/redo

**Owner:** Coder A (after 3.1)

**Work packages:**
- WP-3.3.1: `undo/commands.py` - QUndoCommand subclasses: `AddAtomCommand`, `RemoveAtomCommand`, `AddBondCommand`, `RemoveBondCommand`, `MoveAtomsCommand` (with mergeId for continuous drags), `ChangePropertyCommand` (generic)
- WP-3.3.2: Wire QUndoStack to Edit > Undo/Redo menu items and Ctrl+Z / Ctrl+Shift+Z shortcuts

### Verification (Milestone 3)

```bash
source source_me.sh && python -m bkchem_qt
# Manual: switch modes, draw molecule, select/move atoms, undo/redo, delete
source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_modes.py -v
source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_undo.py -v
```

---

## Milestone 4: Dialogs, Templates, Arrows/Text, Context Menus

**Objective:** Property dialogs, template placement, arrow/text graphics, right-click context menus.

**Depends on:** M3 (interaction framework must work)

**Entry criteria:** M3 exits clean

**Exit criteria:**
- Double-click atom -> atom properties dialog (symbol, charge, isotope, valency, show/hide, font, color)
- Double-click bond -> bond properties dialog (order, type, width, color, stereo)
- Template mode: click to place functional group templates (system, biomolecule, user)
- Arrow and text modes functional
- Right-click context menus for atoms, bonds, molecules
- All dialogs match Tk functionality

### Work packages (single workstream, some parallelizable)

- WP-4.1: `dialogs/atom_dialog.py` - QDialog with form layout for atom properties
- WP-4.2: `dialogs/bond_dialog.py` - QDialog for bond properties
- WP-4.3: `dialogs/scale_dialog.py`, `dialogs/text_dialog.py`, `dialogs/arrow_dialog.py`
- WP-4.4: `canvas/items/arrow_item.py` - arrow QGraphicsItem with configurable heads, spline curves (port from `arrow_lib.py`)
- WP-4.5: `canvas/items/text_item.py` - rich text QGraphicsItem using QTextDocument (replaces BkFtext)
- WP-4.6: `modes/template_mode.py` + template manager integration - load group templates from OASA `known_groups`, place on click near existing atom. Reuse `temp_manager.py` logic for system/bio/user templates
- WP-4.7: Context menu system - QMenu on right-click, dispatched to atom/bond/molecule-specific menus

### Verification (Milestone 4)

```bash
source source_me.sh && python -m bkchem_qt
# Manual: double-click atom/bond -> edit properties, apply template, draw arrow/text
# Manual: right-click context menus
source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/ -v
```

---

## Milestone 5: File I/O, Marks, Remaining Modes, Async Bridge

**Objective:** Full file format support, chemical marks, all remaining modes, and async OASA operations.

**Depends on:** M4 (dialogs and templates must work)

**Entry criteria:** M4 exits clean

**Exit criteria:**
- CDML save round-trips cleanly (open -> edit -> save -> reopen = same)
- Import: MOL, SDF, SMILES, InChI, CML, CDXML via OASA codec registry
- Export: SVG, PNG, PDF
- Marks: charge circles, radical dots, electron pairs, lone pairs
- All 18 modes from Tk version functional
- OASA operations (coord generation, file parsing) run async via QThread, GUI stays responsive during heavy operations (e.g., loading large molecules)

### Work packages

- WP-5.1: `io/cdml_io.py` save path - serialize Qt scene to CDML XML
- WP-5.2: `io/format_bridge.py` - integrate OASA `codec_registry` for all chemistry format import/export. Use `QThread` worker for format conversion to keep GUI responsive
- WP-5.3: `io/export.py` - SVG via QSvgGenerator, PNG via QImage/QPainter, PDF via QPrinter
- WP-5.4: `canvas/items/mark_item.py` - charge marks, radical dots, electron pairs as QGraphicsItems attached to parent atom items
- WP-5.5: `canvas/items/graphics_item.py` - vector graphics (rect, oval, polygon, polyline)
- WP-5.6: Remaining modes: `rotate_mode.py` (2D/3D rotation), `repair_mode.py` (normalize geometry via OASA), `bondalign_mode.py` (align/mirror/invert), `bracket_mode.py`, `misc_mode.py` (numbering, wavy), `plus_mode.py`, `vector_mode.py`
- WP-5.7: `bridge/worker.py` - QThread-based workers for: coordinate generation (`calculate_coords`), file parsing, format conversion. Emit progress signals for status bar. This is the key piece for "give OASA more work while keeping GUI responsive"

### Verification (Milestone 5)

```bash
source source_me.sh && python -m bkchem_qt
# Round-trip: open CDML, edit, save, reopen, verify unchanged
# Import .mol, .sdf, .smi files
# Export SVG, open in browser; export PNG; export PDF
# Screenshot comparison with Tk version: /Users/vosslab/nsh/easy-screenshot/run.sh
# Test async: load a large molecule, verify GUI stays responsive
source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_io.py -v
source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_export.py -v
```

---

## Milestone 6: Polish, Themes, Shortcuts, Packaging

**Objective:** Production-quality UI with polished dark/light themes, full keyboard shortcuts, preferences dialog, macOS integration, and packaging.

**Depends on:** M5 (all features must work)

**Entry criteria:** M5 exits clean

**Exit criteria:**
- Dark and light themes with smooth switching
- All keyboard shortcuts from Tk version work
- Preferences dialog persists all settings via QSettings
- macOS: native menu bar, Cmd shortcuts, .app bundle
- Splash screen, about dialog with version/license
- All pyflakes clean, all tests pass
- Feature parity checklist 100% complete

### Work packages

- WP-6.1: `themes/theme_manager.py` polish - dark/light QSS with smooth transition, system theme detection
- WP-6.2: `config/keybindings.py` - QShortcut-based shortcuts, configurable via preferences
- WP-6.3: `dialogs/preferences.py` - full preferences dialog (appearance, drawing defaults, file locations, shortcuts)
- WP-6.4: `widgets/toolbar.py` polish - SVG icons (Lucide set), tooltips, separator groups, proper sizing (min 32x32 touch targets)
- WP-6.5: `dialogs/about_dialog.py` - version, license, credits
- WP-6.6: macOS integration - native menu bar, Cmd+Q, `py2app` or `pyinstaller` bundle
- WP-6.7: `resources/icons/` - complete SVG icon set for all modes and actions
- WP-6.8: Feature parity audit - compare every Tk feature against Qt implementation, file gaps as issues

### Verification (Milestone 6)

```bash
source source_me.sh && python -m bkchem_qt
# Visual: toggle dark/light mode, verify all elements themed
# Keyboard: test all shortcuts
# macOS: verify native menu bar, Cmd shortcuts
# Screenshot: /Users/vosslab/nsh/easy-screenshot/run.sh
source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/ -v
source source_me.sh && python -m pytest tests/test_pyflakes_code_lint.py -k bkchem_qt
```

---

## UI Design Specification

### Color palette (dark mode default)

| Role | Color | Usage |
| --- | --- | --- |
| Background | `#1e1e2e` | Window, panel background |
| Surface | `#2a2a3e` | Cards, toolbar, dialogs |
| Primary | `#7c3aed` | Active mode highlight, selection |
| Secondary | `#06b6d4` | Chemical bonds accent, links |
| Text primary | `#e2e8f0` | Body text |
| Text muted | `#94a3b8` | Labels, captions |
| Canvas background | `#ffffff` | Always white (chemistry accuracy) |
| Success | `#22c55e` | Valid states |
| Warning | `#f59e0b` | Warnings |
| Error | `#ef4444` | Errors |

### Typography

- UI font: System default (San Francisco on macOS)
- Atom labels: Monospace for chemical formulas
- Minimum toolbar button: 32x32px

### Layout

- Floating toolbar at top (detachable)
- Mode toolbar at left or top (configurable)
- Canvas fills remaining space
- Status bar at bottom: mouse coords, current mode name, zoom %
- Optional dockable property panel (sidebar)
- Tab bar for multiple documents

### Interaction

- Cursor changes per mode (crosshair for draw, arrow for edit, hand for pan)
- Hover highlights on atoms/bonds (subtle glow or outline)
- Smooth zoom (150-300ms ease via QTimeLine or QPropertyAnimation)
- Rubber-band selection rectangle
- All clickable elements have pointer cursor

---

## Async OASA Bridge Design

To keep the GUI responsive while pushing work to OASA:

```python
# bridge/worker.py
class OasaWorker(QThread):
    finished = Signal(object)  # result
    error = Signal(str)        # error message
    progress = Signal(int)     # 0-100

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        result = self._func(*self._args, **self._kwargs)
        self.finished.emit(result)
```

**Operations to run async:**
- `coords_generator.calculate_coords()` - can be slow for large molecules
- `codec.read_file()` / `codec.write_file()` - file I/O
- `oasa_bridge.oasa_mol_to_qt_mol()` - conversion for large molecules
- `render_lib.build_bond_ops()` / `build_vertex_ops()` - render op generation

**UI pattern:** Show progress in status bar, disable editing during async ops, re-enable on completion.

---

## Existing Files to Reuse

| Source file | Reuse strategy |
| --- | --- |
| `bkchem-app/bkchem/oasa_bridge.py` | Adapt: create Qt model types instead of Tk types |
| `bkchem-app/bkchem/data.py` | Copy: key/symbol mappings are pure data |
| `bkchem-app/bkchem/messages.py` | Copy: UI text strings |
| `bkchem-app/bkchem/CDML_versions.py` | Copy: version constants |
| `bkchem-app/bkchem_data/modes.yaml` | Reuse directly: mode definitions for Qt toolbar |
| `bkchem-app/bkchem_data/pixmaps/src/*.svg` | Copy: SVG icons for modes/actions |
| `oasa/oasa/render_lib/` | Call directly: render ops -> QPainter translation |
| `oasa/oasa/codec_registry.py` | Call directly: format import/export |
| `oasa/oasa/coords_generator.py` | Call directly: coordinate generation |

---

## Parallelization Opportunities

| Parallel pair | Why independent |
| --- | --- |
| M1: WP-1.2.3 (canvas/view) + WP-1.2.6 (themes) | Different files, merge at main_window |
| M2: WP-2.1 (models) + WP-2.2 (items) | Agree interface first, implement independently |
| M3: WP-3.2 (edit/draw modes) + WP-3.3 (undo) | Orthogonal subsystems |
| M4: WP-4.1-4.3 (dialogs) + WP-4.4-4.5 (items) | Independent widget trees |
| M5: WP-5.1-5.3 (file I/O) + WP-5.4 (marks) | Different subsystems |
| M6: WP-6.1 (themes) + WP-6.2 (keybindings) | Appearance vs interaction |

---

## Risk Register

| Risk | Impact | Trigger | Mitigation |
| --- | --- | --- | --- |
| Bond rendering fidelity | High | QPainter draws differently than Tk Canvas | Use OASA render_ops as source of truth; translate LineOp/PolygonOp/PathOp to QPainter faithfully |
| Rich text rendering | Medium | BkFtext heavily uses Tk font metrics | Use QTextDocument + QFontMetrics; verify formula display |
| CDML round-trip breakage | High | Qt coordinate handling differs | Unit test: load in Tk, save, load in Qt, compare; match coordinate conversion exactly |
| PySide6 version compatibility | Low | API changes between versions | Pin `PySide6>=6.7` in pyproject.toml |
| macOS native feel | Medium | Qt apps look non-native | Use native dialogs, Cmd shortcuts, QMacStyle hints |
| Large molecule performance | Medium | OASA coord generation blocks UI | Async bridge workers (WP-5.7); progress reporting |
| Async race conditions | Medium | Multiple workers modifying scene | Serialize scene mutations; workers return results, main thread applies |

---

## Migration and Compatibility

- Both `bkchem-app` (Tk) and `bkchem-qt.app` (Qt) coexist in the monorepo
- OASA is unchanged and shared
- CDML file format is the interop format - files saved by either app must load in the other
- No breaking changes to existing packages
- The Qt app is a new package, not a replacement (yet)
- Version synced across all packages (`26.02a1`)

---

## Patch Plan

- Patch 1: Package scaffold (`pyproject.toml`, `cli.py`, `__init__.py`, `__main__.py`)
- Patch 2: App and main window (`app.py`, `main_window.py`, menu stubs)
- Patch 3: Status bar widget (`widgets/status_bar.py`)
- Patch 4: QGraphicsView with zoom/pan (`canvas/view.py`)
- Patch 5: QGraphicsScene with grid + preferences + dark theme (`canvas/scene.py`, `config/preferences.py`, `themes/`)
- Patch 6: Atom QGraphicsItem (`canvas/items/atom_item.py`)
- Patch 7: Bond QGraphicsItem (`canvas/items/bond_item.py`)
- Patch 8: Chemistry model wrappers (`models/atom_model.py`, `bond_model.py`, `molecule_model.py`)
- Patch 9: Bridge layer (`bridge/oasa_bridge.py`)
- Patch 10: CDML loader + File > Open (`io/cdml_io.py`, `actions/file_actions.py`)
- Patch 11: Mode framework (`modes/base_mode.py`, `config.py`, `mode_loader.py`, view dispatcher)
- Patch 12: Edit mode (`modes/edit_mode.py`)
- Patch 13: Draw mode (`modes/draw_mode.py`)
- Patch 14: Undo system (`undo/commands.py`, `actions/edit_actions.py`)
- Patch 15: Mode toolbar + edit ribbon (`widgets/mode_toolbar.py`, `widgets/edit_ribbon.py`)
- Patch 16: Atom properties dialog (`dialogs/atom_dialog.py`)
- Patch 17: Bond properties dialog (`dialogs/bond_dialog.py`)
- Patch 18: Scale/text/arrow dialogs
- Patch 19: Arrow + text QGraphicsItems
- Patch 20: Template mode + manager
- Patch 21: Context menu system
- Patch 22: CDML save path
- Patch 23: Format import bridge (codec registry integration)
- Patch 24: SVG/PNG/PDF export
- Patch 25: Marks system (charge, radical, electron pair)
- Patch 26: Remaining modes (rotate, repair, bracket, vector, misc, plus, atom, bondalign)
- Patch 27: Async OASA workers (`bridge/worker.py`)
- Patch 28: Dark/light theme polish
- Patch 29: Keyboard shortcuts system
- Patch 30: Preferences dialog
- Patch 31: Polished toolbar with SVG icons
- Patch 32: macOS integration + .app bundle
- Patch 33: Icon set (SVG)
- Patch 34: Feature parity audit + final fixes

---

## Open Questions

1. **Icon set:** Lucide for general UI + custom chemistry SVG icons? Or port the existing 100+ SVG pixmaps from `bkchem_data/pixmaps/src/`?
2. **Property panel:** Dockable sidebar for atom/bond properties (modern), or popup dialogs only (traditional like Tk version)? Can decide during M4.
3. **i18n:** Port the gettext/locale system from Tk app, or defer localization?
4. **Periodic table popup:** Full periodic table widget for element selection, or simple combo box?

---

## Documentation Close-out

Per milestone, update:
- `docs/CHANGELOG.md` with additions under appropriate sections
- `docs/FILE_STRUCTURE.md` to include new package
- `docs/INSTALL.md` to include PySide6 dependency
- `docs/USAGE.md` with `bkchem-qt` launch instructions
- `README.md` to mention the Qt frontend
