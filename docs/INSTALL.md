# Install

Install OASA and the PySide6 `bkchem-qt` application from this source tree.
OASA is the chemistry library and authoritative persistent CDML backend;
BKChem-Qt presents and interacts with its disposable scene projection.

## Requirements

- Python 3.10 or newer.
- pip able to install the declared OASA and PySide6 dependencies. These include
  RDKit, rustworkx, lxml, pycairo, PyYAML, and PySide6.
- A desktop session suitable for PySide6.

## Install

From the repository root, install the backend and the only shipped BKChem
frontend:

```sh
python3 -m pip install packages/oasa packages/bkchem-qt.app
```

For source-tree development, use editable installs instead:

```sh
python3 -m pip install -e packages/oasa -e packages/bkchem-qt.app
```

`packages/bkchem-app/` is retained only as historical source and fixture
reference during the migration. It is not a current-user installation path.

## Verify install

Confirm that pip installed the Qt application entry point:

```sh
bkchem-qt --version
```

The command prints the installed BKChem-Qt version without starting the GUI.

## Installed lifecycle validation

Before a release claim, run the installed Qt authoritative round-trip from an
isolated environment. The runner rejects source-checkout package origins,
executes its scenario inside the Qt event loop, and records the exact terminal
phase in a caller-owned receipt:

```sh
source source_me.sh && mkdir -p tmp/installed_qt_roundtrip_check
env -u PYTHONPATH QT_QPA_PLATFORM=offscreen \
  /path/to/isolated/venv/bin/python -W error \
  tests/e2e/e2e_installed_qt_authoritative_roundtrip.py \
  --kill-after 3 \
  --output tmp/installed_qt_roundtrip_check \
  --receipt tmp/installed_qt_roundtrip_check/receipt.json
```

Use a new output directory per run. A completed receipt confirms native Open,
backend-authoritative Arrow commit, exact-snapshot Save, clean close, reopen,
and controlled Qt retirement. It does not establish a signed, notarized, or
DMG delivery artifact.

## Known limitations

- This repository documents pip source installs. A signed, notarized, or DMG
  application artifact is not currently claimed. A direct frozen-executable
  lifecycle smoke is retained as bounded builder evidence; Finder registration,
  signing, notarization, and DMG delivery belong to a separate distribution
  project.
- The app saves editable documents only as `.cdml`; see [USAGE.md](USAGE.md)
  for imports, rendered exports, and Recovery Export.
