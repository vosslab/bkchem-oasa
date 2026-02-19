# SMILES/IsoSMILES to CDML Import Plan

## Objective

Replace the existing direct-bridge SMILES import (`oasa_bridge.read_smiles` ->
`oasa_mol_to_bkchem_mol`) with a CDML-routed import path
(SMILES -> OASA molecule -> CDML XML -> BKChem `add_object_from_package`). This
aligns with the CDML Architecture Plan where CDML is the canonical transfer
layer between OASA and BKChem.

## Design philosophy

CDML is the serialization contract between OASA and BKChem
([docs/archive/CDML_ARCHITECTURE_PLAN.md](docs/archive/CDML_ARCHITECTURE_PLAN.md)).
The current `read_smiles` bypasses this contract by calling
`oasa_mol_to_bkchem_mol()` directly. This plan routes SMILES import through the
canonical CDML path so that:

- All molecule transfers go through one pipeline.
- BKChem receives a standard CDML DOM element, the same as file import and
  clipboard paste.
- Property fidelity is governed by the CDML spec, not ad-hoc bridge code.
- Future import sources (PubChem, InChI) can reuse the same CDML import path.

## Scope

- **In scope**: SMILES and IsoSMILES text input via BKChem GUI dialog, routed
  through OASA CDML serialization, imported as a standard CDML molecule.
- **In scope**: Update the existing Chemistry > Read SMILES menu entry and
  dialog.
- **In scope**: Add an `oasa_bridge` helper that converts SMILES text to a CDML
  DOM element via OASA.

## Non-goals

- No changes to OASA SMILES parser (`oasa/smiles.py`).
- No changes to OASA CDML writer (`oasa/cdml_writer.py`).
- No changes to the BKChem CDML reading pipeline (`paper.read_package`,
  `molecule.read_package`, `CDML_versions.py`).
- No new menu entries (reuse existing "Read SMILES" command).
- No PubChem integration (separate plan).
- No OASA changes at all; this is BKChem-only.

## Current state summary

### Existing SMILES import path

`main.py:read_smiles()` (line 1262):

1. Shows `Pmw.PromptDialog` with outdated warning text about missing stereo
   support.
2. Calls `oasa_bridge.read_smiles(text, self.paper)`.
3. Bridge calls `oasa.codec_registry.get_codec("smiles").read_text(text)` to
   get an OASA molecule.
4. Bridge calls `_calculate_coords(mol)` for 2D layout.
5. Bridge calls `oasa_mol_to_bkchem_mol(mol, paper)` to convert directly.
6. `main.py` appends molecule to paper stack, draws, adds bindings.

### CDML import path (already working for files and clipboard)

`paper.paste_clipboard()` (line 980) and `paper.read_package()` (line 532):

1. Parse XML DOM nodes.
2. Call `paper.add_object_from_package(dom_element)` for each child.
3. For `<molecule>` nodes: `molecule(self, package=dom_element)` which calls
   `molecule.read_package()`.
4. `molecule.read_package()` processes CDML `<atom>`, `<group>`, `<bond>`
   elements with full property support.

### OASA CDML writer (already working)

`oasa/cdml_writer.py`:

- `write_cdml_molecule_element(mol)` -> `minidom.Element` (line 117)
- `mol_to_text(mol)` -> full CDML XML string with `<cdml>` wrapper (line 152)

## Architecture boundaries and ownership

| Component | Owner | Changes |
| --- | --- | --- |
| `oasa/smiles.py` | OASA | None |
| `oasa/cdml_writer.py` | OASA | None |
| `oasa/coords_generator*.py` | OASA | None |
| `bkchem/oasa_bridge.py` | BKChem | Add `smiles_to_cdml_element()` |
| `bkchem/main.py` | BKChem | Update `read_smiles()` dialog and import path |
| `bkchem/paper.py` | BKChem | None |
| `bkchem/molecule.py` | BKChem | None |

## Phase plan

### Phase 1: Add SMILES-to-CDML bridge function

**Deliverable**: New function `smiles_to_cdml_element(text, paper)` in
`oasa_bridge.py`.

**Implementation**:

```
def smiles_to_cdml_element(smiles_text, paper):
    # 1. Parse SMILES to OASA molecule
    codec = _get_codec("smiles")
    mol = codec.read_text(smiles_text)
    # 2. Generate 2D coordinates
    _calculate_coords(mol, bond_length=1.0, force=1)
    # 3. Rescale coordinates to BKChem screen units
    #    (use Screen.any_to_px and paper.standard.bond_length)
    # 4. Serialize to CDML DOM element
    element = cdml_writer.write_cdml_molecule_element(mol)
    return element
```

The coordinate rescaling step is critical. Currently `oasa_mol_to_bkchem_mol`
rescales from OASA abstract units to BKChem screen pixels using
`Screen.any_to_px(paper.standard.bond_length)`. The CDML writer outputs
coordinates in cm via `POINTS_PER_CM`. The BKChem CDML reader
(`molecule.read_package`) uses `misc.split_number_and_unit()` and
`Screen.any_to_px()` to convert cm to screen pixels.

**Coordinate strategy**: After `_calculate_coords`, scale the OASA molecule
coordinates so the average bond length matches `paper.standard.bond_length`
(in cm), then let the CDML writer emit cm coordinates. BKChem's reader handles
the cm-to-pixel conversion automatically.

**Done check**:
- Function exists and is callable.
- Given "CCO" (ethanol), returns a valid `minidom.Element` with `<molecule>`
  containing `<atom>` and `<bond>` children with cm coordinates.

### Phase 2: Wire dialog to CDML import path

**Deliverable**: Updated `main.py:read_smiles()` that uses the CDML path.

**Implementation**:

1. Update dialog text: remove the outdated warning about missing stereo/bracket
   support. OASA SMILES parser supports stereochemistry and brackets. New text:
   `"Enter a SMILES or IsoSMILES string:"`.
2. Call `oasa_bridge.smiles_to_cdml_element(text, self.paper)` instead of
   `oasa_bridge.read_smiles(text, self.paper)`.
3. Import the element using `self.paper.add_object_from_package(element)`.
4. Draw, add bindings, start undo record (same as current code).

**Centering**: The CDML import path does not auto-center on the canvas.
After import, translate the molecule to center of the current viewport. The
existing `paste_clipboard` uses an offset from clipboard position. For SMILES
import, center on the visible canvas area.

**Done check**:
- Entering "CCO" in the dialog produces ethanol on the canvas.
- Entering "C1=CC=CC=C1" produces benzene.
- Entering "OC[C@@H](O)[C@H](O)C=O" produces a sugar with stereo wedges.
- The molecule appears centered on the visible canvas.
- Undo reverses the import.

### Phase 3: Tests

**Deliverable**: Pytest tests for the bridge function and integration.

**Test file**: `tests/test_smiles_cdml_import.py`

**Unit tests**:
- `test_smiles_to_cdml_element_ethanol`: "CCO" produces `<molecule>` with 3
  atoms and 2 bonds.
- `test_smiles_to_cdml_element_benzene`: "c1ccccc1" produces 6 atoms, 6 bonds.
- `test_smiles_to_cdml_element_coordinates_in_cm`: all `<point>` elements have
  `x` and `y` attributes ending in "cm".
- `test_smiles_to_cdml_element_bond_length_reasonable`: average bond length in
  the output is close to `paper.standard.bond_length`.
- `test_smiles_to_cdml_element_stereo_wedges`: IsoSMILES with `@@` produce
  wedge bond types (`w1` or `h1`) in CDML output.
- `test_smiles_to_cdml_element_empty_raises`: empty string raises ValueError.
- `test_smiles_to_cdml_element_invalid_raises`: invalid SMILES raises an error.

**Done check**:
- All tests pass with `pytest tests/test_smiles_cdml_import.py -q`.

### Phase 4: Cleanup

**Deliverable**: Remove the old direct-bridge SMILES import path.

**Implementation**:
- Remove `oasa_bridge.read_smiles()` function (lines 107-111).
- Verify no other callers reference `oasa_bridge.read_smiles`.
- Update any imports if needed.

**Done check**:
- `grep -r "oasa_bridge.read_smiles" packages/bkchem-app/` returns zero hits
  (except possibly tests that test the new path).
- Full test suite passes.

## Acceptance criteria and gates

