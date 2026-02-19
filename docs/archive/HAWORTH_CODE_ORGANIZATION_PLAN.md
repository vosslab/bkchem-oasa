Plan to implement

Plan: Move Haworth modules to subpackage + YAML sugar name integration

Context

packages/oasa/oasa/haworth_renderer.py is 1,381 lines -- too large for a single file. It mixes pure geometry, text layout,
hydroxyl optimization, and rendering logic. Additionally, three Haworth-related modules (haworth.py, haworth_spec.py,
haworth_renderer.py) are scattered in the flat oasa/ directory alongside 30+ unrelated modules. Moving them into a dedicated
oasa/haworth/ subpackage improves organization and makes the split natural.

Separately, sugar names are hardcoded in tests/fixtures/neurotiker_archive_mapping.py but
packages/oasa/oasa_data/sugar_codes.yaml is the intended single source of truth.

Part 1: Create oasa/haworth/ subpackage

Target directory structure

packages/oasa/oasa/haworth/
__init__.py          # Current haworth.py contents (ring templates, layout helpers)
spec.py              # From haworth_spec.py (unchanged, just moved)
renderer.py          # Core render() + op builders (~580 lines)
renderer_config.py   # Constants (~115 lines)
renderer_geometry.py # Pure geometry helpers (~200 lines)
renderer_text.py     # Text formatting/positioning (~180 lines)
renderer_layout.py   # Hydroxyl layout optimizer (~300 lines)

Backward compatibility shims

Six import paths are used across the codebase and must keep working:
| Pattern | Used in | Solution |
| --- | --- | --- |
| from oasa import haworth | 3 files | Works automatically -- haworth/ package replaces haworth.py |
| import oasa.haworth | 2 files | Same -- package import |
| oasa.haworth._ring_template etc. | internal | Same -- functions in __init__.py |
| import oasa.haworth_renderer | 5 files | Keep thin shim at oasa/haworth_renderer.py |
| import oasa.haworth_spec | 6 files | Keep thin shim at oasa/haworth_spec.py |
| from .haworth_spec import HaworthSpec | 1 file | Works via shim |
Shim files (kept at old paths, ~5 lines each):

packages/oasa/oasa/haworth_renderer.py:
"""Backward-compat shim -- real code lives in oasa.haworth.renderer."""
from .haworth.renderer import *  # noqa: F401,F403
from .haworth.renderer import render, carbon_slot_map

packages/oasa/oasa/haworth_spec.py:
"""Backward-compat shim -- real code lives in oasa.haworth.spec."""
from .haworth.spec import *  # noqa: F401,F403

Module contents after split

haworth/__init__.py -- current packages/oasa/oasa/haworth.py contents (525 lines, unchanged logic)
, Ring template functions, front-edge tagging, substituent placement
, _ring_template(), PYRANOSE_O_INDEX, FURANOSE_O_INDEX, etc.

haworth/spec.py -- current packages/oasa/oasa/haworth_spec.py contents (328 lines, unchanged logic)
, HaworthSpec dataclass, generate() function
, Internal import path changes: from . import haworth becomes relative to package

haworth/renderer_config.py (~115 lines) -- extracted constants
, PYRANOSE_SLOTS, FURANOSE_SLOTS, slot indices, RING_SLOT_SEQUENCE
, Slot label configs, RING_RENDER_CONFIG
, Layout tuning: HYDROXYL_*, INTERNAL_PAIR_*, FURANOSE_TOP_*
, Validation: VALID_DIRECTIONS, VALID_ANCHORS, REQUIRED_SIMPLE_JOB_KEYS
, Imports: from . import (package __init__ for PYRANOSE_O_INDEX, FURANOSE_O_INDEX)

haworth/renderer_geometry.py (~200 lines) -- pure computational geometry
, normalize_vector(), edge_polygon()
, intersection_area(), point_in_box(), rect_corners()
, point_in_polygon(), segments_intersect(), box_overlaps_polygon()
, Imports: math only -- no Haworth dependencies
, Functions drop leading underscore (become module-public)

haworth/renderer_text.py (~180 lines) -- text formatting and positioning
, Text formatting: chain_labels(), is_chain_like_label(), format_label_text(), format_chain_label_text(),
apply_subscript_markup()
, Text positioning: anchor_x_offset(), leading_carbon_anchor_offset(), trailing_carbon_anchor_offset(),
hydroxyl_oxygen_radius(), leading_carbon_center(), hydroxyl_oxygen_center(), visible_text_length()
, Imports: re, constants from renderer_config

haworth/renderer_layout.py (~300 lines) -- hydroxyl layout optimizer
, Validation: validate_simple_job()
, Two-pass optimizer: resolve_hydroxyl_layout_jobs()
, Job classification: job_is_hydroxyl(), job_is_internal_hydroxyl(), job_can_flip_internal_anchor()
, Internal pair resolution: best_equal_internal_hydroxyl_length(), hydroxyl_candidate_jobs(), job_end_point(),
internal_pair_overlap_area(), internal_pair_horizontal_gap(), resolve_internal_hydroxyl_pair_overlap()
, Penalty scoring: job_text_bbox(), text_bbox(), overlap_penalty(), hydroxyl_job_penalty()
, Imports: renderer_config, renderer_geometry, renderer_text

