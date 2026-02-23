# Tkinter coupling assessment

Assessment of how deeply BKChem is coupled to tkinter, conducted 2026-02-19.
Relevant to future toolkit migration (PySide, Tauri, etc.).

## Overview

- **Total files:** 78 Python files in `packages/bkchem-app/bkchem/`
- **Total lines:** ~25,072
- **Files with tkinter imports:** 17
- **Files with Canvas drawing calls:** 14
- **Estimated tkinter-entangled lines:** ~1,000+

## File categories

### Category A: pure logic / model (no tkinter)

~50 files, ~10,000+ lines. Fully portable without modification.

| File | Lines | Role |
| --- | --- | --- |
| `molecule.py` | 1007 | Graph model for molecules |
| `bond.py` | 394 | Bond model, pure geometry/chemistry |
| `bond_cdml.py` | 137 | Bond CDML serialization |
| `bond_type_control.py` | 170 | Bond type state machine |
| `bond_render_ops.py` | 275 | Render geometry calculations |
| `undo.py` | 400 | Undo manager, pure state bookkeeping |
| `oasa_bridge.py` | 442 | OASA chemistry engine bridge |
| `dom_extensions.py` | 168 | XML DOM utilities |
| `safe_xml.py` | ~60 | XML parsing helpers |
| `data.py` | 171 | Constant tables (paper sizes, element data) |
| `config.py` | ~60 | Config constants |
| `misc.py` | 177 | General utility functions |
| `graph_vertex_mixin.py` | 172 | Graph connectivity mixin |
| `id_manager.py` | 78 | Object ID registry |
| `chem_compat.py` | 120 | ABC compatibility shim |
| `chem_protocols.py` | 420 | Protocol/ABC definitions |
| `checks.py` | ~50 | Chemistry integrity checks |
| `validator.py` | 125 | Chemistry validation |
| `CDML_versions.py` | 274 | CDML format version transforms |
| `xml_serializer.py` | ~60 | XML serialization |
| `export.py` | ~80 | Export format routing |
| `format_loader.py` | 225 | File format loader |
| `reaction.py` | ~100 | Reaction model |
| `fragment.py` | 137 | Fragment model |
| `group.py` | 384 | Group model (chemistry) |
| `queryatom.py` | 302 | Query atom (substructure) |
| `tuning.py` | ~60 | Screen tuning constants |
| `os_support.py` | 242 | OS/filesystem helpers |
| `singleton_store.py` | 140 | App-wide singletons (Store, Screen) |
| `temp_manager.py` | 154 | Template manager |
| `template_catalog.py` | 213 | Template catalog |
| `groups_table.py` | ~50 | Chemical groups table |
| `messages.py` | 131 | User-facing message strings |
| `debug.py` | ~20 | Debug utilities |
| `import_checker.py` | ~30 | Import checker |
| `pref_manager.py` | 134 | Preference manager (XML-based) |
| `actions/__init__.py` | 158 | MenuAction dataclass, ActionRegistry |
| `actions/align_actions.py` | ~70 | Alignment actions |
| `actions/chemistry_actions.py` | 158 | Chemistry actions |
| `actions/edit_actions.py` | ~80 | Edit actions |
| `actions/file_actions.py` | 95 | File actions |
| `actions/help_actions.py` | ~50 | Help actions |
| `actions/insert_actions.py` | ~60 | Insert actions |
| `actions/object_actions.py` | 83 | Object actions |
| `actions/options_actions.py` | ~60 | Options actions |
| `actions/plugins_actions.py` | ~40 | Plugin actions |
| `actions/view_actions.py` | ~60 | View actions |
| `plugins/__init__.py` | ~10 | Plugin package |
| `plugins/plugin.py` | 86 | Plugin base class |
| `plugins/gtml.py` | 288 | GTML plugin, pure output logic |

### Category B: light tkinter use (1-20 tk-specific lines)

~13 files, ~5,000 lines. Shallow coupling via `tkinter.font` for text metrics,
`tkMessageBox` for error dialogs, or a few canvas `paper.create_*` calls.
Replaceable in a day or two per file.

| File | Lines | Nature of coupling |
| --- | --- | --- |
| `special_parents.py` | 862 | `tkinter.font.Font()` for metrics; `paper.create_*` in draw/redraw |
| `marks.py` | 734 | `tkinter.font` for font metrics; `paper.create_oval/text/move/delete/lift` |
| `arrow.py` | 482 | `tkinter.font` import; `paper.create_line/move/coords` |
| `bond_drawing.py` | 275 | `paper.create_line/oval` only, thin mixin |
| `bond_display.py` | 204 | 26 `paper.` canvas calls |
| `atom.py` | 760 | All via `self.paper.create_*`, no direct tkinter imports |
| `classes.py` | 772 | `tkinter.font` for font; `paper.create_text/line/delete/move` |
| `ftext.py` | 321 | `tkinter.font.Font` for sizing; `canvas.create_text/bbox/move/delete/lift` |
| `logger.py` | 117 | One `tkinter.messagebox.showinfo` call |
| `context_menu.py` | 385 | Subclasses `tkinter.Menu`; `.add_command()`, `.post()` |
| `external_data.py` | 329 | One `bk_dialogs.PromptDialog` for data entry |
| `bkchem_app.py` | 221 | Indirect tkinter use via Store |
| `splash.py` | ~80 | Subclasses `tkinter.Toplevel` |
| `pixmaps.py` | 99 | `tkinter.PhotoImage` only |

