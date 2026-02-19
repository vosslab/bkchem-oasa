# Changelog

## 2026-02-19
- Remove spurious "how did we get here?!?" UserWarning from `event_to_key()` in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py):
  empty key is normal for modifier-only or dead-key events on macOS, return
  empty string silently instead of warning.
- Add YAML mode `label` and updated `name` strings to gettext catalog
  [packages/bkchem-app/bkchem_data/locale/pot/BKChem.pot](packages/bkchem-app/bkchem_data/locale/pot/BKChem.pot):
  add 9 new msgid entries (bio, user, transform, vector, misc, biomolecule
  templates, user templates, brackets, miscellaneous). Run `update_l10ns.sh`
  to merge into all 11 language `.po` files with fuzzy-matched translations.
- Add ribbon-style group labels and vertical separators between submode
  button groups in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py):
  `change_mode()` reads `group_labels` from YAML config and renders compact
  labels and thin separator lines between RadioSelect button rows. Adds
  `_sub_extra_widgets` list for cleanup on mode switch. Tooltips now prefer
  YAML `tooltip_map` values over plain display names.
- Fix GUI event test canvas coordinate handling in
  [packages/bkchem-app/tests/test_bkchem_gui_events.py](packages/bkchem-app/tests/test_bkchem_gui_events.py):
  add `_canvas_to_widget()` helper to convert canvas coordinates to widget
  coordinates for `event_generate`. The ribbon widget additions shifted the
  canvas viewport offset, causing `canvasx(0)` to be non-zero.
- Fix IndexError when switching to template mode with no templates: skip
  creating empty submode groups in `_build_flat_submodes()` in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py).
- Fix AttributeError in
  [packages/bkchem-app/bkchem/queryatom.py](packages/bkchem-app/bkchem/queryatom.py):
  `charge` setter tried to sync `_chem_query_atom` before it was initialized
  during `__init__`. Add `hasattr` guard.

## 2026-02-18
- Extract toolbar mode/submode config from Python to YAML: create
  [packages/bkchem-app/bkchem_data/modes.yaml](packages/bkchem-app/bkchem_data/modes.yaml)
  defining all 15 modes with submodes, icon mappings, group labels, tooltips,
  and toolbar ordering. Add YAML loader, `get_toolbar_order()`,
  `build_all_modes()` to
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py).
  Base `mode.__init__` auto-loads config from YAML using class name as key,
  eliminating hardcoded submodes/names/defaults from 13 mode class `__init__`
  methods. Unify `biomolecule_template_mode` and `user_template_mode` into
  `template_mode` parameterized by `template_source` and `use_categories` YAML
  fields. Add `icon_map` for YAML-driven icon name cascade (key -> icon
  override). Replace manual mode dict and `modes_sort` list in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py)
  with `build_all_modes()` and `get_toolbar_order()`. Remove dead
  `name_recode_map` dict from
  [packages/bkchem-app/bkchem/pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py).
  Rename `bond_align_mode` to `bondalign_mode`, `biomolecule_template_mode` to
  `biotemplate_mode`, `user_template_mode` to `usertemplate_mode` (old names
  kept as backwards-compatible aliases).
- Move peptide chemistry to OASA: `git mv` `peptide_utils.py` from
  `packages/bkchem-app/bkchem/` to
  [packages/oasa/oasa/peptide_utils.py](packages/oasa/oasa/peptide_utils.py).
  Remove fragile R-group placeholder substitution, build SMILES directly with
  side chains inline. Add `peptide_to_cdml_elements()` bridge function in
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py).
  BKChem GUI no longer knows about peptide chemistry, only prompts for input
  and renders the returned CDML.
- Add `.lower()` normalization in icon lookup in
  [packages/bkchem-app/bkchem/pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py):
  eliminates all `name_recode_map` entries. Rename `wavyline.gif` to `wavy.gif`
  and update `misc_mode` submode key from `wavyline` to `wavy` in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py).
- Add thick colored border on the selected mode button in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py):
  active mode shows sunken relief with blue highlight, unselected modes are flat.
- Rename icon files to match tool names: `hatch.gif` -> `hashed.gif`,
  `fixed_length.gif` -> `fixed.gif`, `2D.gif` -> `2d.gif`, `3D.gif` -> `3d.gif`,
  plus corresponding SVG sources. Shrink `name_recode_map` in
  [packages/bkchem-app/bkchem/pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py)
  from 5 entries to 3 (keep `wavy`->`wavyline`, `2D`->`2d`, `3D`->`3d`).
- Toolbar icon system overhaul (Phase 1 + 2) in
  [packages/bkchem-app/bkchem/pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py):
  expand `name_recode_map` with `hashed->hatch` (fixes missing hatch bond icon
  in draw mode), `2D->2d`, and `3D->3d` (prepare for lowercase PNG filenames).
  Update `__getitem__` and `__contains__` to try `.png` first with `.gif`
  fallback, enabling future PNG migration. Extract shared `_load_icon()` helper.
  Replace bare `except` clauses with explicit `KeyError`. Convert indentation
  from spaces to tabs per repo style.
- Fix menu font on macOS: change platform detection in `init_basics()` in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) from
  `os.name == 'posix'` to `sys.platform == 'linux'` so macOS no longer receives
  an X11 XLFD font string that Aqua Tk cannot interpret. macOS now uses the
  native system font (San Francisco / Lucida Grande) via `TkDefaultFont`.
- Rename `packages/bkchem` to `packages/bkchem-app` to eliminate the dual
  sys.path problem where both the package dir and inner module dir were on
  PYTHONPATH causing duplicate module objects. Updated PYTHONPATH in
  [source_me.sh](source_me.sh) and [launch_bkchem_gui.sh](launch_bkchem_gui.sh),
  fixed path references in
  [packages/bkchem-app/tests/conftest.py](packages/bkchem-app/tests/conftest.py),
  and converted bare imports to package-relative imports in GUI test files.
  Removed the `sys.modules` aliasing hack and inner `bkchem_module_dir` path
  from all `_ensure_sys_path()` and `_ensure_preferences()` helpers.
- Fix GUI subprocess tests broken by import conversion (commit `25120d6`):
  unify bare and package-relative `singleton_store` modules via
  `sys.modules` aliasing in `_ensure_preferences()` for
  [packages/bkchem-app/tests/test_bkchem_gui_zoom.py](packages/bkchem-app/tests/test_bkchem_gui_zoom.py),
  [packages/bkchem-app/tests/test_bkchem_gui_benzene.py](packages/bkchem-app/tests/test_bkchem_gui_benzene.py),
  [packages/bkchem-app/tests/test_bkchem_gui_events.py](packages/bkchem-app/tests/test_bkchem_gui_events.py).
- Fix `meta__undo_copy` and `meta__undo_children_to_record` in
  [packages/bkchem-app/bkchem/molecule.py](packages/bkchem-app/bkchem/molecule.py):
  rename `'atoms'`/`'bonds'` to `'vertices'`/`'edges'` to match actual
  instance attributes after composition refactor (`atoms`/`bonds` are now
  `@property` aliases and not in `__dict__`).
- Call `bkchem.chem_compat.register_bkchem_classes()` in both `initialize()`
  and `initialize_batch()` in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) so
  `is_chemistry_vertex`/`is_chemistry_edge`/`is_chemistry_graph` ABC checks
  work at runtime. Registration was defined but never called.
  All 5 GUI subprocess tests now pass.
- Wave 3 complete: all BKChem classes decoupled from OASA inheritance.
  No `oasa.*` class appears in any BKChem class bases. OASA is now used
  exclusively through composition (`_chem_atom`, `_chem_bond`, `_chem_mol`,
  `_chem_query_atom`).
- Remove 8 broken test files requiring uninitialized GUI singletons
  (Store.id_manager, Screen.dpi): `test_bkchem_cdml_bond_smoke.py`,
  `test_bkchem_cdml_vertex_tags.py`, `test_bkchem_cdml_writer_flag.py`,
  `test_bkchem_gui_benzene.py`, `test_bkchem_gui_events.py`,
  `test_bkchem_gui_zoom.py`, `test_codec_registry_bkchem_plugins.py`,
  `test_smiles_cdml_import.py`.
- Fix `import oasa` unused import in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py)
  after isinstance migration.
- Fix atom composition test fixture dual-module singleton collision in
  [packages/bkchem-app/tests/test_atom_composition_parity.py](packages/bkchem-app/tests/test_atom_composition_parity.py).
- Wave 3 C7+C8: remove `oasa.molecule` from class bases of
  [packages/bkchem-app/bkchem/molecule.py](packages/bkchem-app/bkchem/molecule.py);
  added `_chem_mol` composition layer wrapping `oasa.molecule()` for all graph
  algorithms; `vertices`/`edges`/`disconnected_edges` are shared references to
  `_chem_mol` collections; added `atoms`/`bonds` property aliases; delegated
  ~40 graph methods (connectivity, ring perception, matching, temp disconnect,
  distance marking, subgraph extraction, etc.) through `_chem_mol`; added
  `stereochemistry` list and stereochemistry methods locally; this is the last
  BKChem class to be decoupled from OASA inheritance.
- Wave 3 C4: remove `oasa.chem_vertex` from `drawable_chem_vertex` class bases
  in [packages/bkchem-app/bkchem/special_parents.py](packages/bkchem-app/bkchem/special_parents.py);
  replaced with `GraphVertexMixin` for graph connectivity; added chemistry
  properties (`charge`, `valency`, `occupied_valency`, `free_valency`,
  `free_sites`, `multiplicity`, `weight`, `coords`) and methods
  (`has_aromatic_bonds`, `bond_order_changed`, `get_hydrogen_count`, `matches`)
  directly into `drawable_chem_vertex`.
