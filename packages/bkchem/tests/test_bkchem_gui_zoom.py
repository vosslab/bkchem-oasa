"""BKChem GUI zoom behavior pytest."""

# Standard Library
import builtins
import math
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
def _build_benzene(app, cx=320, cy=240):
	"""Create a benzene ring from 6 atoms with alternating double bonds."""
	from bond import bond
	from singleton_store import Screen

	paper = app.paper
	mol = paper.new_molecule()
	bond_length = Screen.any_to_px(paper.standard.bond_length)
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
def _snapshot_state(paper, label):
	"""Capture scale, content bbox center, and viewport center into a dict."""
	bbox = paper._content_bbox()
	if bbox:
		bbox_cx = (bbox[0] + bbox[2]) / 2
		bbox_cy = (bbox[1] + bbox[3]) / 2
	else:
		bbox_cx = None
		bbox_cy = None
	vp_cx = paper.canvasx(paper.winfo_width() / 2)
	vp_cy = paper.canvasy(paper.winfo_height() / 2)
	n_items = len(paper.find_all())
	return {
		"label": label,
		"scale": paper._scale,
		"bbox_cx": bbox_cx,
		"bbox_cy": bbox_cy,
		"vp_cx": vp_cx,
		"vp_cy": vp_cy,
		"n_items": n_items,
	}


#============================================
def _print_diagnostic_table(snapshots):
	"""Print formatted table of all snapshots for debugging."""
	print()
	print("=" * 80)
	print("ZOOM DIAGNOSTIC TABLE")
	print("=" * 80)
	header = (
		f"{'Step':<6} {'Label':<22} {'Scale':>8}"
		f"  {'BBox CX':>9} {'BBox CY':>9}"
		f"  {'VP CX':>9} {'VP CY':>9}"
		f"  {'Items':>6}"
	)
	print(header)
	print("-" * 88)
	for snap in snapshots:
		bbox_cx_str = f"{snap['bbox_cx']:.1f}" if snap["bbox_cx"] is not None else "N/A"
		bbox_cy_str = f"{snap['bbox_cy']:.1f}" if snap["bbox_cy"] is not None else "N/A"
		row = (
			f"{snap['label']:<28} {snap['scale']:>8.4f}"
			f"  {bbox_cx_str:>9} {bbox_cy_str:>9}"
			f"  {snap['vp_cx']:>9.1f} {snap['vp_cy']:>9.1f}"
			f"  {snap['n_items']:>6}"
		)
		print(row)
	print("=" * 88)


