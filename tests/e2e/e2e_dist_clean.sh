#!/usr/bin/env bash
# Exercise the generated-artifact boundary against an isolated Git worktree.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
source "$REPO_ROOT/source_me.sh"
FIXTURE_ROOT="$(mktemp -d "$REPO_ROOT/tmp/dist_clean_fixture.XXXXXX")"

git init -q "$FIXTURE_ROOT"
mkdir -p "$FIXTURE_ROOT/build" "$FIXTURE_ROOT/tmp" \
	"$FIXTURE_ROOT/cache/__pycache__" "$FIXTURE_ROOT/cache/tmp/__pycache__"
touch "$FIXTURE_ROOT/build/generated.txt" "$FIXTURE_ROOT/tmp/sentinel.txt"
touch "$FIXTURE_ROOT/cache/__pycache__/generated.pyc" \
	"$FIXTURE_ROOT/cache/tmp/sentinel.txt" "$FIXTURE_ROOT/source.txt"

dry_run_output="$("$REPO_ROOT/devel/dist_clean.sh" --root "$FIXTURE_ROOT" --dry-run)"
[ "${dry_run_output#*"$FIXTURE_ROOT/build"}" != "$dry_run_output" ]
[ -e "$FIXTURE_ROOT/build/generated.txt" ]
[ -e "$FIXTURE_ROOT/tmp/sentinel.txt" ]
[ -e "$FIXTURE_ROOT/cache/tmp/sentinel.txt" ]

"$REPO_ROOT/devel/dist_clean.sh" --root "$FIXTURE_ROOT" >/dev/null
[ -e "$FIXTURE_ROOT/tmp/sentinel.txt" ]
[ -e "$FIXTURE_ROOT/cache/tmp/sentinel.txt" ]
[ -e "$FIXTURE_ROOT/source.txt" ]
[ ! -e "$FIXTURE_ROOT/build" ]
[ ! -e "$FIXTURE_ROOT/cache/__pycache__" ]

"$REPO_ROOT/devel/dist_clean.sh" --root "$FIXTURE_ROOT" --include-tmp >/dev/null
[ ! -e "$FIXTURE_ROOT/tmp" ]
[ -e "$FIXTURE_ROOT/source.txt" ]
[ -e "$FIXTURE_ROOT/cache/tmp/sentinel.txt" ]

OUTSIDE_TARGET="$REPO_ROOT/tmp/dist_clean_outside_target"
mkdir -p "$OUTSIDE_TARGET"
ln -s "$OUTSIDE_TARGET" "$FIXTURE_ROOT/node_modules"
if "$REPO_ROOT/devel/dist_clean.sh" --root "$FIXTURE_ROOT" --dry-run >/dev/null 2>&1; then
	echo "dist_clean.sh accepted a symlink-escape target" >&2
	exit 1
fi
[ -d "$OUTSIDE_TARGET" ]

if "$REPO_ROOT/devel/dist_clean.sh" --root / --dry-run >/dev/null 2>&1; then
	echo "dist_clean.sh accepted the filesystem root" >&2
	exit 1
fi

if "$REPO_ROOT/devel/dist_clean.sh" --root "$HOME" --dry-run >/dev/null 2>&1; then
	echo "dist_clean.sh accepted the home directory" >&2
	exit 1
fi

mkdir "$FIXTURE_ROOT/not_a_root"
if "$REPO_ROOT/devel/dist_clean.sh" --root "$FIXTURE_ROOT/not_a_root" --dry-run >/dev/null 2>&1; then
	echo "dist_clean.sh accepted a non-root worktree directory" >&2
	exit 1
fi

FAKE_GIT_ROOT="$REPO_ROOT/tmp/dist_clean_fake_git_root"
mkdir -p "$FAKE_GIT_ROOT/.git"
if "$REPO_ROOT/devel/dist_clean.sh" --root "$FAKE_GIT_ROOT" --dry-run >/dev/null 2>&1; then
	echo "dist_clean.sh accepted a fake Git directory" >&2
	exit 1
fi

if "$REPO_ROOT/devel/dist_clean.sh" --root "" --dry-run >/dev/null 2>&1; then
	echo "dist_clean.sh accepted an empty root" >&2
	exit 1
fi

if "$REPO_ROOT/devel/dist_clean.sh" --root "$FIXTURE_ROOT/missing" --dry-run >/dev/null 2>&1; then
	echo "dist_clean.sh accepted a nonexistent root" >&2
	exit 1
fi

echo "dist_clean generated-artifact scope passed. Fixture retained at $FIXTURE_ROOT"
