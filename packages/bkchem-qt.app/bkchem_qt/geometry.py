"""Model-space affine geometry for persistent document transforms."""

# local repo modules
import bkchem_qt.models.document_object
import bkchem_qt.models.molecule_model


#============================================
def bounds_from_points(
		points: list[tuple[float, float]],
		) -> tuple[float, float, float, float] | None:
	"""Return the normalized bounding rectangle enclosing ``points``.

	The result is ``(left, top, right, bottom)``.  It deliberately works on
	document-model coordinates instead of graphics-item bounds so a transform
	can be committed before, or without, a live scene projection.
	"""
	if not points:
		return None
	xs = [point[0] for point in points]
	ys = [point[1] for point in points]
	bounds = (min(xs), min(ys), max(xs), max(ys))
	return bounds


#============================================
def union_bounds(
		bounds_list: list[tuple[float, float, float, float] | None],
		) -> tuple[float, float, float, float] | None:
	"""Return the bounding rectangle enclosing all nonempty rectangles."""
	available = [bounds for bounds in bounds_list if bounds is not None]
	if not available:
		return None
	bounds = (
		min(bounds[0] for bounds in available),
		min(bounds[1] for bounds in available),
		max(bounds[2] for bounds in available),
		max(bounds[3] for bounds in available),
	)
	return bounds


#============================================
def molecule_bounds(
		molecule_model: bkchem_qt.models.molecule_model.MoleculeModel,
		) -> tuple[float, float, float, float] | None:
	"""Return one molecule's model-coordinate bounds from all of its atoms."""
	bounds = bounds_from_points([
		(float(atom_model.x), float(atom_model.y))
		for atom_model in molecule_model.atoms
	])
	return bounds


#============================================
def presentation_bounds(
		presentation_model: bkchem_qt.models.document_object.PresentationObject,
		) -> tuple[float, float, float, float] | None:
	"""Return persistent presentation geometry bounds.

	Point-based objects and rectangular objects may each carry geometry, so the
	union preserves every serialized coordinate rather than trusting scene-only
	item bounds.
	"""
	point_bounds = bounds_from_points([
		(float(x), float(y)) for x, y, _z in presentation_model.points
	])
	bounds = presentation_model.bounds
	if bounds is None:
		return point_bounds
	x, y, width, height = bounds
	rect_bounds = (
		min(x, x + width), min(y, y + height),
		max(x, x + width), max(y, y + height),
	)
	return union_bounds([point_bounds, rect_bounds])


#============================================
def top_level_bounds(
		object_model: object,
		) -> tuple[float, float, float, float] | None:
	"""Return persistent bounds for one molecule or presentation top level."""
	if isinstance(
			object_model, bkchem_qt.models.molecule_model.MoleculeModel,
			):
		bounds = molecule_bounds(object_model)
	elif isinstance(
			object_model, bkchem_qt.models.document_object.PresentationObject,
			):
		bounds = presentation_bounds(object_model)
	else:
		raise TypeError(f"Unsupported document object: {type(object_model)!r}")
	return bounds


#============================================
def transform_point(
		point: tuple[float, float], origin: tuple[float, float],
		scale_x: float, scale_y: float,
		) -> tuple[float, float]:
	"""Apply an axis-aligned affine scale/reflection about ``origin``."""
	x, y = point
	origin_x, origin_y = origin
	transformed = (
		origin_x + (x - origin_x) * scale_x,
		origin_y + (y - origin_y) * scale_y,
	)
	return transformed


#============================================
def translate_bounds(
		bounds: tuple[float, float, float, float] | None,
		dx: float,
		dy: float,
		) -> tuple[float, float, float, float] | None:
	"""Translate persistent ``(x, y, width, height)`` bounds unchanged in size."""
	if bounds is None:
		return None
	x, y, width, height = bounds
	translated = (x + dx, y + dy, width, height)
	return translated


#============================================
def transform_bounds(
		bounds: tuple[float, float, float, float] | None,
		origin: tuple[float, float], scale_x: float, scale_y: float,
		) -> tuple[float, float, float, float] | None:
	"""Transform ``(x, y, width, height)`` bounds and retain that encoding."""
	if bounds is None:
		return None
	x, y, width, height = bounds
	transformed = [
		transform_point((x, y), origin, scale_x, scale_y),
		transform_point((x + width, y), origin, scale_x, scale_y),
		transform_point((x, y + height), origin, scale_x, scale_y),
		transform_point((x + width, y + height), origin, scale_x, scale_y),
	]
	transformed_bounds = bounds_from_points(transformed)
	if transformed_bounds is None:
		return None
	left, top, right, bottom = transformed_bounds
	bounds = (left, top, right - left, bottom - top)
	return bounds
