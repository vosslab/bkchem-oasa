# Release and distribution

This document describes the intended distribution paths for BKChem and OASA
(Open Architecture for Sketching Atoms and Molecules).
The [GitHub repository](https://github.com/vosslab/bkchem) is the primary
homepage and source of releases.

## OASA (PyPI)

Planned approach:

- Publish OASA as a standalone PyPI package from `packages/oasa/`.
- Keep packaging metadata in `packages/oasa/pyproject.toml`.
- Build and upload source distributions and wheels as needed.

## BKChem (binary installers)

Planned approach:

- Ship binary installers for end users.
- Target formats:
-  - macOS: `bkchem.dmg`
-  - Linux: Flatpak (or similar)
-  - Windows: installer built from `packages/bkchem-app/bkchem.iss`
- Develop automated tooling to build:
  - macOS `bkchem.dmg` -- built by [devel/build_macos_dmg.py](../../devel/build_macos_dmg.py)
  - Windows installer
  - Linux Flatpak

## GitHub releases

- Use GitHub releases for release notes and downloadable artifacts.
- Link installers and checksums from the release page.
