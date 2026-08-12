# Code architecture

## Overview

BKChem persists one complete CDML document through the frontend-neutral OASA
backend boundary. OASA owns the accepted document; PySide6 BKChem-Qt owns the
interactive desktop experience and disposable Qt projections of that document.

- OASA owns complete canonical CDML snapshots, monotonically increasing
  revisions, atomic commits, saved-baseline state, persistent objects, durable
  IDs, and typed failures.
- A frontend sends complete CDML candidates or a declared operation's durable
  IDs and scalar intent. It receives immutable backend values, never Qt
  objects, graphics, callbacks, or lifetime state.
- Qt owns gestures, previews, selection, dialogs, worker delivery, QObject
  lifetime, and a rebuildable scene projection. A successful backend commit is
  final even if Qt must retry projection installation.
- [packages/bkchem-qt.app/](../packages/bkchem-qt.app/) is the current
  release-selected and packaged BKChem frontend. The classic Tk frontend in
  [packages/bkchem-app/](../packages/bkchem-app/) is deprecated but retained
  as legacy source and behavioral evidence. It is not the current packaging
  target or an architecture constraint on the frontend-neutral backend.

[CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
is the normative backend behavior. [QT_CONTRACT.md](QT_CONTRACT.md) specifies
the Qt client and lifecycle behavior. This document maps that behavior to the
current implementation; it does not add another contract.

## Major components

### OASA authority

- [packages/oasa/oasa/cdml_document.py](../packages/oasa/oasa/cdml_document.py)
  provides `CDMLDocument` and `CDMLDocumentSession`. They retain typed and
  opaque CDML in source order, validate candidates in detached state, commit
  atomically, maintain history and saved baseline, and publish immutable
  snapshots and projection observations.
- `packages/oasa/oasa/cdml_presentation_insert.py`,
  `packages/oasa/oasa/cdml_presentation_properties.py`, and
  `packages/oasa/oasa/cdml_bracket.py` extend that stable document surface with
  focused presentation operations. Geometric/Bracket insertion and Configure
  patches accept plain intent without exposing the DOM.
- `cdml_molecule_insertion.py` returns root-only durable insertion facts;
  `cdml_projection_plan.py` publishes the immutable exact-revision plan that
  synchronized frontends hydrate. `cdml_bracket_pair.py` recognizes only
  structurally complete bracket pairs and supports their atomic shared patch.
- `haworth/assembly.py` provides a separate explicit three-ring backend API.
  Its callers declare durable atoms, ring membership, linkages, and faces; it
  does not infer topology, numbering, or stereochemistry. The current Qt UI
  remains the separately bounded direct two-ring route.
- [packages/oasa/oasa/cdml_conformance.py](../packages/oasa/oasa/cdml_conformance.py),
  [packages/oasa/oasa/cdml_xml.py](../packages/oasa/oasa/cdml_xml.py), and
  [packages/oasa/oasa/cdml_writer.py](../packages/oasa/oasa/cdml_writer.py)
  provide CDML assessment, hardened parsing, and controlled serialization.
- [packages/oasa/oasa/render_ops.py](../packages/oasa/oasa/render_ops.py) and
  [packages/oasa/oasa/render_lib/](../packages/oasa/oasa/render_lib/) provide
  frontend-neutral chemistry and portable render facts. OASA values remain
  plain, serialized, or immutable backend-owned data at the boundary.

### PySide6 client and projection

- [packages/bkchem-qt.app/bkchem_qt/cli.py](../packages/bkchem-qt.app/bkchem_qt/cli.py)
  exposes the `bkchem-qt` application entry point; [app.py](../packages/bkchem-qt.app/bkchem_qt/app.py)
  starts Qt and [main_window.py](../packages/bkchem-qt.app/bkchem_qt/main_window.py)
  coordinates tabs and application-wide actions.
- [packages/bkchem-qt.app/bkchem_qt/models/document_session.py](../packages/bkchem-qt.app/bkchem_qt/models/document_session.py)
  is a Qt-side client/adapter. It binds one tab to a private OASA session,
  tracks delivery and projection generations, and coordinates backend history
  navigation. It is not part of the frontend-neutral backend contract.
- [packages/bkchem-qt.app/bkchem_qt/models/projection_lifecycle.py](../packages/bkchem-qt.app/bkchem_qt/models/projection_lifecycle.py)
  defines dependency-light projection results and a session-bound delivery
  port. The port uses a public session ownership query, so queued delivery does
  not depend on `DocumentSession` internals or retarget another tab.
- [packages/bkchem-qt.app/bkchem_qt/io/cdml_document_io.py](../packages/bkchem-qt.app/bkchem_qt/io/cdml_document_io.py)
  decodes backend snapshots into detached Qt projections. Its synchronized
  route accepts one exact-revision OASA projection envelope; compatibility
  decoders remain isolated from synchronized persistence.
- [packages/bkchem-qt.app/bkchem_qt/canvas/document_projection.py](../packages/bkchem-qt.app/bkchem_qt/canvas/document_projection.py)
  and [packages/bkchem-qt.app/bkchem_qt/canvas/molecule_projection.py](../packages/bkchem-qt.app/bkchem_qt/canvas/molecule_projection.py)
  and [packages/bkchem-qt.app/bkchem_qt/canvas/graphics_retirement.py](../packages/bkchem-qt.app/bkchem_qt/canvas/graphics_retirement.py)
  create, replace, and retire scene items. Models, graphics items, and their
  QObject lifetimes are presentation-only and replaceable. Shared spline-path
  construction keeps Arrow and polyline curves geometrically consistent.
- [packages/bkchem-qt.app/bkchem_qt/actions/](../packages/bkchem-qt.app/bkchem_qt/actions/),
  [packages/bkchem-qt.app/bkchem_qt/modes/](../packages/bkchem-qt.app/bkchem_qt/modes/),
  and [packages/bkchem-qt.app/bkchem_qt/dialogs/](../packages/bkchem-qt.app/bkchem_qt/dialogs/)
  capture user intent.
  Persistent actions use the session adapter; Qt retains only the temporary
  preview and user-visible failure handling.
- Geometric property dialogs expose constrained width and labeled stroke/fill
  controls. They return detached scalar changes; the captured session adapter
  owns submission, history, reprojection, and durable selection recovery.
- The responsive shell keeps all modes reachable: compact menu at 640 and
  1024 pixels, full mode toolbar at 1280 pixels, and bounded status/zoom
  controls at all three widths. This is presentation layout, not persistence.

## Data flow

1. `bkchem-qt` starts the PySide6 application. `MainWindow` creates a Qt
   `DocumentSession` for each tab.
2. Native Open loads complete CDML into `CDMLDocumentSession`. OASA returns an
   immutable snapshot plus exact-revision presentation, paper, molecule,
   group, fragment, mark, and render observations.
3. The Qt adapter validates that one envelope, creates a detached `Document`
   and scene projection, then installs it on the GUI thread. Stable backend IDs
   may restore selection; old wrappers and XML are not retained as recovery
   state.
4. During an edit, Qt displays a transient preview. On acceptance it sends the
   expected revision with either a complete candidate or one explicit bounded
   operation using durable IDs and scalar values.
5. OASA validates and applies the request in detached state. Rejection leaves
   the snapshot, revision, history, and saved baseline unchanged; acceptance
   creates one canonical snapshot and revision.
6. Qt discards the preview and replaces the projection from the accepted
   backend result. If replacement fails, recovery reprojects the exact current
   snapshot without resubmitting the request or merging old scene state.
7. Ordinary Save writes the exact current backend snapshot and then marks that
   snapshot saved. Recovery Export writes an exact snapshot without changing
   history, dirty state, or the saved baseline.

## Current implementation mapping

- The OASA public document session is the persistent owner; Qt's
  `DocumentSession`, `Document`, molecule models, presentation models, and
  graphics items are current projection machinery.
- [packages/bkchem-qt.app/bkchem_qt/bridge/oasa_bridge.py](../packages/bkchem-qt.app/bkchem_qt/bridge/oasa_bridge.py)
  and [packages/bkchem-qt.app/bkchem_qt/bridge/worker.py](../packages/bkchem-qt.app/bkchem_qt/bridge/worker.py)
  adapt OASA public data and pure preparation results for Qt. They do not
  establish another persistent document store.
- Synchronized presentation creation and stack ordering send typed scalar intent
  to OASA; no Qt module constructs persistent presentation XML.
- [packages/bkchem-app/](../packages/bkchem-app/) retains the deprecated Tk
  code, templates, addons, and focused tests for behavioral comparison. Its
  package metadata and module code remain source material, not current
  release-delivery evidence.

## Testing and verification

- [packages/oasa/tests/](../packages/oasa/tests/) verifies backend CDML
  preservation, operations, revision behavior, and typed failures without Qt.
- [packages/bkchem-qt.app/tests/](../packages/bkchem-qt.app/tests/) verifies
  session adaptation, projection replacement, Qt actions, and lifecycle
  behavior with offscreen PySide6.
- [tests/e2e/](../tests/e2e/) contains focused end-to-end authority and
  projection-disposal checks. [tests/](../tests/) also contains repository
  structural checks such as [test_markdown_links.py](../tests/test_markdown_links.py).
- Run only the pointed test modules for the changed slice. The M6 release gate
  named in the active migration plan is a one-time integration check, not a
  routine full-suite command.

## Extension points

- Add persistent chemistry, CDML, revisioned operations, or immutable backend
  observations in [packages/oasa/oasa/](../packages/oasa/oasa/) with focused
  tests in [packages/oasa/tests/](../packages/oasa/tests/).
- Add Qt presentation, interaction, dialogs, action routing, or lifecycle
  behavior in [packages/bkchem-qt.app/bkchem_qt/](../packages/bkchem-qt.app/bkchem_qt/)
  with focused offscreen tests in [packages/bkchem-qt.app/tests/](../packages/bkchem-qt.app/tests/).
- Add a new persistent Qt feature by declaring an OASA operation or
  complete-candidate route first, then consume its immutable result in a Qt
  adapter. Do not make a Qt model, scene item, raw XML clone, or undo command
  an alternate persistent owner.
- Use [packages/bkchem-app/](../packages/bkchem-app/) to inspect legacy behavior
  or fixtures and for bounded contract or regression fixes. Keep new delivery
  features on the Qt path; Tk remains deprecated and outside current packaging.

## Known gaps

- M6 source, package, documentation, managed-screenshot, and audit checks are
  complete. The retained direct frozen-process lifecycle smoke and clean
  installed-wheel evidence support the source/pip delivery claim. Signing,
  notarization, Finder integration, and DMG delivery remain a separate future
  distribution project.
- The delivered compatibility decoder and Qt-local undo are isolated routes,
  not synchronized persistence sources. A future feature adds an OASA operation
  or complete-candidate route before it joins the synchronized release set.
- The deprecated Tk frontend remains in the repository. It is not the current
  delivery package or a feature-parity gate for the Qt release.
