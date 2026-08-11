"""Behavior and import-boundary coverage for scalar display geometry."""

# Standard Library
import ast
import math
import pathlib

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.bridge.display_geometry
import bkchem_qt.config.geometry_units
import bkchem_qt.widgets.periodic_table


_CONSUMER_MODULES = (
	"bkchem_qt/widgets/periodic_table.py",
	"bkchem_qt/canvas/scene.py",
	"bkchem_qt/config/geometry_units.py",
	"bkchem_qt/canvas/items/render_ops_painter.py",
	"bkchem_qt/canvas/items/atom_item.py",
	"bkchem_qt/canvas/items/bond_item.py",
)
_QT_PACKAGE_ROOT = pathlib.Path(__file__).parents[1] / "bkchem_qt"


#============================================
def test_scalar_geometry_bridge_returns_immutable_finite_lattice_values() -> None:
	"""A bounded grid request returns safe scalar facts instead of OASA containers."""
	points = bkchem_qt.bridge.display_geometry.hex_grid_points(
		0.0, 0.0, 120.0, 90.0, 30.0,
	)
	edges = bkchem_qt.bridge.display_geometry.hex_grid_edges(
		0.0, 0.0, 120.0, 90.0, 30.0,
	)

	assert isinstance(points, tuple) and all(math.isfinite(value) for point in points for value in point)
	assert isinstance(edges, tuple) and all(
		math.isfinite(value) for edge in edges for point in edge for value in point
	)


#============================================
def test_overlay_vertices_and_interaction_snap_share_one_lattice() -> None:
	"""Every interior interaction result is one of the displayed grid vertices."""
	spacing = 40.0
	points = bkchem_qt.bridge.display_geometry.hex_grid_points(
		-100.0, -100.0, 100.0, 100.0, spacing,
	)
	queries = ((17.0, 19.0), (-31.0, 44.0), (62.0, -7.0))
	snapped = (
		bkchem_qt.bridge.display_geometry.snap_to_hex_grid(x, y, spacing)
		for x, y in queries
	)

	assert all(
		any(math.dist(result, point) < 1e-9 for point in points)
		for result in snapped
	)


#============================================
def test_scalar_geometry_bridge_rejects_nonfinite_snap_input() -> None:
	"""Invalid interaction coordinates receive the stable typed boundary error."""
	with pytest.raises(ValueError, match="must be finite"):
		bkchem_qt.bridge.display_geometry.snap_to_hex_grid(math.inf, 0.0, 40.0)


#============================================
@pytest.mark.parametrize("invalid_spacing", (math.nan, math.inf, True, 0.0, -1.0))
def test_scene_keeps_its_grid_when_spacing_is_invalid(
		main_window: object, invalid_spacing: object,
		) -> None:
	"""A rejected spacing update preserves the current visible interaction lattice."""
	scene = main_window.scene
	before = scene.grid_spacing_pt
	scene.set_grid_spacing_pt(invalid_spacing)

	assert scene.grid_spacing_pt == before


#============================================
def test_scene_spacing_commit_keeps_current_grid_when_bridge_build_fails(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed new projection leaves the old visible lattice authoritative."""
	scene = main_window.scene
	overlay = scene._grid_overlay
	before = scene.grid_spacing_pt

	def fail_grid_build(*args: object) -> tuple:
		del args
		raise ValueError("simulated display-geometry failure")

	monkeypatch.setattr(
		bkchem_qt.bridge.display_geometry, "hex_grid_edges", fail_grid_build,
	)
	with pytest.raises(ValueError, match="simulated display-geometry failure"):
		scene.set_grid_spacing_pt(52.0)

	assert scene.grid_spacing_pt == before and scene._grid_overlay is overlay


#============================================
@pytest.mark.parametrize("invalid_value", (math.nan, math.inf, True))
def test_scalar_geometry_bridge_rejects_non_numeric_coordinate_forms(
		invalid_value: object,
		) -> None:
	"""The boundary rejects values that cannot describe a CDML coordinate."""
	with pytest.raises(ValueError):
		bkchem_qt.bridge.display_geometry.cm_to_points(invalid_value)


#============================================
def test_geometry_units_round_trip_through_plain_bridge_scale() -> None:
	"""Qt configuration preserves the backend CDML physical coordinate scale."""
	centimetres = 2.54
	converted = bkchem_qt.config.geometry_units.pt_to_cm(
		bkchem_qt.config.geometry_units.cm_to_pt(centimetres)
	)

	assert converted == pytest.approx(centimetres)


#============================================
def test_periodic_table_widget_projects_bridge_color(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A visible element button receives its normalized scalar bridge color."""
	del qapp
	dialog = bkchem_qt.widgets.periodic_table.PeriodicTablePopup()
	carbon_button = next(
		button for button in dialog.findChildren(PySide6.QtWidgets.QPushButton)
		if button.text() == "C"
	)
	color = bkchem_qt.bridge.display_geometry.element_category_color("C")
	style_sheet = carbon_button.styleSheet()
	dialog.close()
	dialog.deleteLater()

	assert color in style_sheet


#============================================
def test_display_geometry_consumers_have_no_direct_oasa_imports() -> None:
	"""Qt consumers receive OASA-derived display facts only through their bridge."""
	violations = []
	for relative_path in _CONSUMER_MODULES:
		path = _QT_PACKAGE_ROOT / relative_path.removeprefix("bkchem_qt/")
		module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
		for node in ast.walk(module):
			if isinstance(node, ast.Import):
				for alias in node.names:
					if alias.name == "oasa" or alias.name.startswith("oasa."):
						violations.append(f"{relative_path}:{node.lineno}:{alias.name}")
			if isinstance(node, ast.ImportFrom) and node.module is not None:
				if node.module == "oasa" or node.module.startswith("oasa."):
					violations.append(f"{relative_path}:{node.lineno}:{node.module}")

	assert not violations, "direct OASA imports in Qt display consumers: " + ", ".join(violations)
