# Install

Install OASA and the PySide6 `bkchem-qt` frontend from this repository to get
the current BKChem application. The older Tkinter `bkchem` package remains a
compatibility oracle, not the primary frontend.

## Requirements

- Python 3.10 or newer; the repository's agent and test runtime uses Python 3.12.
- `bkchem-qt` requires PySide6, PyYAML, and OASA; pip installs the declared
  dependencies.
- OASA declares `defusedxml`, `lxml`, `pycairo`, PyYAML, RDKit, and rustworkx.
	`defusedxml` provides hardened legacy XML entry points; `lxml` handles
	CDML/CDXML parsing and controlled SVG rendering. `pycairo` supports OASA's
	Cairo PNG, PDF, and SVG renderers.
- The Tkinter compatibility package directly requires OASA, plus its own YAML
  and secure-XML readers. Pip resolves OASA's rendering and chemistry
  dependencies transitively. Install it only when comparing legacy behavior.

## Install the modern frontend

From the repository root, install OASA and the PySide6 frontend in editable
mode while developing:

```sh
python3 -m pip install -e packages/oasa -e packages/bkchem-qt.app
```

For a regular, non-editable install from the same source tree:

```sh
python3 -m pip install packages/oasa packages/bkchem-qt.app
```

## Install the compatibility oracle

The old `bkchem` command is the Tkinter frontend. It remains useful for
comparison during the migration, but is not the recommended daily application:

```sh
python3 -m pip install -e packages/bkchem-app
```

That package brings in its declared backend dependencies.

## Verify install

Confirm that the modern command-line entry point was installed:

```sh
bkchem-qt --version
```

## Qt app-builder preview

Preview one fresh, isolated Qt-only `BKChem.app` experiment without running
PyInstaller or creating files. The explicit run root must be a currently absent
path below the repository `tmp/` directory:

```sh
source source_me.sh && python3 devel/build_qt_app.py \
  --output tmp/qt_bundle/next-arm64-run --dry-run
```

The preview describes the accepted Qt bundle plan, local frontend-wheel build,
wheel-derived metadata stage for frozen `--version`, and future normal Qt
timer-exit smoke command. A real macOS arm64 build remains a controlled
experiment; this repository does not yet claim a signed, notarized, or DMG
delivery artifact.

A real build supplies an explicit numeric macOS build identity. The public
release label remains the zero-padded root `VERSION` spelling, while wheel
metadata is normalized and the bundle stores each macOS representation in its
appropriate field:

```sh
source source_me.sh && python3 devel/build_qt_app.py \
  --output tmp/qt_bundle/next-arm64-run \
  --bundle-build 26.2.1 \
  --smoke-exit 2
```

Each real build also gives PyInstaller a fresh configuration/cache parent below
that same retained run root. The builder copies the sourced environment for the
PyInstaller child and sets its `PYINSTALLER_CONFIG_DIR` there, keeping tool
state inspectable with the rest of the experiment rather than in a user-level
location.

On a real build, the wrapper first round-trips the system Chess icon through
`iconutil`. A healthy system encoder retains the standard ten-member iconset
route. When that bounded host check cannot encode a known-good iconset, the
wrapper visibly selects its deterministic Qt SVG-to-seven-size PNG-chunk ICNS
route instead. Both routes derive only from the Qt application icon source.

## Development runtime

Repository automation uses the configured Python 3.12 environment. From the
repository root, load it before running source-tree tools:

```sh
source source_me.sh
python3 -c "import oasa, bkchem_qt; print('OASA and BKChem-Qt imports OK')"
```

For PySide6 tests, set `QT_QPA_PLATFORM=offscreen` before PySide6 imports and
use only focused tests. See [QT_CONTRACT.md](QT_CONTRACT.md) for the native
wrapper teardown contract.

## Known gaps

- TODO: Verify platform-specific binary-install workflows before documenting
  installers beyond pip source installs.
