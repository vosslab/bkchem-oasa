# Modular Menu Function Architecture

## Overview

This document defines the architecture for **modular built-in menu functions** (not "plugins") that provide extensibility without security risks.

## Core Principle

**Menu functions are modular built-in code, not plugins.**
- Built-in: Shipped with BKChem, not loaded from arbitrary files
- Modular: Clean interfaces, can be enabled/disabled
- Type-safe: Python imports, not exec()
- Discoverable: Registered in action registry

## Current State Analysis

### Category 1: Import/Export Format Handlers

**Current location:** `packages/bkchem/bkchem/plugins/*.py`

**Examples:**
- CML, CML2, CDXML (chemistry formats)
- molfile, SMILES, InChI (standard formats)
- PDF, PNG, SVG, PS (renderers)

**Recommendation:** **Move to OASA backend**

These are chemistry codecs, not GUI functionality:

```python
# New location: packages/oasa/oasa/formats/
oasa/
  formats/
    __init__.py          # FormatRegistry
    cml.py              # CMLCodec
    molfile.py          # MolfileCodec
    smiles.py           # SMILESCodec
    cdxml.py            # CDXMLCodec
```

**Benefits:**
- OASA is standalone (CLI tools can use formats)
- Clear separation: OASA = data, BKChem = UI
- No plugin loader needed
- Standard Python imports

### Category 2: Addons (Chemistry Tools)

**Current location:** `packages/bkchem/addons/*.py` + `*.xml`

**Examples:**
- `angle_between_bonds.py` - Measure bond angles
- `text_to_group.py` - Convert text atoms to groups
- `red_aromates.py` - Highlight aromatic bonds
- `fetch_from_webbook.py` - Fetch NIST data
- `fragment_search.py` - Search for fragments
- `mass_scissors.py` - Mass-related tool
- `animate_undo.py` - Undo animation

**Current architecture (PROBLEMATIC):**
```python
# XML manifest with translations
<plugin>
  <meta>
    <description lang="en">Measures angle between two selected bonds.</description>
  </meta>
  <source>
    <file>angle_between_bonds.py</file>
    <menu-text lang="en">Angle between bonds</menu-text>
  </source>
</plugin>

# Python file with main() function
def main(app):
    # Direct access to app.paper, app.paper.selected, etc.
    # exec() loads this with no sandboxing
```

**Problems:**
1. **Security:** `exec()` with full app access
2. **Complexity:** XML manifest for simple tools
3. **Tight coupling:** Direct manipulation of app internals
4. **Hard to test:** Requires full GUI
5. **No type safety:** Loaded as strings, not imported

**Recommendation:** **Convert to modular built-in chemistry tools**

Two options:

#### Option A: Move chemistry logic to OASA backend

For tools that are pure chemistry (no GUI):
```python
# New location: packages/oasa/oasa/analysis/
oasa/
  analysis/
    __init__.py
    geometry.py      # angle_between_bonds -> measure_bond_angle()
    aromaticity.py   # red_aromates -> detect_aromatic_bonds()
    fragments.py     # fragment_search -> find_substructure()
```

BKChem GUI just calls OASA:
```python
# In BKChem menu action
def measure_bond_angle_action(app):
    """Menu action: Measure angle between two selected bonds."""
    bonds = [b for b in app.paper.selected if b.object_type == "bond"]

    if len(bonds) != 2:
        app.show_message("Select exactly 2 bonds")
        return

    # Convert BKChem bonds to OASA bonds
    oasa_bonds = [bond.to_oasa() for bond in bonds]

    # Call OASA backend (pure chemistry, no GUI)
    angle_degrees = oasa.analysis.geometry.measure_bond_angle(
        oasa_bonds[0],
        oasa_bonds[1]
    )

    # GUI displays result
    app.paper.new_text(x, y, text=f"{angle_degrees:.2f} degrees").draw()
    app.show_message(f"Angle: {angle_degrees:.2f} degrees")
```

#### Option B: Keep as BKChem GUI tools

For tools that are GUI-specific:
```python
# New location: packages/bkchem/bkchem/tools/
bkchem/
  tools/
    __init__.py
    geometry.py      # MeasureBondAngleTool
    conversion.py    # TextToGroupTool
    visual.py        # HighlightAromaticsTool
    fetchers.py      # FetchFromWebbookTool
```

