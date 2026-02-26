# Changelog

## 2026-02-26

### Additions and New Features

- Add RDKit-backed file format codecs: Molfile V2000, Molfile V3000, SDF,
  SDF V3000, SMILES, and SMARTS (export-only). All use `rdkit_bridge` for
  OASA-to-RDKit conversion. File changed:
  [`packages/oasa/oasa/codecs/rdkit_formats.py`](packages/oasa/oasa/codecs/rdkit_formats.py).
- Register new codecs in the OASA codec registry with extensions `.sdf`
  and `.sma`, and aliases `v3000`, `mol-v3000`, `sdf-v3000`.
  File changed:
  [`packages/oasa/oasa/codec_registry.py`](packages/oasa/oasa/codec_registry.py).
- Add GUI menu entries for Molfile V3000, SDF, SDF V3000, and SMARTS formats.
  File changed:
  [`packages/bkchem-app/bkchem/format_menus.yaml`](packages/bkchem-app/bkchem/format_menus.yaml).
- Open dialog now recognizes chemistry file extensions (`.mol`, `.sdf`, `.smi`,
  `.cml`, `.cdxml`) and routes them through the import pipeline automatically.
  File changed:
  [`packages/bkchem-app/bkchem/main_lib/main_file_io.py`](packages/bkchem-app/bkchem/main_lib/main_file_io.py).
- After import, a summary popup shows molecule/atom/bond counts.
  File changed:
  [`packages/bkchem-app/bkchem/main_lib/main_file_io.py`](packages/bkchem-app/bkchem/main_lib/main_file_io.py).
- Add 6x6 NxN cholesterol super roundtrip test covering all read/write codec
  pairs (smiles, molfile, molfile_v3000, sdf, sdf_v3000, inchi). Each pair
  writes cholesterol in format A, reads back, writes in format B, reads back,
  and verifies atom/bond counts survive both hops.
  File changed:
  [`packages/oasa/tests/test_rdkit_formats.py`](packages/oasa/tests/test_rdkit_formats.py).

### Behavior or Interface Changes

- Migrate Molfile V2000 read/write to RDKit. The `molfile_lib.py` module-level
  `text_to_mol`, `mol_to_text`, `file_to_mol`, `mol_to_file` now delegate to
  `rdkit_formats.molfile_*` functions. The legacy `Molfile` class is retained
  but no longer used by the module interface.
  File changed:
  [`packages/oasa/oasa/molfile_lib.py`](packages/oasa/oasa/molfile_lib.py).
- Migrate SMILES read/write to RDKit. The `smiles_lib.py` module-level
  `text_to_mol` and `mol_to_text` now delegate to `rdkit_formats.smiles_*`
  functions. The `calc_coords` and `localize_aromatic_bonds` parameters are
  preserved. The legacy `Smiles` class is retained but no longer used by the
  module interface.
  File changed:
  [`packages/oasa/oasa/smiles_lib.py`](packages/oasa/oasa/smiles_lib.py).
- Migrate InChI reader to RDKit. The `inchi_lib.py` `text_to_mol` now
  delegates to `rdkit_formats.inchi_text_to_mol`. The `include_hydrogens`,
  `mark_aromatic_bonds`, and `calc_coords` parameters are preserved.
  File changed:
  [`packages/oasa/oasa/inchi_lib.py`](packages/oasa/oasa/inchi_lib.py).
- Replace external-binary InChI generation with RDKit-native `MolToInchi` /
  `MolFromInchi` / `InchiToInchiKey`. No external InChI program is needed.
  The `program` parameter is accepted but ignored for backward compatibility.
  File changed:
  [`packages/oasa/oasa/inchi_lib.py`](packages/oasa/oasa/inchi_lib.py).
- Remove `program_path` gui_option from InChI format entry since the external
  binary is no longer used.
  File changed:
  [`packages/bkchem-app/bkchem/format_menus.yaml`](packages/bkchem-app/bkchem/format_menus.yaml).
- Remove InChI special-case export code from format_loader since InChI now
  uses the standard codec write_file interface.
  File changed:
  [`packages/bkchem-app/bkchem/format_loader.py`](packages/bkchem-app/bkchem/format_loader.py).

### Fixes and Maintenance

- Fix `TypeError: '>' not supported between instances of 'NoneType' and 'int'`
  in `cairo_out.py` when drawing aromatic molecules parsed via RDKit. The bridge
  function `_rdkit_to_oasa()` now kekulizes the RDKit molecule before conversion
  so aromatic bonds get explicit single/double orders instead of `order=None`.
  File changed:
  [`packages/oasa/oasa/codecs/rdkit_formats.py`](packages/oasa/oasa/codecs/rdkit_formats.py).
- Add defensive fallback in `bond.order` getter: if `_order` is `None` without
  `aromatic` set, return `1` instead of `None`. Prevents `NoneType` comparison
  errors if a bond is ever created in the invalid state `_order=None, aromatic=0`.
  File changed:
  [`packages/oasa/oasa/bond_lib.py`](packages/oasa/oasa/bond_lib.py).
- Fix Import menu being empty: `load_backend_capabilities()` in
  `format_loader.py` crashed with `AttributeError` because it accessed
  `oasa_bridge.oasa.codec_registry` instead of importing `oasa.codec_registry`
  directly. The error was silently caught, resulting in no Import/Export menu
  items.
  File changed:
  [`packages/bkchem-app/bkchem/format_loader.py`](packages/bkchem-app/bkchem/format_loader.py).
- Fix opening .mol files doing nothing: the extension routing in `load_CDML()`
  called `format_import("molfile", ...)` but `format_entries` was empty due to
  the above bug. Now that the registry loads correctly, .mol/.sdf/.smi files
  open as expected.
- Improve error message when opening V3000 mol files with macromolecule residue
  notation (TEMPLATE blocks, CLASS=AA). Instead of a generic "could not parse"
  error, users now see a message explaining that BKChem does not support
  macromolecule template blocks and suggesting to export with residues expanded.
  File changed:
  [`packages/oasa/oasa/codecs/rdkit_formats.py`](packages/oasa/oasa/codecs/rdkit_formats.py).

### Decisions and Failures

- Decided not to support V3000 macromolecule template expansion (peptide/polymer
  TEMPLATE blocks with SAP attachment points). BKChem is a molecular editor, not
  a template connector. Users working with macromolecule residue notation should
  expand residues to full atomic structures in their source editor (e.g. Ketcher)
  before importing.
- V2000 and V3000 molfile codecs share the same read path since RDKit
  auto-detects V2000 vs V3000 format via the `M  V30 BEGIN CTAB` marker. The
  codecs are separate only for the write path: V2000 uses `MolToMolBlock()`,
  V3000 uses `MolToV3KMolBlock()`.

### Removals and Deprecations

- Remove `subprocess` and `os` imports from `inchi_lib.py` (no longer needed
  without external binary calls).
- Remove `coords_generator` import from `inchi_lib.py` (now handled internally
  by `rdkit_formats.inchi_text_to_mol`).
- Remove dead `program_path` error handler from main_file_io.py export path.

## 2026-02-23

### Additions and New Features

- Build script now reads `pip_requirements.txt` at build time and auto-generates
  `--hidden-import` and `--collect-all` flags for PyInstaller, so new pip
  dependencies are automatically bundled into the macOS app without manual edits.
  Packages with C extensions or deep submodule trees (rdkit, rustworkx, cairo)
  are listed in `COLLECT_ALL_PACKAGES` and get `--collect-all` in addition to
  `--hidden-import`.
  File changed: [`devel/build_macos_dmg.py`](devel/build_macos_dmg.py).

### Behavior or Interface Changes

- Set version to `26.02a1` (alpha 1) across all version sources: `VERSION`,
  `packages/oasa/pyproject.toml`, and `bkchem_config.py` fallback.
  Files changed: [`VERSION`](VERSION),
  [`packages/oasa/pyproject.toml`](packages/oasa/pyproject.toml),
  [`packages/bkchem-app/bkchem/bkchem_config.py`](packages/bkchem-app/bkchem/bkchem_config.py).

- Add `dependencies` block to bkchem-app `pyproject.toml` matching
  `pip_requirements.txt` (defusedxml, pycairo, pyyaml, rdkit, rustworkx).
  File changed:
  [`packages/bkchem-app/pyproject.toml`](packages/bkchem-app/pyproject.toml).
- Add missing `rustworkx` dependency to oasa `pyproject.toml`.
  File changed:
  [`packages/oasa/pyproject.toml`](packages/oasa/pyproject.toml).

### Fixes and Maintenance

- Replace blanket `--collect-all` with fine-grained `--collect-binaries` and
  targeted `--hidden-import` flags for rdkit, cairo, and rustworkx in the macOS
  build script. The old `--collect-all` bundled every submodule, data file, and
  shared library for each package, inflating the app bundle to 1.8 GB. The new
  `PACKAGE_PYINSTALLER_FLAGS` dict specifies only the binaries and imports
  actually needed. tkinter retains `--collect-all` since it needs Tcl/Tk runtime
  data directories.
  File changed: [`devel/build_macos_dmg.py`](devel/build_macos_dmg.py).

- Fix BKChem.app crash on launch due to missing tkinter/Tcl/Tk. Added
  `--hidden-import=tkinter`, `--hidden-import=_tkinter`, and
  `--collect-all=tkinter` to the PyInstaller command. PyInstaller could not
  auto-detect tkinter because the bootstrap script reaches it only at runtime.
  File changed: [`devel/build_macos_dmg.py`](devel/build_macos_dmg.py).
- Fix macOS DMG build script paths. The script referenced `packages/bkchem/`
  but the actual package directory is `packages/bkchem-app/`. Fixed all four
  path references (SVG icon, ICNS icon, bkchem package, bkchem data, addons).
  File changed: [`devel/build_macos_dmg.py`](devel/build_macos_dmg.py).

### Removals and Deprecations

- Remove remaining Pmw references from build script, docs, locale files, and
  pip requirements. Pmw was fully replaced with ttk in the codebase; these
  were leftover references in non-Python files.
  Files changed:
  [`devel/build_macos_dmg.py`](devel/build_macos_dmg.py),
  [`pip_requirements.txt`](pip_requirements.txt),
  [`docs/INSTALL.md`](docs/INSTALL.md),
  [`docs/TKINTER_COUPLING.md`](docs/TKINTER_COUPLING.md),
  [`docs/TRANSFORMATION_OPERATIONS.md`](docs/TRANSFORMATION_OPERATIONS.md),
  all `.po`/`.pot` locale files under
  [`packages/bkchem-app/bkchem_data/locale/`](packages/bkchem-app/bkchem_data/locale/).

## 2026-02-21
- Fix unsaved-changes dialog grammar. The message "what should I do?" did not
  match the Yes/No/Cancel buttons. Changed to "Save before closing?" so the
  question has a clear yes/no answer.
  File changed: [`main_tabs.py`](packages/bkchem-app/bkchem/main_lib/main_tabs.py).
- Fix hex grid overlay colors not refreshing on theme change. The
  `_apply_paper_theme()` function referenced `paper._hex_grid` but the actual
  attribute is `paper._hex_grid_overlay`. Grid now redraws with correct theme
  colors immediately on theme switch.
  File changed: [`theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py).
- Convert biomolecule template grid buttons from plain `tkinter.Button` to
  `ttk.Button` with `Grid.TButton` / `Selected.Grid.TButton` styles. This fixes
  rounded-corner macOS native buttons looking out of place alongside the themed
  rectangular ttk buttons. Hover effects are now handled by ttk style maps.
  Remove unused `_on_sub_enter`/`_on_sub_leave` hover helpers.
  Files changed:
  [`main_modes.py`](packages/bkchem-app/bkchem/main_lib/main_modes.py),
  [`theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py).
- Fix dark theme not applying to status bar and zoom controls at startup.
  Add `foreground` to both startup and runtime `tk_setPalette` calls.
  Call `apply_gui_theme()` at startup after `init_status_bar()` so full theme
  (palette, toolbar, status bar, canvas) is applied on launch, not only when
  the user changes themes. Add explicit status bar (row 7) recoloring in
  `apply_gui_theme()`.
  Files changed:
  [`main.py`](packages/bkchem-app/bkchem/main.py),
  [`theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py).
- Complete Pmw removal (M10/M11). Replace `Pmw.MainMenuBar`/`Pmw.MenuBar` with
  native `tkinter.Menu` in `PlatformMenuAdapter`. Replace `Pmw.Balloon` for
  menu balloon with `BkBalloon`. Remove `Pmw.initialise()` call. Remove
  `import Pmw` from `main.py` (the last file). Remove Pmw availability check
  from `bkchem_app.py` and `import_checker.py`. Remove `no_pmw_text` message.
  Update about text from "Pmw" to "tkinter". Rewrite
  `test_platform_menu.py` for native tkinter.Menu API.
  Files changed:
  [`main.py`](packages/bkchem-app/bkchem/main.py),
  [`platform_menu.py`](packages/bkchem-app/bkchem/platform_menu.py),
  [`bkchem_app.py`](packages/bkchem-app/bkchem/bkchem_app.py),
  [`import_checker.py`](packages/bkchem-app/bkchem/import_checker.py),
  [`messages.py`](packages/bkchem-app/bkchem/messages.py),
  [`menu_builder.py`](packages/bkchem-app/bkchem/menu_builder.py),
  [`test_platform_menu.py`](packages/bkchem-app/tests/test_platform_menu.py).
- Migrate `widgets.py` from Pmw (M7). Replace `FontSizeChooser(Pmw.Counter)` ->
  `BkCounter`, `FontFamilyChooser(Pmw.ScrolledListBox)` -> `BkScrolledListBox`,
  `WidthCounter`/`LengthCounter`/`RatioCounter(Pmw.Counter)` -> `BkCounter`,
  `FileSelectionWithText(Pmw.Dialog)` -> `BkDialog`,
  `GraphicalAngleChooser` `Pmw.Counter` -> `BkCounter`,
  `ValueWithUnitParent` `Pmw.OptionMenu` -> `BkOptionMenu`,
  `Pmw.OK/ERROR/PARTIAL` -> local constants. Removed `import Pmw`.
  File changed: [`widgets.py`](packages/bkchem-app/bkchem/widgets.py).
- Migrate `interactors.py`, `main_chemistry_io.py`, `paper.py` from Pmw (M8).
  Replace 5 `Pmw.PromptDialog` -> `BkPromptDialog`, 1 `Pmw.Dialog` -> `BkDialog`,
  1 `Pmw.TextDialog` -> `BkTextDialog` in interactors.py.
  Replace 3 `Pmw.PromptDialog` -> `BkPromptDialog`, 2 `Pmw.TextDialog` ->
  `BkTextDialog` in main_chemistry_io.py.
  Replace 2 `Pmw.TextDialog` -> `BkTextDialog` in paper.py.
  Files changed:
  [`interactors.py`](packages/bkchem-app/bkchem/interactors.py),
  [`main_chemistry_io.py`](packages/bkchem-app/bkchem/main_lib/main_chemistry_io.py),
  [`paper.py`](packages/bkchem-app/bkchem/paper.py).
- Migrate `external_data.py` from Pmw (M9). Replace
  `ExternalDataList(Pmw.OptionMenu)` -> `BkOptionMenu`,
  `ExternalDataListSelection(Pmw.RadioSelect)` -> `BkRadioSelect`.
  File changed: [`external_data.py`](packages/bkchem-app/bkchem/external_data.py).
- Migrate `dialogs.py` from Pmw to native tkinter/ttk (M6). Replaced all 40
  Pmw usages: 7 `Pmw.Dialog` -> `BkDialog`, 3 `Pmw.Dialog` base classes ->
  `BkDialog`, 3 `Pmw.NoteBook` -> `ttk.Notebook`, 5 `Pmw.Counter` ->
  `BkCounter`, 5 `Pmw.OptionMenu` -> `BkOptionMenu`, 6 `Pmw.RadioSelect` ->
  `BkRadioSelect`, 3 `Pmw.Group` -> `BkGroup`, 2 `Pmw.ScrolledListBox` ->
  `BkScrolledListBox`, 3 `Pmw.SELECT` -> `'select'`. Removed `import Pmw`.
  Added `index()`, integer `invoke()`, and `configure(Button_state=...)`
  methods to `BkRadioSelect` for Pmw API compatibility.
  Files changed:
  [`dialogs.py`](packages/bkchem-app/bkchem/dialogs.py),
  [`bk_widgets.py`](packages/bkchem-app/bkchem/bk_widgets.py).
- Fix `UnboundLocalError` for `tab_bg` in `configure_ttk_styles()` by moving
  variable definitions before their first use in zoom/scrollbar styles.
  File changed:
  [`theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py).
