# Haworth Schematic Renderer - Implementation Plan (Attempt 2)

Status: Closed (2026-02-14). Core Haworth schematic renderer (Phases 1-5c) complete.
SMILES conversion phases (6, 7) and stretch goals (6b) deferred to backlog.

## Phase Status Tracker

Use this checklist to track implementation progress against this plan.

- [x] Phase 1: Sugar Code Parser
- [x] Phase 2: Haworth Spec Generator
- [x] Phase 3: Haworth Schematic Renderer
- [x] Phase 4: Integration
- [x] Phase 5: Verify
- [x] Phase 5b: NEUROtiker Archive Reference Testing
- [x] Phase 5c: Rendering Polish and Documentation
- [x] Phase 0 Exit Checklist fully closed
- [-] Phase 6b: Stretch Goals (deferred to backlog)
- [-] Phase 6: Sugar Code to SMILES (deferred to backlog)
- [-] Phase 7: SMILES to Sugar Code (deferred to backlog)

## Background

Attempt 1 (`docs/HAWORTH_IMPLEMENTATION_PLAN_attempt1.md`) used SMILES to build a
molecular graph, then rendered it through the standard atom/bond pipeline. This worked
for ring geometry (stages 1-3) but failed at stage 4 (substituent placement): OH and H
groups became atom objects with bonds, producing cluttered molecular diagrams instead of
clean Haworth projections.

Attempt 2 bypasses the molecular graph entirely. A custom sugar code string
(see `docs/SUGAR_CODE_SPEC.md`) feeds a schematic renderer that outputs `render_ops`
directly. Substituents are floating text labels, not atoms.

## Scope

This renderer is **schematic-only**. It produces a flat list of `render_ops` (primitive
drawing instructions) for visual output. It does NOT produce:
- Molecule objects (no atoms, bonds, or graph)
- Editable chemical drawings
- CDML-round-trippable data
- Anything that interacts with selection, editing, or molecule-semantic tools

Integration points are limited to contexts where molecule semantics are not required:
- `tools/selftest_sheet.py` vignettes (visual output only)
- Future standalone CLI for Haworth SVG/PNG export

If editable Haworth drawings are ever needed, that would require a separate approach
building on the molecular graph pipeline (see attempt 1 for why that is hard).

## Architecture

```
Sugar Code String          e.g. "ARLRDM" + "alpha" + "pyranose"
       |
  sugar_code.parse()       -> ParsedSugarCode dataclass
       |
  haworth_spec.generate()  -> HaworthSpec dataclass (substituent labels)
       |
  haworth_renderer.render() -> list[render_ops] (LineOp, TextOp, PolygonOp)
       |
  ops_to_svg / ops_to_cairo  (existing infrastructure)
```

No molecular graph. No atom/bond rendering. No `_build_molecule_ops()`.

## Phase 0: Definition of Done

Phase 0 is complete only when the following are true:

- Parser, spec generator, and schematic renderer (Phases 1-5) are implemented.
- Conversion supports all Haworth-cyclizable prefixes in the matrix: `A`, `MK`.
- Both ring families are supported: `furanose` and `pyranose`.
- Meso trioses are accepted as parseable sugar codes but rejected for Haworth
  conversion with explicit ring-capacity `ValueError`.
- All tests listed in Phases 1-5 pass.
- Selftest integration renders non-empty outputs for required examples.
- No molecule graph/CDML editing semantics are introduced.

Phase 0 non-goals:

- Sugar code to SMILES conversion.
- SMILES to sugar code conversion.
- Editable Haworth molecules in BKChem.
- Transparent/alpha-channel background masking for the oxygen label (solid
  `bg_color` polygon is the only masking strategy; callers using transparent
  backgrounds will see a visible mask rectangle).
- Pixel-accurate text width measurement (character-count heuristic via
  `_visible_text_length` is sufficient for Phase 0; font-metric-aware width
  measurement is deferred).
- Exocyclic chain rendering beyond 2 carbons (common sugars have at most 2
  exocyclic carbons; heptose/octose chains will render collinearly, which is
  acceptable for Phase 0).
- Multi-ring layout (disaccharides, polysaccharides) requires a ring-positioning
  coordinator that does not exist yet. Single monosaccharide rendering only.
- Text collision detection (post-render bounding box overlap analysis and automatic
  connector length adjustment). Heuristic spacing multipliers are sufficient for
  Phase 0.

Phase 0 acceptance gates:

- Unit gate: parser/spec/renderer tests pass.
- Geometry gate: substituent up/down placement tests verify y-coordinates
  relative to ring vertices for alpha-D-glucopyranose and beta-D-glucopyranose
  (wrong placement must fail, not silently render).
- Integration gate: `tools/selftest_sheet.py --format svg` runs and outputs expected vignettes.
- Regression gate: full repository tests pass.
- Determinism gate: repeated runs with same input produce identical slot mapping and label placement.

## Per-Phase Test Matrix (deliverable + unit + integration + smoke/system/E2E)

- Phase 1 (parser)
  - Deliverable: `packages/oasa/oasa/sugar_code.py` with `ParsedSugarCode` and `parse()`.
  - Unit: `tests/test_sugar_code.py` (28 cases listed) isolated parser behaviors.
  - Integration: none (parser is leaf); keep units fast.
  - Smoke/System: `tests/smoke/test_sugar_code_smoke.py` runs a curated batch from `tests/fixtures/smoke_sugar_codes.txt`, asserting Haworth-eligible codes parse without exceptions, invalids raise `ValueError`, and `sugar_code_raw` round-trips.
  - Additional angles: add Hypothesis-based property test (parser idempotence on whitespace/footnote ordering) if time permits.

- Phase 2 (spec generator)
  - Deliverable: `packages/oasa/oasa/haworth_spec.py` with `HaworthSpec` and `generate()`.
  - Unit: `tests/test_haworth_spec.py` (16 cases) for substituent logic and ring-capacity errors.
  - Integration: parser + spec happy-path matrix test (`parse()` then `generate()` for common sugars) to ensure token handoff remains compatible.
  - Smoke/System: `tests/smoke/test_haworth_spec_smoke.py` iterates sugar fixtures across `ring_type` `{pyranose,furanose}` and `anomeric` `{alpha,beta}` where legal; asserts non-empty `substituents`, alpha/beta flip at anomeric carbon, meso trioses raise ring-capacity `ValueError` with prefix/ring detail.

- Phase 3 (renderer)
  - Deliverable: `packages/oasa/oasa/haworth_renderer.py` with `render()` returning `render_ops`.
  - Unit: `tests/test_haworth_renderer.py` (31 cases) geometry, bbox, label placement, bg mask, chain handling.
  - Integration: parser + spec + renderer pipeline test renders ops and checks slot mapping is stable (no file I/O).
  - Smoke/System: `tests/smoke/test_haworth_renderer_smoke.py` generates ops for the sugar matrix, writes SVGs via `ops_to_svg` to temp files, asserts file exists, size > 0, contains `<svg`, and ops include `PolygonOp` and `TextOp`; includes one colored `bg_color` render.

- Phase 4 (integration into selftest)
  - Deliverable: updated `tools/selftest_sheet.py` and `packages/oasa/oasa/__init__.py` wiring.
  - Unit/Integration: `tests/test_selftest_haworth_builders.py` imports `_build_alpha_d_glucopyranose_ops()` and `_build_beta_d_fructofuranose_ops()`; asserts non-empty ops, presence of `PolygonOp` and `TextOp`, and positive bbox. This is faster and more direct than invoking the CLI.
  - Smoke/System: existing acceptance gate `python tools/selftest_sheet.py --format svg` remains for visual/manual check; could be automated later with a golden SVG snapshot once outputs stabilize.

- Phase 5 (verify)
  - Deliverable: all prior phases green.
  - System/E2E: run `python -m pytest tests/` plus `python tools/selftest_sheet.py --format svg` as release gate; no new tests authored in this phase.

