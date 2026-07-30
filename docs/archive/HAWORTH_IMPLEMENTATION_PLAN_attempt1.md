# Haworth implementation plan

## Purpose
- Add a Haworth projection renderer for monosaccharides, targeting the look of
  the NEUROtiker SVG style while staying consistent with OASA and BKChem
  rendering conventions.
- Produce clean, publication-grade rings with front-edge bolding and
  consistent label placement.

## Scope
- Initial focus: pyranose (6-member) and furanose (5-member) rings with D/L
  and alpha/beta variants.
- Defer complex glycans until the base ring templates are stable.
- Keep the implementation optional so standard coordinate generation is
  unaffected.

## Style targets (from local SVG samples)
- Use filled polygons or thick strokes for front-facing ring edges.
- Use thinner strokes for back-facing ring edges and substituent bonds.
- Keep ring geometry flat; use Haworth bond styles to convey front/back depth.
- Use existing OASA/BKChem font settings and label spacing to avoid custom
  typography rules.

## Assets for reference
- Local samples:
  - `Alpha-D-Glucopyranose.svg`
  - `Alpha-D-Arabinofuranose.svg`
  - `D-Ribose_Haworth.svg`
  - `D-Xylulose_Haworth.svg`
  - `Haworth_projection_of_a-L-Glucopyranose.svg`
  - [GDP-D-Mannose.svg](../sample_haworth/GDP-D-Mannose.svg)
  - [Sucralose.svg](../sample_haworth/Sucralose.svg)
- Additional sample files from the NEUROtiker galleries (external references,
  not stored in this repo).
  - [NEUROtiker archive 1](https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive1)
  - [NEUROtiker archive 2](https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive2)
  - [NEUROtiker archive 3](https://commons.wikimedia.org/wiki/User:NEUROtiker/gallery/archive3)

## Current rendering constraints
- OASA has a global `line_width` and `bond_width`, but no per-bond thickness.
- OASA bond type includes `'b'` (bold) but is not rendered specially yet.
- OASA has wedge (`'w'`) and hashed (`'h'`) rendering in Cairo, but no wavy
  bond type yet.
- `svg_out.py` ignores `line_width` for edges, hard-codes stroke width, and
  does not render wedge/hashed/bold bond types.
- SVG output currently lacks support for wedge/hashed/bold, so new bond styles
  must land there before Haworth output can be correct.

## Proposed architecture
- Add an OASA module `oasa/haworth.py` that generates coordinates plus style
  hints for Haworth projections.
- Add a `haworth_layout` helper that:
  - Builds ring templates (pyranose and furanose).
  - Assigns atom order and ring orientation.
  - Tags front bonds as bold and back bonds as normal, using existing bond
    styles instead of custom typography.
  - Uses non-regular ring templates derived from sample Haworth drawings,
    avoiding regular polygons.
  - Keeps the ring flat and relies on Haworth bond styles for perspective.
  - Ensures ring bond direction matches the ordered ring traversal so
    wedge/hashed directions are deterministic.
  - Normalizes ring traversal orientation (signed area) so left/right stays
    stable across inputs.
  - For wedge bonds, force the front vertex to be the wide end after
    tagging the Haworth front edge.
  - Positions substituents up/down based on D/L and alpha/beta choices.
- Add a minimal public API to request Haworth layout, for example:
  - `oasa.haworth.build_haworth(mol, mode="pyranose", stereo="alpha", series="D")`

## Rendering updates (OASA)
- Implement per-bond thickness:
  - In `cairo_out.py`, honor `bond.type == "b"` by increasing line width.
  - In `svg_out.py`, pass the `line_width` argument to the SVG elements and
    apply the bold override when `bond.type == "b"`.
- Add explicit Haworth bond styles:
  - Wedge bond for Haworth side edges (solid, non-dashed).
  - Wide rectangle bond for front-facing ring edges (NEUROtiker-style strip).
- Add a wavy bond type (`'s'`) for non-canonical stereochemistry and map it to
  standard molfile stereo code 4 ("either") once rendering exists.
- Keep defaults unchanged for non-Haworth drawings.

## Bond style specs (draft)
- Bold multiplier: derived from NEUROtiker sample
  `docs/sample_haworth/GDP-D-Mannose.svg`, where line stroke width is
  `1.35` and rectangle bond thickness is about `1.615`, yielding ~`1.2x`.
  Use ~1.2x as the initial bold multiplier and adjust if additional samples
  show a different ratio.
- Haworth front selection: use the frontmost edge (largest screen y) for
  the rectangle bond, then apply wedges on the adjacent edges.
- Wavy bond: use a smooth sine wave (see `wavy_bond.png`) for "either"
  stereochemistry.

## Data model and detection
- Start with explicit user input (mode, series, alpha/beta, ring atom order).
- Avoid full SMILES stereochemistry inference in phase 1.
- Add a lightweight sugar template descriptor later if needed.

## Implementation phases
1) Rendering: add per-bond thickness support in Cairo and SVG.
2) Layout: implement pyranose and furanose ring templates with Haworth
   bond tagging.
2.5) Ring oxygen placement: rotate the ring so the O atom sits at the top
   portion of the ring when present.
3) Substituents: position OH/CH2OH groups using up/down rules for D/L and
   alpha/beta.
4) Bond styles: add full new bond type support in Cairo and SVG, including
   wavy variants, wide rectangle, and per-bond colors.
