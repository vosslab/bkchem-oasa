"""Backend-owned insertion of portable rectangular and round bracket artwork."""

# Standard Library
import dataclasses
import math
import numbers
import re

# local repo modules
import oasa.cdml_document
import oasa.cdml_bracket_pair
import oasa.cdml_standard
import oasa.cdml_writer
import oasa.cdml_xml


class CDMLBracketInsertError(oasa.cdml_document.CDMLValidationError):
	"""Raised when one revision-bound bracket insertion is invalid."""


class CDMLBracketPropertiesPatchError(oasa.cdml_document.CDMLValidationError):
	"""Raised when one revision-bound bracket-pair appearance patch is invalid."""


@dataclasses.dataclass(frozen=True)
class CDMLBracketInsertRequest:
	"""One immutable pair of bracket curves inside normalized scene bounds."""

	expected_revision: int
	style: str
	bounds: tuple[float, float, float, float]


@dataclasses.dataclass(frozen=True)
class CDMLBracketInsertResult:
	"""The accepted bracket-pair commit with durable pair and member addresses."""

	snapshot: oasa.cdml_document.CDMLSnapshot
	changed: bool
	commit: oasa.cdml_document.CDMLCommit | None
	pair_id: str
	left_id: str
	right_id: str


@dataclasses.dataclass(frozen=True)
class CDMLBracketPropertiesPatch:
	"""One exact-revision stroke patch for one durable bracket pair."""

	expected_revision: int
	pair_id: str
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLBracketPropertiesPatchResult:
	"""The current or accepted snapshot for one bracket-pair appearance patch."""

	snapshot: oasa.cdml_document.CDMLSnapshot
	changed: bool
	commit: oasa.cdml_document.CDMLCommit | None
	pair_id: str
	member_ids: tuple[str, str]


_STYLES = frozenset({"rectangular", "round"})
_PATCH_FIELDS = frozenset({"line_width", "line_color"})
_CORE_NAMESPACES = frozenset({"", oasa.cdml_document.CDML_NAMESPACE_URI})


#============================================
def _validate_request(
		request: object,
		) -> tuple[str, tuple[float, float, float, float]]:
	"""Validate exact style and normalized finite bounds before XML work."""
	if type(request) is not CDMLBracketInsertRequest:
		raise CDMLBracketInsertError("Bracket insertion requires an exact request")
	if type(request.expected_revision) is not int:
		raise CDMLBracketInsertError("Bracket expected_revision must be an int")
	if type(request.style) is not str or request.style not in _STYLES:
		raise CDMLBracketInsertError("Bracket style must be rectangular or round")
	if type(request.bounds) is not tuple or len(request.bounds) != 4:
		raise CDMLBracketInsertError("Bracket bounds must be an immutable four-tuple")
	if any(
			type(value) is bool or not isinstance(value, numbers.Real)
			or not math.isfinite(value)
			for value in request.bounds
		):
		raise CDMLBracketInsertError("Bracket bounds must contain finite real numbers")
	left, top, right, bottom = tuple(float(value) for value in request.bounds)
	if not left < right or not top < bottom:
		raise CDMLBracketInsertError("Bracket bounds must have strict normalized order")
	return request.style, (left, top, right, bottom)


#============================================
def _validate_patch(
		request: object,
		) -> tuple[str, tuple[tuple[str, object], ...]]:
	"""Validate explicit pair-stroke intent before authoritative target lookup."""
	if type(request) is not CDMLBracketPropertiesPatch:
		raise CDMLBracketPropertiesPatchError(
			"Bracket appearance requires an exact properties patch",
		)
	if type(request.expected_revision) is not int:
		raise CDMLBracketPropertiesPatchError(
			"Bracket appearance expected_revision must be an int",
		)
	if type(request.pair_id) is not str or not request.pair_id.strip():
		raise CDMLBracketPropertiesPatchError(
			"Bracket appearance pair_id must contain a non-whitespace character",
		)
	if type(request.changes) is not tuple:
		raise CDMLBracketPropertiesPatchError(
			"Bracket appearance changes must be an immutable tuple",
		)
	validated = []
	seen = set()
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLBracketPropertiesPatchError(
				"Bracket appearance changes must be field/value pairs",
			)
		field_name, value = change
		if type(field_name) is not str or field_name not in _PATCH_FIELDS:
			raise CDMLBracketPropertiesPatchError(
				"Bracket appearance field is unsupported",
			)
		if field_name in seen:
			raise CDMLBracketPropertiesPatchError(
				"Bracket appearance fields must be unique",
			)
		seen.add(field_name)
		if field_name == "line_width":
			if (
				type(value) is bool or not isinstance(value, numbers.Real)
				or not math.isfinite(value) or not 0.1 <= value <= 20
			):
				raise CDMLBracketPropertiesPatchError(
					"Bracket appearance line_width must be a finite number from 0.1 to 20",
				)
			value = float(value)
		elif type(value) is not str or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
			raise CDMLBracketPropertiesPatchError(
				"Bracket appearance line_color must be a six-digit hex color",
			)
		else:
			value = value.lower()
		validated.append((field_name, value))
	return request.pair_id, tuple(validated)