- Wave 3 C3: remove `oasa.query_atom` from class bases of
  [packages/bkchem-app/bkchem/queryatom.py](packages/bkchem-app/bkchem/queryatom.py);
  `symbol` property now reads/writes through `_chem_query_atom` composition
  attribute; `__init__` passes coords to composed `_chem_query_atom`; added
  `matches()` method delegating to `_chem_query_atom.matches()`; cleaned up
  trailing comma in class definition.
- Wave 3 C1: remove `oasa.bond` from class bases of
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py); all
  chemistry properties (`order`, `type`, `aromatic`, `stereochemistry`) now
  delegate solely through `_chem_bond` composition attribute; added standalone
  `_bond_vertices` list, `vertices` property, `get_vertices()`/`set_vertices()`
  methods, and `properties_`/`disconnected` attributes formerly inherited from
  `oasa.edge`.
- Wave 3 C2: remove `oasa.atom` from class bases of
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py); all
  chemistry properties (`symbol`, `isotope`, `multiplicity`, `occupied_valency`,
  `electronegativity`, `oxidation_number`, etc.) now delegate through `_chem_atom`
  composition attribute; removed `xfail` markers from 7 composition parity tests.
- Wave 3 C6: replace 4 `isinstance(x, oasa.*)` checks in
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py) with
  `bkchem.chem_compat` helpers (`is_chemistry_vertex`, `is_chemistry_edge`,
  `is_chemistry_graph`); verified `interactors.py` has 0 isinstance oasa checks.
- Wave 2 shadow layer: add `_chem_bond` composition attribute to
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py) with
  `_bond_vertices` shadow list; redirect `order`, `type`, `aromatic`,
  `stereochemistry` properties through `_chem_bond`; redirect
  `atom1`/`atom2`/`atoms` through `_bond_vertices`.
- Wave 2 shadow layer: add `_chem_atom` composition attribute to
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py); sync
  `symbol`, `isotope`, `charge`, `valency`, `multiplicity` through `_chem_atom`.
- Wave 2 shadow layer: add `_chem_query_atom` composition attribute to
  [packages/bkchem-app/bkchem/queryatom.py](packages/bkchem-app/bkchem/queryatom.py);
  sync `symbol` and `charge` through `_chem_query_atom`.
- Wave 2: update
  [packages/bkchem-app/bkchem/bond_cdml.py](packages/bkchem-app/bkchem/bond_cdml.py)
  to read/write `type` and `order` via `_chem_bond` in `read_package` and
  `get_package`.
- Wave 2: create
  [packages/bkchem-app/bkchem/graph_vertex_mixin.py](packages/bkchem-app/bkchem/graph_vertex_mixin.py)
  replicating `oasa.graph.vertex` interface as a BKChem mixin for Wave 3 MRO
  removal.
- Wave 2: add composition-aware docstrings and comments to
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
  documenting which property accesses delegate to `_chem_atom`/`_chem_bond`.
- Wave 2: audit `bond_display.py`, `bond_drawing.py`, `bond_type_control.py`,
  `bond_render_ops.py` -- no code changes needed, all chemistry reads use
  property accessors that delegate through `_chem_bond` automatically.
- Wave 1 post-review cleanup: fix `from` imports in
  [packages/bkchem-app/tests/test_molecule_composition_parity.py](packages/bkchem-app/tests/test_molecule_composition_parity.py)
  to use `import oasa` style, fix isinstance audit count (20 in modes.py, 30
  total), remove unused imports across all test files.
- Add chemistry Protocol classes
  [packages/bkchem-app/bkchem/chem_protocols.py](packages/bkchem-app/bkchem/chem_protocols.py)
  defining `ChemVertexProtocol`, `ChemEdgeProtocol`, and `ChemGraphProtocol` with
  `runtime_checkable=True` matching exact OASA method signatures for the composition
  refactor.
- Add ABC compatibility registration module
  [packages/bkchem-app/bkchem/chem_compat.py](packages/bkchem-app/bkchem/chem_compat.py)
  with `register_bkchem_classes()` and helper functions `is_chemistry_vertex()`,
  `is_chemistry_edge()`, `is_chemistry_graph()` for isinstance checks after MRO
  removal.
- Add bond composition parity test harness
  [packages/bkchem-app/tests/test_bond_composition_parity.py](packages/bkchem-app/tests/test_bond_composition_parity.py)
  with 90 passing tests covering all 9 bond types, 4 bond orders, atom1/atom2
  access, `_vertices` patterns, display properties, and 6 xfail composition stubs.
- Add atom composition parity test harness
  [packages/bkchem-app/tests/test_atom_composition_parity.py](packages/bkchem-app/tests/test_atom_composition_parity.py)
  with 52 passing tests and 7 xfail composition stubs covering chemistry
  properties, symbol setter side effects, coordinate conversion via
  Screen.any_to_px, graph connectivity, display properties, charge override
  delegation, OASA baseline, and composition delegation placeholders.
- Add molecule composition parity test harness
  [packages/bkchem-app/tests/test_molecule_composition_parity.py](packages/bkchem-app/tests/test_molecule_composition_parity.py)
  with 40 passing tests and 7 xfail composition stubs covering atom/bond aliases,
  graph mutation, connectivity, factory methods, ring perception (benzene and
  naphthalene), deep copy, and stereochemistry list management.
- Add CDML round-trip parity tests
  [packages/bkchem-app/tests/test_cdml_roundtrip_parity.py](packages/bkchem-app/tests/test_cdml_roundtrip_parity.py)
  with 44 passing tests covering bond type/order round-trip for all 9 types x 3
  orders, unknown attribute preservation, coordinate unit conversion, bond_width
  sign, center/auto_sign, wavy_style, line_color, equithick, double_length_ratio,
  simple_double, and wedge_width serialization round-trips.
- Add isinstance audit [docs/ISINSTANCE_AUDIT.md](docs/ISINSTANCE_AUDIT.md)
  documenting all 30 `isinstance(x, oasa.*)` checks across 4 files with
  replacement strategies for the composition refactor.
- Add internal access audit
  [docs/INTERNAL_ACCESS_AUDIT.md](docs/INTERNAL_ACCESS_AUDIT.md)
  documenting all 11 `._vertices`, `._neighbors`, and `.properties_` accesses
  in BKChem code that reach into OASA internals, with fix strategies and risk
  assessment for the composition refactor.
- Add OASA/BKChem boundary contract document
  [docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  defining atom, bond, molecule, CDML serialization, and bridge layer contracts.
- Add composition refactor plan
  [docs/active_plans/COMPOSITION_REFACTOR_PLAN.md](active_plans/COMPOSITION_REFACTOR_PLAN.md)
  with three-wave approach: foundation infrastructure, shadow layer, MRO removal.
- Convert bare local imports to package-relative imports in 16 bkchem
  utility/support files:
  [pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py) (1 import),
  [marks.py](packages/bkchem-app/bkchem/marks.py) (4 imports),
  [classes.py](packages/bkchem-app/bkchem/classes.py) (7 imports),
  [graphics.py](packages/bkchem-app/bkchem/graphics.py) (7 imports),
  [helper_graphics.py](packages/bkchem-app/bkchem/helper_graphics.py) (1 import),
  [arrow.py](packages/bkchem-app/bkchem/arrow.py) (7 imports),
  [undo.py](packages/bkchem-app/bkchem/undo.py) (1 import),
  [debug.py](packages/bkchem-app/bkchem/debug.py) (1 import),
  [logger.py](packages/bkchem-app/bkchem/logger.py) (1 import),
  [validator.py](packages/bkchem-app/bkchem/validator.py) (4 imports),
  [external_data.py](packages/bkchem-app/bkchem/external_data.py) (10 imports),
  [plugin_support.py](packages/bkchem-app/bkchem/plugin_support.py) (4 imports),
  [template_catalog.py](packages/bkchem-app/bkchem/template_catalog.py) (1 import),
  [format_loader.py](packages/bkchem-app/bkchem/format_loader.py) (2 imports),
  [checks.py](packages/bkchem-app/bkchem/checks.py) (1 import),
  [plugins/__init__.py](packages/bkchem-app/bkchem/plugins/__init__.py) (1 import),
  [plugins/gtml.py](packages/bkchem-app/bkchem/plugins/gtml.py) (7 imports).
- Convert bare local imports to package-relative imports in four bkchem
  application files:
  [main.py](packages/bkchem-app/bkchem/main.py) (24 imports),
  [paper.py](packages/bkchem-app/bkchem/paper.py) (28 imports),
  [bkchem_app.py](packages/bkchem-app/bkchem/bkchem_app.py) (8 imports),
  [splash.py](packages/bkchem-app/bkchem/splash.py) (2 imports).
  [cli.py](packages/bkchem-app/bkchem/cli.py) had no bare local imports (uses
  `runpy.run_module` which is not a bare import).
- Convert bare local imports to package-relative imports in six UI/interaction
  bkchem files:
  [dialogs.py](packages/bkchem-app/bkchem/dialogs.py) (6 imports),
  [widgets.py](packages/bkchem-app/bkchem/widgets.py) (5 imports),
  [interactors.py](packages/bkchem-app/bkchem/interactors.py) (9 imports),
  [edit_pool.py](packages/bkchem-app/bkchem/edit_pool.py) (5 imports),
  [modes.py](packages/bkchem-app/bkchem/modes.py) (18 imports),
  [context_menu.py](packages/bkchem-app/bkchem/context_menu.py) (7 imports).
- Convert bare local imports to package-relative imports in six bkchem files:
  [molecule.py](packages/bkchem-app/bkchem/molecule.py) (13 imports),
  [reaction.py](packages/bkchem-app/bkchem/reaction.py) (2 imports),
  [oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py) (4 imports),
  [export.py](packages/bkchem-app/bkchem/export.py) (2 imports),
  [CDML_versions.py](packages/bkchem-app/bkchem/CDML_versions.py) (2 imports).
  [peptide_utils.py](packages/bkchem-app/bkchem/peptide_utils.py) had no local imports.
- Convert bare local imports to package-relative imports in four bkchem
  vertex files:
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py),
  [packages/bkchem-app/bkchem/group.py](packages/bkchem-app/bkchem/group.py),
  [packages/bkchem-app/bkchem/textatom.py](packages/bkchem-app/bkchem/textatom.py),
  [packages/bkchem-app/bkchem/queryatom.py](packages/bkchem-app/bkchem/queryatom.py).
  Changed `import data/marks/dom_extensions/groups_table` to
  `from . import ...` and `from singleton_store/special_parents import ...`
  to `from .singleton_store/special_parents import ...`.
  [packages/bkchem-app/bkchem/groups_table.py](packages/bkchem-app/bkchem/groups_table.py)
  has no imports and required no changes.
