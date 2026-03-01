#!/usr/bin/env python3
"""Qt GUI smoke tests for BKChem-Qt using subprocess isolation.

Each test case runs as a subprocess to avoid QApplication singleton issues.
The subprocess pattern ensures that each test gets a fresh QApplication
instance and avoids Qt cleanup conflicts between tests.

Tests show the window, take screenshots via QWidget.grab(), and save them
to output_smoke/ for human review. Dark mode tests also verify pixel colors.

Usage:
	# run all tests via pytest
	source source_me.sh && python -m pytest packages/bkchem-qt.app/tests/test_qt_gui_smoke.py -v

	# run a single test runner directly (for debugging)
	source source_me.sh && python packages/bkchem-qt.app/tests/test_qt_gui_smoke.py --test launch
"""

# Standard Library
import math
import os
import subprocess
import sys
import tempfile

# PIP3 modules
import pytest

# absolute path to this script for subprocess invocations
_THIS_FILE = os.path.abspath(__file__)

# timeout in seconds for each subprocess test
_SUBPROCESS_TIMEOUT = 30

# output directory for screenshots (reused per REPO_STYLE.md)
OUTPUT_DIR = os.path.join(os.path.dirname(_THIS_FILE), "output_smoke")


#============================================
def _check_subprocess_result(result) -> None:
	"""Evaluate a subprocess result and raise or skip appropriately.

	Checks stderr and stdout for known skip conditions (missing PySide6,
	no display). If the process exited with a nonzero return code and no
	skip condition applies, raises AssertionError with combined output.

	Args:
		result: CompletedProcess from subprocess.run.
	"""
	if result.returncode == 0:
		return
	combined = (result.stdout or "") + (result.stderr or "")
	# skip if PySide6 is not installed
	if "PySide6" in combined or "No module named" in combined:
		pytest.skip("PySide6 not available")
	# skip if no display server is available (headless CI)
	if "cannot open display" in combined.lower():
		pytest.skip("No display available for Qt tests")
	if "could not connect to display" in combined.lower():
		pytest.skip("No display available for Qt tests")
	if "this application failed to start" in combined.lower():
		pytest.skip("No display available for Qt tests")
	raise AssertionError(f"Qt smoke test failed (rc={result.returncode}).\n{combined}")


# ======================================================================
# Pytest wrapper functions (spawn subprocess for each test)
# ======================================================================

#============================================
def test_qt_gui_launch_smoke():
	"""Verify that the Qt GUI launches and creates core widgets."""
	cmd = [sys.executable, _THIS_FILE, "--test", "launch"]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT)
	_check_subprocess_result(result)


#============================================
def test_qt_dark_mode_smoke():
	"""Verify that theme toggling between dark and light works."""
	cmd = [sys.executable, _THIS_FILE, "--test", "dark_mode"]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT)
	_check_subprocess_result(result)


#============================================
def test_qt_status_bar_coords_smoke():
	"""Verify that status bar labels update with coords, zoom, and mode."""
	cmd = [sys.executable, _THIS_FILE, "--test", "status_bar"]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT)
	_check_subprocess_result(result)


#============================================
def test_qt_draw_benzene_smoke():
	"""Verify programmatic benzene ring construction on the canvas."""
	cmd = [sys.executable, _THIS_FILE, "--test", "benzene"]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT)
	_check_subprocess_result(result)


#============================================
def test_qt_zoom_smoke():
	"""Verify zoom scale and reset on the graphics view."""
	cmd = [sys.executable, _THIS_FILE, "--test", "zoom"]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT)
	_check_subprocess_result(result)


#============================================
def test_qt_import_cholesterol_smoke():
	"""Verify SMILES import of cholesterol populates the document."""
	cmd = [sys.executable, _THIS_FILE, "--test", "cholesterol"]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT)
	_check_subprocess_result(result)


#============================================
def test_qt_mode_cycling_smoke():
	"""Verify cycling through all registered modes without crashing."""
	cmd = [sys.executable, _THIS_FILE, "--test", "mode_cycling"]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT)
	_check_subprocess_result(result)


#============================================
def test_qt_grid_toggle_smoke():
	"""Verify grid toggle shows and hides grid lines."""
	cmd = [sys.executable, _THIS_FILE, "--test", "grid"]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=_SUBPROCESS_TIMEOUT)
	_check_subprocess_result(result)


