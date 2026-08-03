# Troubleshooting

## GUI launch issues
- If `bkchem-qt` fails to start, confirm that PySide6 is installed and that the
  command runs from a desktop session. Reinstall the supported OASA and
  BKChem-Qt packages if either import is unavailable. See [INSTALL.md](INSTALL.md).

## Missing Cairo output
- PNG or PDF export requires pycairo. Install it if cairo-based output fails.
  See `README.md`.

## Historical Tk reference

- `packages/bkchem-app/` remains source and fixture evidence for contributors.
  It is not an installation, launch, or screenshot workflow for this release.

## Known gaps
- Add platform-specific troubleshooting steps once installer testing is done.
