"""Frontend-neutral display facts for periodic colors and canvas geometry.

This adapter is the Qt application's one OASA entry point for periodic-table
colors, hex-grid geometry, and CDML point conversions.  Its public results are
only immutable built-in scalar tuples, so Qt widgets can create their own
QColor, QPainterPath, and QPointF projections without taking ownership of
backend values.
"""

# Standard Library
import math
import re

# local repo modules
import oasa.cdml_writer
import oasa.hex_grid
import oasa.periodic_table


_HEX_COLOR_RE = re.compile(r"#[0-9a-f]{6}")


#============================================
def element_category_color(symbol: str) -> str:
	"""Return the normalized category color for one element symbol.

	Args:
		symbol: Chemical element symbol.

	Returns:
		A lowercase ``#rrggbb`` color string.

	Raises:
		ValueError: If the backend does not provide a CSS hex color.
	"""
	color = oasa.periodic_table.get_element_category_color(symbol).strip().lower()
	if _HEX_COLOR_RE.fullmatch(color) is None:
		raise ValueError(f"element category color is not a CSS hex value: {color!r}")
	return color


#============================================
def points_per_cm() -> float:
	"""Return the backend-owned CDML point scale as one plain finite number."""
	scale = float(oasa.cdml_writer.POINTS_PER_CM)
	if not math.isfinite(scale) or scale <= 0.0:
		raise ValueError("CDML points-per-centimetre scale must be finite and positive")
	return scale


#============================================
def cm_to_points(cm: float) -> float:
	"""Convert one finite CDML centimetre coordinate to display points."""
	value = _finite_coordinate(cm, "centimetres")
	result = value * points_per_cm()
	if not math.isfinite(result):
		raise ValueError("centimetre conversion is not representable as a finite point")
	return result


#============================================
def points_to_cm(points: float) -> float:
	"""Convert one finite display-point coordinate to CDML centimetres."""
	value = _finite_coordinate(points, "points")
	result = value / points_per_cm()
	if not math.isfinite(result):
		raise ValueError("point conversion is not representable as a finite centimetre")
	return result


#============================================
def hex_grid_points(
		x_min: float, y_min: float, x_max: float, y_max: float, spacing: float,
		) -> tuple[tuple[float, float], ...]:
	"""Return immutable finite lattice vertices for one display rectangle.

	An oversized grid is intentionally represented by an empty tuple.  Qt uses
	that same result as an empty decorative overlay rather than retaining an
	OASA list or a backend sentinel.
	"""
	values = _validate_hex_grid_inputs(x_min, y_min, x_max, y_max, spacing)
	points = oasa.hex_grid.generate_hex_grid_points(*values)
	if points is None:
		return ()
	normalized = tuple(_finite_pair(point, "hex-grid point") for point in points)
	return normalized


#============================================
def hex_grid_edges(
		x_min: float, y_min: float, x_max: float, y_max: float, spacing: float,
		) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
	"""Return immutable finite honeycomb edges for one display rectangle."""
	values = _validate_hex_grid_inputs(x_min, y_min, x_max, y_max, spacing)
	edges = oasa.hex_grid.generate_hex_honeycomb_edges(*values)
	if edges is None:
		return ()
	normalized = tuple(
		(
			_finite_pair(edge[0], "hex-grid edge start"),
			_finite_pair(edge[1], "hex-grid edge end"),
		)
		for edge in edges
	)
	return normalized


#============================================
def snap_to_hex_grid(x: float, y: float, spacing: float) -> tuple[float, float]:
	"""Return the nearest finite hex-grid vertex for finite display scalars.

	Raises:
		ValueError: If a coordinate or spacing is non-finite, or spacing is not
			positive.
	"""
	px = _finite_coordinate(x, "x coordinate")
	py = _finite_coordinate(y, "y coordinate")
	grid_spacing = _positive_spacing(spacing)
	point = oasa.hex_grid.snap_to_hex_grid(px, py, grid_spacing)
	result = _finite_pair(point, "snapped hex-grid point")
	return result


#============================================
def normalize_hex_grid_spacing(value: float) -> float:
	"""Return one finite positive grid spacing as a built-in float.

	This small request/result operation lets a frontend validate a proposed
	spacing before it changes any disposable Qt projection state.
	"""
	return _positive_spacing(value)


#============================================
def _validate_hex_grid_inputs(
		x_min: float, y_min: float, x_max: float, y_max: float, spacing: float,
		) -> tuple[float, float, float, float, float]:
	"""Validate the finite scalar rectangle grammar expected by OASA geometry."""
	values = (
		_finite_coordinate(x_min, "x minimum"),
		_finite_coordinate(y_min, "y minimum"),
		_finite_coordinate(x_max, "x maximum"),
		_finite_coordinate(y_max, "y maximum"),
		_positive_spacing(spacing),
	)
	return values


#============================================
def _finite_coordinate(value: float, label: str) -> float:
	"""Return one finite built-in float or raise the boundary's typed error."""
	if isinstance(value, bool):
		raise ValueError(f"{label} must be a finite number")
	try:
		result = float(value)
	except (TypeError, ValueError):
		raise ValueError(f"{label} must be a finite number") from None
	if not math.isfinite(result):
		raise ValueError(f"{label} must be finite")
	return result


#============================================
def _positive_spacing(value: float) -> float:
	"""Return one finite positive display spacing or raise ``ValueError``."""
	spacing = _finite_coordinate(value, "hex-grid spacing")
	if spacing <= 0.0:
		raise ValueError("hex-grid spacing must be greater than zero")
	return spacing


#============================================
def _finite_pair(value: object, label: str) -> tuple[float, float]:
	"""Normalize one backend point-like value into a finite built-in pair."""
	x, y = value
	result = (_finite_coordinate(x, f"{label} x"), _finite_coordinate(y, f"{label} y"))
	return result
