# Sugar code guide

This guide explains the sugar code strings used by OASA and listed in
[packages/oasa/oasa_data/sugar_codes.yaml](packages/oasa/oasa_data/sugar_codes.yaml).
It is based on parser behavior in
[packages/oasa/oasa/sugar_code.py](packages/oasa/oasa/sugar_code.py) and tests in
[tests/test_sugar_code.py](tests/test_sugar_code.py).

## What a sugar code is

A sugar code is a compact string that encodes:
- chain pattern and stereochemistry
- aldose or ketose family
- D/L configuration (when present)
- terminal group token
- optional footnote overrides

Examples:
- `ARLRDM` (D-glucose style aldohexose code)
- `MKLRDM` (D-fructose style ketohexose code)
- `ALLLDM` (D-talose style aldohexose code)
- `ARLLDc` (D-galacturonic acid style terminal carboxyl code)

## Core token meanings

Common uppercase tokens:
- `A`: aldehyde marker
- `K`: keto marker
- `R`: right-oriented stereocenter
- `L`: left-oriented stereocenter
- `D`: dexter config token (penultimate position)
- `M`: hydroxymethyl terminal token

Common lowercase modifier tokens:
- `d`: deoxy
- `a`: amino
- `n`: n-acetyl
- `p`: phosphate
- `P`: phosphate-left
- `f`: fluoro
- `c`: carboxyl

## Prefix interpretation

The parser normalizes prefixes into one of:
- `ALDO`
- `KETO`
- `3-KETO`

Detected forms include:
- `A...` -> `ALDO`
- `MK...` -> `KETO`
- `MRK...` or `MLK...` -> `3-KETO`
- some no-prefix forms are inferred by token placement

## Configuration and terminal

The penultimate token usually sets config:
- `D` -> `DEXTER`
- `L` -> `LAEVUS`

Some short forms can be `MESO` (see parser rules in
[packages/oasa/oasa/sugar_code.py](packages/oasa/oasa/sugar_code.py)).

The final token is the terminal token, often `M`, but it can be a modifier
token such as `c`.

## Digit markers and footnotes

Digit tokens in the body are placeholders that require footnote definitions.
Rules:
- digit value must match its position index in the body
- footnotes are attached as `[key=value,...]`
- key pattern is `n`, `nL`, `nR`, or `nC` where `n` is `1-9`
- footnotes must be in ascending index order

Examples:
- `A2LRDM[2R=CH3]` (single-side override, missing side auto-fills as `H`)
- `A2M[2L=COOH,2R=CH3]` (explicit side pair)
- `c23[2C=C3(EPO3),3C=CH2]` (carbon-state pathway style)

Validation rules:
- no nested `[]`
- parenthesis depth in footnote values must balance
- duplicate keys are rejected
- plain and side/carbon keys cannot be mixed at one index
- chiral positions cannot use plain `n=...`; use side-qualified keys or `nC`

## How to read `sugar_codes.yaml`

The YAML file is grouped by sugar families (for example `D-aldopentoses`,
`D-aldohexoses`, `D-ketoheptoses`). Each entry maps:
- sugar code -> human-readable sugar name

Example mapping:
- `ARLRDM: D-glucose`
- `MKLRDM: D-fructose`
- `ARLLDc: D-galacturonic acid` (if present in your local file set)

Use it as:
- a lookup table for code-to-name translation
- a curated corpus for renderer/smoke coverage
- a source for docs and UI labels

## Quick parsing examples

```text
ARLRDM
prefix: ALDO
config: DEXTER
terminal: M
```

```text
A2LRDM[2R=CH3]
prefix: ALDO
config: DEXTER
footnotes: 2R=CH3, 2L=H (auto-filled)
```

```text
c23[2C=C3(EPO3),3C=CH2]
prefix: ALDO
config: MESO
digit pathway with carbon-state footnotes
```

## Related files

- [packages/oasa/oasa/sugar_code.py](packages/oasa/oasa/sugar_code.py)
- [packages/oasa/oasa_data/sugar_codes.yaml](packages/oasa/oasa_data/sugar_codes.yaml)
- [tests/test_sugar_code.py](tests/test_sugar_code.py)
- [tests/test_haworth_spec.py](tests/test_haworth_spec.py)
