# Menu Template Extract

Reference table for all `menu_template` entries in `main.py` lines 175-295.
Every coder must use this as the source of truth for label keys, help keys,
accelerators, handler expressions, and state variables.

Source: `packages/bkchem/bkchem/main.py`

## Tuple Format Reference

- **menu**: `(menu_label, 'menu', help_text, side)`
- **command**: `(menu_label, 'command', label, accelerator, help, handler, state_var)`
- **separator**: `(menu_label, 'separator')`
- **cascade**: `(menu_label, 'cascade', label, help_text)`

## File Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | menu | File | - | Open, save, export, and import files | - | - | menu.file |
| 2 | command | New | (C-x C-n) | Create a new file in a new tab | self.add_new_paper | None | file.new |
| 3 | command | Save | (C-x C-s) | Save the file | self.save_CDML | None | file.save |
| 4 | command | Save As.. | (C-x C-w) | Save the file under different name | self.save_as_CDML | None | file.save_as |
| 5 | command | Save As Template | None | Save the file as template, certain criteria must be met for this to work | self.save_as_template | None | file.save_as_template |
| 6 | command | Load | (C-x C-f) | Load (open) a file in a new tab | self.load_CDML | None | file.load |
| 7 | command | Load to the same tab | None | Load a file replacing the current one | lambda: self.load_CDML(replace=1) | None | file.load_same_tab |
| 8 | cascade | Recent files | - | The most recently used files | - | - | cascade.recent_files |
| 9 | separator | - | - | - | - | - | - |
| 10 | cascade | Export | - | Export the current file | - | - | cascade.export |
| 11 | cascade | Import | - | Import a non-native file format | - | - | cascade.import |
| 12 | separator | - | - | - | - | - | - |
| 13 | command | File properties | None | Set the papers size and other properties of the document | self.change_properties | None | file.properties |
| 14 | separator | - | - | - | - | - | - |
| 15 | command | Close tab | (C-x C-t) | Close the current tab, exit when there is only one tab | self.close_current_paper | None | file.close_tab |
| 16 | separator | - | - | - | - | - | - |
| 17 | command | Exit | (C-x C-c) | Exit BKChem | self._quit | None | file.exit |

## Edit Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 18 | menu | Edit | - | Undo, Copy, Paste etc. | - | - | menu.edit |
| 19 | command | Undo | (C-z) | Revert the last change made | lambda: self.paper.undo() | lambda: self.paper.um.can_undo() | edit.undo |
| 20 | command | Redo | (C-S-z) | Revert the last undo action | lambda: self.paper.redo() | lambda: self.paper.um.can_redo() | edit.redo |
| 21 | separator | - | - | - | - | - | - |
| 22 | command | Cut | (C-w) | Copy the selected objects to clipboard and delete them | lambda: self.paper.selected_to_clipboard(delete_afterwards=1) | selected | edit.cut |
| 23 | command | Copy | (A-w) | Copy the selected objects to clipboard | lambda: self.paper.selected_to_clipboard() | selected | edit.copy |
| 24 | command | Paste | (C-y) | Paste the content of clipboard to current paper | lambda: self.paper.paste_clipboard(None) | lambda: self._clipboard | edit.paste |
| 25 | separator | - | - | - | - | - | - |
| 26 | command | Selected to clipboard as SVG | None | Create SVG for the selected objects and place it to clipboard in text form | lambda: self.paper.selected_to_real_clipboard_as_SVG() | selected | edit.selected_to_svg |
| 27 | separator | - | - | - | - | - | - |
| 28 | command | Select all | (C-S-a) | Select everything on the paper | lambda: self.paper.select_all() | None | edit.select_all |

## Insert Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 29 | menu | Insert | - | Insert templates and reusable structures | - | - | menu.insert |
| 30 | command | Biomolecule template | None | Insert a biomolecule template into the drawing | self.insert_biomolecule_template | None | insert.biomolecule_template |

## Align Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 31 | menu | Align | - | Aligning of selected objects | - | - | menu.align |
| 32 | command | Top | (C-a C-t) | Align the tops of selected objects | lambda: self.paper.align_selected('t') | two_or_more_selected | align.top |
| 33 | command | Bottom | (C-a C-b) | Align the bottoms of selected objects | lambda: self.paper.align_selected('b') | two_or_more_selected | align.bottom |
| 34 | command | Left | (C-a C-l) | Align the left sides of selected objects | lambda: self.paper.align_selected('l') | two_or_more_selected | align.left |
| 35 | command | Right | (C-a C-r) | Align the rights sides of selected objects | lambda: self.paper.align_selected('r') | two_or_more_selected | align.right |
| 36 | separator | - | - | - | - | - | - |
| 37 | command | Center horizontally | (C-a C-h) | Align the horizontal centers of selected objects | lambda: self.paper.align_selected('h') | two_or_more_selected | align.center_h |
| 38 | command | Center vertically | (C-a C-v) | Align the vertical centers of selected objects | lambda: self.paper.align_selected('v') | two_or_more_selected | align.center_v |