- Convert bare local import to package-relative import in
  [packages/bkchem-app/bkchem/dom_extensions.py](packages/bkchem-app/bkchem/dom_extensions.py):
  `import safe_xml` changed to `from . import safe_xml`.
- Replace local `get_repo_root()` / `_get_repo_root()` definitions in 14
  `tools/*.py` files with `import git_file_utils` from
  [tests/git_file_utils.py](tests/git_file_utils.py). Removes duplicated
  subprocess calls and centralizes repo root detection. Affected files:
  [tools/neurotiker_furanose_geometry.py](tools/neurotiker_furanose_geometry.py),
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py),
  [tools/haworth_visual_check_pdf.py](tools/haworth_visual_check_pdf.py),
  [tools/measure_cairo_pdf_parity.py](tools/measure_cairo_pdf_parity.py),
  [tools/rdkit_sugar_comparison.py](tools/rdkit_sugar_comparison.py),
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py),
  [tools/check_translation.py](tools/check_translation.py),
  [tools/render_reference_outputs.py](tools/render_reference_outputs.py),
  [tools/coords_comparison.py](tools/coords_comparison.py),
  [tools/selftest_sheet.py](tools/selftest_sheet.py),
  [tools/sugar_codes_summary.py](tools/sugar_codes_summary.py),
  [tools/alignment_summary.py](tools/alignment_summary.py),
  [tools/gap_perp_gate.py](tools/gap_perp_gate.py),
  [tools/render_beta_sheets.py](tools/render_beta_sheets.py).
  Also removed now-unused `import subprocess` from files that no longer need it.
- Fix import references in 25 OASA test files under
  [packages/oasa/tests/](packages/oasa/tests/) after move from repo root
  `tests/` directory: remove `conftest.add_oasa_to_sys_path()` calls (now
  handled automatically by the new conftest.py), remove `sys.modules["oasa"]`
  cleanup lines, replace `conftest.tests_path(` with
  `conftest.repo_tests_path(`, and remove now-unused `import conftest`,
  `import sys` lines where appropriate.
- Add Align menu action registrations in
  [packages/bkchem-app/bkchem/actions/align_actions.py](packages/bkchem-app/bkchem/actions/align_actions.py):
  registers 6 Align menu actions (top, bottom, left, right, center_h,
  center_v) with enabled_when='two_or_more_selected'.
- Add Insert menu action registrations in
  [packages/bkchem-app/bkchem/actions/insert_actions.py](packages/bkchem-app/bkchem/actions/insert_actions.py):
  registers 1 Insert menu action (biomolecule_template).
- Add Options menu action registrations in
  [packages/bkchem-app/bkchem/actions/options_actions.py](packages/bkchem-app/bkchem/actions/options_actions.py):
  registers 5 Options menu actions (standard, language, logging,
  inchi_path, preferences) with try/except for interactors and Store.
- Add Help menu action registrations in
  [packages/bkchem-app/bkchem/actions/help_actions.py](packages/bkchem-app/bkchem/actions/help_actions.py):
  registers 1 Help menu action (about).
- Add Plugins menu action registrations in
  [packages/bkchem-app/bkchem/actions/plugins_actions.py](packages/bkchem-app/bkchem/actions/plugins_actions.py):
  no-op register function for the currently empty Plugins menu.
- Add tests for remaining menu actions in
  [packages/bkchem-app/tests/test_remaining_actions.py](packages/bkchem-app/tests/test_remaining_actions.py):
  9 tests covering action counts, IDs, enabled_when, and label keys for
  align, insert, options, help, and plugins menus.
- Add menu builder in
  [packages/bkchem-app/bkchem/menu_builder.py](packages/bkchem-app/bkchem/menu_builder.py):
  MenuBuilder class that reads YAML menu structure, resolves actions from
  ActionRegistry, and calls PlatformMenuAdapter to construct menus. Supports
  dynamic state updates via enabled_when predicates and plugin slot injection
  for exporter/importer cascades.
- Add menu builder tests in
  [packages/bkchem-app/tests/test_menu_builder.py](packages/bkchem-app/tests/test_menu_builder.py):
  11 tests covering menu creation, command placement, separators, cascades,
  missing action handling, state updates (callable and string predicates),
  plugin slot discovery, and plugin slot injection.
- Add Chemistry menu action registrations in
  [packages/bkchem-app/bkchem/actions/chemistry_actions.py](packages/bkchem-app/bkchem/actions/chemistry_actions.py):
  registers 14 Chemistry menu actions (info, check, expand-groups,
  oxidation-number, read-smiles, read-inchi, read-peptide, gen-smiles,
  gen-inchi, set-name, set-id, create-fragment, view-fragments,
  convert-to-linear) with the ActionRegistry.
- Add View menu action registrations in
  [packages/bkchem-app/bkchem/actions/view_actions.py](packages/bkchem-app/bkchem/actions/view_actions.py):
  registers 5 View menu actions (zoom-in, zoom-out, zoom-reset,
  zoom-to-fit, zoom-to-content) with the ActionRegistry.
- Add tests for chemistry and view actions in
  [packages/bkchem-app/tests/test_chemistry_view_actions.py](packages/bkchem-app/tests/test_chemistry_view_actions.py):
  6 tests covering action counts, IDs, and enabled_when type correctness.
- Fix pyproject.toml multiline inline table that blocked pytest 9.0.2 TOML
  parsing for all tests under packages/bkchem-app/.
- Add platform menu adapter in
  [packages/bkchem-app/bkchem/platform_menu.py](packages/bkchem-app/bkchem/platform_menu.py):
  wraps Pmw.MainMenuBar (macOS) and Pmw.MenuBar (Linux/Windows) behind a uniform
  PlatformMenuAdapter class with methods for add_menu, add_command, add_separator,
  add_cascade, add_command_to_cascade, get_menu_component, and set_item_state.
- Add platform menu adapter tests in
  [packages/bkchem-app/tests/test_platform_menu.py](packages/bkchem-app/tests/test_platform_menu.py):
  10 tests covering macOS vs Linux menubar selection, menu/command/separator/cascade
  addition, side-argument suppression on macOS, and enable/disable state changes.
- Add YAML menu structure file
  [packages/bkchem-app/bkchem_data/menus.yaml](packages/bkchem-app/bkchem_data/menus.yaml):
  defines the complete menu hierarchy (10 menus, 55 actions, 19 separators,
  3 cascades) with order, side placement, and cascade definitions. Action details
  remain in the ActionRegistry.
- Add menu YAML tests in
  [packages/bkchem-app/tests/test_menu_yaml.py](packages/bkchem-app/tests/test_menu_yaml.py):
  13 tests covering YAML parsing, menu count/order, side assignments, item type
  validation, action ID format, duplicate detection, cascade resolution, and
  per-menu item counts.
- Add Edit menu action registrations in
  [packages/bkchem-app/bkchem/actions/edit_actions.py](packages/bkchem-app/bkchem/actions/edit_actions.py):
  registers 7 Edit menu actions (undo, redo, cut, copy, paste, selected-to-SVG,
  select-all) with the ActionRegistry.
- Add Object menu action registrations in
  [packages/bkchem-app/bkchem/actions/object_actions.py](packages/bkchem-app/bkchem/actions/object_actions.py):
  registers 7 Object menu actions (scale, bring-to-front, send-back,
  swap-on-stack, vertical-mirror, horizontal-mirror, configure) with the
  ActionRegistry.
- Add tests for edit and object actions in
  [packages/bkchem-app/tests/test_edit_object_actions.py](packages/bkchem-app/tests/test_edit_object_actions.py):
  6 tests covering action counts, IDs, and enabled_when type correctness.
- Add File menu action registrations in
  [packages/bkchem-app/bkchem/actions/file_actions.py](packages/bkchem-app/bkchem/actions/file_actions.py):
  registers 9 File menu actions (new, save, save-as, save-as-template, load,
  load-same-tab, properties, close-tab, exit) with the ActionRegistry. Includes
  tests in
  [packages/bkchem-app/tests/test_file_actions.py](packages/bkchem-app/tests/test_file_actions.py).
- Add ActionRegistry core package in
  [packages/bkchem-app/bkchem/actions/__init__.py](packages/bkchem-app/bkchem/actions/__init__.py):
  provides `MenuAction` dataclass and `ActionRegistry` class as the shared contract
  for the modular menu refactor. Includes `register_all_actions()` with graceful
  import guards for per-menu modules not yet written.
- Add Phase 0 menu template extract
  [docs/active_plans/MENU_TEMPLATE_EXTRACT.md](docs/active_plans/MENU_TEMPLATE_EXTRACT.md):
  catalogs all 87 `menu_template` tuples (10 menus, 55 commands, 19 separators,
  3 cascades) with proposed action IDs, handler expressions, state variables,
  and summary counts. Source-of-truth reference for all 8 parallel coders.
