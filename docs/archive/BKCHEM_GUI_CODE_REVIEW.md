# BKChem GUI code review

## Scope

Reviewed the main GUI entry points and interaction layers:
- [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) - main application class, menu system, mode toolbar
- [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py) - drawing canvas (chem_paper class), event bindings
- [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py) - mode classes, key sequence handling
- [packages/bkchem-app/bkchem/context_menu.py](packages/bkchem-app/bkchem/context_menu.py) - right-click context menus
- [packages/bkchem-app/bkchem/interactors.py](packages/bkchem-app/bkchem/interactors.py) - user interaction dialogs
- [packages/bkchem-app/bkchem/singleton_store.py](packages/bkchem-app/bkchem/singleton_store.py) - global singleton pattern
- [packages/bkchem-app/bkchem/plugin_support.py](packages/bkchem-app/bkchem/plugin_support.py) - plugin system

## Overall quality

The GUI is functional and feature rich, but it remains tightly coupled to
application globals and direct execution of scripts. The event and mode systems
are powerful but fragile, with platform specific input handling and manual key
sequence state. The primary improvement opportunities are in separation of
concerns, hardening script execution boundaries, and stabilizing input handling.

## Findings (ordered by severity)

- High: Batch mode runs arbitrary script files with `exec` and no path
  restrictions or sandboxing. This is a direct code execution surface and it
  runs inside the GUI process with full privileges. Consider gating it behind a
  trust prompt, or moving execution to a separate process. See
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) lines
  1435-1446.
- High: Plugin execution loads and `exec`s Python scripts directly in the UI
  process, with only directory checks and a temporary sys.path mutation. There
  is no isolation, timeout, or error recovery strategy if a plugin blocks the
  event loop. See [packages/bkchem-app/bkchem/plugin_support.py](packages/bkchem-app/bkchem/plugin_support.py)
  lines 84-110.
- Medium: Global singleton state (`Store.app`, `Screen.dpi`, and other Store
  usage) is set in the GUI constructor and consumed across modules. This makes
  the GUI hard to test, encourages cross module coupling, and blurs the boundary
  between UI and model. See [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py)
  lines 69-87 and [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py)
  lines 137-165.
- Medium: Input handling is platform specific and incomplete. Mouse wheel
  bindings use Button-4 and Button-5 (Linux) while the Windows path is commented
  out, and there is no trackpad handling. This results in inconsistent zoom and
  scroll behavior across platforms. See [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py)
  lines 158-168.
- Medium: Mode key sequence handling relies on manual modifier state and a
  cleanup hack to recover from dialogs that swallow key releases. This creates
  fragile keyboard state and risks stuck modifiers when focus changes. See
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py) lines
  113-168.
- Low: Display form parsing manually encodes UTF-8 and falls back to escaping
  with broad exception handling. This can hide encoding errors and makes it hard
  to distinguish malformed input from input encoding problems. See
  [packages/bkchem-app/bkchem/interactors.py](packages/bkchem-app/bkchem/interactors.py)
  lines 187-199.

## Additional architectural findings

### Menu system architecture

The menu system (see [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) lines 178-289) uses a flat tuple-based template with an implicit schema:
- Schema: `(menu_name, type, label, accelerator, status_help, command, state_var)`
- Types include: `'menu'`, `'command'`, `'separator'`, `'cascade'`
- Menu creation loops through the template and calls Pmw methods directly
- Enable/disable logic in `update_menu_after_selection_change()` (line 1406) inspects the `state_var` field which can be:
  - A callable that returns a boolean
  - A string attribute name on the paper object
  - `None` for always-enabled items

Issues with this approach:
- No type safety: tuple position errors are not caught until runtime
- No validation: invalid menu types or missing fields cause cryptic errors
- Hard to extend: adding a new field requires updating all creation and update logic
- Testing difficulty: menus are only constructed when the GUI initializes
- String attribute lookups prevent static analysis and refactoring

### Mode system architecture

The mode system (see [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py)) implements a state machine where each mode handles mouse and keyboard events differently. Key observations:

- **Mode registration**: Modes are registered in `init_modes()` at [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) line 456, with a separate ordering list `modes_sort` (line 476) that controls toolbar button order
- **Plugin modes**: Mode plugins are dynamically imported and added to the mode registry (lines 480-493), creating a potential name collision risk
- **Submodes**: Each mode can have multiple submodes with either button-based or pulldown menu UIs (see mode toolbar creation at line 496)
- **Submode state**: The submode state is stored per mode object and copied when modes switch (see `change_mode()` at line 546)

The mode toolbar (lines 496-524) creates a `Pmw.RadioSelect` widget for each mode, with icons from `pixmaps.images` when available. Clicking a button calls `change_mode()` which:
1. Cleans up the old mode
2. Copies settings from old to new mode
3. Destroys old submode buttons
4. Creates new submode buttons for the active mode

### Key sequence handling

The key sequence system (see [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py) lines 113-168) implements Emacs-style key chords:

- **Modifier tracking**: CAMS (Control-Alt-Meta-Shift) modifiers are tracked in `_specials_pressed` dict
- **Sequence building**: Each key press appends to `_recent_key_seq` with CAMS prefix
- **Sequence matching**: Completed sequences are looked up in `_key_sequences` registry
- **Prefix matching**: Partial matches keep the sequence active for multi-key chords

Critical fragility:
- **KeyRelease events**: The cleanup logic at line 154 calls `cleanup_key_modifiers()` on every key release
- **Dialog swallowing**: Dialogs can swallow KeyRelease events, leaving modifiers stuck
- **Focus changes**: Losing focus can leave modifier state incorrect
- **Hack workaround**: The code includes explicit "ugly hack" comments about this issue

