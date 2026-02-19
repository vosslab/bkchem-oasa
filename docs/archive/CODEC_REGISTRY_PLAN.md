# Codec registry plan

## Objective
- Provide a single, shared registry for format codecs (SMILES, InChI, molfile,
  CDML) so BKChem and OASA use one canonical lookup path.
- Keep format-specific parsing and serialization in OASA modules, while the
  registry standardizes discovery, aliases, extensions, and capability checks.

## Scope
- In scope: registry API, default codec registrations, and usage in CLI tools
  and BKChem import/export paths.
- Out of scope: new format implementations, GUI plugin UX changes, or new
  external dependencies.

## Guiding rules
- The registry stores metadata and callable adapters only.
- The registry does not own parsing logic; OASA modules remain the source.
- Keep behavior deterministic: stable names, aliases, and extension mapping.
- Prefer explicit configuration (no environment variables).

## Current state
- Registry implemented in `packages/oasa/oasa/codec_registry.py` with default
  registrations for SMILES, InChI, molfile, and CDML.
- CLI conversion in `packages/oasa/chemical_convert.py` uses the registry.
- CDML writer now provides text/file helpers in
  `packages/oasa/oasa/cdml_writer.py`.
- Unit coverage exists in `tests/test_codec_registry.py`.

## Phase 0: Inventory and policy
- Inventory codec entry points in OASA and BKChem.
- Define canonical names, aliases, and extensions.
- Decide which codecs must support both text and file IO.

Deliverable:
- This plan updated with a definitive codec table.

## Phase 1: Registry API baseline (DONE)
- Provide a `Codec` container and registry helpers:
  - `register_codec`, `register_alias`, `get_codec`, `get_codec_by_extension`.
- Register default codecs and aliases.
- Add unit tests for registry behavior.

## Phase 2: OASA integration
- Route OASA CLI conversion through the registry (DONE).
- Provide a small `list_codecs()` call for tooling and tests (DONE).
- Ensure CDML text/file IO exists for registry usage (DONE).

## Phase 3: BKChem integration (DONE)
- Route BKChem import/export bridges through the registry:
  - `packages/bkchem-app/bkchem/oasa_bridge.py` becomes the adapter that calls the
    registry instead of direct module calls.
- Update BKChem format plugins to use the bridge API only.
- Keep plugin menu names and extensions unchanged for users.

## Phase 4: Plugin contract cleanup (DONE)
- Document the registry-backed contract in
  [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md).
- Ensure plugin export paths use codec capabilities for validation.

## Phase 5: Tests and drift prevention (DONE)
- Add tests that:
  - Assert the registry returns the same codec for names and aliases.
  - Assert extension mapping is stable.
  - Assert BKChem import/export uses the registry (mocked unit tests).

## Acceptance criteria
- All BKChem and OASA format conversions go through the registry.
- Default codecs are discoverable by name, alias, and extension.
- Removing a legacy codec requires a registry update (no hidden imports).

## Related documents
- [docs/RENDER_BACKEND_UNIFICATION.md](docs/RENDER_BACKEND_UNIFICATION.md):
  no overlap, but rendering parity depends on shared IO.
- [docs/ROUNDED_WEDGES_PLAN.md](docs/ROUNDED_WEDGES_PLAN.md): registry does not
  affect wedge geometry, but stable CDML IO supports tests.
- [docs/HAWORTH_IMPLEMENTATION_PLAN.md](docs/HAWORTH_IMPLEMENTATION_PLAN.md):
  Haworth CLI or batch output should use registry-backed CDML/SMILES IO.
- [docs/BKCHEM_FORMAT_SPEC.md](docs/BKCHEM_FORMAT_SPEC.md): codec registry must
  preserve CDML rules and namespaces.
- [docs/BOND_BACKEND_ALIGNMENT_PLAN.md](docs/BOND_BACKEND_ALIGNMENT_PLAN.md):
  registry integration should not bypass bond IO normalization.
- [docs/CDML_ARCHITECTURE_PLAN.md](docs/CDML_ARCHITECTURE_PLAN.md): CDML IO
  remains OASA-owned; registry is the discovery layer.
- [docs/CUSTOM_PLUGINS.md](docs/CUSTOM_PLUGINS.md): update once BKChem plugins
  route through the registry.
- [docs/LICENSE_MIGRATION.md](docs/LICENSE_MIGRATION.md): new registry modules
  require SPDX headers (LGPL-3.0-or-later).
- [docs/TODO_CODE.md](docs/TODO_CODE.md): registry work reduces duplication
  before adding new external codecs.