### Category C: heavily tkinter-dependent

~15 files, ~8,000 lines. Structurally fused with tkinter. Migration requires
full rewrite or deep refactor.

#### `paper.py` (2012 lines) - critical hub

`chem_paper` inherits from `tkinter.Canvas`. Every drawing call in the entire
codebase ultimately calls methods on this Canvas subclass:
- 48 tkinter pattern matches
- `self.bind(...)` with 20+ event bindings
- `create_rectangle`, `delete`, `bbox`, `scale`, `find_withtag`,
  `find_overlapping`, `addtag_withtag`, `dtag`, `gettags`, `lift`, `lower`
- `winfo_width/height`, `winfo_rgb`, `canvasx/y`, `xview/yview`
- `config(scrollregion=...)`, `update_idletasks`
- `event_generate("<<selection-changed>>")`, clipboard ops

#### `main.py` (1639 lines) - critical hub

`BKChem` inherits from `tkinter.Tk`:
- 83 tkinter matches (Pmw replaced with ttk/bk_widgets)
- `StringVar`, `filedialog`, `.after()`, `.mainloop()`
- `.pack()`, `.grid()` geometry managers throughout

#### `modes.py` (2276 lines) - critical

All mouse/keyboard event handling:
- `event.x`, `event.y`, `event.keysym`, `event.char`, `event.num`, `event.delta`
- `tkinter.messagebox` calls

#### `dialogs.py` (1164 lines) - critical

Heaviest former Pmw user (now uses bk_dialogs/bk_widgets ttk replacements):
- `bk_dialogs.Dialog`, `bk_dialogs.Counter`, `bk_widgets.OptionMenu`,
  `bk_widgets.RadioSelect`, `bk_dialogs.TextDialog`
- `tkinter.IntVar`, `tkinter.StringVar`, `tkinter.Checkbutton`

#### `widgets.py` (533 lines) - critical

79 tkinter matches (Pmw replaced with bk_widgets):
- `ColorButton(tkinter.Button)`, `ModeButton`, tool palette buttons
- `tkinter.colorchooser`, `tkinter.filedialog`

#### Other heavily coupled files

| File | Lines | Coupling |
| --- | --- | --- |
| `edit_pool.py` | 288 | Subclasses `tkinter.Frame` |
| `interactors.py` | 485 | `bk_dialogs.PromptDialog`, `tkinter.messagebox` |
| `platform_menu.py` | 140 | Wraps `tkinter.Menu` (Pmw replaced with ttk) |
| `helper_graphics.py` | 234 | 33 canvas op matches |
| `graphics.py` | 624 | 35 canvas op matches |
| `menu_builder.py` | 189 | Uses `platform_menu.py` menu wrapper |

## Inheritance tree

The core coupling is inheritance-deep, not just import-deep:

```
tkinter.Tk       <-  BKChem          (main.py)
tkinter.Canvas   <-  chem_paper      (paper.py)
tkinter.Frame    <-  editPool        (edit_pool.py)
tkinter.Menu     <-  context_menu    (context_menu.py)
tkinter.Button   <-  ColorButton     (widgets.py)
tkinter.Toplevel <-  Splash          (splash.py)
```

The `paper` object (a Canvas subclass) is passed as `self.paper` to every
drawable object: atoms, bonds, marks, arrows, graphics. All call
`self.paper.create_line(...)`, `self.paper.move(...)`, `self.paper.delete(...)`
directly. There is no rendering abstraction layer.

## Canvas API surface

Full list of tkinter Canvas methods used throughout the codebase (230 calls
across 12 files):

`create_line`, `create_oval`, `create_rectangle`, `create_text`,
`create_polygon`, `move`, `delete`, `coords`, `bbox`, `lift`, `lower`,
`find_overlapping`, `find_withtag`, `tag_bind`, `addtag_withtag`, `dtag`,
`gettags`, `itemconfigure`, `canvasx`, `canvasy`, `xview`, `yview`,
`winfo_width`, `winfo_height`, `scrollregion`

## Font metrics

`tkinter.font.Font` is used in ~6 files for text measurements (glyph widths,
ascent, descent) that drive layout decisions like bond clipping and mark
placement: `special_parents.py`, `marks.py`, `ftext.py`, `classes.py`,
`arrow.py`.

## Migration path (future reference)

The recommended strategy for a future PySide or Tauri migration:

1. Define a `RendererProtocol` abstract interface for drawing operations
2. Make `chem_paper` satisfy the protocol today (no behavior change)
3. Build a Qt/Tauri renderer satisfying the same protocol
4. Migrate drawable objects to use the protocol, not Canvas methods directly
5. Replace `tkinter.font.Font` metrics with `QFontMetrics` or equivalent

The ~50 pure-logic files (~10,000 lines) can be reused directly.
The ~15 heavily coupled files (~8,000 lines) require full rewrite.
The single biggest task is abstracting `chem_paper` from `tkinter.Canvas`.