**Key changes:**
1. **No XML manifests** - metadata in Python
2. **No exec()** - standard imports
3. **Tool interface** - clean API contract
4. **Type-safe** - proper classes, type hints

## Proposed Architecture: Modular Built-In Tools

### 1. Tool Interface

```python
# packages/bkchem/bkchem/tools/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Any

@dataclass
class ToolMetadata:
    """Tool metadata (replaces XML manifest)."""
    id: str                          # "measure_bond_angle"
    name_key: str                    # Translation key: "Angle between bonds"
    description_key: str             # Translation key for tooltip
    category: str                    # "analysis", "conversion", "visual", etc.
    icon: Optional[str] = None       # Icon filename
    requires_selection: bool = False # Tool needs selection
    selection_types: List[str] = None # ["bond", "atom", "molecule"]

    @property
    def name(self) -> str:
        """Return translated name."""
        return _(self.name_key)

    @property
    def description(self) -> str:
        """Return translated description."""
        return _(self.description_key)


class Tool(ABC):
    """Base class for all chemistry tools.

    Tools are modular built-in functions that operate on
    the current drawing. They have clean interfaces and
    can be tested independently.
    """

    def __init__(self, app):
        """Initialize tool with app reference.

        Args:
            app: BKChem application instance
        """
        self.app = app

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return tool metadata."""
        pass

    def can_run(self) -> tuple[bool, Optional[str]]:
        """Check if tool can run with current selection.

        Returns:
            (can_run, error_message)
            If can_run is False, error_message explains why.
        """
        if self.metadata.requires_selection:
            if not self.app.paper.selected:
                return False, _("No objects selected")

            if self.metadata.selection_types:
                selected_types = {obj.object_type for obj in self.app.paper.selected}
                if not selected_types & set(self.metadata.selection_types):
                    types_str = ", ".join(self.metadata.selection_types)
                    return False, _(f"Select {types_str} objects")

        return True, None

    @abstractmethod
    def run(self) -> Any:
        """Run the tool.

        Returns:
            Tool-specific result (or None)
        """
        pass


class ToolRegistry:
    """Registry of all chemistry tools."""

    def __init__(self):
        self._tools = {}

    def register(self, tool_class: type[Tool]):
        """Register tool class.

        Args:
            tool_class: Tool subclass

        Raises:
            ValueError: If tool ID already registered
        """
        # Instantiate to get metadata
        temp = tool_class(None)
        tool_id = temp.metadata.id

        if tool_id in self._tools:
            raise ValueError(f"Duplicate tool ID: {tool_id}")

        self._tools[tool_id] = tool_class

    def get_tool(self, tool_id: str, app) -> Tool:
        """Get tool instance by ID.

        Args:
            tool_id: Tool identifier
            app: BKChem app instance

        Returns:
            Tool instance

        Raises:
            KeyError: If tool not found
        """
        if tool_id not in self._tools:
            raise KeyError(f"Tool not found: {tool_id}")

        return self._tools[tool_id](app)

    def list_tools(self, category: Optional[str] = None) -> List[ToolMetadata]:
        """List all registered tools.

        Args:
            category: Filter by category (None for all)

        Returns:
            List of ToolMetadata
        """
        tools = []
        for tool_class in self._tools.values():
            temp = tool_class(None)
            if category is None or temp.metadata.category == category:
                tools.append(temp.metadata)
        return tools


# Global registry
default_registry = ToolRegistry()
```

### 2. Example Tool Implementation

