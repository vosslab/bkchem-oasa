"""Pytest configuration for bkchem package tests."""

# Standard Library
import os
import sys


# Resolve directory layout once at import time
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_BKCHEM_PKG = os.path.dirname(_TESTS_DIR)
_PACKAGES_DIR = os.path.dirname(_BKCHEM_PKG)
_REPO_ROOT = os.path.dirname(_PACKAGES_DIR)


#============================================
def _ensure_paths():
	"""Add bkchem and oasa packages to sys.path if not already present.

	Uses the known relative layout: this file lives at
	packages/bkchem/tests/conftest.py, so packages/ is two levels up.
	"""
	# bkchem package root (packages/bkchem)
	if _BKCHEM_PKG not in sys.path:
		sys.path.insert(0, _BKCHEM_PKG)
	# bkchem inner module directory (packages/bkchem/bkchem)
	bkchem_module_dir = os.path.join(_BKCHEM_PKG, "bkchem")
	if bkchem_module_dir not in sys.path:
		sys.path.append(bkchem_module_dir)
	# oasa package root (packages/oasa)
	oasa_pkg = os.path.join(_PACKAGES_DIR, "oasa")
	if oasa_pkg not in sys.path:
		sys.path.insert(0, oasa_pkg)


#============================================
def repo_root() -> str:
	"""Return the absolute path to the repository root."""
	return _REPO_ROOT


#============================================
def repo_tests_path(*parts) -> str:
	"""Return a path under the repo-root tests/ directory.

	Args:
		*parts: Path components relative to tests/ (e.g. "fixtures", "cdml").

	Returns:
		Absolute path joined from <repo_root>/tests/ and the given parts.
	"""
	return os.path.join(_REPO_ROOT, "tests", *parts)


_ensure_paths()