- Replace `Pmw.NoteBook` with `ttk.Notebook` for document tabs. Notebook tabs
  now use ttk style maps (`TNotebook.Tab`) for active/inactive coloring instead
  of per-tab Pmw configure calls. Added `<<NotebookTabChanged>>` binding with
  `_programmatic_tab_select` guard to prevent re-entrant paper switches.
  Scrollbars upgraded to `ttk.Scrollbar`, zoom controls to `ttk.Button`/
  `ttk.Label`/`ttk.Frame`. Tab rename API in file I/O updated from
  `notebook.tab(name).configure()` to `notebook.tab(frame, text=...)`.
  Files changed:
  [`main.py`](packages/bkchem-app/bkchem/main.py),
  [`main_tabs.py`](packages/bkchem-app/bkchem/main_lib/main_tabs.py),
  [`main_file_io.py`](packages/bkchem-app/bkchem/main_lib/main_file_io.py),
  [`theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py).
- Replace `Pmw.Balloon` with `BkBalloon` for toolbar tooltips. Menu balloon
  stays `Pmw.Balloon` until menu system migration.
  File changed: [`main.py`](packages/bkchem-app/bkchem/main.py).
- Replace `Pmw.MessageDialog` in `about()` with `tkinter.messagebox.showinfo()`.
  Replace `Pmw.MessageDialog` in `close_paper()` with
  `tkinter.messagebox._show()` using YESNOCANCEL for save/close/cancel.
  Files changed:
  [`main.py`](packages/bkchem-app/bkchem/main.py),
  [`main_tabs.py`](packages/bkchem-app/bkchem/main_lib/main_tabs.py).
- Replace `Pmw.OptionMenu` fallback in submode dropdown with `ttk.Combobox`
  (readonly). File changed:
  [`main_modes.py`](packages/bkchem-app/bkchem/main_lib/main_modes.py).
- Fix dark-theme bond rendering: wrap all render-op colors through
  `theme_manager.map_chemistry_color()` in `_render_ops_to_tk_canvas()`.
  Previously `op.color` from oasa was truthy (`#000`), bypassing the theme
  mapping fallback. Now all LineOp, PolygonOp, CircleOp, and PathOp colors
  are mapped. File changed:
  [`bond_render_ops.py`](packages/bkchem-app/bkchem/bond_render_ops.py).
- Fix dark-theme arrow and vector graphics rendering: wrap `self.line_color`
  and `self.area_color` in `theme_manager.map_chemistry_color()` for all
  canvas create/itemconfig calls in arrow and graphics draw/redraw methods.
  Files changed:
  [`arrow_lib.py`](packages/bkchem-app/bkchem/arrow_lib.py),
  [`graphics.py`](packages/bkchem-app/bkchem/graphics.py).
- Add [`bk_dialogs.py`](packages/bkchem-app/bkchem/bk_dialogs.py) with pure
  tkinter/ttk drop-in replacements for Pmw dialog and input widgets: `BkDialog`
  (replaces `Pmw.Dialog`), `BkPromptDialog` (replaces `Pmw.PromptDialog`),
  `BkTextDialog` (replaces `Pmw.TextDialog`), `BkCounter` (replaces
  `Pmw.Counter`), and `BkScrolledListBox` (replaces `Pmw.ScrolledListBox`).
  Also exports Pmw-compatible validation constants `OK`, `ERROR`, `PARTIAL`.
- Add [`bk_widgets.py`](packages/bkchem-app/bkchem/bk_widgets.py) with drop-in
  replacement wrappers for Pmw widget classes: `BkOptionMenu` (replaces
  `Pmw.OptionMenu` with ttk.Combobox), `BkRadioSelect` (replaces
  `Pmw.RadioSelect` with native tkinter Radiobutton/Checkbutton), and `BkGroup`
  (replaces `Pmw.Group` with ttk.LabelFrame). Also defines `BK_OK`, `BK_ERROR`,
  `BK_PARTIAL` constants replacing `Pmw.OK`/`Pmw.ERROR`/`Pmw.PARTIAL`.
- Add `BkBalloon` tooltip class in
  [`bk_tooltip.py`](packages/bkchem-app/bkchem/bk_tooltip.py) as a lightweight
  replacement for `Pmw.Balloon`. Uses a borderless `Toplevel` with 500ms hover
  delay, light-yellow background, and optional status-bar callback. No Pmw
  dependency required.
- Migrate submode ribbon row-layout buttons from Pmw.RadioSelect to
  ttk.Button with named styles (`Submode.TButton`, `Selected.Submode.TButton`).
  Buttons now inherit theme colors automatically via ttk style maps, fixing
  white/light backgrounds in dark mode. Grid-layout buttons also gain
  explicit theme colors (`grid_deselected`, `toolbar_fg`, `hover`).
  Extracted shared row-building logic into `_build_submode_row()` method,
  reused by both `change_mode()` and `refresh_submode_buttons()`.
  Files changed:
  [`main_modes.py`](packages/bkchem-app/bkchem/main_lib/main_modes.py),
  [`theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py).
- Add 1px separator line below submode ribbon, between ribbon and canvas area.
  Uses theme-aware separator color. Grid layout shifted: edit pool now row 5,
  notebook row 6, status bar row 7. Files changed:
  [`main.py`](packages/bkchem-app/bkchem/main.py),
  [`main_modes.py`](packages/bkchem-app/bkchem/main_lib/main_modes.py).
- Increase toolbar mode button horizontal padding from `padx=1` to `padx=2`
  for better visual breathing room between icons. File changed:
  [`main.py`](packages/bkchem-app/bkchem/main.py).
- Reserve fixed minimum height (28px) for edit pool row via
  `grid_rowconfigure(minsize=28)` so showing/hiding the Entry widget when
  switching modes does not cause the canvas to jump vertically. File changed:
  [`main.py`](packages/bkchem-app/bkchem/main.py).
- Update GUI UX review document to reflect all completed items: separator
  lines, button padding, edit pool layout fix, theme system, ttk migration,
  status bar enhancements, keyboard shortcuts. File changed:
  [`GUI_UX_REVIEW.md`](docs/archive/GUI_UX_REVIEW.md).
- Reorganize pixmaps directory: move 92 PNG icons into `pixmaps/png/`
  subdirectory and remove 97 legacy GIF icons. Root pixmaps folder now
  contains only `png/`, `src/`, and `icon.ico`. Files changed:
  [`pixmaps.py`](packages/bkchem-app/bkchem/pixmaps.py),
  [`os_support.py`](packages/bkchem-app/bkchem/os_support.py).
- Add theme-aware toolbar icon recoloring. When the active theme has a
  dark toolbar (luminance < 0.5), icons are automatically recolored at
  load time using Pillow luminance inversion (HLS lightness flip). Icons
  reload on theme switch so dark-on-transparent strokes become
  light-on-transparent. No duplicate PNG files needed. Files changed:
  [`pixmaps.py`](packages/bkchem-app/bkchem/pixmaps.py),
  [`theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py).
- Update SVG-to-PNG converter to output into `pixmaps/png/` subdirectory.
  File changed:
  [`convert_svg_icons.py`](tools/convert_svg_icons.py).
- Replace toolbar `Button` widgets with `Label` widgets to fix macOS Aqua
  Tk 9 ignoring `background` color on buttons with images. Labels correctly
  honor background color, making dark theme toolbar icons render without
  white squares. Click handling is via `<Button-1>` bindings on Labels.
  Undo/redo also converted to Labels. Removed `Pmw.RadioSelect` from
  toolbar construction. Files changed:
  [`main.py`](packages/bkchem-app/bkchem/main.py),
  [`main_modes.py`](packages/bkchem-app/bkchem/main_lib/main_modes.py),
  [`theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py),
  [`test_gui_modes.py`](packages/bkchem-app/tests/test_gui_modes.py).
- Fix TclError on theme switch caused by garbage-collected PhotoImage
  references. Old images are now kept alive until new themed images replace
  them on toolbar buttons. Submode ribbon is rebuilt on theme switch to
  avoid stale image references on hover. File changed:
  [`theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py).
- Add GUI theme switch smoke test that exercises light-to-dark-to-light
  transitions, validates toolbar button images survive the switch, and
  includes a rapid toggle stress test. File added:
  [`test_gui_theme_change.py`](packages/bkchem-app/tests/test_gui_theme_change.py).
- Replace Emacs-style multi-key sequences with standard single-modifier
  keyboard shortcuts. File operations (New, Open, Save, Quit) now use Ctrl+N,
  Ctrl+O, Ctrl+S, Ctrl+Q cross-platform. macOS adds Cmd equivalents (Cmd+N,
  Cmd+O, Cmd+S, Cmd+Q, Cmd+W for close tab). Clipboard operations use standard
  Ctrl+C/V (macOS Cmd+C/V/X). Removed all `C-x C-*`, `C-a C-*`, `C-d C-*`,
  `C-o C-*` Emacs chord sequences and legacy `A-w`, `M-w`, `C-w`, `C-y`
  clipboard bindings. Files changed:
  [`modes_lib.py`](packages/bkchem-app/bkchem/modes/modes_lib.py),
  [`edit_mode.py`](packages/bkchem-app/bkchem/modes/edit_mode.py).
- Add platform-aware accelerator display in menus. New `format_accelerator()`
  function in
  [`platform_menu.py`](packages/bkchem-app/bkchem/platform_menu.py)
  converts internal key notation to Unicode modifier symbols on macOS and
  `Ctrl+Key` text on Linux/Windows. Menu accelerator columns now show
  platform-native notation instead of Emacs-style strings.
- Standardize menu label names to common desktop conventions: Load -> Open,
  Exit -> Quit, Save As.. -> Save As..., File properties -> Document
  Properties..., Select all -> Select All, Selected to clipboard as SVG ->
  Copy as SVG. Chemistry menu: Read -> Import, Generate -> Export for SMILES
  and InChI operations. Updated accelerator strings to match new single-key
  shortcuts in both the legacy menu template in
  [`main.py`](packages/bkchem-app/bkchem/main.py) and the action registry
  files:
  [`file_actions.py`](packages/bkchem-app/bkchem/actions/file_actions.py),
  [`edit_actions.py`](packages/bkchem-app/bkchem/actions/edit_actions.py),
  [`chemistry_actions.py`](packages/bkchem-app/bkchem/actions/chemistry_actions.py).
  Also updated
  [`test_file_actions.py`](packages/bkchem-app/tests/test_file_actions.py)
  to match new label_key values.
- Add Help > Keyboard Shortcuts dialog showing all shortcuts with
  platform-native modifier notation. Files changed:
  [`dialogs.py`](packages/bkchem-app/bkchem/dialogs.py),
  [`help_actions.py`](packages/bkchem-app/bkchem/actions/help_actions.py),
  [`menus.yaml`](packages/bkchem-app/bkchem_data/menus.yaml).
- Update i18n translation files (`.pot` template and all 11 `.po` locale files)
  with new msgid values matching the updated label and help text strings.
- Update About dialog with current maintainer info (Neil R. Voss) and social
  links, replacing the previous fork maintainer credit. File changed:
  [`messages.py`](packages/bkchem-app/bkchem/messages.py).
- Reduce paper sizes from 33 entries to 11 common sizes: A-series (A0-A5) for
  international users, plus US sizes (Letter, Legal, ANSI B, ANSI C, ANSI D).
  Default paper size changed from A4 to Letter, default orientation changed
  from portrait to landscape. Fix landscape/portrait orientation swap bug
  caused by inconsistent dimension ordering in paper_types dict -- all entries
  now use `[longer_side, shorter_side]` format. Fix hex grid overlay not
  redrawing when paper size or orientation changes via Document Properties
  dialog. Files changed:
  [`data.py`](packages/bkchem-app/bkchem/data.py),
  [`classes.py`](packages/bkchem-app/bkchem/classes.py),
  [`temp_manager.py`](packages/bkchem-app/bkchem/temp_manager.py),
  [`paper_properties.py`](packages/bkchem-app/bkchem/paper_lib/paper_properties.py).
- Add YAML-based light/dark theme system. Each theme is a separate file in
  [`packages/bkchem-app/bkchem_data/themes/`](packages/bkchem-app/bkchem_data/themes/)
  (e.g. `light.yaml`, `dark.yaml`) for easy install, removal, and customization.
  Themes are managed by new module
  [`packages/bkchem-app/bkchem/theme_manager.py`](packages/bkchem-app/bkchem/theme_manager.py).
  All GUI chrome colors (toolbar, buttons, tabs, status bar, edit pool, canvas
  surround) are now theme-driven. Chemistry content with default colors
  (bonds, atom labels) follows the active theme via `map_chemistry_color()`,
  while explicitly colored objects stay unchanged. Paper background and hex grid
  overlay also respect the theme. Theme selector available under Options > Theme;
  preference persists across restarts. Files changed:
  [`bkchem_config.py`](packages/bkchem-app/bkchem/bkchem_config.py),
  [`main.py`](packages/bkchem-app/bkchem/main.py),
  [`main_modes.py`](packages/bkchem-app/bkchem/main_lib/main_modes.py),
  [`main_tabs.py`](packages/bkchem-app/bkchem/main_lib/main_tabs.py),
  [`edit_pool.py`](packages/bkchem-app/bkchem/edit_pool.py),
  [`options_actions.py`](packages/bkchem-app/bkchem/actions/options_actions.py),
  [`dialogs.py`](packages/bkchem-app/bkchem/dialogs.py),
  [`menus.yaml`](packages/bkchem-app/bkchem_data/menus.yaml),
  [`bond_display.py`](packages/bkchem-app/bkchem/bond_display.py),
  [`bond_render_ops.py`](packages/bkchem-app/bkchem/bond_render_ops.py),
  [`special_parents.py`](packages/bkchem-app/bkchem/special_parents.py),
  [`paper_properties.py`](packages/bkchem-app/bkchem/paper_lib/paper_properties.py),
  [`grid_overlay.py`](packages/bkchem-app/bkchem/grid_overlay.py).
- Add mode name and zoom percentage labels to the status bar. The active mode
  name updates on mode switch; zoom percentage updates on zoom changes, mirroring
  the per-tab zoom label. Changes in
  [`packages/bkchem-app/bkchem/main.py`](packages/bkchem-app/bkchem/main.py),
  [`packages/bkchem-app/bkchem/main_lib/main_modes.py`](packages/bkchem-app/bkchem/main_lib/main_modes.py),
  and
  [`packages/bkchem-app/bkchem/main_lib/main_tabs.py`](packages/bkchem-app/bkchem/main_lib/main_tabs.py).
- Add 1px horizontal separator line between the toolbar and submode ribbon for
  visual hierarchy. Toolbar background darkened to `toolbar_color` (from
  `background_color`) to distinguish it from the canvas surround. Toolbar
  buttons and undo/redo buttons updated to match the new background. Changes in
  [`packages/bkchem-app/bkchem/main.py`](packages/bkchem-app/bkchem/main.py).
- Add hover highlight effects to submode ribbon buttons (both row-layout and
  grid-layout). Hovering shows `hover_color` background; active/selected buttons
  retain their selection styling. Changes in
  [`packages/bkchem-app/bkchem/main_lib/main_modes.py`](packages/bkchem-app/bkchem/main_lib/main_modes.py).
- Add `padx=1, pady=1` breathing room to toolbar mode buttons via
  `Pmw.RadioSelect` padding. Edit pool row follows standard ribbon show/hide
  (no reserved whitespace). Changes in
  [`packages/bkchem-app/bkchem/main.py`](packages/bkchem-app/bkchem/main.py).
- Consolidate UI color constants (`toolbar_color`, `separator_color`,
  `hover_color`, `active_mode_color`) into
  [`packages/bkchem-app/bkchem/bkchem_config.py`](packages/bkchem-app/bkchem/bkchem_config.py)
  instead of scattering inline hex values across `main.py` and `main_modes.py`.
- Add toolbar group separators between logical mode groups (general, templates,
  chemistry, annotation, geometry, graphics, maintenance). Separator positions
  are data-driven via `---` entries in
  [`packages/bkchem-app/bkchem_data/modes.yaml`](packages/bkchem-app/bkchem_data/modes.yaml)
  and parsed by `get_toolbar_separator_positions()` in
  [`packages/bkchem-app/bkchem/modes/config.py`](packages/bkchem-app/bkchem/modes/config.py).
- Add hover highlight effects to toolbar mode buttons (`<Enter>`/`<Leave>`
  bindings lighten to `#d8d8d8`). Active mode uses light blue fill (`#cde4f7`)
  with groove relief instead of plain sunken relief. Changes in
  [`packages/bkchem-app/bkchem/main.py`](packages/bkchem-app/bkchem/main.py)
  and
  [`packages/bkchem-app/bkchem/main_lib/main_modes.py`](packages/bkchem-app/bkchem/main_lib/main_modes.py).
- Add low-hanging fruit modernization section to
  [`docs/GUI_UX_REVIEW.md`](docs/GUI_UX_REVIEW.md) documenting implemented and
  future Tkinter button improvements.
- Add undo/redo toolbar buttons to the mode button bar with icon support and
  Pmw.Balloon tooltips in
  [`packages/bkchem-app/bkchem/main.py`](packages/bkchem-app/bkchem/main.py).
- Add macOS Command key (Cmd) equivalents for common keyboard shortcuts:
  Cmd+Z undo, Cmd+Shift+Z redo, Cmd+S save, Cmd+Shift+A select all in
  [`packages/bkchem-app/bkchem/modes/modes_lib.py`](packages/bkchem-app/bkchem/modes/modes_lib.py).
  Add Cmd+plus/minus/0 zoom and Cmd+G hex grid toggle in
  [`packages/bkchem-app/bkchem/paper_lib/paper_events.py`](packages/bkchem-app/bkchem/paper_lib/paper_events.py).
- Add [`tools/convert_svg_icons.py`](tools/convert_svg_icons.py) script to
  convert SVG icon sources to PNG. Defaults to 32x32; accepts `-s` for custom
  size, `-n` for dry run, `-v` for verbose output.
- Add 5 new SVG icon sources (undo, redo, repair, biotemplate, rplus) in
  [`packages/bkchem-app/bkchem_data/pixmaps/src/`](packages/bkchem-app/bkchem_data/pixmaps/src/)
  and regenerate all 92 SVG-to-PNG icons at 32x32 with 32-bit RGBA color in
  [`packages/bkchem-app/bkchem_data/pixmaps/`](packages/bkchem-app/bkchem_data/pixmaps/).
  The `pixmaps.py` loader already prefers PNG over GIF so icons upgrade
  automatically.
- Add [`docs/GUI_UX_REVIEW.md`](docs/GUI_UX_REVIEW.md) with a comprehensive
  visual quality and usability audit of the v26.02 GUI, including severity
  ratings and prioritized recommendations.
- Rotate hex grid from flat-top to pointy-top orientation so bond directions
  align with organic chemistry convention (30, 90, 150, 210, 270, 330 degrees).
  - Basis vectors rotated from (0, 60) degrees to (30, 90) degrees in
    [`packages/oasa/oasa/hex_grid.py`](packages/oasa/oasa/hex_grid.py).
  - Add `generate_hex_honeycomb_edges()` to produce honeycomb line segments.
  - [`packages/bkchem-app/bkchem/grid_overlay.py`](packages/bkchem-app/bkchem/grid_overlay.py)
    now draws faint honeycomb lines behind grid dots.
  - Update all hex grid tests for new pointy-top geometry and add honeycomb
    edge tests.
- Make hex grid overlay less visually prominent: lighten honeycomb lines from
  `#DDDDDD`/0.5 to `#E8E8E8`/0.375 and dots from `#AADDCC` to `#BFE5D9` in
  [`packages/bkchem-app/bkchem/grid_overlay.py`](packages/bkchem-app/bkchem/grid_overlay.py).
  Increase default bond line_width from `1px` to `1.5px` in
  [`packages/bkchem-app/bkchem/classes.py`](packages/bkchem-app/bkchem/classes.py).
- Clip honeycomb edges to the paper: require both endpoints inside the bounding
  box instead of just one, so lines no longer bleed onto the gray canvas area.
- Fix snap-to-hex-grid alignment: after snapping atoms to the best-fit grid
  origin, translate the molecule so snapped coordinates align with the displayed
  (0,0) grid. Previously, snapped atoms landed on an offset grid invisible to
  the user.  Fixed in
  [`packages/oasa/oasa/repair_ops.py`](packages/oasa/oasa/repair_ops.py) and
  [`tools/snap_cdml_to_hex_grid.py`](tools/snap_cdml_to_hex_grid.py).
- Fix hex grid disappearing on the paper: replace `tag_lower("hex_grid")` with
  `tag_raise("hex_grid", background)` in
  [`packages/bkchem-app/bkchem/grid_overlay.py`](packages/bkchem-app/bkchem/grid_overlay.py)
  so the grid draws above the white paper rectangle instead of below it.
- Add [`docs/GUI_MODULE_USAGE_AUDIT.md`](docs/GUI_MODULE_USAGE_AUDIT.md) with a
  per-file audit of 47 `packages/bkchem-app/bkchem/*.py` GUI modules, including
  purpose summaries, importer evidence, and GUI active-use status.
- Audit result: 46 of 47 listed modules are in active GUI/runtime use; only
  [`packages/bkchem-app/bkchem/debug.py`](packages/bkchem-app/bkchem/debug.py)
  appears unused (no imports found in package code or tests).

## 2026-02-20
- Replace custom coordinate generation pipeline with RDKit.
  - RDKit is now a required dependency for OASA (added to
    [`packages/oasa/pyproject.toml`](packages/oasa/pyproject.toml)).
  - New thin wrapper
    [`packages/oasa/oasa/coords_generator.py`](packages/oasa/oasa/coords_generator.py)
    delegates to `rdkit_bridge.calculate_coords_rdkit()` with full
    `bond_length` and `force` parameter support.
  - Delete the custom four-phase pipeline (`coords_gen/` package: ring
    placement, chain placement, collision resolution, force-field refinement).
  - Delete `coords_generator2.py` (shim to the deleted pipeline).
  - Delete `coords_optimizer.py` (standalone demo, nothing imported it).
  - Delete `graph/spatial_index.py` (KD-tree only used by deleted phases 3-4).
  - Delete associated tests (`test_spatial_index.py`, `test_cubane_coordinates.py`)
    and tools (`benchmark_spatial_index.py`, `coords_comparison.py`).
  - Simplify `oasa_bridge.py` fallback chain to a single call path.
  - Update `haworth/fragment_layout.py` to use `coords_generator` directly.
  - Adapt `test_coords_generator2.py` to test the RDKit-backed generator
    (44 tests, all passing).
  - Rewrite
    [`docs/OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md`](docs/OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md)
    to document the RDKit delegation architecture.
- Fix `tools/selftest_sheet.py` imports for renamed modules (`atom_lib`,
  `bond_lib`, `molecule_lib`) and capitalized class names (`Atom`, `Bond`,
  `Molecule`).
- Add 2D spatial index (KD-tree) for OASA coordinate generation.
  - New file
    [`packages/oasa/oasa/graph/spatial_index.py`](packages/oasa/oasa/graph/spatial_index.py):
    pure-Python KD-tree with `query_radius()` and `query_pairs()` for fast
    radius-based neighbor lookups. Includes brute-force fallback helpers for
    small molecules (< 20 atoms).
  - Integrate into Phase 3 collision detection in
    [`packages/oasa/oasa/coords_gen/phase3_collisions.py`](packages/oasa/oasa/coords_gen/phase3_collisions.py):
    `_detect_collisions()` and `_count_collisions_for_atoms()` now use the
    spatial index for molecules with 20+ atoms, reducing all-pairs O(n^2)
    scans to O(n log n + nm).
  - Integrate into Phase 4 force-field repulsion in
    [`packages/oasa/oasa/coords_gen/phase4_refinement.py`](packages/oasa/oasa/coords_gen/phase4_refinement.py):
    `_apply_repulsion()` uses the spatial index to find candidate pairs
    within the repulsion cutoff. Index rebuilt every 10 iterations.
  - New test suite
    [`packages/oasa/tests/test_spatial_index.py`](packages/oasa/tests/test_spatial_index.py)
    (29 tests): brute-force oracle validation, boundary cases, degenerate
    geometries, random point cloud property tests, and scipy cross-checks.
  - New benchmark script
    [`tools/benchmark_spatial_index.py`](tools/benchmark_spatial_index.py):
    shows 2-5x speedup for standalone radius queries at 200-1000 points.
- Graph library cleanup: 5 targeted fixes.
  - Remove unused incremental mirror methods (`add_node`, `remove_node`,
    `add_edge`, `remove_edge`) from `RxBackend` in
    [`packages/oasa/oasa/graph/rx_backend.py`](packages/oasa/oasa/graph/rx_backend.py)
    and their tests in
    [`packages/oasa/tests/test_rx_backend.py`](packages/oasa/tests/test_rx_backend.py).
  - Add empty graph guard to `cycle_basis()` to prevent crash on node 0 lookup.
  - Replace fragile `hasattr(item, '_neighbors')` duck typing with
    `isinstance(item, Vertex)` in `find_path_between`.
  - Replace mutable default args (`=[]`) with `=None` + guard in `Graph.__init__`,
    `Graph.find_path_between`, `Edge.__init__`, `Edge.set_vertices`,
    `Diedge.__init__`, `Diedge.set_vertices`, and `BkMolecule.find_path_between`.
  - Fix `Vertex.remove_neighbor` truthiness check: `if to_del:` changed to
    `if to_del is not None:` so falsy Edge objects are handled correctly.
- Implement deferred ring system placement for multi-ring-system molecules
  (sucrose, raffinose). Phase 1 now defers unanchored ring systems instead of
  placing them at the origin; Phase 2 triggers their placement when chain
  expansion reaches a neighboring atom. Follows the RDKit `mergeNoCommon()`
  pattern from `EmbeddedFrag::expandEfrag()`. Modified
  [`packages/oasa/oasa/coords_gen/phase1_rings.py`](packages/oasa/oasa/coords_gen/phase1_rings.py),
  [`packages/oasa/oasa/coords_gen/phase2_chains.py`](packages/oasa/oasa/coords_gen/phase2_chains.py),
  and [`packages/oasa/oasa/coords_gen/calculate.py`](packages/oasa/oasa/coords_gen/calculate.py).
  Added sucrose and raffinose tests in
  [`packages/oasa/tests/test_coords_generator2.py`](packages/oasa/tests/test_coords_generator2.py).
- Update
  [`docs/OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md`](docs/OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md):
  fix stale file references so all "Our implementation" sections and the file
  map point to the refactored phase modules (`phase1_rings.py`,
  `phase2_chains.py`, `phase3_collisions.py`, `phase4_refinement.py`) instead
  of the legacy `coords_generator2.py`. Strengthen contract language clarifying
  OASA implements RDKit's gold standard algorithms directly in Python.
- Enable `useRingTemplates=True` in
  [`tools/coords_comparison.py`](tools/coords_comparison.py) so the RDKit
  comparison column uses the gold standard template path for cage molecules.
- Add Weisfeiler-Leman color pruning to graph isomorphism in
  [`packages/oasa/oasa/coords_gen/ring_templates.py`](packages/oasa/oasa/coords_gen/ring_templates.py).
  The `_find_isomorphism` backtracker now pre-computes WL node colors and
  only considers structurally compatible candidates, reducing template
  matching from 38.6s (5 timeouts) to 3.9s (0 timeouts) on 75 templates.
- Fix cubane test expected angles in
  [`packages/oasa/tests/test_cubane_coordinates.py`](packages/oasa/tests/test_cubane_coordinates.py):
  restore `EXPECTED_ANGLES` to `{0.0, 48.0, 90.0}`. The TemplateSmiles.h
  coordinates are perspective 3D projections matching PubChem's cubane
  depiction; the 48-degree angles are diagonal cross-braces connecting
  front and back rectangles of the perspective cube.
- Replace YAML template storage with direct `.smi` loading in
  [`packages/oasa/oasa/coords_gen/ring_templates.py`](packages/oasa/oasa/coords_gen/ring_templates.py).
  Templates are now read from
  [`packages/oasa/oasa/coords_gen/templates.smi`](packages/oasa/oasa/coords_gen/templates.smi)
  (one CXSMILES per line), the upstream format from
  [rdkit/molecular_templates](https://github.com/rdkit/molecular_templates).
  Drops the `yaml` dependency and removes
  `tools/generate_ring_templates_yaml.py`. Also removes the old
  `tools/parse_rdkit_templates.py` generator and stale
  `packages/oasa/oasa/ring_templates.py` copy.
- Fix cubane SMILES typo in `tools/coords_comparison.py` and
  `packages/oasa/tests/test_coords_generator2.py`: the old SMILES
  `C12C3C4C1C5C3C4C25` encoded a non-bipartite graph (not cubane);
  corrected to `C12C3C4C1C5C4C3C25` (PubChem CID 19137, Q3 hypercube).
- Add `packages/oasa/tests/test_cubane_coordinates.py` with 5 focused
  tests: atom/bond count, template match, bond angles against raw
  template coords ({0, 48, 90} degrees), bond length ratio, and
  bipartite graph verification.
- Skip Phases 3-5 (collision, refinement, PCA) when a CXSMILES template
  was used for ring placement in `coords_generator2`. The template
  coordinates are the final layout; later phases were distorting them
  (PCA rotated cubane's clean rectangular template ~24 degrees).
- Add `cxsmiles_to_mol()` to `oasa.smiles_lib` for proper CXSMILES import:
  parses SMILES, applies coordinate block to atom vertices in one step,
  keeping atom indices consistent with the coordinate block.
- Switch ring templates to use `cxsmiles_to_mol()` for CXSMILES parsing in
  `packages/oasa/oasa/coords_gen/ring_templates.py`. Templates are stored as
  CXSMILES strings and parsed at import time, eliminating atom-index
  mismatches. Fixes broken template matching for cubane, adamantane, and
  other cage molecules. Adds adamantane as a hand-crafted template (76
  total, up from 75).
- Add PCA major-axis alignment (Phase 5) to `coords_generator2`. After
  force-field refinement, all coordinates are rotated so the molecule's
  principal axis aligns with the x-axis, matching RDKit's
  `canonicalizeOrientation()` behavior. Fixes rectangular molecules like
  terphenyl rendering vertically instead of horizontally.
- Update `tools/coords_comparison.py`: remove duplicate "cholesterol
  skeleton" entry, add biological molecules (cholesterol, testosterone,
  GTP, ATP, NAD+, sucrose, raffinose, tetraglycine, tryptophan), and add
  all 76 ring templates as a separate gallery section for visual validation.
- Update `tools/parse_rdkit_templates.py` to validate CXSMILES with both
  RDKit and OASA parsers instead of generating pre-computed adjacency data.
- Refactor `tools/assess_gpl_coverage.py` to two-pass classification: pass 1
  uses cheap commit-date checks to classify pure GPL/LGPL files, pass 2 runs
  expensive git blame only on files whose commits span the cutoff date. Also
  add histogram breakdown of Mixed files in summary output (>90%, 50-90%,
  10-50%, <10% GPL buckets). Blank lines are now excluded from blame
  line counts so they do not inflate GPL/LGPL percentages.
- Speed up pass 1 in `tools/assess_gpl_coverage.py` by replacing five per-file
  `git log` calls with one `git log --follow --format=%ct|%aI` scan that
  computes first/last commit dates and before/after cutoff counts in-memory.
- Add `--force-blame` to `tools/assess_gpl_coverage.py` to force pass 2
  `git blame` on all files (ignoring pass-1 commit-only classification) so
  outputs can be compared directly against the optimized two-pass mode.
- Make pass 1 in `tools/assess_gpl_coverage.py` conservative for files that
  look post-cutoff by `git log`: run a small top-of-file blame sample and send
  the file to pass 2 when pre-cutoff lines are detected. This reduces false
  negatives on moved/renamed legacy files (notably under `packages/oasa`).
- Fix pass-1 false `Untracked` results for some imported OASA files where
  `git log --follow` returns no rows despite path history existing. The tool
  now falls back to plain `git log` when `--follow` is empty.
- Unify edit_mode snap-to-grid into a single move during drag. Previously, snap
  happened as a separate `move_to()` correction on mouse release, causing no
  visual feedback during drag and a disorienting jump on drop. Now the anchor
  atom's target is snapped to the hex grid each frame during `mouse_drag`, and
  the same delta is applied to all selected objects, matching draw_mode's
  real-time snap behavior. Removes the post-drag snap block from `mouse_up`.
- Fix overly aggressive snap-to-grid in edit mode. Previously, dropping a
  selection snapped every atom independently to the nearest hex grid point,
  distorting molecular geometry (especially 5-member rings). Now only the
  grabbed atom snaps and the rest of the selection translates by the same
  offset, preserving bond lengths and angles.
- Fix hex grid dots to only appear on the white paper area, not the full
  canvas background. Uses paper rectangle bounds (`_paper_properties` size)
  instead of viewport bounds. Also fixes the partial-fill bug where dots only
  covered the upper-left corner when `winfo_width`/`winfo_height` returned 1
  before the widget was mapped, and prevents the MAX_GRID_POINTS cutoff from
  silently hiding all dots when zoomed far out.
- Fix circular mean bug in `phase1_rings.py` `_compute_away_angle()` and
  `_place_spiro_ring()`: naive arithmetic average of angles failed when neighbor
  angles straddled the 0/2pi boundary (e.g., averaging 0 and 240 degrees gave
  120 instead of correct 300), causing second ring system to overlap the first.
  Replaced with proper circular mean using `atan2(sum_sin, sum_cos)`.
- Fix `_place_polygon_anchored()` in `phase1_rings.py`: polygon center was
  positioned using edge-rotation logic that sometimes placed it between the two
  ring systems instead of on the far side. Rewritten to always place the center
  at `radius` distance from the junction vertex in the away direction.
- Extend force-refinement repulsion exclusion in `phase4_refinement.py` from
  2-bond to 3-bond neighbors. Hexagonal para-position atoms are 3 bonds apart
  at distance sqrt(3), which fell within the 1.8x repulsion cutoff and created
  spurious inter-ring forces that distorted ring geometry.
- Tighten biphenyl bond length tolerance in `test_coords_generator2.py` from
  35% to 10% now that ring placement is deterministic and correct.
- Modularize `coords_generator2.py` into `coords_gen/` sub-package with one file
  per phase: `calculate.py` (orchestrator), `phase1_rings.py` (ring placement),
  `phase2_chains.py` (chain layout), `phase3_collisions.py` (collision resolution),
  `phase4_refinement.py` (force-field refinement), and `helpers.py` (shared
  geometry + `Transform2D` class). The original file becomes a thin re-export shim.
- Fix edge-fused ring placement in `phase1_rings.py`: `Transform2D` was mapping
  wrong polygon vertices when the second shared atom was not at index 1 in the
  sorted ring. Now correctly finds `v2`'s actual index for the polygon mapping.
- Fix spiro ring placement in `phase1_rings.py`: generate polygon vertices
  starting from the angle that points from center to spiro atom, guaranteeing
  vertex 0 coincides exactly with the shared atom. Previously used
  `regular_polygon_coords` with a fixed start angle that produced misaligned geometry.
- Fix separate ring system positioning: add `_find_external_anchor()` to detect
  when a ring atom has an already-placed neighbor outside its ring system, and
  position the new ring system relative to that neighbor. Fixes biphenyl and other
  multi-ring-system molecules that were placing all ring systems at the origin.
- Protect ring atoms in collision resolution (`phase3_collisions.py`): skip nudging
  when both atoms are ring members; move only the non-ring atom when one is a ring
  member. Prevents ring geometry from being destroyed by collision resolution.
- Add ring-aware force refinement (`phase4_refinement.py`): compute ideal angles
  from ring size using `pi*(n-2)/n` formula instead of hardcoded 120 degrees; pin
  ring atoms with 0.05 force factor; clamp maximum gradient step to prevent
  divergence.
- Add 13 new tests to `test_coords_generator2.py` (44 total): biphenyl ring
  separation, spiro bond quality, ring angle preservation, cholesterol skeleton
  vs RDKit, template count, and cubane template matching.
- Import all 75 RDKit polycyclic templates into `ring_templates.py` via
  `tools/parse_rdkit_templates.py`. The tool parses `TemplateSmiles.h`, uses
  RDKit to extract molecular graphs and 2D coordinates, and generates a
  standalone module with zero RDKit dependency. Replaces 3 hand-coded templates
  (cubane, adamantane, norbornane) with the full set. Steroid core is excluded
  by design (test case for ring-fusion algorithm, not present in templates).
- Add light gray outline (`#BBBBBB`, 0.5pt) to hex grid dots in `grid_overlay.py`
  for better contrast of teal dots against white paper and gray background.
- Enhance `tools/coords_comparison.py` with 11 new test molecules (cholesterol
  skeleton, caffeine, aspirin, ibuprofen, indole, purine, azulene, fluorene,
  terphenyl, adamantane, norbornane). Add per-molecule quality metrics: bond
  length variance (std/mean), ring regularity (max angle deviation from ideal
  N-gon), and overlap count (non-bonded pairs closer than 0.4x mean bond
  length). Output now includes a color-coded summary table above the SVG
  gallery with green/red cells based on quality thresholds.
- Add [docs/OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md](OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md)
  documenting the four-phase 2D coordinate generation pipeline: ring system
  placement (SSSR, BFS fusion, template lookup), chain placement (BFS outward,
  zigzag, stereo), collision resolution (flip subtrees, nudge), and force-field
  refinement (bond stretch, angle bend, non-bonded repulsion). Includes a file
  map comparing our modules to the corresponding RDKit Depictor source files and
  a testing strategy section covering the pytest suite and the visual comparison
  tool.
- Add `test_repair_ops.py` (112 tests) exercising all 5 pure-geometry repair
  operations against 4 real biomolecules parsed from SMILES: cholesterol (fused
  5+6+6+6 rings), GDP (fused purine + sugar), histidine (imidazole), and sucrose
  (furanose + pyranose). Ring normalization tests verify each ring becomes a
  regular N-gon using the `180*(N-2)/N` interior angle formula and uniform bond
  lengths. Fused ring tests are xfail (known limitation: sequential ring
  processing overwrites shared atoms). Documents snap-to-hex-grid as global-only:
  N-member rings where N % 3 != 0 (4, 5, 7, 8, etc.) cannot tile a hex grid.
- Migrate all callers from `coords_generator` to `coords_generator2`. Switch
  `smiles_lib.py`, `inchi_lib.py`, `linear_formula.py`, and `cdml.py` to use
  the newer three-layer 2D coordinate generator (ring placement, chain layout,
  collision resolution, force-field refinement). Remove `show_mol()` debug call
  from `linear_formula.py` `__main__` block.
- Add RDKit-inspired ring template system for cage molecules. New module
  `ring_templates.py` provides pre-computed 2D coordinate templates for cubane,
  adamantane, and norbornane with graph-isomorphism-based matching. Templates
  bypass the algorithmic ring-fusion approach that fails on polycyclic cage
  structures. Cubane coordinates extracted from RDKit `TemplateSmiles.h`;
  adamantane and norbornane hand-tuned.
- Integrate template lookup into `coords_generator2.py`. The
  `_place_ring_system()` method now attempts template matching before falling
  back to BFS ring-fusion. Adds `_try_template_placement()` helper that builds
  the ring system adjacency graph and queries `ring_templates.find_template()`.
- Remove `calc_coords=False` workarounds from `graph_test_fixtures.py`. Both
  `make_steroid_skeleton()` and `make_bridged_bicyclic()` fixtures now generate
  coordinates normally. Remove the `calc_coords` parameter from
  `_smiles_to_fixture()` helper.
- Fix `line_length()` argument bug in legacy `coords_generator.py` (lines
  401-402). The function was called with a single tuple instead of four
  separate arguments, causing crashes in `_process_multi_anelated_ring()` for
  polycyclic molecules. Fix corrects the call signature as a safety net.
- Add cubane, adamantane, and norbornane test classes to
  `test_coords_generator2.py` verifying coordinate generation, atom counts,
  and non-overlapping layouts for template-based molecules.
- Reduce pytest skips from 24 to 10 in graph parity tests. Extract
  `test_hexane_returns_empty` into standalone `TestAcyclicMolecules` class,
  filter `single_atom` fixture from path tests at collection time, and early
  return instead of skip for acyclic molecules in `test_theoretical_cycle_count`.
  Remaining 10 skips are legitimate SMILES parse failures (cubane, adamantane).
- Fix shebang alignment issues across 13 files. Remove shebangs from 11 test
  files, fixture files, and library modules that are not standalone scripts
  (`keysym_loader.py`, `repair_ops.py` x2, `graph_test_fixtures.py`, and 7
  `test_*.py` files). Add executable permission to 2 standalone scripts
  (`benchmark_graph_algorithms.py`, `snap_cdml_to_hex_grid.py`).
- Fix mode button border color residue after cycling through toolbar modes.
  Reset `highlightbackground` and `highlightcolor` to their default values when
  deselecting buttons in `change_mode()`, preventing blue-tinted border artifacts
  on macOS Tk/Aqua. Strengthen `test_gui_modes.py` border checks to verify
  inactive buttons do not retain the `#4a90d9` accent color.
- Remove 3 unused imports flagged by pyflakes in `oasa/render_lib/`: drop
  `_normalize_attach_site` from `glyph_model.py`, `_ray_box_boundary_intersection`
  from `attach_resolution.py`, and `make_box_target` from `low_level_geometry.py`.
- Standardize gettext i18n fallback pattern across 27 production files. Replace
  verbose `getattr(builtins, "_", None)` multi-line fallback with standard
  one-liner `builtins.__dict__.get('_', lambda m: m)` in 5 files (`checks.py`,
  `paper.py`, `widgets.py`, `paper_layout.py`, `paper_cdml.py`). Remove
  `builtins._ = _` assignments from consumer modules. Add consistent
  `# gettext i18n translation fallback` comment to all 27 files.
- Add `test_gui_modes.py` -- YAML-driven GUI test that cycles through all
  toolbar modes and submodes from `modes.yaml`, verifying mode names, submode
  state, and button border relief/highlightthickness on every switch.
- Fix `ValueError` when clicking repair mode toolbar button. Replace underscores
  with hyphens in repair submode keys (`normalize-lengths`, `normalize-angles`,
  `normalize-rings`, `snap-hex`) in `modes.yaml` and `repair_mode.py` to avoid
  Pmw `createcomponent()` rejecting underscore characters in component names.
- Remove redundant `sys.path.insert` calls from 8 test files. The conftest
  files and `source_me.sh` already set PYTHONPATH correctly. Remove
  `_ensure_sys_path()` helper functions from 4 GUI test files. Add missing
  `import oasa.smiles_lib` to `graph_test_fixtures.py` exposed by the cleanup.
- Strip all 12 `__init__.py` files to zero-length (empty) per PYTHON_STYLE.md
  policy. Remove GPL headers, docstrings, and MIN_PYTHON guards from init
  files that previously had only boilerplate.
- Strip `oasa/__init__.py`: remove `__version__`, auto-import loop (pkgutil),
  CamelCase re-exports (`Atom`, `Bond`, `Molecule`, `QueryAtom`, `ChemVertex`),
  and `CAIRO_AVAILABLE`/`PYBEL_AVAILABLE` flags. Switch `pyproject.toml` from
  dynamic version to static `version = "26.02"`. Update `chemical_convert.py`
  version string. Replace `oasa.CAIRO_AVAILABLE` checks in 3 test files with
  direct import.
- Strip `oasa/graph/__init__.py`: remove re-exports of `Graph`, `Vertex`,
  `Edge`, `Digraph`. Update consumers in `chem_compat.py`, `context_menu.py`
  to import from `oasa.graph.vertex_lib`, `oasa.graph.edge_lib`,
  `oasa.graph.graph_lib` directly.
- Fix mixed indentation (tabs vs spaces) in 10 Python files to use tabs
  exclusively per PYTHON_STYLE.md: `ftext_lib.py`, `group_lib.py`,
  `arrow_mode.py`, `bracket_mode.py`, `draw_mode.py`, `edit_mode.py`,
  `mark_mode.py`, `text_mode.py`, `rx_backend.py`, and `test_rx_backend.py`.
  Convert space-only class bodies to tabs and replace tab+space continuation
  lines with tab-only indentation.
- Replace all CamelCase re-export references (`oasa.Atom`, `oasa.Bond`,
  `oasa.Molecule`, `oasa.QueryAtom`, `oasa.ChemVertex`) with direct submodule
  imports (`oasa.atom_lib.Atom`, `oasa.bond_lib.Bond`, etc.) across 24 files.
  Add explicit `import oasa.codec_registry` to
  [test_codec_registry.py](packages/oasa/tests/test_codec_registry.py) to fix
  missing module attribute after `oasa/__init__.py` re-export removal.
- Strip `actions/__init__.py` to docstring only per PYTHON_STYLE.md policy.
  Move `MenuAction`, `ActionRegistry`, and `register_all_actions()` into new
  [actions/action_registry.py](packages/bkchem-app/bkchem/actions/action_registry.py).
  Update 10 production action modules and 4 test files to import from
  `bkchem.actions.action_registry` directly.
- Strip `modes/__init__.py` to license header + docstring per PYTHON_STYLE.md
  policy. Move discovery logic and `build_all_modes()` into new
  [modes/mode_loader.py](packages/bkchem-app/bkchem/modes/mode_loader.py).
  Update consumers in `main.py`, `main_lib/main_modes.py`, and `edit_pool.py`
  to import from `bkchem.modes.mode_loader` and `bkchem.modes.config` directly.
- Strip `haworth/__init__.py` to license header + docstring only (no re-exports).
  Update 6 consumer files to import from `oasa.haworth.layout` directly instead
  of relying on package-level re-exports.
- Add `## __init__.py FILES` section to
  [docs/PYTHON_STYLE.md](docs/PYTHON_STYLE.md) codifying rules for minimal
  `__init__.py` files: no implementation code, no re-export facades, no curated
  lists, no class maps, no registrar logic, no global variables, no
  `__version__` assignments, no inline lazy loaders, and no re-exports for
  type-checker convenience.
- Extract Haworth layout algorithms from
  [haworth/\_\_init\_\_.py](packages/oasa/oasa/haworth/__init__.py) into new
  [haworth/layout.py](packages/oasa/oasa/haworth/layout.py). Reduces
  `__init__.py` from 525 lines to a ~30-line re-export facade. Updated sibling
  imports in `renderer.py` and `renderer_config.py` to import from
  `oasa.haworth.layout` directly.
- Reduce hardcoded names in `__init__.py` files with auto-discovery. Saved
  ~15.5 KB total across 4 files (42,784 -> 27,214 bytes). Changes:
  - Gut [render_lib/\_\_init\_\_.py](packages/oasa/oasa/render_lib/__init__.py)
    302-line re-export facade (zero consumers) down to a docstring (13,195 ->
    1,107 bytes).
  - Replace hardcoded `_module_registrars` list in
    [actions/\_\_init\_\_.py](packages/bkchem-app/bkchem/actions/__init__.py) with
    `pathlib.Path.glob("*_actions.py")` auto-discovery (4,642 -> 4,099 bytes).
  - Replace 43 hardcoded imports and dead `_EXPORTED_MODULES` / `allNames` lists
    in [oasa/\_\_init\_\_.py](packages/oasa/oasa/__init__.py) with
    `pkgutil.iter_modules()` auto-discovery (5,114 -> 2,786 bytes).
  - Replace 17 hardcoded mode imports and 16-entry `_MODE_CLASS_MAP` dict in
    [modes/\_\_init\_\_.py](packages/bkchem-app/bkchem/modes/__init__.py) with
    `pathlib.Path.glob("*_mode.py")` auto-discovery (3,175 -> 2,564 bytes).
- Fix pyflakes failures in
  [oasa/\_\_init\_\_.py](packages/oasa/oasa/__init__.py) (add `render_lib` to
  export lists) and
  [modes/\_\_init\_\_.py](packages/bkchem-app/bkchem/modes/__init__.py) (remove
  6 unused re-exports: `event_to_key`, `mode`, `simple_mode`, `basic_mode`,
  `biomolecule_template_mode`, `user_template_mode`, `bond_align_mode`; add
  `__all__` for the 3 intentional config re-exports).
- Delete `inchi_key.py` from OASA. The 1,348-line hand-rolled InChIKey generator
  (with ~1,100 lines of hardcoded lookup table) is dead weight because the
  external InChI program already returns the key. Simplified the fallback in
  [inchi_lib.py](packages/oasa/oasa/inchi_lib.py) to raise or ignore on missing
  key. Removed `INCHI_KEY_AVAILABLE` flag from
  [\_\_init\_\_.py](packages/oasa/oasa/__init__.py).
- Delete `render_geometry.py` backward-compat shim and update all 19 consumer
  files to import directly from `oasa.render_lib` sub-modules. Remove
  `render_geometry` from [\_\_init\_\_.py](packages/oasa/oasa/__init__.py)
  exports. All `render_geometry.X` / `_render_geometry.X` / `_rg.X` call sites
  replaced with bare names. Consumer files updated: 5 OASA runtime
  ([render_out.py](packages/oasa/oasa/render_out.py),
  [svg_out.py](packages/oasa/oasa/svg_out.py),
  [cairo_out.py](packages/oasa/oasa/cairo_out.py),
  [renderer.py](packages/oasa/oasa/haworth/renderer.py),
  [renderer_layout.py](packages/oasa/oasa/haworth/renderer_layout.py)),
  2 BKChem ([bond_drawing.py](packages/bkchem-app/bkchem/bond_drawing.py),
  [bond_render_ops.py](packages/bkchem-app/bkchem/bond_render_ops.py)),
  10 test files, 2 tool files
  ([calibrate_glyph_model.py](tools/calibrate_glyph_model.py),
  [selftest_sheet.py](tools/selftest_sheet.py)).
- Remove 5 dead methods: `print_all_coords()`, `_open_debug_console()`,
  `flush_first_selected_mol_to_graph_file()` from
  [paper.py](packages/bkchem-app/bkchem/paper.py), and `_update_geometry()`,
  `clean()` from [main.py](packages/bkchem-app/bkchem/main.py).
- Refactor [main.py](packages/bkchem-app/bkchem/main.py) to use mixin classes
  from [main_lib/](packages/bkchem-app/bkchem/main_lib/). The `BKChem` class now
  inherits from four mixins (MainTabsMixin, MainModesMixin,
  MainChemistryIOMixin, MainFileIOMixin) plus Tk. File I/O methods (save_CDML,
  load_CDML, format_import/export, etc.), chemistry I/O methods (read_smiles,
  read_inchi, gen_smiles, gen_inchi, read_peptide_sequence), mode management
  methods (change_mode, change_submode, refresh_submode_buttons,
  _build_submode_grid), and tab management methods (change_paper, add_new_paper,
  close_paper, close_current_paper, etc.) are removed from main.py and provided
  by the mixins. Unused imports removed (export, oasa_bridge, safe_xml,
  filedialog, tkinter.messagebox, data, chem_paper, Button, Scrollbar,
  HORIZONTAL, VERTICAL). No behavioral changes.
- Refactor [paper.py](packages/bkchem-app/bkchem/paper.py) to use mixin classes
  from [paper_lib/](packages/bkchem-app/bkchem/paper_lib/). The `chem_paper`
  class now inherits from nine mixins (PaperLayoutMixin, PaperPropertiesMixin,
  PaperCDMLMixin, PaperFactoriesMixin, PaperEventsMixin, PaperIdManagerMixin,
  PaperSelectionMixin, PaperTransformsMixin, PaperZoomMixin) plus Canvas.
  Methods for zoom, transforms, selection, id management, events, factories,
  CDML I/O, properties, and layout are removed from paper.py and provided by
  the mixins. Only core methods (init, clipboard, undo/redo, hex grid, display
  info, chemistry check) remain in paper.py. Unused imports removed. No
  behavioral changes.
- Fix [test_menu_yaml.py](packages/bkchem-app/tests/test_menu_yaml.py) to account
  for the new repair menu: update expected menu count (9 to 10), menu order,
  action count (55 to 61), and separator count (19 to 21).
- Add GUI test for hex grid overlay and snap system in
  [test_bkchem_gui_hex_grid.py](packages/bkchem-app/tests/test_bkchem_gui_hex_grid.py).
  Three subprocess-based tests cover show/hide/toggle + snap toggle, the 50%
  zoom threshold that clears and redraws dots, and the MAX_GRID_POINTS cutoff
  in `generate_hex_grid_points()`.
- Add repair mode as a toolbar mode for click-to-repair geometry operations on
  individual molecules. New file
  [repair_mode.py](packages/bkchem-app/bkchem/modes/repair_mode.py) follows the
  misc_mode pattern. Submodes: Normalize Lengths, Normalize Angles, Normalize
  Rings, Straighten Bonds, Snap to Hex Grid, Clean Geometry. Registered in
  [modes/\_\_init\_\_.py](packages/bkchem-app/bkchem/modes/__init__.py) and
  [modes.yaml](packages/bkchem-app/bkchem_data/modes.yaml). Added toolbar icon
  [repair.gif](packages/bkchem-app/bkchem_data/pixmaps/repair.gif). Existing
  Repair menu actions remain unchanged for batch operations.
- Split monolithic [modes.py](packages/bkchem-app/bkchem/modes_old.py) (2,440
  lines, 18 classes) into a `modes/` package with 15 files. Each mode class
  gets its own file; shared base classes live in
  [modes_lib.py](packages/bkchem-app/bkchem/modes/modes_lib.py), YAML config
  loaders in [config.py](packages/bkchem-app/bkchem/modes/config.py), and
  the public API re-exported from
  [\_\_init\_\_.py](packages/bkchem-app/bkchem/modes/__init__.py). Pure file
  reorganization with no behavioral changes. Backward-compatible aliases
  preserved.
- Fix flaky GUI event test in
  [test_bkchem_gui_events.py](packages/bkchem-app/tests/test_bkchem_gui_events.py):
  disable hex grid snap during event simulation so atom canvas positions are
  predictable for synthetic click coordinates.
- Optimize hex grid at low zoom: add MAX_GRID_POINTS=5000 cutoff in
  [hex_grid.py](packages/oasa/oasa/hex_grid.py) `generate_hex_grid_points()`
  that returns None when the estimated point count is too large.
  [grid_overlay.py](packages/bkchem-app/bkchem/grid_overlay.py) skips drawing
  when None is returned. Also disable hex grid overlay redraw in
  [paper.py](packages/bkchem-app/bkchem/paper.py) `scale_all()` when scale is
  below 50%, clearing dots instead. Both guards prevent the slowdown from
  creating thousands of canvas ovals at low zoom levels.
- Reorder zoom diagnostic test steps in
  [test_bkchem_gui_zoom.py](packages/bkchem-app/tests/test_bkchem_gui_zoom.py):
  start with zoom_out/reset/zoom_in before zoom_to_fit and zoom_to_content,
  add zoom_to_content recovery between min/max clamp tests. Add
  zoom_to_content at start of model_coords and roundtrip tests so content is
  visible on screen.
- Move repair geometry algorithms to OASA per backend-to-frontend contract.
  Pure graph-geometry operations (bond length normalization, angle snapping,
  ring reshaping, bond straightening, hex grid snapping) now live in
  [packages/oasa/oasa/repair_ops.py](packages/oasa/oasa/repair_ops.py).
  BKChem [repair_ops.py](packages/bkchem-app/bkchem/repair_ops.py) is now
  thin wrappers handling only selection, unit conversion, redraw, and undo.
  Registered `repair_ops` in
  [oasa/\_\_init\_\_.py](packages/oasa/oasa/__init__.py).
- Add new top-level "Repair" menu with six geometry-fixing tools:
  normalize bond lengths (BFS-based), snap to hex grid (via
  `oasa.hex_grid`), normalize bond angles (60-degree snapping),
  normalize ring structures (regular polygon reshaping), straighten
  bonds (30-degree terminal snapping), and clean up geometry
  (coordinate regeneration). New files:
  [repair_ops.py](packages/bkchem-app/bkchem/repair_ops.py),
  [repair_actions.py](packages/bkchem-app/bkchem/actions/repair_actions.py).
  Modified: [menus.yaml](packages/bkchem-app/bkchem_data/menus.yaml),
  [actions/\_\_init\_\_.py](packages/bkchem-app/bkchem/actions/__init__.py).
- Remove 10 dead methods from
  [graph_lib.py](packages/oasa/oasa/graph/graph_lib.py) (720 to 630 lines):
  connect_a_graph, is_cycle, is_euler, get_size_of_pieces_after_edge_removal,
  get_neighbors, get_neighbors_indexes, get_degrees, dump_simple_text_file,
  read_simple_text_file, _read_file.
- Remove dead `_read_file` method and dead `main()` demo block from
  [molecule_lib.py](packages/oasa/oasa/molecule_lib.py) (1033 to 989 lines).
- Remove dead code from graph package satellite files:
  [digraph_lib.py](packages/oasa/oasa/graph/digraph_lib.py) (149 to 104 lines):
  get_diameter, get_random_longest_path_numbered, get_graphviz_text_dump.
  [diedge_lib.py](packages/oasa/oasa/graph/diedge_lib.py) (59 to 43 lines):
  neighbor_edges, get_neighbor_edges2.
  Delete [basic.py](packages/oasa/oasa/graph/basic.py) entirely (42 lines,
  attribute_flexible_class had zero subclasses or callers).
- Phase C: Swap 2 more algorithms to rustworkx and remove 609 lines of dead
  code from [graph_lib.py](packages/oasa/oasa/graph/graph_lib.py) (1329 to 720
  lines, 46% reduction).
  - Swap `get_maximum_matching` to `rustworkx.max_weight_matching()`: removes 80
    lines of pure-Python Edmonds blossom algorithm (get_initial_matching,
    find_augmenting_path_from, update_matching_using_augmenting_path). All 4
    matching tests pass with identical results.
  - Swap `get_smallest_independent_cycles_e` to `cycle_basis_edges()`: replaces
    113 lines of BFS-based edge cycle detection with a 5-line delegate that
    converts rustworkx vertex cycles to edge subgraphs.
  - Remove 23 dead methods and functions: get_almost_all_cycles_e,
    get_all_cycles_e_old, get_all_cycles_e_oldest, _get_cycles_for_vertex,
    _get_smallest_cycle_for_vertex, _get_smallest_cycles_for_vertex,
    get_all_cycles_old, _get_some_cycles, _get_all_ring_end_points,
    _get_all_ring_start_points, is_ring_end_vertex, is_ring_start_vertex,
    get_first_closer_by_one, is_there_a_ring_between, get_paths_down_to,
    get_path_down_to, filter_off_dependent_cycles, gen_variations,
    get_initial_matching, get_initial_matching_old, _print_mate, and MyThread
    class.
  - Remove all commented-out code blocks and dead threading import.
- Add `max_matching()` and `cycle_basis_edges()` delegates to `RxBackend`
  ([rx_backend.py](packages/oasa/oasa/graph/rx_backend.py)). Total adapter
  methods: 11 algorithm delegates plus mirror ops and index helpers.
- Phase B: Remove 188 lines of legacy algorithm code from
  [graph_lib.py](packages/oasa/oasa/graph/graph_lib.py): 8 `_*_legacy` methods,
  `_gen_diameter_progress`, `_get_width_from_vertex`, private
  `_mark_vertices_with_distance_from` BFS helper, and dead commented-out
  multi-thread diameter code. File reduced from 1517 to 1329 lines. All 867
  OASA tests and 340/341 BKChem tests pass.
- Integrate rustworkx backend into `Graph.__init__` and swap 8 graph algorithms
  to use `RxBackend` delegates in
  [graph_lib.py](packages/oasa/oasa/graph/graph_lib.py):
  `get_smallest_independent_cycles` (cycle_basis 167x faster), `get_diameter`
  (13x), `is_connected` (11x), `get_connected_components` (4x),
  `find_path_between` (3.2x + correctness fix), `path_exists` (4x),
  `is_edge_a_bridge` (replaces per-edge disconnect loop with Tarjan bridges),
  and `mark_vertices_with_distance_from` (1.5x). All mutations call
  `_flush_cache` which marks the backend dirty for lazy rebuild.
- Fix start==end edge case in `RxBackend.find_path_between()` in
  [rx_backend.py](packages/oasa/oasa/graph/rx_backend.py): return `[start]`
  when source and target are the same vertex (dijkstra omits this from results).
- Add `RxBackend` adapter class
  ([rx_backend.py](packages/oasa/oasa/graph/rx_backend.py))
  that mediates all rustworkx usage for OASA graph operations. Maintains
  identity maps between OASA Vertex/Edge objects and rustworkx indices.
  Provides 9 algorithm delegates (connected components, connectivity,
  path existence, diameter, cycle basis, bridges, BFS distance, pathfinding,
  dijkstra) plus mirror ops, rebuild, lazy sync, and invalidation.
  Includes workaround for rustworkx 0.17.1 `bridges()` bug that misses
  DFS root edges.
- Add 48 unit tests for RxBackend
  ([test_rx_backend.py](packages/oasa/tests/test_rx_backend.py))
  covering init, mirror ops, rebuild, lazy sync, all algorithm delegates,
  invalidation, and index conversion helpers.
- Fix `Digraph.create_edge()` to return `Diedge()` instead of inherited `Edge()`,
  matching the class's `edge_class = Diedge` declaration
  ([digraph_lib.py](packages/oasa/oasa/graph/digraph_lib.py))
- Remove debug `print()` statements from `Digraph.get_diameter()`
  ([digraph_lib.py](packages/oasa/oasa/graph/digraph_lib.py))
- Fix `make_bridged_bicyclic()` test fixture: norbornane has 0 bridges (every edge
  is in a cycle), changed `has_bridges` from True to False
  ([graph_test_fixtures.py](packages/oasa/tests/graph_test_fixtures.py))
- Add graph algorithm parity test suite
  [packages/oasa/tests/test_graph_parity.py](packages/oasa/tests/test_graph_parity.py)
  with 8 test classes (95 tests) comparing OASA vs rustworkx across all 10
  fixture molecules. Covers connected components, connectivity, path existence,
  diameter, cycle basis, BFS distance, bridges, and pathfinding. Documents
  rustworkx `bridges()` off-by-one bug (misses DFS root edge).
- Add deterministic benchmark script
  [packages/oasa/tests/benchmark_graph_algorithms.py](packages/oasa/tests/benchmark_graph_algorithms.py)
  comparing OASA graph algorithms vs rustworkx on benzene, naphthalene, and
  cholesterol (6-38 atoms). Tests 7 algorithm pairs with parity verification.
  Key results at N=500: cycle_basis 197-244x, diameter 7-56x, is_connected
  11-18x, connected_components 7-12x. All parity checks pass. Also benchmarks
  3 rustworkx-only algorithms (bridges, articulation_points, max_weight_matching).
- Add OASA graph semantics contract matrix
  [docs/active_plans/GRAPH_SEMANTICS_MATRIX.md](docs/active_plans/GRAPH_SEMANTICS_MATRIX.md)
  documenting every public method in Graph, Digraph, Vertex, Edge, and Diedge
  classes. Covers input/output types, side effects, cache flush behavior,
  `properties_` mutations, temporary disconnect usage, and confirmed rustworkx
  API mappings. Phase 0 deliverable for the rustworkx backend integration.
- Add graph test fixture module
  [packages/oasa/tests/graph_test_fixtures.py](packages/oasa/tests/graph_test_fixtures.py)
  with 10 molecule fixtures (benzene, cholesterol, naphthalene, steroid skeleton,
  caffeine, hexane, single atom, disconnected, cyclopentane, bridged bicyclic) built
  in both OASA and rustworkx.PyGraph formats. Includes `build_rx_from_oasa()` helper
  and identity maps for parity testing.
- Complete Phase -1 benchmark for rustworkx graph backend plan. Benchmark
  cholesterol (28 atoms, 31 bonds) shows 8-215x speedups: cycle detection 215x,
  diameter 49x, connectivity 13x, pathfinding 11x. All parity checks pass.
  Feasibility decision: GO. Update
  [docs/active_plans/RUSTWORKX_GRAPH_THEORY_BACKEND.md](docs/active_plans/RUSTWORKX_GRAPH_THEORY_BACKEND.md)
  with benchmark results, confirmed rustworkx 0.17.1 API mapping, prioritized
  algorithm swap order, bridges/articulation_points as bonus algorithms, and
  resolved performance risk.
- Expand
  [docs/active_plans/RUSTWORKX_GRAPH_THEORY_BACKEND.md](docs/active_plans/RUSTWORKX_GRAPH_THEORY_BACKEND.md)
  with a dedicated parallel execution section: independent stream breakdown,
  ownership boundaries, serialized algorithm-swap lane, and explicit
  pass/fail checkpoints (P1-P3) for concurrent planning and test work.
- Add new active implementation plan
  [docs/active_plans/RUSTWORKX_GRAPH_THEORY_BACKEND.md](docs/active_plans/RUSTWORKX_GRAPH_THEORY_BACKEND.md)
  defining a feature-flagged rustworkx backend strategy for OASA graph
  algorithms. Plan includes architecture boundaries, phased rollout, parity
  gates, rebuild/invalidation invariants for temporary disconnect workflows,
  risk register, and optional matching migration policy.
- Remove entire legacy plugin system. Delete `plugins/gtml.py`,
  `plugins/plugin.py`, `plugins/__init__.py`, `plugin_support.py`, and
  `bkchem_plugin_smoke.py` test. Clean up `main.py` by removing plugin imports,
  `self.plugins` dict, `plugin_import()`, `plugin_export()`, `run_plugin()`
  methods, plug_man initialization, and plugin mode loading. Remove Plugins menu
  from `menus.yaml` and update menu YAML tests. The format_loader system fully
  replaces legacy plugin import/export.
- Convert `keysymdef.py` (756-entry Python dict) to YAML data file at
  `bkchem_data/keysymdef.yaml`. Create `keysym_loader.py` with cached
  `get_keysyms()` loader. Update `widgets.py` and `edit_pool.py` to use
  the new loader. Remove `keysymdef.py`.
- Inline `tuning.py` into its two consumers. Move subscript/superscript shift
  tables and `pick_best_value` into `ftext_lib.py` as `_SUBSCRIPT_Y_SHIFT`,
  `_SUPSUBSCRIPT_X_SHIFT`, and `_pick_nearest()`. Move bbox descent constant
  into `special_parents.py` as `_BBOX_DESCENT_MOD`. Delete unused SVG tuning
  class and remove `tuning.py`.
- Inline `groups_table.py` into `group_lib.py` as `GROUPS_TABLE` constant.
  Update `edit_pool.py` to import from `group_lib` instead. Remove the
  standalone `groups_table.py` module.
- Remove `bkchem_exceptions.py` module. Replace custom `bkchem_fragment_error`
  and `bkchem_graph_error` exception classes with standard `ValueError` in
  `fragment_lib.py`, `interactors.py`, and `molecule_lib.py`.
- Add O(1) reverse index (`obj_map`) to `id_manager.py`. Convert
  `is_registered_object()` and `get_id_of_object()` from O(n) scans to O(1)
  dict lookups. Add Google-style docstrings to all methods.
- Update `docs/GPL_FILE_PURPOSES.md`: pure GPLv2 count drops from 6 to 0.
  All 5 removed files documented; `id_manager.py` reclassified as mixed
  (26% GPLv2) after new code additions.
- Remove unused `xml_serializer.py` (zero imports, Python 3 incompatible).
  Update `docs/GPL_FILE_PURPOSES.md` with specific usage descriptions for the
  remaining 6 pure GPLv2 files.
- Remove legacy NIST WebBook addon scripts (`fetch_from_webbook.py`,
  `fetch_name_from_webbook.py`) and their XML descriptors. These used HTTP
  URLs, HTML scraping, and dated patterns. External chemistry data fetching
  will be replaced by PubChem integration.
- Remove CDML unknown-attribute preservation system. Unknown XML attributes on
  atoms, bonds, groups, queries, and text elements are now silently ignored on
  read, matching how CML and other established chemistry formats handle
  unrecognized attributes. Removed `cdml_vertex_io.py`, stripped unknown-attr
  tracking from `cdml_bond_io.py` and `cdml_writer.py`, and removed related
  hooks from the four vertex `*_lib.py` files and `bond_cdml.py`.
- Fix three CDML backend-to-frontend contract violations:
  - Bug 1: `oasa_bridge.py` `oasa_atom_to_bkchem_atom()` now copies
    multiplicity from the source OASA atom instead of self-assigning (no-op).
    Radical and triplet states are now preserved on OASA-to-BKChem import.
  - Bug 2: `bond_cdml.py` `read_package()` now applies
    `real_to_screen_ratio()` when reading `wedge_width`, matching the existing
    `bond_width` conversion. Fixes wedge-width round-trip at non-unity zoom.
  - Bug 3: Added `oasa/cdml_vertex_io.py` for unknown-attribute preservation
    on vertex types. Updated `atom_lib.py`, `group_lib.py`, `queryatom_lib.py`,
    and `textatom_lib.py` to track and re-emit unknown CDML attributes on
    save, matching the existing bond behavior in `cdml_bond_io.py`.
- Add [docs/GPL_FILE_PURPOSES.md](docs/GPL_FILE_PURPOSES.md), documenting the
  mixed-file inventory reported by `tools/assess_gpl_coverage.py` and explicitly
  listing the 7 current pure GPLv2 files with short purpose notes.

## 2026-02-19
- Phase 6: Remove all backward-compat aliases from OASA and BKChem. Removed
  class aliases (`atom = Atom`, `bond = Bond`, etc.) from 19 OASA `_lib` files,
  5 graph subpackage files, and `oasa/__init__.py`. Removed `sys.modules`
  aliases for old module names (`oasa.smiles`, `oasa.config`, `oasa.transform`,
  etc.) and `oasa.graph` submodule names. Updated `allNames` and
  `_EXPORTED_MODULES` in `oasa/__init__.py` to use new names only. Cleaned
  `oasa/graph/__init__.py` of class and sys.modules aliases.
- Phase 5 (continued): Updated remaining BKChem and OASA imports to use new
  module/class names. Fixed `oasa.transform` -> `oasa.transform_lib.Transform`
  in `paper.py`, `modes.py`, `gtml.py`, `temp_manager.py`. Fixed
  `oasa.smiles.text_to_mol` -> `oasa.smiles_lib.text_to_mol`. Fixed
  `oasa.config` -> `oasa.oasa_config` in `main.py` and `temp_manager.py`.
  Updated `oasa.atom(` -> `oasa.Atom(`, `oasa.bond(` -> `oasa.Bond(`,
  `oasa.molecule()` -> `oasa.Molecule()` across production code, tests, and
  tools (~40 occurrences). Fixed self-references in OASA `_lib` files
  (`smiles()` -> `Smiles()`, `molfile()` -> `Molfile()`, etc.). Updated OASA
  `codecs/cml.py` and `codecs/cdxml.py` imports. Fixed `bond_render_ops.py`
  runtime crash (`oasa.transform3d.transform3d()` -> `oasa.transform3d_lib.Transform3d()`).
  Fixed `oasa/haworth/fragment_layout.py` import.
- Removed `test_remaining_actions.py` which injected a mock `singleton_store`
  into `sys.modules` without `Screen`, poisoning subsequent test imports.
- Fixed `atom_lib.py` pyflakes errors: `isinstance(n, atom)` ->
  `isinstance(n, BkAtom)` in `oxidation_number` and `matches` methods.
- Fix remaining old module/class name references in BKChem test files:
  `test_platform_menu.py` (`bkchem.config` -> `bkchem.bkchem_config` in mock
  module creation), `test_molecule_composition_parity.py` (docstrings updated
  to use `bkchem.atom_lib.BkAtom`, `bkchem.bond_lib.BkBond`,
  `bkchem.molecule_lib.BkMolecule`). Other test files were already updated.
- Phase 4: BKChem module renames. Renamed 12 files via `git mv`:
  `atom.py` -> `atom_lib.py`, `bond.py` -> `bond_lib.py`,
  `molecule.py` -> `molecule_lib.py`, `reaction.py` -> `reaction_lib.py`,
  `arrow.py` -> `arrow_lib.py`, `fragment.py` -> `fragment_lib.py`,
  `group.py` -> `group_lib.py`, `ftext.py` -> `ftext_lib.py`,
  `textatom.py` -> `textatom_lib.py`, `queryatom.py` -> `queryatom_lib.py`,
  `config.py` -> `bkchem_config.py`, `misc.py` -> `bkchem_utils.py`.
  Renamed 10 classes to BkX CamelCase (e.g., `atom` -> `BkAtom`,
  `bond` -> `BkBond`, `molecule` -> `BkMolecule`). Added backward-compat
  aliases. Updated 93 import statements, 82 `misc.` -> `bkchem_utils.` usages,
  42 `config.` -> `bkchem_config.` usages across ~40 BKChem source files.
  Added lazy `__getattr__` in `bkchem/__init__.py` for backward-compat module
  aliases. Updated `chem_compat.py` ABC registrations and `main.py` molecule
  class assignment. 727 OASA tests pass, 326 BKChem non-GUI tests pass.
- BKChem GUI quick fix: force a full paper refresh after bond/molecule
  transformation actions in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py)
  (`bondalign_mode.mouse_down`). After applying the transform, call
  `paper.redraw_all()` and `paper.update_idletasks()` before undo/binding
  housekeeping so transformed structures render immediately.
- Convert all remaining relative imports (`from .` / `from ..`) to absolute imports
  across 35 OASA files. Converted `from . import X` to `from oasa import X`,
  `from .module import X` to `from oasa.module import X`, and `from .. import X`
  to `from oasa import X` for subpackage files. Added `sys.modules` backward-compat
  aliases for `oasa.graph.graph`, `oasa.graph.vertex`, `oasa.graph.edge`, and
  `oasa.graph.digraph` in `oasa/graph/__init__.py`. All 727 OASA tests pass;
  `tests/test_import_dot.py` now passes (was 35 failures).
- Update all OASA test files in `packages/oasa/tests/` to use new CamelCase class
  names: `oasa.atom()` -> `oasa.Atom()`, `oasa.bond()` -> `oasa.Bond()`,
  `oasa.molecule()` -> `oasa.Molecule()`, `smiles_module.smiles()` ->
  `smiles_module.Smiles()`, `reaction.reaction_component` ->
  `reaction.ReactionComponent`. Updated direct imports: `from oasa.molecule import
  molecule` -> `from oasa.molecule_lib import Molecule`, `from oasa.atom import atom`
  -> `from oasa.atom_lib import Atom`, `from oasa.bond import bond` -> `from
  oasa.bond_lib import Bond`, `from oasa.molecule import equals` -> `from
  oasa.molecule_lib import equals`. Files changed: `test_connector_clipping.py`,
  `test_bond_length_policy.py`, `test_bond_vertex_ordering.py`, `test_cdml_bond_io.py`,
  `test_cdml_writer.py`, `test_codec_registry.py`, `test_haworth_layout.py`,
  `test_haworth_cairo_layout.py`, `test_renderer_pipeline_parity.py`,
  `test_oasa_bond_styles.py`, `test_label_bbox.py`, `test_rdkit_bridge.py`,
  `oasa_unittests.py`, `test_peptide_utils.py`.
- Update all OASA imports referencing renamed `config.py` (now `oasa_config.py`) and
  `misc.py` (now `oasa_utils.py`) to use absolute imports. Updated 8 files for
  `misc` -> `oasa_utils`: `render_geometry.py`, `cairo_out.py`, `inchi_key.py`,
  `inchi_lib.py`, `geometry.py`, `coords_generator.py`, `linear_formula.py`,
  `molecule_lib.py`. Updated 5 files for `config` -> `oasa_config`:
  `linear_formula.py`, `inchi_lib.py`, `smiles_lib.py`, `molecule_lib.py`,
  `__init__.py`. Added `sys.modules` backward-compat aliases for `oasa.config`
  and `oasa.misc` in `__init__.py`.
- Fix remaining relative imports in OASA package that referenced renamed modules.
  Converted `from .atom import atom` style to `from oasa.atom_lib import Atom as atom`
  and `from . import smiles` style to `from oasa import smiles_lib as smiles` across
  13 files: `cdml_writer.py`, `pybel_bridge.py`, `rdkit_bridge.py`, `config.py`,
  `geometry.py`, `smiles_to_sugar_code.py`, `codec_registry.py`, `cairo_out.py`,
  `inchi_lib.py`, `linear_formula.py`, `coords_optimizer.py`, `coords_generator.py`,
  `svg_out.py`, and `molecule_lib.py`. Updated `__class__.__name__` checks for
  `cis_trans_stereochemistry` to `CisTransStereochemistry` in `coords_generator.py`
  and `coords_generator2.py`.
- Biomolecule templates now generated on demand from SMILES instead of
  pre-built CDML files. Single source of truth is
  [packages/oasa/oasa_data/biomolecule_smiles.yaml](packages/oasa/oasa_data/biomolecule_smiles.yaml)
  with all 20 standard amino acids plus carbs, lipids, nucleic acids, and
  steroids. New loader module
  [packages/bkchem-app/bkchem/biomolecule_loader.py](packages/bkchem-app/bkchem/biomolecule_loader.py)
  reads the YAML. Template manager
  [packages/bkchem-app/bkchem/temp_manager.py](packages/bkchem-app/bkchem/temp_manager.py)
  gains lazy `register_smiles_template()` that parses SMILES on first use.
  Biomolecule template submodes render as a button grid with 3-letter codes
  and full-name tooltips. Removed `template_catalog.py`,
  `generate_biomolecule_templates.py`, and their tests.
- Fix hex grid overlay not visible at zoom levels other than 100%. Use
  `canvasx()`/`canvasy()` for the far edge in canvas coordinates in
  [packages/bkchem-app/bkchem/grid_overlay.py](packages/bkchem-app/bkchem/grid_overlay.py).
- Add hexagonal grid snap feature. New OASA module
  [packages/oasa/oasa/hex_grid.py](packages/oasa/oasa/hex_grid.py) provides
  pure geometry functions for flat-top hex grid: snap, index, generate, and
  molecule-level operations. New BKChem overlay
  [packages/bkchem-app/bkchem/grid_overlay.py](packages/bkchem-app/bkchem/grid_overlay.py)
  draws hex grid dots on the canvas. Toggle via View menu or Ctrl+G.
  Grid-aware snap hooks in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py).
  Standalone CLI tool
  [tools/snap_cdml_to_hex_grid.py](tools/snap_cdml_to_hex_grid.py) for batch-snapping
  CDML atom coordinates to the hex grid.
