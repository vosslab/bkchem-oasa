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

## BKChem Qt delivery

Planned approach:

- Use [build_qt_app.py](../../devel/build_qt_app.py) with a fresh
  repository-local `tmp/` run root and `--dry-run` to validate and print the
  Qt-only PyInstaller input plan before an experimental native app build.
- `build_qt_app.py` and [qt_bundle_plan.py](../../devel/qt_bundle_plan.py) are
  the only active macOS application build path. The repository makes no DMG
  release claim; a DMG requires separate, controlled packaging evidence.
- Build the first `BKChem.app` only after a controlled macOS experiment
  verifies the package resources, OASA data, Qt Cocoa plugin, and native
  dependency collection.
- Treat `packages/bkchem-app/` as an unshipped historical reference corpus;
  it is outside Qt artifacts and current-user delivery paths.
- Plan Linux, Windows, signing, notarization, and automated releases after the
  macOS bundle experiment provides evidence for their platform-specific work.

## GitHub releases

- Use GitHub releases for release notes and downloadable artifacts.
- Link installers and checksums from the release page.
