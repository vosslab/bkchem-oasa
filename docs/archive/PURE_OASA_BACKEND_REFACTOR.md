# Pure OASA backend refactor

## Phase summary and status

<!-- Agents: update the Status column as work progresses. -->
<!-- Use: NOT STARTED / IN PROGRESS / COMPLETED -->
<!-- Update subgoal checkboxes as each is finished: [ ] -> [x] -->

| Phase | Status | Scope |
|-------|--------|-------|
| A | COMPLETED | Plumbing refactor (registry, generic load/save, coordinate boundary, deprecations) |
| B | COMPLETED | Options audit and legacy retention decisions |
| C | COMPLETED | Rendering migration (render-ops MVP, export swap, Tk pipeline removal) |

### Subgoal checklist

**Phase A: Plumbing refactor**
- [x] A1: `get_registry_snapshot()` is the source of truth for capabilities and extensions
- [x] A2: Generic load/save routing through `oasa_bridge` + scope handler; `format_loader.py` + GUI manifest created; format plugins removed (rendering plugin infrastructure removed in Phase C)
- [x] A3: Coordinate canonicalization boundary enforced (no per-codec Y-flips)
- [x] A4: CML v1/v2 export removed (import retained); CDXML plugin deleted; POVRay deleted; GTML import retained

**Phase B: Options audit and retention decisions**
- [x] B1: Inventory every GUI option; classify as keep / move-to-default / codec-only / retire
- [x] B2: GUI manifest schema validated (strict failure on unknown keys)
- [x] B3: GTML retention level decided and documented
- [x] B4: CDML depiction audit (identify gaps before Phase C rendering swap)
- [x] B5: CDML v2 decision: additive changes stay on current CDML; breaking changes trigger v2

**Phase C: Rendering migration**
- [x] C1: Render-ops MVP for full molecules (bonds, labels, charges, stereo)
- [x] C2: Export pipeline (SVG/PDF/PNG/PS) uses OASA renderers
- [x] C3: CD-SVG codec ported to OASA with safe SVG subset rules
- [x] C4: Tk canvas export code removed (`tk2cairo.py`, `cairo_lowlevel.py`, all `*_cairo.py` plugins)

---

## Design philosophy

**BKChem is format-blind. OASA is GUI-blind. CDML is the contract.**

BKChem only speaks CDML. It never parses, serializes, or even knows about
external file formats (molfile, CML, SMILES, etc.). When a user opens a file,
BKChem hands OASA a file path and receives CDML back. When a user saves to a
format, BKChem hands OASA its CDML and OASA writes the target format. An
OASA-only user (CLI, scripts, other frontends) has access to every capability
that BKChem offers, without importing BKChem or Tkinter.

### Data flow

```
Import:  BKChem gives file path  -->  OASA reads format  -->  OASA emits CDML  -->  BKChem receives CDML
Export:  BKChem gives CDML        -->  OASA converts CDML -->  OASA writes format
Render:  BKChem gives CDML        -->  OASA renders CDML  -->  OASA writes PDF/PNG/SVG/PS
```

### CDML bridge API contract

The data flow above says "OASA emits CDML" and "BKChem gives CDML," but today
the OASA codec registry is molecule-centric: codecs return OASA `molecule`
objects, not CDML strings. The bridge (`oasa_bridge.py`) converts between
BKChem molecule objects and OASA molecule objects. CDML is not currently an
explicit wire format between the two layers.

To realize the target architecture, the bridge must provide two conversion
boundaries:

```
Import:  file path  -->  codec.read_file()  -->  oasa.molecule
                         oasa.molecule       -->  bridge.oasa_mol_to_cdml()  -->  CDML string
                         CDML string         -->  BKChem loads into canvas

Export:  BKChem canvas  -->  bridge.canvas_to_cdml()  -->  CDML string
                             CDML string               -->  bridge.cdml_to_oasa_mol()  -->  oasa.molecule
                             oasa.molecule              -->  codec.write_file()
```

The key functions that must exist (in `oasa_bridge.py` or a new module):

- **`oasa_mol_to_cdml(mol) -> str`**: Serialize an OASA molecule to a CDML
  string in canonical coordinates. Uses `cdml_writer`.
- **`cdml_to_oasa_mol(cdml_str) -> molecule`**: Parse a CDML string into an
  OASA molecule. Uses `cdml.text_to_mol`.
- **`canvas_to_cdml(paper) -> str`**: Extract CDML from the BKChem canvas,
  canonicalizing coordinates if the transitional path is active.
- **`cdml_to_canvas(paper, cdml_str)`**: Load a CDML string into the BKChem
  canvas, de-canonicalizing if the transitional path is active.

Today `oasa_bridge.py` already has `oasa_mol_to_bkchem_mol()` and
`bkchem_mol_to_oasa_mol()`. The new functions wrap these with CDML
serialization/parsing at the boundary so that the format loader never touches
OASA molecule objects directly.

This is implementation work within Phase A2. The format loader calls the bridge;
the bridge handles the molecule <-> CDML conversion internally.

### Coordinate systems

CDML uses canonical math coordinates (+Y up). OASA works entirely in this
canonical space. BKChem's Tk canvas uses screen coordinates (+Y down).

**Preferred boundary:** The transform between canonical CDML and canvas
coordinates happens at the CDML-to-canvas boundary inside BKChem's renderer,
not inside any codec, not inside the bridge, and not per-format.

**Transitional exception:** During migration, BKChem may still store
coordinates in canvas space internally. In that case, the bridge canonicalizes
CDML before passing it to OASA and de-canonicalizes on the way back. This is
temporary architectural debt, not a co-equal design. The goal is to eliminate
this bridge transform and store canonical coordinates throughout.

Regardless of which path is active: all CDML exchanged with OASA is in
canonical coordinates (+Y up). Individual codecs (molfile, CML, etc.) never
apply Y-axis inversion; they work in canonical space.

### WYSIWYG contract: CDML must carry depiction semantics