## Object Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 39 | menu | Object | - | Set properties of selected objects | - | - | menu.object |
| 40 | command | Scale | None | Scale selected objects | self.scale | selected | object.scale |
| 41 | separator | - | - | - | - | - | - |
| 42 | command | Bring to front | (C-o C-f) | Lift selected objects to the top of the stack | lambda: self.paper.lift_selected_to_top() | selected | object.bring_to_front |
| 43 | command | Send back | (C-o C-b) | Lower the selected objects to the bottom of the stack | lambda: self.paper.lower_selected_to_bottom() | selected | object.send_back |
| 44 | command | Swap on stack | (C-o C-s) | Reverse the ordering of the selected objects on the stack | lambda: self.paper.swap_selected_on_stack() | two_or_more_selected | object.swap_on_stack |
| 45 | separator | - | - | - | - | - | - |
| 46 | command | Vertical mirror | None | Creates a reflection of the selected objects, the reflection axis is the common vertical axis of all the selected objects | lambda: self.paper.swap_sides_of_selected() | selected_mols | object.vertical_mirror |
| 47 | command | Horizontal mirror | None | Creates a reflection of the selected objects, the reflection axis is the common horizontal axis of all the selected objects | lambda: self.paper.swap_sides_of_selected('horizontal') | selected_mols | object.horizontal_mirror |
| 48 | separator | - | - | - | - | - | - |
| 49 | command | Configure | Mouse-3 | Set the properties of the object, such as color, font size etc. | lambda: self.paper.config_selected() | selected | object.configure |

## View Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 50 | menu | View | - | Zoom and display controls | - | - | menu.view |
| 51 | command | Zoom In | (C-+) | Zoom in | lambda: self.paper.zoom_in() | None | view.zoom_in |
| 52 | command | Zoom Out | (C--) | Zoom out | lambda: self.paper.zoom_out() | None | view.zoom_out |
| 53 | separator | - | - | - | - | - | - |
| 54 | command | Zoom to 100% | (C-0) | Reset zoom to 100% | lambda: self.paper.zoom_reset() | None | view.zoom_reset |
| 55 | command | Zoom to Fit | None | Fit drawing to window | lambda: self.paper.zoom_to_fit() | None | view.zoom_to_fit |
| 56 | command | Zoom to Content | None | Fit and center on drawn content | lambda: self.paper.zoom_to_content() | None | view.zoom_to_content |

## Chemistry Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 57 | menu | Chemistry | - | Information about molecules, group expansion and other chemistry related stuff | - | - | menu.chemistry |
| 58 | command | Info | (C-o C-i) | Display summary formula and other info on all selected molecules | lambda: self.paper.display_info_on_selected() | selected_mols | chemistry.info |
| 59 | command | Check chemistry | (C-o C-c) | Check if the selected objects have chemical meaning | lambda: self.paper.check_chemistry_of_selected() | selected_mols | chemistry.check |
| 60 | command | Expand groups | (C-o C-e) | Expand all selected groups to their structures | lambda: self.paper.expand_groups() | groups_selected | chemistry.expand_groups |
| 61 | separator | - | - | - | - | - | - |
| 62 | command | Compute oxidation number | None | Compute and display the oxidation number of selected atoms | lambda: interactors.compute_oxidation_number(self.paper) | selected_atoms | chemistry.oxidation_number |
| 63 | separator | - | - | - | - | - | - |
| 64 | command | Read SMILES | None | Read a SMILES string and convert it to structure | self.read_smiles | None | chemistry.read_smiles |
| 65 | command | Read InChI | None | Read an InChI string and convert it to structure | self.read_inchi | None | chemistry.read_inchi |
| 66 | command | Read Peptide Sequence | None | Read a peptide amino acid sequence and convert it to structure | self.read_peptide_sequence | None | chemistry.read_peptide |
| 67 | separator | - | - | - | - | - | - |
| 68 | command | Generate SMILES | None | Generate SMILES for the selected structure | self.gen_smiles | selected_mols | chemistry.gen_smiles |
| 69 | command | Generate InChI | None | Generate an InChI for the selected structure by calling the InChI program | self.gen_inchi | lambda: Store.pm.has_preference("inchi_program_path") and self.paper.selected_mols | chemistry.gen_inchi |
| 70 | separator | - | - | - | - | - | - |
| 71 | command | Set molecule name | None | Set the name of the selected molecule | lambda: interactors.ask_name_for_selected(self.paper) | selected_mols | chemistry.set_name |
| 72 | command | Set molecule ID | None | Set the ID of the selected molecule | lambda: interactors.ask_id_for_selected(self.paper) | one_mol_selected | chemistry.set_id |
| 73 | separator | - | - | - | - | - | - |
| 74 | command | Create fragment | None | Create a fragment from the selected part of the molecule | lambda: interactors.create_fragment_from_selected(self.paper) | one_mol_selected | chemistry.create_fragment |
| 75 | command | View fragments | None | Show already defined fragments | lambda: interactors.view_fragments(self.paper) | None | chemistry.view_fragments |
| 76 | separator | - | - | - | - | - | - |
| 77 | command | Convert selection to linear form | None | Convert selected part of chain to linear fragment. The selected chain must not be split. | lambda: interactors.convert_selected_to_linear_fragment(self.paper) | selected_mols | chemistry.convert_to_linear |

