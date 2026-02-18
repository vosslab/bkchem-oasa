# Absolute package import refactor

## Objective

Convert all bare local imports in `packages/bkchem/bkchem/` from `import X` and `from X import Y` to absolute package form (`from bkchem import X` and `from bkchem.X import Y`). This enables proper Python packaging and future macOS `.app` distribution without `sys.path` hacks.

## Design philosophy

- Mechanical transformation only: change import style, not behavior
- Each file's bare local imports become `from bkchem` absolute imports
- External packages (`oasa`, stdlib, pip) stay unchanged
- `from bkchem import X` for bare `import X` where X is a local module
- `from bkchem.X import Y` for `from X import Y` where X is a local module
- After conversion, remove `packages/bkchem/bkchem` from PYTHONPATH in launch script

## Scope

- ~45 `.py` files in `packages/bkchem/bkchem/`
- ~3 files in `packages/bkchem/bkchem/plugins/`
- ~10 files in `packages/bkchem/bkchem/actions/`
- ~245 import lines total

## Non-goals

- Do not refactor oasa package imports (separate package)
- Do not change any logic or behavior
- Do not rename modules or restructure directories
- Do not touch test files or tools/

## Local modules (files in packages/bkchem/bkchem/)

arrow, atom, bkchem_app, bkchem_exceptions, bond, bond_cdml, bond_display,
bond_drawing, bond_render_ops, bond_type_control, CDML_versions, checks,
classes, cli, config, context_menu, data, debug, dialogs, dom_extensions,
edit_pool, export, external_data, format_loader, fragment, ftext, graphics,
group, groups_table, helper_graphics, id_manager, import_checker, interactors,
keysymdef, logger, main, marks, menu_builder, messages, misc, modes, molecule,
oasa_bridge, os_support, paper, parents, peptide_utils, pixmaps, platform_menu,
plugin_support, pref_manager, queryatom, reaction, safe_xml, singleton_store,
special_parents, splash, temp_manager, template_catalog, textatom, tuning,
undo, validator, widgets, xml_serializer

## Conversion rules

1. `import config` becomes `from bkchem import config` (when config is a local module)
2. `from singleton_store import Store` becomes `from bkchem.singleton_store import Store`
3. `from parents import meta_enabled, drawable` becomes `from bkchem.parents import meta_enabled, drawable`
4. Do NOT convert: `import oasa`, `import os`, `import tkinter`, `import yaml`, etc.
5. For plugins/ subpackage: same as above, `from bkchem import X` and `from bkchem.X import Y`
6. For actions/ subpackage: same as above (if any exist)

## Phase 1 status (completed with wrong style)

The initial conversion used relative imports (`from . import X`, `from .X import Y`).
These need to be corrected to absolute package imports (`from bkchem import X`, `from bkchem.X import Y`).

## Phase 2: Fix relative to absolute (current)

Mechanical text replacement across all ~48 changed files:

| Pattern | Replacement |
| --- | --- |
| `from .. import X` | `from bkchem import X` |
| `from ..X import Y` | `from bkchem.X import Y` |
| `from . import X` | `from bkchem import X` |
| `from .X import Y` | `from bkchem.X import Y` |

Order matters: replace `..` patterns before `.` patterns.

## Verification gate

Per file:
```bash
source source_me.sh && python3 -m py_compile packages/bkchem/bkchem/<file>.py
```

Integration:
```bash
source source_me.sh && python3 -c "from bkchem import main"
source source_me.sh && python3 -m pytest packages/bkchem/tests/ -x -q
```

## Post-integration

- Remove `packages/bkchem/bkchem` from PYTHONPATH in `launch_bkchem_gui.sh`
- Update `docs/CHANGELOG.md`
