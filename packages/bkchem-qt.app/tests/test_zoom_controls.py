"""Tests for zoom controls: view API, main window handlers, and widget."""

# Standard Library
import math
import pathlib

# PIP3 modules
import pytest
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.view
import bkchem_qt.widgets.zoom_controls

_CHOLESTEROL_SMILES = (
	"CC(C)CCCC(C)C1CCC2C3CC=C4C[C@H](O)CC[C@]4(C)C3CC[C@]12C"
)
_SWEEP_PERCENT_LEVELS = tuple(list(range(25, 396, 10)) + [400])


#============================================
def _flush_events() -> None:
	"""Process pending Qt events."""
	PySide6.QtWidgets.QApplication.processEvents()


#============================================
def _viewport_center_scene(view: object) -> object:
	"""Return viewport center mapped into scene coordinates."""
	center_px = view.viewport().rect().center()
	return view.mapToScene(center_px)


#============================================
def _import_cholesterol_from_smiles(
		main_window: object, insert_smiles_through_backend: object,
		) -> object:
	"""Install cholesterol through the backend-authoritative molecule route."""
	molecule = insert_smiles_through_backend(main_window, _CHOLESTEROL_SMILES)
	_flush_events()
	return molecule


#============================================
def _first_molecule(main_window: object) -> object:
	"""Return the first molecule in the document."""
	if not main_window.document.molecules:
		raise AssertionError("Expected at least one molecule in the document.")
	return main_window.document.molecules[0]


#============================================
def _capture_model_coords(molecule: object) -> list:
	"""Capture atom model coordinates as a list of tuples."""
	return [(atom.x, atom.y) for atom in molecule.atoms]


#============================================
def _fixed_atom_pair_scene_points(molecule: object) -> tuple:
	"""Choose two stable molecule points (leftmost and rightmost atoms)."""
	if len(molecule.atoms) < 2:
		raise AssertionError("Need at least two atoms to track fixed points.")
	left = min(molecule.atoms, key=lambda atom: (atom.x, atom.y))
	right = max(molecule.atoms, key=lambda atom: (atom.x, atom.y))
	if left is right:
		raise AssertionError("Failed to choose two distinct fixed atom points.")
	return (float(left.x), float(left.y)), (float(right.x), float(right.y))


#============================================
def _augment_snapshot_with_fixed_pair(
	snapshot: dict, view: object, p1_scene: object, p2_scene: object,
) -> dict:
	"""Add viewport coordinates and vector metrics for two fixed scene points."""
	p1_view = view.mapFromScene(p1_scene[0], p1_scene[1])
	p2_view = view.mapFromScene(p2_scene[0], p2_scene[1])
	pair_dx = float(p2_view.x() - p1_view.x())
	pair_dy = float(p2_view.y() - p1_view.y())
	snapshot["p1_vx"] = float(p1_view.x())
	snapshot["p1_vy"] = float(p1_view.y())
	snapshot["p2_vx"] = float(p2_view.x())
	snapshot["p2_vy"] = float(p2_view.y())
	snapshot["pair_dx"] = pair_dx
	snapshot["pair_dy"] = pair_dy
	snapshot["pair_len"] = math.hypot(pair_dx, pair_dy)
	return snapshot


#============================================
def _snapshot_zoom_state(main_window: object, label: str) -> dict:
	"""Capture zoom and viewport center for diagnostics."""
	view = main_window.view
	vp_center = _viewport_center_scene(view)
	t = view.transform()
	return {
		"label": label,
		"zoom": view.zoom_percent,
		"vp_x": vp_center.x(),
		"vp_y": vp_center.y(),
		"items": len(main_window.scene.items()),
		"m11": t.m11(),
		"m22": t.m22(),
		"det": t.determinant(),
	}


