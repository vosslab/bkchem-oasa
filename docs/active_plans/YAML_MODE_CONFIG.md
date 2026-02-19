# YAML mode config: extract toolbar config from modes.py

## Context

The mode/submode system in BKChem encodes all toolbar configuration as Python
data structures inside 18 class `__init__` methods across 2,276 lines in
`modes.py`. This mixes static UI config (names, icons, submode lists, defaults)
with behavioral logic (mouse handlers, key bindings, transforms).

Extracting the config to YAML:
1. Creates an **icon manifest** - single source of truth for every icon reference,
   critical for the upcoming SVG-to-PNG icon migration (87 SVG sources, 96 icons)
2. Makes the config **portable** - YAML is toolkit-agnostic, supporting future
   migration from tkinter to PySide or Tauri
3. **Eliminates hardcoded class definitions** - YAML keys define what mode classes
   exist; Python only provides behavioral methods for modes that need them
4. Forces us to **generalize** what was previously hardcoded
5. Enables **ribbon-style UI refinements** - group labels, tooltips, button sizing,
   and grid layouts are data-driven from YAML, not hardcoded in rendering logic

## Current state (Step 0 already done)

- `.lower()` normalization in `pixmaps.py` - done
- `name_recode_map` emptied - done (`wavy.gif` rename eliminated last entry)
- Mode button border highlight in `main.py` - done

## Files to create/modify

| File | Change |
| --- | --- |
| `bkchem_data/modes.yaml` | NEW - all 14 mode/submode configs |
| `bkchem/modes.py` | Class factory + behavioral methods only |
| `bkchem/main.py` | Use `icon_map` for submode icon lookup; `toolbar_order` from YAML |
| `bkchem/pixmaps.py` | Remove dead `name_recode_map` dict entirely |
| `docs/CHANGELOG.md` | Document changes |

All paths relative to `packages/bkchem-app/`.

---

## Architecture: YAML-driven class generation

### Core idea

The YAML file is the **class registry**. Every mode key in the YAML becomes a
Python class. Python code only exists for modes that need custom behavioral
methods (mouse handlers, key bindings, transforms).

### How it works

1. YAML defines all 14 modes with their config (name, parent, submodes, icons)
2. A **mode factory** reads the YAML and generates a class for each key
3. For modes that need custom behavior, a **behavior registry** maps YAML keys
   to Python classes that provide the methods
4. The factory merges: `YAML config + parent class + behavior mixin = final class`

### Three categories of modes

| Category | Count | YAML provides | Python provides |
| --- | --- | --- | --- |
| Config-only | 1 | everything | nothing (class fully generated) |
| Behavioral | 9 | config (name, submodes, icons) | mouse/key handlers |
| Complex dynamic | 4 | metadata (name, icon) | submodes + handlers + catalog logic |

**Config-only** (fully generated from YAML, no Python class needed):
- `user_template_mode` - zero custom methods, just sets `template_manager`

**Behavioral** (YAML config + Python handlers):
- `draw_mode`, `arrow_mode`, `plus_mode`, `text_mode`, `atom_mode`,
  `rotate_mode`, `vector_mode`, `bracket_mode`, `edit_mode`

**Complex dynamic** (YAML metadata + Python builds submodes at runtime):
- `template_mode`, `biomolecule_template_mode`, `mark_mode`,
  `bond_align_mode`, `misc_mode`

---

## Step 1: Create `bkchem_data/modes.yaml`

Full YAML with all 14 modes (11 static + 3 dynamic).

