# Sugar Code Specification

## Overview

Sugar codes provide a compact notation for representing carbohydrate structures,
including both standard and modified sugars. This specification extends the original
sugar code format to support chemical modifications using lowercase letter codes
and numeric footnote markers.

**Key rule**: `len(sugar_code) == backbone_carbons`.
Each character, including prefix characters, corresponds to one backbone carbon
position.
For unbranched sugars, `backbone_carbons == total_carbons` (triose=3, tetrose=4,
pentose=5, hexose=6, heptose=7). For branched pathway compounds, total carbons
may exceed sugar-code length.
Two-carbon "sugars" are out of scope; monosaccharides here start at 3 carbons.
Codes with fewer than 3 total characters are invalid.

**Source of truth**: [packages/oasa/oasa_data/sugar_codes.yaml](packages/oasa/oasa_data/sugar_codes.yaml).

## Normative Language

The terms MUST, SHOULD, and MAY are used as defined in RFC 2119 style guidance:

- MUST: required for compliant parsing/conversion behavior.
- SHOULD: recommended unless there is a documented reason to differ.
- MAY: optional behavior.

## Basic Format

### Standard Sugar Code

```
<PREFIX><STEREOCENTERS><CONFIG><C_TERMINAL_STATE>
```

**Components**:

1. **PREFIX** (1-3 characters): Defines the carbonyl type
   - Prefix characters occupy the first backbone carbon positions (they are not
     out-of-band metadata).
   - `A*****` = aldose (aldehyde at C1)
   - `MK****` = 2-ketose (ketone at C2, hydroxymethyl at C1)
   - `MRK***` or `MLK***` = 3-ketose family prefixes (ketone at C3, stereocenter at C2)
   - Note: `*` characters are visual fillers for alignment only, not literal code characters.
   - Parser implementations SHOULD normalize these tokens to:
     - `A` -> `ALDO`
     - `MK` -> `KETO`
     - `MRK`/`MLK` -> `3-KETO`
   - Parser/output models SHOULD preserve:
     - `sugar_code`: body only (no footnote block), with literal prefix token
     - `sugar_code_raw`: exact original input (includes footnotes when present)

2. **STEREOCENTERS** (0+ characters): Interior chiral carbons
   - `R` = OH on right (in Fischer projection)
   - `L` = OH on left (in Fischer projection)
   - Can be replaced with lowercase letter codes or numeric footnote modifiers (see below)

3. **CONFIG** (1 character): Series configuration
   - `D` = D-series (penultimate carbon has OH on right)
   - `L` = L-series (penultimate carbon has OH on left)

4. **C_TERMINAL_STATE** (1 character): C-terminal carbon state token
   - `M` = hydroxymethyl (CH2OH)
   - May be replaced by a modifier token (for example `p`, `c`, digit marker)

### Prefix-Only Strings

`MRK` and `MLK` are valid PREFIX tokens, but bare strings like `MRK` or `MLK`
are INVALID full sugar codes because `<CONFIG><C_TERMINAL_STATE>` are missing.

### Position Mapping

Each character maps to a carbon. For aldoses (`A` prefix):
```
A      R      L      R      D      M
C1     C2     C3     C4     C5     C6
(CHO)  (OH-R) (OH-L) (OH-R) (D-cfg)(CH2OH)
```

For 2-ketoses (`MK` prefix):
```
M      K      L      R      D      M
C1     C2     C3     C4     C5     C6
(CH2OH)(keto) (OH-L) (OH-R) (D-cfg)(CH2OH)
```

### Pathway C1-Substitution Extension

For open-chain pathway encoding, the carbonyl marker position defines the family:

- `K` at C2 defines a 2-keto family entry, while C1 can be any valid token
  (for example `MKLRDM`, `pKLRDp`, `cK3`).
- `K` at C3 defines a 3-keto family entry.
- If no `K` appears at C2/C3, the entry is treated as aldose-derived, and C1 may
  still be substituted in pathway mode (for example `pRLRDp`).

### Representative examples (full mapping lives in sugar_codes.yaml)

For complete code-to-name data, use
[packages/oasa/oasa_data/sugar_codes.yaml](packages/oasa/oasa_data/sugar_codes.yaml).
This spec intentionally shows only minimal examples needed to explain format.

