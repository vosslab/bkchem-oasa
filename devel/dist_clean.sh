#!/usr/bin/env bash
# dist_clean.sh - remove generated distribution artifacts from one repository.
#
# The normal cleanup scope deliberately preserves repo-root tmp/. It is a
# working and evidence area. Use --include-tmp only when that area itself is
# the artifact being retired.
set -euo pipefail

DRY_RUN=0
INCLUDE_TMP=0
REQUESTED_ROOT=""
REQUESTED_ROOT_SET=0
TARGETS=()

usage() {
	cat <<'EOF'
Usage: devel/dist_clean.sh [--dry-run] [--include-tmp] [--root DIRECTORY]

Remove known generated distribution, build, cache, and dependency artifacts
from one Git worktree. Deletion is permanent.

Options:
  --dry-run           Print each resolved target without deleting it.
  --include-tmp       Also remove that worktree's repo-root tmp/ directory.
  --root DIRECTORY    Use this Git worktree instead of the current one.
  --help              Show this help.

The default scope preserves repo-root tmp/ completely, including nested caches,
because it is used for working files and retained evidence. --root is useful
for an isolated verification worktree; it accepts only that worktree's root.
EOF
}

fail() {
	echo "dist_clean.sh: $*" >&2
	exit 2
}

require_option_value() {
	[ "$#" -ge 2 ] || fail "$1 requires a directory"
}

while [ "$#" -gt 0 ]; do
	case "$1" in
		--dry-run)
			DRY_RUN=1
			;;
		--include-tmp)
			INCLUDE_TMP=1
			;;
		--root)
			require_option_value "$@"
			REQUESTED_ROOT="$2"
			REQUESTED_ROOT_SET=1
			shift
			;;
		--help)
			usage
			exit 0
			;;
		*)
			fail "unknown option: $1"
			;;
	esac
	shift
done

canonical_directory() {
	local path="$1"
	[ -d "$path" ] || fail "directory does not exist: $path"
	(
		cd -P -- "$path"
		pwd
	)
}

resolve_repository_root() {
	local candidate_root
	local git_root
	if [ "$REQUESTED_ROOT_SET" -eq 1 ]; then
		candidate_root="$(canonical_directory "$REQUESTED_ROOT")"
	else
		candidate_root="$(git rev-parse --show-toplevel)" || fail "run inside a Git worktree"
		candidate_root="$(canonical_directory "$candidate_root")"
	fi
	git_root="$(git -C "$candidate_root" rev-parse --show-toplevel)" || \
		fail "not a Git worktree: $candidate_root"
	git_root="$(canonical_directory "$git_root")"
	[ "$candidate_root" = "$git_root" ] || fail "--root must name the Git worktree root"
	echo "$git_root"
}

REPO_ROOT="$(resolve_repository_root)"
HOME_ROOT="$(canonical_directory "$HOME")"
[ "$REPO_ROOT" != "/" ] || fail "refusing filesystem root"
[ "$REPO_ROOT" != "$HOME_ROOT" ] || fail "refusing home directory"

