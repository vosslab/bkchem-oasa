"""Qt-free geometry for deterministic Wavy presentation lines."""

# Standard Library
import math
import numbers


WAVY_SEGMENT_LENGTH = 12.0
WAVY_MAX_AMPLITUDE = 4.0
# 4,096 segments span about 49,152 scene points: roughly 17 m at 72 pt/in.
# That is far beyond a normal page while still bounding one gesture's work.
WAVY_MAX_SEGMENTS = 4096


#============================================
def wavy_points(
		start: tuple[numbers.Real, numbers.Real],
		end: tuple[numbers.Real, numbers.Real],
		) -> tuple[tuple[float, float], ...]:
	"""Return bounded zigzag geometry with exact finite endpoints.

	Args:
		start: Immutable finite ``(x, y)`` gesture start tuple.
		end: Immutable finite ``(x, y)`` gesture end tuple.

	Returns:
		Ordered immutable points, or an empty tuple for a zero-length gesture.

	Raises:
		ValueError: If endpoint or derived geometry is not finite or is too large.
	"""
	start_x, start_y = _finite_point(start, "start")
	end_x, end_y = _finite_point(end, "end")
	dx = end_x - start_x
	dy = end_y - start_y
	if not math.isfinite(dx) or not math.isfinite(dy):
		raise ValueError("Wavy geometry endpoints are too far apart")
	length = math.hypot(dx, dy)
	if not math.isfinite(length):
		raise ValueError("Wavy geometry length must be finite")
	if length == 0.0:
		return ()
	segment_estimate = length / WAVY_SEGMENT_LENGTH
	if segment_estimate > WAVY_MAX_SEGMENTS + 0.5:
		raise ValueError(
			f"Wavy geometry exceeds {WAVY_MAX_SEGMENTS} segment safety limit",
		)
	segments = max(2, round(segment_estimate))
	amplitude = min(WAVY_MAX_AMPLITUDE, length / 6.0)
	normal_x = -dy / length
	normal_y = dx / length
	if not all(math.isfinite(value) for value in (amplitude, normal_x, normal_y)):
		raise ValueError("Wavy geometry derived values must be finite")
	points = [(start_x, start_y)]
	for index in range(1, segments):
		fraction = index / segments
		offset = amplitude if index % 2 else -amplitude
		x = start_x + dx * fraction + normal_x * offset
		y = start_y + dy * fraction + normal_y * offset
		if not math.isfinite(x) or not math.isfinite(y):
			raise ValueError("Wavy geometry derived coordinates must be finite")
		points.append((x, y))
	points.append((end_x, end_y))
	result = tuple(points)
	return result


#============================================
def _finite_point(
		point: tuple[numbers.Real, numbers.Real],
		label: str,
		) -> tuple[float, float]:
	"""Validate one immutable finite coordinate tuple."""
	if not isinstance(point, tuple) or len(point) != 2:
		raise ValueError(f"Wavy {label} must be an immutable (x, y) tuple")
	x, y = point
	if (
			not isinstance(x, numbers.Real) or isinstance(x, bool)
			or not isinstance(y, numbers.Real) or isinstance(y, bool)
			):
		raise ValueError(f"Wavy {label} coordinates must be non-boolean real values")
	try:
		x_float, y_float = float(x), float(y)
	except OverflowError:
		raise ValueError(f"Wavy {label} coordinates must be finite")
	if not math.isfinite(x_float) or not math.isfinite(y_float):
		raise ValueError(f"Wavy {label} coordinates must be finite")
	result = (x_float, y_float)
	return result
