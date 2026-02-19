# BKChem and OASA

BKChem is a GUI for drawing chemical structures. OASA (Open Architecture for
Sketching Atoms and Molecules) is the chemistry library that powers structure
conversion and analysis. This repository is the primary home for both projects.

## Packages
- `packages/bkchem-app/` BKChem Tk GUI for drawing chemical structures.
- `packages/oasa/` OASA (Open Architecture for Sketching Atoms and Molecules)
  library and CLI converters used by BKChem.

## Terminology
- Plugin: BKChem GUI extension (menu action or drawing mode) that runs inside the
  editor and uses Tk/UI state.
- Addon: filesystem plugin loaded from `packages/bkchem-app/addons/` or
  `~/.bkchem/addons/`, described by a small XML manifest and script.
- Codec: OASA format adapter for reading and writing molecules (SMILES, InChI,
  molfile, CDML). Codecs are non-GUI and registered in OASA.

## BKChem
BKChem is the user-facing drawing application. It uses OASA as the backend for
structure parsing, conversion, and analysis.

Use BKChem when you need:
- A GUI for drawing and editing structures by hand.
- Template-based sketching, fragment reuse, and layout helpers.
- Visual export workflows backed by OASA conversions.

## OASA
OASA is the chemistry library and conversion engine. It can be used on its own
in scripts or services, and it powers BKChem under the hood.

Use OASA when you need:
- Programmatic access to structure graphs and conversions.
- Batch processing and automation outside the GUI.
- A reusable backend for other chemistry tools.

## Highlights
BKChem
- Interactive chemical drawing with templates and reusable fragments.
- Batch mode scripting for automation and scripted edits.
- Export and import workflows powered by OASA.

OASA
- Python library for chemical structure graphs and conversions.
- Used by BKChem but available as a standalone library.

## Screenshots (legacy)
The screenshots below are from the archived site (Python 2 era) but still show
core workflows that BKChem supports today.

![BKChem drawing example](docs/assets/bkchem_drawing.png)
![BKChem PDF export example](docs/assets/bkchem_pdf_export.png)
![BKChem templates example](docs/assets/bkchem_templates.png)

## Docs
- [docs/AUTHORS.md](docs/AUTHORS.md) primary maintainers and contributors.
- [docs/BATCH_MODE.md](docs/BATCH_MODE.md) batch scripting workflow.
- [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md) CDML format specification.
- [docs/CHANGELOG.md](docs/CHANGELOG.md) chronological change log.
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) system overview and data flow.
- [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md) plugin and addon guidance.
- [docs/CUSTOM_TEMPLATES.md](docs/CUSTOM_TEMPLATES.md) template workflow.
- [docs/EXTERNAL_IMPORT.md](docs/EXTERNAL_IMPORT.md) scripting from Python.
- [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) directory map and assets.
- [docs/INSTALL.md](docs/INSTALL.md) setup, dependencies, and environment.
- [docs/MARKDOWN_STYLE.md](docs/MARKDOWN_STYLE.md) Markdown conventions.
- [docs/MIGRATION.md](docs/MIGRATION.md) BKChem + OASA merge summary.
- [docs/PYTHON_STYLE.md](docs/PYTHON_STYLE.md) Python coding conventions.
- [docs/RELEASE_DISTRIBUTION.md](docs/RELEASE_DISTRIBUTION.md) release plans.
- [docs/RELEASE_HISTORY.md](docs/RELEASE_HISTORY.md) historical release notes.
- [docs/REPO_STYLE.md](docs/REPO_STYLE.md) repo structure and naming.
- [docs/SUPPORTED_FORMATS.md](docs/SUPPORTED_FORMATS.md) supported file formats.
- [docs/TODO_REPO.md](docs/TODO_REPO.md) publishing, planning, and policy tasks.
- [docs/TODO_CODE.md](docs/TODO_CODE.md) coding tasks and feature work.
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) BKChem manual.
- [packages/oasa/README.md](packages/oasa/README.md) for OASA-specific usage.
- [packages/bkchem-app/README.md](packages/bkchem-app/README.md) for BKChem-specific usage.

## Distribution
- Planned: publish OASA to PyPI from this repository.
- Planned: ship BKChem binary installers (macOS dmg, Linux Flatpak, Windows).

## Local website mirror
- `bkchem_webpage/` contains a local copy of the legacy BKChem website.

## Project home
- [GitHub repository](https://github.com/vosslab/bkchem) is the primary homepage.

## Legacy references
- [Legacy BKChem site](https://bkchem.zirael.org/) (Python 2 era, not maintained).
- [Legacy OASA site](https://bkchem.zirael.org/oasa_en.html) (Python 2 era, not maintained).

## License
- See `LICENSE`.