## Options Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 78 | menu | Options | - | Settings that affect how BKChem works | - | - | menu.options |
| 79 | command | Standard | None | Set the default drawing style here | self.standard_values | None | options.standard |
| 80 | command | Language | None | Set the language used after next restart | lambda: interactors.select_language(self.paper) | None | options.language |
| 81 | command | Logging | None | Set how messages in BKChem are displayed to you | lambda: interactors.set_logging(self.paper, Store.logger) | None | options.logging |
| 82 | command | InChI program path | None | To use InChI in BKChem you must first give it a path to the InChI program here | interactors.ask_inchi_program_path | None | options.inchi_path |
| 83 | separator | - | - | - | - | - | - |
| 84 | command | Preferences | None | Preferences | self.ask_preferences | None | options.preferences |

## Help Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 85 | menu | Help | - | Help and information about the program | - | - | menu.help |
| 86 | command | About | None | General information about BKChem | self.about | None | help.about |

## Plugins Menu

| # | Type | Label Key | Accel | Help Key | Handler | State Var | Action ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 87 | menu | Plugins | - | Small additional scripts | - | - | menu.plugins |

## Summary Counts

| Menu | menu | command | separator | cascade | Total |
| --- | --- | --- | --- | --- | --- |
| File | 1 | 9 | 4 | 3 | 17 |
| Edit | 1 | 7 | 3 | 0 | 11 |
| Insert | 1 | 1 | 0 | 0 | 2 |
| Align | 1 | 6 | 1 | 0 | 8 |
| Object | 1 | 7 | 3 | 0 | 11 |
| View | 1 | 5 | 1 | 0 | 7 |
| Chemistry | 1 | 14 | 6 | 0 | 21 |
| Options | 1 | 5 | 1 | 0 | 7 |
| Help | 1 | 1 | 0 | 0 | 2 |
| Plugins | 1 | 0 | 0 | 0 | 1 |
| **Total** | **10** | **55** | **19** | **3** | **87** |

## State Variable Reference

These are the distinct `enabled_when` / `state_var` values used:

| State Var | Type | Where Used | Meaning |
| --- | --- | --- | --- |
| None | - | 24 commands | Always enabled |
| `'selected'` | string | Edit (cut, copy, svg), Object (scale, front, back, configure) | Something is selected on the paper |
| `'selected_mols'` | string | Object (mirrors), Chemistry (info, check, smiles, name, linear) | Selected items include molecules |
| `'selected_atoms'` | string | Chemistry (oxidation) | Selected items include atoms |
| `'groups_selected'` | string | Chemistry (expand) | Selected items include groups |
| `'one_mol_selected'` | string | Chemistry (id, fragment) | Exactly one molecule is selected |
| `'two_or_more_selected'` | string | Align (all 6), Object (swap) | Two or more items selected |
| `lambda: self.paper.um.can_undo()` | callable | Edit (undo) | Undo manager has history |
| `lambda: self.paper.um.can_redo()` | callable | Edit (redo) | Undo manager has redo history |
| `lambda: self._clipboard` | callable | Edit (paste) | Clipboard is not empty |
| `lambda: Store.pm.has_preference(...) and self.paper.selected_mols` | callable | Chemistry (gen_inchi) | InChI path set AND mols selected |

## Commented-Out Entry (Not Extracted)

Line 267-269: `Set display form` command (Chemistry menu) is commented out and excluded
from this extract.

## Plugin Injection Points

After `menu_template` is processed, `init_menu()` (lines 330-344) adds script plugin
entries. Each plugin specifies a target menu via its XML `<menu>` element. If the
translated menu name matches an existing menu, the plugin entry is added there with a
separator. Otherwise it falls back to the Plugins menu.

Known addon menu targets from XML manifests:
- `fragment_search.xml`: `<menu>File</menu>` -- injects into File menu
- All other addons: no `<menu>` element or `<menu>Plugins</menu>` -- default to Plugins