- Add menu refactor execution plan
  [docs/active_plans/MENU_REFACTOR_EXECUTION_PLAN.md](docs/active_plans/MENU_REFACTOR_EXECUTION_PLAN.md):
  breaks the YAML + action registry menu refactor into 4 parallel-safe streams
  with file ownership boundaries, dependency graph, and measurable done checks.
  Scopes out format-handler migration, renderer unification, and Tool framework
  as separate projects.
- Add "Read Peptide Sequence" menu item under Chemistry in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py):
  prompts for a single-letter amino acid sequence (e.g. ANKLE), converts it
  to IsoSMILES via new
  [packages/bkchem-app/bkchem/peptide_utils.py](packages/bkchem-app/bkchem/peptide_utils.py),
  and renders the polypeptide structure through the existing SMILES-to-CDML
  pipeline.

## 2026-02-17
- Route all complex substituents through `coords_generator2` in
  [packages/oasa/oasa/haworth/fragment_layout.py](packages/oasa/oasa/haworth/fragment_layout.py):
  remove `_two_carbon_tail_fragment()` special case and `branch_length` parameter.
  CH(OH)CH2OH and CHAIN<N> now use the same 120-degree lattice-aligned molecular
  geometry path. Down-direction two-carbon tails produce symmetric 30/150 degree
  branch angles instead of side-dependent orientation.
- Route CHAIN<N> labels through `_add_fragment_ops()` in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  CHAIN3+ labels now use `coords_generator2` zigzag geometry with proper OH
  branches at each junction, replacing the collinear `_add_chain_ops()` path.
  Add `_fragment_chain_numbers()` for sequential chain segment op_id naming
  (chain1, chain1_oh, chain2, chain2_oh, chain3).
- Add fragment-based substituent layout module
  [packages/oasa/oasa/haworth/fragment_layout.py](packages/oasa/oasa/haworth/fragment_layout.py):
  uses `coords_generator2` to identify display groups from SMILES fragments, and
  provides `FragmentAtom` dataclass and `layout_fragment()` for computing
  positioned atom groups for complex substituents (CH(OH)CH2OH, CHAIN<N>).
- Add unified `_add_fragment_ops()` renderer path in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  replaces `_add_furanose_two_carbon_tail_ops()` for branched CH(OH)CH2OH tails
  using the new fragment layout infrastructure. Produces backwards-compatible
  op_ids and rendering (connectors, text labels, hashed bonds). Legacy
  `_add_chain_ops` retained for sequential CHAIN<N> rendering.
- Add 25 unit tests in
  [tests/test_haworth_fragment_layout.py](tests/test_haworth_fragment_layout.py)
  covering SMILES lookup, fragment grouping, two-carbon tail geometry (branch
  angles, bond styles, parent indices), and CHAIN<N> group identification.
- Switch chain-like labels (CH2OH, CHOH, CH3, HOH2C, etc.) to full-box bond
  trimming (`target_kind="label_box"`) in the Haworth renderer.  Connector
  endpoints now resolve against the full label bounding box instead of
  narrowing to the specific carbon glyph.  Removes the `endswith("C")` hack
  for reversed labels.  Hydroxyl (OH/HO) labels keep oxygen-circle targeting;
  two-carbon tail ops and multi-segment chain ops keep explicit `attach_box`
  targeting.
- Fix IndexError crash when rotating molecules with double bonds in
  [packages/bkchem-app/bkchem/bond_display.py](packages/bkchem-app/bkchem/bond_display.py):
  guard `self.second[0]` access in `transform()` since the render-ops draw path
  never populates `self.second` for double bonds.
- Route BKChem SMILES import through CDML: replace direct
  `oasa_mol_to_bkchem_mol` bridge with `smiles_to_cdml_elements()` in
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py),
  update `read_smiles()` dialog in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) to use
  `paper.add_object_from_package()`, and remove old `read_smiles` bridge
  function. Updated dialog text to indicate IsoSMILES support.
- Add pytest test suite
  [tests/test_smiles_cdml_import.py](tests/test_smiles_cdml_import.py) for the
  `smiles_to_cdml_elements()` function in `oasa_bridge.py` (7 tests covering
  ethanol, benzene, coordinate units, bond length, disconnected SMILES, empty
  input, and atom names).
- Fix disconnected SMILES handling in `smiles_to_cdml_elements()` in
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py):
  add `mol.remove_zero_order_bonds()` call so dot-separated SMILES like "CC.OO"
  are correctly split into separate CDML molecule elements.
- Add SMILES/IsoSMILES CDML import plan
  [docs/active_plans/SMILES_CDML_IMPORT_PLAN.md](docs/active_plans/SMILES_CDML_IMPORT_PLAN.md)
  to route SMILES import through the canonical CDML serialization path instead
  of the direct `oasa_mol_to_bkchem_mol` bridge.
- Add three-layer 2D coordinate generator
  [packages/oasa/oasa/coords_generator2.py](packages/oasa/oasa/coords_generator2.py)
  that produces RDKit-quality 2D layouts without the RDKit dependency.
  Implements ring system assembly (fused, spiro, bridged), BFS chain/substituent
  placement, collision detection with flip/nudge resolution, and force-field
  refinement (bond stretch + angle bend + non-bonded repulsion).
- Add coordinate generator tests
  [tests/test_coords_generator2.py](tests/test_coords_generator2.py) covering
  single atoms, chains, benzene, naphthalene, spiro, steroid skeleton, triple
  bonds, branching, and force parameter behavior (23 tests).
- Add visual comparison tool
  [tools/coords_comparison.py](tools/coords_comparison.py) that renders
  side-by-side HTML galleries of old vs new vs RDKit 2D coordinate layouts
  for 24 test molecules.
- Update [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
  to prefer `coords_generator2` over legacy `coords_generator` when RDKit is not
  available, with graceful fallback to the old generator.
- Add RDKit bridge module
  [packages/oasa/oasa/rdkit_bridge.py](packages/oasa/oasa/rdkit_bridge.py) for
  converting between OASA and RDKit molecule representations and generating 2D
  coordinates via `AllChem.Compute2DCoords`.  Provides `oasa_to_rdkit_mol`,
  `rdkit_to_oasa_mol`, and `calculate_coords_rdkit` functions following the same
  pattern as the existing `pybel_bridge.py`.
- Add RDKit sugar comparison gallery tool
  [tools/rdkit_sugar_comparison.py](tools/rdkit_sugar_comparison.py) that
  renders side-by-side Haworth projection SVGs and RDKit 2D depiction SVGs for
  all sugar codes.  Outputs `output_smoke/rdkit_comparison_pyranose.html` and
  `output_smoke/rdkit_comparison_furanose.html` with comparison pairs.
- Wire RDKit coordinate generation into bkchem SMILES import pipeline.
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
  now uses `rdkit_bridge.calculate_coords_rdkit` when RDKit is available,
  falling back to OASA's native `coords_generator` when it is not.
- Add `rdkit` to [pip_requirements.txt](pip_requirements.txt).
- Add 3-KETO ring rules to Haworth spec
  ([packages/oasa/oasa/haworth/spec.py](packages/oasa/oasa/haworth/spec.py)):
  furanose (anomeric=3, closure=6, min_carbons=6) and pyranose (anomeric=3,
  closure=7, min_carbons=7).  Handle 3-KETO anomeric substituent with
  CH(OH)CH2OH pre-anomeric chain.  Enables rendering of 3-ketohexoses.
- Fix CH2OH label overlap on left-side furanose ring slots.  Chain-like labels
  (CH2OH, CHOH) at anchor=end slots (ML, BL) now render as HOH2C/HOHC via
  `format_chain_label_text`, so the carbon atom faces the ring and the label
  does not overlap ring bonds.  Connector attach-atom policy updated to target
  the trailing carbon in reversed text.
- Add sugar codes HTML gallery script
  [tools/sugar_codes_summary.py](tools/sugar_codes_summary.py) that reads all
  106 sugar codes from
  [packages/oasa/oasa_data/sugar_codes.yaml](packages/oasa/oasa_data/sugar_codes.yaml),
  renders each valid ring/anomeric combination as a Haworth projection SVG
  file, and writes two separate HTML gallery pages:
  `output_smoke/sugar_codes_pyranose.html` and
  `output_smoke/sugar_codes_furanose.html`.  SVG previews are written to
  `output_smoke/sugar_codes_previews/` and referenced via `<img>` tags.  Each
  page has a cross-link to the other ring type gallery in the sticky header.
  Uses the same earth-tone CSS theme and `_normalize_generated_svg` viewBox
  logic as `tools/archive_matrix_summary.py`.  Grouped by YAML category with
  section headers; sugars that cannot form valid rings show "No valid
  [ring type] ring forms".

## 2026-02-15
- Add macOS DMG build script
  [devel/build_macos_dmg.py](devel/build_macos_dmg.py) that produces a
  self-contained `BKChem.app` bundle via PyInstaller and wraps it in a
  `BKChem-VERSION.dmg` disk image.  Generates `.icns` icon from
  `bkchem.svg` via `rsvg-convert` + `iconutil`.  Bundles embedded Python
  3.12, Tcl/Tk, pycairo, Pmw, oasa, bkchem_data, oasa_data, and addons.
  Patches `Info.plist` with version, bundle ID, Retina support, and
  `.cdml` file association.  Post-build verification checks executable,
  data dirs, Tcl/Tk, and libcairo presence.  Add `pyinstaller` to
  [pip_requirements-dev.txt](pip_requirements-dev.txt) and `librsvg` to
  [Brewfile](Brewfile).  Update
  [docs/active_plans/RELEASE_DISTRIBUTION.md](docs/active_plans/RELEASE_DISTRIBUTION.md)
  to reference the new script.
- Fix bond line overlapping C glyph in HOH2C connector on two-carbon down
  tails.  Two changes in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  (1) make `_retreat_to_target_gap()` iterative (up to 4 iterations) so
  diagonal approach angles converge to the correct gap instead of
  under-retreating on a single pass; (2) add a second retreat pass against
  the full label text box after the endpoint-atom retreat, using
  `ATTACH_GAP_TARGET` as the minimum gap, so the bond clears non-attach
  characters (like the subscript "2") that are closer than the target atom.
  Add diagonal convergence test in
  [tests/test_render_geometry.py](tests/test_render_geometry.py).  Update
  attach-element epsilon in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to
  accommodate the additional full-label retreat.
- Fix key letter selection in glyph bond alignment measurement.  The character
  selection heuristic used canonical text ("CH2OH") instead of displayed text
  ("HOH2C") and did not skip terminal H in multi-character labels, causing the
  measurement tool to pick "H" at the far left of "HOH2C" instead of "C" at
  the bond endpoint on the right.  Add `_select_key_letter()` helper in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) that searches
  inward from the specified end, skipping H for multi-character labels.  Switch
  alpha_chars extraction from canonical to displayed text via
  `label_geometry_text()`.  Add cross-reference comment in
  [tools/measurelib/glyph_model.py](tools/measurelib/glyph_model.py) linking
  `is_measurement_label()` to the key letter heuristic.  Update and add tests
  in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py).