add_target() {
	local target="$1"
	local existing
	for existing in "${TARGETS[@]:-}"; do
		[ -n "$existing" ] || continue
		[ "$target" = "$existing" ] && return
		case "$target" in
			"$existing"/*)
				return
				;;
		esac
	done
	TARGETS+=("$target")
}

add_direct_target() {
	local relative_path="$1"
	local target="$REPO_ROOT/$relative_path"
	if [ -e "$target" ] || [ -L "$target" ]; then
		add_target "$target"
	fi
}

add_find_targets() {
	local match
	while IFS= read -r -d '' match; do
		add_target "$match"
	done < <(find "$REPO_ROOT" -type d -name tmp -prune -o "$@" -print0)
}

validate_target() {
	local target="$1"
	local resolved_target
	[ -n "$target" ] || fail "refusing an empty target"
	[ -e "$target" ] || [ -L "$target" ] || fail "target disappeared: $target"
	resolved_target="$(realpath "$target")" || fail "cannot resolve target: $target"
	[ "$resolved_target" != "/" ] || fail "refusing filesystem root target"
	[ "$resolved_target" != "$HOME_ROOT" ] || fail "refusing home-directory target"
	case "$resolved_target" in
		"$REPO_ROOT"/*)
			;;
		*)
			fail "target escapes repository root: $target -> $resolved_target"
			;;
	esac
}

# Generic build outputs (any language).
add_direct_target dist
add_direct_target dist-single
add_direct_target _site
add_direct_target build
add_direct_target out
if [ "$INCLUDE_TMP" -eq 1 ]; then
	add_direct_target tmp
fi

# TypeScript / JS artifacts and dependency installs.
add_direct_target _bundle.js
add_direct_target meta.json
add_direct_target stats.html
add_direct_target node_modules
add_direct_target .cache
add_direct_target .eslintcache
add_direct_target .prettiercache
add_direct_target .nyc_output
add_find_targets -type f -name '*.tsbuildinfo'

# Xcode / Swift build outputs and metadata.
add_direct_target .build
add_direct_target .swiftpm
add_direct_target DerivedData
add_find_targets -type d -name '*.xcresult'
add_find_targets -type d -name 'xcuserdata'
add_find_targets -type f -path '*/xcshareddata/swiftpm/Package.resolved'
add_find_targets -type d -path '*/Packages/*/.build'
add_find_targets -type d -path '*/Packages/*/.swiftpm'
add_find_targets -type f -path '*/Packages/*/Package.resolved'

# Test outputs.
add_direct_target test-results
add_direct_target playwright-report
add_direct_target blob-report
add_direct_target coverage
add_direct_target cover_db

# Python bytecode, virtualenvs, and tool caches.
add_direct_target .venv
add_direct_target venv
add_direct_target env
add_find_targets -type d -name build -prune
add_find_targets -type d -name '*.egg-info' -prune
add_find_targets -type d -name '*.dist-info' -prune
add_find_targets -type d -name '__pycache__' -prune
add_find_targets -type d -name '.pytest_cache' -prune
add_find_targets -type d -name '.mypy_cache' -prune
add_find_targets -type d -name '.ruff_cache' -prune

# Perl build/test artifacts.
add_direct_target blib
add_direct_target _build
add_direct_target Build
add_direct_target Build.bat
add_direct_target MYMETA.json
add_direct_target MYMETA.yml
add_direct_target Makefile.old
add_direct_target pm_to_blib
add_direct_target local/lib/perl5

# C/C++ and CMake/autotools generated outputs.
add_direct_target CMakeCache.txt
add_direct_target CMakeFiles
add_direct_target cmake_install.cmake
add_direct_target compile_commands.json
add_direct_target autom4te.cache
add_find_targets -type d -name CMakeFiles -prune
add_find_targets -type f -name CMakeCache.txt
add_find_targets -type f \( -name '*.o' -o -name '*.obj' -o -name '*.a' \
	-o -name '*.so' -o -name '*.dylib' \)

# Rust build outputs.
add_direct_target target

for target in "${TARGETS[@]:-}"; do
	[ -n "$target" ] || continue
	validate_target "$target"
done

if [ "${#TARGETS[@]}" -eq 0 ]; then
	echo "No generated artifacts found."
	exit 0
fi

if [ "$DRY_RUN" -eq 1 ]; then
	echo "Generated artifact cleanup preview:"
	for target in "${TARGETS[@]:-}"; do
		[ -n "$target" ] || continue
		echo "  $target"
	done
	exit 0
fi

echo "Removing generated artifacts permanently:"
for target in "${TARGETS[@]:-}"; do
	[ -n "$target" ] || continue
	echo "  $target"
	rm -rf -- "$target"
done
