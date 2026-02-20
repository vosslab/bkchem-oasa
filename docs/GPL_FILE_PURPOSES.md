# GPL File Purposes and Inventory

This document records the purpose of files from the GPL/LGPL coverage scan
(`tools/assess_gpl_coverage.py`, cutoff `2025-01-01`). As of 2026-02-20 there
are zero pure GPLv2 files remaining.

## Pure GPLv2 Files (0)

All former pure GPLv2 files have been removed or received enough new LGPLv3
code to become mixed. `id_manager.py` crossed the threshold after adding
reverse-index logic and docstrings (26% GPLv2, 74% LGPLv3).

### Removed or reclassified pure GPLv2 files

These files were eliminated or inlined to reduce the GPLv2 footprint:

- `bkchem_exceptions.py`: replaced with standard `ValueError` in 3 call sites.
- `groups_table.py`: inlined as `GROUPS_TABLE` constant in `group_lib.py`.
- `keysymdef.py`: converted to `bkchem_data/keysymdef.yaml` with cached loader.
- `plugins/plugin.py`: removed with the entire legacy plugin system.
- `tuning.py`: inlined into `ftext_lib.py` and `special_parents.py`.
- `id_manager.py`: now mixed (26% GPLv2) after adding reverse index and
  docstrings.

## Mixed Files (GPLv2 + LGPLv3)

### BKChem Frontend Core

Purpose: BKChem GUI app lifecycle, UI interaction modes, rendering orchestration,
CDML handling, undo/redo, preferences, and frontend chemistry object layers.

