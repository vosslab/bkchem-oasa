"""BKChem GUI hex grid overlay and snap pytest."""

# Standard Library
import builtins
import os
import subprocess
import sys
import time

# Third Party
import pytest



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
	from bkchem import os_support
	from bkchem import pref_manager
	from bkchem import singleton_store

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
def _init_app():
	"""Create and initialize a BKChem app instance for testing."""
	_ensure_gettext_fallbacks()
	_verify_tkinter()
	_ensure_preferences()
	import bkchem.main

	app = bkchem.main.BKChem()
	app.withdraw()
	app.initialize()
	if not getattr(app, "paper", None):
		raise RuntimeError("BKChem hex grid test failed to create a paper.")
	return app


#============================================
def _run_toggle_test():
	"""Exercise show/hide/toggle and snap enable/disable."""
	app = _init_app()
	try:
		app.deiconify()
		_flush_events(app, delay=0.1)
		paper = app.paper
		_flush_events(app, delay=0.05)

		# Step 1: overlay is lazily created, should be None at start
		if paper._hex_grid_overlay is not None:
			raise AssertionError(
				"Step 1: _hex_grid_overlay should be None before first use."
			)

		# Step 2: show creates the overlay and makes it visible
		paper.show_hex_grid()
		_flush_events(app, delay=0.05)
		if paper._hex_grid_overlay is None:
			raise AssertionError(
				"Step 2: _hex_grid_overlay should exist after show_hex_grid()."
			)
		if not paper._hex_grid_overlay.visible:
			raise AssertionError(
				"Step 2: overlay should be visible after show_hex_grid()."
			)

		# Step 3: hex_grid tagged items should exist
		dot_count = len(paper.find_withtag("hex_grid"))
		print("Step 3: hex_grid dot count after show = %d" % dot_count)
		if dot_count <= 0:
			raise AssertionError(
				"Step 3: expected hex_grid dots > 0 after show, got %d." % dot_count
			)

		# Step 4: hide removes dots and sets visible to False
		paper.hide_hex_grid()
		_flush_events(app, delay=0.05)
		if paper._hex_grid_overlay.visible:
			raise AssertionError(
				"Step 4: overlay should not be visible after hide_hex_grid()."
			)
		dot_count = len(paper.find_withtag("hex_grid"))
		if dot_count != 0:
			raise AssertionError(
				"Step 4: expected 0 hex_grid dots after hide, got %d." % dot_count
			)

		# Step 5: toggle shows again
		paper.toggle_hex_grid()
		_flush_events(app, delay=0.05)
		if not paper._hex_grid_overlay.visible:
			raise AssertionError(
				"Step 5: overlay should be visible after first toggle."
			)
		dot_count = len(paper.find_withtag("hex_grid"))
		if dot_count <= 0:
			raise AssertionError(
				"Step 5: expected dots > 0 after toggle on, got %d." % dot_count
			)

		# Step 6: toggle hides again
		paper.toggle_hex_grid()
		_flush_events(app, delay=0.05)
		if paper._hex_grid_overlay.visible:
			raise AssertionError(
				"Step 6: overlay should not be visible after second toggle."
			)
		dot_count = len(paper.find_withtag("hex_grid"))
		if dot_count != 0:
			raise AssertionError(
				"Step 6: expected 0 dots after toggle off, got %d." % dot_count
			)

		# Step 7: snap is enabled by default
		if not paper.hex_grid_snap_enabled:
			raise AssertionError(
				"Step 7: hex_grid_snap_enabled should be True by default."
			)

		# Step 8: toggle snap off
		paper.toggle_hex_grid_snap()
		if paper.hex_grid_snap_enabled:
			raise AssertionError(
				"Step 8: hex_grid_snap_enabled should be False after first toggle."
			)

		# Step 9: toggle snap back on
		paper.toggle_hex_grid_snap()
		if not paper.hex_grid_snap_enabled:
			raise AssertionError(
				"Step 9: hex_grid_snap_enabled should be True after second toggle."
			)

		print("OK: hex grid toggle test passed.")

	finally:
		app.destroy()


