"""Frontend-neutral insertion operations for direct-root CDML presentations."""

# Standard Library
import dataclasses
import math
import numbers

# local repo modules
import oasa.cdml_document
import oasa.cdml_standard
import oasa.cdml_writer
import oasa.cdml_xml


class CDMLPresentationInsertError(oasa.cdml_document.CDMLValidationError):
	"""Raised when one revision-bound presentation insertion is invalid."""


@dataclasses.dataclass(frozen=True)
class CDMLGeometricInsertRequest:
	"""One geometric presentation intent with immutable authored scene points."""

	expected_revision: int
	kind: str
	points: tuple[tuple[float, float], ...]


@dataclasses.dataclass(frozen=True)
class CDMLArrowInsertRequest:
	"""One declared Arrow kind, curve state, and two immutable endpoints."""

	expected_revision: int
	kind: str
	spline: bool
	endpoints: tuple[tuple[float, float], tuple[float, float]]


@dataclasses.dataclass(frozen=True)
class CDMLTextInsertRequest:
	"""One plain Text intent with a scene point and unformatted content."""

	expected_revision: int
	position: tuple[float, float]
	text: str


@dataclasses.dataclass(frozen=True)
class CDMLPlusInsertRequest:
	"""One symbolic Plus intent at a scene-space center point."""

	expected_revision: int
	position: tuple[float, float]


@dataclasses.dataclass(frozen=True)
class CDMLWavyInsertRequest:
	"""One Wavy-line intent with frontend-independent endpoint geometry."""

	expected_revision: int
	start: tuple[float, float]
	end: tuple[float, float]


@dataclasses.dataclass(frozen=True)
class CDMLPresentationInsertResult:
	"""Immutable accepted presentation insertion with stable durable IDs."""

	snapshot: oasa.cdml_document.CDMLSnapshot
	changed: bool
	commit: oasa.cdml_document.CDMLCommit
	presentation_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLPresentationReorderRequest:
	"""One revision-bound source-order operation for durable presentation roots."""

	expected_revision: int
	mode: str
	root_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class CDMLPresentationReorderResult:
	"""Immutable result of one backend-owned presentation stack operation."""

	snapshot: oasa.cdml_document.CDMLSnapshot
	changed: bool
	commit: oasa.cdml_document.CDMLCommit | None


_BOUNDED_GEOMETRIC_KINDS = frozenset({"rect", "square", "oval", "circle"})
_PATH_GEOMETRIC_KINDS = frozenset({"polygon", "polyline"})
_GEOMETRIC_KINDS = _BOUNDED_GEOMETRIC_KINDS | _PATH_GEOMETRIC_KINDS
_ARROW_KINDS = frozenset({
	"normal", "electron", "retro", "equilibrium", "equilibrium2",
})
_ARROW_DEFAULTS = {
	"normal": ("no", "yes", "(8,10,3)"),
	"electron": ("no", "yes", "(8,10,3)"),
	"retro": ("no", "yes", "(8,10,3)"),
	"equilibrium": ("no", "yes", "(8,10,3)"),
	"equilibrium2": ("no", "yes", "(8,10,3)"),
}
_PRESENTATION_ROOT_NAMES = frozenset({
	"arrow", "plus", "text", "rect", "oval", "square", "circle",
	"polygon", "polyline",
})
_REORDER_MODES = frozenset({"bring-to-front", "send-back", "swap-at-slots"})
WAVY_SEGMENT_LENGTH = 12.0
WAVY_MAX_AMPLITUDE = 4.0
WAVY_MAX_SEGMENTS = 4096