haworth/renderer.py (~580 lines) -- core rendering + op builders
, Public API: render(), carbon_slot_map() -- unchanged signatures
, Internal: _ring_slot_sequence(), _ring_render_config(), _ring_carbons()
, Op builders: _add_simple_label_ops(), _add_chain_ops(), _add_furanose_two_carbon_tail_ops(), _baseline_shift(),
_add_gradient_edge_ops()
, Imports from sibling modules via relative imports:
from . import renderer_geometry as _geom
from . import renderer_text as _text
from . import renderer_layout as _layout
from .renderer_config import OXYGEN_COLOR, RING_RENDER_CONFIG, ...
from .. import render_ops
from .spec import HaworthSpec

Dependency graph (acyclic)

haworth/__init__.py  (ring templates -- leaf)
|
renderer_config  (imports __init__ for O_INDEX constants)
|
+----+----+
|         |
geometry  text (uses config constants)
|         |
+----+----+
|
layout  (uses config + geometry + text)
|
renderer (uses all above + render_ops + spec)

init.py update

In packages/oasa/oasa/__init__.py:
, Change from . import haworth -- already works (package replaces module)
, Keep from . import haworth_spec and from . import haworth_renderer -- these import the shim files
, Add new submodule imports to _EXPORTED_MODULES if desired (optional, since internal)

Part 2: YAML sugar name integration

New file: packages/oasa/oasa/sugar_code_names.py (~50 lines)

, Follows the same data-loading pattern as packages/oasa/oasa/isotope_database.py: os.path.join(os.path.dirname(__file__),
"..", "oasa_data", "sugar_codes.yaml")
, Loads packages/oasa/oasa_data/sugar_codes.yaml once, caches in module-level dict
, Flattens family-grouped YAML into flat {code: name} dict
, Provides: get_sugar_name(code: str) -> str | None and all_sugar_names() -> dict[str, str]
, Applies str.title() to names so YAML lowercase ("D-glucose") becomes display case ("D-Glucose")
, Uses yaml.safe_load() (pyyaml is already in pip_requirements.txt)

Update: tests/fixtures/neurotiker_archive_mapping.py

, Remove hardcoded "name" keys from NEUROTIKER_ARCHIVE_MAP entries
, Flatten structure from {"name": ..., "ring_forms": {...}} to just {(ring_type, anomeric): filename}
, Update all_mappable_entries() to call sugar_code_names.get_sugar_name(code) for the name
, 3 codes not in YAML (ALRRLd, ARRLLd, ARLLDc) get a small local _SPECIAL_NAMES dict
, Add oasa package to sys.path for import (following existing pattern in tools/archive_matrix_summary.py lines 58-66)

No changes needed to consumers

, tools/archive_matrix_summary.py -- calls all_mappable_entries(), same 5-tuple interface
, tests/smoke/test_haworth_renderer_smoke.py -- same import unchanged

Implementation order

1. Create packages/oasa/oasa/haworth/ directory

2. Move haworth.py contents to haworth/__init__.py (use git mv + adjust)

3. Move haworth_spec.py contents to haworth/spec.py, fix internal imports

4. Create haworth/renderer_config.py -- extract constants

5. Create haworth/renderer_geometry.py -- extract geometry functions

6. Create haworth/renderer_text.py -- extract text functions

7. Create haworth/renderer_layout.py -- extract layout functions

8. Create haworth/renderer.py -- refactored core renderer with imports from new modules

9. Replace oasa/haworth_renderer.py and oasa/haworth_spec.py with backward-compat shims

10. Update oasa/__init__.py if needed

11. Checkpoint: Run tests to verify split

12. Create oasa/sugar_code_names.py -- YAML loader

13. Update tests/fixtures/neurotiker_archive_mapping.py -- use YAML names

14. Add sugar_code_names to oasa/__init__.py

15. Checkpoint: Run full tests

16. Run pyflakes lint

17. Update docs/CHANGELOG.md

Verification

source source_me.sh

# After split (step 11)
python3 -m pytest tests/test_haworth_renderer.py tests/smoke/test_haworth_renderer_smoke.py -v
python3 -m pytest tests/test_haworth_spec.py tests/smoke/test_haworth_spec_smoke.py -v
python3 -m pytest tests/test_haworth_layout.py tests/test_haworth_cairo_layout.py -v

# After YAML integration (step 15)
python3 -m pytest tests/ -v

# Lint
python3 -m pytest tests/test_pyflakes_code_lint.py -v

# Verify backward-compat imports
python3 -c "import oasa.haworth; print('haworth OK')"
python3 -c "import oasa.haworth_renderer; print('renderer OK')"
python3 -c "import oasa.haworth_spec; print('spec OK')"
python3 -c "from oasa.sugar_code_names import get_sugar_name; print(get_sugar_name('ARLRDM'))"

# Verify tool still works
python3 tools/archive_matrix_summary.py --help

Files to create

, packages/oasa/oasa/haworth/__init__.py (from current haworth.py)
, packages/oasa/oasa/haworth/spec.py (from current haworth_spec.py)
, packages/oasa/oasa/haworth/renderer.py (refactored from haworth_renderer.py)
, packages/oasa/oasa/haworth/renderer_config.py (extracted constants)
, packages/oasa/oasa/haworth/renderer_geometry.py (extracted geometry)
, packages/oasa/oasa/haworth/renderer_text.py (extracted text functions)
, packages/oasa/oasa/haworth/renderer_layout.py (extracted layout optimizer)
, packages/oasa/oasa/sugar_code_names.py (new YAML loader)

Files to modify

, packages/oasa/oasa/haworth_renderer.py -- replace with backward-compat shim
, packages/oasa/oasa/haworth_spec.py -- replace with backward-compat shim
, packages/oasa/oasa/__init__.py -- add sugar_code_names import
, tests/fixtures/neurotiker_archive_mapping.py -- use YAML for sugar names
, docs/CHANGELOG.md -- document changes
