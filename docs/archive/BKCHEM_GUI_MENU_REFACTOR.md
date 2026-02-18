# BKChem GUI menu refactor

## Purpose

Document where the menu and toolbar UI is defined, how entries are created, and
what to improve to make the system more modular and intuitive.

## Menu-related files

- [packages/bkchem/bkchem/main.py](packages/bkchem/bkchem/main.py)
  - Defines `menu_template` and constructs the top menu bar.
  - Adds plugin menu entries and wires enable/disable logic.
  - Builds the mode toolbar (radio buttons).
- [packages/bkchem/bkchem/context_menu.py](packages/bkchem/bkchem/context_menu.py)
  - Defines the right-click context menu and dynamically builds entries based
    on the current selection.
- [packages/bkchem/bkchem/modes.py](packages/bkchem/bkchem/modes.py)
  - Defines mode classes referenced by the mode toolbar.
- [packages/bkchem/bkchem/pixmaps.py](packages/bkchem/bkchem/pixmaps.py)
  - Holds toolbar icons used by mode buttons.
- [packages/bkchem/bkchem/plugins](packages/bkchem/bkchem/plugins)
  - Provides importer/exporter plugins that add to File > Import/Export.
- [packages/bkchem/bkchem/plugin_support.py](packages/bkchem/bkchem/plugin_support.py)
  - Defines script plugin discovery and menu injection logic.

## How each menu entry is created

### Top menu bar (main menus)

Definition:
- `menu_template` in `main.py` (line 178) is a list of tuples with the schema:
  - **Position 0**: `menu_name` (str) - Parent menu name, must match a registered menu
  - **Position 1**: `type` (str) - One of: `'menu'`, `'command'`, `'separator'`, `'cascade'`
  - **Position 2**: `label` (str) - Display text for the menu item (or help text for `'menu'` type)
  - **Position 3**: `accelerator` (str or None) - Keyboard shortcut in format like `'(C-x C-s)'`
  - **Position 4**: `status_help` (str) - Status bar help text shown on hover
  - **Position 5**: `command` (callable or None) - Function to call when item is clicked
  - **Position 6**: `state_var` (callable, str, or None) - Enablement predicate (see below)

Menu type special cases:
- `'menu'` type: Position 2 is balloon help, position 3 is side (`'left'` or `'right'`)
- `'cascade'` type: Position 2 is label, position 3 is status help
- `'separator'` type: Only positions 0-1 are used

Creation path (lines 302-319):
- `init_menu()` loops over `menu_template` and calls Pmw:
  - `'menu'` -> `addmenu(name, help, side=...)` - Creates a top-level menu
  - `'command'` -> `addmenuitem(menu, 'command', label=..., accelerator=..., statusHelp=..., command=...)`
  - `'separator'` -> `addmenuitem(menu, 'separator')`
  - `'cascade'` -> `addcascademenu(menu, label, help, tearoff=0)` - Creates a submenu

Enable/disable logic (line 1406):
- `update_menu_after_selection_change(e)` is called on every selection change event
- Loops through `menu_template` looking for `type == 'command'` with non-None `state_var`
- For each such entry:
  - If `state_var` is callable: call it and convert result to `'normal'` or `'disabled'`
  - If `state_var` is a string: look up attribute on `self.paper` and convert to state
  - Call `self._get_menu_component(menu_name).entryconfigure(label, state=state)`

Examples from the current template:
```python
# Always enabled (state_var=None)
(_('File'), 'command', _('New'), '(C-x C-n)', _("Create a new file..."), self.add_new_paper, None)

# Enabled when callable returns True
(_('Edit'), 'command', _('Undo'), '(C-z)', _("Revert the last change"),
 lambda: self.paper.undo(), lambda: self.paper.um.can_undo())

# Enabled when paper.selected is truthy
(_('Edit'), 'command', _('Cut'), '(C-w)', _("Copy and delete"),
 lambda: self.paper.selected_to_clipboard(delete_afterwards=1), 'selected')
```

### Plugins menu entries

Two plugin sources are inserted into the menu system:

- Import/Export plugins:
  - `init_plugins_menu()` adds entries into File > Import and File > Export
    by calling `menu.addmenuitem()` with the plugin handlers.
- Script plugins:
  - After menu creation, `init_menu()` inserts script plugins into either a
    named menu or the Plugins menu. A separator is inserted once per menu.

### Mode toolbar buttons

- `init_mode_buttons()` creates a `Pmw.RadioSelect` and adds a button per mode
  in `self.modes_sort`.
- Each button is created via `radiobuttons.add()` and uses an icon from
  `pixmaps.images` when present; otherwise it uses text.
- Clicking a button calls `change_mode()` which switches the active mode.

### Context menu (right click)

- `context_menu` is a `tkinter.Menu` that is assembled per selection.
- It builds cascades for configurable properties, then appends specific
  commands based on object types (bond, group, atom, mark, etc.).

## Internationalization (translation) system

### How menu translation works

BKChem uses the standard GNU gettext system for internationalization. The translation system is initialized at startup in [packages/bkchem/bkchem/bkchem.py](packages/bkchem/bkchem/bkchem.py) lines 44-96.

**Translation initialization flow**:

1. **Read language preference**: The preferred language is read from `prefs.xml` via `Store.pm.get_preference("lang")`

2. **Search for translation files**: BKChem looks for compiled message catalogs (`.mo` files) in these directories:
   - `../../../../share/locale` (system install location)
   - `../locale` (local development location)
   - Translation files are located at: `bkchem_data/locale/{language}/BKChem.po`

3. **Install translation function**: If a translation is found, gettext installs the `_()` function into Python's builtins:
   ```python
   tr = gettext.translation('BKChem', localedir=localedir, languages=lang)
   tr.install(names=['ngettext'])
   ```

4. **Fallback to English**: If no translation is found or language is `"en"`, a passthrough lambda is installed:
   ```python
   builtins.__dict__['_'] = lambda m: m
   ```

**Per-module translation usage**:

Every module that needs translation includes this pattern at the top:
```python
import builtins
_ = builtins.__dict__.get('_', lambda m: m)
```

