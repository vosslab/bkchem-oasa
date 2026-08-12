#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Frame-relative branch fan geometry for schematic renderers."""

# Standard Library
import math


#============================================
def branch_fan_layout(
		origin: tuple[float, float],
		stem_unit: tuple[float, float],
		branch_angles: tuple[float, ...],
		lengths: tuple[float, ...],
		reflection_options: tuple[int, ...],
		collision_score: object,
		length_scale_options: tuple[tuple[float, ...], ...] = ()) -> tuple[tuple[float, float], ...]:
	"""Lay out a finite fan in a local frame and choose its safest reflection.

	Angles are relative to ``stem_unit`` in screen coordinates.  A caller owns
	the semantic meaning and styling of each arm; this routine only transforms
	geometry and deterministically chooses among explicitly allowed reflections
	and caller-authored arm-length candidates.
	"""
	if len(branch_angles) != len(lengths):
		raise ValueError("Branch fan angles and lengths must have equal size")
	if not branch_angles:
		raise ValueError("Branch fan requires at least one arm")
	if not reflection_options:
		raise ValueError("Branch fan requires at least one reflection option")
	if not length_scale_options:
		length_scale_options = (tuple(1.0 for _length in lengths),)
	for scales in length_scale_options:
		if len(scales) != len(lengths):
			raise ValueError("Branch fan length-scale option has invalid arm count")
		if not all(math.isfinite(scale) and scale > 0.0 for scale in scales):
			raise ValueError("Branch fan length scales must be finite and positive")
	stem_x, stem_y = stem_unit
	stem_length = math.hypot(stem_x, stem_y)
	if stem_length <= 1e-12:
		raise ValueError("Branch fan stem must have nonzero length")
	unit_x = stem_x / stem_length
	unit_y = stem_y / stem_length
	base_angle = math.atan2(unit_y, unit_x)
	candidates = []
	for scale_index, scales in enumerate(length_scale_options):
		for reflection in sorted(set(reflection_options)):
			if reflection not in (-1, 1):
				raise ValueError("Branch fan reflection must be -1 or 1")
			points = tuple(
				(
					origin[0] + (math.cos(base_angle + (reflection * math.radians(angle))) * length * scale),
					origin[1] + (math.sin(base_angle + (reflection * math.radians(angle))) * length * scale),
				)
				for angle, length, scale in zip(branch_angles, lengths, scales, strict=True)
			)
			candidates.append((float(collision_score(points)), scale_index, reflection, points))
	_score, _scale_index, _reflection, result = min(
		candidates, key=lambda candidate: (candidate[0], candidate[1], candidate[2])
	)
	return result
