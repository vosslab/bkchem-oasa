# BKChem and OASA

A Qt chemical drawing application and Python chemistry backend for scientists and educators who need editable molecular documents, with CDML as the durable source of truth.

## One durable drawing, rebuildable UI

BKChem-Qt is an interactive chemical drawing application whose complete persistent
document is backend-authoritative: OASA owns canonical CDML, while Qt handles
interaction and a disposable scene projection that can be rebuilt from that CDML.
This keeps the editable document separate from any one window, canvas item, or
temporary preview.

The PySide6 screenshot below shows a real drawing session and demonstrates that the
visible scene is the editor's projection of the document, not the document itself.

<!-- screenshots:begin (managed by screenshot-docs) -->
![BKChem-Qt showing an OASA-loaded benzene reaction with an arrow, condition text, and plus object](docs/screenshots/bkchem_qt_cdml_projection.png)
<!-- screenshots:end -->

## Choose the right package

| If you need | Use | Why |
| --- | --- | --- |
| Draw, edit, open, and save a molecular document | BKChem-Qt | The shipped PySide6 desktop application provides the interactive workflow. |
| Use chemistry, CDML, conversion, or analysis from Python | OASA | The library owns chemistry behavior and the authoritative complete-CDML document. |

BKChem-Qt sends persistent intent to OASA, then replaces its scene from the accepted
backend result. That boundary makes native documents durable even when a Qt projection
is discarded and rebuilt.

## Status and format boundaries

Pip source installation is supported. BKChem-Qt is the current release-selected and
packaged frontend; Qt provides interaction and a replaceable scene projection, while
OASA remains the authoritative complete-CDML backend. The classic Tk frontend is
deprecated but intentionally retained as legacy source and behavioral reference. It
is not the current release installation or packaging target.

Native editable Save is CDML. OASA-supported imports create a pathless, dirty CDML
session until Save As chooses a new `.cdml` destination. SVG, PNG, and PDF are rendered
exports, not editable Save formats. A signed, notarized, DMG, or frozen application
artifact is not currently claimed.

The managed screenshot is a reproducible PySide6 capture of a native CDML session
opened through the public application path and projected from OASA's backend snapshot.
The more detailed [docs/CAPABILITIES.md](docs/CAPABILITIES.md) visual tour covers
persistent drawing objects and verified Haworth chemistry. Refresh the complete
managed screenshot catalog from the repository root with:

```sh
source source_me.sh && ./devel/take_qt_screenshot.sh --kill-after 3
```

## Quick start

Use Python 3.10 or newer with a desktop session suitable for PySide6. From a source
checkout, install OASA and the current BKChem frontend:

```sh
python3 -m pip install packages/oasa packages/bkchem-qt.app
bkchem-qt --version
bkchem-qt
```

The version command prints the installed BKChem-Qt version; the final command opens an
empty drawing session. The complete dependency and editable-install guidance is in
[docs/INSTALL.md](docs/INSTALL.md).

## Native CDML workflow

Open an editable CDML drawing from the command line:

```sh
bkchem-qt example.cdml
```

Draw or edit in the window, then choose **File > Save As** and give the document a
`.cdml` name. Reopen that file with the same command to continue editing. Ordinary Save
writes OASA's exact current backend snapshot and marks that revision saved only after
the write succeeds. [docs/USAGE.md](docs/USAGE.md) describes native Open, imports,
Recovery Export, and rendered SVG, PNG, and PDF export.

## What the Qt application supports

- Create, open, save, close, and reopen the implemented native CDML document path.
- Draw molecules; place atoms and templates; edit supported structures and presentation
  objects; and use undo and redo.
- Work with arrows, text, plus signs, brackets, vectors, marks, clipboard operations,
  supported chemistry helpers, and artifact export.
- Import supported chemistry formats through OASA, then save the editable result as a
  new native CDML document.

The release-facing action inventory distinguishes supported work from explicitly
unsupported historical variants. The accepted Qt/OASA composition boundary, clean
dependency-isolated installation, installed round-trip evidence, and tracked managed
screenshots are complete. Frozen application, DMG, signing, and notarization delivery
remain separate from the supported source and pip installation.

## Documentation

- [docs/CAPABILITIES.md](docs/CAPABILITIES.md) provides the reproducible visual tour
  and a concise current-capability map.
- [docs/INSTALL.md](docs/INSTALL.md) gives source installation, verification, and
  current delivery limits.
- [docs/USAGE.md](docs/USAGE.md) explains launching, native file handling, imports,
  recovery, and rendered export.
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) maps backend ownership, Qt
  projection, and the live data flow.
- [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) identifies the shipped packages,
  retained deprecated source, and extension locations.
- [docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md](docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  defines complete-CDML persistence, revisions, and backend operations.
- [docs/QT_CONTRACT.md](docs/QT_CONTRACT.md) defines Qt session, projection, save, and
  lifecycle behavior.
- [docs/active_plans/active/cdml_backend_authority_migration_2026-07-27.md](docs/active_plans/active/cdml_backend_authority_migration_2026-07-27.md)
  records the accepted authority boundary and remaining release gates.

## Provenance and license

This repository continues the BKChem and OASA open-source projects while delivering the
current Qt application path. OASA and BKChem-Qt declare GPL-2.0-only licensing;
see [LICENSE](LICENSE) for the GNU General Public License, version 2.
