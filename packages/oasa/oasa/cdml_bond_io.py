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

# local repo modules
from oasa.render_lib.data_types import BondDepiction


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
	"haworth_position",
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
	"haworth_position",
)

HAWORTH_POSITIONS = {"front", "back"}
CDML_EXPLICIT_FIELDS_KEY = "_cdml_explicit_depiction_fields"

_DIRECT_FIELD_NAMES = {
	"color": "line_color",
	"double_ratio": "double_length_ratio",
	"auto_sign": "auto_bond_sign",
}


#============================================
def read_cdml_bond_attributes(
	bond_el: object,
	bond: object,
	preserve_attrs: object=None,
	known_attrs: object=None,
) -> set:
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
		name = _local_attribute_name(attr)
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
		if name == "haworth_position":
			if value in HAWORTH_POSITIONS:
				bond.properties_[name] = value
			continue
		if name in preserve_attrs:
			bond.properties_[name] = value
	set_cdml_bond_explicit_fields(bond, present & CDML_META_ATTRS)
	return present


#============================================
def set_cdml_bond_explicit_fields(bond: object, fields: object) -> None:
	"""Record exact depiction-attribute presence without authoring new CDML."""
	explicit = frozenset(str(name) for name in fields if name in CDML_META_ATTRS)
	bond.properties_[CDML_EXPLICIT_FIELDS_KEY] = explicit


#============================================
def cdml_bond_explicit_fields(bond: object) -> frozenset[str]:
	"""Return explicit depiction fields, deriving them for programmatic bonds."""
	properties = getattr(bond, "properties_", {})
	recorded = properties.get(CDML_EXPLICIT_FIELDS_KEY)
	if recorded is not None:
		return frozenset(recorded)
	explicit = set()
	for name in CDML_META_ATTRS:
		direct_name = _DIRECT_FIELD_NAMES.get(name, name)
		if getattr(bond, direct_name, None) is not None:
			explicit.add(name)
		if name in properties:
			explicit.add(name)
	if "line_color" in properties:
		explicit.add("color")
	return frozenset(explicit)


#============================================
def has_recorded_cdml_bond_presence(bond: object) -> bool:
	"""Return whether a parsed/projected edge carries authoritative presence."""
	properties = getattr(bond, "properties_", {})
	return CDML_EXPLICIT_FIELDS_KEY in properties


#============================================
def resolve_bond_depiction(bond: object) -> BondDepiction:
	"""Resolve shared effective values without changing lexical CDML presence."""
	explicit_fields = cdml_bond_explicit_fields(bond)
	line_width = _optional_float_value(bond, "line_width")
	bond_width = _optional_float_value(bond, "bond_width")
	wedge_width = _optional_float_value(bond, "wedge_width")
	double_ratio = _optional_float_value(bond, "double_ratio")
	if double_ratio is None:
		double_ratio = 0.75
	center = _optional_center_value(bond)
	auto_sign = _optional_int_value(bond, "auto_sign")
	if auto_sign is None:
		auto_sign = 1
	equithick = _optional_bool_value(bond, "equithick")
	if equithick is None:
		equithick = False
	simple_double = _optional_bool_value(bond, "simple_double")
	if simple_double is None:
		simple_double = True
	color = _optional_text_value(bond, "color")
	wavy_style = _optional_text_value(bond, "wavy_style")
	haworth_position = _optional_text_value(bond, "haworth_position")
	depiction = BondDepiction(
		line_width=line_width,
		bond_width=bond_width,
		wedge_width=wedge_width,
		double_ratio=double_ratio,
		center=center,
		auto_sign=auto_sign,
		equithick=equithick,
		simple_double=simple_double,
		color=color,
		wavy_style=wavy_style,
		haworth_position=haworth_position,
		explicit_fields=explicit_fields,
	)
	return depiction


#============================================
def _optional_raw_value(bond: object, name: str) -> object | None:
	"""Return one direct depiction value or its retained CDML spelling."""
	direct_name = _DIRECT_FIELD_NAMES.get(name, name)
	value = getattr(bond, direct_name, None)
	if value is not None:
		return value
	properties = getattr(bond, "properties_", {})
	if name == "color":
		value = properties.get("line_color")
		if value is not None:
			return value
	return properties.get(name)


#============================================
def _optional_float_value(bond: object, name: str) -> float | None:
	"""Return one optional depiction value as a float."""
	value = _optional_raw_value(bond, name)
	if value is None:
		return None
	return float(value)


#============================================
def _optional_int_value(bond: object, name: str) -> int | None:
	"""Return one optional depiction value as an integer."""
	value = _optional_raw_value(bond, name)
	if value is None:
		return None
	return int(value)


#============================================
def _optional_bool_value(bond: object, name: str) -> bool | None:
	"""Return one optional integer-like depiction value as a boolean."""
	value = _optional_raw_value(bond, name)
	if value is None:
		return None
	return bool(int(value))


#============================================
def _optional_center_value(bond: object) -> bool | None:
	"""Return the optional centered-double selection."""
	value = _optional_raw_value(bond, "center")
	if value is None:
		return None
	if isinstance(value, str):
		return value == "yes"
	return bool(value)


#============================================
def _optional_text_value(bond: object, name: str) -> str | None:
	"""Return one optional depiction value as text."""
	value = _optional_raw_value(bond, name)
	if value is None:
		return None
	return str(value)


#============================================
def _local_attribute_name(attribute: object) -> str:
	"""Return an XML attribute's semantic name independently of its prefix."""
	local_name = getattr(attribute, "localName", None)
	if local_name:
		return str(local_name)
	return str(attribute.name).rsplit(":", maxsplit=1)[-1]


#============================================
def select_cdml_attributes(
		values: object,
		defaults: object=None,
		present: object=None,
		force: object=None,
		allow_non_default_without_presence: object=True,
) -> list:
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
