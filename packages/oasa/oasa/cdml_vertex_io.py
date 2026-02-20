#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#     Copyright (C) 2003-2008 Beda Kosata <beda@zirael.org>
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     Complete text of GNU GPL can be found in the file LICENSE in the
#     main directory of the program
#
#--------------------------------------------------------------------------

"""CDML vertex attribute helpers for unknown-attribute preservation."""


CDML_PRESENT_KEY = "_cdml_present"
CDML_UNKNOWN_KEY = "_cdml_unknown_attrs"

# known attribute sets per vertex element type
CDML_ATOM_KNOWN_ATTRS = {
	"id", "name", "pos", "charge", "hydrogens", "show",
	"background-color", "multiplicity", "valency",
	"show_number", "number", "free_sites",
}

CDML_GROUP_KNOWN_ATTRS = {
	"id", "name", "pos", "group-type", "background-color",
	"show_number", "number",
}

CDML_QUERY_KNOWN_ATTRS = {
	"id", "name", "pos", "background-color",
	"show_number", "number", "free_sites",
}

CDML_TEXT_KNOWN_ATTRS = {
	"id", "pos", "background-color",
	"show_number", "number",
}


#============================================
def read_cdml_vertex_attributes(element, vertex, known_attrs):
	"""Read CDML vertex attributes and track present/unknown sets.

	Iterates all attributes on the DOM element, records which were
	present, and stores any unknown attributes for later re-emission.

	Args:
		element: DOM element with CDML vertex attributes.
		vertex: BKChem vertex object to annotate.
		known_attrs: set of attribute names the caller handles.
	"""
	present = set()
	if not hasattr(element, "attributes") or element.attributes is None:
		vertex.properties_[CDML_PRESENT_KEY] = present
		return
	unknown = {}
	for attr in element.attributes.values():
		name = attr.name
		value = attr.value
		present.add(name)
		if name not in known_attrs:
			unknown[name] = value
			vertex.properties_[name] = value
	vertex.properties_[CDML_PRESENT_KEY] = present
	if unknown:
		vertex.properties_[CDML_UNKNOWN_KEY] = dict(unknown)


#============================================
def get_cdml_present(vertex):
	"""Return the set of CDML attributes present on input, if recorded.

	Args:
		vertex: BKChem vertex object.

	Returns:
		set or None: Attribute name set, or None if not recorded.
	"""
	present = vertex.properties_.get(CDML_PRESENT_KEY)
	if isinstance(present, set):
		return set(present)
	return None


#============================================
def collect_unknown_cdml_vertex_attributes(vertex, known_attrs, present):
	"""Collect unknown CDML attributes preserved in vertex.properties_.

	Args:
		vertex: BKChem vertex object.
		known_attrs: set of attribute names handled by the caller.
		present: set of attribute names present on input (or None).

	Returns:
		list of (name, value) tuples for unknown attributes to re-emit.
	"""
	# prefer the explicit unknown dict if available
	unknown = vertex.properties_.get(CDML_UNKNOWN_KEY)
	out = []
	if isinstance(unknown, dict):
		for name in sorted(unknown.keys()):
			value = unknown[name]
			if present is not None and name not in present:
				continue
			if value is None:
				continue
			out.append((name, str(value)))
		return out
	# fallback: scan properties_ for non-internal, non-known keys
	for name in sorted(vertex.properties_.keys()):
		value = vertex.properties_[name]
		if name.startswith("_"):
			continue
		if name in known_attrs:
			continue
		if present is not None and name not in present:
			continue
		if value is None:
			continue
		out.append((name, str(value)))
	return out