```
ADM     = D-glyceraldehyde        # triose aldose
ARRDM   = D-ribose                # pentose aldose
ARLRDM  = D-glucose               # aldohexose
MKLRDM  = D-fructose              # ketohexose
MKRRDM  = D-psicose               # ketohexose
ARLRRDM = D-glycero-D-gluco-heptose  # aldoheptose
```

## Extended Format: Chemical Modifications

Two systems for modifications: **letter codes** (common, no footnotes needed)
and **numeric footnotes** (rare/custom, must be defined).

### Letter Codes (Common Modifications)

Lowercase letters replace `R` or `L` at stereocenter positions. No footnote
definition needed - the meaning is built into the letter.

| Letter | Modification | Description | Replaces |
|--------|-------------|-------------|----------|
| `d` | deoxy | No oxygen | OH -> H,H |
| `a` | amino | Amino group | OH -> NH2 |
| `n` | N-acetyl | N-acetyl amino group | OH -> NHAc |
| `p` | phosphate-right/terminal phosphate | Phosphate at Fischer-right stereocenter or terminal phosphate | OH -> OPO3 |
| `P` | phosphate-left | Phosphate at Fischer-left stereocenter | OH -> OPO3 |
| `f` | fluoro | Fluorine | OH -> F |
| `c` | carboxyl | Carboxyl (terminal) | CH2OH -> COOH |

Phosphate side semantics:
- At stereocenters, `p` is the right-side phosphate form and `P` is the left-side phosphate form.
- At terminal position, use `p`; `P` is invalid at terminal position.

**Examples using letter codes** (no footnotes needed):
```
AdRDM   = 2-deoxy-D-ribose (deoxyribose, DNA sugar)
AdLRDM  = 2-deoxy-D-glucose
AaLRDM  = glucosamine (2-amino-2-deoxy-D-glucose)
AnLRDM  = N-acetylglucosamine (GlcNAc)
ARLRDc  = D-glucuronic acid (C6 is COOH)
ARLRDp  = glucose-6-phosphate
MKp     = dihydroxyacetone phosphate (DHAP)
pKLRDp  = D-fructose-1,6-bisphosphate
pRLRDp  = D-glucose-1,6-bisphosphate
```

**Uronic acid note** (terminal oxidation `M` -> `c`):
```
Glucuronic acid:  ARLRDc  (from ARLRDM)
Galacturonic acid: ARLLDc (from ARLLDM)
Mannuronic acid:  ALLRDc  (from ALLRDM)
```

### Numeric Footnotes (Rare/Custom Modifications)

Numbers (`1`-`9`) are positional backbone-index markers for modifications not
covered by letter codes. Each number must be defined in a `[...]` section.
Under the numbering system used here, body digits MUST match backbone indices
in all modes (monosaccharide and pathway).
Digits refer to sugar-code backbone indices (character positions from the
left), not IUPAC atom numbering.

For chiral carbons, numeric footnotes also support built-in side-qualified keys:
`<index>L` and `<index>R` (Fischer-left and Fischer-right substituents).
To describe the carbon atom state itself (rather than an attached substituent),
use `<index>C`.

**Format**:
```
<SUGAR_CODE>[<DEFINITIONS>]
```

**Examples using numeric footnotes**:
```
A2LRDM[2R=CH3]                   C2 right-side methyl substitution example
A2LRD6[2R=sulfate,6=phosphate]   C2 sulfate + C6 phosphate
A2M[2L=COOH,2R=CH3]              side-specific custom triose substituents at C2
A2M[2L=OH]                       equivalent to ALM (`2R` defaults to `H`)
A2M[2R=OH]                       equivalent to ADM (`2L` defaults to `H`)
```

Invalid under positional numbering:
```
A1LRDM[1=CH3]                    invalid (digit must equal the backbone position it occupies)
A2LRDM[2=CH3]                    invalid at chiral C2 (must use 2L/2R, or 2C for carbon-state)
```

