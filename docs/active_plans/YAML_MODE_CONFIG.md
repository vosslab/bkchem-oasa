# YAML mode config, `.lower()` icon lookup, and selected-mode border

## Context

The mode/submode system in BKChem encodes toolbar configuration as Python data
structures inside class `__init__` methods (`modes.py`). This makes the config
hard to read and edit. The icon lookup chain uses a `name_recode_map` dict plus
multi-directory filesystem searches to resolve icon filenames. The active mode
button has minimal visual distinction (1px border change).

This plan addresses four improvements in one pass:
1. Extract static mode/submode config to a YAML data file
2. Add `.lower()` normalization in icon lookup (eliminates `2D`/`3D` recode entries)
3. Put icon filenames in YAML so lookup is direct (eliminates remaining recode map)
4. Add a thick colored border around the selected mode button

## Files to modify

| File | Change |
| --- | --- |
| `packages/bkchem-app/bkchem/pixmaps.py` | Step 0: add `.lower()`, shrink recode map to 1 entry |
| `packages/bkchem-app/bkchem/main.py` | Step 0: thick border on selected mode button |
| `packages/bkchem-app/bkchem_data/modes.yaml` | Step 1+: NEW - mode/submode config |
| `packages/bkchem-app/bkchem/modes.py` | Step 2: load submodes from YAML |
| `docs/CHANGELOG.md` | Document changes |

## Step 0: Quick wins - `.lower()` and mode button border

Two independent changes that can land immediately, no YAML needed.

### 0a: Add `.lower()` to icon lookup in `pixmaps.py`

In `images_dict.__getitem__` and `__contains__`, normalize `item` to lowercase
before looking it up. This handles `2D` -> `2d` and `3D` -> `3d` automatically.

Remove the `'2D'` and `'3D'` entries from `name_recode_map`, leaving only:

```python
name_recode_map = {
	'wavy': 'wavyline',  # draw_mode uses 'wavy', misc_mode uses 'wavyline' directly
}
```

The `wavy` -> `wavyline` entry stays until Step 4 replaces it with `icon_map`.

### 0b: Big border on selected mode button in `main.py`

In `change_mode()` (~line 582), after setting `self.mode`, loop through all
mode buttons and apply thick border + color to the selected one, flat to rest:

```python
# highlight the selected mode button
for btn_name in self.modes_sort:
	btn = self.radiobuttons.button(btn_name)
	if btn_name == tag:
		btn.configure(relief='sunken', borderwidth=3,
			highlightbackground='#4a90d9',
			highlightcolor='#4a90d9',
			highlightthickness=2)
	else:
		btn.configure(relief='flat', borderwidth=1,
			highlightthickness=0)
```

### Step 0 verification

```bash
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -k "pixmaps or main" -x
```

Then GUI smoke test to confirm:
- Draw mode selected shows thick blue border, others flat
- Rotate mode: 2D/3D icons load (`.lower()` handles case)
- Draw mode: wavy icon loads (still via recode map for now)

---

## Step 1: Create `modes.yaml`

New file at `packages/bkchem-app/bkchem_data/modes.yaml`.

Structure for each static mode (11 modes total, 3 are dynamic and stay in Python):

