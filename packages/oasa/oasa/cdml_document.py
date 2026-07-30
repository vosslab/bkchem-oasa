"""Authoritative complete-CDML document storage and revision transactions.

This module deliberately keeps a complete XML DOM as the persistent source of
truth.  The molecule codec may provide a chemistry view elsewhere, but it must
never be used to reconstruct this document because CDML also contains arrows,
text, reactions, paper data, and extension XML.
"""

# Standard Library
import collections.abc
import dataclasses
import hashlib
import math
import re
import types

# local repo modules
import oasa.bond_semantics
import oasa.cdml_writer
import oasa.cdml_xml
import oasa.codecs.rdkit_formats
import oasa.periodic_table


_PROVISIONAL_ID_PREFIX = "__bkchem_new__"
_PROVISIONAL_ID_PATTERN = re.compile(
	r"^__bkchem_new__[A-Za-z][A-Za-z0-9_-]{0,63}$",
)
CDML_NAMESPACE_URI = oasa.cdml_xml.CDML_NAMESPACE_URI
_ID_DECLARATION_ELEMENT_NAMES = frozenset({
	"arrow", "atom", "bond", "circle", "fragment",
	"group", "molecule", "oval", "paper", "plus", "polygon", "polyline", "reaction",
	"query", "rect", "square", "text", "viewport",
})
_TOP_LEVEL_INSERTION_NAMES = frozenset({
	"molecule", "arrow", "plus", "text", "rect", "square", "oval", "circle",
	"polygon", "polyline", "reaction",
})
_TOP_LEVEL_DELETE_NAMES = frozenset({
	"molecule", "arrow", "plus", "text", "rect", "square", "oval", "circle",
	"polygon", "polyline",
})
_MOLECULE_VERTEX_NAMES = frozenset({"atom", "group", "text", "query"})
_MOLECULE_CHILD_NAMES = _MOLECULE_VERTEX_NAMES | frozenset({"bond", "template", "fragment"})
_REACTION_ROLE_NAMES = frozenset({"arrow", "condition", "plus", "product", "reactant"})
_POINT_CM_PER_POSTSCRIPT_POINT = 2.54 / 72.0
_COORDINATE_PATTERN = re.compile(r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?(?:cm)?$")
_EMPTY_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" '
	'version="26.07"></cdml>'
)
_CDML_PAPER_SIZES_MM = {
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
_CDML_PAPER_PROPERTY_FIELDS = frozenset({
	"type", "orientation", "crop_svg", "crop_margin", "use_real_minus",
	"replace_minus", "dimensions",
})


#============================================
def paper_catalog() -> dict[str, list[float] | None]:
	"""Return a fresh plain-data catalog of the authored CDML paper names.

	Standard pairs are portrait ``[width_mm, height_mm]`` values.  ``custom``
	requires dimensions supplied by a document operation and therefore has no
	standard pair.  A fresh result prevents a frontend from changing OASA's
	catalog through a retained Python reference.
	"""
	return {
		name: None if dimensions is None else list(dimensions)
		for name, dimensions in _CDML_PAPER_SIZES_MM.items()
	}


class CDMLDocumentError(ValueError):
	"""Base error for a complete CDML document operation."""


class CDMLParseError(CDMLDocumentError):
	"""Raised when text is not a parseable CDML document."""


class CDMLValidationError(CDMLDocumentError):
	"""Raised when a complete CDML document violates backend invariants."""


class CDMLAtomNumberCompatibilityError(CDMLValidationError):
	"""Raised when a direct legacy atom-number mark prevents a number edit."""


class CDMLMoleculeNameEditError(CDMLValidationError):
	"""Raised when a direct-root molecule display-name edit is invalid."""


class CDMLMoleculeSmilesUnavailableError(CDMLDocumentError):
	"""Raised when one direct-root molecule cannot produce a SMILES value."""


class CDMLPaperPropertiesError(CDMLValidationError):
	"""Raised when one revision-bound paper-properties patch is invalid."""


class CDMLBondPropertiesPatchError(CDMLValidationError):
	"""Raised when one revision-bound bond-properties patch is invalid."""


class CDMLAtomPropertiesPatchError(CDMLValidationError):
	"""Raised when one revision-bound atom-properties patch is invalid."""


class CDMLRevisionConflictError(CDMLDocumentError):
	"""Raised when a transaction was built from an obsolete revision."""


class CDMLRevisionUnavailableError(CDMLDocumentError):
	"""Raised when a bounded session no longer retains a requested revision."""


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeInsertionRequest:
	"""One detached molecule-only proposal for an optimistic backend insertion."""

	expected_revision: int
	proposal_cdml: str
	label: str | None = None


@dataclasses.dataclass(frozen=True)
class CDMLTopLevelInsertionRequest:
	"""One detached, translated, top-level CDML composition request."""

	expected_revision: int
	fragment_cdml: str
	translation: tuple[float, float]
	label: str | None = None


@dataclasses.dataclass(frozen=True)
class CDMLGeometryRepairRequest:
	"""One revision-bound, direct-root geometry repair request."""

	expected_revision: int
	molecule_ids: tuple[str, ...]
	kind: str
	target_spacing_pt: float


@dataclasses.dataclass(frozen=True)
class CDMLAtomAlignRequest:
	"""One revision-bound direct-core atom alignment request."""

	expected_revision: int
	axis: str
	targets: tuple[tuple[str, str], ...]


@dataclasses.dataclass(frozen=True)
class CDMLAtomTranslateRequest:
	"""One revision-bound translation of selected direct-core atoms in points."""

	expected_revision: int
	targets: tuple[tuple[str, str], ...]
	delta: tuple[float, float]


@dataclasses.dataclass(frozen=True)
class CDMLAtomRotateRequest:
	"""One revision-bound 2D rotation of selected direct-core atoms."""

	expected_revision: int
	targets: tuple[tuple[str, str], ...]
	center: tuple[float, float]
	angle_radians: float


@dataclasses.dataclass(frozen=True)
class CDMLBondOrderEditRequest:
	"""One revision-bound exact order edit for a direct core bond."""

	expected_revision: int
	molecule_id: str
	bond_id: str
	order: int


@dataclasses.dataclass(frozen=True)
class CDMLBondTypeEditRequest:
	"""One revision-bound exact type edit for a direct core bond."""

	expected_revision: int
	molecule_id: str
	bond_id: str
	bond_type: str


@dataclasses.dataclass(frozen=True)
class CDMLBondPropertiesPatch:
	"""One revision-bound explicit-field patch for one direct core bond."""

	expected_revision: int
	molecule_id: str
	bond_id: str
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLAtomPropertiesPatch:
	"""One revision-bound explicit-field patch for one direct core atom."""

	expected_revision: int
	molecule_id: str
	atom_id: str
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLTopLevelDeleteRequest:
	"""One revision-bound request to remove durable direct-root records."""

	expected_revision: int
	root_ids: tuple[str, ...]
	label: str | None = None


@dataclasses.dataclass(frozen=True)
class CDMLStructuralEditRequest:
	"""One revision-bound persistent Draw-mode topology operation.

	All positions are PostScript scene points.  The operation grammar is
	deliberately narrow: it represents completed Draw-mode gestures without
	exposing a mutable XML or chemistry graph to a frontend.
	"""

	expected_revision: int
	kind: str
	molecule_id: str | None = None
	source_atom_id: str | None = None
	target_atom_id: str | None = None
	bond_id: str | None = None
	source_position: tuple[float, float] | None = None
	target_position: tuple[float, float] | None = None
	element: str | None = None
	bond_type: str | None = None
	bond_order: int | None = None
	simple_double: bool | None = None


@dataclasses.dataclass(frozen=True)
class CDMLAtomElementEditRequest:
	"""One revision-bound replacement of a direct core atom element."""

	expected_revision: int
	molecule_id: str
	atom_id: str
	element: str


@dataclasses.dataclass(frozen=True)
class CDMLAtomNumberEditRequest:
	"""One revision-bound assignment or clearing of a direct atom number."""

	expected_revision: int
	molecule_id: str
	atom_id: str
	number: int | None
	show_number: bool | None


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeNameEditRequest:
	"""One revision-bound replacement or clear of a direct-root molecule name."""

	expected_revision: int
	molecule_id: str
	name: str


@dataclasses.dataclass(frozen=True)
class CDMLPaperPropertiesPatch:
	"""One revision-bound patch containing only explicit paper-field intent.

	``changes`` is an ordered tuple of exact two-value tuples.  Keeping this
	immutable request representation permits the backend to reject duplicate
	field declarations instead of silently choosing a frontend-side winner.
	"""

	expected_revision: int
	changes: tuple[tuple[str, object], ...]


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeSmilesQuery:
	"""One revision-bound, nonmutating direct-root molecule SMILES query."""

	expected_revision: int
	molecule_id: str


@dataclasses.dataclass(frozen=True)
class CDMLMoleculeSmilesResult:
	"""One immutable SMILES observation from an authoritative snapshot."""

	revision: int
	molecule_id: str
	smiles: str


@dataclasses.dataclass(frozen=True)
class CDMLIssue:
	"""One strict-validation finding with a stable document location hint."""

	code: str
	message: str
	path: str


@dataclasses.dataclass(frozen=True)
class CDMLObjectRecord:
	"""An immutable persistent-element view with stable preorder metadata."""

	position: int
	path: str
	local_name: str
	identifier: str | None
	raw_xml: str
	opaque: bool


@dataclasses.dataclass(frozen=True)
class CDMLReactionRoleRecord:
	"""An immutable recognized reaction-role reference in document order."""

	reaction_path: str
	path: str
	role_name: str
	target_identifier: str | None


@dataclasses.dataclass(frozen=True)
class CDMLSnapshot:
	"""One immutable view of a backend-owned revision."""

	revision: int
	cdml: str
	is_dirty: bool


@dataclasses.dataclass(frozen=True)
class CDMLCommit:
	"""The accepted backend result for a commit or restore transaction."""

	snapshot: CDMLSnapshot
	id_map: collections.abc.Mapping[str, str]

	@property
	def revision(self) -> int:
		"""Return the newly accepted monotonic backend revision."""
		return self.snapshot.revision

	@property
	def cdml(self) -> str:
		"""Return canonical complete CDML from the accepted backend snapshot."""
		return self.snapshot.cdml


@dataclasses.dataclass(frozen=True)
class CDMLGeometryRepairResult:
	"""Immutable result of one geometry repair observation or accepted commit."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLAtomAlignResult:
	"""Immutable result of one backend-authoritative atom alignment."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLAtomTranslateResult:
	"""Immutable result of one backend-authoritative atom translation."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLAtomRotateResult:
	"""Immutable result of one backend-authoritative atom rotation."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLBondOrderEditResult:
	"""Immutable result of one exact backend-authoritative bond-order edit."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLBondTypeEditResult:
	"""Immutable result of one exact backend-authoritative bond-type edit."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLBondPropertiesPatchResult:
	"""Immutable result of one backend-authoritative bond-properties patch."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLAtomPropertiesPatchResult:
	"""Immutable result of one backend-authoritative atom-properties patch."""

	snapshot: CDMLSnapshot
	changed: bool
	commit: CDMLCommit | None


@dataclasses.dataclass(frozen=True)
class CDMLStructuralEditResult:
	"""Immutable authoritative result of one accepted structural operation."""

	commit: CDMLCommit
	created_molecule_id: str | None = None
	created_atom_ids: tuple[str, ...] = ()
	created_bond_ids: tuple[str, ...] = ()
	updated_bond_ids: tuple[str, ...] = ()

	@property
	def snapshot(self) -> CDMLSnapshot:
		"""Return the accepted canonical snapshot without exposing mutable DOM."""
		return self.commit.snapshot


#============================================
def _local_name(node: object) -> str:
	"""Return an XML local name without changing the stored node."""
	name = getattr(node, "localName", None) or getattr(node, "tagName", "")
	if ":" in name:
		name = name.rsplit(":", 1)[1]
	return str(name)


#============================================
def _is_core_cdml_element(element: object) -> bool:
	"""Return whether one element itself has a recognized CDML name and namespace."""
	namespace_uri = getattr(element, "namespaceURI", None)
	is_core_element = (
		_local_name(element) in oasa.cdml_xml.CDML_CORE_ELEMENT_NAMES
		and namespace_uri in (None, "", CDML_NAMESPACE_URI)
	)
	return is_core_element


#============================================
def _is_cdml_element(element: object) -> bool:
	"""Return whether an element is editable core CDML in its document context.

	Standalone legacy CDML has no namespace.  Prefix-qualified CDML must use
	the canonical namespace URI.  Every element ancestor must also be core CDML:
	an unknown wrapper owns its complete subtree, even when a descendant uses a
	known CDML local name and namespace.
	"""
	if oasa.cdml_xml.has_preservation_only_ancestor(element):
		return False
	current = element
	while current is not None and getattr(current, "nodeType", None) == current.ELEMENT_NODE:
		if not _is_core_cdml_element(current):
			return False
		parent = current.parentNode
		if parent is None or getattr(parent, "nodeType", None) != parent.ELEMENT_NODE:
			break
		current = parent
	return True


#============================================
def _element_children(node: object) -> list:
	"""Return direct element children in their existing document order."""
	children = []
	for child in node.childNodes:
		if child.nodeType == child.ELEMENT_NODE:
			children.append(child)
	return children


#============================================
def _descendant_elements(node: object) -> list:
	"""Return descendants in depth-first source order, including ``node``."""
	elements = [node]
	for child in _element_children(node):
		elements.extend(_descendant_elements(child))
	return elements


#============================================
def _node_path(node: object) -> str:
	"""Return a compact location hint for diagnostics without modifying XML."""
	parts = []
	current = node
	while current is not None and getattr(current, "nodeType", None) == current.ELEMENT_NODE:
		parts.append(_local_name(current))
		parent = current.parentNode
		if parent is None or getattr(parent, "nodeType", None) != parent.ELEMENT_NODE:
			break
		current = parent
	path = "/" + "/".join(reversed(parts))
	return path


#============================================
def _is_provisional_id(value: str) -> bool:
	"""Return whether ``value`` is a transaction-only frontend correlation ID."""
	return bool(_PROVISIONAL_ID_PATTERN.fullmatch(value))


#============================================
def _has_provisional_id_prefix(value: str) -> bool:
	"""Return whether a value claims the reserved provisional-ID namespace."""
	return value.startswith(_PROVISIONAL_ID_PREFIX)


#============================================
def _durable_prefix(local_name: str) -> str:
	"""Return a readable durable-ID prefix for a recognized CDML object."""
	prefixes = {
		"atom": "a",
		"bond": "b",
		"molecule": "m",
	}
	prefix = prefixes.get(local_name, local_name[:1] or "o")
	return prefix


#============================================
def _next_durable_id(local_name: str, used_ids: set[str]) -> str:
	"""Allocate one collision-free backend durable ID without mutating callers."""
	prefix = _durable_prefix(local_name)
	serial = 1
	identifier = f"{prefix}{serial}"
	while identifier in used_ids:
		serial += 1
		identifier = f"{prefix}{serial}"
	return identifier


#============================================
def _known_reference_attributes(element: object) -> tuple[str, ...]:
	"""Return schema-supported reference attributes for one recognized element."""
	if not _is_cdml_element(element):
		return ()
	local_name = _local_name(element)
	if local_name == "bond":
		return ("start", "end")
	if local_name == "template":
		return ("atom", "bond_first", "bond_second")
	parent = element.parentNode
	if (
		parent is not None
		and _is_cdml_element(parent)
		and _local_name(parent) == "reaction"
		and local_name in ("arrow", "condition", "plus", "product", "reactant")
	):
		return ("idref",)
	return ()


#============================================
def _is_id_declaration(element: object) -> bool:
	"""Return whether an element may declare a provisional backend ID.

	This is deliberately narrower than ``_is_id_definition``.  Known editable
	CDML declarations participate in frontend provisional-ID allocation, while
	opaque extension XML owns literal IDs without receiving any provisional-ID
	interpretation.
	"""
	return (
		_is_cdml_element(element)
		and _local_name(element) in _ID_DECLARATION_ELEMENT_NAMES
		and not oasa.cdml_xml.is_preservation_only_container(element)
		and not _fragment_member_reference(element)
	)


#============================================
def _is_id_definition(element: object) -> bool:
	"""Return whether an ``id`` is a lookup definition, including opaque XML.

	Opaque IDs are indexed for whole-document lookup but never inspected for
	provisional-token validation or backend allocation unless their element is a
	recognized editable declaration.
	"""
	return not _fragment_member_reference(element)


#============================================
def _element_locations(root: object) -> tuple[tuple[int, object], ...]:
	"""Return all persistent elements in stable depth-first preorder."""
	elements = _descendant_elements(root)[1:]
	locations = tuple(enumerate(elements))
	return locations


#============================================
def _record_for_element(position: int, element: object) -> CDMLObjectRecord:
	"""Build a node-free immutable record from one persistent XML element."""
	local_name = _local_name(element)
	identifier = element.getAttribute("id") or None
	record = CDMLObjectRecord(
		position=position,
		path=_node_path(element),
		local_name=local_name,
		identifier=identifier,
		raw_xml=element.toxml(),
		opaque=not _is_cdml_element(element),
	)
	return record


#============================================
def _fragment_member_reference(element: object) -> bool:
	"""Return whether an ``id`` attribute is a documented fragment member ref."""
	parent = element.parentNode
	if (
		parent is None
		or not _is_cdml_element(element)
		or not _is_cdml_element(parent)
		or _local_name(parent) != "fragment"
	):
		return False
	return _local_name(element) in ("vertex", "bond")


#============================================
def _copy_proposal_namespace_declarations(proposal_root: object, molecule: object) -> None:
	"""Keep proposal-root namespace bindings available on one imported molecule."""
	for index in range(proposal_root.attributes.length):
		attribute = proposal_root.attributes.item(index)
		if not attribute.name.startswith("xmlns"):
			continue
		if not molecule.hasAttribute(attribute.name):
			molecule.setAttribute(attribute.name, attribute.value)


#============================================
def _insertion_coordinate(value: str) -> float:
	"""Convert one accepted CDML scene coordinate to centimeters."""
	if not isinstance(value, str) or not _COORDINATE_PATTERN.fullmatch(value):
		raise CDMLValidationError(f"invalid insertion coordinate: {value!r}")
	is_centimeters = value.endswith("cm")
	number_text = value[:-2] if is_centimeters else value
	number = float(number_text)
	if not math.isfinite(number):
		raise CDMLValidationError(f"nonfinite insertion coordinate: {value!r}")
	coordinate = number if is_centimeters else number * _POINT_CM_PER_POSTSCRIPT_POINT
	if not math.isfinite(coordinate):
		raise CDMLValidationError(f"overflow insertion coordinate: {value!r}")
	return coordinate


#============================================
def _translated_coordinate(value: str, offset: float) -> str:
	"""Return one translated, canonical centimeter coordinate."""
	coordinate = _insertion_coordinate(value) + offset
	if not math.isfinite(coordinate):
		raise CDMLValidationError("translated insertion coordinate is nonfinite")
	result = f"{coordinate:.3f}cm"
	return result


#============================================
def _canonical_authored_coordinate(coordinate: float) -> str:
	"""Return one 0.001 cm canonical coordinate without a signed zero.

	Persistent coordinate operations compare authored values at the precision
	that they can write.  This keeps a geometrically real but sub-resolution
	motion from creating a meaningless revision, while retaining a source's
	lexical spelling whenever that axis is unchanged.
	"""
	rounded = round(coordinate, 3)
	if rounded == 0.0:
		rounded = 0.0
	return f"{rounded:.3f}cm"


#============================================
def _translate_point(point: object, dx: float, dy: float) -> None:
	"""Validate and translate one established CDML point in detached state."""
	if _element_children(point):
		raise CDMLValidationError("insertion point may not contain element children")
	if not point.hasAttribute("x") or not point.hasAttribute("y"):
		raise CDMLValidationError("insertion point requires x and y")
	if point.hasAttribute("z"):
		_insertion_coordinate(point.getAttribute("z"))
	point.setAttribute("x", _translated_coordinate(point.getAttribute("x"), dx))
	point.setAttribute("y", _translated_coordinate(point.getAttribute("y"), dy))


#============================================
def _translate_mark(mark: object, dx: float, dy: float) -> None:
	"""Translate an explicit mark position while retaining all mark semantics."""
	if _element_children(mark):
		raise CDMLValidationError("insertion mark may not contain element children")
	has_x = mark.hasAttribute("x")
	has_y = mark.hasAttribute("y")
	if has_x != has_y:
		raise CDMLValidationError("insertion mark x and y must be present together")
	if has_x:
		mark.setAttribute("x", _translated_coordinate(mark.getAttribute("x"), dx))
		mark.setAttribute("y", _translated_coordinate(mark.getAttribute("y"), dy))


#============================================
def _validate_vertex_geometry(vertex: object, dx: float, dy: float) -> None:
	"""Validate and translate one complete established molecular vertex."""
	name = _local_name(vertex)
	allowed_children = {
		"atom": frozenset({"point", "font", "ftext", "mark"}),
		"group": frozenset({"point", "font", "mark"}),
		"text": frozenset({"point", "font", "ftext", "mark"}),
		"query": frozenset({"point", "font", "mark"}),
	}[name]
	points = []
	for child in _element_children(vertex):
		child_name = _local_name(child)
		if not _is_cdml_element(child) or child_name not in allowed_children:
			raise CDMLValidationError(f"unsupported {name} child: {child_name}")
		if child_name == "point":
			points.append(child)
		elif child_name == "font" and _element_children(child):
			raise CDMLValidationError(f"insertion {name} font may not contain element children")
		elif child_name == "mark":
			_translate_mark(child, dx, dy)
	if len(points) != 1:
		raise CDMLValidationError(f"insertion {name} requires exactly one direct point")
	_translate_point(points[0], dx, dy)


#============================================
def _validate_molecule_fragment(molecule: object, dx: float, dy: float) -> None:
	"""Validate the closed molecular insertion subset and translate its geometry."""
	for child in _element_children(molecule):
		name = _local_name(child)
		if not _is_cdml_element(child) or name not in _MOLECULE_CHILD_NAMES:
			raise CDMLValidationError(f"unsupported molecule child: {name}")
		if name in _MOLECULE_VERTEX_NAMES:
			_validate_vertex_geometry(child, dx, dy)
		elif name in ("bond", "template") and _element_children(child):
			raise CDMLValidationError(f"insertion {name} may not contain element children")
		elif name == "fragment":
			for member in _element_children(child):
				member_name = _local_name(member)
				if not _is_cdml_element(member) or member_name not in (
						"name", "bond", "vertex", "property",
				):
					raise CDMLValidationError(f"unsupported fragment child: {member_name}")
				if _element_children(member):
					raise CDMLValidationError(f"insertion fragment {member_name} may not contain children")


#============================================
def _translate_top_level_geometry(element: object, dx: float, dy: float) -> None:
	"""Validate and translate the allowlisted top-level presentation grammar."""
	name = _local_name(element)
	children = _element_children(element)
	if name == "molecule":
		_validate_molecule_fragment(element, dx, dy)
		return
	if name == "arrow":
		if len(children) < 2 or any(
				not _is_cdml_element(child) or _local_name(child) != "point" for child in children
		):
			raise CDMLValidationError("insertion arrow requires at least two direct points")
		for point in children:
			_translate_point(point, dx, dy)
		return
	if name == "plus":
		if sum(_local_name(child) == "point" for child in children) != 1 or sum(
				_local_name(child) == "font" for child in children
		) > 1 or any(
				not _is_cdml_element(child) or _local_name(child) not in ("point", "font") for child in children
			):
			raise CDMLValidationError("insertion plus requires one point and optional font")
		for child in children:
			if _local_name(child) == "font" and _element_children(child):
				raise CDMLValidationError("insertion plus font may not contain element children")
		_translate_point(next(child for child in children if _local_name(child) == "point"), dx, dy)
		return
	if name == "text":
		if sum(_local_name(child) == "point" for child in children) != 1 or sum(
				_local_name(child) == "ftext" for child in children
		) != 1 or sum(_local_name(child) == "font" for child in children) > 1 or any(
				not _is_cdml_element(child) or _local_name(child) not in ("point", "font", "ftext")
				for child in children
		):
			raise CDMLValidationError("insertion text requires one point, one ftext, and optional font")
		for child in children:
			if _local_name(child) == "font" and _element_children(child):
				raise CDMLValidationError("insertion text font may not contain element children")
		_translate_point(next(child for child in children if _local_name(child) == "point"), dx, dy)
		return
	if name in ("rect", "square", "oval", "circle"):
		if children:
			raise CDMLValidationError(f"insertion {name} may not contain element children")
		for attribute in ("x1", "y1", "x2", "y2"):
			if not element.hasAttribute(attribute):
				raise CDMLValidationError(f"insertion {name} requires {attribute}")
			offset = dx if attribute.startswith("x") else dy
			element.setAttribute(attribute, _translated_coordinate(element.getAttribute(attribute), offset))
		return
	if name in ("polygon", "polyline"):
		minimum = 3 if name == "polygon" else 2
		if len(children) < minimum or any(
				not _is_cdml_element(child) or _local_name(child) != "point" for child in children
		):
			raise CDMLValidationError(f"insertion {name} requires direct points")
		for point in children:
			_translate_point(point, dx, dy)
		return
	if name == "reaction":
		if any(
			not _is_cdml_element(child)
			or _local_name(child) not in _REACTION_ROLE_NAMES
			or _element_children(child)
			or child.attributes.length != 1
			or not child.hasAttribute("idref")
			or not child.getAttribute("idref")
			for child in children
		):
			raise CDMLValidationError("insertion reaction has unsupported children")
		return
	raise CDMLValidationError(f"unsupported insertion root: {name}")


#============================================
def _validate_insertion_translation(translation: object) -> tuple[float, float]:
	"""Return finite PostScript point offsets from one plain-data request value."""
	if type(translation) is not tuple or len(translation) != 2:
		raise CDMLValidationError("insertion translation requires exactly two numeric values")
	values = []
	for value in translation:
		if type(value) not in (int, float):
			raise CDMLValidationError("insertion translation requires finite plain numeric values")
		try:
			numeric_value = float(value)
		except OverflowError as error:
			raise CDMLValidationError("insertion translation requires finite plain numeric values") from error
		if not math.isfinite(numeric_value):
			raise CDMLValidationError("insertion translation requires finite plain numeric values")
		offset = numeric_value * _POINT_CM_PER_POSTSCRIPT_POINT
		if not math.isfinite(offset):
			raise CDMLValidationError("insertion translation requires finite plain numeric values")
		values.append(offset)
	return values[0], values[1]


#============================================
def _is_insertion_definition(element: object) -> bool:
	"""Return whether one allowlisted-fragment element owns a durable ID."""
	if not _is_cdml_element(element) or _fragment_member_reference(element):
		return False
	parent = element.parentNode
	if parent is not None and _is_cdml_element(parent) and _local_name(parent) == "reaction":
		return False
	name = _local_name(element)
	if parent is not None and _is_cdml_element(parent) and _local_name(parent) == "molecule":
		return name in _MOLECULE_VERTEX_NAMES or name in ("bond", "fragment")
	if parent is not None and _is_cdml_element(parent) and _local_name(parent) == "cdml":
		return name in _TOP_LEVEL_INSERTION_NAMES
	return False


#============================================
def _insertion_references(element: object) -> tuple[str, ...]:
	"""Return the closed-fragment reference fields for one recognized element."""
	parent = element.parentNode
	parent_name = _local_name(parent) if parent is not None else ""
	name = _local_name(element)
	if parent_name == "molecule" and name == "bond":
		return ("start", "end")
	if parent_name == "molecule" and name == "template":
		references = ["atom"]
		for attribute in ("bond_first", "bond_second"):
			if element.hasAttribute(attribute):
				references.append(attribute)
		return tuple(references)
	if _fragment_member_reference(element):
		return ("id",)
	if parent_name == "reaction" and name in _REACTION_ROLE_NAMES:
		return ("idref",)
	return ()


#============================================
def _prepare_top_level_fragment(
		fragment: "CDMLDocument",
		destination_cdml: str,
		consumed_tokens: set[str],
		dx: float,
		dy: float,
		) -> tuple:
	"""Validate, privately tokenise, and translate one detached insertion fragment."""
	root = fragment._dom_document.documentElement
	roots = tuple(_element_children(root))
	if not roots:
		raise CDMLValidationError("top-level insertion fragment requires an element child")
	for element in roots:
		if not _is_cdml_element(element) or _local_name(element) not in _TOP_LEVEL_INSERTION_NAMES:
			raise CDMLValidationError(f"unsupported insertion root: {_local_name(element)}")
		_translate_top_level_geometry(element, dx, dy)
	definitions = []
	by_source_id = {}
	for root_element in roots:
		for element in _descendant_elements(root_element):
			if not _is_insertion_definition(element):
				continue
			source_id = element.getAttribute("id")
			if source_id:
				if source_id in by_source_id:
					raise CDMLValidationError(f"duplicate insertion source id: {source_id}")
				by_source_id[source_id] = element
			definitions.append((source_id, element))
	for root_element in roots:
		for element in _descendant_elements(root_element):
			for attribute in _insertion_references(element):
				reference = element.getAttribute(attribute)
				if not reference or reference not in by_source_id:
					raise CDMLValidationError(
						f"insertion {attribute} reference must resolve inside the fragment: {reference}",
					)
	reserved_text = destination_cdml + fragment.serialize()
	reserved_tokens = set(consumed_tokens)
	token_by_source_id = {}
	serial = 1
	for source_id, element in definitions:
		while True:
			token = f"__bkchem_new__insert_{serial}"
			serial += 1
			if token not in reserved_tokens and token not in reserved_text:
				break
		reserved_tokens.add(token)
		if source_id:
			token_by_source_id[source_id] = token
		element.setAttribute("id", token)
	for root_element in roots:
		for element in _descendant_elements(root_element):
			for attribute in _insertion_references(element):
				reference = element.getAttribute(attribute)
				if reference:
					element.setAttribute(attribute, token_by_source_id[reference])
	return roots


#============================================
def _proposal_molecules(proposal: "CDMLDocument") -> tuple:
	"""Return the bounded top-level molecule payload from one proposal document."""
	root = proposal._dom_document.documentElement
	molecules = tuple(_element_children(root))
	if not molecules:
		raise CDMLValidationError("molecule insertion proposal must contain a molecule")
	for element in molecules:
		if not _is_cdml_element(element) or _local_name(element) != "molecule":
			raise CDMLValidationError(
			"molecule insertion proposal may contain only top-level molecules",
		)
		for descendant in _descendant_elements(element):
			if not _is_id_declaration(descendant):
				continue
			identifier = descendant.getAttribute("id")
			if not _is_provisional_id(identifier):
				raise CDMLValidationError(
					"molecule insertion declarations require valid provisional IDs",
				)
	return molecules


#============================================
def _direct_core_child_by_id(parent: object, identifier: str, local_name: str) -> object:
	"""Return one direct editable core child or reject a non-core target."""
	for child in _element_children(parent):
		if (
			_is_cdml_element(child)
			and _local_name(child) == local_name
			and child.getAttribute("id") == identifier
		):
			return child
	raise CDMLValidationError(
		f"structural edit target is not a direct editable {local_name}: {identifier}",
	)


#============================================
def _direct_root_molecule(document: "CDMLDocument", identifier: str) -> object:
	"""Return a direct-root core molecule without traversing opaque wrappers."""
	root = document._dom_document.documentElement
	return _direct_core_child_by_id(root, identifier, "molecule")


#============================================
def _first_direct_core_child(document: "CDMLDocument", local_name: str) -> object | None:
	"""Return the first direct core root of one local name in source order."""
	root = document._dom_document.documentElement
	for child in _element_children(root):
		if _is_cdml_element(child) and _local_name(child) == local_name:
			return child
	return None


#============================================
def _new_paper_defaults(document: "CDMLDocument") -> tuple[str, str]:
	"""Read valid direct standard defaults or return the authored fallback."""
	standard = _first_direct_core_child(document, "standard")
	if standard is not None:
		paper_type = standard.getAttribute("paper_type")
		orientation = standard.getAttribute("paper_orientation")
		if (
			paper_type in _CDML_PAPER_SIZES_MM
			and paper_type != "custom"
			and orientation in ("portrait", "landscape")
		):
			return paper_type, orientation
	return "A4", "portrait"


#============================================
def _paper_dimension_text(value: float) -> str:
	"""Return one finite positive paper dimension in stable CDML text."""
	return "%g" % value


#============================================
def _direct_molecule_atom(molecule: object, identifier: str) -> object:
	"""Return one direct atom in the named editable molecule."""
	return _direct_core_child_by_id(molecule, identifier, "atom")


#============================================
def _direct_molecule_bond(molecule: object, identifier: str) -> object:
	"""Return one direct bond in the named editable molecule."""
	return _direct_core_child_by_id(molecule, identifier, "bond")


#============================================
def _new_core_element(document: "CDMLDocument", parent: object, local_name: str) -> object:
	"""Create a core element that retains the target document's namespace style."""
	prefix = getattr(parent, "prefix", None)
	namespace_uri = getattr(parent, "namespaceURI", None)
	if namespace_uri == CDML_NAMESPACE_URI:
		qualified_name = f"{prefix}:{local_name}" if prefix else local_name
		return document._dom_document.createElementNS(namespace_uri, qualified_name)
	return document._dom_document.createElement(local_name)


#============================================
def _point_text(position: tuple[float, float]) -> tuple[str, str]:
	"""Convert a validated scene point to the established CDML centimeter text."""
	x, y = position
	return (
		"%.3fcm" % (x * _POINT_CM_PER_POSTSCRIPT_POINT),
		"%.3fcm" % (y * _POINT_CM_PER_POSTSCRIPT_POINT),
	)


#============================================
def _append_atom(
		document: "CDMLDocument", molecule: object, identifier: str,
		element: str, position: tuple[float, float],
		) -> object:
	"""Append one direct atom and its point in the established CDML grammar."""
	atom = _new_core_element(document, molecule, "atom")
	atom.setAttribute("id", identifier)
	atom.setAttribute("name", element)
	point = _new_core_element(document, atom, "point")
	x_text, y_text = _point_text(position)
	point.setAttribute("x", x_text)
	point.setAttribute("y", y_text)
	atom.appendChild(point)
	molecule.appendChild(atom)
	return atom


#============================================
def _append_bond(
		document: "CDMLDocument", molecule: object, identifier: str,
		start: str, end: str, bond_type: str, bond_order: int,
		simple_double: bool,
		) -> object:
	"""Append one direct bond with selected Draw-mode semantics."""
	bond = _new_core_element(document, molecule, "bond")
	bond.setAttribute("id", identifier)
	bond.setAttribute("start", start)
	bond.setAttribute("end", end)
	bond.setAttribute("type", f"{bond_type}{bond_order}")
	_apply_simple_double_policy(bond, bond_type, bond_order, simple_double)
	molecule.appendChild(bond)
	return bond


#============================================
def _apply_simple_double_policy(
		bond: object, bond_type: str, bond_order: int, simple_double: bool,
		) -> None:
	"""Write the selected added-lane style where the CDML grammar uses it."""
	styled_triple = bond_type in ("a", "d", "o") and bond_order == 3
	if bond_order == 2 or styled_triple:
		bond.setAttribute("simple_double", str(int(simple_double)))
	elif bond.hasAttribute("simple_double"):
		bond.removeAttribute("simple_double")


#============================================
def _finite_bond_attribute(bond: object, name: str, default: float) -> float:
	"""Read one finite numeric depiction field before a bond-tool transition."""
	if not bond.hasAttribute(name):
		return default
	try:
		value = float(bond.getAttribute(name))
	except ValueError as error:
		raise CDMLValidationError(f"bond {name} is not numeric") from error
	if not math.isfinite(value):
		raise CDMLValidationError(f"bond {name} is not finite")
	return value


#============================================
def _bond_centered(bond: object) -> bool:
	"""Return the established CDML interpretation of a centered double bond."""
	return bond.getAttribute("center") == "yes"


#============================================
def _set_bond_number(bond: object, name: str, value: float) -> None:
	"""Store a finite depiction value without changing unrelated attributes."""
	if not math.isfinite(value):
		raise CDMLValidationError(f"bond {name} transition is not finite")
	bond.setAttribute(name, "%g" % value)


#============================================
def _apply_bond_tool_transition(
		bond: object, bond_type: str, bond_order: int, simple_double: bool,
		) -> None:
	"""Apply the established Draw-mode type/order/depiction transition in CDML."""
	current_type, current_order, _legacy = oasa.bond_semantics.parse_cdml_bond_type(
		bond.getAttribute("type"),
	)
	if current_type not in oasa.bond_semantics.BOND_TYPES or current_order < 1:
		raise CDMLValidationError("bond has unsupported current type or order")
	if bond_type != current_type:
		bond.setAttribute("type", f"{bond_type}{bond_order}")
	elif bond_order == 1 and bond_type in ("n", "d"):
		bond.setAttribute("type", f"{bond_type}{(current_order % 3) + 1}")
	elif bond_order != current_order:
		bond.setAttribute("type", f"{bond_type}{bond_order}")
	else:
		if bond_type in ("w", "h"):
			start = bond.getAttribute("start")
			bond.setAttribute("start", bond.getAttribute("end"))
			bond.setAttribute("end", start)
		elif bond_order == 2:
			bond_width = _finite_bond_attribute(bond, "bond_width", 6.0)
			auto_sign = _finite_bond_attribute(bond, "auto_sign", 1.0)
			if _bond_centered(bond):
				_set_bond_number(bond, "bond_width", -bond_width)
				_set_bond_number(bond, "auto_sign", -auto_sign)
				bond.setAttribute("center", "no")
			elif bond_width > 0:
				_set_bond_number(bond, "bond_width", -bond_width)
				_set_bond_number(bond, "auto_sign", -auto_sign)
			else:
				bond.setAttribute("center", "yes")
	updated_type, updated_order, _legacy = oasa.bond_semantics.parse_cdml_bond_type(
		bond.getAttribute("type"),
	)
	_apply_simple_double_policy(bond, updated_type or "n", updated_order, simple_double)


#============================================
def _required_structural_identifier(value: object, name: str) -> str:
	"""Return one plain durable identifier or raise a stable validation error."""
	if not isinstance(value, str) or not value:
		raise CDMLValidationError(f"structural edit {name} must be a nonempty string")
	return value


#============================================
def _required_structural_position(value: object, name: str) -> tuple[float, float]:
	"""Return one finite scene point expressed as a two-value plain tuple."""
	if type(value) is not tuple or len(value) != 2:
		raise CDMLValidationError(f"structural edit {name} must be a two-value tuple")
	coordinates = []
	for coordinate in value:
		if type(coordinate) not in (int, float) or not math.isfinite(coordinate):
			raise CDMLValidationError(
				f"structural edit {name} must contain finite plain numeric values",
			)
		coordinates.append(float(coordinate))
	return coordinates[0], coordinates[1]


#============================================
def _required_structural_element(value: object) -> str:
	"""Return an OASA-supported atom symbol for a created atom."""
	if not isinstance(value, str) or value not in oasa.periodic_table.periodic_table:
		raise CDMLValidationError("structural edit element must be a supported atom symbol")
	return value


#============================================
def _required_structural_bond_settings(request: CDMLStructuralEditRequest) -> tuple[str, int, bool]:
	"""Validate the selected Draw-mode bond settings without frontend coupling."""
	if request.bond_type not in oasa.bond_semantics.BOND_TYPES:
		raise CDMLValidationError("structural edit bond_type is unsupported")
	if type(request.bond_order) is not int:
		raise CDMLValidationError("structural edit bond_order must be an int")
	if not oasa.bond_semantics.is_authored_bond_order(request.bond_type, request.bond_order):
		raise CDMLValidationError("structural edit bond_type/order is unsupported")
	if type(request.simple_double) is not bool:
		raise CDMLValidationError("structural edit simple_double must be a bool")
	return request.bond_type, request.bond_order, request.simple_double


#============================================
def _validate_structural_request(request: object) -> tuple:
	"""Validate one exact structural grammar production before candidate mutation."""
	if not isinstance(request, CDMLStructuralEditRequest):
		raise CDMLValidationError("structural edit requires a structural edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("structural edit expected_revision must be an int")
	bond_type, bond_order, simple_double = _required_structural_bond_settings(request)
	if request.kind == "create-bonded-pair":
		if any(value is not None for value in (
				request.molecule_id, request.source_atom_id, request.target_atom_id, request.bond_id,
		)):
			raise CDMLValidationError("create-bonded-pair accepts no existing durable IDs")
		return (
			request.kind,
			_required_structural_position(request.source_position, "source_position"),
			_required_structural_position(request.target_position, "target_position"),
			_required_structural_element(request.element),
			bond_type,
			bond_order,
			simple_double,
		)
	if request.kind == "extend-atom":
		if any(value is not None for value in (
				request.target_atom_id, request.bond_id, request.source_position,
		)):
			raise CDMLValidationError("extend-atom accepts one source atom and endpoint only")
		return (
			request.kind,
			_required_structural_identifier(request.molecule_id, "molecule_id"),
			_required_structural_identifier(request.source_atom_id, "source_atom_id"),
			_required_structural_position(request.target_position, "target_position"),
			_required_structural_element(request.element),
			bond_type,
			bond_order,
			simple_double,
		)
	if request.kind == "join-atoms":
		if any(value is not None for value in (
				request.bond_id, request.source_position, request.target_position, request.element,
		)):
			raise CDMLValidationError("join-atoms accepts two existing atoms and bond settings only")
		return (
			request.kind,
			_required_structural_identifier(request.molecule_id, "molecule_id"),
			_required_structural_identifier(request.source_atom_id, "source_atom_id"),
			_required_structural_identifier(request.target_atom_id, "target_atom_id"),
			bond_type,
			bond_order,
			simple_double,
		)
	if request.kind == "apply-bond-tool":
		if any(value is not None for value in (
				request.source_atom_id, request.target_atom_id, request.source_position,
				request.target_position, request.element,
		)):
			raise CDMLValidationError("apply-bond-tool accepts one existing bond and settings only")
		return (
			request.kind,
			_required_structural_identifier(request.molecule_id, "molecule_id"),
			_required_structural_identifier(request.bond_id, "bond_id"),
			bond_type,
			bond_order,
			simple_double,
		)
	raise CDMLValidationError(f"unsupported structural edit kind: {request.kind}")


#============================================
def _validate_atom_element_request(request: object) -> tuple[str, str, str]:
	"""Validate one plain atom-element substitution request before mutation."""
	if not isinstance(request, CDMLAtomElementEditRequest):
		raise CDMLValidationError("atom element edit requires an atom element edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("atom element edit expected_revision must be an int")
	if not isinstance(request.molecule_id, str) or not request.molecule_id:
		raise CDMLValidationError("atom element edit molecule_id must be a nonempty string")
	if not isinstance(request.atom_id, str) or not request.atom_id:
		raise CDMLValidationError("atom element edit atom_id must be a nonempty string")
	if not isinstance(request.element, str) or request.element not in oasa.periodic_table.periodic_table:
		raise CDMLValidationError("atom element edit element must be a supported atom symbol")
	return request.molecule_id, request.atom_id, request.element


#============================================
def _validate_atom_properties_patch(
		request: object,
		) -> tuple[str, str, tuple[tuple[str, object], ...]]:
	"""Validate explicit atom intent before resolving or changing a target."""
	if type(request) is not CDMLAtomPropertiesPatch:
		raise CDMLAtomPropertiesPatchError("atom properties requires an atom properties patch")
	if type(request.expected_revision) is not int:
		raise CDMLAtomPropertiesPatchError("atom properties expected_revision must be an int")
	for name, value in (("molecule_id", request.molecule_id), ("atom_id", request.atom_id)):
		if not isinstance(value, str) or not value:
			raise CDMLAtomPropertiesPatchError(
				"atom properties %s must be a nonempty string" % name,
			)
	if type(request.changes) is not tuple:
		raise CDMLAtomPropertiesPatchError("atom properties changes must be an immutable tuple")
	validated = []
	seen = set()
	fields = (
		"element", "charge", "valency", "isotope", "multiplicity", "show",
		"show_hydrogens", "font_size", "line_color",
	)
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLAtomPropertiesPatchError("atom properties changes must be field/value pairs")
		field_name, value = change
		if type(field_name) is not str or field_name not in fields:
			raise CDMLAtomPropertiesPatchError(
				"atom properties field must be a supported string",
			)
		if field_name in seen:
			raise CDMLAtomPropertiesPatchError("atom properties fields must be unique")
		seen.add(field_name)
		if field_name == "element":
			if type(value) is not str or value not in oasa.periodic_table.periodic_table:
				raise CDMLAtomPropertiesPatchError(
					"atom properties element must be a supported atom symbol",
				)
		elif field_name == "charge":
			if type(value) is not int or not -9 <= value <= 9:
				raise CDMLAtomPropertiesPatchError("atom properties charge must be an int from -9 to 9")
		elif field_name == "valency":
			if type(value) is not int or not 0 <= value <= 10:
				raise CDMLAtomPropertiesPatchError("atom properties valency must be an int from 0 to 10")
		elif field_name == "isotope":
			if value is not None and (type(value) is not int or not 1 <= value <= 300):
				raise CDMLAtomPropertiesPatchError(
					"atom properties isotope must be null or an int from 1 to 300",
				)
		elif field_name == "multiplicity":
			if type(value) is not int or value not in (1, 2, 3):
				raise CDMLAtomPropertiesPatchError(
					"atom properties multiplicity must be an int from 1 to 3",
				)
		elif field_name in ("show", "show_hydrogens"):
			if type(value) is not bool:
				raise CDMLAtomPropertiesPatchError("atom properties %s must be a bool" % field_name)
		elif field_name == "font_size":
			if type(value) is not int or not 4 <= value <= 72:
				raise CDMLAtomPropertiesPatchError(
					"atom properties font_size must be an int from 4 to 72",
				)
		else:
			if type(value) is not str or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
				raise CDMLAtomPropertiesPatchError(
					"atom properties line_color must be a six-digit hex color",
				)
			value = value.lower()
		validated.append((field_name, value))
	return request.molecule_id, request.atom_id, tuple(validated)


#============================================
def _validate_atom_translate_request(
		request: object,
		) -> tuple[tuple[tuple[str, str], ...], tuple[float, float]]:
	"""Validate one immutable direct-atom translation before candidate mutation."""
	if type(request) is not CDMLAtomTranslateRequest:
		raise CDMLValidationError("atom translation requires an atom translation request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("atom translation expected_revision must be an int")
	if not isinstance(request.targets, tuple) or not request.targets:
		raise CDMLValidationError("atom translation targets must be a nonempty immutable tuple")
	if any(
			not isinstance(target, tuple) or len(target) != 2
			or any(not isinstance(identifier, str) or not identifier for identifier in target)
			for target in request.targets
		):
		raise CDMLValidationError("atom translation targets must contain nonempty ID pairs")
	if len(set(request.targets)) != len(request.targets):
		raise CDMLValidationError("atom translation targets must be unique")
	delta_cm = _validate_insertion_translation(request.delta)
	return request.targets, delta_cm


#============================================
def _validate_atom_rotate_request(
		request: object,
		) -> tuple[tuple[tuple[str, str], ...], tuple[float, float], float]:
	"""Validate one immutable direct-atom rotation before candidate mutation."""
	if type(request) is not CDMLAtomRotateRequest:
		raise CDMLValidationError("atom rotation requires an atom rotation request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("atom rotation expected_revision must be an int")
	if type(request.targets) is not tuple or not request.targets:
		raise CDMLValidationError("atom rotation targets must be a nonempty immutable tuple")
	if any(
			type(target) is not tuple or len(target) != 2
			or any(type(identifier) is not str or not identifier for identifier in target)
			for target in request.targets
		):
		raise CDMLValidationError("atom rotation targets must contain nonempty ID pairs")
	if len(set(request.targets)) != len(request.targets):
		raise CDMLValidationError("atom rotation targets must be unique")
	center_cm = _validate_insertion_translation(request.center)
	if type(request.angle_radians) not in (int, float):
		raise CDMLValidationError("atom rotation angle must be a finite plain numeric value")
	try:
		angle = float(request.angle_radians)
	except OverflowError as error:
		raise CDMLValidationError("atom rotation angle must be a finite plain numeric value") from error
	if not math.isfinite(angle):
		raise CDMLValidationError("atom rotation angle must be a finite plain numeric value")
	return request.targets, center_cm, angle


#============================================
def _validate_bond_order_edit_request(request: object) -> tuple[str, str, int]:
	"""Validate one exact direct-core bond-order request before mutation."""
	if type(request) is not CDMLBondOrderEditRequest:
		raise CDMLValidationError("bond order edit requires a bond order edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("bond order edit expected_revision must be an int")
	for name, value in (("molecule_id", request.molecule_id), ("bond_id", request.bond_id)):
		if not isinstance(value, str) or not value:
			raise CDMLValidationError("bond order edit %s must be a nonempty string" % name)
	if type(request.order) is not int or request.order not in (1, 2, 3):
		raise CDMLValidationError("bond order edit order must be 1, 2, or 3")
	return request.molecule_id, request.bond_id, request.order


#============================================
def _validate_bond_type_edit_request(request: object) -> tuple[str, str, str]:
	"""Validate one exact direct-core ordinary bond-type request."""
	if type(request) is not CDMLBondTypeEditRequest:
		raise CDMLValidationError("bond type edit requires a bond type edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("bond type edit expected_revision must be an int")
	for name, value in (("molecule_id", request.molecule_id), ("bond_id", request.bond_id)):
		if not isinstance(value, str) or not value:
			raise CDMLValidationError("bond type edit %s must be a nonempty string" % name)
	if request.bond_type not in ("n", "w", "h", "a", "b", "d", "o", "s"):
		raise CDMLValidationError("bond type edit requested type must be an ordinary type character")
	return request.molecule_id, request.bond_id, request.bond_type


#============================================
def _bond_patch_number(value: object, field_name: str, minimum: float, maximum: float) -> float:
	"""Validate one finite authored depiction number within its CDML range."""
	if type(value) not in (int, float) or not math.isfinite(value):
		raise CDMLBondPropertiesPatchError(
			"bond properties %s must be a finite number" % field_name,
		)
	number = float(value)
	if not minimum <= number <= maximum:
		raise CDMLBondPropertiesPatchError(
			"bond properties %s is outside its supported range" % field_name,
		)
	return number


#============================================
def _bond_patch_color(value: object) -> str:
	"""Validate and normalize one frontend-neutral six-digit CDML color."""
	if not isinstance(value, str) or re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
		raise CDMLBondPropertiesPatchError(
			"bond properties color must be a six-digit hex color",
		)
	return value.lower()


#============================================
def _validate_bond_properties_patch(
		request: object,
		) -> tuple[str, str, tuple[tuple[str, object], ...]]:
	"""Validate immutable explicit intent before reading or mutating a target."""
	if type(request) is not CDMLBondPropertiesPatch:
		raise CDMLBondPropertiesPatchError(
			"bond properties requires a bond properties patch",
		)
	if type(request.expected_revision) is not int:
		raise CDMLBondPropertiesPatchError(
			"bond properties expected_revision must be an int",
		)
	for name, value in (("molecule_id", request.molecule_id), ("bond_id", request.bond_id)):
		if not isinstance(value, str) or not value:
			raise CDMLBondPropertiesPatchError(
				"bond properties %s must be a nonempty string" % name,
			)
	if type(request.changes) is not tuple:
		raise CDMLBondPropertiesPatchError("bond properties changes must be an immutable tuple")
	validated = []
	seen = set()
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLBondPropertiesPatchError("bond properties changes must be field/value pairs")
		field_name, value = change
		if not isinstance(field_name, str) or field_name not in (
				"order", "type", "center", "line_width", "bond_width",
				"wedge_width", "color",
				):
			raise CDMLBondPropertiesPatchError(
				"bond properties field must be a supported string",
			)
		if field_name in seen:
			raise CDMLBondPropertiesPatchError("bond properties fields must be unique")
		seen.add(field_name)
		if field_name == "order":
			if type(value) is not int or value not in (1, 2, 3):
				raise CDMLBondPropertiesPatchError("bond properties order must be 1, 2, or 3")
		elif field_name == "type":
			if type(value) is not str or value not in ("n", "w", "h", "a", "b", "d", "o", "s"):
				raise CDMLBondPropertiesPatchError(
					"bond properties type must be an ordinary type character",
				)
		elif field_name == "center":
			if type(value) is not bool:
				raise CDMLBondPropertiesPatchError("bond properties center must be a bool")
		elif field_name == "line_width":
			value = _bond_patch_number(value, field_name, 0.1, 20.0)
		elif field_name in ("bond_width", "wedge_width"):
			value = _bond_patch_number(value, field_name, 0.1, 40.0)
		elif field_name == "color":
			value = _bond_patch_color(value)
		validated.append((field_name, value))
	return request.molecule_id, request.bond_id, tuple(validated)


#============================================
def _editable_bond_type(value: str) -> tuple[str, int]:
	"""Return an exact supported CDML bond spelling for the order-edit boundary."""
	if not isinstance(value, str) or len(value) != 2:
		raise CDMLValidationError("bond order edit target has no supported bond type")
	type_char, order_text = value
	if type_char not in oasa.bond_semantics.BOND_TYPES or order_text not in ("1", "2", "3"):
		raise CDMLValidationError("bond order edit target has an ambiguous bond type")
	order = int(order_text)
	if not oasa.bond_semantics.is_authored_bond_order(type_char, order):
		raise CDMLValidationError("bond order edit target has an unsupported bond type/order")
	return type_char, order


#============================================
def _editable_bond_type_for_type_edit(value: str) -> tuple[str, int]:
	"""Return the exact current spelling accepted by the type-edit boundary."""
	if not isinstance(value, str) or len(value) != 2:
		raise CDMLValidationError("bond type edit target has no supported bond type")
	type_char, order_text = value
	if order_text not in ("1", "2", "3"):
		raise CDMLValidationError("bond type edit target has an ambiguous bond type")
	order = int(order_text)
	if type_char in ("l", "r"):
		if order != 1:
			raise CDMLValidationError("bond type edit target has an unsupported bond type/order")
		return type_char, order
	if type_char == "q":
		if order != 1:
			raise CDMLValidationError("bond type edit target has an unsupported bond type/order")
		return type_char, order
	if type_char not in ("n", "w", "h", "a", "b", "d", "o", "s"):
		raise CDMLValidationError("bond type edit target has an ambiguous bond type")
	if not oasa.bond_semantics.is_authored_bond_order(type_char, order):
		raise CDMLValidationError("bond type edit target has an unsupported bond type/order")
	return type_char, order


#============================================
def _validate_atom_number_request(
		request: object,
		) -> tuple[str, str, int | None, bool | None]:
	"""Validate one plain direct-atom number request before candidate work."""
	if type(request) is not CDMLAtomNumberEditRequest:
		raise CDMLValidationError("atom number edit requires an atom number edit request")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("atom number edit expected_revision must be an int")
	if not isinstance(request.molecule_id, str) or not request.molecule_id:
		raise CDMLValidationError("atom number edit molecule_id must be a nonempty string")
	if not isinstance(request.atom_id, str) or not request.atom_id:
		raise CDMLValidationError("atom number edit atom_id must be a nonempty string")
	if request.number is None and request.show_number is None:
		return request.molecule_id, request.atom_id, None, None
	if type(request.number) is not int or request.number <= 0 or type(request.show_number) is not bool:
		raise CDMLValidationError(
			"atom number edit requires a positive integer number and boolean visibility",
		)
	return request.molecule_id, request.atom_id, request.number, request.show_number


#============================================
def _validate_molecule_smiles_query(request: object) -> str:
	"""Validate one exact immutable molecule-SMILES query grammar."""
	if type(request) is not CDMLMoleculeSmilesQuery:
		raise CDMLValidationError("molecule SMILES query requires a molecule SMILES query")
	if type(request.expected_revision) is not int:
		raise CDMLValidationError("molecule SMILES query expected_revision must be an int")
	if not isinstance(request.molecule_id, str) or not request.molecule_id:
		raise CDMLValidationError("molecule SMILES query molecule_id must be a nonempty string")
	return request.molecule_id


#============================================
def _validate_molecule_name_request(request: object) -> tuple[str, str]:
	"""Validate one exact direct-root molecule display-name request."""
	if type(request) is not CDMLMoleculeNameEditRequest:
		raise CDMLMoleculeNameEditError("molecule name edit requires a molecule name edit request")
	if type(request.expected_revision) is not int:
		raise CDMLMoleculeNameEditError("molecule name edit expected_revision must be an int")
	if not isinstance(request.molecule_id, str) or not request.molecule_id:
		raise CDMLMoleculeNameEditError("molecule name edit molecule_id must be a nonempty string")
	if not isinstance(request.name, str):
		raise CDMLMoleculeNameEditError("molecule name edit name must be a string")
	return request.molecule_id, request.name


#============================================
def _validate_paper_properties_patch(request: object) -> dict[str, object]:
	"""Validate one explicit-field paper patch before candidate mutation."""
	if type(request) is not CDMLPaperPropertiesPatch:
		raise CDMLPaperPropertiesError(
			"paper properties require a paper properties patch request",
		)
	if type(request.expected_revision) is not int:
		raise CDMLPaperPropertiesError(
			"paper properties expected_revision must be an int",
		)
	if type(request.changes) is not tuple:
		raise CDMLPaperPropertiesError("paper properties changes must be a tuple")
	changes = {}
	for change in request.changes:
		if type(change) is not tuple or len(change) != 2:
			raise CDMLPaperPropertiesError(
				"paper properties changes must contain exact field/value pairs",
			)
		name, value = change
		if type(name) is not str or name not in _CDML_PAPER_PROPERTY_FIELDS:
			raise CDMLPaperPropertiesError("paper properties field is unsupported")
		if name in changes:
			raise CDMLPaperPropertiesError(
				f"paper properties field is repeated: {name}",
			)
		changes[name] = value
	if "type" in changes:
		paper_type = changes["type"]
		if type(paper_type) is not str or paper_type not in _CDML_PAPER_SIZES_MM:
			raise CDMLPaperPropertiesError("paper properties type is unsupported")
	if "orientation" in changes:
		orientation = changes["orientation"]
		if type(orientation) is not str or orientation not in ("portrait", "landscape"):
			raise CDMLPaperPropertiesError(
				"paper properties orientation must be portrait or landscape",
			)
	for name in ("crop_svg", "use_real_minus", "replace_minus"):
		if name in changes and type(changes[name]) is not bool:
			raise CDMLPaperPropertiesError(
				f"paper properties {name} must be a bool",
			)
	if "crop_margin" in changes:
		margin = changes["crop_margin"]
		if type(margin) is not int or margin < 0:
			raise CDMLPaperPropertiesError(
				"paper properties crop_margin must be a nonnegative int",
			)
	if "dimensions" in changes:
		dimensions = changes["dimensions"]
		if type(dimensions) is not tuple or len(dimensions) != 2:
			raise CDMLPaperPropertiesError(
				"paper properties dimensions must be an exact two-value tuple",
			)
		for dimension in dimensions:
			if type(dimension) not in (int, float) or not math.isfinite(dimension) or dimension <= 0:
				raise CDMLPaperPropertiesError(
					"paper properties dimensions must be finite positive plain numbers",
				)
		changes["dimensions"] = (float(dimensions[0]), float(dimensions[1]))
	if changes.get("type") == "custom" and "dimensions" not in changes:
		raise CDMLPaperPropertiesError(
			"paper properties custom type requires dimensions",
		)
	if "type" in changes and changes["type"] != "custom" and "dimensions" in changes:
		raise CDMLPaperPropertiesError(
			"paper properties dimensions apply only to custom paper",
		)
	return changes


#============================================
def _candidate_durable_ids(candidate: "CDMLDocument") -> set[str]:
	"""Return every current durable identifier, including opaque reservations."""
	used_ids = set()
	for element in _descendant_elements(candidate._dom_document.documentElement):
		if not _is_id_definition(element):
			continue
		identifier = element.getAttribute("id")
		if identifier:
			used_ids.add(identifier)
	return used_ids


#============================================
def _molecule_atom_ids(molecule: object) -> set[str]:
	"""Return direct editable atom IDs in one direct-root molecule."""
	return {
		atom.getAttribute("id")
		for atom in _element_children(molecule)
		if _is_cdml_element(atom) and _local_name(atom) == "atom" and atom.getAttribute("id")
	}


#============================================
def _require_editable_bond_endpoints(molecule: object, bond: object) -> tuple[str, str]:
	"""Require a direct bond to connect two direct atoms in the same molecule."""
	start = bond.getAttribute("start")
	end = bond.getAttribute("end")
	atom_ids = _molecule_atom_ids(molecule)
	if not start or not end or start == end or start not in atom_ids or end not in atom_ids:
		raise CDMLValidationError("structural edit bond has invalid direct-molecule endpoints")
	return start, end


#============================================
def _has_direct_bond(molecule: object, first_atom_id: str, second_atom_id: str) -> bool:
	"""Return whether a direct editable molecule already has the undirected edge."""
	requested = frozenset((first_atom_id, second_atom_id))
	for bond in _element_children(molecule):
		if not _is_cdml_element(bond) or _local_name(bond) != "bond":
			continue
		start = bond.getAttribute("start")
		end = bond.getAttribute("end")
		if frozenset((start, end)) != requested:
			continue
		if start in _molecule_atom_ids(molecule) and end in _molecule_atom_ids(molecule):
			return True
	return False


#============================================
class CDMLDocument:
	"""A complete, DOM-backed CDML document with ordered opaque preservation."""

	#============================================
	def __init__(self, dom_document: object) -> None:
		"""Store a validated detached XML DOM owned solely by this document."""
		self._dom_document = dom_document

	#============================================
	@classmethod
	def parse(cls, text: str, *, validation: str = "compat") -> "CDMLDocument":
		"""Parse complete CDML text and optionally apply strict backend checks."""
		try:
			source = text.encode("utf-8")
			dom_document = oasa.cdml_xml.parse_cdml_dom(source)
		except (UnicodeError, oasa.cdml_xml.CDMLXMLParseError) as error:
			raise CDMLParseError(f"CDML XML parse failed: {error}") from error
		root = dom_document.documentElement
		if root is None or not _is_cdml_element(root) or _local_name(root) != "cdml":
			raise CDMLParseError("CDML root element must be <cdml>")
		document = cls(dom_document)
		if validation == "strict":
			document.validate(validation="strict")
		elif validation != "compat":
			raise CDMLValidationError(f"unknown CDML validation mode: {validation}")
		return document

	#============================================
	def serialize(self, *, mode: str = "preserve") -> str:
		"""Return backend-owned complete CDML without ID allocation or reordering."""
		if mode != "preserve":
			raise CDMLValidationError(f"unknown CDML serialization mode: {mode}")
		text = self._dom_document.toxml(encoding="utf-8").decode("utf-8")
		return text

	#============================================
	def objects(self) -> tuple[CDMLObjectRecord, ...]:
		"""Return direct document-child records in document order.

		The ``position`` and ``path`` metadata use full-document preorder so they
		remain comparable with the broader definition lookup in ``find_by_id``.
		"""
		records = []
		root = self._dom_document.documentElement
		for position, element in _element_locations(self._dom_document.documentElement):
			if element.parentNode is root:
				records.append(_record_for_element(position, element))
		return tuple(records)

	#============================================
	def find_by_id(self, identifier: str) -> CDMLObjectRecord | None:
		"""Find a declaration ID anywhere in the document by stable preorder.

		Unlike ``objects()``, this broader lookup includes known nested durable
		definitions such as atoms and bonds; fragment member references are never
		considered definitions.
		"""
		for position, element in _element_locations(self._dom_document.documentElement):
			if not _is_id_definition(element):
				continue
			if element.getAttribute("id") != identifier:
				continue
			record = _record_for_element(position, element)
			return record
		return None

	#============================================
	def reaction_roles(self) -> tuple[CDMLReactionRoleRecord, ...]:
		"""Return recognized role references from core direct-child reactions.

		The records expose persistent reaction semantics without giving callers
		mutable DOM nodes. Compatibility validation remains responsible for
		reference resolution; profile validators can apply narrower authored
		semantics to these immutable records.
		"""
		records = []
		root = self._dom_document.documentElement
		for reaction in _element_children(root):
			if not _is_cdml_element(reaction) or _local_name(reaction) != "reaction":
				continue
			for child in _element_children(reaction):
				if not _is_cdml_element(child):
					continue
				role_name = _local_name(child)
				if role_name not in _REACTION_ROLE_NAMES:
					continue
				target_identifier = child.getAttribute("idref") or None
				records.append(CDMLReactionRoleRecord(
					reaction_path=_node_path(reaction),
					path=_node_path(child),
					role_name=role_name,
					target_identifier=target_identifier,
				))
		return tuple(records)

	#============================================
	def validation_issues(self, *, validation: str = "strict") -> tuple[CDMLIssue, ...]:
		"""Return durable-ID and known-reference findings without changing this document.

		The public issue value lets pure conformance clients share the backend's
		strict identity/reference rules without duplicating session behavior.  It
		deliberately does not allocate identifiers, normalize XML, or inspect
		opaque extension content beyond its literal document-wide ``id`` value.
		"""
		if validation == "compat":
			return ()
		if validation != "strict":
			raise CDMLValidationError(f"unknown CDML validation mode: {validation}")
		issues = []
		seen_ids = {}
		elements = _descendant_elements(self._dom_document.documentElement)
		for element in elements:
			if not _is_id_definition(element):
				continue
			identifier = element.getAttribute("id")
			if not identifier:
				continue
			if _is_id_declaration(element) and _has_provisional_id_prefix(identifier):
				code = "provisional_id" if _is_provisional_id(identifier) else "malformed_provisional_id"
				message = "provisional IDs are valid only during commit"
				issues.append(CDMLIssue(
					code, message, _node_path(element),
				))
			elif identifier in seen_ids:
				issues.append(CDMLIssue(
					"duplicate_id", f"duplicate CDML id: {identifier}", _node_path(element),
				))
			else:
				seen_ids[identifier] = element
		for element in elements:
			for attribute_name in _known_reference_attributes(element):
				reference = element.getAttribute(attribute_name)
				if not reference:
					continue
				if _has_provisional_id_prefix(reference):
					code = "provisional_reference" if _is_provisional_id(reference) else "malformed_provisional_reference"
					issues.append(CDMLIssue(
						code, "provisional reference escaped commit", _node_path(element),
					))
				elif reference not in seen_ids:
					issues.append(CDMLIssue(
						"unresolved_reference",
						f"unresolved {attribute_name} reference: {reference}", _node_path(element),
					))
			if _fragment_member_reference(element):
				reference = element.getAttribute("id")
				if _has_provisional_id_prefix(reference):
					code = "provisional_reference" if _is_provisional_id(reference) else "malformed_provisional_reference"
					issues.append(CDMLIssue(
						code, "provisional reference escaped commit", _node_path(element),
					))
				elif reference and reference not in seen_ids:
					issues.append(CDMLIssue(
						"unresolved_fragment_member",
						f"unresolved fragment member: {reference}", _node_path(element),
					))
		return tuple(issues)

	#============================================
	def validate(self, *, validation: str = "strict") -> tuple[CDMLIssue, ...]:
		"""Raise for strict findings while preserving the established API behavior."""
		issues = self.validation_issues(validation=validation)
		if issues:
			messages = "; ".join(issue.message for issue in issues)
			raise CDMLValidationError(messages)
		return issues

	#============================================
	def _commit_candidate_ids(self) -> dict[str, str]:
		"""Replace valid transaction-only IDs and known refs in this detached DOM."""
		elements = _descendant_elements(self._dom_document.documentElement)
		used_ids = set()
		seen_source_ids = set()
		provisional_nodes = []
		for element in elements:
			if not _is_id_definition(element):
				continue
			identifier = element.getAttribute("id")
			if not identifier:
				continue
			if identifier in seen_source_ids:
				raise CDMLValidationError(f"duplicate CDML id: {identifier}")
			seen_source_ids.add(identifier)
			if _is_id_declaration(element) and _has_provisional_id_prefix(identifier):
				if not _is_provisional_id(identifier):
					raise CDMLValidationError(f"malformed provisional CDML id: {identifier}")
				provisional_nodes.append((identifier, element))
			else:
				used_ids.add(identifier)
		id_map = {}
		for token, element in provisional_nodes:
			if token in id_map:
				raise CDMLValidationError(f"duplicate provisional CDML id: {token}")
			assigned_id = _next_durable_id(_local_name(element), used_ids)
			used_ids.add(assigned_id)
			id_map[token] = assigned_id
		for token, element in provisional_nodes:
			element.setAttribute("id", id_map[token])
		for element in elements:
			for attribute_name in _known_reference_attributes(element):
				reference = element.getAttribute(attribute_name)
				if not _has_provisional_id_prefix(reference):
					continue
				if not _is_provisional_id(reference):
					raise CDMLValidationError(
						f"malformed provisional {attribute_name} reference: {reference}",
					)
				if reference not in id_map:
					raise CDMLValidationError(
					f"dangling provisional {attribute_name} reference: {reference}",
				)
				element.setAttribute(attribute_name, id_map[reference])
			if _fragment_member_reference(element):
				reference = element.getAttribute("id")
				if not _has_provisional_id_prefix(reference):
					continue
				if not _is_provisional_id(reference):
					raise CDMLValidationError(
						f"malformed provisional fragment member: {reference}",
					)
				if reference not in id_map:
					raise CDMLValidationError(
						f"dangling provisional fragment member: {reference}",
					)
				element.setAttribute("id", id_map[reference])
		return id_map


#============================================
class CDMLDocumentSession:
	"""Revisioned backend owner for atomic complete-document CDML commits."""

	#============================================
	def __init__(self, document: CDMLDocument, history_capacity: int) -> None:
		"""Create a clean revision-zero backend session from one accepted document."""
		if history_capacity < 3:
			raise CDMLValidationError("history_capacity must be at least three")
		# Reparse into session-owned DOM state so caller-held documents cannot
		# mutate the accepted revision outside an atomic transaction.
		detached_document = CDMLDocument.parse(document.serialize(), validation="strict")
		self._history_capacity = history_capacity
		self._revision = 0
		self._document = detached_document
		self._saved_revision = 0
		self._saved_cdml = detached_document.serialize()
		self._saved_digest = _content_digest(self._saved_cdml)
		self._history = {0: detached_document}
		# Correlation tokens belong to this backend document session.  They are
		# consumed only after a commit has become authoritative, never by a
		# detached candidate that is later rejected.
		self._consumed_provisional_tokens: set[str] = set()
		# A restore behaves like an undo navigation step.  Keep the revision that
		# was current immediately before that step available for one redo.
		self._redo_revision: int | None = None

	#============================================
	@classmethod
	def load(cls, text: str, *, history_capacity: int = 20) -> "CDMLDocumentSession":
		"""Load a strict, clean revision-zero complete CDML backend document."""
		document = CDMLDocument.parse(text, validation="strict")
		return cls(document, history_capacity)

	#============================================
	@classmethod
	def load_imported(
			cls, text: str, *, history_capacity: int = 20,
			) -> "CDMLDocumentSession":
		"""Stage strict imported CDML against the empty-document saved baseline.

		An external chemistry file has not yet been published as native CDML.
		Its canonical document is therefore authoritative immediately but dirty
		until ordinary Save publishes that exact snapshot.
		"""
		document = CDMLDocument.parse(text, validation="strict")
		session = cls(document, history_capacity)
		empty_document = CDMLDocument.parse(_EMPTY_CDML, validation="strict")
		session._saved_cdml = empty_document.serialize()
		session._saved_digest = _content_digest(session._saved_cdml)
		return session

	#============================================
	@property
	def revision(self) -> int:
		"""Return the current backend revision number."""
		return self._revision

	#============================================
	@property
	def is_dirty(self) -> bool:
		"""Return content-based dirty state relative to the saved backend baseline."""
		current_cdml = self._document.serialize()
		return _content_digest(current_cdml) != self._saved_digest

	#============================================
	def snapshot(self) -> CDMLSnapshot:
		"""Return an immutable view of the current authoritative backend state."""
		cdml = self._document.serialize()
		return CDMLSnapshot(
			revision=self._revision,
			cdml=cdml,
			is_dirty=self.is_dirty,
		)

	#============================================
	def paper_catalog(self) -> dict[str, list[float] | None]:
		"""Return the backend-owned plain-data catalog for a document client.

		The catalog is document-format policy rather than frontend presentation
		state.  Returning a fresh value keeps callers from retaining mutable
		backend-owned catalog data between operations.
		"""
		return paper_catalog()

	#============================================
	def paper_properties_context(self) -> dict[str, object]:
		"""Return fresh plain data for one paper-properties client view.

		The backend identifies the editable first direct core ``paper`` record
		and calculates the effective creation defaults.  A frontend uses this
		observation to display an absent paper consistently with a later patch;
		it must not infer a separate UI default from its own document projection.
		"""
		paper = _first_direct_core_child(self._document, "paper")
		default_type, default_orientation = _new_paper_defaults(self._document)
		return {
			"paper_present": paper is not None,
			"attributes": (
				{} if paper is None else {
					paper.attributes.item(index).name: paper.attributes.item(index).value
					for index in range(paper.attributes.length)
				}
			),
			"default_type": default_type,
			"default_orientation": default_orientation,
		}

	#============================================
	def commit(self, *, expected_revision: int, complete_cdml: str) -> CDMLCommit:
		"""Atomically accept a detached complete-CDML candidate at one revision."""
		self._check_expected_revision(expected_revision)
		candidate = CDMLDocument.parse(complete_cdml, validation="compat")
		id_map = candidate._commit_candidate_ids()
		candidate.validate(validation="strict")
		reused_tokens = set(id_map).intersection(self._consumed_provisional_tokens)
		if reused_tokens:
			reused_token = sorted(reused_tokens)[0]
			raise CDMLValidationError(
				f"provisional correlation token already consumed: {reused_token}",
			)
		# A new accepted edit starts a different history branch, so it clears the
		# one-step redo protection.  Validation above must finish first so failed
		# candidates leave the session state, including redo, untouched.
		commit = self._accept_document(candidate, id_map, redo_revision=None)
		self._consumed_provisional_tokens.update(id_map)
		return commit

	#============================================
	def insert_molecules(self, request: CDMLMoleculeInsertionRequest) -> CDMLCommit:
		"""Append a detached molecule-only proposal through the complete commit path.

		The optional request label is operation metadata only.  It never enters the
		persistent CDML candidate and does not affect validation or ID allocation.
		"""
		if request.label is not None and not isinstance(request.label, str):
			raise CDMLValidationError("molecule insertion label must be a string or None")
		self._check_expected_revision(request.expected_revision)
		proposal = CDMLDocument.parse(request.proposal_cdml, validation="compat")
		molecules = _proposal_molecules(proposal)
		candidate = CDMLDocument.parse(self.snapshot().cdml, validation="compat")
		candidate_root = candidate._dom_document.documentElement
		proposal_root = proposal._dom_document.documentElement
		for molecule in molecules:
			imported_molecule = candidate._dom_document.importNode(molecule, deep=True)
			_copy_proposal_namespace_declarations(proposal_root, imported_molecule)
			candidate_root.appendChild(imported_molecule)
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def insert_top_level(self, request: CDMLTopLevelInsertionRequest) -> CDMLCommit:
		"""Append an allowlisted, translated fragment through one normal commit.

		The fragment is a complete untrusted CDML document.  Its IDs are source
		labels only: this method creates fresh private provisional IDs in detached
		state, so a pasted reference can never accidentally bind the destination.
		Translation is expressed in CDML/PostScript scene points.
		"""
		if type(request.expected_revision) is not int:
			raise CDMLValidationError("top-level insertion expected_revision must be an int")
		if request.label is not None and not isinstance(request.label, str):
			raise CDMLValidationError("top-level insertion label must be a string or None")
		if not isinstance(request.fragment_cdml, str):
			raise CDMLValidationError("top-level insertion fragment_cdml must be a string")
		dx, dy = _validate_insertion_translation(request.translation)
		# Reject obsolete requests before parsing or building detached work.
		self._check_expected_revision(request.expected_revision)
		fragment = CDMLDocument.parse(request.fragment_cdml, validation="compat")
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		roots = _prepare_top_level_fragment(
			fragment,
			candidate.serialize(),
			self._consumed_provisional_tokens,
			dx,
			dy,
		)
		candidate_root = candidate._dom_document.documentElement
		fragment_root = fragment._dom_document.documentElement
		for root in roots:
			imported_root = candidate._dom_document.importNode(root, deep=True)
			_copy_proposal_namespace_declarations(fragment_root, imported_root)
			candidate_root.appendChild(imported_root)
		# ``commit`` repeats the revision check immediately before its final
		# acceptance path, retaining the ordinary optimistic-transaction contract.
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def edit_structure(self, request: CDMLStructuralEditRequest) -> CDMLStructuralEditResult:
		"""Accept one narrow Draw-mode structural operation atomically.

		The operation acts on a detached copy of the authoritative complete CDML
		document.  It neither receives nor returns frontend objects, and all
		created IDs are allocated by OASA before the ordinary commit path accepts
		the validated candidate.
		"""
		validated = _validate_structural_request(request)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		used_ids = _candidate_durable_ids(candidate)
		kind = validated[0]
		created_molecule_id = None
		created_atom_ids: tuple[str, ...] = ()
		created_bond_ids: tuple[str, ...] = ()
		updated_bond_ids: tuple[str, ...] = ()
		if kind == "create-bonded-pair":
			(_kind, source_position, target_position, element, bond_type, bond_order, simple_double) = validated
			root = candidate._dom_document.documentElement
			created_molecule_id = _next_durable_id("molecule", used_ids)
			used_ids.add(created_molecule_id)
			first_atom_id = _next_durable_id("atom", used_ids)
			used_ids.add(first_atom_id)
			second_atom_id = _next_durable_id("atom", used_ids)
			used_ids.add(second_atom_id)
			bond_id = _next_durable_id("bond", used_ids)
			molecule = _new_core_element(candidate, root, "molecule")
			molecule.setAttribute("id", created_molecule_id)
			root.appendChild(molecule)
			_append_atom(candidate, molecule, first_atom_id, element, source_position)
			_append_atom(candidate, molecule, second_atom_id, element, target_position)
			_append_bond(
				candidate, molecule, bond_id, first_atom_id, second_atom_id,
				bond_type, bond_order, simple_double,
			)
			created_atom_ids = (first_atom_id, second_atom_id)
			created_bond_ids = (bond_id,)
		elif kind == "extend-atom":
			(_kind, molecule_id, source_atom_id, target_position, element, bond_type, bond_order, simple_double) = validated
			molecule = _direct_root_molecule(candidate, molecule_id)
			_direct_molecule_atom(molecule, source_atom_id)
			new_atom_id = _next_durable_id("atom", used_ids)
			used_ids.add(new_atom_id)
			bond_id = _next_durable_id("bond", used_ids)
			_append_atom(candidate, molecule, new_atom_id, element, target_position)
			_append_bond(
				candidate, molecule, bond_id, source_atom_id, new_atom_id,
				bond_type, bond_order, simple_double,
			)
			created_atom_ids = (new_atom_id,)
			created_bond_ids = (bond_id,)
		elif kind == "join-atoms":
			(_kind, molecule_id, source_atom_id, target_atom_id, bond_type, bond_order, simple_double) = validated
			molecule = _direct_root_molecule(candidate, molecule_id)
			_direct_molecule_atom(molecule, source_atom_id)
			_direct_molecule_atom(molecule, target_atom_id)
			if source_atom_id == target_atom_id:
				raise CDMLValidationError("join-atoms requires two distinct atoms")
			if _has_direct_bond(molecule, source_atom_id, target_atom_id):
				raise CDMLValidationError("join-atoms rejects a duplicate direct-molecule bond")
			bond_id = _next_durable_id("bond", used_ids)
			_append_bond(
				candidate, molecule, bond_id, source_atom_id, target_atom_id,
				bond_type, bond_order, simple_double,
			)
			created_bond_ids = (bond_id,)
		else:
			(_kind, molecule_id, bond_id, bond_type, bond_order, simple_double) = validated
			molecule = _direct_root_molecule(candidate, molecule_id)
			bond = _direct_molecule_bond(molecule, bond_id)
			_require_editable_bond_endpoints(molecule, bond)
			_apply_bond_tool_transition(bond, bond_type, bond_order, simple_double)
			updated_bond_ids = (bond_id,)
		candidate.validate(validation="strict")
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLStructuralEditResult(
			commit=commit,
			created_molecule_id=created_molecule_id,
			created_atom_ids=created_atom_ids,
			created_bond_ids=created_bond_ids,
			updated_bond_ids=updated_bond_ids,
		)

	#============================================
	def set_atom_element(self, request: CDMLAtomElementEditRequest) -> CDMLCommit:
		"""Atomically replace one direct core atom name in complete CDML.

		The operation intentionally preserves every other atom field and every
		unrelated document record.  Valence, bond, charge, and presentation
		changes require separately specified backend operations.
		"""
		molecule_id, atom_id, element = _validate_atom_element_request(request)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		molecule = _direct_root_molecule(candidate, molecule_id)
		atom = _direct_molecule_atom(molecule, atom_id)
		current_element = atom.getAttribute("name")
		if current_element not in oasa.periodic_table.periodic_table:
			raise CDMLValidationError("atom element edit target has an unsupported atom symbol")
		if element == current_element:
			raise CDMLValidationError("atom element edit replacement must differ from the current symbol")
		atom.setAttribute("name", element)
		candidate.validate(validation="strict")
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def patch_atom_properties(
			self, request: CDMLAtomPropertiesPatch,
			) -> CDMLAtomPropertiesPatchResult:
		"""Apply one complete explicit atom-properties intent atomically.

		The patch changes only direct core atom fields and its direct core font.
		Every scalar is validated before the target or detached candidate changes.
		"""
		molecule_id, atom_id, changes = _validate_atom_properties_patch(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		atom = _direct_molecule_atom(molecule, atom_id)
		if atom.getAttribute("name") not in oasa.periodic_table.periodic_table:
			raise CDMLAtomPropertiesPatchError(
				"atom properties target has an unsupported atom symbol",
			)
		if not changes:
			return CDMLAtomPropertiesPatchResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		candidate_atom = _direct_molecule_atom(candidate_molecule, atom_id)
		change_map = dict(changes)
		for field_name, value in changes:
			if field_name == "element":
				candidate_atom.setAttribute("name", value)
			elif field_name == "charge":
				if value == 0:
					candidate_atom.removeAttribute("charge")
				else:
					candidate_atom.setAttribute("charge", str(value))
			elif field_name == "valency":
				candidate_atom.setAttribute("valency", str(value))
			elif field_name == "isotope":
				if value is None:
					candidate_atom.removeAttribute("isotope")
				else:
					candidate_atom.setAttribute("isotope", str(value))
			elif field_name == "multiplicity":
				if value == 1:
					candidate_atom.removeAttribute("multiplicity")
				else:
					candidate_atom.setAttribute("multiplicity", str(value))
			elif field_name == "show":
				candidate_atom.setAttribute("show", "yes" if value else "no")
			elif field_name == "show_hydrogens":
				candidate_atom.setAttribute("hydrogens", "on" if value else "off")
		if "font_size" in change_map or "line_color" in change_map:
			fonts = [
				child for child in _element_children(candidate_atom)
				if _is_cdml_element(child) and _local_name(child) == "font"
			]
			if len(fonts) > 1:
				raise CDMLAtomPropertiesPatchError(
					"atom properties target has multiple direct core fonts",
				)
			font = fonts[0] if fonts else _new_core_element(candidate, candidate_atom, "font")
			if "font_size" in change_map:
				font.setAttribute("size", str(change_map["font_size"]))
			if "line_color" in change_map:
				font.setAttribute("color", change_map["line_color"])
			if not fonts:
				candidate_atom.appendChild(font)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLAtomPropertiesPatchResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLAtomPropertiesPatchResult(commit.snapshot, True, commit)

	#============================================
	def set_atom_number(self, request: CDMLAtomNumberEditRequest) -> CDMLCommit:
		"""Atomically assign, replace, or clear one direct core atom number."""
		molecule_id, atom_id, number, show_number = _validate_atom_number_request(request)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		molecule = _direct_root_molecule(candidate, molecule_id)
		atom = _direct_molecule_atom(molecule, atom_id)
		for child in _element_children(atom):
			if (
					_is_cdml_element(child)
					and _local_name(child) == "mark"
					and child.getAttribute("type") == "atom_number"
				):
				raise CDMLAtomNumberCompatibilityError(
					"atom number edit target has a direct legacy atom_number mark",
				)
		if number is None:
			atom.removeAttribute("number")
			atom.removeAttribute("show_number")
		else:
			atom.setAttribute("number", str(number))
			atom.setAttribute("show_number", "yes" if show_number else "no")
		candidate.validate(validation="strict")
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def set_molecule_name(self, request: CDMLMoleculeNameEditRequest) -> CDMLCommit:
		"""Atomically replace or clear one direct-root molecule display name."""
		molecule_id, name = _validate_molecule_name_request(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		current_name = molecule.getAttribute("name") if molecule.hasAttribute("name") else ""
		if current_name == name:
			return CDMLCommit(self.snapshot(), types.MappingProxyType({}))
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		molecule = _direct_root_molecule(candidate, molecule_id)
		if name:
			molecule.setAttribute("name", name)
		else:
			molecule.removeAttribute("name")
		candidate.validate(validation="strict")
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def patch_paper_properties(self, request: CDMLPaperPropertiesPatch) -> CDMLCommit:
		"""Apply explicit paper-field intent through one detached CDML commit.

		Only the first direct core ``paper`` record is editable.  The operation
		never reconstructs that record, so unrecognized attributes, descendants,
		and later compatibility paper records retain their exact XML ownership.
		"""
		changes = _validate_paper_properties_patch(request)
		self._check_expected_revision(request.expected_revision)
		if not changes:
			return CDMLCommit(self.snapshot(), types.MappingProxyType({}))
		current_paper = _first_direct_core_child(self._document, "paper")
		if current_paper is None:
			current_type, _current_orientation = _new_paper_defaults(self._document)
		else:
			current_type = current_paper.getAttribute("type") if current_paper.hasAttribute("type") else ""
		effective_type = changes.get("type", current_type)
		if "dimensions" in changes and effective_type != "custom":
			raise CDMLPaperPropertiesError(
				"paper properties dimensions apply only to custom paper",
			)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		paper = _first_direct_core_child(candidate, "paper")
		if paper is None:
			root = candidate._dom_document.documentElement
			paper = _new_core_element(candidate, root, "paper")
			default_type, default_orientation = _new_paper_defaults(candidate)
			paper.setAttribute("type", default_type)
			paper.setAttribute("orientation", default_orientation)
			viewport = _first_direct_core_child(candidate, "viewport")
			if viewport is None:
				root.appendChild(paper)
			else:
				root.insertBefore(paper, viewport)
		if "type" in changes:
			paper.setAttribute("type", changes["type"])
		if "orientation" in changes:
			paper.setAttribute("orientation", changes["orientation"])
		for name in ("crop_svg", "use_real_minus", "replace_minus"):
			if name in changes:
				paper.setAttribute(name, "1" if changes[name] else "0")
		if "crop_margin" in changes:
			paper.setAttribute("crop_margin", str(changes["crop_margin"]))
		if effective_type == "custom":
			if "dimensions" in changes:
				dimensions = changes["dimensions"]
				paper.setAttribute("size_x", _paper_dimension_text(dimensions[0]))
				paper.setAttribute("size_y", _paper_dimension_text(dimensions[1]))
		elif "type" in changes:
			for name in ("size_x", "size_y"):
				if paper.hasAttribute(name):
					paper.removeAttribute(name)
		candidate.validate(validation="strict")
		if candidate.serialize() == self._document.serialize():
			return CDMLCommit(self.snapshot(), types.MappingProxyType({}))
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def query_molecule_smiles(
			self, request: CDMLMoleculeSmilesQuery,
			) -> CDMLMoleculeSmilesResult:
		"""Return canonical isomeric SMILES for one direct-root molecule.

		The query reads the current authoritative DOM in place. It does not build
		a candidate, serialize CDML, or affect revision, history, or the saved
		canonical-content baseline.
		"""
		molecule_id = _validate_molecule_smiles_query(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		try:
			oasa_molecule = oasa.cdml_writer.read_direct_core_cdml_molecule_element(
				molecule,
			)
			if oasa_molecule is None:
				raise ValueError("CDML molecule has no supported chemistry conversion")
			smiles = oasa.codecs.rdkit_formats.depiction_stereo_smiles_mol_to_text(
				oasa_molecule,
			)
		except (
				AttributeError, IndexError, KeyError, RuntimeError,
				TypeError, ValueError,
			) as error:
			raise CDMLMoleculeSmilesUnavailableError(
				f"molecule SMILES query is unavailable for direct-root molecule: {molecule_id}",
			) from error
		return CDMLMoleculeSmilesResult(self._revision, molecule_id, smiles)

	#============================================
	def delete_top_level(self, request: CDMLTopLevelDeleteRequest) -> CDMLCommit:
		"""Atomically remove selected durable core records from the root stack.

		The request is deliberately narrower than a generic XML deletion: it only
		addresses direct core-CDML records with durable IDs.  This preserves opaque
		extensions and leaves structural atom/bond editing to its separate grammar.
		"""
		if not isinstance(request, CDMLTopLevelDeleteRequest):
			raise CDMLValidationError("top-level deletion requires a deletion request")
		if type(request.expected_revision) is not int:
			raise CDMLValidationError("top-level deletion expected_revision must be an int")
		if request.label is not None and not isinstance(request.label, str):
			raise CDMLValidationError("top-level deletion label must be a string or None")
		if (
			not isinstance(request.root_ids, tuple)
			or not request.root_ids
			or any(not isinstance(identifier, str) or not identifier for identifier in request.root_ids)
			or len(set(request.root_ids)) != len(request.root_ids)
		):
			raise CDMLValidationError(
				"top-level deletion root_ids must be unique nonempty strings",
			)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		root = candidate._dom_document.documentElement
		eligible = {}
		for child in _element_children(root):
			if (
				_is_cdml_element(child)
				and _local_name(child) in _TOP_LEVEL_DELETE_NAMES
				and child.getAttribute("id")
			):
				eligible[child.getAttribute("id")] = child
		missing = [identifier for identifier in request.root_ids if identifier not in eligible]
		if missing:
			raise CDMLValidationError(
				"top-level deletion target is not a supported durable root: %s" % missing[0],
			)
		target_ids = frozenset(request.root_ids)
		for role in candidate.reaction_roles():
			if role.target_identifier in target_ids:
				raise CDMLValidationError(
					"top-level deletion target is referenced by reaction role: %s" % role.target_identifier,
				)
		for identifier in request.root_ids:
			root.removeChild(eligible[identifier])
		return self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)

	#============================================
	def repair_geometry(
			self, request: CDMLGeometryRepairRequest,
			) -> CDMLGeometryRepairResult:
		"""Run one supported geometry repair through the authoritative CDML path."""
		if not isinstance(request, CDMLGeometryRepairRequest):
			raise CDMLValidationError("geometry repair requires a geometry repair request")
		if type(request.expected_revision) is not int:
			raise CDMLValidationError("geometry repair expected_revision must be an int")
		if request.kind not in (
				"normalize-bond-lengths", "normalize-bond-angles", "clean-geometry",
				"snap-to-hex-grid",
				):
			raise CDMLValidationError("unsupported geometry repair kind: %s" % request.kind)
		if (
			not isinstance(request.molecule_ids, tuple)
			or not request.molecule_ids
			or any(not isinstance(identifier, str) or not identifier for identifier in request.molecule_ids)
			or len(set(request.molecule_ids)) != len(request.molecule_ids)
		):
			raise CDMLValidationError(
				"geometry repair molecule_ids must be unique nonempty strings",
			)
		if (
			isinstance(request.target_spacing_pt, bool)
			or not isinstance(request.target_spacing_pt, (int, float))
			or not math.isfinite(request.target_spacing_pt)
			or request.target_spacing_pt <= 0
		):
			raise CDMLValidationError(
				"geometry repair target_spacing_pt must be a finite positive number",
			)
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		try:
			import oasa.cdml_geometry_repair
			if request.kind == "normalize-bond-lengths":
				oasa.cdml_geometry_repair.normalize_bond_lengths_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
			elif request.kind == "normalize-bond-angles":
				oasa.cdml_geometry_repair.normalize_bond_angles_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
			elif request.kind == "clean-geometry":
				oasa.cdml_geometry_repair.clean_geometry_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
			else:
				oasa.cdml_geometry_repair.snap_to_hex_grid_in_document(
					candidate, request.molecule_ids, float(request.target_spacing_pt),
				)
		except ValueError as exc:
			raise CDMLValidationError(str(exc)) from exc
		candidate.validate(validation="strict")
		if candidate.serialize() == self._document.serialize():
			return CDMLGeometryRepairResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLGeometryRepairResult(commit.snapshot, True, commit)

	#============================================
	def align_atoms(self, request: CDMLAtomAlignRequest) -> CDMLAtomAlignResult:
		"""Align direct-root durable atoms on one authoritative coordinate axis."""
		if not isinstance(request, CDMLAtomAlignRequest):
			raise CDMLValidationError("atom alignment requires an atom alignment request")
		if type(request.expected_revision) is not int:
			raise CDMLValidationError("atom alignment expected_revision must be an int")
		if request.axis not in ("horizontal", "vertical"):
			raise CDMLValidationError("atom alignment axis must be horizontal or vertical")
		if not isinstance(request.targets, tuple) or not request.targets:
			raise CDMLValidationError("atom alignment targets must be a nonempty immutable tuple")
		if any(
				not isinstance(target, tuple) or len(target) != 2
				or any(not isinstance(identifier, str) or not identifier for identifier in target)
				for target in request.targets
			):
			raise CDMLValidationError("atom alignment targets must contain nonempty ID pairs")
		if len(set(request.targets)) != len(request.targets):
			raise CDMLValidationError("atom alignment targets must be unique")
		self._check_expected_revision(request.expected_revision)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		root = candidate._dom_document.documentElement
		molecules = {
			child.getAttribute("id"): child
			for child in _element_children(root)
			if _is_cdml_element(child) and _local_name(child) == "molecule" and child.getAttribute("id")
		}
		points = []
		for molecule_id, atom_id in request.targets:
			molecule = molecules.get(molecule_id)
			if molecule is None:
				raise CDMLValidationError(
					"atom alignment target is not a durable direct-root molecule: %s" % molecule_id,
				)
			atoms = {
				child.getAttribute("id"): child
				for child in _element_children(molecule)
				if _is_cdml_element(child) and _local_name(child) == "atom" and child.getAttribute("id")
			}
			atom = atoms.get(atom_id)
			if atom is None:
				raise CDMLValidationError(
					"atom alignment target is not a durable direct molecule atom: %s" % atom_id,
				)
			atom_points = [
				child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"
			]
			if len(atom_points) != 1:
				raise CDMLValidationError("atom alignment atom requires one direct core point")
			point = atom_points[0]
			if not point.hasAttribute("x") or not point.hasAttribute("y"):
				raise CDMLValidationError("atom alignment point requires x and y")
			# Convert through the established coordinate parser before mutation.
			x = _insertion_coordinate(point.getAttribute("x"))
			y = _insertion_coordinate(point.getAttribute("y"))
			points.append((point, x, y))
		if len(points) < 2:
			return CDMLAtomAlignResult(self.snapshot(), False, None)
		axis_index = 2 if request.axis == "horizontal" else 1
		# Equal selected-axis coordinates are a semantic no-op. Decide this before
		# calculating the mean or touching the detached DOM so compatible lexical
		# spellings such as ``3cm`` remain byte-for-byte preserved.
		axis_coordinates = tuple(point[axis_index] for point in points)
		if all(coordinate == axis_coordinates[0] for coordinate in axis_coordinates[1:]):
			return CDMLAtomAlignResult(self.snapshot(), False, None)
		mean = sum(axis_coordinates) / len(axis_coordinates)
		if not math.isfinite(mean):
			raise CDMLValidationError("atom alignment mean coordinate is nonfinite")
		attribute = "y" if request.axis == "horizontal" else "x"
		for point, _x, _y in points:
			point.setAttribute(attribute, f"{mean:.3f}cm")
		candidate.validate(validation="strict")
		if candidate.serialize() == self._document.serialize():
			return CDMLAtomAlignResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate.serialize(),
		)
		return CDMLAtomAlignResult(commit.snapshot, True, commit)

	#============================================
	def translate_atoms(self, request: CDMLAtomTranslateRequest) -> CDMLAtomTranslateResult:
		"""Translate selected direct-core atom points through one atomic commit.

		The request expresses its delta in PostScript scene points. Validate every
		durable target and coordinate against the accepted snapshot before making a
		detached candidate, so an invalid later target cannot partially move an
		earlier atom.
		"""
		targets, (dx_cm, dy_cm) = _validate_atom_translate_request(request)
		self._check_expected_revision(request.expected_revision)
		points = []
		for molecule_id, atom_id in targets:
			molecule = _direct_root_molecule(self._document, molecule_id)
			atom = _direct_molecule_atom(molecule, atom_id)
			atom_points = [
				child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"
			]
			if len(atom_points) != 1:
				raise CDMLValidationError("atom translation atom requires one direct core point")
			point = atom_points[0]
			if not point.hasAttribute("x") or not point.hasAttribute("y"):
				raise CDMLValidationError("atom translation point requires x and y")
			x = _insertion_coordinate(point.getAttribute("x"))
			y = _insertion_coordinate(point.getAttribute("y"))
			points.append((molecule_id, atom_id, x, y))
		if dx_cm == 0.0 and dy_cm == 0.0:
			return CDMLAtomTranslateResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		for molecule_id, atom_id, x, y in points:
			molecule = _direct_root_molecule(candidate, molecule_id)
			atom = _direct_molecule_atom(molecule, atom_id)
			point = next(
				child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"
			)
			# Preserve the untouched source attribute exactly. Compatible CDML may
			# use unitless PostScript points that parsing would otherwise rewrite.
			if dx_cm != 0.0:
				x_coordinate = x + dx_cm
				if not math.isfinite(x_coordinate):
					raise CDMLValidationError("atom translation coordinate is nonfinite")
				point.setAttribute("x", f"{x_coordinate:.3f}cm")
			if dy_cm != 0.0:
				y_coordinate = y + dy_cm
				if not math.isfinite(y_coordinate):
					raise CDMLValidationError("atom translation coordinate is nonfinite")
				point.setAttribute("y", f"{y_coordinate:.3f}cm")
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLAtomTranslateResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLAtomTranslateResult(commit.snapshot, True, commit)

	#============================================
	def rotate_atoms(self, request: CDMLAtomRotateRequest) -> CDMLAtomRotateResult:
		"""Rotate selected direct-core atom points through one atomic commit.

		The center arrives in PostScript scene points, matching frontend preview
		coordinates.  Convert it once at this boundary, validate every target in
		the authoritative snapshot, and then rotate the detached candidate using
		the same positive-angle convention as the 2D preview.
		"""
		targets, (center_x, center_y), angle = _validate_atom_rotate_request(request)
		self._check_expected_revision(request.expected_revision)
		points = []
		for molecule_id, atom_id in targets:
			molecule = _direct_root_molecule(self._document, molecule_id)
			atom = _direct_molecule_atom(molecule, atom_id)
			atom_points = [
				child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"
			]
			if len(atom_points) != 1:
				raise CDMLValidationError("atom rotation atom requires one direct core point")
			point = atom_points[0]
			if not point.hasAttribute("x") or not point.hasAttribute("y"):
				raise CDMLValidationError("atom rotation point requires x and y")
			x = _insertion_coordinate(point.getAttribute("x"))
			y = _insertion_coordinate(point.getAttribute("y"))
			points.append((molecule_id, atom_id, x, y))
		cosine = math.cos(angle)
		sine = math.sin(angle)
		rotations = []
		for molecule_id, atom_id, x, y in points:
			rotated_x = center_x + (x - center_x) * cosine - (y - center_y) * sine
			rotated_y = center_y + (x - center_x) * sine + (y - center_y) * cosine
			if not math.isfinite(rotated_x) or not math.isfinite(rotated_y):
				raise CDMLValidationError("atom rotation coordinate is nonfinite")
			canonical_x = _canonical_authored_coordinate(rotated_x)
			canonical_y = _canonical_authored_coordinate(rotated_y)
			rotations.append((
				molecule_id, atom_id, x, y, canonical_x, canonical_y,
			))
		if all(
				_canonical_authored_coordinate(x) == canonical_x
				and _canonical_authored_coordinate(y) == canonical_y
				for _molecule_id, _atom_id, x, y, canonical_x, canonical_y
				in rotations
			):
			return CDMLAtomRotateResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		for molecule_id, atom_id, x, y, canonical_x, canonical_y in rotations:
			molecule = _direct_root_molecule(candidate, molecule_id)
			atom = _direct_molecule_atom(molecule, atom_id)
			point = next(
				child for child in _element_children(atom)
				if _is_cdml_element(child) and _local_name(child) == "point"
			)
			if _canonical_authored_coordinate(x) != canonical_x:
				point.setAttribute("x", canonical_x)
			if _canonical_authored_coordinate(y) != canonical_y:
				point.setAttribute("y", canonical_y)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLAtomRotateResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLAtomRotateResult(commit.snapshot, True, commit)

	#============================================
	def set_bond_order(self, request: CDMLBondOrderEditRequest) -> CDMLBondOrderEditResult:
		"""Set one direct core bond's exact order without changing its type or depiction.

		The operation validates the entire editable target against the accepted
		snapshot before detaching a candidate.  It retains the existing supported
		type character, including styled bonds such as ``w2``, and changes only the
		order digit in ``bond@type``.
		"""
		molecule_id, bond_id, requested_order = _validate_bond_order_edit_request(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		bond = _direct_molecule_bond(molecule, bond_id)
		_require_editable_bond_endpoints(molecule, bond)
		if bond.hasAttribute("order"):
			raise CDMLValidationError("bond order edit rejects an independent bond@order attribute")
		type_char, current_order = _editable_bond_type(bond.getAttribute("type"))
		if type_char == "q" and requested_order != 1:
			raise CDMLValidationError("bond order edit Haworth bonds require order 1")
		if current_order == requested_order:
			return CDMLBondOrderEditResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		candidate_bond = _direct_molecule_bond(candidate_molecule, bond_id)
		candidate_bond.setAttribute("type", "%s%s" % (type_char, requested_order))
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLBondOrderEditResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLBondOrderEditResult(commit.snapshot, True, commit)

	#============================================
	def set_bond_type(self, request: CDMLBondTypeEditRequest) -> CDMLBondTypeEditResult:
		"""Set one direct core bond's exact ordinary type without changing its order.

		Compatibility ``l1`` and ``r1`` spellings are semantically hashed wedges:
		requesting ``h`` preserves their original lexical spelling, while another
		ordinary request replaces only the type character.  A current ``q1``
		Haworth edge may similarly become an ordinary type.
		"""
		molecule_id, bond_id, requested_type = _validate_bond_type_edit_request(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		bond = _direct_molecule_bond(molecule, bond_id)
		_require_editable_bond_endpoints(molecule, bond)
		if bond.hasAttribute("order"):
			raise CDMLValidationError("bond type edit rejects an independent bond@order attribute")
		current_type, current_order = _editable_bond_type_for_type_edit(
			bond.getAttribute("type"),
		)
		if current_type in ("l", "r") and requested_type == "h":
			return CDMLBondTypeEditResult(self.snapshot(), False, None)
		if current_type == requested_type:
			return CDMLBondTypeEditResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		candidate_bond = _direct_molecule_bond(candidate_molecule, bond_id)
		candidate_bond.setAttribute("type", "%s%s" % (requested_type, current_order))
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLBondTypeEditResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLBondTypeEditResult(commit.snapshot, True, commit)

	#============================================
	def patch_bond_properties(
			self, request: CDMLBondPropertiesPatch,
			) -> CDMLBondPropertiesPatchResult:
		"""Apply one explicit bond-property intent atomically through CDML.

		Order and type are interpreted as one final spelling.  All target and
		grammar checks precede the detached candidate so malformed late fields or
		unsupported final combinations cannot leave a partial backend commit.
		"""
		molecule_id, bond_id, changes = _validate_bond_properties_patch(request)
		self._check_expected_revision(request.expected_revision)
		molecule = _direct_root_molecule(self._document, molecule_id)
		bond = _direct_molecule_bond(molecule, bond_id)
		_require_editable_bond_endpoints(molecule, bond)
		if bond.hasAttribute("order"):
			raise CDMLBondPropertiesPatchError(
				"bond properties rejects an independent bond@order attribute",
			)
		current_type, current_order = _editable_bond_type_for_type_edit(
			bond.getAttribute("type"),
		)
		change_map = dict(changes)
		final_order = change_map.get("order", current_order)
		requested_type = change_map.get("type")
		if current_type in ("l", "r") and requested_type == "h" and final_order == 1:
			final_type = current_type
		elif requested_type is None:
			final_type = current_type
		else:
			final_type = requested_type
		compatibility_hashed = current_type in ("l", "r") and requested_type == "h" and final_order == 1
		if ("order" in change_map or "type" in change_map) and not compatibility_hashed:
			if not oasa.bond_semantics.is_authored_bond_order(final_type, final_order):
				raise CDMLBondPropertiesPatchError(
					"bond properties final type/order is unsupported",
				)
		if not changes:
			return CDMLBondPropertiesPatchResult(self.snapshot(), False, None)
		candidate = CDMLDocument.parse(self._document.serialize(), validation="compat")
		candidate_molecule = _direct_root_molecule(candidate, molecule_id)
		candidate_bond = _direct_molecule_bond(candidate_molecule, bond_id)
		if "order" in change_map or "type" in change_map:
			candidate_bond.setAttribute("type", "%s%s" % (final_type, final_order))
		for field_name, value in changes:
			if field_name in ("order", "type"):
				continue
			if field_name == "center":
				candidate_bond.setAttribute("center", "yes" if value else "no")
			elif field_name in ("line_width", "bond_width", "wedge_width"):
				candidate_bond.setAttribute(field_name, "%g" % value)
			else:
				candidate_bond.setAttribute("color", value)
		candidate.validate(validation="strict")
		candidate_cdml = candidate.serialize()
		if candidate_cdml == self._document.serialize():
			return CDMLBondPropertiesPatchResult(self.snapshot(), False, None)
		commit = self.commit(
			expected_revision=request.expected_revision,
			complete_cdml=candidate_cdml,
		)
		return CDMLBondPropertiesPatchResult(commit.snapshot, True, commit)

	#============================================
	def restore(self, *, target_revision: int, expected_revision: int) -> CDMLCommit:
		"""Restore retained content as a new monotonic backend revision."""
		self._check_expected_revision(expected_revision)
		if target_revision not in self._history:
			raise CDMLRevisionUnavailableError(
				f"CDML revision is not retained: {target_revision}",
		)
		target_cdml = self._history[target_revision].serialize()
		restored = CDMLDocument.parse(target_cdml, validation="strict")
		# Capture the pre-restore current revision before accepting the forward
		# revision.  The next restore can then redo this exact content.
		return self._accept_document(restored, {}, redo_revision=self._revision)

	#============================================
	def mark_saved(self, *, expected_revision: int) -> CDMLSnapshot:
		"""Set the current authoritative content as the clean saved baseline."""
		self._check_expected_revision(expected_revision)
		self._saved_cdml = self._document.serialize()
		self._saved_digest = _content_digest(self._saved_cdml)
		self._saved_revision = self._revision
		self._prune_history()
		return self.snapshot()

	#============================================
	def _check_expected_revision(self, expected_revision: int) -> None:
		"""Require optimistic-concurrency callers to name the current revision."""
		if expected_revision != self._revision:
			raise CDMLRevisionConflictError(
				f"expected revision {expected_revision}, current revision is {self._revision}",
			)

	#============================================
	def _accept_document(
		self,
		document: CDMLDocument,
		id_map: dict[str, str],
		*,
		redo_revision: int | None,
	) -> CDMLCommit:
		"""Install one already-valid document and retain it under a new revision."""
		self._revision += 1
		self._document = document
		self._history[self._revision] = document
		self._redo_revision = redo_revision
		self._prune_history()
		immutable_id_map = types.MappingProxyType(dict(id_map))
		commit = CDMLCommit(snapshot=self.snapshot(), id_map=immutable_id_map)
		return commit

	#============================================
	def _prune_history(self) -> None:
		"""Bound history while retaining current, saved, and immediate redo content."""
		protected_revisions = {self._revision, self._saved_revision}
		if self._redo_revision is not None:
			protected_revisions.add(self._redo_revision)
		while len(self._history) > self._history_capacity:
			removable_revisions = [
				revision for revision in sorted(self._history)
				if revision not in protected_revisions
			]
			if not removable_revisions:
				raise CDMLValidationError("history capacity cannot retain required revisions")
			del self._history[removable_revisions[0]]

#============================================
def _content_digest(text: str) -> str:
	"""Return a stable content digest used for backend dirty-state comparison."""
	digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
	return digest
