# File structure

## Top level
- `oasa/` package source code.
- `oasa_data/` packaged data assets for OASA.
- `docs/` documentation set for repo-wide conventions and guides.
- `tests/` lightweight test scripts and static check runners.
- `README.md` project overview and usage notes.
- `LICENSE` license text (stored at the repo root).
- `pyproject.toml` packaging metadata and build entry point.
- `pyproject.toml` build system configuration.
- `MANIFEST.in` packaging include rules.
- `chemical_convert.py` conversion helper script.
- `.gitignore` and `.git/` version control metadata.

## Package layout (`oasa/`)
- `oasa/__init__.py` public API aggregation and feature availability flags.
- `oasa/graph/` graph primitives and core algorithms.
- `oasa/atom.py`, `oasa/bond.py`, `oasa/molecule.py` core chemistry model.
- `oasa/smiles.py`, `oasa/molfile.py`, `oasa/inchi.py`, `oasa/cdml.py` format I O.
- `oasa/coords_generator.py`, `oasa/rdkit_bridge.py` coordinate layout via RDKit.
- `oasa/geometry.py`, `oasa/transform.py`, `oasa/transform3d.py` geometry tools.
- `oasa/stereochemistry.py` stereochemistry helpers.
- `oasa/svg_out.py`, `oasa/cairo_out.py` rendering backends.
- `oasa/query_atom.py`, `oasa/known_groups.py` search utilities.
- `oasa/oasa_exceptions.py` custom exception types.
- `oasa/periodic_table.py`, `oasa/linear_formula.py` chemistry references.
- `oasa_data/*.json` bundled data assets.

## Documentation (`docs/`)
- `docs/REPO_STYLE.md` repo structure and file placement rules.
- `docs/PYTHON_STYLE.md` Python coding conventions.
- `docs/MARKDOWN_STYLE.md` Markdown formatting rules.
- `docs/AUTHORS.md` maintainers and contributors.
- `docs/CODE_ARCHITECTURE.md` system overview and data flow.
- `docs/FILE_STRUCTURE.md` directory map and generated assets.
- `docs/USAGE.md` usage notes and examples.

## Generated or temporary outputs
- `__pycache__/` and `*.pyc` created by Python execution.
- `build/`, `dist/`, and `oasa.egg-info/` created by packaging tools.
- `pyflakes.txt` created by the `run_pyflakes.sh` workflow from the style guide.

## Tests (`tests/`)
- `tests/oasa_mypy.ini` static typing configuration.
- `tests/run_oasa_mypy.sh` OASA mypy runner.
- `tests/oasa_legacy_test.py` legacy rendering script.
- `tests/oasa_unittests.py` legacy unittest runner.
- `tests/oasa_smoke_png.py` smoke rendering script.
- `tests/oasa_test_common.py` small common helper test.

## References
- [BKChem GitHub repository](https://github.com/vosslab/bkchem).
