# OASA

OASA (Open Architecture for Sketching Atoms and Molecules) is a frontend-neutral
Python chemistry library for structure graphs, format conversion, 2D layout, and
complete CDML documents. It is distributed under the GNU GPL v2 only; see the
[license](https://github.com/vosslab/bkchem/blob/main/LICENSE).

The monorepo [VERSION](../../VERSION) registry defines the release version
(`26.07`), which this package's distribution metadata mirrors; that metadata
declares OASA's runtime requirements. OASA can be used directly in Python or as
the authoritative persistent-CDML backend for BKChem-Qt. It owns the complete
ordered document, chemistry semantics, and typed or opaque persistent content;
a frontend supplies only a disposable projection and transient interaction
state. See the
[CDML backend-to-frontend contract](https://github.com/vosslab/bkchem/blob/main/docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
and the
[CDML format specification](https://github.com/vosslab/bkchem/blob/main/docs/CDML_FORMAT_SPEC.md).

## Install

OASA requires Python 3.10 or newer. Install the package and its declared runtime
dependencies with pip:

```sh
python3 -m pip install oasa
```

For a source checkout, install this package directory instead:

```sh
python3 -m pip install packages/oasa
```

## First success

Parse ethanol from SMILES, generate its 2D coordinates, and serialize it back:

```python
from oasa import smiles_lib

molecule = smiles_lib.text_to_mol("CCO")
print(smiles_lib.mol_to_text(molecule))
```

The output is a canonical SMILES representation such as `CCO`. The parsed
OASA atoms have 2D coordinates generated through the packaged RDKit bridge.

## Capabilities

- Create and analyze chemical structure graphs; read and write SMILES and
  supported molecule formats.
- Generate 2D molecular coordinates with RDKit, preserving existing coordinates
  unless regeneration is requested. See the
  [coordinate-generation methods](https://github.com/vosslab/bkchem/blob/main/docs/OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md).
- Own, validate, serialize, and revision-track complete CDML documents while
  preserving ordered known and opaque persistent XML content.
- Provide typed molecule codecs and frontend-neutral rendering observations;
  these adapters never replace the complete-CDML document session.
- Render supported molecular content through Cairo-backed outputs, including
  PNG, PDF, and SVG paths.

## Runtime dependencies

The following dependencies are declared by the distribution and installed with
OASA:

| Dependency | Role |
| --- | --- |
| `defusedxml` | Hardened XML parsing for untrusted XML entry points. |
| `lxml` | Hardened CDML authorization, CDXML input, and controlled SVG generation. |
| `RDKit` | Molecule-format bridges and 2D coordinate generation. |
| `rustworkx` | Graph-algorithm backend behind OASA graph adapters. |
| `PyYAML` | Packaged sugar-name and biomolecule-template data. |
| `pycairo` | Cairo rendering surfaces and image/vector export paths. |

## BKChem relationship

BKChem-Qt is the sole shipped GUI consumer of OASA. Its Qt scene is a
replaceable projection of the backend's current CDML snapshot; it does not own
or reconstruct persistent document state. Retained Tk source is historical
source and fixture reference only: it ships no package and creates no GUI or
compatibility requirement for OASA users.

## Current limitations

- Stereochemistry support is limited, particularly outside cis/trans double
  bonds; tetrahedral SMILES support is not extensively validated.
- Not every molfile properties-block record is supported by the typed molecule
  codec, so some such files may not load completely.
- Compatibility CDML input can preserve incomplete, unknown, and opaque
  content without claiming that every preserved record is editable, chemically
  decoded, or renderable.
- Unusual crowded or cage-like structures can still need manual review after
  automatic 2D coordinate generation.

## Documentation and support

The [BKChem repository](https://github.com/vosslab/bkchem) contains the
[installation guide](https://github.com/vosslab/bkchem/blob/main/docs/INSTALL.md),
[usage guide](https://github.com/vosslab/bkchem/blob/main/docs/USAGE.md), and
current development documentation. Report reproducible issues through the
[issue tracker](https://github.com/vosslab/bkchem/issues).
