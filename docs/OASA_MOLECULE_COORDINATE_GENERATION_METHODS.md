# OASA molecule coordinate generation methods

## Overview

2D coordinate generation assigns x,y positions to every atom in a molecule so
that a structure diagram can be rendered on screen or in an SVG/PNG export. The
goal is a layout that looks like a hand-drawn structural formula: rings are
regular polygons, chains extend in a zigzag, atoms do not overlap, and bond
lengths are uniform.

OASA delegates all 2D coordinate generation to RDKit's `Compute2DCoords`
algorithm via the bridge module
[packages/oasa/oasa/rdkit_bridge.py](../packages/oasa/oasa/rdkit_bridge.py).
RDKit is a required dependency declared in
[packages/oasa/pyproject.toml](../packages/oasa/pyproject.toml).

---

## Public API

The entry point for callers is `calculate_coords()` in
[packages/oasa/oasa/coords_generator.py](../packages/oasa/oasa/coords_generator.py):

```python
def calculate_coords(mol, bond_length: float = 0, force: int = 0) -> None
```

### Parameters

| Parameter | Type | Default | Behavior |
| --- | --- | --- | --- |
| `mol` | OASA molecule | required | Modified in place |
| `bond_length` | float | 0 | 0: use default (1.0). -1: derive from existing coords. >0: use specified value |
| `force` | int | 0 | 0: skip if all atoms already have coords. 1: regenerate unconditionally |

### `bond_length` semantics

- `bond_length > 0`: RDKit generates coordinates scaled so the average bond
  length equals this value.
- `bond_length == 0`: uses the default value of 1.0.
- `bond_length == -1`: measures the average bond length from existing
  coordinates (useful when molecules are loaded from CDML with pixel-scale
  coordinates), then scales RDKit output to match.

### `force` semantics

- `force == 0`: if every atom already has non-None x and y coordinates, return
  immediately without calling RDKit. This preserves hand-placed or loaded
  coordinates.
- `force == 1`: always regenerate coordinates via RDKit, overwriting any
  existing positions.

---

## Bridge conversion pipeline

The coordinate generation pipeline works as follows:

1. `coords_generator.calculate_coords()` resolves `bond_length` and `force`,
   then calls `rdkit_bridge.calculate_coords_rdkit()`.
2. `calculate_coords_rdkit()` converts the OASA molecule to an RDKit `RWMol`
   via `oasa_to_rdkit_mol()`.
3. RDKit's `AllChem.Compute2DCoords()` generates 2D coordinates.
4. `AllChem.StraightenDepiction()` cleans up the layout.
5. Coordinates are scaled to match the requested `bond_length` and copied
   back into the OASA atom `.x` and `.y` attributes.

---

## Callers

| Caller | Import | Usage |
| --- | --- | --- |
| [packages/oasa/oasa/smiles_lib.py](../packages/oasa/oasa/smiles_lib.py) | `from oasa import coords_generator` | SMILES parsing with coord generation |
| [packages/oasa/oasa/inchi_lib.py](../packages/oasa/oasa/inchi_lib.py) | `from oasa import coords_generator` | InChI parsing with coord generation |
| [packages/oasa/oasa/cdml.py](../packages/oasa/oasa/cdml.py) | `from oasa.coords_generator import calculate_coords` | CDML loading with `bond_length=-1` |
| [packages/oasa/oasa/linear_formula.py](../packages/oasa/oasa/linear_formula.py) | `from oasa import coords_generator` | Linear formula parsing |
| [packages/oasa/oasa/haworth/fragment_layout.py](../packages/oasa/oasa/haworth/fragment_layout.py) | `from oasa import coords_generator` | Haworth substituent layout |
| [packages/bkchem-app/bkchem/oasa_bridge.py](../packages/bkchem-app/bkchem/oasa_bridge.py) | `from oasa import coords_generator` | BKChem GUI bridge |
| [packages/bkchem-app/bkchem/group_lib.py](../packages/bkchem-app/bkchem/group_lib.py) | `oasa.coords_generator` | Group template loading |
| [packages/bkchem-app/bkchem/paper_lib/paper_layout.py](../packages/bkchem-app/bkchem/paper_lib/paper_layout.py) | `import oasa.coords_generator` | Paper layout with `force=0, bond_length=-1` |

---

## Testing strategy

**Pytest unit tests.**
[packages/oasa/tests/test_coords_generator2.py](../packages/oasa/tests/test_coords_generator2.py)
covers the coordinate generator with molecules parsed from SMILES:

- Single atom, single bond, linear chains, branched molecules, ring systems.
- Verifies every atom receives non-None x,y coordinates.
- Checks bond length uniformity (all bonds within tolerance of the target length).
- Checks minimum non-bonded separation to catch gross overlaps.
- Cage molecules (cubane, adamantane, norbornane).
- Force parameter behavior (force=0 preserves, force=1 regenerates).
- Complex multi-ring systems (steroids, sucrose, raffinose).

Run with:
```bash
source source_me.sh && python -m pytest packages/oasa/tests/test_coords_generator2.py -v
```

**RDKit bridge tests.**
[packages/oasa/tests/test_rdkit_bridge.py](../packages/oasa/tests/test_rdkit_bridge.py)
tests the OASA-to-RDKit conversion roundtrip and coordinate generation directly.

Run with:
```bash
source source_me.sh && python -m pytest packages/oasa/tests/test_rdkit_bridge.py -v
```

**Pyflakes lint.**
```bash
source source_me.sh && python -m pytest tests/test_pyflakes_code_lint.py
```

---

## File map

| File | Responsibility |
| --- | --- |
| [coords_generator.py](../packages/oasa/oasa/coords_generator.py) | Public API with `bond_length` and `force` semantics |
| [rdkit_bridge.py](../packages/oasa/oasa/rdkit_bridge.py) | OASA-to-RDKit conversion and `Compute2DCoords` call |
