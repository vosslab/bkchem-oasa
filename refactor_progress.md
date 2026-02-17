# Refactor progress

Last updated: 2026-02-15

## Snapshot
- Registry refactor: OASA codec registry is implemented and in use by the CLI.
- Rendering refactor: SVG/Cairo unified via render ops, rounded wedges default.
- CDML refactor: OASA CDML writer is the only BKChem serialization path.
- Haworth CLI: batch SMILES rendering is available via `packages/oasa/oasa_cli.py`.
- Menu refactor: [docs/active_plans/MENU_REFACTOR_SUMMARY.md](docs/active_plans/MENU_REFACTOR_SUMMARY.md) is
  the master plan; implementation is not started.
- PubChem integration: plan is documented; implementation not started.
- Data reorg: OASA isotope data moved to JSON and legacy data sources removed.

## Not started
- [docs/active_plans/SMILES_CDML_IMPORT_PLAN.md](docs/active_plans/SMILES_CDML_IMPORT_PLAN.md):
  Route SMILES/IsoSMILES import through CDML instead of direct bridge; plan
  documented, implementation not started.
- Menu refactor implementation:
  [docs/active_plans/MENU_REFACTOR_SUMMARY.md](docs/active_plans/MENU_REFACTOR_SUMMARY.md) and the supporting
  docs define the plan, but no code migration has landed yet.
- [docs/active_plans/BKCHEM_GUI_MENU_REFACTOR.md](docs/active_plans/BKCHEM_GUI_MENU_REFACTOR.md):
  Implementation work not started; docs describe the refactor scope and plan.
- [docs/active_plans/MENU_REFACTOR_ANALYSIS.md](docs/active_plans/MENU_REFACTOR_ANALYSIS.md):
  Analysis complete; implementation not started.
- [docs/active_plans/MODULAR_MENU_ARCHITECTURE.md](docs/active_plans/MODULAR_MENU_ARCHITECTURE.md):
  Tool registry and migration are planned but not implemented.
- [docs/active_plans/PUBCHEM_API_PLAN.md](docs/active_plans/PUBCHEM_API_PLAN.md):
  PubChem lookups are planned with no code landed yet.
- BKChem modernization (from [docs/TODO_CODE.md](docs/TODO_CODE.md)):
  Mirror OASA cleanup work (pyflakes cleanup and globals refactors).
- Legacy export decision (from [docs/TODO_CODE.md](docs/TODO_CODE.md)):
  Decide whether to remove the legacy PostScript builtin exporter now that
  Cairo is required.
- Format expansion evaluation (from [docs/TODO_CODE.md](docs/TODO_CODE.md)):
  RDKit/Open Babel format expansion planning (SDF/SD, MOL2, PDB, CIF).
- Repo modernization and distribution (from [docs/TODO_REPO.md](docs/TODO_REPO.md)):
  Publish OASA to PyPI, plan BKChem binary distribution, mirror OASA packaging
  metadata + version reporting for BKChem, decide BKChem mypy scope and add a
  runner, reconcile licensing guidance, and document runtime dependencies.
- [docs/active_plans/RELEASE_DISTRIBUTION.md](docs/RELEASE_DISTRIBUTION.md):
  Automated installer tooling is planned for macOS dmg, Windows installer, and
  Linux Flatpak builds.

## In progress
- [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md):
  Phases 0-4 implemented and unit-tested (40 render_geometry, 11 connector
  clipping, 45 phase4 known failures, 9 pipeline parity tests all green).
  Phase 4 wires shared `AttachConstraints` with `ATTACH_GAP_TARGET` and
  `ATTACH_PERP_TOLERANCE` through all four consumers: `cairo_out.py`,
  `svg_out.py`, `bond_render_ops.py`, and `bond_drawing.py`. Gap/perp gate
  (2026-02-15) shows Haworth corpus unchanged at baseline (0/362 aligned under
  strict spec); BKChem and OASA generic corpus buckets are empty so consumer
  impact is not yet measurable. Phases 5-6 not started.
- [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md):
  Phases 3 and 4 are complete in runtime/tests and matrix validation,
  including manager checklist fixture coverage plus straightness/lattice
  geometry gates; independent measurement gate is green (`--fail-on-miss`,
  alignment rate `100.00%`); latest closure reruns are green
  (`Strict-overlap failures: 0`, `524 passed, 6 skipped` twice consecutively);
  Phase 5 rollout and close-out is next and not started.
- [docs/active_plans/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/active_plans/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md):
  Phase 0 work is complete; future Phases 6/7 remain planned.
- [docs/active_plans/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md):
  Active policy; continue enforcing SPDX headers on new files.