- Phases 6-7 (SMILES conversion, future scope)
  - Deliverables: `sugar_code_smiles.py`, `smiles_to_sugar_code.py` and their unit tests (already listed).
  - Integration: parser/spec + SMILES conversion round-trip (`sugar_code -> smiles -> sugar_code`).
  - Smoke/E2E: `tests/smoke/test_sugar_code_smiles_roundtrip.py` (initially `@pytest.mark.skip` until Phase 6 lands) covering canonical sugars; rejects pathway-only carbon-state inputs.
  - Additional angle: golden/snapshot tests for canonical SMILES strings to catch drift.

Test taxonomy guidance: unit (single function), integration (multiple components in-process), system/E2E (CLI/real I/O), smoke (minimal happy-path batch), regression (bug fixes), property-based (Hypothesis), performance/load (later if renderer speed becomes a concern), snapshot/golden (SVG output once stable), fuzz (parser input fuzz to guard against crashes).

## Phase 1: Sugar Code Parser

**New file**: `packages/oasa/oasa/sugar_code.py`

```python
@dataclasses.dataclass(frozen=True)
class ParsedSugarCode:
    prefix: str                          # "ALDO", "KETO", or "3-KETO" (normalized kind)
    positions: list[tuple[str, tuple]]   # [("R", ()), ("d", ("deoxy",)), ...]
    config: str                          # "DEXTER", "LAEVUS", or "MESO" (internal parser value)
    terminal: tuple[str, tuple]          # ("M", ()) or ("c", ("carboxyl",))
    footnotes: dict[str, str]            # {"1": "deoxy", ...}
    sugar_code: str                      # body only (no footnote block), includes literal prefix token
    sugar_code_raw: str                  # exact original input (includes footnote block if present)

def parse(code_string: str) -> ParsedSugarCode
def _extract_footnotes(s: str) -> tuple[str, dict[str, str]]
def _parse_prefix(body: str) -> tuple[str, str]
def _parse_config_and_terminal(remainder: str, footnotes: dict) -> tuple[list, str, tuple]
```

**Key parsing logic**:
- Split `"A2LRDM[2R=CH3]"` into body `"A2LRDM"` + footnotes `{"2R": "CH3"}`
- Extract prefix by matching `^(A|MK|M[RL]K)`
- Accept `MRK`/`MLK` as valid prefix tokens.
- Reject bare prefix-only codes (for example `MRK`, `MLK`) because they do not
  satisfy `<PREFIX><STEREOCENTERS><CONFIG><C_TERMINAL_STATE>`.
- Normalize prefix token to internal kind:
  - `A` -> `ALDO`
  - `MK` -> `KETO`
  - `MRK`/`MLK` -> `3-KETO`
- Store both sugar-code forms (no separate `prefix_token` field):
  - `sugar_code`: body before footnotes, includes literal prefix token
  - `sugar_code_raw`: exact original input string
- Enforce split invariants:
  - no footnotes: `sugar_code_raw == sugar_code`
  - with footnotes: `sugar_code_raw.startswith(sugar_code)` and the suffix is
    the bracket footnote block
- Scan remaining characters left-to-right: each character is one carbon position
- Config token is `D` or `L` in the penultimate position, except meso form `MKM`
- Parser normalizes config tokens to internal values:
  - `D` -> `DEXTER`
  - `L` -> `LAEVUS`
  - meso forms -> `MESO`
- Terminal is the last character (`M`, or a letter code like `c`/`p`, or a digit)
- Letter codes (`d`, `a`, `n`, `p`, `f`, `c`) are resolved to their built-in meanings
- Unrecognized lowercase letter codes raise `ValueError` with the unknown
  character and its position; the parser does not pass through unknown codes
- Digit markers are resolved via the footnotes dict
- Side-qualified digit footnotes (`nL`, `nR`) are parsed as explicit
  Fischer-left/Fischer-right substituent overrides for backbone position `n`
- Carbon-state keys (`nC`) are parsed as properties of backbone position `n` itself
  (for example `3C=CH2`)
- Numeric overrides use backbone-index-matched body digits in all modes
  (for example `c23[2C=C3(EPO3),3C=CH2]`, `A2LRDM[2R=CH3]`)
- Compound carbon-state plus attachments use a single key:
  `nC=<state>(<attachment1>,...)` (for example `2C=C3(EPO3)`); this is the
  only valid way to combine carbon-state and attached-group data for one
  backbone position
- Validate parser-level syntax per [docs/SUGAR_CODE_SPEC.md](docs/SUGAR_CODE_SPEC.md):
  - all digits must have definitions
  - numeric definitions must reference only digits present in the body
  - definitions are emitted in ascending digit order
  - body digits must match backbone position indices
  - plain `n=` is invalid at chiral stereocenters (must use `nL`/`nR`, or `nC`)
  - if only `nL` or only `nR` appears, missing side defaults to `H`
  - `nC` keys are allowed only for indices present in the body
  - for one backbone position index:
    - plain `n` and `nC` are mutually exclusive
    - `nL` and `nR` may co-occur
    - plain `n`/`nC` must not co-occur with `nL`/`nR`
  - one backbone position index cannot appear more than once as plain `n` or
    `nC` in the same footnote block
  - minimum sugar code body length is 3 (`len(body) >= 3`)
  - one- and two-character codes are invalid
  - `len(body) == backbone_carbons`
  - for unbranched sugars, `backbone_carbons == total_carbons`
  - suffix is `[DL]<terminal-or-modifier>`, except meso ketotriose forms
    `MK<terminal-or-modifier>`
  - `D` appears only in the penultimate position (token-level rule)

**Haworth conversion matrix** (used by `haworth_spec.generate`):

| Prefix | Ring Type | Min Carbons | Ring Closure | Ring Carbons | Exocyclic |
|--------|-----------|-------------|--------------|--------------|-----------|
| `A` | furanose | 4 (tetrose) | C1-O-C4 | C1,C2,C3,C4 | Cn>4 off C4 |
| `A` | pyranose | 5 (pentose) | C1-O-C5 | C1,C2,C3,C4,C5 | Cn>5 off C5 |
| `MK` | furanose | 5 (pentose) | C2-O-C5 | C2,C3,C4,C5 | C1 off C2, Cn>5 off C5 |
| `MK` | pyranose | 6 (hexose) | C2-O-C6 | C2,C3,C4,C5,C6 | C1 off C2, Cn>6 off C6 |

Sugars larger than the minimum have extra exocyclic carbons. For example, an
aldohexose (6 carbons) + furanose closes C1-O-C4 with C5 and C6 hanging off C4.
This is fully deterministic: one carbonyl = one anomeric center = one possible ring
closure per ring size.

The parser validates `len(body)` matches backbone carbon count. The spec generator
validates that the prefix + ring_type combination is in the matrix above and that the
required carbon count constraints are met. Mismatches raise `ValueError` with a
descriptive message.
This is the final handling path for supported prefixes and ring closures; non-cyclizable
inputs fail fast with explicit minimum-carbon and closure diagnostics.

**New test file**: `tests/test_sugar_code.py`
- `test_parse_simple_aldose`: ARLRDM (D-glucose, 6 chars)
- `test_parse_pentose`: ARRDM (D-ribose, 5 chars)
- `test_parse_ketose`: MKLRDM (D-fructose, 6 chars)
- `test_parse_letter_code`: AdRDM (deoxyribose, 5 chars)
- `test_parse_with_footnotes`: A2LRDM[2R=CH3] (6 chars)
- `test_parse_raw_and_body_split`: `A2LRDM[2R=CH3]` stores
  `sugar_code="A2LRDM"` and `sugar_code_raw="A2LRDM[2R=CH3]"`
- `test_parse_mixed`: AdLRD6[6=sulfate] (6 chars, letter + footnote)
- `test_parse_meso_forms`: MKM parses with `config="MESO"`
- `test_parse_meso_modified_triose`: MKp parses with `config="MESO"`
- `test_parse_config_normalization`: `D`/`L` tokens normalize to
  `DEXTER`/`LAEVUS`
