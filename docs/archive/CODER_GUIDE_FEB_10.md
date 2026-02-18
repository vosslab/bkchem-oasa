# Haworth Coder Guide (Feb 10)

Status: Legacy guidance as of 2026-02-11.
Superseded by: [docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md](docs/active_plans/BOND_LABEL_GLYPH_CONTRACT_PLAN.md)

## Objective
Deliver a universal, no-hack fix for Haworth connector-to-label attachment quality, with strict overlap enforcement and clear visual parity to references.

## Design Philosophy
- Prefer structural correctness over cosmetic tuning.
- Use one geometry authority for attachment semantics, then layer layout policy on top.
- Treat connectors as chemically authoritative and labels as adaptive.
- Make failures explicit and measurable; do not hide defects behind permissive overlap carve-outs.
- Optimize for generality: one rule should fix families of sugars, not single examples.

## Architecture Enforcement (Required)
- The renderer interface must accept sugar-code inputs directly at a stable
  top-level API: `code`, `ring_type`, `anomeric` (for example
  `ALRRDM`, `furanose`, `alpha`).
- Tools must consume that top-level API and must not re-implement renderer
  policy in tool code.
- Attachment-target policy (for example chain-like vs hydroxyl targeting) must
  live in runtime renderer modules only, not duplicated in tools.
- Strict validation must use shared renderer/geometry policy, not tool-local
  op-id heuristics.

### Explicitly Not Allowed In Tools
- Matching `op_id` substrings (for example `\"_chain2_\"`) to choose attach behavior.
- Re-deriving chain-like detection from ad hoc text cleanup in tool code.
- Divergent strict-check targeting rules that are not imported from runtime.

## Scope
- Runtime implementation files:
  - `/Users/vosslab/nsh/bkchem/packages/oasa/oasa/haworth/renderer.py`
  - `/Users/vosslab/nsh/bkchem/packages/oasa/oasa/render_geometry.py`
- Matrix validation tool:
  - `/Users/vosslab/nsh/bkchem/tools/archive_matrix_summary.py`
- Tests to update only after runtime behavior is correct:
  - `/Users/vosslab/nsh/bkchem/tests/test_haworth_renderer.py`
  - `/Users/vosslab/nsh/bkchem/tests/smoke/test_haworth_renderer_smoke.py`
  - `/Users/vosslab/nsh/bkchem/tests/test_attach_targets.py`

## Non-Negotiable Rules
- No sugar-specific hacks (`if code == ...`).
- No global constant tuning as the primary fix strategy.
- Bond geometry is authoritative; labels adapt to bond endpoints.
- Keep methyl readable as `CH<sub>3</sub>`.
- Keep strict overlap checks meaningful; do not relax them to pass bad visuals.

## Root Cause: Why CH<sub>2</sub>OH Misses C
Connector endpoints are solved against estimated attach targets, not true glyph outlines. For long labels (for example `CH<sub>2</sub>OH`), slight span estimation error can place endpoints into the C/H gap while still being mathematically inside a broad token box.

Implications:
- "Inside target" is necessary but not sufficient.
- Visual correctness requires carbon-centerline alignment, not only interior inclusion.

## Target Cases And Expected Visual Outcomes

### Case A: Ribose C4-up connector (major)
- Files:
  - `/Users/vosslab/nsh/bkchem/output_smoke/archive_matrix_previews/generated/ARRDM_furanose_alpha.svg`
  - `/Users/vosslab/nsh/bkchem/output_smoke/archive_matrix_previews/generated/ARRDM_furanose_beta.svg`
- Ops:
  - Connector: `C4_up_connector`
  - Label: `C4_up_label` (`CH<sub>2</sub>OH`)
- Current problem:
  - Connector can visually hit between C and H.
- Expected visual:
  - Connector remains vertical and lands on carbon, not C/H boundary.

### Case B: Galactose/Gulose furanose two-carbon tail (major)
- Files:
  - `/Users/vosslab/nsh/bkchem/output_smoke/archive_matrix_previews/generated/ARLLDM_furanose_alpha.svg`
  - `/Users/vosslab/nsh/bkchem/output_smoke/archive_matrix_previews/generated/ARRLDM_furanose_alpha.svg`
- Ops:
  - Chain2 connector: `C4_down_chain2_connector`
  - Chain2 label: `C4_down_chain2_label`
  - Branch mate: `C4_down_chain1_oh_connector`, `C4_down_chain1_oh_label`
- Current problem:
  - Branch/label geometry still looks off and not consistently carbon-attached.