- [docs/TODO_CODE.md](docs/TODO_CODE.md):
  Still relevant backlog; needs updates for plugin/addon removal work.
- OASA CLI expansion: Planned next step is to broaden `packages/oasa/oasa_cli.py` once the public CLI surface is finalized.

## Completed
- [docs/active_plans/CODER_GUIDE_FEB_10.md](docs/active_plans/CODER_GUIDE_FEB_10.md):
  Marked legacy and superseded by
  [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md).
- [docs/archive/RENDER_BACKEND_UNIFICATION.md](docs/archive/RENDER_BACKEND_UNIFICATION.md):
  Render ops, SVG/Cairo thin painters, ops snapshots, and drift tests are in place.
- [docs/archive/ROUNDED_WEDGES_PLAN.md](docs/archive/ROUNDED_WEDGES_PLAN.md):
  Rounded wedge geometry is shared via `wedge_geometry.py` and used by render ops
  and BKChem bond rendering.
- [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md):
  Closed and archived as the historical source-of-record; 2026-02-10 recovery
  addendum gates are complete and release closure is verified.
- [docs/archive/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/archive/BOND_BACKEND_ALIGNMENT_PLAN.md):
  Phases 0-5 complete; Phase 4 optional. Bond semantics normalized with tests.
- [docs/archive/CDML_ARCHITECTURE_PLAN.md](docs/archive/CDML_ARCHITECTURE_PLAN.md):
  Phases 1-2 complete; Phase 3 optional. OASA CDML writer is default path.
- [docs/archive/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md):
  Updated for normalized hashed bonds and current bond type list.
- [docs/archive/CODEC_REGISTRY_PLAN.md](docs/archive/CODEC_REGISTRY_PLAN.md):
  Phase 1-5 complete; registry used by CLI and BKChem oasa_bridge.
- Data reorganization:
  Isotope data moved to `packages/oasa/oasa_data/isotopes.json`, legacy OASA data
  files removed, and `tools/convert_isotope_data.py` added for refresh.

## Reference docs
- [docs/active_plans/BKCHEM_GUI_MENU_REFACTOR.md](docs/active_plans/BKCHEM_GUI_MENU_REFACTOR.md)
- [docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md](docs/active_plans/BOND_LABEL_ATTACHMENT_IMPROVEMENT_PLAN.md)
- [docs/archive/COMPLETE_BOND_LABEL_PLAN.md](docs/archive/COMPLETE_BOND_LABEL_PLAN.md)
- [docs/active_plans/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/active_plans/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
- [docs/active_plans/MENU_REFACTOR_ANALYSIS.md](docs/active_plans/MENU_REFACTOR_ANALYSIS.md)
- [docs/active_plans/MENU_REFACTOR_SUMMARY.md](docs/active_plans/MENU_REFACTOR_SUMMARY.md)
- [docs/active_plans/MODULAR_MENU_ARCHITECTURE.md](docs/active_plans/MODULAR_MENU_ARCHITECTURE.md)
- [docs/active_plans/PUBCHEM_API_PLAN.md](docs/active_plans/PUBCHEM_API_PLAN.md)
- [docs/active_plans/RENDERER_CAPABILITIES_SHEET_PLAN.md](docs/active_plans/RENDERER_CAPABILITIES_SHEET_PLAN.md)
- [docs/archive/BACKEND_CODE_REVIEW.md](docs/archive/BACKEND_CODE_REVIEW.md)
- [docs/archive/BKCHEM_GUI_CODE_REVIEW.md](docs/archive/BKCHEM_GUI_CODE_REVIEW.md)
- [docs/archive/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/archive/BOND_BACKEND_ALIGNMENT_PLAN.md)
- [docs/archive/CDML_ARCHITECTURE_PLAN.md](docs/archive/CDML_ARCHITECTURE_PLAN.md)
- [docs/archive/CODEC_REGISTRY_PLAN.md](docs/archive/CODEC_REGISTRY_PLAN.md)
- [docs/archive/HAWORTH_CODE_ORGANIZATION_PLAN.md](docs/archive/HAWORTH_CODE_ORGANIZATION_PLAN.md)
- [docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt1.md](docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt1.md)
- [docs/archive/PHASE_B_AUDIT.md](docs/archive/PHASE_B_AUDIT.md)
- [docs/archive/PURE_OASA_BACKEND_REFACTOR.md](docs/archive/PURE_OASA_BACKEND_REFACTOR.md)
- [docs/archive/RENDER_BACKEND_UNIFICATION.md](docs/archive/RENDER_BACKEND_UNIFICATION.md)
- [docs/archive/ROUNDED_WEDGES_PLAN.md](docs/archive/ROUNDED_WEDGES_PLAN.md)
