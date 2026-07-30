"""Pytest configuration for bkchem package tests."""

# Standard Library
import os
import subprocess
import sys

# PIP3 modules
import pytest

pytest_plugins = ("pytest_kill_after",)


_LEGACY_TK_E2E_TEST_FILES = frozenset({
	"test_bkchem_gui_events.py",
	"test_gui_modes.py",
	"test_bkchem_gui_benzene.py",
	"test_bkchem_gui_hex_grid.py",
	"test_gui_theme_change.py",
	"test_bkchem_gui_zoom.py",
})


#============================================
def pytest_addoption(parser: pytest.Parser) -> None:
	"""Register the explicit opt-in for native Tk end-to-end tests."""
	parser.addoption(
		"--run-legacy-tk-e2e",
		action="store_true",
		default=False,
		help="run legacy Tk tests that create native Cocoa windows",
	)


#============================================
def pytest_collection_modifyitems(
	config: pytest.Config,
	items: list[pytest.Item],
) -> None:
	"""Skip legacy native-Tk E2E modules unless explicitly requested."""
	if config.getoption("--run-legacy-tk-e2e"):
		return
	skip_legacy_tk = pytest.mark.skip(
		reason="native Tk E2E tests require --run-legacy-tk-e2e",
	)
	for item in items:
		if item.path.name in _LEGACY_TK_E2E_TEST_FILES:
			item.add_marker(skip_legacy_tk)


#============================================
def _get_repo_root() -> str:
	"""Find repo root via git."""
	return subprocess.check_output(
		["git", "rev-parse", "--show-toplevel"],
		text=True,
	).strip()


_REPO_ROOT = _get_repo_root()


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
