"""Qt-free codec for CDML 26.07 escaped rich-text character data.

The complete CDML document remains owned by :mod:`oasa.cdml_document`.  This
module owns only the small, explicitly supported authored fragment grammar in
one ``ftext`` character-data value.  It never returns lxml objects across its
public boundary.
"""

# Standard Library
import dataclasses

# PIP3 modules
from lxml import etree


_STYLE_ORDER = ("b", "i", "sub", "sup")
_STYLE_NAMES = frozenset(_STYLE_ORDER)


class CDMLFTextCodecError(ValueError):
	"""Raised when an authored CDML rich-text fragment is unsupported."""


@dataclasses.dataclass(frozen=True)
class CDMLFTextRun:
	"""One immutable text span with canonical CDML rich-text styles.

	Styles are an ordered, duplicate-free subset of ``b``, ``i``, ``sub``, and
	``sup`` in that documented order.  A run's ``text`` is rendered character
	data, not XML source.
	"""

	text: str
	styles: tuple[str, ...]


#============================================
def _fragment_parser() -> etree.XMLParser:
	"""Create one hardened parser for an authored ftext fragment."""
	return etree.XMLParser(
		resolve_entities=False,
		no_network=True,
		load_dtd=False,
		dtd_validation=False,
		recover=False,
		huge_tree=False,
		remove_blank_text=False,
		remove_comments=False,
		remove_pis=False,
	)


#============================================
def _canonical_styles(styles: object) -> tuple[str, ...]:
	"""Validate one exact style tuple and return its stable canonical order."""
	if type(styles) is not tuple:
		raise CDMLFTextCodecError("ftext styles must be an exact tuple")
	if any(type(style) is not str or style not in _STYLE_NAMES for style in styles):
		raise CDMLFTextCodecError("ftext styles contain an unsupported value")
	if len(set(styles)) != len(styles):
		raise CDMLFTextCodecError("ftext styles must not repeat")
	if "sub" in styles and "sup" in styles:
		raise CDMLFTextCodecError("ftext styles cannot combine sub and sup")
	return tuple(style for style in _STYLE_ORDER if style in styles)


#============================================
def normalize(runs: object) -> tuple[CDMLFTextRun, ...]:
	"""Return canonical runs, joining adjacent equal styles and dropping empties."""
	if type(runs) is not tuple:
		raise CDMLFTextCodecError("ftext runs must be an exact immutable tuple")
	normalized: list[CDMLFTextRun] = []
	for run in runs:
		if type(run) is not CDMLFTextRun:
			raise CDMLFTextCodecError("ftext runs must contain exact run values")
		if type(run.text) is not str:
			raise CDMLFTextCodecError("ftext run text must be a string")
		styles = _canonical_styles(run.styles)
		if not run.text:
			continue
		if normalized and normalized[-1].styles == styles:
			previous = normalized[-1]
			normalized[-1] = CDMLFTextRun(previous.text + run.text, styles)
		else:
			normalized.append(CDMLFTextRun(run.text, styles))
	return tuple(normalized)


#============================================
def _append_text(runs: list[CDMLFTextRun], text: str | None, styles: tuple[str, ...]) -> None:
	"""Append nonempty parser character data without leaking parser nodes."""
	if text:
		runs.append(CDMLFTextRun(text, styles))


#============================================
def _decode_children(element: object, styles: tuple[str, ...], runs: list[CDMLFTextRun]) -> None:
	"""Decode one validated lxml element subtree into plain immutable runs."""
	_append_text(runs, element.text, styles)
	for child in element:
		if not isinstance(child.tag, str):
			raise CDMLFTextCodecError(
				"ftext markup cannot contain comments or processing instructions",
			)
		if child.tag not in _STYLE_NAMES or child.prefix is not None or child.nsmap != {}:
			raise CDMLFTextCodecError("ftext markup contains an unsupported namespace or tag")
		if child.attrib:
			raise CDMLFTextCodecError("ftext markup tags cannot have attributes")
		child_styles = _canonical_styles(styles + (child.tag,))
		_decode_children(child, child_styles, runs)
		_append_text(runs, child.tail, styles)


#============================================
def decode(authored: object) -> tuple[CDMLFTextRun, ...]:
	"""Decode one escaped CDML ftext value into normalized public runs.

	``authored`` is the unescaped character-data value held by a CDML ``ftext``
	node.  Formatting tags are therefore ordinary text here; the enclosing CDML

	serializer escapes them when it writes the complete document.
	"""
	if type(authored) is not str:
		raise CDMLFTextCodecError("ftext authored content must be a string")
	if "<!DOCTYPE" in authored.upper() or "<!ENTITY" in authored.upper():
		raise CDMLFTextCodecError("ftext markup cannot declare DTDs or entities")
	try:
		source = ("<ftext-root>" + authored + "</ftext-root>").encode("utf-8")
		root = etree.fromstring(source, _fragment_parser())
	except (UnicodeError, etree.XMLSyntaxError) as error:
		raise CDMLFTextCodecError("ftext markup is malformed") from error
	if root.attrib or root.nsmap != {}:
		raise CDMLFTextCodecError("ftext markup cannot declare attributes or namespaces")
	runs: list[CDMLFTextRun] = []
	_decode_children(root, (), runs)
	return normalize(tuple(runs))


#============================================
def encode(runs: object) -> str:
	"""Encode runs as canonical authored markup for a CDML ftext text node.

	The complete-CDML serializer performs the outer XML escaping when it stores
	this authored string as ftext character data.
	"""
	normalized = normalize(runs)
	parts: list[str] = []
	for run in normalized:
		# lxml's element serializer gives the complete XML escaping policy without
		# exposing a parser object.  Slice only the controlled text payload.
		container = etree.Element("ftext")
		container.text = run.text
		serialized = etree.tostring(container, encoding="unicode")
		escaped = serialized[len("<ftext>"):-len("</ftext>")]
		for style in reversed(run.styles):
			escaped = "<%s>%s</%s>" % (style, escaped, style)
		parts.append(escaped)
	return "".join(parts)