```yaml
# modes.yaml - toolbar mode/submode configuration
# YAML keys define mode classes. Python provides behavioral methods where needed.

toolbar_order:
  - edit
  - draw
  - template
  - biotemplate
  - usertemplate
  - atom
  - mark
  - arrow
  - plus
  - text
  - bracket
  - rotate
  - bondalign
  - vector
  - misc

modes:
  draw:
    name: draw
    parent: edit_mode
    icon: draw
    submodes:
      - group_label: Angle Step
        options:
          - {key: '30', tooltip: 30 degree snap}
          - {key: '18', tooltip: 18 degree snap}
          - {key: '6', tooltip: 6 degree snap}
          - {key: '1', tooltip: 1 degree snap}
        default: 0
      - group_label: Bond Order
        options:
          - {key: single, size: large}
          - {key: double, size: large}
          - {key: triple, size: large}
        default: 0
      - group_label: Bond Type
        options:
          - {key: normal, size: large}
          - {key: wedge, size: large}
          - {key: hashed, size: large}
          - {key: adder}
          - {key: bbold, name: bold}
          - {key: dash}
          - {key: dotted}
          - {key: wavy}
        default: 0
      - group_label: Length
        options:
          - {key: fixed, name: fixed length, tooltip: snap to fixed bond length}
          - {key: freestyle, tooltip: drag to any length}
        default: 0
      - group_label: Double Bond Style
        options:
          - {key: nosimpledouble, name: normal double bonds for wedge/hashed}
          - {key: simpledouble, name: simple double bonds for wedge/hashed}
        default: 1

  rotate:
    name: rotate
    parent: edit_mode
    icon: rotate
    submodes:
      - group_label: Dimension
        options:
          - {key: '2D', icon: '2d', size: large}
          - {key: '3D', icon: '3d', size: large}
        default: 0
      - group_label: 3D Style
        options:
          - {key: normal3d, name: normal 3D rotation}
          - {key: fixsomething, name: fix selected bond in 3D, icon: none}
        default: 0

  arrow:
    name: arrow
    parent: edit_mode
    icon: arrow
    submodes:
      - group_label: Angle Step
        options:
          - {key: '30', tooltip: 30 degree snap}
          - {key: '18', tooltip: 18 degree snap}
          - {key: '6', tooltip: 6 degree snap}
          - {key: '1', tooltip: 1 degree snap}
        default: 0
      - group_label: Length
        options:
          - {key: fixed, name: fixed length}
          - {key: freestyle}
        default: 0
      - group_label: Shape
        options:
          - {key: anormal, name: normal, size: large}
          - {key: spline, size: large}
        default: 0
      - group_label: Arrow Type
        options:
          - {key: normal, size: large}
          - {key: electron, name: electron transfer, size: large}
          - {key: retro, name: retrosynthetic, size: large}
          - {key: equilibrium, size: large}
          - {key: equilibrium2, name: equilibrium simple, size: large}
        default: 0

  edit:
    name: edit
    parent: basic_mode
    icon: edit
    submodes: []

  plus:
    name: plus
    parent: edit_mode
    icon: rplus
    submodes: []

  text:
    name: text
    parent: edit_mode
    icon: text
    submodes: []

  atom:
    name: atom
    parent: edit_mode
    icon: atom
    submodes: []

  bondalign:
    name: transformation mode
    parent: edit_mode
    icon: bondalign
    submodes:
      - group_label: Transform
        options:
          - {key: tohoriz, name: horizontal align, size: large, tooltip: align bond horizontally}
          - {key: tovert, name: vertical align, size: large, tooltip: align bond vertically}
          - {key: invertthrough, name: invert through a point, size: large}
          - {key: mirrorthrough, name: mirror through a line, size: large}
          - {key: freerotation, name: free rotation around bond, size: large}
        default: 0

  vector:
    name: vector graphics
    parent: edit_mode
    icon: vector
    submodes:
      - group_label: Shape
        options:
          - {key: rectangle, size: large}
          - {key: square, size: large}
          - {key: oval, size: large}
          - {key: circle, size: large}
          - {key: polygon, size: large}
          - {key: polyline, size: large}
        default: 0

  mark:
    name: mark
    parent: edit_mode
    icon: mark
    submodes:
      - group_label: Mark Type
        options:
          - {key: radical, size: large}
          - {key: biradical, size: large}
          - {key: electronpair, name: electron pair, size: large}
          - {key: dottedelectronpair, name: dotted electron pair}
          - {key: plusincircle, name: plus, size: large}
          - {key: minusincircle, name: minus, size: large}
          - {key: pzorbital, name: pz orbital, size: large}
        default: 0
      - group_label: Action
        options:
          - {key: add, tooltip: add mark to atom}
          - {key: remove, tooltip: remove mark from atom}
        default: 0

  bracket:
    name: Brackets
    parent: edit_mode
    icon: bracket
    submodes:
      - group_label: Bracket Style
        options:
          - {key: rectangularbracket, name: Rectangular, size: large}
          - {key: roundbracket, name: Round, size: large}
        default: 0

  misc:
    name: Miscellaneous
    parent: edit_mode
    icon: misc
    submodes:
      - group_label: Tool
        options:
          - {key: numbering, name: Numbering, size: large}
          - {key: wavy, name: Wavy line, size: large}
        default: 0

  # --- Dynamic modes: submodes loaded at runtime ---

  template:
    name: template
    parent: edit_mode
    icon: template
    dynamic: true
    template_source: system
    submodes:
      - group_label: Template
        layout: row

  biotemplate:
    name: biomolecule templates
    parent: edit_mode
    icon: biotemplate
    dynamic: true
    template_source: biomolecule
    use_categories: true
    submodes:
      - group_label: Category
        layout: row
      - group_label: Templates
        layout: grid
        columns: 4

  usertemplate:
    name: users templates
    parent: edit_mode
    icon: usertemplate
    dynamic: true
    template_source: user
    submodes:
      - group_label: Template
        layout: row
```

