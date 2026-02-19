#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""CD-SVG codec: SVG rendering with embedded CDML metadata."""

# Standard Library
import io
import xml.dom.minidom as dom

# local repo modules
from oasa import cdml
from oasa import cdml_writer
from oasa import render_out
from oasa import safe_xml
from oasa import svg_out


_CDML_NAMESPACE = cdml_writer.CDML_NAMESPACE
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
def _first_element(node):
	for child in node.childNodes:
		if child.nodeType == child.ELEMENT_NODE:
			return child
	return None


#============================================
def _assert_safe_svg_export(svg_text):
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
def _extract_cdml_element(svg_text):
	doc = safe_xml.parse_dom_from_string(svg_text)
	nodes = doc.getElementsByTagNameNS(_CDML_NAMESPACE, "cdml")
	if nodes:
		return nodes[0]
	# Backward compatibility: older BKChem CD-SVG files may have <cdml>
	# without a namespace, so fall back to non-namespaced lookup.
	for node in doc.getElementsByTagName("cdml"):
		return node
	return None


#============================================
def _extract_cdml_writer_kwargs(kwargs):
	cdml_kwargs = {}
	for key in _CDML_WRITER_KWARGS:
		if key in kwargs:
			cdml_kwargs[key] = kwargs[key]
	return cdml_kwargs


#============================================
def _build_cdsvg_text(mol, **kwargs):
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
def text_to_mol(text, **kwargs):
	"""Parse CD-SVG by extracting only the embedded CDML payload."""
	del kwargs
	cdml_element = _extract_cdml_element(text)
	if cdml_element is None:
		raise ValueError("CD-SVG import failed: no embedded CDML block found.")
	doc = dom.Document()
	doc.appendChild(doc.importNode(cdml_element, True))
	return cdml.text_to_mol(doc.toxml("utf-8"))


#============================================
def file_to_mol(file_obj, **kwargs):
	text = file_obj.read()
	if isinstance(text, bytes):
		text = text.decode("utf-8")
	return text_to_mol(text, **kwargs)


#============================================
def mol_to_text(mol, **kwargs):
	return _build_cdsvg_text(mol, **kwargs)


#============================================
def mol_to_file(mol, file_obj, **kwargs):
	text = _build_cdsvg_text(mol, **kwargs)
	if isinstance(file_obj, io.TextIOBase):
		file_obj.write(text)
	else:
		file_obj.write(text.encode("utf-8"))
