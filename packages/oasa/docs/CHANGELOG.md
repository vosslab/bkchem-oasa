# Changelog

## 2025-12-26
- Move packaging metadata into `pyproject.toml` and drop `setup.py`.
- Update documentation references to the GitHub repository homepage.
- Define OASA as "Open Architecture for Sketching Atoms and Molecules".

## 2025-12-24
- Modernized Python 3 support and packaging (`setup.py`, `README.md`, `oasa/__init__.py`).
- Added repo documentation for architecture and file layout
  ([CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md),
  [FILE_STRUCTURE.md](FILE_STRUCTURE.md)).
- Added developer tooling and tests (`tests/`, `mypy.ini`, `pip_requirements.txt`).
- Added smoke rendering test (`tests/smoke_png.py`) that requires `pycairo`.
- Cleaned Pyflakes findings and fixed several runtime issues across core modules.
- Moved legacy conversion logs and removed generated outputs.
- Renamed `README` to `README.md`, removed root `__init__.py`, and relocated legacy test
  runner and virtual test script under [tests](../tests).
- Renamed the conversion script to `chemical_convert.py` and documented usage in
  [USAGE.md](USAGE.md).
- Removed `tests/run_virtual_test.sh` (local unittests are sufficient).
- Moved `mypy.ini` and legacy `test.py` into [tests](../tests).
- Bumped version to 0.16beta.
- Added `pyproject.toml`, `MANIFEST.in`, and richer packaging metadata for PyPI.
- Added `__version__` to `oasa/__init__.py`.
- Standardized license references to `LICENSE`.
