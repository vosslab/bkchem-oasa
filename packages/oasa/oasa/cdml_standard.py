"""Frontend-neutral CDML drawing-standard observations and patch grammar."""

# Standard Library
import dataclasses
import math
import re
import types

# local repo modules
import oasa.cdml_xml


_POINT_CM = 2.54 / 72.0
_NUMBER_WITH_UNIT = re.compile(
	r"([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)(cm|mm|in|px)?",
)
_COLOR = re.compile(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?")
DRAWING_STANDARD_FIELDS = (
	"line_width", "font_size", "font_family", "line_color", "area_color",
	"bond_width", "wedge_width", "double_ratio", "show_hydrogens",
)
_PATCH_FIELDS = frozenset(DRAWING_STANDARD_FIELDS)
_APPLICATION_SCOPES = frozenset({"defaults", "selected", "all"})
_PRESENTATION_ROOTS = frozenset({
	"arrow", "plus", "text", "rect", "square", "oval", "circle",
	"polygon", "polyline",
})
PAPER_SIZES_MM = {
	"A0": (841.0, 1189.0), "A1": (594.0, 841.0), "A2": (420.0, 594.0),
	"A3": (297.0, 420.0), "A4": (210.0, 297.0), "A5": (148.0, 210.0),
	"A6": (105.0, 148.0), "A7": (74.0, 105.0), "A8": (52.0, 74.0),
	"A9": (37.0, 52.0), "A10": (26.0, 37.0),
	"B0": (1000.0, 1414.0), "B1": (707.0, 1000.0), "B2": (500.0, 707.0),
	"B3": (353.0, 500.0), "B4": (250.0, 353.0), "B5": (176.0, 250.0),
	"B6": (125.0, 176.0), "B7": (88.0, 125.0), "B8": (62.0, 88.0),
	"B9": (44.0, 62.0), "B10": (31.0, 44.0),
	"C0": (917.0, 1297.0), "C1": (648.0, 917.0), "C2": (458.0, 648.0),
	"C3": (324.0, 458.0), "C4": (229.0, 324.0), "C5": (162.0, 229.0),
	"C6": (114.0, 162.0), "C7": (81.0, 114.0), "C8": (57.0, 81.0),
	"C9": (40.0, 57.0), "C10": (28.0, 40.0),
	"Ledger": (279.4, 431.8), "Legal": (215.9, 355.6),
	"Letter": (215.9, 279.4), "Tabloid": (279.4, 431.8),
	"custom": None,
}


#============================================
def paper_catalog() -> dict[str, list[float] | None]:
	"""Return a fresh plain-data copy of the authored CDML paper catalog."""
	catalog = {
		name: None if dimensions is None else list(dimensions)
		for name, dimensions in PAPER_SIZES_MM.items()
	}
	return catalog


#============================================
def paper_defaults(root: object) -> tuple[str, str]:
	"""Return valid direct-standard paper defaults or the authored fallback."""
	standard = _direct_element(root, "standard")
	if standard is not None:
		paper_type = standard.getAttribute("paper_type")
		orientation = standard.getAttribute("paper_orientation")
		if (
			paper_type in PAPER_SIZES_MM and paper_type != "custom"
			and orientation in ("portrait", "landscape")
		):
			return paper_type, orientation
	return "A4", "portrait"


#============================================
class CDMLDrawingStandardError(ValueError):
	"""Raised when drawing-standard observation or patch intent is invalid."""


#============================================
@dataclasses.dataclass(frozen=True)
class CDMLDrawingStandardQuery:
	"""One revision-bound drawing-standard observation request."""

	expected_revision: int


#============================================
@dataclasses.dataclass(frozen=True)
class CDMLDrawingStandardPatch:
	"""One revision-bound explicit-field drawing-standard patch."""

	expected_revision: int
	changes: tuple[tuple[str, object], ...]


#============================================
@dataclasses.dataclass(frozen=True)
class CDMLDrawingStandardApplication:
	"""One atomic standard patch plus optional existing-object overrides."""

	expected_revision: int
	changes: tuple[tuple[str, object], ...]
	apply_scope: str = "defaults"
	root_ids: tuple[str, ...] = ()
	override_fields: tuple[str, ...] = ()


CDMLDrawingStandardRequest = CDMLDrawingStandardPatch | CDMLDrawingStandardApplication


#============================================
@dataclasses.dataclass(frozen=True)
class CDMLDrawingStandardObservation:
	"""Immutable effective drawing defaults from one authoritative document."""

	revision: int
	present: bool
	line_width: float
	font_size: int
	font_family: str
	line_color: str
	area_color: str
	bond_width: float
	wedge_width: float
	double_ratio: float
	show_hydrogens: bool
	issues: tuple[str, ...]


#============================================
def _local_name(element: object) -> str:
	"""Return one DOM element local name without exposing namespace prefixes."""
	name = element.localName or element.tagName.split(":")[-1]
	return name


#============================================
def _is_core(element: object) -> bool:
	"""Return whether one DOM element belongs to the editable CDML namespace."""
	namespace = getattr(element, "namespaceURI", None)
	return namespace in (None, "", oasa.cdml_xml.CDML_NAMESPACE_URI)


#============================================
def _direct_element(parent: object, name: str) -> object | None:
	"""Return the first direct core child with one local name."""
	for child in parent.childNodes:
		if child.nodeType == child.ELEMENT_NODE and _is_core(child) and _local_name(child) == name:
			return child
	return None


#============================================
def _length_points(value: str) -> float | None:
	"""Convert one accepted historical standard length to scene-space points."""
	match = _NUMBER_WITH_UNIT.fullmatch(value.strip())
	if match is None:
		return None
	number = float(match.group(1))
	unit = match.group(2)
	if unit == "cm":
		number /= _POINT_CM
	elif unit == "mm":
		number /= _POINT_CM * 10.0
	elif unit == "in":
		number *= 72.0
	if not math.isfinite(number) or number <= 0.0:
		return None
	return number


#============================================
def _normalized_color(value: str, allow_empty: bool = False) -> str | None:
	"""Return one six-digit lowercase color or an allowed transparent value."""
	if allow_empty and value == "":
		return ""
	if _COLOR.fullmatch(value) is None:
		return None
	hex_value = value[1:].lower()
	if len(hex_value) == 3:
		hex_value = "".join(character * 2 for character in hex_value)
	return "#" + hex_value


#============================================
def _valid_float(value: str, lower: float, upper: float) -> float | None:
	"""Return one finite bounded float or None."""
	try:
		number = float(value)
	except ValueError:
		return None
	if not math.isfinite(number) or not lower < number <= upper:
		return None
	return number


#============================================
def observe(root: object, revision: int) -> CDMLDrawingStandardObservation:
	"""Observe the first direct core standard while preserving malformed source."""
	standard = _direct_element(root, "standard")
	issues = []
	values = {
		"line_width": 1.0,
		"font_size": 12,
		"font_family": "helvetica",
		"line_color": "#000000",
		"area_color": "",
		"bond_width": 6.0,
		"wedge_width": 5.0,
		"double_ratio": 0.75,
		"show_hydrogens": False,
	}
	if standard is None:
		return CDMLDrawingStandardObservation(revision, False, **values, issues=())
	root_fields = (
		("line_width", "line_width", lambda value: _length_points(value)),
		("font_size", "font_size", _font_size),
		("font_family", "font_family", lambda value: value.strip() or None),
		("line_color", "line_color", lambda value: _normalized_color(value)),
		("area_color", "area_color", lambda value: _normalized_color(value, allow_empty=True)),
	)
	for attribute, field, parser in root_fields:
		if not standard.hasAttribute(attribute):
			continue
		parsed = parser(standard.getAttribute(attribute))
		if parsed is None:
			issues.append("standard@%s is malformed" % attribute)
		else:
			values[field] = parsed
	bond = _direct_element(standard, "bond")
	if bond is not None:
		for attribute, field, parser in (
			("width", "bond_width", _length_points),
			("wedge-width", "wedge_width", _length_points),
			("double-ratio", "double_ratio", lambda value: _valid_float(value, 0.0, 1.0)),
		):
			if not bond.hasAttribute(attribute):
				continue
			parsed = parser(bond.getAttribute(attribute))
			if parsed is None:
				issues.append("standard/bond@%s is malformed" % attribute)
			else:
				values[field] = parsed
	atom = _direct_element(standard, "atom")
	if atom is not None and atom.hasAttribute("show_hydrogens"):
		text = atom.getAttribute("show_hydrogens").strip().lower()
		if text in ("1", "true", "yes", "on"):
			values["show_hydrogens"] = True
		elif text in ("0", "false", "no", "off"):
			values["show_hydrogens"] = False
		else:
			issues.append("standard/atom@show_hydrogens is malformed")
	return CDMLDrawingStandardObservation(revision, True, **values, issues=tuple(issues))


#============================================
def query_session(session: object, query: object) -> CDMLDrawingStandardObservation:
	"""Run one exact standard observation against a document-session authority."""
	if type(query) is not CDMLDrawingStandardQuery:
		raise CDMLDrawingStandardError("drawing standard requires an exact query")
	if type(query.expected_revision) is not int:
		raise CDMLDrawingStandardError("drawing standard expected_revision must be an int")
	session._check_expected_revision(query.expected_revision)
	root = session._document._dom_document.documentElement
	return observe(root, session._revision)


#============================================
def resolve_atom_values(
		standard: CDMLDrawingStandardObservation,
		show_hydrogens: bool | None, font_family: str | None,
		font_size: int | None, line_color: str | None,
		) -> tuple[bool | None, str | None, int | None, str | None]:
	"""Apply document defaults only to absent atom depiction values."""
	if not standard.present:
		return show_hydrogens, font_family, font_size, line_color
	values = (
		standard.show_hydrogens if show_hydrogens is None else show_hydrogens,
		standard.font_family if font_family is None else font_family,
		standard.font_size if font_size is None else font_size,
		standard.line_color if line_color is None else line_color,
	)
	return values


#============================================
def resolve_bond_values(
		standard: CDMLDrawingStandardObservation,
		line_width: float | None, bond_width: float | None,
		wedge_width: float | None, double_ratio: float | None,
		line_color: str | None,
		) -> tuple[float | None, float | None, float | None, float | None, str | None]:
	"""Apply document defaults only to absent bond depiction values."""
	if not standard.present:
		return line_width, bond_width, wedge_width, double_ratio, line_color
	values = (
		standard.line_width if line_width is None else line_width,
		standard.bond_width if bond_width is None else bond_width,
		standard.wedge_width if wedge_width is None else wedge_width,
		standard.double_ratio if double_ratio is None else double_ratio,
		standard.line_color if line_color is None else line_color,
	)
	return values


#============================================
def install_bond_render_values(
		bond: object, double_ratio: float | None, line_color: str | None,
		) -> tuple[object, object]:
	"""Temporarily project effective standard values onto one decoded bond."""
	previous = (getattr(bond, "double_length_ratio", None), bond.properties_.get("line_color"))
	if double_ratio is not None:
		bond.double_length_ratio = double_ratio
	bond.properties_["line_color"] = line_color or "__backend_foreground__"
	return previous


#============================================
def bond_second_line_shortening(double_ratio: float | None) -> float:
	"""Translate a CDML double-line ratio into symmetric endpoint shortening."""
	return max(0.0, (1.0 - (double_ratio or 1.0)) / 2.0)


#============================================
def restore_bond_render_values(bond: object, previous: tuple[object, object]) -> None:
	"""Restore one decoded bond after temporary authoritative rendering."""
	previous_ratio, previous_color = previous
	if previous_ratio is not None:
		bond.double_length_ratio = previous_ratio
	if previous_color is None:
		bond.properties_.pop("line_color", None)
	else:
		bond.properties_["line_color"] = previous_color


#============================================
def validate_patch(request: object) -> tuple[tuple[str, object], ...]:
	"""Validate and normalize one immutable explicit-field patch."""
	if type(request) is not CDMLDrawingStandardPatch:
		raise CDMLDrawingStandardError("drawing standard requires a drawing-standard patch")
	if type(request.expected_revision) is not int:
		raise CDMLDrawingStandardError("drawing standard expected_revision must be an int")
	if type(request.changes) is not tuple:
		raise CDMLDrawingStandardError("drawing standard changes must be a tuple")
	normalized = []
	seen = set()
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLDrawingStandardError("drawing standard changes require exact pairs")
		name, value = change
		if type(name) is not str or name not in _PATCH_FIELDS:
			raise CDMLDrawingStandardError("drawing standard field is unsupported")
		if name in seen:
			raise CDMLDrawingStandardError("drawing standard field is repeated: %s" % name)
		seen.add(name)
		if name in ("line_width", "bond_width", "wedge_width"):
			if isinstance(value, bool) or not isinstance(value, (int, float)):
				raise CDMLDrawingStandardError("drawing standard width must be numeric")
			value = float(value)
			if not math.isfinite(value) or not 0.0 < value <= 1000.0:
				raise CDMLDrawingStandardError("drawing standard width is out of range")
		elif name == "font_size":
			if type(value) is not int or not 4 <= value <= 144:
				raise CDMLDrawingStandardError("drawing standard font size must be from 4 to 144")
		elif name == "font_family":
			if type(value) is not str or not value.strip() or len(value) > 128:
				raise CDMLDrawingStandardError("drawing standard font family must be nonblank")
			value = value.strip()
		elif name in ("line_color", "area_color"):
			if type(value) is not str:
				raise CDMLDrawingStandardError("drawing standard color must be text")
			value = _normalized_color(value, allow_empty=name == "area_color")
			if value is None:
				raise CDMLDrawingStandardError("drawing standard color must be hexadecimal")
		elif name == "double_ratio":
			if isinstance(value, bool) or not isinstance(value, (int, float)):
				raise CDMLDrawingStandardError("drawing standard double ratio must be numeric")
			value = float(value)
			if not math.isfinite(value) or not 0.0 < value <= 1.0:
				raise CDMLDrawingStandardError("drawing standard double ratio must be above 0 and at most 1")
		elif type(value) is not bool:
			raise CDMLDrawingStandardError("drawing standard show hydrogens must be a bool")
		normalized.append((name, value))
	return tuple(normalized)


#============================================
def apply_patch(root: object, changes: tuple[tuple[str, object], ...]) -> None:
	"""Apply validated standard fields to one detached complete-CDML root."""
	standard = _direct_element(root, "standard")
	if standard is None:
		if root.namespaceURI == oasa.cdml_xml.CDML_NAMESPACE_URI:
			standard = root.ownerDocument.createElementNS(root.namespaceURI, "standard")
		else:
			standard = root.ownerDocument.createElement("standard")
		before = next((
			child for child in root.childNodes
			if child.nodeType == child.ELEMENT_NODE and _is_core(child)
			and _local_name(child) in {"paper", "viewport", "molecule", "arrow", "plus", "text"}
		), None)
		if before is None:
			root.appendChild(standard)
		else:
			root.insertBefore(standard, before)
	change_map = dict(changes)
	for name in ("font_size", "font_family", "line_color", "area_color"):
		if name in change_map:
			standard.setAttribute(name, str(change_map[name]))
	if "line_width" in change_map:
		standard.setAttribute("line_width", _points_text(change_map["line_width"]))
	if any(name in change_map for name in ("bond_width", "wedge_width", "double_ratio")):
		bond = _ensure_child(standard, "bond")
		for name, attribute in (
			("bond_width", "width"), ("wedge_width", "wedge-width"),
		):
			if name in change_map:
				bond.setAttribute(attribute, _points_text(change_map[name]))
		if "double_ratio" in change_map:
			bond.setAttribute("double-ratio", "%g" % change_map["double_ratio"])
	if "show_hydrogens" in change_map:
		atom = _ensure_child(standard, "atom")
		atom.setAttribute("show_hydrogens", "1" if change_map["show_hydrogens"] else "0")


#============================================
def _validate_application(
		request: object,
		) -> tuple[tuple[tuple[str, object], ...], str, tuple[str, ...], tuple[str, ...]]:
	"""Validate one immutable standard-and-overrides request before mutation."""
	if type(request) is not CDMLDrawingStandardApplication:
		raise CDMLDrawingStandardError("drawing standard application requires an exact request")
	changes = validate_patch(CDMLDrawingStandardPatch(
		request.expected_revision, request.changes,
	))
	if type(request.apply_scope) is not str or request.apply_scope not in _APPLICATION_SCOPES:
		raise CDMLDrawingStandardError("drawing standard apply_scope is unsupported")
	if type(request.root_ids) is not tuple:
		raise CDMLDrawingStandardError("drawing standard root_ids must be a tuple")
	if any(type(identifier) is not str or not identifier for identifier in request.root_ids):
		raise CDMLDrawingStandardError("drawing standard root IDs must be nonblank strings")
	if len(set(request.root_ids)) != len(request.root_ids):
		raise CDMLDrawingStandardError("drawing standard root IDs must be unique")
	if type(request.override_fields) is not tuple:
		raise CDMLDrawingStandardError("drawing standard override_fields must be a tuple")
	if any(type(name) is not str or name not in _PATCH_FIELDS for name in request.override_fields):
		raise CDMLDrawingStandardError("drawing standard override field is unsupported")
	if len(set(request.override_fields)) != len(request.override_fields):
		raise CDMLDrawingStandardError("drawing standard override fields must be unique")
	if request.apply_scope == "defaults":
		if request.root_ids or request.override_fields:
			raise CDMLDrawingStandardError(
				"defaults-only drawing standard application cannot target object overrides",
			)
	elif request.apply_scope == "selected":
		if not request.root_ids:
			raise CDMLDrawingStandardError("selected drawing standard application needs root IDs")
	elif request.root_ids:
		raise CDMLDrawingStandardError("all-object drawing standard application cannot name roots")
	return changes, request.apply_scope, request.root_ids, request.override_fields


#============================================
def _direct_core_children(parent: object, names: frozenset[str]) -> tuple[object, ...]:
	"""Return direct editable children whose local names belong to ``names``."""
	return tuple(
		child for child in parent.childNodes
		if child.nodeType == child.ELEMENT_NODE and _is_core(child)
		and _local_name(child) in names
	)


#============================================
def _identifier_counts(root: object) -> dict[str, int]:
	"""Count literal IDs across the complete candidate document."""
	counts: dict[str, int] = {}
	def visit(element: object) -> None:
		identifier = element.getAttribute("id") if element.hasAttribute("id") else ""
		if identifier:
			counts[identifier] = counts.get(identifier, 0) + 1
		for child in element.childNodes:
			if child.nodeType == child.ELEMENT_NODE:
				visit(child)
	visit(root)
	return counts


#============================================
def _application_roots(
		root: object, apply_scope: str, root_ids: tuple[str, ...],
		) -> tuple[object, ...]:
	"""Resolve exact selected roots or all supported direct editable roots."""
	eligible = _direct_core_children(root, _PRESENTATION_ROOTS | {"molecule"})
	if apply_scope == "all":
		return eligible
	if apply_scope == "defaults":
		return ()
	counts = _identifier_counts(root)
	by_identifier = {
		element.getAttribute("id"): element
		for element in eligible
		if element.hasAttribute("id") and counts.get(element.getAttribute("id")) == 1
	}
	if any(identifier not in by_identifier for identifier in root_ids):
		raise CDMLDrawingStandardError(
			"drawing standard selected root is missing, ambiguous, or unsupported",
		)
	return tuple(by_identifier[identifier] for identifier in root_ids)


#============================================
def _set_color_or_remove(element: object, attribute: str, value: str) -> None:
	"""Set one explicit color, removing transparent optional attributes."""
	if value:
		element.setAttribute(attribute, value)
	elif element.hasAttribute(attribute):
		element.removeAttribute(attribute)


#============================================
def _single_or_new_font(element: object) -> object:
	"""Return one direct core font or create it; reject ambiguous targets."""
	fonts = _direct_core_children(element, frozenset({"font"}))
	if len(fonts) > 1:
		raise CDMLDrawingStandardError(
			"drawing standard target has multiple direct core font records",
		)
	return fonts[0] if fonts else _ensure_child(element, "font")


#============================================
def _apply_molecule_overrides(
		molecule: object, values: CDMLDrawingStandardObservation,
		fields: frozenset[str],
		) -> None:
	"""Materialize applicable atom and bond values below one molecule root."""
	atom_fields = fields & {"font_family", "font_size", "line_color", "show_hydrogens"}
	for atom in _direct_core_children(molecule, frozenset({"atom"})):
		if "show_hydrogens" in atom_fields:
			atom.setAttribute("hydrogens", "on" if values.show_hydrogens else "off")
		if atom_fields & {"font_family", "font_size", "line_color"}:
			font = _single_or_new_font(atom)
			if "font_family" in atom_fields:
				font.setAttribute("family", values.font_family)
			if "font_size" in atom_fields:
				font.setAttribute("size", str(values.font_size))
			if "line_color" in atom_fields:
				font.setAttribute("color", values.line_color)
	bond_attributes = (
		("line_width", "line_width"), ("bond_width", "bond_width"),
		("wedge_width", "wedge_width"), ("double_ratio", "double_ratio"),
	)
	for bond in _direct_core_children(molecule, frozenset({"bond"})):
		for field, attribute in bond_attributes:
			if field in fields:
				bond.setAttribute(attribute, "%g" % getattr(values, field))
		if "line_color" in fields:
			bond.setAttribute("color", values.line_color)


#============================================
def _apply_presentation_overrides(
		element: object, values: CDMLDrawingStandardObservation,
		fields: frozenset[str],
		) -> None:
	"""Materialize applicable standard values on one presentation root."""
	name = _local_name(element)
	if name == "arrow":
		if "line_width" in fields:
			element.setAttribute("width", "%g" % values.line_width)
		if "line_color" in fields:
			element.setAttribute("color", values.line_color)
	elif name in {"rect", "square", "oval", "circle", "polygon", "polyline"}:
		if "line_width" in fields:
			element.setAttribute("width", "%g" % values.line_width)
		if "line_color" in fields:
			element.setAttribute("line_color", values.line_color)
		if "area_color" in fields and name != "polyline":
			element.setAttribute("area_color", values.area_color)
	elif name == "text":
		if "area_color" in fields:
			_set_color_or_remove(element, "background-color", values.area_color)
		if fields & {"font_family", "font_size", "line_color"}:
			font = _single_or_new_font(element)
			if "font_family" in fields:
				font.setAttribute("family", values.font_family)
			if "font_size" in fields:
				font.setAttribute("size", str(values.font_size))
			if "line_color" in fields:
				font.setAttribute("color", values.line_color)
	elif name == "plus":
		if "font_size" in fields:
			element.setAttribute("font_size", str(values.font_size))
		if "line_color" in fields:
			element.setAttribute("color", values.line_color)
		if "area_color" in fields:
			_set_color_or_remove(element, "background-color", values.area_color)


#============================================
def apply_session(session: object, request: object, commit_type: object) -> object:
	"""Apply defaults and optional object overrides in one backend transaction."""
	changes, apply_scope, root_ids, override_fields = _validate_application(request)
	session._check_expected_revision(request.expected_revision)
	if not changes and not override_fields:
		return commit_type(session.snapshot(), types.MappingProxyType({}))
	current_cdml = session._document.serialize()
	candidate = session._document.__class__.parse(current_cdml, validation="compat")
	root = candidate._dom_document.documentElement
	apply_patch(root, changes)
	values = observe(root, request.expected_revision)
	if changes:
		values = dataclasses.replace(values, **dict(changes))
	fields = frozenset(override_fields)
	for element in _application_roots(root, apply_scope, root_ids):
		if _local_name(element) == "molecule":
			_apply_molecule_overrides(element, values, fields)
		else:
			_apply_presentation_overrides(element, values, fields)
	candidate.validate(validation="strict")
	candidate_cdml = candidate.serialize()
	if candidate_cdml == current_cdml:
		return commit_type(session.snapshot(), types.MappingProxyType({}))
	return session.commit(
		expected_revision=request.expected_revision, complete_cdml=candidate_cdml,
	)


#============================================
def patch_session(session: object, request: object, commit_type: object) -> object:
	"""Apply standard intent through one authority-owned detached transaction."""
	if type(request) is CDMLDrawingStandardApplication:
		return apply_session(session, request, commit_type)
	changes = validate_patch(request)
	session._check_expected_revision(request.expected_revision)
	if not changes:
		return commit_type(session.snapshot(), types.MappingProxyType({}))
	current_cdml = session._document.serialize()
	candidate = session._document.__class__.parse(current_cdml, validation="compat")
	apply_patch(candidate._dom_document.documentElement, changes)
	candidate.validate(validation="strict")
	candidate_cdml = candidate.serialize()
	if candidate_cdml == current_cdml:
		return commit_type(session.snapshot(), types.MappingProxyType({}))
	return session.commit(
		expected_revision=request.expected_revision, complete_cdml=candidate_cdml,
	)


#============================================
def _ensure_child(parent: object, name: str) -> object:
	"""Return or append one direct core standard child."""
	child = _direct_element(parent, name)
	if child is not None:
		return child
	if parent.namespaceURI == oasa.cdml_xml.CDML_NAMESPACE_URI:
		child = parent.ownerDocument.createElementNS(parent.namespaceURI, name)
	else:
		child = parent.ownerDocument.createElement(name)
	parent.appendChild(child)
	return child


#============================================
def _points_text(value: float) -> str:
	"""Serialize scene points as the portable authored centimetre standard."""
	text = "%.6gcm" % (value * _POINT_CM)
	return text


#============================================
def _font_size(value: str) -> int | None:
	"""Return one supported font size or None."""
	if not value.isdigit():
		return None
	size = int(value)
	return size if 4 <= size <= 144 else None