#============================================
def _print_diagnostic_table(snapshots: list) -> None:
	"""Print a compact zoom diagnostic table for -s visual runs."""
	print()
	print("=" * 114)
	print("QT ZOOM DIAGNOSTIC TABLE")
	print("=" * 114)
	print(
		f"{'Step':<24} {'Zoom %':>9} {'VP X':>10} {'VP Y':>10} "
		f"{'m11':>10} {'m22':>10} {'det':>12} {'Items':>8}"
	)
	print("-" * 114)
	for snap in snapshots:
		print(
			f"{snap['label']:<24} {snap['zoom']:>9.2f} "
			f"{snap['vp_x']:>10.1f} {snap['vp_y']:>10.1f} "
			f"{snap['m11']:>10.4f} {snap['m22']:>10.4f} "
			f"{snap['det']:>12.6f} {snap['items']:>8d}"
		)
	print("=" * 114)


#============================================
def _print_fixed_pair_table(title: str, snapshots: list) -> None:
	"""Print fixed-point viewport tracking for mirror/inversion diagnosis."""
	if not snapshots:
		return
	base_dx = snapshots[0]["pair_dx"]
	base_dy = snapshots[0]["pair_dy"]
	print()
	print("=" * 132)
	print(title)
	print("=" * 132)
	print(
		f"{'Step':<14} {'Zoom %':>8} {'P1(x,y)':>20} {'P2(x,y)':>20} "
		f"{'dX':>9} {'dY':>9} {'Len':>10} {'Dot(base)':>11}"
	)
	print("-" * 132)
	for snap in snapshots:
		dot_base = snap["pair_dx"] * base_dx + snap["pair_dy"] * base_dy
		p1_text = f"({snap['p1_vx']:.1f},{snap['p1_vy']:.1f})"
		p2_text = f"({snap['p2_vx']:.1f},{snap['p2_vy']:.1f})"
		print(
			f"{snap['label']:<14} {snap['zoom']:>8.1f} {p1_text:>20} {p2_text:>20} "
			f"{snap['pair_dx']:>9.1f} {snap['pair_dy']:>9.1f} "
			f"{snap['pair_len']:>10.2f} {dot_base:>11.2f}"
		)
	print("=" * 132)


#============================================
def _run_percent_sweep_with_fixed_pair(
	main_window: object,
	percents: list,
	label_prefix: str,
	p1_scene: object,
	p2_scene: object,
) -> list:
	"""Run zoom percent sweep while tracking a fixed molecule point pair."""
	snapshots = []
	base_pair_dx = None
	base_pair_dy = None
	prev_pair_len = None
	is_increasing = percents[-1] > percents[0]
	for percent in percents:
		main_window.view.set_zoom_percent(float(percent))
		_flush_events()
		snap = _snapshot_zoom_state(main_window, f"{label_prefix}{percent}%")
		snap = _augment_snapshot_with_fixed_pair(snap, main_window.view, p1_scene, p2_scene)
		snapshots.append(snap)

		assert main_window.view.zoom_percent == pytest.approx(percent, abs=0.05)
		assert snap["m11"] > 0.0, (
			f"Transform m11 became non-positive at {percent}%: {snap['m11']:.6f}"
		)
		assert snap["m22"] > 0.0, (
			f"Transform m22 became non-positive at {percent}%: {snap['m22']:.6f}"
		)
		assert snap["det"] > 0.0, (
			f"Transform determinant became non-positive at {percent}%: "
			f"{snap['det']:.6f}"
		)

		if base_pair_dx is None:
			base_pair_dx = snap["pair_dx"]
			base_pair_dy = snap["pair_dy"]
			assert snap["pair_len"] > 1.0, (
				"Fixed-point pair too small in viewport; cannot diagnose mirroring."
			)
		else:
			# dot(base)>0 keeps pair vector in same hemisphere (no visual mirror flip)
			dot_base = snap["pair_dx"] * base_pair_dx + snap["pair_dy"] * base_pair_dy
			assert dot_base > 0.0, (
				f"Fixed-point vector flipped relative to baseline at {percent}% "
				f"(dot={dot_base:.3f}, base=({base_pair_dx:.3f},{base_pair_dy:.3f}), "
				f"now=({snap['pair_dx']:.3f},{snap['pair_dy']:.3f}))."
			)

		if prev_pair_len is not None:
			if is_increasing:
				assert snap["pair_len"] >= prev_pair_len - 0.75, (
					f"Pair length should increase for upward sweep at {percent}%: "
					f"prev={prev_pair_len:.2f}, now={snap['pair_len']:.2f}"
				)
			else:
				assert snap["pair_len"] <= prev_pair_len + 0.75, (
					f"Pair length should decrease for downward sweep at {percent}%: "
					f"prev={prev_pair_len:.2f}, now={snap['pair_len']:.2f}"
				)
		prev_pair_len = snap["pair_len"]

	return snapshots


