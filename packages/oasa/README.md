# OASA

OASA (Open Architecture for Sketching Atoms and Molecules) is a free Python
library for manipulating and analyzing chemical structures. This package lives
under `packages/oasa/` in the BKChem monorepo
and is distributed under the GNU GPL. For details see
[LICENSE](../../LICENSE).

More info can be found in the [BKChem GitHub repository](https://github.com/vosslab/bkchem).
BKChem, the primary consumer of this library, is documented in the same repo.
Legacy sites are archived and relate to the Python 2 era.
Usage notes are in [docs/USAGE.md](docs/USAGE.md).
Current version: 26.02a1.

## Distribution

Planned: publish OASA to PyPI from this monorepo. For now, install from source.

## Install

OASA needs Python 3.10 or higher to run properly. Tested with Python 3.12.

To install from the monorepo:

```sh
cd packages/oasa
pip3 install .
```

To use OASA from a Python program:

```python
import oasa
```

## Testing

Run static checks from the repo root `tests/` folder:
- `tests/run_pyflakes.sh` (shared)
- `tests/run_oasa_mypy.sh` (OASA only)

## Status

Below are summarized the limitations of the library. This does not mean there
are no other limitations, but for these it has no sense to write bug reports.

OVERALL:
- no documentation beyond the source code is available
- stereochemistry support is limited to cis/trans stereochemistry on double bonds
  and only in some formats
- not much effort was invested into optimization, it may be slow sometimes
- the API might be unstable

SMILES:
- cis/trans stereochemistry is supported, some attempt were made to make
  tetrahedral stereochemistry work, but it is not very much tested

InChI:
- reading is done natively by OASA
- for writing the original InChI program is needed (cInChI, cInChI.exe)

MOLFILE:
- not all data in the properties block (after the bond block) are supported
  (this means that molfiles containing a properties block might not be read
  properly)

COORDS GENERATOR:
- coords for molecules like calix[4]arene and similar do not give a very nice
  picture

CAIRO_OUT:
- pycairo is required to make use of cairo_out functionality
- PNG, PDF and SVG export is supported now
