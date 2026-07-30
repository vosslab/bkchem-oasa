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

"""Frontend-neutral CDML bond semantics and compatibility helpers."""


# The canonical 26.07 meaning belongs to the CDML/OASA boundary.  Qt labels
# live separately in bkchem_qt.bond_presentation so presentation wording does
# not become a backend concern.
BOND_TYPE_SEMANTICS = {
	"n": "normal",
	"w": "directed solid wedge",
	"h": "directed hashed wedge",
	"a": "adder or unspecified stereochemistry",
	"b": "bold",
	"d": "dashed",
	"o": "dotted",
	"s": "wavy",
	"q": "Haworth front edge",
}

# Ordinary styles retain their established single, double, and triple forms.
# A Haworth front edge is one explicit drawing convention rather than a
# generic fourth bond order.
AUTHORED_BOND_ORDERS = {
	"n": (1, 2, 3),
	"w": (1, 2, 3),
	"h": (1, 2, 3),
	"a": (1, 2, 3),
	"b": (1, 2, 3),
	"d": (1, 2, 3),
	"o": (1, 2, 3),
	"s": (1, 2, 3),
	"q": (1,),
}

# Retain the long-standing public constant for OASA callers.
BOND_TYPES = tuple(BOND_TYPE_SEMANTICS)
LEGACY_BOND_TYPES = {
	"l": "h",
	"r": "h",
}


#============================================
def authored_bond_orders(bond_type: str) -> tuple:
	"""Return authored orders for one canonical CDML bond type.

	Args:
		bond_type: Canonical one-character CDML bond style.

	Returns:
		Tuple of permitted integer orders, or an empty tuple for an unknown type.
	"""
	orders = AUTHORED_BOND_ORDERS.get(bond_type)
	if orders is None:
		return ()
	return orders


#============================================
def is_authored_bond_order(bond_type: str, order: int) -> bool:
	"""Return whether one canonical CDML style/order pair is authorable.

	Args:
		bond_type: Canonical one-character CDML bond style.
		order: Requested integer bond order.

	Returns:
		True when the pair is part of the authored CDML profile.
	"""
	return order in authored_bond_orders(bond_type)


#============================================
def normalize_bond_type_char(bond_type: str) -> tuple:
	"""Normalize a single-character bond type.

	Args:
		bond_type (str): Single-character bond type.

	Returns:
		tuple[str | None, str | None]: (normalized, legacy_type)
	"""
	if not bond_type:
		return None, None
	normalized = LEGACY_BOND_TYPES.get(bond_type, bond_type)
	legacy = bond_type if normalized != bond_type else None
	return normalized, legacy


#============================================
def parse_cdml_bond_type(value: str) -> tuple:
	"""Parse a CDML bond type string like "n1".

	Args:
		value (str): CDML bond type value.

	Returns:
		tuple[str | None, int, str | None]: (type_char, order, legacy_type)
	"""
	if not value:
		return None, 0, None
	bond_type = value[0]
	order_value = value[1:]
	order = 1
	if order_value:
		try:
			order = int(order_value)
		except ValueError:
			order = 1
	normalized, legacy = normalize_bond_type_char(bond_type)
	return normalized, order, legacy


#============================================
def canonicalize_bond_vertices(bond: object, layout_ctx: object=None) -> object:
	"""Canonicalize bond vertices for deterministic wedge/hashed direction.

	Args:
		bond: Bond-like object with .type and .vertices.
		layout_ctx: Optional layout context for orientation.

	Returns:
		The bond instance (mutated in place).
	"""
	if not bond or bond.type not in ("w", "h"):
		return bond
	vertices = getattr(bond, "vertices", None)
	if not vertices or len(vertices) != 2:
		return bond
	v1, v2 = vertices
	front = _resolve_front_vertex(v1, v2, layout_ctx)
	if front is None:
		return bond
	if v2 is not front:
		bond.set_vertices((v2, v1))
	return bond


#============================================
def _resolve_front_vertex(v1: object, v2: object, layout_ctx: object=None) -> object | None:
	"""Select the front vertex using layout context or geometry."""
	front_vertices = _get_layout_value(layout_ctx, "front_vertices")
	if front_vertices:
		v1_front = v1 in front_vertices
		v2_front = v2 in front_vertices
		if v1_front and not v2_front:
			return v1
		if v2_front and not v1_front:
			return v2
	coords1 = _get_vertex_xy(v1)
	coords2 = _get_vertex_xy(v2)
	if coords1 is None or coords2 is None:
		return None
	x1, y1 = coords1
	x2, y2 = coords2
	if y1 > y2:
		return v1
	if y2 > y1:
		return v2
	if x1 > x2:
		return v1
	if x2 > x1:
		return v2
	return None


#============================================
def _get_layout_value(layout_ctx: object, name: str) -> object | None:
	"""Fetch a layout attribute from an object or dict."""
	if layout_ctx is None:
		return None
	if hasattr(layout_ctx, name):
		return getattr(layout_ctx, name)
	if isinstance(layout_ctx, dict):
		return layout_ctx.get(name)
	return None


#============================================
def _get_vertex_xy(vertex: object) -> tuple | None:
	"""Return (x, y) for a vertex if available."""
	if vertex is None:
		return None
	x = getattr(vertex, "x", None)
	y = getattr(vertex, "y", None)
	if x is not None and y is not None:
		return x, y
	get_xy = getattr(vertex, "get_xy", None)
	if callable(get_xy):
		return get_xy()
	return None
