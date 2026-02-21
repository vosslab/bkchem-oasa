# GUI UX review

Audit of BKChem v26.02 graphical interface, covering visual quality and
usability across the Tkinter + Pmw application.

## Summary

BKChem is a functional chemical structure editor with a mature feature set.
The interface has been modernized with YAML-driven menus, hex grid overlays,
and a ribbon-style submode toolbar. However, visual quality lags behind modern
chemistry editors due to legacy 24x24 GIF icons, flat gray theming, and
limited visual feedback. The highest-impact improvements are: upgraded icons,
undo/redo toolbar buttons, and better mode state indication.

## Methodology

- Visual inspection of the running v26.02 application on macOS (Retina display)
- Code review of all GUI modules (~46 active Python files)
- Cross-reference of YAML configuration files against runtime behavior
- Comparison with common chemistry editor conventions (ChemDraw, MarvinSketch)

---

## Visual quality findings

### V1. Icon quality and HiDPI support

**Severity: HIGH**

All toolbar icons are 24x24 GIF files from the original ~2002 codebase. On
macOS Retina displays (2x scaling), these appear blurry and pixelated.

- 95 GIF files in
  [`packages/bkchem-app/bkchem_data/pixmaps/`](../packages/bkchem-app/bkchem_data/pixmaps/)
- [`pixmaps.py`](../packages/bkchem-app/bkchem/pixmaps.py) already implements
  PNG-first loading with GIF fallback, but no PNG files existed until this
  review
- 87 SVG source files exist in
  [`pixmaps/src/`](../packages/bkchem-app/bkchem_data/pixmaps/src/) ready for
  conversion
- Missing SVG sources for some icons (undo, redo, repair submodes)

**Recommendation:** Convert all SVG sources to 32x32 PNG files. The existing
`pixmaps.py` loader will automatically prefer them over GIF.

### V2. Color palette and visual hierarchy

**Severity: MEDIUM**

The application uses a flat `#eaeaea` gray palette set via `tk_setPalette()` in
[`main.py:83`](../packages/bkchem-app/bkchem/main.py). The toolbar, submode
ribbon, canvas surround, and status bar all share the same background color,
creating no visual hierarchy between functional areas.

- Background color defined in
  [`bkchem_config.py:53`](../packages/bkchem-app/bkchem/bkchem_config.py) as
  `#eaeaea`
- Canvas paper is white, providing the only contrast
- No gradient, shadow, or border treatment separating toolbar from canvas
- Entry widget backgrounds are explicitly set to white
  ([`main.py:81`](../packages/bkchem-app/bkchem/main.py))

**Recommendation:** Add subtle 1px separator lines between the mode toolbar
(row 1), submode ribbon (row 2), and canvas area (row 4). Consider a slightly
darker toolbar background (`#e0e0e0`) to distinguish it from the canvas
surround.

### V3. Typography and text rendering

**Severity: LOW**

- Three guaranteed fonts: helvetica, courier, times
  ([`data.py`](../packages/bkchem-app/bkchem/data.py))
- macOS correctly uses native system font (San Francisco) by skipping the
  `*font` option ([`main.py:350-351`](../packages/bkchem-app/bkchem/main.py))
- Linux falls back to Adobe Helvetica ISO-10646
  ([`main.py:344`](../packages/bkchem-app/bkchem/main.py))
- Group labels in the submode ribbon use `sans-serif 8pt`
  ([`main_modes.py:55`](../packages/bkchem-app/bkchem/main_lib/main_modes.py))
- Atom labels rendered via `ftext_lib.py` support sub/superscript positioning

**Recommendation:** No urgent changes needed. Typography is adequate for a
chemistry editor.

### V4. Spacing, alignment, and layout density

**Severity: MEDIUM**

The toolbar packs 16 mode buttons horizontally with no visual grouping. Related
modes (template / biotemplate / usertemplate) sit adjacent but have no visual
distinction from unrelated modes.

- Mode buttons use `padx=0, pady=0` with `hull_relief='flat'`
  ([`main.py:473-476`](../packages/bkchem-app/bkchem/main.py))
- Submode ribbon groups are separated by 1px `#b0b0b0` vertical lines
  ([`main_modes.py:51`](../packages/bkchem-app/bkchem/main_lib/main_modes.py))
- Edit pool (text entry) appears/disappears per mode, causing layout shifts
  ([`main_modes.py:123-126`](../packages/bkchem-app/bkchem/main_lib/main_modes.py))

**Recommendation:** Add small spacing gaps between logical mode groups in the
toolbar (edit/draw, templates, chemistry tools, geometry tools). Reduce layout
shift by reserving space for the edit pool row.

### V5. Canvas rendering quality

**Severity: LOW**

Canvas rendering is adequate. Bond line width was recently increased from 1px
to 1.5px. The hex grid overlay uses subtle colors (`#E8E8E8` lines, `#BFE5D9`
dots) that do not overwhelm the drawing.

