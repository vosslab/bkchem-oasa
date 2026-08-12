"""Recognition of durable bracket-pair relationships on core polylines."""

# Standard Library
import math

# local repo modules
import oasa.cdml_projection_plan


_ROUND_SPLINES = frozenset({"yes", "true", "1"})
_RECTANGULAR_SPLINES = frozenset({"no", "false", "0"})


#============================================
def _shared_width(left: object, right: object) -> float | None:
	"""Return a shared finite width, retaining imported disagreement as null."""
	left_text = left.getAttribute("width")
	right_text = right.getAttribute("width")
	if left_text != right_text:
		return None
	try:
		width = float(left_text)
	except ValueError:
		return None
	if not math.isfinite(width):
		return None
	return width


#============================================
def _shared_color(left: object, right: object) -> str | None:
	"""Return an authored shared color without normalizing imported spelling."""
	left_color = left.getAttribute("line_color")
	right_color = right.getAttribute("line_color")
	if left_color != right_color:
		return None
	return left_color or None


#============================================
def _pair_style(left: object, right: object) -> str | None:
	"""Recognize only matching established spline spellings for a pair."""
	left_spline = left.getAttribute("spline")
	right_spline = right.getAttribute("spline")
	if left_spline in _ROUND_SPLINES and right_spline in _ROUND_SPLINES:
		return "round"
	if left_spline in _RECTANGULAR_SPLINES and right_spline in _RECTANGULAR_SPLINES:
		return "rectangular"
	return None


#============================================
def valid_bracket_members(
		elements: tuple[object, ...], is_core_element: object, local_name: object,
		) -> tuple[tuple[object, object], ...]:
	"""Return only exact direct-core bracket sides in left-root source order."""
	polylines = tuple(
		element for element in elements
		if is_core_element(element) and local_name(element) == "polyline"
	)
	identifier_counts = {}
	for polyline in polylines:
		identifier = polyline.getAttribute("id")
		if identifier:
			identifier_counts[identifier] = identifier_counts.get(identifier, 0) + 1
	by_pair = {}
	for polyline in polylines:
		pair_id = polyline.getAttribute("bracket_pair")
		if pair_id:
			by_pair.setdefault(pair_id, []).append(polyline)
	members = []
	for pair_id, candidates in by_pair.items():
		if len(candidates) != 2:
			continue
		left = next((item for item in candidates if item.getAttribute("bracket_side") == "left"), None)
		right = next((item for item in candidates if item.getAttribute("bracket_side") == "right"), None)
		if left is None or right is None or left is right:
			continue
		left_id = left.getAttribute("id")
		right_id = right.getAttribute("id")
		if (
			not left_id or not right_id or left_id == right_id or pair_id != left_id
			or identifier_counts[left_id] != 1 or identifier_counts[right_id] != 1
			or _pair_style(left, right) is None
		):
			continue
		members.append((left, right))
	ordered = tuple(sorted(members, key=lambda pair: elements.index(pair[0])))
	return ordered


#============================================
def observe_bracket_pairs(
		elements: tuple[object, ...], is_core_element: object, local_name: object,
		) -> tuple[oasa.cdml_projection_plan.CDMLBracketPairRecord, ...]:
	"""Return immutable facts for exact valid pairs and no proximity guesses."""
	records = []
	for left, right in valid_bracket_members(elements, is_core_element, local_name):
		records.append(oasa.cdml_projection_plan.CDMLBracketPairRecord(
			left.getAttribute("id"), (left.getAttribute("id"), right.getAttribute("id")),
			_pair_style(left, right), _shared_width(left, right), _shared_color(left, right),
		))
	return tuple(records)