- Fix hatch strokes touching glyph letters by using `epsilon=0.0` for hatch
  filtering in `validate_attachment_paint()`.  The previous `STRICT_OVERLAP_EPSILON`
  (0.5) shrank the forbidden box, allowing hatches up to 0.5 px inside the glyph
  boundary.  Solid connectors avoid this via an additional retreat step that
  hatches lack, so hatches need exact boundary enforcement.  Fix in
  `_append_branch_connector_ops()` in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
- Trim hatched bond carrier line endpoint to last surviving hatch stroke in
  Haworth renderer.  When forbidden-region filtering removes hatch strokes
  near a label, the invisible carrier line no longer extends past the last
  visible stroke into the glyph boundary.  Prevents false-negative gap
  measurements from the carrier endpoint reaching into label space.  Fix in
  `_append_branch_connector_ops()` in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
- Implement Phase 6: expand sugar_code_to_smiles() from 2-entry bootstrap to
  generalized algorithmic Fischer-to-SMILES builder.  Supports all ~148 sugar
  codes in sugar_codes.yaml across pyranose/furanose ring forms and alpha/beta
  anomeric configurations.  Uses fixed ring traversal order with position-based
  chirality mapping (Fischer R/L to SMILES @/@@) derived from the existing
  Haworth spec up/down labels.  Handles aldoses and ketoses including tetroses
  through heptoses with 1-3 carbon exocyclic chains, plus modified sugars
  (deoxy, amino, N-acetyl, fluoro, phosphate, carboxyl) in
  [packages/oasa/oasa/sugar_code_smiles.py](packages/oasa/oasa/sugar_code_smiles.py).
  Tests expanded from 6 to 446 in
  [tests/test_sugar_code_smiles.py](tests/test_sugar_code_smiles.py).
- Implement Phase 7: create smiles_to_sugar_code() reverse converter with
  two-tier approach.  Tier 1 builds a lookup table at module load from all
  sugar_codes.yaml entries via Phase 6 sugar_code_to_smiles().  Tier 2 parses
  the SMILES into a molecule, finds sugar-like rings, and tries candidate
  matches.  New module
  [packages/oasa/oasa/smiles_to_sugar_code.py](packages/oasa/oasa/smiles_to_sugar_code.py)
  with SugarCodeResult dataclass and SugarCodeError exception.  All standard
  sugar codes round-trip perfectly (sugar code -> SMILES -> sugar code).
  447 tests in
  [tests/test_smiles_to_sugar_code.py](tests/test_smiles_to_sugar_code.py).
  Registered in
  [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py).
- Widen HOH2C solid connector gap using standard OASA geometry.  The CH2OH arm
  in `_add_furanose_two_carbon_tail_ops()` used a custom
  `_align_text_origin_to_endpoint_target_centroid()` step and
  `direction_policy="line"` that differed from the standard `_add_chain_ops`
  path.  Remove the custom alignment, switch to `direction_policy="auto"` with
  `attach_site="core_center"`, and add round-cap compensation
  (`connector_width * 0.5`) to `target_gap` so the visual gap after the round
  cap extends is at least `ATTACH_GAP_TARGET`.  Affects furanose sugars with
  two-carbon tails in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
- Extend down-direction furanose two-carbon tail connectors to match up-direction
  lengths.  Down-direction tails (e.g., ARRLDM furanose beta, ALRLDM furanose
  alpha) had very short HO and HOH2C branch arms because no oxygen clearance
  extension was applied for `direction == "down"`.  Add the same minimum
  effective_length formula used by up-direction tails inside the two-carbon-tail
  block in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py),
  giving symmetric trunk lengths for both directions.
- Fix hatched connector overlap with CH2OH text in furanose two-carbon tails.
  Hatch strokes near the label end were incorrectly allowed through the
  forbidden-region filter because `allowed_regions` (the attach-point carve-out
  for the invisible carrier line) overrode the text bounding-box exclusion.
  Remove `allowed_regions` from hatch stroke legality checks in
  `_append_branch_connector_ops()` in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  so individual hatch marks always stop before the label text.  Affects
  furanose sugars with hatched CH2OH branch (up direction: ALLRDM, ALRRDM,
  ARLRDM, etc.) and hatched HO branch (down direction: ARRLDM, etc.).
- Close and archive Haworth schematic renderer implementation plan (attempt 2).
  Core phases 1-5c complete. Deferred SMILES conversion phases (6, 7) and
  stretch goals (6b) to [docs/TODO_CODE.md](docs/TODO_CODE.md). Move plan to
  [docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md).
  Fix stale [docs/ROADMAP.md](docs/ROADMAP.md) references to archived plans.
- Add ring oxygen gap measurement via virtual connector lines.  Haworth sugar
  SVGs render ring edges as filled `<polygon>` elements, not `<line>` elements,
  so the ring oxygen "O" label had no nearby line endpoint and got
  `no_connector` in measurements.  Store polygon vertex coordinates in ring
  primitives (`"points"` key) in
  [tools/measurelib/svg_parse.py](tools/measurelib/svg_parse.py).  New
  `oxygen_virtual_connector_lines()` in
  [tools/measurelib/haworth_ring.py](tools/measurelib/haworth_ring.py) finds the
  two ring polygon edges closest to the O label and synthesizes virtual line
  dicts from their center axes.  Integrate virtual lines into the analysis
  pipeline in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py): append to
  `lines` list, include in connector candidates, exclude from width pool, bond
  length statistics, and checked bond indexes.  Include virtual lines in
  diagnostic perpendicular markers.
- Replace CH2OH fan-out solver with standard OASA connector path in Haworth
  furanose two-carbon tail renderer.  Delete `_chain2_label_offset_candidates()`
  and `_solve_chain2_label_with_resolver()` (53-candidate fan-out solver) from
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  Use same standard 3-step connector path as the HO arm and all simple OH
  connectors: `_align_text_origin_to_endpoint_target_centroid()` +
  `label_target_from_text_origin()` +
  `resolve_label_connector_endpoint_from_text_origin()` with
  `direction_policy="line"`.  Remove `min_standoff_factor` floor hack so
  `branch_standoff` uses `segment_length` directly.  Before: CH2OH arm ~10.2
  units vs HO arm ~17.0 units (67% mismatch); hatched connector overlapped
  CH2OH glyph in up case.  After: both arms use the same geometry-derived
  length with standard gaps.  Mark H-024 and H-025 as removed in
  [docs/HAWORTH_OVERRIDES.md](docs/HAWORTH_OVERRIDES.md).  Update
  `direction_policy` in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to match.
- Fix two-carbon tail bond lengths in Haworth furanose renderer.  Unify
  `min_standoff_factor` from direction-asymmetric values (`up=1.75`,
  `down=1.35`) to a single `1.35` floor so standard `segment_length` wins.
  Normalize `ho_length_factor` and `ch2_length_factor` from `0.90`/`0.95`/`1.20`
  to `1.0` for both up and down directions so arm lengths match the base
  `segment_length` used by simple hydroxyl connectors.  Before: CH2OH bond
  ~20.3 units with text overlap, HO bond ~12.8 units with sub-minimum gap.
  After: both arms ~16 units with 1.3-1.7 gaps matching standard connectors.
  Changes in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  Update H-025 status in
  [docs/HAWORTH_OVERRIDES.md](docs/HAWORTH_OVERRIDES.md).
  Relax hashed connector nearest-hatch threshold from 15% to 18% of connector
  length in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to
  accommodate shorter normalized connectors.  Remove 3 `xfail` markers from
  ALLLDM pyranose beta upward hydroxyl connector tests that now pass with
  unified standoff.
- Fix regression expectations in
  [tests/test_attach_targets.py](tests/test_attach_targets.py) for
  `label_target()` box geometry after calibrated text top/bottom offsets in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Update legacy-value fixtures for `O`, `OH`, and `NH3+` to current
  deterministic coordinates.
- Speed up
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  by memoizing the expensive render-and-measure result so the suite computes
  it once per test session instead of once per test function.
- Draw perpendicular cross-lines at all bond endpoints in diagnostic SVG
  overlay.  New `_draw_bond_perpendicular_markers()` helper in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py)
  draws short perpendicular lines at both ends of every checked bond line:
  magenta `#ff00ff` for endpoints used for gap measurement, dark blue
  `#00008b` for other endpoints.  Include Haworth base ring bonds and
  double bond secondary lines in the perpendicular marker set so both
  primary and secondary bond lines get endpoint markers.  Double bond
  secondary lines now included in connector candidates so labels like
  CH2OH find the correct nearest bond endpoint (secondary going toward
  the label) instead of the primary going the wrong direction.  Markers
  are drawn as a background layer before per-label overlays.  Remove
  per-metric orange perpendicular line (now redundant).  Change hull contact
  point marker from circle to ellipse (rx=1.5, ry=0.8).  Legend updated with
  perpendicular line swatches for "Connector endpoint" and "Other endpoint".
  Tests in
  [tests/test_measurelib_diagnostic_svg.py](tests/test_measurelib_diagnostic_svg.py)
  cover perpendicular marker presence, backward compatibility, and hull
  contact ellipse.
