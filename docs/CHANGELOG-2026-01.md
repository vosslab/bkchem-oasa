# Changelog

## 2026-01-31
- Add [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
  to outline Haworth projection goals, scope, and implementation phases.
- Document the biomolecule template side feature in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md),
  covering CDML templates and the initial macro categories.
- Add the wavy-bond smoke glucose note to
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Note that biomolecule template categories are inferred from folder names by
  scanning CDML files on load in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Note that template subcategories are inferred from subfolder names in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Expand [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
  with Haworth bond style notes (left/right hatch, wide rectangle),
  CDML ownership guidance, insert-only template workflow, and the
  wavy_bond.png reference.
- Add a testing plan (unit and smoke tests) to
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Add staged rollout notes with testable outcomes to
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Expand [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
  with bond style specs, including the NEUROtiker-derived bold multiplier and
  the sine-wave wavy bond decision.
- Note template distribution in the macOS app bundle and the Insert-menu
  entry point in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md).
- Implement Stage 1 renderer updates: SVG wedge/hatch/bold support and
  per-bond line widths in SVG/Cairo (`packages/oasa/oasa/svg_out.py`,
  `packages/oasa/oasa/cairo_out.py`).
- Add a smoke test for SVG/PNG bond style rendering (normal, bold, wedge,
  hatch) in `tests/test_oasa_bond_styles.py`.
- Update the Stage 2 plan in
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md)
  to cover full new bond type support and add a post-Stage 2 printer-style
  smoke test plan with colored bonds.
- Rename the bond style smoke test outputs to
  `oasa_bond_styles_smoke.svg` and `oasa_bond_styles_smoke.png`.
- Add `defusedxml` as a required dependency and use it for safe XML parsing via
  new `safe_xml` helpers in BKChem and OASA.
- Set the shared BKChem/OASA version registry to `26.02`.
- Update version references and fallbacks to `26.02` in release history,
  format docs, and the OASA README.
- Bump the CDML format version to `26.02` with a compatibility transformer and
  add `tests/test_cdml_versioning.py` for legacy CDML smoke coverage.
- Add [docs/VERSIONING_DOCS.md](docs/VERSIONING_DOCS.md) to track release and
  CDML version update locations.
- Add a Haworth CLI phase to
  [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md),
  including a draft `packages/oasa/oasa_cli.py haworth` command and smoke
  testing notes.
- Update `tests/oasa_legacy_test.py` to write named outputs into a temporary
  directory so test files are cleaned up after the run.
- Use `defusedxml.minidom` in `tests/test_cdml_versioning.py` to satisfy
  Bandit B318.
- Start Stage 2 Haworth work: add new bond type rendering (wavy variants,
  left/right hatch, wide rectangle) plus per-bond colors in OASA SVG/Cairo,
  update BKChem bond/SVG handling for the new types, and add a printer
  self-test smoke in `tests/test_oasa_bond_styles.py`.
- Add a `--save` flag to `tests/test_oasa_bond_styles.py` so bond-style smoke
  outputs can be written to the current working directory.
- Implement Stage 3 Haworth layout in OASA with ring templates and front-edge
  bond tagging, and add `tests/test_haworth_layout.py` for layout and SVG
  smoke coverage.
- Allow `tests/test_haworth_layout.py` to save SVG output to the current
  working directory with the shared `--save` pytest flag.
- Expand the bond-style printer self-test grid to use bond types along the
  x-axis and colors along the y-axis, increase output size, and densify
  wavy-bond sampling for smoother SVG output.
- Flatten the Haworth ring template (no skew) and increase wide-rectangle
  bond thickness in OASA and BKChem rendering.
- Tag Haworth front edges with left hatch, wide rectangle, and right hatch
  bond styles by default, and fix midpoint lookup when resolving hatch sides.
- Drop Haworth ring distortion parameters (skew/vertical squash) in favor of
  flat ring geometry plus Haworth bond styles, and update the plan text.
- Replace regular-polygon Haworth rings with non-regular pyranose/furanose
  templates derived from sample geometry.
- Make Haworth front edges use wedge side bonds plus a wide rectangle by
  default, update the smoke test to render both ring types, and switch to
  symmetric non-regular templates.
- Rotate Haworth ring atom order so a ring oxygen sits at the top portion of
  the template when present, and add a smoke assertion for that placement.
- Combine the Haworth pyranose/furanose smoke render into a single
  side-by-side SVG output.
- Set ring bond vertex order to match the ring traversal and pick the
  Haworth rectangle edge by frontmost midpoint with adjacent wedges.
- Flip the furanose template vertically to keep the front edge at the
  bottom, and normalize Haworth ring traversal orientation for consistent
  left/right behavior.
- Orient Haworth wedge bonds so the front vertex is the wide end, and add a
  smoke assertion that the front edge is the max-midpoint-y edge.
