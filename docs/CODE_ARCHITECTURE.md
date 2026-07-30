# Code architecture

## Overview

This repository is a three-package chemical-drawing workspace:

- [packages/oasa/](../packages/oasa/) is the reusable chemistry backend.
- [packages/bkchem-qt.app/](../packages/bkchem-qt.app/) is the active PySide6
  desktop frontend.
- [packages/bkchem-app/](../packages/bkchem-app/) is the retained Tkinter
  frontend and compatibility oracle, not the target UI architecture.

OASA owns chemistry.  The Qt frontend owns document presentation, interaction,
and Qt object lifetime.  CDML is the native persistence boundary between them;
the current division is defined by [QT_CONTRACT.md](QT_CONTRACT.md) and
[CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md).

## Major components

### OASA backend

- [packages/oasa/oasa/](../packages/oasa/oasa/) provides molecular graphs,
  atoms, bonds, stereochemistry, coordinate generation, repair operations, and
  codecs.
- [packages/oasa/oasa/cdml_writer.py](../packages/oasa/oasa/cdml_writer.py)
  serializes OASA-owned molecular CDML.
- [packages/oasa/oasa/codec_registry.py](../packages/oasa/oasa/codec_registry.py)
  selects chemistry-format codecs; the backend also supplies SVG and Cairo
  render operations.
- [packages/oasa/oasa/coords_generator.py](../packages/oasa/oasa/coords_generator.py)
  and [packages/oasa/oasa/repair_ops.py](../packages/oasa/oasa/repair_ops.py)
  implement chemistry-aware geometry work used by the Qt frontend.

### PySide6 frontend

- [packages/bkchem-qt.app/bkchem_qt/app.py](../packages/bkchem-qt.app/bkchem_qt/app.py)
  creates the application; [main_window.py](../packages/bkchem-qt.app/bkchem_qt/main_window.py)
  owns tabs, global controls, file workflow, and ordered shutdown.
- [models/document_session.py](../packages/bkchem-qt.app/bkchem_qt/models/document_session.py)
  is the per-tab ownership boundary.  A session owns exactly one `Document`,
  scene, view, mode manager, import request tokens, and import workers.
- [models/document.py](../packages/bkchem-qt.app/bkchem_qt/models/document.py)
  owns ordered document objects, CDML envelope state, clean/dirty state, and a
  `QUndoStack`.  [canvas/](../packages/bkchem-qt.app/bkchem_qt/canvas/) projects
  that model into `QGraphicsItem` objects without becoming the persistence
  authority.
- [bridge/oasa_bridge.py](../packages/bkchem-qt.app/bkchem_qt/bridge/oasa_bridge.py)
  adapts OASA molecules to Qt models.  [bridge/worker.py](../packages/bkchem-qt.app/bkchem_qt/bridge/worker.py)
  keeps parsing, coordinate generation, and component preparation off the GUI
  thread; Qt model construction remains on the GUI thread.
- [io/cdml_document_io.py](../packages/bkchem-qt.app/bkchem_qt/io/cdml_document_io.py)
  reads and writes the full CDML document envelope.  It delegates molecule
  topology to OASA while preserving paper, presentation objects, reactions,
  external data, and unrepresented XML owned by the frontend.
- [actions/](../packages/bkchem-qt.app/bkchem_qt/actions/) registers commands,
  menus, context actions, and property editing.  The `ActionRegistry` and
  [resources/menus.yaml](../packages/bkchem-qt.app/bkchem_qt/resources/menus.yaml)
  build menus; registered `QAction` shortcuts are the keyboard source of truth.
  [config/keybindings.py](../packages/bkchem-qt.app/bkchem_qt/config/keybindings.py)
  installs active-session bindings and reports conflicts.
- [modes/](../packages/bkchem-qt.app/bkchem_qt/modes/) holds drawing and editing
  modes, configured by [resources/modes.yaml](../packages/bkchem-qt.app/bkchem_qt/resources/modes.yaml).
  [undo/commands.py](../packages/bkchem-qt.app/bkchem_qt/undo/commands.py) pairs
  model and scene mutations in undoable commands.
