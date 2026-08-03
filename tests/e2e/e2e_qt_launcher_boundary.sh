#!/usr/bin/env bash
# Exercise the root supported-launcher boundary without starting a Qt process.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
source "$REPO_ROOT/source_me.sh"
FIXTURE_ROOT="$(mktemp -d "$REPO_ROOT/tmp/qt_launcher_boundary.XXXXXX")"
STUB_BIN="$FIXTURE_ROOT/bin"
CAPTURE_PATH="$FIXTURE_ROOT/pythonpath.txt"
mkdir -p "$STUB_BIN"

printf '%s\n' '#!/usr/bin/env bash' \
	'printf "%s\\n" "$PYTHONPATH" > "$BKCHEM_QT_LAUNCH_ENV"' \
	'printf "%s\\n" "$*" > "$BKCHEM_QT_LAUNCH_ARGS"' \
	> "$STUB_BIN/python3"
chmod +x "$STUB_BIN/python3"

env PATH="$STUB_BIN:$PATH" \
	PYTHONPATH="$REPO_ROOT/packages/bkchem-app" \
	BKCHEM_QT_LAUNCH_ENV="$CAPTURE_PATH" \
	BKCHEM_QT_LAUNCH_ARGS="$FIXTURE_ROOT/arguments.txt" \
	"$REPO_ROOT/launch_bkchem-qt_gui.sh" --version

expected_path="$REPO_ROOT/packages/bkchem-qt.app:$REPO_ROOT/packages/oasa"
[ "$(<"$CAPTURE_PATH")" = "$expected_path" ]
[ "$(<"$FIXTURE_ROOT/arguments.txt")" = "-m bkchem_qt --version" ]

# The root keeps precisely one application launcher.  This guards the delivery
# boundary without making an exact retired filename the test's only oracle.
unexpected_launchers="$(find "$REPO_ROOT" -maxdepth 1 -type f -name 'launch_bkchem*_gui.sh' ! -name 'launch_bkchem-qt_gui.sh' -print -quit)"
[ -z "$unexpected_launchers" ]

echo "Qt launcher boundary passed. Fixture retained at $FIXTURE_ROOT"