Moving export rendering from the Tk canvas pipeline to OASA render-ops creates
a risk: the OASA renderer may produce visually different output than what the
user sees in the GUI. This is the "WYSIWYG gap." The gap is not about file
formats; it is about depiction choices (label placement, bond spacing, stereo
conventions) diverging between two independent rendering engines.

CDML must carry enough depiction intent that rendering is deterministic across
backends. Otherwise the export will drift from the GUI even when the chemistry
is identical.

CDML already stores two layers:

- **Structure layer:** atoms, bonds, orders, stereo flags, charges.
- **Depiction layer:** 2D coordinates, `<standard>` block (bond length, stroke
  width, font family/size, double-ratio, wedge-width), per-bond style
  attributes (`type`, `line_width`, `wedge_width`), per-atom label positioning.

When the depiction layer is present, it is authoritative. The renderer follows
CDML, not its own heuristics. Specifically:

- **Global drawing style** (bond length, stroke width, font, double-bond
  spacing) is stored in the `<standard>` block and applies to all molecules
  unless overridden per-object.
- **Stereo depiction** (wedge type, hatch spacing, rounded vs sharp wedge) is
  stored per-bond as `type` and `wedge_width`.
- **Manual tweaks** (label offsets, custom colors, z-order) are stored
  per-object. The renderer applies the stored result, not an algorithm.

What may still be missing and should be audited in Phase B:

- Aromatic depiction policy (circle vs alternating bonds vs kekulized). If this
  is a renderer default rather than a CDML attribute, the Tk and OASA renderers
  can disagree.
- Label direction rules ("HO" vs "OH"). If stored, the renderer follows it. If
  inferred, it can differ.
- Any other depiction choice where BKChem and OASA have independent defaults.

**Phase A does not touch this.** The GUI renders to the Tk canvas from molecule
objects. Phase A only changes how formats are routed.

**Phase C is where this matters.** We are replacing the export renderer. The
WYSIWYG gap is managed through golden geometry tests that compare Tk-derived
and OASA-derived output features for the same CDML input. If they differ, it is
either a renderer bug or CDML is missing depiction fields.

### CDML versioning: when to introduce CDML v2

If the Phase B depiction audit reveals that closing the WYSIWYG gap requires
significant schema changes (new required attributes, changed semantics of
existing attributes, or structural reorganization), those changes should go into
a **CDML v2** rather than being patched into the current format. The threshold:

- **Stay on current CDML** if the changes are purely additive (new optional
  attributes that old readers can safely ignore).
- **Introduce CDML v2** if any of the following apply:
  - Existing attributes change meaning or default interpretation.
  - New attributes are required for correct rendering (old readers would
    produce wrong output without them).
  - The depiction profile or coordinate convention changes in a way that is
    not backward-compatible.

If CDML v2 is introduced:
- The `<cdml version="...">` attribute already exists and distinguishes
  versions.
- OASA reads both v1 and v2. BKChem saves only v2. Old BKChem installations
  can still open v1 files.
- The migration path is: open v1 file -> save -> file is now v2. No batch
  converter needed.
- Document the v2 schema changes in
  [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md).

The Phase B depiction audit produces the evidence for this decision. Do not
pre-commit to v2; let the audit determine whether the changes are additive or
breaking.

### Rules

- **BKChem is format-blind.** No format parsing or serialization in BKChem.
  BKChem only reads and writes CDML. OASA codecs own all external format I/O.
- **OASA is GUI-blind.** No Tkinter, no canvas coordinates, no display DPI, no
  selection dialogs. OASA works in canonical CDML coordinates.
- **CDML is the contract.** All data exchange between BKChem and OASA goes
  through CDML (canonical coordinates). Coordinate transforms between canonical
  and canvas space happen at the rendering boundary in BKChem, not in codecs.
- **No rendering in BKChem.** OASA renderers produce PDF, PNG, SVG, PostScript,
  ODF from CDML/molecule data. The Tk canvas is for interactive editing only.
- **GUI dialogs collect parameters only.** Molecule selection, file path, and
  preferences are collected by the GUI and passed to OASA. Dialogs do not
  process data.
- **The `plugins/` directory goes away.** The OASA codec registry is the
  backend source of truth. BKChem reads capabilities from the registry at
  runtime (or from a generated snapshot). A single GUI YAML manifest in BKChem
  declares display names, menu placement, scope, and dialog options. A generic
  loader replaces all per-format plugin files.

### Current state vs target

Today BKChem violates this architecture in several ways:

- BKChem plugins open files, call `oasa_bridge` functions, and apply
  format-specific transforms (e.g. Y-axis inversion in `molfile.py`).
  BKChem should hand OASA a file path and get CDML back. The Y-axis
  inversion is removed by canonicalizing CDML at the GUI-to-model boundary,
  not by moving inversion into any codec.
- BKChem's in-memory molecule objects use canvas coordinates (+Y down), not
  canonical CDML coordinates. The bridge converts between BKChem objects and
  OASA objects, but coordinates are in canvas space. This must be fixed so
  CDML exchanged with OASA is always in canonical space.
- Rendering plugins walk raw Tk canvas items through `tk2cairo.py`, bypassing
  molecule semantics entirely. BKChem should hand OASA its CDML and get a
  rendered file back.

What already works toward the target:

- The codec registry
  ([packages/oasa/oasa/codec_registry.py](packages/oasa/oasa/codec_registry.py))
  centralizes format I/O for SMILES, InChI, molfile, CDML, CML, CML2, and
  CDXML.
- CML/CML2/CDXML plugins are thin bridge wrappers that can be deleted.
- OASA has rendering backends (`svg_out.py`, `cairo_out.py`) and an
  intermediate render-ops layer (`render_ops.py`) with `LineOp`, `PolygonOp`,
  `CircleOp`, `PathOp`, and `TextOp`.
- The
  [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md)
  plan defines the ops spec, geometry producers, and thin painters.

---

## Inventory: all I/O formats before and after