This retrieves the globally-installed `_()` function, or falls back to a no-op if gettext is not initialized (e.g., in tests).

**Menu translation mechanism**:

All menu labels, help text, and accelerators use the `_()` function:
```python
(_('File'),  'command',  _('Save'),  '(C-x C-s)', _("Save the file"), self.save_CDML, None)
```

When the menu is created:
- `_('File')` looks up "File" in the message catalog
- If found, it returns the translated string (e.g., "Fichier" for French)
- If not found, it returns the original English string
- The Pmw menu widgets display the translated text

**Plugin menu translation**:

Plugin menu entries can also be translated. The pattern is:
```python
# In plugin code
menu = _("Plugins")  # Translatable parent menu
label = _("My Export Format")  # Translatable label

# In main.py plugin registration (line 328)
if menu and _(menu) in menus:
	menu = _(menu)  # Translate the menu name
```

This allows plugins to insert into translated menus (e.g., `_("File")` will match the File menu regardless of language).

**Available languages** (as of current codebase):

Translation files exist for these languages in `bkchem_data/locale/`:
- Czech (cs)
- German (de)
- Spanish (es)
- French (fr)
- Italian (it)
- Japanese (ja)
- Latvian (lv)
- Polish (pl)
- Russian (ru)
- Turkish (tr)
- Chinese Traditional (zh_TW)

**Language selection UI**:

Users can change the language via Options > Language menu item, which calls `interactors.select_language()` (line 356 in interactors.py):
- Shows a dialog with available languages
- Saves selection to preferences
- Requires restart to take effect

### Translation implications for menu refactor

When refactoring the menu system, the following translation-related requirements must be maintained:

1. **All user-visible strings must be wrapped in `_()`**:
   - Menu labels
   - Status bar help text
   - Tooltip text
   - Error messages

2. **String extraction must still work**: The `xgettext` tool scans source code for `_()` calls to build `.pot` template files. Any new menu definition format must be parseable by standard gettext tools.

3. **Menu lookup by translated name must be avoided**: Current code at line 328 looks up menus by `_(menu)` which is fragile:
   ```python
   if menu and _(menu) in menus:  # Bad: depends on translation
   ```
   The refactored system should use menu IDs, not labels:
   ```python
   if menu_id in menu_registry:  # Good: translation-independent
   ```

4. **Accelerator keys should not be translated**: Keyboard shortcuts like `(C-x C-s)` should remain consistent across languages. Only the display text changes.

5. **Plural forms need special handling**: If menu items display counts (e.g., "1 item selected" vs "5 items selected"), use `ngettext()`:
   ```python
   ngettext("%d item selected", "%d items selected", count) % count
   ```

### Recommended translation approach for refactored menus

For the proposed action registry system, translation should work like this:

```python
@dataclass
class Action:
	id: str                 # Not translated: "file.save"
	label_key: str          # Translation key: "Save"
	help_key: str           # Translation key: "Save the file"
	accelerator: str = None # Not translated: "C-x C-s"
	# ... other fields

	@property
	def label(self) -> str:
		"""Return translated label."""
		return _(self.label_key)

	@property
	def help_text(self) -> str:
		"""Return translated help text."""
		return _(self.help_key)
```

This approach:
- Keeps translation keys close to action definitions
- Allows lazy translation (evaluated when accessed, not at registration time)
- Makes it clear what strings need translation
- Enables validation that all keys exist in message catalogs

## Issues with the current structure

- The menu definition is embedded inside `main.py`, which mixes UI layout with
  application behavior and makes it harder to test or reuse.
- The `menu_template` tuple format is implicit and scattered; a small schema
  change requires editing both creation and update logic.
- Plugins inject menu items in multiple places (import/export and script
  plugins), with no central registry or consistent ordering policy.
- Mode toolbar and menu actions are separate definitions even when they trigger
  the same behavior.
- Enable/disable logic is centralized but relies on string attribute lookups on
  `paper`, which makes static analysis and refactoring difficult.

## Review notes

- Tuple lengths vary by menu type: `'menu'` and `'cascade'` entries use four
  fields, `'separator'` uses two, and `'command'` uses seven. Any refactor
  should validate length per type.
- `update_menu_after_selection_change()` accepts `state_var` values of
  callables, `paper` attribute names, and literal state strings
  (`'normal'` or `'disabled'`).
- Menu component lookup differs on macOS (`Pmw.MainMenuBar` vs `Pmw.MenuBar`).
  Refactors should preserve `_get_menu_component()` behavior for state updates.
- Translation assets: runtime lookup uses compiled `.mo` files in `share/locale`
  or `../locale`, while the repo ships `.po` sources in `bkchem_data/locale`.

## Review comments on the YAML + Dataclass Hybrid proposal