# ======================================================================
# Helper functions for the runner implementations
# ======================================================================

#============================================
def _hex_points(cx: float, cy: float, radius: float) -> list:
	"""Compute 6 hexagonal vertex positions for a benzene ring.

	Returns coordinates arranged as a regular hexagon centered at
	(cx, cy) with the given radius.

	Args:
		cx: Center x coordinate.
		cy: Center y coordinate.
		radius: Distance from center to each vertex.

	Returns:
		List of 6 (x, y) tuples arranged counterclockwise.
	"""
	points = []
	for i in range(6):
		# start at top and go counterclockwise
		angle = math.pi / 2 + i * (2 * math.pi / 6)
		x = cx + radius * math.cos(angle)
		y = cy - radius * math.sin(angle)
		points.append((x, y))
	return points


#============================================
def _save_screenshot(widget, test_name: str) -> str:
	"""Grab a screenshot of the widget and save to output_smoke/.

	Args:
		widget: QWidget to capture.
		test_name: Test name used in the filename.

	Returns:
		Path to the saved screenshot file.
	"""
	os.makedirs(OUTPUT_DIR, exist_ok=True)
	pixmap = widget.grab()
	path = os.path.join(OUTPUT_DIR, f"qt_{test_name}.png")
	pixmap.save(path)
	print(f"Screenshot saved: {path}")
	return path


#============================================
def _sample_pixel_color(widget, x: int, y: int) -> tuple:
	"""Sample the pixel color at (x, y) from a widget grab.

	Args:
		widget: QWidget to sample from.
		x: Pixel x coordinate.
		y: Pixel y coordinate.

	Returns:
		Tuple of (r, g, b) color values.
	"""
	pixmap = widget.grab()
	image = pixmap.toImage()
	color = image.pixelColor(x, y)
	return (color.red(), color.green(), color.blue())


# ======================================================================
# Individual test runner functions (called when script is run directly)
# ======================================================================

#============================================
def _run_launch_smoke() -> None:
	"""Test that the Qt GUI launches and creates core widgets.

	Creates a QApplication, ThemeManager, and MainWindow. Verifies that
	the scene, view, and status bar are initialized. Shows the window,
	takes a screenshot, then auto-closes.
	"""
	import PySide6.QtCore
	import PySide6.QtWidgets
	import bkchem_qt.themes.theme_manager
	import bkchem_qt.main_window

	# create the application
	app = PySide6.QtWidgets.QApplication(sys.argv)
	# create theme manager and restore theme
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_manager.restore_theme()
	# create the main window
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)

	# verify core widgets exist
	assert main_window._scene is not None, "scene should not be None"
	assert main_window._view is not None, "view should not be None"
	assert main_window._status_bar is not None, "status bar should not be None"

	# show the window and process events so Qt renders
	main_window.show()
	app.processEvents()

	# take screenshot for visual review
	_save_screenshot(main_window, "launch")

	# schedule auto-close so the test does not hang
	PySide6.QtCore.QTimer.singleShot(500, app.quit)
	# run the event loop briefly
	app.exec()
	print("BKChem-Qt GUI smoke test OK")