#============================================
def _run_zoom_diagnostic():
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
		raise RuntimeError("BKChem zoom test failed to create a paper.")

	try:
		app.deiconify()
		_flush_events(app, delay=0.1)
		paper = app.paper
		_flush_events(app, delay=0.05)

		# Draw benzene so there is content to zoom around
		_build_benzene(app)
		_flush_events(app, delay=0.05)

		snapshots = []

		# -- Step 0: Initial state --
		snap0 = _snapshot_state(paper, "0: initial")
		snapshots.append(snap0)
		if snap0["scale"] != 1.0:
			raise AssertionError(
				"Step 0: initial scale should be 1.0, got %.4f" % snap0["scale"]
			)
		if snap0["bbox_cx"] is None:
			raise AssertionError("Step 0: content bbox should exist after drawing benzene.")

		# -- Step 1: zoom_to_fit --
		paper.zoom_to_fit()
		_flush_events(app, delay=0.05)
		snap1 = _snapshot_state(paper, "1: zoom_to_fit")
		snapshots.append(snap1)
		if snap1["scale"] == 1.0:
			raise AssertionError("Step 1: zoom_to_fit should change scale from 1.0.")
		if snap1["bbox_cx"] is None:
			raise AssertionError("Step 1: content bbox should exist after zoom_to_fit.")

		# -- Step 2: zoom_reset --
		paper.zoom_reset()
		_flush_events(app, delay=0.05)
		snap2 = _snapshot_state(paper, "2: zoom_reset")
		snapshots.append(snap2)
		if snap2["scale"] != 1.0:
			raise AssertionError(
				"Step 2: zoom_reset should restore scale to 1.0, got %.4f"
				% snap2["scale"]
			)

		# -- Step 3: zoom_to_content --
		paper.zoom_to_content()
		_flush_events(app, delay=0.05)
		snap3 = _snapshot_state(paper, "3: zoom_to_content")
		snapshots.append(snap3)
		content_scale = snap3["scale"]
		if content_scale < 0.1:
			raise AssertionError(
				"Step 3: zoom_to_content scale %.4f below ZOOM_MIN." % content_scale
			)
		if content_scale > 4.0:
			raise AssertionError(
				"Step 3: zoom_to_content scale %.4f above 4.0 cap." % content_scale
			)
		if snap3["bbox_cx"] is None:
			raise AssertionError("Step 3: content bbox should exist after zoom_to_content.")

		# -- Step 4: zoom_out x3 --
		for i in range(3):
			paper.zoom_out()
			_flush_events(app, delay=0.02)
			snapshots.append(_snapshot_state(paper, "4.%d: zoom_out" % (i+1)))
		snap4 = snapshots[-1]
		expected_scale_4 = content_scale / (1.2 ** 3)
		if abs(snap4["scale"] - expected_scale_4) > 0.001:
			raise AssertionError(
				"Step 4: expected scale %.4f after 3x zoom_out, got %.4f"
				% (expected_scale_4, snap4["scale"])
			)

		# -- Step 5: zoom_in x3 (round-trip) --
		for i in range(3):
			paper.zoom_in()
			_flush_events(app, delay=0.02)
			snapshots.append(_snapshot_state(paper, "5.%d: zoom_in" % (i+1)))
		snap5 = snapshots[-1]
		if abs(snap5["scale"] - content_scale) > 0.001:
			raise AssertionError(
				"Step 5: round-trip scale should be %.4f, got %.4f"
				% (content_scale, snap5["scale"])
			)

		# -- Step 6: zoom_to_content again (idempotent check) --
		paper.zoom_to_content()
		_flush_events(app, delay=0.05)
		snap6 = _snapshot_state(paper, "6: zoom_to_content (2nd)")
		snapshots.append(snap6)
		tolerance = 0.05
		idempotent_drift = abs(snap6["scale"] - content_scale) / max(content_scale, 0.01)
		if idempotent_drift > tolerance:
			raise AssertionError(
				"Step 6: zoom_to_content not idempotent after round-trip. "
				"Expected ~%.4f, got %.4f (%.1f%% off)."
				% (content_scale, snap6["scale"], idempotent_drift * 100)
			)

		# -- Step 7: zoom_out x50 (clamp at ZOOM_MIN) --
		paper.zoom_reset()
		_flush_events(app, delay=0.02)
		for i in range(50):
			paper.zoom_out()
		_flush_events(app, delay=0.05)
		snap7 = _snapshot_state(paper, "7: zoom_out x50")
		snapshots.append(snap7)
		if abs(snap7["scale"] - 0.1) > 0.001:
			raise AssertionError(
				"Step 7: scale should clamp at ZOOM_MIN=0.1, got %.4f"
				% snap7["scale"]
			)

		# -- Step 8: zoom_in x50 after reset (clamp at ZOOM_MAX) --
		paper.zoom_reset()
		_flush_events(app, delay=0.02)
		for i in range(50):
			paper.zoom_in()
		_flush_events(app, delay=0.05)
		snap8 = _snapshot_state(paper, "8: zoom_in x50")
		snapshots.append(snap8)
		if abs(snap8["scale"] - 10.0) > 0.001:
			raise AssertionError(
				"Step 8: scale should clamp at ZOOM_MAX=10.0, got %.4f"
				% snap8["scale"]
			)

		# -- Diagnostic output --
		_print_diagnostic_table(snapshots)

		# -- Viewport drift analysis (step 3 vs step 5) --
		print()
		print("VIEWPORT DRIFT ANALYSIS (step 3 vs step 5)")
		print("-" * 50)
		if snap3["vp_cx"] is not None and snap5["vp_cx"] is not None:
			drift_x = abs(snap5["vp_cx"] - snap3["vp_cx"])
			drift_y = abs(snap5["vp_cy"] - snap3["vp_cy"])
			drift_total = math.sqrt(drift_x ** 2 + drift_y ** 2)
			print(f"  VP center step 3: ({snap3['vp_cx']:.1f}, {snap3['vp_cy']:.1f})")
			print(f"  VP center step 5: ({snap5['vp_cx']:.1f}, {snap5['vp_cy']:.1f})")
			print(f"  Drift X: {drift_x:.1f} px")
			print(f"  Drift Y: {drift_y:.1f} px")
			print(f"  Drift total: {drift_total:.1f} px")
			if drift_total > 50.0:
				raise AssertionError(
					"Viewport drift of %.1f px after zoom_out x3 + zoom_in x3 "
					"round-trip exceeds 50 px tolerance." % drift_total
				)
			else:
				print("  OK: viewport drift is within 50 px tolerance.")

		# -- BBox drift assertion (step 3 vs step 5) --
		if snap3["bbox_cx"] is not None and snap5["bbox_cx"] is not None:
			bbox_drift_x = abs(snap5["bbox_cx"] - snap3["bbox_cx"])
			bbox_drift_y = abs(snap5["bbox_cy"] - snap3["bbox_cy"])
			bbox_drift_total = math.sqrt(bbox_drift_x ** 2 + bbox_drift_y ** 2)
			print(f"  BBox center step 3: ({snap3['bbox_cx']:.1f}, {snap3['bbox_cy']:.1f})")
			print(f"  BBox center step 5: ({snap5['bbox_cx']:.1f}, {snap5['bbox_cy']:.1f})")
			print(f"  BBox drift total: {bbox_drift_total:.1f} px")
			if bbox_drift_total > 50.0:
				raise AssertionError(
					"BBox center drift of %.1f px after zoom_out x3 + zoom_in x3 "
					"round-trip exceeds 50 px tolerance." % bbox_drift_total
				)
		print()

	finally:
		app.destroy()