```yaml
# Static mode/submode configuration for BKChem toolbar
# Dynamic modes (template, biotemplate, usertemplate) load submodes at runtime

draw:
  name: draw
  icon: draw
  submodes:
    - options:
        - {key: '30', name: '30', icon: '30'}
        - {key: '18', name: '18', icon: '18'}
        - {key: '6', name: '6', icon: '6'}
        - {key: '1', name: '1', icon: '1'}
      default: 0
    - options:
        - {key: single, name: single, icon: single}
        - {key: double, name: double, icon: double}
        - {key: triple, name: triple, icon: triple}
      default: 0
    - options:
        - {key: normal, name: normal, icon: normal}
        - {key: wedge, name: wedge, icon: wedge}
        - {key: hashed, name: hashed, icon: hashed}
        - {key: adder, name: adder, icon: adder}
        - {key: bbold, name: bold, icon: bbold}
        - {key: dash, name: dash, icon: dash}
        - {key: dotted, name: dotted, icon: dotted}
        - {key: wavy, name: wavy, icon: wavyline}
      default: 0
    - options:
        - {key: fixed, name: fixed length, icon: fixed}
        - {key: freestyle, name: freestyle}
      default: 0
    - options:
        - {key: nosimpledouble, name: 'normal double bonds for wedge/hashed', icon: nosimpledouble}
        - {key: simpledouble, name: 'simple double bonds for wedge/hashed', icon: simpledouble}
      default: 1

rotate:
  name: rotate
  icon: rotate
  submodes:
    - options:
        - {key: '2D', name: '2D', icon: '2d'}
        - {key: '3D', name: '3D', icon: '3d'}
      default: 0
    - options:
        - {key: normal3d, name: 'normal 3D rotation', icon: normal3d}
        - {key: fixsomething, name: 'fix selected bond in 3D'}
      default: 0

# ... similar entries for arrow, edit, plus, text, bondalign, vector, mark,
#     bracket, misc modes
```

Key points:
- `key` = the submode string used in Python logic (unchanged)
- `name` = display label (passed through `_()` for i18n)
- `icon` = exact icon filename stem (no extension), omit if text-only
- `default` = index of initially selected option
- Dynamic modes (`template`, `biotemplate`, `usertemplate`) are NOT in YAML

## Step 2: Load YAML in `modes.py`

Add a module-level loader function:

```python
import yaml
from bkchem import os_support

def _load_modes_yaml() -> dict:
    yaml_path = os_support.get_path('modes.yaml', 'ostypes')
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

MODES_CONFIG = None  # loaded lazily on first use
```

Each static mode class `__init__` loads its config from YAML:

```python
class draw_mode(edit_mode):
    def __init__(self):
        edit_mode.__init__(self)
        global MODES_CONFIG
        if MODES_CONFIG is None:
            MODES_CONFIG = _load_modes_yaml()
        cfg = MODES_CONFIG['draw']
        self.name = _(cfg['name'])
        self.submodes = []
        self.submodes_names = []
        self.submode = []
        self.icon_map = {}  # submode key -> icon filename
        for group in cfg['submodes']:
            keys = [opt['key'] for opt in group['options']]
            names = [_(opt['name']) for opt in group['options']]
            self.submodes.append(keys)
            self.submodes_names.append(names)
            self.submode.append(group['default'])
            for opt in group['options']:
                if 'icon' in opt:
                    self.icon_map[opt['key']] = opt['icon']
```

To reduce duplication, add a helper to the base `mode` class:

```python
def _load_config_from_yaml(self, mode_key: str) -> None:
    global MODES_CONFIG
    if MODES_CONFIG is None:
        MODES_CONFIG = _load_modes_yaml()
    cfg = MODES_CONFIG[mode_key]
    self.name = _(cfg['name'])
    self.submodes = []
    self.submodes_names = []
    self.submode = []
    self.icon_map = {}
    for group in cfg['submodes']:
        keys = [opt['key'] for opt in group['options']]
        names = [_(opt['name']) for opt in group['options']]
        self.submodes.append(keys)
        self.submodes_names.append(names)
        self.submode.append(group['default'])
        for opt in group['options']:
            if 'icon' in opt:
                self.icon_map[opt['key']] = opt['icon']
```

Then each static mode class simplifies to:

```python
class draw_mode(edit_mode):
    def __init__(self):
        edit_mode.__init__(self)
        self._load_config_from_yaml('draw')
        # mode-specific state
        self._moved_atom = None
        self._start_atom = None
```

Dynamic modes (`template_mode`, `biomolecule_template_mode`, `user_template_mode`)
keep their Python-based submode setup unchanged since their options come from
`Store.tm` / `Store.utm` at runtime.