- Render charge marks as circled symbols in OASA SVG output instead of
  appending +/- as inline text.  Store mark data in vertex `properties_` in
  [tools/render_beta_sheets.py](tools/render_beta_sheets.py), suppress charge
  text suffix in `vertex_label_text()` when marks are present, and generate
  `CircleOp`/`LineOp` for circled plus (blue) and minus (red) marks in
  `build_vertex_ops()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Update bond count expectations in
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  to account for the 6 new mark lines.
- Fix furanose beta MR OH / ML CH2OH text collision in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  When MR carries a simple hydroxyl and ML carries a chain-like tail
  (e.g. ALRRDM furanose beta), skip the oxygen clearance override entirely so
  the MR OH bond stays at the default 13.5 length instead of being pushed up
  to 18.49 where it collides with the CH2OH text.  Remove unused constant
  `FURANOSE_TOP_RIGHT_HYDROXYL_EXTRA_CLEARANCE_FACTOR` from
  [packages/oasa/oasa/haworth/renderer_config.py](packages/oasa/oasa/haworth/renderer_config.py).
- Rebalance furanose "up" two-carbon tail branch length factors in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  `ho_length_factor` changed from 0.72 to 0.90, `ch2_length_factor` from 1.08
  to 0.95 in `_furanose_two_carbon_tail_profile()`.  This reduces the HO vs
  CH2OH branch length ratio from ~2.5:1 to ~1.3:1.
- Use round linecaps for all Haworth bond lines in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  The hashed-bond carrier line in `_add_branch_connector_ops()` was the only
  remaining `cap="butt"` bond line; changed to `cap="round"` for visual
  consistency with all other bond connectors.  Hatch cross-strokes retain butt
  caps since they are decorative marks, not bond lines.  Add `CircleOp` rounding
  caps at back ring vertices (ML, TL, MR for pyranose) so the thin polygon ring
  edges also appear rounded where they meet instead of showing square corners.
  Make the hashed-bond carrier line fully transparent (`color="none"`) so only
  the hatch cross-strokes are visible.  Add `HASHED_BOND_WEDGE_RATIO` constant
  (4.6, up from hardcoded 2.8) to
  [packages/oasa/oasa/haworth/renderer_config.py](packages/oasa/oasa/haworth/renderer_config.py)
  to widen the hatch bond fan angle.
- Empirically calibrate glyph bounding-box vertical offset in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  `_label_box_coords()` `bottom_offset` changed from `0.035` to `0.008` based
  on rsvg/Pango pixel measurements (actual descent is 0.1 SVG units at 12pt,
  ratio 0.008).  Previous value overestimated descent, inflating glyph boxes
  and causing Haworth ring-edge overlap failures.  Add
  `_text_ink_bearing_correction()` helper that computes the left and right
  bearing gap between Cairo advance width and actual ink extent.
- Increase oxygen exclusion safety margin in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  `_oxygen_exclusion_radius()` safety factor raised from `0.05` to `0.09` to
  compensate for the tighter glyph box: ring edges now maintain visual
  clearance from the oxygen label despite the smaller bounding box.
- Improve glyph calibration tool
  [tools/calibrate_glyph_model.py](tools/calibrate_glyph_model.py).
  `_generate_subscript_svg()` now generates proper SVG `<tspan>` subscript
  structure matching the renderer's output (font-size scaling, dy offsets)
  instead of rendering plain text.  Fix pyflakes lint: remove unused imports
  (`math`, `pathlib`, `glyph_char_advance`, `glyph_text_width`), unused
  variable (`sub_dy`), and unnecessary f-string prefixes.
- Alignment measurement improvement: Haworth OH/HO alignment increased from
  ~52% to 100% (HO) and 94.7% (OH).  Overall alignment (excluding ring
  oxygens) improved from ~33.9% to 81.3%.  Bond-end gap values now land in
  the [1.3, 1.7] target range (avg 1.52) for both alpha and beta anomers.

- Add Cairo PDF parity measurement tool for comparing PDF and SVG renderer
  output.  New `tools/measure_cairo_pdf_parity.py` CLI supports two modes:
  parity mode (SVG+PDF pair comparison) and PDF-only mode (standalone PDF
  analysis).  New modules:
  [tools/measurelib/pdf_parse.py](tools/measurelib/pdf_parse.py) extracts
  lines, labels, ring primitives, and wedge bonds from Cairo-generated PDF
  files via `pdfplumber` with Y-coordinate flipping to SVG space;
  [tools/measurelib/parity.py](tools/measurelib/parity.py) performs
  nearest-neighbor matching of SVG and PDF primitives with configurable
  tolerance and computes a parity score;
  [tools/measurelib/pdf_analysis.py](tools/measurelib/pdf_analysis.py)
  runs the full structural analysis pipeline (Haworth detection, hatch
  detection, violations) on PDF-extracted primitives.  Tests in
  [tests/test_cairo_pdf_parity.py](tests/test_cairo_pdf_parity.py) cover
  PDF extraction, parity matching, file pairing, and standalone PDF
  analysis (19 tests).  Existing SVG measurement tool is unchanged.
- Fix antiparallel reverse-strand terminal text orientation in
  [tools/render_beta_sheets.py](tools/render_beta_sheets.py) so C->N chains
  read as `-OOC ... NH3+` (instead of `COO- ... H3N+`).  Add direction-aware
  terminal label text/position handling (`COO`/`H3N` for forward strands,
  `OOC`/`NH3` for reverse strands) and charge-mark side placement.  Add
  regression coverage in
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  to assert reverse-strand terminal labels and charge mark positions.
- Add double bond pair detection and exclusion to glyph-bond alignment
  measurement tool.  New `detect_double_bond_pairs()` in
  [tools/measurelib/hatch_detect.py](tools/measurelib/hatch_detect.py) finds
  parallel line pairs (C=O double bonds) and excludes the secondary offset line
  from measurement.  Uses linecap attribute to classify primary (round-cap) vs
  secondary (butt-cap) lines.  Add `DOUBLE_BOND_*` constants to
  [tools/measurelib/constants.py](tools/measurelib/constants.py).  Report now
  includes `decorative_double_bond_offset_count` and `double_bond_pairs`.
- Add multi-bond label support to glyph-bond alignment measurement tool.
  New `all_endpoints_near_glyph_primitives()` and
  `all_endpoints_near_text_path()` in
  [tools/measurelib/glyph_model.py](tools/measurelib/glyph_model.py) return all
  bond endpoints within search distance, grouped by approach side (left/right).
  Per-label measurement loop in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) now builds a
  `connectors` list with independent alignment metrics for each side.  A label
  is aligned only if all its connectors pass.  Backward-compatible top-level
  fields are preserved from the primary (nearest) connector.
- Update re-exports in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  for new double bond and multi-connector public names.
- Add tests for double bond detection and multi-connector labels in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py).
  Update expected bond counts in
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  to reflect double bond exclusion (42 detected, 6 excluded, 36 checked).
- Fix double-bond perpendicular distance measurement in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py).  Perpendicular
  distance was measured from the glyph optical center to the primary drawn line,
  but for C=O double bonds the two parallel lines are offset ~6 SVG units from
  the true bond axis.  The O glyph center sits on the bond axis (between the
  two lines), giving a spurious perp offset of ~3.  Fix: compute a midline by
  averaging primary and secondary line coordinates, then measure perpendicular
  distance to the midline.  O label perp values drop from 3.03 to 0.03.
  Update infinite-line overlay in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py)
  to draw the midline for double-bond primaries.
- Add gap-ratio filter to multi-connector label detection in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py).  Distant bonds
  from the far side of a label were incorrectly included as secondary connectors
  (e.g. O labels getting a spurious connector with gap=27 alongside the real
  C=O connector with gap=8).  Discard connectors whose gap exceeds
  `MULTI_CONNECTOR_GAP_RATIO_MAX` (3.0) times the minimum gap among all sides.
  Add constant to
  [tools/measurelib/constants.py](tools/measurelib/constants.py).

- Fix double-bond centering inconsistency in OASA generic renderer.
  `molecule_to_ops()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  was passing `point_for_atom=None`, so `_double_bond_side()` compared
  transformed bond coordinates against raw (untransformed) atom positions.
  Neighbor atoms appeared on the wrong side, producing offset double bonds
  where centered was correct.  Fix: pass a `point_for_atom` callback that
  applies the same `transform_xy` used for bond coordinates.
