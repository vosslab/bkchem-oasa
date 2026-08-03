# File structure

## Top-level layout

```text
bkchem-oasa/
+- packages/
|  +- oasa/                 authoritative chemistry and CDML backend
|  +- bkchem-qt.app/        sole supported PySide6 BKChem frontend
|  `- bkchem-app/           historical Tk source and fixture evidence
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
  desktop launcher. The release boundary does not include a Tk launcher.

## Package layout

### OASA backend

```text
packages/oasa/
+- oasa/                    backend library source
|  +- cdml_document.py      complete-CDML session and operations
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
|  +- undo/                 Qt-local undo retained during migration
|  +- widgets/              Qt docks, toolbars, and controls
|  +- app.py                QApplication setup and shutdown
|  +- cli.py                bkchem-qt console entry point
|  `- main_window.py        tab host and global Qt coordinator
+- tests/                   focused offscreen PySide6 tests
`- pyproject.toml           bkchem-qt package and console script
```

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
  build and dispose Qt scene objects on the frontend side of the boundary.

### Historical BKChem source

```text
packages/bkchem-app/
+- bkchem/                  retained Tk application source
|  +- actions/              historical action modules
|  +- main_lib/             historical window responsibilities
|  +- modes/                historical interaction modes
|  `- paper_lib/            historical canvas helpers
+- bkchem_data/             legacy templates, assets, locales, and DTDs
+- addons/                  legacy XML-described addons
+- tests/                   focused historical behavior evidence
`- pyproject.toml           retained legacy package metadata
```

[packages/bkchem-app/](../packages/bkchem-app/) is retained for source and
fixture reference only. It is not a supported frontend, runtime dependency,
packaging target, compatibility commitment, or parity target. New work does
not belong in this subtree.

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
- Consult [packages/bkchem-app/](../packages/bkchem-app/) only for historical
  source or fixtures needed as migration evidence. Do not add frontend,
  packaging, compatibility, or parity work there.

## Known gaps

- Source and pip installation are the delivered application paths. A frozen
  application, DMG, signing, and notarization workflow remains a separate
  delivery project rather than a requirement for this release.
- Compatibility decoding and deliberately local compatibility undo remain
  explicit isolated routes. Synchronized persistence remains backend-owned.
- Legacy source remains in the checkout as historical evidence; that retained
  layout does not expand the shipped product boundary.