- `test_parse_numeric_pathway_override`: `c23[2C=C3(EPO3),3C=CH2]`
  parses with backbone-index-matched numeric overrides
- `test_parse_numeric_pathway_carbon_state`: `c23[2C=C3(EPO3),3C=CH2]`
  parses with explicit carbon-state keys
- `test_parse_numeric_pathway_duplicate_index_invalid`: reject multiple plain/nC
  entries for the same backbone position index in one block
- `test_parse_invalid_key_mix_same_index`: reject mixed key families for one
  position index (for example `2C=...` with `2L=...`, or `2=...` with `2C=...`)
- `test_parse_compound_carbon_state_single_key`: accept `nC=<state>(...)` as
  the combined form and reject split multi-key alternatives for the same
  position
- `test_parse_side_qualified_footnotes`: `A2M[2L=COOH,2R=CH3]` parses with explicit
  left/right override entries for backbone position 2
- `test_parse_side_qualified_footnotes_single_defaults_h`: `A2M[2L=OH]`
  defaults `2R` to `H` (equivalent to `ALM`)
- `test_parse_side_qualified_footnotes_single_defaults_h_right`: `A2M[2R=OH]`
  defaults `2L` to `H` (equivalent to `ADM`)
- `test_parse_invalid_raises`: missing config, undefined footnotes, wrong length
- `test_parse_invalid_digit_position`: reject `A1LRDM[1=CH3]` (backbone-index mismatch)
- `test_parse_invalid_chiral_plain_key`: reject `A2LRDM[2=CH3]` (chiral side unspecified)
- `test_parse_too_short_invalid`: one- and two-character codes raise `ValueError`
- `test_parse_mrk_mlk_prefix_supported`: accept `MRK` and `MLK` as prefixes in full codes
- `test_parse_prefix_only_invalid`: reject bare prefix-only codes like `MRK`/`MLK`
- `test_parse_prefix_ring_mismatch`: pentose + pyranose aldose raises ValueError
- `test_generate_meso_ring_capacity_error`: MKM/MKp + furanose/pyranose raises ValueError
- `test_parse_unknown_letter_code_raises`: reject unrecognized lowercase letter
  code (for example `AzRDM` where `z` is not in the built-in table) with
  `ValueError` naming the unknown character and its backbone position
- `test_parse_unknown_letter_code_uppercase_not_affected`: uppercase letters
  (`R`, `L`, `D`, `M`) are config/terminal tokens, not letter codes; they must
  not trigger the unknown-letter-code check
- `test_parse_pathway_profile_haworth_ineligible_marker`: parse pathway-style
  carbon-state chemistry (for example `c23[2C=C3(EPO3),3C=CH2]`) without
  auto-qualifying it as Haworth-eligible

## Phase 2: Haworth Spec Generator

**New file**: `packages/oasa/oasa/haworth_spec.py`

```python
@dataclasses.dataclass(frozen=True)
class HaworthSpec:
    ring_type: str                  # "pyranose" or "furanose"
    anomeric: str                   # "alpha" or "beta"
    substituents: dict[str, str]    # {"C1_up": "OH", "C1_down": "H", ...}
    carbon_count: int               # 5 (pyranose) or 4 (furanose) ring carbons
    title: str                      # "alpha-D-Glucopyranose"

def generate(
    parsed: ParsedSugarCode,
    ring_type: str,
    anomeric: str,
) -> HaworthSpec
```

### Ring closure rules

The anomeric carbon and ring closure point are determined by prefix + ring type.
One carbonyl = one anomeric center = one possible ring closure per ring size.

| Prefix | Anomeric | Furanose closure | Pyranose closure |
|--------|----------|------------------|------------------|
| `A` | C1 | C1-O-C4 | C1-O-C5 |
| `MK` | C2 | C2-O-C5 | C2-O-C6 |

Both supported prefixes are handled by the same ring-closure logic. If a sugar does not
have enough carbons for the requested ring closure, `generate()` raises `ValueError`.

### Phase 0 Haworth-eligible subset gate

`haworth_spec.generate()` in Phase 0 accepts only Haworth-eligible sugar-code
inputs that map directly to up/down substituent labels on ring carbons and
simple exocyclic chain positions. Pathway-profile carbon-state chemistry is not
Haworth-eligible in Phase 0.

Must reject with clear `ValueError` (prefix, ring type, and reason):
- any `nC=` carbon-state entries
- alkene/enol descriptors (for example `C=<index>(E)`, `C=<index>(Z)`,
  `C=C...`, `EPO3`)
- pathway-specific non-Haworth carbon-state compounds (for example
  `C(=O)OPO3`, `C(=O)SCoA`)

### Series resolution for generation

- Parsed `DEXTER` and `LAEVUS` are consumed during substituent-direction generation.
- Parsed `MESO` is parseable (`MKM`, `MKp`) but not cyclizable for Haworth conversion.
- `HaworthSpec` stores resolved up/down substituent labels and does not carry a
  separate `config` field.
- Haworth conversion for meso trioses fails at ring-capacity validation.

**General formula**: closure_carbon = anomeric + (ring_members - 2), where
ring_members = 4 (furanose) or 5 (pyranose) carbon atoms in the ring.

### Ring vs exocyclic carbon classification

Given a sugar code with `n` total carbons and a ring closing at Cx:

- **Ring carbons**: anomeric through Cx (inclusive)
- **Pre-anomeric exocyclic**: carbons before the anomeric (A: none, MK: C1)
- **Post-closure exocyclic**: carbons after Cx (Cx+1 through Cn hang off Cx)
- **Exocyclic chain lengths**:
  - `pre_chain_len = anomeric - 1`
  - `post_chain_len = n - closure_carbon`

**Worked examples**:

| Sugar code | Ring type | n | Ring | Pre-exo | Post-exo |
|------------|-----------|---|------|---------|----------|
| ARLRDM (glucose) | pyranose | 6 | C1-C5 | none | C6 off C5 |
| ARLRDM (glucose) | furanose | 6 | C1-C4 | none | C5,C6 off C4 |
| ARRDM (ribose) | furanose | 5 | C1-C4 | none | C5 off C4 |
| ARRDM (ribose) | pyranose | 5 | C1-C5 | none | none |
| ARDM (erythrose) | furanose | 4 | C1-C4 | none | none |
| MKLRDM (fructose) | furanose | 6 | C2-C5 | C1 off C2 | C6 off C5 |
| MKLRDM (fructose) | pyranose | 6 | C2-C6 | C1 off C2 | none |

### Substituent assignment algorithm

For each ring carbon Ci, assign up/down labels:

1. **Anomeric carbon**: OH placed by alpha/beta rule
   - D-alpha -> OH down, H up
   - D-beta -> OH up, H down
   - L-series: reversed
   - This alpha/beta orientation rule is applied at the anomeric carbon for both
     supported prefixes (`A`, `MK`).
2. **Interior ring stereocenters** (from sugar code R/L or letter codes):
   - `R` -> OH down, H up (Fischer right -> Haworth down)
   - `L` -> OH up, H down
   - `d` -> H down, H up (deoxy: both H)
   - Other letter codes: replace OH with the modification label
3. **Config carbon** (`DEXTER` or `LAEVUS`, resolved from config token):
   - If in the ring: determines which direction the exocyclic chain points
   - DEXTER: exocyclic chain up; LAEVUS: exocyclic chain down
   - If exocyclic: its own OH follows its R/L equivalent (DEXTER=right, LAEVUS=left)
4. **Post-closure exocyclic chain** (off the last ring carbon):
   - 0 extra carbons: no exocyclic substituent (H on that side)
   - 1 extra carbon with `M` terminal: label = "CH2OH"
   - 1 extra carbon with modifier: label = modifier (e.g., "COOH" for `c`)
   - 2+ extra carbons: label = "CH(OH)CH2OH" or rendered as a mini chain
     (LineOp connectors with intermediate labels; see Phase 3 Step 5)
