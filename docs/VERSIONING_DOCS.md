# Versioning docs

## Overview
BKChem and OASA share one release version stored in the repo root. CDML format
versioning is separate and should only change when the file format changes.

## Release version (BKChem and OASA)
Update these when releasing a new BKChem/OASA version:
- [version.txt](../version.txt): single source of truth for the repo version.
- [packages/bkchem-app/bkchem/config.py](../packages/bkchem-app/bkchem/config.py):
  `current_BKChem_version` fallback when `version.txt` is missing.
- [packages/oasa/oasa/__init__.py](../packages/oasa/oasa/__init__.py):
  `__version__` fallback when `version.txt` is missing.
- [packages/oasa/README.md](../packages/oasa/README.md): "Current version" line.
- [docs/CHANGELOG.md](CHANGELOG.md): add a release entry for the date.
- [docs/RELEASE_HISTORY.md](RELEASE_HISTORY.md): update the release history.

These files pull their version from code and do not store a literal version:
- [packages/bkchem-app/pyproject.toml](../packages/bkchem-app/pyproject.toml)
- [packages/oasa/pyproject.toml](../packages/oasa/pyproject.toml)

## CDML format version
Update these when the CDML format changes (new attributes, elements, bond
types, or color model changes):
- [packages/bkchem-app/bkchem/config.py](../packages/bkchem-app/bkchem/config.py):
  `current_CDML_version` used when saving new CDML and CD-SVG.
- [packages/bkchem-app/bkchem/CDML_versions.py](../packages/bkchem-app/bkchem/CDML_versions.py):
  add a new transformer so older CDML can be upgraded to the new version.
- [docs/BKCHEM_FORMAT_SPEC.md](BKCHEM_FORMAT_SPEC.md): update examples and
  the documented current CDML version.
- [tests/test_cdml_versioning.py](../tests/test_cdml_versioning.py): update or
  extend smoke coverage for legacy CDML upgrades.

## Automation status
[devel/bump_version.py](../devel/bump_version.py) assumes a single-package repo.
Use manual updates for this monorepo until the script is updated.
