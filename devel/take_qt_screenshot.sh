#!/bin/sh

set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

exec "$REPO_ROOT/tools/capture_qt_cdml_projection.py" "$@"
