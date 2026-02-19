# CDML Architecture: BKChem (Editor) vs OASA (Codec)

## Design Principle

**BKChem** = Document editor (pages, groups, UI, version migration)
**OASA** = Molecule codec (chemistry semantics, stable molecule I/O)

Clean boundaries prevent duplication and clarify responsibilities.

## Implementation status

- Phase 1: Complete (OASA molecule writer in place, BKChem uses it).
- Phase 2: Complete (round-trip fixtures and tests are in place).
- Phase 3: Optional (not started).
- Follow-up: Remove legacy BKChem CDML serialization path now that the default
  is flipped to the OASA writer.

---

## 1. Layer Responsibilities

### BKChem Owns: CDML-as-Document
- Pages, groups, arrows, text, marks, transforms
- Embedded CDML-in-SVG parsing
- Version migration (CDML_versions.py)
- GUI object lifecycle
- Units conversion (screen to/from real)

### OASA Owns: CDML-as-Chemistry
- Molecules: atoms, bonds, stereochem semantics
- Stable read/write rules for chemistry objects
- Canonical attribute serialization
- Chemistry validation (bond order, valence, etc.)

---

## 2. Single CDML Parsing Stack

### Stage A: Parse
**Single safe XML parser wrapper**
- Use existing `safe_xml.py` (present in both repos)
- Helper to find `<cdml>` inside SVG (namespace-aware)
- Extract from BKChem or duplicate in OASA if no-dependency preferred

### Stage B: Migrate
**Keep migrations in BKChem only**
- `CDML_versions.py` stays in BKChem
- Expose as callable: `normalize_cdml_dom(doc) -> doc`
- OASA expects "current CDML only" (post-migration)
- BKChem normalizes before calling OASA

### Stage C: Decode / Encode

**OASA provides:**
```python
read_cdml_molecule_element(element) -> molecule
write_cdml_molecule_element(molecule, *, policy) -> minidom.Element
```

**BKChem provides:**
- `read_package()` iterates objects, calls OASA for molecule core
- `get_package()` delegates molecule serialization to OASA
- Wraps OASA molecules in BKChem GUI objects

---

## 3. Preserving Attributes Without Loss

### Rule 1: Unknown Attribute Sidecar

**On read:**
```python
bond._cdml_unknown_attrs = {"custom_attr": "value", ...}
atom._cdml_unknown_attrs = {"gui_hint": "bold", ...}
```

**On write:**
```python
# Emit canonical known attrs first (from cdml_bond_io)
attrs = canonical_attrs(bond)
# Then replay unknown attrs verbatim
attrs.update(bond._cdml_unknown_attrs or {})
```

Extends existing bond pattern to atoms and molecule-level.
Store `_cdml_unknown_attrs` and `_cdml_present` directly on the object to avoid
overloading `properties_`.

### Rule 2: Track "Present on Input"

**Problem:** Cannot infer presence from `value == default`

**Solution:** Presence flags
```python
# On read:
bond._cdml_present = {"line_width", "wedge_width"}

# On write (policy-driven):
if policy == "present_only":
    emit only attrs in _cdml_present
elif policy == "always":
    emit everything (BKChem legacy)
elif policy == "minimal":
    emit only semantic essentials
```

**BKChem export:** Start with `"always"`, migrate to `"present_only"` after tests pass.

---

## 4. Version Migration: BKChem-Only

**Do NOT reimplement migrations in OASA.**

### BKChem provides:
```python
def normalize_cdml_dom(doc):
    """Migrate doc to current CDML version."""
    # Uses CDML_versions.py logic
    return migrated_doc
```

### Integration paths:

**Option A: OASA expects normalized input**
- Document clearly: "OASA accepts current CDML version only"
- BKChem always normalizes before calling OASA

**Option B: OASA accepts optional normalizer**
```python
def read_cdml(text, *, normalize_fn=None):
    doc = parse(text)
    if normalize_fn:
        doc = normalize_fn(doc)
    return decode_molecules(doc)
```

---

## 5. Integration Plan (Phased)

### Phase 1: OASA Writes Molecules Only (SAFE)

**Goal:** Delegate molecule serialization without breaking BKChem

1. Implement `oasa.cdml.write_cdml_molecule_element()`
2. BKChem `molecule.get_package()` delegates atoms/bonds to OASA
3. Keep all non-molecule objects in BKChem
4. Remove legacy writer path once OASA output is stable

**Deliverables:**
- `oasa/cdml_writer.py` module
- Unit tests for molecule round-trip
- BKChem integration behind flag

**Status:** Complete. The writer exists and BKChem always routes molecule
serialization through OASA.

### Phase 2: Round-Trip Invariants (SAFER)