- Add intentional overlap for Haworth wide rectangles and wedges in SVG/Cairo
  output to eliminate seam gaps without changing atom coordinates.
- Lengthen the furanose front edge by widening the template coordinates.
- Render Haworth wide rectangles as thick stroked lines with round caps to
  smooth joins and clean up the silhouette.
- Inset Haworth round-capped front edges by half the line width to avoid
  protruding past wedge joins.
- Drop wedge cap circles; keep wedge polygons and round-capped front edges
  for cleaner Haworth joins.
- Replace Haworth wedge bases with rounded arc paths aligned to the front
  edge cap center to eliminate join artifacts.
- Extend the Haworth layout smoke test to render Cairo PNG output alongside
  SVG output (skipping when pycairo is unavailable).
- Offset wedge cap centers inward to keep wedge length stable, and flip the
  Haworth Cairo smoke molecule so PNG orientation matches SVG.
- Increase the default Cairo render scaling factor for higher-resolution PNG
  output.
- Replace legacy XML parsing in BKChem and OASA with `safe_xml` wrappers,
  including ftext markup parsing and CDML/CDATA imports.
- Replace `eval()` with `ast.literal_eval()` in preference and external data
  parsing.
- Harden NIST WebBook fetchers with scheme/host validation and randomized
  request delays.
- Replace `tempfile.mktemp()` with a temporary directory in the ODF exporter.
- Parameterize structure database SQL lookups in OASA.
- Add a plugin path allowlist and explicit exec annotations for plugin and
  batch script execution.
- Normalize indentation to tabs in the files flagged by
  `tests/test_indentation.py`.
- Annotate validated WebBook urlopen calls to silence Bandit B310.
- Expand the Haworth plan scope to cover pyranose and furanose rings, and add
  local SVG references.
- Update [docs/TODO_CODE.md](docs/TODO_CODE.md) to match the Haworth scope.
- Align Haworth style notes with existing renderer defaults and add external
  NEUROtiker archive references.
- Replace the TODO list with [docs/TODO_REPO.md](docs/TODO_REPO.md) and
  [docs/TODO_CODE.md](docs/TODO_CODE.md).
- Refresh todo references in [README.md](../README.md),
  [docs/REPO_STYLE.md](docs/REPO_STYLE.md), and
  [packages/oasa/docs/REPO_STYLE.md](../packages/oasa/docs/REPO_STYLE.md).

## 2025-12-26
- Update [README.md](../README.md) with monorepo overview, doc links, and
  package locations.
- Refresh [docs/INSTALL.md](docs/INSTALL.md) with merged repo run instructions
  and updated Python requirements.
- Revise [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) for the
  `packages/bkchem-app/` and `packages/oasa/` layout plus the local website mirror.
- Update [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) to use the new
  monorepo paths and OASA doc references.
- Update [packages/oasa/README.md](../packages/oasa/README.md) for monorepo
  install and test locations.
- Add `pyproject.toml` packaging for BKChem and OASA, remove legacy
  `setup.py`, and add a `bkchem` console entry point.
- Teach BKChem path resolution to look in `bkchem_data` and shared install
  directories before legacy relative paths.
- Add [docs/MIGRATION.md](docs/MIGRATION.md) with the BKChem and OASA merge
  summary.
- Switch documentation and packaging metadata to the GitHub repository as the
  primary homepage and mark legacy sites as archived.
- Update Windows installer metadata URLs to point at the GitHub project.
- Migrate legacy HTML and DocBook docs into Markdown
  (`docs/USER_GUIDE.md`, `docs/BATCH_MODE.md`, `docs/CUSTOM_PLUGINS.md`,
  `docs/CUSTOM_TEMPLATES.md`, `docs/EXTERNAL_IMPORT.md`).
- Add [docs/RELEASE_DISTRIBUTION.md](docs/RELEASE_DISTRIBUTION.md) with planned
  distribution paths for BKChem and OASA.
- Add legacy notices to HTML and DocBook sources that now point to Markdown.
- Fix initial pyflakes findings in batch scripts and gettext helpers in core
  modules.
- Define OASA as "Open Architecture for Sketching Atoms and Molecules" across
  docs and metadata.
- Add BKChem modernization follow-ups to [docs/TODO.md](docs/TODO.md).
- Fix more pyflakes findings in BKChem core modules and plugin exporters.
- Exclude the local website mirror from the pyflakes scan.
- Fix additional pyflakes issues in logger, interactors, plugins, and tests.
- Remove Piddle export plugins and Piddle-specific tuning hooks.
- Remove Piddle strings from locale catalogs.
- Rename filesystem plugin scripts to addons, update plugin discovery paths,
  packaging data files, and documentation references.
- Fix more pyflakes findings in core modules, addon scripts, and exporters, and
  prune the website mirror from pyflakes scans.