5. **Pre-anomeric exocyclic** (for `MK` prefix: C1 hangs off anomeric C2):
   - C1 is always CH2OH (from the `M` in `MK`)
   - Placed opposite to the anomeric OH
   - D-alpha: C2_up=CH2OH, C2_down=OH
   - D-beta: C2_up=OH, C2_down=CH2OH
   - **Collision note**: both visible labels are wide text. Renderer should
     increase `sub_length` for carbons where neither label is "H".

**Letter code label mapping**:

| Letter | Modification | Haworth label |
|--------|-------------|---------------|
| `d` | deoxy | H (both up and down) |
| `a` | amino | NH2 |
| `n` | N-acetyl | NHAc |
| `p` | phosphate-right/terminal phosphate | OPO3 |
| `P` | phosphate-left | OPO3 |
| `f` | fluoro | F |
| `c` | carboxyl | COOH |

**New test file**: `tests/test_haworth_spec.py`

Standard cases:
- `test_glucose_alpha_pyranose`: ARLRDM + pyranose + alpha -> C1_down=OH, C2_down=OH, C3_up=OH, C5_up=CH2OH
- `test_glucose_beta_pyranose`: C1_up=OH (only change from alpha)
- `test_galactose_alpha`: ARLLDM + pyranose -> C4 epimer differs from glucose
- `test_deoxyribose_furanose`: AdRDM + furanose + beta -> C2 both H, C4_up=CH2OH
- `test_fructose_beta_furanose`: MKLRDM + furanose + beta -> C2_up=OH, C2_down=CH2OH
- `test_fructose_alpha_furanose`: MKLRDM + furanose + alpha -> C2_up=CH2OH, C2_down=OH
- `test_fructose_anomeric_both_wide`: verify both C2 labels are non-trivial (not "H")
- `test_triose_haworth_not_cyclizable`: ADM and MKM raise ring-capacity `ValueError`

Ring closure edge cases:
- `test_glucose_furanose`: ARLRDM + furanose -> ring C1-C4, exocyclic C5+C6 off C4
- `test_ribose_pyranose`: ARRDM + pyranose -> ring C1-C5, no exocyclic chain
- `test_erythrose_furanose`: ARDM + furanose -> ring C1-C4, no exocyclic chain
- `test_fructose_pyranose`: MKLRDM + pyranose -> ring C2-C6, C1 off C2, no post-exo
- `test_triose_ring_capacity_error`: MKM + furanose/pyranose raises ValueError
- `test_haworth_rejects_pathway_carbon_state`: parser accepts
  `c23[2C=C3(EPO3),3C=CH2]`, `haworth_spec.generate()` raises `ValueError`
- `test_haworth_rejects_acyl_state_tokens`: parser accepts pathway-style
  `nC` chemistry tokens, `haworth_spec.generate()` rejects as non-Haworth

Exocyclic chain length:
- `test_exocyclic_0`: aldopentose pyranose has no exocyclic carbons
- `test_exocyclic_1`: aldohexose pyranose has 1 exocyclic carbon (CH2OH off C5)
- `test_exocyclic_2`: aldohexose furanose has 2 exocyclic carbons (C5+C6 off C4)

## Phase 3: Haworth Schematic Renderer

**New file**: `packages/oasa/oasa/haworth_renderer.py`

```python
def render(spec: HaworthSpec, bond_length: float = 30.0,
           font_size: float = 12.0, font_name: str = "sans-serif",
           show_carbon_numbers: bool = False,
           line_color: str = "#000", label_color: str = "#000",
           bg_color: str = "#fff") -> list
```

Font defaults match `render_ops.TextOp` (font_size=12.0, font_name="sans-serif").
Thickness multipliers are proportional to `bond_length`, not absolute values.
`bg_color` is used for the O-label mask polygon (see Step 4). Callers on non-white
backgrounds should pass their background color to avoid halo artifacts.

### Step 1: Ring coordinates

Reuse templates from `haworth.py`:
```python
from . import haworth
template = haworth.PYRANOSE_TEMPLATE  # or FURANOSE_TEMPLATE
o_index = haworth.PYRANOSE_O_INDEX    # or FURANOSE_O_INDEX
scaled = haworth._ring_template(ring_size, bond_length)
```

### Step 2: Template slots and carbon mapping

Confirmed from HTML templates in biology-problems repo
(`haworth_pyranose_table.html`, `haworth_furanose_table.html`):

```python
# Slot names are semantic and ordered around the ring in template traversal order.
# This keeps the representation stable and readable without exposing arbitrary indices.
# Two-letter slots are abbreviations of explicit position names:
# ML=MIDDLE_LEFT, TL=TOP_LEFT, TO=TOP_OXYGEN,
# MR=MIDDLE_RIGHT, BR=BOTTOM_RIGHT, BL=BOTTOM_LEFT
PYRANOSE_SLOTS = ("ML", "TL", "TO", "MR", "BR", "BL")
FURANOSE_SLOTS = ("ML", "BL", "BR", "MR", "TO")

PYRANOSE_SLOT_INDEX = {
    "ML": 0,
    "TL": 1,
    "TO": 2,
    "MR": 3,     # anomeric slot for prefix A
    "BR": 4,
    "BL": 5,
}

FURANOSE_SLOT_INDEX = {
    "ML": 0,
    "BL": 1,
    "BR": 2,
    "MR": 3,     # anomeric slot for prefix A
    "TO": 4,
}

def carbon_slot_map(spec: HaworthSpec) -> dict[str, str]:
    # Dynamic carbon->slot mapping handles both supported prefix families.
    # A-furanose:  C1->MR, C2->BR, C3->BL, C4->ML
    # MK-furanose: C2->MR, C3->BR, C4->BL, C5->ML
    # A-pyranose:  C1->MR, C2->BR, C3->BL, C4->ML, C5->TL
    # MK-pyranose: C2->MR, C3->BR, C4->BL, C5->ML, C6->TL
    ...
}
```

### Step 3: Draw ring edges as filled polygons

Each ring edge is a filled `PolygonOp` (4-point shape), not a line. This matches the
NEUROtiker reference SVGs where every edge is a `<path>` polygon.

**Core geometry**:
```python
def _edge_polygon(p1, p2, thickness_at_p1, thickness_at_p2):
    """Compute a 4-point filled polygon for a ring edge.
    Uniform edges: same thickness at both ends.
    Wedge edges: thickness tapers from thick to thin.
    """
```

**Three edge styles**:

1. **Front edge** (bottommost, e.g. C2-C3 in pyranose): thick uniform polygon
   - `thickness = bond_length * 0.15`

2. **Wedge side edges** (adjacent to front edge): tapered trapezoid
   - Thick end at front vertex: `bond_length * 0.15`
   - Thin end at back vertex: `bond_length * 0.04`

3. **Back edges** (all others): thin uniform polygon
   - `thickness = bond_length * 0.04`

**Edge classification** via explicit template metadata (not inferred from coordinates):

```python
# Front edge is keyed by slot for readability, then resolved to index.
PYRANOSE_FRONT_EDGE_SLOT = "BR"  # edge BR -> BL
FURANOSE_FRONT_EDGE_SLOT = "BL"  # edge BL -> BR

PYRANOSE_FRONT_EDGE_INDEX = PYRANOSE_SLOT_INDEX[PYRANOSE_FRONT_EDGE_SLOT]
FURANOSE_FRONT_EDGE_INDEX = FURANOSE_SLOT_INDEX[FURANOSE_FRONT_EDGE_SLOT]
```

Wedge edges are the two edges adjacent to the front edge (indices +/-1 mod ring_size).
All other edges are back edges. This avoids fragile y-midpoint inference that could
break under coordinate system flips or template rotations.

### Step 4: Place oxygen label

