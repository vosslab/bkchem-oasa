# Historical evidence: BKChem Qt completion plan

## Status

This file is a historical evidence index, not an active implementation plan.
The persistent-authority milestones, work packages, completion claims, and Qt
document-ownership instructions formerly here are superseded. Git history
retains their original detail.

The active authority plan is
`docs/active_plans/active/cdml_backend_authority_migration_2026-07-27.md`.
That path remains code rather than a Markdown link until the new plan is
tracked. It governs every persistent change: OASA owns the complete CDML
document, and Qt projects backend canonical CDML without re-merging content.

## Evidence retained

- The PySide6 package, session/tab lifecycle, scene teardown, item rendering,
  modes, workers, chemistry bridge, imports, packaging, and focused test work
  remain useful implementation evidence.
- Current persistent ownership and transaction rules are in
  [CDML_BACKEND_TO_FRONTEND_CONTRACT.md](../../CDML_BACKEND_TO_FRONTEND_CONTRACT.md).
- Current Qt lifecycle and projection rules are in
  [QT_CONTRACT.md](../../QT_CONTRACT.md).
- Molecule coordinate-generation evidence remains in
  [OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md](../../OASA_MOLECULE_COORDINATE_GENERATION_METHODS.md).

## Use of this record

Use the historical evidence to understand existing code or validate a migration
slice. Take new implementation tasks, authority decisions, acceptance gates,
and persistence claims from the active backend-authority plan and contracts.