#============================================
def _point(value: object, label: str) -> tuple[float, float]:
	"""Return one exact finite immutable scene point or raise a typed error."""
	if type(value) is not tuple or len(value) != 2:
		raise CDMLPresentationInsertError(
			f"Presentation insertion {label} must be an immutable two-coordinate tuple",
		)
	if any(
			type(coordinate) is bool or not isinstance(coordinate, numbers.Real)
			for coordinate in value
			):
		raise CDMLPresentationInsertError(
			f"Presentation insertion {label} must contain finite real coordinates",
		)
	try:
		point = float(value[0]), float(value[1])
	except (OverflowError, ValueError) as error:
		raise CDMLPresentationInsertError(
			f"Presentation insertion {label} must contain finite real coordinates",
		) from error
	if not all(math.isfinite(coordinate) for coordinate in point):
		raise CDMLPresentationInsertError(
			f"Presentation insertion {label} must contain finite real coordinates",
		)
	return point


#============================================
def _points(value: object, label: str) -> tuple[tuple[float, float], ...]:
	"""Return an exact immutable nonempty point sequence or raise a typed error."""
	if type(value) is not tuple or not value:
		raise CDMLPresentationInsertError(
			f"Presentation insertion {label} must be a nonempty immutable tuple",
		)
	return tuple(_point(point, f"{label}[{index}]") for index, point in enumerate(value))


#============================================
def _validate_request(
		request: object,
		) -> tuple[str, tuple[tuple[float, float], ...]]:
	"""Validate one exact geometric request before authoritative XML work."""
	if type(request) is not CDMLGeometricInsertRequest:
		raise CDMLPresentationInsertError(
			"Geometric insertion requires an exact geometric request",
		)
	if type(request.expected_revision) is not int:
		raise CDMLPresentationInsertError(
			"Geometric insertion expected_revision must be an int",
		)
	if type(request.kind) is not str or request.kind not in _GEOMETRIC_KINDS:
		raise CDMLPresentationInsertError(
			"Geometric insertion kind is unsupported",
		)
	points = _points(request.points, "points")
	minimum = 3 if request.kind == "polygon" else 2
	if len(points) != 2 and request.kind in _BOUNDED_GEOMETRIC_KINDS:
		raise CDMLPresentationInsertError(
			"Bounded geometric insertion requires exactly two scene points",
		)
	if len(points) < minimum:
		raise CDMLPresentationInsertError(
			f"{request.kind} insertion requires at least {minimum} scene points",
		)
	if any(first == second for first, second in zip(points, points[1:])):
		raise CDMLPresentationInsertError(
			"Geometric insertion cannot contain zero-length segments",
		)
	if request.kind == "polygon" and points[0] == points[-1]:
		raise CDMLPresentationInsertError(
			"Polygon closure is implicit; do not repeat the first scene point",
		)
	if request.kind in _BOUNDED_GEOMETRIC_KINDS and points[0] == points[1]:
		raise CDMLPresentationInsertError(
			"Bounded geometric insertion requires nonzero bounds",
		)
	return request.kind, points


#============================================
def _constrained_bounds(
		kind: str, points: tuple[tuple[float, float], ...],
		) -> tuple[float, float, float, float]:
	"""Return canonical bounds, constraining square and circle extents."""
	start, end = points
	if kind in {"square", "circle"}:
		delta_x = end[0] - start[0]
		delta_y = end[1] - start[1]
		side = max(abs(delta_x), abs(delta_y))
		end = (
			start[0] + math.copysign(side, delta_x if delta_x else 1.0),
			start[1] + math.copysign(side, delta_y if delta_y else 1.0),
		)
	left, right = sorted((start[0], end[0]))
	top, bottom = sorted((start[1], end[1]))
	return left, top, right, bottom


#============================================
def _element(document: object, root: object, local_name: str) -> object:
	"""Create one direct core element in the document root's namespace style."""
	qualified_name = local_name if root.prefix is None else f"{root.prefix}:{local_name}"
	if root.namespaceURI:
		return document.createElementNS(root.namespaceURI, qualified_name)
	return document.createElement(local_name)