`TextOp("O")` at `coords[o_index]`, bold, dark red. A `PolygonOp` filled with
`bg_color` behind it to mask ring edges at that vertex. Default `bg_color="#fff"`;
callers rendering on colored backgrounds must pass their background color to
avoid halo artifacts.

**Known limitation (Phase 0 non-goal)**: The solid-polygon mask cannot handle
transparent/alpha-channel backgrounds. On a transparent PNG, the mask will
appear as a visible opaque rectangle behind the "O" label. Solving this would
require clipping the ring-edge paths to exclude the oxygen vertex region, which
is deferred to a future phase.

### Step 5: Place substituent labels

**Critical design decision**: Substituents are ONLY `TextOp` + `LineOp`. No atoms.
No bonds. No molecular graph objects. Just:
- A short connector `LineOp` from the ring vertex outward
- A `TextOp("OH", x, y)` at the end of the connector

Per-slot label directions (from HTML template analysis):

```python
PYRANOSE_SLOT_LABEL_CONFIG = {
    "MR": {"up_dir": (1, -1),  "down_dir": (1, 1),  "anchor": "start"},
    "BR": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "end"},
    "BL": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "start"},
    "ML": {"up_dir": (-1, -1), "down_dir": (-1, 1), "anchor": "end"},
    "TL": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "middle"},
}

FURANOSE_SLOT_LABEL_CONFIG = {
    "MR": {"up_dir": (1, -1),  "down_dir": (1, 1),  "anchor": "start"},
    "BR": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "end"},
    "BL": {"up_dir": (0, -1),  "down_dir": (0, 1),  "anchor": "start"},
    "ML": {"up_dir": (-1, -1), "down_dir": (-1, 1), "anchor": "end"},
}
```

Direction selection is slot-based, then labels are attached using the dynamic
carbon-to-slot map for the current prefix and ring type.

**Simple substituents** (0 or 1 exocyclic carbons):

For each ring carbon:
1. Look up `spec.substituents["C{n}_up"]` and `spec.substituents["C{n}_down"]`
2. Normalize direction vector, multiply by `sub_length = bond_length * 0.4`
3. Draw `LineOp` connector + `TextOp` label
4. TextOp supports `<sub>` tags for subscripts: `"CH<sub>2</sub>OH"`
5. For bbox measurement, strip HTML tags before computing text width:
   `_visible_text_length("CH<sub>2</sub>OH")` returns `5` (not `20`).
   Implementation: `re.sub(r"<[^>]+>", "", text)` then `len(result)`
   **Known limitation (Phase 0 non-goal)**: `_visible_text_length` counts
   characters, not pixel width. Wide characters like "W" and narrow ones like
   "I" count equally. This is a rough heuristic that works for typical sugar
   labels (OH, H, CH2OH, NH2, F, COOH) but will not prevent all overlaps for
   unusually wide or narrow labels. Font-metric-aware width measurement would
   require coupling to the rendering backend and is deferred.
6. For carbons where both labels are non-trivial (neither is "H"), increase
   `sub_length` by 1.5x to avoid label collision

**Multi-carbon exocyclic chains** (2+ exocyclic carbons, e.g. aldohexose furanose):

When the post-closure exocyclic chain has 2+ carbons (e.g. C5-C6 off C4 in
aldohexose furanose), render as a mini chain of connectors and labels extending
from the last ring carbon:

```
Ring-C4 ---LineOp---> "CHOH" ---LineOp---> "CH2OH"
          (sub_length)         (sub_length)
```

Each segment uses the same direction vector as the parent carbon's up/down
direction. The intermediate carbon's stereochemistry (R/L at the config position)
determines whether its OH label goes left or right of the chain. This is the
same connector+text approach used for simple substituents, just chained.

**Known limitation (Phase 0 non-goal)**: All exocyclic chain segments extend
collinearly (same direction vector). For sugars with 3+ exocyclic carbons (e.g.
aldoheptose furanose with C5-C6-C7 off C4), the chain will be a long straight
line. This is acceptable for Phase 0 because common monosaccharides have at most
2 exocyclic carbons. Zigzag or angled chain rendering is deferred.

### Step 6: Optional carbon numbers

Small `TextOp` labels (font_size * 0.65) placed between vertex and ring center.

### Concrete example: alpha-D-Glucopyranose

Input: `sugar_code.parse("ARLRDM")` + pyranose + alpha

```
C1_up: "H"       C1_down: "OH"     <- alpha: OH down
C2_up: "H"       C2_down: "OH"     <- R: OH down
C3_up: "OH"      C3_down: "H"      <- L: OH up
C4_up: "H"       C4_down: "OH"     <- R: OH down
C5_up: "CH2OH"   C5_down: "H"      <- D-series: CH2OH up
```

Output: ~28 primitive render_ops (PolygonOp for ring edges + O mask, TextOp for labels,
LineOp for connectors). Zero molecule/atom/bond objects.

**New test file**: `tests/test_haworth_renderer.py`
- `test_render_returns_ops`: non-empty list
- `test_render_contains_text_ops`: has O, OH, H labels
- `test_render_contains_polygon_ops`: ring edge count
- `test_render_bbox_reasonable`: bounding box within expected range
- `test_render_furanose`: 5-member ring works
- `test_render_with_carbon_numbers`: adds number labels
- `test_render_aldohexose_furanose`: ARLRDM + furanose renders multi-carbon chain off C4
- `test_render_ribose_pyranose`: ARRDM + pyranose has no exocyclic chain
- `test_render_erythrose_furanose`: ARDM + furanose has no exocyclic chain
- `test_render_front_edge_stable`: verify front edge index matches template metadata
- `test_render_furanose_labels`: furanose label directions match `FURANOSE_SLOT_LABEL_CONFIG`
- `test_render_bbox_sub_tags`: bbox for "CH<sub>2</sub>OH" matches visible width (5 chars)
- `test_render_fructose_anomeric_no_overlap`: both wide labels on C2 don't collide

Substituent geometry verification (concern: renderer tests must verify up/down
placement, not just presence):
- `test_render_alpha_glucose_c1_oh_below`: render ARLRDM + pyranose + alpha,
  find the "OH" TextOp associated with C1 (slot MR), verify its y-coordinate is
  greater than (below) the C1 ring vertex y-coordinate. This catches a wrong
  up/down assignment that presence-only tests would miss.
- `test_render_alpha_glucose_c3_oh_above`: same sugar, find the "OH" TextOp at
  C3 (slot BL), verify its y-coordinate is less than (above) the C3 ring vertex
  y-coordinate (L -> OH up).
- `test_render_beta_glucose_c1_oh_above`: render ARLRDM + pyranose + beta,
  verify C1 "OH" TextOp y < ring vertex y (beta flips C1 OH from down to up).
- `test_render_all_substituents_correct_side`: for alpha-D-glucopyranose, iterate
  over every ring carbon, collect (vertex_y, up_label_y, down_label_y) triples,
  and assert that every "up" label has y < vertex_y and every "down" label has
  y > vertex_y. This is a systematic geometry gate that catches any single
  misplaced label.
- `test_render_fructose_c2_labels_both_offset`: for MKLRDM + furanose + beta,
  verify both C2 labels (OH and CH2OH) are offset from the ring vertex by at
  least `sub_length` distance, and that the up-label y < vertex y < down-label y.
- `test_render_l_series_reverses_directions`: render ALRLDM + pyranose + alpha
  (L-glucose), verify that C1 OH is up (opposite of D-alpha), confirming L-series
  reversal logic.

Visible text length and collision avoidance:
- `test_visible_text_length_strips_tags`: `_visible_text_length("CH<sub>2</sub>OH")`
  returns 5
- `test_visible_text_length_no_tags`: `_visible_text_length("OH")` returns 2
- `test_visible_text_length_empty`: `_visible_text_length("")` returns 0
- `test_visible_text_length_nested_tags`: `_visible_text_length("<b>O<sub>2</sub></b>")`
  returns 2