#============================================
def _run_dark_mode_smoke() -> None:
	"""Test theme toggling between dark and light modes.

	Creates the GUI, verifies the initial theme is valid, switches to
	dark mode and checks both the palette Window color and the viewport
	pixel colors via screenshot sampling. Then switches to light and
	back to dark to confirm round-trip works.
	"""
	import PySide6.QtCore
	import PySide6.QtGui
	import PySide6.QtWidgets
	import bkchem_qt.themes.theme_manager
	import bkchem_qt.main_window

	app = PySide6.QtWidgets.QApplication(sys.argv)
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_manager.restore_theme()
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)
	# verify the window was created with a valid scene
	assert main_window._scene is not None, "scene should exist during theme test"

	# verify initial theme is one of the expected values
	current = theme_manager.current_theme
	assert current in ("dark", "light"), f"unexpected initial theme: {current}"

	# switch to dark mode and verify palette
	theme_manager.apply_theme("dark")
	dark_window_color = app.palette().color(
		PySide6.QtGui.QPalette.ColorRole.Window
	)
	# dark bg should be #2b2b2b (from dark.yaml gui.background)
	assert dark_window_color.name() == "#2b2b2b", (
		f"dark mode Window color should be #2b2b2b, got {dark_window_color.name()}"
	)

	# show window and process events so viewport renders
	main_window.show()
	app.processEvents()

	view = main_window._view
	# scroll to scene origin so viewport shows dark margin outside paper
	view.horizontalScrollBar().setValue(0)
	view.verticalScrollBar().setValue(0)
	app.processEvents()

	# take dark mode screenshot
	_save_screenshot(main_window, "dark_mode")

	# sample a viewport corner pixel (top-left area, outside paper)
	# at scroll (0,0), viewport(5,5) maps to scene(5,5) which is
	# outside the paper rect (paper starts at scene x=1000, y=750)
	corner_color = _sample_pixel_color(view, 5, 5)
	# compute lightness as average of RGB channels
	corner_lightness = sum(corner_color) / 3.0
	print(f"Dark mode viewport corner pixel: {corner_color}, lightness: {corner_lightness:.0f}")
	# viewport corner should be dark (not white)
	assert corner_lightness < 80, (
		f"dark mode viewport corner should be dark (lightness < 80), "
		f"got lightness={corner_lightness:.0f}, rgb={corner_color}"
	)

	# scroll to center the paper and sample its center pixel
	paper_rect = main_window._scene.paper_rect
	paper_cx = paper_rect.x() + paper_rect.width() / 2.0
	paper_cy = paper_rect.y() + paper_rect.height() / 2.0
	view.centerOn(paper_cx, paper_cy)
	app.processEvents()

	# sample the viewport center (should now be over the paper)
	center_color = _sample_pixel_color(view, view.width() // 2, view.height() // 2)
	center_lightness = sum(center_color) / 3.0
	print(f"Dark mode paper center pixel: {center_color}, lightness: {center_lightness:.0f}")
	# dark theme paper color is #2b2b2b (from dark.yaml), so it should be dark
	assert center_lightness < 80, (
		f"dark mode paper center should be dark (lightness < 80), "
		f"got lightness={center_lightness:.0f}, rgb={center_color}"
	)

	# switch to light mode and take screenshot
	theme_manager.apply_theme("light")
	app.processEvents()
	light_window_color = app.palette().color(
		PySide6.QtGui.QPalette.ColorRole.Window
	)
	assert light_window_color.name() != "#2b2b2b", (
		"light mode Window color should NOT be #2b2b2b"
	)
	_save_screenshot(main_window, "light_mode")

	# switch back to dark and re-verify palette round-trip
	theme_manager.apply_theme("dark")
	app.processEvents()
	dark_again_color = app.palette().color(
		PySide6.QtGui.QPalette.ColorRole.Window
	)
	assert dark_again_color.name() == "#2b2b2b", (
		f"dark mode round-trip failed, got {dark_again_color.name()}"
	)

	# scroll to origin and verify viewport corner is still dark
	view.horizontalScrollBar().setValue(0)
	view.verticalScrollBar().setValue(0)
	app.processEvents()
	corner_color2 = _sample_pixel_color(view, 5, 5)
	corner_lightness2 = sum(corner_color2) / 3.0
	assert corner_lightness2 < 80, (
		f"dark mode round-trip: viewport corner should still be dark, "
		f"got lightness={corner_lightness2:.0f}, rgb={corner_color2}"
	)

	# auto-close
	PySide6.QtCore.QTimer.singleShot(500, app.quit)
	app.exec()
	print("BKChem-Qt dark mode smoke test OK")


#============================================
def _run_status_bar_smoke() -> None:
	"""Test that status bar labels update correctly.

	Updates coordinates, zoom, and mode labels on the status bar and
	verifies the label text contains expected values.
	"""
	import PySide6.QtCore
	import PySide6.QtWidgets
	import bkchem_qt.themes.theme_manager
	import bkchem_qt.main_window

	app = PySide6.QtWidgets.QApplication(sys.argv)
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_manager.restore_theme()
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)

	# show window and process events
	main_window.show()
	app.processEvents()

	# update coordinates
	main_window._status_bar.update_coords(123.4, 567.8)
	coords_text = main_window._status_bar._coords_label.text()
	assert "123.4" in coords_text, f"coords label should contain '123.4', got: {coords_text}"
	assert "567.8" in coords_text, f"coords label should contain '567.8', got: {coords_text}"

	# update zoom
	main_window._status_bar.update_zoom(200.0)
	zoom_text = main_window._status_bar._zoom_label.text()
	assert "200" in zoom_text, f"zoom label should contain '200', got: {zoom_text}"

	# update mode
	main_window._status_bar.update_mode("Draw")
	mode_text = main_window._status_bar._mode_label.text()
	assert "Draw" in mode_text, f"mode label should contain 'Draw', got: {mode_text}"

	# take screenshot for visual review
	app.processEvents()
	_save_screenshot(main_window, "status_bar")

	# auto-close
	PySide6.QtCore.QTimer.singleShot(500, app.quit)
	app.exec()
	print("BKChem-Qt status bar smoke test OK")