#============================================
def _print_up_down_coordinate_comparison(up_snapshots: list, down_snapshots: list) -> None:
	"""Print per-zoom coordinate comparison between upward and downward sweeps."""
	down_by_zoom = {
		int(round(snap["zoom"])): snap
		for snap in down_snapshots
	}
	print()
	print("=" * 150)
	print("QT UP/DOWN FIXED-POINT COMPARISON")
	print("=" * 150)
	print(
		f"{'Zoom%':>6} {'P1 up':>20} {'P1 dn':>20} {'|dP1|':>8} "
		f"{'P2 up':>20} {'P2 dn':>20} {'|dP2|':>8} {'dShift':>16} {'|dLen|':>8}"
	)
	print("-" * 150)
	for up in up_snapshots:
		zoom_key = int(round(up["zoom"]))
		down = down_by_zoom.get(zoom_key)
		if down is None:
			continue
		dp1 = math.hypot(up["p1_vx"] - down["p1_vx"], up["p1_vy"] - down["p1_vy"])
		dp2 = math.hypot(up["p2_vx"] - down["p2_vx"], up["p2_vy"] - down["p2_vy"])
		dlen = abs(up["pair_len"] - down["pair_len"])
		shift_x = down["p1_vx"] - up["p1_vx"]
		shift_y = down["p1_vy"] - up["p1_vy"]
		p1_up = f"({up['p1_vx']:.1f},{up['p1_vy']:.1f})"
		p1_dn = f"({down['p1_vx']:.1f},{down['p1_vy']:.1f})"
		p2_up = f"({up['p2_vx']:.1f},{up['p2_vy']:.1f})"
		p2_dn = f"({down['p2_vx']:.1f},{down['p2_vy']:.1f})"
		shift_text = f"({shift_x:+.1f},{shift_y:+.1f})"
		print(
			f"{zoom_key:>6d} {p1_up:>20} {p1_dn:>20} {dp1:>8.2f} "
			f"{p2_up:>20} {p2_dn:>20} {dp2:>8.2f} {shift_text:>16} {dlen:>8.2f}"
		)
	print("=" * 150)


#============================================
def _assert_up_down_coordinate_symmetry(
	up_snapshots: list,
	down_snapshots: list,
	point_tol_px: float = 25.0,
	length_tol_px: float = 2.5,
	vector_tol_px: float = 1.5,
	translation_consistency_tol_px: float = 1.5,
) -> None:
	"""Assert that matching zoom levels from up/down sweeps are coordinate-close."""
	down_by_zoom = {
		int(round(snap["zoom"])): snap
		for snap in down_snapshots
	}
	for up in up_snapshots:
		zoom_key = int(round(up["zoom"]))
		down = down_by_zoom.get(zoom_key)
		if down is None:
			raise AssertionError(
				f"Missing downward sweep snapshot for zoom {zoom_key}%."
			)
		dp1 = math.hypot(up["p1_vx"] - down["p1_vx"], up["p1_vy"] - down["p1_vy"])
		dp2 = math.hypot(up["p2_vx"] - down["p2_vx"], up["p2_vy"] - down["p2_vy"])
		dlen = abs(up["pair_len"] - down["pair_len"])
		dvec_x = abs(up["pair_dx"] - down["pair_dx"])
		dvec_y = abs(up["pair_dy"] - down["pair_dy"])
		p1_shift_x = down["p1_vx"] - up["p1_vx"]
		p1_shift_y = down["p1_vy"] - up["p1_vy"]
		p2_shift_x = down["p2_vx"] - up["p2_vx"]
		p2_shift_y = down["p2_vy"] - up["p2_vy"]
		assert dp1 <= point_tol_px, (
			f"P1 mismatch at {zoom_key}%: |dP1|={dp1:.2f}px "
			f"(tol={point_tol_px:.2f}px)."
		)
		assert dp2 <= point_tol_px, (
			f"P2 mismatch at {zoom_key}%: |dP2|={dp2:.2f}px "
			f"(tol={point_tol_px:.2f}px)."
		)
		assert dlen <= length_tol_px, (
			f"Pair-length mismatch at {zoom_key}%: |dLen|={dlen:.2f}px "
			f"(tol={length_tol_px:.2f}px)."
		)
		assert dvec_x <= vector_tol_px, (
			f"Pair-vector dx mismatch at {zoom_key}%: |dVecX|={dvec_x:.2f}px "
			f"(tol={vector_tol_px:.2f}px)."
		)
		assert dvec_y <= vector_tol_px, (
			f"Pair-vector dy mismatch at {zoom_key}%: |dVecY|={dvec_y:.2f}px "
			f"(tol={vector_tol_px:.2f}px)."
		)
		assert abs(p1_shift_x - p2_shift_x) <= translation_consistency_tol_px, (
			f"Translation X inconsistent at {zoom_key}%: "
			f"p1_shift_x={p1_shift_x:.2f}px p2_shift_x={p2_shift_x:.2f}px "
			f"(tol={translation_consistency_tol_px:.2f}px)."
		)
		assert abs(p1_shift_y - p2_shift_y) <= translation_consistency_tol_px, (
			f"Translation Y inconsistent at {zoom_key}%: "
			f"p1_shift_y={p1_shift_y:.2f}px p2_shift_y={p2_shift_y:.2f}px "
			f"(tol={translation_consistency_tol_px:.2f}px)."
		)