Every format supported by BKChem or OASA today, where the code lives now, and
where it must live after this refactor. Nothing in the "After" column should
reference BKChem plugin files.

### Chemical structure formats

| Format | Read | Write | Before: code location | After: code location | Phase | Notes |
|--------|------|-------|----------------------|---------------------|-------|-------|
| SMILES | Yes | Yes | OASA `smiles.py` + BKChem `smiles.py` plugin (export-only) | OASA codec only | A | BKChem plugin has GUI selection; move to generic scope handler |
| InChI | Yes | Yes | OASA `inchi.py` + BKChem `inchi.py` plugin (export-only) | OASA codec only | A | External program path from preferences passed as kwarg |
| Molfile | Yes | Yes | OASA `molfile.py` + BKChem `molfile.py` plugin | OASA codec only | A | `invert_coords()` removed; canonical CDML fixes this |
| CDML | Yes | Yes | OASA `cdml.py`/`cdml_writer.py` + BKChem `main.py` save/load | OASA codec + BKChem save/load (CDML is the contract) | N/A | Already correct architecture; BKChem reads/writes CDML natively |
| CML v1 | **Import only** | Drop export | OASA `codecs/cml.py` + BKChem `CML.py` plugin | OASA codec (read-only) | A | 20+ year old format; keep import for legacy file recovery, drop export |
| CML v2 | **Import only** | Drop export | OASA `codecs/cml2.py` + BKChem `CML2.py` plugin | OASA codec (read-only) | A | Same as CML v1; keep import, drop export |
| CDXML | Yes | Yes | OASA `codecs/cdxml.py` + BKChem `CDXML.py` plugin | OASA codec only | A | Plugin is pure bridge wrapper, delete |
| GTML | **Import only** | No | BKChem `gtml.py` plugin only | OASA codec (read-only) or retire | A/B | Legacy format; keep import for old file recovery, no export needed |
| CD-SVG | Yes | Yes | BKChem `export.py` + `paper.py` (SVG with embedded CDML) | OASA codec (CDML-in-SVG container) | C | Port to OASA; BKChem is format-agnostic. See security notes below |
| OpenBabel formats | Yes | Yes | OASA `pybel_bridge.py` (optional) | OASA (optional, unchanged) | N/A | SDF, MOL2, PDB, XYZ, CIF, etc. via pip_extras.txt |

### Rendering/graphics output

| Format | Read | Write | Before: code location | After: code location | Phase | Notes |
|--------|------|-------|----------------------|---------------------|-------|-------|
| PDF | No | Yes | BKChem `pdf_cairo.py` plugin (walks Tk canvas) | OASA renderer via `cairo_out.py` | C | OASA already has `cairo_out` with PDF support |
| PNG | No | Yes | BKChem `png_cairo.py` plugin (walks Tk canvas) | OASA renderer via `cairo_out.py` | C | OASA already has `cairo_out` with PNG support |
| SVG (clean) | No | Yes | BKChem `svg_cairo.py` plugin (walks Tk canvas) | OASA renderer via `svg_out.py` or `cairo_out.py` | C | OASA already has `svg_out.py` (pure Python) |
| PostScript | No | Yes | BKChem `ps_cairo.py` + `ps_builtin.py` plugins | OASA renderer via `cairo_out.py` | C | Two BKChem plugins (Cairo + Tk builtin) collapse to one OASA renderer |
| ODF Draw | No | Yes | BKChem `odf.py` plugin (walks `paper.stack`) | Deferred (renderer removed in Phase C; re-add only via OASA codec) | Post-C | ODF export was dropped with Tk plugin removal; track reintroduction as explicit OASA work item |
| POVRay | No | Yes | BKChem `povray.py` plugin (walks Tk canvas) | **Retire** (delete) | A | Unfinished, 3D renderer for a 2D program; not worth porting |

### Plugin infrastructure (not formats)

| File | Purpose | Before | After | Phase |
|------|---------|--------|-------|-------|
| `plugin.py` | Base importer/exporter classes, exception types | BKChem `plugins/plugin.py` | Deleted; generic loader handles this | A |
| `__init__.py` | Dynamic plugin discovery from `_names` list | BKChem `plugins/__init__.py` | Deleted; registry-driven loader replaces | A |
| `cairo_lowlevel.py` | Base class for Cairo rendering plugins | BKChem `plugins/cairo_lowlevel.py` | Deleted; OASA renderers replace | C |
| `tk2cairo.py` | Tk canvas item to Cairo converter | BKChem `plugins/tk2cairo.py` | Deleted; no Tk canvas walking in export | C |

### CD-SVG: OASA codec with security mitigations

CD-SVG is "CDML wrapped in SVG" - a single file that is both previewable as a
graphic and editable as a chemistry document. BKChem is format-agnostic, so
CD-SVG belongs in OASA as a codec. This lets CLI tools and other frontends
round-trip CD-SVG without importing BKChem.

The OASA CD-SVG codec combines two existing OASA capabilities: SVG rendering
(via `svg_out.py`) and CDML serialization (via `cdml_writer.py`). On write,
OASA renders molecules to SVG and embeds the CDML payload in a namespaced
metadata block. On read, OASA extracts the CDML block and ignores the SVG
graphics.

**SVG security:** SVG is active XML that can contain `<script>`, `onload`
handlers, `<foreignObject>`, and external URLs.

Mitigations:
- **On export:** Emit clean SVG only. No `<script>`, no event handlers, no
  `<foreignObject>`, no external URLs. CDML lives in a namespaced metadata
  block with no executable surface.
- **On import:** Treat as untrusted. Extract only the CDML namespace block
  and ignore all other SVG content.

---

## Target architecture

### OASA codec registry as backend source of truth

The OASA codec registry (`codec_registry.py`) already knows every codec's name,
extensions, and read/write capabilities. A separate YAML file duplicating that
information would drift. Instead, OASA exposes an introspection method:

```python
# packages/oasa/oasa/codec_registry.py

def get_registry_snapshot():
    """Return a dict of all registered codecs and their capabilities.

    Each entry contains: name, extensions, reads_text, writes_text,
    reads_files, writes_files. Used by BKChem's format loader to discover
    available codecs at runtime without hardcoding names.
    """
    _ensure_defaults_registered()
    snapshot = {}
    for name, codec in sorted(_CODECS.items()):
        snapshot[name] = {
            "extensions": list(codec.extensions),
            "reads_text": codec.reads_text,
            "writes_text": codec.writes_text,
            "reads_files": codec.reads_files,
            "writes_files": codec.writes_files,
        }
    return snapshot
```

BKChem reads OASA capabilities from the registry (or a generated snapshot) at
runtime. No hand-maintained OASA YAML file exists. A CLI command
(`python -m oasa.codec_registry --snapshot`) can emit a JSON/YAML dump for
debugging or documentation, but it is never read at runtime.

### BKChem GUI manifest (menus, dialogs, preferences)

```yaml
# packages/bkchem-app/bkchem/format_menus.yaml
# GUI-specific metadata. References OASA codec names.

formats:

  cml:
    display_name: CML
    menu_capabilities: [import]
    scope: paper
    gui_options: []

  cml2:
    display_name: CML2
    menu_capabilities: [import]
    scope: paper
    gui_options: []

  cdxml:
    display_name: CDXML
    scope: paper
    gui_options: []

  molfile:
    display_name: Molfile
    scope: selected_molecule
    gui_options: []

  smiles:
    display_name: SMILES
    menu_capabilities: [export]
    scope: selected_molecule
    gui_options: []

  inchi:
    display_name: InChI
    menu_capabilities: [export]
    scope: selected_molecule
    gui_options:
      - key: program_path
        source: preference
        preference_key: inchi_program_path
        required: true

renderers:

  pdf:
    display_name: PDF
    scope: paper
    gui_options:
      - key: crop
        source: paper_property
        property_key: crop_svg

  png:
    display_name: PNG
    scope: paper
    gui_options:
      - key: crop
        source: paper_property
        property_key: crop_svg
      - key: scaling
        source: dialog
        dialog_type: scaling_slider

  svg:
    display_name: SVG
    scope: paper
    gui_options:
      - key: crop
        source: paper_property
        property_key: crop_svg

  postscript:
    display_name: PostScript
    scope: paper
    gui_options:
      - key: crop
        source: paper_property
        property_key: crop_svg

  odf:
    display_name: ODF Draw
    scope: paper
    gui_options: []
```

The OASA codec registry is the source of truth for what codecs exist, what
extensions they handle, and what they can read or write. The BKChem GUI manifest
adds display names, menu placement, scope (paper vs selected molecule), and GUI
option sources (preferences, paper properties, dialogs). At startup, the format
loader calls `get_registry_snapshot()` to discover OASA capabilities, then joins
with the GUI manifest by codec name. A CLI tool queries only the registry.

### Scope types

The `scope` field replaces the duplicated molecule-selection boilerplate that is
currently copy-pasted across molfile, smiles, and inchi plugins:

- **`paper`**: Export all molecules on the paper. The bridge calls
  `paper.molecules` and merges them. No selection dialog needed.
- **`selected_molecule`**: Require exactly one molecule selected. The bridge
  calls `paper.selected_to_unique_top_levels()`, validates the count, and
  passes the single molecule. On error, shows a standard dialog.

BKChem implements one generic scope handler for each type. No per-format Python
code needed.

### GUI option sources

The `gui_options` list declares parameters the GUI must collect before calling
OASA. Each option has a `source` type:

- **`preference`**: Read from BKChem preferences (`Store.pm.get_preference()`).
  If missing and `required: true`, show an error dialog.
- **`paper_property`**: Read from `paper.get_paper_property()`.
- **`dialog`**: Show a specific dialog type (scaling slider, color picker, etc.)
  and pass the result as a kwarg.

### Generic loader

One Python module in BKChem replaces the entire `plugins/` directory:

```python
# packages/bkchem-app/bkchem/format_loader.py

def load_backend_capabilities():
    """Query OASA codec registry. Returns codec capabilities dict."""

def load_gui_manifest():
    """Read format_menus.yaml from BKChem. Returns GUI metadata dict."""

def build_importer(codec_name, scope, gui_options):
    """Return a callable: (paper, filename, **gui_kwargs) -> molecules."""

def build_exporter(codec_name, scope, gui_options):
    """Return a callable: (paper, filename, **gui_kwargs) -> None."""
```

The `main.py` menu builder queries the registry for backend capabilities, reads
the GUI manifest for menu metadata, joins them by codec name, creates menu
items, and wires each to a generic import/export handler that:

1. Resolves `gui_options` from BKChem preferences/properties/dialogs.
2. Handles `scope` validation (molecule selection or full paper).
3. On import: passes file path to OASA, receives CDML back, loads into canvas.
4. On export: extracts CDML from canvas (canonical coordinates), passes CDML
   and target codec name to OASA, OASA writes the file.

---

## Test fixtures and continuous test matrix

### Canonical fixture set

All round-trip, smoke, and golden-output tests reference this fixture set.
Fixtures live in `tests/fixtures/codec_roundtrip/` (to be created). Each
fixture molecule is chosen to exercise a specific feature that could break
during the refactor.

| Fixture | Format(s) | Exercises | Notes |
|---------|-----------|-----------|-------|
| benzene | `.mol`, `.cdml` | Aromatic bonds, ring detection | Existing `aromatic.cdml` covers CDML side |
| lactic acid | `.mol`, `.cdml` | Stereo wedge/hash bonds | Existing `stereo.cdml` covers CDML side |
| glycine zwitterion | `.mol`, `.cdml` | Charges (+/-) on atoms | New fixture needed |
| cyclohexane | `.mol`, `.cdml` | Double bond placement in ring | |
| caffeine | `.mol`, `.cdml` | Fused rings, heteroatoms, implicit H | |
| one Haworth sugar | `.cdml` | Haworth-specific bond types (q) | Use existing sugar fixture if available |
| legacy CML sample | `.cml` | CML v1 import path | |
| legacy CDXML sample | `.cdxml` | CDXML import/export path | |

