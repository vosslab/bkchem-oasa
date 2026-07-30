# Tk drawing environment event flow (2026-03-01)

## Purpose

This document focuses specifically on the Tk drawing/editing environment:
how click/drag/key events move through `main.py`, `paper.py`, and mode/tool
submodules to mutate molecules, bonds, atoms, labels, and transforms.

The goal is to preserve this behavior exactly in the Qt version.


## Entry-point architecture for drawing actions

## 1) Main configures mode and current paper

`BKChem` sets current mode and paper, then delegates all drawing interactions
to `chem_paper` plus the active mode object.

- mode switching and submode UI:
  [main_modes.py](../../packages/bkchem-app/bkchem/main_lib/main_modes.py)
- active tab/paper switching:
  [main_tabs.py](../../packages/bkchem-app/bkchem/main_lib/main_tabs.py)


## 2) Paper converts Tk events and dispatches to mode

`PaperEventsMixin.set_bindings()` binds canvas mouse/key events, converts
coordinates to paper coordinates, and calls mode callbacks:

- button 1 down/up/drag -> `mode.mouse_down`, `mode.mouse_up`, `mode.mouse_drag`
- right/middle click -> `mode.mouse_down3`, `mode.mouse_down2`
- key press/release -> `mode.key_pressed`, `mode.key_released`

Source:
[paper_events.py](../../packages/bkchem-app/bkchem/paper_lib/paper_events.py)

This is the core event contract. Qt parity should preserve this separation:
the view dispatches, the mode decides, the document mutates.


## 3) Modes mutate the paper/document model

Most tools inherit from `edit_mode`, which provides shared selection, moving,
delete, text editing, clipboard, and undo-boundary behavior.

Source:
[edit_mode.py](../../packages/bkchem-app/bkchem/modes/edit_mode.py)


## Call-flow by operation

## A) Drawing bonds and adding atoms (draw mode)

Primary mode:
[draw_mode.py](../../packages/bkchem-app/bkchem/modes/draw_mode.py)

Low-level model:
[molecule_lib.py](../../packages/bkchem-app/bkchem/molecule_lib.py),
[bond_type_control.py](../../packages/bkchem-app/bkchem/bond_type_control.py)

Flow:

1. `paper_events._pressed1` -> `draw_mode.mouse_down`.
2. If no focused atom/bond, draw mode creates a new molecule and seed atom at
   click position (with optional hex-grid snap).
3. On click release without drag, `draw_mode.mouse_click`:
   - on atom focus: create `BkBond`, call `molecule.add_atom_to(...)`,
     select new atom.
   - on bond focus: call `bond.toggle_type(...)` for type/order/style cycling.
4. On drag, `draw_mode.mouse_drag`:
   - create provisional endpoint atom + bond from start atom.
   - move endpoint using fixed-length angle snap or free-length drag.
   - optional hex-grid snap for dragged endpoint.
5. On release, `draw_mode.mouse_up`:
   - overlap reconciliation (`paper.handle_overlap`),
   - valency update and warnings (`update_after_valency_change`,
     free-valency checks),
   - double-bond side repositioning around affected atoms/bonds,
   - finalize with `start_new_undo_record()`.

Notable behavior to preserve:

- bond order/type are controlled by draw submodes.
- clicking an existing bond is an edit operation (type/order cycle), not just
  selection.
- free/fixed-length branch exists in draw submode and affects drag geometry.
- ring/overlap closure logic runs at mouse-up.


## B) Adding/changing atom letter labels

Two pathways are used in Tk:

### Path 1: keyboard-driven label editing in edit mode

`edit_mode` key sequences:

- letter/space/Return captured by `basic_mode` key queue
- mapped to `_set_name_to_selected` / `_set_old_name_to_selected`
- opens edit pool entry UI (`editPool.activate`)
- commits via `paper.set_name_to_selected`

Sources:
[edit_mode.py](../../packages/bkchem-app/bkchem/modes/edit_mode.py),
[edit_pool.py](../../packages/bkchem-app/bkchem/edit_pool.py),
[paper_layout.py](../../packages/bkchem-app/bkchem/paper_lib/paper_layout.py)

`set_name_to_selected` behavior:

- for atom-like vertices, creates replacement vertex class using
  `molecule.create_vertex_according_to_text(...)`.
- copies settings, rewires bonds with `replace_vertices`, redraws new vertex.
- triggers reposition of nearby bonds/marks and undo record.

### Path 2: explicit atom mode click editing

`atom_mode.mouse_click`:

- click empty space: prompt for symbol/text, create vertex according to text.
- click existing vertex: prompt and replace vertex class/symbol similarly.

Source:
[atom_mode.py](../../packages/bkchem-app/bkchem/modes/atom_mode.py)

Important detail:

- `BkAtom.update_after_valency_change()` redraws hydrogens when valency shifts.
- atom textual representation is dynamic (`xml_ftext`), including hydrogens and
  charge formatting.

Source:
[atom_lib.py](../../packages/bkchem-app/bkchem/atom_lib.py)


## C) Moving atoms/bonds/selections

Shared logic in `edit_mode.mouse_drag`:

- determines drag intent:
  - drag selected items,
  - drag focused container,
  - resize selection handles,
  - rectangle-select region.
- for selected move:
  - includes neighbor atoms/bonds/arrows that must be redrawn,
  - supports hex-grid snapping of moved selection via anchor atom,
  - updates bond geometry live during drag.

On `mouse_up` after drag:

- atom label placement recalculation (`decide_pos`),
- double-bond side repositioning around changed geometry,
- overlap handling and undo record.

