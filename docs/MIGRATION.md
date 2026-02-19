# Repository merge and reorganization summary

This note summarizes the BKChem and OASA merge into a single monorepo while
preserving them as separate Python packages.

## Initial state
- BKChem and OASA were separate GitHub repositories.
- BKChem included a vendored OASA copy under `bkchem/oasa`.
- Documentation and ancillary files overlapped.
- Each project had independent packaging metadata.

## Goals
- Keep BKChem as an application and OASA as a standalone library.
- Publish two separate PyPI packages from one repository.
- Preserve full git history for both projects.
- Use a single shared versioning strategy.
- Remove the vendored OASA copy inside BKChem.

## Structural changes
- Introduced a monorepo layout with a `packages/` top level.
- `packages/bkchem-app/` contains the BKChem application package.
- `packages/oasa/` contains the OASA library package.
- Moved BKChem source into `packages/bkchem-app/bkchem/`.
- Consolidated BKChem runtime assets into `packages/bkchem-app/bkchem_data/`.
- Left `docs/`, `tests/`, and `tools/` at the repository root.
- Added `bkchem_webpage/` to `.gitignore` as a generated artifact.

## OASA integration
- Added the OASA repository as a remote.
- Imported OASA into `packages/oasa/` with `git subtree add` to preserve history.
- Verified that the OASA Python package lives at `packages/oasa/oasa/`.

## Dependency cleanup
- Deleted the vendored OASA copy previously located under BKChem.
- Verified that BKChem imports reference `oasa` directly.
- Confirmed that BKChem now depends on OASA as an external library.

## Result
- One GitHub repository hosts both projects.
- Two independent Python distributions can be built and published.
- OASA history is preserved and traceable.
- BKChem no longer carries a private fork of OASA.
- The codebase is structured for long-term maintenance and clearer separation
  of concerns.

## Documentation hosting
- The GitHub repository is the primary homepage and documentation source.
- Legacy websites from the Python 2 era are archived and not maintained.
