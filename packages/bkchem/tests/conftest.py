"""Pytest configuration for bkchem package tests."""

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
	"""Add bkchem, oasa packages, and repo tests/ to sys.path."""
	# bkchem package root (packages/bkchem)
	bkchem_pkg = os.path.join(_REPO_ROOT, "packages", "bkchem")
	if bkchem_pkg not in sys.path:
		sys.path.insert(0, bkchem_pkg)
	# bkchem inner module directory (packages/bkchem/bkchem)
	bkchem_module_dir = os.path.join(bkchem_pkg, "bkchem")
	if bkchem_module_dir not in sys.path:
		sys.path.append(bkchem_module_dir)
	# oasa package root (packages/oasa)
	oasa_pkg = os.path.join(_REPO_ROOT, "packages", "oasa")
	if oasa_pkg not in sys.path:
		sys.path.insert(0, oasa_pkg)
	# repo tests/ so git_file_utils is importable
	tests_dir = os.path.join(_REPO_ROOT, "tests")
	if tests_dir not in sys.path:
		sys.path.insert(0, tests_dir)


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
