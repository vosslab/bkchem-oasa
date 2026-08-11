"""Pure complete-CDML candidates used by frontend persistent actions."""

# Standard Library
import xml.dom.minidom

# local repo modules
import oasa.cdml_writer
import oasa.cdml_document
import oasa.cdml_standard
import oasa.safe_xml


_PRESENTATION_ROOT_NAMES = frozenset({
	"arrow", "plus", "text", "rect", "oval", "square", "circle",
	"polygon", "polyline",
})


#============================================
def _qualified_child_name(root: xml.dom.minidom.Element, local_name: str) -> str:
	"""Return a child name in the root's existing CDML prefix, if any."""
	prefix = root.prefix
	name = local_name if prefix is None else prefix + ":" + local_name
	return name


#============================================
def _cm_text(value: float) -> str:
	"""Format one scene-space point coordinate as canonical CDML centimetres."""
	text = "%.3fcm" % (float(value) / oasa.cdml_writer.POINTS_PER_CM)
	return text


#============================================
def _present_drawing_standard(value: object | None) -> object | None:
	"""Validate one stable observation and return it only when authored."""
	if value is None:
		return None
	if type(value) is not oasa.cdml_standard.CDMLDrawingStandardObservation:
		raise TypeError("Presentation candidate requires an exact drawing-standard observation")
	return value if value.present else None


#============================================
def append_arrow_candidate(
		complete_cdml: str, provisional_id: str,
		start: tuple[float, float], end: tuple[float, float],
		drawing_standard: object | None = None,
		) -> str:
	"""Append one normal arrow to a complete authoritative CDML document.

	The caller supplies only plain coordinates and a provisional correlation
	token.  OASA validates the resulting complete document and replaces that
	token with the durable persistent identifier in its immutable commit result.
	"""
	document = oasa.safe_xml.parse_dom_from_string(complete_cdml)
	root = document.documentElement
	standard = _present_drawing_standard(drawing_standard)
	arrow_name = _qualified_child_name(root, "arrow")
	point_name = _qualified_child_name(root, "point")
	namespace = root.namespaceURI
	if namespace:
		arrow = document.createElementNS(namespace, arrow_name)
	else:
		arrow = document.createElement(arrow_name)
	arrow.setAttribute("id", provisional_id)
	arrow.setAttribute("type", "normal")
	arrow.setAttribute("start", "no")
	arrow.setAttribute("end", "yes")
	arrow.setAttribute("spline", "no")
	arrow.setAttribute("width", "%g" % standard.line_width if standard else "1.5")
	arrow.setAttribute("color", standard.line_color if standard else "#000000")
	arrow.setAttribute("shape", "(8,10,3)")
	for x_coord, y_coord in (start, end):
		if namespace:
			point = document.createElementNS(namespace, point_name)
		else:
			point = document.createElement(point_name)
		point.setAttribute("x", _cm_text(x_coord))
		point.setAttribute("y", _cm_text(y_coord))
		arrow.appendChild(point)
	root.appendChild(arrow)
	candidate = document.toxml()
	return candidate


#============================================
def append_text_candidate(
		complete_cdml: str, provisional_id: str,
		position: tuple[float, float], text: str,
		drawing_standard: object | None = None,
		) -> str:
	"""Append one plain-text annotation to complete authoritative CDML.

	The caller supplies a frontend-only correlation token and plain scene-space
	values. OASA validates the complete candidate and replaces the token with a
	durable identifier in the accepted immutable result.
	"""
	document = oasa.safe_xml.parse_dom_from_string(complete_cdml)
	root = document.documentElement
	standard = _present_drawing_standard(drawing_standard)
	text_name = _qualified_child_name(root, "text")
	point_name = _qualified_child_name(root, "point")
	font_name = _qualified_child_name(root, "font")
	ftext_name = _qualified_child_name(root, "ftext")
	namespace = root.namespaceURI
	if namespace:
		text_element = document.createElementNS(namespace, text_name)
		point = document.createElementNS(namespace, point_name)
		font = document.createElementNS(namespace, font_name)
		ftext = document.createElementNS(namespace, ftext_name)
	else:
		text_element = document.createElement(text_name)
		point = document.createElement(point_name)
		font = document.createElement(font_name)
		ftext = document.createElement(ftext_name)
	text_element.setAttribute("id", provisional_id)
	point.setAttribute("x", _cm_text(position[0]))
	point.setAttribute("y", _cm_text(position[1]))
	font.setAttribute("family", standard.font_family if standard else "Arial")
	font.setAttribute("size", str(standard.font_size) if standard else "14")
	font.setAttribute("color", standard.line_color if standard else "#000000")
	if standard is not None and standard.area_color:
		text_element.setAttribute("background-color", standard.area_color)
	# A DOM text node performs the one required XML escaping during serialization.
	ftext.appendChild(document.createTextNode(text))
	text_element.appendChild(point)
	text_element.appendChild(font)
	text_element.appendChild(ftext)
	root.appendChild(text_element)
	candidate = document.toxml()
	return candidate


