# Haworth object and menu system

## Goals
- Add Haworth sugar ring projections (furanose and pyranose) to the BKChem GUI
  via the Insert menu.
- Render with perspective thick-line style (thick front bonds, thin back bonds).
- Treat the ring as a single locked object that cannot be internally edited but
  allows external bonds to attach at ring carbon positions.

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

**Open question**: Which strategy to pursue? Strategy A is faster to build but
less useful for chemistry workflows. Strategy B is more work but the result is
a real molecule.

### User configuration dialog
On insertion, a dialog should offer:
- Ring type: pyranose (6-membered) or furanose (5-membered), pre-selected
  based on which menu item was clicked.
- Anomeric form: alpha or beta (radio buttons).
- Series: D or L (radio buttons).
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

Add to Insert menu in `packages/bkchem-app/bkchem_data/menus.yaml`:

```yaml
- action: insert.haworth_pyranose
- action: insert.haworth_furanose
```

## Files to create

- `packages/bkchem-app/bkchem/haworth_insert.py` -- dialog and insertion logic

## Files to modify

- `packages/bkchem-app/bkchem/actions/insert_actions.py` -- register actions
- `packages/bkchem-app/bkchem_data/menus.yaml` -- add menu items
- `packages/bkchem-app/bkchem/oasa_bridge.py` -- bridge helper if needed

## Insertion flow (Strategy A sketch)

1. User clicks "Insert > Haworth pyranose" or "Haworth furanose".
2. Dialog appears with alpha/beta, D/L radio buttons.
3. On OK:
   a. Build `HaworthSpec` from `oasa.haworth.spec`.
   b. Compute ring vertex positions from template arrays scaled to standard
      bond length.
   c. Draw thick-front/thin-back ring polygon on canvas as a grouped Tk canvas
      item (using `create_polygon`, `create_line` with varying widths).
   d. Store attachment point coordinates (one per ring carbon).
   e. Register the group as a canvas object that supports bond attachment.
   f. `paper.start_new_undo_record()`.

## Testing needs

- Unit tests for Haworth spec generation and coordinate computation.
- Integration test: insert a pyranose, verify canvas items are created.
- Integration test: draw a bond to a ring attachment point, verify connection.
- Manual smoke test: visual inspection of thick-front/thin-back rendering.

## Risks

- **Tk canvas limitations**: thick/thin perspective rendering may not look
  great with basic Tk canvas primitives. May need anti-aliased rendering
  or SVG-to-canvas conversion.
- **Bond attachment snapping**: detecting when a drawn bond endpoint is near
  a Haworth attachment point requires hooking into the draw mode's endpoint
  resolution logic.
- **CDML serialization**: custom canvas groups need save/load support in the
  CDML format. This is a non-trivial addition.
- **Chemistry integration**: Strategy A objects would not participate in
  SMILES generation, formula calculation, or substructure search.