### Context menu architecture

The context menu system (see [packages/bkchem-app/bkchem/context_menu.py](packages/bkchem-app/bkchem/context_menu.py)) dynamically builds menus based on the current selection:

- **Configurable properties**: A `configurable` dict maps object types to attribute lists
- **Dynamic values**: Each attribute references a `config_values` entry with internationalized names and value lists
- **Cascade creation**: Properties become cascade submenus, values become commands
- **Object filtering**: Menu items are filtered by object type and class name
- **Command registration**: Special commands (center bond, expand group, etc.) are added conditionally

The menu is rebuilt on every right-click, which is flexible but potentially slow for large selections.

### Canvas event binding

The canvas (chem_paper class) sets up event bindings in `set_bindings()` at [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py) lines 137-163:

Platform-specific issues:
- **Linux scrolling**: Button-4 and Button-5 for mouse wheel (lines 159-160)
- **Linux zoom**: Control + Button-4/5 for zoom (lines 162-163)
- **Windows scrolling**: Commented out and marked with "hope it does not clash" (line 167)
- **No macOS trackpad**: No support for smooth scrolling or pinch-to-zoom gestures

The `add_bindings()` method at line 252 is misnamed - it does not actually add bindings, it:
- Lowers the background layer
- Lifts all objects to the top
- Clears the `_do_not_focus` temporary list
- Generates a `<<selection-changed>>` virtual event

### Template and singleton initialization

Singleton managers are initialized in `init_singletons()` at [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) lines 407-433:
- Template manager (tm): Default chemical templates
- User template manager (utm): User-created templates
- Biomolecule template manager (btm): Biomolecule templates
- Group manager (gm): Chemical group definitions
- Plugin manager: Script plugin registry

All are stored in the global `Store` class (see [packages/bkchem-app/bkchem/singleton_store.py](packages/bkchem-app/bkchem/singleton_store.py)), making them accessible anywhere but hard to test or replace.

### Plugin menu integration

Plugins are added to menus in two places:

1. **Import/Export plugins** (line 389): Loop through `self.plugins` dict and add to File > Import or File > Export cascades
2. **Script plugins** (line 324): Loop through plugin manager names and add to either a specified menu (if it exists and is translated) or to the Plugins menu

Both use `misc.lazy_apply()` to defer command execution, creating closures over plugin names.

### Recent files menu

Recent files are added dynamically in `init_preferences()` at line 442, reading from preferences `recent-file1` through `recent-file5` and adding menu items to the "Recent files" cascade. The list is updated in `_record_recent_file()` at line 1419.

## Recommended next steps

### Immediate (security and stability)

1. **Script execution boundaries**: Add trust prompts for batch scripts and plugin execution. Consider a plugin allowlist or signature verification. Move long-running operations to background threads to avoid blocking the UI.

2. **Platform input normalization**: Create a unified scroll/zoom handler that detects platform (sys.platform) and binds appropriate events:
   - macOS: `<MouseWheel>` with event.delta for trackpad
   - Linux: `<Button-4>`, `<Button-5>`
   - Windows: `<MouseWheel>` with different delta semantics
   - Add smooth scrolling support for modern trackpads

3. **Key modifier state recovery**: Replace manual modifier tracking with Tk's built-in `event.state` bitmask. Add a focus-in handler that resets modifier state to avoid stuck keys.

### Medium term (architecture cleanup)

4. **Menu system refactor**: See detailed plan in [docs/BKCHEM_GUI_MENU_REFACTOR.md](docs/BKCHEM_GUI_MENU_REFACTOR.md). Create an action registry with declarative menu definitions.

5. **Singleton dependency injection**: Start with small modules (logger, id_manager) and pass them as constructor parameters instead of accessing Store globally. Add a context object that can be passed down the call stack.

6. **Mode system cleanup**:
   - Extract mode metadata (name, icon, help text) from mode classes
   - Create a mode registry with validation
   - Prevent mode/submode name collisions with namespacing
   - Add mode lifecycle hooks (on_enter, on_exit, on_cleanup)

### Long term (testing and maintainability)

7. **Unit test harness**: Create test fixtures that can instantiate paper/mode objects without a full Tk GUI. Mock Store singletons for isolated testing.

8. **Event binding tests**: Add smoke tests that validate:
   - All menu accelerators map to actual commands
   - All key sequences in mode._key_sequences are unique
   - No duplicate event bindings on the canvas
   - Platform-specific bindings are correctly conditional

9. **Configuration validation**: Add schema validation for menu templates, mode definitions, and plugin manifests. Fail fast on startup if configuration is invalid.

10. **Documentation**: Document the mode lifecycle, key sequence format, menu template schema, and plugin API contract. Create architecture diagrams showing the initialization order and singleton dependencies.

## Review notes

- Key sequence handling: the code does not call a `cleanup_key_modifiers()` helper on
  every KeyRelease. Modifiers are cleared per-key in `key_released()`, and
  `clean_key_queue()` is called from the canvas enter/leave handlers in
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py).
- Mode switching: `copy_settings()` only copies `_specials_pressed`. Submode state
  is not copied between modes.
- Translation assets: runtime lookup uses compiled `.mo` files under
  `share/locale` or `../locale`. The repo contains `.po` sources in
  `bkchem_data/locale` that must be compiled for runtime use.
- Menu enablement: `state_var` may be a callable, a `paper` attribute name, or
  a literal state string (`'normal'` or `'disabled'`).
