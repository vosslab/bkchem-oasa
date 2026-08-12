# File structure

## Top-level layout

```text
bkchem-oasa/
+- packages/
|  +- oasa/                 authoritative chemistry and CDML backend
|  +- bkchem-qt.app/        current PySide6 release frontend
|  `- bkchem-app/           deprecated, retained Tk frontend source
+- docs/                    contracts, plans, architecture, and user docs
+- tests/                   repository-wide structural and E2E checks
+- tools/                   focused developer utilities
+- devel/                   maintenance and release-preparation scripts
+- launch_bkchem-qt_gui.sh  local Qt development launcher
+- source_me.sh             local development environment setup
`- VERSION                  shared version registry
```

- [README.md](../README.md) is the repository landing page.
- [pip_requirements.txt](../pip_requirements.txt),
  [pip_requirements-dev.txt](../pip_requirements-dev.txt), and
  [pip_extras.txt](../pip_extras.txt) declare Python dependencies.
- [source_me.sh](../source_me.sh) sets the repository Python path for local
  pointed checks.
- [launch_bkchem-qt_gui.sh](../launch_bkchem-qt_gui.sh) is the current local
  desktop launcher. The deprecated Tk source remains present, but the current
  release boundary does not package a Tk launcher.

## Package layout

### OASA backend

```text
packages/oasa/
+- oasa/                    backend library source
|  +- cdml_document.py      complete-CDML session and operations
|  +- cdml_bracket.py       rectangular/round bracket insertion
|  +- cdml_bracket_pair.py  bracket-pair observation and atomic patch eligibility
|  +- cdml_molecule_insertion.py  root-only molecule insertion facts
|  +- cdml_projection_plan.py  immutable synchronized projection facts
|  +- cdml_presentation_insert.py  direct-root presentation insertion
|  +- cdml_presentation_properties.py  focused presentation-root patches
|  +- codecs/               molecule-format codecs
|  +- graph/                graph primitives and backends
|  +- haworth/              carbohydrate layout helpers
|  `- render_lib/           portable rendering geometry and operations
+- oasa_data/               package data used by OASA
+- tests/                   backend behavior and preservation tests
`- pyproject.toml           oasa distribution metadata
```

- [packages/oasa/oasa/cdml_document.py](../packages/oasa/oasa/cdml_document.py)
  is the persistent-document authority. It owns snapshots, revisioned atomic
  operations, history, saved baseline, durable identities, and typed failures.
- `packages/oasa/oasa/cdml_presentation_properties.py`
  owns bounded Arrow and shared geometric-root property patches without
  frontend or toolkit dependencies.
- `packages/oasa/oasa/cdml_presentation_insert.py` owns typed geometric intent,
  drawing-standard application, durable IDs, and atomic direct-root insertion.
- `packages/oasa/oasa/cdml_bracket.py` owns bracket style, proportional
  control-point geometry, standard-derived strokes, and atomic pair insertion.
- `packages/oasa/oasa/cdml_bracket_pair.py` defines durable pair identity from
  two marked ordinary polylines; malformed and unmarked polylines are not
  inferred as pairs.
- `packages/oasa/oasa/cdml_projection_plan.py` is the frontend-neutral,
  exact-revision hydration value. Synchronized Qt never parses canonical CDML.
- [packages/oasa/oasa/cdml_xml.py](../packages/oasa/oasa/cdml_xml.py) and
  [packages/oasa/oasa/cdml_writer.py](../packages/oasa/oasa/cdml_writer.py)
  provide hardened CDML parsing and controlled output.
- [packages/oasa/oasa/render_ops.py](../packages/oasa/oasa/render_ops.py) and
  [packages/oasa/oasa/render_lib/](../packages/oasa/oasa/render_lib/) keep
  render facts independent of a particular frontend toolkit.

### PySide6 BKChem frontend

```text
packages/bkchem-qt.app/
+- bkchem_qt/
|  +- actions/              action registration and handlers
|  +- bridge/               OASA adapters and background preparation
|  +- canvas/               scene projection, items, and retirement
|  +- config/               frontend preferences and keybinding configuration
|  +- dialogs/              Qt dialogs
|  +- io/                   snapshot hydration, candidates, clipboard, I/O
|  +- models/               disposable projection and tab-session models
|  +- modes/                interactive drawing and editing modes
|  +- resources/            packaged menus, themes, and pixmaps
|  +- setup/                application and mode setup helpers
|  +- themes/               Qt theme definitions and helpers
|  +- undo/                 synchronized backend history; legacy-local compatibility isolated
|  +- widgets/              Qt docks, toolbars, and controls
|  +- app.py                QApplication setup and shutdown
|  +- cli.py                bkchem-qt console entry point
|  `- main_window.py        tab host and global Qt coordinator
+- tests/                   focused deterministic Qt-package tests
`- pyproject.toml           bkchem-qt package and console script
```

The dialogs folder includes the detached geometric width/stroke/fill form;
session adapters, rather than widgets or projected models, own its commit.
Drawing modes submit scalar insertion intent; persistent XML construction and
presentation-stack ordering remain in OASA.

The Qt shell uses responsive mode and status widgets. At 640 and 1024 pixels
the mode chooser is compact; at 1280 pixels it is a full toolbar. The same
registered actions remain reachable at every supported width.

