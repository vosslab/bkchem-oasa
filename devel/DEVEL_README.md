# devel scripts

`devel/` holds maintainer-only tools for developing, validating, and releasing
this repository. These files are not product code and are not part of the fast
pytest lane.

Use this folder for scripts that help maintainers do repo-level work:

- Version and release preparation.
- Changelog querying, commit-message drafting, and changelog rotation.
- Documentation repair and repo hygiene cleanup.
- Build-output cleanup that is useful across repo types.
- Template-only developer helpers that should ship into consumer repos under
  their own `devel/` folders.

Do not put reusable library code, runtime application code, or permanent tests
here. Shared test helpers belong in `tests/`; shipped runtime files belong in
the appropriate repo root, package, or `templates/<type>/` path.

## Current root scripts

| File | Kind of work |
| --- | --- |
| [bump_version.py](bump_version.py) | Set or bump repo versions across version files. |
| [changelog_lib.py](changelog_lib.py) | Shared parser and helpers for changelog tools. |
| [commit_changelog.py](commit_changelog.py) | Draft a commit message from new changelog entries. |
| [query_changelog.py](query_changelog.py) | Search active and archived changelog entries. |
| [rotate_changelog.py](rotate_changelog.py) | Move old changelog day blocks into archive files. |
| [flatten_broken_md_links.py](flatten_broken_md_links.py) | Repair or flatten broken Markdown links. |
| [dist_clean.sh](dist_clean.sh) | Remove generated build artifacts, caches, and dependency installs; preserves `tmp/` by default. |

## Template devel scripts

Some developer tools ship into consumer repos via propagation and appear in `devel/` when present.

`templates/shared/devel/` holds tools that propagate to non-PyPI python, rust, swift, and other
consumer repo types (repos with `pyproject.toml` are excluded by the `lacks_file` condition).
When present in a consumer repo, `devel/make_release.py` prepares a GitHub source
release: CalVer freshness check, free-tag check, committed-LICENSE verification, zip and tgz
archive build with byte-level LICENSE spot-check, LLM-prompt generation for the release
description, optional `docs/RELEASE_HISTORY.md` and `docs/NEWS.md` updates, and printed
`git tag` + `gh release create` commands. Use `--dry-run` to preview or `--write` to update
doc files. See [docs/REPO_STYLE.md](../docs/REPO_STYLE.md) versioning section for the full flow.

Some developer tools are type-specific and live under `templates/<type>/devel/`
so they propagate only to matching consumer repos. Examples include Python
release publishing helpers and TypeScript setup/rendering helpers.

## Running scripts

For Python scripts, use the repo bootstrap environment:

```bash
source source_me.sh && python3 devel/<script>.py
```

Run individual scripts with `--help` for current options. Keep command details
in script help output instead of duplicating them here.

## Installed Qt lifecycle check

`tests/e2e/e2e_installed_qt_authoritative_roundtrip.py` is the direct release
check for an isolated installed OASA and `bkchem-qt` pair. It opens native
CDML, commits an Arrow through the public persistent-operation route, performs
authoritative Save, closes the saved tab, reopens it, and retires the window
through the production Qt lifecycle. Its application-owned deadline defaults
to three seconds and its optional JSON receipt records the terminal outcome.

Use a fresh caller-owned directory under repo-root `tmp/` for every invocation
so the runner cannot overwrite a prior saved document or receipt:

```bash
source source_me.sh && mkdir -p tmp/installed_qt_roundtrip_check
env -u PYTHONPATH QT_QPA_PLATFORM=offscreen \
  /path/to/isolated/venv/bin/python -W error \
  tests/e2e/e2e_installed_qt_authoritative_roundtrip.py \
  --kill-after 3 \
  --output tmp/installed_qt_roundtrip_check \
  --receipt tmp/installed_qt_roundtrip_check/receipt.json
```

The receipt must report `status: completed` and installed origins outside
`packages/oasa` and `packages/bkchem-qt.app`. The runner closes its saved and
reopened tabs, then exercises `close_session_at(0)` for the remaining clean
sole tab before proving QObject retirement. This is isolated-wheel evidence,
not a substitute for the later controlled PyInstaller build and inspection.

## Documentation screenshots

