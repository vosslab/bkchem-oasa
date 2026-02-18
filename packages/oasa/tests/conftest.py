"""Pytest configuration for oasa package tests."""

# Standard Library
import os
import subprocess
import sys


#============================================
def _get_repo_root() -> str:
	"""Find repo root via git."""
	return subprocess.check_output(
		["git", "rev-parse", "--show-toplevel"],
		text=True,
	).strip()


_REPO_ROOT = _get_repo_root()


#============================================
def _ensure_paths():
	"""Add oasa package and repo tests/ to sys.path."""
	# oasa package root (packages/oasa)
	oasa_pkg = os.path.join(_REPO_ROOT, "packages", "oasa")
	if oasa_pkg not in sys.path:
		sys.path.insert(0, oasa_pkg)
	# repo tests/ so git_file_utils is importable
	tests_dir = os.path.join(_REPO_ROOT, "tests")
	if tests_dir not in sys.path:
		sys.path.insert(0, tests_dir)


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