Exact fixture files are chosen by the implementer. The table above is a minimum
coverage target, not an exhaustive list.

### Continuous test matrix

Tests run during refactoring, not after. The done-check gates in each phase
reference these categories.

**A. Unit tests (fast, mandatory in CI)**

1. **Registry snapshot invariants.** `get_registry_snapshot()` returns correct
   `reads_files` / `writes_files` for every codec. CML v1/v2 have
   `writes_files == False`.
2. **GUI manifest schema.** Strict validation: unknown keys fail. Every codec
   name in `format_menus.yaml` exists in the registry snapshot.
3. **Scope handler.** `selected_molecule` rejects 0 and >1 selections, accepts
   exactly 1.
4. **CD-SVG security.** Exported CD-SVG contains no `<script>`, no event
   handler attributes, no `<foreignObject>`, no external URLs. Import extracts
   only the CDML namespace block.

**B. Round-trip conversion tests (catch semantic regressions)**

1. **Molfile round-trip geometry.** `fixture.mol` -> OASA -> CDML -> OASA ->
   `output.mol`. Compare atom count, bond count, bond orders, 2D coordinates
   within tolerance. Assert no global Y-inversion occurred.
2. **Stereo preservation.** Lactic acid molfile round-trip and CDML idempotence
   must preserve wedge (`w1`) and hatch (`h1`) bond types, not just counts and
   coordinates. Assert bond type strings survive the round-trip.
3. **Aromatic representation stability.** Benzene molfile import then export
   must not silently change aromatic bond typing (e.g. kekulized to aromatic
   or vice versa). Assert bond orders and aromatic flags match input.
4. **CDML idempotence.** Load CDML fixture -> extract CDML -> re-import. Assert
   molecule graph, canonical coordinates, and bond types unchanged.
5. **Legacy import-only.** CML v1 -> CDML -> reload. CML v2 -> CDML -> reload.
   GTML -> CDML -> reload (document any data-loss exceptions for reactions,
   arrows, etc.).

**C. Smoke tests (whole wiring after plugin deletion)**

1. **Menu visibility.** "Save as..." does not list CML v1, CML v2, POVRay.
   "Open..." still accepts `.cml`, `.cdxml`, and legacy formats.
2. **End-to-end import/export.** For each fixture molecule: import molfile ->
   export molfile; import CDXML -> export CDXML; export SMILES/InChI for
   selected molecule. Export SVG/PDF/PNG once Phase C is active.

**D. Golden output and WYSIWYG tests for rendering (Phase C only)**

Do geometry diffs, not pixel diffs.

1. **Geometry invariants (fast unit tests).** For a known wedge bond: assert
   the generated polygon has correct orientation (wide end at substituent),
   correct signed area direction, and does not self-intersect. For hatch:
   assert hatch lines are on the correct side and segment count matches
   expectation at a given bond length.

2. **Golden SVG geometry.** Render fixture molecules to SVG via render-ops
   path. Assert stable op counts by type and stable key coordinates (bond
   midpoints, text anchor positions). Parse SVG XML: required elements exist,
   no banned elements.

3. **WYSIWYG comparison.** For the same CDML input, compare derived geometry
   features between Tk-derived output and OASA render-ops output: number of
   polygons for wedge bonds, bounding boxes of wedge polygons, angles of hatch
   strokes relative to bond vector, attachment point consistency. Differences
   indicate either a renderer bug or missing depiction fields in CDML.

**E. Gating rule**

Do not delete old code (plugins, Tk render path) until the corresponding smoke
suite passes in CI. Tests are the continuous "no pause" mechanism.

---

## Phases

Tests run continuously during each phase. The "done checks" below are gates:
what must pass before you delete old code, not what must pass before you start
the next phase.

---

### Phase A: Plumbing refactor

**Goal:** All format I/O routes through the OASA codec registry and a generic
loader. The `plugins/` directory is deleted. Deprecated export paths are gone.
Coordinate canonicalization is enforced at a single boundary.

#### A1: Registry as source of truth

Add `get_registry_snapshot()` to the codec registry so BKChem can discover
capabilities at runtime. CML and CML2 codecs become read-only: retain
`text_to_mol` / `file_to_mol` but set `mol_to_text` / `mol_to_file` to `None`
so `writes_files == False`. Any accidental export attempt raises immediately.

**Files changed:**
- `packages/oasa/oasa/codec_registry.py`: Add `get_registry_snapshot()`.
- `packages/oasa/oasa/codecs/cml.py`: Remove or disable export functions.
- `packages/oasa/oasa/codecs/cml2.py`: Same.

#### A2: Generic load/save and plugin directory removal

Replace the entire `plugins/` directory with a registry-driven loader. BKChem
reads OASA capabilities from the registry and GUI metadata from
`format_menus.yaml`. A single `format_loader.py` builds importer/exporter
callables for each registered codec.

The generic scope handler replaces the duplicated `on_begin()` /
`selected_to_unique_top_levels()` boilerplate in molfile, smiles, and inchi
plugins. InChI `program_path` resolves from preferences via `gui_options`.

**Files created:**
- `packages/bkchem-app/bkchem/format_loader.py`: Queries registry, reads GUI
  manifest, builds menu items with scope validation and gui_option resolution.
- `packages/bkchem-app/bkchem/format_menus.yaml`: GUI manifest declaring display
  names, `menu_capabilities`, scope, and `gui_options`.

**Files changed:**
- `packages/bkchem-app/bkchem/main.py`: Replace `init_plugins_menu()`,
  `plugin_import()`, `plugin_export()` with calls to the format loader.

