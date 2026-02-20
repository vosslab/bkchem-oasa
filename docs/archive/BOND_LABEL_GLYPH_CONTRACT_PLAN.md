# Bond-label glyph contract plan

## Title and objective

Objective: define and implement one universal, renderer-level bond-to-label contract so connectors attach to intended element glyphs deterministically, with fixed bond-length policy by bond style and tightly controlled exceptions.

Status: Phase 4 complete on 2026-02-11 after independent alignment gate closure; Phase 5 next (not started).

## Design philosophy

- One geometry truth: attachment legality and endpoint selection are defined in shared runtime geometry, never in caller or tool heuristics.
- Chemistry-first semantics: attachments target chemically selected elements and explicit attach sites, not incidental text position.
- Primitive realism with calibration: treat each target element as a glyph convex hull proxy via analytic primitives, and allow this only when calibrated against true glyph outlines within explicit error budgets.
- Measurable primitives: every analytic glyph primitive must expose one explicit center point and one explicit measurable area so alignment and legality checks can be computed precisely and consistently.
- Fixed defaults, explicit exceptions: bond lengths are policy-driven by style with tagged, auditable exceptions only.
- Direction lattice contract: bond directions must be constrained to canonical
  30-degree lattice angles (`30*n mod 360`; i.e. `0, 30, 60, ..., 330`)
  unless an explicit, documented exception is approved.
  This contract applies to generated/template geometry paths (Haworth and
  non-Haworth ring generation), not to BKChem GUI freehand draw-mode snapping
  options (`30/18/6/1` and `freestyle`).
- Connector authority: bond geometry is authoritative and labels adapt; labels do not relocate chemically meaningful endpoints.
- Drift prevention by evidence: visual acceptance must include external reference metrics, not only self-derived internal centroids.

## Scope and non-goals

Scope:
- Shared attachment contract in `packages/oasa/oasa/render_geometry.py`.
- Shared bond-length policy contract for bond styles used by OASA/BKChem render paths.
- Haworth as primary validation surface for current regressions.
- Minimal sentinel validation outside Haworth to prove this is a core contract, not a Haworth-only patch.
- Tooling boundary enforcement so `tools/archive_matrix_summary.py` consumes renderer APIs but does not implement geometry policy.

Non-goals:
- No per-sugar or per-label-text hacks (`if code == ...`, `if op_id contains ...`).
- No large font-engine rewrite for all Unicode glyphs.
- No full chemistry semantic expansion.
- No broad UI redesign.

## Current state summary

- Shared runtime endpoint authority now covers Haworth connector paths, including chain2 and hydroxyl branch connectors.
- Independent SVG-only measurement reports are generated from existing matrix outputs and now pass hard gate (`--fail-on-miss`).
- Matrix regeneration strict checks are green (`Strict-overlap failures: 0`) with known Haworth alignment blockers corrected.
- Phase 4 closure evidence includes two consecutive full `tests/test*.py` runs with no regressions.

## Architecture boundaries and ownership

Architecture boundaries:
- Core contract owner: `packages/oasa/oasa/render_geometry.py`.
- Haworth caller integration: `packages/oasa/oasa/haworth/renderer.py`.
- Public facade consistency: `packages/oasa/oasa/haworth_renderer.py`.
- Report tool boundary: `tools/archive_matrix_summary.py` (generation/report only).

Ownership:
- Coder A (core geometry): glyph attach-site primitives and endpoint resolution.
- Coder B (bond style policy): fixed bond lengths by style and exception policy.
- Coder C (validation): Haworth matrix checks, strict checks, minimal non-Haworth sentinels.
- Manager reviewer: gate decisions and documentation close-out.

## Phase plan (ordered, dependency-aware)

Current phase status:
- Phase 3 is complete.
- Phase 4 is complete with manager-defined alignment target checks and
  straightness/lattice gates passing (2026-02-11).
- Phase 5 is next and remains blocked until explicitly started.

### Phase 0: contract freeze and baseline

Deliverables:
- Freeze canonical attach contract vocabulary:
  - `attach_element`: chemical element selector (`C`, `O`, `N`, `S`, `P`, ...).
  - `attach_site`: geometric site selector (`core_center`, `stem_centerline`, `closed_center`).
- Freeze canonical bond-length policy vocabulary:
  - `bond_style`: single, double, triple, dashed_hbond, rounded_wedge, hashed_wedge, wavy.
  - `length_profile`: style-to-length ratio table relative to base single-bond length.
