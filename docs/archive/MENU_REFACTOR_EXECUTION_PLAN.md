# Menu Refactor Execution Plan

## Objective

Replace the tuple-based `menu_template` in `main.py` with a YAML structure file
and a modular Python action registry, preserving all current menu behavior,
translations, plugin integration, and platform handling.

## Design Philosophy

- **Additive, then swap.** Build new system alongside old. Switch over per-menu.
  Delete old code only after the new path is validated.
- **Spread code across files.** Action registrations split into one file per menu
  group. Prefer many small files over one large file.
- **File ownership is law.** Each coder owns specific files. No two coders edit
  the same file at the same time.
- **Shared interface contract.** All coders follow the `MenuAction` dataclass and
  `ActionRegistry` API defined in this document. No deviations.
- **Tkinter/Pmw stays.** No toolkit migration. The platform adapter wraps Pmw
  only.

## Scope

**In scope:**
- Action registry package (`actions/`) with `MenuAction` dataclass
- Per-menu action registration modules (one file per menu group)
- YAML menu structure (`menus.yaml`)
- Menu builder that combines YAML + registry into Pmw menus
- Platform adapter preserving macOS `MainMenuBar` vs Linux `MenuBar`
- Plugin compatibility for existing import/export/script plugins
- Enablement logic (selection-based enable/disable)
- Translation key preservation (all `_()` keys unchanged)
- Unit tests for every new module
- Translation key validation test

**Out of scope (separate projects):**
- Moving format handlers to OASA (see [docs/TODO_CODE.md](docs/TODO_CODE.md))
- Renderer unification
- Tool framework replacing addons (see
  [docs/active_plans/MODULAR_MENU_ARCHITECTURE.md](docs/active_plans/MODULAR_MENU_ARCHITECTURE.md))
- Performance monitoring infrastructure
- Qt/Gtk/native/web backend abstraction
- Toolbar/mode button unification (defer to follow-up)

## Current State

- `main.py` lines 175-295: `menu_template` list of tuples defining 10 menus
- `main.py` lines 312-344: `init_menu()` iterates tuples, builds Pmw menus, adds
  plugin entries via `plug_man`
- `main.py` lines 396-480: `init_plugins_menu()` populates Import/Export from
  `format_loader` and legacy `plugins` dict
- `main.py` lines 1551-1570: `_get_menu_component()` and
  `update_menu_after_selection_change()` for enable/disable
- 10 menus: File, Edit, Insert, Align, Object, View, Chemistry, Options, Help,
  Plugins
- Platform: macOS uses `Pmw.MainMenuBar`, others use `Pmw.MenuBar`
- Translations: 11 locales (cs, de, es, fr, it, ja, lv, pl, ru, tr, zh_TW),
  all labels wrapped in `_()`
- Plugins: format handlers via `format_loader.py` + legacy `plugins` dict, script
  plugins via `plugin_support.py` `plug_man` (XML manifests + `exec()`)
- Handler methods: 23 methods in `main.py` referenced by `menu_template`
  (save_CDML, read_smiles, etc.)
- Interactor functions: 9 functions in `interactors.py` called from menu lambdas

## Architecture

```
bkchem_data/menus.yaml       actions/            menu_builder.py
(menu hierarchy)        +    (per-menu           (combines YAML
                              registrations)  --> + registry)
                                                     |
                                                     v
                                               platform_menu.py
                                               (Pmw adapter)
                                                     |
                                                     v
                                               Pmw.MainMenuBar (macOS)
                                               Pmw.MenuBar (Linux/Windows)
```

## Shared Interface Contract

All coders must follow this interface exactly. Coder 1 implements it; Coders 2-5
consume it.

