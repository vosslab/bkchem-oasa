"""Pytest configuration for bkchem package tests."""

# Standard Library
import os
import sys

pytest_plugins = ("pytest_kill_after",)


_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


#============================================
def _ensure_paths() -> None:
	"""Add bkchem-app, oasa packages, and repo tests/ to sys.path."""
	# bkchem package root (packages/bkchem-app)
	bkchem_pkg = os.path.join(_REPO_ROOT, "packages", "bkchem-app")
	if bkchem_pkg not in sys.path:
		sys.path.insert(0, bkchem_pkg)
	# oasa package root (packages/oasa)
	oasa_pkg = os.path.join(_REPO_ROOT, "packages", "oasa")
	if oasa_pkg not in sys.path:
		sys.path.insert(0, oasa_pkg)
	# repo tests/ so git_file_utils is importable
	tests_dir = os.path.join(_REPO_ROOT, "tests")
	if tests_dir not in sys.path:
		sys.path.insert(0, tests_dir)


_ensure_paths()
