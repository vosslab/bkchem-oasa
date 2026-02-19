# Phase B audit report

## Scope

This report closes Phase B of
[docs/archive/PURE_OASA_BACKEND_REFACTOR.md](docs/archive/PURE_OASA_BACKEND_REFACTOR.md):

- B1 option inventory and classification.
- B2 GUI manifest schema validation.
- B3 GTML retention decision.
- B4 CDML depiction audit before Phase C renderer swap.
- B5 CDML v2 decision.

## B1 option inventory

| Option | Current location | Formats | Default | Classification | Rationale |
|---|---|---|---|---|---|
| `scope=selected_molecule` | `packages/bkchem-app/bkchem/format_menus.yaml` + `format_loader` | Molfile, SMILES, InChI | exactly one selected molecule required | keep in BKChem GUI | This is user intent, not codec behavior. |
| `program_path` | `packages/bkchem-app/bkchem/format_menus.yaml` (`source: preference`) | InChI export | required preference value | keep in BKChem GUI | External binary location is host configuration, not molecular serialization policy. |
| `menu_capabilities` | `packages/bkchem-app/bkchem/format_menus.yaml` | all registry-routed formats | derived from registry when omitted | keep in BKChem GUI | Menu presence is UI policy. |
| CML/CML2 write path | `packages/oasa/oasa/codecs/cml.py`, `packages/oasa/oasa/codecs/cml2.py` | CML, CML2 | disabled | retire | Legacy export retired; import retained for recovery. |
| Coordinate orientation (+Y up canonical exchange) | OASA codecs + bridge path | Molfile and all registry codecs | no per-format Y flip | move to codec defaults | Orientation is core data contract, not a per-format UI toggle. |
| `invert_coords` hack | removed `packages/bkchem-app/bkchem/plugins/molfile.py` | legacy Molfile plugin | n/a | retire | Removed in Phase A; replaced by canonical coordinate boundary. |
| Per-plugin molecule selection dialogs | removed format plugins | legacy Molfile/SMILES/InChI plugins | n/a | retire | Replaced by shared `scope` handler in `format_loader`. |
| GTML export menu entry | `packages/bkchem-app/bkchem/plugins/gtml.py` | GTML | disabled in Phase B | retire | GTML is legacy import-only. |
| Crop toggle (`crop_svg`) | `packages/bkchem-app/bkchem/plugins/cairo_lowlevel.py`, `packages/bkchem-app/bkchem/plugins/ps_builtin.py` | legacy PDF/PNG/SVG/PS exporters | current paper property | keep in BKChem GUI (temporary) | Rendering plugins remain until Phase C swap. |
| Page size (`size_x`, `size_y`) | legacy render plugins | legacy PDF/PNG/SVG/PS/ODF exporters | current paper property | keep in BKChem GUI (temporary) | User-facing output size control remains until OASA renderers replace Tk path. |
| PNG scaling and DPI controls | `packages/bkchem-app/bkchem/plugins/png_cairo.py` | legacy PNG exporter | dialog-selected values | keep in BKChem GUI (temporary) | Human output resolution choice; revisit during Phase C renderer options migration. |
| PNG background color | `packages/bkchem-app/bkchem/plugins/png_cairo.py` | legacy PNG exporter | dialog-selected | keep in BKChem GUI (temporary) | User-facing visual output option; migrate in Phase C. |

### Decision record

- Keep `scope=selected_molecule` in GUI because it captures user selection intent.
- Keep InChI `program_path` in GUI preferences because it is environment configuration.
- Keep `menu_capabilities` in GUI manifest because it is menu policy, not codec logic.
- Retire CML/CML2 export permanently; import remains for legacy recovery.
- Move coordinate orientation to backend default contract (+Y up), with no per-format toggle.
- Retire `invert_coords`; this is already complete from Phase A.
- Retire per-plugin selection dialogs; shared scope logic already replaced them.
- Retire GTML export path; GTML is import-only in Phase B.
- Keep crop/page-size/PNG rendering controls in BKChem only until Phase C replaces Tk render plugins.

### Deprecation plan

- Removed now: `invert_coords`, CML/CML2 export, per-plugin selection dialogs, GTML export entry.
- Phase C migration target: crop/page-size/PNG options move from Tk plugin dialogs to OASA render APIs, preserving user-visible controls where still valuable.

## B2 GUI manifest schema validation

Validation is strict and test-backed:

- unknown top-level keys fail.
- unknown format keys fail.
- unknown gui option keys fail.
- unsupported `menu_capabilities`, `scope`, and `source` values fail.
- every codec in the manifest must be present in `get_registry_snapshot()`.

## B3 GTML retention decision

Decision: retain GTML as import-only for legacy file recovery.

Implementation:

- `packages/bkchem-app/bkchem/plugins/gtml.py` now sets `exporter = None`.
- GTML remains available in import paths, including HTTP import hooks.

Documented data-loss exceptions for GTML -> CDML conversion through the OASA molecule codec path:

- reaction graph semantics (reactant/product grouping, arrows, plus signs) are not represented in OASA CDML molecule codec output.
- GTML placement heuristics are not preserved as explicit CDML depiction metadata.
- non-molecule GTML graph metadata is not round-tripped through OASA molecule CDML codec.

## B4 CDML depiction audit

### Depiction fields currently stored in OASA CDML molecule codec

- atom coordinates (`x`, `y`, optional `z`).
- atom chemistry attributes (`name`, `charge`, `multiplicity`, `valency`, `free_sites`).
- bond `type` and `order`.
- bond depiction attributes: `line_width`, `bond_width`, `wedge_width`, `double_ratio`, `center`, `auto_sign`, `equithick`, `simple_double`, `color`, `wavy_style`.
- unknown CDML attributes are preserved on read/write when present.

### Gaps before Phase C renderer swap

- no explicit `<standard>` style profile handling in OASA CDML molecule codec path.
- no explicit atom-label placement offsets or label-direction metadata in OASA CDML molecule codec path.
- no explicit z-order/layer depiction metadata in OASA CDML molecule codec path.
- aromatic depiction policy is still partly renderer-default driven and must be pinned for WYSIWYG parity.

These gaps are tracked for Phase C in `docs/TODO_CODE.md`.

## B5 CDML v2 decision

Decision: stay on current CDML version for now.

Reasoning:

- identified depiction gaps can be addressed with additive optional metadata.
- no Phase B evidence requires changing semantics of existing fields or introducing new required fields.

Escalation rule:

- introduce CDML v2 only if Phase C WYSIWYG closure requires breaking semantic changes or new mandatory depiction fields.