**Files deleted (format plugins only):**
- `packages/bkchem-app/bkchem/plugins/CML.py`
- `packages/bkchem-app/bkchem/plugins/CML2.py`
- `packages/bkchem-app/bkchem/plugins/CDXML.py`
- `packages/bkchem-app/bkchem/plugins/molfile.py`
- `packages/bkchem-app/bkchem/plugins/smiles.py`
- `packages/bkchem-app/bkchem/plugins/inchi.py`
- `packages/bkchem-app/bkchem/plugins/povray.py`

**Do NOT delete until Phase B decides retention:**
- `packages/bkchem-app/bkchem/plugins/gtml.py` (GTML import retained until
  Phase B audit confirms coverage; see B3)

**Do NOT delete until Phase C gate passes:**
- `plugin.py`, `__init__.py` (rendering plugins import from `plugin.py`)
- `tk2cairo.py`, `cairo_lowlevel.py`, `pdf_cairo.py`, `png_cairo.py`,
  `svg_cairo.py`, `ps_cairo.py`, `ps_builtin.py`, `odf.py`

These rendering plugins (and the plugin infrastructure they depend on) are still
the active export path until Phase C replaces them with OASA renderers.

#### A3: Coordinate canonicalization boundary

Remove `invert_coords()` from the molfile plugin. All CDML exchanged with OASA
uses canonical coordinates (+Y up). No OASA codec ever applies Y-axis
inversion.

**Preferred (clean break):** BKChem stores canonical coordinates internally.
The Tk canvas renderer applies the Y-flip at draw time.

**Transitional (if preferred is too disruptive now):** The bridge canonicalizes
CDML before passing it to OASA and de-canonicalizes on the way back. This is
temporary architectural debt, not a co-equal design.

Either way, `invert_coords()` is deleted and no per-format coordinate logic
exists anywhere.

#### A4: Deprecations

- Delete `CML.py`, `CML2.py`, `CDXML.py`, `povray.py` plugins.
- CML v1/v2: import retained, export dropped.
- CDXML: full import/export via codec registry.
- GTML: `gtml.py` stays until Phase B audit (B3) decides retention level.
  Do not delete in Phase A.
- POVRay: retired entirely.

**Extension overlap:** CML and CML2 both use `.cml` / `.xml` file extensions.
Since both are import-only (export is dropped), the extension overlap is
harmless: the Open dialog accepts `.cml` files, and the importer inspects file
content to determine whether the document is CML v1 or v2 (content sniffing),
not the file extension. No menu disambiguation is needed.

#### Phase A done checks

- [x] `get_registry_snapshot()` returns entries for all codecs with correct
  `reads_files`, `writes_files`, `extensions`.
- [x] CML/CML2 codecs have `writes_files == False` and `writes_text == False`.
- [x] Format loader reads registry + GUI manifest and produces correct menu
  items. Generic importer/exporter call bridge functions with correct codec
  names.
- [x] Scope `selected_molecule` rejects zero/multiple selections.
- [x] `validate_selected_molecule()` returns molecule when exactly one selected.
- [x] CDML exchanged with OASA uses canonical coordinates (+Y up).
- [x] Molfile round-trip (fixture molecules) preserves atom count, bond count,
  bond orders, and 2D coordinates within tolerance. No global Y-inversion.
- [x] Stereo round-trip: lactic acid wedge (`w1`) and hatch (`h1`) bond types
  survive molfile round-trip and CDML idempotence.
- [x] Aromatic round-trip: benzene import then export does not change aromatic
  bond typing (kekulized vs aromatic flags match input).
- [x] CDML idempotence: load fixture CDML -> extract -> re-import -> graph,
  coordinates, and bond types unchanged.
- [x] Legacy import: CML v1 and CML v2 fixtures import to CDML without error.
- [x] `invert_coords` does not exist anywhere in the codebase.
- [x] "Save as..." does not offer CML v1, CML v2, or POVRay.
- [x] "Open..." still accepts `.cml`, `.cdxml`, and legacy formats.
- [x] End-to-end smoke: import/export molfile, import/export CDXML, export
  SMILES/InChI for each fixture molecule.
- [x] `python3 -m pytest tests/ -v` passes.
- [x] `python3 -m pytest tests/test_pyflakes_code_lint.py -v` passes.

---

### Phase B: Options audit and legacy retention decisions

**Goal:** Every per-format GUI option is classified. The GUI manifest schema is
validated. GTML retention level is decided and documented.

Phase B deliverables and decisions are documented in
[docs/archive/PHASE_B_AUDIT.md](docs/archive/PHASE_B_AUDIT.md).

#### B1: Option inventory and classification

Classify every existing per-format option into four buckets:

1. **Keep in BKChem GUI.** Human choice, cross-format, or widely expected.
   Examples: output image size, include background, pretty-print XML, embed
   fonts, include title block.

2. **Move to codec defaults.** Not a user decision. Examples: coordinate
   canonicalization, unit normalization, deterministic attribute ordering,
   whitespace conventions. These become fixed codec behavior.

3. **Expose only when the codec supports it.** Format-specific options that map
   to a real codec capability. Examples: aromatic kekulization, stereochemistry
   wedge policy, 2D vs 3D coordinates. These are accepted as kwargs by the OASA
   codec and appear in the GUI manifest as `gui_options` only for codecs that
   support them.

4. **Retire.** Options that exist only because of the old bridge, broken
   pathways, or canvas-to-format hacks. Examples: per-format Y-axis flip,
   canvas scaling knobs, "export via Tk canvas" toggles.

**Deliverables:**
- Inventory table: option name, current location, formats affected, default,
  classification, rationale.
- Decision record: one-line justification per option.
- Deprecation plan: retired options get a warning in one release, removed in
  the next.

#### B2: GUI manifest schema validation

Add strict schema validation for `format_menus.yaml`. Unknown keys cause test
failure. Every codec name in the manifest must have a matching entry in
`get_registry_snapshot()`.

#### B3: GTML retention decision

