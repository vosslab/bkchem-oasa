# GUI module usage audit

## Scope
- Files audited: 47 modules listed in the request under packages/bkchem-app/bkchem.
- Goal: identify each module purpose and whether it is in active GUI use.

## Method
- Read GUI entrypoints: bkchem_app.py, main.py, and dynamic mode loader modes/mode_loader.py.
- Built static import evidence by parsing Python AST imports across packages/bkchem-app.
- Marked modules as ACTIVE when imported by GUI runtime modules, including mode modules loaded dynamically.
- Marked modules as NOT ACTIVE when no importers were found in package code or tests.

## Results

| File | Purpose | Evidence of use | GUI status |
| --- | --- | --- | --- |
| `CDML_versions.py` | Support for backward compatible CDML reading. | `packages/bkchem-app/bkchem/paper_lib/paper_cdml.py`; `packages/bkchem-app/bkchem/temp_manager.py`; `packages/bkchem-app/tests/test_cdml_versioning.py` | ACTIVE |
| `arrow_lib.py` | The arrow class resides here. | `packages/bkchem-app/bkchem/modes/rotate_mode.py`; `packages/bkchem-app/bkchem/paper_lib/paper_factories.py`; `packages/bkchem-app/bkchem/paper_lib/paper_properties.py` | ACTIVE |
| `atom_lib.py` | Home for atom class. | `packages/bkchem-app/bkchem/chem_compat.py`; `packages/bkchem-app/bkchem/context_menu.py`; `packages/bkchem-app/bkchem/external_data.py`; +9 more importer(s) | ACTIVE |
| `bkchem_app.py` | Starter of the application. | Launcher entrypoint module executed directly to start BKChem GUI. | ACTIVE |
| `bkchem_config.py` | Global runtime configuration and version helpers. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/bkchem/debug.py`; `packages/bkchem-app/bkchem/edit_pool.py`; +10 more importer(s) | ACTIVE |
| `bkchem_utils.py` | Module containing miscelanous functions used in BKChem that don't. | `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/bond_drawing.py`; `packages/bkchem-app/bkchem/bond_lib.py`; +24 more importer(s) | ACTIVE |
| `bond_lib.py` | Home of the bond class. | `packages/bkchem-app/bkchem/chem_compat.py`; `packages/bkchem-app/bkchem/external_data.py`; `packages/bkchem-app/bkchem/modes/bondalign_mode.py`; +12 more importer(s) | ACTIVE |
| `checks.py` | Functions used for various checks and maintanence throughout BKChem. | `packages/bkchem-app/bkchem/paper.py` | ACTIVE |
| `classes.py` | Set of basic classes such as standard, plus, text etc. | `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/dialogs.py`; `packages/bkchem-app/bkchem/graphics.py`; +8 more importer(s) | ACTIVE |
| `context_menu.py` | Right-click context menu actions for edit and mark modes. | `packages/bkchem-app/bkchem/modes/edit_mode.py`; `packages/bkchem-app/bkchem/modes/mark_mode.py` | ACTIVE |
| `data.py` | This module contains most of the data that are not module specific. | `packages/bkchem-app/bkchem/CDML_versions.py`; `packages/bkchem-app/bkchem/atom_lib.py`; `packages/bkchem-app/bkchem/dialogs.py`; +9 more importer(s) | ACTIVE |
| `debug.py` | Small conditional debug logger gated by bkchem_config.debug. | No imports found via AST scan or text search for module usage. | NOT ACTIVE (likely legacy) |
| `dialogs.py` | Set of dialogs used by BKChem. | `packages/bkchem-app/addons/fragment_search.py`; `packages/bkchem-app/bkchem/interactors.py`; `packages/bkchem-app/bkchem/main.py`; +2 more importer(s) | ACTIVE |
| `dom_extensions.py` | Some extensions to DOM for more convenient work. | `packages/bkchem-app/bkchem/CDML_versions.py`; `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/atom_lib.py`; +20 more importer(s) | ACTIVE |
| `edit_pool.py` | The 'edit pool' widget resides here. | `packages/bkchem-app/bkchem/main.py` | ACTIVE |
| `export.py` | Support for exporters resides here. | `packages/bkchem-app/bkchem/main_lib/main_file_io.py` | ACTIVE |
| `external_data.py` | Provide external_data_manager class. | `packages/bkchem-app/bkchem/paper.py` | ACTIVE |
| `fragment_lib.py` | Fragment object model used by molecules and templates. | `packages/bkchem-app/bkchem/molecule_lib.py` | ACTIVE |
| `ftext_lib.py` | Extended methods for formating text items (for canvas). | `packages/bkchem-app/bkchem/classes.py`; `packages/bkchem-app/bkchem/parents.py`; `packages/bkchem-app/bkchem/special_parents.py` | ACTIVE |
| `graphics.py` | Set of basic vector graphics classes such as rect, oval etc. | `packages/bkchem-app/bkchem/paper_lib/paper_factories.py`; `packages/bkchem-app/bkchem/paper_lib/paper_properties.py` | ACTIVE |
| `group_lib.py` | Home for group - a vertex of a molecular graph. | `packages/bkchem-app/addons/text_to_group.py`; `packages/bkchem-app/bkchem/context_menu.py`; `packages/bkchem-app/bkchem/edit_pool.py`; +6 more importer(s) | ACTIVE |
| `helper_graphics.py` | Set of helper graphics items such as selection rects etc. | `packages/bkchem-app/bkchem/graphics.py`; `packages/bkchem-app/bkchem/modes/edit_mode.py`; `packages/bkchem-app/bkchem/paper.py` | ACTIVE |
| `id_manager.py` | ID allocation and lookup for CDML object identifiers. | `packages/bkchem-app/bkchem/main.py`; `packages/bkchem-app/bkchem/paper_lib/paper_cdml.py` | ACTIVE |
| `import_checker.py` | Runtime dependency preflight for BKChem launcher. | `packages/bkchem-app/bkchem/bkchem_app.py` | ACTIVE |
| `interactors.py` | Glue functions between application or paper and the dialogs. | `packages/bkchem-app/bkchem/actions/chemistry_actions.py`; `packages/bkchem-app/bkchem/actions/options_actions.py`; `packages/bkchem-app/bkchem/context_menu.py`; +6 more importer(s) | ACTIVE |
| `keysym_loader.py` | Cached loader for keysym definition data. | `packages/bkchem-app/bkchem/edit_pool.py`; `packages/bkchem-app/bkchem/widgets.py` | ACTIVE |
| `main.py` | Main application class. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/tests/bkchem_batch_examples.py`; `packages/bkchem-app/tests/bkchem_gui_smoke.py`; +6 more importer(s) | ACTIVE |
| `marks.py` | Set of marks such as charges, radicals etc. | `packages/bkchem-app/bkchem/atom_lib.py`; `packages/bkchem-app/bkchem/context_menu.py`; `packages/bkchem-app/bkchem/group_lib.py`; +5 more importer(s) | ACTIVE |
| `messages.py` | messages for use throughout the program. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/bkchem/main.py`; `packages/bkchem-app/bkchem/modes/modes_lib.py`; +2 more importer(s) | ACTIVE |
| `molecule_lib.py` | Home of the molecule class. | `packages/bkchem-app/bkchem/chem_compat.py`; `packages/bkchem-app/bkchem/external_data.py`; `packages/bkchem-app/bkchem/interactors.py`; +12 more importer(s) | ACTIVE |
| `oasa_bridge.py` | Bridge between BKChem objects and OASA or codec I O. | `packages/bkchem-app/bkchem/export.py`; `packages/bkchem-app/bkchem/format_loader.py`; `packages/bkchem-app/bkchem/main_lib/main_chemistry_io.py`; +3 more importer(s) | ACTIVE |
| `os_support.py` | OS and path helpers for runtime file and config locations. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/bkchem/dialogs.py`; `packages/bkchem-app/bkchem/external_data.py`; +17 more importer(s) | ACTIVE |
| `paper.py` | chem_paper - main drawing part for BKChem. | `packages/bkchem-app/bkchem/main_lib/main_tabs.py` | ACTIVE |
| `parents.py` | This file stores the oldest parents of used classes. | `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/bond_lib.py`; `packages/bkchem-app/bkchem/classes.py`; +8 more importer(s) | ACTIVE |
| `pixmaps.py` | Images for buttons all over BKChem. | `packages/bkchem-app/bkchem/main.py`; `packages/bkchem-app/bkchem/main_lib/main_modes.py` | ACTIVE |
| `pref_manager.py` | XML preference read and write manager. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/tests/bkchem_batch_examples.py`; `packages/bkchem-app/tests/bkchem_gui_smoke.py`; +6 more importer(s) | ACTIVE |
| `queryatom_lib.py` | The query_atom class. | `packages/bkchem-app/bkchem/chem_compat.py`; `packages/bkchem-app/bkchem/external_data.py`; `packages/bkchem-app/bkchem/molecule_lib.py` | ACTIVE |
| `reaction_lib.py` | Reaction container object tying arrows and molecules. | `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/paper_lib/paper_factories.py` | ACTIVE |
| `singleton_store.py` | The Store class which is a manager for application wide singletons resides here. | `packages/bkchem-app/addons/angle_between_bonds.py`; `packages/bkchem-app/addons/fragment_search.py`; `packages/bkchem-app/addons/text_to_group.py`; +71 more importer(s) | ACTIVE |
| `special_parents.py` | Chemistry-specific drawable parent mixins and base classes. | `packages/bkchem-app/bkchem/atom_lib.py`; `packages/bkchem-app/bkchem/group_lib.py`; `packages/bkchem-app/bkchem/modes/mark_mode.py`; +4 more importer(s) | ACTIVE |
| `splash.py` | the Splash class resides here. | `packages/bkchem-app/bkchem/bkchem_app.py` | ACTIVE |
| `temp_manager.py` | Template manager resides here. | `packages/bkchem-app/bkchem/main.py`; `packages/bkchem-app/tests/test_biomolecule_smiles_templates.py` | ACTIVE |
| `textatom_lib.py` | Home for the textatom - a vertex of a molecular graph. | `packages/bkchem-app/addons/text_to_group.py`; `packages/bkchem-app/bkchem/external_data.py`; `packages/bkchem-app/bkchem/modes/edit_mode.py`; +4 more importer(s) | ACTIVE |
| `undo.py` | This module implements undo_manager and state_record classes. | `packages/bkchem-app/bkchem/paper.py` | ACTIVE |
| `widgets.py` | Set of specialized widgets, such as color-selection-buttons etc. | `packages/bkchem-app/bkchem/dialogs.py`; `packages/bkchem-app/bkchem/interactors.py` | ACTIVE |


## UNADDRESSED


| File | Purpose | Evidence of use | GUI status |
| --- | --- | --- | --- |

| `bkchem_app.py` | Starter of the application. | Launcher entrypoint module executed directly to start BKChem GUI. | ACTIVE |
| `bkchem_config.py` | Global runtime configuration and version helpers. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/bkchem/debug.py`; `packages/bkchem-app/bkchem/edit_pool.py`; +10 more importer(s) | ACTIVE |
| `bkchem_utils.py` | Module containing miscelanous functions used in BKChem that don't. | `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/bond_drawing.py`; `packages/bkchem-app/bkchem/bond_lib.py`; +24 more importer(s) | ACTIVE |