- Bond rendering uses OASA render-ops pipeline
  ([`bond_render_ops.py`](../packages/bkchem-app/bkchem/bond_render_ops.py))
- Hex grid honeycomb lines clipped to paper boundaries
  ([`grid_overlay.py`](../packages/bkchem-app/bkchem/grid_overlay.py))
- Selection handles use 9-point rectangles
  ([`helper_graphics.py`](../packages/bkchem-app/bkchem/helper_graphics.py))

**Recommendation:** No urgent changes needed.

---

## Usability findings

### U1. Mode switching and discoverability

**Severity: HIGH**

The active mode is indicated by a sunken relief with blue highlight border
(`#4a90d9`, thickness 2) on the selected toolbar button
([`main_modes.py:136-139`](../packages/bkchem-app/bkchem/main_lib/main_modes.py)).
This is a recent improvement but may still be subtle on some displays.

- 16 toolbar mode buttons (edit, draw, template, biotemplate, usertemplate,
  atom, mark, arrow, plus, text, bracket, rotate, bondalign, vector, repair,
  misc)
- Template / biotemplate / usertemplate could potentially merge into one mode
  with a source dropdown
- Draw mode has 5 submode groups which can overwhelm new users
- No mode description visible in the status bar when switching

**Recommendation:** Display the active mode name in the status bar when
switching modes. Consider merging the three template modes long-term.

### U2. Menu organization and depth

**Severity: LOW**

The menu structure is well-organized with 8 top-level menus: File, Edit,
Insert, Align, Object, View, Chemistry, Options, Help. Menus are built from
YAML configuration
([`menus.yaml`](../packages/bkchem-app/bkchem_data/menus.yaml)) with an
ActionRegistry pattern
([`action_registry.py`](../packages/bkchem-app/bkchem/actions/action_registry.py)).

- Keyboard accelerators shown but use Emacs-style notation (see U5)
- Chemistry menu provides SMILES/InChI import/export
- Recent files submenu under File
- Export/Import cascades populated dynamically from format registry

**Recommendation:** No structural changes needed.

### U3. Toolbar density and grouping

**Severity: MEDIUM**

The toolbar contains 16 mode buttons packed side-by-side with no visual
grouping. Users scanning for a specific tool must read labels or icons
sequentially.

| Group | Modes | Count |
| --- | --- | --- |
| General | edit, draw | 2 |
| Templates | template, biotemplate, usertemplate | 3 |
| Chemistry | atom, mark | 2 |
| Annotation | arrow, plus, text, bracket | 4 |
| Geometry | rotate, bondalign | 2 |
| Graphics | vector | 1 |
| Maintenance | repair, misc | 2 |

**Recommendation:** Add thin separator frames between logical groups to improve
scannability. Long-term, consider merging template/biotemplate/usertemplate.

### U4. Dialog design and consistency

**Severity: LOW**

Dialogs are implemented via Pmw.Dialog with consistent button placement. The
`dialogs.py` module contains 27+ dialog classes. Color selection uses the
standard `tkinter.colorchooser`. Scale dialog includes aspect-ratio locking.

**Recommendation:** No urgent changes needed.

### U5. Keyboard shortcuts and accessibility

**Severity: MEDIUM**

BKChem uses Emacs-style key sequences (C-x C-s for Save, C-x C-f for Load,
C-a C-t for Align Top). These are unfamiliar to most chemistry software users
who expect standard shortcuts (Ctrl+S, Ctrl+O, Ctrl+Z).

- Key sequences defined in
  [`modes_lib.py`](../packages/bkchem-app/bkchem/modes/modes_lib.py) with
  `_key_sequences` dict and `_specials_pressed` tracker
- Undo/Redo use C-z / C-S-z (standard-compatible)
- Most other shortcuts require Emacs-style multi-key sequences
- No keyboard shortcut reference dialog or cheat sheet

**Recommendation:** Keep Emacs sequences for power users but add standard
single-key alternatives where possible (Ctrl+S for save, Ctrl+O for open).
Add a keyboard shortcut reference in the Help menu.

### U6. Status bar and user feedback

**Severity: MEDIUM**

The status bar shows two fields: a message area (left, expanding) and cursor
position (right). Messages auto-clear after a calculated timeout
([`main.py:517-518`](../packages/bkchem-app/bkchem/main.py)). The menu balloon
helper sends hover text to the status bar via `statuscommand`.

- No active mode name displayed in status bar
- No undo history depth indicator
- No zoom level display
- Cursor position shows pixel coordinates, not chemistry-meaningful units

**Recommendation:** Add the current mode name and zoom level to the status bar.
Display undo stack depth when available.

### U7. Tab management

**Severity: LOW**

Multiple drawings supported via Pmw.NoteBook
([`main.py:98`](../packages/bkchem-app/bkchem/main.py)). Tabs show filename
with unsaved-change indicators. Close-tab is available via menu (C-x C-t).