| Gate | Criteria | Measured by |
| --- | --- | --- |
| CDML element valid | Output parses as valid XML with `<molecule>`, `<atom>`, `<bond>` | Unit test |
| Coordinates correct | cm-unit coordinates, bond length matches standard | Unit test |
| Stereo preserved | IsoSMILES stereo produces wedge/hash bonds in CDML | Unit test |
| GUI functional | Dialog accepts SMILES, molecule appears on canvas | Manual test |
| Undo works | Ctrl+Z after import removes the molecule | Manual test |
| No regressions | Existing test suite passes | `pytest tests/ -q` |
| Old path removed | No references to `oasa_bridge.read_smiles` | grep check |

## Test and verification strategy

- **Unit tests**: Pure Python, no GUI dependency. Test `smiles_to_cdml_element`
  with known SMILES inputs and verify DOM output structure.
- **Smoke test**: Manual GUI test with 3-5 SMILES strings covering basic,
  aromatic, and stereo cases.
- **Regression**: Run existing test suite to confirm no breakage.
- **Pyflakes**: Run `pytest tests/test_pyflakes_code_lint.py` for import
  hygiene.

## Migration and compatibility policy

- **Additive**: Phase 1-2 add the new path. Phase 4 removes the old path.
- **No CDML version bump**: No changes to CDML format or version.
- **No OASA changes**: All changes are BKChem-side only.
- **Backward compatible**: The GUI behavior is the same (dialog -> molecule on
  canvas), only the internal pipeline changes.

## Risk register

| Risk | Impact | Trigger | Mitigation |
| --- | --- | --- | --- |
| Coordinate scaling mismatch | Molecules too large/small on canvas | Bond length units differ between OASA coords and CDML cm | Unit test verifies bond length matches standard; use existing `_calculate_coords` bond_length param |
| CDML reader rejects OASA-generated element | Import fails silently | Missing required attributes in generated CDML | Test round-trip: generate CDML, parse with BKChem reader, verify atom/bond counts |
| Stereo bonds not serialized to CDML | Wedge/hash bonds missing | OASA CDML writer does not emit stereo bond types from SMILES-parsed molecules | Test with IsoSMILES input; verify bond type attributes in output |
| Centering on canvas | Molecule appears off-screen | No viewport translation after import | Add explicit translation to canvas center after import |

## Rollout and release checklist

- [ ] Phase 1: `smiles_to_cdml_element` implemented and unit-tested
- [ ] Phase 2: `read_smiles` dialog updated and wired to CDML path
- [ ] Phase 3: All tests pass
- [ ] Phase 4: Old `oasa_bridge.read_smiles` removed
- [ ] Pyflakes clean
- [ ] Manual smoke test with GUI
- [ ] Changelog updated

## Documentation close-out

- Update `docs/CHANGELOG.md` with the change.
- Update `refactor_progress.md` to note SMILES import uses CDML path.
- Archive this plan to `docs/archive/` when Phase 4 is complete.

## Open questions

- **Q1**: Should the dialog title change from "Smiles" to "SMILES / IsoSMILES"?
  Recommendation: yes, to indicate stereo support.
- **Q2**: Should InChI import (`read_inchi`) also be migrated to the CDML path
  in this plan? Recommendation: no, keep it as a separate follow-up to limit
  scope.
- **Q3**: Should disconnected SMILES (e.g. "CC.OO") produce multiple molecules?
  The existing `_read_codec_file_to_bkchem_mols` handles disconnected graphs by
  splitting. The new function should do the same: check `mol.is_connected()`,
  split if needed, return one CDML element per component.

## References

- [docs/archive/CDML_ARCHITECTURE_PLAN.md](docs/archive/CDML_ARCHITECTURE_PLAN.md):
  OASA/BKChem boundary design
- [docs/CDML_FORMAT_SPEC.md](docs/CDML_FORMAT_SPEC.md):
  CDML format specification
- [docs/active_plans/PUBCHEM_API_PLAN.md](docs/active_plans/PUBCHEM_API_PLAN.md):
  Related future plan for molecule lookup
- `packages/bkchem-app/bkchem/oasa_bridge.py`: Current bridge code
- `packages/bkchem-app/bkchem/main.py` lines 1262-1289: Current `read_smiles`
- `packages/oasa/oasa/cdml_writer.py` lines 117-170: CDML molecule writer