## Step 3: Add `.lower()` in `pixmaps.py` and remove recode map

In `images_dict.__getitem__` and `__contains__`, normalize the item name:

```python
def __getitem__(self, item: str) -> tkinter.PhotoImage:
    # normalize to lowercase for filesystem lookup
    item = item.lower()
    try:
        return dict.__getitem__(self, item)
    except KeyError:
        icon = _load_icon(item)
        self.__setitem__(item, icon)
        return icon
```

Delete `name_recode_map` entirely. The `wavy` -> `wavyline` mapping is now
handled by `icon_map` in the YAML config (step 2). The `2D` -> `2d` and
`3D` -> `3d` mappings are handled by `.lower()`.

## Step 4: Use `icon_map` for submode icon lookup in `main.py`

Update `change_mode()` (lines 611-618) to check `mode.icon_map` first:

```python
for sub in m.submodes[i]:
    # use explicit icon name from YAML if available
    icon_name = getattr(m, 'icon_map', {}).get(sub, sub)
    img_name = m.__class__.__name__.replace("_mode", "") + "-" + icon_name
    if img_name in pixmaps.images:
        img = pixmaps.images[img_name]
    elif icon_name in pixmaps.images:
        img = pixmaps.images[icon_name]
    else:
        img = None
```

This means `wavy` looks up `icon_map['wavy']` -> `'wavyline'` -> loads
`wavyline.gif` directly. No recode map needed.

## Step 5: Big border on selected mode button

In `main.py`, update mode button creation and selection to show a thick
colored border around the active mode:

1. Change mode button `borderwidth` from `config.border_width` (1) to 3
2. Add a highlight callback in `change_mode()`:

```python
def change_mode(self, tag):
    # ... existing cleanup code ...

    # highlight the selected mode button with a thick colored border
    for btn_name in self.modes_sort:
        btn = self.radiobuttons.button(btn_name)
        if btn_name == tag:
            btn.configure(relief='sunken', borderwidth=3,
                          highlightbackground='#4a90d9',
                          highlightcolor='#4a90d9',
                          highlightthickness=2)
        else:
            btn.configure(relief='flat', borderwidth=1,
                          highlightthickness=0)
```

This gives the selected mode a visible sunken+blue-border effect while
unselected modes stay flat and borderless.

## Step 6: YAML file location and loading

The YAML file lives at `packages/bkchem-app/bkchem_data/modes.yaml` (root of
the `bkchem_data` package). Loading uses `os_support._get_bkchem_data_dir()`
which resolves via `importlib.util.find_spec('bkchem_data')`:

```python
def _load_modes_yaml() -> dict:
    data_dir = os_support._get_bkchem_data_dir()
    yaml_path = os.path.join(data_dir, 'modes.yaml')
    with open(yaml_path, 'r') as fh:
        return yaml.safe_load(fh)
```

No changes to `os_support.py` needed.

## Step 7: Update changelog

Add entry to `docs/CHANGELOG.md` documenting all four changes.

## Verification

```bash
# pyflakes lint on changed files
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py -k "pixmaps or modes or main" -x

# verify YAML loads correctly
source source_me.sh && python3 -c "
import yaml
with open('packages/bkchem-app/bkchem_data/modes.yaml') as f:
    cfg = yaml.safe_load(f)
print(f'Loaded {len(cfg)} modes from YAML')
for mode_name, mode_cfg in cfg.items():
    n_submodes = len(mode_cfg.get('submodes', []))
    print(f'  {mode_name}: {n_submodes} submode groups')
"

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
- Selected mode button has thick colored border, unselected are flat
- All submode icons load (draw: hashed, wavy, fixed, etc.)
- Rotate mode: 2D/3D icons load via `.lower()`
- Misc mode: wavyline icon loads via `icon_map`
- Dynamic modes (template, biotemplate, usertemplate) still work