Schema notes:

Core fields:
- `key` = primary identifier; used in Python logic and as default for `name`
  and `icon` when those are omitted
- `name` = display label override; if omitted, defaults to `key`. All `name`
  and `group_label` values are passed through `_()` for i18n/gettext at load
  time, so translators can localize them via `.po` files
- `icon` = icon filename stem override (no extension); if omitted, defaults to
  `key`. Omit entirely for text-only buttons (no icon at all) by setting
  `icon: none`
- `default` = index of initially selected option
- `dynamic: true` = submodes built at runtime, not from YAML
- `template_source` = which template manager to use (system, biomolecule, user)
- `use_categories: true` = build category buttons from directory structure
- `toolbar_order` = replaces hardcoded `modes_sort` list in `main.py`
- `parent` = Python parent class used by the factory when generating the class

Ribbon-inspired fields (all optional):
- `group_label` = label text displayed above or below the button row (separator
  line drawn automatically between labeled groups). Passed through `_()` for
  i18n like all display strings
- `tooltip` = rich tooltip text for individual buttons; if omitted falls back
  to `name` then `key`
- `size` = `large` or omitted (default small); controls icon size in the button.
  Use `large` for primary actions the user reaches for most often
- `layout` = `row` (default) or `grid`; `grid` renders buttons in a multi-row
  grid with `columns` controlling width; useful for template galleries
- `columns` = number of columns when `layout: grid` (default 4)

Default cascade: `key` -> `name` -> `icon`. When all three are the same
string, only `key` is needed. Example: `{key: single}` is equivalent to
`{key: single, name: single, icon: single}`. Override `name` when the display
label should differ (e.g., `{key: bbold, name: bold}`). Override `icon` when
the icon filename differs from the key.

### Internationalization (i18n)

All user-visible strings in the YAML (`name`, `group_label`, `tooltip`, mode
`name`) are passed through `_()` (gettext) at load time. This means:
- The YAML contains English source strings
- Translators add translations to `.po` files as usual
- The loader calls `_(cfg['name'])` etc. so the UI renders in the active locale
- `key` values are never translated (they are internal identifiers)
- Template names from the filesystem are also passed through `_()` so
  biomolecule template labels can be localized

Arrow mode: `available_types` and `available_type_names` (previously imported
from `arrow.py` at runtime) are now inlined in YAML since they are static
constants. The `arrow` module import stays for behavioral methods.

Verification:
```bash
source source_me.sh && python3 -c "
import yaml
with open('packages/bkchem-app/bkchem_data/modes.yaml') as f:
    cfg = yaml.safe_load(f)
print(f'toolbar_order: {len(cfg[\"toolbar_order\"])} modes')
print(f'mode definitions: {len(cfg[\"modes\"])} modes')
"
```

---

## Step 2: Mode factory and auto-config in `modes.py`

### Module-level loader