- Expected visual:
  - Fixed branch geometry, chain2 endpoint on carbon target, no branch-label artifacts.

### Case C: Fucose/Rhamnose internal methyl readability (high)
- Files:
  - `/Users/vosslab/nsh/bkchem/output_smoke/archive_matrix_previews/generated/ALRRLd_pyranose_alpha.svg`
  - `/Users/vosslab/nsh/bkchem/output_smoke/archive_matrix_previews/generated/ARRLLd_pyranose_alpha.svg`
- Current problem:
  - Methyl can crowd oxygen/ring bonds.
- Expected visual:
  - `CH<sub>3</sub>` remains readable and non-overlapping.

### Case D: Strict overlap gate fidelity (major)
- Tool:
  - `/Users/vosslab/nsh/bkchem/tools/archive_matrix_summary.py -r`
- Current problem:
  - Some visually bad cases can pass due to permissive allowed regions.
- Expected behavior:
  - Strict mode fails if connector paint enters label interior outside intended attach micro-region.

### Case E: Matrix output policy (must keep)
- Outputs:
  - `/Users/vosslab/nsh/bkchem/output_smoke/archive_matrix_summary.html`
  - `/Users/vosslab/nsh/bkchem/output_smoke/l-sugar_matrix.html`
- Policy:
  - Referenced L sugars (L-Fucose/L-Rhamnose) remain in archive summary.
  - L-sugar page is for no-reference L sugars only.

## Two-Carbon Direction Families (Applies To Alpha And Beta)

### Down Two-Carbon Chains
- `ARRLDM | D-Gulose | furanose`
- `ALRLDM | D-Idose | furanose`
- `ARLLDM | D-Galactose | furanose`
- `ALLLDM | D-Talose | furanose`
- `ARRLLM | L-Mannose | furanose`
- `ALRLLM | L-Glucose | furanose`
- `ARLLLM | L-Altrose | furanose`
- `ALLLLM | L-Allose | furanose`

### Up Two-Carbon Chains
- `ALLRDM | D-Mannose | furanose`
- `ARLRDM | D-Glucose | furanose`
- `ALRRDM | D-Altrose | furanose`
- `ARRRDM | D-Allose | furanose`
- `ALLRLM | L-Gulose | furanose`
- `ARLRLM | L-Idose | furanose`
- `ALRRLM | L-Galactose | furanose`
- `ARRRLM | L-Talose | furanose`

## Pass/Fail Rubric (Measured)

### A. Ribose pass criteria
- `abs(C4_up_connector.x2 - C4_up_connector.x1) <= 0.05`
- `abs(endpoint_x - carbon_target_center_x) <= 0.20`
- Endpoint inside carbon target with interior margin:
  - `m = max(0.05, 0.04 * font_size)`
  - `x in [x1 + m, x2 - m]`
- Fail if endpoint visually lands between C and H.

### B. Galactose/Gulose pass criteria
- `C4_down_chain2_connector` endpoint lies inside chain2 carbon attach target.
- No runtime `No legal chain2 label placement...` errors.
- No visible connector-through-label overlap outside attach region.

### C. Methyl pass criteria
- Label text is `CH<sub>3</sub>` (not plain `CH3`).
- No visible overlap with oxygen glyph or adjacent ring edge paint.

### D. Strict gate pass criteria
- Real matrix regeneration passes strict checks.
- Induced-overlap fixture fails with non-zero exit and clear op IDs.

### E. Matrix policy pass criteria
- L-Fucose/L-Rhamnose appear in `archive_matrix_summary.html` with references.
- `l-sugar_matrix.html` contains only no-reference L-sugar rows.

## Implementation Order
1. Fix runtime geometry for Case A and Case B only.
2. Re-run target tests and strict matrix generation.
3. Validate Case C readability and Case E policy.
4. Update tests/docs only after runtime behavior is stable.

## Required Validation Commands
```bash
source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test_haworth_renderer.py
source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/smoke/test_haworth_renderer_smoke.py
source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 -m pytest -q tests/test*.py
source source_me.sh && /opt/homebrew/opt/python@3.12/bin/python3.12 tools/archive_matrix_summary.py -r
```

## Report Template (Required)
For each case A-E, report:
- `PASS` or `FAIL`
- measured values (where applicable)
- one before/after image path
- one-sentence explanation of what changed

Minimum images:
- `ARRDM_furanose_alpha.svg`
- `ARLLDM_furanose_alpha.svg`
- `ARRLDM_furanose_alpha.svg`
- `ALRRLd_pyranose_alpha.svg`