- `test_sub_length_multiplier_dual_wide`: for a carbon where both up and down
  labels are non-"H" (e.g. fructose C2 with OH and CH2OH), verify the connector
  LineOp length is approximately 1.5x the default `sub_length` (within 5%
  tolerance)
- `test_sub_length_default_single_wide`: for a carbon where one label is "H"
  (e.g. glucose C1 with H up and OH down), verify the connector LineOp length
  matches the default `sub_length` (no multiplier)

Oxygen mask and background color:
- `test_render_o_mask_uses_bg_color`: render with `bg_color="#f0f0f0"`, find the
  PolygonOp behind the "O" TextOp, verify its fill color is "#f0f0f0" (not white)
- `test_render_o_mask_default_white`: render with default args, verify the O-mask
  PolygonOp fill is "#fff"
- `test_render_o_mask_is_polygon_not_rect`: verify the mask is a PolygonOp
  (not a rectangle), documenting that this is a solid polygon approach

Multi-carbon exocyclic chain geometry:
- `test_render_exocyclic_2_chain_direction`: render ARLRDM + furanose (2
  exocyclic carbons C5-C6 off C4), verify the chain extends in the same
  direction as C4's up/down slot direction, and both segments share the same
  direction vector
- `test_render_exocyclic_2_chain_labels`: same sugar, verify the chain contains
  a "CHOH" TextOp followed by a "CH2OH" TextOp at increasing distance from C4
- `test_render_exocyclic_0_no_chain`: render ARRDM + pyranose (0 exocyclic
  carbons), verify no chain connectors extend beyond the ring
- `test_render_exocyclic_3_collinear`: render a 7-carbon aldose + furanose
  (ARLRRDM, 3 exocyclic carbons C5-C6-C7 off C4), verify all 3 chain segments
  use the same direction vector (documenting the collinear Phase 0 behavior)

## Phase 4: Integration

**Modify**: `tools/selftest_sheet.py`

Replace `_build_alpha_d_glucopyranose_ops()` and `_build_beta_d_fructofuranose_ops()`:

```python
def _build_alpha_d_glucopyranose_ops():
    parsed = sugar_code.parse("ARLRDM")
    spec = haworth_spec.generate(parsed, ring_type="pyranose", anomeric="alpha")
    return haworth_renderer.render(spec, bond_length=30)

def _build_beta_d_fructofuranose_ops():
    parsed = sugar_code.parse("MKLRDM")
    spec = haworth_spec.generate(parsed, ring_type="furanose", anomeric="beta")
    return haworth_renderer.render(spec, bond_length=30)
```

Remove dead code: `_build_alpha_d_glucopyranose_mol()`,
`_build_beta_d_fructofuranose_mol()`, `_add_explicit_h_to_haworth()`.

**Modify**: `packages/oasa/oasa/__init__.py`

Register new modules in imports and `_EXPORTED_MODULES`.

## Phase 5: Verify

- `python -m pytest tests/test_sugar_code.py -v`
- `python -m pytest tests/test_haworth_spec.py -v`
- `python -m pytest tests/test_haworth_renderer.py -v`
- `python tools/selftest_sheet.py --format svg` -> visually inspect output
- `python -m pytest tests/` -> full regression (existing tests still pass)

## Phase 5b: NEUROtiker Archive Reference Testing

The `neurotiker_haworth_archive/` directory contains 103 high-quality Haworth projection
SVGs from Wikimedia's NEUROtiker gallery. 78 of these map to specific sugar code +
ring type + anomeric combinations and serve as visual reference targets.

### Archive Mapping (78 mappable SVGs)

| Sugar Code | Name | Ring Forms |
|-----------|------|------------|
| `ARDM` | D-Erythrose | furanose (alpha/beta) |
| `ALDM` | D-Threose | furanose (alpha/beta) |
| `ARRDM` | D-Ribose | furanose + pyranose (alpha/beta) |
| `ALRDM` | D-Arabinose | furanose + pyranose (alpha/beta) |
| `ARLDM` | D-Xylose | furanose + pyranose (alpha/beta) |
| `ALLDM` | D-Lyxose | furanose + pyranose (alpha/beta) |
| `ARRRDM` | D-Allose | furanose + pyranose (alpha/beta) |
| `ALRRDM` | D-Altrose | furanose + pyranose (alpha/beta) |
| `ARLRDM` | D-Glucose | furanose + pyranose (alpha/beta) |
| `ALLRDM` | D-Mannose | furanose + pyranose (alpha/beta) |
| `ARRLDM` | D-Gulose | furanose + pyranose (alpha/beta) |
| `ALRLDM` | D-Idose | furanose + pyranose (alpha/beta) |
| `ARLLDM` | D-Galactose | furanose + pyranose (alpha/beta) |
| `ALLLDM` | D-Talose | furanose + pyranose (alpha/beta) |
| `MKRDM` | D-Ribulose | furanose (alpha/beta) |
| `MKLDM` | D-Xylulose | furanose (alpha/beta) |
| `MKLRDM` | D-Fructose | furanose + pyranose (alpha/beta) |
| `MKLLDM` | D-Tagatose | furanose + pyranose (alpha/beta) |
| `MKRRDM` | D-Psicose | furanose + pyranose (alpha/beta) |
| `MKRLDM` | D-Sorbose | furanose + pyranose (alpha/beta) |
| `ALRRLd` | L-Fucose | pyranose (alpha/beta) |
| `ARRLLd` | L-Rhamnose | pyranose (alpha/beta) |
| `ARLLDc` | D-Galacturonic acid | pyranose (alpha/beta) |

### Not mappable (25 SVGs)

- 20 generic `D-Sugar_Haworth.svg` (open-chain equilibrium, no specific anomeric form)
- 3 polysaccharides: Amylopektin, Cellulose, Chitin (stretch goals)
- 2 disaccharides: Lactose, Maltose (stretch goals)

### Test fixtures

- `tests/fixtures/neurotiker_archive_mapping.py` - sugar code to archive filename mapping
- `tests/fixtures/archive_ground_truth.py` - manually verified substituent labels for all 78 forms

### Test coverage

- **Parametrized spec tests** (`test_haworth_spec.py::test_archive_ground_truth`): 78 entries
  validating every substituent label against ground truth derived from Fischer projection
  stereocenter rules and cross-referenced against archive SVGs.
- **Full smoke matrix** (`smoke/test_haworth_renderer_smoke.py::test_archive_full_matrix`):
  78 entries rendering every mappable sugar and verifying SVG output.

### Rendering quality improvements

Applied during Phase 5b to improve visual fidelity relative to NEUROtiker references:

1. **Gradient ring edges near oxygen**: Ring edges touching the oxygen vertex are split
   into two colored halves (dark red near O, black away from O), matching the molecular
   renderer's `color_bonds=True` behavior.
2. **Connector-to-label alignment**: Text positioning uses direction-aware baseline shift
   instead of directional offset, eliminating gaps between connector endpoints and labels.
3. **Connector length consistency**: Dual-wide substituent multiplier reduced from 1.5x
   to 1.2x for more uniform visual spacing.

## Phase 5c: Rendering Polish and Documentation

### Explicit hydrogen toggle

Added `show_hydrogens: bool = True` parameter to `haworth_renderer.render()`. When
`False`, H labels and their connector lines are suppressed, matching conventions
used by NEUROtiker archive and most published Haworth projections. Default is `True`
for backward compatibility.

### Connector spacing tuning

- Default connector length increased from `bond_length * 0.40` to `bond_length * 0.45`
  for 12.5% more breathing room between ring vertices and labels.
- Dual-wide multiplier (for carbons with both labels non-H) increased from 1.2x to 1.3x.

### Collision test vignettes

Added two new vignettes to the selftest sheet (row 3):
- **alpha-D-Psicopyranose** (MKRRDM): inner ring collision test case (multiple OH
  groups on same side at adjacent carbons)
