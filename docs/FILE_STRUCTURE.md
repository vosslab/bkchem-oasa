# File structure

## Top-level layout

```text
bkchem-oasa/
+- packages/
|  +- oasa/                 chemistry backend package
|  +- bkchem-qt.app/        active PySide6 frontend package
|  `- bkchem-app/           retained Tkinter compatibility package
+- docs/                    contracts, plans, and project documentation
+- tests/                   repository-wide test and style checks
+- tools/                   focused developer utilities
+- devel/                   release and maintenance scripts
+- launch_bkchem-qt_gui.sh  Qt launcher
+- launch_bkchem-tk_gui.sh  Tkinter compatibility launcher
+- source_me.sh             local development environment setup
`- VERSION                  shared release version
```

- [README.md](../README.md) introduces BKChem and OASA.
- [pip_requirements.txt](../pip_requirements.txt),
  [pip_requirements-dev.txt](../pip_requirements-dev.txt), and
  [pip_extras.txt](../pip_extras.txt) record Python dependencies.
- [devel/dist_clean.sh](../devel/dist_clean.sh) removes generated package and
  test artifacts after local builds and checks.

## Package layout

### OASA backend

```text
packages/oasa/
+- oasa/                    library source
|  +- codecs/               registered molecule-format codecs
|  +- graph/                graph primitives and backends
|  +- haworth/              carbohydrate layout and rendering helpers
|  `- render_lib/           shared rendering geometry and operations
+- oasa_data/               package data for backend behavior
+- tests/                   backend unit, parity, and smoke tests
+- docs/                    OASA package documentation
`- pyproject.toml           oasa distribution metadata
```

- [packages/oasa/oasa/cdml_writer.py](../packages/oasa/oasa/cdml_writer.py)
  owns molecular CDML serialization.
- [packages/oasa/oasa/codec_registry.py](../packages/oasa/oasa/codec_registry.py)
  resolves chemistry codecs.
- [packages/oasa/oasa/coords_generator.py](../packages/oasa/oasa/coords_generator.py)
  and [packages/oasa/oasa/repair_ops.py](../packages/oasa/oasa/repair_ops.py)
  expose geometry operations used by the frontend.

### PySide6 BKChem frontend

```text
packages/bkchem-qt.app/
+- bkchem_qt/
|  +- actions/              QAction registry, menus, and command handlers
|  +- bridge/               OASA adapters and background workers
|  +- canvas/               scene, view, projection, and graphics items
|  +- config/               preferences, geometry units, keybindings
|  +- dialogs/              Qt dialogs
|  +- io/                   CDML, clipboard, import, and export boundary
|  +- models/               document, session, molecule, atom, and bond state
|  +- modes/                drawing and editing interaction modes
|  +- resources/            packaged YAML, themes, and pixmaps
|  +- undo/                 QUndoCommand implementations
|  +- widgets/              docks, toolbars, ribbons, and controls
|  +- app.py                QApplication setup and shutdown
|  +- cli.py                bkchem-qt console entry point
|  `- main_window.py        tab host and global UI coordinator
+- tests/                   offscreen PySide6 behavior and lifecycle tests
`- pyproject.toml           bkchem-qt distribution metadata
```

- [packages/bkchem-qt.app/bkchem_qt/models/document_session.py](../packages/bkchem-qt.app/bkchem_qt/models/document_session.py)
  owns one tab's document, scene, view, mode manager, and import lifetime.
- [packages/bkchem-qt.app/bkchem_qt/io/cdml_document_io.py](../packages/bkchem-qt.app/bkchem_qt/io/cdml_document_io.py)
  preserves the full Qt document envelope around OASA chemistry.
- [packages/bkchem-qt.app/bkchem_qt/resources/menus.yaml](../packages/bkchem-qt.app/bkchem_qt/resources/menus.yaml)
  and [packages/bkchem-qt.app/bkchem_qt/resources/modes.yaml](../packages/bkchem-qt.app/bkchem_qt/resources/modes.yaml)
  configure menus and modes; `ActionRegistry` and `QAction` shortcuts provide
  the executable and keybinding source of truth.

### Tkinter compatibility frontend

```text
packages/bkchem-app/
+- bkchem/                  retained Tkinter implementation
|  +- actions/              legacy action modules
|  +- main_lib/             main-window responsibilities
|  +- modes/                legacy interaction modes
|  `- paper_lib/            Tk Canvas document helpers
+- bkchem_data/             templates, themes, locales, images, and DTDs
+- addons/                  legacy XML-described addons
+- tests/                   focused compatibility tests
`- pyproject.toml           bkchem distribution metadata
```

- [packages/bkchem-app/bkchem/main.py](../packages/bkchem-app/bkchem/main.py)
  and [packages/bkchem-app/bkchem/paper.py](../packages/bkchem-app/bkchem/paper.py)
  remain the Tkinter reference entry point and canvas.
- This package is a compatibility oracle for behavior and old documents; new
  primary GUI work belongs under `packages/bkchem-qt.app/bkchem_qt/`.

## Documentation map

- [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) describes ownership and data flow.
- [QT_CONTRACT.md](QT_CONTRACT.md) specifies PySide6 document, signal, worker,
  save, and teardown contracts.
- [CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  defines the backend/frontend CDML boundary.
- [OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md](OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md)
  records coordinate-generation methods.
- [active_plans/](active_plans/) contains active plans, audits, reports,
  decisions, and workstreams; [archive/](archive/) holds closed reference plans.

## Generated artifacts

- Python bytecode and test caches: `__pycache__/`, `.pytest_cache/`, and `*.pyc`.
- Package-build output: `build/`, `dist/`, `*.egg-info/`, and `*.dist-info/`.
- Local reports and smoke output: `report_*.txt` and `output_smoke/`.
- [devel/dist_clean.sh](../devel/dist_clean.sh) is the targeted cleanup entry
  point; these artifacts are not source files.

## Where to add work

- Add chemistry and format behavior to [packages/oasa/oasa/](../packages/oasa/oasa/)
  with a focused test in [packages/oasa/tests/](../packages/oasa/tests/).
- Add Qt UI behavior to [packages/bkchem-qt.app/bkchem_qt/](../packages/bkchem-qt.app/bkchem_qt/)
  with an offscreen test in [packages/bkchem-qt.app/tests/](../packages/bkchem-qt.app/tests/).
- Add retained Tkinter compatibility evidence to
  [packages/bkchem-app/tests/](../packages/bkchem-app/tests/), rather than
  treating it as the primary implementation path.
- Add cross-package tooling to [tools/](../tools/) or [devel/](../devel/), and
  durable documentation to [docs/](.).

## Known gaps

- Prefix-qualified core CDML remains a known strict-roundtrip limitation.
- M4 action completion is partial; use the current action inventory and focused
  tests before marking command parity complete.
- Tkinter compatibility coverage is representative, not exhaustive, so an
  untested legacy behavior requires direct comparison before porting.