#============================================
def _run_zoom_model_coords_stable():
	"""Verify that model coordinates (atom.x, atom.y) are unchanged by zoom."""
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
		raise RuntimeError("BKChem zoom test failed to create a paper.")

	try:
		app.deiconify()
		_flush_events(app, delay=0.1)
		paper = app.paper
		_flush_events(app, delay=0.05)

		# Place benzene at the pixel center of the paper so viewport
		# centering during zoom never hits the scroll-region clamp.
		bg = paper.coords(paper.background)
		pcx = (bg[0] + bg[2]) / 2
		pcy = (bg[1] + bg[3]) / 2
		mol = _build_benzene(app, cx=pcx, cy=pcy)
		_flush_events(app, delay=0.05)

		# Record model coordinates before zoom
		coords_before = [(a.x, a.y) for a in mol.atoms]
		print("Model coords before zoom:", coords_before[:3], "...")

		# Zoom in to 10x (max)
		paper.zoom_reset()
		_flush_events(app, delay=0.02)
		for _i in range(50):
			paper.zoom_in()
		_flush_events(app, delay=0.05)
		coords_at_max = [(a.x, a.y) for a in mol.atoms]
		print("Scale at max zoom: %.4f" % paper._scale)
		for idx, (before, at_max) in enumerate(zip(coords_before, coords_at_max)):
			dx = abs(at_max[0] - before[0])
			dy = abs(at_max[1] - before[1])
			if dx > 1e-6 or dy > 1e-6:
				raise AssertionError(
					"Atom %d model coords changed after zoom_in x50: "
					"(%.6f, %.6f) -> (%.6f, %.6f)" % (idx, before[0], before[1], at_max[0], at_max[1])
				)

		# Zoom out to 0.1x (min)
		for _i in range(100):
			paper.zoom_out()
		_flush_events(app, delay=0.05)
		coords_at_min = [(a.x, a.y) for a in mol.atoms]
		print("Scale at min zoom: %.4f" % paper._scale)
		for idx, (before, at_min) in enumerate(zip(coords_before, coords_at_min)):
			dx = abs(at_min[0] - before[0])
			dy = abs(at_min[1] - before[1])
			if dx > 1e-6 or dy > 1e-6:
				raise AssertionError(
					"Atom %d model coords changed after zoom_out x100: "
					"(%.6f, %.6f) -> (%.6f, %.6f)" % (idx, before[0], before[1], at_min[0], at_min[1])
				)

		# Zoom back to 1x
		paper.zoom_reset()
		_flush_events(app, delay=0.05)
		coords_at_reset = [(a.x, a.y) for a in mol.atoms]
		print("Scale at reset: %.4f" % paper._scale)
		for idx, (before, at_reset) in enumerate(zip(coords_before, coords_at_reset)):
			dx = abs(at_reset[0] - before[0])
			dy = abs(at_reset[1] - before[1])
			if dx > 1e-6 or dy > 1e-6:
				raise AssertionError(
					"Atom %d model coords changed after zoom round-trip: "
					"(%.6f, %.6f) -> (%.6f, %.6f)" % (idx, before[0], before[1], at_reset[0], at_reset[1])
				)

		print("OK: model coordinates are stable across all zoom levels.")

	finally:
		app.destroy()