Preferred substituent tokens for footnote values:
`H`, `OH`, `CH3`, `CH2`, `CH`, `COOH`, `COO-`, `NH2`, `NHAc`, `F`, `OPO3`,
`EPO3`, `C(=O)`, `C(=O)OPO3`, `C(=O)SCoA`, `C=<index>(E)`, `C=<index>(Z)`.
Parser implementations MAY accept aliases (for example `hydroxyl`) but SHOULD
normalize to canonical tokens above; unknown values SHOULD raise `ValueError`.

### Numeric Pathway Convention (Positional by Digit)

For pathway intermediates that need custom per-carbon chemistry, digit
markers MUST use the backbone index directly (single-letter body rule is
preserved), with definitions listed in ascending numeric order.

**Format**:
```
<SUGAR_CODE>[1=<mod>,2=<mod>,...]
```

**Examples**:
```
cK3[3C=CH3]                       pyruvate
c23[2C=C3(EPO3),3C=CH2]           phosphoenolpyruvate (PEP)
```

### Mixing Letters and Numbers

Letter codes and numeric footnotes can be combined:
```
AdLRDp  = 2-deoxy-glucose-6-phosphate (all common, no footnotes)
AdLRD6[6=sulfate]   = 2-deoxy-glucose-6-sulfate (deoxy=common, sulfate=rare)
```

### Rules

- Lowercase letters and digits replace `R` or `L` at stereocenter positions
- Lowercase letters and digits also replace `M` at terminal position (`c` for carboxyl, `p` for phosphate, `1` for a custom footnote)
- Uppercase `P` is valid only at stereocenters (phosphate-left); terminal `P` is invalid
- Each position is exactly one character; for multiple modifications on one carbon, use a numeric footnote with a compound definition (e.g., `1=amino-phosphate`)
- All digit markers must be defined in `[...]`; letters need no definition
- Footnote keys MAY be `n`, `nL`, `nR`, or `nC` (`n` in `1..9`)
- If only one side-qualified key is present, the other side defaults to `H`
- If both side-qualified keys are present, both values are used as provided
- At chiral stereocenters, substituent overrides MUST use `nL`/`nR`; plain `n=...`
  is invalid there (use `nC=...` only when defining carbon-state semantics)
- Plain `n=` is permitted only at non-chiral positions
- Within one bracket block, for a given backbone index `n`:
  - plain `n` and `nC` are mutually exclusive (at most one may appear)
  - `nL` and `nR` may co-occur
  - plain `n` or `nC` MUST NOT co-occur with `nL`/`nR` for the same index
  - combined carbon-state plus attachments MUST be expressed in a single `nC=` value
- In `nC=<state>(<attachment1>,...)`, parenthesized terms are substituents
  attached to carbon `n`
- In pathway convention, digits MUST match backbone indices and definitions MUST be listed in ascending order
- Letters take priority: if a modification has a letter code, prefer it over a number

## Validation Rules

### Monosaccharide Mode (Core)

1. **Core prefix (Haworth-compatible)**: Must match `^(A|MK|M[RL]K)`
2. **Core suffix/config pattern**: Must end in `[DL]M` or `[DL]<modifier>`
   - Exception: meso ketotriose family `MK<terminal-or-modifier>` (for example `MKM`, `MKp`, `MK1[...]`)
3. **Config slot rule**: `D`/`L` is the penultimate position in monosaccharide mode

### Pathway Mode (Non-Haworth)

4. **Pathway profile prefix**:
   - C2=`K` means 2-keto family, regardless of C1 token
   - C3=`K` means 3-keto family
   - no `K` at C2/C3 means aldose-derived family
5. **Pathway config-slot exception**: achiral pathway intermediates MAY replace
   the penultimate `D/L` slot with a modifier/digit (for example `cK3`, `c23`)
6. **D token restriction**: if present, `D` may only appear in penultimate position

### Shared Structural Rules

7. **Length** = number of carbons in the represented backbone
   - Minimum valid length is 3 (`len(sugar_code) >= 3`)
   - Codes of length 1 or 2 are invalid
   - For unbranched forms, backbone length equals total carbons
   - For branched pathway forms, extra carbons are represented via branch footnote terms
8. **Valid stereocenter characters**: `R`, `L`, letter codes (`d`, `a`, `n`, `p`, `P`, `f`, `c`), or digits (`1`-`9`)
9. All numeric markers must be defined; definitions MUST reference only digits
   present in the sugar code body