#============================================
def test_zoom_in_increases_percent(
		main_window: object, insert_smiles_through_backend: object,
		) -> None:
	"""Calling on_zoom_in raises zoom on visible cholesterol content."""
	_import_cholesterol_from_smiles(main_window, insert_smiles_through_backend)
	main_window.on_zoom_to_content()
	_flush_events()
	start_zoom = main_window.view.zoom_percent
	main_window.on_zoom_in()
	assert main_window.view.zoom_percent > start_zoom


#============================================
def test_zoom_out_decreases_percent(main_window: object) -> None:
	"""Calling on_zoom_out lowers the zoom percent below 100."""
	main_window.on_zoom_out()
	assert main_window.view.zoom_percent < 100


#============================================
def test_reset_zoom_returns_100(main_window: object) -> None:
	"""Zoom in then reset returns zoom percent to 100."""
	main_window.on_zoom_in()
	assert main_window.view.zoom_percent != 100
	main_window.on_reset_zoom()
	assert main_window.view.zoom_percent == pytest.approx(100.0)


#============================================
def test_zoom_to_fit_no_crash(main_window: object) -> None:
	"""zoom_to_fit should run and land on the configured snap ladder."""
	main_window.on_zoom_to_fit()
	assert any(
		abs(main_window.view.zoom_percent - level) < 1e-6
		for level in bkchem_qt.canvas.view.ZOOM_SNAP_LEVELS
	), (
		"zoom_to_fit should land on snap ladder; "
		f"got {main_window.view.zoom_percent:.4f}"
	)


#============================================
def test_zoom_to_content_no_crash(main_window: object) -> None:
	"""Calling on_zoom_to_content does not raise an exception."""
	main_window.on_zoom_to_content()


#============================================
def test_zoom_to_content_includes_document_backed_vector_projection(
		main_window: object, tmp_path: pathlib.Path,
		) -> None:
	"""Content fit keeps a distant persistent vector inside the viewport."""
	candidate = """\
<cdml version="26.07">
 <text id="anchor"><point x="1cm" y="1cm"/><ftext>Anchor</ftext></text>
 <rect id="distant" x1="20cm" y1="12cm" x2="24cm" y2="16cm"/>
</cdml>
	"""
	source = tmp_path / "vector-content.cdml"
	source.write_text(candidate, encoding="utf-8")
	was_visible = main_window.isVisible()
	main_window.resize(1280, 800)
	main_window.show()
	try:
		assert main_window.open_file_path(str(source))
		_flush_events()
		session = next(
			session for session in main_window.sessions
			if session.document is main_window.document
		)
		vector = next(
			item for item in session.scene.items()
			if getattr(getattr(item, "document_object_model", None), "object_id", None)
			== "distant"
		)

		main_window.on_zoom_to_content()
		_flush_events()
		vector_center = vector.mapToScene(vector.boundingRect().center())
		viewport_center = main_window.view.mapFromScene(vector_center)

		assert main_window.view.viewport().rect().contains(viewport_center)
	finally:
		if not was_visible:
			main_window.hide()