- Fix additional pyflakes issues in addons, import/export plugins, and core
  helpers (unused imports, gettext fallbacks, and minor logic fixes).
- Resolve remaining pyflakes findings across core modules and plugins, and
  harden the pyflakes runner to skip local website mirrors.
- Add `version.txt` as a shared version registry and wire BKChem and OASA
  version reads to it.
- Standardize BKChem and OASA to use the same version string from
  `version.txt`.
- Bump the shared BKChem/OASA version to `0.16beta1`.
- Add [docs/RELEASE_HISTORY.md](docs/RELEASE_HISTORY.md) from the legacy
  progress log.
- Restore the pyflakes runner skip list for `bkchem_webpage` and
  `bkchem_website`.
- Add [tests/bkchem_batch_examples.py](../tests/bkchem_batch_examples.py) to exercise
  the batch script examples against a temporary CDML file.
- Rename BKChem test runners to drop the `run_` prefix.
- Consolidate test scripts under `tests/`, add OASA-specific runners with
  `oasa_` prefixes, and remove duplicate pyflakes scripts.
- Update OASA docs and file structure notes to reference the new test paths.
- Rename Markdown docs to ALL CAPS filenames and refresh references across
  README, legacy HTML stubs, and doc links.
- Update REPO_STYLE naming rules (root and OASA) for ALL CAPS documentation
  filenames.
- Expand [README.md](../README.md) with highlights, legacy screenshots, and
  updated wording for OASA and repository positioning.
- Add dedicated BKChem and OASA sections to [README.md](../README.md) with
  differences, use cases, and the backend relationship.
- Fix BKChem test runners to add the legacy module path so `import data` resolves.
- Keep `packages/bkchem-app/` ahead of the legacy module path so `bkchem.main` imports
  correctly in the BKChem test runners.
- Remove legacy HTML/DocBook sources now that Markdown docs are canonical.
- Update `packages/bkchem-app/prepare_release.sh` to skip DocBook generation when
  sources are no longer present.
- Remove legacy log references from OASA file-structure docs after deleting
  `docs/legacy/`.
- Remove `packages/oasa/LICENSE` and standardize on the root `LICENSE` file.
- Update repo style licensing rules to reflect GPLv2 for the whole repository.
- Update BKChem and OASA packaging metadata to GPL-2.0-only and clean up the
  OASA MANIFEST license references.
- Expand the root README docs list to include every Markdown document under
  `docs/`.
- Update [docs/RELEASE_HISTORY.md](docs/RELEASE_HISTORY.md) with the simone16
  0.15 fork acknowledgment and a 0.16beta1 entry.
- Refine the 0.15 simone16 release entry with a date range and concise highlights.
- Initialize BKChem preferences in GUI and batch test runners to avoid
  Store.pm errors.
- Align BKChem test runner preference initialization with legacy imports to
  avoid duplicate singleton modules.
- Add `tests/run_smoke.sh` to run BKChem smoke tests together.
- Remove the background Tk thread from the batch example logic to avoid Tcl
  threading errors on macOS.
- Move BKChem example scripts out of `docs/scripts/` into `tests/`.
- Inline legacy batch script behavior into `tests/bkchem_batch_examples.py`
  and remove the standalone example scripts.
- Add success checks to BKChem smoke and batch example tests.
- Add `tests/bkchem_manual.py` for interactive manual testing.
- Extend `tests/run_smoke.sh` to include the OASA smoke render and verify output.
- Filter optional plugin-load warnings from the smoke test output.
- Number the smoke test output steps in `tests/run_smoke.sh`.
- Keep `tests/run_smoke.sh` running all tests and report failures at the end.
- Fix BKChem batch examples to use `bkchem.main.BKChem()` instead of legacy
  `bkchem.myapp`.
- Add `tests/oasa_smoke_formats.py` to render SVG, PDF, and PNG variants in
  smoke tests.
- Switch BKChem plugin imports to explicit relative paths so optional plugins
  load reliably under Python 3 packaging.
- Surface plugin import errors with module names and exception details, with
  optional tracebacks when debug mode is enabled.
- Add `tests/bkchem_plugin_smoke.py` and `tests/run_plugin_smoke.sh` to report
  loaded plugins and fail fast on missing plugin imports.
- Drop the legacy OpenOffice Draw export plugin and remove its unused manifest.
- Refresh the ODF exporter description to reference OpenDocument and LibreOffice.
- Allow BKChem plugin loader to import config when plugins are loaded as a
  top-level package.
- Skip the standard-value replacement prompt when opening built-in templates.
- Add SMILES and InChI export plugins powered by OASA for BKChem exports.
- Expand the BKChem plugin smoke test to report plugin modes, extensions, and
  doc strings (optional summary output).