- Record baseline failing fixtures and expected visual outcomes (Ribose, Galactose, Gulose, Fucose, Rhamnose).

Done checks:
- Contract terms and baseline fixture list are documented and approved.
- No new geometry commits before contract freeze.

### Phase 1: glyph-attach primitive model

Deliverables:
- Implement glyph class model used by endpoint targeting:
  - `O/C/S`: oval-like closed forms.
  - `N/H`: rectangle-like forms.
  - `P`: special composite form (closed bowl + stem treatment).
- Define primitive measurement contract:
  - `primitive_center`: canonical center used for centerline alignment checks.
  - `primitive_area`: canonical closed area used for attach legality and overlap checks.
  - `boundary_projection(point, direction)`: deterministic boundary hit used by endpoint solver.
- Provide deterministic target primitives from labels using element-aware tokenization.
- Add explicit `P` handling rules so `P` cannot silently fall back to generic behavior.

Done checks:
- Attach primitives are produced by shared runtime code only.
- Target primitives are independent of Haworth-specific branching.
- Primitive center and area values are queryable in runtime and test utilities for direct numerical assertions.

### Phase 2: endpoint resolver unification

Deliverables:
- Route connector endpoint resolution through one shared resolver that consumes:
  - start point,
  - selected target primitive,
  - constraints (vertical lock, direction policy, retreat legality).
- Remove or block caller-side endpoint shortcuts that bypass resolver contract.
- Require strict validator to use the same primitive and endpoint legality semantics as runtime.

Done checks:
- Haworth endpoint logic no longer duplicates core geometry policy.
- Strict validator and runtime agree on legality outcomes for the same ops.

### Phase 3: fixed bond-length policy

Deliverables:
- Define fixed default lengths by bond style (relative to single bond base length):
  - double and triple shorter than single,
  - dashed hydrogen bond longer,
  - rounded wedge and hatch fixed.
- Add explicit exception policy with required justification tags:
  - `EXC_OXYGEN_AVOID_UP` (may lengthen),
  - `EXC_RING_INTERIOR_CLEARANCE` (may shorten),
  - no untagged exceptions.
- Ensure exceptions are local, auditable, and minimal.

Done checks:
- A central style-length table exists in runtime policy.
- Any non-default length used in runtime is tied to a documented exception tag.

### Phase 4: validation and stabilization

Deliverables:
- Haworth-first validation for known failure set.
- Minimal non-Haworth sentinel coverage (three contract tests only):
  - one `CH2OH` attach-to-`C`,
  - one `CH3` attach-to-`C`,
  - one `OH/HO` attach-to-`O`.
- Regenerate matrix via top-level renderer interface only.
- Add independent measurement tool
  `tools/measure_glyph_bond_alignment.py` that analyzes existing generated
  SVGs from `output_smoke/archive_matrix_previews/generated/*.svg` without
  calling `haworth_renderer.render_from_code(...)`, and reports per-label
  endpoint-to-target distances plus top misses.
- Independent measurement report includes bond-length distribution metrics
  (all lines, connector lines, non-connector lines) to detect style drift.

Done checks:
- Known Haworth failures are corrected without regressions in previously correct cases.
- Sentinel tests prove contract is shared beyond Haworth.
- Independent measurement tool reports alignment rate and miss inventory, and
  supports non-zero exit (`--fail-on-miss`) for gate enforcement.
- All manager-defined Phase 4 alignment targets pass exactly as specified.
- Ring-connected bond straightness contract is satisfied:
  any bond segment that directly connects to a Haworth ring must be straight.
- Off-ring branch angle contract is satisfied:
  bonds that connect to bonds off the ring follow
  canonical `30*n mod 360` angle rules.
- Non-Haworth ring bond angle contract is satisfied:
  non-Haworth ring bonds also follow canonical `30*n mod 360`.