GTML is BKChem's legacy native format (molecules, atoms, bonds, reactions,
arrows, plus signs). CDML is the modern equivalent.

- Inventory any features GTML supports that CDML does not.
- If CDML covers everything: GTML is import-only for legacy file recovery.
- If CDML is missing features: file items in
  [docs/TODO_CODE.md](docs/TODO_CODE.md) for CDML/OASA extensions.

#### Phase B done checks

- [x] Every option classified as "move to codec defaults" has a corresponding
  OASA codec test asserting the default behavior.
- [x] Every option classified as "expose only when codec supports it" is
  accepted as a kwarg by the OASA codec and has a codec test.
- [x] No retired option appears in the GUI manifest or as a codec kwarg.
- [x] GUI manifest schema validation test passes (strict, no unknown keys).
- [x] Every codec name in `format_menus.yaml` matches `get_registry_snapshot()`.
- [x] GTML retention decision documented. If import-only: round-trip test
  (GTML -> CDML -> reload) passes with documented data-loss exceptions.
- [x] No deprecated exporters appear in the GUI.
- [x] CDML depiction audit: identify any depiction choices (aromatic style,
  label direction, etc.) where BKChem and OASA have independent defaults.
  Document which are stored in CDML and which need to be added before Phase C.
- [x] CDML v2 decision made: if all depiction changes are additive (new
  optional attributes), stay on current CDML. If any changes are breaking
  (changed semantics, new required attributes), introduce CDML v2.

---

### Phase C: Rendering migration

**Goal:** BKChem export menus produce output by passing CDML to OASA renderers.
No Tk canvas item walking. No `tk2cairo.py`.

This phase depends on the render-ops unification described in
[docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md).

#### Current rendering pipeline (to be replaced)

```
paper.stack  -->  Tk Canvas items  -->  tk2cairo walks items  -->  Cairo surface
(molecules)      (lines, text,          (itemcget, coords,        (PDF/PNG/SVG/PS)
                  polygons)              find_all)
```

#### Target rendering pipeline

```
BKChem canvas  -->  CDML (canonical)  -->  OASA molecules  -->  render_geometry  -->  render_ops
(+Y down)          (+Y up)                (atoms, bonds,       (bond/atom layout)     (LineOp,
                                           coordinates)                                 TextOp, etc.)
                                                                     |
                                                                     v
                                                            OASA thin painters
                                                            (ops_to_cairo, ops_to_svg)
                                                                     |
                                                                     v
                                                            Output file (PDF/PNG/SVG/PS)
```

#### C1: Render-ops MVP for full molecules

Extend `render_geometry.py` to produce ops for all molecule types (not just
Haworth sugars). This is the largest subgoal; scope with an explicit MVP.

**MVP feature list (required before complex molecule tests):**
- Single bonds (lines between atom positions)
- Double bonds (parallel offset lines, including asymmetric placement in rings)
- Triple bonds (three parallel lines)
- Aromatic bonds (alternating single/double or dashed inner ring)
- Wedge bonds (filled triangle for stereo "up")
- Hash/dash bonds (dashed wedge for stereo "down")
- Atom labels (element symbol at vertex when not implicit carbon)
- Charge labels (+, -, 2+, etc. positioned near atom)
- Implicit hydrogen counts (H, H2, H3 appended to atom label)

Test with simple molecules (benzene, ethanol, acetic acid) before attempting
larger structures (cholesterol, caffeine).

**Files changed:**
- `packages/oasa/oasa/render_geometry.py`: Add `molecule_to_ops(mol, style)`.
- `packages/oasa/oasa/render_ops.py`: Add any missing op types if needed.

#### C2: Export pipeline swap

Factor painting out of `svg_out.py` and `cairo_out.py` so they accept
render-ops only. Add high-level entry points in `render_out.py`:
`render_to_pdf(mol, path, **options)`, `render_to_png(...)`, etc.

Register rendering formats in the codec registry as export-only codecs.

During migration, keep old Tk-based and new OASA-based render paths behind a
config flag. Remove old path once smoke tests match.

**Files changed:**
- `packages/oasa/oasa/svg_out.py`: Extract `ops_to_svg(ops, options)`.
- `packages/oasa/oasa/cairo_out.py`: Extract `ops_to_cairo(ops, context, options)`.
- `packages/oasa/oasa/render_out.py`: High-level render entry points.
- `packages/oasa/oasa/codec_registry.py`: Register `pdf`, `png`, `svg`, `ps`
  renderers.

#### C3: CD-SVG codec

Port CD-SVG to OASA. Combines SVG rendering (`svg_out.py`) and CDML
serialization (`cdml_writer.py`). On write, embed CDML in a namespaced metadata
block. On read, extract only the CDML block and ignore all SVG content.

**SVG security mitigations:**
- On export: no `<script>`, no event handlers, no `<foreignObject>`, no
  external URLs.
- On import: treat as untrusted; extract only CDML namespace block.

#### C4: Tk canvas export removal

Delete the Tk canvas export pipeline once the new OASA render path passes all
smoke tests.

**Files deleted:**
- `packages/bkchem-app/bkchem/plugins/tk2cairo.py`
- `packages/bkchem-app/bkchem/plugins/cairo_lowlevel.py`
- `packages/bkchem-app/bkchem/plugins/pdf_cairo.py`
- `packages/bkchem-app/bkchem/plugins/png_cairo.py`
- `packages/bkchem-app/bkchem/plugins/svg_cairo.py`
- `packages/bkchem-app/bkchem/plugins/ps_cairo.py`
- `packages/bkchem-app/bkchem/plugins/ps_builtin.py`
- `packages/bkchem-app/bkchem/plugins/odf.py`

#### Phase C done checks

- [x] `molecule_to_ops()` returns ops for fixture molecules (benzene, lactic
  acid, glycine zwitterion, cyclohexane, caffeine) with correct bond types,
  atom labels, and charge labels.
