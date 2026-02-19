# Transformation operations

Reference for all coordinate transformations in BKChem/OASA.

## Matrix primitives

All transforms compose three primitives from `packages/oasa/oasa/transform.py`:

| Primitive | Method | Effect |
| --- | --- | --- |
| Translate | `set_move(dx, dy)` | Shift coordinates by (dx, dy) |
| Rotate | `set_rotation(angle)` | Rotate by angle (radians) around origin |
| Scale | `set_scaling_xy(mx, my)` | Scale axes independently |
| Uniform scale | `set_scaling(s)` | Scale both axes equally |

3D transforms use `packages/oasa/oasa/transform3d.py` which adds Z-axis
rotation via `set_rotation(angle_x, angle_y, angle_z)`.

## Operation catalog

### Global operations (apply to every atom in the molecule)

| Operation | Current location | Input | Matrix composition | Notes |
| --- | --- | --- | --- | --- |
| Move/translate | `molecule.move()` at `molecule.py:740` | dx, dy | Direct coord addition (no matrix) | BKChem display-only; plan adds OASA matrix version |
| Align to horizontal | `_transform_tohoriz` at `modes.py:1768` | Bond (2 atoms) | move(-cx,-cy), rotate(-bond_angle), move(cx,cy) | Flips 180 deg if already horizontal |
| Align to vertical | `_transform_tovert` at `modes.py:1790` | Bond (2 atoms) | move(-cx,-cy), rotate(pi/2 - bond_angle), move(cx,cy) | Flips 180 deg if already vertical |
| Invert through point | `_transform_invertthrough` at `modes.py:1810` | Point or bond midpoint | move(-x,-y), scale(-1,-1), move(x,y) | Equivalent to 180 deg rotation |
| Mirror through bond | `_transform_mirrorthrough` at `modes.py:1824` | Bond (2 atoms) | move(-cx,-cy), rotate(-a), scale(1,-1), rotate(a), move(cx,cy) | Reflects across the bond axis |
| Flip X | Planned: `cdml_transform_mirror.py` | Center point | move(-cx,-cy), scale(1,-1), move(cx,cy) | Mirror top-to-bottom (across horizontal axis) |
| Flip Y | Planned: `cdml_transform_mirror.py` | Center point | move(-cx,-cy), scale(-1,1), move(cx,cy) | Mirror left-to-right (across vertical axis) |
| 2D rotate | `rotate_mode` at `modes.py:1628` | Center + angle | move(-cx,-cy), rotate(angle), move(cx,cy) | Interactive drag during editing |
| 3D rotate (free) | `rotate_mode` at `modes.py:1654` | Center + dx/dy angles | transform3d: move, rotate(angleX, angleY, 0), move back | Updates x, y, and z per atom |

### Partial operations (apply to a subgraph)

These operations are interactive: BKChem handles the drag visually for
responsiveness, transforming only a subset of atoms on each mouse event. On
mouse-up, the final coordinates must be sent to OASA to update the CDML and
run overlap resolution. The user sees smooth dragging in BKChem, but the
authoritative coordinate update happens in OASA when the interaction ends.

| Operation | Current location | Input | Matrix composition | Notes |
| --- | --- | --- | --- | --- |
| Free rotation | `_transform_freerotation` at `modes.py:1840` | Bond (2 atoms) | Same matrix as mirror | Disconnects bond, applies only to the smaller connected component |
| 3D rotate (fixed axis) | `rotate_mode` at `modes.py:1638` | Bond axis + angle | `geometry.create_transformation_to_rotate_around_particular_axis()` | Rotates only `_rotated_atoms` subset from `_get_objs_to_rotate()` |

### Scale selected (hybrid operation)

`paper.scale_selected()` at `paper.py:1219` resizes selected objects on canvas.
Original Beda Kosata code from 2004. Supports anisotropic scaling
(ratio_x != ratio_y) which changes bond lengths and angles. Useful for fitting
reaction schemes to a page or normalizing bond lengths between pasted molecules.

Any anisotropic change to atom coordinates changes the underlying CDML, so the
molecule-scaling part must go through OASA like every other coordinate
transform. The non-molecule parts (arrows, text, shapes, fonts) stay in BKChem.

| Part | Owner | What it scales |
| --- | --- | --- |
| Atom coordinates | OASA | x, y positions of all atoms in the molecule |
| Bond widths | OASA | `bond_width` stored in CDML |
| Font sizes, mark sizes | BKChem | Display-only properties |
| Arrows, text, shapes | BKChem | Non-molecular canvas objects |

### Viewport zoom (BKChem only)

`paper.scale_all()` at `paper.py:1283` zooms the canvas in and out. Changes
`self._scale` and redraws. Never modifies atom coordinates or CDML.

## Owner layer

- **OASA** owns coordinate geometry: atom (x, y, z), bond angles, transforms
  that change molecular shape.
- **BKChem** owns display: canvas items, selection, fonts, viewport zoom,
  interactive drag feedback.

After the transform refactor (see plan), all coordinate transforms move to OASA
modules. BKChem serializes to CDML, calls OASA, and redraws from the result.

See [docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md](docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
for the full backend-to-frontend boundary contract.

## OASA transform modules (planned)

Each module implements:

```python
def apply(mol, ref_atoms: list, angle: float = 0.0):
    """Apply this transform to mol in-place. Return mol."""
```

| Module | Operations |
| --- | --- |
| `cdml_transform_align.py` | align_horiz, align_vert |
| `cdml_transform_mirror.py` | mirror, flip_x, flip_y |
| `cdml_transform_invert.py` | invert |
| `cdml_transform_rotate2d.py` | rotate2d |
| `cdml_transform_rotate3d.py` | rotate3d, rotate_fixed_axis |
| `cdml_transform_translate.py` | translate |
| `cdml_transform_scale.py` | scale (anisotropic), molecule part only |
| `cdml_transform_base.py` | Shared helpers and dispatcher |
| `cdml_transform_cli.py` | CLI batch tool |

## Transform pattern

All non-trivial transforms follow the same pattern:

1. Translate the reference point to the origin
2. Apply the core operation (rotate, scale, or both)
3. Translate back to the original reference point

```
tr = transform()
tr.set_move(-cx, -cy)       # step 1: center at origin
tr.set_rotation(angle)       # step 2: core operation
tr.set_move(cx, cy)          # step 3: restore position
mol.transform(tr)
```

Mirror through an arbitrary axis adds rotate-to-axis and rotate-back steps
around the scale (five-step composition):

```
tr.set_move(-cx, -cy)
tr.set_rotation(-axis_angle)
tr.set_scaling_xy(1, -1)
tr.set_rotation(axis_angle)
tr.set_move(cx, cy)
```

## Related work

- **Hexagonal grid alignment** (separate plan): OASA module (`hex_grid.py`)
  providing `snap_to_hex_grid()`, `all_atoms_on_hex_grid()`, and
  `all_bonds_on_hex_grid()`. Hex grid spacing matches bond length; standard
  chemistry structures (benzene, chair conformations, zigzag chains) land on
  grid points. Useful for validating transforms (rotate 60 degrees, check
  grid alignment preserved) and for `coords_generator2` snap-on-generate.
  Visual dot overlay and interactive snap-to-grid in BKChem are a separate
  Tk/PMW feature built on top of the OASA geometry.