- [packages/bkchem-qt.app/pyproject.toml](../packages/bkchem-qt.app/pyproject.toml)
  defines the `bkchem-qt` console entry point and packages the Qt runtime
  resources.
- [packages/bkchem-qt.app/bkchem_qt/models/document_session.py](../packages/bkchem-qt.app/bkchem_qt/models/document_session.py)
  is the per-tab Qt client/adapter to OASA, not a backend-contract type.
- [packages/bkchem-qt.app/bkchem_qt/models/projection_lifecycle.py](../packages/bkchem-qt.app/bkchem_qt/models/projection_lifecycle.py)
  holds projection-delivery outcomes and the generation-bound port without Qt
  or OASA imports.
- [packages/bkchem-qt.app/bkchem_qt/io/cdml_document_io.py](../packages/bkchem-qt.app/bkchem_qt/io/cdml_document_io.py)
  turns one OASA snapshot envelope into a detached Qt projection.
- [packages/bkchem-qt.app/bkchem_qt/canvas/document_projection.py](../packages/bkchem-qt.app/bkchem_qt/canvas/document_projection.py)
  and [packages/bkchem-qt.app/bkchem_qt/canvas/molecule_projection.py](../packages/bkchem-qt.app/bkchem_qt/canvas/molecule_projection.py)
  and [packages/bkchem-qt.app/bkchem_qt/canvas/graphics_retirement.py](../packages/bkchem-qt.app/bkchem_qt/canvas/graphics_retirement.py)
  build and dispose Qt scene objects on the frontend side of the boundary;
  `canvas/spline_path.py` supplies shared Arrow/polyline curve construction.

### Deprecated Tk BKChem source

```text
packages/bkchem-app/
+- bkchem/                  retained Tk application source
|  +- actions/              legacy action modules
|  +- main_lib/             legacy window responsibilities
|  +- modes/                legacy interaction modes
|  `- paper_lib/            legacy canvas helpers
+- bkchem_data/             legacy templates, assets, locales, and DTDs
+- addons/                  legacy XML-described addons
+- tests/                   focused legacy behavior evidence
`- pyproject.toml           retained legacy package metadata
```

[packages/bkchem-app/](../packages/bkchem-app/) is a deprecated but retained
frontend. It supplies legacy behavior and fixtures and may receive bounded
contract or regression fixes. It is not the current release packaging target;
new user-facing delivery work belongs on the Qt path. It preserves a complete
marked bracket pair during compatibility load/paste; malformed or unmarked
polylines stay independent rather than being guessed into a pair.

## Documentation map

- [CAPABILITIES.md](CAPABILITIES.md) shows the current application and backend
  surface through reproducible Qt screenshots.
- [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) maps ownership and live data
  flow.
- [CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  defines frontend-neutral persistent behavior, operations, snapshots, and
  typed failures.
- [QT_CONTRACT.md](QT_CONTRACT.md) defines PySide6 session, projection,
  lifecycle, and delivery behavior.
- [OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md](OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md)
  describes coordinate-generation methods.
- [active_plans/](active_plans/) contains current migration and release work;
  [archive/](archive/) retains closed reference plans.

## Generated artifacts

- `.gitignore` excludes Python bytecode directories through `__pycache__/`.
- Build output is excluded through `build/`, `dist/`, `sdist/`, `*.egg`,
  `*.egg-info/`, and `site/`.
- Local smoke and report output is excluded through `output_smoke/`, `tmp/`,
  `output*/`, `report_*.txt`, `oasa_capabilities_sheet.*`, and
  `*Python_*.png`.
- [devel/dist_clean.sh](../devel/dist_clean.sh) is the targeted cleanup entry
  point for generated distribution and test artifacts.

## Where to add work

- Add persistent CDML behavior, chemistry operations, durable-ID allocation,
  revision/history behavior, and backend observations in
  [packages/oasa/oasa/](../packages/oasa/oasa/), with focused tests in
  [packages/oasa/tests/](../packages/oasa/tests/).
- Add Qt presentation, interaction, dialogs, action routing, projection, and
  QObject-lifetime behavior in
  [packages/bkchem-qt.app/bkchem_qt/](../packages/bkchem-qt.app/bkchem_qt/),
  with focused tests in
  [packages/bkchem-qt.app/tests/](../packages/bkchem-qt.app/tests/).
- Put a persistent Qt feature's authoritative operation or complete-candidate
  route in OASA first. The Qt side then submits plain intent and displays the
  accepted immutable result; it must not become a second persistence store.
- Put cross-package developer utilities in [tools/](../tools/) or
  [devel/](../devel/), durable documentation in [docs/](.), and repository-wide
  checks in [tests/](../tests/).
- Consult [packages/bkchem-app/](../packages/bkchem-app/) for legacy source or
  fixtures and make bounded contract or regression fixes there when needed.
  Keep new packaging and user-facing delivery work on the Qt path.

## Known gaps

- Source and pip installation are the delivered application paths. A frozen
  application, DMG, signing, and notarization workflow remains a separate
  delivery project rather than a requirement for this release.
- Compatibility decoding and deliberately local compatibility undo remain
  explicit isolated routes. Synchronized persistence remains backend-owned.
- Deprecated Tk source remains in the checkout; that retained layout does not
  expand the current shipped product boundary.
