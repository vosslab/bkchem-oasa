#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""CD-SVG codec: SVG rendering with embedded CDML metadata."""

# Standard Library
import io

# local repo modules
from oasa import cdml
from oasa import cdml_document
from oasa import cdml_writer
from oasa import render_out
from oasa import safe_xml
from oasa import svg_out


_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
_FORBIDDEN_EXPORT_SNIPPETS = (
	"<script",
	" onload=",
	" onerror=",
	"<foreignobject",
)
_CDML_WRITER_KWARGS = frozenset(
	("policy", "version", "namespace", "coord_to_text", "width_to_text")
)


#============================================
def _first_element(node: object) -> object | None:
	for child in node.childNodes:
		if child.nodeType == child.ELEMENT_NODE:
			return child
	return None


#============================================
def _assert_safe_svg_export(svg_text: str) -> None:
	lower_text = svg_text.lower()
	for snippet in _FORBIDDEN_EXPORT_SNIPPETS:
		if snippet in lower_text:
			raise ValueError(f"Unsafe SVG content blocked during CD-SVG export: {snippet}")
	doc = safe_xml.parse_dom_from_string(svg_text)
	for node in doc.getElementsByTagName("*"):
		namespace = node.namespaceURI or ""
		if namespace and namespace != _SVG_NAMESPACE:
			continue
		local_name = (node.localName or node.tagName or "").lower()
		if local_name in ("script", "foreignobject"):
			raise ValueError(f"Unsafe SVG content blocked during CD-SVG export: <{local_name}>")
		attributes = getattr(node, "attributes", None)
		if attributes is None:
			continue
		for attr in attributes.values():
			attr_name = attr.name.lower()
			attr_value = (attr.value or "").strip().lower()
			if attr_name.startswith("on"):
				raise ValueError(
					f"Unsafe SVG content blocked during CD-SVG export: {attr_name}"
				)
			if attr_name in ("href", "xlink:href") and (
				attr_value.startswith("http://") or attr_value.startswith("https://")
			):
				raise ValueError(
					f"Unsafe SVG content blocked during CD-SVG export: {attr_name}"
				)
			if "url(http://" in attr_value or "url(https://" in attr_value:
				raise ValueError("Unsafe SVG content blocked during CD-SVG export: external-url")


#============================================
def _extract_cdml_elements(svg_text: object) -> tuple[object, ...]:
	"""Return embedded CDML roots without interpreting rendered SVG content."""
	doc = safe_xml.parse_dom_from_string(svg_text)
	return tuple(
		node for node in doc.getElementsByTagName("*")
		if (node.localName or node.tagName).split(":")[-1] == "cdml"
	)


#============================================
def _extract_cdml_element(svg_text: object) -> object | None:
	"""Return the first embedded root for legacy molecule-only codec behavior."""
	nodes = _extract_cdml_elements(svg_text)
	return nodes[0] if nodes else None


#============================================
def _extract_cdml_writer_kwargs(kwargs: object) -> dict:
	cdml_kwargs = {}
	for key in _CDML_WRITER_KWARGS:
		if key in kwargs:
			cdml_kwargs[key] = kwargs[key]
	return cdml_kwargs


#============================================
def _build_cdsvg_text(mol: object, **kwargs) -> str:
	svg_buffer = io.StringIO()
	render_out.render_to_svg(mol, svg_buffer, **kwargs)
	svg_doc = safe_xml.parse_dom_from_string(svg_buffer.getvalue())
	root = _first_element(svg_doc)
	if root is None or root.tagName.lower() != "svg":
		raise ValueError("CD-SVG export failed to construct an SVG root node.")
	metadata = svg_doc.createElement("metadata")
	metadata.setAttribute("id", "bkchem_cdml")
	cdml_kwargs = _extract_cdml_writer_kwargs(kwargs)
	cdml_doc = safe_xml.parse_dom_from_string(cdml_writer.mol_to_text(mol, **cdml_kwargs))
	cdml_root = _first_element(cdml_doc)
	if cdml_root is None:
		raise ValueError("CD-SVG export failed to build CDML payload.")
	metadata.appendChild(svg_doc.importNode(cdml_root, True))
	root.appendChild(metadata)
	svg_text = svg_out.pretty_print_svg(svg_doc.toxml("utf-8"))
	_assert_safe_svg_export(svg_text)
	return svg_text


#============================================
def text_to_mol(text: object, **kwargs) -> object:
	"""Extract embedded CDML chemistry through OASA's molecule-import policy."""
	del kwargs
	cdml_element = _extract_cdml_element(text)
	if cdml_element is None:
		raise ValueError("CD-SVG import failed: no embedded CDML block found.")
	return cdml.text_to_mol(cdml_element.toxml("utf-8"))


#============================================
def file_to_mol(file_obj: object, **kwargs) -> object:
	text = file_obj.read()
	if isinstance(text, bytes):
		text = text.decode("utf-8")
	return text_to_mol(text, **kwargs)


#============================================
def text_to_document(text: object, **kwargs: object) -> str:
	"""Extract exactly one strict complete CDML document from CD-SVG."""
	del kwargs
	nodes = _extract_cdml_elements(text)
	if not nodes:
		raise ValueError("CD-SVG import failed: no embedded CDML block found.")
	if len(nodes) != 1:
		raise ValueError("CD-SVG import failed: multiple embedded CDML blocks found.")
	cdml_text = nodes[0].toxml("utf-8").decode("utf-8")
	return cdml_document.CDMLDocument.parse(
		cdml_text, validation="strict",
	).serialize()


#============================================
def file_to_document(file_obj: object, **kwargs: object) -> str:
	"""Extract complete CDML from one caller-owned CD-SVG file object."""
	return text_to_document(file_obj.read(), **kwargs)


#============================================
def mol_to_text(mol: object, **kwargs) -> str:
	return _build_cdsvg_text(mol, **kwargs)


#============================================
def mol_to_file(mol: object, file_obj: object, **kwargs) -> None:
	text = _build_cdsvg_text(mol, **kwargs)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text)
	else:
		file_obj.write(text.encode("utf-8"))