#============================================
def _cm_text(value: float) -> str:
	"""Serialize one scene-space point coordinate in CDML centimetres."""
	return f"{value / oasa.cdml_writer.POINTS_PER_CM:.3f}cm"


#============================================
def _document_context(
		session: object, expected_revision: object,
		) -> tuple[object, object, object]:
	"""Capture one exact authoritative snapshot and detached validated DOM."""
	if type(session) is not oasa.cdml_document.CDMLDocumentSession:
		raise CDMLPresentationInsertError(
			"Presentation insertion requires an exact document session",
		)
	if type(expected_revision) is not int:
		raise CDMLPresentationInsertError(
			"Presentation insertion expected_revision must be an int",
		)
	snapshot = session.snapshot()
	if snapshot.revision != expected_revision:
		raise oasa.cdml_document.CDMLRevisionConflictError(
			"Presentation insertion expected revision does not match current revision",
		)
	document = oasa.cdml_xml.parse_cdml_dom(snapshot.cdml.encode("utf-8"))
	return snapshot, document, document.documentElement


#============================================
def _insertion_context(
		session: object, expected_revision: object,
		) -> tuple[object, object, object, object]:
	"""Capture exact document context plus its effective drawing standard."""
	snapshot, document, root = _document_context(session, expected_revision)
	standard = session.drawing_standard(
		oasa.cdml_standard.CDMLDrawingStandardQuery(snapshot.revision),
	)
	return snapshot, standard, document, root


#============================================
def _commit_root(
		session: oasa.cdml_document.CDMLDocumentSession,
		snapshot: oasa.cdml_document.CDMLSnapshot,
		document: object, root: object, presentation: object, token_kind: str,
		) -> CDMLPresentationInsertResult:
	"""Append and atomically accept one internally correlated presentation root."""
	provisional_id = (
		f"__bkchem_new__presentation-r{snapshot.revision}-{token_kind}"
	)
	presentation.setAttribute("id", provisional_id)
	root.appendChild(presentation)
	commit = session.commit(
		expected_revision=snapshot.revision,
		complete_cdml=document.toxml(),
	)
	return CDMLPresentationInsertResult(
		commit.snapshot, True, commit, (commit.id_map[provisional_id],),
	)


#============================================
def insert_geometric(
		session: object, request: CDMLGeometricInsertRequest,
		) -> CDMLPresentationInsertResult:
	"""Insert one styled geometric root into the authoritative document."""
	kind, points = _validate_request(request)
	snapshot, standard, document, root = _insertion_context(
		session, request.expected_revision,
	)
	presentation = _element(document, root, kind)
	presentation.setAttribute("line_color", standard.line_color)
	presentation.setAttribute("width", f"{standard.line_width:g}")
	if kind in _PATH_GEOMETRIC_KINDS:
		if kind == "polyline":
			presentation.setAttribute("spline", "no")
		else:
			presentation.setAttribute("area_color", standard.area_color)
		for x_coordinate, y_coordinate in points:
			point = _element(document, root, "point")
			point.setAttribute("x", _cm_text(x_coordinate))
			point.setAttribute("y", _cm_text(y_coordinate))
			presentation.appendChild(point)
	else:
		left, top, right, bottom = _constrained_bounds(kind, points)
		presentation.setAttribute("x1", _cm_text(left))
		presentation.setAttribute("y1", _cm_text(top))
		presentation.setAttribute("x2", _cm_text(right))
		presentation.setAttribute("y2", _cm_text(bottom))
		presentation.setAttribute("area_color", standard.area_color)
	return _commit_root(
		session, snapshot, document, root, presentation, "geometric",
	)


#============================================
def _endpoints(
		start_value: object, end_value: object, label: str,
		) -> tuple[tuple[float, float], tuple[float, float]]:
	"""Validate and return two distinct finite presentation endpoints."""
	start = _point(start_value, f"{label} start")
	end = _point(end_value, f"{label} end")
	if start == end:
		raise CDMLPresentationInsertError(
			f"{label} insertion requires two distinct scene points",
		)
	return start, end


