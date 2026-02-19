# Internal access audit

Audit of every `._vertices`, `._neighbors`, `._edges`, and `.properties_`
access in BKChem code that reaches into OASA internals. After the composition
refactor, BKChem classes will no longer inherit from OASA, so each of these
access points must be identified and fixed.

## Summary statistics

| Pattern | BKChem occurrences | Risk |
| --- | --- | --- |
| `._vertices` | 8 (all in bond.py) | High |
| `._neighbors` | 1 (special_parents.py) | Medium |
| `._edges` | 0 | None |
| `.properties_` | 2 (oasa_bridge.py, bond_cdml.py) | Low |
| **Total** | **11** | |

## Detailed findings

### `._vertices` access in bond.py

BKChem `bond` inherits from `oasa.bond` which inherits from
`oasa.graph.edge`. The `_vertices` list is defined in `oasa.graph.edge.__init__`
(line 29) and stores the two endpoint vertices of the edge. BKChem `bond`
properties (`atom1`, `atom2`, `atoms`) read and write `self._vertices` directly.

| File | Line | Code | Context | Fix strategy |
| --- | --- | --- | --- | --- |
| `bond.py` | 177 | `return self._vertices[0]` | `atom1` property getter | Shadow with local `_bond_vertices` list |
| `bond.py` | 185 | `self._vertices[0] = mol` | `atom1` setter, normal case | Shadow with local `_bond_vertices` list |
| `bond.py` | 187 | `self._vertices = [mol, None]` | `atom1` setter, IndexError fallback | Shadow with local `_bond_vertices` list |
| `bond.py` | 194 | `return self._vertices[1]` | `atom2` property getter | Shadow with local `_bond_vertices` list |
| `bond.py` | 202 | `self._vertices[1] = mol` | `atom2` setter, normal case | Shadow with local `_bond_vertices` list |
| `bond.py` | 204 | `self._vertices = [None, mol]` | `atom2` setter, IndexError fallback | Shadow with local `_bond_vertices` list |
| `bond.py` | 210 | `return self._vertices` | `atoms` property getter | Shadow with local `_bond_vertices` list |
| `bond.py` | 215 | `self._vertices = mol` | `atoms` property setter | Shadow with local `_bond_vertices` list |

**Risk: HIGH.** These are the core bond-to-atom linkage accessors. Every bond
operation in BKChem flows through these properties. After removing OASA
inheritance, `self._vertices` will not exist unless shadowed locally.

**Fix strategy:** Add a `_bond_vertices` list attribute to BKChem `bond.__init__`
and replace all `self._vertices` references with `self._bond_vertices`. Also
keep `_vertices` in sync with the OASA delegate if composition wraps an inner
`oasa.bond`, or remove the delegate entirely and own the vertex list.

### `_neighbors` access in special_parents.py

The OASA `graph.vertex` class stores neighbor information in a `_neighbors`
dict (mapping edge -> vertex) defined in `oasa.graph.vertex.__init__` (line 40).
BKChem `atom` inherits from `oasa.atom` which inherits from `graph.vertex`.

| File | Line | Code | Context | Fix strategy |
| --- | --- | --- | --- | --- |
| `special_parents.py` | 292 | `meta__undo_copy = vertex_common.meta__undo_copy + ('_neighbors',)` | Undo system deep-copies `_neighbors` for rollback | Delegate to `_chem_atom._neighbors` |

**Risk: MEDIUM.** The undo system uses `meta__undo_copy` to snapshot attribute
values via `copy.copy()`. After composition, `_neighbors` will live on the
inner OASA atom, not on `self`. The undo system must be taught to snapshot the
delegate's `_neighbors` instead.

Note: lines 223 and 433 in `special_parents.py` use `self.neighbors` (the
public property, no underscore). These are safe because the composition wrapper
will provide a `neighbors` property that delegates to the inner OASA object.

**Fix strategy:** Change the undo copy tuple to reference a wrapper property
or override the undo snapshot/restore methods to reach into
`self._chem_atom._neighbors` for the copy. Alternatively, keep a local
`_neighbors` cache that stays in sync with the delegate.

### `.properties_` access in BKChem

The `properties_` dict is defined on `oasa.bond.__init__` (line 59) and on
`oasa.graph.vertex` (via `graph.graph` property assignment). BKChem code
accesses it in two places.

| File | Line | Code | Context | Fix strategy |
| --- | --- | --- | --- | --- |
| `oasa_bridge.py` | 306 | `a.properties_.get('inchi_number', None)` | Reading OASA atom property during conversion | Chemistry property, keep on OASA delegate |
| `bond_cdml.py` | 23 | `self.properties_["legacy_bond_type"] = legacy` | Storing CDML bond type metadata | Chemistry property, keep on OASA delegate |

**Risk: LOW.** Both accesses are chemistry-related properties that belong on
the OASA objects. In `oasa_bridge.py`, `a` is already a pure OASA atom (not a
BKChem atom), so the access is unaffected by the composition refactor. In
`bond_cdml.py`, `self` is the BKChem bond; after composition, provide a
`properties_` property that delegates to the inner OASA bond's `properties_`
dict.

**Fix strategy:**
- `oasa_bridge.py:306` -- No change needed. The variable `a` is an OASA atom
  from the OASA molecule, not a BKChem wrapper.
- `bond_cdml.py:23` -- Add a `properties_` property on BKChem `bond` that
  delegates to the composed OASA bond, or initialize a local `properties_`
  dict on the BKChem bond.

### Properties_ classification: chemistry vs display

For reference, `properties_` keys observed in OASA code:

| Key | Used in | Category |
| --- | --- | --- |
| `inchi_number` | atom, oasa_bridge | Chemistry |
| `legacy_bond_type` | bond_cdml | Chemistry (CDML format) |
| `show_symbol` | cairo_out | Display |
| `show_hydrogens` | cairo_out | Display |
| `label` | render_geometry | Display |
| `label_anchor` | render_geometry | Display |
| `marks` | render_geometry | Display |
| `attach_atom` | render_geometry | Display |
| `attach_element` | render_geometry | Display |
| `attach_site` | render_geometry | Display |
| `line_color` | render_geometry | Display |
| `color` | render_geometry | Display |
| `wavy_style` | render_geometry | Display |
| `haworth_position` | render_geometry | Display |
| `d` | graph.py | Algorithm (BFS distance) |

Chemistry properties should stay on the OASA delegate. Display properties are
set by BKChem rendering code and must be accessible on the composed object,
either through delegation or a local overlay dict.

## OASA source definitions

For context, these are the OASA classes that own the internal attributes:

- `oasa.graph.edge` (`_vertices`): defined at
  `packages/oasa/oasa/graph/edge.py:29`
- `oasa.graph.vertex` (`_neighbors`): defined at
  `packages/oasa/oasa/graph/vertex.py:40`
- `oasa.bond` (`properties_`): defined at
  `packages/oasa/oasa/bond.py:59`

## Migration priority

1. **bond.py `_vertices`** (8 occurrences, HIGH risk) -- Must be fixed first.
   Every bond creation and atom lookup depends on this.
2. **special_parents.py `_neighbors`** (1 occurrence, MEDIUM risk) -- Undo
   system must be updated to snapshot delegate state.
3. **bond_cdml.py `properties_`** (1 occurrence, LOW risk) -- Simple
   delegation or local dict.
4. **oasa_bridge.py `properties_`** (0 changes needed) -- Already accessing
   pure OASA objects.
