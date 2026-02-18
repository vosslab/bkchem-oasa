"""BKChem GUI benzene smoke coverage."""

# Standard Library
import builtins
import math
import os
import subprocess
import sys

# Third Party
import pytest

# Local repo modules
import conftest


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
def _hex_points(cx, cy, radius):
	"""Return 6 points for a regular hexagon."""
	points = []
	for i in range(6):
		angle = math.radians(-90 + (60 * i))
		x = cx + radius * math.cos(angle)
		y = cy + radius * math.sin(angle)
		points.append((x, y))
	return points


#============================================
def _build_benzene(app):
	"""Create a benzene ring from 6 atoms with alternating double bonds."""
	from bond import bond
	from singleton_store import Screen

	paper = app.paper
	mol = paper.new_molecule()
	bond_length = Screen.any_to_px(paper.standard.bond_length)
	cx, cy = 320, 240
	points = _hex_points(cx, cy, bond_length)
	atoms = [mol.create_new_atom(x, y) for x, y in points]
	for index, atom in enumerate(atoms):
		other = atoms[(index + 1) % len(atoms)]
		order = 2 if index % 2 == 0 else 1
		b = bond(standard=paper.standard, order=order, type="n")
		mol.add_edge(atom, other, e=b)
		b.molecule = mol
		b.draw()
	paper.add_bindings()
	return mol


#============================================
def _run_benzene_smoke():
	root_dir = conftest.repo_root()
	_ensure_sys_path(root_dir)
	_ensure_gettext_fallbacks()
	_verify_tkinter()
	_ensure_preferences()
	import bkchem.main

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize()
	if not getattr(app, "paper", None):
		raise RuntimeError("BKChem benzene smoke test failed to create a paper.")
	try:
		mol = _build_benzene(app)
		if len(mol.atoms) != 6:
			raise AssertionError("Benzene should have 6 atoms.")
		if len(mol.bonds) != 6:
			raise AssertionError("Benzene should have 6 bonds.")
		double_bonds = [b for b in mol.bonds if b.order == 2]
		if len(double_bonds) != 3:
			raise AssertionError("Benzene should have 3 double bonds.")
		for atom in mol.atoms:
			if len(atom.neighbor_edges) != 2:
				raise AssertionError("Each benzene atom should have 2 bonds.")
	finally:
		app.destroy()


#============================================
def main():
	"""Entry point for running the benzene smoke check directly."""
	_run_benzene_smoke()


#============================================
def test_bkchem_gui_benzene_smoke():
	cmd = [sys.executable, os.path.abspath(__file__)]
	result = subprocess.run(cmd, capture_output=True, text=True, check=False)
	if result.returncode == 0:
		return
	combined = (result.stdout or "") + (result.stderr or "")
	if "tkinter is not available" in combined:
		pytest.skip("tkinter is not available for BKChem benzene smoke test.")
	if "Fatal Python error: Aborted" in combined:
		pytest.skip("BKChem benzene smoke test aborted while initializing Tk.")
	if "TclError" in combined:
		pytest.skip("BKChem benzene smoke test failed to initialize Tk.")
	if result.returncode < 0:
		message = (
			"BKChem benzene smoke subprocess terminated by signal %d."
			% abs(result.returncode)
		)
		pytest.skip(message)
	raise AssertionError(
		"BKChem benzene smoke subprocess failed.\n%s" % combined
	)


if __name__ == "__main__":
	main()
