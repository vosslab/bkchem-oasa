"""Pytest configuration for bkchem package tests."""

# Standard Library
import os
import subprocess
import sys

# PIP3 modules
import pytest


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


#============================================
_tk_root = None


#============================================
@pytest.fixture(scope="session", autouse=True)
def _init_gui_singletons():
	"""Create a hidden Tk root so GUI singletons are available in tests."""
	global _tk_root
	try:
		from tkinter import Tk
	except ImportError:
		yield
		return
	_tk_root = Tk()
	_tk_root.withdraw()
	dpi = _tk_root.winfo_fpixels("1i")
	# attach a paper.standard so molecule factory methods work
	# (create_vertex/create_edge fall back to Store.app.paper.standard)
	try:
		import bkchem.classes
		_tk_root.paper = type('_MockPaper', (), {
			'standard': bkchem.classes.standard(),
		})()
	except ImportError:
		pass
	# set singletons for GUI tests
	try:
		from bkchem.singleton_store import Store, Screen
		Screen.dpi = dpi
		if Store.app is None:
			Store.app = _tk_root
	except ImportError:
		pass
	_propagate_singletons(dpi, _tk_root)
	yield
	_tk_root.destroy()
	_tk_root = None


#============================================
def _propagate_singletons(dpi: float, app=None) -> None:
	"""Set Screen.dpi and Store.app on special_parents module."""
	# special_parents imports Screen/Store directly; references may differ
	try:
		from bkchem import special_parents
		special_parents.Screen.dpi = dpi
		if app is not None and getattr(special_parents.Store, 'app', None) is None:
			special_parents.Store.app = app
	except ImportError:
		pass
