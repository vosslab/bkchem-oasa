# Supported formats

`bkchem-qt`, the current PySide6 frontend, deliberately advertises a smaller
set of formats than the OASA codec registry. A format appears in the GUI only
after its document-session route has been verified.

## Native document

- BKChem CDML: `.cdml` (open and save)

CDML retains the editable chemistry, presentation objects, and document
metadata supported by the frontend. A name without a suffix receives `.cdml`;
Save As refuses other suffixes.

## Chemistry-only imports

- MDL Molfile: `.mol`
- Structure Data File: `.sdf`
- SMILES: `.smi`, `.smiles`
- ChemDraw XML: `.cdxml`
- Chemical Markup Language: `.cml`

These formats enter through the session-owned OASA worker. They import
chemical structure and available coordinates, not a complete BKChem
presentation document. Imported work therefore opens as a new, unsaved
session and must be saved as CDML.

## Scene exports

- Scalable Vector Graphics: `.svg`
- Portable Network Graphics: `.png`
- Portable Document Format: `.pdf`

Scene exports capture rendered, supported graphics for publication or sharing.
PNG and PDF use the modeled paper page. SVG honors CDML `crop_svg` and
`crop_margin` when enabled, rendering cropped content without paper or grid
decorations. Retained unsupported CDML remains available for native CDML
round-trip but is not claimed as rendered export output. These artifacts are
not editable BKChem documents and do not replace CDML saving.

## Backend codecs

OASA also contains codecs for formats such as InChI, CD-SVG, and chemistry-only
exports. The CML backend retains a legacy `.xml` alias, but `bkchem-qt` does
not advertise generic `.xml` because that extension is ambiguous. Backend
availability does not imply that the PySide6 File menu supports the same
operation. New GUI formats must preserve the session, undo, and
backend/frontend ownership contracts before they are advertised.

The retained Tk source contains older plugin routes as contributor reference
evidence only. Those routes are not a supported frontend, packaging target, or
part of the BKChem-Qt format contract.