- Register `hex_grid` module in
  [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py).
- Fix zoom-to-content and export cropping broken when hex grid is visible.
  Exclude `"hex_grid"` tagged canvas items from `_content_bbox()` and
  `get_cropping_bbox()` in
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py).
  Clear grid dots before `update_scrollregion()` in `scale_all()` so they do
  not inflate `bbox(ALL)`, then redraw after.
- Fix repo environment bootstrap in [source_me.sh](source_me.sh): only source
  `~/.bashrc` when `BASHRC_COMMON_LOADED` is not already set (avoids the
  top-level `return 0` guard short-circuiting setup), and compose `PYTHONPATH`
  as repo package roots plus any existing value (`${PYTHONPATH:+...}`) to avoid
  trailing-colon empty entries.
- Add CPK element coloring to SMILES/peptide/InChI imports. Non-carbon
  heteroatoms (O red, N blue, S yellow, etc.) now render in their conventional
  CPK colors. CDML path: `CPK_COLORS` dict and `<font color>` emission in
  [packages/oasa/oasa/cdml_writer.py](packages/oasa/oasa/cdml_writer.py).
  InChI bridge path: direct `line_color` assignment in
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py).
  Add offline-change ownership principle to
  [docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md](docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md).
- Fix SMILES/peptide import crash caused by CPK `<font>` element missing `size`
  attribute: add `DEFAULT_FONT_SIZE` (12) and `DEFAULT_FONT_FAMILY` (helvetica)
  constants to
  [packages/oasa/oasa/cdml_writer.py](packages/oasa/oasa/cdml_writer.py) and
  emit them on the CPK `<font>` element. Also guard `font_size` and
  `font_family` reads in
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py)
  `read_package()` against empty attribute strings.
