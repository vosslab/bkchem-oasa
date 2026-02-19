# LICENSE_MIGRATION.md

License migration strategy for the BKChem monorepo.

## Summary

This repository is transitioning from GPL-2.0 to a mixed GPL-2.0 / LGPL-3.0-or-later licensing model based on code provenance. The goal is to preserve legal compatibility while making modern renderer and library components available under LGPL for broader reuse.

## Core Principle: Provenance, Not Percentage

**Default rule:**
- All new files are `LGPL-3.0-or-later`
- Any file that contains GPLv2-derived code stays `GPL-2.0`
- Any mixed file (GPLv2 + new code) stays `GPL-2.0` until all GPLv2 content
  is fully removed and the file is rewritten from scratch

No percentage tests. No intent tests. Just provenance.

## Review comments

- The compatibility notes need a careful correction. `LGPL-3.0-or-later`
  is compatible with `GPL-2.0-or-later`, but not with `GPL-2.0-only`.
  The plan should explicitly confirm whether BKChem is GPL-2.0-only or
  GPL-2.0-or-later before relying on LGPLv3 components.
- The "GPL v2 Code Coverage Assessment Plan" introduces percentage-based
  classification for "Mixed" files, which conflicts with the earlier rule
  of "provenance, not percentage." These percentage metrics must be
  reporting-only: use them to understand scope and support outreach to
  original authors, not to justify relicensing decisions.
- The 2025-based cutoff is a tracking heuristic, not proof of provenance.
  A pre-2025 creation date does not automatically imply GPLv2 provenance,
  and a 2025 creation date does not prove a clean-room rewrite. Document
  this as a reporting assumption only.
- The document assumes git history is authoritative. That is useful for
  reporting, but it is not sufficient for relicensing decisions when files
  were moved, rebased, or imported. Add a note that provenance may require
  manual review beyond git timestamps.

## Mixed Licensing Is Intentional

- **Legacy BKChem and OASA files**: `GPL-2.0`
- **Newly introduced files**: `LGPL-3.0-or-later`
- **Compatibility**: LGPL code can be used by GPL-2.0 code, but not vice versa
- **Architecture alignment**: BKChem depends on OASA, not the other way around

This is a clean, conservative, and future-proof approach that matches how long-lived scientific and GUI projects survive license transitions.

## SPDX Headers Are Required

### New files

Every new file must include an SPDX header at the top:

```python
# SPDX-License-Identifier: LGPL-3.0-or-later
```

For Python files with shebangs, the SPDX header comes after the shebang:

```python
#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later
```

### Legacy files

Do not touch the license header unless you are certain the file is a clean rewrite.

If a file was edited in place, preserves structure, or obviously evolved from an older implementation, treat it as `GPL-2.0` even if it is heavily modified.

## Conservative Relicensing Policy

A file remains `GPL-2.0` if:
- It was edited in place
- It preserves original structure
- It obviously evolved from an older implementation
- You are uncertain about provenance

A file can be relicensed to `LGPL-3.0-or-later` only if:
- It is a completely new file with no GPLv2-derived code
- It is a full rewrite from scratch with a new implementation
- It is moved to a new path as part of a clean rewrite

**When in doubt, keep it GPL-2.0.**

## Licensing Boundaries

The renderer backend boundary aligns with licensing:

### LGPL-3.0-or-later (reusable library components)
- `packages/oasa/oasa/render_ops.py`
- `packages/oasa/oasa/wedge_geometry.py`
- `packages/oasa/oasa/bond_semantics.py`
- `packages/oasa/oasa/cdml_bond_io.py`
- `packages/oasa/oasa/safe_xml.py`
- `packages/oasa/oasa/atom_colors.py`
- Layout logic: `packages/oasa/oasa/haworth.py`
- Tests for LGPL components
- CLI tooling
- Future renderer utilities

### GPL-2.0 (legacy and GUI-specific code)
- BKChem GUI: `packages/bkchem-app/bkchem/main.py`
- CDML glue: legacy parts of `packages/oasa/oasa/cdml.py`
- BKChem bond rendering: `packages/bkchem-app/bkchem/bond.py`
- Legacy IO and external data fetchers
- Plugin system
- Template catalog

This boundary is not strict, but it is a useful guide.

## Compatibility Rules

1. **LGPL code can be used by GPL-2.0 code**
   - BKChem (GPL-2.0) can depend on OASA render ops (LGPL-3.0-or-later)
   - This is safe and legally sound

2. **GPL-2.0 code cannot be relicensed "upward" to LGPL**
   - Legacy code with GPLv2 provenance stays GPL-2.0
   - No exceptions

