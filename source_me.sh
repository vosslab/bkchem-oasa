# source_me.sh - Set up environment for testing and development
#
# This script is for TESTING AND DEVELOPMENT ONLY, not for installation.
# It configures PYTHONPATH so you can run tests and scripts that import
# from packages/oasa and packages/bkchem-app.
#
# Usage:
#   source source_me.sh
#   . source_me.sh
set | grep -q '^BASH_VERSION=' || echo "use bash for your shell"
set | grep -q '^BASH_VERSION=' || exit 1

# Set Python environment optimizations
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

source $HOME/.bashrc

# Determine repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"

# Add packages to PYTHONPATH
export PYTHONPATH="${REPO_ROOT}/packages/oasa:${REPO_ROOT}/packages/bkchem-app:${PYTHONPATH:-}"

echo "Environment configured:"
echo "  REPO_ROOT=${REPO_ROOT}"
echo "  PYTHONPATH=${PYTHONPATH}"
echo ""
echo "You can now run:"
echo "  python3 -c 'from oasa import haworth; print(haworth)'"
echo "  python3 packages/oasa/oasa/selftest_sheet.py --format png"