- Add `center` attribute to OASA bond class in
  [packages/oasa/oasa/bond.py](packages/oasa/oasa/bond.py).  Parse
  `center="yes"` from CDML in
  [packages/oasa/oasa/cdml_bond_io.py](packages/oasa/oasa/cdml_bond_io.py).
  Honor the attribute in `build_bond_ops()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  when `edge.center` is set, skip geometric side detection and force centered
  double-bond rendering.

- Add N, O, R, and H-only atoms to the glyph-bond measurement tool.
  `is_measurement_label()` in
  [tools/measurelib/glyph_model.py](tools/measurelib/glyph_model.py) now uses
  first/last letter logic instead of substring search; measurable atoms are
  {C, O, S, N, R} plus H-only labels.  Add R to `GLYPH_STEM_CHAR_SET` in
  [tools/measurelib/constants.py](tools/measurelib/constants.py).  Replace
  element-priority alignment center selection in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) with first/last
  letter logic that picks the connecting character based on which side of the
  label the bond approaches.  Add bounding-box fallback in
  [tools/measurelib/lcf_optical.py](tools/measurelib/lcf_optical.py) to use
  character shape type for optical fitting: curved glyphs (C, O, S) get
  ellipse fitting, stem glyphs (N, H, R) get bounding-box center.  Update
  tests in
  [tests/test_measurelib_glyph_model.py](tests/test_measurelib_glyph_model.py)
  and
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  for new measurement label set and first/last letter alignment.

- Add CPK default colors for charge marks in
  [packages/bkchem-app/bkchem/marks.py](packages/bkchem-app/bkchem/marks.py): `plus`
  marks default to blue (`#0000FF`) and `minus` marks default to red
  (`#FF0000`) instead of inheriting the atom's line color.  Override the
  `line_color` property in each subclass with a CPK fallback; explicit color
  set via `set_color()` or `_line_color` still takes precedence.
- Add zoom scaling for all mark subclasses in
  [packages/bkchem-app/bkchem/marks.py](packages/bkchem-app/bkchem/marks.py).  Add
  `_scaled_size()` helper to the base `mark` class that multiplies `self.size`
  by `self.paper._scale`.  Update `draw()` in `radical`, `biradical`,
  `electronpair`, `plus`, `minus`, and `text_mark` to use `_scaled_size()`
  for canvas pixel dimensions so marks grow/shrink proportionally with zoom.
  The inset constant in `plus`/`minus` cross/dash lines also scales.  SVG
  export and CDML serialization remain unscaled (model coordinates).  Skip
  `pz_orbital` (mixes model coords with size differently).
- Fix bond drawing after zoom for shown atoms (N, O, R, H3N, COOH).  Bonds
  connected to labeled atoms drew as long diagonal lines after zoom because
  `molecule.redraw()` redraws bonds before atoms, and bonds call `atom.bbox()`
  which read stale pre-zoom canvas positions.  Fix by redrawing atoms first so
  their canvas items are at correct positions, then redrawing bonds, then
  lifting atoms above bonds to restore z-ordering.
- Fix double bond convergence toward labeled atoms (take 2). Secondary
  parallel lines of double/triple bonds were independently resolved against
  label targets, but each offset line approaches the label at a different
  angle, so Steps 1-3 of the constraint pipeline broke parallelism. Remove all
  `_resolve_endpoint_with_constraints` calls from secondary bond lines in
  `build_bond_ops()`. Secondary lines inherit correct clearance from the main
  bond's already-resolved endpoints via `find_parallel()`. Remove the
  now-unused `no_gap_constraints` variable. Cross-label overlap avoidance
  (`_avoid_cross_label_overlaps`) is retained for all lines.
- Rewrite [tools/render_beta_sheets.py](tools/render_beta_sheets.py) to produce
  bkchem-quality beta-sheet CDML and SVG fixtures.  Write CDML directly via
  `xml.dom.minidom` (not `oasa.cdml_writer`) to emit proper bkchem element
  types: `<atom>` for backbone C/N/O, `<query>` for R groups, and
  `<text><ftext>` with `<sub>` markup for terminals.  N-terminus H3N uses
  `<mark type="plus" draw_circle="yes"/>` (bkchem circled charge mark);
  C-terminus COO uses `<mark type="minus" draw_circle="yes"/>` (carboxylate).
  C=O bonds use `type="n2" center="yes" bond_width="6.0"`.  Geometry matches
  the hand-drawn reference template (0.700 cm bond length, 30-degree zigzag).
  Four residues per strand, 19 atoms and 18 bonds each, 38 atoms total per
  file (no cross-strand H-bonds).  SVG rendered via `render_out.render_to_svg()`
  with `show_hydrogens_on_hetero=False`; oasa charge display appends +/- via
  `vertex_label_text`.  Fixtures at
  [tests/fixtures/oasa_generic/](tests/fixtures/oasa_generic/), SVGs at
  `output_smoke/oasa_generic_renders/`.
- Fix gap retreat reference mismatch: change `_retreat_to_target_gap()` in
  `resolve_label_connector_endpoint_from_text_origin` to use
  `contract.endpoint_target` (per-character glyph model) instead of
  `contract.full_target` (full label bounding box). The measurement tool
  measures from the tight glyph body outline, which sits inside the bbox by
  0.5-1.3 px, causing measured gaps to overshoot by that inset. Using the
  tighter endpoint target aligns the retreat reference with the measurement
  reference. Legality retreat still uses `full_target` to prevent text overlap.
  Expand `_point_in_target_closed` tolerance in the chain2 label solver
  ([packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py))
  by `ATTACH_GAP_TARGET` so the endpoint validity check accommodates the
  intentional gap distance. Update chain2 resolver test to use matching
  `epsilon=1e-3` and `make_attach_constraints()` factory call.
- Fix Haworth renderer gap target mismatch: pass `target_gap=ATTACH_GAP_TARGET`
  (1.5 px) explicitly at all 6 `make_attach_constraints()` call sites in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  Previously the renderer used the font-relative fallback (`12.0 * 0.058 = 0.696 px`),
  which fell outside the measurement spec's 1.3-1.7 px window.
- Add `make_attach_constraints()` factory and `ATTACH_GAP_FONT_FRACTION` constant
  to [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Three-tier gap resolution: explicit `target_gap` > font-relative > absolute default.
  Delete Haworth-only `TARGET_GAP_FRACTION` constant and replace all inline
  `AttachConstraints()` calls across Haworth, cairo_out, svg_out, bond_render_ops,
  and bond_drawing with the shared factory. Phase 5 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Wire shared gap/perp constraints through `BondRenderContext` into
  `build_bond_ops()`. Add `attach_constraints` field to `BondRenderContext` and
  `attach_gap_target`/`attach_perp_tolerance` style keys to `molecule_to_ops()`.
  Update `cairo_out.py`, `svg_out.py`, `bond_render_ops.py`, and `bond_drawing.py`
  to construct and pass `AttachConstraints` with shared constants. Phase 4 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Fix zoom viewport drift caused by orphaned canvas items leaking during
  redraw.  Non-showing atoms (carbon) in
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py) called
  `get_xy_on_paper()` which created a `vertex_item`, then overwrote
  `self.vertex_item = self.item`, orphaning the first item.  These leaked
  items accumulated at stale `canvas.scale()` coordinates, inflating the
  content bounding box and causing cumulative drift (571 px after 6 zoom
  steps).  Fix computes coordinates directly via `real_to_canvas()`.
- Fix bond position drift during zoom by repositioning `vertex_item`
  coordinates to `model_coord * scale` at the top of `molecule.redraw()`
  in [packages/bkchem-app/bkchem/molecule.py](packages/bkchem-app/bkchem/molecule.py).
  Bonds redraw before atoms for z-ordering and read atom positions from
  `vertex_item`; without the reset they used stale canvas-scaled coords.
- Add `_center_viewport_on_canvas()` helper to
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py) and
  call it after `update_scrollregion()` in `scale_all()` to re-center the
  viewport on the zoom origin.  Refactor `zoom_to_content()` to use the
  new helper.
- Fix interactive zoom drift: remove redundant `canvas.scale('all', ox, oy,
  factor, factor)` from `scale_all()` in
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py).
  `redraw_all()` already redraws content from model coords at the new scale,
  but the background rectangle (`self.background`) is not in `self.stack` and
  was never reset by `redraw_all()`.  The `canvas.scale()` call scaled it
  around the viewport center while `redraw_all()` scales from the origin,
  causing the background and content to diverge.  Fix explicitly resets the
  background via `create_background()` + `scale(background, 0, 0, scale,
  scale)` after `redraw_all()`.
- Fix Tk canvas inset bug in `_center_viewport_on_canvas()` fraction formula
  in [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py).
  Tk's `xview moveto` internally subtracts the canvas inset
  (`borderwidth + highlightthickness`) from the computed origin.  The
  fraction formula must include a `+inset` correction so that `canvasx()`
  lands on the target point after scrolling.  Without this fix, each zoom
  step introduced a systematic ~3 px centering error (matching the default
  inset of 3), causing cumulative viewport drift across zoom operations.
- Upgrade zoom test assertions in
  [tests/test_bkchem_gui_zoom.py](tests/test_bkchem_gui_zoom.py):
  convert idempotency and drift warnings to hard assertions (5% scale
  tolerance, 50 px bbox/viewport drift tolerance), add per-zoom-step
  snapshots with canvas item counts.
- Add `test_zoom_model_coords_stable` and `test_zoom_roundtrip_symmetry` to
  [tests/test_bkchem_gui_zoom.py](tests/test_bkchem_gui_zoom.py).
  Model-coords test verifies `atom.x`/`atom.y` are unchanged after zoom_in
  x50, zoom_out x100, and zoom reset.  Roundtrip-symmetry test zooms from
  1000% to ~250% (8 steps) and back, checking model-space viewport drift
  stays under 3.0 px.
- Add [docs/TKINTER_WINDOW_DEBUGGING.md](docs/TKINTER_WINDOW_DEBUGGING.md)
  documenting Tk Canvas zoom debugging techniques, the orphaned
  `vertex_item` root cause, and the `redraw()` ordering pitfall.

## 2026-02-14
- Replace "first child that changes endpoint" behavior in composite target branch
  of `_correct_endpoint_for_alignment()` with scoring-based candidate selection
  that minimizes perpendicular error to the desired centerline and tiebreaks by
  distance from original endpoint. Phase 3 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add Phase 3 composite target alignment tests in
  [tests/test_render_geometry.py](tests/test_render_geometry.py).
