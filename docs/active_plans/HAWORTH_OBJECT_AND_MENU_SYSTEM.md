# Haworth object and menu system

## Goals
- Add Haworth sugar ring projections (furanose and pyranose) to the BKChem GUI
  via the Insert menu.
- Render with perspective thick-line style (thick front bonds, thin back bonds).
- Insert a real editable molecule whose ring bonds retain Haworth front/back
  depiction tags.

## Non-goals
- Do not add a full Haworth toolbar mode (menu items are sufficient).
- Do not modify existing atom/bond editing logic in the first iteration.
- Do not support disaccharide chains or glycosidic linkage automation.

## Design decisions needed

### Ring object type
Two strategies were considered:

**Strategy A: Custom canvas group**
- Render the Haworth ring as a grouped Tk canvas item (polygon + thick/thin
  lines) that acts as a single draggable object.
- Define attachment points at each ring carbon position.
- When the user draws a bond ending near an attachment point, snap to it.
- Ring internal geometry is locked; only external bonds are editable.
- Simpler to implement but less integrated with chemistry operations (SMILES
  export, valence checking, etc. would not see the ring atoms).

**Strategy B: Molecule with locked ring flag**
- Insert as a real BKChem molecule with atoms and bonds.
- Add a `locked` flag to ring atoms/bonds that prevents editing.
- Ring bonds render with thick-front/thin-back style via custom draw code.
- External atoms/bonds are fully editable.
- More complex but fully integrated with OASA chemistry.

**Decision (2026-07-28)**: the Qt frontend uses Strategy B's real-molecule
boundary without an initial locking layer. This makes the inserted sugar
immediately usable by atom/bond editing, chemistry checks, SMILES export, and
CDML. Ring locking, multi-ring/disaccharide automation, and attachment-aware
glycosidic construction remain out of scope for this first slice.

### User configuration dialog
On insertion, a dialog should offer:
- Ring type: pyranose (6-membered) or furanose (5-membered), pre-selected
  based on which menu item was clicked.
- Anomeric form: alpha or beta (radio buttons).
- No D/L selector: the entered sugar code is authoritative for D/L and avoids
  contradictory duplicate state.
- Optional: sugar name dropdown (glucose, galactose, mannose, etc.) that
  auto-configures substituent positions.

## Existing backend code

The OASA package has extensive Haworth support already:

| Component | File | Notes |
| --- | --- | --- |
| Ring templates | `packages/oasa/oasa/haworth/__init__.py` | `PYRANOSE_TEMPLATE`, `FURANOSE_TEMPLATE` coordinate arrays |
| Spec builder | `packages/oasa/oasa/haworth/spec.py` | `HaworthSpec` dataclass, `generate()` for stereochemistry |
| Full renderer | `packages/oasa/oasa/haworth/renderer.py` | 2057 lines, perspective rendering with thick/thin bonds |
| Layout | `packages/oasa/oasa/haworth/fragment_layout.py` | Fragment positioning |
| Geometry | `packages/oasa/oasa/haworth/renderer_geometry.py` | Wedge polygons, collision detection |
| Text | `packages/oasa/oasa/haworth/renderer_text.py` | Label placement |
| Config | `packages/oasa/oasa/haworth/renderer_config.py` | Rendering parameters |
| Sugar codes | `packages/oasa/oasa/sugar_code.py` | Compact notation for carbohydrates |
| SMILES data | `packages/oasa/oasa_data/biomolecule_smiles.yaml` | Scaffold SMILES for furanose/pyranose |

## Menu structure

Add to Insert menu in `packages/bkchem-qt.app/bkchem_qt/resources/menus.yaml`:

```yaml
- action: insert.haworth_pyranose
- action: insert.haworth_furanose
```

## Files to create

- `packages/bkchem-qt.app/bkchem_qt/actions/haworth_actions.py` -- dialog,
  session-owned worker request, and undoable GUI delivery

## Files to modify

- `packages/bkchem-qt.app/bkchem_qt/resources/menus.yaml` -- add menu items
- `packages/bkchem-qt.app/bkchem_qt/bridge/oasa_bridge.py` -- retain Haworth
  front/back depiction tags across the model bridge

## Implemented insertion flow (editable molecule)

1. User clicks "Insert > Haworth pyranose" or "Haworth furanose".
2. Dialog appears with alpha/beta; D/L derives from the sugar code.
3. On OK:
   a. A session-owned OASA worker converts sugar code to stereochemical SMILES,
      generates initial coordinates, and calls `haworth.layout.build_haworth`.
   b. The queued GUI relay converts the OASA graph into one `MoleculeModel` at
      the active scene bond length.
   c. `AddMoleculeCommand` inserts its real atoms, bonds, and graphics, making
      both insertion and undo consistent with all other molecule imports.

## Testing needs

- Focused preparation test: known glucose code produces editable OASA/Qt
  topology with a wide Haworth front edge.
- Focused delivery test: a prepared model enters the originating session and
  undo returns that session to its clean baseline.

## Remaining boundary

- **Multi-ring chemistry**: OASA now has a pure direct-glycosidic planner for
  two strict 5/6-member C/O rings and one external oxygen bridge. This menu
  slice still does not deliver disaccharides to the document, infer carbon
  numbering, place exocyclic substituents, or automate larger glycans.
- **Ring locking**: editable atoms and bonds are deliberate for this first
  real-molecule implementation; a later interaction policy may add locks.
