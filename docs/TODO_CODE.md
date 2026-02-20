# Todo code

- Mirror OASA modernization for BKChem (pyflakes cleanup and globals refactors).
- Expand `packages/oasa/oasa_cli.py` beyond Haworth once the CLI surface is finalized
  (format conversion, batch reference output generation).
- Decide whether to remove the legacy PostScript builtin exporter once Cairo is
  required.
- Add a hash-based verification layer for newly generated CDML files, including
  a stable canonicalization step before digest calculation.
- Add OASA CDML depiction metadata support needed for Phase C WYSIWYG parity:
  `<standard>` profile fields, explicit label-placement metadata, and stable
  aromatic depiction policy controls.
- Reintroduce ODF export only as an OASA codec/renderer (no BKChem plugin
  path), or formally retire ODF if there is no downstream requirement.
- Define GTML import-loss mitigation for reaction semantics in CDML/OASA path:
  preserve reactant/product grouping and arrow/plus objects when converting
  legacy GTML content to CDML-backed workflows.
- Clean up `packages/oasa/oasa/graph/graph.py` dead algorithm variants. The
  file contains multiple generations of the same graph operations kept as
  `_old` / `_oldest` suffixed methods (e.g., `get_all_cycles_e`,
  `get_all_cycles_e_old`, `get_all_cycles_e_oldest`) plus commented-out
  methods. Identify the current callers, delete the unused variants, and
  remove commented-out code. Likely ~200-300 lines of dead code.
- Evaluate optional RDKit/Open Babel integration for expanded import/export
  formats.
  - Target formats: SDF/SD, MOL2, PDB, CIF.
  - Coverage notes:
    - RDKit: SDF/SD, MOL2, PDB; CIF support is limited.
    - Open Babel: SDF/SD, MOL2, PDB, CIF (broader format coverage).
  - Candidate entry points:
    - `packages/bkchem-app/bkchem/oasa_bridge.py` for conversion hooks.
    - `packages/bkchem-app/bkchem/format_loader.py` and
      `packages/bkchem-app/bkchem/format_menus.yaml` for BKChem format wiring.
    - [docs/SUPPORTED_FORMATS.md](docs/SUPPORTED_FORMATS.md) to list new formats.
- Multi-ring Haworth layout coordinator for disaccharides/polysaccharides
  (see [docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  Phase 6b).
- Haworth text collision detection with bounding box analysis
  (see [docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](docs/archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  Phase 6b).
