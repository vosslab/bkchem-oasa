"""Pytest configuration for oasa package tests."""

# Standard Library
import os
import sys

# directory containing this conftest.py
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
# packages/oasa
_OASA_PKG = os.path.dirname(_TESTS_DIR)
# packages/
_PACKAGES_DIR = os.path.dirname(_OASA_PKG)
# repo root
_REPO_ROOT = os.path.dirname(_PACKAGES_DIR)


#============================================
def pytest_addoption(parser):
	"""Register custom pytest command-line options."""
	parser.addoption(
		"--save",
		action="store_true",
		default=False,
		help="Save rendered outputs to the current working directory",
	)


#============================================
def _ensure_paths():
	"""Add oasa package to sys.path if not already present.

	Uses the known relative layout: this file lives at
	packages/oasa/tests/conftest.py, so the oasa package root
	is one level up.
	"""
	if _OASA_PKG not in sys.path:
		sys.path.insert(0, _OASA_PKG)


#============================================
def repo_root() -> str:
	"""Return the repository root directory."""
	return _REPO_ROOT


#============================================
def repo_tests_path(*parts) -> str:
	"""Return a path under the repo-root tests/ directory.

	Args:
		*parts: path components relative to tests/
	"""
	return os.path.join(_REPO_ROOT, "tests", *parts)


_ensure_paths()
