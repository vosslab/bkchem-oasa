# Todo code

- Implement the PubChem lookup work in
  [PUBCHEM_API_PLAN.md](active_plans/PUBCHEM_API_PLAN.md).
- I would like to see the undo functions in BKChem stick to the CDML contract.
  Basically UNDO becomes a CDML becomes a CDML history. When you make a change in
  BKChem the old version is saved as temporary CDML file. We could keep a history
  of N=20 of these backward files. Any changes to interface that do not affect the
  molecule (i.e. no CDML change) cannot be UNDOne. Am I thinking of this correctly?
- Expand `packages/oasa/oasa_cli.py` beyond Haworth once the CLI surface is finalized
  (format conversion, batch reference output generation).
- Remove the legacy PostScript builtin exporter now that Cairo is required.
- Add a hash-based verification layer for newly generated CDML files, including
  a stable canonicalization step before digest calculation.
- Add OASA CDML depiction metadata support needed for Phase C WYSIWYG parity:
  `<standard>` profile fields, explicit label-placement metadata, and stable
  aromatic depiction policy controls.
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
    - [SUPPORTED_FORMATS.md](SUPPORTED_FORMATS.md) to list new formats.
- Extend the direct-glycosidic disaccharide Haworth planner into a document
  coordinator for polysaccharides, attachment-aware substituents, and frontend
  undo delivery. The current pure OASA slice deliberately supports only two
  vertex-disjoint 5/6-member C/O rings and one direct oxygen bridge (see
  [HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  Phase 6b).
- Haworth text collision detection with bounding box analysis
  (see [HAWORTH_IMPLEMENTATION_PLAN_attempt2.md](archive/HAWORTH_IMPLEMENTATION_PLAN_attempt2.md)
  Phase 6b).