```python
import os
import yaml
from bkchem import os_support

_MODES_CONFIG = None  # loaded lazily on first use

def _load_modes_yaml() -> dict:
    data_dir = os_support._get_bkchem_data_dir()
    yaml_path = os.path.join(data_dir, 'modes.yaml')
    with open(yaml_path, 'r') as fh:
        return yaml.safe_load(fh)

def get_toolbar_order() -> list:
    global _MODES_CONFIG
    if _MODES_CONFIG is None:
        _MODES_CONFIG = _load_modes_yaml()
    return list(_MODES_CONFIG['toolbar_order'])
```

### Auto-config in base `mode.__init__`

The base class auto-loads config from YAML using the class name as the key.
No subclass needs to call a loader explicitly.

```python
class mode:
    def __init__(self):
        global _MODES_CONFIG
        if _MODES_CONFIG is None:
            _MODES_CONFIG = _load_modes_yaml()
        # derive YAML key from class name: draw_mode -> 'draw'
        yaml_key = type(self).__name__.replace('_mode', '')
        cfg = _MODES_CONFIG['modes'].get(yaml_key, {})
        # load name
        self.name = _(cfg['name']) if 'name' in cfg else 'mode'
        # load submodes from YAML (empty for dynamic modes)
        self.submodes = []
        self.submodes_names = []
        self.submode = []
        self.icon_map = {}
        self.pulldown_menu_submodes = []
        self.group_labels = []
        self.group_layouts = []
        self.tooltip_map = {}
        self.size_map = {}
        for group in cfg.get('submodes', []):
            keys = [opt['key'] for opt in group['options']]
            # default cascade: name defaults to key, icon defaults to key
            names = [_(opt.get('name', opt['key'])) for opt in group['options']]
            self.submodes.append(keys)
            self.submodes_names.append(names)
            self.submode.append(group.get('default', 0))
            # group label for ribbon-style display (i18n)
            label = group.get('group_label', '')
            self.group_labels.append(_(label) if label else '')
            self.group_layouts.append(group.get('layout', 'row'))
            for opt in group['options']:
                key = opt['key']
                # icon: defaults to key; 'none' means no icon
                icon_val = opt.get('icon', key)
                if icon_val != 'none':
                    self.icon_map[key] = icon_val
                # tooltip: defaults to name, then key
                if 'tooltip' in opt:
                    self.tooltip_map[key] = _(opt['tooltip'])
                # size hint
                if 'size' in opt:
                    self.size_map[key] = opt['size']
        # shared state
        self._key_sequences = {}
        self._recent_key_seq = ''
        self._specials_pressed = {'C': 0, 'A': 0, 'M': 0, 'S': 0}
```

### Class name to YAML key mapping

The convention is: `{yaml_key}_mode` is the Python class name.

| YAML key | Python class name | Derives automatically? |
| --- | --- | --- |
| `draw` | `draw_mode` | YES |
| `arrow` | `arrow_mode` | YES |
| `edit` | `edit_mode` | YES |
| `template` | `template_mode` | YES |
| `biotemplate` | `biomolecule_template_mode` | NO - needs alias |
| `usertemplate` | `user_template_mode` | NO - needs alias |
| `bondalign` | `bond_align_mode` | NO - needs alias |

Three classes don't follow `{key}_mode` exactly. Options:
1. Rename the YAML keys to match: `biomolecule_template`, `user_template`, `bond_align`
2. Rename the Python classes to match: `biotemplate_mode`, `usertemplate_mode`, `bondalign_mode`
3. Add an explicit `class_name` field in YAML for overrides

Option 2 (rename Python classes) is simplest since these are internal names.
Old names become aliases for backwards compatibility during transition.

### Behavior registry

Modes that need custom methods define a Python class as usual, but skip all
config setup in `__init__` (handled by base class):

```python
class draw_mode(edit_mode):
    def __init__(self):
        edit_mode.__init__(self)
        # only mode-specific state, NO config loading
        self._moved_atom = None
        self._start_atom = None

    def mouse_down(self, event, modifiers=[]):
        # ... behavioral logic unchanged ...

    def mouse_up(self, event):
        # ... behavioral logic unchanged ...
```

For `user_template_mode` (zero custom methods), no Python class definition is
needed at all. The factory generates it from YAML:

```python
# generated automatically by factory from YAML:
# usertemplate_mode = type('usertemplate_mode', (template_mode,), {})
```

### Factory function

Generates classes for modes that have no Python behavior class:

```python
# parent class lookup
_PARENT_MAP = {
    'edit_mode': edit_mode,
    'basic_mode': basic_mode,
    'template_mode': template_mode,
}

def _build_mode_classes() -> dict:
    """Generate mode classes from YAML for modes without Python behavior."""
    global _MODES_CONFIG
    if _MODES_CONFIG is None:
        _MODES_CONFIG = _load_modes_yaml()
    result = {}
    for yaml_key, cfg in _MODES_CONFIG['modes'].items():
        class_name = yaml_key + '_mode'
        # skip if a Python class already exists (has custom behavior)
        if class_name in globals():
            result[yaml_key] = globals()[class_name]
            continue
        # generate class from YAML
        parent = _PARENT_MAP.get(cfg.get('parent', 'edit_mode'), edit_mode)
        result[yaml_key] = type(class_name, (parent,), {})
    return result
```

---

## Step 3: Simplify and unify the 3 template modes

### Problem

The current design has 3 separate template mode classes with duplicated logic:
- `template_mode` (4 methods) - flat list from `Store.tm`
- `biomolecule_template_mode` (9 methods) - overengineered: filesystem scanning,
  category cross-referencing, index mapping, 7 state variables
- `user_template_mode` (0 methods) - just sets `template_manager = Store.utm`

Templates are simple: pick from a list, click to place. The category/catalog
complexity in `biomolecule_template_mode` should be in `template_catalog.py`
(which already exists), not in the mode class.

### Solution: one `template_mode` parameterized by YAML

All three become instances of a single `template_mode` class. The YAML config
specifies the template source. Categories (for biomolecule templates) are
handled by `template_catalog.py` and surfaced as submodes automatically.

YAML config for the 3 template modes:
```yaml
  template:
    name: template
    parent: edit_mode
    icon: template
    dynamic: true
    template_source: system
    # submodes: flat list of template names as buttons

  biotemplate:
    name: biomolecule templates
    parent: edit_mode
    icon: biotemplate
    dynamic: true
    template_source: biomolecule
    use_categories: true
    # submodes: [category buttons, template buttons for selected category]
    # same RadioSelect UI as draw_mode (angle row, bond order row, etc.)

  usertemplate:
    name: users templates
    parent: edit_mode
    icon: usertemplate
    dynamic: true
    template_source: user
    # submodes: flat list of user template names as buttons
```

No `pulldown_menu_submodes` needed. All template modes use the same
RadioSelect button rows as every other mode. For biomolecule templates:
row 0 = category buttons (amino acids, nucleotides, ...), row 1 = template
buttons for selected category. Clicking a category button refreshes the
template row - same pattern as other multi-row submodes.

Button labels for biomolecule templates can use standard 3-letter codes
(Ala, Gly, Cyt, Glc, etc.) which are compact and fit well in button rows.
Amino acids, nucleic acids, and sugars all have official 3-letter codes.
Lipids will need longer labels. This is handled by
`template_catalog.format_entry_label()`, not the YAML schema.

### Unified template_mode class

One class handles all three template sources. The `__init__` reads
`template_source` from YAML to decide which template manager to use.

