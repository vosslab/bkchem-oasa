# CDML backend-to-frontend contract

Formal boundary contract between OASA (chemistry backend) and BKChem (GUI
frontend). This document defines which properties and operations belong to each
layer and how they communicate.

## Design philosophy

- OASA owns all chemistry: element identity, valency, bond order, aromaticity,
  stereochemistry, graph topology, formula, substructure search.
- BKChem owns all presentation: canvas drawing, selection/focus, marks, text
  layout, undo, templates, coordinate units (pixel conversion).
- CDML serialization must round-trip cleanly through both sides.
- The bridge layer (`oasa_bridge.py`) copies data between pure OASA objects and
  BKChem objects. It must never assume inheritance.
- If a change would apply equally to a saved CDML file processed offline
  (without the GUI running), it belongs in OASA, not BKChem.

---

## 1. Atom contract

### 1.1 OASA-owned chemistry properties

These properties live on the OASA `atom` / `chem_vertex` / `graph.vertex` and
are authoritative for chemistry operations.

| Property | Type | Defined in | Notes |
| --- | --- | --- | --- |
| `symbol` | str | `oasa.atom` | Element symbol, sets valency via periodic table |
| `symbol_number` | int | `oasa.atom` | Atomic number, set by symbol setter |
| `charge` | int | `oasa.chem_vertex` | Formal charge |
| `valency` | int | `oasa.chem_vertex` | Maximum valency |
| `occupied_valency` | int (computed) | `oasa.atom` | Sum of bond orders + charge + multiplicity |
| `free_valency` | int (computed) | `oasa.chem_vertex` | `valency - occupied_valency` |
| `multiplicity` | int | `oasa.chem_vertex` | Spin multiplicity (1=singlet) |
| `free_sites` | int | `oasa.chem_vertex` | Coordination sites beyond valency |
| `isotope` | int or None | `oasa.atom` | Mass number |
| `explicit_hydrogens` | int | `oasa.atom` | Explicitly declared H count |
| `weight` | float (computed) | `oasa.chem_vertex` | Atomic weight from periodic table |
| `has_aromatic_bonds()` | bool | `oasa.chem_vertex` | Checks `_neighbors` for aromatic bonds |
| `matches(other)` | bool | `oasa.atom` | Substructure matching |
| `get_hydrogen_count()` | int | `oasa.chem_vertex` | Implicit hydrogen count |

### 1.2 BKChem-owned display properties

These properties are defined or overridden in BKChem's `drawable_chem_vertex`,
`vertex_common`, or `atom` classes.

| Property | Type | Defined in | Notes |
| --- | --- | --- | --- |
| `show` | bool (0/1) | `bkchem.atom` | Whether to display the atom symbol |
| `show_hydrogens` | int | `bkchem.atom` | Whether to display hydrogen labels |
| `pos` | str | `drawable_chem_vertex` | Text alignment: `center-first` or `center-last` |
| `font_size` | int | `drawable_chem_vertex` | Display font size |
| `font_family` | str | inherited from `text_like` | Display font family |
| `line_color` | str | inherited from `area_colored` | Atom label color |
| `area_color` | str | inherited from `area_colored` | Background color |
| `item` | int or None | `drawable_chem_vertex` | Tk canvas item id |
| `selector` | int or None | `drawable_chem_vertex` | Selection rectangle canvas id |
| `ftext` | ftext or None | `drawable_chem_vertex` | Rich text renderer |
| `marks` | set | `vertex_common` | Set of mark objects (radical, charge, etc.) |
| `number` | int or None | `vertex_common` | Atom numbering |
| `show_number` | bool | `vertex_common` | Whether to display atom number |

### 1.3 Shared coordinates

Coordinates are shared between layers but with unit conversion in BKChem.

| Property | OASA type | BKChem override | Notes |
| --- | --- | --- | --- |
| `x` | float (abstract) | `Screen.any_to_px()` conversion | BKChem stores in pixels |
| `y` | float (abstract) | `Screen.any_to_px()` conversion | BKChem stores in pixels |
| `z` | float | Direct storage | Used for 3D stereochemistry |

### 1.4 Graph connectivity interface

These come from `oasa.graph.vertex` and are used by both layers.

