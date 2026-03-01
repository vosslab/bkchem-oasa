# source_me.sh - Set up environment for testing and development
#
# This script is for TESTING AND DEVELOPMENT ONLY, not for installation.
# It configures PYTHONPATH so you can run tests and scripts that import
# from packages/oasa and packages/bkchem-app.
#
# Usage:
#   source source_me.sh
#   . source_me.sh
set | grep -q "^BASH_VERSION=" || echo "use bash for your shell"
set | grep -q "^BASH_VERSION=" || exit 1

# Set Python environment optimizations
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Only source ~/.bashrc if it has not already been loaded in this shell.
if [[ -z "${BASHRC_COMMON_LOADED:-}" ]]; then
	source "$HOME/.bashrc"
fi

# Determine repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"

# Add packages to PYTHONPATH
unset PYTHONPATH
export PYTHONPATH="${REPO_ROOT}/packages/oasa:${REPO_ROOT}/packages/bkchem-app:${REPO_ROOT}/packages/bkchem-qt.app"

echo "Environment configured:"
echo "  REPO_ROOT=${REPO_ROOT}"
echo "  PYTHONPATH=${PYTHONPATH}"
echo ""
echo "Agents run with :"
echo "  source source_me.sh && python3 -c 'from oasa import haworth; print(haworth)'"
echo "  source source_me.sh && python3 tools/selftest_sheet.py --format png"