#============================================
def test_set_zoom_percent(main_window: object) -> None:
	"""set_zoom_percent should honor exact user-entered percentages."""
	main_window.view.set_zoom_percent(173.91)
	assert main_window.view.zoom_percent == pytest.approx(173.91, abs=0.01)


#============================================
def test_zoom_controls_widget_exists(main_window: object) -> None:
	"""The production status bar contains the reusable zoom interaction."""
	zoom_controls = main_window.statusBar().findChild(
		bkchem_qt.widgets.zoom_controls.ZoomControls,
	)
	assert isinstance(zoom_controls, bkchem_qt.widgets.zoom_controls.ZoomControls)


#============================================
def test_zoom_controls_label_updates(main_window: object) -> None:
	"""After zooming in, the zoom controls label no longer reads 100%."""
	main_window.on_zoom_in()
	label = main_window.statusBar().findChild(
		PySide6.QtWidgets.QLabel, "current-zoom-percentage",
	)
	if label is None:
		raise AssertionError("The current zoom percentage readout is missing.")
	label_text = label.text()
	assert label_text != "100%"


#============================================
def _visible_inside(
		widget: PySide6.QtWidgets.QWidget,
		container: PySide6.QtWidgets.QWidget,
		) -> bool:
	"""Return whether a visible status control fits inside its bar."""
	widget_rect = PySide6.QtCore.QRect(
		widget.mapToGlobal(PySide6.QtCore.QPoint()), widget.size()
	)
	container_rect = PySide6.QtCore.QRect(
		container.mapToGlobal(PySide6.QtCore.QPoint()), container.size()
	)
	return widget.isVisible() and container_rect.contains(widget_rect)


#============================================
@pytest.mark.parametrize("width", (640, 1024, 1280))
def test_status_and_zoom_controls_remain_reachable_at_desktop_widths(
		width: int, main_window: object,
		) -> None:
	"""Keep every status and zoom task reachable in the production window."""
	status_bar = main_window.statusBar()
	zoom_controls = status_bar.findChild(
		bkchem_qt.widgets.zoom_controls.ZoomControls,
	)
	if zoom_controls is None:
		raise AssertionError("The production status bar has no zoom controls.")
	status_bar.set_context_message(
		"Choose a tool, then click or drag on the drawing canvas."
	)
	original_size = main_window.size()
	try:
		main_window.resize(width, 480)
		main_window.show()
		_flush_events()

		assert main_window.width() == width
		assert status_bar.visible_message
		for object_name in ("cursor-coordinates", "active-editing-mode"):
			readout = status_bar.findChild(
				PySide6.QtWidgets.QLabel, object_name,
			)
			if readout is None:
				raise AssertionError(f"The {object_name} readout is missing.")
			assert _visible_inside(readout, status_bar)
		for object_name in (
			"zoom-out", "zoom-in", "reset-zoom", "zoom-to-page",
			"zoom-to-page-content", "zoom-percentage-slider",
		):
			control = zoom_controls.findChild(
				PySide6.QtWidgets.QWidget, object_name,
			)
			if control is None:
				raise AssertionError(f"The {object_name} control is missing.")
			assert _visible_inside(control, status_bar)
			assert control.focusPolicy() != PySide6.QtCore.Qt.FocusPolicy.NoFocus
	finally:
		main_window.resize(original_size)
		_flush_events()


#============================================
def test_zoom_control_accessible_names_describe_every_action() -> None:
	"""Expose unambiguous names for keyboard and assistive-technology users."""
	zoom_controls = bkchem_qt.widgets.zoom_controls.ZoomControls()
	for object_name in ("reset-zoom", "zoom-to-page", "zoom-to-page-content"):
		control = zoom_controls.findChild(
			PySide6.QtWidgets.QWidget, object_name,
		)
		if control is None:
			raise AssertionError(f"The {object_name} control is missing.")
		assert control.accessibleName()