```python
# packages/bkchem/bkchem/tools/geometry.py
"""Geometry analysis tools."""
from .base import Tool, ToolMetadata, default_registry
import oasa.analysis.geometry


class MeasureBondAngleTool(Tool):
    """Measure angle between two selected bonds."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            id='measure_bond_angle',
            name_key='Angle between bonds',
            description_key='Measures angle between two selected bonds',
            category='analysis',
            requires_selection=True,
            selection_types=['bond'],
        )

    def can_run(self) -> tuple[bool, Optional[str]]:
        """Check if exactly 2 bonds selected."""
        can_run, error = super().can_run()
        if not can_run:
            return can_run, error

        bonds = [b for b in self.app.paper.selected if b.object_type == "bond"]
        if len(bonds) != 2:
            return False, _("Select exactly 2 bonds")

        return True, None

    def run(self) -> float:
        """Measure and display bond angle."""
        # Get selected bonds
        bonds = [b for b in self.app.paper.selected if b.object_type == "bond"]

        # Use OASA backend for chemistry logic
        oasa_bonds = [bond.to_oasa() for bond in bonds]
        angle_degrees = oasa.analysis.geometry.measure_bond_angle(
            oasa_bonds[0],
            oasa_bonds[1]
        )

        # Display result (GUI logic stays in tool)
        x = sum(b.atom1.x + b.atom2.x for b in bonds) / 4
        y = sum(b.atom1.y + b.atom2.y for b in bonds) / 4
        self.app.paper.new_text(x, y, text=f"{angle_degrees:.2f} deg").draw()

        # Log result
        self.app.show_message(f"Angle: {angle_degrees:.2f} degrees")

        return angle_degrees


# Register tool
default_registry.register(MeasureBondAngleTool)
```

### 3. Tool Categories and Organization

```python
# packages/bkchem/bkchem/tools/__init__.py
"""Chemistry tools - modular built-in functionality."""
from .base import Tool, ToolMetadata, ToolRegistry, default_registry

# Import all tool modules to trigger registration
from . import geometry     # MeasureBondAngleTool
from . import conversion   # TextToGroupTool
from . import visual       # HighlightAromaticsTool
from . import fetchers     # FetchFromWebbookTool
from . import editing      # MassScissorsTool, etc.

__all__ = ['Tool', 'ToolMetadata', 'ToolRegistry', 'default_registry']
```

**Tool categories:**
- `analysis` - Measurement and analysis tools
- `conversion` - Convert between representations
- `visual` - Visual highlighting and display
- `fetchers` - Fetch data from external sources
- `editing` - Bulk editing operations

### 4. Menu Integration

Tools automatically populate the Tools menu:

```yaml
# In menus.yaml
menus:
  tools:
    items:
      - tool_category: analysis
      - separator: true
      - tool_category: conversion
      - separator: true
      - tool_category: visual
      - separator: true
      - tool_category: fetchers
```

MenuBuilder populates from tool registry:

```python
# In menu_builder.py
def _build_menu_items(self, menu_handle, items):
    for item in items:
        if 'tool_category' in item:
            # Populate from tool registry
            category = item['tool_category']
            tools = default_registry.list_tools(category=category)

            for tool_meta in sorted(tools, key=lambda t: t.name):
                # Create action for tool
                action = MenuAction(
                    id=f'tool.{tool_meta.id}',
                    label_key=tool_meta.name_key,
                    help_key=tool_meta.description_key,
                    handler=lambda app, tid=tool_meta.id: self._run_tool(app, tid),
                )
                self.actions.register(action)

                # Add to menu
                item_handle = self.backend.add_menu_item(
                    menu_handle,
                    action.label,
                    action.handler,
                    None,  # No accelerator for tools
                    action.help_text
                )
                self._menu_items[action.id] = item_handle

def _run_tool(self, app, tool_id):
    """Run a tool from menu."""
    tool = default_registry.get_tool(tool_id, app)

    # Check if tool can run
    can_run, error = tool.can_run()
    if not can_run:
        app.show_message(error, message_type='hint')
        return

    # Run tool
    try:
        result = tool.run()
        app.paper.start_new_undo_record()
    except Exception as e:
        app.show_message(f"Tool error: {e}", message_type='error')
        import traceback
        traceback.print_exc()
```

### 5. Migration Path for Addons

Each addon follows this pattern:

**Before (addon with XML + exec):**
```
addons/
  angle_between_bonds.xml  # XML manifest
  angle_between_bonds.py   # Script with main(app)
```

**After (built-in tool):**
```python
# packages/bkchem/bkchem/tools/geometry.py
class MeasureBondAngleTool(Tool):
    @property
    def metadata(self):
        return ToolMetadata(
            id='measure_bond_angle',
            name_key='Angle between bonds',
            ...
        )

    def run(self):
        # Chemistry logic moved to OASA
        angle = oasa.analysis.geometry.measure_bond_angle(...)
        # GUI logic stays here
        self.app.paper.new_text(...)
```

