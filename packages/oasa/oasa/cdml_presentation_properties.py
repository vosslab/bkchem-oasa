"""Backend-owned property operations for direct-root CDML presentation records."""

# Standard Library
import dataclasses
import math
import numbers
import re

# local repo modules
import oasa.cdml_document
import oasa.safe_xml


class CDMLArrowPropertiesPatchError(oasa.cdml_document.CDMLValidationError):
	"""Raised when one revision-bound Arrow property patch is invalid."""


@dataclasses.dataclass(frozen=True)
class CDMLArrowPropertiesPatch:
	"""One revision-bound explicit-field patch for one direct-root Arrow."""

	expected_revision: int
	arrow_id: str
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLArrowPropertiesPatchResult:
	"""Immutable result of one backend-authoritative Arrow property patch."""

	snapshot: oasa.cdml_document.CDMLSnapshot
	changed: bool
	commit: oasa.cdml_document.CDMLCommit | None


_FIELDS = frozenset({"start_head", "end_head", "spline", "line_width", "color"})
_TRUE_VALUES = frozenset({"yes", "true", "1"})
_FALSE_VALUES = frozenset({"no", "false", "0"})


#============================================
def _validate_patch(
		request: object,
		) -> tuple[str, tuple[tuple[str, object], ...]]:
	"""Validate immutable Arrow intent before authoritative target lookup."""
	if type(request) is not CDMLArrowPropertiesPatch:
		raise CDMLArrowPropertiesPatchError(
			"Arrow properties requires an exact Arrow properties patch",
		)
	if type(request.expected_revision) is not int:
		raise CDMLArrowPropertiesPatchError(
			"Arrow properties expected_revision must be an int",
		)
	if type(request.arrow_id) is not str or not request.arrow_id.strip():
		raise CDMLArrowPropertiesPatchError(
			"Arrow properties arrow_id must contain a non-whitespace character",
		)
	if type(request.changes) is not tuple:
		raise CDMLArrowPropertiesPatchError(
			"Arrow properties changes must be an immutable tuple",
		)
	validated = []
	seen = set()
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLArrowPropertiesPatchError(
				"Arrow properties changes must be field/value pairs",
			)
		field_name, value = change
		if type(field_name) is not str or field_name not in _FIELDS:
			raise CDMLArrowPropertiesPatchError("Arrow properties field is unsupported")
		if field_name in seen:
			raise CDMLArrowPropertiesPatchError("Arrow properties fields must be unique")
		seen.add(field_name)
		if field_name in {"start_head", "end_head", "spline"}:
			if type(value) is not bool:
				raise CDMLArrowPropertiesPatchError(
					"Arrow head and spline properties must be bool values",
				)
		elif field_name == "line_width":
			if (
				type(value) is bool or not isinstance(value, numbers.Real)
				or not math.isfinite(value) or not 0.1 <= value <= 20
			):
				raise CDMLArrowPropertiesPatchError(
					"Arrow line_width must be a finite number from 0.1 to 20",
				)
			value = float(value)
		else:
			if type(value) is not str or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
				raise CDMLArrowPropertiesPatchError(
					"Arrow color must be a six-digit hex color",
				)
			value = value.lower()
		validated.append((field_name, value))
	return request.arrow_id, tuple(validated)


#============================================
def _attribute_bool(
		attributes: dict[str, str], name: str, default: bool, *, heads: bool = False,
		) -> bool:
	"""Return one validated historical yes/no presentation value."""
	if name not in attributes:
		return default
	value = attributes[name].strip().lower()
	if value in _TRUE_VALUES or heads and value == "both":
		return True
	if value in _FALSE_VALUES:
		return False
	raise CDMLArrowPropertiesPatchError(
		"Arrow properties target has an invalid %s value" % name,
	)