```python
# actions/__init__.py - THE CONTRACT

import builtins
_ = builtins.__dict__.get('_', lambda m: m)

@dataclass
class MenuAction:
    id: str                # Unique: "file.save", "edit.undo"
    label_key: str         # English key: "Save" (translated via _() at access)
    help_key: str          # English key: "Save the file"
    accelerator: str       # Shortcut: "(C-x C-s)" or None
    handler: object        # Callable or None (for menu/cascade entries)
    enabled_when: object   # Callable, string, or None

    @property
    def label(self) -> str:
        return _(self.label_key)

    @property
    def help_text(self) -> str:
        return _(self.help_key)

class ActionRegistry:
    def register(self, action: MenuAction) -> None: ...
    def get(self, action_id: str) -> MenuAction: ...
    def __contains__(self, action_id: str) -> bool: ...
    def all_actions(self) -> dict: ...
    def is_enabled(self, action_id: str, context) -> bool: ...
```

Each per-menu module exports one function:

```python
# Pattern for actions/file_actions.py, actions/edit_actions.py, etc.
def register_file_actions(registry: ActionRegistry, app) -> None:
    """Register all File menu actions."""
    registry.register(MenuAction(
        id='file.new',
        label_key='New',
        help_key='Create a new file in a new tab',
        accelerator='(C-x C-n)',
        handler=app.add_new_paper,
        enabled_when=None,
    ))
    # ... more actions
```

## File Ownership Map (8 Coders)

All paths relative to `packages/bkchem-app/`.

| New File | Coder | Purpose |
| --- | --- | --- |
| `bkchem/actions/__init__.py` | Coder 1 | MenuAction dataclass, ActionRegistry, register_all_actions() |
| `tests/test_action_registry.py` | Coder 1 | Registry core tests |
| `bkchem/actions/file_actions.py` | Coder 2 | File menu: New, Save, Load, Close, Exit, etc. |
| `tests/test_file_actions.py` | Coder 2 | File action registration tests |
| `bkchem/actions/edit_actions.py` | Coder 3 | Edit menu: Undo, Redo, Cut, Copy, Paste, Select All |
| `bkchem/actions/object_actions.py` | Coder 3 | Object menu: Scale, Front/Back, Mirror, Configure |
| `tests/test_edit_object_actions.py` | Coder 3 | Edit + Object tests |
| `bkchem/actions/chemistry_actions.py` | Coder 4 | Chemistry menu: SMILES, InChI, Peptide, fragments |
| `bkchem/actions/view_actions.py` | Coder 4 | View menu: Zoom In/Out, Fit, Content |
| `tests/test_chemistry_view_actions.py` | Coder 4 | Chemistry + View tests |
| `bkchem/actions/align_actions.py` | Coder 5 | Align menu: Top, Bottom, Left, Right, Center |
| `bkchem/actions/insert_actions.py` | Coder 5 | Insert menu: Biomolecule template |
| `bkchem/actions/options_actions.py` | Coder 5 | Options menu: Standard, Language, Logging, Prefs |
| `bkchem/actions/help_actions.py` | Coder 5 | Help menu: About |
| `bkchem/actions/plugins_actions.py` | Coder 5 | Plugins menu (top-level only) |
| `tests/test_remaining_actions.py` | Coder 5 | Align+Insert+Options+Help+Plugins tests |
| `bkchem_data/menus.yaml` | Coder 6 | YAML menu hierarchy |
| `tests/test_menu_yaml.py` | Coder 6 | YAML validation tests |
| `bkchem/platform_menu.py` | Coder 7 | Pmw platform adapter |
| `tests/test_platform_menu.py` | Coder 7 | Platform adapter tests |
| `bkchem/menu_builder.py` | Coder 8 | YAML + registry combiner |
| `tests/test_menu_builder.py` | Coder 8 | Builder integration tests |

## Action ID Naming Convention

All coders must use this naming scheme:

- Top-level menus: `menu.file`, `menu.edit`, `menu.insert`, `menu.align`,
  `menu.object`, `menu.view`, `menu.chemistry`, `menu.options`, `menu.help`,
  `menu.plugins`
- Commands: `<menu>.<verb_or_noun>` e.g. `file.new`, `file.save`,
  `file.save_as`, `edit.undo`, `chemistry.read_smiles`, `align.top`
- Cascades: `cascade.recent_files`, `cascade.export`, `cascade.import`

## Phase Plan

### Phase 0: Shared Prerequisites (lead, before parallel work)