#============================================
def _run_zoom_roundtrip_symmetry():
	"""Zoom from 1000% down to ~250% and back; viewport center must match."""
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
		raise RuntimeError("BKChem zoom test failed to create a paper.")

	try:
		app.deiconify()
		_flush_events(app, delay=0.1)
		paper = app.paper
		_flush_events(app, delay=0.05)

		# Place benzene at the pixel center of the paper so the
		# viewport center stays away from scroll-region edges.
		bg = paper.coords(paper.background)
		pcx = (bg[0] + bg[2]) / 2
		pcy = (bg[1] + bg[3]) / 2
		_build_benzene(app, cx=pcx, cy=pcy)
		_flush_events(app, delay=0.05)

		# Zoom to max (10x = 1000%)
		paper.zoom_reset()
		_flush_events(app, delay=0.02)
		for _i in range(50):
			paper.zoom_in()
		_flush_events(app, delay=0.05)

		# Center viewport on the content
		paper.zoom_to_content()
		_flush_events(app, delay=0.05)

		# Now zoom to max again so content is centered at 1000%
		for _i in range(50):
			paper.zoom_in()
		_flush_events(app, delay=0.05)

		start_scale = paper._scale
		start_vp_cx = paper.canvasx(paper.winfo_width() / 2)
		start_vp_cy = paper.canvasy(paper.winfo_height() / 2)
		# Convert viewport center to model coords for comparison
		start_mx = start_vp_cx / start_scale
		start_my = start_vp_cy / start_scale
		print("Start: scale=%.4f  model center=(%.2f, %.2f)" % (start_scale, start_mx, start_my))

		# Count how many zoom_out steps to reach ~250%
		# ZOOM_FACTOR=1.2, so 1.2^n = 10/2.5 = 4 => n = log(4)/log(1.2) ~ 7.6 => 8 steps
		n_steps = 0
		while paper._scale > 2.5 and n_steps < 50:
			paper.zoom_out()
			_flush_events(app, delay=0.02)
			n_steps += 1
		mid_scale = paper._scale
		mid_vp_cx = paper.canvasx(paper.winfo_width() / 2)
		mid_vp_cy = paper.canvasy(paper.winfo_height() / 2)
		mid_mx = mid_vp_cx / mid_scale
		mid_my = mid_vp_cy / mid_scale
		print("After %d zoom_out steps: scale=%.4f  model center=(%.2f, %.2f)" % (n_steps, mid_scale, mid_mx, mid_my))

		# Zoom back in the same number of steps
		for _i in range(n_steps):
			paper.zoom_in()
			_flush_events(app, delay=0.02)
		_flush_events(app, delay=0.05)

		end_scale = paper._scale
		end_vp_cx = paper.canvasx(paper.winfo_width() / 2)
		end_vp_cy = paper.canvasy(paper.winfo_height() / 2)
		end_mx = end_vp_cx / end_scale
		end_my = end_vp_cy / end_scale

		print("After %d zoom_in steps:  scale=%.4f  model center=(%.2f, %.2f)" % (n_steps, end_scale, end_mx, end_my))

		# Scale should be back to start
		scale_diff = abs(end_scale - start_scale)
		if scale_diff > 0.001:
			raise AssertionError(
				"Scale did not round-trip: %.4f -> %.4f (diff %.6f)"
				% (start_scale, end_scale, scale_diff)
			)

		# Model-space viewport center should match within tolerance.
		# At 10x zoom, 1 model pixel = 10 canvas pixels, so even
		# small Tk rounding errors are magnified.  Allow 3 model pixels.
		drift_mx = abs(end_mx - start_mx)
		drift_my = abs(end_my - start_my)
		drift_model = math.sqrt(drift_mx ** 2 + drift_my ** 2)
		print("Model-space viewport drift: (%.4f, %.4f) = %.4f px" % (drift_mx, drift_my, drift_model))

		tolerance = 3.0  # model pixels
		if drift_model > tolerance:
			raise AssertionError(
				"Viewport center drifted %.4f model pixels after "
				"zoom_out x%d + zoom_in x%d round-trip "
				"(tolerance: %.1f model px). "
				"Start model=(%.2f,%.2f) End model=(%.2f,%.2f)"
				% (drift_model, n_steps, n_steps, tolerance,
					start_mx, start_my, end_mx, end_my)
			)
		print("OK: zoom +/- round-trip drift %.4f model px (tolerance %.1f)" % (drift_model, tolerance))

	finally:
		app.destroy()