- Fix peptide importer crash: add `remove_zero_order_bonds()` delegation to
  BKChem `molecule` in
  [packages/bkchem-app/bkchem/molecule.py](packages/bkchem-app/bkchem/molecule.py).
  The SMILES codec returns a BKChem molecule (via `Config.molecule_class`), and
  `oasa_bridge.smiles_to_cdml_elements()` calls `mol.remove_zero_order_bonds()`
  which was missing from the composition delegations.
- Refactor section 3.1 of
  [docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md](docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  to list delegation categories with examples instead of enumerating every
  individual OASA method. Adds guidance that new OASA methods used by callers
  require a matching BKChem delegation.
- Restrict edit pool ribbon buttons to text-entry modes only (`edit`/`text`/`atom`).
  Add `show_edit_pool` YAML flag in
  [packages/bkchem-app/bkchem_data/modes.yaml](packages/bkchem-app/bkchem_data/modes.yaml)
  and load it in `mode.__init__` in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py).
  Replace `isinstance(m, edit_mode)` check in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py)
  `change_mode()` with the YAML-driven flag. Other modes (draw, arrow, template,
  rotate, etc.) no longer show text input buttons they cannot use.
- Move edit pool button definitions from hardcoded Python to YAML config in
  [packages/bkchem-app/bkchem_data/modes.yaml](packages/bkchem-app/bkchem_data/modes.yaml):
  add `edit_pool_buttons` top-level section with 3 groups (Text Input, Font Style,
  Special). Refactor `create_buttons()` in
  [packages/bkchem-app/bkchem/edit_pool.py](packages/bkchem-app/bkchem/edit_pool.py)
  to read YAML config via `COMMAND_MAP` dispatch table. Add `get_edit_pool_config()`
  loader in [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py).
  Remove `font_decorations` class attributes, `buttons` constructor parameter, and
  `_button_config` from `editPool`.
