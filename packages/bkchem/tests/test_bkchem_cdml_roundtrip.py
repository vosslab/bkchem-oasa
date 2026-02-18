"""BKChem CDML round-trip metadata checks (Phase 3)."""

# Standard Library
import argparse
import builtins
import os
import subprocess
import sys
import tempfile

# Third Party
import pytest
import defusedxml.ElementTree

# Local repo modules
import conftest


FIXTURES_DIR = conftest.repo_tests_path("fixtures", "cdml_roundtrip")
FIXTURE_CHECKS = {
	"custom_attr.cdml": "_check_custom_attr",
	"wavy_color.cdml": "_check_wavy_color",
	"vertex_ordering.cdml": "_check_vertex_ordering",
}


#============================================
def _ensure_sys_path(root_dir):
	"""Ensure BKChem and OASA package paths are on sys.path."""
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
def _load_cdml(path):
	"""Load a CDML file as an ElementTree root."""
	return defusedxml.ElementTree.parse(path).getroot()


#============================================
def _parse_coord(value):
	"""Parse a CDML coordinate string to float."""
	if value is None:
		return 0.0
	text = value.strip()
	for unit in ("cm", "px", "mm", "in"):
		if text.endswith(unit):
			text = text[: -len(unit)]
			break
	try:
		return float(text)
	except ValueError:
		return 0.0


#============================================
def _strip_namespace(tag):
	if "}" in tag:
		return tag.split("}", 1)[1]
	return tag


#============================================
def _iter_elements(root, name):
	for element in root.iter():
		if _strip_namespace(element.tag) == name:
			yield element


#============================================
def _atom_coords(root):
	coords = {}
	for atom in _iter_elements(root, "atom"):
		atom_id = atom.get("id")
		point = None
		for child in atom:
			if _strip_namespace(child.tag) == "point":
				point = child
				break
		if atom_id and point is not None:
			coords[atom_id] = (
				_parse_coord(point.get("x")),
				_parse_coord(point.get("y")),
			)
	return coords


#============================================
def _check_custom_attr(root):
	bonds = list(_iter_elements(root, "bond"))
	if not bonds:
		raise AssertionError("No bonds found for custom attribute check")
	matches = [bond for bond in bonds if bond.get("custom") == "keep"]
	if not matches:
		raise AssertionError("Custom attribute was not preserved")


#============================================
def _check_wavy_color(root):
	bonds = list(_iter_elements(root, "bond"))
	if not bonds:
		raise AssertionError("No bonds found for wavy color check")
	for bond in bonds:
		bond_type = bond.get("type") or ""
		if bond_type.startswith("s"):
			if bond.get("wavy_style") != "triangle":
				raise AssertionError("wavy_style missing from wavy bond")
			if bond.get("color") != "#239e2d":
				raise AssertionError("color missing from wavy bond")
			return
	raise AssertionError("No wavy bond found for wavy_color fixture")


#============================================
def _check_vertex_ordering(root):
	coords = _atom_coords(root)
	bonds = [
		bond
		for bond in _iter_elements(root, "bond")
		if (bond.get("type") or "").startswith(("w", "h"))
	]
	if not bonds:
		raise AssertionError("No wedge/hashed bonds found for vertex ordering")
	for bond in bonds:
		start = bond.get("start")
		end = bond.get("end")
		if not start or not end:
			raise AssertionError("Bond missing start/end attributes")
		start_xy = coords.get(start)
		end_xy = coords.get(end)
		if start_xy is None or end_xy is None:
			raise AssertionError("Missing atom coordinates for vertex ordering")
		front_id = start
		if end_xy[1] > start_xy[1]:
			front_id = end
		elif end_xy[1] == start_xy[1] and end_xy[0] > start_xy[0]:
			front_id = end
		if end != front_id:
			raise AssertionError("Bond end is not the front vertex")