**Goal:** Prove no data loss

**Test:** BKChem reads CDML -> writes CDML -> reads again

**Assert:**
- Bond types and stereochem stable
- Vertex ordering stable (wedge/hashed preservation)
- No attribute drop (known + unknown sets)
- Units consistent
- Aromatic representation stable

**Golden corpus:**
- benzene.cdml
- stereochem.cdml (wedge/hashed)
- haworth.cdml (sugars)
- cholesterol.cdml (complex biomolecule)
- legacy_weird.cdml (triggers migration)

**Status:** Complete. Fixtures and round-trip tests are in place.

### Phase 3: Expand Beyond Molecules (OPTIONAL)

**Only if needed:** Move arrows/text/marks to shared doc model

This is a larger architectural shift. Not required for chemistry maintainability.

**Status:** Optional, not started.

---

## 6. Practical Pitfalls

### Embedded CDML in SVG
- Keep "find `<cdml>`" logic in BKChem
- Write tests for SVG embedding/extraction
- OASA should NOT know about SVG wrapping

### Units
- **Decision:** OASA reads/writes CDML in real units.
- BKChem converts at boundary (screen <-> real) and never asks OASA to guess
  `paper.real_to_screen_ratio()`.
- Do NOT let OASA guess `paper.real_to_screen_ratio()`

### Aromatic Order 4
- Do NOT serialize aromatic as `order="4"` unless `render_ops` supports it
- Prefer aromatic flag or keep BKChem's current representation
- Update renderer first, then serialization

### Unknown Attribute Ordering
- If diffing XML in tests, normalize attribute dict ordering first
- Or snapshot normalized dicts instead of raw XML
- Prevents spurious test failures from reordering

---

## 7. Implementation Checklist

### Step 1: Add OASA Molecule Writer
```python
# oasa/cdml_writer.py

def write_cdml_molecule_element(mol, *, policy="present_only"):
    """
    Serialize molecule to CDML element.

    Args:
        mol: OASA molecule object
        policy: "present_only" | "always" | "minimal"

    Returns:
        xml.dom.minidom.Element
    """
    pass
```

Features:
- Known attrs via `cdml_bond_io` (deterministic ordering)
- Unknown replay via `_cdml_unknown_attrs`
- Presence tracking via `_cdml_present`
- Return a `minidom.Element` with no namespace attributes (BKChem adds `xmlns`
  on the root CDML element).

### Step 2: Wire BKChem Integration
```python
# bkchem/molecule.py

def get_package(self, doc):
    if USE_OASA_WRITER:
        # Delegate molecule core to OASA
        mol_elem = oasa.cdml.write_cdml_molecule_element(self)
        # Add BKChem GUI attributes
        self._add_gui_attrs(mol_elem)
        return mol_elem
    else:
        # Legacy path
        return self._legacy_get_package(doc)
```

Feature flag must live in BKChem config or preferences (no environment
  variables).

### Step 3: Golden Corpus Tests
```
tests/fixtures/cdml/
    benzene.cdml
    stereochem.cdml
    haworth.cdml
    cholesterol.cdml
    legacy_v0.11.cdml  # triggers migration
    embedded_cdml.svg  # CDML inside SVG wrapper
```

Test: Round-trip each file, assert invariants.

### Step 4: Gradual Rollout
1. Feature flag `USE_OASA_WRITER=False` initially
2. Run full test suite
3. Enable for new files only
4. Enable for all files
5. Remove legacy code path

---

## Benefits

### Maintainability
- One authoritative chemistry codec (OASA)
- Clear boundary: document vs chemistry
- No duplicated parsing rules

### Stability
- Unknown attributes preserved
- Presence tracking prevents spurious diffs
- Round-trip tests catch regressions

### Extensibility
- OASA can add chemistry features independently
- BKChem can add GUI features independently
- Clean API boundary enables both

---

## Next Steps

1. **Document current state:** Inventory existing CDML read/write in both repos
2. **Prototype OASA writer:** Implement `write_cdml_molecule_element()` for benzene
3. **Round-trip test:** Prove benzene -> CDML -> benzene is stable
4. **Expand corpus:** Add stereochem, haworth, cholesterol
5. **Integrate:** Wire BKChem behind feature flag
6. **Validate:** Full test suite with OASA writer enabled
7. **Ship:** Remove flag, make OASA writer canonical

---

## References

- Existing: `packages/oasa/oasa/cdml_bond_io.py` (bond attribute mapping)
- Existing: `packages/bkchem-app/bkchem/CDML_versions.py` (version migration)
- Existing: `packages/*/safe_xml.py` (safe XML parsing)
- Plan: `docs/RENDER_BACKEND_UNIFICATION.md` (analogous separation of concerns)