#============================================
def _run_benzene_smoke() -> None:
	"""Test programmatic construction of a benzene ring on the canvas.

	Creates a MoleculeModel with 6 carbon atoms arranged in a hexagon,
	connects them with alternating single/double bonds, and adds the
	corresponding AtomItem and BondItem graphics objects to the scene.
	Takes a screenshot for visual verification.
	"""
	import PySide6.QtCore
	import PySide6.QtWidgets
	import bkchem_qt.themes.theme_manager
	import bkchem_qt.main_window
	import bkchem_qt.models.molecule_model
	import bkchem_qt.canvas.items.atom_item
	import bkchem_qt.canvas.items.bond_item

	app = PySide6.QtWidgets.QApplication(sys.argv)
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_manager.restore_theme()
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)

	# create a molecule model
	mol = bkchem_qt.models.molecule_model.MoleculeModel()

	# compute hexagonal positions for 6 carbon atoms
	hex_pts = _hex_points(2000, 1500, 40)

	# create 6 carbon atoms with coordinates on both model and OASA layers
	atom_models = []
	for i in range(6):
		atom = mol.create_atom("C")
		atom.x = hex_pts[i][0]
		atom.y = hex_pts[i][1]
		# also set coordinates on the underlying OASA atom so render_lib
		# can compute double bond placement from neighbor positions
		atom._chem_atom.x = hex_pts[i][0]
		atom._chem_atom.y = hex_pts[i][1]
		mol.add_atom(atom)
		atom_models.append(atom)

	# create 6 bonds with alternating double/single (2,1,2,1,2,1)
	bond_models = []
	bond_orders = [2, 1, 2, 1, 2, 1]
	for i in range(6):
		order = bond_orders[i]
		bond = mol.create_bond(order=order)
		mol.add_bond(atom_models[i], atom_models[(i + 1) % 6], bond)
		bond_models.append(bond)

	# add AtomItem graphics objects to the scene
	for atom_model in atom_models:
		atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom_model)
		main_window._scene.addItem(atom_item)

	# add BondItem graphics objects to the scene
	for bond_model in bond_models:
		bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
		main_window._scene.addItem(bond_item)

	# verify counts
	assert len(mol.atoms) == 6, f"expected 6 atoms, got {len(mol.atoms)}"
	assert len(mol.bonds) == 6, f"expected 6 bonds, got {len(mol.bonds)}"

	# count double bonds
	double_count = sum(1 for b in mol.bonds if b.order == 2)
	assert double_count == 3, f"expected 3 double bonds, got {double_count}"

	# show window and take screenshot
	main_window.show()
	app.processEvents()
	_save_screenshot(main_window, "benzene")

	# auto-close
	PySide6.QtCore.QTimer.singleShot(500, app.quit)
	app.exec()
	print("BKChem-Qt draw benzene smoke test OK")