#============================================
def test_zoom_diagnostic_with_cholesterol(
		main_window: object, insert_smiles_through_backend: object,
		) -> None:
	"""Run a cholesterol-backed zoom diagnostic with round-trip checks."""
	_import_cholesterol_from_smiles(main_window, insert_smiles_through_backend)
	main_window.on_zoom_to_content()
	_flush_events()

	snapshots = [_snapshot_zoom_state(main_window, "0: zoom_to_content")]
	base_zoom = main_window.view.zoom_percent
	assert base_zoom > 0.0
	assert base_zoom <= bkchem_qt.canvas.view.ZOOM_MAX_PERCENT
	assert any(
		abs(base_zoom - level) < 1e-6
		for level in bkchem_qt.canvas.view.ZOOM_SNAP_LEVELS
	), (
		f"zoom_to_content should snap to configured zoom ladder, got {base_zoom:.4f}"
	)
	roundtrip_start_zoom = base_zoom
	min_roundtrip_zoom = (
		bkchem_qt.canvas.view.ZOOM_MIN_PERCENT
		* (bkchem_qt.canvas.view.ZOOM_FACTOR_PER_NOTCH ** 3)
	)
	if roundtrip_start_zoom <= min_roundtrip_zoom:
		main_window.on_reset_zoom()
		_flush_events()
		roundtrip_start_zoom = main_window.view.zoom_percent
		snapshots.append(_snapshot_zoom_state(main_window, "0b: zoom_reset"))
	roundtrip_start_snapshot = snapshots[-1]

	for idx in range(3):
		main_window.on_zoom_out()
		_flush_events()
		snapshots.append(_snapshot_zoom_state(main_window, f"1.{idx + 1}: zoom_out"))
	zoom_after_out = main_window.view.zoom_percent
	assert zoom_after_out < roundtrip_start_zoom

	for idx in range(3):
		main_window.on_zoom_in()
		_flush_events()
		snapshots.append(_snapshot_zoom_state(main_window, f"2.{idx + 1}: zoom_in"))
	zoom_after_roundtrip = main_window.view.zoom_percent
	assert zoom_after_roundtrip == pytest.approx(roundtrip_start_zoom, rel=0.02, abs=0.5)

	start_vp = roundtrip_start_snapshot
	end_vp = snapshots[-1]
	drift = math.hypot(end_vp["vp_x"] - start_vp["vp_x"], end_vp["vp_y"] - start_vp["vp_y"])
	assert drift <= 20.0, (
		f"Viewport drift too large after zoom round-trip: {drift:.2f}px "
		f"(start=({start_vp['vp_x']:.1f},{start_vp['vp_y']:.1f}) "
		f"end=({end_vp['vp_x']:.1f},{end_vp['vp_y']:.1f}))"
	)

	main_window.on_zoom_to_content()
	_flush_events()
	snapshots.append(_snapshot_zoom_state(main_window, "3: zoom_to_content"))
	assert main_window.view.zoom_percent == pytest.approx(base_zoom, rel=0.05, abs=0.5)

	_print_diagnostic_table(snapshots)


