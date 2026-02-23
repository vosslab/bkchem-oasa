# Installation

This repo combines the BKChem GUI and the OASA chemistry library. The steps
below focus on running BKChem from the merged source tree. For OASA-specific
setup, see [packages/oasa/README.md](../packages/oasa/README.md).
The project homepage and documentation live in the GitHub repository; legacy
websites from the Python 2 era are archived.

## Before you start

- Python 3.10 or newer. Tested with Python 3.12.
- Tkinter (required for the GUI).
- Required Python packages: `defusedxml`, `oasa`, `pycairo`.
- Optional external tools:
  - `inchi` (InChI generation, via OASA). Required only for InChI export.

## Run BKChem from source

1. Change into the BKChem package:

```sh
cd packages/bkchem
```

2. Run the GUI:

```sh
python3 bkchem/bkchem.py
```

BKChem reads templates, pixmaps, and localization files from
`packages/bkchem-app/bkchem_data/` and loads addon descriptors from
`packages/bkchem-app/addons/`.

## System-wide install (pip)

BKChem uses `pyproject.toml` and setuptools for builds.

```sh
cd packages/bkchem
pip3 install .
```

This installs the BKChem package, data files, and a `bkchem` launcher script.
Run `bkchem` to start the GUI after install.

## macOS notes

If you use Homebrew Python, Tk is not always included by default. Install the
Tk support package and verify that Tk loads:

```sh
brew install python-tk@3.12
python3 -c "import _tkinter, tkinter; print('tk', tkinter.TkVersion, 'tcl', tkinter.TclVersion)"
```
