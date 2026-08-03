"""Plain CDML compatibility facts for Qt-only callers.

This small IO boundary owns hardened XML inspection for legacy retained
fragments. Callers receive only scalar facts and never retain parser objects.
"""

# Standard Library
import xml.parsers.expat

# local repo modules
import oasa.safe_xml


#============================================
def direct_ftext_text(fragment: str) -> str | None:
	"""Return direct character data from one retained ftext fragment.

	Direct text and CDATA children retain their authored order. Nested markup is
	not flattened: the plain Text Configure route continues to use only its
	direct character data while separately established rich-text eligibility
	determines whether that route is available.

	Args:
		fragment: Inner XML retained below one CDML ``ftext`` element.

	Returns:
		Direct text, an empty string for valid markup without direct character
		data, or None when the retained compatibility fragment is malformed.
	"""
	try:
		document = oasa.safe_xml.parse_dom_from_string("<wrapper>%s</wrapper>" % fragment)
	except (ValueError, xml.parsers.expat.ExpatError):
		return None
	parts = []
	for child in document.documentElement.childNodes:
		if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
			parts.append(child.data)
	text = "".join(parts)
	return text


#============================================
def root_id(raw_xml: str) -> str | None:
	"""Return the exact nonempty ID on one retained compatibility root.

	Args:
		raw_xml: One complete retained XML fragment.

	Returns:
		The root's nonempty ID spelling, or None for missing, empty, or malformed
		compatibility content.
	"""
	try:
		element = oasa.safe_xml.parse_dom_from_string(raw_xml).documentElement
	except (ValueError, xml.parsers.expat.ExpatError):
		return None
	identifier = element.getAttribute("id")
	if not identifier:
		return None
	return identifier