| `checks.py` | Functions used for various checks and maintanence throughout BKChem. | `packages/bkchem-app/bkchem/paper.py` | ACTIVE |

| `context_menu.py` | Right-click context menu actions for edit and mark modes. | `packages/bkchem-app/bkchem/modes/edit_mode.py`; `packages/bkchem-app/bkchem/modes/mark_mode.py` | ACTIVE |
| `data.py` | This module contains most of the data that are not module specific. | `packages/bkchem-app/bkchem/CDML_versions.py`; `packages/bkchem-app/bkchem/atom_lib.py`; `packages/bkchem-app/bkchem/dialogs.py`; +9 more importer(s) | ACTIVE |


| `dialogs.py` | Set of dialogs used by BKChem. | `packages/bkchem-app/addons/fragment_search.py`; `packages/bkchem-app/bkchem/interactors.py`; `packages/bkchem-app/bkchem/main.py`; +2 more importer(s) | ACTIVE |

| `edit_pool.py` | The 'edit pool' widget resides here. | `packages/bkchem-app/bkchem/main.py` | ACTIVE |
| `export.py` | Support for exporters resides here. | `packages/bkchem-app/bkchem/main_lib/main_file_io.py` | ACTIVE |
| `external_data.py` | Provide external_data_manager class. | `packages/bkchem-app/bkchem/paper.py` | ACTIVE |

