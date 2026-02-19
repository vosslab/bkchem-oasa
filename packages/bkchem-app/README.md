# BKChem

BKChem is a GUI application for drawing chemical structures. It uses OASA
(Open Architecture for Sketching Atoms and Molecules) as its backend for
structure conversion and analysis.

## Install
Install from the repository:

```sh
cd packages/bkchem
pip3 install .
```

Run the application:

```sh
bkchem
```

## Batch mode and addons
- Batch mode scripting uses the `-b` flag. See [docs/BATCH_MODE.md](../../docs/BATCH_MODE.md).
- Addons live under `packages/bkchem-app/addons/` and are installed to
  `share/bkchem/addons`.

## Tests
- `tests/run_pyflakes.sh` shared linting check.
- `tests/bkchem_gui_smoke.py` basic GUI smoke test (requires Tk).
- `tests/bkchem_batch_examples.py` runs the batch script examples (requires Tk).

## Docs
- [docs/USER_GUIDE.md](../../docs/USER_GUIDE.md) BKChem manual.
- [docs/INSTALL.md](../../docs/INSTALL.md) setup and dependencies.
- [docs/EXTERNAL_IMPORT.md](../../docs/EXTERNAL_IMPORT.md) scripting from Python.
- [docs/CUSTOM_TEMPLATES.md](../../docs/CUSTOM_TEMPLATES.md) template workflow.
- [docs/CUSTOM_PLUGINS.md](../../docs/CUSTOM_PLUGINS.md) plugin/addon guidance.

## Legacy
Legacy websites are archived and reflect the Python 2 era:
- [BKChem legacy site](https://bkchem.zirael.org/)
- [OASA legacy site](https://bkchem.zirael.org/oasa_en.html)