- [x] After MVP: Haworth sugar fixture renders (q-type bonds).
- [x] SVG output parses as valid XML with expected elements.
- [x] Cairo renders without exceptions for PDF, PNG, SVG, PostScript.
- [x] Render-ops equivalence: SVG and Cairo paths receive the same ops list
  from `molecule_to_ops()`. Ops are compared by type, count, and geometry
  within coordinate tolerance (1e-3), not by strict JSON identity. Painters
  may legitimately differ in text metrics and rounding.
- [x] `get_codec("pdf").write_file(mol, file_obj)` produces non-empty output.
- [x] Wedge geometry invariants: polygon has correct orientation (wide end at
  substituent), correct signed area, no self-intersection. Hatch lines on
  correct side, segment count matches bond length.
- [x] Golden SVG: fixture molecules produce stable op counts by type and
  stable key coordinates (bond midpoints, text anchors). Geometry diffs,
  not pixel diffs.
- [x] WYSIWYG comparison: for same CDML input, Tk-derived and OASA render-ops
  output match on wedge polygon count/bounding boxes, hatch stroke angles,
  attachment points. Differences indicate renderer bug or missing CDML
  depiction fields.
- [x] Smoke: BKChem exports each fixture to SVG, PDF, PNG without exceptions.
- [x] Security smoke: exported CD-SVG contains no `<script>`, no `onload=`,
  no `<foreignObject>`, no external URLs. Import extracts only CDML block.
- [x] `tk2cairo.py`, `cairo_lowlevel.py`, and all `*_cairo.py` rendering
  plugins are deleted.
- [x] `python3 -m pytest tests/ -v` passes.
- [x] `python3 -m pytest tests/test_pyflakes_code_lint.py -v` passes.

---

## Guardrails

- **Tests are the continuous mechanism.** Run tests while you refactor. The
  done-check gates tell you when you can delete old code, not when you can
  start the next phase.
- **Manifest drift.** The BKChem GUI manifest can reference codec names that
  no longer exist in the OASA registry. A unit test must assert that every
  codec name in `format_menus.yaml` has a matching entry in
  `get_registry_snapshot()`. Run this test in CI.
- **CDML is always canonical coordinates.** All CDML exchanged between BKChem
  and OASA uses +Y up. The canvas-to-canonical transform lives in BKChem's
  renderer (preferred) or at the bridge boundary (transitional). No OASA codec
  ever flips coordinates. No per-format Y-axis logic anywhere.
- **Rendering dual-path.** During Phase C, old Tk-based and new OASA-based
  render paths coexist behind a config flag. The old path is not deleted until
  smoke-test output from both paths matches within tolerance (file size,
  element count, visual diff).
- **GTML is investigation, not deletion.** Phase B audits GTML vs CDML feature
  coverage. No files are deleted until the audit proves zero data loss.

---

## Related documents

- [docs/CODEC_REGISTRY_PLAN.md](docs/CODEC_REGISTRY_PLAN.md): Codec registry
  phases 0-5 (all complete). This refactor is the next evolution.
- [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md):
  Render-ops spec, geometry producers, thin painters. Phase C depends on
  and extends that work.
- [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md): BKChem
  owns CDML-as-document, OASA owns CDML-as-chemistry. Phase B evaluates
  whether GTML can retire in favor of CDML.
- [docs/MODULAR_MENU_ARCHITECTURE.md](docs/MODULAR_MENU_ARCHITECTURE.md):
  Proposes moving format handlers to OASA and chemistry tools to modular
  built-ins. Phase A implements the format handler portion.
- [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md): Current plugin contract
  documentation. Will be superseded by the YAML manifest spec.
- [docs/TODO_CODE.md](docs/TODO_CODE.md): Contains related backlog items
  (legacy PostScript removal, RDKit/Open Babel evaluation).

## Key files

### OASA (backend)

- [packages/oasa/oasa/codec_registry.py](packages/oasa/oasa/codec_registry.py):
  Codec registry with `Codec` class, `register_codec()`, `get_codec()`.
- [packages/oasa/oasa/render_ops.py](packages/oasa/oasa/render_ops.py):
  Render op dataclasses (`LineOp`, `PolygonOp`, `CircleOp`, `PathOp`,
  `TextOp`) and JSON serialization.
- [packages/oasa/oasa/render_geometry.py](packages/oasa/oasa/render_geometry.py):
  Bond geometry producer, `BondRenderContext`.
- [packages/oasa/oasa/svg_out.py](packages/oasa/oasa/svg_out.py): SVG renderer.
- [packages/oasa/oasa/cairo_out.py](packages/oasa/oasa/cairo_out.py): Cairo
  renderer (PNG, PDF, SVG, PostScript via Cairo).
- [packages/oasa/oasa/render_out.py](packages/oasa/oasa/render_out.py):
  Multi-format entry point.
- [packages/oasa/oasa/codecs/](packages/oasa/oasa/codecs/): CML, CML2, CDXML
  codec modules.

### BKChem (GUI shell)

- [packages/bkchem-app/bkchem/oasa_bridge.py](packages/bkchem-app/bkchem/oasa_bridge.py):
  Bridge layer with generic `_read_codec_file_to_bkchem_mols()` and
  `_write_codec_file_from_bkchem_paper()`.
- [packages/bkchem-app/bkchem/plugins/__init__.py](packages/bkchem-app/bkchem/plugins/__init__.py):
  Current plugin loader (to be replaced).
- [packages/bkchem-app/bkchem/main.py](packages/bkchem-app/bkchem/main.py):
  `init_plugins_menu()`, `plugin_import()`, `plugin_export()` (to be
  replaced).

### Tests

- [tests/test_codec_registry.py](tests/test_codec_registry.py): OASA codec
  registry unit tests.
- [tests/test_codec_registry_bkchem_bridge.py](tests/test_codec_registry_bkchem_bridge.py):
  Bridge function tests.
- [tests/test_codec_registry_bkchem_plugins.py](tests/test_codec_registry_bkchem_plugins.py):
  Plugin routing tests (rewritten in Phase A).