- Add "Zoom to Content" button and View menu entry that resets zoom, computes
  bounding box of drawn content only (excluding page background), scales to fit
  with 10% margin capped at 400%, and centers the viewport on the molecules.
  New `_content_bbox()` helper and `zoom_to_content()` method in
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py); button
  and menu wiring in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py).
- Shorten wavy bond wavelength from `ref * 1.2` to `ref * 0.5` (floor 2.0) in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  for tighter, more visible wave oscillations.
- Add gap/perp gate harness
  [tools/gap_perp_gate.py](tools/gap_perp_gate.py) that runs glyph-bond
  alignment measurement on fixture buckets (haworth, oasa_generic, bkchem)
  and emits compact JSON with per-label stats and failure reason counts.
  Phase 0 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add gate test
  [tests/test_gap_perp_gate.py](tests/test_gap_perp_gate.py) verifying gate
  report structure, reason tallies, empty-bucket handling, and haworth
  corpus file count.
- Add shared gap/perp spec constants (`ATTACH_GAP_TARGET`, `ATTACH_GAP_MIN`,
  `ATTACH_GAP_MAX`, `ATTACH_PERP_TOLERANCE`) to
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Add `alignment_tolerance` field to `AttachConstraints` (default 0.07) and
  replace hardcoded `max(line_width * 0.5, 0.25)` tolerance in
  `resolve_label_connector_endpoint_from_text_origin()` with
  `constraints.alignment_tolerance`. Phase 1 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add Phase 1 tests in
  [tests/test_render_geometry.py](tests/test_render_geometry.py) verifying
  shared constants, default/custom alignment tolerance, and no fallback to
  old hardcoded tolerance expression.

- Add wavy bond to GUI draw mode bond type submenu so users can select and
  draw wavy bonds from the toolbar (the rendering was already implemented but
  not wired into the GUI).
- Fix wavy bond rendering in GUI: scale amplitude/wavelength off `wedge_width`
  (not `line_width`) so waves are visible, use 4 sparse control points per
  wavelength with 1.5x amplitude overshoot so Tk's B-spline `smooth=1`
  produces genuinely smooth curves instead of visible straight-line segments,
  and widen stroke by 10% in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
- Fix hashed bond rendering in GUI: rewrite `_hashed_ops()` to compute each
  hash line perpendicular to the bond axis (unit-vector math) instead of
  connecting points on converging wedge edges, so all hash lines are parallel;
  linearly interpolate hash line length from `line_width` at the narrow end to
  `wedge_width` at the wide end; tighten spacing to `0.4 * wedge_width` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
- Rewrite
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md)
  into a focused execution plan for getting gap/perp into spec across shared
  OASA and BKChem rendering paths (not Haworth-only), with current baseline
  metrics, phased implementation, and hard acceptance gates.
- Update glyph-bond measurement pass/fail criteria in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) so labels are
  marked aligned only when `1.3 <= gap <= 1.7` and `perp <= 0.07`; all other
  cases are violations.
- Replace `err = perp` with a normalized combined metric in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py):
  `err = ((gap - 1.5)/0.2)^2 + (perp/0.07)^2`.
- Add explicit alignment gap/perp constants in
  [tools/measurelib/constants.py](tools/measurelib/constants.py).
- Update alignment tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to validate the new combined error formula and pass/fail rule.
- Add per-label `bond_len` reporting to
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) and include
  `bond_len=...` in diagnostic SVG annotation blocks in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py),
  alongside `gap/perp/err`.
- Propagate per-label bond lengths through JSON/report data points in
  [tools/measurelib/reporting.py](tools/measurelib/reporting.py).

## 2026-02-13
- Add `_resolve_endpoint_with_constraints()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  full 4-step constraint pipeline (boundary resolve, centerline correction,
  legality retreat, target-gap retreat) replacing `_clip_to_target()` at all
  6 bond-clipping call sites in `build_bond_ops()` (single, double side-path,
  double parallel-pair). Add clipping to triple bond offset lines which
  previously had none. Deprecate `_clip_to_target()`. Phase 2 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add Phase 2 tests in
  [tests/test_render_geometry.py](tests/test_render_geometry.py): none-target
  passthrough, backward compatibility with `_clip_to_target()`, alignment
  correction, gap retreat, legality retreat, and triple bond offset clipping.
- Tighten gap and perp renderer parameters to meet gap 1.3-1.7 and perp < 0.07
  spec. Change `TARGET_GAP_FRACTION` from 0.04 to 0.058 in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  (yields target_gap=0.70 at font_size=12). Tighten renderer alignment tolerance
  from `max(line_width * 0.5, 0.25)` to 0.07 in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Add post-gap re-alignment pass after gap retreat to catch perpendicular drift.
  Result: OH gap=1.37, HO gap=1.30, CH2OH gap=1.70 (all in spec). Perp values
  unchanged (structural limitation of composite target geometry).
- Add median to `length_stats()` in
  [tools/measurelib/util.py](tools/measurelib/util.py). Per-label alignment
  summary now shows avg/stddev/median for both bond_end_gap and perp_offset.
- Tighten perpendicular alignment tolerance from ~1.0 to 0.07 in
  [tools/measurelib/constants.py](tools/measurelib/constants.py) and simplify
  formula in [tools/measurelib/analysis.py](tools/measurelib/analysis.py).
  Rename alignment columns to `bond_end_gap` and `perp_offset` for clarity.
- Switch per-label `gap_distance_stats` to use signed distance (negative when
  bond endpoint penetrates glyph body) in
  [tools/measurelib/reporting.py](tools/measurelib/reporting.py).
- Add distance annotations (gap, perp, err) to diagnostic SVGs near each bond
  endpoint in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py).
- Create standalone
  [tools/alignment_summary.py](tools/alignment_summary.py) script that reads
  existing JSON report and prints per-label alignment summary without re-running
  the full analysis.
- Replace duplicate inline console code in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  `main()` with `print_summary()` call.
- Add `_avoid_cross_label_overlaps()` to
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (Phase 4 of OASA-Wide Glyph-Bond Awareness plan). Retreats bond endpoints
  away from non-own-vertex label targets using capsule intersection tests and
  `retreat_endpoint_until_legal()`. Integrated into `build_bond_ops()` for
  single, double (asymmetric and symmetric), and triple bond paths. Includes
  minimum bond length guard (`max(half_width * 4.0, 1.0)`) to prevent bonds
  from collapsing when surrounded by labels. Note: Haworth renderer uses its
  own pipeline and is not yet affected by this change.
- Add 6 unit tests for `_avoid_cross_label_overlaps` in
  [tests/test_render_geometry.py](tests/test_render_geometry.py): cross-target
  exclusion of own vertices, near-end retreat, near-start retreat,
  no-intersection passthrough, and minimum-length guard.
- Re-baseline plan metrics in
  [OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md):
  record post-connector-fix measurements (362/362 alignment, 0 misses), update
  acceptance criteria to current baseline, relabel Phases 1-3 from DONE to
  IMPLEMENTED, add per-atom optical centering feasibility note.
- Update [refactor_progress.md](refactor_progress.md) with re-baselined gate
  status and connector selection fix diagnosis.
- Include hashed bond carrier lines as connector candidates in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py). Carrier lines
  for hatched (behind-the-plane) bonds are intentionally drawn thin with
  perpendicular hatch strokes; the width filter was excluding them, causing
  labels like CH2OH to match distant unrelated bonds instead of the actual
  hatched bond.
- Add unit tests for `_retreat_to_target_gap`, `_correct_endpoint_for_alignment`,
  and `_perpendicular_distance_to_line` in new
  [tests/test_render_geometry.py](tests/test_render_geometry.py).
- Move
  [OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md)
  to `docs/active_plans/` and add NOT STARTED labels to Changes 6, 7, 8.
- Add consumer adoption note to OASA-Wide Glyph-Bond Awareness plan clarifying
  that `target_gap` and `alignment_center` are consumed by Haworth first; other
  consumers adopt when their rendering paths are ready.
- Extract `TARGET_GAP_FRACTION` constant in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  replacing 4 occurrences of `font_size * 0.04`.
- Run full acceptance metrics and record gate results in
  `output_smoke/acceptance_gate_results_2026-02-13.txt`.
- Port `letter-center-finder` algorithms directly into
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  as `_lcf_*` prefixed functions (SVG parsing, glyph isolation rendering,
  contour extraction, convex hull, ellipse fitting), removing the external
  sibling-repo dependency on `/Users/vosslab/nsh/letter-center-finder/`.
- Extend optical glyph centering to all alphanumeric characters, not just O/C.
  Change `_lcf_extract_chars_from_string` guard from `char in ('O', 'C')` to
  `char.isalnum()`.
- Delete fallback centering functions `_alignment_primitive_center`,
  `_first_carbon_primitive_center`, and `_first_primitive_center_for_char` from
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py).
  Optical centering failures now propagate visibly instead of silently falling
  back to inaccurate heuristics.
- Remove `--alignment-center-mode` CLI argument and hardcode optical mode in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py).
- Add `numpy`, `opencv-python`, and `scipy` to
  [pip_extras.txt](pip_extras.txt) as optional dependencies for glyph optical
  center fitting.
- Use Cairo font-metric label box width in `_label_box_coords()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (Phase 1 of OASA-Wide Glyph-Bond Awareness plan). Replace hardcoded
  `font_size * 0.75 * char_count` with `sum(_text_char_advances(...))`,
  making the full label box consistent with the sub-label attach box that
  already used Cairo metrics.
- Add `target_gap` and `alignment_center` fields to `AttachConstraints` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (Phase 2 and Phase 3 of OASA-Wide Glyph-Bond Awareness plan). Phase 2 adds
  `_retreat_to_target_gap()` for uniform whitespace between connector endpoint
  and glyph body. Phase 3 adds `_correct_endpoint_for_alignment()` to re-aim
  endpoints through the attach atom optical center, reducing bond/glyph overlaps
  from 219 to 211.