Phase 4 passing checklist (required target fixtures):
- `ARDM` | `D-Erythrose` | `furanose` | `alpha`: check all three `OH` groups.
- `ARRDM` | `D-Ribose` | `furanose` | `beta`: check upward `CH2OH` group.
- `ARRDM` | `D-Ribose` | `pyranose` | `alpha`: check all downward `OH` groups.
- `ALLDM` | `D-Lyxose` | `furanose` | `beta`: check internal `OH` groups.
- `ALLDM` | `D-Lyxose` | `pyranose` | `alpha`: check internal `OH` groups.
- `ARRRDM` | `D-Allose` | `furanose` | `alpha`: check two-carbon up-left `OH` and `CH2OH`.
- `ARRRDM` | `D-Allose` | `pyranose` | `alpha`: check upward `CH2OH` group.
- `ARRLDM` | `D-Gulose` | `furanose` | `alpha`: check two-carbon down-left `OH` and `CH2OH`.
- `MKRDM` | `D-Ribulose` | `furanose` | `alpha`: check right-side `CH2OH` and `OH`; bonds must be straight.
- `ARRLLd` | `L-Rhamnose` | `pyranose` | `alpha`: check internal `CH3` group for straight bond, correct bond length, and `C` label-to-bond alignment.
- `ARLLDc` | `D-Galacturonic Acid` | `pyranose` | `alpha`: check up-left `COOH` group for straight bond, correct bond length, and `C` label-to-bond alignment.
- Global Phase 4 geometry checks:
  - Any bond that connects to a Haworth ring MUST be straight.
  - Any bond that connects to bonds off the ring MUST follow canonical
    `30*n mod 360` (`0, 30, 60, ..., 330`).
  - Non-Haworth ring bonds MUST follow canonical
    `30*n mod 360` (`0, 30, 60, ..., 330`).

Side goal (assigned to junior coder, independent execution):
- Add one standalone SVG checker mode (or tool) that runs multiple checks on a
  provided input SVG file and writes a report.
- Required report checks:
  1. number of bonds outside canonical lattice angles
     (`30*n mod 360`; `0, 30, 60, ..., 330`);
  2. glyph/glyph overlap count;
  3. bond/bond overlap count;
  4. bond/glyph overlap count;
  5. glyph-bond alignment count outside tolerance spec;
  6. Haworth base ring template detection and exclusion from checks.
- CLI requirement:
  - add boolean argparse flag `--exclude-haworth-base-ring` with default ON;
  - add paired opt-out flag (for example `--include-haworth-base-ring`) that
    disables exclusion.
- Independence requirement:
  - this side-goal checker must analyze input SVG geometry directly and run
    independently of generation-time rendering code paths.

### Phase 5: rollout and close-out

Deliverables:
- Merge plan status updates, closure notes, and changelog records.
- Archive or supersede stale guide sections once this contract becomes source-of-truth.
- Record residual issues as follow-up work, not hidden exceptions.

Done checks:
- Closure recommendation with explicit gate outcomes.
- Documentation reflects actual implementation state.

## Per-phase deliverables and done checks

- Phase 0:
  - Deliverables: contract terms + baseline fixtures.
  - Done: approved contract vocabulary and frozen baseline.
- Phase 1:
  - Deliverables: glyph primitive model and `P` special handling.
  - Done: runtime target model is shared and deterministic.
- Phase 2:
  - Deliverables: one endpoint resolver path and strict/runtime semantic parity.
  - Done: no caller-side bypasses remain active.
- Phase 3:
  - Deliverables: central bond-length policy + tagged exception mechanism.
  - Done: complete; untagged length deviations are disallowed.
- Phase 4:
  - Deliverables: Haworth regressions fixed + 3 non-Haworth sentinel proofs.
  - Done: complete; manager checklist targets and geometry gates are green.
- Phase 5:
  - Deliverables: close-out docs and status alignment.
  - Done: next; not complete yet.

## Acceptance criteria and gates

Unit gate:
- Shared attach-target tests and endpoint legality tests pass for all attach-site modes.
- Primitive-measurement tests pass for center and area invariants for `C`, `O`, `S`, `N`, `H`, and `P`.

Integration gate:
- `tools/archive_matrix_summary.py -r` succeeds using renderer-owned APIs only.
- `tools/measure_glyph_bond_alignment.py --fail-on-miss` runs on existing
  generated SVG outputs and exits zero only when no misses are detected.

Regression gate:
- Full `tests/test*.py` passes.
- Haworth targeted visuals no longer show C/H boundary misses in the baseline failure set.
- Phase 4 required target fixtures (manager checklist) pass and are recorded with
  per-target evidence.
- Straightness and lattice-angle rules pass:
  Haworth ring-connected bonds are straight, and off-ring/non-Haworth ring
  bonds comply with canonical `30*n mod 360`.

Release gate:
- Two consecutive full-suite green runs.
- No active geometry policy in `tools/archive_matrix_summary.py`.
- Any length exception in runtime maps to a documented exception tag.

## Test and verification strategy

Primary verification:
- Haworth matrix (because it currently exposes failures clearly).

Independent verification:
- Run `tools/measure_glyph_bond_alignment.py` against existing generated SVGs
  (no re-render in this tool), and persist JSON/TXT metric artifacts under
  `output_smoke/`.

