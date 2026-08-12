# Usage

`bkchem-qt` is the current release-selected BKChem frontend. OASA owns the
canonical, persistent CDML document; Qt supplies presentation, interaction,
and a replaceable scene projection of the current backend snapshot. The
classic Tk frontend is deprecated but retained; it is not the release launcher
documented here.

## Quick start

Launch an empty drawing session:

```sh
bkchem-qt
```

From a dependency-ready source checkout before installing the entry point, use
the equivalent Qt launcher:

```sh
./launch_bkchem-qt_gui.sh
```

Open a native document at launch:

```sh
bkchem-qt example.cdml
```

Use File > Save As to choose a `.cdml` name, then reopen that file to continue
with a clean, path-backed document.

## Command line

The normal command form is `bkchem-qt [files...]`. The only ordinary
user-facing flag is `-v` or `--version`, which prints the installed version.
The positional launch files are CDML documents.

## Files, saving, and recovery

- `.cdml` is the native editable format and the only ordinary Save or Save As
  target. A name without a suffix receives `.cdml`; another suffix is refused.
- File > Open accepts native `.cdml`. It opens each ordinary file in a separate
  session and activates an already-open source instead of duplicating it.
- File > Import accepts `.mol`, `.sdf`, `.smi`, `.smiles`, `.cdxml`, `.cml`,
  and CD-SVG files with `.svg`, `.svgz`, or `.cdsvg` suffixes through OASA.
  Generic `.xml` is not accepted because it does not name a chemistry format.
- Imported material becomes a dirty, pathless CDML session. Save As creates a
  new `.cdml` document and never overwrites the source import format.
- Ordinary Save publishes the exact current backend snapshot and marks that
  backend revision as saved only after the file write succeeds. Qt never
  reconstructs a complete document for publication.

If ordinary Save is unavailable because the current Qt projection is not an
exact current backend snapshot, use File > Recovery Export Backend CDML. It
writes the exact backend snapshot as `.cdml` without changing the session or
its saved baseline. Qt-local edits not present in that snapshot are excluded.
If the app reports unconfirmed durability, the snapshot may exist at the chosen
path, but the tab remains open and no session state changes.

## Rendered export

File > Export writes the current backend snapshot as SVG, PNG, or PDF for
sharing or publication. These rendered outputs are not editable document save
formats; keep the `.cdml` file as the editable source.

## Carbohydrate drawings

Insert > Direct Glycosidic Haworth accepts a supported structural SMILES and
creates a detached two-ring five- or six-member C/O Haworth drawing through the
same backend insertion and undo path as other molecules. The generated CDML
retains its Haworth depiction records on Save and reopen. This is a drawing
tool for the supported direct-oxygen profile; it does not assign alpha/beta or
tetrahedral stereochemistry.

## Current limitations

- Group expansion requires one current plain implicit group with exactly one
  exterior bond. Fragment workflows support ordinary fragment metadata; rich
  imported or generated fragment records are display-only. Linear-form
  conversion requires a selected unbranched atom path.
- Rendered export can report unsupported persistent objects that it omitted.
- OASA's frontend-neutral backend contract defines the data boundary only; this
  release packages Qt while retaining the deprecated Tk source separately.

For the detailed ownership and lifecycle rules, see
[QT_CONTRACT.md](QT_CONTRACT.md) and
[CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md).