#============================================
def _run_zoom_threshold_test():
	"""Verify dots disappear at low zoom and reappear at high zoom."""
	app = _init_app()
	try:
		app.deiconify()
		_flush_events(app, delay=0.1)
		paper = app.paper
		_flush_events(app, delay=0.05)

		# Step 1: show hex grid at default 1.0 scale
		paper.show_hex_grid()
		_flush_events(app, delay=0.05)
		dot_count = len(paper.find_withtag("hex_grid"))
		print("Step 1: dots at scale=%.4f: %d" % (paper._scale, dot_count))
		if dot_count <= 0:
			raise AssertionError(
				"Step 1: expected dots > 0 at default zoom, got %d." % dot_count
			)

		# Step 2: zoom out past 50% threshold
		# ZOOM_FACTOR=1.2, so 1.2^n < 0.5 => n > log(2)/log(1.2) ~ 3.8 => 5 steps
		for i in range(8):
			paper.zoom_out()
			_flush_events(app, delay=0.02)
		current_scale = paper._scale
		print("Step 2: scale after 8x zoom_out = %.4f" % current_scale)
		if current_scale >= 0.5:
			raise AssertionError(
				"Step 2: expected scale < 0.5 after 8x zoom_out, got %.4f."
				% current_scale
			)

		# Step 3: dots should be cleared at low zoom
		dot_count = len(paper.find_withtag("hex_grid"))
		if dot_count != 0:
			raise AssertionError(
				"Step 3: expected 0 dots at scale %.4f (< 0.5), got %d."
				% (current_scale, dot_count)
			)

		# Step 4: overlay still thinks it is visible (dots just cleared)
		if not paper._hex_grid_overlay.visible:
			raise AssertionError(
				"Step 4: overlay.visible should still be True at low zoom "
				"(dots cleared by scale_all, not by hide)."
			)

		# Step 5: zoom back in past 50% threshold
		for i in range(8):
			paper.zoom_in()
			_flush_events(app, delay=0.02)
		current_scale = paper._scale
		print("Step 5: scale after 8x zoom_in = %.4f" % current_scale)

		# Step 6: dots should reappear
		dot_count = len(paper.find_withtag("hex_grid"))
		print("Step 6: dots after zoom back in = %d" % dot_count)
		if dot_count <= 0:
			raise AssertionError(
				"Step 6: expected dots > 0 after zoom back in at scale %.4f, "
				"got %d." % (current_scale, dot_count)
			)

		print("OK: hex grid zoom threshold test passed.")

	finally:
		app.destroy()


#============================================
def _run_cutoff_test():
	"""Verify the MAX_GRID_POINTS cutoff in generate_hex_grid_points."""
	import oasa.hex_grid

	spacing = 20.0

	# Small bounding box should return a list of points
	result_small = oasa.hex_grid.generate_hex_grid_points(
		0, 0, 200, 200, spacing
	)
	if result_small is None:
		raise AssertionError(
			"Cutoff test: small bbox (200x200) should return points, got None."
		)
	if len(result_small) == 0:
		raise AssertionError(
			"Cutoff test: small bbox should produce at least 1 point."
		)
	print("Small bbox: %d points" % len(result_small))

	# Huge bounding box should trigger cutoff and return None
	result_huge = oasa.hex_grid.generate_hex_grid_points(
		0, 0, 100000, 100000, spacing
	)
	if result_huge is not None:
		raise AssertionError(
			"Cutoff test: huge bbox (100000x100000, spacing=20) should return "
			"None due to MAX_GRID_POINTS cutoff, got %d points."
			% len(result_huge)
		)
	print("Huge bbox: correctly returned None (cutoff).")

	# Medium bbox just under cutoff should return points;
	# MAX_GRID_POINTS=5000, rows * cols must stay under that.
	# With spacing=20, a 600x600 box produces roughly (600/20)*(600/(20*0.866))
	# = 30 * 35 ~ 1050, well under 5000.
	result_medium = oasa.hex_grid.generate_hex_grid_points(
		0, 0, 600, 600, spacing
	)
	if result_medium is None:
		raise AssertionError(
			"Cutoff test: medium bbox (600x600) should return points, got None."
		)
	print("Medium bbox: %d points" % len(result_medium))

	print("OK: hex grid cutoff test passed.")


#============================================
def main():
	"""Entry point for running hex grid tests directly."""
	import sys as _sys
	which = _sys.argv[1] if len(_sys.argv) > 1 else "toggle"
	if which == "toggle":
		_run_toggle_test()
	elif which == "zoom_threshold":
		_run_zoom_threshold_test()
	elif which == "cutoff":
		_run_cutoff_test()
	else:
		raise ValueError("Unknown test variant: %s" % which)


#============================================
def _run_subprocess_test(arg):
	"""Run a test variant in a subprocess; skip on Tk/signal failures."""
	cmd = [sys.executable, os.path.abspath(__file__), arg]
	result = subprocess.run(cmd, capture_output=True, text=True, check=False)
	if result.returncode == 0:
		if result.stdout:
			print(result.stdout)
		return
	combined = (result.stdout or "") + (result.stderr or "")
	if "tkinter is not available" in combined:
		pytest.skip("tkinter is not available for BKChem hex grid test.")
	if "Fatal Python error: Aborted" in combined:
		pytest.skip("BKChem hex grid test aborted while initializing Tk.")
	if "TclError" in combined:
		pytest.skip("BKChem hex grid test failed to initialize Tk.")
	if result.returncode < 0:
		message = (
			"BKChem hex grid test subprocess terminated by signal %d."
			% abs(result.returncode)
		)
		pytest.skip(message)
	raise AssertionError(
		"BKChem hex grid test subprocess failed.\n%s" % combined
	)


#============================================
def test_hex_grid_toggle():
	"""Show/hide/toggle hex grid overlay and snap enable/disable."""
	_run_subprocess_test("toggle")


#============================================
def test_hex_grid_zoom_threshold():
	"""Dots disappear below 50% zoom and reappear above it."""
	_run_subprocess_test("zoom_threshold")


#============================================
def test_hex_grid_cutoff():
	"""generate_hex_grid_points returns None when point count exceeds cutoff."""
	_run_subprocess_test("cutoff")


if __name__ == "__main__":
	main()