| Interface | Source | Access pattern | Notes |
| --- | --- | --- | --- |
| `_neighbors` | `graph.vertex` | dict: `{edge: vertex}` | Core connectivity store |
| `neighbors` | `graph.vertex` property | `[v for (e,v) in _neighbors if not e.disconnected]` | Filtered neighbor list |
| `degree` | `graph.vertex` property | `len(neighbors)` | Vertex degree |
| `neighbor_edges` | `graph.vertex` property | Active edges from `_neighbors` | Edge list |
| `get_neighbor_edge_pairs()` | `graph.vertex` | Yields `(edge, vertex)` pairs | Iterator |
| `add_neighbor(v, e)` | `graph.vertex` | Mutates `_neighbors` | Graph mutation |
| `remove_neighbor(v)` | `graph.vertex` | Mutates `_neighbors` | Graph mutation |
| `get_edge_leading_to(a)` | `graph.vertex` | Searches `_neighbors` | Edge lookup |

---

## 2. Bond contract

### 2.1 OASA-owned chemistry properties

| Property | Type | Defined in | Notes |
| --- | --- | --- | --- |
| `order` | int | `oasa.bond` | 1-3 normal, 4 aromatic (unlocalized) |
| `_order` | int or None | `oasa.bond` | Internal storage; None when aromatic |
| `aromatic` | bool or None | `oasa.bond` | None=not set, 1=aromatic |
| `type` | str | `oasa.bond` | `n/w/h/a/b/d/o/s/q` (stereochemistry) |
| `stereochemistry` | object or None | `oasa.bond` | Stereochemistry descriptor |
| `line_color` | str or None | `oasa.bond` | Serialized color (also used in display) |
| `wavy_style` | str or None | `oasa.bond` | Wavy bond style variant |

### 2.2 BKChem-owned display properties

| Property | Type | Defined in | Notes |
| --- | --- | --- | --- |
| `item` | int or None | `bond.__init__` | Primary Tk canvas item |
| `second` | list | `bond.__init__` | Secondary canvas items (double/triple) |
| `third` | list | `bond.__init__` | Tertiary canvas items |
| `items` | list | `bond.__init__` | Additional items (hashed, dotted) |
| `_render_item_ids` | list | `bond.__init__` | Render-ops draw path output ids |
| `selector` | int or None | `bond.__init__` | Selection canvas item |
| `_selected` | int | `bond.__init__` | Selection state flag |
| `center` | bool or None | `bond.__init__` | Double bond centering (display) |
| `bond_width` | float | `bond.__init__` | Signed display width |
| `wedge_width` | float | `bond.__init__` | Wedge display width |
| `simple_double` | int | `bond.__init__` | Non-normal bond double style option |
| `auto_bond_sign` | int | `bond.__init__` | Auto sign for bond placement |
| `double_length_ratio` | float | `bond.__init__` | Second line length ratio |
| `equithick` | int | `bond.__init__` | Equal thickness flag |
| `line_width` | float | inherited from `with_line` | Display line width |
| `line_color` | str | inherited from `line_colored` | Display line color |

### 2.3 Tight coupling: `_vertices` access

BKChem `bond` accesses `oasa.bond._vertices` directly for `atom1`/`atom2`:

```python
# bond.py lines 174-215
@property
def atom1(self):
    return self._vertices[0]  # Direct access to oasa.edge._vertices

@atom1.setter
def atom1(self, mol):
    self._vertices[0] = mol   # Direct mutation

@property
def atoms(self):
    return self._vertices      # Exposes internal list
```

**Composition fix**: Shadow `_vertices` with a local list `self._bond_vertices`
initialized from `_chem_bond._vertices`. The `atom1`/`atom2`/`atoms` properties
read from the local list. Graph operations update both.

### 2.4 Bond `order` override

BKChem `bond.order` delegates to `oasa.bond.order` via descriptor protocol:

```python
@property
def order(self):
    return oasa.bond.order.__get__(self)

@order.setter
def order(self, mol):
    oasa.bond.order.__set__(self, mol)
    self.__dirty = 1
```

**Composition fix**: Redirect to `self._chem_bond.order` with dirty flag.

---

## 3. Molecule contract

### 3.1 OASA-owned chemistry operations

From `oasa.molecule` (inherits `oasa.graph.graph`). BKChem's composition layer
(`self._chem_mol`) must delegate every OASA graph or chemistry method that
callers use. The categories below describe what must be delegated, with examples
from each group. When OASA adds a new method that callers invoke on a BKChem
molecule, a matching delegation must be added to `bkchem.molecule`.