10. Side-qualified keys (`nL`, `nR`) are valid only for backbone indices present in the sugar code body; missing side defaults to `H`
11. Carbon-state keys (`nC`) are valid only for backbone indices present in the sugar code body
12. For any backbone index `n` in one footnote block: plain `n` and `nC` are
    mutually exclusive; `nL`/`nR` may co-occur with each other; plain `n`/`nC`
    must not co-occur with `nL`/`nR`
13. In all modes, any body digit MUST equal its backbone index position
14. At chiral stereocenters, plain `n=` is invalid; use `nL`/`nR` (or `nC` for
    carbon-state notation)
15. Haworth conversion must satisfy prefix/ring minimum carbon counts (see matrix below)

## Phase 0 Conversion Contract

The initial Haworth implementation MUST satisfy these constraints:

- Input: sugar code + ring type (`furanose` or `pyranose`) + anomeric (`alpha`/`beta`).
- Prefix support for Haworth-mode parsing: `A`, `MK`, `MRK`, `MLK`.
- Prefix support for Phase 0 Haworth conversion: `A`, `MK`.
- Output: schematic Haworth label specification (not a molecule graph).
- Ring closure MUST follow the matrix in this document.
- If requested ring type is impossible for the code length/prefix, conversion MUST fail with `ValueError`.
- Meso codes MAY parse as sugar codes (for example `MKM`, `MKp`), but they are
  non-cyclizable for Haworth conversion and MUST fail with ring-capacity `ValueError`.
- Pathway-profile extended forms (for example `pKLRDp`, `pRLRDp`, `cK3`, `c23`)
  MAY parse in non-Haworth mode and MUST be rejected by Haworth conversion unless
  they also satisfy core Haworth-compatible constraints.

## Pathway Coverage Profile (Non-Haworth)

To cover full glycolysis/CAC naming with one notation family, implementations MAY
support a pathway profile using numeric footnote markers.

- This profile is intended for open-chain metabolite encoding, not Haworth rendering.
- Parsers MUST accept dense digit-based overrides and preserve sorted definitions.
- Pathway-profile parsing MUST enforce backbone-index-matched digits and ascending definition order.
- Parsers SHOULD support side-qualified chiral footnotes (`nL`, `nR`) for explicit
  left/right substituent definition at custom stereocenters.
- Parsers SHOULD support carbon-state keys (`nC`) to disambiguate backbone carbon
  state from attached-group notation (for example `3C=CH2`).
- Branched compounds SHOULD be represented with explicit substituent groups on
  existing backbone indices (for example `3R=COO-`).
- Haworth conversion MUST reject pathway-profile cases that are non-cyclizable or
  not representable as `A`/`MK` cyclizations.

### Canonical Pathway Codebook

The following table defines canonical codes for glycolysis and CAC intermediates
under the pathway profile.

**Glycolysis**

| Metabolite | Canonical sugar code |
|-----------|----------------------|
| D-glucose | `ARLRDM` |
| D-glucose-6-phosphate | `ARLRDp` |
| D-fructose-6-phosphate | `MKLRDp` |
| D-fructose-1,6-bisphosphate | `pKLRDp` |
| Dihydroxyacetone | `MKM` |
| Dihydroxyacetone phosphate | `MKp` |
| D-glyceraldehyde-3-phosphate | `ADp` |
| 1,3-bisphosphoglycerate | `1Rp[1C=C(=O)OPO3]` |
| 3-phosphoglycerate | `cRp` |
| 2-phosphoglycerate | `cpM` |
| Phosphoenolpyruvate | `c23[2C=C3(EPO3),3C=CH2]` |
| Pyruvate | `cK3[3C=CH3]` |

**Citric Acid Cycle (CAC)**

| Metabolite | Canonical sugar code |
|-----------|----------------------|
| Citrate | `c23cc[2C=CH2,3L=OH,3R=COO-]` |
| cis-Aconitate | `c23cc[2C=C3(Z),3R=COO-]` |
| Isocitrate | `c23cc[2L=OH,2R=H,3C=COO-]` |
| alpha-Ketoglutarate | `cK34c[3C=CH2,4C=CH2]` |
| Succinyl-CoA | `c234[2C=CH2,3C=CH2,4C=C(=O)SCoA]` |
| Succinate | `c23c[2C=CH2,3C=CH2]` |
| Fumarate | `c23c[2C=C3(E)]` |
| Malate | `c23c[2L=OH,2R=H,3C=CH2]` |
| Oxaloacetate | `cK3c[3C=CH2]` |