| `helper_graphics.py` | Set of helper graphics items such as selection rects etc. | `packages/bkchem-app/bkchem/graphics.py`; `packages/bkchem-app/bkchem/modes/edit_mode.py`; `packages/bkchem-app/bkchem/paper.py` | ACTIVE |
| `id_manager.py` | ID allocation and lookup for CDML object identifiers. | `packages/bkchem-app/bkchem/main.py`; `packages/bkchem-app/bkchem/paper_lib/paper_cdml.py` | ACTIVE |

| `import_checker.py` | Runtime dependency preflight for BKChem launcher. | `packages/bkchem-app/bkchem/bkchem_app.py` | ACTIVE |
| `interactors.py` | Glue functions between application or paper and the dialogs. | `packages/bkchem-app/bkchem/actions/chemistry_actions.py`; `packages/bkchem-app/bkchem/actions/options_actions.py`; `packages/bkchem-app/bkchem/context_menu.py`; +6 more importer(s) | ACTIVE |
| `keysym_loader.py` | Cached loader for keysym definition data. | `packages/bkchem-app/bkchem/edit_pool.py`; `packages/bkchem-app/bkchem/widgets.py` | ACTIVE |
| `main.py` | Main application class. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/tests/bkchem_batch_examples.py`; `packages/bkchem-app/tests/bkchem_gui_smoke.py`; +6 more importer(s) | ACTIVE |

| `messages.py` | messages for use throughout the program. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/bkchem/main.py`; `packages/bkchem-app/bkchem/modes/modes_lib.py`; +2 more importer(s) | ACTIVE |