| Category | Examples | Notes |
| --- | --- | --- |
| Vertex/edge collections | `atoms`/`vertices`, `bonds`/`edges` | Aliased properties into graph lists |
| Graph mutation | `add_vertex()`, `add_edge()`, `delete_vertex()`, `disconnect()` | Add or remove vertices and edges |
| Connectivity queries | `is_connected()`, `path_exists()`, `find_path_between()` | Test or traverse graph connectivity |
| Subgraph extraction | `get_disconnected_subgraphs()`, `get_connected_components()`, `get_induced_subgraph_from_vertices()` | Decompose graph into parts |
| Cycle perception | `get_smallest_independent_cycles()`, `get_all_cycles()`, `contains_cycle()` | Ring detection algorithms |
| Temporary edge ops | `temporarily_disconnect_edge()`, `reconnect_temporarily_disconnected_edge()` | Reversible edge removal for algorithms |
| Copy operations | `copy()`, `deep_copy()` | Shallow and deep graph duplication |
| SMILES cleanup | `remove_zero_order_bonds()` | Post-parse cleanup of dot-separator bonds |
| Aromaticity | `localize_aromatic_bonds()`, `mark_aromatic_bonds()` | Kekulization and aromatic annotation |
| Distance/path utilities | `mark_vertices_with_distance_from()`, `sort_vertices_in_path()` | BFS distance and path ordering |
| Factory methods | `create_vertex()`, `create_edge()`, `create_graph()` | Must be overridden to produce BKChem types |
| Stereochemistry | `stereochemistry`, `add_stereochemistry()`, `remove_stereochemistry()` | Stereo descriptor list management |

### 3.2 BKChem-owned molecule operations

From `bkchem.molecule`:

| Operation | Notes |
| --- | --- |
| `paper` | Canvas reference |
| `draw()` / `redraw()` | Canvas rendering |
| `move(dx, dy)` | Canvas movement |
| `read_package(package)` | CDML deserialization |
| `get_package(doc)` | CDML serialization |
| `fragments` | Fragment set for grouping |
| `display_form` | Linear formula display text |
| `t_bond_first/second`, `t_atom` | Template attachment points |
| Undo support via `meta__undo_*` | Undo/redo metadata |

### 3.3 Factory method contract

BKChem `molecule` must override OASA factory methods so that graph algorithms
create BKChem-typed objects:

| Method | OASA default | BKChem override needed |
| --- | --- | --- |
| `create_vertex()` | `oasa.atom()` | `bkchem.atom()` |
| `create_edge()` | `oasa.bond()` | `bkchem.bond()` |
| `create_graph()` | `oasa.molecule()` | `bkchem.molecule()` |

---

## 4. CDML serialization contract

### 4.1 Attribute ownership in CDML

Bond CDML attributes (from `bond_cdml.py`):

| CDML attribute | Owner | Read | Write |
| --- | --- | --- | --- |
| `type` | OASA | `self.type`, `self.order` | `self.type + self.order` |
| `start`, `end` | BKChem | `self.atom1`, `self.atom2` via id manager | `self.atom1.id`, `self.atom2.id` |
| `id` | BKChem | `self.id` | `self.id` |
| `bond_width` | BKChem | `self.bond_width` | Scaled by `screen_to_real_ratio` |
| `wedge_width` | BKChem | `self.wedge_width` | Scaled by `screen_to_real_ratio` |
| `line_width` | BKChem | `self.line_width` | Direct |
| `center` | BKChem | `self.center` | `yes`/`no` |
| `color` | BKChem | `self.line_color` | Direct |
| `double_ratio` | BKChem | `self.double_length_ratio` | Direct |
| `auto_sign` | BKChem | `self.auto_bond_sign` | Direct |
| `equithick` | BKChem | `self.equithick` | Direct |
| `simple_double` | BKChem | `self.simple_double` | Direct |
| `wavy_style` | both | `self.wavy_style` | Direct |

### 4.2 Coordinate conversion

- CDML stores coordinates in centimeters with unit suffix (e.g., `"3.5cm"`)
- BKChem stores coordinates in pixels, converting via `Screen.any_to_px()`
- Round-trip: CDML cm -> `Screen.any_to_px()` -> pixels -> `Screen.px_to_text_with_unit()` -> CDML cm

### 4.3 Round-trip preservation rules

1. All CDML attributes present in the source must be preserved on save, even if
   BKChem does not use them (tracked via `properties_["_cdml_present"]`).
2. Unknown attributes are stored in `properties_` and re-emitted on save via
   `oasa.cdml_bond_io.collect_unknown_cdml_attributes()`.
3. Bond type normalization uses `oasa.bond_semantics.normalize_bond_type_char()`
   on read and stores legacy types in `properties_["legacy_bond_type"]`.
4. Bond vertex canonicalization runs on read via
   `oasa.bond_semantics.canonicalize_bond_vertices()`.

---

## 5. Bridge layer contract

### 5.1 OASA to BKChem (`oasa_bridge.py`)

