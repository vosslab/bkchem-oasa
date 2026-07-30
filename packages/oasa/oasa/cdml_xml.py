"""Hardened parsing and semantic inspection for complete CDML documents.

This module is the one policy gate for external complete CDML.  It deliberately
keeps lxml nodes private: the authoritative document stores the original,
accepted bytes in the existing defused minidom compatibility representation.
"""

# Standard Library
import dataclasses
import xml.dom
import xml.parsers.expat

# PIP3 modules
from lxml import etree

# local repo modules
import oasa.safe_xml


CDML_NAMESPACE_URI = "http://www.freesoftware.fsf.org/bkchem/cdml"
CDML_CORE_ELEMENT_NAMES = frozenset({
	"arrow", "atom", "author", "author_program", "bond", "cdml", "circle", "condition",
	"display-form", "doc", "external-data", "font", "fragment", "ftext", "group",
	"info", "mark", "metadata", "molecule", "name", "oval", "paper", "plus",
	"note", "point", "polygon", "polyline", "product", "property", "query", "reactant",
	"reaction", "rect", "square", "standard", "template", "text", "user-data",
	"vertex", "viewport",
})
# These established CDML records provide durable containers without granting
# their payload a typed CDML grammar.  Their descendants retain lexical XML
# ownership even when they use familiar CDML-looking names.
CDML_PRESERVATION_ONLY_CONTAINER_NAMES = frozenset({
	"display-form", "external-data", "user-data",
})
# This preservation-only registry mirrors documented CDML attributes and
# compatibility names accepted by the implemented readers/writers.  It is not
# a schema validator: unlisted input remains accepted as opaque content.
CDML_CORE_ATTRIBUTE_NAMES = {
	"arrow": frozenset({"color", "end", "id", "idref", "length", "shape", "spline", "start", "type", "width"}),
	"atom": frozenset({
		"background-color", "charge", "explicit_hydrogens", "free_sites",
		"hydrogens", "id", "isotope", "multiplicity", "name", "number",
		"pos", "show", "show_hydrogens", "show_number", "valency",
	}),
	"author": frozenset(), "author_program": frozenset({"version"}),
	"bond": frozenset({"auto_sign", "bond_width", "center", "color", "distance", "double-ratio", "double_ratio", "end", "equithick", "haworth_position", "id", "line_width", "length", "min_wedge_angle", "simple_double", "start", "type", "wavy_style", "wedge-width", "wedge_width", "width"}),
	"cdml": frozenset({"type", "version"}),
	"circle": frozenset({"area_color", "id", "line_color", "width", "x1", "x2", "y1", "y2"}),
	"condition": frozenset({"idref"}), "display-form": frozenset(), "doc": frozenset({"href"}), "external-data": frozenset(),
	"font": frozenset({"color", "family", "size"}), "fragment": frozenset({"id", "type"}),
	"ftext": frozenset(), "group": frozenset({"background-color", "group-type", "id", "name", "number", "pos", "show_number"}),
	"info": frozenset(), "mark": frozenset({"auto", "draw_circle", "line_width", "refname", "size", "text", "type", "x", "y"}),
	"metadata": frozenset(), "molecule": frozenset({"id", "name"}), "name": frozenset(), "note": frozenset(),
	"oval": frozenset({"area_color", "id", "line_color", "width", "x1", "x2", "y1", "y2"}),
	"paper": frozenset({"crop_margin", "crop_svg", "orientation", "replace_minus", "size_x", "size_y", "type", "use_real_minus"}),
	"plus": frozenset({"background-color", "color", "font_size", "id", "idref"}), "point": frozenset({"x", "y", "z"}),
	"polygon": frozenset({"area_color", "id", "line_color", "width"}), "polyline": frozenset({"id", "line_color", "spline", "width"}),
	"product": frozenset({"idref"}), "property": frozenset({"name", "type", "value"}),
	"query": frozenset({"background-color", "free_sites", "id", "name", "number", "pos", "show_number"}),
	"reactant": frozenset({"idref"}), "reaction": frozenset({"id"}),
	"rect": frozenset({"area_color", "id", "line_color", "width", "x1", "x2", "y1", "y2"}),
	"square": frozenset({"area_color", "id", "line_color", "width", "x1", "x2", "y1", "y2"}),
	"standard": frozenset({"area_color", "font_family", "font_size", "line_color", "line_width", "paper_crop_margin", "paper_crop_svg", "paper_orientation", "paper_type"}),
	"template": frozenset({"atom", "bond_first", "bond_second"}),
	"text": frozenset({"background-color", "id", "number", "pos", "show_number"}), "user-data": frozenset(),
	"vertex": frozenset({"id"}), "viewport": frozenset({"id", "viewport"}),
}
_XML_NAMESPACE_URI = "http://www.w3.org/XML/1998/namespace"
_XMLNS_NAMESPACE_URI = "http://www.w3.org/2000/xmlns/"