#============================================
def _element(document: object, root: object, local_name: str) -> object:
	"""Create one core element in the document root's namespace style."""
	prefix = root.prefix
	qualified_name = local_name if prefix is None else f"{prefix}:{local_name}"
	if root.namespaceURI:
		return document.createElementNS(root.namespaceURI, qualified_name)
	return document.createElement(local_name)


#============================================
def _cm_text(value: float) -> str:
	"""Serialize one scene-space point coordinate in CDML centimetres."""
	return f"{value / oasa.cdml_writer.POINTS_PER_CM:.3f}cm"


#============================================
def _point_sets(
		style: str, bounds: tuple[float, float, float, float],
		) -> tuple[tuple[tuple[float, float], ...], ...]:
	"""Return classic-compatible left and right bracket control points."""
	left, top, right, bottom = bounds
	dx = 0.05 * math.hypot(right - left, bottom - top)
	if style == "round":
		dy = 0.05 * (bottom - top)
		return (
			((left + dx, top), (left, top + dy), (left, bottom - dy), (left + dx, bottom)),
			((right - dx, top), (right, top + dy), (right, bottom - dy), (right - dx, bottom)),
		)
	return (
		((left + dx, top), (left, top), (left, bottom), (left + dx, bottom)),
		((right - dx, top), (right, top), (right, bottom), (right - dx, bottom)),
	)


#============================================
def insert_brackets(
		session: object, request: CDMLBracketInsertRequest,
		) -> CDMLBracketInsertResult:
	"""Append one backend-allocated bracket pair as an atomic complete document."""
	if type(session) is not oasa.cdml_document.CDMLDocumentSession:
		raise CDMLBracketInsertError("Bracket insertion requires an exact session")
	style, bounds = _validate_request(request)
	snapshot = session.snapshot()
	if snapshot.revision != request.expected_revision:
		raise oasa.cdml_document.CDMLRevisionConflictError(
			"Bracket expected revision does not match current revision",
		)
	standard = session.drawing_standard(
		oasa.cdml_standard.CDMLDrawingStandardQuery(snapshot.revision),
	)
	# Keep every complete-CDML read behind the lxml authorization policy before
	# the established defused-DOM compatibility representation is constructed.
	document = oasa.cdml_xml.parse_cdml_dom(snapshot.cdml.encode("utf-8"))
	root = document.documentElement
	provisional_ids = tuple(
		f"__bkchem_new__bracket-r{snapshot.revision}-{side}"
		for side in ("left", "right")
	)
	for side, provisional_id, points in zip(
			("left", "right"), provisional_ids, _point_sets(style, bounds),
		):
		polyline = _element(document, root, "polyline")
		polyline.setAttribute("id", provisional_id)
		polyline.setAttribute("bracket_pair", provisional_ids[0])
		polyline.setAttribute("bracket_side", side)
		polyline.setAttribute("line_color", standard.line_color)
		polyline.setAttribute("width", f"{standard.line_width:g}")
		polyline.setAttribute("spline", "yes" if style == "round" else "no")
		for x_coordinate, y_coordinate in points:
			point = _element(document, root, "point")
			point.setAttribute("x", _cm_text(x_coordinate))
			point.setAttribute("y", _cm_text(y_coordinate))
			polyline.appendChild(point)
		root.appendChild(polyline)
	commit = session.commit(
		expected_revision=request.expected_revision, complete_cdml=document.toxml(),
	)
	left_id, right_id = tuple(commit.id_map[identifier] for identifier in provisional_ids)
	return CDMLBracketInsertResult(
		commit.snapshot, True, commit, left_id, left_id, right_id,
	)