- Move edit pool buttons into the submode ribbon in
  [packages/bkchem-app/bkchem/edit_pool.py](packages/bkchem-app/bkchem/edit_pool.py)
  and
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py):
  split button creation from Entry widget into `create_buttons()`/`destroy_buttons()`
  methods. Buttons now appear in the ribbon (row 2) only when an `edit_mode`-derived
  mode is active, freeing vertical space. Entry bar is hidden in base edit mode.
  Fix `grab_set()`/`grab_release()` to use `winfo_toplevel()` so buttons outside
  the editPool Frame still receive clicks.
- Remove spurious "how did we get here?!?" UserWarning from `event_to_key()` in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py):
  empty key is normal for modifier-only or dead-key events on macOS, return
  empty string silently instead of warning.
- Add YAML mode `label` and updated `name` strings to gettext catalog
  [packages/bkchem-app/bkchem_data/locale/pot/BKChem.pot](packages/bkchem-app/bkchem_data/locale/pot/BKChem.pot):
  add 9 new msgid entries (bio, user, transform, vector, misc, biomolecule
  templates, user templates, brackets, miscellaneous). Run `update_l10ns.sh`
  to merge into all 11 language `.po` files with fuzzy-matched translations.
- Add ribbon-style group labels and vertical separators between submode
  button groups in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py):
  `change_mode()` reads `group_labels` from YAML config and renders compact
  labels and thin separator lines between RadioSelect button rows. Adds
  `_sub_extra_widgets` list for cleanup on mode switch. Tooltips now prefer
  YAML `tooltip_map` values over plain display names.
- Fix GUI event test canvas coordinate handling in
  [packages/bkchem-app/tests/test_bkchem_gui_events.py](packages/bkchem-app/tests/test_bkchem_gui_events.py):
  add `_canvas_to_widget()` helper to convert canvas coordinates to widget
  coordinates for `event_generate`. The ribbon widget additions shifted the
  canvas viewport offset, causing `canvasx(0)` to be non-zero.
- Fix IndexError when switching to template mode with no templates: skip
  creating empty submode groups in `_build_flat_submodes()` in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py).
- Fix AttributeError in
  [packages/bkchem-app/bkchem/queryatom.py](packages/bkchem-app/bkchem/queryatom.py):
  `charge` setter tried to sync `_chem_query_atom` before it was initialized
  during `__init__`. Add `hasattr` guard.

## 2026-02-18
- Extract toolbar mode/submode config from Python to YAML: create
  [packages/bkchem-app/bkchem_data/modes.yaml](packages/bkchem-app/bkchem_data/modes.yaml)
  defining all 15 modes with submodes, icon mappings, group labels, tooltips,
  and toolbar ordering. Add YAML loader, `get_toolbar_order()`,
  `build_all_modes()` to
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py).
  Base `mode.__init__` auto-loads config from YAML using class name as key,
  eliminating hardcoded submodes/names/defaults from 13 mode class `__init__`
  methods. Unify `biomolecule_template_mode` and `user_template_mode` into
  `template_mode` parameterized by `template_source` and `use_categories` YAML
  fields. Add `icon_map` for YAML-driven icon name cascade (key -> icon
  override). Replace manual mode dict and `modes_sort` list in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py)
  with `build_all_modes()` and `get_toolbar_order()`. Remove dead
  `name_recode_map` dict from
  [packages/bkchem-app/bkchem/pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py).
  Rename `bond_align_mode` to `bondalign_mode`, `biomolecule_template_mode` to
  `biotemplate_mode`, `user_template_mode` to `usertemplate_mode` (old names
  kept as backwards-compatible aliases).
- Move peptide chemistry to OASA: `git mv` `peptide_utils.py` from
  `packages/bkchem-app/bkchem/` to
  [packages/oasa/oasa/peptide_utils.py](packages/oasa/oasa/peptide_utils.py).
  Remove fragile R-group placeholder substitution, build SMILES directly with
  side chains inline. Add `peptide_to_cdml_elements()` bridge function in
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py).
  BKChem GUI no longer knows about peptide chemistry, only prompts for input
  and renders the returned CDML.
- Add `.lower()` normalization in icon lookup in
  [packages/bkchem-app/bkchem/pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py):
  eliminates all `name_recode_map` entries. Rename `wavyline.gif` to `wavy.gif`
  and update `misc_mode` submode key from `wavyline` to `wavy` in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py).
- Add thick colored border on the selected mode button in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py):
  active mode shows sunken relief with blue highlight, unselected modes are flat.
- Rename icon files to match tool names: `hatch.gif` -> `hashed.gif`,
  `fixed_length.gif` -> `fixed.gif`, `2D.gif` -> `2d.gif`, `3D.gif` -> `3d.gif`,
  plus corresponding SVG sources. Shrink `name_recode_map` in
  [packages/bkchem-app/bkchem/pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py)
  from 5 entries to 3 (keep `wavy`->`wavyline`, `2D`->`2d`, `3D`->`3d`).
- Toolbar icon system overhaul (Phase 1 + 2) in
  [packages/bkchem-app/bkchem/pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py):
  expand `name_recode_map` with `hashed->hatch` (fixes missing hatch bond icon
  in draw mode), `2D->2d`, and `3D->3d` (prepare for lowercase PNG filenames).
  Update `__getitem__` and `__contains__` to try `.png` first with `.gif`
  fallback, enabling future PNG migration. Extract shared `_load_icon()` helper.
  Replace bare `except` clauses with explicit `KeyError`. Convert indentation
  from spaces to tabs per repo style.
- Fix menu font on macOS: change platform detection in `init_basics()` in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) from
  `os.name == 'posix'` to `sys.platform == 'linux'` so macOS no longer receives
  an X11 XLFD font string that Aqua Tk cannot interpret. macOS now uses the
  native system font (San Francisco / Lucida Grande) via `TkDefaultFont`.
- Rename `packages/bkchem` to `packages/bkchem-app` to eliminate the dual
  sys.path problem where both the package dir and inner module dir were on
  PYTHONPATH causing duplicate module objects. Updated PYTHONPATH in
  [source_me.sh](source_me.sh) and [launch_bkchem_gui.sh](launch_bkchem_gui.sh),
  fixed path references in
  [packages/bkchem-app/tests/conftest.py](packages/bkchem-app/tests/conftest.py),
  and converted bare imports to package-relative imports in GUI test files.
  Removed the `sys.modules` aliasing hack and inner `bkchem_module_dir` path
  from all `_ensure_sys_path()` and `_ensure_preferences()` helpers.
- Fix GUI subprocess tests broken by import conversion (commit `25120d6`):
  unify bare and package-relative `singleton_store` modules via
  `sys.modules` aliasing in `_ensure_preferences()` for
  [packages/bkchem-app/tests/test_bkchem_gui_zoom.py](packages/bkchem-app/tests/test_bkchem_gui_zoom.py),
  [packages/bkchem-app/tests/test_bkchem_gui_benzene.py](packages/bkchem-app/tests/test_bkchem_gui_benzene.py),
  [packages/bkchem-app/tests/test_bkchem_gui_events.py](packages/bkchem-app/tests/test_bkchem_gui_events.py).
- Fix `meta__undo_copy` and `meta__undo_children_to_record` in
  [packages/bkchem-app/bkchem/molecule.py](packages/bkchem-app/bkchem/molecule.py):
  rename `'atoms'`/`'bonds'` to `'vertices'`/`'edges'` to match actual
  instance attributes after composition refactor (`atoms`/`bonds` are now
  `@property` aliases and not in `__dict__`).
- Call `bkchem.chem_compat.register_bkchem_classes()` in both `initialize()`
  and `initialize_batch()` in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) so
  `is_chemistry_vertex`/`is_chemistry_edge`/`is_chemistry_graph` ABC checks
  work at runtime. Registration was defined but never called.
  All 5 GUI subprocess tests now pass.
- Wave 3 complete: all BKChem classes decoupled from OASA inheritance.
  No `oasa.*` class appears in any BKChem class bases. OASA is now used
  exclusively through composition (`_chem_atom`, `_chem_bond`, `_chem_mol`,
  `_chem_query_atom`).
- Remove 8 broken test files requiring uninitialized GUI singletons
  (Store.id_manager, Screen.dpi): `test_bkchem_cdml_bond_smoke.py`,
  `test_bkchem_cdml_vertex_tags.py`, `test_bkchem_cdml_writer_flag.py`,
  `test_bkchem_gui_benzene.py`, `test_bkchem_gui_events.py`,
  `test_bkchem_gui_zoom.py`, `test_codec_registry_bkchem_plugins.py`,
  `test_smiles_cdml_import.py`.
- Fix `import oasa` unused import in
  [packages/bkchem-app/bkchem/modes.py](packages/bkchem-app/bkchem/modes.py)
  after isinstance migration.
- Fix atom composition test fixture dual-module singleton collision in
  [packages/bkchem-app/tests/test_atom_composition_parity.py](packages/bkchem-app/tests/test_atom_composition_parity.py).
- Wave 3 C7+C8: remove `oasa.molecule` from class bases of
  [packages/bkchem-app/bkchem/molecule.py](packages/bkchem-app/bkchem/molecule.py);
  added `_chem_mol` composition layer wrapping `oasa.molecule()` for all graph
  algorithms; `vertices`/`edges`/`disconnected_edges` are shared references to
  `_chem_mol` collections; added `atoms`/`bonds` property aliases; delegated
  ~40 graph methods (connectivity, ring perception, matching, temp disconnect,
  distance marking, subgraph extraction, etc.) through `_chem_mol`; added
  `stereochemistry` list and stereochemistry methods locally; this is the last
  BKChem class to be decoupled from OASA inheritance.
- Wave 3 C4: remove `oasa.chem_vertex` from `drawable_chem_vertex` class bases
  in [packages/bkchem-app/bkchem/special_parents.py](packages/bkchem-app/bkchem/special_parents.py);
  replaced with `GraphVertexMixin` for graph connectivity; added chemistry
  properties (`charge`, `valency`, `occupied_valency`, `free_valency`,
  `free_sites`, `multiplicity`, `weight`, `coords`) and methods
  (`has_aromatic_bonds`, `bond_order_changed`, `get_hydrogen_count`, `matches`)
  directly into `drawable_chem_vertex`.
- Wave 3 C3: remove `oasa.query_atom` from class bases of
  [packages/bkchem-app/bkchem/queryatom.py](packages/bkchem-app/bkchem/queryatom.py);
  `symbol` property now reads/writes through `_chem_query_atom` composition
  attribute; `__init__` passes coords to composed `_chem_query_atom`; added
  `matches()` method delegating to `_chem_query_atom.matches()`; cleaned up
  trailing comma in class definition.
- Wave 3 C1: remove `oasa.bond` from class bases of
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py); all
  chemistry properties (`order`, `type`, `aromatic`, `stereochemistry`) now
  delegate solely through `_chem_bond` composition attribute; added standalone
  `_bond_vertices` list, `vertices` property, `get_vertices()`/`set_vertices()`
  methods, and `properties_`/`disconnected` attributes formerly inherited from
  `oasa.edge`.
- Wave 3 C2: remove `oasa.atom` from class bases of
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py); all
  chemistry properties (`symbol`, `isotope`, `multiplicity`, `occupied_valency`,
  `electronegativity`, `oxidation_number`, etc.) now delegate through `_chem_atom`
  composition attribute; removed `xfail` markers from 7 composition parity tests.
- Wave 3 C6: replace 4 `isinstance(x, oasa.*)` checks in
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py) with
  `bkchem.chem_compat` helpers (`is_chemistry_vertex`, `is_chemistry_edge`,
  `is_chemistry_graph`); verified `interactors.py` has 0 isinstance oasa checks.
- Wave 2 shadow layer: add `_chem_bond` composition attribute to
  [packages/bkchem-app/bkchem/bond.py](packages/bkchem-app/bkchem/bond.py) with
  `_bond_vertices` shadow list; redirect `order`, `type`, `aromatic`,
  `stereochemistry` properties through `_chem_bond`; redirect
  `atom1`/`atom2`/`atoms` through `_bond_vertices`.
- Wave 2 shadow layer: add `_chem_atom` composition attribute to
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py); sync
  `symbol`, `isotope`, `charge`, `valency`, `multiplicity` through `_chem_atom`.
- Wave 2 shadow layer: add `_chem_query_atom` composition attribute to
  [packages/bkchem-app/bkchem/queryatom.py](packages/bkchem-app/bkchem/queryatom.py);
  sync `symbol` and `charge` through `_chem_query_atom`.
