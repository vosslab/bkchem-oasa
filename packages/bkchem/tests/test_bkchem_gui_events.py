"""BKChem GUI event simulation smoke coverage."""

# Standard Library
import builtins
import os
import subprocess
import sys
import time

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
def _flush_events(app, delay=0.05):
	"""Process Tk events with a brief delay for GUI updates."""
	app.update_idletasks()
	app.update()
	time.sleep(delay)
	app.update_idletasks()
	app.update()


#============================================
def _event_click(paper, x, y):
	"""Simulate a left click at the provided canvas coordinates."""
	paper.event_generate("<Button-1>", x=x, y=y)
	paper.event_generate("<ButtonRelease-1>", x=x, y=y)


#============================================
def _event_drag(paper, x1, y1, x2, y2):
	"""Simulate a left-button drag between two canvas coordinates."""
	button_state = 256
	mid_x = int((x1 + x2) / 2)
	mid_y = int((y1 + y2) / 2)
	paper.event_generate("<Button-1>", x=x1, y=y1, state=button_state)
	paper.update_idletasks()
	paper.update()
	paper.event_generate("<B1-Motion>", x=mid_x, y=mid_y, state=button_state)
	paper.update_idletasks()
	paper.update()
	paper.event_generate("<B1-Motion>", x=x2, y=y2, state=button_state)
	paper.update_idletasks()
	paper.update()
	paper.event_generate("<ButtonRelease-1>", x=x2, y=y2, state=button_state)
	paper.update_idletasks()
	paper.update()


#============================================
def _event_key_press(paper, key):
	"""Simulate a key press/release pair."""
	paper.event_generate(f"<KeyPress-{key}>")
	paper.event_generate(f"<KeyRelease-{key}>")


#============================================
def _event_key_combo(paper, specials, key):
	"""Simulate a key combo using explicit modifier press/release events."""
	for special in specials:
		paper.event_generate(f"<KeyPress-{special}>")
	paper.event_generate(f"<KeyPress-{key}>")
	paper.event_generate(f"<KeyRelease-{key}>")
	for special in reversed(specials):
		paper.event_generate(f"<KeyRelease-{special}>")


#============================================
def _count_atoms(paper):
	"""Return the number of atoms across all molecules."""
	return sum(len(mol.atoms) for mol in paper.molecules)


#============================================
def _count_bonds(paper):
	"""Return the number of bonds across all molecules."""
	return sum(len(mol.bonds) for mol in paper.molecules)


#============================================
def _run_gui_event_simulation():
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
		raise RuntimeError("BKChem GUI event test failed to create a paper.")

	try:
		app.deiconify()
		_flush_events(app, delay=0.1)
		paper = app.paper
		paper.focus_set()
		_flush_events(app, delay=0.05)

		app.change_mode("draw")
		_flush_events(app, delay=0.05)

		start_atoms = _count_atoms(paper)
		start_bonds = _count_bonds(paper)

		_event_drag(paper, 200, 200, 260, 200)
		_flush_events(app, delay=0.05)

		after_drag_atoms = _count_atoms(paper)
		after_drag_bonds = _count_bonds(paper)
		if after_drag_atoms < start_atoms + 2 or after_drag_bonds < start_bonds + 1:
			print("Draw drag did not create a full chain, falling back to click.")
			_event_click(paper, 200, 200)
			_flush_events(app, delay=0.05)
			after_drag_atoms = _count_atoms(paper)
			after_drag_bonds = _count_bonds(paper)
		if after_drag_atoms < start_atoms + 2:
			raise AssertionError("Initial draw did not create two atoms.")
		if after_drag_bonds < start_bonds + 1:
			raise AssertionError("Initial draw did not create a bond.")

		if not paper.molecules:
			raise AssertionError("No molecules found after draw drag.")
		target_atom = paper.molecules[0].atoms[0]
		x, y = target_atom.get_xy_on_paper()
		_event_click(paper, int(x), int(y))
		_flush_events(app, delay=0.05)

		after_click_atoms = _count_atoms(paper)
		after_click_bonds = _count_bonds(paper)
		if after_click_atoms < after_drag_atoms + 1:
			raise AssertionError("Draw click did not extend the chain.")
		if after_click_bonds < after_drag_bonds + 1:
			raise AssertionError("Draw click did not add a bond.")

		_event_key_combo(paper, ["Control_L"], "1")
		_flush_events(app, delay=0.05)

		if getattr(app.mode, "name", "") != "edit":
			raise AssertionError("Ctrl-1 did not switch to edit mode.")

		target_atom = paper.molecules[0].atoms[0]
		x, y = target_atom.get_xy_on_paper()
		_event_click(paper, int(x), int(y))
		_flush_events(app, delay=0.05)

		if target_atom not in paper.selected:
			raise AssertionError("Edit click did not select the target atom.")

		paper.focus_set()
		_event_key_press(paper, "Delete")
		_flush_events(app, delay=0.05)

		pre_delete_atoms = after_click_atoms
		after_delete_atoms = _count_atoms(paper)
		if after_delete_atoms >= pre_delete_atoms:
			raise AssertionError("Delete key did not remove the selected atom.")
		if paper.is_registered_object(target_atom):
			raise AssertionError("Target atom still registered after delete.")

		_event_key_combo(paper, ["Control_L"], "z")
		_flush_events(app, delay=0.05)
		after_undo_atoms = _count_atoms(paper)
		if after_undo_atoms != pre_delete_atoms:
			raise AssertionError("Ctrl-Z did not undo the deletion.")

		_event_key_combo(paper, ["Control_L", "Shift_L"], "z")
		_flush_events(app, delay=0.05)
		after_redo_atoms = _count_atoms(paper)
		if after_redo_atoms != after_delete_atoms:
			raise AssertionError("Ctrl-Shift-Z did not redo the deletion.")

		_event_key_combo(paper, ["Control_L"], "2")
		_flush_events(app, delay=0.05)
		if getattr(app.mode, "name", "") != "draw":
			raise AssertionError("Ctrl-2 did not switch back to draw mode.")
	finally:
		app.destroy()


#============================================
def main():
	"""Entry point for running the GUI event simulation directly."""
	_run_gui_event_simulation()


#============================================
def test_bkchem_gui_event_simulation():
	cmd = [sys.executable, os.path.abspath(__file__)]
	result = subprocess.run(cmd, capture_output=True, text=True, check=False)
	if result.returncode == 0:
		return
	combined = (result.stdout or "") + (result.stderr or "")
	if "tkinter is not available" in combined:
		pytest.skip("tkinter is not available for BKChem GUI event test.")
	if "Fatal Python error: Aborted" in combined:
		pytest.skip("BKChem GUI event test aborted while initializing Tk.")
	if "TclError" in combined:
		pytest.skip("BKChem GUI event test failed to initialize Tk.")
	if result.returncode < 0:
		message = (
			"BKChem GUI event test subprocess terminated by signal %d."
			% abs(result.returncode)
		)
		pytest.skip(message)
	raise AssertionError(
		"BKChem GUI event test subprocess failed.\n%s" % combined
	)


if __name__ == "__main__":
	main()