```python
_TEMPLATE_MANAGERS = {
    'system': lambda: Store.tm,
    'biomolecule': lambda: Store.btm,
    'user': lambda: Store.utm,
}

class template_mode(edit_mode):
    def __init__(self):
        edit_mode.__init__(self)
        # name, icon_map loaded from YAML automatically
        # look up template source from YAML config
        cfg = _MODES_CONFIG['modes'].get(
            type(self).__name__.replace('_mode', ''), {}
        )
        source_key = cfg.get('template_source', 'system')
        self.template_manager = _TEMPLATE_MANAGERS[source_key]()
        # build submodes from template manager
        if cfg.get('use_categories'):
            self._build_categorized_submodes()
        else:
            self._build_flat_submodes()
        self.register_key_sequence('C-t', self._mark_focused_as_template_atom_or_bond)

    def _build_flat_submodes(self):
        """Simple flat list of template names."""
        names = self.template_manager.get_template_names()
        self.submodes = [names]
        self.submodes_names = [names]
        self.submode = [0]

    def _build_categorized_submodes(self):
        """Categories from directory structure via template_catalog."""
        entries = template_catalog.scan_template_dirs(
            template_catalog.discover_biomolecule_template_dirs()
        )
        catalog = template_catalog.build_category_map(entries)
        self._catalog = catalog
        self._category_keys = sorted(catalog.keys())
        category_labels = [k.replace('_', ' ') for k in self._category_keys]
        # get templates for first category
        template_labels = self._templates_for_category(0)
        self.submodes = [category_labels, template_labels]
        self.submodes_names = [category_labels, template_labels]
        self.submode = [0, 0]

    def _templates_for_category(self, category_index: int) -> list:
        """Get template names for a category index."""
        if not self._category_keys:
            return []
        key = self._category_keys[category_index]
        subcats = self._catalog[key]
        entries = []
        for subcat in sorted(subcats.keys()):
            entries.extend(subcats[subcat])
        return [template_catalog.format_entry_label(e) for e in entries]

    def on_submode_switch(self, submode_index, name=''):
        """When category changes, refresh template list."""
        if submode_index == 0 and hasattr(self, '_catalog'):
            template_labels = self._templates_for_category(self.submode[0])
            self.submodes[1] = template_labels
            self.submodes_names[1] = template_labels
            self.submode[1] = 0

    def mouse_click(self, event):
        # places template on canvas at click location
        # handles: empty space, atom attachment, bond attachment
        # validates valency before placement
        # (logic unchanged from current template_mode.mouse_click)
        ...

    def _mark_focused_as_template_atom_or_bond(self):
        # key binding C-t: marks focused atom/bond as template anchor
        ...

    def _get_transformed_template(self, index, coords, type='empty', paper=None):
        return self.template_manager.get_transformed_template(index, coords, type=type, paper=paper)

    def _get_templates_valency(self, index=None):
        if index is None:
            index = self.submode[0]
        return self.template_manager.get_templates_valency(index)
```

### What gets deleted

- `biomolecule_template_mode` class (164 lines) - replaced by `use_categories: true`
- `user_template_mode` class (15 lines) - replaced by `template_source: user`
- 7 state variables from biomolecule catalog
- 5 helper methods (`_apply_category_selection`, `_update_template_menu`,
  `_get_selected_template_index`, `_format_label`, `_build_biomolecule_catalog`)

The `biotemplate_mode` and `usertemplate_mode` Python classes are no longer
needed. The factory generates them from YAML with `template_mode` as parent.
The YAML `template_source` and `use_categories` fields drive the behavior.

---

## Step 4: Use `icon_map` and ribbon fields in `main.py`

Update submode button rendering in `change_mode()` (~line 611):

```python
for i, group_keys in enumerate(m.submodes):
    # render group label and separator if present
    label = m.group_labels[i] if hasattr(m, 'group_labels') else ''
    layout = m.group_layouts[i] if hasattr(m, 'group_layouts') else 'row'
    if label:
        # draw separator line above group, then label text
        _render_group_label(toolbar_frame, label)

    for sub in group_keys:
        # icon: use icon_map (handles default cascade from YAML)
        icon_name = getattr(m, 'icon_map', {}).get(sub, sub)
        img_name = m.__class__.__name__.replace("_mode", "") + "-" + icon_name
        if img_name in pixmaps.images:
            img = pixmaps.images[img_name]
        elif icon_name in pixmaps.images:
            img = pixmaps.images[icon_name]
        else:
            img = None
        # button size from YAML
        btn_size = getattr(m, 'size_map', {}).get(sub, 'small')
        # tooltip from YAML (falls back to name)
        tip = getattr(m, 'tooltip_map', {}).get(sub, '')
```

For `layout: grid`, render buttons in a multi-column grid frame instead of
a single row. The `columns` value from YAML controls wrap width.

Replace hardcoded `modes_sort` with YAML-driven ordering:

```python
self.modes_sort = modes.get_toolbar_order()
```

Replace hardcoded mode instantiation dict with factory:

```python
# before: manual dict of 14 instantiations
self.modes = {
    'draw': modes.draw_mode(),
    'edit': modes.edit_mode(),
    ...
}

# after: factory builds all modes from YAML
self.modes = modes.build_all_modes()
```