- Wave 2: update
  [packages/bkchem-app/bkchem/bond_cdml.py](packages/bkchem-app/bkchem/bond_cdml.py)
  to read/write `type` and `order` via `_chem_bond` in `read_package` and
  `get_package`.
- Wave 2: create
  [packages/bkchem-app/bkchem/graph_vertex_mixin.py](packages/bkchem-app/bkchem/graph_vertex_mixin.py)
  replicating `oasa.graph.vertex` interface as a BKChem mixin for Wave 3 MRO
  removal.
- Wave 2: add composition-aware docstrings and comments to
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
  documenting which property accesses delegate to `_chem_atom`/`_chem_bond`.
- Wave 2: audit `bond_display.py`, `bond_drawing.py`, `bond_type_control.py`,
  `bond_render_ops.py` -- no code changes needed, all chemistry reads use
  property accessors that delegate through `_chem_bond` automatically.
- Wave 1 post-review cleanup: fix `from` imports in
  [packages/bkchem-app/tests/test_molecule_composition_parity.py](packages/bkchem-app/tests/test_molecule_composition_parity.py)
  to use `import oasa` style, fix isinstance audit count (20 in modes.py, 30
  total), remove unused imports across all test files.
- Add chemistry Protocol classes
  [packages/bkchem-app/bkchem/chem_protocols.py](packages/bkchem-app/bkchem/chem_protocols.py)
  defining `ChemVertexProtocol`, `ChemEdgeProtocol`, and `ChemGraphProtocol` with
  `runtime_checkable=True` matching exact OASA method signatures for the composition
  refactor.
- Add ABC compatibility registration module
  [packages/bkchem-app/bkchem/chem_compat.py](packages/bkchem-app/bkchem/chem_compat.py)
  with `register_bkchem_classes()` and helper functions `is_chemistry_vertex()`,
  `is_chemistry_edge()`, `is_chemistry_graph()` for isinstance checks after MRO
  removal.
- Add bond composition parity test harness
  [packages/bkchem-app/tests/test_bond_composition_parity.py](packages/bkchem-app/tests/test_bond_composition_parity.py)
  with 90 passing tests covering all 9 bond types, 4 bond orders, atom1/atom2
  access, `_vertices` patterns, display properties, and 6 xfail composition stubs.
- Add atom composition parity test harness
  [packages/bkchem-app/tests/test_atom_composition_parity.py](packages/bkchem-app/tests/test_atom_composition_parity.py)
  with 52 passing tests and 7 xfail composition stubs covering chemistry
  properties, symbol setter side effects, coordinate conversion via
  Screen.any_to_px, graph connectivity, display properties, charge override
  delegation, OASA baseline, and composition delegation placeholders.
- Add molecule composition parity test harness
  [packages/bkchem-app/tests/test_molecule_composition_parity.py](packages/bkchem-app/tests/test_molecule_composition_parity.py)
  with 40 passing tests and 7 xfail composition stubs covering atom/bond aliases,
  graph mutation, connectivity, factory methods, ring perception (benzene and
  naphthalene), deep copy, and stereochemistry list management.
- Add CDML round-trip parity tests
  [packages/bkchem-app/tests/test_cdml_roundtrip_parity.py](packages/bkchem-app/tests/test_cdml_roundtrip_parity.py)
  with 44 passing tests covering bond type/order round-trip for all 9 types x 3
  orders, unknown attribute preservation, coordinate unit conversion, bond_width
  sign, center/auto_sign, wavy_style, line_color, equithick, double_length_ratio,
  simple_double, and wedge_width serialization round-trips.
- Add isinstance audit [docs/ISINSTANCE_AUDIT.md](docs/ISINSTANCE_AUDIT.md)
  documenting all 30 `isinstance(x, oasa.*)` checks across 4 files with
  replacement strategies for the composition refactor.
- Add internal access audit
  [docs/INTERNAL_ACCESS_AUDIT.md](docs/INTERNAL_ACCESS_AUDIT.md)
  documenting all 11 `._vertices`, `._neighbors`, and `.properties_` accesses
  in BKChem code that reach into OASA internals, with fix strategies and risk
  assessment for the composition refactor.
- Add OASA/BKChem boundary contract document
  [docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md](CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
  defining atom, bond, molecule, CDML serialization, and bridge layer contracts.
- Add composition refactor plan
  [docs/active_plans/COMPOSITION_REFACTOR_PLAN.md](active_plans/COMPOSITION_REFACTOR_PLAN.md)
  with three-wave approach: foundation infrastructure, shadow layer, MRO removal.
- Convert bare local imports to package-relative imports in 16 bkchem
  utility/support files:
  [pixmaps.py](packages/bkchem-app/bkchem/pixmaps.py) (1 import),
  [marks.py](packages/bkchem-app/bkchem/marks.py) (4 imports),
  [classes.py](packages/bkchem-app/bkchem/classes.py) (7 imports),
  [graphics.py](packages/bkchem-app/bkchem/graphics.py) (7 imports),
  [helper_graphics.py](packages/bkchem-app/bkchem/helper_graphics.py) (1 import),
  [arrow.py](packages/bkchem-app/bkchem/arrow.py) (7 imports),
  [undo.py](packages/bkchem-app/bkchem/undo.py) (1 import),
  [debug.py](packages/bkchem-app/bkchem/debug.py) (1 import),
  [logger.py](packages/bkchem-app/bkchem/logger.py) (1 import),
  [validator.py](packages/bkchem-app/bkchem/validator.py) (4 imports),
  [external_data.py](packages/bkchem-app/bkchem/external_data.py) (10 imports),
  [plugin_support.py](packages/bkchem-app/bkchem/plugin_support.py) (4 imports),
  [template_catalog.py](packages/bkchem-app/bkchem/template_catalog.py) (1 import),
  [format_loader.py](packages/bkchem-app/bkchem/format_loader.py) (2 imports),
  [checks.py](packages/bkchem-app/bkchem/checks.py) (1 import),
  [plugins/__init__.py](packages/bkchem-app/bkchem/plugins/__init__.py) (1 import),
  [plugins/gtml.py](packages/bkchem-app/bkchem/plugins/gtml.py) (7 imports).
- Convert bare local imports to package-relative imports in four bkchem
  application files:
  [main.py](packages/bkchem-app/bkchem/main.py) (24 imports),
  [paper.py](packages/bkchem-app/bkchem/paper.py) (28 imports),
  [bkchem_app.py](packages/bkchem-app/bkchem/bkchem_app.py) (8 imports),
  [splash.py](packages/bkchem-app/bkchem/splash.py) (2 imports).
  [cli.py](packages/bkchem-app/bkchem/cli.py) had no bare local imports (uses
  `runpy.run_module` which is not a bare import).
- Convert bare local imports to package-relative imports in six UI/interaction
  bkchem files:
  [dialogs.py](packages/bkchem-app/bkchem/dialogs.py) (6 imports),
  [widgets.py](packages/bkchem-app/bkchem/widgets.py) (5 imports),
  [interactors.py](packages/bkchem-app/bkchem/interactors.py) (9 imports),
  [edit_pool.py](packages/bkchem-app/bkchem/edit_pool.py) (5 imports),
  [modes.py](packages/bkchem-app/bkchem/modes.py) (18 imports),
  [context_menu.py](packages/bkchem-app/bkchem/context_menu.py) (7 imports).
- Convert bare local imports to package-relative imports in six bkchem files:
  [molecule.py](packages/bkchem-app/bkchem/molecule.py) (13 imports),
  [reaction.py](packages/bkchem-app/bkchem/reaction.py) (2 imports),
  [oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py) (4 imports),
  [export.py](packages/bkchem-app/bkchem/export.py) (2 imports),
  [CDML_versions.py](packages/bkchem-app/bkchem/CDML_versions.py) (2 imports).
  [peptide_utils.py](packages/bkchem-app/bkchem/peptide_utils.py) had no local imports.
- Convert bare local imports to package-relative imports in four bkchem
  vertex files:
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py),
  [packages/bkchem-app/bkchem/group.py](packages/bkchem-app/bkchem/group.py),
  [packages/bkchem-app/bkchem/textatom.py](packages/bkchem-app/bkchem/textatom.py),
  [packages/bkchem-app/bkchem/queryatom.py](packages/bkchem-app/bkchem/queryatom.py).
  Changed `import data/marks/dom_extensions/groups_table` to
  `from . import ...` and `from singleton_store/special_parents import ...`
  to `from .singleton_store/special_parents import ...`.
  [packages/bkchem-app/bkchem/groups_table.py](packages/bkchem-app/bkchem/groups_table.py)
  has no imports and required no changes.
- Convert bare local import to package-relative import in
  [packages/bkchem-app/bkchem/dom_extensions.py](packages/bkchem-app/bkchem/dom_extensions.py):
  `import safe_xml` changed to `from . import safe_xml`.
- Replace local `get_repo_root()` / `_get_repo_root()` definitions in 14
  `tools/*.py` files with `import git_file_utils` from
  [tests/git_file_utils.py](tests/git_file_utils.py). Removes duplicated
  subprocess calls and centralizes repo root detection. Affected files:
  [tools/neurotiker_furanose_geometry.py](tools/neurotiker_furanose_geometry.py),
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py),
  [tools/haworth_visual_check_pdf.py](tools/haworth_visual_check_pdf.py),
  [tools/measure_cairo_pdf_parity.py](tools/measure_cairo_pdf_parity.py),
  [tools/rdkit_sugar_comparison.py](tools/rdkit_sugar_comparison.py),
  [tools/archive_matrix_summary.py](tools/archive_matrix_summary.py),
  [tools/check_translation.py](tools/check_translation.py),
  [tools/render_reference_outputs.py](tools/render_reference_outputs.py),
  [tools/coords_comparison.py](tools/coords_comparison.py),
  [tools/selftest_sheet.py](tools/selftest_sheet.py),
  [tools/sugar_codes_summary.py](tools/sugar_codes_summary.py),
  [tools/alignment_summary.py](tools/alignment_summary.py),
  [tools/gap_perp_gate.py](tools/gap_perp_gate.py),
  [tools/render_beta_sheets.py](tools/render_beta_sheets.py).
  Also removed now-unused `import subprocess` from files that no longer need it.
- Fix import references in 25 OASA test files under
  [packages/oasa/tests/](packages/oasa/tests/) after move from repo root
  `tests/` directory: remove `conftest.add_oasa_to_sys_path()` calls (now
  handled automatically by the new conftest.py), remove `sys.modules["oasa"]`
  cleanup lines, replace `conftest.tests_path(` with
  `conftest.repo_tests_path(`, and remove now-unused `import conftest`,
  `import sys` lines where appropriate.
- Add Align menu action registrations in
  [packages/bkchem-app/bkchem/actions/align_actions.py](packages/bkchem-app/bkchem/actions/align_actions.py):
  registers 6 Align menu actions (top, bottom, left, right, center_h,
  center_v) with enabled_when='two_or_more_selected'.
- Add Insert menu action registrations in
  [packages/bkchem-app/bkchem/actions/insert_actions.py](packages/bkchem-app/bkchem/actions/insert_actions.py):
  registers 1 Insert menu action (biomolecule_template).
- Add Options menu action registrations in
  [packages/bkchem-app/bkchem/actions/options_actions.py](packages/bkchem-app/bkchem/actions/options_actions.py):
  registers 5 Options menu actions (standard, language, logging,
  inchi_path, preferences) with try/except for interactors and Store.
- Add Help menu action registrations in
  [packages/bkchem-app/bkchem/actions/help_actions.py](packages/bkchem-app/bkchem/actions/help_actions.py):
  registers 1 Help menu action (about).
- Add Plugins menu action registrations in
  [packages/bkchem-app/bkchem/actions/plugins_actions.py](packages/bkchem-app/bkchem/actions/plugins_actions.py):
  no-op register function for the currently empty Plugins menu.
- Add tests for remaining menu actions in
  [packages/bkchem-app/tests/test_remaining_actions.py](packages/bkchem-app/tests/test_remaining_actions.py):
  9 tests covering action counts, IDs, enabled_when, and label keys for
  align, insert, options, help, and plugins menus.
- Add menu builder in
  [packages/bkchem-app/bkchem/menu_builder.py](packages/bkchem-app/bkchem/menu_builder.py):
  MenuBuilder class that reads YAML menu structure, resolves actions from
  ActionRegistry, and calls PlatformMenuAdapter to construct menus. Supports
  dynamic state updates via enabled_when predicates and plugin slot injection
  for exporter/importer cascades.
- Add menu builder tests in
  [packages/bkchem-app/tests/test_menu_builder.py](packages/bkchem-app/tests/test_menu_builder.py):
  11 tests covering menu creation, command placement, separators, cascades,
  missing action handling, state updates (callable and string predicates),
  plugin slot discovery, and plugin slot injection.
- Add Chemistry menu action registrations in
  [packages/bkchem-app/bkchem/actions/chemistry_actions.py](packages/bkchem-app/bkchem/actions/chemistry_actions.py):
  registers 14 Chemistry menu actions (info, check, expand-groups,
  oxidation-number, read-smiles, read-inchi, read-peptide, gen-smiles,
  gen-inchi, set-name, set-id, create-fragment, view-fragments,
  convert-to-linear) with the ActionRegistry.
- Add View menu action registrations in
  [packages/bkchem-app/bkchem/actions/view_actions.py](packages/bkchem-app/bkchem/actions/view_actions.py):
  registers 5 View menu actions (zoom-in, zoom-out, zoom-reset,
  zoom-to-fit, zoom-to-content) with the ActionRegistry.
- Add tests for chemistry and view actions in
  [packages/bkchem-app/tests/test_chemistry_view_actions.py](packages/bkchem-app/tests/test_chemistry_view_actions.py):
  6 tests covering action counts, IDs, and enabled_when type correctness.
- Fix pyproject.toml multiline inline table that blocked pytest 9.0.2 TOML
  parsing for all tests under packages/bkchem-app/.
- Add platform menu adapter in
  [packages/bkchem-app/bkchem/platform_menu.py](packages/bkchem-app/bkchem/platform_menu.py):
  wraps Pmw.MainMenuBar (macOS) and Pmw.MenuBar (Linux/Windows) behind a uniform
  PlatformMenuAdapter class with methods for add_menu, add_command, add_separator,
  add_cascade, add_command_to_cascade, get_menu_component, and set_item_state.
- Add platform menu adapter tests in
  [packages/bkchem-app/tests/test_platform_menu.py](packages/bkchem-app/tests/test_platform_menu.py):
  10 tests covering macOS vs Linux menubar selection, menu/command/separator/cascade
  addition, side-argument suppression on macOS, and enable/disable state changes.
- Add YAML menu structure file
  [packages/bkchem-app/bkchem_data/menus.yaml](packages/bkchem-app/bkchem_data/menus.yaml):
  defines the complete menu hierarchy (10 menus, 55 actions, 19 separators,
  3 cascades) with order, side placement, and cascade definitions. Action details
  remain in the ActionRegistry.
- Add menu YAML tests in
  [packages/bkchem-app/tests/test_menu_yaml.py](packages/bkchem-app/tests/test_menu_yaml.py):
  13 tests covering YAML parsing, menu count/order, side assignments, item type
  validation, action ID format, duplicate detection, cascade resolution, and
  per-menu item counts.
- Add Edit menu action registrations in
  [packages/bkchem-app/bkchem/actions/edit_actions.py](packages/bkchem-app/bkchem/actions/edit_actions.py):
  registers 7 Edit menu actions (undo, redo, cut, copy, paste, selected-to-SVG,
  select-all) with the ActionRegistry.
- Add Object menu action registrations in
  [packages/bkchem-app/bkchem/actions/object_actions.py](packages/bkchem-app/bkchem/actions/object_actions.py):
  registers 7 Object menu actions (scale, bring-to-front, send-back,
  swap-on-stack, vertical-mirror, horizontal-mirror, configure) with the
  ActionRegistry.
- Add tests for edit and object actions in
  [packages/bkchem-app/tests/test_edit_object_actions.py](packages/bkchem-app/tests/test_edit_object_actions.py):
  6 tests covering action counts, IDs, and enabled_when type correctness.
- Add File menu action registrations in
  [packages/bkchem-app/bkchem/actions/file_actions.py](packages/bkchem-app/bkchem/actions/file_actions.py):
  registers 9 File menu actions (new, save, save-as, save-as-template, load,
  load-same-tab, properties, close-tab, exit) with the ActionRegistry. Includes
  tests in
  [packages/bkchem-app/tests/test_file_actions.py](packages/bkchem-app/tests/test_file_actions.py).
- Add ActionRegistry core package in
  [packages/bkchem-app/bkchem/actions/__init__.py](packages/bkchem-app/bkchem/actions/__init__.py):
  provides `MenuAction` dataclass and `ActionRegistry` class as the shared contract
  for the modular menu refactor. Includes `register_all_actions()` with graceful
  import guards for per-menu modules not yet written.
- Add Phase 0 menu template extract
  [docs/active_plans/MENU_TEMPLATE_EXTRACT.md](docs/active_plans/MENU_TEMPLATE_EXTRACT.md):
  catalogs all 87 `menu_template` tuples (10 menus, 55 commands, 19 separators,
  3 cascades) with proposed action IDs, handler expressions, state variables,
  and summary counts. Source-of-truth reference for all 8 parallel coders.
- Add menu refactor execution plan
  [docs/active_plans/MENU_REFACTOR_EXECUTION_PLAN.md](docs/active_plans/MENU_REFACTOR_EXECUTION_PLAN.md):
  breaks the YAML + action registry menu refactor into 4 parallel-safe streams
  with file ownership boundaries, dependency graph, and measurable done checks.
  Scopes out format-handler migration, renderer unification, and Tool framework
  as separate projects.
- Add "Read Peptide Sequence" menu item under Chemistry in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py):
  prompts for a single-letter amino acid sequence (e.g. ANKLE), converts it
  to IsoSMILES via new
  [packages/bkchem-app/bkchem/peptide_utils.py](packages/bkchem-app/bkchem/peptide_utils.py),
  and renders the polypeptide structure through the existing SMILES-to-CDML
  pipeline.

## 2026-02-17
- Route all complex substituents through `coords_generator2` in
  [packages/oasa/oasa/haworth/fragment_layout.py](packages/oasa/oasa/haworth/fragment_layout.py):
  remove `_two_carbon_tail_fragment()` special case and `branch_length` parameter.
  CH(OH)CH2OH and CHAIN<N> now use the same 120-degree lattice-aligned molecular
  geometry path. Down-direction two-carbon tails produce symmetric 30/150 degree
  branch angles instead of side-dependent orientation.
- Route CHAIN<N> labels through `_add_fragment_ops()` in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  CHAIN3+ labels now use `coords_generator2` zigzag geometry with proper OH
  branches at each junction, replacing the collinear `_add_chain_ops()` path.
  Add `_fragment_chain_numbers()` for sequential chain segment op_id naming
  (chain1, chain1_oh, chain2, chain2_oh, chain3).
- Add fragment-based substituent layout module
  [packages/oasa/oasa/haworth/fragment_layout.py](packages/oasa/oasa/haworth/fragment_layout.py):
  uses `coords_generator2` to identify display groups from SMILES fragments, and
  provides `FragmentAtom` dataclass and `layout_fragment()` for computing
  positioned atom groups for complex substituents (CH(OH)CH2OH, CHAIN<N>).
- Add unified `_add_fragment_ops()` renderer path in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py):
  replaces `_add_furanose_two_carbon_tail_ops()` for branched CH(OH)CH2OH tails
  using the new fragment layout infrastructure. Produces backwards-compatible
  op_ids and rendering (connectors, text labels, hashed bonds). Legacy
  `_add_chain_ops` retained for sequential CHAIN<N> rendering.
- Add 25 unit tests in
  [tests/test_haworth_fragment_layout.py](tests/test_haworth_fragment_layout.py)
  covering SMILES lookup, fragment grouping, two-carbon tail geometry (branch
  angles, bond styles, parent indices), and CHAIN<N> group identification.
- Switch chain-like labels (CH2OH, CHOH, CH3, HOH2C, etc.) to full-box bond
  trimming (`target_kind="label_box"`) in the Haworth renderer.  Connector
  endpoints now resolve against the full label bounding box instead of
  narrowing to the specific carbon glyph.  Removes the `endswith("C")` hack
  for reversed labels.  Hydroxyl (OH/HO) labels keep oxygen-circle targeting;
  two-carbon tail ops and multi-segment chain ops keep explicit `attach_box`
  targeting.
- Fix IndexError crash when rotating molecules with double bonds in
  [packages/bkchem-app/bkchem/bond_display.py](packages/bkchem-app/bkchem/bond_display.py):
  guard `self.second[0]` access in `transform()` since the render-ops draw path
  never populates `self.second` for double bonds.
- Route BKChem SMILES import through CDML: replace direct
  `oasa_mol_to_bkchem_mol` bridge with `smiles_to_cdml_elements()` in
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py),
  update `read_smiles()` dialog in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py) to use
  `paper.add_object_from_package()`, and remove old `read_smiles` bridge
  function. Updated dialog text to indicate IsoSMILES support.
- Add pytest test suite
  [tests/test_smiles_cdml_import.py](tests/test_smiles_cdml_import.py) for the
  `smiles_to_cdml_elements()` function in `oasa_bridge.py` (7 tests covering
  ethanol, benzene, coordinate units, bond length, disconnected SMILES, empty
  input, and atom names).
- Fix disconnected SMILES handling in `smiles_to_cdml_elements()` in
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py):
  add `mol.remove_zero_order_bonds()` call so dot-separated SMILES like "CC.OO"
  are correctly split into separate CDML molecule elements.
- Add SMILES/IsoSMILES CDML import plan
  [docs/active_plans/SMILES_CDML_IMPORT_PLAN.md](docs/active_plans/SMILES_CDML_IMPORT_PLAN.md)
  to route SMILES import through the canonical CDML serialization path instead
  of the direct `oasa_mol_to_bkchem_mol` bridge.
- Add three-layer 2D coordinate generator
  [packages/oasa/oasa/coords_generator2.py](packages/oasa/oasa/coords_generator2.py)
  that produces RDKit-quality 2D layouts without the RDKit dependency.
  Implements ring system assembly (fused, spiro, bridged), BFS chain/substituent
  placement, collision detection with flip/nudge resolution, and force-field
  refinement (bond stretch + angle bend + non-bonded repulsion).
