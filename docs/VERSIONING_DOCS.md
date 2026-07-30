# Versioning docs

## Overview
BKChem and OASA share one release version stored in the repo root. CDML format
versioning is separate and should only change when the file format changes.

## Release version (BKChem and OASA)
Update these when releasing a new BKChem/OASA version:
- [VERSION](../VERSION): canonical release registry, with `version = <PEP 440 version>`.
- Every package's `pyproject.toml`: matching static `[project] version` value.
- The OASA requirement in BKChem and BKChem-Qt `pyproject.toml` files: matching
  minimum release version.
- [README.md](../packages/oasa/README.md): "Current version" line.
- [CHANGELOG.md](CHANGELOG.md): add a release entry for the date.
- [RELEASE_HISTORY.md](RELEASE_HISTORY.md): update the release history.

Runtime code does not carry release literals. In a wheel it uses installed package
metadata. In the known `packages/<package>` source-tree layout it reads the root
`VERSION` registry; installed packages never probe paths outside their package.
The focused `tests/test_version_consistency.py` test enforces the registry and
package metadata contract.

### Qt bundle representations

The root registry and checked-in package manifests retain the exact public
CalVer display label, including its zero-padded month (for example `26.02a1`
or `26.07`). Wheel filenames, `.dist-info` names, `METADATA: Version`, and
`importlib.metadata.version()` use the deliberately normalized PEP 440
distribution form (`26.2a1` and `26.7`). `bkchem-qt --version` reconstructs
and reports the exact display label in both source and installed layouts.

The Qt macOS builder derives `CFBundleShortVersionString` as a numeric dotted
release projection (`26.2.0` for `26.02a1`) and requires an explicit numeric
`--bundle-build` value for `CFBundleVersion`. It stores the complete public
release label in `BKChemReleaseVersion`. Post-build inspection validates each
representation at its own boundary; a normalized wheel value never becomes a
replacement release authority.

Release tooling uses `devel/version_registry.py` for strict parsing and
assignment-preserving updates. Do not replace the root registry with a bare
version value: comments and the `version =` assignment are part of its format.
The registry deliberately accepts a portable PEP 440 subset: numeric release
segments with optional `aN`, `bN`, `rcN`, `.postN`, `.devN`, and local suffixes.
Epochs and leading `v` prefixes are excluded so the stored value remains the
same canonical release string used by the package metadata and bump tool.

## CDML format version

CDML format versioning is independent of package releases. The authored-current
profile is `26.07`; `26.02` and earlier chain versions remain compatibility
inputs. The authoritative format reference is
[CDML_FORMAT_SPEC.md](CDML_FORMAT_SPEC.md), not the archived historical
[BKCHEM_FORMAT_SPEC.md](archive/BKCHEM_FORMAT_SPEC.md).

The implemented `26.02` -> `26.07` transition is structurally no-op: it sets
only root `cdml@version` and does not reinterpret a 26.02 document. The
implemented wiring includes:

- [cdml_writer.py](../packages/oasa/oasa/cdml_writer.py): the current writer
  default for new CDML documents and molecule-insertion proposals, inherited
  by Qt envelope and clipboard producers;
- [CDML_versions.py](../packages/bkchem-app/bkchem/CDML_versions.py): the
  retained legacy transformer registry, including the `26.02` -> `26.07` edge;
- [test_cdml_versioning.py](../packages/bkchem-app/tests/test_cdml_versioning.py)
  and focused OASA fixtures for 26.02 preservation, unknown-future root
  preservation, and 26.07 authoring.

Loaded complete documents retain their declared supported-old or unknown-future
root version unless a caller explicitly invokes the legacy transformer. Root
`cdml@version` is format metadata; `author_program@version` is independent
application-release metadata.

Do not substitute CML, CDXML, SVG, or either historical checked-in schema for
the CDML version chain. Those formats are comparison or interchange evidence,
not CDML migration targets or validators.

## Automation status

[bump_version.py](../devel/bump_version.py) is the canonical monorepo release
updater. It updates the root registry, every package `[project] version`, and
the BKChem/BKChem-Qt OASA lower bounds together. PyPI `--set-version` delegates
to that same updater.