Minimal non-Haworth verification:
- Add only three sentinel tests outside Haworth (contract smoke, not full expansion).

Verification evidence required per fix:
- Before/after rendered artifact path.
- Numeric attach-site check against externally defined visual target, including centerline offset and area-boundary hit metrics.
- Strict legality outcome for same case.

Failure semantics:
- Any visual regression in baseline fixtures blocks progression.
- Any untagged bond-length exception blocks progression.
- Any tool-level geometry heuristic blocks progression.
- Any independent measurement miss (or missing connector assignment) blocks
  Phase 4 closure.
- Any violation of straightness or 30-degree lattice-angle rules blocks
  Phase 4 closure.

## Migration and compatibility policy

Additive-first rollout:
- Introduce new attach-site and length-profile semantics with backward-compatible defaults.
- Migrate callers to shared contract before removing legacy aliases.

Compatibility promises:
- Existing API callers remain functional during migration.
- Top-level renderer interface (`code`, `ring_type`, `anomeric`) remains stable.

Deletion criteria:
- Remove legacy policy branches only after caller migration and green gates.
- Remove stale guide instructions that conflict with finalized contract.

Rollback strategy:
- If phase-level regressions occur, roll back to previous green runtime contract while preserving failing fixtures and diagnostic artifacts.

## Risk register and mitigations

- Risk: glyph primitive approximation is insufficient for some fonts.
  - Impact: High.
  - Trigger: attach drift across font backends.
  - Mitigation: keep primitive model deterministic and add fallback calibration constants per element class, not per sugar.
  - Owner: Coder A.

- Risk: `P` special handling introduces inconsistent behavior.
  - Impact: Medium.
  - Trigger: `P` labels fail strict legality or look detached.
  - Mitigation: isolate `P` model contract with dedicated tests before wider rollout.
  - Owner: Coder A.

- Risk: bond-length policy causes visual crowding in dense Haworth cases.
  - Impact: Medium.
  - Trigger: increased overlap failures after enforcing fixed lengths.
  - Mitigation: apply only tagged exceptions with narrow scope and explicit rationale.
  - Owner: Coder B.

- Risk: tool-level heuristics reappear.
  - Impact: High.
  - Trigger: attachment logic added to `archive_matrix_summary.py`.
  - Mitigation: CI grep gate for prohibited geometry policy patterns in tools.
  - Owner: Coder C.

- Risk: plan drift (tests pass, visuals still wrong).
  - Impact: High.
  - Trigger: self-referential metric passes with unresolved visual mismatch.
  - Mitigation: require one external visual-reference metric in acceptance evidence.
  - Owner: Manager reviewer.

## Rollout and release checklist

- [x] Contract vocabulary frozen and approved.
- [x] Glyph primitive model implemented (`O/C/S`, `N/H`, `P` special).
- [x] Shared endpoint resolver used by runtime and strict validator.
- [x] Fixed style-length table implemented and documented.
- [x] Exception tags implemented and audited.
- [x] Baseline Haworth failures corrected with before/after evidence.
- [x] Minimal non-Haworth sentinel tests passing.
- [x] Full suite passes twice consecutively.
- [x] Changelog and progress docs updated.
- [x] Independent glyph-bond alignment tool implemented and green
      (`tools/measure_glyph_bond_alignment.py --fail-on-miss`).
- [x] Phase 4 manager checklist targets pass (all 11 required fixtures above).

## Documentation close-out requirements

- Update `docs/CHANGELOG.md` at each phase closure with gate command outcomes.
- Update `refactor_progress.md` status when this plan transitions phases.
- Mark `docs/active_plans/CODER_GUIDE_FEB_10.md` as legacy guidance once this plan becomes active source-of-truth.
- If complete, archive this plan with closure evidence and link from `refactor_progress.md`.

## Open questions and decisions needed

1. Should `P` be modeled as one custom polygon/compound primitive now, or as a short-term rectangle fallback with explicit follow-up?
2. Should we implement true glyph outlines (lines/curves/polygons) now?
   - Recommendation: not in this phase. Start with deterministic analytic primitives per element class, then consider outline mode as a later optional accuracy phase.
3. What exact default length ratios should we lock for double, triple, dashed_hbond, rounded_wedge, and hashed_wedge?
4. Should exception tags be surfaced in debug artifacts by default, or only in strict/debug mode?
5. What Phase 4 closure threshold should independent alignment use:
   strict zero misses or a temporary bounded miss budget?
