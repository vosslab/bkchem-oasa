# Running BKChem from Python

Legacy note: This document is migrated from the legacy HTML docs that are no longer
tracked in the repo. The
[GitHub repository](https://github.com/vosslab/bkchem) is the primary homepage
and documentation source. Legacy websites are archived and not maintained. Any
legacy email addresses are kept for attribution only and are not support
contacts.

## Warning about API stability

BKChem's scripting API is not yet stable or fully documented. Scripts that work
now may need updates as the codebase evolves.

## Example script

The example logic lives in `tests/bkchem_batch_examples.py`. It opens a CDML file,
recolors all double bonds to red, saves the result, and exits.

Key pieces of the script:

```python
import sys
import threading

from bkchem import bkchem_app

# Application instance
app = bkchem_app.myapp
app.in_batch_mode = 1

# Run the Tk mainloop in a background thread
thread = threading.Thread(target=app.mainloop, name="app", daemon=True)
thread.start()
```

Then operate on the document:

```python
app.load_CDML(sys.argv[1])
for mol in app.paper.molecules:
	for bond in mol.bonds:
		if bond.order == 2:
			bond.line_color = "#aa0000"
			bond.redraw()
app.save_CDML()
app.destroy()
```

## Import paths

If BKChem is installed with `pip3 install .`, use:

```python
from bkchem import bkchem_app
```

If you are running from a source checkout, make sure `packages/bkchem` is on the
Python path before importing.