Source:
[edit_mode.py](../../packages/bkchem-app/bkchem/modes/edit_mode.py)


## D) Deleting bonds/atoms/objects

Flow:

1. Delete or Backspace key -> `edit_mode._delete_selected`.
2. Calls `paper.delete_selected()`.
3. `PaperSelectionMixin.delete_selected` removes by object category
   (arrows, pluses, text, vectors, bonds/atoms).
4. For molecular items it calls `molecule.delete_items(...)`.
5. `molecule.delete_items`:
   - deletes atoms/bonds,
   - removes orphan bonds and atoms,
   - re-splits disconnected components via `check_integrity`,
   - redraws affected double bonds and atoms.
6. `paper.start_new_undo_record()` when applicable.

Sources:
[edit_mode.py](../../packages/bkchem-app/bkchem/modes/edit_mode.py),
[paper_selection.py](../../packages/bkchem-app/bkchem/paper_lib/paper_selection.py),
[molecule_lib.py](../../packages/bkchem-app/bkchem/molecule_lib.py)


## E) Changing bond types/orders/styles

Primary user action:

- click bond in draw mode (`draw_mode.mouse_click`) with current draw submodes.

Mechanism:

- `BkBond.toggle_type(...)` applies type/order switching rules.
- handles wedge/hash orientation flips, double-bond centered/side toggles,
  equithick behavior for hashed/wedge variants.
- redraws bond immediately.

Sources:
[draw_mode.py](../../packages/bkchem-app/bkchem/modes/draw_mode.py),
[bond_type_control.py](../../packages/bkchem-app/bkchem/bond_type_control.py)

Behavior to preserve:

- repeated click cycles style/order states, not a one-shot assign only.
- Shift-click special handling is distinct (`only_shift` path).


## F) Rotating about a bond and general rotation

Tool mode:
[rotate_mode.py](../../packages/bkchem-app/bkchem/modes/rotate_mode.py)

Supported flows:

- 2D rotation of molecule or arrow around computed center.
- 3D rotation of molecule by drag.
- 3D rotation around fixed bond (`fixsomething` submode):
  - selected bond is axis,
  - shift can restrict rotating subset depending on connected component split.

Lifecycle:

1. `mouse_down` captures rotated target and center/axis setup.
2. `mouse_drag` applies transform incrementally.
3. `mouse_up` redraws/repositions and records undo.


## G) Bond-based transformations (align/mirror/invert/free rotation)

Tool mode:
[bondalign_mode.py](../../packages/bkchem-app/bkchem/modes/bondalign_mode.py)

Important distinction:

- Transform is executed on `mouse_down` after selecting required atoms/bond.
- `mouse_drag` and `mouse_up` are intentionally no-op in this mode.

Operations include:

- align bond horizontal/vertical (`tohoriz`, `tovert`),
- invert through point,
- mirror through line,
- free rotation of one connected component around a bond axis.

After transform:

- full redraw (`paper.redraw_all`),
- `start_new_undo_record()`,
- refresh bindings.


## H) Geometry cleanup and snap transformations

Tool mode:
[repair_mode.py](../../packages/bkchem-app/bkchem/modes/repair_mode.py)

Single-click operations on focused molecule:

- normalize lengths,
- normalize angles,
- normalize rings,
- straighten bonds,
- snap molecule to hex grid,
- clean geometry (selection-based clean path).

Backed by:

- `oasa.repair_ops.*`,
- `paper.clean_selected` for selection-driven coordinate regeneration.


## Where `main.py` matters most for drawing

`main.py` participates through:

- mode/submode activation and ribbon rebuild:
  [main_modes.py](../../packages/bkchem-app/bkchem/main_lib/main_modes.py)
- edit pool visibility by mode (`show_edit_pool` contract),
- status updates (mode name, cursor position, zoom),
- menu action wiring that calls paper/mode operations.

It does not mutate bonds/atoms directly; it orchestrates tool routing.


## Non-obvious behaviors that define Tk quality

1. Selection-aware drag updates neighboring bonds/arrows continuously.
2. Overlap merge is part of draw/move finalization, not a separate command.
3. Atom class replacement on text change (`atom`, `group`, `query`, `textatom`)
   is automatic and chemically aware.
4. Bond toggle logic is stateful and chemistry-informed, not only visual.
5. Transform modes have different gesture semantics:
   rotate is drag-based, bondalign is click-apply.
6. Undo boundaries are explicit at operation end, preserving predictable undo.


## Qt parity checklist for drawing environment

To claim parity for drawing interactions, Qt must satisfy:

1. Event dispatch boundary: view events -> active mode callbacks.
2. Shared edit-mode behavior for select/move/delete/text, reused by draw/atom.
3. Draw-mode click and drag semantics (including bond click toggling).
4. Label editing through edit pool equivalent and atom-class replacement logic.
5. Delete pipeline with molecule integrity checks and split handling.
6. Rotate mode 2D/3D/fixed-axis behavior.
7. Bondalign click-apply transform behavior (no drag dependency).
8. Repair-mode click operations mapped to geometry ops.
9. Continuous redraw and post-op cleanup (marks, double bonds, overlap).
10. Stable undo record boundaries matching operation completion.


## Suggested test focus from this analysis

1. UI-driven bond draw tests: click atom -> bond added, click bond -> toggle.
2. Label replacement tests: atom text edits change class correctly.
3. Move tests: dragged selections keep adjacent bond geometry valid.
4. Delete tests: bond/atom delete preserves graph integrity and splits molecule.
5. Rotation tests: fixed-bond rotation only rotates intended component.
6. Bondalign tests: click operation applies transform without drag.
7. Undo tests: one logical op == one undo step across tools.
