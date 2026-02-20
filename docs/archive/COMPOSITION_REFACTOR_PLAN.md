# Composition refactor plan

Replace OASA inheritance with composition in BKChem GUI classes. See
[docs/CDML_BACKEND_TO_FRONTEND_CONTRACT.md](../CDML_BACKEND_TO_FRONTEND_CONTRACT.md)
for the boundary contract.

## Wave 1: foundation infrastructure

All new files. No overlap with existing code. Each coder owns distinct files.

| Coder | Stream | Owned files | Goal |
| --- | --- | --- | --- |
| C1 | Protocol interfaces | `packages/bkchem-app/bkchem/chem_protocols.py` | `ChemVertexProtocol`, `ChemEdgeProtocol`, `ChemGraphProtocol` |
| C2 | ABC registration | `packages/bkchem-app/bkchem/chem_compat.py` | Register BKChem classes with OASA ABCs |
| C3 | Bond parity tests | `packages/bkchem-app/tests/test_bond_composition_parity.py` | Inheritance vs composition bond comparison |
| C4 | Atom parity tests | `packages/bkchem-app/tests/test_atom_composition_parity.py` | Inheritance vs composition atom comparison |
| C5 | Molecule parity tests | `packages/bkchem-app/tests/test_molecule_composition_parity.py` | Graph ops and factory method comparison |
| C6 | CDML round-trip tests | `packages/bkchem-app/tests/test_cdml_roundtrip_parity.py` | Save-load-compare for all object types |
| C7 | isinstance audit | `docs/ISINSTANCE_AUDIT.md` | Every `isinstance(x, oasa.*)` with replacement strategy |
| C8 | Internal access audit | `docs/INTERNAL_ACCESS_AUDIT.md` | Every `._vertices`, `._neighbors`, `._edges` access |

### Wave 1 acceptance gate

- All new files pass pyflakes
- All test files run (may skip/xfail pending composition code)
- Audit reports are complete
- Protocol interfaces match contract document

---

## Wave 2: shadow layer

Add composition wrappers. OASA classes stay in MRO (shadow-first). Each coder
owns one distinct production file.

| Coder | Stream | Owned files | Goal |
| --- | --- | --- | --- |
| C1 | Bond shadow | `bond.py` | Add `_chem_bond`, redirect `order`/`type`/`aromatic` |
| C2 | Atom shadow | `atom.py` | Add `_chem_atom`, redirect `symbol`/`isotope` |
| C3 | Queryatom shadow | `queryatom.py` | Add `_chem_query_atom`, redirect query properties |
| C4 | Bond CDML adapter | `bond_cdml.py` | Use `_chem_bond` in `read_package`/`get_package` |
| C5 | Bond display adapter | `bond_display.py`, `bond_drawing.py` | Use `_chem_bond` for chemistry reads |
| C6 | Bond type/render | `bond_type_control.py`, `bond_render_ops.py` | Use `_chem_bond` for chemistry reads |
| C7 | GraphVertexMixin | new `packages/bkchem-app/bkchem/graph_vertex_mixin.py` | Replicate `oasa.graph.vertex` interface |
| C8 | Bridge update | `oasa_bridge.py` | Add `_chem_bond`/`_chem_atom` awareness |

### Wave 2 acceptance gate

- All existing tests still pass
- Parity tests from Wave 1 pass against shadowed classes
- CDML round-trip tests pass
- Pyflakes clean

---

## Wave 3: MRO removal and molecule

Remove OASA from class bases. Some streams have dependencies.

| Coder | Stream | Owned files | Depends on | Goal |
| --- | --- | --- | --- | --- |
| C1 | Bond MRO removal | `bond.py` | Wave 2 C1 | Remove `oasa.bond` from bases |
| C2 | Atom MRO removal | `atom.py` | Wave 2 C2 | Remove `oasa.atom` from bases |
| C3 | Queryatom MRO removal | `queryatom.py` | Wave 2 C3 | Remove `oasa.query_atom` from bases |
| C4 | drawable decoupling | `special_parents.py` | C1+C2+C3 | Remove `oasa.chem_vertex`, add `GraphVertexMixin` |
| C5 | isinstance migration | `modes.py`, `context_menu.py` | Wave 1 C7 | Replace `isinstance(x, oasa.*)` |
| C6 | isinstance migration | `paper.py`, `interactors.py` | Wave 1 C7 | Same pattern, different files |
| C7 | Molecule shadow | `molecule.py` | C4 | Add `_chem_mol`, shadow graph ops |
| C8 | Molecule MRO removal | `molecule.py` | C7 | Remove `oasa.molecule` from bases |

### Wave 3 sub-ordering

- C1, C2, C3 start immediately (parallel)
- C5, C6 start immediately (parallel, independent files)
- C4 starts after C1+C2+C3 complete
- C7 starts after C4 completes
- C8 starts after C7 completes

### Wave 3 acceptance gate

- No `oasa.*` in any BKChem class base list
- All parity tests pass
- CDML round-trip tests pass
- Full pyflakes clean
- Application starts and basic molecule drawing works

---

## Verification commands

After each wave:

```bash
source source_me.sh && python3 -m pytest tests/test_pyflakes_code_lint.py
source source_me.sh && python3 -m pytest tests/test_ascii_compliance.py
source source_me.sh && python3 -m pytest packages/bkchem-app/tests/ -k composition
source source_me.sh && python3 -m pytest packages/bkchem-app/tests/ -k cdml
```

---

## File ownership summary

| File | Wave 2 owner | Wave 3 owner |
| --- | --- | --- |
| `bond.py` | C1 | C1 |
| `atom.py` | C2 | C2 |
| `queryatom.py` | C3 | C3 |
| `bond_cdml.py` | C4 | -- |
| `bond_display.py`, `bond_drawing.py` | C5 | -- |
| `bond_type_control.py`, `bond_render_ops.py` | C6 | -- |
| `oasa_bridge.py` | C8 | -- |
| `special_parents.py` | -- | C4 |
| `modes.py`, `context_menu.py` | -- | C5 |
| `paper.py`, `interactors.py` | -- | C6 |
| `molecule.py` | -- | C7 then C8 |

---

## Risk register

| Risk | Severity | Wave | Mitigation |
| --- | --- | --- | --- |
| `isinstance` checks fail after MRO removal | High | 3 | ABC registration in Wave 1 C2, audit in Wave 1 C7 |
| `_vertices` access breaks bond rendering | High | 2-3 | Shadow with local list first, then remove |
| `occupied_valency` returns wrong values | High | 3 | Keep reading from graph `_neighbors` |
| Graph algorithms fail on duck-typed vertices | Medium | 3 | `GraphVertexMixin` replicates exact interface |
| Two coders accidentally edit same file | Medium | any | File ownership table enforced per wave |
| Undo system breaks | Medium | 3 | Undo reads properties by name, verify each wave |