#============================================
def insert_arrow(
		session: object, request: CDMLArrowInsertRequest,
		) -> CDMLPresentationInsertResult:
	"""Insert one declared Arrow with canonical standard-derived semantics."""
	if type(request) is not CDMLArrowInsertRequest:
		raise CDMLPresentationInsertError(
			"Arrow insertion requires an exact Arrow request",
		)
	if type(request.expected_revision) is not int:
		raise CDMLPresentationInsertError(
			"Arrow insertion expected_revision must be an int",
		)
	if type(request.kind) is not str or request.kind not in _ARROW_KINDS:
		raise CDMLPresentationInsertError("Arrow insertion kind is unsupported")
	if type(request.spline) is not bool:
		raise CDMLPresentationInsertError("Arrow insertion spline must be a bool")
	if type(request.endpoints) is not tuple or len(request.endpoints) != 2:
		raise CDMLPresentationInsertError(
			"Arrow insertion endpoints must be an immutable pair of scene points",
		)
	start, end = _endpoints(request.endpoints[0], request.endpoints[1], "Arrow")
	snapshot, standard, document, root = _insertion_context(
		session, request.expected_revision,
	)
	arrow = _element(document, root, "arrow")
	start_head, end_head, shape = _ARROW_DEFAULTS[request.kind]
	arrow.setAttribute("type", request.kind)
	arrow.setAttribute("start", start_head)
	arrow.setAttribute("end", end_head)
	arrow.setAttribute("spline", "yes" if request.spline else "no")
	arrow.setAttribute("width", f"{standard.line_width:g}")
	arrow.setAttribute("color", standard.line_color)
	arrow.setAttribute("shape", shape)
	for x_coordinate, y_coordinate in (start, end):
		point = _element(document, root, "point")
		point.setAttribute("x", _cm_text(x_coordinate))
		point.setAttribute("y", _cm_text(y_coordinate))
		arrow.appendChild(point)
	return _commit_root(session, snapshot, document, root, arrow, "arrow")


#============================================
def insert_text(
		session: object, request: CDMLTextInsertRequest,
		) -> CDMLPresentationInsertResult:
	"""Insert one plain Text root with standard-derived font appearance."""
	if type(request) is not CDMLTextInsertRequest:
		raise CDMLPresentationInsertError(
			"Text insertion requires an exact Text request",
		)
	if type(request.text) is not str or not request.text or request.text != request.text.strip():
		raise CDMLPresentationInsertError(
			"Text insertion content must be a nonblank stripped string",
		)
	position = _point(request.position, "Text position")
	snapshot, standard, document, root = _insertion_context(
		session, request.expected_revision,
	)
	text = _element(document, root, "text")
	point = _element(document, root, "point")
	point.setAttribute("x", _cm_text(position[0]))
	point.setAttribute("y", _cm_text(position[1]))
	font = _element(document, root, "font")
	font.setAttribute("family", standard.font_family)
	font.setAttribute("size", str(standard.font_size))
	font.setAttribute("color", standard.line_color)
	if standard.area_color:
		text.setAttribute("background-color", standard.area_color)
	ftext = _element(document, root, "ftext")
	ftext.appendChild(document.createTextNode(request.text))
	text.appendChild(point)
	text.appendChild(font)
	text.appendChild(ftext)
	return _commit_root(session, snapshot, document, root, text, "text")