**Owner:** Lead
**Goal:** Extract the data all coders need.

**Deliverables:**
1. `docs/active_plans/MENU_TEMPLATE_EXTRACT.md` - table of every
   `menu_template` tuple: menu name, type, label key, accelerator, help key,
   handler expression, state_var expression, proposed action ID.
2. Spot check translation keys against 3 locale `.po` files.

**Done check:**
- Extract table covers every tuple in `menu_template` lines 175-295

---

### Phase 1: All 8 Coders in Parallel

#### Coder 1: Action Registry Core

**Files:** `bkchem/actions/__init__.py`, `tests/test_action_registry.py`
**Depends on:** Phase 0 extract table (for action count validation)

**Deliverables:**

1. `bkchem/actions/__init__.py`:
   - `MenuAction` dataclass (exact contract above)
   - `ActionRegistry` class with `register()`, `get()`, `__contains__()`,
     `all_actions()`, `is_enabled(action_id, context)`
   - `register_all_actions(app)` that calls each per-menu registration function:
     ```python
     def register_all_actions(app) -> ActionRegistry:
         registry = ActionRegistry()
         file_actions.register_file_actions(registry, app)
         edit_actions.register_edit_actions(registry, app)
         # ... all per-menu modules
         return registry
     ```
   - Import guards: if a per-menu module is not yet written, skip gracefully
     (enables parallel development)

2. `tests/test_action_registry.py`:
   - `test_register_and_get` - round trip
   - `test_duplicate_id_raises` - ValueError on duplicate
   - `test_contains` - `__contains__` works
   - `test_is_enabled_none` - always enabled when `enabled_when` is None
   - `test_is_enabled_callable` - calls predicate
   - `test_is_enabled_string` - looks up attribute on context

**Done checks:**
- `source source_me.sh && python3 -m pyflakes bkchem/actions/__init__.py` clean
- `source source_me.sh && python3 -m pytest tests/test_action_registry.py -v`
  all pass

---

#### Coder 2: File Menu Actions

**Files:** `bkchem/actions/file_actions.py`, `tests/test_file_actions.py`
**Depends on:** Interface contract (above). No import dependency on Coder 1 at
write time; tested after merge.

**Goal:** Register all File menu entries including top-level menu and cascades.

**Actions to register (from menu_template):**
- `menu.file` (menu entry)
- `file.new` - handler: `app.add_new_paper`
- `file.save` - handler: `app.save_CDML`
- `file.save_as` - handler: `app.save_as_CDML`
- `file.save_as_template` - handler: `app.save_as_template`
- `file.load` - handler: `app.load_CDML`
- `file.load_same_tab` - handler: `lambda: app.load_CDML(replace=1)`
- `cascade.recent_files`
- `cascade.export`
- `cascade.import`
- `file.properties` - handler: `app.change_properties`
- `file.close_tab` - handler: `app.close_current_paper`
- `file.exit` - handler: `app._quit`

**Test file:** Verify count, verify IDs, verify label_keys match exact English
strings from `menu_template` (e.g. `'Save As..'` not `'Save As...'`).

**Done checks:**
- pyflakes clean
- pytest passes

---

#### Coder 3: Edit + Object Menu Actions

**Files:** `bkchem/actions/edit_actions.py`,
`bkchem/actions/object_actions.py`, `tests/test_edit_object_actions.py`

**Edit menu actions:**
- `menu.edit`
- `edit.undo` - handler: `lambda: app.paper.undo()`,
  enabled_when: `lambda: app.paper.um.can_undo()`
- `edit.redo` - handler: `lambda: app.paper.redo()`,
  enabled_when: `lambda: app.paper.um.can_redo()`
- `edit.cut` - enabled_when: `'selected'`
- `edit.copy` - enabled_when: `'selected'`
- `edit.paste` - enabled_when: `lambda: app._clipboard`
- `edit.selected_to_svg` - enabled_when: `'selected'`
- `edit.select_all`