5) API + tests: add a small smoke test and a reference PNG/SVG output.
6) Docs: document the new API and add usage examples.
7) CLI: add a small CLI entry point for Haworth output so batch and test
   rendering can be scripted.

## Testing plan
### Unit tests
- Haworth layout geometry: verify ring templates yield expected atom order
  and bond directions for pyranose and furanose.
- Bond tagging: confirm front edges are tagged with the correct bond style
  (wide rectangle) and back edges remain normal.
- Stereochemistry flags: confirm D/L and alpha/beta input toggles the expected
  up/down substituent placement without needing full stereochemical inference.
- CDML encoding: ensure new bond types round-trip through CDML load/save.
- Template discovery: scan the templates folder tree and verify categories and
  subcategories are inferred from folder names.

### Smoke tests
- Render a Haworth reference molecule to SVG and PNG, then compare key
  properties (non-empty output, expected dimensions, and presence of bold/wavy
  bond markers).
- Render a glucose "smoke" molecule with a wavy anomeric bond and confirm the
  wavy bond path exists in SVG output.
- Insert each template (furanose, pyranose, alanine, palmitate, pyrimidine,
  purine) into a blank drawing and confirm a non-empty molecule is created.
- Post-Stage 2: render a "printer self-test" sheet that includes every bond
  type and wavy variant in multiple colors (hex RGB), and confirm the SVG/PNG
  outputs are non-empty and contain the expected bond markers.

## Staged rollout with testable outcomes
### Stage 1: SVG/Cairo bond width + existing styles
- Outcome: `bond.type == "b"` renders thicker in SVG and Cairo; wedge/hashed
  render in SVG.
- Tests: render a molecule with normal, bold, wedge, and hashed bonds; assert
  SVG contains the expected stroke widths and wedge/hashed shapes.

### Stage 2: Full new bond types support
- Outcome: new bond types render in SVG and Cairo, including wavy variants,
  wide rectangle, and per-bond colors (hex RGB).
- Tests: render a "printer self-test" sheet with every bond type and color;
  assert SVG includes bond-style markers and PNG output is non-empty.

### Stage 3: Haworth layout (ring geometry + bond tagging)
- Outcome: `build_haworth()` produces pyranose/furanose layouts and tags
  front edges with the correct Haworth bond styles.
- Tests: unit tests for ring coordinates and bond tags; smoke render to SVG/PNG
  and confirm bold/wide bonds are present.

### Stage 4: Substituent placement (D/L, alpha/beta)
- Outcome: substituent up/down rules apply correctly for both ring types.
- Tests: unit tests comparing substituent vectors against expected up/down
  orientation.

### Stage 5: Templates (insert-only flow + folder scan)
- Outcome: templates are discovered by folder/subfolder names and inserted
  into an existing drawing.
- Tests: scan returns correct category/subcategory mapping; smoke test inserts
  all six templates into a blank document and confirms a non-empty molecule.

### Stage 6: Docs + reference outputs
- Outcome: updated docs plus reference SVG/PNG for Haworth and wavy-bond
  glucose samples.
- Store reference outputs under `reference_outputs`
  and document regeneration in
  [REFERENCE_OUTPUTS.md](../REFERENCE_OUTPUTS.md).
- Tests: smoke test ensures reference outputs exist and are non-empty.

### Stage 7: CLI + batch output
- Outcome: provide a CLI for Haworth rendering that accepts SMILES input and
  produces SVG/PNG outputs for batch testing and automation.
- Example target command (final syntax TBD):
  - `python3 packages/oasa/oasa_cli.py haworth --smiles 'OC[C@@H]1O`O``O``O`[C@H]1O' --output alpha-D-glucopyranose.png`
- Tests: smoke run the CLI with known SMILES inputs and confirm output files
  exist and are non-empty.

## Open questions
- Where to host the Haworth entry point in BKChem (GUI tool, exporter option,
  or a separate script)?
- What minimal input format should be used to avoid ambiguous stereochemistry?
- Should bolding be a fixed multiplier or derived from the base line width?
  - Initial draft: ~1.2x derived from NEUROtiker sample rectangles.

## CDML format ownership
- CDML is a BKChem-native format (no external governing body). New bond types
  should be documented in BKChem format docs and kept backward compatible
  within BKChem tooling.

## Side feature: biomolecule templates
- Add a simple template picker in the BKChem GUI for common biomolecule
  starting points, without new rendering logic.
- Use four macro categories with six templates:
  - Carbs: furanose, pyranose (generic rings to edit into glucose/fructose).
  - Protein: alanine.
  - Lipids: palmitate.
  - Nucleic acids: pyrimidine, purine.
- Store templates as plain CDML files (native BKChem format) to keep them small.
- Keep templates in a simple folder tree and infer categories and
  subcategories from folder names by scanning `.cdml` files on load, so users
  can add or customize templates by dropping in new CDML files.
- Use an insert workflow (add templates into existing drawings) instead of
  replacing the current molecule file.
- Ship templates inside the macOS DMG app bundle so they are available under
  `/Applications/BKChem.app/` installs; pick a stable resource path within the
  app bundle and scan it at startup.
- Menu placement: add an Insert menu item (for example "Insert > Biomolecule
  Template...") that opens the template picker.

## Side feature: wavy bond smoke molecule
- Use a glucose "smoke" molecule that shows unknown anomeric carbon with a
  wavy bond from the anomeric carbon to the OH group.
- Reference sample image: `wavy_bond.png` (wide-kurtosis sine wave style).