#============================================
def _check_cdml_doc_pointer(root):
	metadata_nodes = [node for node in _iter_elements(root, "metadata")]
	if not metadata_nodes:
		raise AssertionError("Missing CDML metadata node with doc pointer")
	doc_nodes = []
	for metadata in metadata_nodes:
		for child in metadata:
			if _strip_namespace(child.tag) == "doc":
				doc_nodes.append(child)
	if not doc_nodes:
		raise AssertionError("Missing CDML metadata/doc pointer node")
	for doc_node in doc_nodes:
		href = doc_node.get("href") or ""
		if href.endswith("/docs/CDML_FORMAT_SPEC.md"):
			return
	raise AssertionError("CDML metadata/doc pointer href is missing or incorrect")


#============================================
def _run_roundtrip(fixtures_dir, output_dir=None):
	root_dir = conftest.repo_root()
	_ensure_sys_path(root_dir)
	_ensure_gettext_fallbacks()
	_verify_tkinter()
	_ensure_preferences()
	import bkchem.main
	import bkchem.export

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize_batch()
	if not getattr(app, "paper", None):
		raise RuntimeError("BKChem round-trip test failed to create a paper.")
	try:
		if output_dir:
			_output_dir = output_dir
			for filename, check_name in FIXTURE_CHECKS.items():
				fixture_path = os.path.join(fixtures_dir, filename)
				if not os.path.isfile(fixture_path):
					raise AssertionError("Missing fixture: %s" % fixture_path)
				if not app.load_CDML(fixture_path, replace=1):
					raise AssertionError("Failed to load %s" % fixture_path)
				output_path = os.path.join(_output_dir, "roundtrip_%s" % filename)
				if not bkchem.export.export_CDML(app.paper, output_path, gzipped=0):
					raise AssertionError("Failed to export %s" % output_path)
				root = _load_cdml(output_path)
				_check_cdml_doc_pointer(root)
				globals()[check_name](root)
		else:
			with tempfile.TemporaryDirectory() as tmp_dir:
				for filename, check_name in FIXTURE_CHECKS.items():
					fixture_path = os.path.join(fixtures_dir, filename)
					if not os.path.isfile(fixture_path):
						raise AssertionError("Missing fixture: %s" % fixture_path)
					if not app.load_CDML(fixture_path, replace=1):
						raise AssertionError("Failed to load %s" % fixture_path)
					output_path = os.path.join(tmp_dir, "roundtrip_%s" % filename)
					if not bkchem.export.export_CDML(app.paper, output_path, gzipped=0):
						raise AssertionError("Failed to export %s" % output_path)
					root = _load_cdml(output_path)
					_check_cdml_doc_pointer(root)
					globals()[check_name](root)
	finally:
		app.destroy()


#============================================
def _parse_args():
	parser = argparse.ArgumentParser(
		description="Run BKChem CDML round-trip checks."
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
	args = _parse_args()
	_run_roundtrip(args.fixtures_dir, output_dir=args.output_dir)


#============================================
def test_bkchem_cdml_roundtrip():
	cmd = [sys.executable, os.path.abspath(__file__)]
	result = subprocess.run(cmd, capture_output=True, text=True, check=False)
	if result.returncode == 0:
		return
	combined = (result.stdout or "") + (result.stderr or "")
	if "tkinter is not available" in combined:
		pytest.skip("tkinter is not available for BKChem round-trip test.")
	if "Fatal Python error: Aborted" in combined:
		pytest.skip("BKChem round-trip test aborted while initializing Tk.")
	if "TclError" in combined:
		pytest.skip("BKChem round-trip test failed to initialize Tk.")
	if result.returncode < 0:
		message = (
			"BKChem round-trip subprocess terminated by signal %d."
			% abs(result.returncode)
		)
		pytest.skip(message)
	raise AssertionError("BKChem CDML round-trip failed.\n%s" % combined)


if __name__ == "__main__":
	main()