**Object menu actions:**
- `menu.object`
- `object.scale` - enabled_when: `'selected'`
- `object.bring_to_front` - enabled_when: `'selected'`
- `object.send_back` - enabled_when: `'selected'`
- `object.swap_on_stack` - enabled_when: `'two_or_more_selected'`
- `object.vertical_mirror` - enabled_when: `'selected_mols'`
- `object.horizontal_mirror` - enabled_when: `'selected_mols'`
- `object.configure` - enabled_when: `'selected'`

**Done checks:**
- pyflakes clean on both files
- pytest passes

---

#### Coder 4: Chemistry + View Menu Actions

**Files:** `bkchem/actions/chemistry_actions.py`,
`bkchem/actions/view_actions.py`, `tests/test_chemistry_view_actions.py`

**Chemistry menu actions:**
- `menu.chemistry`
- `chemistry.info` - enabled_when: `'selected_mols'`
- `chemistry.check` - enabled_when: `'selected_mols'`
- `chemistry.expand_groups` - enabled_when: `'groups_selected'`
- `chemistry.oxidation_number` - enabled_when: `'selected_atoms'`
- `chemistry.read_smiles` - handler: `app.read_smiles`
- `chemistry.read_inchi` - handler: `app.read_inchi`
- `chemistry.read_peptide` - handler: `app.read_peptide_sequence`
- `chemistry.gen_smiles` - enabled_when: `'selected_mols'`
- `chemistry.gen_inchi` - enabled_when: lambda (has_preference AND selected_mols)
- `chemistry.set_name` - enabled_when: `'selected_mols'`
- `chemistry.set_id` - enabled_when: `'one_mol_selected'`
- `chemistry.create_fragment` - enabled_when: `'one_mol_selected'`
- `chemistry.view_fragments`
- `chemistry.convert_to_linear` - enabled_when: `'selected_mols'`

**View menu actions:**
- `menu.view`
- `view.zoom_in`, `view.zoom_out`, `view.zoom_reset`, `view.zoom_to_fit`,
  `view.zoom_to_content`

**Done checks:**
- pyflakes clean on both files
- pytest passes

---

#### Coder 5: Align + Insert + Options + Help + Plugins Actions

**Files:** `bkchem/actions/align_actions.py`,
`bkchem/actions/insert_actions.py`, `bkchem/actions/options_actions.py`,
`bkchem/actions/help_actions.py`, `bkchem/actions/plugins_actions.py`,
`tests/test_remaining_actions.py`

**Align menu (6 actions):** top/bottom/left/right/center_h/center_v, all
enabled_when: `'two_or_more_selected'`

**Insert menu (1 action):** `insert.biomolecule_template`

**Options menu (5 actions):** standard, language, logging, inchi_path, preferences

**Help menu (1 action):** `help.about`

**Plugins menu (0 command actions, just `menu.plugins` top-level entry)**

**Done checks:**
- pyflakes clean on all 5 files
- pytest passes

---

#### Coder 6: YAML Menu Structure

**Files:** `bkchem_data/menus.yaml`, `tests/test_menu_yaml.py`
**Depends on:** Phase 0 extract table and action ID naming convention

**Goal:** Transcribe the menu hierarchy into YAML. Action IDs must match the
naming convention. Order must match current `menu_template` exactly.

**Deliverables:**

1. `packages/bkchem-app/bkchem_data/menus.yaml`:
   ```yaml
   menus:
     file:
       label_key: "File"
       help_key: "Open, save, export, and import files"
       side: "left"
       items:
         - action: file.new
         - action: file.save
         # ... exact order from menu_template
         - cascade: recent_files
         - separator: true
         - cascade: export
         - cascade: import
         # ...
   cascades:
     recent_files:
       label_key: "Recent files"
       help_key: "The most recently used files"
     export:
       label_key: "Export"
       help_key: "Export the current file"
     import:
       label_key: "Import"
       help_key: "Import a non-native file format"
   ```

2. `tests/test_menu_yaml.py`:
   - `test_yaml_parses`
   - `test_all_ten_menus_present`
   - `test_item_types_valid` - every item is action, separator, or cascade
   - `test_action_ids_well_formed` - match `word.word` or `word.word_word`
   - `test_cascade_refs_have_definitions`
   - `test_no_duplicate_action_ids_in_yaml`

