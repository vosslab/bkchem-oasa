# Troubleshooting

## GUI launch issues
- If BKChem fails to start with a Tk error, install a Python build with Tk
  support and retry. See [INSTALL.md](INSTALL.md).

## Missing Cairo output
- PNG or PDF export requires pycairo. Install it if cairo-based output fails.
  See `README.md`.

## Batch mode scripts
- Batch and GUI smoke scripts require Tk even when running headless. See
  [bkchem_batch_examples.py](../packages/bkchem-app/tests/bkchem_batch_examples.py).

## Known gaps
- Add platform-specific troubleshooting steps once installer testing is done.