#============================================
def _arrow_values(record: object) -> dict[str, object]:
	"""Return validated visible Arrow semantics from one plain observation."""
	attributes = dict(record.attributes)
	width = 1.0
	if "width" in attributes:
		try:
			width = float(attributes["width"])
		except ValueError as error:
			raise CDMLArrowPropertiesPatchError(
				"Arrow properties target width must be a finite number",
			) from error
		if not math.isfinite(width) or not 0.1 <= width <= 20:
			raise CDMLArrowPropertiesPatchError(
				"Arrow properties target width must be a finite number from 0.1 to 20",
			)
	color = attributes.get("color", "#000000")
	if re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None:
		raise CDMLArrowPropertiesPatchError(
			"Arrow properties target color must be a six-digit hex color",
		)
	return {
		"start_head": _attribute_bool(attributes, "start", False, heads=True),
		"end_head": _attribute_bool(attributes, "end", True, heads=True),
		"spline": _attribute_bool(attributes, "spline", False),
		"line_width": width,
		"color": color.lower(),
	}


#============================================
def _arrow_record(session: object, expected_revision: int, arrow_id: str) -> object:
	"""Return one current editable direct-root Arrow observation by durable ID."""
	description = session.presentation_description(
		oasa.cdml_document.CDMLPresentationDescriptionQuery(expected_revision),
	)
	matches = tuple(
		record for record in description.records
		if record.identifier == arrow_id and record.kind == "arrow"
	)
	if len(matches) != 1 or matches[0].disposition != "editable":
		raise CDMLArrowPropertiesPatchError(
			"Arrow properties target is not one unique direct editable Arrow: %s" % arrow_id,
		)
	return matches[0]


#============================================
def _candidate_arrow(document: object, arrow_id: str) -> object:
	"""Return the exact direct core Arrow element in one detached candidate."""
	root = document.documentElement
	matches = tuple(
		child for child in root.childNodes
		if child.nodeType == child.ELEMENT_NODE
		and (child.namespaceURI or "") in ("", oasa.cdml_document.CDML_NAMESPACE_URI)
		and (child.localName or child.tagName) == "arrow"
		and child.getAttribute("id") == arrow_id
	)
	if len(matches) != 1:
		raise CDMLArrowPropertiesPatchError(
			"Arrow properties target disappeared from detached candidate",
		)
	return matches[0]


#============================================
def patch_arrow_properties(
		session: object, request: CDMLArrowPropertiesPatch,
		) -> CDMLArrowPropertiesPatchResult:
	"""Apply one explicit Arrow root-property intent through OASA authority."""
	if type(session) is not oasa.cdml_document.CDMLDocumentSession:
		raise CDMLArrowPropertiesPatchError(
			"Arrow properties requires an exact CDML document session",
		)
	arrow_id, changes = _validate_patch(request)
	snapshot = session.snapshot()
	if snapshot.revision != request.expected_revision:
		raise oasa.cdml_document.CDMLRevisionConflictError(
			"Arrow properties expected revision does not match current revision",
		)
	record = _arrow_record(session, request.expected_revision, arrow_id)
	current = _arrow_values(record)
	if not changes or all(current[field_name] == value for field_name, value in changes):
		return CDMLArrowPropertiesPatchResult(snapshot, False, None)
	candidate_dom = oasa.safe_xml.parse_dom_from_string(snapshot.cdml)
	arrow = _candidate_arrow(candidate_dom, arrow_id)
	attribute_names = {
		"start_head": "start", "end_head": "end", "spline": "spline",
		"line_width": "width", "color": "color",
	}
	for field_name, value in changes:
		attribute_name = attribute_names[field_name]
		if field_name in {"start_head", "end_head", "spline"}:
			text = "yes" if value else "no"
		elif field_name == "line_width":
			text = "%g" % value
		else:
			text = value
		arrow.setAttribute(attribute_name, text)
	candidate = oasa.cdml_document.CDMLDocument.parse(
		candidate_dom.toxml(), validation="compat",
	)
	candidate.validate(validation="strict")
	candidate_cdml = candidate.serialize()
	if candidate_cdml == snapshot.cdml:
		return CDMLArrowPropertiesPatchResult(snapshot, False, None)
	commit = session.commit(
		expected_revision=request.expected_revision, complete_cdml=candidate_cdml,
	)
	return CDMLArrowPropertiesPatchResult(commit.snapshot, True, commit)
