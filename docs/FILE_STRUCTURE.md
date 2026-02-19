# File structure

## Top level
- [packages/](packages/) monorepo packages for BKChem and OASA.
- [docs/](docs/) project documentation, plans, and reference assets.
- [tests/](tests/) repo-level test runners and smoke tests.
- [tools/](tools/) maintenance scripts and reference render helpers.
- [devel/](devel/) release and automation scripts.
- [bkchem_webpage/](bkchem_webpage/) local mirror of the legacy BKChem website.
- [README.md](README.md), [LICENSE](LICENSE), [AGENTS.md](AGENTS.md) project
  references.
- [pip_requirements.txt](pip_requirements.txt), [Brewfile](Brewfile)
  dependency manifests.
- [version.txt](version.txt) shared version registry for BKChem and OASA.

## BKChem package (`packages/bkchem-app/`)
- [packages/bkchem-app/bkchem/](packages/bkchem-app/bkchem/) BKChem application package.
- [packages/bkchem-app/bkchem/bkchem.py](packages/bkchem-app/bkchem/bkchem.py)
  application bootstrap and CLI flags.
- [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) main Tk
  application class and menus.
- [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py) canvas and
  document container (`chem_paper`).
- [packages/bkchem-app/bkchem/molecule.py](packages/bkchem-app/bkchem/molecule.py),
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py),
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py) core chemical
  objects.
- [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py),
  [packages/bkchem-app/bkchem/interactors.py](packages/bkchem-app/bkchem/interactors.py),
  [packages/bkchem-app/bkchem/context_menu.py](packages/bkchem-app/bkchem/context_menu.py)
  UI modes and input handling.
- [packages/bkchem-app/bkchem/export.py](packages/bkchem-app/bkchem/export.py) CDML and
  CD-SVG export helpers.
- [packages/bkchem-app/bkchem/plugin_support.py](packages/bkchem-app/bkchem/plugin_support.py)
  plugin discovery and execution.
- [packages/bkchem-app/bkchem/plugins/](packages/bkchem-app/bkchem/plugins/) built-in
  exporter backends and format handlers.
- [packages/bkchem-app/addons/](packages/bkchem-app/addons/) user-facing addon scripts
  and XML descriptors.
- [packages/bkchem-app/bkchem_data/](packages/bkchem-app/bkchem_data/) templates,
  images, pixmaps, locale files, and DTDs.
- [packages/bkchem-app/bkchem_data/templates/biomolecules/](packages/bkchem-app/bkchem_data/templates/biomolecules/)
  biomolecule template folders (carbs, protein, lipids, nucleic acids).
- [packages/bkchem-app/pyproject.toml](packages/bkchem-app/pyproject.toml),
  [packages/bkchem-app/MANIFEST.in](packages/bkchem-app/MANIFEST.in) packaging metadata.
- [packages/bkchem-app/bkchem.iss](packages/bkchem-app/bkchem.iss),
  [packages/bkchem-app/prepare_release.sh](packages/bkchem-app/prepare_release.sh)
  release assets.

## OASA package (`packages/oasa/`)
- [packages/oasa/oasa/](packages/oasa/oasa/) OASA library source code.
- [packages/oasa/docs/](packages/oasa/docs/) OASA-specific documentation,
  including [packages/oasa/docs/FILE_STRUCTURE.md](packages/oasa/docs/FILE_STRUCTURE.md).
- [packages/oasa/chemical_convert.py](packages/oasa/chemical_convert.py)
  conversion helper script.
- [packages/oasa/pyproject.toml](packages/oasa/pyproject.toml) packaging metadata.
- [packages/oasa/pip_requirements.txt](packages/oasa/pip_requirements.txt)
  OASA-specific dependencies.

## Documentation map
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) system overview and
  data flow.
- [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) directory map and assets.
- [docs/REFERENCE_OUTPUTS.md](docs/REFERENCE_OUTPUTS.md) reference render
  outputs under [docs/reference_outputs/](docs/reference_outputs/).
- [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
  Haworth plan and staged outcomes.
- [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md)
  render ops plan and drift guards.
- [docs/ROUNDED_WEDGES_PLAN.md](docs/ROUNDED_WEDGES_PLAN.md) rounded wedge
  geometry plan.

## Generated or temporary outputs
- `__pycache__/`, `*.pyc` Python bytecode.
- `build/`, `dist/`, `*.egg-info/` packaging outputs.
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` test caches.
- [docs/reference_outputs/](docs/reference_outputs/) reference render outputs.
- `report_*.txt` security and lint reports.
- `haworth_layout_smoke.svg`, `haworth_layout_smoke.png` when saved by tests.

## Where to add new work
- New core BKChem features: [packages/bkchem-app/bkchem/](packages/bkchem-app/bkchem/).
- New OASA features: [packages/oasa/oasa/](packages/oasa/oasa/).
- New tests and smoke scripts: [tests/](tests/).
- New docs: [docs/](docs/) following [docs/REPO_STYLE.md](docs/REPO_STYLE.md).
- New maintenance scripts: [tools/](tools/).
