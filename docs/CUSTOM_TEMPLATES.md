# Custom templates

Legacy note: This document is migrated from the legacy HTML docs that are no longer
tracked in the repo. The
[GitHub repository](https://github.com/vosslab/bkchem) is the primary homepage
and documentation source. Legacy websites are archived and not maintained. Any
legacy email addresses are kept for attribution only and are not support
contacts.

## Overview

BKChem supports custom templates that you can place onto drawings. A template
captures a molecule plus a defined attachment point (atom) and optional
attachment bond.

## Mark the template atom

1. Draw the molecule that will become the template.
2. Add a substituent atom at the position you want to be the attachment point.
3. Switch to Template mode (the cyclohexane icon).
4. Focus the atom and press `Ctrl+t`.

The focused atom becomes the template atom. This marker atom is deleted when the
template is placed.

## Mark the template bond (optional)

If you want the template to attach to a bond (for example, building naphthalene
from two benzenes), focus the bond in Template mode and press `Ctrl+t`. The bond
is marked but not deleted when the template is used.

## Name the template

Select the molecule and use `Chemistry -> Set molecule name`. The molecule name
becomes the template name shown in the Custom templates menu.

## Save the template

Templates can be stored in:

- `~/.bkchem/templates/` for per-user templates.
- `packages/bkchem-app/bkchem_data/templates/` for source checkouts.
- `share/bkchem/templates/` when installed system-wide.

Use `File -> Save As Template` to save and validate templates.
