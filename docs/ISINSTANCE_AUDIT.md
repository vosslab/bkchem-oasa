# isinstance audit for OASA types

Audit of every `isinstance(x, oasa.*)` check in the BKChem codebase.
These checks must be replaced before the composition refactor removes
OASA inheritance from BKChem classes.

## Summary statistics

| Metric | Count |
| --- | --- |
| Total isinstance checks | 30 |
| Unique files | 4 (excluding chem_compat.py) |
| issubclass checks | 0 |

### Counts by file

| File | Count |
| --- | --- |
| `modes.py` | 20 |
| `paper.py` | 4 |
| `context_menu.py` | 4 |
| `chem_compat.py` | 3 (helper wrappers, keep as-is) |

### Counts by OASA type

| OASA type | Count |
| --- | --- |
| `oasa.graph.vertex` | 22 |
| `oasa.graph.edge` | 1 |
| `oasa.graph.graph` | 1 |
| `oasa.bond` | 2 |
| Tuple `(oasa.graph.vertex, bond)` | 3 |

## Replacement strategies

| OASA type | Replacement |
| --- | --- |
| `oasa.graph.vertex` | `chem_compat.is_chemistry_vertex(x)` |
| `oasa.graph.edge` | `chem_compat.is_chemistry_edge(x)` |
| `oasa.graph.graph` | `chem_compat.is_chemistry_graph(x)` |
| `oasa.bond` | `chem_compat.is_chemistry_edge(x)` or `isinstance(x, bond)` |
| `(oasa.graph.vertex, bond)` | Use both helpers or a combined check |

The `chem_compat.py` helpers centralize the isinstance logic so that
only three lines need updating when OASA inheritance is fully removed.
All other call sites should migrate to these helpers.

## Full occurrence table

Priority is ordered by file risk (modes.py first, highest density).

### modes.py (19 occurrences)

| Line | isinstance call | Replacement |
| --- | --- | --- |
| 472 | `isinstance(o, oasa.graph.vertex)` | `is_chemistry_vertex(o)` |
| 475 | `isinstance(o, oasa.graph.vertex)` | `is_chemistry_vertex(o)` |
| 530 | `isinstance(self.focused, (oasa.graph.vertex, bond))` | `is_chemistry_vertex(self.focused) or isinstance(self.focused, bond)` |
| 836 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 891 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 917 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 1169 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 1206 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 1214 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 1279 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 1322 | `isinstance(self.focused, oasa.graph.vertex) or isinstance(self.focused, bond)` | `is_chemistry_vertex(self.focused) or isinstance(self.focused, bond)` |
| 1430 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 1438 | `isinstance(self.focused, oasa.graph.vertex) or isinstance(self.focused, bond)` | `is_chemistry_vertex(self.focused) or isinstance(self.focused, bond)` |
| 1459 | `isinstance(self.focused, (oasa.graph.vertex, bond))` | `is_chemistry_vertex(self.focused) or isinstance(self.focused, bond)` |
| 1461 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 1476 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 1809 | `isinstance(a, oasa.graph.vertex)` | `is_chemistry_vertex(a)` |
| 1899 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 2050 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |
| 2085 | `isinstance(self.focused, oasa.graph.vertex)` | `is_chemistry_vertex(self.focused)` |

### paper.py (4 occurrences)

| Line | isinstance call | Replacement |
| --- | --- | --- |
| 217 | `isinstance(o, oasa.graph.vertex)` | `is_chemistry_vertex(o)` |
| 222 | `isinstance(o, oasa.graph.edge)` | `is_chemistry_edge(o)` |
| 822 | `isinstance(item, oasa.graph.vertex)` | `is_chemistry_vertex(item)` |
| 965 | `isinstance(o, oasa.graph.graph)` | `is_chemistry_graph(o)` |

### context_menu.py (4 occurrences)

| Line | isinstance call | Replacement |
| --- | --- | --- |
| 221 | `isinstance(o, oasa.graph.vertex)` | `is_chemistry_vertex(o)` |
| 229 | `isinstance(o, oasa.bond)` | `is_chemistry_edge(o)` |
| 376 | `isinstance(a, oasa.graph.vertex)` | `is_chemistry_vertex(a)` |
| 383 | `isinstance(b, oasa.bond)` | `is_chemistry_edge(b)` |

### chem_compat.py (3 occurrences -- keep as-is)

These are the centralized helpers that wrap the isinstance checks.
After the refactor, only these three lines change.

| Line | isinstance call | Notes |
| --- | --- | --- |
| 72 | `isinstance(obj, oasa.graph.vertex)` | Body of `is_chemistry_vertex()` |
| 85 | `isinstance(obj, oasa.graph.edge)` | Body of `is_chemistry_edge()` |
| 98 | `isinstance(obj, oasa.graph.graph)` | Body of `is_chemistry_graph()` |

## Migration plan

1. **Phase 1** -- Add `import bkchem.chem_compat` to `modes.py`,
   `paper.py`, and `context_menu.py`.
2. **Phase 2** -- Replace each `isinstance(x, oasa.graph.vertex)` with
   `chem_compat.is_chemistry_vertex(x)` (and similarly for edge/graph).
3. **Phase 3** -- For `oasa.bond` checks in `context_menu.py`, decide
   whether to use `is_chemistry_edge()` or `isinstance(x, bond)` based
   on whether the check needs to include all edge types or only bonds.
4. **Phase 4** -- Update `chem_compat.py` helper bodies to use
   duck-typing or direct BKChem type checks once OASA inheritance is
   fully removed.
5. **Phase 5** -- Remove `import oasa` / `import oasa.graph` from files
   that no longer need them directly.
