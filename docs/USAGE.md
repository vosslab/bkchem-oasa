# Usage

`bkchem-qt` is the current PySide6 chemical-drawing frontend over the OASA
backend. The older Tkinter `bkchem` command remains a compatibility oracle
while feature parity is completed.

## Quick start

Launch an empty drawing session:

```sh
bkchem-qt
```

Open one or more native CDML documents at launch:

```sh
bkchem-qt example.cdml second-example.cdml
```

The CLI form is `bkchem-qt [files...]`. Use `--version` to print the installed
frontend version.

## Files and saving

- Native `.cdml` is the only save target currently supported by `bkchem-qt`.
- A suffixless Save As name receives `.cdml`; other save suffixes are refused.
- Opening native CDML creates a clean, path-backed document session.
- File import supports `.mol`, `.sdf`, `.smi`, `.smiles`, `.cdxml`, and `.cml`
  through OASA. Generic `.xml` is not an import option because XML alone does
  not identify a chemistry format.
  Imported chemistry becomes a dirty, pathless session, so use Save As to
  create a CDML document instead of overwriting the original source.
- The app opens ordinary files in separate sessions and activates an existing
  tab when that source is already open.

## Typical workflow

1. Start `bkchem-qt` and sketch a structure, or open a `.cdml` document.
2. Use File > Import for a Molfile, SDF, SMILES, CDXML, or CML input.
3. Select File > Save As and choose a `.cdml` name for imported work.
4. Reopen the saved CDML document to continue editing in a clean session.

See [QT_CONTRACT.md](QT_CONTRACT.md) for session, save, import, and teardown
semantics. The backend/frontend data boundary is specified in
[CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md).

## OASA and the Tkinter oracle

OASA is also available as a Python library after installation:

```python
import oasa
```

Use `bkchem` only when comparing the legacy Tkinter behavior against the
modern frontend. Its batch scripting is described in
[BATCH_MODE.md](BATCH_MODE.md); it is not the primary PySide6 workflow.

## macOS delivery preview

For the next isolated Qt-only app experiment, provide a new path below the
repository `tmp/` directory:

```sh
source source_me.sh && python3 devel/build_qt_app.py \
  --output tmp/qt_bundle/next-arm64-run --dry-run
```

The preview prints deterministic icon, local frontend-wheel, metadata-staging,
PyInstaller, and normal timer-exit smoke stages without writing the requested
run root. A later controlled macOS arm64 run may use the same command without
`--dry-run`; it builds one local frontend wheel into that retained run root,
stages its complete matching distribution metadata, then starts source-tree
PyInstaller analysis. Every run root is single-use and preserved for inspection.
The PyInstaller subprocess receives a copied environment with its configuration
and cache parent rooted in that same run directory, so the experiment retains
all of its builder-owned state together.

The real-build icon encoder is host-adaptive: a bounded system Chess-icon
round-trip selects the existing standard `iconutil` path when that encoder is
healthy. A failed self-test is reported and selects a validated multiresolution
ICNS container built from seven Qt-rendered copies of the current application
SVG. The preview does not run the self-test, renderer, or encoder.

## Current limits

- Group expansion, fragment workflows, and conversion to linear form do not
  yet have complete PySide6 action parity.
- The current migration boundary and completion evidence are tracked in
  [BKCHEM_QT_COMPLETION_PLAN_2026-07-27.md](active_plans/active/BKCHEM_QT_COMPLETION_PLAN_2026-07-27.md).

## Exporting a rendered page

Use File > Export to write the current scene as SVG, PNG, or PDF. These are
rendered outputs for sharing or publication; continue saving the editable
document as CDML.