`oasa_atom_to_bkchem_atom(a, paper, m)` copies:

| From OASA | To BKChem | Method |
| --- | --- | --- |
| `a.x, a.y, a.z` | `at.x, at.y, at.z` | Direct assignment |
| `a.symbol` | `at.set_name(a.symbol)` | Name interpretation |
| `a.charge` | `at.charge` | Direct |
| `a.isotope` | `at.isotope` | Direct |
| `a.valency` | `at.valency` | Direct |
| `a.properties_['inchi_number']` | `at.number` | Optional |

`oasa_bond_to_bkchem_bond(b, paper)` copies:

| From OASA | To BKChem | Method |
| --- | --- | --- |
| `b.type` | `bo.type` | Direct |
| `b.order` | `bo.order` | Direct |

### 5.2 BKChem to OASA (`oasa_bridge.py`)

`bkchem_atom_to_oasa_atom(a)` copies:

| From BKChem | To OASA | Method |
| --- | --- | --- |
| `a.symbol` | `ret.symbol` (via constructor) | Constructor arg |
| `a.get_xyz()` | `ret.x, ret.y, ret.z` | Direct |
| `a.charge` | `ret.charge` | Direct |
| `a.multiplicity` | `ret.multiplicity` | Direct |
| `a.valency` | `ret.valency` | Direct |
| `a.isotope` | `ret.isotope` | Conditional |

`bkchem_bond_to_oasa_bond(b)` copies:

| From BKChem | To OASA | Method |
| --- | --- | --- |
| `b.type` | `b2.type` | Direct via `__init__` |
| `b.order` | `b2.order` | Direct via `__init__` |

### 5.3 Composition awareness

After composition refactor, bridge functions must not assume BKChem objects
inherit from OASA. They should:

- Access chemistry properties through the BKChem object's public API (which
  delegates to `_chem_atom` / `_chem_bond` internally)
- Not access `_neighbors`, `_vertices`, or other OASA internals
- Use factory methods (`create_vertex`, `create_edge`) when building objects

---

## 6. Known contract violations

Current tight-coupling points that the composition refactor must resolve.

| File | Line(s) | Violation | Severity |
| --- | --- | --- | --- |
| `bond.py` | 177, 185, 187, 194, 202, 204, 210, 215 | Direct `_vertices` access | High |
| `bond.py` | 165, 170 | `oasa.bond.order.__get__/__set__` descriptor call | High |
| `atom.py` | 85 | `oasa.atom.symbol.__set__` descriptor call | High |
| `atom.py` | 127, 132 | `drawable_chem_vertex.charge.__get__/__set__` | Medium |
| `atom.py` | 86-87 | `occupied_valency` reads `_neighbors.keys()` | High |
| `special_parents.py` | 269 | `oasa.chem_vertex` in class bases | High |
| `atom.py` | 46 | `oasa.atom` in class bases | High |
| `bond.py` | 64 | `oasa.bond` in class bases | High |
| `queryatom.py` | 46 | `oasa.query_atom` in class bases | High |
| `molecule.py` | 49 | `oasa.molecule` in class bases | High |
| `modes.py` | 25 locations | `isinstance(x, oasa.graph.vertex)` | High |
| `paper.py` | 4 locations | `isinstance(x, oasa.graph.vertex/edge/graph)` | High |
| `context_menu.py` | 4 locations | `isinstance(x, oasa.graph.vertex/bond)` | High |

---

## 7. Inheritance chains (current)

```
oasa.graph.vertex
  -> oasa.chem_vertex
    -> oasa.atom
      -> bkchem.atom (via drawable_chem_vertex + oasa.atom)
    -> oasa.query_atom
      -> bkchem.queryatom (via drawable_chem_vertex + oasa.query_atom)

oasa.graph.edge
  -> oasa.bond
    -> bkchem.bond (via mixins + oasa.bond)

oasa.graph.graph
  -> oasa.molecule
    -> bkchem.molecule (via parents + oasa.molecule)
```

## 8. Target inheritance chains (after refactor)

```
bkchem.atom
  inherits: drawable_chem_vertex (BKChem-only parents)
  has-a: _chem_atom (oasa.atom instance)
  mixin: GraphVertexMixin (replicates oasa.graph.vertex interface)

bkchem.bond
  inherits: BKChem mixins + parents
  has-a: _chem_bond (oasa.bond instance)
  local: _bond_vertices list (shadows _vertices)

bkchem.molecule
  inherits: BKChem parents
  has-a: _chem_mol (oasa.molecule instance)
  delegates: graph algorithms to _chem_mol
```