## 2026-02-01
- Regenerate biomolecule template CDML files from `biomolecule_smiles.txt`.
- Add `tools/generate_biomolecule_templates.py` to rebuild biomolecule templates.
- Split biomolecule template selection into category and template dropdowns.
- Match the disabled edit-pool background to the UI theme to avoid a black bar.
- Fix mixed indentation in `packages/oasa/oasa/selftest_sheet.py`.
- Pretty-print SVG output when writing files in `packages/oasa/oasa/svg_out.py`.
- Add [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  with a phased plan for aligning BKChem and OASA bond semantics.
- Teach `tools/generate_biomolecule_templates.py` to read YAML input and add
  legacy name mapping when generating template paths.
- Regenerate biomolecule templates from `biomolecule_smiles.yaml`.
- Remove left/right hatch references from
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md) and
  focus on deterministic vertex ordering for hashed bonds.
- Refine [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  to call out vertex ordering rules, snapshot guidance, and updated risks.
- Add explicit canonicalization helper and serialization policy to
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md).
- Add test strategy section to
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  covering fixtures, invariants, and vertex ordering tests.
- Expand the test strategy in
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  with atom label and coordinate transform smoke tests plus fixture suite scope.
- Add maintainability expansion guidance to
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md)
  covering shared OASA core boundaries, next semantic layers, and a deletion
  gate.
- Add measurable phases with pass criteria to
  [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md),
  including the test harness phase and deletion gate phase.

## 2026-01-31
- Add an optional export check to the BKChem plugin smoke test, writing sample
  files and reporting output sizes.
- Use the macOS system menu bar when running on Darwin, keeping in-window menus
  for other platforms.
- Add [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md) to document the
  CDML file format.
- Add [docs/SUPPORTED_FORMATS.md](docs/SUPPORTED_FORMATS.md) with import/export
  formats and default save behavior.
- Update [docs/TODO.md](docs/TODO.md) with new follow-up items.
- Note optional RDKit/Open Babel integration as a potential format expansion path.
- Expand RDKit/Open Babel TODO with candidate files and docs.
- Add format coverage notes to the RDKit/Open Babel TODO entry.
- Add `inchi` to the Homebrew dependencies.
- Clarify required and optional dependencies in [docs/INSTALL.md](docs/INSTALL.md).
- Mark `pycairo` as a required dependency.
- Resolve OASA mypy errors by tightening class imports, annotations, and a
  stderr print fix.
- Adjust OASA graph base classes to allow extended `attrs_to_copy` tuples.
- Fix macOS system menubar initialization with Pmw MainMenuBar.
- Update OASA digraph base import for the refactored graph module exports.
- Update OASA config to reference the molecule class directly after import
  refactors.
- Normalize standard comparison to avoid false "Replace standard values" prompts
  when files match current defaults.
- Add `docs/assets/` screenshots and update the root README to use them.
- Add a draft BKChem package README and link it from the root README.

## 2025-12-24
- Add [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) with system overview
  and data flow.
- Add [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md) with directory map and
  generated assets.
- Rename `README` to `README.md`.
- Update packaging references to `README.md` in `MANIFEST.in` and `setup.py`.
- Scope `tests/run_pyflakes.sh` to core app sources under `bkchem/`.
- Refactor plugin scripts to expose `main(app)` and call it from
  `bkchem/plugin_support.py`.
- Fix core pyflakes warnings for missing gettext helpers and unused imports or
  variables.
- Rewrite `docs/INSTALL.md` with clearer Markdown structure and code blocks.
- Add `pip_requirements.txt` for runtime and optional pip3 dependencies.
- Address additional core pyflakes items in `external_data.py`,
  `singleton_store.py`, `import_checker.py`, `graphics.py`, `misc.py`,
  `edit_pool.py`, `main.py`, and `atom.py`.
- Remove `from tkinter import *` from `bkchem/main.py`.
- Fix `_` usage in `bkchem/edit_pool.py` and clean up unused variables and
  imports in `bkchem/main.py`.
- Add `tests/bkchem_gui_smoke.py` to open the GUI briefly for a smoke test.
- Improve GUI smoke test error handling when Tk is unavailable.
- Add `Brewfile` with Homebrew dependencies for Tk support.
- Add `python-tk@3.12` to `Brewfile` and macOS Tk notes to
  `docs/INSTALL.md`.
- Update `tests/bkchem_gui_smoke.py` to add the BKChem package directory to
  `sys.path` for legacy relative imports.
- Update GUI smoke test to import `bkchem.main` directly and replace deprecated
  `imp` usage with `importlib` in `bkchem/main.py`.
- Add gettext fallback in `bkchem/messages.py` for module-level strings.
- Initialize gettext fallbacks in `tests/bkchem_gui_smoke.py`.
- Add [docs/TODO.md](docs/TODO.md) with a note to replace legacy exporters with
  Cairo equivalents.