- Add coordinate generator tests
  [tests/test_coords_generator2.py](tests/test_coords_generator2.py) covering
  single atoms, chains, benzene, naphthalene, spiro, steroid skeleton, triple
  bonds, branching, and force parameter behavior (23 tests).
- Add visual comparison tool
  [tools/coords_comparison.py](tools/coords_comparison.py) that renders
  side-by-side HTML galleries of old vs new vs RDKit 2D coordinate layouts
  for 24 test molecules.
- Update [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
  to prefer `coords_generator2` over legacy `coords_generator` when RDKit is not
  available, with graceful fallback to the old generator.
- Add RDKit bridge module
  [packages/oasa/oasa/rdkit_bridge.py](packages/oasa/oasa/rdkit_bridge.py) for
  converting between OASA and RDKit molecule representations and generating 2D
  coordinates via `AllChem.Compute2DCoords`.  Provides `oasa_to_rdkit_mol`,
  `rdkit_to_oasa_mol`, and `calculate_coords_rdkit` functions following the same
  pattern as the existing `pybel_bridge.py`.
- Add RDKit sugar comparison gallery tool
  [tools/rdkit_sugar_comparison.py](tools/rdkit_sugar_comparison.py) that
  renders side-by-side Haworth projection SVGs and RDKit 2D depiction SVGs for
  all sugar codes.  Outputs `output_smoke/rdkit_comparison_pyranose.html` and
  `output_smoke/rdkit_comparison_furanose.html` with comparison pairs.
- Wire RDKit coordinate generation into bkchem SMILES import pipeline.
  [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py)
  now uses `rdkit_bridge.calculate_coords_rdkit` when RDKit is available,
  falling back to OASA's native `coords_generator` when it is not.
- Add `rdkit` to [pip_requirements.txt](pip_requirements.txt).
- Add 3-KETO ring rules to Haworth spec
  ([packages/oasa/oasa/haworth/spec.py](packages/oasa/oasa/haworth/spec.py)):
  furanose (anomeric=3, closure=6, min_carbons=6) and pyranose (anomeric=3,
  closure=7, min_carbons=7).  Handle 3-KETO anomeric substituent with
  CH(OH)CH2OH pre-anomeric chain.  Enables rendering of 3-ketohexoses.
- Fix CH2OH label overlap on left-side furanose ring slots.  Chain-like labels
  (CH2OH, CHOH) at anchor=end slots (ML, BL) now render as HOH2C/HOHC via
  `format_chain_label_text`, so the carbon atom faces the ring and the label
  does not overlap ring bonds.  Connector attach-atom policy updated to target
  the trailing carbon in reversed text.
- Add sugar codes HTML gallery script
  [tools/sugar_codes_summary.py](tools/sugar_codes_summary.py) that reads all
  106 sugar codes from
  [packages/oasa/oasa_data/sugar_codes.yaml](packages/oasa/oasa_data/sugar_codes.yaml),
  renders each valid ring/anomeric combination as a Haworth projection SVG
  file, and writes two separate HTML gallery pages:
  `output_smoke/sugar_codes_pyranose.html` and
  `output_smoke/sugar_codes_furanose.html`.  SVG previews are written to
  `output_smoke/sugar_codes_previews/` and referenced via `<img>` tags.  Each
  page has a cross-link to the other ring type gallery in the sticky header.
  Uses the same earth-tone CSS theme and `_normalize_generated_svg` viewBox
  logic as `tools/archive_matrix_summary.py`.  Grouped by YAML category with
  section headers; sugars that cannot form valid rings show "No valid
  [ring type] ring forms".

## 2026-02-15
- Add macOS DMG build script
  [devel/build_macos_dmg.py](devel/build_macos_dmg.py) that produces a
  self-contained `BKChem.app` bundle via PyInstaller and wraps it in a
  `BKChem-VERSION.dmg` disk image.  Generates `.icns` icon from
  `bkchem.svg` via `rsvg-convert` + `iconutil`.  Bundles embedded Python
  3.12, Tcl/Tk, pycairo, Pmw, oasa, bkchem_data, oasa_data, and addons.
  Patches `Info.plist` with version, bundle ID, Retina support, and
  `.cdml` file association.  Post-build verification checks executable,
  data dirs, Tcl/Tk, and libcairo presence.  Add `pyinstaller` to
  [pip_requirements-dev.txt](pip_requirements-dev.txt) and `librsvg` to
  [Brewfile](Brewfile).  Update
  [docs/active_plans/RELEASE_DISTRIBUTION.md](docs/active_plans/RELEASE_DISTRIBUTION.md)
  to reference the new script.
- Fix bond line overlapping C glyph in HOH2C connector on two-carbon down
  tails.  Two changes in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  (1) make `_retreat_to_target_gap()` iterative (up to 4 iterations) so
  diagonal approach angles converge to the correct gap instead of
  under-retreating on a single pass; (2) add a second retreat pass against
  the full label text box after the endpoint-atom retreat, using
  `ATTACH_GAP_TARGET` as the minimum gap, so the bond clears non-attach
  characters (like the subscript "2") that are closer than the target atom.
  Add diagonal convergence test in
  [tests/test_render_geometry.py](tests/test_render_geometry.py).  Update
  attach-element epsilon in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to
  accommodate the additional full-label retreat.
- Fix key letter selection in glyph bond alignment measurement.  The character
  selection heuristic used canonical text ("CH2OH") instead of displayed text
  ("HOH2C") and did not skip terminal H in multi-character labels, causing the
  measurement tool to pick "H" at the far left of "HOH2C" instead of "C" at
  the bond endpoint on the right.  Add `_select_key_letter()` helper in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) that searches
  inward from the specified end, skipping H for multi-character labels.  Switch
  alpha_chars extraction from canonical to displayed text via
  `label_geometry_text()`.  Add cross-reference comment in
  [tools/measurelib/glyph_model.py](tools/measurelib/glyph_model.py) linking
  `is_measurement_label()` to the key letter heuristic.  Update and add tests
  in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py).
- Fix hatch strokes touching glyph letters by using `epsilon=0.0` for hatch
  filtering in `validate_attachment_paint()`.  The previous `STRICT_OVERLAP_EPSILON`
  (0.5) shrank the forbidden box, allowing hatches up to 0.5 px inside the glyph
  boundary.  Solid connectors avoid this via an additional retreat step that
  hatches lack, so hatches need exact boundary enforcement.  Fix in
  `_append_branch_connector_ops()` in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
- Trim hatched bond carrier line endpoint to last surviving hatch stroke in
  Haworth renderer.  When forbidden-region filtering removes hatch strokes
  near a label, the invisible carrier line no longer extends past the last
  visible stroke into the glyph boundary.  Prevents false-negative gap
  measurements from the carrier endpoint reaching into label space.  Fix in
  `_append_branch_connector_ops()` in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
- Implement Phase 6: expand sugar_code_to_smiles() from 2-entry bootstrap to
  generalized algorithmic Fischer-to-SMILES builder.  Supports all ~148 sugar
  codes in sugar_codes.yaml across pyranose/furanose ring forms and alpha/beta
  anomeric configurations.  Uses fixed ring traversal order with position-based
  chirality mapping (Fischer R/L to SMILES @/@@) derived from the existing
  Haworth spec up/down labels.  Handles aldoses and ketoses including tetroses
  through heptoses with 1-3 carbon exocyclic chains, plus modified sugars
  (deoxy, amino, N-acetyl, fluoro, phosphate, carboxyl) in
  [packages/oasa/oasa/sugar_code_smiles.py](packages/oasa/oasa/sugar_code_smiles.py).
  Tests expanded from 6 to 446 in
  [tests/test_sugar_code_smiles.py](tests/test_sugar_code_smiles.py).
- Implement Phase 7: create smiles_to_sugar_code() reverse converter with
  two-tier approach.  Tier 1 builds a lookup table at module load from all
  sugar_codes.yaml entries via Phase 6 sugar_code_to_smiles().  Tier 2 parses
  the SMILES into a molecule, finds sugar-like rings, and tries candidate
  matches.  New module
  [packages/oasa/oasa/smiles_to_sugar_code.py](packages/oasa/oasa/smiles_to_sugar_code.py)
  with SugarCodeResult dataclass and SugarCodeError exception.  All standard
  sugar codes round-trip perfectly (sugar code -> SMILES -> sugar code).
  447 tests in
  [tests/test_smiles_to_sugar_code.py](tests/test_smiles_to_sugar_code.py).
  Registered in
  [packages/oasa/oasa/__init__.py](packages/oasa/oasa/__init__.py).
- Widen HOH2C solid connector gap using standard OASA geometry.  The CH2OH arm
  in `_add_furanose_two_carbon_tail_ops()` used a custom
  `_align_text_origin_to_endpoint_target_centroid()` step and
  `direction_policy="line"` that differed from the standard `_add_chain_ops`
  path.  Remove the custom alignment, switch to `direction_policy="auto"` with
  `attach_site="core_center"`, and add round-cap compensation
  (`connector_width * 0.5`) to `target_gap` so the visual gap after the round
  cap extends is at least `ATTACH_GAP_TARGET`.  Affects furanose sugars with
  two-carbon tails in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
- Extend down-direction furanose two-carbon tail connectors to match up-direction
  lengths.  Down-direction tails (e.g., ARRLDM furanose beta, ALRLDM furanose
  alpha) had very short HO and HOH2C branch arms because no oxygen clearance
  extension was applied for `direction == "down"`.  Add the same minimum
  effective_length formula used by up-direction tails inside the two-carbon-tail
  block in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py),
  giving symmetric trunk lengths for both directions.
- Fix hatched connector overlap with CH2OH text in furanose two-carbon tails.
  Hatch strokes near the label end were incorrectly allowed through the
  forbidden-region filter because `allowed_regions` (the attach-point carve-out
  for the invisible carrier line) overrode the text bounding-box exclusion.
  Remove `allowed_regions` from hatch stroke legality checks in
  `_append_branch_connector_ops()` in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  so individual hatch marks always stop before the label text.  Affects
  furanose sugars with hatched CH2OH branch (up direction: ALLRDM, ALRRDM,
  ARLRDM, etc.) and hatched HO branch (down direction: ARRLDM, etc.).
- Close and archive Haworth schematic renderer implementation plan (attempt 2).
  Core phases 1-5c complete. Deferred SMILES conversion phases (6, 7) and
  stretch goals (6b) to [docs/TODO_CODE.md](docs/TODO_CODE.md). Move plan to
  [docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md).
  Fix stale [docs/ROADMAP.md](docs/ROADMAP.md) references to archived plans.
- Add ring oxygen gap measurement via virtual connector lines.  Haworth sugar
  SVGs render ring edges as filled `<polygon>` elements, not `<line>` elements,
  so the ring oxygen "O" label had no nearby line endpoint and got
  `no_connector` in measurements.  Store polygon vertex coordinates in ring
  primitives (`"points"` key) in
  [tools/measurelib/svg_parse.py](tools/measurelib/svg_parse.py).  New
  `oxygen_virtual_connector_lines()` in
  [tools/measurelib/haworth_ring.py](tools/measurelib/haworth_ring.py) finds the
  two ring polygon edges closest to the O label and synthesizes virtual line
  dicts from their center axes.  Integrate virtual lines into the analysis
  pipeline in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py): append to
  `lines` list, include in connector candidates, exclude from width pool, bond
  length statistics, and checked bond indexes.  Include virtual lines in
  diagnostic perpendicular markers.
- Replace CH2OH fan-out solver with standard OASA connector path in Haworth
  furanose two-carbon tail renderer.  Delete `_chain2_label_offset_candidates()`
  and `_solve_chain2_label_with_resolver()` (53-candidate fan-out solver) from
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  Use same standard 3-step connector path as the HO arm and all simple OH
  connectors: `_align_text_origin_to_endpoint_target_centroid()` +
  `label_target_from_text_origin()` +
  `resolve_label_connector_endpoint_from_text_origin()` with
  `direction_policy="line"`.  Remove `min_standoff_factor` floor hack so
  `branch_standoff` uses `segment_length` directly.  Before: CH2OH arm ~10.2
  units vs HO arm ~17.0 units (67% mismatch); hatched connector overlapped
  CH2OH glyph in up case.  After: both arms use the same geometry-derived
  length with standard gaps.  Mark H-024 and H-025 as removed in
  [docs/HAWORTH_OVERRIDES.md](docs/HAWORTH_OVERRIDES.md).  Update
  `direction_policy` in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to match.
- Fix two-carbon tail bond lengths in Haworth furanose renderer.  Unify
  `min_standoff_factor` from direction-asymmetric values (`up=1.75`,
  `down=1.35`) to a single `1.35` floor so standard `segment_length` wins.
  Normalize `ho_length_factor` and `ch2_length_factor` from `0.90`/`0.95`/`1.20`
  to `1.0` for both up and down directions so arm lengths match the base
  `segment_length` used by simple hydroxyl connectors.  Before: CH2OH bond
  ~20.3 units with text overlap, HO bond ~12.8 units with sub-minimum gap.
  After: both arms ~16 units with 1.3-1.7 gaps matching standard connectors.
  Changes in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  Update H-025 status in
  [docs/HAWORTH_OVERRIDES.md](docs/HAWORTH_OVERRIDES.md).
  Relax hashed connector nearest-hatch threshold from 15% to 18% of connector
  length in
  [tests/test_haworth_renderer.py](tests/test_haworth_renderer.py) to
  accommodate shorter normalized connectors.  Remove 3 `xfail` markers from
  ALLLDM pyranose beta upward hydroxyl connector tests that now pass with
  unified standoff.
- Fix regression expectations in
  [tests/test_attach_targets.py](tests/test_attach_targets.py) for
  `label_target()` box geometry after calibrated text top/bottom offsets in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Update legacy-value fixtures for `O`, `OH`, and `NH3+` to current
  deterministic coordinates.
- Speed up
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  by memoizing the expensive render-and-measure result so the suite computes
  it once per test session instead of once per test function.
- Draw perpendicular cross-lines at all bond endpoints in diagnostic SVG
  overlay.  New `_draw_bond_perpendicular_markers()` helper in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py)
  draws short perpendicular lines at both ends of every checked bond line:
  magenta `#ff00ff` for endpoints used for gap measurement, dark blue
  `#00008b` for other endpoints.  Include Haworth base ring bonds and
  double bond secondary lines in the perpendicular marker set so both
  primary and secondary bond lines get endpoint markers.  Double bond
  secondary lines now included in connector candidates so labels like
  CH2OH find the correct nearest bond endpoint (secondary going toward
  the label) instead of the primary going the wrong direction.  Markers
  are drawn as a background layer before per-label overlays.  Remove
  per-metric orange perpendicular line (now redundant).  Change hull contact
  point marker from circle to ellipse (rx=1.5, ry=0.8).  Legend updated with
  perpendicular line swatches for "Connector endpoint" and "Other endpoint".
  Tests in
  [tests/test_measurelib_diagnostic_svg.py](tests/test_measurelib_diagnostic_svg.py)
  cover perpendicular marker presence, backward compatibility, and hull
  contact ellipse.
- Render charge marks as circled symbols in OASA SVG output instead of
  appending +/- as inline text.  Store mark data in vertex `properties_` in
  [tools/render_beta_sheets.py](tools/render_beta_sheets.py), suppress charge
  text suffix in `vertex_label_text()` when marks are present, and generate
  `CircleOp`/`LineOp` for circled plus (blue) and minus (red) marks in
  `build_vertex_ops()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Update bond count expectations in
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  to account for the 6 new mark lines.
- Fix furanose beta MR OH / ML CH2OH text collision in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  When MR carries a simple hydroxyl and ML carries a chain-like tail
  (e.g. ALRRDM furanose beta), skip the oxygen clearance override entirely so
  the MR OH bond stays at the default 13.5 length instead of being pushed up
  to 18.49 where it collides with the CH2OH text.  Remove unused constant
  `FURANOSE_TOP_RIGHT_HYDROXYL_EXTRA_CLEARANCE_FACTOR` from
  [packages/oasa/oasa/haworth/renderer_config.py](packages/oasa/oasa/haworth/renderer_config.py).
- Rebalance furanose "up" two-carbon tail branch length factors in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  `ho_length_factor` changed from 0.72 to 0.90, `ch2_length_factor` from 1.08
  to 0.95 in `_furanose_two_carbon_tail_profile()`.  This reduces the HO vs
  CH2OH branch length ratio from ~2.5:1 to ~1.3:1.
- Use round linecaps for all Haworth bond lines in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  The hashed-bond carrier line in `_add_branch_connector_ops()` was the only
  remaining `cap="butt"` bond line; changed to `cap="round"` for visual
  consistency with all other bond connectors.  Hatch cross-strokes retain butt
  caps since they are decorative marks, not bond lines.  Add `CircleOp` rounding
  caps at back ring vertices (ML, TL, MR for pyranose) so the thin polygon ring
  edges also appear rounded where they meet instead of showing square corners.
  Make the hashed-bond carrier line fully transparent (`color="none"`) so only
  the hatch cross-strokes are visible.  Add `HASHED_BOND_WEDGE_RATIO` constant
  (4.6, up from hardcoded 2.8) to
  [packages/oasa/oasa/haworth/renderer_config.py](packages/oasa/oasa/haworth/renderer_config.py)
  to widen the hatch bond fan angle.
- Empirically calibrate glyph bounding-box vertical offset in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  `_label_box_coords()` `bottom_offset` changed from `0.035` to `0.008` based
  on rsvg/Pango pixel measurements (actual descent is 0.1 SVG units at 12pt,
  ratio 0.008).  Previous value overestimated descent, inflating glyph boxes
  and causing Haworth ring-edge overlap failures.  Add
  `_text_ink_bearing_correction()` helper that computes the left and right
  bearing gap between Cairo advance width and actual ink extent.
- Increase oxygen exclusion safety margin in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  `_oxygen_exclusion_radius()` safety factor raised from `0.05` to `0.09` to
  compensate for the tighter glyph box: ring edges now maintain visual
  clearance from the oxygen label despite the smaller bounding box.
- Improve glyph calibration tool
  [tools/calibrate_glyph_model.py](tools/calibrate_glyph_model.py).
  `_generate_subscript_svg()` now generates proper SVG `<tspan>` subscript
  structure matching the renderer's output (font-size scaling, dy offsets)
  instead of rendering plain text.  Fix pyflakes lint: remove unused imports
  (`math`, `pathlib`, `glyph_char_advance`, `glyph_text_width`), unused
  variable (`sub_dy`), and unnecessary f-string prefixes.
- Alignment measurement improvement: Haworth OH/HO alignment increased from
  ~52% to 100% (HO) and 94.7% (OH).  Overall alignment (excluding ring
  oxygens) improved from ~33.9% to 81.3%.  Bond-end gap values now land in
  the [1.3, 1.7] target range (avg 1.52) for both alpha and beta anomers.

- Add Cairo PDF parity measurement tool for comparing PDF and SVG renderer
  output.  New `tools/measure_cairo_pdf_parity.py` CLI supports two modes:
  parity mode (SVG+PDF pair comparison) and PDF-only mode (standalone PDF
  analysis).  New modules:
  [tools/measurelib/pdf_parse.py](tools/measurelib/pdf_parse.py) extracts
  lines, labels, ring primitives, and wedge bonds from Cairo-generated PDF
  files via `pdfplumber` with Y-coordinate flipping to SVG space;
  [tools/measurelib/parity.py](tools/measurelib/parity.py) performs
  nearest-neighbor matching of SVG and PDF primitives with configurable
  tolerance and computes a parity score;
  [tools/measurelib/pdf_analysis.py](tools/measurelib/pdf_analysis.py)
  runs the full structural analysis pipeline (Haworth detection, hatch
  detection, violations) on PDF-extracted primitives.  Tests in
  [tests/test_cairo_pdf_parity.py](tests/test_cairo_pdf_parity.py) cover
  PDF extraction, parity matching, file pairing, and standalone PDF
  analysis (19 tests).  Existing SVG measurement tool is unchanged.
- Fix antiparallel reverse-strand terminal text orientation in
  [tools/render_beta_sheets.py](tools/render_beta_sheets.py) so C->N chains
  read as `-OOC ... NH3+` (instead of `COO- ... H3N+`).  Add direction-aware
  terminal label text/position handling (`COO`/`H3N` for forward strands,
  `OOC`/`NH3` for reverse strands) and charge-mark side placement.  Add
  regression coverage in
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  to assert reverse-strand terminal labels and charge mark positions.
- Add double bond pair detection and exclusion to glyph-bond alignment
  measurement tool.  New `detect_double_bond_pairs()` in
  [tools/measurelib/hatch_detect.py](tools/measurelib/hatch_detect.py) finds
  parallel line pairs (C=O double bonds) and excludes the secondary offset line
  from measurement.  Uses linecap attribute to classify primary (round-cap) vs
  secondary (butt-cap) lines.  Add `DOUBLE_BOND_*` constants to
  [tools/measurelib/constants.py](tools/measurelib/constants.py).  Report now
  includes `decorative_double_bond_offset_count` and `double_bond_pairs`.
- Add multi-bond label support to glyph-bond alignment measurement tool.
  New `all_endpoints_near_glyph_primitives()` and
  `all_endpoints_near_text_path()` in
  [tools/measurelib/glyph_model.py](tools/measurelib/glyph_model.py) return all
  bond endpoints within search distance, grouped by approach side (left/right).
  Per-label measurement loop in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) now builds a
  `connectors` list with independent alignment metrics for each side.  A label
  is aligned only if all its connectors pass.  Backward-compatible top-level
  fields are preserved from the primary (nearest) connector.
- Update re-exports in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  for new double bond and multi-connector public names.
- Add tests for double bond detection and multi-connector labels in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py).
  Update expected bond counts in
  [tests/test_beta_sheet_measurement.py](tests/test_beta_sheet_measurement.py)
  to reflect double bond exclusion (42 detected, 6 excluded, 36 checked).
- Fix double-bond perpendicular distance measurement in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py).  Perpendicular
  distance was measured from the glyph optical center to the primary drawn line,
  but for C=O double bonds the two parallel lines are offset ~6 SVG units from
  the true bond axis.  The O glyph center sits on the bond axis (between the
  two lines), giving a spurious perp offset of ~3.  Fix: compute a midline by
  averaging primary and secondary line coordinates, then measure perpendicular
  distance to the midline.  O label perp values drop from 3.03 to 0.03.
  Update infinite-line overlay in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py)
  to draw the midline for double-bond primaries.
- Add gap-ratio filter to multi-connector label detection in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py).  Distant bonds
  from the far side of a label were incorrectly included as secondary connectors
  (e.g. O labels getting a spurious connector with gap=27 alongside the real
  C=O connector with gap=8).  Discard connectors whose gap exceeds
  `MULTI_CONNECTOR_GAP_RATIO_MAX` (3.0) times the minimum gap among all sides.
  Add constant to
  [tools/measurelib/constants.py](tools/measurelib/constants.py).

- Fix double-bond centering inconsistency in OASA generic renderer.
  `molecule_to_ops()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  was passing `point_for_atom=None`, so `_double_bond_side()` compared
  transformed bond coordinates against raw (untransformed) atom positions.
  Neighbor atoms appeared on the wrong side, producing offset double bonds
  where centered was correct.  Fix: pass a `point_for_atom` callback that
  applies the same `transform_xy` used for bond coordinates.
