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

"""CDML bond attribute helpers."""


CDML_CORE_ATTRS = {
	"type",
	"start",
	"end",
	"id",
}

CDML_META_ATTRS = {
	"line_width",
	"bond_width",
	"wedge_width",
	"double_ratio",
	"center",
	"auto_sign",
	"equithick",
	"simple_double",
	"color",
	"wavy_style",
}

CDML_ALL_ATTRS = CDML_CORE_ATTRS | CDML_META_ATTRS

CDML_ATTR_ORDER = (
	"line_width",
	"bond_width",
	"center",
	"auto_sign",
	"equithick",
	"wedge_width",
	"double_ratio",
	"simple_double",
	"color",
	"wavy_style",
)


#============================================
def read_cdml_bond_attributes(bond_el, bond, preserve_attrs=None, known_attrs=None):
	"""Read CDML bond attributes into the bond object.

	Args:
		bond_el: CDML bond element.
		bond: Bond object to update.
		preserve_attrs (set[str] | None): Attrs to preserve in properties_.
		known_attrs (set[str] | None): Attrs to exclude from unknown capture.

	Returns:
		set[str]: Names of attributes present on input.
	"""
	if preserve_attrs is None:
		preserve_attrs = set()
	if known_attrs is None:
		known_attrs = CDML_ALL_ATTRS
	present = set()
	if not hasattr(bond_el, "attributes") or bond_el.attributes is None:
		return present
	for attr in bond_el.attributes.values():
		name = attr.name
		value = attr.value
		present.add(name)
		if name == "color":
			bond.line_color = value
			bond.properties_["line_color"] = value
			continue
		if name == "wavy_style":
			bond.wavy_style = value
			bond.properties_["wavy_style"] = value
			continue
		if name == "center":
			bond.center = (value == "yes")
			bond.properties_["center"] = value
			continue
		if name in preserve_attrs:
			bond.properties_[name] = value
	return present


#============================================
def select_cdml_attributes(
		values,
		defaults=None,
		present=None,
		force=None,
		allow_non_default_without_presence=True,
):
	"""Select attributes to serialize based on defaults and presence.

	Args:
		values (dict[str, str]): Attribute values.
		defaults (dict[str, str] | None): Default values to compare.
		present (set[str] | None): Attrs present on input.
		force (set[str] | None): Attrs forced to serialize.
		allow_non_default_without_presence (bool): Treat non-defaults as explicit.

	Returns:
		list[tuple[str, str]]: Ordered list of attributes to serialize.
	"""
	out = []
	if defaults is None:
		defaults = {}
	if force is None:
		force = set()
	for name in CDML_ATTR_ORDER:
		if name not in values:
			continue
		value = values.get(name)
		if value is None:
			continue
		default = defaults.get(name)
		if name in force:
			out.append((name, value))
			continue
		if default is not None and str(value) == str(default):
			continue
		if present is not None and name in present:
			out.append((name, value))
			continue
		if allow_non_default_without_presence:
			out.append((name, value))
	return out