#============================================
def append_plus_candidate(
		complete_cdml: str, provisional_id: str,
		position: tuple[float, float],
		drawing_standard: object | None = None,
		) -> str:
	"""Append one symbolic Plus record to complete authoritative CDML.

	The stored point is the symbol's visual center.  Qt may use font metrics to
	project that center, but no graphics state participates in persistence.
	"""
	document = oasa.safe_xml.parse_dom_from_string(complete_cdml)
	root = document.documentElement
	standard = _present_drawing_standard(drawing_standard)
	plus_name = _qualified_child_name(root, "plus")
	point_name = _qualified_child_name(root, "point")
	namespace = root.namespaceURI
	if namespace:
		plus = document.createElementNS(namespace, plus_name)
		point = document.createElementNS(namespace, point_name)
	else:
		plus = document.createElement(plus_name)
		point = document.createElement(point_name)
	plus.setAttribute("id", provisional_id)
	plus.setAttribute("font_size", "18")
	plus.setAttribute("color", standard.line_color if standard else "#000000")
	if standard is not None and standard.area_color:
		plus.setAttribute("background-color", standard.area_color)
	point.setAttribute("x", _cm_text(position[0]))
	point.setAttribute("y", _cm_text(position[1]))
	plus.appendChild(point)
	root.appendChild(plus)
	candidate = document.toxml()
	return candidate


#============================================
def append_vector_candidate(
		complete_cdml: str, provisional_id: str, shape: str,
		start: tuple[float, float], end: tuple[float, float],
		drawing_standard: object | None = None,
		) -> str:
	"""Append one bounded Vector presentation record to complete CDML.

	The caller supplies only the selected core shape, two scene points, and a
	frontend-only correlation token.  This operation preserves every existing
	root child, including comments and opaque extension content, and appends one
	direct core presentation record for the normal complete-CDML commit route.
	"""
	if shape not in {"rect", "oval", "polyline"}:
		raise ValueError("Vector shape is unsupported")
	document = oasa.safe_xml.parse_dom_from_string(complete_cdml)
	root = document.documentElement
	standard = _present_drawing_standard(drawing_standard)
	namespace = root.namespaceURI
	shape_name = _qualified_child_name(root, shape)
	point_name = _qualified_child_name(root, "point")
	if namespace:
		vector = document.createElementNS(namespace, shape_name)
	else:
		vector = document.createElement(shape_name)
	vector.setAttribute("id", provisional_id)
	if shape == "polyline":
		vector.setAttribute("line_color", standard.line_color if standard else "#000000")
		vector.setAttribute("width", "%g" % standard.line_width if standard else "1.5")
		vector.setAttribute("spline", "no")
		for x_coord, y_coord in (start, end):
			if namespace:
				point = document.createElementNS(namespace, point_name)
			else:
				point = document.createElement(point_name)
			point.setAttribute("x", _cm_text(x_coord))
			point.setAttribute("y", _cm_text(y_coord))
			vector.appendChild(point)
	else:
		x1 = min(start[0], end[0])
		y1 = min(start[1], end[1])
		x2 = max(start[0], end[0])
		y2 = max(start[1], end[1])
		vector.setAttribute("x1", _cm_text(x1))
		vector.setAttribute("y1", _cm_text(y1))
		vector.setAttribute("x2", _cm_text(x2))
		vector.setAttribute("y2", _cm_text(y2))
		vector.setAttribute("area_color", standard.area_color if standard else "")
		vector.setAttribute("line_color", standard.line_color if standard else "#000000")
		vector.setAttribute("width", "%g" % standard.line_width if standard else "1.5")
	root.appendChild(vector)
	candidate = document.toxml()
	return candidate


#============================================
def append_rectangular_bracket_candidate(
		complete_cdml: str, provisional_ids: tuple[str, str],
		bounds: tuple[float, float, float, float],
		drawing_standard: object | None = None,
		) -> str:
	"""Append one rectangular bracket pair as two direct core polylines.

	The pair deliberately has no wrapper or attachment schema: both persistent
	records are ordinary top-level CDML presentation objects.  Building them in
	one detached complete-CDML candidate gives the backend one atomic acceptance
	and retains all pre-existing root ordering and opaque content.
	"""
	if type(provisional_ids) is not tuple or len(provisional_ids) != 2:
		raise ValueError("Bracket creation requires two immutable provisional IDs")
	if provisional_ids[0] == provisional_ids[1]:
		raise ValueError("Bracket provisional IDs must be distinct")
	left, top, right, bottom = bounds
	document = oasa.safe_xml.parse_dom_from_string(complete_cdml)
	root = document.documentElement
	standard = _present_drawing_standard(drawing_standard)
	namespace = root.namespaceURI
	polyline_name = _qualified_child_name(root, "polyline")
	point_name = _qualified_child_name(root, "point")
	point_sets = (
		((left + 8.0, top), (left, top), (left, bottom), (left + 8.0, bottom)),
		((right - 8.0, top), (right, top), (right, bottom), (right - 8.0, bottom)),
	)
	for provisional_id, points in zip(provisional_ids, point_sets):
		if namespace:
			polyline = document.createElementNS(namespace, polyline_name)
		else:
			polyline = document.createElement(polyline_name)
		polyline.setAttribute("id", provisional_id)
		polyline.setAttribute("line_color", standard.line_color if standard else "#000000")
		polyline.setAttribute("width", "%g" % standard.line_width if standard else "2.0")
		polyline.setAttribute("spline", "no")
		for x_coord, y_coord in points:
			if namespace:
				point = document.createElementNS(namespace, point_name)
			else:
				point = document.createElement(point_name)
			point.setAttribute("x", _cm_text(x_coord))
			point.setAttribute("y", _cm_text(y_coord))
			polyline.appendChild(point)
		root.appendChild(polyline)
	return document.toxml()