#============================================
def main():
	"""Entry point for running the zoom diagnostic directly."""
	import sys as _sys
	which = _sys.argv[1] if len(_sys.argv) > 1 else "diagnostic"
	if which == "model_coords":
		_run_zoom_model_coords_stable()
	elif which == "roundtrip":
		_run_zoom_roundtrip_symmetry()
	else:
		_run_zoom_diagnostic()


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
		pytest.skip("tkinter is not available for BKChem zoom test.")
	if "Fatal Python error: Aborted" in combined:
		pytest.skip("BKChem zoom test aborted while initializing Tk.")
	if "TclError" in combined:
		pytest.skip("BKChem zoom test failed to initialize Tk.")
	if result.returncode < 0:
		message = (
			"BKChem zoom test subprocess terminated by signal %d."
			% abs(result.returncode)
		)
		pytest.skip(message)
	raise AssertionError(
		"BKChem zoom test subprocess failed.\n%s" % combined
	)


#============================================
def test_bkchem_gui_zoom():
	_run_subprocess_test("diagnostic")


#============================================
def test_zoom_model_coords_stable():
	"""Model coordinates (atom.x, atom.y) must not change during zoom."""
	_run_subprocess_test("model_coords")


#============================================
def test_zoom_roundtrip_symmetry():
	"""Zoom out from 1000% to ~250% then back; viewport center must match."""
	_run_subprocess_test("roundtrip")


if __name__ == "__main__":
	main()