#============================================
def _is_core_polyline(element: object) -> bool:
	"""Return whether one direct candidate is a core polyline."""
	return (
		element.nodeType == element.ELEMENT_NODE
		and (element.namespaceURI or "") in _CORE_NAMESPACES
		and (element.localName or element.tagName) == "polyline"
	)


#============================================
def _local_name(element: object) -> str:
	"""Return one core element's local name without changing its stored form."""
	return str(element.localName or element.tagName)


#============================================
def _pair_members(document: object, pair_id: str) -> tuple[object, object]:
	"""Resolve exactly one complete direct-core bracket pair in a candidate DOM."""
	root = document.documentElement
	for left, right in oasa.cdml_bracket_pair.valid_bracket_members(
		tuple(child for child in root.childNodes if child.nodeType == child.ELEMENT_NODE),
		_is_core_polyline, _local_name,
	):
		if left.getAttribute("id") == pair_id:
			return left, right
	raise CDMLBracketPropertiesPatchError(
		"Bracket appearance requires one complete valid marked pair",
	)


#============================================
def _member_values(member: object) -> dict[str, object]:
	"""Return one validated bracket-member stroke without supplying fallbacks."""
	width_text = member.getAttribute("width")
	try:
		width = float(width_text)
	except ValueError as error:
		raise CDMLBracketPropertiesPatchError(
			"Bracket appearance member width must be a finite number",
		) from error
	if not math.isfinite(width) or not 0.1 <= width <= 20:
		raise CDMLBracketPropertiesPatchError(
			"Bracket appearance member width must be a finite number from 0.1 to 20",
		)
	color = member.getAttribute("line_color")
	if re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None:
		raise CDMLBracketPropertiesPatchError(
			"Bracket appearance member line_color must be a six-digit hex color",
		)
	return {"line_width": width, "line_color": color.lower()}


#============================================
def patch_bracket_properties(
		session: object, request: CDMLBracketPropertiesPatch,
		) -> CDMLBracketPropertiesPatchResult:
	"""Patch both validated bracket members in one authoritative transaction."""
	if type(session) is not oasa.cdml_document.CDMLDocumentSession:
		raise CDMLBracketPropertiesPatchError(
			"Bracket appearance requires an exact CDML document session",
		)
	pair_id, changes = _validate_patch(request)
	snapshot = session.snapshot()
	if snapshot.revision != request.expected_revision:
		raise oasa.cdml_document.CDMLRevisionConflictError(
			"Bracket appearance expected revision does not match current revision",
		)
	# The current snapshot is complete CDML, so use the same authorization gate
	# used by all other backend presentation operations.
	candidate_dom = oasa.cdml_xml.parse_cdml_dom(snapshot.cdml.encode("utf-8"))
	left, right = _pair_members(candidate_dom, pair_id)
	member_ids = (left.getAttribute("id"), right.getAttribute("id"))
	values = tuple(_member_values(member) for member in (left, right))
	if not changes or all(
		all(value[field_name] == changed_value for value in values)
		for field_name, changed_value in changes
		):
		return CDMLBracketPropertiesPatchResult(
			snapshot, False, None, pair_id, member_ids,
		)
	attribute_names = {"line_width": "width", "line_color": "line_color"}
	for member in (left, right):
		for field_name, value in changes:
			text = f"{value:g}" if field_name == "line_width" else value
			member.setAttribute(attribute_names[field_name], text)
	candidate = oasa.cdml_document.CDMLDocument.parse(
		candidate_dom.toxml(), validation="compat",
	)
	candidate.validate(validation="strict")
	candidate_cdml = candidate.serialize()
	if candidate_cdml == snapshot.cdml:
		return CDMLBracketPropertiesPatchResult(
			snapshot, False, None, pair_id, member_ids,
		)
	commit = session.commit(
		expected_revision=request.expected_revision, complete_cdml=candidate_cdml,
	)
	return CDMLBracketPropertiesPatchResult(
		commit.snapshot, True, commit, pair_id, member_ids,
	)