Notes:
- This canonical table is required before Phase 0 is considered complete.
- Side-qualified groups in symmetric CAC intermediates (for example citrate-class
  forms) are attachment-bookkeeping notation, not a claim of true stereochemical
  chirality at that center.

## Conversion to Haworth Projection

### Algorithm

1. **Parse sugar code** -> prefix, stereocenters, config, terminal
2. **Determine ring type**: pyranose (6-membered) or furanose (5-membered), then
   verify the sugar has enough carbons for that prefix/ring closure
3. **Map stereocenters to substituents**:
   - `R` -> OH down, H up (Fischer right -> Haworth down)
   - `L` -> OH up, H down
   - Modifications replace OH with specified group
4. **Resolve series orientation**:
   - `D` -> DEXTER
   - `L` -> LAEVUS
   - meso trioses (for example `MKM`, `MKp`) are non-cyclizable in Haworth mode
5. **Apply anomeric configuration**:
   - D-alpha: anomeric OH down
   - D-beta: anomeric OH up
   - L-series: reversed
6. **Output HaworthSpec** with resolved text labels per position (no separate
   `config` field required at render stage)

### Required Conversion Errors

Implementations MUST raise clear `ValueError` messages for:

- Unsupported ring type string.
- Prefix/ring pair below minimum carbon count.
- Non-cyclizable trioses requested in Haworth mode.
- Undefined numeric footnotes.
- Numeric footnote definitions that do not match index markers present in the body.

### Haworth Ring Closure Matrix

| Prefix | Anomeric | Ring Type | Min Carbons | Closure |
|--------|----------|-----------|-------------|---------|
| `A` | C1 | furanose | 4 | C1-O-C4 |
| `A` | C1 | pyranose | 5 | C1-O-C5 |
| `MK` | C2 | furanose | 5 | C2-O-C5 |
| `MK` | C2 | pyranose | 6 | C2-O-C6 |

If a code does not meet the minimum carbons for the requested ring type (for example
triose `ADM`, `MKM`, or `MKp`), conversion must fail with a clear validation error.

### Example: alpha-D-Glucopyranose

**Sugar code**: `ARLRDM` + pyranose + alpha

```
C1_up: "H"       C1_down: "OH"     <- alpha: OH down
C2_up: "H"       C2_down: "OH"     <- R: OH down
C3_up: "OH"      C3_down: "H"      <- L: OH up
C4_up: "H"       C4_down: "OH"     <- R: OH down
C5_up: "CH2OH"   C5_down: "H"      <- D-series: CH2OH up
```

### Example: beta-D-2-Deoxyribofuranose

**Sugar code**: `AdRDM` + furanose + beta

```
C1_up: "OH"      C1_down: "H"      <- beta: OH up
C2_up: "H"       C2_down: "H"      <- d (deoxy): both H
C3_up: "H"       C3_down: "OH"     <- R -> OH down (D-series)
C4_up: "CH2OH"   C4_down: "H"      <- terminal CH2OH up
```

## Limitations

1. **Non-standard ring sizes**: Oxetose (4-membered) and septanose (7-membered)
   rings require manual specification
2. **Branched structure support is mode-limited**:
   - Pathway profile (non-Haworth): branched forms are supported through
     explicit side-qualified/carbon-state footnotes
   - Haworth conversion (Phase 0): branched/non-cyclizable pathway forms are
     rejected
3. **Multiple ring forms**: Pyranose vs furanose specified separately
4. **Anomeric position**: Alpha/beta is a parameter, not encoded in the sugar code
5. **Phase 0 scope**: specification targets sugar-code-to-Haworth conversion only;
   SMILES round-trip work is a separate future phase.

## References

- Original sugar code system: `sugarlib.py` (biology-problems repo)
- Vetted sugar codes: `sugar_codes.yaml` (biology-problems repo)
- Haworth projection layout: `packages/oasa/oasa/haworth.py`