The tracked `take_qt_screenshot.sh` command runs
`tools/capture_qt_cdml_projection.py` to regenerate the managed README and
capability-gallery images. Each catalog scenario opens deterministic complete
CDML through the public `MainWindow` path, verifies its backend-owned snapshot,
fits its disposable projection, grabs only that Qt window, and retires the same
window through the production lifecycle boundary. Scenarios use fresh bounded
processes and repository-root `tmp/documentation_screenshots/` for generated
CDML input and isolated Qt settings.

Run the default 1280x800 light-theme capture from the repository root:

```bash
source source_me.sh && ./take_qt_screenshot.sh --kill-after 3
```

The default catalog writes the three PNGs embedded by `README.md` and
`docs/CAPABILITIES.md`. Use a named `--scenario` with `--output` to inspect one
repository-contained preview without replacing a managed asset:

```bash
source source_me.sh && ./take_qt_screenshot.sh \
  --scenario drawing-objects --output tmp/drawing-objects-preview.png \
  --kill-after 3
```

## Clean installed-wheel release gate

`tests/e2e/e2e_clean_qt_install.py` creates one retained repository-`tmp/`
run root, builds fresh local OASA and BKChem-Qt wheels, and installs them into
a new Python 3.12 virtual environment with system site packages disabled. It
removes `PYTHONPATH` for every build, installation, and installed execution,
uses `/usr/bin/clang` for native dependency compilation, and retains command
logs, wheel artifacts, installed-origin evidence, package resolution, CLI
smoke output, and two authoritative roundtrip receipts.

Run it directly from the bootstrap environment:

```bash
source source_me.sh && python3 tests/e2e/e2e_clean_qt_install.py
```

The gate succeeds only when `pip check` passes, OASA and BKChem-Qt import from
the new environment rather than `packages/`, the sole BKChem console entry is
`bkchem-qt`, the installed CLI reports its version and completes the one-second
offscreen smoke, and each `--kill-after 3` authoritative edit/save/reopen
receipt reports `status: completed`. It resolves ordinary runtime dependencies
through pip, so it requires the package index or a suitable local pip cache.
The retained output path printed on success is evidence for this run; it is
not a frozen-app build or inspection result.

## Experimental frozen Qt bundle

`devel/build_qt_app.py` builds one retained `BKChem.app` below a new
repository-local `tmp/` path. The build plan explicitly excludes `tkinter` and
`_tkinter`, and `PIL.ImageTk`: RDKit's optional `PIL.ImageTk` route can otherwise
make PyInstaller collect Tcl/Tk into an application that only delivers Qt. Post-build inspection
scans both the complete bundle filesystem payload and every recursive member of
the frozen executable's PyInstaller archives. It rejects Tcl/Tk, legacy
BKChem application/data, and add-on payloads before a smoke may count as
evidence. The builder writes final version metadata, then ad-hoc signs and
strictly verifies that complete local bundle before inspection or launch.

Use a dry run to inspect the selected inputs and commands:

```bash
source source_me.sh && python3 devel/build_qt_app.py \
  --output tmp/qt_bundle_preview --dry-run
```

A real build requires a fresh output name and a macOS bundle build identity:

```bash
source source_me.sh && python3 devel/build_qt_app.py \
  --output tmp/qt_bundle_build --bundle-build 26.7.1 --smoke-exit 3
```

The builder runs the bundled executable directly with an offscreen Qt platform
and retains its output plus the app-owned lifecycle receipt under `smoke/`.
That bounded result proves the frozen process entered and left its production
event loop cleanly. Finder registration is not an application correctness gate;
signing, notarization, and DMG delivery remain a separate distribution project.

## Generated-artifact cleanup

[dist_clean.sh](dist_clean.sh) removes known generated distribution, build,
cache, and dependency-install artifacts from the resolved Git worktree. Its
normal scope preserves repo-root `tmp/` and nested `tmp/` directories
completely because they hold working files and retained validation evidence.
Preview the exact resolved targets before deletion:

```bash
source source_me.sh && devel/dist_clean.sh --dry-run
```

Use `--include-tmp` when a deliberate full removal of that worktree's `tmp/`
directory is needed. Cleanup permanently removes its reported targets; it does
not move them to a recovery location. The `--root DIRECTORY` option supports
isolated Git-worktree verification and rejects roots outside that worktree.
