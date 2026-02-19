# Usage

## BKChem GUI
- Install BKChem from the repo as documented in
  [docs/INSTALL.md](docs/INSTALL.md).
- Launch the GUI using the `bkchem` command (see
  [packages/bkchem-app/README.md](packages/bkchem-app/README.md)).

```sh
bkchem
```

## Batch mode
- Batch scripting uses the `-b` flag. See
  [docs/BATCH_MODE.md](docs/BATCH_MODE.md).

## OASA library
- OASA usage notes live in
  [packages/oasa/docs/USAGE.md](packages/oasa/docs/USAGE.md).
- Install and import instructions are in
  [packages/oasa/README.md](packages/oasa/README.md).

## OASA CLI
- Render Haworth projections from SMILES using
  [packages/oasa/oasa_cli.py](packages/oasa/oasa_cli.py).

Examples:
```sh
python3 packages/oasa/oasa_cli.py haworth -s "C1CCOCC1" -o haworth.svg
python3 packages/oasa/oasa_cli.py haworth -s "C1CCOCC1" -o haworth.png
```

## Terminology
- Plugin: BKChem GUI extension that adds a menu action or drawing mode.
- Addon: filesystem plugin loaded from the addons folders and described by an
  XML descriptor plus a Python script.
- Codec: OASA format adapter for reading and writing molecule data (SMILES,
  InChI, molfile, CDML) without any GUI dependencies.

## Reference outputs
- Regenerate Haworth and wavy-bond reference outputs using
  [tools/render_reference_outputs.py](tools/render_reference_outputs.py).
  See [docs/REFERENCE_OUTPUTS.md](docs/REFERENCE_OUTPUTS.md).

## Known gaps
- Add format-conversion CLI examples once the public CLI surface is finalized.