**Done checks:**
- pytest passes
- Menu count and item count match `menu_template`

---

#### Coder 7: Platform Adapter

**Files:** `bkchem/platform_menu.py`, `tests/test_platform_menu.py`

**Goal:** Wrap Pmw menubar creation and manipulation, isolating platform
differences (macOS vs Linux).

**Deliverables:**

1. `bkchem/platform_menu.py`:
   - `PlatformMenuAdapter` class
   - `__init__(parent_window, balloon)` - detects `sys.platform == 'darwin'`
   - `create_menubar()` - returns `Pmw.MainMenuBar` on macOS (with
     `self.configure(menu=...)` call), `Pmw.MenuBar` in frame on others
     (matches `main.py` lines 164-173 exactly)
   - `add_menu(name, help_text, side='left')` - wraps `addmenu()`
   - `add_command(menu_name, label, accelerator, help_text, command)` -
     wraps `addmenuitem(menu, 'command', ...)`
   - `add_separator(menu_name)` - wraps `addmenuitem(menu, 'separator')`
   - `add_cascade(menu_name, label, help_text)` - wraps `addcascademenu()`
   - `get_menu_component(name)` - returns the Tk menu widget for
     `entryconfigure` calls (matches `_get_menu_component()` in main.py)
   - `set_item_state(menu_name, label, enabled)` - wraps `entryconfigure()`
   - `add_command_to_cascade(cascade_name, label, help_text, command)` -
     for plugin slot injection

2. `tests/test_platform_menu.py`:
   - Mock Pmw classes (MockMainMenuBar, MockMenuBar)
   - `test_macos_uses_main_menu_bar` - verify MainMenuBar on darwin
   - `test_linux_uses_menu_bar` - verify MenuBar on linux
   - `test_add_menu_calls_addmenu`
   - `test_add_command_calls_addmenuitem`
   - `test_add_separator`
   - `test_add_cascade`

**Done checks:**
- pyflakes clean
- pytest passes

---

#### Coder 8: Menu Builder

**Files:** `bkchem/menu_builder.py`, `tests/test_menu_builder.py`
**Depends on:** Interfaces from Coders 1, 6, 7 (can stub them initially)

**Goal:** Read YAML, look up actions in registry, call platform adapter to
construct menus. Handle plugin slot injection. Handle state updates.

**Deliverables:**

1. `bkchem/menu_builder.py`:
   - `MenuBuilder` class
   - `__init__(yaml_path, action_registry, platform_adapter)`
   - `build_menus()` - reads YAML, for each menu: calls adapter.add_menu(),
     then iterates items calling add_command/add_separator/add_cascade
   - `update_menu_states(app)` - iterates actions with `enabled_when`,
     evaluates predicate, calls `adapter.set_item_state()`.
     Supports three `enabled_when` types:
     - `None` -> always enabled
     - callable -> call it, convert bool to state
     - string -> `getattr(app.paper, string)`, convert to state
   - `get_plugin_slots()` - returns dict mapping slot names
     (`'importers'`, `'exporters'`, `'scripts'`) to cascade names for
     plugin injection
   - `add_to_plugin_slot(slot_name, label, help_text, command)` - add
     entry to a plugin slot cascade

2. `tests/test_menu_builder.py`:
   - Uses mock registry, mock YAML data, mock adapter
   - `test_build_creates_all_menus` - adapter.add_menu called 10 times
   - `test_build_creates_commands` - adapter.add_command called for each action
   - `test_separators_placed`
   - `test_cascades_created`
   - `test_update_states_calls_set_item_state`
   - `test_update_states_handles_string_predicate`
   - `test_plugin_slots_returned`
   - `test_add_to_plugin_slot`

**Done checks:**
- pyflakes clean
- pytest passes

---

### Phase 2: Integration (sequential, after all 8 coders complete)

**Owner:** Lead
**Files modified:** `bkchem/main.py`
**Depends on:** All 8 coders complete and passing

**Deliverables:**