| `oasa_bridge.py` | Bridge between BKChem objects and OASA or codec I O. | `packages/bkchem-app/bkchem/export.py`; `packages/bkchem-app/bkchem/format_loader.py`; `packages/bkchem-app/bkchem/main_lib/main_chemistry_io.py`; +3 more importer(s) | ACTIVE |
| `os_support.py` | OS and path helpers for runtime file and config locations. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/bkchem/dialogs.py`; `packages/bkchem-app/bkchem/external_data.py`; +17 more importer(s) | ACTIVE |
| `paper.py` | chem_paper - main drawing part for BKChem. | `packages/bkchem-app/bkchem/main_lib/main_tabs.py` | ACTIVE |
| `parents.py` | This file stores the oldest parents of used classes. | `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/bond_lib.py`; `packages/bkchem-app/bkchem/classes.py`; +8 more importer(s) | ACTIVE |
| `pixmaps.py` | Images for buttons all over BKChem. | `packages/bkchem-app/bkchem/main.py`; `packages/bkchem-app/bkchem/main_lib/main_modes.py` | ACTIVE |
| `pref_manager.py` | XML preference read and write manager. | `packages/bkchem-app/bkchem/bkchem_app.py`; `packages/bkchem-app/tests/bkchem_batch_examples.py`; `packages/bkchem-app/tests/bkchem_gui_smoke.py`; +6 more importer(s) | ACTIVE |

| `splash.py` | the Splash class resides here. | `packages/bkchem-app/bkchem/bkchem_app.py` | ACTIVE |
| `temp_manager.py` | Template manager resides here. | `packages/bkchem-app/bkchem/main.py`; `packages/bkchem-app/tests/test_biomolecule_smiles_templates.py` | ACTIVE |

| `undo.py` | This module implements undo_manager and state_record classes. | `packages/bkchem-app/bkchem/paper.py` | ACTIVE |
| `widgets.py` | Set of specialized widgets, such as color-selection-buttons etc. | `packages/bkchem-app/bkchem/dialogs.py`; `packages/bkchem-app/bkchem/interactors.py` | ACTIVE |

## MOVE TO OASA

| File | Purpose | Reason |
| --- | --- | --- |
| `CDML_versions.py` | Support for backward compatible CDML reading. | CDML import/export is done at OASA level not GUI |
| `validator.py` | Provide validator class that checks chemistry. | chemistry is OASA, unless we need more quick realtime |


## REMOVE

| File | Purpose | Reason |
| --- | --- | --- |
| `logger.py` | Application logger abstraction for normal, batch, and status modes. | GUI should not have batch mode |
| `bkchem_batch_examples.py` | N/A | GUI should not have batch mode |
| `debug.py` | Small conditional debug logger gated by bkchem_config.debug. | No imports found via AST scan or text search for module usage. | NOT ACTIVE (likely legacy) |

## OBJECTS, make sure they stick to CDML CONTRACT RULES
| File | Purpose | Evidence of use | GUI status |
| --- | --- | --- | --- |
| `arrow_lib.py` | The arrow class resides here. | `packages/bkchem-app/bkchem/modes/rotate_mode.py`; `packages/bkchem-app/bkchem/paper_lib/paper_factories.py`; `packages/bkchem-app/bkchem/paper_lib/paper_properties.py` | ACTIVE |
| `atom_lib.py` | Home for atom class. | `packages/bkchem-app/bkchem/chem_compat.py`; `packages/bkchem-app/bkchem/context_menu.py`; `packages/bkchem-app/bkchem/external_data.py`; +9 more importer(s) | ACTIVE |
| `bond_lib.py` | Home of the bond class. | `packages/bkchem-app/bkchem/chem_compat.py`; `packages/bkchem-app/bkchem/external_data.py`; `packages/bkchem-app/bkchem/modes/bondalign_mode.py`; +12 more importer(s) | ACTIVE |
| `classes.py` | Set of basic classes such as standard, plus, text etc. | `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/dialogs.py`; `packages/bkchem-app/bkchem/graphics.py`; +8 more importer(s) | ACTIVE |
| `dom_extensions.py` | Some extensions to DOM for more convenient work. | `packages/bkchem-app/bkchem/CDML_versions.py`; `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/atom_lib.py`; +20 more importer(s) | ACTIVE |
| `fragment_lib.py` | Fragment object model used by molecules and templates. | `packages/bkchem-app/bkchem/molecule_lib.py` | ACTIVE |
| `ftext_lib.py` | Extended methods for formating text items (for canvas). | `packages/bkchem-app/bkchem/classes.py`; `packages/bkchem-app/bkchem/parents.py`; `packages/bkchem-app/bkchem/special_parents.py` | ACTIVE |
| `graphics.py` | Set of basic vector graphics classes such as rect, oval etc. | `packages/bkchem-app/bkchem/paper_lib/paper_factories.py`; `packages/bkchem-app/bkchem/paper_lib/paper_properties.py` | ACTIVE |
| `group_lib.py` | Home for group - a vertex of a molecular graph. | `packages/bkchem-app/addons/text_to_group.py`; `packages/bkchem-app/bkchem/context_menu.py`; `packages/bkchem-app/bkchem/edit_pool.py`; +6 more importer(s) | ACTIVE |
| `marks.py` | Set of marks such as charges, radicals etc. | `packages/bkchem-app/bkchem/atom_lib.py`; `packages/bkchem-app/bkchem/context_menu.py`; `packages/bkchem-app/bkchem/group_lib.py`; +5 more importer(s) | ACTIVE |
| `molecule_lib.py` | Home of the molecule class. | `packages/bkchem-app/bkchem/chem_compat.py`; `packages/bkchem-app/bkchem/external_data.py`; `packages/bkchem-app/bkchem/interactors.py`; +12 more importer(s) | ACTIVE |
| `queryatom_lib.py` | The query_atom class. | `packages/bkchem-app/bkchem/chem_compat.py`; `packages/bkchem-app/bkchem/external_data.py`; `packages/bkchem-app/bkchem/molecule_lib.py` | ACTIVE |
| `reaction_lib.py` | Reaction container object tying arrows and molecules. | `packages/bkchem-app/bkchem/arrow_lib.py`; `packages/bkchem-app/bkchem/paper_lib/paper_factories.py` | ACTIVE |
| `singleton_store.py` | The Store class which is a manager for application wide singletons resides here. | `packages/bkchem-app/addons/angle_between_bonds.py`; `packages/bkchem-app/addons/fragment_search.py`; `packages/bkchem-app/addons/text_to_group.py`; +71 more importer(s) | ACTIVE |
| `special_parents.py` | Chemistry-specific drawable parent mixins and base classes. | `packages/bkchem-app/bkchem/atom_lib.py`; `packages/bkchem-app/bkchem/group_lib.py`; `packages/bkchem-app/bkchem/modes/mark_mode.py`; +4 more importer(s) | ACTIVE |
| `textatom_lib.py` | Home for the textatom - a vertex of a molecular graph. | `packages/bkchem-app/addons/text_to_group.py`; `packages/bkchem-app/bkchem/external_data.py`; `packages/bkchem-app/bkchem/modes/edit_mode.py`; +4 more importer(s) | ACTIVE |



## Summary
- Active in GUI runtime: 46 of 47 modules.
- Not active: debug.py (no imports found).
- Practical takeaway: this list is almost entirely live GUI code; debug.py is the only clear cleanup candidate.
