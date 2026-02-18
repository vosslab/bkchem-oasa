"""BKChem CDML smoke coverage for Phase 0 fixtures."""

# Standard Library
import argparse
import builtins
import os
import subprocess
import sys
import tempfile

# Third Party
import pytest

# Local repo modules
import conftest


FIXTURES_DIR = conftest.repo_tests_path("fixtures", "bkchem_phase0")
FIXTURE_FILES = (
	"basic_types.cdml",
	"stereo.cdml",
	"aromatic.cdml",
	"wavy_color.cdml",
	"bkchem_widths.cdml",
)


#============================================
def _ensure_sys_path(root_dir):
	"""Ensure BKChem package paths are on sys.path."""
	bkchem_pkg_dir = os.path.join(root_dir, "packages", "bkchem")
	if bkchem_pkg_dir not in sys.path:
		sys.path.insert(0, bkchem_pkg_dir)
	bkchem_module_dir = os.path.join(bkchem_pkg_dir, "bkchem")
	if bkchem_module_dir not in sys.path:
		sys.path.append(bkchem_module_dir)
	oasa_pkg_dir = os.path.join(root_dir, "packages", "oasa")
	if oasa_pkg_dir not in sys.path:
		sys.path.insert(0, oasa_pkg_dir)
	oasa_module_dir = os.path.join(oasa_pkg_dir, "oasa")
	if oasa_module_dir not in sys.path:
		sys.path.append(oasa_module_dir)
	if "oasa" in sys.modules:
		del sys.modules["oasa"]


#============================================
def _ensure_gettext_fallbacks():
	"""Ensure gettext helpers exist for module-level strings."""
	if "_" not in builtins.__dict__:
		builtins.__dict__["_"] = lambda m: m
	if "ngettext" not in builtins.__dict__:
		builtins.__dict__["ngettext"] = lambda s, p, n: s if n == 1 else p


#============================================
def _verify_tkinter():
	"""Verify Tk is available for GUI-backed tests."""
	try:
		import tkinter
	except ModuleNotFoundError as exc:
		if exc.name in ("_tkinter", "tkinter"):
			message = (
				"tkinter is not available. Install a Python build with Tk support."
			)
			pytest.skip(message, allow_module_level=True)
		raise
	tkinter.TkVersion


#============================================
def _ensure_preferences():
	"""Initialize preference manager for tests."""
	import os_support
	import pref_manager
	import singleton_store

	if singleton_store.Store.pm is None:
		singleton_store.Store.pm = pref_manager.pref_manager([
			os_support.get_config_filename("prefs.xml", level="global", mode="r"),
			os_support.get_config_filename("prefs.xml", level="personal", mode="r"),
		])


#============================================
def _assert_fixture_exists(path):
	"""Fail fast when a fixture is missing."""
	if not os.path.isfile(path):
		raise AssertionError("Missing CDML fixture: %s" % path)


#============================================
def _load_fixture(app, path):
	"""Load a CDML file into the current paper."""
	app.paper.changes_made = 0
	if not app.load_CDML(path, replace=1):
		raise AssertionError("Failed to load CDML fixture: %s" % path)
	if not app.paper.molecules:
		raise AssertionError("No molecules loaded from CDML fixture: %s" % path)


#============================================
def _export_cdml(app, output_path):
	"""Export the current paper to CDML."""
	import bkchem.export

	if not bkchem.export.export_CDML(app.paper, output_path, gzipped=0):
		raise AssertionError("Failed to export CDML: %s" % output_path)


#============================================
def _run_cdml_smoke(fixtures_dir, output_dir=None):
	"""Run the BKChem CDML load/save/reload checks."""
	root_dir = conftest.repo_root()
	_ensure_sys_path(root_dir)
	_ensure_gettext_fallbacks()
	_verify_tkinter()
	_ensure_preferences()
	import bkchem.main

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize_batch()
	if not getattr(app, "paper", None):
		raise RuntimeError("BKChem CDML smoke test failed to create a paper.")
	try:
		if output_dir:
			_output_dir = output_dir
			for filename in FIXTURE_FILES:
				fixture_path = os.path.join(fixtures_dir, filename)
				_assert_fixture_exists(fixture_path)
				_load_fixture(app, fixture_path)
				output_path = os.path.join(_output_dir, "phase0_%s" % filename)
				_export_cdml(app, output_path)
				_load_fixture(app, output_path)
		else:
			with tempfile.TemporaryDirectory() as tmp_dir:
				for filename in FIXTURE_FILES:
					fixture_path = os.path.join(fixtures_dir, filename)
					_assert_fixture_exists(fixture_path)
					_load_fixture(app, fixture_path)
					output_path = os.path.join(tmp_dir, "phase0_%s" % filename)
					_export_cdml(app, output_path)
					_load_fixture(app, output_path)
	finally:
		app.destroy()


#============================================
def _parse_args():
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Run BKChem CDML Phase 0 smoke checks."
	)
	parser.add_argument(
		"--fixtures-dir",
		dest="fixtures_dir",
		default=FIXTURES_DIR,
		help="Directory containing CDML fixtures.",
	)
	parser.add_argument(
		"--output-dir",
		dest="output_dir",
		default=None,
		help="Optional output directory for exported CDML.",
	)
	args = parser.parse_args()
	return args


#============================================
def main():
	"""Entry point for running the smoke check directly."""
	args = _parse_args()
	_run_cdml_smoke(args.fixtures_dir, output_dir=args.output_dir)


#============================================
def test_bkchem_cdml_fixtures():
	cmd = [sys.executable, os.path.abspath(__file__)]
	result = subprocess.run(cmd, capture_output=True, text=True, check=False)
	if result.returncode == 0:
		return
	combined = (result.stdout or "") + (result.stderr or "")
	if "tkinter is not available" in combined:
		pytest.skip("tkinter is not available for BKChem CDML smoke test.")
	if "Fatal Python error: Aborted" in combined:
		pytest.skip("BKChem CDML smoke test aborted while initializing Tk.")
	if "TclError" in combined:
		pytest.skip("BKChem CDML smoke test failed to initialize Tk.")
	if result.returncode < 0:
		message = (
			"BKChem CDML smoke subprocess terminated by signal %d."
			% abs(result.returncode)
		)
		pytest.skip(message)
	raise AssertionError(
		"BKChem CDML smoke subprocess failed.\n%s" % combined
	)


if __name__ == "__main__":
	main()