1. Modify `init_menu()`:
   - Import `actions`, `menu_builder`, `platform_menu`
   - Create `PlatformMenuAdapter(self, self.menu_balloon)`
   - Call `actions.register_all_actions(self)` to get registry
   - Create `MenuBuilder(yaml_path, registry, adapter)`
   - Call `builder.build_menus()`
   - Wire plugin integration:
     - Format entries from `format_loader` into Import/Export slots via
       `builder.add_to_plugin_slot()`
     - Legacy plugin entries from `self.plugins` dict
     - Script plugins from `plug_man` into Plugins slot
   - Comment out old `menu_template` for rollback reference
   - Store `self.menu_builder = builder`

2. Modify `update_menu_after_selection_change()`:
   - Replace `for temp in self.menu_template:` with
     `self.menu_builder.update_menu_states(self)`

3. Modify `init_plugins_menu()`:
   - Use builder plugin slot API instead of direct `self.menu.addmenuitem()`

**Done checks:**
- pyflakes clean on main.py
- Manual GUI test: all 10 menus functional
- Manual GUI test: Import/Export shows format entries
- Manual GUI test: enable/disable works on selection change
- Manual GUI test: Chemistry > Read SMILES works

---

### Phase 3: Cleanup (after Phase 2 validated)

**Owner:** Lead

1. Delete commented-out `menu_template`
2. Delete old `init_menu()` loop code
3. Delete `_get_menu_component()` if unreferenced
4. pyflakes full pass
5. Update [docs/CHANGELOG.md](docs/CHANGELOG.md)
6. Update [refactor_progress.md](refactor_progress.md)
7. Archive planning docs to `docs/archive/`

**Done checks:**
- No references to `menu_template` in codebase
- pyflakes clean
- GUI smoke test passes

## Dependency Graph

```
Phase 0 (extract table)
    |
    +---> Coder 1 (registry core)  ----\
    |                                    \
    +---> Coder 2 (file actions)   ------\
    |                                     \
    +---> Coder 3 (edit+object)    -------\
    |                                      \
    +---> Coder 4 (chem+view)      ------->  Phase 2    -->  Phase 3
    |                                      /  (wire         (cleanup)
    +---> Coder 5 (align+opts+etc) -------/   main.py)
    |                                    /
    +---> Coder 6 (YAML)          ------/
    |                                  /
    +---> Coder 7 (platform)      ----/
    |                                /
    +---> Coder 8 (builder)       --/
```

All 8 coders run fully in parallel. Coders 2-5 follow the interface contract
from this document and do not import from Coder 1 at development time. After
merge, `actions/__init__.py` imports from all per-menu modules.

## Risk Register

| Risk | Impact | Trigger | Mitigation |
| --- | --- | --- | --- |
| Translation keys change | Breaks 11 locales | Wrong label_key | Extract table is source of truth |
| Action ID mismatch | YAML refs break | Coder 6 uses different IDs than 2-5 | Naming convention in this doc |
| macOS menu breaks | GUI unusable | Platform adapter wrong | Adapter mirrors main.py exactly |
| Plugin injection fails | No Import/Export | Slot wiring wrong | Phase 2 tests explicitly |
| State update regression | UI lag | New code path slower | Compare before/after Phase 2 |
| Merge conflicts | Delays | Two coders edit same file | File ownership map prevents this |

## Migration and Compatibility

- **Additive rollout:** `menu_template` not deleted until Phase 3.
- **Translation keys:** Exact same English keys. No `.po` changes needed.
- **Plugin API:** `format_loader` and `plug_man` APIs unchanged. Builder
  exposes plugin slots.
- **Legacy deletion:** Old code deleted only after Phase 2 manual validation.

## Open Questions

1. **Resolved:** `menus.yaml` lives in `bkchem_data/` (declarative data).
2. **Resolved:** `MenuAction.handler` preserves exactly what exists today
   (lambdas and method refs as-is).
3. **Confirm:** Are there script plugins that inject into menus other than
   "Plugins"? The `fragment_search` addon uses `<menu>File</menu>` in its XML.
   Builder needs label-to-ID compatibility for script plugin injection.