Remove `pulldown_menu_submodes` handling entirely. All submodes now render as
RadioSelect button rows (or grids). The `if i not in m.pulldown_menu_submodes`
branch and the `Pmw.OptionMenu` fallback are deleted. Template modes use the
same button UI as every other mode. For `on_submode_switch`, when a category
button is clicked, the template button row rebuilds (same as how other modes
handle dependent submode rows).

---

## Step 5: Clean up `pixmaps.py`

Remove `name_recode_map` dict and all references. The `.lower()` normalization
stays. The `icon_map` from YAML handles any key-to-filename divergences.

---

## Step 6: Update `docs/CHANGELOG.md`

---

## Parallel work plan (8 coders)

### Dependency graph

```
Phase 1 (no deps)        Phase 2 (needs YAML)     Phase 3 (integration)
 +-----------+            +-----------+             +-----------+
 | A: YAML   |----+------>| C: loader |--+--------->| G: main   |
 | file      |    |       | + base    |  |          | integrate |
 +-----------+    |       +-----------+  |          +-----------+
                  |                      |                |
 +-----------+    |       +-----------+  |          +-----------+
 | B: tests  |    +------>| D: static |--+--------->| H: verify |
 | (stubs)   |    |       | modes     |  |          | + changelog|
 +-----------+    |       +-----------+  |          +-----------+
                  |                      |
                  |       +-----------+  |
                  +------>| E: template|--+
                  |       | unify     |
                  |       +-----------+
                  |
                  |       +-----------+
                  +------>| F: ribbon |
                          | renderer  |
                          +-----------+
```

### Phase 1: parallel, no dependencies (coders A + B)

**Coder A: Write `modes.yaml`** (Step 1)
- Create `bkchem_data/modes.yaml` with all 14 mode definitions
- Verify YAML parses and all icon stems resolve to files in `pixmaps/`
- This is the critical path - everything else blocks on it
- Output: one file, validated by the verification script in Step 1

**Coder B: Write test stubs** (parallel with A)
- Write `tests/test_modes_yaml.py`: YAML loads, toolbar_order has 15 entries,
  every mode has `name` and `parent`, all icon stems resolve, default cascade
  works (key-only entries produce correct name/icon)
- Write `tests/test_mode_factory.py`: factory produces 14 classes, each has
  correct `name`, `submodes`, `icon_map`, `group_labels`, `tooltip_map`,
  `size_map` attributes
- Write `tests/test_template_mode_unified.py`: template_mode with
  `template_source` picks correct manager, `use_categories` builds 2 submode
  rows, category switch refreshes template row
- Tests use mocks/stubs initially, validate against interfaces

### Phase 2: parallel, each needs only the YAML file (coders C-F)

**Coder C: YAML loader + base class auto-config** (Step 2, first half)
- `_load_modes_yaml()`, `get_toolbar_order()`, `get_modes_config()`
- Rewrite `mode.__init__` to auto-load from YAML (the base class code in Step 2)
- Handle default cascade (`key` -> `name` -> `icon`)
- Handle ribbon fields (`group_labels`, `group_layouts`, `tooltip_map`, `size_map`)
- File: `modes.py` (top ~100 lines + base class)

**Coder D: Strip config from 11 static mode classes** (Step 2, second half)
- Remove hardcoded submodes/names/defaults from each `__init__`
- Keep all behavioral methods (mouse_down, mouse_up, etc.) unchanged
- Rename 3 classes: `bond_align_mode` -> `bondalign_mode`, etc.
- Write factory function `_build_mode_classes()` and `build_all_modes()`
- File: `modes.py` (the 11 class definitions)
- Depends on: Coder C's base class being done first, or work against the
  agreed interface (base class sets `self.submodes`, `self.icon_map`, etc.)

**Coder E: Unify 3 template modes** (Step 3)
- Write unified `template_mode` with `_build_flat_submodes()` and
  `_build_categorized_submodes()`
- Delete `biomolecule_template_mode` (164 lines) and `user_template_mode`
  (15 lines)
- Wire up `on_submode_switch` for category refresh
- File: `modes.py` (template section) + `template_catalog.py` if needed
- Can work in parallel with Coder D since template modes are separate classes