**Recommendation:** No urgent changes needed.

### U8. Context menus

**Severity: LOW**

Right-click context menus are dynamically built per selected object type in
[`context_menu.py`](../packages/bkchem-app/bkchem/context_menu.py). Menus
provide object-specific actions (configure atom, change bond order, etc.).

**Recommendation:** No urgent changes needed.

---

## Prioritized recommendations

| Priority | Finding | Effort | Impact | Action |
| --- | --- | --- | --- | --- |
| HIGH | V1 Icons | Low | High | Convert SVGs to 32x32 PNGs; loader already supports PNG |
| HIGH | U1 Mode feedback | Low | High | Verify tooltips; show mode name in status bar |
| HIGH | U3 Undo/redo access | Low | High | Add undo/redo buttons to toolbar |
| MEDIUM | V2 Visual hierarchy | Low | Medium | Add separator lines between UI regions |
| MEDIUM | V4 Toolbar grouping | Low | Medium | Add separator gaps between mode groups |
| MEDIUM | U5 Keyboard shortcuts | Medium | Medium | Add standard Ctrl+key alternatives |
| MEDIUM | U6 Status bar info | Low | Medium | Show mode name and zoom in status bar |
| LOW | V3 Typography | None | Low | Adequate as-is |
| LOW | V5 Canvas quality | None | Low | Recently improved |
| LOW | U2 Menu organization | None | Low | Well structured |
| LOW | U4 Dialogs | None | Low | Consistent design |
| LOW | U7 Tab management | None | Low | Working well |
| LOW | U8 Context menus | None | Low | Working well |

---

## Low-hanging fruit: modern button feel within Tkinter

Tkinter is not a modern toolkit, but several small changes make the toolbar
feel more responsive and polished without requiring a framework migration.

### Implemented

| Technique | Effect | Effort |
| --- | --- | --- |
| Hover highlight | Buttons lighten to `#d8d8d8` on mouse enter, restore on leave | Low |
| Active mode fill | Selected mode uses `#cde4f7` light blue background instead of sunken relief | Low |
| Groove relief | Active button uses `groove` border (subtle 3D) instead of `sunken` | Low |
| Toolbar group separators | 1px `#b0b0b0` vertical lines between logical mode groups (data-driven from `modes.yaml`) | Low |
| `activebackground` tint | Button press flash uses `#d0d8e8` instead of default gray | Low |

### Additional opportunities

| Technique | Effect | Effort |
| --- | --- | --- |
| ttk themed widgets | `ttk.Button` with custom `ttk.Style` follows OS theme on macOS; gives native aqua look | Medium |
| Icon-only toolbar | Remove text labels, rely on Pmw.Balloon tooltips; reduces toolbar height | Low |
| Toolbar background band | Slightly darker toolbar frame (`#e0e0e0`) to separate from canvas surround | Low |
| 1px top/bottom separator lines | Thin `#c8c8c8` lines between toolbar and submode ribbon, ribbon and canvas | Low |
| Submode hover effects | Apply same `<Enter>`/`<Leave>` hover pattern to submode ribbon buttons | Low |
| Padding adjustment | Add `padx=2, pady=1` to mode buttons for breathing room | Low |
| Animated transitions | Use `after()` to fade hover color in/out over 100ms (limited by Tk redraw speed) | Medium |

---

## Changes implemented during this review

### Completed

- **V1 PNG icons:** Converted all 87 SVG source files to 32x32 PNG with
  32-bit RGBA and antialiased edges. Created 5 new SVG/PNG icons (undo, redo,
  repair, biotemplate, rplus). The `pixmaps.py` loader automatically prefers
  PNG over GIF. Conversion pipeline in
  [`tools/convert_svg_icons.py`](../tools/convert_svg_icons.py).
- **U3 Undo/redo toolbar buttons:** Added undo and redo buttons to the toolbar
  frame, positioned after the mode buttons with a visual separator.
- **U5 macOS Command key shortcuts:** Added macOS-specific Cmd+Z (undo),
  Cmd+Shift+Z (redo), Cmd+S (save), Cmd+Shift+A (select all) key sequence
  equivalents. Added Cmd+plus/minus/0 zoom and Cmd+G hex grid toggle to the
  canvas event bindings.
- **V4 Toolbar group separators:** Added data-driven separator positions in
  `modes.yaml` (`---` entries) with thin vertical lines between logical mode
  groups (general, templates, chemistry, annotation, geometry, graphics,
  maintenance).
- **Modern button feel:** Added hover highlight effects (`<Enter>`/`<Leave>`
  bindings), active mode fill color (`#cde4f7`), groove relief for selected
  mode, and `activebackground` tint for button press feedback.

### Deferred

- Template mode consolidation (architectural change, needs user testing)
- Status bar enhancements (mode name, zoom level display)
- Fresh screenshots (need manual GUI capture; legacy screenshots still in place)
- ttk themed widget migration (medium effort, needs compatibility testing)