**Migration checklist per addon:**
1. Extract chemistry logic -> move to OASA backend
2. Keep GUI logic -> wrap in Tool class
3. Move translations to .po file (from XML)
4. Register in tool registry
5. Add tests
6. Delete XML manifest and script file

## Benefits of This Architecture

### Compared to current addon system:

| Aspect | Current (Addons) | New (Built-In Tools) |
|--------|------------------|----------------------|
| Security | exec() with full access | Standard imports, controlled API |
| Type safety | No (strings) | Yes (classes, type hints) |
| Testing | Hard (needs GUI) | Easy (mock app) |
| Discovery | XML parsing | Tool registry |
| Translations | XML files | .po files (standard) |
| Maintenance | Scattered files | Organized modules |
| Extensibility | User scripts | Modular built-in + Python extensions |

### Compared to plugins:

| Aspect | Plugins | Built-In Tools |
|--------|---------|----------------|
| Loading | Dynamic (exec) | Static (import) |
| Trust model | Untrusted code | Trusted code (shipped) |
| API stability | Fragile (app internals) | Stable (Tool interface) |
| Error handling | None | Proper try/except |
| Undo support | Manual | Automatic (framework) |

## Future Extensibility (If Needed)

If users need custom tools, use **Python extensions** (not plugins):

```python
# User creates: ~/.bkchem/extensions/my_custom_tool.py
from bkchem.tools import Tool, ToolMetadata, default_registry

class MyCustomTool(Tool):
    @property
    def metadata(self):
        return ToolMetadata(
            id='my_custom_tool',
            name_key='My Custom Tool',
            description_key='Does something custom',
            category='custom',
        )

    def run(self):
        # Custom logic
        pass

# Auto-register
default_registry.register(MyCustomTool)
```

BKChem discovers and imports:
```python
# In main.py startup
def load_user_extensions(self):
    """Load user extensions from ~/.bkchem/extensions/"""
    ext_dir = os.path.join(get_bkchem_private_dir(), 'extensions')
    if not os.path.exists(ext_dir):
        return

    import importlib.util
    for filename in os.listdir(ext_dir):
        if filename.endswith('.py'):
            module_name = filename[:-3]
            module_path = os.path.join(ext_dir, filename)

            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            except Exception as e:
                logger.warning(f"Failed to load extension {module_name}: {e}")
```

**Benefits over exec()-based plugins:**
- Standard Python import (safer than exec)
- Clear API contract (Tool base class)
- Type checking works
- Still extensible for advanced users

## Implementation Phases

### Phase 1: Create Tool Framework
- Implement Tool base class
- Implement ToolRegistry
- Create tool categories
- Add menu integration

### Phase 2: Migrate Addons
Migrate in order of complexity:
1. `red_aromates` (simplest - just visual)
2. `angle_between_bonds` (geometry)
3. `text_to_group` (conversion)
4. `mass_scissors` (editing)
5. `fragment_search` (search)
6. `fetch_from_webbook` (external API)
7. `fetch_name_from_webbook` (external API)
8. `animate_undo` (may be removed - niche feature)

### Phase 3: OASA Backend Extraction
Move chemistry logic to OASA:
- `oasa.analysis.geometry` - bond angles, distances
- `oasa.analysis.aromaticity` - aromatic detection
- `oasa.external.nist_webbook` - NIST data fetchers
- `oasa.search.substructure` - fragment search

### Phase 4: Remove Plugin Infrastructure
- Delete plugin_support.py
- Delete XML manifests
- Delete addons directory
- Update documentation

## Summary

**Recommendation:**
1. [x] **Drop "plugins" terminology** - use "tools" for modular functions
2. [x] **Convert addons to built-in tools** - Tool base class with clean API
3. [x] **Move chemistry logic to OASA** - Backend handles data, GUI handles display
4. [x] **Remove exec()-based loading** - Use standard Python imports
5. [x] **Keep extensibility option** - Python extensions if needed (better than exec)

**Result:**
- **Security:** No exec(), no arbitrary code execution
- **Modularity:** Clean Tool interface, category-based organization
- **Maintainability:** Standard Python modules, proper tests
- **Simplicity:** ~500 lines of plugin infrastructure deleted
- **Extensibility:** Still possible via Python extensions (safer than plugins)

Menu functions are modular built-in code, not plugins.