**Coder F: Ribbon-style renderer in `main.py`** (Step 4, renderer only)
- Write `_render_group_label()` helper function
- Write `_render_submode_grid()` for `layout: grid`
- Implement button `size: large` vs default small
- Implement tooltip display from `tooltip_map`
- These are self-contained rendering functions that consume the mode attributes
  set by Coder C's base class
- File: `main.py` (new helper functions, can be written independently)

### Phase 3: integration (coders G + H)

**Coder G: Wire everything together in `main.py`** (Step 4, integration)
- Replace `modes_sort` with `modes.get_toolbar_order()`
- Replace manual mode dict with `modes.build_all_modes()`
- Update `change_mode()` to use `icon_map`, call Coder F's renderer functions
- Remove `pulldown_menu_submodes` / `Pmw.OptionMenu` handling
- Remove `name_recode_map` from `pixmaps.py` (Step 5)
- File: `main.py` + `pixmaps.py`
- Depends on: C, D, E, F all merged

**Coder H: Verification + changelog** (Step 6)
- Run all test suites (Coder B's tests + existing tests)
- Run icon resolution verification script
- Run GUI smoke test
- Visual checks (all 14 modes, submodes, icons, template switching)
- Update `docs/CHANGELOG.md`
- Depends on: G complete

### Optimal timeline

```
         Coder A   B   C   D   E   F   G   H
Phase 1: [YAML ] [tests]
Phase 2:             [loader] [static] [tmpl] [ribbon]
Phase 3:                                      [wire] [verify]
```

Phase 1 coders (A, B) become available for Phase 2 review or Phase 3.
Coders C and D touch the same file (`modes.py`) but different sections -
coordinate via separate functions/classes, merge at end of Phase 2.
Coders E and F are fully independent of each other.
Coder G is the integration bottleneck - needs all Phase 2 work merged first.
Coder H runs after G, but can prepare test scripts during Phase 2.

### Merge strategy

Since coders C, D, and E all touch `modes.py`, use one of:
1. **Feature branches per section**: C works on `modes_loader.py` (new file),
   D and E work on separate branches of `modes.py`, merge sequentially
2. **Split `modes.py`**: extract loader to `modes_config.py`, keep behavioral
   classes in `modes.py`, template modes in `template_modes.py` - merge is
   trivial since files don't overlap
3. **Section ownership**: C owns lines 1-100, D owns lines 100-1500,
   E owns lines 1500-2276 - risky if line numbers shift

Option 2 (split into files, merge back if desired) is safest for parallel work.

---



```bash
# YAML loads and all icon references resolve
source source_me.sh && python3 -c "
import yaml, os, importlib.util
with open('packages/bkchem-app/bkchem_data/modes.yaml') as f:
    cfg = yaml.safe_load(f)
spec = importlib.util.find_spec('bkchem_data')
pixmap_dir = os.path.join(os.path.dirname(spec.origin), 'pixmaps')
missing = []
for mode_name, mcfg in cfg['modes'].items():
    for group in mcfg.get('submodes', []):
        for opt in group['options']:
            icon = opt.get('icon')
            if icon and not (os.path.exists(os.path.join(pixmap_dir, icon + '.gif'))
                         or os.path.exists(os.path.join(pixmap_dir, icon + '.png'))):
                missing.append(f'{mode_name}/{opt[\"key\"]}: {icon}')
if missing:
    print(f'MISSING ICONS: {missing}')
else:
    print(f'All icon references resolve ({len(cfg[\"modes\"])} modes)')
"

# pyflakes lint
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -k "pixmaps or modes or main" -x

# full bkchem-app test suite
source source_me.sh && python3 -m pytest packages/bkchem-app/tests/ -x

# GUI smoke test
source source_me.sh && python3 -c "
import sys; sys.argv = ['bkchem']
from bkchem.main import BKChem
app = BKChem()
app.initialize()
app.after(3000, app.destroy)
app.mainloop()
"
```

Visual checks:
- All 14 mode buttons appear in correct toolbar order
- Selected mode button has thick colored border
- All submode icons load for every mode
- Rotate: 2D/3D icons load via `.lower()`
- Draw: wavy icon loads via `icon_map`
- Arrow: all 5 arrow types load (previously from `arrow.available_types`)
- Dynamic modes populate correctly
- Biomolecule template category switching works
