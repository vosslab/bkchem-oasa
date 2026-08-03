# Custom templates

Legacy note: This document is migrated from the legacy HTML docs that are no longer
tracked in the repo. The
[GitHub repository](https://github.com/vosslab/bkchem) is the primary homepage
and documentation source. Legacy websites are archived and not maintained. Any
legacy email addresses are kept for attribution only and are not support
contacts.

## Overview

The delivered PySide6 application supports detached saved molecule templates.
Each template is one complete CDML document containing exactly one direct
molecule. BKChem validates that document before it is saved or offered in the
Template mode, and OASA owns the accepted CDML when it is placed.

The current template action centers the saved molecule's authored atom geometry
at the canvas click. It does not attach, fuse, bond to, or change a molecule
already on the canvas.

## Save a template

1. Draw or open a document with one eligible detached molecule.
2. Choose `File -> Save As Template`.
3. Give the template a lowercase `.cdml` filename in the configured user-template
   folder. BKChem adds that suffix when it is omitted.

Successful template publication refreshes every open session automatically.
Choose `File -> Refresh User Templates` after adding, replacing, or removing
template files outside BKChem.

The ordinary application configures that folder as `~/.bkchem/templates/`.
An embedded host can supply a different explicit folder or no folder; that
choice belongs to the frontend application, not OASA.

Saving publishes the exact current authoritative backend snapshot. It does not
change the document's revision, undo history, dirty state, or saved baseline.
Use Recovery Export when you need to write an arbitrary exact CDML snapshot
outside the user-template folder.

## Place a template

1. Choose User Template mode.
2. Select a template in its Template ribbon.
3. Click an empty canvas position or an existing atom position to use that
   position as the detached template's anchor.

The template catalog uses a molecule name when present; otherwise it shows the
filename stem. Invalid or unreadable `.cdml` files are skipped with a filename
and reason while valid neighboring templates remain available.

## Current scope

The legacy Tk attachment-marker and attachment-bond workflow is historical
reference material. Marker authoring, template attachment, and template fusion
are separate capabilities and are not part of the delivered PySide6 custom
template grammar.