- **alpha-D-Tagatofuranose** (MKLLDM): external positioning test case (multiple OH
  groups extending outward from the same region)

### OH vs HO convention

The renderer uses side-aware hydroxyl ordering: "OH" for right-anchored labels
(start anchor), "HO" for left-anchored labels (end anchor). This places the oxygen
closest to the ring/connector in both cases. NEUROtiker archive always uses "OH"
regardless of side, but the "HO" convention has chemical advantages and was retained.

### Connector endpoint policy (superseded)

This section is superseded by the closed bond-label cutover in
[docs/archive/COMPLETE_BOND_LABEL_PLAN.md](../archive/COMPLETE_BOND_LABEL_PLAN.md).

Current policy is shared target/constraint attachment resolution, not
hydroxyl-specific endpoint branching:

- Endpoints are resolved through shared target primitives and constraints
  (`AttachTarget`, `AttachConstraints`, `resolve_attach_endpoint(...)` in
  `packages/oasa/oasa/render_geometry.py`).
- Haworth label placement and endpoint legality use the same attachment-policy
  surface as other renderers.
- Historical hydroxyl-specific text/endpoint branches are retired and retained
  here only as implementation history.

## Phase 0 Exit Checklist

Status: complete as of 2026-02-08 after running
`source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest tests/ -q`
(333 passed, 6 skipped) and
`source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/selftest_sheet.py --format svg`
(generated `oasa_capabilities_sheet.svg`).

- Implemented files from Phases 1-4 exist and are imported where required.
- All Phase 1-5 tests pass with Python 3.12.
- Ring-capacity validation errors include prefix, ring type, minimum carbons, and provided carbons.
- Triose Haworth conversion errors include ring-capacity guidance.
- Haworth generator rejects pathway-profile carbon-state chemistry (`nC`/alkene/enol/acyl tokens) with clear eligibility errors.
- Parser rejects unrecognized lowercase letter codes with `ValueError`.
- Renderer uses slot keys (`ML`, `TL`, `TO`, `MR`, `BR`, `BL`) consistently.
- Renderer geometry tests verify y-coordinate placement of substituent labels
  relative to ring vertices (not just presence of labels in the ops list).
- Oxygen mask `bg_color` parameter is tested with non-white colors.
- `docs/SUGAR_CODE_SPEC.md` and this plan agree on prefix/ring closure matrix.
- `docs/SUGAR_CODE_SPEC.md` includes canonical glycolysis/CAC pathway-profile
  sugar codes before Phase 0 sign-off.

## Phase 6b: Stretch Goals (Future Work)

### Multi-ring rendering architecture

Disaccharides and polysaccharides require positioning multiple Haworth rings relative to
each other with glycosidic bond connectors between them. This is a fundamentally different
layout problem from single-ring rendering and needs:

- A `HaworthLayout` coordinator that accepts multiple `HaworthSpec` objects + bond info
- Relative positioning rules (e.g., "ring B's C4 connects to ring A's C1")
- Glycosidic bond rendering (the connector between rings)
- Non-overlapping ring placement algorithm

This architecture does not exist yet and is prerequisite for all multi-ring goals below.

### Disaccharides (requires multi-ring architecture)

Target molecules from NEUROtiker archive:
- Maltose (`neurotiker_haworth_archive/Maltose_Haworth.svg`) - alpha-1,4 linked glucopyranoses
- Lactose (`neurotiker_haworth_archive/Lactose_Haworth.svg`) - galactose beta-1,4 glucose

Additional targets (no archive reference):
- Sucrose (glucose + fructose, alpha-1,2 linkage)
- Isomaltose (glucose + glucose, alpha-1,6 linkage)

### Polysaccharides (requires multi-ring + repeating unit architecture)

Target molecules from NEUROtiker archive:
- Amylopektin (`neurotiker_haworth_archive/Amylopektin_Haworth.svg`)
  - Alpha-1,4 linked glucopyranose with alpha-1,6 branch points
  - NEUROtiker rendering is exceptionally good visual target
- Cellulose (`neurotiker_haworth_archive/Cellulose_Haworth.svg`)
  - Beta-1,4 linked glucopyranose
- Chitin (`neurotiker_haworth_archive/Chitin_Haworth.svg`)
  - Beta-1,4 linked N-acetylglucosamine (GlcNAc)
  - Uses letter code `n` (NHAc) at C2

### Text collision detection (future rendering improvement)

Current Phase 0 uses heuristic spacing (connector length multipliers) without actual
bounding box computation. A future improvement could add:
- Approximate text width estimation based on character count and font size
- Post-render collision detection between TextOp bounding boxes
- Automatic connector length adjustment to resolve overlaps
- Test molecules: D-Psicose (MKRRDM, inner collisions), D-Tagatose (MKLLDM, external)

## Phase 6: Sugar Code to SMILES

This phase is intentionally out of Phase 0 scope. Keep as future work only.

Implementation status (2026-02-08): initial bootstrap landed with
`sugar_code_to_smiles()` support for two validated reference cases
(`ARLRDM` + pyranose + alpha, and `MKLRDM` + furanose + beta), with unit tests;
full matrix conversion remains pending.

**New file**: `packages/oasa/oasa/sugar_code_smiles.py`

```python
def sugar_code_to_smiles(code_string: str, ring_type: str, anomeric: str) -> str
    """Convert a sugar code + ring parameters to a SMILES string.

    Example:
        sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
        -> "OC[C@@H]1OC(O)[C@@H](O)[C@H](O)[C@@H]1O"
    """
```

**Approach**: Build the open-chain carbon skeleton from the sugar code, then apply ring
closure. The stereochemistry mapping (Fischer R/L to SMILES `@`/`@@`) is a fixed lookup
per carbon position because CIP priorities follow a predictable pattern along the sugar
chain.

**Steps**:
1. Parse sugar code to get prefix, stereocenters, config, terminal
2. Build open-chain: C1-C2-...-Cn with correct substituents at each position
3. Map Fischer R/L to CIP R/S at each stereocenter using a position-specific table:
   - For aldohexose: C2(R->@@, L->@), C3(R->@, L->@@), C4(R->@@, L->@), C5(D->@@, L->@)
   - For other sugar types: derive from the substituent priority ordering
4. Apply ring closure (pyranose: C1-O-C5, furanose: C1-O-C4 or C2-O-C5)
5. Set anomeric stereochemistry (alpha/beta)
6. Handle modifications: deoxy removes OH, amino replaces OH with NH2, etc.
7. Return canonical SMILES via OASA's `smiles.get_smiles()` for normalization

**Fischer-to-CIP lookup table** (for D-aldohexoses):

The CIP assignment at each carbon depends on substituent priorities. For standard
aldohexose carbons in pyranose ring form, this is deterministic because the chain
direction and ring oxygen create fixed priority orderings.

**New tests** in `tests/test_sugar_code_smiles.py`:
- `test_glucose_smiles`: ARLRDM + pyranose + alpha -> known glucose SMILES
- `test_galactose_smiles`: ARLLDM -> known galactose SMILES (C4 epimer)
- `test_ribose_smiles`: ARRDM + furanose + beta -> known ribose SMILES
- `test_fructose_smiles`: MKLRDM + furanose + beta -> known fructose SMILES
- `test_deoxyribose_smiles`: AdRDM + furanose + beta -> known deoxyribose SMILES
- `test_round_trip`: sugar code -> SMILES -> (Phase 7) -> sugar code matches original

## Phase 7: SMILES to Sugar Code (Best-Effort)

This phase is intentionally out of Phase 0 scope. Keep as future work only.

**New file**: `packages/oasa/oasa/smiles_to_sugar_code.py`

```python
class SugarCodeResult:
    sugar_code: str          # e.g. "ARLRDM"
    ring_type: str           # "pyranose" or "furanose"
    anomeric: str            # "alpha" or "beta"
    name: str                # "D-glucose" (if known)
    confidence: str          # "exact_match", "inferred", "unsupported"

def smiles_to_sugar_code(smiles_string: str) -> SugarCodeResult
```