class CDMLXMLParseError(ValueError):
	"""Raised when complete CDML is malformed or uses unsafe XML syntax."""


@dataclasses.dataclass(frozen=True)
class CDMLXMLInspection:
	"""A node-free immutable semantic view of one safely parsed CDML source."""

	local_name: str
	namespace: str
	version: str | None
	semantic_fingerprint: tuple


#============================================
def _parser() -> etree.XMLParser:
	"""Create an isolated parser whose security options cannot leak between calls."""
	parser = etree.XMLParser(
		resolve_entities=False,
		no_network=True,
		load_dtd=False,
		dtd_validation=False,
		recover=False,
		huge_tree=False,
		remove_blank_text=False,
		strip_cdata=False,
		remove_comments=False,
		remove_pis=False,
	)
	return parser


#============================================
def _expanded_name(name: object) -> tuple[str, str]:
	"""Return a namespace/local-name pair without exposing lxml values."""
	value = str(name)
	if value.startswith("{"):
		namespace, local_name = value[1:].split("}", 1)
		return namespace, local_name
	return "", value


#============================================
def _dom_expanded_name(node: object) -> tuple[str, str]:
	"""Return one DOM element or attribute name by namespace URI and local name."""
	namespace = getattr(node, "namespaceURI", None) or ""
	local_name = getattr(node, "localName", None) or getattr(node, "nodeName", "")
	name = namespace, str(local_name)
	return name


#============================================
def _namespace_context(element: object, inherited: dict[str, str]) -> dict[str, str]:
	"""Return the lexical namespace bindings in scope after one DOM element."""
	context = dict(inherited)
	attributes = getattr(element, "attributes", None)
	if attributes is None:
		return context
	for index in range(attributes.length):
		attribute = attributes.item(index)
		if attribute.namespaceURI != _XMLNS_NAMESPACE_URI:
			continue
		prefix = "" if attribute.nodeName == "xmlns" else attribute.localName
		context[prefix] = attribute.value
	return context


#============================================
def _is_core_cdml_element(element: object, parent_is_core: bool) -> bool:
	"""Return whether an element is known CDML syntax in a known CDML ancestry."""
	name_namespace, name_local = _dom_expanded_name(element)
	is_core = (
		parent_is_core
		and name_local in CDML_CORE_ELEMENT_NAMES
		and name_namespace in ("", CDML_NAMESPACE_URI)
	)
	return is_core


#============================================
def is_preservation_only_container(element: object) -> bool:
	"""Return whether one established CDML element owns an opaque payload subtree."""
	name_namespace, name_local = _dom_expanded_name(element)
	return (
		name_local in CDML_PRESERVATION_ONLY_CONTAINER_NAMES
		and name_namespace in ("", CDML_NAMESPACE_URI)
	)


#============================================
def has_preservation_only_ancestor(element: object) -> bool:
	"""Return whether an element lies below an established opaque CDML container."""
	parent = getattr(element, "parentNode", None)
	while parent is not None and getattr(parent, "nodeType", None) == parent.ELEMENT_NODE:
		if is_preservation_only_container(parent):
			return True
		parent = parent.parentNode
	return False


#============================================
def _core_attributes(element: object, namespace_context: dict[str, str]) -> tuple:
	"""Return separate known and opaque attributes for one recognized core element."""
	known_attributes = []
	opaque_attributes = []
	element_name = _dom_expanded_name(element)
	recognized_names = CDML_CORE_ATTRIBUTE_NAMES[element_name[1]]
	for index in range(element.attributes.length):
		attribute = element.attributes.item(index)
		if attribute.namespaceURI == _XMLNS_NAMESPACE_URI:
			continue
		attribute_name = _dom_expanded_name(attribute)
		is_recognized = (
			attribute_name[0] in ("", CDML_NAMESPACE_URI)
			and attribute_name[1] in recognized_names
		)
		if is_recognized:
			known_attributes.append((attribute_name, attribute.value))
		else:
			opaque_attributes.append((attribute.nodeName, attribute.value))
	sorted_opaque_attributes = tuple(sorted(opaque_attributes))
	opaque_context = ()
	if sorted_opaque_attributes:
		opaque_context = tuple(sorted(namespace_context.items()))
	result = (
		tuple(sorted(known_attributes)),
		sorted_opaque_attributes,
		opaque_context,
	)
	return result