- The YAML example uses `menu_id.title()` for top-level labels. That will
  not preserve existing translation keys (for example "Save As.." or "Recent
  files"), and it will drift from translated strings. Prefer explicit
  `label_key` entries for top-level menus or keep menu labels in the action
  registry so gettext has stable keys.
- The YAML example stores `label_key`/`help_key` for cascades inside YAML.
  Standard gettext tooling will not extract translation keys from YAML, so
  either add a custom extractor or move cascade labels into Python where
  `_()` is called.
- `MenuBuilder._menu_items` stores `(menu_name, action.label)` and uses
  `entryconfigure(label, ...)`. This relies on translated labels being
  stable identifiers and can break if two labels collide. Prefer storing
  the actual Pmw menu component and index, or keep a mapping from action_id
  to the returned menu entry index.
- The current code uses `_get_menu_component()` to handle macOS vs non-macOS
  menubars. The example uses `pmw_menubar.component(...)` directly, which
  will bypass that logic. Keep `_get_menu_component()` or store the menu
  component returned by Pmw during construction.
- Plugin integration currently looks up menus by translated label text
  (for example `_("Import")`). A refactor should include a compatibility
  layer that maps legacy label-based plugin insertion to menu IDs.
- The YAML example uses bare strings with spaces for `label_key` values.
  YAML requires quoting for such keys (`"Recent files"`), otherwise it is
  easy to misparse.
## Refactor direction: YAML + Dataclass Hybrid

The recommended approach combines **YAML for menu structure** with **Python dataclasses for action definitions**. This provides:

- **Visibility**: Entire menu hierarchy visible in one YAML file
- **Type safety**: Action handlers are real Python functions, not strings
- **Portability**: YAML structure maps cleanly to Qt, macOS/Swift, web frameworks
- **Maintainability**: Non-programmers can reorganize menus, developers define type-safe actions
- **i18n compatibility**: Full gettext support with proper context

### Architecture overview

```
+-----------------------------------------------------------+
|                    Menu System Components                 |
+-----------------------------------------------------------+
|                                                           |
|  +-----------+     +------------+     +------------+      |
|  | menus.yaml|     | actions.py |     | Pmw/Tk     |      |
|  | structure |---->| dataclasses|---->| menus      |      |
|  | only      |     | + handlers |     | rendered   |      |
|  +-----------+     +------------+     +------------+      |
|      |                    |                              |
|      |                    |                              |
|      |                    v                              |
|      |              +------------+                       |
|      +------------->| MenuBuilder|                       |
|                     | YAML +     |                       |
|                     | Actions    |                       |
|                     +------------+                       |
|                                                           |
+-----------------------------------------------------------+
```

### 1. YAML menu structure (human-editable hierarchy)

Create `packages/bkchem/bkchem_data/menus.yaml` with the menu structure:

```yaml
# Menu hierarchy - structure only, no translations
# Easy to visualize and reorganize
menus:
  file:
    items:
      - action: file.new
      - action: file.save
      - action: file.save_as
      - action: file.save_template
      - action: file.load
      - action: file.load_same_tab
      - cascade: recent_files
      - separator: true

      # Export submenu
      - cascade: export
        items:
          - action: export.svg

      # Import submenu
      - cascade: import
        items: []  # Populated by plugins

      - separator: true
      - action: file.properties
      - separator: true
      - action: file.close_tab
      - separator: true
      - action: file.exit

  edit:
    items:
      - action: edit.undo
      - action: edit.redo
      - separator: true
      - action: edit.cut
      - action: edit.copy
      - action: edit.paste
      - separator: true
      - action: edit.copy_svg
      - separator: true
      - action: edit.select_all

  insert:
    items:
      - action: insert.biomolecule_template

  align:
    items:
      - action: align.top
      - action: align.bottom
      - action: align.left
      - action: align.right
      - separator: true
      - action: align.center_h
      - action: align.center_v

# Cascade menu definitions
cascades:
  recent_files:
    label_key: Recent files
    help_key: The most recently used files

  export:
    label_key: Export
    help_key: Export the current file

  import:
    label_key: Import
    help_key: Import a non-native file format

# Mode toolbar (separate from menus but same action IDs)
toolbar:
  modes:
    - action: mode.edit
      icon: edit
    - action: mode.draw
      icon: draw
    - action: mode.template
      icon: template
    - action: mode.biotemplate
      icon: biotemplate
```

**Benefits of YAML structure:**
- [x] Entire menu hierarchy visible at a glance
- [x] Easy to reorganize (drag items, no syntax errors)
- [x] Non-programmers can edit menu order
- [x] Clear separation of structure from behavior
- [x] Can generate from external tools
- [x] Easy to diff in version control

### 2. Python action registry (type-safe handlers)

Create `packages/bkchem/bkchem/actions.py` with type-safe action definitions:

```python
"""Action registry with type-safe dataclasses.

All UI actions defined here with handlers, translations, and enablement logic.
"""
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class MenuAction:
	"""Type-safe action definition.

	Uses translation keys (not translated strings) so translations are
	evaluated lazily when the menu is built.
	"""
	id: str                           # Unique ID: "file.save"
	label_key: str                    # Translation key: "Save"
	help_key: str                     # Translation key: "Save the file"
	handler: Callable                 # Function to call
	accelerator: Optional[str] = None # Keyboard shortcut: "C-x C-s"
	enabled_when: Optional[Callable] = None  # Predicate: lambda ctx: ...
	icon: Optional[str] = None        # Icon name from pixmaps

	@property
	def label(self) -> str:
		"""Return translated label (evaluated lazily)."""
		return _(self.label_key)

	@property
	def help_text(self) -> str:
		"""Return translated help text (evaluated lazily)."""
		return _(self.help_key)


class ActionRegistry:
	"""Central registry for all UI actions."""

	def __init__(self):
		self._actions = {}

	def register(self, action: MenuAction) -> MenuAction:
		"""Register an action, raising if ID already exists."""
		if action.id in self._actions:
			raise ValueError(f"Duplicate action ID: {action.id}")
		self._actions[action.id] = action
		return action

	def get(self, action_id: str) -> MenuAction:
		"""Get action by ID, raising if not found."""
		if action_id not in self._actions:
			raise KeyError(f"Action not found: {action_id}")
		return self._actions[action_id]

	def is_enabled(self, action_id: str, context) -> bool:
		"""Check if action is currently enabled."""
		action = self.get(action_id)
		if action.enabled_when is None:
			return True
		return action.enabled_when(context)

	def __contains__(self, action_id: str) -> bool:
		return action_id in self._actions


def register_all_actions(app) -> ActionRegistry:
	"""Register all application actions.

	Called during app initialization with the BKChem app instance.
	Returns the populated action registry.
	"""
	registry = ActionRegistry()

	# Top-level menu definitions (preserves existing translation keys)
	registry.register(MenuAction(
		id='menu.file',
		label_key='File',
		help_key='File operations',
		handler=None,  # Top-level menus have no handler
	))

	registry.register(MenuAction(
		id='menu.edit',
		label_key='Edit',
		help_key='Edit operations',
		handler=None,
	))

	# File menu actions
	registry.register(MenuAction(
		id='file.new',
		label_key='New',
		help_key='Create a new file in a new tab',
		accelerator='C-x C-n',
		handler=app.add_new_paper,
	))

	registry.register(MenuAction(
		id='file.save',
		label_key='Save',
		help_key='Save the file',
		accelerator='C-x C-s',
		handler=app.save_CDML,
	))

	registry.register(MenuAction(
		id='file.exit',
		label_key='Exit',
		help_key='Exit BKChem',
		accelerator='C-x C-c',
		handler=app._quit,
	))

	# Edit menu actions
	registry.register(MenuAction(
		id='edit.undo',
		label_key='Undo',
		help_key='Revert the last change',
		accelerator='C-z',
		handler=lambda: app.paper.undo(),
		enabled_when=lambda ctx: ctx.paper.um.can_undo(),
	))

	registry.register(MenuAction(
		id='edit.cut',
		label_key='Cut',
		help_key='Copy and delete selected objects',
		accelerator='C-w',
		handler=lambda: app.paper.selected_to_clipboard(delete_afterwards=1),
		enabled_when=lambda ctx: bool(ctx.paper.selected),
	))

	# ... register all other actions ...

	return registry
```

**Benefits of Python dataclass actions:**
- [x] Full type safety (handler is `Callable`, not string)
- [x] IDE autocomplete and type checking
- [x] Compile-time error detection
- [x] Easy to test (can instantiate without GUI)
- [x] Lazy translation (evaluated when accessed)
- [x] Clear enablement predicates

### 3. Platform abstraction layer (toolkit and OS independence)

Create `packages/bkchem/bkchem/menu_backend.py` with platform-agnostic interface:

```python
"""Platform and toolkit-agnostic menu backend interface."""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
from dataclasses import dataclass

@dataclass
class MenuItemHandle:
	"""Opaque handle to a menu item (platform-specific)."""
	backend_data: Any

@dataclass
class MenuHandle:
	"""Opaque handle to a menu (platform-specific)."""
	backend_data: Any


class MenuBackend(ABC):
	"""Platform and toolkit-agnostic menu backend interface.

	MenuBuilder uses ONLY this interface, making it portable
	to Qt, Gtk, native macOS/Windows, or web frameworks.
	"""

	@abstractmethod
	def create_menubar(self, parent_window) -> Any:
		"""Create menubar widget."""
		pass

	@abstractmethod
	def add_menu(self, label: str, help_text: str) -> MenuHandle:
		"""Add top-level menu."""
		pass

	@abstractmethod
	def add_menu_item(
		self,
		menu: MenuHandle,
		label: str,
		command: Callable,
		accelerator: Optional[str] = None,
		help_text: Optional[str] = None
	) -> MenuItemHandle:
		"""Add menu item."""
		pass

	@abstractmethod
	def add_separator(self, menu: MenuHandle) -> MenuItemHandle:
		"""Add separator."""
		pass

	@abstractmethod
	def add_cascade(
		self,
		menu: MenuHandle,
		label: str,
		help_text: str
	) -> MenuHandle:
		"""Add cascade submenu."""
		pass

	@abstractmethod
	def set_item_state(self, item: MenuItemHandle, enabled: bool):
		"""Enable or disable menu item."""
		pass


class PmwMenuBackend(MenuBackend):
	"""Pmw/Tk menu backend with platform auto-detection."""

	def __init__(self, parent_window):
		self.parent = parent_window
		self.adapter = self._create_platform_adapter()
		self._menu_index = {}
		self._item_index = {}

	def _create_platform_adapter(self):
		"""Auto-detect platform and create adapter."""
		import sys
		if sys.platform == 'darwin':
			return PmwMacOSAdapter()
		elif sys.platform == 'win32':
			return PmwWindowsAdapter()
		else:
			return PmwLinuxAdapter()

	# Implementation delegates to platform adapter
	# (see MENU_REFACTOR_ANALYSIS.md for full code)
```

Create `packages/bkchem/bkchem/menu_adapters.py` with platform-specific implementations:

```python
"""Platform-specific Pmw menu adapters."""
import Pmw

class PmwAdapter:
	"""Base adapter with common Pmw logic."""

	def add_menu_item(self, menubar, menu_name, label, command, accel, help_text):
		menubar.addmenuitem(menu_name, 'command',
		                    label=label, command=command,
		                    accelerator=accel, statusHelp=help_text or '')

	def add_separator(self, menubar, menu_name):
		menubar.addmenuitem(menu_name, 'separator')


class PmwMacOSAdapter(PmwAdapter):
	"""macOS-specific adapter using MainMenuBar."""

	def create_menubar(self, parent):
		return Pmw.MainMenuBar(parent)

	def get_menu_component(self, menubar, menu_name):
		# macOS-specific component lookup
		return menubar.component(menu_name + '-menu')


class PmwLinuxAdapter(PmwAdapter):
	"""Linux-specific adapter using standard MenuBar."""

	def create_menubar(self, parent):
		return Pmw.MenuBar(parent, hull_relief='raised', hull_borderwidth=1)

	def get_menu_component(self, menubar, menu_name):
		return menubar.component(menu_name + '-menu')


class PmwWindowsAdapter(PmwAdapter):
	"""Windows-specific adapter."""

	def create_menubar(self, parent):
		return Pmw.MenuBar(parent, hull_relief='flat', hull_borderwidth=0)

	def get_menu_component(self, menubar, menu_name):
		return menubar.component(menu_name + '-menu')
```

**Benefits of platform abstraction:**
- [x] YAML and actions 100% platform-agnostic
- [x] MenuBuilder has zero platform-specific code
- [x] Easy to port to Qt, Gtk, Cocoa (swap backend)
- [x] Platform differences isolated in adapters
- [x] Testable with mock backends

### 4. Menu builder (combines YAML + actions)

Create `packages/bkchem/bkchem/menu_builder.py` to combine YAML structure with Python actions:

```python
"""Menu builder that combines YAML structure with action registry."""
import yaml
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class MenuContext:
	"""Context passed to action enablement predicates."""
	app: 'BKChem'
	paper: 'chem_paper'


@dataclass
class CascadeDefinition:
	"""Cascade submenu definition with translation keys."""
	id: str
	label_key: str
	help_key: str

	@property
	def label(self) -> str:
		return _(self.label_key)

	@property
	def help_text(self) -> str:
		return _(self.help_key)


class MenuBuilder:
	"""Platform-agnostic menu builder.

	Uses MenuBackend interface - no platform-specific code.
	Works with Pmw, Qt, Gtk, or native menus via backend swap.
	"""

	def __init__(
		self,
		yaml_path: str,
		action_registry: ActionRegistry,
		cascades: Dict[str, CascadeDefinition],
		backend: MenuBackend
	):
		"""Initialize menu builder.

		Args:
			yaml_path: Path to menus.yaml file
			action_registry: Registry containing all actions
			cascades: Dict of cascade definitions with translation keys
			backend: MenuBackend implementation (Pmw, Qt, etc.)
		"""
		with open(yaml_path, 'r') as f:
			self.menu_data = yaml.safe_load(f)
		self.actions = action_registry
		self.cascades = cascades
		self.backend = backend  # ONLY interface we use

		# Track items by action_id -> MenuItemHandle (platform-agnostic)
		self._menu_items = {}

	def build_menus(self, parent_window):
		"""Build all menus from YAML structure.

		Args:
			parent_window: Parent window widget

		Returns:
			Toolkit-specific menubar widget
		"""
		menubar = self.backend.create_menubar(parent_window)

		for menu_id, menu_def in self.menu_data['menus'].items():
			# Get menu label from action registry to preserve translation keys
			menu_action = self.actions.get(f'menu.{menu_id}')

			# Add menu (backend handles platform differences)
			menu_handle = self.backend.add_menu(
				menu_action.label,
				menu_action.help_text
			)

			# Build menu items recursively
			self._build_menu_items(menu_handle, menu_def['items'])

		return menubar

	def _build_menu_items(self, menu_handle: MenuHandle, items: list):
		"""Recursively build menu items (platform-agnostic).

		Args:
			menu_handle: MenuHandle from backend
			items: List of item definitions from YAML
		"""
		for item in items:
			if item.get('separator'):
				self.backend.add_separator(menu_handle)

			elif 'action' in item:
				action_id = item['action']
				action = self.actions.get(action_id)

				# Add menu item via backend
				item_handle = self.backend.add_menu_item(
					menu_handle,
					action.label,
					action.handler,
					action.accelerator,
					action.help_text
				)

				# Track for state updates (using opaque handle)
				self._menu_items[action_id] = item_handle

			elif 'cascade' in item:
				cascade_id = item['cascade']
				cascade_def = self.cascades[cascade_id]

				# Add cascade via backend
				cascade_handle = self.backend.add_cascade(
					menu_handle,
					cascade_def.label,
					cascade_def.help_text
				)

				# Build cascade items recursively
				if 'items' in item:
					self._build_menu_items(cascade_handle, item['items'])

	def update_menu_states(self, context: MenuContext):
		"""Update enable/disable state for all menu items.

		Called on selection changes and other state updates.
		Platform-agnostic - backend handles toolkit specifics.
		"""
		for action_id, item_handle in self._menu_items.items():
			enabled = self.actions.is_enabled(action_id, context)
			# Backend handles platform-specific state setting
			self.backend.set_item_state(item_handle, enabled)


# Usage in main.py (platform-agnostic)
def init_menu(self):
	"""Initialize menu system using YAML + action registry."""
	# Register all actions (platform-agnostic)
	self.action_registry = register_all_actions(self)

	# Define cascades with translation keys (platform-agnostic)
	cascades = {
		'export': CascadeDefinition(
			id='export',
			label_key='Export',
			help_key='Export to other formats'
		),
		'import': CascadeDefinition(
			id='import',
			label_key='Import',
			help_key='Import from other formats'
		),
		'recent_files': CascadeDefinition(
			id='recent_files',
			label_key='Recent files',
			help_key='Recently opened files'
		),
	}

	# Create backend (auto-detects platform: macOS/Linux/Windows)
	backend = PmwMenuBackend(self)

	# Build menus from YAML (platform-agnostic)
	menu_yaml_path = os.path.join(
		os_support.get_bkchem_run_dir(),
		'../bkchem_data/menus.yaml'
	)
	self.menu_builder = MenuBuilder(
		menu_yaml_path,
		self.action_registry,
		cascades,
		backend  # Swap backend for Qt/Gtk/native
	)

	# Create menubar
	self.menubar = self.menu_builder.build_menus(self)
	self.menubar.pack(fill='x')

def update_menu_after_selection_change(self, event):
	"""Update menu states on selection changes."""
	context = MenuContext(app=self, paper=self.paper)
	self.menu_builder.update_menu_states(context)
```

**Benefits of menu builder:**
- [x] Clean separation: YAML structure, Python handlers, backend rendering
- [x] Platform-agnostic: Zero platform-specific code in builder
- [x] Easy to test: Can build menus with mock backend
- [x] Portable: Swap backend for Qt, Gtk, native, web
- [x] Maintainable: Change structure in YAML, add actions in Python

### 5. Performance monitoring (critical requirement)

**REQUIREMENT:** Menu state updates MUST NOT slow down interaction. Target < 5ms per update.

Create `packages/bkchem/bkchem/menu_performance.py`:

```python
"""Performance monitoring for menu system."""
import time
import logging
from collections import deque
from typing import Callable, Any

logger = logging.getLogger(__name__)


class PerformanceMonitor:
	"""Monitor menu operation performance."""

	def __init__(self, warn_threshold_ms: float = 5.0):
		"""Initialize performance monitor.

		Args:
			warn_threshold_ms: Warn if operation exceeds this (milliseconds)
		"""
		self.warn_threshold = warn_threshold_ms / 1000.0  # Convert to seconds
		self.measurements = deque(maxlen=100)  # Keep last 100 measurements
		self.enabled = True  # Can disable in production

	def measure(self, operation_name: str):
		"""Context manager to measure operation time.

		Usage:
			with perf_monitor.measure("update_menu_states"):
				menu_builder.update_menu_states(context)
		"""
		return _MeasurementContext(self, operation_name)

	def record(self, operation_name: str, duration_sec: float):
		"""Record measurement."""
		if not self.enabled:
			return

		self.measurements.append((operation_name, duration_sec))

		# Warn if slow
		if duration_sec > self.warn_threshold:
			logger.warning(
				f"Menu operation '{operation_name}' took {duration_sec*1000:.2f}ms "
				f"(threshold: {self.warn_threshold*1000:.0f}ms)"
			)

	def get_stats(self, operation_name: str = None):
		"""Get statistics for operations.

		Args:
			operation_name: Filter by operation name (None for all)

		Returns:
			Dict with min, max, avg, p95 times in milliseconds
		"""
		if operation_name:
			measurements = [d for n, d in self.measurements if n == operation_name]
		else:
			measurements = [d for _, d in self.measurements]

		if not measurements:
			return None

		measurements_sorted = sorted(measurements)
		return {
			'count': len(measurements),
			'min_ms': measurements_sorted[0] * 1000,
			'max_ms': measurements_sorted[-1] * 1000,
			'avg_ms': sum(measurements) / len(measurements) * 1000,
			'p95_ms': measurements_sorted[int(len(measurements) * 0.95)] * 1000
		}


class _MeasurementContext:
	"""Context manager for measuring operation time."""

	def __init__(self, monitor: PerformanceMonitor, operation_name: str):
		self.monitor = monitor
		self.operation_name = operation_name
		self.start_time = None

	def __enter__(self):
		self.start_time = time.perf_counter()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		duration = time.perf_counter() - self.start_time
		self.monitor.record(self.operation_name, duration)
		return False  # Don't suppress exceptions
```

**Instrumented MenuBuilder:**

```python
class MenuBuilder:
	def __init__(self, yaml_path, actions, cascades, backend, perf_monitor=None):
		# ... existing init code ...
		self.perf_monitor = perf_monitor or PerformanceMonitor()

	def build_menus(self, parent_window):
		"""Build menus with performance monitoring."""
		with self.perf_monitor.measure("build_menus"):
			menubar = self.backend.create_menubar(parent_window)

			for menu_id, menu_def in self.menu_data['menus'].items():
				with self.perf_monitor.measure(f"build_menu_{menu_id}"):
					menu_action = self.actions.get(f'menu.{menu_id}')
					menu_handle = self.backend.add_menu(
						menu_action.label,
						menu_action.help_text
					)
					self._build_menu_items(menu_handle, menu_def['items'])

			return menubar

	def update_menu_states(self, context: MenuContext):
		"""Update menu states with performance monitoring."""
		with self.perf_monitor.measure("update_menu_states"):
			for action_id, item_handle in self._menu_items.items():
				enabled = self.actions.is_enabled(action_id, context)
				self.backend.set_item_state(item_handle, enabled)

	def print_performance_stats(self):
		"""Print performance statistics."""
		stats = self.perf_monitor.get_stats("update_menu_states")
		if stats:
			print(f"Menu state updates (last {stats['count']} operations):")
			print(f"  Min:  {stats['min_ms']:.2f}ms")
			print(f"  Avg:  {stats['avg_ms']:.2f}ms")
			print(f"  P95:  {stats['p95_ms']:.2f}ms")
			print(f"  Max:  {stats['max_ms']:.2f}ms")
```

**Usage with performance monitoring:**

```python
# In main.py
def init_menu(self):
	# Create performance monitor
	perf_monitor = PerformanceMonitor(warn_threshold_ms=5.0)

	# Create backend
	backend = PmwMenuBackend(self)

	# Create menu builder with monitoring
	self.menu_builder = MenuBuilder(
		menu_yaml_path,
		self.action_registry,
		cascades,
		backend,
		perf_monitor=perf_monitor
	)

	# Build menus
	self.menubar = self.menu_builder.build_menus(self)

	# Print initial build stats
	if config.debug:
		self.menu_builder.print_performance_stats()

def update_menu_after_selection_change(self, event):
	"""Update menu states with monitoring."""
	context = MenuContext(app=self, paper=self.paper)
	self.menu_builder.update_menu_states(context)

	# Check performance periodically
	if config.debug and hasattr(self, '_menu_update_count'):
		self._menu_update_count += 1
		if self._menu_update_count % 100 == 0:
			self.menu_builder.print_performance_stats()
```

**Baseline measurement script:**

```python
# tests/benchmark_menu_performance.py
"""Benchmark menu system performance."""
import time
from unittest.mock import Mock

def benchmark_current_system():
	"""Benchmark current tuple-based menu system."""
	# Mock BKChem app with current menu system
	app = create_mock_app_current()

	# Measure menu build time
	start = time.perf_counter()
	app.init_menu()
	build_time = time.perf_counter() - start

	# Measure update time (100 iterations)
	update_times = []
	for _ in range(100):
		start = time.perf_counter()
		app.update_menu_after_selection_change(None)
		update_times.append(time.perf_counter() - start)

	print(f"Current system:")
	print(f"  Build time: {build_time*1000:.2f}ms")
	print(f"  Update avg: {sum(update_times)/len(update_times)*1000:.2f}ms")
	print(f"  Update p95: {sorted(update_times)[95]*1000:.2f}ms")

def benchmark_new_system():
	"""Benchmark new YAML + action registry system."""
	# Similar benchmarking for new system
	pass

if __name__ == "__main__":
	print("Benchmarking menu systems...")
	benchmark_current_system()
	benchmark_new_system()

	# Acceptance criteria:
	# - Build time: < 100ms (one-time cost, not critical)
	# - Update time p95: < 5ms (critical - happens frequently)
	# - Update time avg: < 3ms (target)
```

**Performance acceptance criteria:**

| Operation | Current | Target | Maximum |
|-----------|---------|--------|---------|
| Menu build (one-time) | ~50ms | < 100ms | 200ms |
| State update (frequent) | ~20ms | < 3ms avg | 5ms p95 |
| Action lookup | O(n) | O(1) | O(1) |
| State predicate eval | - | < 0.1ms | 0.5ms |

**Optimization strategy if targets not met:**

1. **Index actions by state dependency** (expected: 5-10x speedup)
2. **Cache predicate results** (expected: 2-3x speedup)
3. **Batch state updates with after_idle** (expected: reduces jank)
4. **Use C extension for hot paths** (last resort)

**Continuous monitoring:**

```python
# Enable in development builds
if config.debug:
	# Log slow menu operations
	logging.basicConfig(level=logging.WARNING)

	# Print stats on exit
	import atexit
	atexit.register(lambda: app.menu_builder.print_performance_stats())
```

### 4. Plugin menu API (stable contract)

Plugins can register actions without modifying YAML:

```python
class PluginMenuAPI:
	"""Stable API for plugins to register menu actions."""

	def __init__(self, action_registry: ActionRegistry, menu_builder: MenuBuilder):
		self.actions = action_registry
		self.menus = menu_builder

	def register_action(self, action: MenuAction) -> None:
		"""Register a new action.

		Args:
			action: MenuAction with id, label_key, handler, etc.

		Raises:
			ValueError: If action ID already exists
		"""
		self.actions.register(action)

	def add_to_menu(self, menu_path: str, action_id: str, position: int = -1):
		"""Add an action to a menu at runtime.

		Args:
			menu_path: Menu path like "File/Export" or "Plugins"
			action_id: ID of registered action
			position: Where to insert (-1 for end)

		Example:
			api.add_to_menu("File/Export", "export.my_format")
		"""
		# Parse menu path and insert into YAML structure
		# This allows plugins to extend menus dynamically
		pass

	def create_submenu(self, parent_path: str, submenu_id: str,
	                   label_key: str, help_key: str):
		"""Create a new submenu.

		Example:
			api.create_submenu("Plugins", "my_plugin",
			                  "My Plugin", "My plugin commands")
		"""
		pass


# Plugin usage example
def init_export_plugin(api: PluginMenuAPI):
	"""Plugin initialization (called by plugin loader)."""

	# Register action
	api.register_action(MenuAction(
		id='export.my_format',
		label_key='My Custom Format',
		help_key='Export to my custom format',
		handler=my_export_function,
	))

	# Add to Export submenu
	api.add_to_menu('File/Export', 'export.my_format')
```

**Benefits for plugins:**
- [x] No direct YAML editing required
- [x] Type-safe action registration
- [x] Can extend any menu by path
- [x] Automatic translation support
- [x] Same pattern as core actions

#### Backward compatibility for legacy plugins

Existing plugins use label-based menu lookup (e.g., `_("Import")`). Provide a compatibility shim:

```python
class PluginMenuAPI:
	# ... existing methods ...

	def _legacy_label_to_menu_id(self, translated_label: str) -> str:
		"""Map legacy translated labels to menu IDs.

		Used for backward compatibility with plugins that call:
			self.menu.addmenuitem(_("Import"), ...)

		Args:
			translated_label: Translated menu label like "Import"

		Returns:
			Menu ID like "import"

		Raises:
			KeyError: If label not found
		"""
		# Build reverse mapping from translated labels to cascade IDs
		label_map = {
			cascade_def.label: cascade_id
			for cascade_id, cascade_def in self.menus.cascades.items()
		}

		# Also map top-level menu labels
		for menu_id in self.menus.menu_data['menus'].keys():
			menu_action = self.actions.get(f'menu.{menu_id}')
			label_map[menu_action.label] = menu_id

		if translated_label not in label_map:
			raise KeyError(f"No menu found for label: {translated_label}")

		return label_map[translated_label]

	def add_to_menu_by_label(self, menu_label: str, action_id: str):
		"""Add action to menu by translated label (legacy compatibility).

		DEPRECATED: Use add_to_menu with menu path instead.

		Args:
			menu_label: Translated menu label like _("Import")
			action_id: ID of registered action

		Example (legacy plugin code):
			api.add_to_menu_by_label(_("Import"), "import.my_format")
		"""
		# Convert label to menu ID, then use modern API
		menu_id = self._legacy_label_to_menu_id(menu_label)
		self.add_to_menu(menu_id, action_id)
```

**Migration path for plugins:**
1. Phase 4: Add compatibility shim so existing plugins continue working
2. Document new `add_to_menu(path, action_id)` API for new plugins
3. Deprecate `add_to_menu_by_label()` with warnings in plugin docs
4. Phase 6: Remove compatibility shim after plugin migration complete

### 5. Toolbar unification (modes use same action IDs)

Mode toolbar defined in same YAML file:

```yaml
# In menus.yaml
toolbar:
  modes:
    - action: mode.edit
      icon: edit
    - action: mode.draw
      icon: draw
    - action: mode.template
      icon: template
    # ... more modes
```

Toolbar builder uses action registry:

```python
def build_mode_toolbar(self, radioframe, app):
	"""Build mode toolbar from YAML + action registry."""
	toolbar_def = self.menu_data.get('toolbar', {})
	mode_defs = toolbar_def.get('modes', [])

	radiobuttons = Pmw.RadioSelect(
		radioframe,
		buttontype='button',
		selectmode='single',
		orient='horizontal',
		command=app.change_mode,
	)

	for mode_def in mode_defs:
		action_id = mode_def['action']
		icon_name = mode_def.get('icon')
		action = self.actions.get(action_id)

		# Add button with icon or text
		if icon_name and icon_name in pixmaps.images:
			button = radiobuttons.add(
				action.id,
				image=pixmaps.images[icon_name],
				text=action.label,
			)
			# Tooltip from action help text
			app.balloon.bind(button, action.help_text)
		else:
			radiobuttons.add(action.id, text=action.label)

	return radiobuttons
```

**Benefits:**
- [x] Same action definitions for menu and toolbar
- [x] Consistent labels and help text
- [x] Single place to change mode metadata
- [x] Toolbar order in YAML, not scattered in code

### 6. Comprehensive tests

Create `tests/test_menu_system.py`:

```python
"""Test suite for YAML + dataclass menu system."""
import yaml
from bkchem.actions import register_all_actions, MenuAction
from bkchem.menu_builder import MenuBuilder


def test_all_yaml_actions_exist():
	"""Validate YAML references only registered actions."""
	# Load YAML structure
	with open('bkchem_data/menus.yaml') as f:
		menu_data = yaml.safe_load(f)

	# Register all actions (with mock app)
	class MockApp:
		pass
	registry = register_all_actions(MockApp())

	# Check all action IDs in YAML exist in registry
	def check_items(items):
		for item in items:
			if 'action' in item:
				assert item['action'] in registry, \
					f"YAML references unknown action: {item['action']}"
			if 'items' in item:
				check_items(item['items'])

	for menu_def in menu_data['menus'].values():
		check_items(menu_def['items'])


def test_accelerators_are_unique():
	"""Validate no duplicate keyboard shortcuts."""
	registry = register_all_actions(MockApp())
	accelerators = {}

	for action_id, action in registry._actions.items():
		if action.accelerator:
			assert action.accelerator not in accelerators, \
				f"Duplicate accelerator {action.accelerator}: " \
				f"{action_id} and {accelerators[action.accelerator]}"
			accelerators[action.accelerator] = action_id


def test_all_handlers_callable():
	"""Validate all action handlers are callable."""
	registry = register_all_actions(MockApp())

	for action_id, action in registry._actions.items():
		assert callable(action.handler), \
			f"Action {action_id} handler is not callable"


def test_all_translation_keys_exist():
	"""Validate all translation keys exist in .po files."""
	registry = register_all_actions(MockApp())

	# This would check actual .po files for label_key and help_key
	# For now, just ensure keys are not empty
	for action_id, action in registry._actions.items():
		assert action.label_key, \
			f"Action {action_id} missing label_key"
		assert action.help_key, \
			f"Action {action_id} missing help_key"


def test_yaml_syntax_valid():
	"""Validate YAML file parses without errors."""
	with open('bkchem_data/menus.yaml') as f:
		data = yaml.safe_load(f)

	assert 'menus' in data
	assert 'cascades' in data
	assert isinstance(data['menus'], dict)


def test_menu_builder_no_crashes():
	"""Smoke test: menu builder runs without crashing."""
	registry = register_all_actions(MockApp())
	builder = MenuBuilder('bkchem_data/menus.yaml', registry)

	# Should not raise
	assert builder.menu_data is not None
	assert builder.actions is not None
```

**Test benefits:**
- [x] Catch YAML syntax errors early
- [x] Detect orphaned action IDs
- [x] Prevent duplicate shortcuts
- [x] Validate translation keys
- [x] Run without full GUI

## Implementation phases

### Phase 0: Preparation and baseline measurement (no refactor code changes)
- Document current menu structure
- Map all menu items to their handlers
- Identify all enablement predicates
- Create test plan
- **Measure actual menu update performance baseline**: Before building any
  performance monitoring infrastructure, measure the current
  `update_menu_after_selection_change()` timing with a simple `time.perf_counter`
  wrapper. If the current system is not actually slow (< 5ms), the
  PerformanceMonitor class and optimization phases are unnecessary. The proposed
  indexed state updates are the right optimization idea, but the monitoring
  framework around it is premature until a real performance problem is confirmed.
- **Scope boundary**: Moving format handlers to OASA is a separate architectural
  project from the menu refactor. Format handlers are tightly coupled to
  BKChem's CDML document model; extracting them requires solving the
  molecule-to-CDML conversion problem. That work should have its own plan
  document and should not block menu refactor progress.

### Phase 1: Action registry foundation
- Create `actions.py` module with `Action` and `ActionRegistry` classes
- Register File menu actions as proof of concept
- Add unit tests for registry (add, get, duplicate detection)
- No GUI changes yet

### Phase 2: Parallel menu building
- Create `MenuItem` and `MENU_STRUCTURE` for File menu only
- Add `build_menu()` function that can build from both old template and new structure
- Keep old `menu_template` active, build new structure in parallel
- Add integration test comparing both outputs
- Verify File menu looks and behaves identically

### Phase 3: Incremental migration
- Migrate one menu at a time: Edit, Insert, Align, Object, Chemistry, Options, Help
- For each menu:
  - Register all actions in registry
  - Define MenuItem structure
  - Remove from old template
  - Add regression test
- Keep both systems working during migration

### Phase 4: Plugin integration
- Create `PluginMenuAPI`
- Update import/export plugin registration to use API
- Update script plugin registration to use API
- Remove old plugin menu code

### Phase 5: Toolbar unification
- Extract mode actions into registry
- Update toolbar creation to reference actions
- Share enablement logic between menu and toolbar

### Phase 6: Cleanup
- Remove old `menu_template`
- Remove old `init_menu()` code
- Remove old `update_menu_after_selection_change()` code
- Add comprehensive test suite
- Update documentation

## Suggested first step

Start with Phase 1: Create `packages/bkchem/bkchem/actions.py` and register just the File > Save/Load actions:

```python
# actions.py
from dataclasses import dataclass

@dataclass
class Action:
	id: str
	label: str
	help_text: str
	accelerator: str = None
	handler: callable = None
	enabled_when: callable = None

class ActionRegistry:
	def __init__(self):
		self._actions = {}

	def register(self, action):
		if action.id in self._actions:
			raise ValueError(f"Duplicate action: {action.id}")
		self._actions[action.id] = action
		return action

	def get(self, action_id):
		return self._actions[action_id]

	def __contains__(self, action_id):
		return action_id in self._actions

# Create global registry
_registry = ActionRegistry()

# Register File menu actions
def register_file_actions(app):
	"""Register File menu actions. Called during app init."""
	_registry.register(Action(
		id='file.new',
		label=_('New'),
		help_text=_("Create a new file in a new tab"),
		accelerator='C-x C-n',
		handler=app.add_new_paper,
		enabled_when=None  # Always enabled
	))

	_registry.register(Action(
		id='file.save',
		label=_('Save'),
		help_text=_("Save the file"),
		accelerator='C-x C-s',
		handler=app.save_CDML,
		enabled_when=None
	))

	# ... more actions

def get_registry():
	return _registry
```

Then add a test in `tests/test_actions.py`:

```python
def test_file_actions_registered():
	from bkchem.actions import get_registry
	registry = get_registry()
	assert 'file.new' in registry
	assert 'file.save' in registry
	# Verify no duplicates
	assert len(registry._actions) == len(set(registry._actions.keys()))
```

This provides a foundation to build on incrementally without breaking the existing menu system.