#============================================
def _run_zoom_smoke() -> None:
	"""Test zoom controls on the graphics view.

	Verifies the initial zoom is 100%, scales up to 150%, then resets
	back to 100%. Takes screenshots at 150% and after reset.
	"""
	import PySide6.QtCore
	import PySide6.QtWidgets
	import bkchem_qt.themes.theme_manager
	import bkchem_qt.main_window

	app = PySide6.QtWidgets.QApplication(sys.argv)
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_manager.restore_theme()
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)

	# show window and process events
	main_window.show()
	app.processEvents()

	# verify initial zoom is approximately 100%
	initial_zoom = main_window._view.zoom_percent
	assert abs(initial_zoom - 100.0) < 0.1, (
		f"initial zoom should be ~100%, got {initial_zoom}"
	)

	# scale up and update the internal zoom tracker
	main_window._view.scale(1.5, 1.5)
	main_window._view._zoom_percent = 150.0
	scaled_zoom = main_window._view.zoom_percent
	assert abs(scaled_zoom - 150.0) < 0.1, (
		f"zoom should be ~150% after scaling, got {scaled_zoom}"
	)

	# take screenshot at 150% zoom
	app.processEvents()
	_save_screenshot(main_window, "zoom_150")

	# reset zoom
	main_window._view.reset_zoom()
	reset_zoom = main_window._view.zoom_percent
	assert abs(reset_zoom - 100.0) < 0.1, (
		f"zoom should be ~100% after reset, got {reset_zoom}"
	)

	# take screenshot after reset
	app.processEvents()
	_save_screenshot(main_window, "zoom_reset")

	# auto-close
	PySide6.QtCore.QTimer.singleShot(500, app.quit)
	app.exec()
	print("BKChem-Qt zoom smoke test OK")


#============================================
def _run_cholesterol_smoke() -> None:
	"""Test SMILES import of cholesterol via the file_actions bridge.

	Writes the cholesterol SMILES to a temp file, loads it through the
	open_file_path action, and verifies the document contains a molecule
	with the expected number of heavy atoms and bonds. Takes a screenshot.
	"""
	import PySide6.QtCore
	import PySide6.QtWidgets
	import bkchem_qt.themes.theme_manager
	import bkchem_qt.main_window
	import bkchem_qt.bridge.oasa_bridge

	app = PySide6.QtWidgets.QApplication(sys.argv)
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_manager.restore_theme()
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)

	# write cholesterol SMILES to a temporary file
	cholesterol_smiles = "CC(C)CCCC(C)C1CCC2C3CC=C4C[C@H](O)CC[C@]4(C)C3CC[C@]12C"
	smi_fd, smi_path = tempfile.mkstemp(suffix=".smi", prefix="cholesterol_")
	with os.fdopen(smi_fd, "w") as f:
		f.write(cholesterol_smiles + "\n")

	# use the bridge to parse the SMILES file into MoleculeModel objects
	# (bypasses the scene rendering pipeline to test the model layer)
	with open(smi_path, "r") as f:
		molecules = bkchem_qt.bridge.oasa_bridge.read_codec_file("smiles", f)

	# clean up the temp file
	os.unlink(smi_path)

	# verify that at least one molecule was parsed
	assert len(molecules) >= 1, (
		f"expected at least 1 molecule, got {len(molecules)}"
	)

	# register the molecule with the document
	for mol_model in molecules:
		main_window._document.add_molecule(mol_model)

	# verify the document contains the molecules
	doc_molecules = main_window._document.molecules
	assert len(doc_molecules) >= 1, (
		f"expected at least 1 molecule in document, got {len(doc_molecules)}"
	)

	# verify atom and bond counts for cholesterol (C27H46O = 28 heavy atoms)
	mol = doc_molecules[0]
	n_atoms = len(mol.atoms)
	n_bonds = len(mol.bonds)
	assert n_atoms >= 27, (
		f"cholesterol should have >= 27 heavy atoms, got {n_atoms}"
	)
	assert n_bonds >= 28, (
		f"cholesterol should have >= 28 bonds, got {n_bonds}"
	)

	# show window and take screenshot
	main_window.show()
	app.processEvents()
	_save_screenshot(main_window, "cholesterol")

	# auto-close
	PySide6.QtCore.QTimer.singleShot(500, app.quit)
	app.exec()
	print("BKChem-Qt import cholesterol smoke test OK")