#============================================
def insert_plus(
		session: object, request: CDMLPlusInsertRequest,
		) -> CDMLPresentationInsertResult:
	"""Insert one symbolic Plus centered at an exact finite scene point."""
	if type(request) is not CDMLPlusInsertRequest:
		raise CDMLPresentationInsertError(
			"Plus insertion requires an exact Plus request",
		)
	position = _point(request.position, "Plus position")
	snapshot, standard, document, root = _insertion_context(
		session, request.expected_revision,
	)
	plus = _element(document, root, "plus")
	plus.setAttribute("font_size", "18")
	plus.setAttribute("color", standard.line_color)
	if standard.area_color:
		plus.setAttribute("background-color", standard.area_color)
	point = _element(document, root, "point")
	point.setAttribute("x", _cm_text(position[0]))
	point.setAttribute("y", _cm_text(position[1]))
	plus.appendChild(point)
	return _commit_root(session, snapshot, document, root, plus, "plus")


#============================================
def wavy_points(
		start_value: object, end_value: object,
		) -> tuple[tuple[float, float], ...]:
	"""Return bounded Wavy zigzag geometry with exact finite endpoints."""
	start = _point(start_value, "Wavy start")
	end = _point(end_value, "Wavy end")
	if start == end:
		return ()
	dx = end[0] - start[0]
	dy = end[1] - start[1]
	if not math.isfinite(dx) or not math.isfinite(dy):
		raise CDMLPresentationInsertError("Wavy endpoints are too far apart")
	length = math.hypot(dx, dy)
	if not math.isfinite(length):
		raise CDMLPresentationInsertError("Wavy length must be finite")
	segment_estimate = length / WAVY_SEGMENT_LENGTH
	if segment_estimate > WAVY_MAX_SEGMENTS + 0.5:
		raise CDMLPresentationInsertError(
			f"Wavy geometry exceeds {WAVY_MAX_SEGMENTS} segment safety limit",
		)
	segments = max(2, round(segment_estimate))
	amplitude = min(WAVY_MAX_AMPLITUDE, length / 6.0)
	normal_x = -dy / length
	normal_y = dx / length
	if not all(math.isfinite(value) for value in (amplitude, normal_x, normal_y)):
		raise CDMLPresentationInsertError("Wavy derived geometry must be finite")
	points = [start]
	for index in range(1, segments):
		fraction = index / segments
		offset = amplitude if index % 2 else -amplitude
		x_coordinate = start[0] + dx * fraction + normal_x * offset
		y_coordinate = start[1] + dy * fraction + normal_y * offset
		if not math.isfinite(x_coordinate) or not math.isfinite(y_coordinate):
			raise CDMLPresentationInsertError(
				"Wavy derived coordinates must be finite",
			)
		points.append((x_coordinate, y_coordinate))
	points.append(end)
	return tuple(points)


#============================================
def insert_wavy(
		session: object, request: CDMLWavyInsertRequest,
		) -> CDMLPresentationInsertResult:
	"""Insert one standard-styled Wavy root with backend-derived geometry."""
	if type(request) is not CDMLWavyInsertRequest:
		raise CDMLPresentationInsertError(
			"Wavy insertion requires an exact Wavy request",
		)
	points = wavy_points(request.start, request.end)
	if len(points) < 2:
		raise CDMLPresentationInsertError(
			"Wavy insertion requires two distinct scene points",
		)
	snapshot, standard, document, root = _insertion_context(
		session, request.expected_revision,
	)
	polyline = _element(document, root, "polyline")
	polyline.setAttribute("line_color", standard.line_color)
	polyline.setAttribute("width", f"{standard.line_width:g}")
	polyline.setAttribute("spline", "no")
	polyline.setAttribute("style", "wavy")
	for x_coordinate, y_coordinate in points:
		point = _element(document, root, "point")
		point.setAttribute("x", _cm_text(x_coordinate))
		point.setAttribute("y", _cm_text(y_coordinate))
		polyline.appendChild(point)
	return _commit_root(session, snapshot, document, root, polyline, "wavy")


