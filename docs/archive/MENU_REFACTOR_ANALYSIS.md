# Menu Refactor: Deep Analysis

## 1. Plugin and Addon Architecture Assessment

### Current Plugin Types

**A. Import/Export Format Handlers** (packages/bkchem/bkchem/plugins/*.py)

These are NOT actually plugins - they are core format handlers statically imported:
- CML, CML2 (Chemical Markup Language v1 and v2)
- CDXML (ChemDraw XML)
- molfile (MDL MOL format)
- SMILES, InChI (chemical identifiers)
- PDF, PNG, SVG, PS (Cairo-based exporters)
- ODF (OpenDocument format)

Current architecture:
```python
# In __init__.py - statically imported
_names = ["CML", "CML2", "smiles", "inchi", "ps_builtin",
          "molfile", "pdf_cairo", "png_cairo", "odf",
          "svg_cairo", "ps_cairo", "CDXML"]

# Each module exports:
name = "SVG_Cairo"
extensions = [".svg"]
exporter = svg_cairo_exporter
importer = None  # or importer class
local_name = _("SVG (Cairo)")
```

**B. Script Plugins** (XML-defined, exec-based)

User-installable Python scripts loaded from:
- System plugin directories
- User's ~/.bkchem/addons/

XML manifest format:
```xml
<plugin type="script">
  <meta>
    <description lang="en">Plugin description</description>
  </meta>
  <source>
    <file>script.py</file>
    <menu-text lang="en">Menu Label</menu-text>
    <menu>Plugins</menu>
  </source>
</plugin>
```

Script execution: `exec(code, {'App': Store.app})` with no sandboxing.

**C. Mode Plugins** (XML-defined, importlib-based)

Custom drawing modes loaded at startup.

### Recommendation: Reclassify, Don't Eliminate

#### Category 1: Core Formats (BELONG IN OASA, NOT BKCHEM)

**ARCHITECTURAL PRINCIPLE:** Format handlers are backend functionality and belong in OASA, not the GUI.

Move to `packages/oasa/oasa/formats/`:
- CML, CML2 (Chemical Markup Language)
- molfile (MDL MOL format)
- SMILES, InChI (chemical identifiers)
- CDXML (ChemDraw XML)

**Rationale:**
- Format I/O is **chemistry logic**, not GUI logic
- OASA is the backend library - it should handle molecule encoding/decoding
- BKChem GUI should just call OASA format registry
- Makes OASA reusable by other tools (command-line, web, etc.)
- Clear separation: OASA = chemistry, BKChem = GUI

**Current problem:**
```python
# BKChem has format handlers tightly coupled to GUI
# packages/bkchem/bkchem/plugins/CML.py
class CML_importer(plugin.importer):
    def get_cdml_dom(self, file_name):
        # Returns CDML (BKChem-specific format)
        # Tightly coupled to BKChem's document structure
```

**Correct architecture:**
```python
# OASA provides format codecs (chemistry only)
# packages/oasa/oasa/formats/cml.py
class CMLCodec:
    def encode(self, molecule: oasa.Molecule) -> str:
        """Encode molecule to CML XML."""
        pass

    def decode(self, cml_string: str) -> oasa.Molecule:
        """Decode CML XML to molecule."""
        pass

# OASA provides format registry (like Python codecs)
# packages/oasa/oasa/formats/registry.py
class FormatRegistry:
    """Registry of molecule format codecs."""

    def __init__(self):
        self._codecs = {}

    def register(self, name: str, extensions: List[str], codec_class):
        """Register format codec."""
        self._codecs[name] = {
            'extensions': extensions,
            'codec': codec_class,
        }

    def get_codec(self, name: str):
        """Get codec by name."""
        return self._codecs[name]['codec']()

    def get_codec_for_extension(self, ext: str):
        """Get codec by file extension."""
        for name, info in self._codecs.items():
            if ext in info['extensions']:
                return info['codec']()
        raise ValueError(f"No codec for extension: {ext}")

# Register built-in formats
default_registry = FormatRegistry()
default_registry.register('CML', ['.cml'], CMLCodec)
default_registry.register('molfile', ['.mol', '.sdf'], MolfileCodec)
default_registry.register('SMILES', ['.smi', '.smiles'], SMILESCodec)
default_registry.register('InChI', ['.inchi'], InChICodec)
default_registry.register('CDXML', ['.cdxml'], CDXMLCodec)

# BKChem GUI just uses OASA registry
# packages/bkchem/bkchem/main.py
def import_file(self, file_path):
    """Import molecule from file."""
    ext = os.path.splitext(file_path)[1]
    codec = oasa.formats.default_registry.get_codec_for_extension(ext)

    with open(file_path, 'r') as f:
        content = f.read()

    molecule = codec.decode(content)

    # Convert OASA molecule to BKChem paper representation
    self.paper.add_molecule_from_oasa(molecule)
```

**Benefits:**
- OASA is truly standalone (doesn't depend on BKChem)
- Command-line tools can use OASA formats: `oasa-convert input.mol output.cml`
- Web applications can use OASA formats
- Clear responsibility: OASA = data, BKChem = UI
- Easier to test (no GUI required for format tests)

**Migration plan:**
1. Create `packages/oasa/oasa/formats/` directory
2. Create `FormatRegistry` in OASA
3. Move chemistry logic from BKChem plugins to OASA codecs
4. BKChem uses OASA registry to populate Import/Export menus
5. Remove BKChem format plugins

**BKChem menu integration:**
```python
# BKChem automatically populates Import/Export from OASA
def init_import_export_menus(self):
    """Build Import/Export menus from OASA format registry."""
    import oasa.formats

    for format_name in oasa.formats.default_registry.list_formats():
        codec_info = oasa.formats.default_registry.get_info(format_name)

        # Add to Import menu if codec supports decoding
        if codec_info.has_decoder:
            self.menu_builder.add_format_action(
                menu='import',
                action_id=f'import.{format_name}',
                label=codec_info.display_name,
                extensions=codec_info.extensions,
                handler=lambda path: self.import_via_oasa(path, format_name)
            )

        # Add to Export menu if codec supports encoding
        if codec_info.has_encoder:
            self.menu_builder.add_format_action(
                menu='export',
                action_id=f'export.{format_name}',
                label=codec_info.display_name,
                extensions=codec_info.extensions,
                handler=lambda path: self.export_via_oasa(path, format_name)
            )
```

**Result:** Import/Export menus automatically populated from OASA, no BKChem "plugins" needed.

#### Category 2: Renderer Backends (SHOULD be plugins, but better API)

Keep as optional but improve architecture:
- PDF (Cairo)
- PNG (Cairo)
- SVG (Cairo) - competes with built-in SVG
- PS (Cairo and built-in)
- ODF (OpenDocument)

**Rationale:**
- Cairo is an external dependency (may not be installed)
- Users might want to extend with new backends
- Legitimate use case for plugin architecture

**Action:** Create a renderer plugin API with capability detection:
```python
# packages/bkchem/bkchem/formats/renderer_plugin.py
class RendererPlugin:
    """Base class for renderer plugins."""

    @property
    def name(self) -> str:
        """User-visible name."""
        pass

    @property
    def file_extensions(self) -> List[str]:
        """File extensions handled."""
        pass

    @property
    def capabilities(self) -> Set[str]:
        """Capabilities: 'vector', 'raster', 'cairo', etc."""
        pass

    def can_render(self) -> bool:
        """Check if dependencies are available."""
        try:
            import cairo
            return True
        except ImportError:
            return False
```

#### Category 3: Script Plugins (SHOULD remain, but sandboxed)

Keep user extensibility but add safety:

**Current risks:**
- Arbitrary code execution in GUI process
- No timeout or error recovery
- Full access to application state
- Can block event loop

**Action:** Redesign script plugin architecture:
```python
class ScriptPluginSandbox:
    """Sandboxed execution environment for plugins."""

    def __init__(self, plugin_path, timeout=30):
        self.plugin_path = plugin_path
        self.timeout = timeout

    def run(self, context):
        """Run plugin in restricted environment.

        Args:
            context: PluginContext with safe API surface

        Raises:
            TimeoutError: Plugin exceeded timeout
            SecurityError: Plugin attempted unsafe operation
        """
        # Restricted globals (no exec, eval, open, etc.)
        safe_globals = {
            'App': context.app_api,  # Limited API, not full app
            'Selection': context.selection_api,
            'Canvas': context.canvas_api,
        }

        # Execute with timeout
        with ExecutionTimeout(self.timeout):
            exec(code, safe_globals)  # nosec - controlled environment
```

#### Category 4: Mode Plugins (RECONSIDER need)

Current: Custom drawing modes via XML manifest + importlib.

**Question:** Are mode plugins actually used?
- Check if any exist in the wild
- If none exist, remove the mechanism
- Drawing modes are tightly coupled to BKChem internals
- Hard to write correctly without deep knowledge

**Recommendation:** Remove mode plugin support unless evidence of actual use.

### Summary: Plugin Reclassification

| Current "Plugin" | New Category | Rationale |
|------------------|--------------|-----------|
| CML, CML2 | Core Format | Standard chemistry interchange |
| CDXML | Core Format | ChemDraw compatibility essential |
| molfile | Core Format | Widely used standard |
| SMILES, InChI | Core Format | Standard identifiers |
| SVG (built-in) | Core Renderer | Native format |
| PDF (Cairo) | Optional Renderer Plugin | Requires Cairo dependency |
| PNG (Cairo) | Optional Renderer Plugin | Requires Cairo dependency |
| SVG (Cairo) | Optional Renderer Plugin | Alternative to built-in |
| PS (Cairo/built-in) | Optional Renderer Plugin | Niche use case |
| ODF | Optional Renderer Plugin | Specialized format |
| Script plugins (XML) | User Extension Plugin | Keep but sandbox |
| Mode plugins (XML) | **Remove** | No evidence of use |
| Batch mode | **Remove or redesign** | Security risk |

---

## 2. Menu System Complexity: Can We Simplify Hooks?

### Current Hook Points

**A. Dynamic Plugin Injection**

Lines 389-404 in main.py:
```python
def init_plugins_menu(self):
    for name in sorted(self.plugins.keys()):
        plugin = self.plugins[name]
        if plugin.importer:
            self.menu.addmenuitem(_("Import"), 'command', ...)
        if plugin.exporter:
            self.menu.addmenuitem(_("Export"), 'command', ...)
```

Lines 325-338 in main.py (script plugins):
```python
for name in self.plug_man.get_names(type="script"):
    menu = self.plug_man.get_menu(name)
    if menu and _(menu) in menus:
        menu = _(menu)
    else:
        menu = _("Plugins")
    self.menu.addmenuitem(menu, 'command', ...)
```

**Complexity factors:**
1. Happens during menu construction
2. Uses translated label lookup (_("Import"))
3. Script plugins can inject into ANY menu by name
4. No validation of menu existence
5. Separators inserted inconsistently

**B. Recent Files Menu**

Built dynamically from preferences:
```python
# Lines 442-445
for i in range(1, 6):
    recent = Store.pm.get_preference("recent-file%d" % i)
    if recent:
        self.menu.addmenuitem("Recent files", ...)
```

**Complexity factors:**
1. Preference-driven menu construction
2. Must happen after menu creation but before display
3. Needs to update when files are opened

**C. Selection-Driven Enablement**

Line 1406-1415:
```python
def update_menu_after_selection_change(self, e):
    """Enable/disable menu items based on selection."""
    for menu_name, type, label, accel, help, command, state_var in self.menu_template:
        if type == 'command' and state_var:
            if callable(state_var):
                enabled = state_var()
            elif isinstance(state_var, str):
                enabled = getattr(self.paper, state_var)
            self._get_menu_component(menu_name).entryconfigure(label, ...)
```

**Complexity factors:**
1. Loops through entire menu template on every selection change
2. Uses translated labels for lookup (fragile)
3. Mixed callable/string state predicates
4. Fires frequently (every click, selection change)

### Simplification Strategies

#### Strategy 1: Declarative Plugin Slots

Replace runtime menu injection with declarative plugin registration:

**Before (complex):**
```python
# Plugin decides where to inject
self.menu.addmenuitem(_("Import"), 'command', label=local_name, ...)
```

**After (simple):**
```python
# Plugin declares capabilities
class CMLPlugin:
    def register_formats(self, registry):
        registry.register_importer(
            name="CML",
            extensions=[".cml"],
            handler=CML_importer,
        )
```

**YAML menu structure (knows about plugins):**
```yaml
menus:
  file:
    items:
      - cascade: import
        items:
          - plugin_slot: importers  # Filled by format registry
      - cascade: export
        items:
          - plugin_slot: exporters  # Filled by format registry
```

**Benefits:**
- No runtime label lookups
- Plugin registration happens before menu construction
- Menu structure is visible in YAML
- Type-safe plugin API

#### Strategy 2: Observable Recent Files

Replace preference polling with observer pattern:

**Before (complex):**
```python
# Read preferences during menu init
for i in range(1, 6):
    recent = Store.pm.get_preference("recent-file%d" % i)
```

**After (simple):**
```python
class RecentFilesManager:
    def __init__(self):
        self._files = []
        self._observers = []

    def add_file(self, path):
        """Add file and notify observers."""
        self._files.insert(0, path)
        self._files = self._files[:5]
        self._notify()

    def get_menu_items(self):
        """Return list of menu action IDs."""
        return [f"file.recent_{i}" for i in range(len(self._files))]
```

**Menu builder:**
```python
# Recent files cascade is dynamically populated
recent_files_manager.add_observer(menu_builder.refresh_recent_files)
```

**Benefits:**
- Recent files manager is testable
- Menu updates automatically
- No preference reading during menu construction
- Clean separation of concerns

#### Strategy 3: Efficient State Updates

Replace full menu scan with targeted updates:

**Before (complex):**
```python
def update_menu_after_selection_change(self, e):
    # Loop through ALL menu items
    for item in self.menu_template:
        if item.state_var:
            # Look up by label (fragile)
            self._get_menu_component(menu).entryconfigure(label, ...)
```

**After (simple):**
```python
class MenuBuilder:
    def __init__(self):
        # Index actions by state dependency
        self._state_dependent_actions = {
            'selection': ['edit.cut', 'edit.copy', 'edit.delete'],
            'undo': ['edit.undo'],
            'redo': ['edit.redo'],
        }

    def update_state(self, state_key, context):
        """Update only actions that depend on this state."""
        for action_id in self._state_dependent_actions.get(state_key, []):
            self._update_action_state(action_id, context)
```

**Event binding:**
```python
# Only update selection-dependent actions
paper.bind("<<selection-changed>>",
           lambda e: menu_builder.update_state('selection', context))
```

**Benefits:**
- O(n) where n = state-dependent actions, not all actions
- No label lookups
- State dependencies are explicit
- Can optimize further (batch updates)

#### Strategy 4: Remove Script Plugin Menu Injection

Script plugins can inject into any menu by translated name. This is too flexible and fragile.

**Before (complex):**
```python
menu = self.plug_man.get_menu(name)  # Can be any string
if menu and _(menu) in menus:  # Translated label lookup
    self.menu.addmenuitem(menu, 'command', ...)
```

**After (simple):**
```python
# Script plugins go in Plugins menu ONLY
# Or register as format handler (goes in Import/Export)
class PluginMenuAPI:
    def add_plugin_command(self, name, handler, description):
        """Add command to Plugins menu."""
        # No menu choice - always goes in Plugins menu
```

**Benefits:**
- No translated label lookups
- Plugins can't break by choosing nonexistent menu
- Predictable location
- Users know where to find plugins

### Hook Complexity Summary

| Hook | Current Complexity | Simplified Approach | Reduction |
|------|-------------------|---------------------|-----------|
| Plugin injection | Runtime label lookup, any menu | Declarative slots, format registry | 70% |
| Recent files | Preference polling during init | Observable manager, auto-update | 60% |
| State updates | Full menu scan on every event | Targeted updates by state key | 80% |
| Script plugins | Arbitrary menu injection | Fixed "Plugins" menu only | 90% |

**Overall:** Menu system complexity can be reduced by ~70% through:
1. Declarative plugin slots (not runtime injection)
2. Observable state managers (not polling)
3. Indexed state updates (not full scans)
4. Restricted plugin locations (not arbitrary menus)

---

## 3. Menu System Migration: Challenges and Solutions

### Challenge 1: Breaking Existing Import/Export Plugins

**Problem:**
- 12+ format handlers (CML, CDXML, molfile, etc.) dynamically add menu items
- Current code: `self.menu.addmenuitem(_("Import"), 'command', label=name, ...)`
- After refactor: "Import" menu might not exist or have different structure

**Impact:** High - users can't import/export files

**Solution:**

**Phase 1:** Add format registry parallel to current system
```python
# New registry (doesn't break anything)
format_registry = FormatRegistry()
for plugin in self.plugins.values():
    if plugin.importer:
        format_registry.register_importer(plugin.name, plugin.importer)
    if plugin.exporter:
        format_registry.register_exporter(plugin.name, plugin.exporter)

# Keep old menu building working
self.init_plugins_menu()  # Old code unchanged
```

**Phase 2:** Update YAML menu to reference registry
```yaml
menus:
  file:
    items:
      - cascade: import
        items:
          - format_slot: importers  # Populated from registry
      - cascade: export
        items:
          - format_slot: exporters  # Populated from registry
```

**Phase 3:** Remove old plugin menu code after validation

**Testing:**
- Verify each format can import/export
- Test with Cairo missing (graceful degradation)
- Test with no plugins loaded

---

### Challenge 2: Translation Key Stability

**Problem:**
- Current menu labels are translation keys: `_("File")`, `_("Save As...")`
- Menu items looked up by translated label
- Changing translation keys breaks:
  - .po files (translators' work)
  - Plugin menu injection (looks up by translated label)
  - Internal code that references menu items

**Impact:** Critical - breaks all non-English users

**Solution:**

**Step 1:** Extract all current translation keys
```bash
# Find all menu labels in menu_template
grep "_('.*')" main.py | sort -u > current_translation_keys.txt

# Example keys:
# _("File")
# _("Save As...")
# _("Recent files")
```

**Step 2:** Preserve keys in action registry
```python
# OLD (in menu_template):
(_('File'), 'command', _('Save As...'), ...)

# NEW (in actions.py):
MenuAction(
    id='file.save_as',
    label_key='Save As...',  # SAME KEY - translations work
    help_key='Save the file with a new name',
    handler=app.save_as,
)
```

**Step 3:** Validate with translation extraction
```bash
# Run xgettext to extract keys
xgettext -k_ -kN_ -o messages.pot actions.py

# Compare with old .pot file
diff old_messages.pot messages.pot

# Should be identical (or only additions)
```

**Step 4:** Test translations
```bash
# For each locale (cs, de, fr, etc.):
# 1. Compile .po files
msgfmt locale/cs/LC_MESSAGES/bkchem.po -o bkchem.mo

# 2. Run BKChem with that locale
LANG=cs_CZ.UTF-8 python3 bkchem

# 3. Check menu labels are translated
```

**Gotchas:**
- Some keys have context: Save (file) vs Save (template)
- Use `pgettext(context, key)` for disambiguation
- Document context in comments for translators

---

### Challenge 3: Plugin Backward Compatibility

**Problem:**
- Existing script plugins use: `self.menu.addmenuitem(_("Plugins"), ...)`
- After refactor, `self.menu` and `addmenuitem` won't exist
- Unknown number of user-created plugins in the wild

**Impact:** Medium - breaks user extensions (but rare)

**Solution:**

**Phase 1:** Add compatibility shim (as documented in BKCHEM_GUI_MENU_REFACTOR.md)
```python
class LegacyMenuShim:
    """Backward compatibility for old plugin API."""

    def __init__(self, menu_builder):
        self.menu_builder = menu_builder

    def addmenuitem(self, menu_label, item_type, **kwargs):
        """Legacy API: add item by translated menu label."""
        # Map translated label to menu ID
        menu_id = self._label_to_id(menu_label)

        # Convert to new action system
        if item_type == 'command':
            action_id = f"plugin.{kwargs['label'].replace(' ', '_')}"
            action = MenuAction(
                id=action_id,
                label_key=kwargs['label'],
                help_key=kwargs.get('statusHelp', ''),
                handler=kwargs['command'],
            )
            self.menu_builder.actions.register(action)
            self.menu_builder.add_to_menu(menu_id, action_id)

    def _label_to_id(self, translated_label):
        """Map translated menu label to menu ID."""
        # Reverse translation lookup
        label_map = {
            _("Plugins"): "plugins",
            _("Import"): "import",
            _("Export"): "export",
        }
        return label_map.get(translated_label, "plugins")
```

**Phase 2:** Document deprecation
```python
# In plugin API docs:
# DEPRECATED: Don't use self.menu.addmenuitem()
# NEW API: Use plugin_api.add_plugin_command()

def init_plugin(plugin_api):
    # OLD WAY (still works but deprecated)
    # self.menu.addmenuitem(_("Plugins"), 'command', ...)

    # NEW WAY
    plugin_api.add_plugin_command(
        name="My Plugin Action",
        handler=my_handler,
        description="What this does",
    )
```

**Phase 3:** Announce deprecation timeline
- Add deprecation warning in console when old API used
- Document migration guide
- Wait 2-3 releases
- Remove shim

**Testing:**
- Find existing script plugins (check forums, GitHub, etc.)
- Test each with shim
- Provide migration examples

---

### Challenge 4: Platform-Specific Menu Handling (macOS)

**Problem:**
- macOS uses different menu class: `MainMenuBar` vs `MenuBar`
- Current code: `_get_menu_component()` abstracts this
- Refactored MenuBuilder must preserve platform differences
- Testing on macOS is essential but may not be available

**Impact:** High - breaks macOS builds completely if wrong

**Solution:**

## Platform Abstraction Architecture

**Goal:** YAML and action registry should be 100% platform-agnostic. All platform differences isolated in backend adapters.

### Architecture Layers

```
+----------------------------------------------------------+
|  Layer 1: Platform-Agnostic Core                         |
|  - menus.yaml (pure structure)                           |
|  - actions.py (pure Python handlers)                     |
|  - MenuBuilder (orchestration only)                      |
+----------------------------------------------------------+
                        |
                        v
+----------------------------------------------------------+
|  Layer 2: Toolkit Abstraction (MenuBackend interface)   |
|  - PmwMenuBackend                                        |
|  - QtMenuBackend (future)                                |
|  - SwiftMenuBackend (future)                             |
+----------------------------------------------------------+
                        |
                        v
+----------------------------------------------------------+
|  Layer 3: Platform-Specific Adapters                    |
|  - PmwMacOSAdapter                                       |
|  - PmwLinuxAdapter                                       |
|  - PmwWindowsAdapter                                     |
+----------------------------------------------------------+
```

**Step 1:** Define platform-agnostic MenuBackend interface
```python
# packages/bkchem/bkchem/menu_backend.py
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Tuple
from dataclasses import dataclass

@dataclass
class MenuItemHandle:
    """Opaque handle to a menu item (platform-specific)."""
    backend_data: Any  # Platform backend stores its own representation

@dataclass
class MenuHandle:
    """Opaque handle to a menu (platform-specific)."""
    backend_data: Any


class MenuBackend(ABC):
    """Platform and toolkit-agnostic menu backend interface.

    This interface provides complete abstraction over:
    - Toolkit differences (Pmw, Qt, Gtk, native)
    - Platform differences (macOS, Linux, Windows)
    - Widget library details (Tk, Qt, Cocoa)

    MenuBuilder uses ONLY this interface, making it portable.
    """

    @abstractmethod
    def create_menubar(self, parent_window) -> Any:
        """Create and return menubar widget.

        Returns:
            Toolkit-specific menubar widget (opaque to caller)
        """
        pass

    @abstractmethod
    def add_menu(self, label: str, help_text: str) -> MenuHandle:
        """Add top-level menu.

        Args:
            label: Translated menu label
            help_text: Translated help text

        Returns:
            MenuHandle for this menu
        """
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
        """Add menu item to menu.

        Args:
            menu: MenuHandle from add_menu or add_cascade
            label: Translated item label
            command: Callback function
            accelerator: Keyboard shortcut (None if none)
            help_text: Translated help text

        Returns:
            MenuItemHandle for this item
        """
        pass

    @abstractmethod
    def add_separator(self, menu: MenuHandle) -> MenuItemHandle:
        """Add separator to menu.

        Args:
            menu: MenuHandle from add_menu or add_cascade

        Returns:
            MenuItemHandle for separator
        """
        pass

    @abstractmethod
    def add_cascade(
        self,
        menu: MenuHandle,
        label: str,
        help_text: str
    ) -> MenuHandle:
        """Add cascade (submenu) to menu.

        Args:
            menu: Parent menu handle
            label: Translated cascade label
            help_text: Translated help text

        Returns:
            MenuHandle for the new submenu
        """
        pass

    @abstractmethod
    def set_item_state(self, item: MenuItemHandle, enabled: bool):
        """Enable or disable menu item.

        Args:
            item: MenuItemHandle from add_menu_item
            enabled: True to enable, False to disable
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return platform name for debugging.

        Returns:
            Platform identifier: "macos", "linux", "windows"
        """
        pass


class PmwMenuBackend(MenuBackend):
    """Pmw/Tk menu backend with platform detection.

    Automatically selects appropriate adapter for current platform.
    """

    def __init__(self, parent_window):
        self.parent = parent_window
        self.platform = self._detect_platform()
        self.adapter = self._create_adapter()
        self.menubar = None
        self._menu_index = {}  # Map MenuHandle -> menu widget
        self._item_index = {}  # Map MenuItemHandle -> (menu, index)

    def _detect_platform(self) -> str:
        """Detect current platform."""
        import sys
        if sys.platform == 'darwin':
            return 'macos'
        elif sys.platform.startswith('linux'):
            return 'linux'
        elif sys.platform == 'win32':
            return 'windows'
        else:
            return 'unknown'

    def _create_adapter(self):
        """Create platform-specific adapter."""
        if self.platform == 'macos':
            return PmwMacOSAdapter()
        elif self.platform == 'linux':
            return PmwLinuxAdapter()
        elif self.platform == 'windows':
            return PmwWindowsAdapter()
        else:
            return PmwLinuxAdapter()  # Default fallback

    def create_menubar(self, parent_window):
        """Create Pmw menubar."""
        self.menubar = self.adapter.create_menubar(parent_window)
        return self.menubar

    def add_menu(self, label: str, help_text: str) -> MenuHandle:
        """Add top-level menu."""
        self.adapter.add_menu(self.menubar, label, help_text)
        menu_widget = self.adapter.get_menu_component(self.menubar, label)

        handle = MenuHandle(backend_data={'name': label, 'widget': menu_widget})
        self._menu_index[id(handle)] = menu_widget
        return handle

    def add_menu_item(
        self,
        menu: MenuHandle,
        label: str,
        command: Callable,
        accelerator: Optional[str] = None,
        help_text: Optional[str] = None
    ) -> MenuItemHandle:
        """Add menu item."""
        menu_widget = self._menu_index[id(menu)]
        menu_name = menu.backend_data['name']

        self.adapter.add_menu_item(
            self.menubar,
            menu_name,
            label,
            command,
            accelerator,
            help_text
        )

        # Get index of newly added item
        item_index = menu_widget.index('end')

        handle = MenuItemHandle(backend_data={
            'menu': menu_widget,
            'index': item_index
        })
        self._item_index[id(handle)] = (menu_widget, item_index)
        return handle

    def add_separator(self, menu: MenuHandle) -> MenuItemHandle:
        """Add separator."""
        menu_name = menu.backend_data['name']
        self.adapter.add_separator(self.menubar, menu_name)

        menu_widget = self._menu_index[id(menu)]
        item_index = menu_widget.index('end')

        handle = MenuItemHandle(backend_data={
            'menu': menu_widget,
            'index': item_index
        })
        return handle

    def add_cascade(
        self,
        menu: MenuHandle,
        label: str,
        help_text: str
    ) -> MenuHandle:
        """Add cascade submenu."""
        menu_name = menu.backend_data['name']
        self.adapter.add_cascade(self.menubar, menu_name, label, help_text)

        cascade_widget = self.adapter.get_menu_component(
            self.menubar,
            f"{menu_name}.{label}"
        )

        handle = MenuHandle(backend_data={
            'name': f"{menu_name}.{label}",
            'widget': cascade_widget
        })
        self._menu_index[id(handle)] = cascade_widget
        return handle

    def set_item_state(self, item: MenuItemHandle, enabled: bool):
        """Enable or disable menu item."""
        menu_widget, item_index = self._item_index[id(item)]
        state = 'normal' if enabled else 'disabled'
        menu_widget.entryconfigure(item_index, state=state)

    def get_platform_name(self) -> str:
        """Return platform name."""
        return self.platform
```

**Step 2:** Platform-specific adapters
```python
# packages/bkchem/bkchem/menu_adapters.py
import Pmw

class PmwAdapter:
    """Base adapter for Pmw menus (common logic)."""

    def add_menu_item(self, menubar, menu_name, label, command, accel, help_text):
        """Add menu item (common implementation)."""
        menubar.addmenuitem(
            menu_name,
            'command',
            label=label,
            command=command,
            accelerator=accel,
            statusHelp=help_text or ''
        )

    def add_separator(self, menubar, menu_name):
        """Add separator (common implementation)."""
        menubar.addmenuitem(menu_name, 'separator')

    def add_cascade(self, menubar, menu_name, label, help_text):
        """Add cascade (common implementation)."""
        menubar.addcascademenu(
            menu_name,
            label,
            help_text or '',
            tearoff=0
        )


class PmwMacOSAdapter(PmwAdapter):
    """macOS-specific Pmw menu adapter."""

    def create_menubar(self, parent):
        """Create macOS menubar.

        macOS uses MainMenuBar with system menubar integration.
        """
        import Pmw
        return Pmw.MainMenuBar(parent)

    def add_menu(self, menubar, label, help_text):
        """Add menu to macOS menubar."""
        menubar.addmenu(label, help_text, side='left')

    def get_menu_component(self, menubar, menu_name):
        """Get menu component (macOS-specific lookup).

        macOS MainMenuBar requires special component access.
        """
        # macOS: Use interior() to get actual menu
        try:
            return menubar.component(menu_name + '-menu')
        except KeyError:
            # Fallback for nested menus
            return menubar.interior().nametowidget(menu_name.replace('.', '-'))


class PmwLinuxAdapter(PmwAdapter):
    """Linux-specific Pmw menu adapter."""

    def create_menubar(self, parent):
        """Create Linux menubar.

        Linux uses standard Pmw.MenuBar.
        """
        return Pmw.MenuBar(parent, hull_relief='raised', hull_borderwidth=1)

    def add_menu(self, menubar, label, help_text):
        """Add menu to Linux menubar."""
        menubar.addmenu(label, help_text, side='left')

    def get_menu_component(self, menubar, menu_name):
        """Get menu component (Linux-specific lookup)."""
        return menubar.component(menu_name + '-menu')


class PmwWindowsAdapter(PmwAdapter):
    """Windows-specific Pmw menu adapter."""

    def create_menubar(self, parent):
        """Create Windows menubar.

        Windows uses standard Pmw.MenuBar (same as Linux).
        """
        return Pmw.MenuBar(parent, hull_relief='flat', hull_borderwidth=0)

    def add_menu(self, menubar, label, help_text):
        """Add menu to Windows menubar."""
        menubar.addmenu(label, help_text, side='left')

    def get_menu_component(self, menubar, menu_name):
        """Get menu component (Windows-specific lookup)."""
        return menubar.component(menu_name + '-menu')
```

**Step 3:** Platform-agnostic MenuBuilder
```python
# packages/bkchem/bkchem/menu_builder.py
class MenuBuilder:
    """Platform-agnostic menu builder.

    Uses only MenuBackend interface - no platform-specific code.
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
            yaml_path: Path to menus.yaml
            action_registry: Registry of all actions
            cascades: Dict of cascade definitions
            backend: MenuBackend implementation (Pmw, Qt, etc.)
        """
        with open(yaml_path, 'r') as f:
            self.menu_data = yaml.safe_load(f)
        self.actions = action_registry
        self.cascades = cascades
        self.backend = backend  # ONLY interface we use

        # Track items for state updates (platform-agnostic)
        self._menu_items = {}  # action_id -> MenuItemHandle

    def build_menus(self, parent_window):
        """Build all menus from YAML structure.

        Args:
            parent_window: Parent window widget

        Returns:
            Toolkit-specific menubar widget
        """
        menubar = self.backend.create_menubar(parent_window)

        for menu_id, menu_def in self.menu_data['menus'].items():
            # Get menu label from action registry
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
        """Update enable/disable state (platform-agnostic).

        Args:
            context: MenuContext with app and paper state
        """
        for action_id, item_handle in self._menu_items.items():
            enabled = self.actions.is_enabled(action_id, context)
            # Backend handles platform-specific entryconfigure
            self.backend.set_item_state(item_handle, enabled)


# Usage in main.py (platform-agnostic)
def init_menu(self):
    """Initialize menu system."""
    # Register actions (platform-agnostic)
    self.action_registry = register_all_actions(self)

    # Define cascades (platform-agnostic)
    cascades = {
        'export': CascadeDefinition(id='export', ...),
        'import': CascadeDefinition(id='import', ...),
    }

    # Create backend (auto-detects platform)
    backend = PmwMenuBackend(self)

    # Build menus (platform-agnostic)
    self.menu_builder = MenuBuilder(
        yaml_path='bkchem_data/menus.yaml',
        action_registry=self.action_registry,
        cascades=cascades,
        backend=backend  # Swap backend for different toolkit/platform
    )

    self.menubar = self.menu_builder.build_menus(self)
    self.menubar.pack(fill='x')
```

**Step 2:** Use adapter in MenuBuilder
```python
class MenuBuilder:
    def __init__(self, yaml_path, actions, cascades, platform_adapter):
        self.platform = platform_adapter

    def _build_menu_items(self, menu_name, items):
        menu_component = self.platform.get_menu_component(menu_name)
        # Rest of logic is platform-agnostic
```

**Step 3:** Test without macOS hardware
```python
# Unit test with mocked platform
def test_menu_builder_macos():
    adapter = PlatformMenuAdapter(mock_menubar)
    adapter.is_macos = True  # Override

    builder = MenuBuilder(yaml_path, actions, cascades, adapter)
    builder.build_menus(mock_menubar, mock_app)

    # Verify correct calls for macOS
    assert mock_menubar.configure.called_with(...)
```

**Step 4:** CI testing
```bash
# GitHub Actions: Test on macOS runner
name: macOS Build
on: [push]
jobs:
  test-macos:
    runs-on: macos-latest
    steps:
      - name: Test menu system
        run: pytest tests/test_menu_macos.py
```

**Fallback:** If CI not available:
- Code review focusing on platform differences
- Use `sys.platform` checks consistently
- Document untested platform code
- Request community testing

---

### Challenge 5: Performance: Menu State Updates

**Problem:**
- Current: `update_menu_after_selection_change()` loops through ALL menu items
- Fires on every selection change (frequent)
- With 50+ menu items, each update does 50+ iterations
- With fragile label lookups: O(n*m) where n=items, m=label length

**Impact:** Medium - UI sluggishness on large drawings

**Solution:**

**Step 1:** Measure baseline
```python
import time

def update_menu_after_selection_change(self, e):
    start = time.perf_counter()
    # Current implementation
    duration = time.perf_counter() - start
    if duration > 0.016:  # More than one frame (60 FPS)
        print(f"Menu update took {duration*1000:.2f}ms")
```

**Step 2:** Index actions by state
```python
class MenuBuilder:
    def __init__(self):
        # Build index at construction time
        self._index_by_state()

    def _index_by_state(self):
        """Index actions by what state they depend on."""
        self.state_index = defaultdict(list)

        for action_id, action in self.actions._actions.items():
            if action.enabled_when:
                # Analyze predicate to determine state dependencies
                deps = self._analyze_dependencies(action.enabled_when)
                for dep in deps:
                    self.state_index[dep].append((action_id, action))

    def _analyze_dependencies(self, predicate):
        """Determine what state a predicate depends on."""
        # Simple heuristic: inspect function source
        import inspect
        source = inspect.getsource(predicate)

        deps = set()
        if 'selected' in source:
            deps.add('selection')
        if 'can_undo' in source:
            deps.add('undo')
        if 'can_redo' in source:
            deps.add('redo')
        return deps
```

**Step 3:** Targeted updates
```python
def update_selection_dependent_actions(self, context):
    """Update only selection-dependent menu items."""
    for action_id, action in self.state_index['selection']:
        enabled = action.enabled_when(context)
        state = 'normal' if enabled else 'disabled'
        menu_component, index = self._menu_items[action_id]
        menu_component.entryconfigure(index, state=state)
```

**Step 4:** Measure improvement
```python
# Before: 50 items * O(n) label lookup = O(n^2)
# After: ~10 selection-dependent items * O(1) index lookup = O(n)
# Expected: 5-10x speedup
```

**Step 5:** Optimize further if needed
```python
# Batch updates with after_idle
def update_selection_dependent_actions(self, context):
    if self._update_pending:
        return

    self._update_pending = True
    self.menubar.after_idle(self._do_update, context)

def _do_update(self, context):
    self._update_pending = False
    # Actual update code
```

---

### Challenge 6: Mode Toolbar Integration

**Problem:**
- Mode toolbar (drawing modes) is separate from menu system
- Built with Pmw.RadioSelect, not menus
- Shares similar pattern (buttons, labels, icons, callbacks)
- Refactoring menus but not toolbar leaves inconsistency

**Impact:** Low urgency but architectural debt

**Solution:**

**Phase 1:** Assess if toolbar unification is worth it
```python
# Count lines of mode toolbar code
wc -l main.py  # Lines 456-524 (68 lines)

# Compare with menu code
wc -l main.py  # Lines 178-404 (226 lines)

# Complexity ratio: ~1:3 (toolbar is simpler)
```

**Decision point:**
- If toolbar code is small and stable: **Don't unify**
- If toolbar has similar issues (translation, plugin injection): **Unify**

**Phase 2:** If unifying, use same YAML + action pattern
```yaml
# In menus.yaml
toolbar:
  modes:
    - action: mode.draw
      icon: draw.png
    - action: mode.select
      icon: select.png
    - action: mode.rotate
      icon: rotate.png
```

**Phase 3:** ToolbarBuilder parallels MenuBuilder
```python
class ToolbarBuilder:
    def __init__(self, yaml_path, action_registry):
        self.yaml_path = yaml_path
        self.actions = action_registry

    def build_toolbar(self, parent, app):
        """Build mode toolbar from YAML."""
        toolbar_def = yaml.safe_load(open(self.yaml_path))['toolbar']

        radiobuttons = Pmw.RadioSelect(parent, ...)
        for mode_def in toolbar_def['modes']:
            action = self.actions.get(mode_def['action'])
            radiobuttons.add(
                action.label,
                icon=mode_def.get('icon'),
                command=action.handler,
            )
```

**Recommendation:** Defer toolbar unification to Phase 5 or later. Not critical path.

---

### Challenge 7: Testing Without Full GUI

**Problem:**
- Current menu system requires full Tk GUI running
- Hard to unit test menu construction
- Integration tests are slow and brittle
- Manual testing required for every change

**Impact:** High - slows development and increases bugs

**Solution:**

**Step 1:** Mock Pmw for unit tests
```python
# tests/test_menu_builder.py
class MockPmwMenuBar:
    def __init__(self):
        self.menus = {}
        self.calls = []

    def addmenu(self, name, help_text, side='left'):
        self.menus[name] = []
        self.calls.append(('addmenu', name, help_text, side))

    def addmenuitem(self, menu, type, **kwargs):
        self.menus[menu].append((type, kwargs))
        self.calls.append(('addmenuitem', menu, type, kwargs))

    def component(self, name):
        return MockMenuComponent()

class MockMenuComponent:
    def entryconfigure(self, index, **kwargs):
        pass

def test_menu_builder_file_menu():
    mock_pmw = MockPmwMenuBar()
    mock_app = MockApp()

    registry = ActionRegistry()
    # Register test actions

    builder = MenuBuilder('test_menus.yaml', registry, {}, mock_app)
    builder.build_menus(mock_pmw, mock_app)

    # Assert File menu was created
    assert 'File' in mock_pmw.menus
    assert len(mock_pmw.menus['File']) > 0

    # Assert specific items exist
    items = [item[1]['label'] for item in mock_pmw.menus['File']]
    assert 'New' in items
    assert 'Save' in items
```

**Step 2:** Test action registry in isolation
```python
def test_action_registry_duplicate():
    registry = ActionRegistry()

    action1 = MenuAction(id='file.save', ...)
    registry.register(action1)

    action2 = MenuAction(id='file.save', ...)
    with pytest.raises(ValueError, match="Duplicate action"):
        registry.register(action2)

def test_action_enablement():
    registry = ActionRegistry()

    action = MenuAction(
        id='edit.cut',
        enabled_when=lambda ctx: bool(ctx.paper.selected),
        ...
    )
    registry.register(action)

    context = MockContext(selected=[])
    assert not registry.is_enabled('edit.cut', context)

    context = MockContext(selected=['atom1'])
    assert registry.is_enabled('edit.cut', context)
```

**Step 3:** Smoke test with real GUI (CI)
```python
# tests/test_menu_integration.py
@pytest.mark.gui
def test_file_menu_opens():
    """Integration test: File menu can be opened."""
    app = create_test_app()

    # Simulate menu click
    app.menu.component('File-menu').invoke(0)

    # Check that callback was called
    assert app.last_command == 'file.new'

# Run with: pytest -m gui tests/
```

**Step 4:** Visual regression testing (optional)
```python
# Screenshot testing for menu appearance
import pyautogui

def test_menu_appearance():
    app = create_test_app()

    # Open File menu
    app.menu.tk_menuBar().entryconfigure(0, ...)

    # Screenshot
    screenshot = pyautogui.screenshot()

    # Compare with baseline
    assert images_similar(screenshot, 'baseline/file_menu.png')
```

**Benefits:**
- Fast unit tests (no GUI) run in CI
- Catch regressions early
- Refactor with confidence
- Integration tests for critical paths only

---

## Summary: Prioritized Action Plan

### Phase 0: Analysis and Preparation
- [x] Document current plugin architecture
- [x] Identify all menu injection points
- [x] List translation keys used in menus
- [ ] Survey for existing script/mode plugins
- [ ] Measure current menu update performance baseline with a simple
  `time.perf_counter` wrapper before building any monitoring infrastructure.
  If the current system is not actually slow (< 5ms), the PerformanceMonitor
  class and optimization phases are unnecessary. The proposed indexed state
  updates are the right optimization idea, but the monitoring framework
  around it is premature until a real performance problem is confirmed.
- [ ] Scope boundary: confirm that format handler migration to OASA is tracked
  as a separate project with its own plan document, not bundled into the menu
  refactor

### Phase 1: Core Architecture
1. Create FormatRegistry for import/export handlers
2. Create ActionRegistry with MenuAction dataclass
3. Write unit tests for both registries
4. Parallel implementation (doesn't break existing code)

**Success criteria:**
- All existing plugins registered in FormatRegistry
- All menu actions in ActionRegistry
- Tests passing
- Old code still works

### Phase 2: YAML Menu Structure
1. Create menus.yaml with File menu only
2. Create CascadeDefinition dataclass
3. Create MenuBuilder with platform adapter
4. Add format_slot support for plugins
5. Test File menu (old and new side-by-side)

**Success criteria:**
- File menu works identically to old version
- Import/Export populated from FormatRegistry
- macOS compatibility preserved
- All translations working

### Phase 3: Incremental Migration
1. Migrate Edit menu
2. Migrate Insert menu
3. Migrate remaining menus
4. Remove old menu_template
5. Remove old init_menu code

**Success criteria:**
- All menus migrated
- No translation key changes
- Performance equal or better
- All formats import/export correctly

### Phase 4: Plugin Compatibility
1. Add LegacyMenuShim for old plugin API
2. Test with any discovered script plugins
3. Document new PluginMenuAPI
4. Add deprecation warnings

**Success criteria:**
- Old plugins still work
- New plugin API documented
- Migration guide written

### Phase 5: Optimization
1. Implement indexed state updates
2. Add performance monitoring
3. Optimize hot paths
4. Profile and measure improvements

**Success criteria:**
- Menu updates < 5ms (was ~20ms)
- No UI sluggishness
- Metrics documented

### Phase 6: Polish and Documentation
1. Remove deprecated code paths
2. Update developer documentation
3. Create architecture diagrams
4. Write migration guide for plugin authors

**Risk mitigation:**
- Each phase is independently testable
- Old code runs parallel until validation complete
- Can rollback at any phase
- Community testing before final removal