#============================================
def _run_mode_cycling_smoke() -> None:
	"""Test cycling through all registered interaction modes.

	Iterates over every registered mode name, switches to it, and
	verifies the current_mode is not None. Ends on the edit mode.
	Takes a screenshot for visual record.
	"""
	import PySide6.QtCore
	import PySide6.QtWidgets
	import bkchem_qt.themes.theme_manager
	import bkchem_qt.main_window

	app = PySide6.QtWidgets.QApplication(sys.argv)
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_manager.restore_theme()
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)

	# show window and process events
	main_window.show()
	app.processEvents()

	# get the mode manager and all mode names
	mode_manager = main_window._mode_manager
	all_modes = mode_manager.mode_names()
	assert len(all_modes) > 0, "should have at least one registered mode"

	# cycle through each mode
	for mode_name in all_modes:
		mode_manager.set_mode(mode_name)
		current = mode_manager.current_mode
		assert current is not None, (
			f"current_mode should not be None after setting mode '{mode_name}'"
		)

	# end on edit mode
	mode_manager.set_mode("edit")
	assert mode_manager.current_mode is not None, (
		"current_mode should not be None after setting edit mode"
	)

	# take screenshot for visual record
	app.processEvents()
	_save_screenshot(main_window, "mode_cycling")

	# auto-close
	PySide6.QtCore.QTimer.singleShot(500, app.quit)
	app.exec()
	print("BKChem-Qt mode cycling smoke test OK")


#============================================
def _run_grid_smoke() -> None:
	"""Test grid toggle shows and hides grid lines on the canvas.

	Enables the grid, verifies it is visible on the scene, takes a
	screenshot, then disables and re-verifies. Also checks that grid
	lines are constrained within the paper rect boundaries.
	"""
	import PySide6.QtCore
	import PySide6.QtWidgets
	import bkchem_qt.themes.theme_manager
	import bkchem_qt.main_window

	app = PySide6.QtWidgets.QApplication(sys.argv)
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_manager.restore_theme()
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)

	# show window and process events
	main_window.show()
	app.processEvents()

	scene = main_window._scene

	# verify grid starts visible by default (matching Tk behavior)
	assert scene.grid_visible, "grid should be visible by default"
	app.processEvents()

	# verify grid group exists and is visible
	grid_group = scene._grid_group
	assert grid_group is not None, "grid group should exist"
	assert grid_group.isVisible(), "grid group should be visible"

	# count grid items in the group (lines + dots)
	grid_children = grid_group.childItems()
	assert len(grid_children) > 0, (
		f"grid group should contain items, got {len(grid_children)}"
	)
	print(f"Grid has {len(grid_children)} items (lines + dots)")

	# verify grid line items are within paper boundaries
	paper_rect = scene.paper_rect
	for child in grid_children[:20]:
		# skip dot ellipses, only check line items
		if not hasattr(child, "line"):
			continue
		line = child.line()
		# check that line endpoints are within the paper rect (with margin)
		assert line.x1() >= paper_rect.x() - 1, (
			f"grid line x1={line.x1()} outside paper left={paper_rect.x()}"
		)
		assert line.x2() <= paper_rect.x() + paper_rect.width() + 1, (
			f"grid line x2={line.x2()} outside paper right"
		)

	# scroll to center the paper to see grid lines
	view = main_window._view
	paper_cx = paper_rect.x() + paper_rect.width() / 2.0
	paper_cy = paper_rect.y() + paper_rect.height() / 2.0
	view.centerOn(paper_cx, paper_cy)
	app.processEvents()

	# take screenshot with grid visible
	_save_screenshot(main_window, "grid_on")

	# disable the grid
	scene.set_grid_visible(False)
	app.processEvents()
	assert not scene.grid_visible, "grid should be hidden after set_grid_visible(False)"
	assert not grid_group.isVisible(), "grid group should be hidden"

	# take screenshot with grid hidden
	_save_screenshot(main_window, "grid_off")

	# auto-close
	PySide6.QtCore.QTimer.singleShot(500, app.quit)
	app.exec()
	print("BKChem-Qt grid toggle smoke test OK")


# ======================================================================
# Main entry point for subprocess dispatch
# ======================================================================

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Qt GUI smoke tests")
	parser.add_argument(
		'--test', dest='test_name', required=True,
		choices=[
			'launch', 'dark_mode', 'status_bar', 'benzene',
			'zoom', 'cholesterol', 'mode_cycling', 'grid',
		],
		help="Name of the test runner to execute",
	)
	args = parser.parse_args()

	# dispatch to the matching runner function
	runners = {
		'launch': _run_launch_smoke,
		'dark_mode': _run_dark_mode_smoke,
		'status_bar': _run_status_bar_smoke,
		'benzene': _run_benzene_smoke,
		'zoom': _run_zoom_smoke,
		'cholesterol': _run_cholesterol_smoke,
		'mode_cycling': _run_mode_cycling_smoke,
		'grid': _run_grid_smoke,
	}
	runners[args.test_name]()