- [resources/](../packages/bkchem-qt.app/bkchem_qt/resources/) is package-owned
  runtime data: menu and mode YAML, themes, and pixmaps.  This keeps installed
  Qt wheels independent of the legacy `bkchem_data` tree.

### Tkinter compatibility oracle

- [packages/bkchem-app/bkchem/](../packages/bkchem-app/bkchem/) is the
  compatibility implementation used to inspect established behavior, legacy
  CDML, menu definitions, modes, and interaction semantics.
- [packages/bkchem-app/bkchem/main.py](../packages/bkchem-app/bkchem/main.py)
  and [paper.py](../packages/bkchem-app/bkchem/paper.py) remain Tkinter entry
  and canvas references.  New frontend work belongs in `bkchem_qt`, not here.
- [packages/bkchem-app/bkchem_data/](../packages/bkchem-app/bkchem_data/) retains
  legacy templates, themes, locales, images, and format assets.

## Data flow

1. [bkchem_qt/cli.py](../packages/bkchem-qt.app/bkchem_qt/cli.py) starts the
   PySide6 application and `MainWindow` creates or activates a `DocumentSession`.
2. A session constructs its `Document`, `ChemScene`, `ChemView`, and mode
   manager.  `MainWindow` binds global controls only to the active session.
3. Drawing, editing, clipboard, and property actions push `QUndoCommand`
   instances.  Commands change persistent models and live projections together.
4. The OASA bridge converts Qt molecule models to and from OASA graphs.  OASA
   performs chemistry conversion and geometry; the Qt layer keeps visual state
   and selection separate.
5. Native save uses the full-document CDML codec: OASA writes molecular CDML,
   while the frontend writes the surrounding document envelope in canonical
   top-level order.  Native loads establish a clean source path; non-CDML
   imports are pathless and dirty so they require Save As.
6. A session close invalidates workers, disconnects callbacks, disposes scene
   items, clears undo history and scene state, then queues detached Qt roots for
   deletion.  This explicit lifecycle avoids PySide/Shiboken wrapper teardown
   crashes.

## Testing and verification

- [packages/oasa/tests/](../packages/oasa/tests/) covers OASA graph, codec,
  coordinate, rendering, and chemistry behavior.
- [packages/bkchem-qt.app/tests/](../packages/bkchem-qt.app/tests/) covers
  document sessions, CDML preservation, undo, menus, modes, clipboard,
  imports, workers, and offscreen Qt smoke tests.
- [packages/bkchem-app/tests/](../packages/bkchem-app/tests/) supplies focused
  Tkinter parity evidence for retained behavior.
- Qt tests use the offscreen platform and shared teardown fixtures.  The pytest
  plugin accepts `--kill-after SECONDS` to stop a genuinely hung pointed run
  with diagnostics; see [QT_CONTRACT.md](QT_CONTRACT.md).
- Repository-wide structural checks live in [tests/](../tests/), including
  [test_markdown_links.py](../tests/test_markdown_links.py).

## Extension points

- Add chemistry algorithms or codecs under [packages/oasa/oasa/](../packages/oasa/oasa/)
  and cover them in [packages/oasa/tests/](../packages/oasa/tests/).
- Add a persistent Qt feature through a `Document` model, projection, undo
  command, action, and focused Qt test; use `DocumentSession` rather than a
  process-global document.
- Add menu actions in [actions/](../packages/bkchem-qt.app/bkchem_qt/actions/)
  and menu/mode declarations in the package-owned resource YAML.
- Add Qt themes and pixmaps under [resources/](../packages/bkchem-qt.app/bkchem_qt/resources/)
  so wheels carry their runtime assets.
- Use the Tkinter package to compare behavior where no explicit Qt contract
  exists; do not add new primary UI features to the compatibility frontend.

## Known gaps

- Prefix-qualified core CDML elements remain an explicit strict-roundtrip
  compatibility boundary; extend the document codec before claiming complete
  namespace parity.
- M4 action parity is partial: remaining chemistry and document actions need
  an inventory, implementation, and focused behavior tests before release.
- Tkinter tests provide representative compatibility evidence, not proof that
  every legacy mode, dialog, and plugin has PySide6 parity.
