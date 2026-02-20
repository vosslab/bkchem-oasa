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

"""Bond length profile and normalization for render operations."""

# Standard Library
import math

# local repo modules
from oasa.render_lib.data_types import BOND_LENGTH_EXCEPTION_TAGS
from oasa.render_lib.data_types import BOND_LENGTH_PROFILE
from oasa.render_lib.data_types import VALID_BOND_STYLES


#============================================
def bond_length_profile() -> dict[str, float]:
	"""Return immutable-copy style-length profile ratios."""
	return dict(BOND_LENGTH_PROFILE)


#============================================
def _normalize_bond_style(bond_style: str) -> str:
	"""Normalize one bond-style selector to canonical style key."""
	if bond_style is None:
		raise ValueError("bond_style must not be None")
	normalized = str(bond_style).strip().lower()
	if normalized not in VALID_BOND_STYLES:
		raise ValueError(f"Invalid bond_style value: {bond_style!r}")
	return normalized


#============================================
def _normalize_exception_tag(exception_tag: str | None) -> str | None:
	"""Normalize one optional exception tag."""
	if exception_tag is None:
		return None
	normalized = str(exception_tag).strip()
	if normalized not in BOND_LENGTH_EXCEPTION_TAGS:
		raise ValueError(f"Invalid bond-length exception tag: {exception_tag!r}")
	return normalized


#============================================
def resolve_bond_length(
		base_length: float,
		bond_style: str,
		requested_length: float | None = None,
		exception_tag: str | None = None) -> float:
	"""Resolve one style-policy bond length with tagged exception enforcement."""
	base_value = float(base_length)
	if base_value < 0.0:
		raise ValueError(f"base_length must be >= 0.0, got {base_length!r}")
	style_key = _normalize_bond_style(bond_style)
	default_length = base_value * float(BOND_LENGTH_PROFILE[style_key])
	if requested_length is None:
		return default_length
	requested = float(requested_length)
	if requested < 0.0:
		raise ValueError(f"requested_length must be >= 0.0, got {requested_length!r}")
	if math.isclose(requested, default_length, abs_tol=1e-9):
		return requested
	tag = _normalize_exception_tag(exception_tag)
	if tag is None:
		raise ValueError(
			"Non-default bond length requires one exception tag from "
			f"{BOND_LENGTH_EXCEPTION_TAGS!r}"
		)
	if tag == "EXC_OXYGEN_AVOID_UP" and requested < (default_length - 1e-9):
		raise ValueError("EXC_OXYGEN_AVOID_UP may only lengthen relative to style default")
	if tag == "EXC_RING_INTERIOR_CLEARANCE" and requested > (default_length + 1e-9):
		raise ValueError("EXC_RING_INTERIOR_CLEARANCE may only shorten relative to style default")
	return requested


#============================================
def _bond_style_for_edge(edge) -> str:
	"""Map one render edge to the canonical bond-style policy key."""
	try:
		order = int(getattr(edge, "order", 1) or 1)
	except Exception:
		order = 1
	if order == 2:
		return "double"
	if order == 3:
		return "triple"
	type_text = str(getattr(edge, "type", "") or "").strip().lower()
	if type_text == "w":
		return "rounded_wedge"
	if type_text == "h":
		return "hashed_wedge"
	if type_text == "s":
		return "wavy"
	if type_text == "d":
		return "dashed_hbond"
	return "single"
