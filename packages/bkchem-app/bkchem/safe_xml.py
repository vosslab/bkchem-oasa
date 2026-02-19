"""Secure XML parsing helpers using defusedxml."""

# Third Party
from defusedxml import ElementTree as elementtree
from defusedxml import minidom


#============================================
def _to_bytes(text):
	if isinstance(text, bytes):
		return text
	return str(text).encode('utf-8')


#============================================
def parse_xml_file(path):
	"""Parse XML from a file path into an ElementTree."""
	return elementtree.parse(str(path))


#============================================
def parse_xml_string(text):
	"""Parse XML from a string into an Element."""
	return elementtree.fromstring(_to_bytes(text))


#============================================
def parse_dom_from_file(path):
	"""Parse XML from a file path into a minidom Document."""
	return minidom.parse(str(path))


#============================================
def parse_dom_from_string(text):
	"""Parse XML from a string into a minidom Document."""
	return minidom.parseString(_to_bytes(text))