**Two-tier approach**:

### Tier 1: Lookup table (high confidence)

Build a canonical SMILES lookup table from `sugar_codes.yaml` at module load time.
For each entry in the YAML, generate all ring forms (pyranose alpha, pyranose beta,
furanose alpha, furanose beta) using Phase 6's `sugar_code_to_smiles()`, canonicalize
via OASA, and store the mapping.

```python
# Built at module load from sugar_codes.yaml
_CANONICAL_LOOKUP = {
    "OC[C@@H]1OC(O)...": SugarCodeResult("ARLRDM", "pyranose", "alpha", "D-glucose", "exact_match"),
    ...
}
```

Input SMILES is canonicalized, then looked up. If found, return with
`confidence="exact_match"`.

### Tier 2: Structural inference (best-effort)

If no exact match, attempt to identify the sugar skeleton:

1. Parse SMILES to molecular graph via `oasa.smiles.read_smiles()`
2. Find the ring oxygen using `mol.get_smallest_independent_cycles()`:
   - Look for a 5-member or 6-member ring containing exactly one oxygen
3. Number ring carbons starting from the anomeric carbon (adjacent to ring O)
4. Determine ring type from ring size (6-member = pyranose, 5-member = furanose)
5. For each ring carbon, check substituents:
   - OH -> R or L (determine by CIP-to-Fischer reverse mapping)
   - H,H (no oxygen) -> `d` (deoxy)
   - NH2 -> `a` (amino)
   - NHAc -> `n` (N-acetyl)
   - F -> `f` (fluoro)
6. Determine D/L from penultimate carbon stereochemistry
7. Determine alpha/beta from anomeric carbon stereochemistry
8. Build sugar code string and return with `confidence="inferred"`

### Graceful failure

If the input cannot be recognized as a monosaccharide (no suitable ring, multiple
rings, unrecognized substituents), return a clear error:

```python
raise SugarCodeError(
    "The input SMILES is not compatible with the sugar code converter.\n"
    "Supported inputs are monosaccharides with a single pyranose or furanose ring.\n"
    "\n"
    "Examples of supported SMILES:\n"
    "  OC[C@@H]1OC(O)[C@@H](O)[C@H](O)[C@@H]1O   (alpha-D-glucopyranose)\n"
    "  OC[C@H]1OC(O)[C@@H](O)[C@@H]1O              (beta-D-ribofuranose)\n"
    "  OC[C@@H]1OC(O)(CO)[C@H](O)[C@@H]1O          (beta-D-fructofuranose)\n"
)
```

**New tests** in `tests/test_smiles_to_sugar_code.py`:
- `test_glucose_from_smiles`: known glucose SMILES -> ARLRDM + pyranose
- `test_galactose_from_smiles`: known galactose SMILES -> ARLLDM
- `test_deoxyribose_from_smiles`: known deoxyribose SMILES -> AdRDM + furanose
- `test_fructose_from_smiles`: known fructose SMILES -> MKLRDM + furanose
- `test_round_trip_all_common`: all entries from sugar_codes.yaml round-trip
- `test_unsupported_smiles_error`: benzene, ethanol, disaccharides -> SugarCodeError
- `test_error_message_has_examples`: error message contains example SMILES

## Key Files

| Action | Phase | File |
|--------|-------|------|
| Create | 1 | `packages/oasa/oasa/sugar_code.py` |
| Create | 2 | `packages/oasa/oasa/haworth_spec.py` |
| Create | 3 | `packages/oasa/oasa/haworth_renderer.py` |
| Create | 6 | `packages/oasa/oasa/sugar_code_smiles.py` |
| Create | 7 | `packages/oasa/oasa/smiles_to_sugar_code.py` |
| Create | 1 | `tests/test_sugar_code.py` |
| Create | 2 | `tests/test_haworth_spec.py` |
| Create | 3 | `tests/test_haworth_renderer.py` |
| Create | 6 | `tests/test_sugar_code_smiles.py` |
| Create | 7 | `tests/test_smiles_to_sugar_code.py` |
| Modify | 4 | `tools/selftest_sheet.py` |
| Modify | 4 | `packages/oasa/oasa/__init__.py` |

**Reference files** (read-only):
- `packages/oasa/oasa/haworth.py` - ring templates and O_INDEX constants
- `packages/oasa/oasa/render_ops.py` - LineOp, TextOp, PolygonOp dataclasses
- `packages/oasa/oasa/render_geometry.py` - `haworth_front_edge_ops()`
- `packages/oasa/oasa/smiles.py` - SMILES parser/writer (Phase 6-7)
- `packages/oasa/oasa/stereochemistry.py` - CIP R/S handling (Phase 6-7)
- `docs/SUGAR_CODE_SPEC.md` - format specification
- `docs/sample_haworth/*.svg` - NEUROtiker reference renderings

## Review Response Log

Findings from code review and how each was addressed:

| ID | Finding | Resolution |
|----|---------|------------|
| P1a | Schematic-only scope not stated | Added "Scope" section: no molecules, no CDML, no editing. Integration limited to selftest vignettes and standalone CLI. |
| P1b | Front-edge detection by y-midpoint is fragile | Replaced with explicit `PYRANOSE_FRONT_EDGE_INDEX` / `FURANOSE_FRONT_EDGE_INDEX` template metadata. Added `test_render_front_edge_stable`. |
| P2a | Ketose 3-substituent anomeric underspecified | Clarified: only 2 visible labels (OH + CH2OH), H is implicit. Added collision avoidance note and `test_fructose_anomeric_no_overlap`. |
| P2b | Hard-coded Arial font | Changed defaults to match `render_ops.TextOp` (sans-serif, 12.0). All style params are caller-configurable. |
| P2c | White O-mask assumes white background | Added `bg_color` parameter (default "#fff") to `render()`. Documented that callers must pass their background color. |
| P3a | Missing FURANOSE_LABEL_CONFIG | Added explicit furanose label config and moved to slot-based direction keys (`MR`, `BR`, `BL`, `ML`) so A/MK furanose closures share the same geometry without arbitrary index numbering. Added `test_render_furanose_labels`. |
| P3b | `<sub>` tag bbox inflation | Added `_visible_text_length()` with `re.sub(r"<[^>]+>", "", text)`. Added `test_render_bbox_sub_tags`. |
| P3c | num_carbons validation undefined | Added validation matrix (prefix + ring_type -> expected carbon count). Added `test_parse_prefix_ring_mismatch`. |
| R2-P1a | Plan hardcodes "terminal M = CH2OH at C5" | Replaced with general ring-closure rule table and exocyclic chain derivation algorithm. Ring vs exocyclic is computed from num_carbons + ring type, not hardcoded. |
| R2-P1b | Furanose aldohexose ring closure not specified | Added explicit ring-closure rules: aldose furanose = C1-O-C4, aldose pyranose = C1-O-C5, etc. Worked examples table covers all combinations. |
| R2-P2a | Ketose anomeric 3-substituent placement rule missing | Added deterministic rule: C1 CH2OH placed opposite to anomeric OH based on alpha/beta. Collision avoidance via increased sub_length. |
| R2-P2b | num_carbons not tied to ring type for exocyclic chain | Added "ring vs exocyclic carbon classification" algorithm deriving post-closure and pre-anomeric exocyclic chains from num_carbons and closure carbon. |
| R2-new | Multi-carbon exocyclic chains (2+) not handled | Added rendering rule: chain of LineOp+TextOp connectors extending from last ring carbon. Tests for aldohexose furanose, ribose pyranose, erythrose furanose. |

## Related Documents

- `docs/SUGAR_CODE_SPEC.md` - sugar code format specification
- `docs/HAWORTH_IMPLEMENTATION_PLAN_attempt1.md` - previous attempt (SMILES-based)