- [packages/bkchem-app/bkchem/CDML_versions.py](packages/bkchem-app/bkchem/CDML_versions.py)
- [packages/bkchem-app/bkchem/arrow_lib.py](packages/bkchem-app/bkchem/arrow_lib.py)
- [packages/bkchem-app/bkchem/atom_lib.py](packages/bkchem-app/bkchem/atom_lib.py)
- [packages/bkchem-app/bkchem/bkchem_app.py](packages/bkchem-app/bkchem/bkchem_app.py)
- [packages/bkchem-app/bkchem/bkchem_config.py](packages/bkchem-app/bkchem/bkchem_config.py)
- [packages/bkchem-app/bkchem/bkchem_utils.py](packages/bkchem-app/bkchem/bkchem_utils.py)
- [packages/bkchem-app/bkchem/bond_lib.py](packages/bkchem-app/bkchem/bond_lib.py)
- [packages/bkchem-app/bkchem/checks.py](packages/bkchem-app/bkchem/checks.py)
- [packages/bkchem-app/bkchem/classes.py](packages/bkchem-app/bkchem/classes.py)
- [packages/bkchem-app/bkchem/context_menu.py](packages/bkchem-app/bkchem/context_menu.py)
- [packages/bkchem-app/bkchem/data.py](packages/bkchem-app/bkchem/data.py)
- [packages/bkchem-app/bkchem/debug.py](packages/bkchem-app/bkchem/debug.py)
- [packages/bkchem-app/bkchem/dialogs.py](packages/bkchem-app/bkchem/dialogs.py)
- [packages/bkchem-app/bkchem/dom_extensions.py](packages/bkchem-app/bkchem/dom_extensions.py)
- [packages/bkchem-app/bkchem/edit_pool.py](packages/bkchem-app/bkchem/edit_pool.py)
- [packages/bkchem-app/bkchem/export.py](packages/bkchem-app/bkchem/export.py)
- [packages/bkchem-app/bkchem/external_data.py](packages/bkchem-app/bkchem/external_data.py)
- [packages/bkchem-app/bkchem/fragment_lib.py](packages/bkchem-app/bkchem/fragment_lib.py)
- [packages/bkchem-app/bkchem/ftext_lib.py](packages/bkchem-app/bkchem/ftext_lib.py)
- [packages/bkchem-app/bkchem/graphics.py](packages/bkchem-app/bkchem/graphics.py)
- [packages/bkchem-app/bkchem/group_lib.py](packages/bkchem-app/bkchem/group_lib.py)
- [packages/bkchem-app/bkchem/helper_graphics.py](packages/bkchem-app/bkchem/helper_graphics.py)
- [packages/bkchem-app/bkchem/id_manager.py](packages/bkchem-app/bkchem/id_manager.py)
- [packages/bkchem-app/bkchem/import_checker.py](packages/bkchem-app/bkchem/import_checker.py)
- [packages/bkchem-app/bkchem/interactors.py](packages/bkchem-app/bkchem/interactors.py)
- [packages/bkchem-app/bkchem/logger.py](packages/bkchem-app/bkchem/logger.py)
- [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py)
- [packages/bkchem-app/bkchem/marks.py](packages/bkchem-app/bkchem/marks.py)
- [packages/bkchem-app/bkchem/messages.py](packages/bkchem-app/bkchem/messages.py)
- [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py)
- [packages/bkchem-app/bkchem/molecule_lib.py](packages/bkchem-app/bkchem/molecule_lib.py)
- [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
- [packages/bkchem-app/bkchem/os_support.py](packages/bkchem-app/bkchem/os_support.py)
- [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py)
- [packages/bkchem-app/bkchem/parents.py](packages/bkchem-app/bkchem/parents.py)
- [packages/bkchem-app/bkchem/pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py)
- [packages/bkchem-app/bkchem/pref_manager.py](packages/bkchem-app/bkchem/pref_manager.py)
- [packages/bkchem-app/bkchem/queryatom_lib.py](packages/bkchem-app/bkchem/queryatom_lib.py)
- [packages/bkchem-app/bkchem/reaction_lib.py](packages/bkchem-app/bkchem/reaction_lib.py)
- [packages/bkchem-app/bkchem/singleton_store.py](packages/bkchem-app/bkchem/singleton_store.py)
- [packages/bkchem-app/bkchem/special_parents.py](packages/bkchem-app/bkchem/special_parents.py)
- [packages/bkchem-app/bkchem/splash.py](packages/bkchem-app/bkchem/splash.py)
- [packages/bkchem-app/bkchem/temp_manager.py](packages/bkchem-app/bkchem/temp_manager.py)
- [packages/bkchem-app/bkchem/textatom_lib.py](packages/bkchem-app/bkchem/textatom_lib.py)
- [packages/bkchem-app/bkchem/undo.py](packages/bkchem-app/bkchem/undo.py)
- [packages/bkchem-app/bkchem/validator.py](packages/bkchem-app/bkchem/validator.py)
- [packages/bkchem-app/bkchem/widgets.py](packages/bkchem-app/bkchem/widgets.py)

### OASA Backend Core and IO

Purpose: OASA chemistry backend primitives, format parsing/serialization,
geometry, stereochemistry, conversion bridges, and shared data/config utilities.

- [packages/oasa/chemical_convert.py](packages/oasa/chemical_convert.py)
- [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py)
- [packages/oasa/oasa/atom_lib.py](packages/oasa/oasa/atom_lib.py)
- [packages/oasa/oasa/bond_lib.py](packages/oasa/oasa/bond_lib.py)
- [packages/oasa/oasa/cairo_out.py](packages/oasa/oasa/cairo_out.py)
- [packages/oasa/oasa/cdml.py](packages/oasa/oasa/cdml.py)
- [packages/oasa/oasa/chem_vertex.py](packages/oasa/oasa/chem_vertex.py)
- [packages/oasa/oasa/common.py](packages/oasa/oasa/common.py)
- [packages/oasa/oasa/converter_base.py](packages/oasa/oasa/converter_base.py)
- [packages/oasa/oasa/coords_generator.py](packages/oasa/oasa/coords_generator.py)
- [packages/oasa/oasa/coords_optimizer.py](packages/oasa/oasa/coords_optimizer.py)
- [packages/oasa/oasa/dom_extensions.py](packages/oasa/oasa/dom_extensions.py)
- [packages/oasa/oasa/geometry.py](packages/oasa/oasa/geometry.py)
- [packages/oasa/oasa/inchi_key.py](packages/oasa/oasa/inchi_key.py)
- [packages/oasa/oasa/inchi_lib.py](packages/oasa/oasa/inchi_lib.py)
- [packages/oasa/oasa/isotope_database.py](packages/oasa/oasa/isotope_database.py)
- [packages/oasa/oasa/known_groups.py](packages/oasa/oasa/known_groups.py)
- [packages/oasa/oasa/linear_formula.py](packages/oasa/oasa/linear_formula.py)
- [packages/oasa/oasa/molecule_lib.py](packages/oasa/oasa/molecule_lib.py)
- [packages/oasa/oasa/molfile_lib.py](packages/oasa/oasa/molfile_lib.py)
- [packages/oasa/oasa/oasa_config.py](packages/oasa/oasa/oasa_config.py)
- [packages/oasa/oasa/oasa_exceptions.py](packages/oasa/oasa/oasa_exceptions.py)
- [packages/oasa/oasa/oasa_utils.py](packages/oasa/oasa/oasa_utils.py)
- [packages/oasa/oasa/periodic_table.py](packages/oasa/oasa/periodic_table.py)
- [packages/oasa/oasa/plugin_lib.py](packages/oasa/oasa/plugin_lib.py)
- [packages/oasa/oasa/pybel_bridge.py](packages/oasa/oasa/pybel_bridge.py)
- [packages/oasa/oasa/query_atom.py](packages/oasa/oasa/query_atom.py)
- [packages/oasa/oasa/reaction_lib.py](packages/oasa/oasa/reaction_lib.py)
- [packages/oasa/oasa/smiles_lib.py](packages/oasa/oasa/smiles_lib.py)
- [packages/oasa/oasa/stereochemistry_lib.py](packages/oasa/oasa/stereochemistry_lib.py)
- [packages/oasa/oasa/subsearch_data.py](packages/oasa/oasa/subsearch_data.py)
- [packages/oasa/oasa/svg_out.py](packages/oasa/oasa/svg_out.py)
- [packages/oasa/oasa/transform3d_lib.py](packages/oasa/oasa/transform3d_lib.py)
- [packages/oasa/oasa/transform_lib.py](packages/oasa/oasa/transform_lib.py)

### OASA Graph Subsystem

Purpose: graph primitives and algorithms that underpin molecule topology,
connectivity, traversal, and directed/undirected edge behavior.

- [packages/oasa/oasa/graph/__init__.py](packages/oasa/oasa/graph/__init__.py)
- [packages/oasa/oasa/graph/basic.py](packages/oasa/oasa/graph/basic.py)
- [packages/oasa/oasa/graph/diedge_lib.py](packages/oasa/oasa/graph/diedge_lib.py)
- [packages/oasa/oasa/graph/digraph_lib.py](packages/oasa/oasa/graph/digraph_lib.py)
- [packages/oasa/oasa/graph/edge_lib.py](packages/oasa/oasa/graph/edge_lib.py)
- [packages/oasa/oasa/graph/graph_lib.py](packages/oasa/oasa/graph/graph_lib.py)
- [packages/oasa/oasa/graph/vertex_lib.py](packages/oasa/oasa/graph/vertex_lib.py)