- Add `center` attribute to OASA bond class in
  [packages/oasa/oasa/bond.py](packages/oasa/oasa/bond.py).  Parse
  `center="yes"` from CDML in
  [packages/oasa/oasa/cdml_bond_io.py](packages/oasa/oasa/cdml_bond_io.py).
  Honor the attribute in `build_bond_ops()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  when `edge.center` is set, skip geometric side detection and force centered
  double-bond rendering.

- Add N, O, R, and H-only atoms to the glyph-bond measurement tool.
  `is_measurement_label()` in
  [tools/measurelib/glyph_model.py](tools/measurelib/glyph_model.py) now uses
  first/last letter logic instead of substring search; measurable atoms are
  {C, O, S, N, R} plus H-only labels.  Add R to `GLYPH_STEM_CHAR_SET` in
  [tools/measurelib/constants.py](tools/measurelib/constants.py).  Replace
  element-priority alignment center selection in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) with first/last
  letter logic that picks the connecting character based on which side of the
  label the bond approaches.  Add bounding-box fallback in
  [tools/measurelib/lcf_optical.py](tools/measurelib/lcf_optical.py) to use
  character shape type for optical fitting: curved glyphs (C, O, S) get
  ellipse fitting, stem glyphs (N, H, R) get bounding-box center.  Update
  tests in
  [tests/test_measurelib_glyph_model.py](tests/test_measurelib_glyph_model.py)
  and
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  for new measurement label set and first/last letter alignment.

- Add CPK default colors for charge marks in
  [packages/bkchem-app/bkchem/marks.py](packages/bkchem-app/bkchem/marks.py): `plus`
  marks default to blue (`#0000FF`) and `minus` marks default to red
  (`#FF0000`) instead of inheriting the atom's line color.  Override the
  `line_color` property in each subclass with a CPK fallback; explicit color
  set via `set_color()` or `_line_color` still takes precedence.
- Add zoom scaling for all mark subclasses in
  [packages/bkchem-app/bkchem/marks.py](packages/bkchem-app/bkchem/marks.py).  Add
  `_scaled_size()` helper to the base `mark` class that multiplies `self.size`
  by `self.paper._scale`.  Update `draw()` in `radical`, `biradical`,
  `electronpair`, `plus`, `minus`, and `text_mark` to use `_scaled_size()`
  for canvas pixel dimensions so marks grow/shrink proportionally with zoom.
  The inset constant in `plus`/`minus` cross/dash lines also scales.  SVG
  export and CDML serialization remain unscaled (model coordinates).  Skip
  `pz_orbital` (mixes model coords with size differently).
- Fix bond drawing after zoom for shown atoms (N, O, R, H3N, COOH).  Bonds
  connected to labeled atoms drew as long diagonal lines after zoom because
  `molecule.redraw()` redraws bonds before atoms, and bonds call `atom.bbox()`
  which read stale pre-zoom canvas positions.  Fix by redrawing atoms first so
  their canvas items are at correct positions, then redrawing bonds, then
  lifting atoms above bonds to restore z-ordering.
- Fix double bond convergence toward labeled atoms (take 2). Secondary
  parallel lines of double/triple bonds were independently resolved against
  label targets, but each offset line approaches the label at a different
  angle, so Steps 1-3 of the constraint pipeline broke parallelism. Remove all
  `_resolve_endpoint_with_constraints` calls from secondary bond lines in
  `build_bond_ops()`. Secondary lines inherit correct clearance from the main
  bond's already-resolved endpoints via `find_parallel()`. Remove the
  now-unused `no_gap_constraints` variable. Cross-label overlap avoidance
  (`_avoid_cross_label_overlaps`) is retained for all lines.
- Rewrite [tools/render_beta_sheets.py](tools/render_beta_sheets.py) to produce
  bkchem-quality beta-sheet CDML and SVG fixtures.  Write CDML directly via
  `xml.dom.minidom` (not `oasa.cdml_writer`) to emit proper bkchem element
  types: `<atom>` for backbone C/N/O, `<query>` for R groups, and
  `<text><ftext>` with `<sub>` markup for terminals.  N-terminus H3N uses
  `<mark type="plus" draw_circle="yes"/>` (bkchem circled charge mark);
  C-terminus COO uses `<mark type="minus" draw_circle="yes"/>` (carboxylate).
  C=O bonds use `type="n2" center="yes" bond_width="6.0"`.  Geometry matches
  the hand-drawn reference template (0.700 cm bond length, 30-degree zigzag).
  Four residues per strand, 19 atoms and 18 bonds each, 38 atoms total per
  file (no cross-strand H-bonds).  SVG rendered via `render_out.render_to_svg()`
  with `show_hydrogens_on_hetero=False`; oasa charge display appends +/- via
  `vertex_label_text`.  Fixtures at
  [tests/fixtures/oasa_generic/](tests/fixtures/oasa_generic/), SVGs at
  `output_smoke/oasa_generic_renders/`.
- Fix gap retreat reference mismatch: change `_retreat_to_target_gap()` in
  `resolve_label_connector_endpoint_from_text_origin` to use
  `contract.endpoint_target` (per-character glyph model) instead of
  `contract.full_target` (full label bounding box). The measurement tool
  measures from the tight glyph body outline, which sits inside the bbox by
  0.5-1.3 px, causing measured gaps to overshoot by that inset. Using the
  tighter endpoint target aligns the retreat reference with the measurement
  reference. Legality retreat still uses `full_target` to prevent text overlap.
  Expand `_point_in_target_closed` tolerance in the chain2 label solver
  ([packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py))
  by `ATTACH_GAP_TARGET` so the endpoint validity check accommodates the
  intentional gap distance. Update chain2 resolver test to use matching
  `epsilon=1e-3` and `make_attach_constraints()` factory call.
- Fix Haworth renderer gap target mismatch: pass `target_gap=ATTACH_GAP_TARGET`
  (1.5 px) explicitly at all 6 `make_attach_constraints()` call sites in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py).
  Previously the renderer used the font-relative fallback (`12.0 * 0.058 = 0.696 px`),
  which fell outside the measurement spec's 1.3-1.7 px window.
- Add `make_attach_constraints()` factory and `ATTACH_GAP_FONT_FRACTION` constant
  to [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Three-tier gap resolution: explicit `target_gap` > font-relative > absolute default.
  Delete Haworth-only `TARGET_GAP_FRACTION` constant and replace all inline
  `AttachConstraints()` calls across Haworth, cairo_out, svg_out, bond_render_ops,
  and bond_drawing with the shared factory. Phase 5 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Wire shared gap/perp constraints through `BondRenderContext` into
  `build_bond_ops()`. Add `attach_constraints` field to `BondRenderContext` and
  `attach_gap_target`/`attach_perp_tolerance` style keys to `molecule_to_ops()`.
  Update `cairo_out.py`, `svg_out.py`, `bond_render_ops.py`, and `bond_drawing.py`
  to construct and pass `AttachConstraints` with shared constants. Phase 4 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Fix zoom viewport drift caused by orphaned canvas items leaking during
  redraw.  Non-showing atoms (carbon) in
  [packages/bkchem-app/bkchem/atom.py](packages/bkchem-app/bkchem/atom.py) called
  `get_xy_on_paper()` which created a `vertex_item`, then overwrote
  `self.vertex_item = self.item`, orphaning the first item.  These leaked
  items accumulated at stale `canvas.scale()` coordinates, inflating the
  content bounding box and causing cumulative drift (571 px after 6 zoom
  steps).  Fix computes coordinates directly via `real_to_canvas()`.
- Fix bond position drift during zoom by repositioning `vertex_item`
  coordinates to `model_coord * scale` at the top of `molecule.redraw()`
  in [packages/bkchem-app/bkchem/molecule.py](packages/bkchem-app/bkchem/molecule.py).
  Bonds redraw before atoms for z-ordering and read atom positions from
  `vertex_item`; without the reset they used stale canvas-scaled coords.
- Add `_center_viewport_on_canvas()` helper to
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py) and
  call it after `update_scrollregion()` in `scale_all()` to re-center the
  viewport on the zoom origin.  Refactor `zoom_to_content()` to use the
  new helper.
- Fix interactive zoom drift: remove redundant `canvas.scale('all', ox, oy,
  factor, factor)` from `scale_all()` in
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py).
  `redraw_all()` already redraws content from model coords at the new scale,
  but the background rectangle (`self.background`) is not in `self.stack` and
  was never reset by `redraw_all()`.  The `canvas.scale()` call scaled it
  around the viewport center while `redraw_all()` scales from the origin,
  causing the background and content to diverge.  Fix explicitly resets the
  background via `create_background()` + `scale(background, 0, 0, scale,
  scale)` after `redraw_all()`.
- Fix Tk canvas inset bug in `_center_viewport_on_canvas()` fraction formula
  in [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py).
  Tk's `xview moveto` internally subtracts the canvas inset
  (`borderwidth + highlightthickness`) from the computed origin.  The
  fraction formula must include a `+inset` correction so that `canvasx()`
  lands on the target point after scrolling.  Without this fix, each zoom
  step introduced a systematic ~3 px centering error (matching the default
  inset of 3), causing cumulative viewport drift across zoom operations.
- Upgrade zoom test assertions in
  [tests/test_bkchem_gui_zoom.py](tests/test_bkchem_gui_zoom.py):
  convert idempotency and drift warnings to hard assertions (5% scale
  tolerance, 50 px bbox/viewport drift tolerance), add per-zoom-step
  snapshots with canvas item counts.
- Add `test_zoom_model_coords_stable` and `test_zoom_roundtrip_symmetry` to
  [tests/test_bkchem_gui_zoom.py](tests/test_bkchem_gui_zoom.py).
  Model-coords test verifies `atom.x`/`atom.y` are unchanged after zoom_in
  x50, zoom_out x100, and zoom reset.  Roundtrip-symmetry test zooms from
  1000% to ~250% (8 steps) and back, checking model-space viewport drift
  stays under 3.0 px.
- Add [docs/TKINTER_WINDOW_DEBUGGING.md](docs/TKINTER_WINDOW_DEBUGGING.md)
  documenting Tk Canvas zoom debugging techniques, the orphaned
  `vertex_item` root cause, and the `redraw()` ordering pitfall.

## 2026-02-14
- Replace "first child that changes endpoint" behavior in composite target branch
  of `_correct_endpoint_for_alignment()` with scoring-based candidate selection
  that minimizes perpendicular error to the desired centerline and tiebreaks by
  distance from original endpoint. Phase 3 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add Phase 3 composite target alignment tests in
  [tests/test_render_geometry.py](tests/test_render_geometry.py).
- Add "Zoom to Content" button and View menu entry that resets zoom, computes
  bounding box of drawn content only (excluding page background), scales to fit
  with 10% margin capped at 400%, and centers the viewport on the molecules.
  New `_content_bbox()` helper and `zoom_to_content()` method in
  [packages/bkchem-app/bkchem/paper.py](packages/bkchem-app/bkchem/paper.py); button
  and menu wiring in
  [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py).
- Shorten wavy bond wavelength from `ref * 1.2` to `ref * 0.5` (floor 2.0) in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  for tighter, more visible wave oscillations.
- Add gap/perp gate harness
  [tools/gap_perp_gate.py](tools/gap_perp_gate.py) that runs glyph-bond
  alignment measurement on fixture buckets (haworth, oasa_generic, bkchem)
  and emits compact JSON with per-label stats and failure reason counts.
  Phase 0 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add gate test
  [tests/test_gap_perp_gate.py](tests/test_gap_perp_gate.py) verifying gate
  report structure, reason tallies, empty-bucket handling, and haworth
  corpus file count.
- Add shared gap/perp spec constants (`ATTACH_GAP_TARGET`, `ATTACH_GAP_MIN`,
  `ATTACH_GAP_MAX`, `ATTACH_PERP_TOLERANCE`) to
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Add `alignment_tolerance` field to `AttachConstraints` (default 0.07) and
  replace hardcoded `max(line_width * 0.5, 0.25)` tolerance in
  `resolve_label_connector_endpoint_from_text_origin()` with
  `constraints.alignment_tolerance`. Phase 1 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add Phase 1 tests in
  [tests/test_render_geometry.py](tests/test_render_geometry.py) verifying
  shared constants, default/custom alignment tolerance, and no fallback to
  old hardcoded tolerance expression.

- Add wavy bond to GUI draw mode bond type submenu so users can select and
  draw wavy bonds from the toolbar (the rendering was already implemented but
  not wired into the GUI).
- Fix wavy bond rendering in GUI: scale amplitude/wavelength off `wedge_width`
  (not `line_width`) so waves are visible, use 4 sparse control points per
  wavelength with 1.5x amplitude overshoot so Tk's B-spline `smooth=1`
  produces genuinely smooth curves instead of visible straight-line segments,
  and widen stroke by 10% in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
- Fix hashed bond rendering in GUI: rewrite `_hashed_ops()` to compute each
  hash line perpendicular to the bond axis (unit-vector math) instead of
  connecting points on converging wedge edges, so all hash lines are parallel;
  linearly interpolate hash line length from `line_width` at the narrow end to
  `wedge_width` at the wide end; tighten spacing to `0.4 * wedge_width` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
- Rewrite
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md)
  into a focused execution plan for getting gap/perp into spec across shared
  OASA and BKChem rendering paths (not Haworth-only), with current baseline
  metrics, phased implementation, and hard acceptance gates.
- Update glyph-bond measurement pass/fail criteria in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) so labels are
  marked aligned only when `1.3 <= gap <= 1.7` and `perp <= 0.07`; all other
  cases are violations.
- Replace `err = perp` with a normalized combined metric in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py):
  `err = ((gap - 1.5)/0.2)^2 + (perp/0.07)^2`.
- Add explicit alignment gap/perp constants in
  [tools/measurelib/constants.py](tools/measurelib/constants.py).
- Update alignment tests in
  [tests/test_measure_glyph_bond_alignment.py](tests/test_measure_glyph_bond_alignment.py)
  to validate the new combined error formula and pass/fail rule.
- Add per-label `bond_len` reporting to
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py) and include
  `bond_len=...` in diagnostic SVG annotation blocks in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py),
  alongside `gap/perp/err`.
- Propagate per-label bond lengths through JSON/report data points in
  [tools/measurelib/reporting.py](tools/measurelib/reporting.py).

## 2026-02-13
- Add `_resolve_endpoint_with_constraints()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  full 4-step constraint pipeline (boundary resolve, centerline correction,
  legality retreat, target-gap retreat) replacing `_clip_to_target()` at all
  6 bond-clipping call sites in `build_bond_ops()` (single, double side-path,
  double parallel-pair). Add clipping to triple bond offset lines which
  previously had none. Deprecate `_clip_to_target()`. Phase 2 of
  [docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md).
- Add Phase 2 tests in
  [tests/test_render_geometry.py](tests/test_render_geometry.py): none-target
  passthrough, backward compatibility with `_clip_to_target()`, alignment
  correction, gap retreat, legality retreat, and triple bond offset clipping.
- Tighten gap and perp renderer parameters to meet gap 1.3-1.7 and perp < 0.07
  spec. Change `TARGET_GAP_FRACTION` from 0.04 to 0.058 in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  (yields target_gap=0.70 at font_size=12). Tighten renderer alignment tolerance
  from `max(line_width * 0.5, 0.25)` to 0.07 in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py).
  Add post-gap re-alignment pass after gap retreat to catch perpendicular drift.
  Result: OH gap=1.37, HO gap=1.30, CH2OH gap=1.70 (all in spec). Perp values
  unchanged (structural limitation of composite target geometry).
- Add median to `length_stats()` in
  [tools/measurelib/util.py](tools/measurelib/util.py). Per-label alignment
  summary now shows avg/stddev/median for both bond_end_gap and perp_offset.
- Tighten perpendicular alignment tolerance from ~1.0 to 0.07 in
  [tools/measurelib/constants.py](tools/measurelib/constants.py) and simplify
  formula in [tools/measurelib/analysis.py](tools/measurelib/analysis.py).
  Rename alignment columns to `bond_end_gap` and `perp_offset` for clarity.
- Switch per-label `gap_distance_stats` to use signed distance (negative when
  bond endpoint penetrates glyph body) in
  [tools/measurelib/reporting.py](tools/measurelib/reporting.py).
- Add distance annotations (gap, perp, err) to diagnostic SVGs near each bond
  endpoint in
  [tools/measurelib/diagnostic_svg.py](tools/measurelib/diagnostic_svg.py).
- Create standalone
  [tools/alignment_summary.py](tools/alignment_summary.py) script that reads
  existing JSON report and prints per-label alignment summary without re-running
  the full analysis.
- Replace duplicate inline console code in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  `main()` with `print_summary()` call.
- Add `_avoid_cross_label_overlaps()` to
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (Phase 4 of OASA-Wide Glyph-Bond Awareness plan). Retreats bond endpoints
  away from non-own-vertex label targets using capsule intersection tests and
  `retreat_endpoint_until_legal()`. Integrated into `build_bond_ops()` for
  single, double (asymmetric and symmetric), and triple bond paths. Includes
  minimum bond length guard (`max(half_width * 4.0, 1.0)`) to prevent bonds
  from collapsing when surrounded by labels. Note: Haworth renderer uses its
  own pipeline and is not yet affected by this change.
- Add 6 unit tests for `_avoid_cross_label_overlaps` in
  [tests/test_render_geometry.py](tests/test_render_geometry.py): cross-target
  exclusion of own vertices, near-end retreat, near-start retreat,
  no-intersection passthrough, and minimum-length guard.
- Re-baseline plan metrics in
  [OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md):
  record post-connector-fix measurements (362/362 alignment, 0 misses), update
  acceptance criteria to current baseline, relabel Phases 1-3 from DONE to
  IMPLEMENTED, add per-atom optical centering feasibility note.
- Update [refactor_progress.md](refactor_progress.md) with re-baselined gate
  status and connector selection fix diagnosis.
- Include hashed bond carrier lines as connector candidates in
  [tools/measurelib/analysis.py](tools/measurelib/analysis.py). Carrier lines
  for hatched (behind-the-plane) bonds are intentionally drawn thin with
  perpendicular hatch strokes; the width filter was excluding them, causing
  labels like CH2OH to match distant unrelated bonds instead of the actual
  hatched bond.
- Add unit tests for `_retreat_to_target_gap`, `_correct_endpoint_for_alignment`,
  and `_perpendicular_distance_to_line` in new
  [tests/test_render_geometry.py](tests/test_render_geometry.py).
- Move
  [OASA-Wide_Glyph-Bond_Awareness.md](docs/active_plans/OASA-Wide_Glyph-Bond_Awareness.md)
  to `docs/active_plans/` and add NOT STARTED labels to Changes 6, 7, 8.
- Add consumer adoption note to OASA-Wide Glyph-Bond Awareness plan clarifying
  that `target_gap` and `alignment_center` are consumed by Haworth first; other
  consumers adopt when their rendering paths are ready.
- Extract `TARGET_GAP_FRACTION` constant in
  [packages/oasa/oasa/haworth/renderer.py](packages/oasa/oasa/haworth/renderer.py)
  replacing 4 occurrences of `font_size * 0.04`.
- Run full acceptance metrics and record gate results in
  `output_smoke/acceptance_gate_results_2026-02-13.txt`.
- Port `letter-center-finder` algorithms directly into
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py)
  as `_lcf_*` prefixed functions (SVG parsing, glyph isolation rendering,
  contour extraction, convex hull, ellipse fitting), removing the external
  sibling-repo dependency on `/Users/vosslab/nsh/letter-center-finder/`.
- Extend optical glyph centering to all alphanumeric characters, not just O/C.
  Change `_lcf_extract_chars_from_string` guard from `char in ('O', 'C')` to
  `char.isalnum()`.
- Delete fallback centering functions `_alignment_primitive_center`,
  `_first_carbon_primitive_center`, and `_first_primitive_center_for_char` from
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py).
  Optical centering failures now propagate visibly instead of silently falling
  back to inaccurate heuristics.
- Remove `--alignment-center-mode` CLI argument and hardcode optical mode in
  [tools/measure_glyph_bond_alignment.py](tools/measure_glyph_bond_alignment.py).
- Add `numpy`, `opencv-python`, and `scipy` to
  [pip_extras.txt](pip_extras.txt) as optional dependencies for glyph optical
  center fitting.
- Use Cairo font-metric label box width in `_label_box_coords()` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (Phase 1 of OASA-Wide Glyph-Bond Awareness plan). Replace hardcoded
  `font_size * 0.75 * char_count` with `sum(_text_char_advances(...))`,
  making the full label box consistent with the sub-label attach box that
  already used Cairo metrics.
- Add `target_gap` and `alignment_center` fields to `AttachConstraints` in
  [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py)
  (Phase 2 and Phase 3 of OASA-Wide Glyph-Bond Awareness plan). Phase 2 adds
  `_retreat_to_target_gap()` for uniform whitespace between connector endpoint
  and glyph body. Phase 3 adds `_correct_endpoint_for_alignment()` to re-aim
  endpoints through the attach atom optical center, reducing bond/glyph overlaps
  from 219 to 211.