#============================================
def _direct_presentation_roots(root: object) -> tuple[object, ...]:
	"""Return direct core presentation roots in authoritative source order."""
	records = []
	for child in root.childNodes:
		if child.nodeType != child.ELEMENT_NODE:
			continue
		local_name = child.localName or child.tagName.rsplit(":", 1)[-1]
		if (
			local_name in _PRESENTATION_ROOT_NAMES
			and child.namespaceURI in (None, "", root.namespaceURI)
			and child.namespaceURI in (None, "", oasa.cdml_xml.CDML_NAMESPACE_URI)
		):
			records.append(child)
	return tuple(records)


#============================================
def _validate_reorder_request(
		request: object,
		) -> tuple[str, tuple[str, ...]]:
	"""Validate one exact immutable stack-reorder request."""
	if type(request) is not CDMLPresentationReorderRequest:
		raise CDMLPresentationInsertError(
			"Presentation reorder requires an exact reorder request",
		)
	if type(request.expected_revision) is not int:
		raise CDMLPresentationInsertError(
			"Presentation reorder expected_revision must be an int",
		)
	if type(request.mode) is not str or request.mode not in _REORDER_MODES:
		raise CDMLPresentationInsertError("Presentation reorder mode is unsupported")
	if type(request.root_ids) is not tuple or not request.root_ids:
		raise CDMLPresentationInsertError(
			"Presentation reorder root_ids must be a nonempty immutable tuple",
		)
	if any(
			type(identifier) is not str or not identifier.strip()
			for identifier in request.root_ids
		):
		raise CDMLPresentationInsertError(
			"Presentation reorder root IDs must be nonblank strings",
		)
	if len(set(request.root_ids)) != len(request.root_ids):
		raise CDMLPresentationInsertError(
			"Presentation reorder root IDs must be unique",
		)
	if request.mode == "swap-at-slots" and len(request.root_ids) < 2:
		raise CDMLPresentationInsertError(
			"Presentation reorder swap requires at least two roots",
		)
	return request.mode, request.root_ids


#============================================
def reorder_presentations(
		session: object, request: CDMLPresentationReorderRequest,
		) -> CDMLPresentationReorderResult:
	"""Reorder durable direct presentation roots while preserving every node slot."""
	mode, root_ids = _validate_reorder_request(request)
	snapshot, document, root = _document_context(
		session, request.expected_revision,
	)
	if root.namespaceURI not in (None, "", oasa.cdml_xml.CDML_NAMESPACE_URI):
		raise CDMLPresentationInsertError(
			"Presentation reorder requires a core CDML root",
		)
	records = _direct_presentation_roots(root)
	by_id: dict[str, list[object]] = {}
	for record in records:
		identifier = record.getAttribute("id")
		if identifier:
			by_id.setdefault(identifier, []).append(record)
	selected_set = set()
	for identifier in root_ids:
		matches = by_id.get(identifier, [])
		if len(matches) != 1:
			raise CDMLPresentationInsertError(
				"Presentation reorder target is not one direct durable presentation root",
			)
		selected_set.add(matches[0])
	selected = [record for record in records if record in selected_set]
	children = list(root.childNodes)
	elements = [child for child in children if child.nodeType == child.ELEMENT_NODE]
	if mode == "bring-to-front":
		ordered_elements = [
			child for child in elements if child not in selected_set
		] + selected
	elif mode == "send-back":
		ordered_elements = selected + [
			child for child in elements if child not in selected_set
		]
	else:
		reversed_selected = iter(reversed(selected))
		ordered_elements = [
			next(reversed_selected) if child in selected_set else child
			for child in elements
		]
	ordered_iterator = iter(ordered_elements)
	ordered = [
		next(ordered_iterator) if child.nodeType == child.ELEMENT_NODE else child
		for child in children
	]
	if ordered == children:
		return CDMLPresentationReorderResult(snapshot, False, None)
	for child in children:
		root.removeChild(child)
	for child in ordered:
		root.appendChild(child)
	commit = session.commit(
		expected_revision=snapshot.revision,
		complete_cdml=document.toxml(),
	)
	return CDMLPresentationReorderResult(commit.snapshot, True, commit)