#============================================
def _opaque_attributes(element: object) -> tuple:
	"""Return opaque attributes by their original lexical QName and literal value."""
	attributes = []
	for index in range(element.attributes.length):
		attribute = element.attributes.item(index)
		attributes.append((attribute.nodeName, attribute.value))
	result = tuple(sorted(attributes))
	return result


#============================================
def _node_fingerprint(
	node: object,
	namespace_context: dict[str, str],
	parent_is_core: bool,
) -> tuple:
	"""Return ordered XML semantics, retaining lexical content below opaque elements."""
	if node.nodeType == xml.dom.Node.COMMENT_NODE:
		fingerprint = ("comment", node.data)
		return fingerprint
	if node.nodeType == xml.dom.Node.PROCESSING_INSTRUCTION_NODE:
		fingerprint = ("processing-instruction", node.target, node.data)
		return fingerprint
	if node.nodeType in (xml.dom.Node.TEXT_NODE, xml.dom.Node.CDATA_SECTION_NODE):
		fingerprint = ("character-data", node.data)
		return fingerprint
	if node.nodeType != xml.dom.Node.ELEMENT_NODE:
		fingerprint = ("node", node.nodeType, node.nodeValue)
		return fingerprint
	current_context = _namespace_context(node, namespace_context)
	is_core = _is_core_cdml_element(node, parent_is_core)
	child_parent_is_core = is_core and not is_preservation_only_container(node)
	children = tuple(
		_node_fingerprint(child, current_context, child_parent_is_core)
		for child in node.childNodes
	)
	if is_core:
		known_attributes, opaque_attributes, opaque_context = _core_attributes(
			node,
			current_context,
		)
		fingerprint = (
			"core-element",
			_dom_expanded_name(node),
			known_attributes,
			("opaque-attributes", opaque_attributes, opaque_context),
			children,
		)
		return fingerprint
	fingerprint = (
		"opaque-element",
		node.nodeName,
		tuple(sorted(current_context.items())),
		_opaque_attributes(node),
		children,
	)
	return fingerprint


#============================================
def _document_fingerprint(document: object) -> tuple:
	"""Return ordered document content using the lexical DOM after lxml authorization."""
	namespace_context = {"xml": _XML_NAMESPACE_URI}
	fingerprint = tuple(
		_node_fingerprint(node, namespace_context, True)
		for node in document.childNodes
	)
	return fingerprint


#============================================
def _parse_root(source: bytes) -> object:
	"""Parse bytes under the complete-CDML policy and reject every DOCTYPE."""
	if not isinstance(source, bytes):
		raise TypeError("complete CDML XML source must be bytes")
	try:
		root = etree.fromstring(source, parser=_parser())
	except etree.XMLSyntaxError as error:
		raise CDMLXMLParseError("CDML XML cannot be safely parsed") from error
	doctype = root.getroottree().docinfo.doctype
	if doctype:
		raise CDMLXMLParseError("CDML XML must not declare a DOCTYPE")
	return root


#============================================
def parse_cdml_dom(source: bytes) -> object:
	"""Authorize complete CDML then return defused minidom storage for the same bytes."""
	_parse_root(source)
	try:
		document = oasa.safe_xml.parse_dom_from_string(source)
	except (ValueError, xml.parsers.expat.ExpatError) as error:
		raise CDMLXMLParseError("CDML XML cannot be safely parsed") from error
	return document


#============================================
def inspect_cdml_xml(source: bytes) -> CDMLXMLInspection:
	"""Return node-free root metadata and semantic preservation content for CDML bytes."""
	root = _parse_root(source)
	document = parse_cdml_dom(source)
	namespace, local_name = _expanded_name(root.tag)
	inspection = CDMLXMLInspection(
		local_name=local_name,
		namespace=namespace,
		version=root.get("version"),
		semantic_fingerprint=_document_fingerprint(document),
	)
	return inspection
