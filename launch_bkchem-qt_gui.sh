#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The supported application deliberately has no path to the historical Tk
# frontend.  Development-only reference access remains in source_me.sh.
export PYTHONPATH="${ROOT_DIR}/packages/bkchem-qt.app:${ROOT_DIR}/packages/oasa"

exec python3 -m bkchem_qt "$@"