3. **Third-party code must be compatible**
   - LGPL-3.0-or-later is compatible with GPL-2.0
   - GPL-2.0 is not compatible with proprietary software
   - LGPL-3.0-or-later allows proprietary linking

## Migration Workflow

### Adding a new file
1. Write the file from scratch
2. Add the SPDX header: `# SPDX-License-Identifier: LGPL-3.0-or-later`
3. Commit and document in [docs/CHANGELOG.md](CHANGELOG.md)

### Rewriting an existing file
1. Verify the file is a complete rewrite with no GPLv2-derived code
2. Move to a new path if desired (optional but recommended)
3. Add the SPDX header: `# SPDX-License-Identifier: LGPL-3.0-or-later`
4. Document the rewrite and relicensing in [docs/CHANGELOG.md](CHANGELOG.md)

### Editing an existing file
1. Do not change the license header
2. Keep the file as `GPL-2.0`
3. If the file has no SPDX header, add one: `# SPDX-License-Identifier: GPL-2.0`

## Long-Term Vision

### Phase 1: Establish mixed licensing (current)
- New files are LGPL-3.0-or-later
- Legacy files stay GPL-2.0
- SPDX headers are added to all files

### Phase 2: Expand LGPL components
- Rewrite additional renderer utilities
- Extract layout algorithms into LGPL modules
- Build a clean LGPL rendering API

### Phase 3: Stabilize boundaries
- Document clear GPL/LGPL boundaries in [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md)
- Ensure LGPL components are self-contained
- Maintain GPL-2.0 for BKChem GUI and legacy IO

### Long-term outcome
- Modern OASA renderer backend: LGPL-3.0-or-later (reusable by proprietary software)
- BKChem GUI and legacy components: GPL-2.0 (preserves original licensing)
- Clean separation allows future projects to use OASA without GPL constraints

## Legal and Community Considerations

### Why this works
- Provenance-based approach is legally defensible
- No retroactive relicensing of GPLv2 code
- Conservative policy minimizes legal risk
- Mixed licensing is common in long-lived open-source projects

### Preventing future confusion
- Explicit SPDX headers in every file
- This document explains the strategy
- [docs/CHANGELOG.md](CHANGELOG.md) tracks all relicensing decisions
- No "cleanup" PRs that change licenses without provenance review

### Community trust
- Transparent migration process
- Conservative relicensing policy
- No license changes without clear provenance
- Respects original GPL-2.0 contributions

## References

- SPDX License List: https://spdx.org/licenses/
- GPL-2.0: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
- LGPL-3.0: https://www.gnu.org/licenses/lgpl-3.0.html
- GPL Compatibility: https://www.gnu.org/licenses/gpl-faq.html#AllCompatibility

## GPL v2 Code Coverage Assessment Plan

### Objective

Assess the current state of GPL v2 code coverage across the repository to track migration progress and identify remaining legacy code. This assessment will provide baseline metrics and guide future relicensing efforts.

### Assumptions

1. **All edits prior to 2025 are GPL-2.0**: Any file with commits before January 1, 2025 is considered GPL v2 code
2. **File creation date determines initial license**: Files created in 2025 or later are LGPL-3.0-or-later unless proven otherwise
3. **Git history is authoritative**: Use git log to determine file creation and modification dates

### Classification System

Files are classified into three categories:

1. **Pure GPL-2.0**: All lines last edited before the cutoff date
   - Every line is GPL v2 provenance
   - Example: untouched legacy files

2. **Pure LGPL-3.0-or-later**: All lines last edited on/after the cutoff date
   - No GPLv2-derived code remains
   - Example: brand new renderer modules

3. **Mixed**: Lines exist on both sides of the cutoff
   - Contains GPL v2 and newer code
   - Must remain GPL-2.0 until fully rewritten

### Assessment Methodology

#### Step 1: Identify all Python files

```bash
# Find all Python files in packages/ and tests/
find packages tests -name "*.py" -type f | sort > /tmp/all_python_files.txt
```

#### Step 2: Classify each file by git blame line dates

For each file, use git blame to read the last edit time for each line:

```bash
git blame --line-porcelain --date=unix -- <file>
```

Classification logic (reporting-only):

```python
cutoff_ts = to_unix_timestamp("2025-01-01")
line_times = [committer_time_per_line(file)]
lines_before = sum(1 for t in line_times if t < cutoff_ts)
lines_after = total_lines - lines_before

if lines_before == 0:
    classification = "Pure LGPL-3.0-or-later"
elif lines_after == 0:
    classification = "Pure GPL-2.0"
else:
    classification = "Mixed"
```

#### Step 3: Calculate GPL v2 percentage for mixed files (reporting only)

For mixed files, calculate GPL v2 percentage using multiple metrics:

**Metric 1: Line age percentage (primary)**
```python
gpl_line_percentage = (lines_before / total_lines) * 100
```

**Metric 2: Commit count percentage (secondary)**
```python
gpl_commit_percentage = (commits_before_2025 / total_commits) * 100
```

**Metric 3: Line-change percentage (secondary)**
```bash
git log --before="2025-01-01" --numstat --pretty="%H" -- <file> | \
  awk 'NF==3 {added+=$1} END {print added}'

git log --since="2025-01-01" --numstat --pretty="%H" -- <file> | \
  awk 'NF==3 {added+=$1} END {print added}'
```

**Recommended metric**: Use line age percentage as primary; other metrics are supplemental.

#### Step 4: Generate summary report

Create a summary report with the following sections:

**Overall Statistics:**
```
Total Python files: X
Pure GPL-2.0 files: Y (Z%)
Pure LGPL-3.0-or-later files: A (B%)
Mixed files: C (D%)
```

**Mixed File Details:**
```
File                                    Total   GPL    LGPL   GPL%
                                        Commits Commits Commits
packages/oasa/oasa/cdml.py              47      42     5      89.4%
packages/bkchem-app/bkchem/bond.py          23      18     5      78.3%
...
```

**GPL v2 Content by Package:**
```
Package                 Total   GPL-2.0  LGPL    Mixed
                        Files   Files    Files   Files
packages/bkchem         45      35       2       8
packages/oasa           67      28       30      9
tests                   89      15       65      9
```

#### Step 5: Track SPDX header compliance

For each file, check if SPDX header matches classification:

```bash
# Check for SPDX header
head -n5 <file> | grep -E "SPDX-License-Identifier: (GPL-2\.0|LGPL-3\.0-or-later)"
```

Report files with:
- Missing SPDX headers
- Incorrect SPDX headers (classification mismatch)
- Need for header addition or correction

### Implementation Script

Create `tools/assess_gpl_coverage.py` with the following structure:

```python
#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-or-later

import subprocess
import os
from datetime import datetime
from pathlib import Path

def get_file_classification(file_path):
    """Classify file based on git history."""
    # Implementation here
    pass

def calculate_gpl_percentage(file_path):
    """Calculate GPL v2 percentage for mixed files."""
    # Implementation here
    pass

def check_spdx_header(file_path):
    """Check if SPDX header matches classification."""
    # Implementation here
    pass

def generate_report():
    """Generate comprehensive GPL v2 coverage report."""
    # Find all Python files
    # Classify each file
    # Calculate statistics
    # Output report
    pass

if __name__ == "__main__":
    generate_report()
```

### Usage

Preferred "one command per report" usage:

```bash
# Summary
/opt/homebrew/opt/python@3.12/bin/python3.12 tools/assess_gpl_coverage.py --summary

# Full report
/opt/homebrew/opt/python@3.12/bin/python3.12 tools/assess_gpl_coverage.py \
  > docs/gpl_coverage_report_$(date +%Y%m%d).txt

# CSV export
/opt/homebrew/opt/python@3.12/bin/python3.12 tools/assess_gpl_coverage.py --csv \
  > gpl_coverage.csv
```

Additional options:

```bash
# Check specific file
/opt/homebrew/opt/python@3.12/bin/python3.12 tools/assess_gpl_coverage.py \
  --file packages/oasa/oasa/cdml.py

# List files needing SPDX headers
/opt/homebrew/opt/python@3.12/bin/python3.12 tools/assess_gpl_coverage.py \
  --missing-headers
```

### Expected Outcomes

1. **Baseline metrics**: Number and percentage of GPL v2, LGPL, and mixed files
2. **Migration progress tracking**: Monitor reduction in GPL v2 percentage over time
3. **SPDX compliance**: Identify files needing license headers
4. **Targeted relicensing**: Prioritize mixed files with low GPL v2 percentage for rewriting
5. **Documentation**: Generated reports document license provenance

### Ongoing Maintenance

- Run assessment monthly during active migration
- Update report after significant relicensing efforts
- Track trends: GPL v2 file count and percentage over time
- Include assessment summary in release notes

### Next Steps

1. Implement `tools/assess_gpl_coverage.py`
2. Run initial assessment to establish baseline
3. Document baseline metrics in CHANGELOG.md
4. Use report to prioritize files for relicensing
5. Re-run assessment quarterly to track progress

## See Also

- [LICENSE](../LICENSE): Full GPL-2.0 license text (repository default)
- [docs/REPO_STYLE.md](REPO_STYLE.md): Repository licensing rules
- [docs/CHANGELOG.md](CHANGELOG.md): Record of all licensing changes
- [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md): Component boundaries