#============================================
def append_wavy_candidate(
		complete_cdml: str, provisional_id: str,
		points: tuple[tuple[float, float], ...],
		drawing_standard: object | None = None,
		) -> str:
	"""Append one validated Wavy polyline to complete authoritative CDML.

	``points`` is already bounded, finite immutable geometry from the shared
	Qt-free Wavy helper.  This pure DOM operation preserves all existing root
	content and adds the one new presentation record at the root tail.
	"""
	document = oasa.safe_xml.parse_dom_from_string(complete_cdml)
	root = document.documentElement
	standard = _present_drawing_standard(drawing_standard)
	polyline_name = _qualified_child_name(root, "polyline")
	point_name = _qualified_child_name(root, "point")
	namespace = root.namespaceURI
	if namespace:
		polyline = document.createElementNS(namespace, polyline_name)
	else:
		polyline = document.createElement(polyline_name)
	polyline.setAttribute("id", provisional_id)
	polyline.setAttribute("line_color", standard.line_color if standard else "#000000")
	polyline.setAttribute("width", "%g" % standard.line_width if standard else "1.5")
	polyline.setAttribute("spline", "no")
	polyline.setAttribute("style", "wavy")
	for x_coord, y_coord in points:
		if namespace:
			point = document.createElementNS(namespace, point_name)
		else:
			point = document.createElement(point_name)
		point.setAttribute("x", _cm_text(x_coord))
		point.setAttribute("y", _cm_text(y_coord))
		polyline.appendChild(point)
	root.appendChild(polyline)
	candidate = document.toxml()
	return candidate


#============================================
def _direct_presentation_root_records(root: xml.dom.minidom.Element) -> tuple:
	"""Return direct, core CDML durable presentation records in source order."""
	records = []
	for child in root.childNodes:
		if child.nodeType != child.ELEMENT_NODE:
			continue
		local_name = child.localName or child.tagName.rsplit(":", 1)[-1]
		if (
				local_name in _PRESENTATION_ROOT_NAMES
				and child.namespaceURI in (None, "", root.namespaceURI)
				and child.namespaceURI in (
					None, "", oasa.cdml_document.CDML_NAMESPACE_URI,
				)
			):
			records.append(child)
	return tuple(records)


#============================================
def reorder_presentation_roots_candidate(
		complete_cdml: str, root_ids: tuple[str, ...], mode: str,
		) -> str:
	"""Return a complete-CDML candidate with selected presentation roots reordered.

	Only direct CDML-core presentation records can be moved.  The DOM is changed
	only after every durable target has been verified, so rejected requests leave
	the supplied source untouched and a semantic no-op returns it byte-for-byte.
	"""
	if mode not in {"bring-to-front", "send-back", "swap-at-slots"}:
		raise ValueError("Presentation stack mode is unsupported")
	if not isinstance(root_ids, tuple) or not root_ids:
		raise ValueError("Presentation stack requires nonempty immutable root IDs")
	if any(not isinstance(identifier, str) or not identifier.strip() for identifier in root_ids):
		raise ValueError("Presentation stack root IDs must be nonblank strings")
	if len(set(root_ids)) != len(root_ids):
		raise ValueError("Presentation stack root IDs must be unique")
	if mode == "swap-at-slots" and len(root_ids) < 2:
		raise ValueError("Presentation stack swap requires at least two roots")
	# Candidate construction receives complete CDML, never an arbitrary XML
	# fragment.  Validate at the owning CDML boundary before compatibility-DOM
	# surgery so malformed/foreign source cannot become a reordered candidate.
	oasa.cdml_document.CDMLDocument.parse(complete_cdml)
	document = oasa.safe_xml.parse_dom_from_string(complete_cdml)
	root = document.documentElement
	if root.namespaceURI not in (None, "", oasa.cdml_document.CDML_NAMESPACE_URI):
		raise ValueError("Presentation stack requires a core CDML root")
	records = _direct_presentation_root_records(root)
	by_id: dict[str, list] = {}
	for record in records:
		identifier = record.getAttribute("id")
		if identifier:
			by_id.setdefault(identifier, []).append(record)
	selected_set = set()
	for identifier in root_ids:
		matches = by_id.get(identifier, [])
		if len(matches) != 1:
			raise ValueError("Presentation stack target is not one direct durable presentation root")
		selected_set.add(matches[0])
	# CDML source order, not caller order, remains authoritative for all modes.
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
		return complete_cdml
	for child in children:
		root.removeChild(child)
	for child in ordered:
		root.appendChild(child)
	candidate = document.toxml()
	return candidate