#============================================
def test_zoom_model_coords_stable_with_cholesterol(
		main_window: object, insert_smiles_through_backend: object,
		) -> None:
	"""Model coordinates must remain unchanged across extreme zoom operations."""
	_import_cholesterol_from_smiles(main_window, insert_smiles_through_backend)
	molecule = _first_molecule(main_window)
	coords_before = _capture_model_coords(molecule)
	assert coords_before, "Expected at least one atom coordinate."

	main_window.on_zoom_to_content()
	_flush_events()

	for _idx in range(250):
		main_window.on_zoom_in()
	_flush_events()
	assert main_window.view.zoom_percent == pytest.approx(
		bkchem_qt.canvas.view.ZOOM_MAX_PERCENT,
		abs=0.01,
	)
	coords_after_max = _capture_model_coords(molecule)

	for _idx in range(500):
		main_window.on_zoom_out()
	_flush_events()
	assert main_window.view.zoom_percent == pytest.approx(
		bkchem_qt.canvas.view.ZOOM_MIN_PERCENT,
		abs=0.01,
	)
	coords_after_min = _capture_model_coords(molecule)

	main_window.on_reset_zoom()
	_flush_events()
	coords_after_reset = _capture_model_coords(molecule)

	for (bx, by), (mx, my), (nx, ny), (rx, ry) in zip(
		coords_before, coords_after_max, coords_after_min, coords_after_reset
	):
		assert mx == pytest.approx(bx, abs=1e-6)
		assert my == pytest.approx(by, abs=1e-6)
		assert nx == pytest.approx(bx, abs=1e-6)
		assert ny == pytest.approx(by, abs=1e-6)
		assert rx == pytest.approx(bx, abs=1e-6)
		assert ry == pytest.approx(by, abs=1e-6)


#============================================
def test_zoom_roundtrip_symmetry_with_cholesterol(
		main_window: object, insert_smiles_through_backend: object,
		) -> None:
	"""Zoom out from high zoom and back; viewport center should round-trip."""
	_import_cholesterol_from_smiles(main_window, insert_smiles_through_backend)
	main_window.on_zoom_to_content()
	_flush_events()

	# Push to max zoom and center on content before round-trip sequence.
	for _idx in range(250):
		main_window.on_zoom_in()
	main_window.on_zoom_to_content()
	_flush_events()
	for _idx in range(250):
		main_window.on_zoom_in()
	_flush_events()

	start_zoom = main_window.view.zoom_percent
	start_center = _viewport_center_scene(main_window.view)
	assert start_zoom == pytest.approx(bkchem_qt.canvas.view.ZOOM_MAX_PERCENT, abs=0.01)

	steps = 0
	while main_window.view.zoom_percent > 250.0 and steps < 80:
		main_window.on_zoom_out()
		steps += 1
	_flush_events()
	assert steps > 0, "Expected at least one zoom-out step from max zoom."

	for _idx in range(steps):
		main_window.on_zoom_in()
	_flush_events()

	end_zoom = main_window.view.zoom_percent
	end_center = _viewport_center_scene(main_window.view)
	assert end_zoom == pytest.approx(start_zoom, abs=0.2)

	drift = math.hypot(end_center.x() - start_center.x(), end_center.y() - start_center.y())
	assert drift <= 15.0, (
		f"Viewport center drifted {drift:.2f}px after high-zoom round-trip "
		f"(steps={steps})."
	)


#============================================
def test_zoom_sweep_25_to_400_and_400_to_25_no_inversion(
		main_window: object, insert_smiles_through_backend: object,
		) -> None:
	"""Sweep fixed direct-set zoom levels and verify no orientation inversion."""
	molecule = _import_cholesterol_from_smiles(
		main_window, insert_smiles_through_backend,
	)
	p1_scene, p2_scene = _fixed_atom_pair_scene_points(molecule)
	main_window.on_zoom_to_content()
	_flush_events()
	assert any(
		level not in bkchem_qt.canvas.view.ZOOM_SNAP_LEVELS
		for level in _SWEEP_PERCENT_LEVELS
	), "Sweep levels must include non-snapped values."
	up_percents = list(_SWEEP_PERCENT_LEVELS)
	down_percents = list(reversed(up_percents))
	up_snapshots = _run_percent_sweep_with_fixed_pair(
		main_window, up_percents, "up ", p1_scene, p2_scene
	)
	down_snapshots = _run_percent_sweep_with_fixed_pair(
		main_window, down_percents, "dn ", p1_scene, p2_scene
	)
	_print_diagnostic_table(up_snapshots)
	_print_fixed_pair_table("QT FIXED-PAIR TABLE (25% -> 400%)", up_snapshots)
	_print_diagnostic_table(down_snapshots)
	_print_fixed_pair_table("QT FIXED-PAIR TABLE (400% -> 25%)", down_snapshots)
	_print_up_down_coordinate_comparison(up_snapshots, down_snapshots)
	_assert_up_down_coordinate_symmetry(up_snapshots, down_snapshots)
