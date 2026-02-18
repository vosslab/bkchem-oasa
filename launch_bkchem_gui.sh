#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT_DIR}/packages/bkchem:${ROOT_DIR}/packages/bkchem/bkchem:${ROOT_DIR}/packages/oasa:${PYTHONPATH:-}"

exec python3 -m bkchem.cli "$@"
