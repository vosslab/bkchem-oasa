"""BKChem-Qt GUI zoom behavior tests."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.canvas.view

_CHOLESTEROL_SMILES = (
	"CC(C)CCCC(C)C1CCC2C3CC=C4C[C@H](O)CC[C@]4(C)C3CC[C@]12C"
)


#============================================
def _flush_events() -> None:
	"""Process pending Qt events to stabilize GUI assertions."""
	PySide6.QtWidgets.QApplication.processEvents()


#============================================
def _count_atoms(scene: object) -> int:
	"""Return AtomItem count in the scene."""
	return sum(
		1 for item in scene.items()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
	)


#============================================
def _count_bonds(scene: object) -> int:
	"""Return BondItem count in the scene."""
	return sum(
		1 for item in scene.items()
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
	)


#============================================
def _viewport_center_scene(view: object) -> PySide6.QtCore.QPointF:
	"""Map the viewport center to scene coordinates."""
	center_px = view.viewport().rect().center()
	return view.mapToScene(center_px)


#============================================
def _assert_close(value: float, expected: float, tol: float, message: str) -> None:
	"""Assert float closeness with an explicit tolerance."""
	if abs(value - expected) > tol:
		raise AssertionError(
			f"{message}: expected {expected:.4f}, got {value:.4f} (tol={tol:.4f})"
		)


#============================================
def _simulate_snapped_button_zoom(start_percent: float, direction: int, steps: int) -> float:
	"""Simulate toolbar zoom steps using the view's snapped ladder logic."""
	current = float(start_percent)
	levels = bkchem_qt.canvas.view.ZOOM_SNAP_LEVELS
	for _idx in range(steps):
		if direction > 0:
			raw = current * bkchem_qt.canvas.view.ZOOM_FACTOR_PER_NOTCH
		else:
			raw = current / bkchem_qt.canvas.view.ZOOM_FACTOR_PER_NOTCH
		raw = max(
			bkchem_qt.canvas.view.ZOOM_MIN_PERCENT,
			min(raw, bkchem_qt.canvas.view.ZOOM_MAX_PERCENT),
		)
		target = min(levels, key=lambda level: (abs(level - raw), -level))
		if direction > 0 and target <= current and current < bkchem_qt.canvas.view.ZOOM_MAX_PERCENT:
			for level in levels:
				if level > current:
					target = level
					break
		elif direction < 0 and target >= current and current > bkchem_qt.canvas.view.ZOOM_MIN_PERCENT:
			for level in reversed(levels):
				if level < current:
					target = level
					break
		if abs(target - current) < 1e-9:
			continue
		current = target
	return current


#============================================
def _import_cholesterol_from_smiles(
		main_window: object, insert_smiles_through_backend: object,
		) -> object:
	"""Install cholesterol through the backend-authoritative molecule route."""
	return insert_smiles_through_backend(main_window, _CHOLESTEROL_SMILES)


#============================================
def test_qt_gui_zoom_diagnostic(
		main_window: object, insert_smiles_through_backend: object,
		) -> None:
	"""Validate zoom sequence behavior around content and viewport symmetry."""
	scene = main_window.scene
	view = main_window.view

	# import biomolecule template content so zoom_to_content has meaningful bounds
	start_atoms = _count_atoms(scene)
	start_bonds = _count_bonds(scene)
	_import_cholesterol_from_smiles(main_window, insert_smiles_through_backend)
	_flush_events()
	assert _count_atoms(scene) >= start_atoms + 27, (
		"cholesterol import should add at least 27 heavy atoms"
	)
	assert _count_bonds(scene) >= start_bonds + 28, (
		"cholesterol import should add at least 28 bonds"
	)

	# initial scale
	_assert_close(view.zoom_percent, 100.0, 0.01, "initial zoom should be 100%")

	# zoom out three steps
	for _i in range(3):
		main_window.on_zoom_out()
	_flush_events()
	expected_out = _simulate_snapped_button_zoom(100.0, direction=-1, steps=3)
	_assert_close(
		view.zoom_percent, expected_out, 0.15,
		"zoom_out x3 should match expected scale",
	)

	# reset to 100%
	main_window.on_reset_zoom()
	_flush_events()
	_assert_close(view.zoom_percent, 100.0, 0.01, "zoom reset should return to 100%")

	# zoom in three steps
	for _i in range(3):
		main_window.on_zoom_in()
	_flush_events()
	expected_in = _simulate_snapped_button_zoom(100.0, direction=1, steps=3)
	_assert_close(
		view.zoom_percent, expected_in, 0.15,
		"zoom_in x3 should match expected scale",
	)

	# content fit should stay within hard bounds
	main_window.on_zoom_to_content()
	_flush_events()
	zoom_after_content = view.zoom_percent
	assert math.isfinite(zoom_after_content)
	assert zoom_after_content > 0.0
	assert zoom_after_content <= bkchem_qt.canvas.view.ZOOM_MAX_PERCENT
	assert any(
		abs(zoom_after_content - level) < 1e-6
		for level in bkchem_qt.canvas.view.ZOOM_SNAP_LEVELS
	), (
		"zoom_to_content should land on snap ladder; "
		f"got {zoom_after_content:.4f}"
	)

	# round-trip symmetry around current view: out x3 then in x3.
	# If content-fit zoom is too close to/below clamp, use reset zoom so the
	# round-trip sequence does not hit hard bounds.
	min_roundtrip_zoom = (
		bkchem_qt.canvas.view.ZOOM_MIN_PERCENT
		* (bkchem_qt.canvas.view.ZOOM_FACTOR_PER_NOTCH ** 3)
	)
	if view.zoom_percent <= min_roundtrip_zoom:
		main_window.on_reset_zoom()
		_flush_events()

	start_zoom = view.zoom_percent
	start_center = _viewport_center_scene(view)
	for _i in range(3):
		main_window.on_zoom_out()
	for _i in range(3):
		main_window.on_zoom_in()
	_flush_events()
	end_zoom = view.zoom_percent
	end_center = _viewport_center_scene(view)

	_assert_close(end_zoom, start_zoom, 0.2, "zoom round-trip should preserve scale")
	drift = math.hypot(end_center.x() - start_center.x(), end_center.y() - start_center.y())
	# snapped zoom ladder and integer scrollbar quantization can yield a
	# slightly larger but still acceptable viewport drift on round-trip.
	assert drift <= 20.0, f"viewport center drift too high after round-trip: {drift:.2f}px"


#============================================
def test_qt_zoom_clamp_and_reset(main_window: object) -> None:
	"""Verify zoom min/max clamps and reset behavior."""
	view = main_window.view

	# clamp toward minimum
	for _i in range(250):
		main_window.on_zoom_out()
	_flush_events()
	_assert_close(
		view.zoom_percent,
		bkchem_qt.canvas.view.ZOOM_MIN_PERCENT,
		0.01,
		"zoom_out should clamp at minimum",
	)

	# clamp toward maximum
	for _i in range(500):
		main_window.on_zoom_in()
	_flush_events()
	_assert_close(
		view.zoom_percent,
		bkchem_qt.canvas.view.ZOOM_MAX_PERCENT,
		0.01,
		"zoom_in should clamp at maximum",
	)

	main_window.on_reset_zoom()
	_flush_events()
	_assert_close(view.zoom_percent, 100.0, 0.01, "zoom reset should return to 100%")
