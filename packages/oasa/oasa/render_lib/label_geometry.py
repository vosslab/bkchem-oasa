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

"""Label text, label boxes, label targets, and attach contracts."""

# Standard Library
import re

# local repo modules
from oasa import oasa_utils as misc
from oasa import render_ops
from oasa.render_lib.data_types import ATTACH_GAP_TARGET
from oasa.render_lib.data_types import AttachConstraints
from oasa.render_lib.data_types import LabelAttachContract
from oasa.render_lib.data_types import LabelAttachPolicy
from oasa.render_lib.data_types import _normalize_attach_site
from oasa.render_lib.data_types import _normalize_element_symbol
from oasa.render_lib.data_types import make_box_target
from oasa.render_lib.data_types import make_circle_target
from oasa.render_lib.data_types import make_composite_target
from oasa.render_lib.glyph_model import glyph_attach_primitive
from oasa.render_lib.attach_resolution import _correct_endpoint_for_alignment
from oasa.render_lib.attach_resolution import _min_distance_point_to_target_boundary
from oasa.render_lib.attach_resolution import _retreat_to_target_gap
from oasa.render_lib.attach_resolution import resolve_attach_endpoint
from oasa.render_lib.attach_resolution import retreat_endpoint_until_legal

try:
	import cairo as _cairo
except ImportError:
	_cairo = None


#============================================
def vertex_is_shown(vertex):
	if vertex.properties_.get("label"):
		return True
	return vertex.symbol != "C" or vertex.charge != 0 or vertex.multiplicity != 1


#============================================
def vertex_label_text(vertex, show_hydrogens_on_hetero):
	label = vertex.properties_.get("label")
	if label:
		text = label
	else:
		text = vertex.symbol
		if show_hydrogens_on_hetero:
			if vertex.free_valency == 1:
				text += "H"
			elif vertex.free_valency > 1:
				text += "H%d" % vertex.free_valency
	# only append charge as text if no circled marks handle it
	if not vertex.properties_.get("marks"):
		if vertex.charge == 1:
			text += "+"
		elif vertex.charge == -1:
			text += "-"
		elif vertex.charge > 1:
			text += str(vertex.charge) + "+"
		elif vertex.charge < -1:
			text += str(vertex.charge)
	return text


#============================================
def _visible_label_text(text):
	return re.sub(r"<[^>]+>", "", text or "")


#============================================
def _visible_label_length(text):
	return max(1, len(_visible_label_text(text)))


#============================================
def _is_hydroxyl_render_text(text):
	"""Return True when visible text is one hydroxyl token."""
	visible = _visible_label_text(text)
	return visible in ("OH", "HO")


#============================================
def _is_chain_like_render_text(text):
	"""Return True for rendered chain-like carbon labels."""
	visible = _visible_label_text(text)
	if visible.startswith("CH"):
		return True
	# Left-anchored CH2OH labels can render as HOH2C while still attaching to C.
	return visible.endswith("C") and ("H2" in visible)


#============================================
def _text_char_advances(text, font_size, font_name):
	"""Return per-visible-character x advances for one formatted text value."""
	visible = _visible_label_text(text)
	if not visible:
		return []
	fallback = [font_size * 0.60] * len(visible)
	if _cairo is None:
		return fallback
	try:
		surface = _cairo.ImageSurface(_cairo.FORMAT_A8, 1, 1)
		context = _cairo.Context(surface)
		context.select_font_face(font_name or "sans-serif", 0, 0)
	except Exception:
		return fallback
	segments = render_ops._text_segments(str(text or ""))
	advances = []
	for chunk, tags in segments:
		segment_state = render_ops._segment_baseline_state(tags)
		segment_size = render_ops._segment_font_size(font_size, segment_state)
		context.set_font_size(segment_size)
		previous_advance = 0.0
		for index in range(len(chunk)):
			prefix = chunk[: index + 1]
			extents = context.text_extents(prefix)
			char_advance = max(0.0, float(extents.x_advance) - previous_advance)
			advances.append(char_advance)
			previous_advance = float(extents.x_advance)
	if len(advances) != len(visible):
		return fallback
	return advances


#============================================
def _text_ink_bearing_correction(text, font_size, font_name):
	"""Return (left_bearing, right_bearing) for the visible label text.

	The left bearing is the gap between the text origin and the first ink pixel.
	The right bearing is the gap between the last ink pixel and the advance end.
	These represent the amount by which sum(advances) overestimates ink width.
	"""
	visible = _visible_label_text(text)
	if not visible:
		return (0.0, 0.0)
	if _cairo is None:
		return (0.0, 0.0)
	try:
		surface = _cairo.ImageSurface(_cairo.FORMAT_A8, 1, 1)
		context = _cairo.Context(surface)
		context.select_font_face(font_name or "sans-serif", 0, 0)
	except Exception:
		return (0.0, 0.0)
	segments = render_ops._text_segments(str(text or ""))
	# Get left bearing of first segment's first character
	left_bearing = 0.0
	for chunk, tags in segments:
		if not chunk:
			continue
		segment_state = render_ops._segment_baseline_state(tags)
		segment_size = render_ops._segment_font_size(font_size, segment_state)
		context.set_font_size(segment_size)
		first_char = chunk[0]
		extents = context.text_extents(first_char)
		left_bearing = max(0.0, float(extents.x_bearing))
		break
	# Get right bearing of last segment's last character
	right_bearing = 0.0
	for chunk, tags in reversed(segments):
		if not chunk:
			continue
		segment_state = render_ops._segment_baseline_state(tags)
		segment_size = render_ops._segment_font_size(font_size, segment_state)
		context.set_font_size(segment_size)
		last_char = chunk[-1]
		extents = context.text_extents(last_char)
		# right_bearing = advance - left_bearing - ink_width
		char_right = float(extents.x_advance) - float(extents.x_bearing) - float(extents.width)
		right_bearing = max(0.0, char_right)
		break
	return (left_bearing, right_bearing)


#============================================
def _label_text_origin(x, y, anchor, font_size, text_len):
	del text_len
	baseline_offset = font_size * 0.375
	start_offset = font_size * 0.3125
	if anchor == "start":
		return (x - start_offset, y + baseline_offset)
	return (x, y + baseline_offset)


#============================================
def _core_element_span_box(
		entry,
		span_x1,
		span_x2,
		font_size,
		glyph_char_width,
		attach_site,
		font_name):
	"""Return attach box bounds for one core element glyph span."""
	attach_site = _normalize_attach_site(attach_site)
	symbol = str(entry.get("symbol", ""))
	# Keep multi-letter core spans (for example Cl/Br) unchanged.
	if len(symbol) != 1:
		return (span_x1, span_x2)
	del glyph_char_width
	primitive = glyph_attach_primitive(
		symbol=symbol,
		span_x1=span_x1,
		span_x2=span_x2,
		y1=0.0,
		y2=1.0,
		font_size=font_size,
		font_name=font_name or "sans-serif",
	)
	site_box = primitive.site_box(attach_site)
	return (site_box[0], site_box[2])


#============================================
def _tokenized_atom_spans(text):
	"""Return decorated token spans for visible label text.

	Decorated spans include compact hydrogen/count suffixes (for example `CH2`)
	so existing first/last-token attachment behavior remains stable.
	"""
	return [entry["decorated_span"] for entry in _tokenized_atom_entries(text)]


#============================================
def _tokenized_atom_entries(text):
	"""Return atom token entries with core/decorated span information.

	Each entry exposes:
	- `core_span`: element-symbol-only span (for example `C` in `CH2`)
	- `decorated_span`: element plus compact suffix decoration span
	  (for example `CH2`)
	"""
	visible_text = _visible_label_text(text)
	entries = []
	length = len(visible_text)
	index = 0
	while index < length:
		char = visible_text[index]
		if not char.isupper():
			index += 1
			continue
		core_start = index
		index += 1
		if index < length and visible_text[index].islower():
			index += 1
		core_end = index
		symbol = visible_text[core_start:core_end]
		decorated_end = core_end
		# Optional atom count directly after the symbol, e.g. O3.
		while decorated_end < length and visible_text[decorated_end].isdigit():
			decorated_end += 1
		has_explicit_count = decorated_end > core_end
		# Condensed hydrogens belong to the decorated token unless this atom
		# already had an explicit numeric count (e.g. O3H should tokenize as O3 + H).
		if symbol != "H" and not has_explicit_count and decorated_end < length and visible_text[decorated_end] == "H":
			decorated_end += 1
			while decorated_end < length and visible_text[decorated_end].isdigit():
				decorated_end += 1
		# Optional trailing charge on terminal tokens, e.g. NH3+.
		if decorated_end < length and visible_text[decorated_end] in "+-":
			charge_end = decorated_end + 1
			while charge_end < length and visible_text[charge_end].isdigit():
				charge_end += 1
			if charge_end == length:
				decorated_end = charge_end
		entries.append(
			{
				"symbol": symbol,
				"core_span": (core_start, core_end),
				"decorated_span": (core_start, decorated_end),
			}
		)
		index = max(index, decorated_end)
	return entries


#============================================
def _label_box_coords(x, y, text, anchor, font_size, font_name=None):
	"""Compute axis-aligned label box coordinates at one label anchor point."""
	text_len = _visible_label_length(text)
	char_advances = _text_char_advances(text, font_size, font_name or "sans-serif")
	if char_advances and len(char_advances) == text_len:
		box_width = sum(char_advances)
	else:
		box_width = font_size * 0.60 * text_len
	# Empirically calibrated against rsvg/Pango rendering of sans-serif at 12pt.
	# top_offset: ascent above baseline (calibrated: 8.8 / 12.0 = 0.733)
	# bottom_offset: descent below baseline (calibrated: 0.1 / 12.0 = 0.008)
	top_offset = -font_size * 0.733
	bottom_offset = font_size * 0.008
	text_x, text_y = _label_text_origin(x, y, anchor, font_size, text_len)
	if anchor == "start":
		x1 = text_x
		x2 = text_x + box_width
	elif anchor == "end":
		x1 = text_x - box_width
		x2 = text_x
	else:
		x1 = text_x - box_width / 2.0
		x2 = text_x + box_width / 2.0
	y1 = text_y + top_offset
	y2 = text_y + bottom_offset
	return misc.normalize_coords((x1, y1, x2, y2))


#============================================
def label_target(x, y, text, anchor, font_size, font_name=None):
	"""Compute one label attachment target at (x, y)."""
	return make_box_target(_label_box_coords(x, y, text, anchor, font_size, font_name=font_name))


#============================================
def label_target_from_text_origin(text_x, text_y, text, anchor, font_size, font_name=None):
	"""Compute one label attachment target from text-origin coordinates."""
	start_offset = font_size * 0.3125
	baseline_offset = font_size * 0.375
	label_x = text_x
	if anchor == "start":
		label_x = text_x + start_offset
	label_y = text_y - baseline_offset
	return label_target(label_x, label_y, text, anchor, font_size, font_name=font_name)


#============================================
def label_attach_target_from_text_origin(
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		attach_element=None,
		attach_site=None,
		font_name=None):
	"""Compute one token-attach target from text-origin coordinates."""
	start_offset = font_size * 0.3125
	baseline_offset = font_size * 0.375
	label_x = text_x
	if anchor == "start":
		label_x = text_x + start_offset
	label_y = text_y - baseline_offset
	return label_attach_target(
		label_x,
		label_y,
		text,
		anchor,
		font_size,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		font_name=font_name,
	)


def _label_attach_box_coords(
		x,
		y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		attach_element=None,
		attach_site=None,
		font_name=None):
	"""Compute box coordinates for one selected attachable atom token."""
	if attach_atom is None:
		attach_atom = "first"
	if attach_atom not in ("first", "last"):
		raise ValueError(f"Invalid attach_atom value: {attach_atom!r}")
	normalized_attach_element = None
	if attach_element is not None:
		if not isinstance(attach_element, str) or not attach_element.strip():
			raise ValueError(f"Invalid attach_element value: {attach_element!r}")
		normalized_attach_element = _normalize_element_symbol(attach_element)
	if attach_site is None:
		if normalized_attach_element == "C":
			attach_site = "closed_center"
		else:
			attach_site = "core_center"
	else:
		attach_site = _normalize_attach_site(attach_site)
	full_bbox = _label_box_coords(x, y, text, anchor, font_size, font_name=font_name)
	entries = _tokenized_atom_entries(text)
	if not entries:
		return full_bbox
	spans = [entry["decorated_span"] for entry in entries]
	selected_span = None
	selected_entry = None
	if normalized_attach_element is not None:
		# Formula-aware attachment: attach_element resolves to the core element
		# glyph span (for example just "C" in CH2OH), not the decorated token.
		matched = [entry for entry in entries if entry["symbol"] == normalized_attach_element]
		if matched:
			if attach_atom == "last":
				selected_entry = matched[-1]
			else:
				selected_entry = matched[0]
			selected_span = selected_entry["core_span"]
	if selected_span is None:
		if len(spans) <= 1:
			return full_bbox
		if attach_atom == "last":
			selected_span = spans[-1]
		else:
			selected_span = spans[0]
	start_index, end_index = selected_span
	visible_len = _visible_label_length(text)
	if visible_len <= 1:
		return full_bbox
	x1, y1, x2, y2 = full_bbox
	# Project token spans using the same segmented text metrics model that
	# render_ops uses for markup-aware text drawing.
	char_advances = _text_char_advances(text, font_size, font_name or "sans-serif")
	if len(char_advances) != visible_len:
		char_advances = [font_size * 0.60] * visible_len
	cumulative_advances = [0.0]
	for advance in char_advances:
		cumulative_advances.append(cumulative_advances[-1] + float(advance))
	glyph_width = cumulative_advances[-1]
	glyph_char_width = glyph_width / float(visible_len) if visible_len else (font_size * 0.60)
	text_x, _text_y = _label_text_origin(x, y, anchor, font_size, visible_len)
	if anchor == "start":
		glyph_x1 = text_x
	elif anchor == "end":
		glyph_x1 = text_x - glyph_width
	else:
		glyph_x1 = text_x - (glyph_width / 2.0)
	span_x1 = glyph_x1 + cumulative_advances[start_index]
	span_x2 = glyph_x1 + cumulative_advances[end_index]
	if selected_entry is not None:
		attach_x1, attach_x2 = _core_element_span_box(
			selected_entry,
			span_x1,
			span_x2,
			font_size,
			glyph_char_width,
			attach_site=attach_site,
			font_name=font_name or "sans-serif",
		)
	else:
		attach_x1 = span_x1
		attach_x2 = span_x2
	# Clamp to full label bbox so attach targets cannot escape label bounds.
	attach_x1 = min(max(attach_x1, x1), x2)
	attach_x2 = min(max(attach_x2, x1), x2)
	return misc.normalize_coords((attach_x1, y1, attach_x2, y2))


#============================================
def label_attach_target(
		x,
		y,
		text,
		anchor,
		font_size,
		attach_atom="first",
		attach_element=None,
		attach_site=None,
		font_name=None):
	"""Compute one attach-token target within a label."""
	return make_box_target(
		_label_attach_box_coords(
			x,
			y,
			text,
			anchor,
			font_size,
			attach_atom=attach_atom,
			attach_element=attach_element,
			attach_site=attach_site,
			font_name=font_name,
		)
	)


#============================================
def default_label_attach_policy(text, chain_attach_site="core_center") -> LabelAttachPolicy:
	"""Return runtime-default attach policy for one rendered label text."""
	site = _normalize_attach_site(chain_attach_site)
	visible = _visible_label_text(text)
	if _is_hydroxyl_render_text(visible):
		attach_atom = "first" if visible == "OH" else "last"
		return LabelAttachPolicy(
			attach_atom=attach_atom,
			attach_element="O",
			attach_site="core_center",
			target_kind="oxygen_circle",
		)
	if _is_chain_like_render_text(visible):
		return LabelAttachPolicy(
			attach_atom="first",
			attach_element="C",
			attach_site=site,
			target_kind="label_box",
		)
	return LabelAttachPolicy(
		attach_atom="first",
		attach_element=None,
		attach_site="core_center",
		target_kind="attach_box",
	)


#============================================
def _resolve_label_attach_policy(
		text,
		attach_atom=None,
		attach_element=None,
		attach_site=None,
		chain_attach_site="core_center",
		target_kind=None):
	"""Resolve one explicit-or-default label attach policy."""
	default_policy = default_label_attach_policy(
		text=text,
		chain_attach_site=chain_attach_site,
	)
	resolved_atom = default_policy.attach_atom if attach_atom is None else attach_atom
	if resolved_atom not in ("first", "last"):
		raise ValueError(f"Invalid attach_atom value: {attach_atom!r}")
	resolved_element = default_policy.attach_element if attach_element is None else attach_element
	normalized_element = None
	if resolved_element is not None:
		normalized_element = _normalize_element_symbol(resolved_element)
	if attach_site is None:
		resolved_site = default_policy.attach_site
	else:
		resolved_site = _normalize_attach_site(attach_site)
	resolved_target_kind = default_policy.target_kind if target_kind is None else str(target_kind).strip().lower()
	if resolved_target_kind not in ("attach_box", "label_box", "oxygen_circle"):
		raise ValueError(f"Unsupported label endpoint target_kind: {target_kind!r}")
	return LabelAttachPolicy(
		attach_atom=resolved_atom,
		attach_element=normalized_element,
		attach_site=resolved_site,
		target_kind=resolved_target_kind,
	)


#============================================
def _oxygen_circle_target_from_attach_target(
		attach_target,
		font_size,
		line_width):
	"""Return hydroxyl O-centered circle target from one attach box."""
	x1, y1, x2, y2 = attach_target.box
	center = ((x1 + x2) * 0.5, (y1 + y2) * 0.5)
	base_radius = max(max(0.0, x2 - x1), max(0.0, y2 - y1)) * 0.5
	# Keep hydroxyl endpoint targeting near the glyph perimeter so connector
	# endpoints remain visually attached to the oxygen shape in matrix output.
	safety_margin = max(0.05, float(font_size) * 0.005)
	line_margin = max(0.0, float(line_width)) * 0.05
	radius = base_radius + line_margin + safety_margin
	return make_circle_target(center, radius)


#============================================
def _oxygen_allowed_target(full_target, endpoint_target):
	"""Return paint-allowed target for hydroxyl oxygen circles."""
	if full_target.kind != "box" or endpoint_target.kind != "circle":
		return endpoint_target
	return make_composite_target((endpoint_target, full_target))


#============================================
def _chain_attach_allowed_target(
		full_target,
		attach_target):
	"""Return paint-allowed target corridors for chain-like C attachment."""
	if full_target.kind != "box" or attach_target.kind != "box":
		return attach_target
	full_x1, full_y1, full_x2, full_y2 = full_target.box
	attach_x1, attach_y1, attach_x2, attach_y2 = attach_target.box
	targets = [attach_target]
	if full_x1 < attach_x1:
		targets.append(make_box_target((full_x1, attach_y1, attach_x1, attach_y2)))
	if attach_x2 < full_x2:
		targets.append(make_box_target((attach_x2, attach_y1, full_x2, attach_y2)))
	if full_y1 < attach_y1:
		targets.append(make_box_target((attach_x1, full_y1, attach_x2, attach_y1)))
	if attach_y2 < full_y2:
		targets.append(make_box_target((attach_x1, attach_y2, attach_x2, full_y2)))
	if len(targets) == 1:
		return attach_target
	return make_composite_target(tuple(targets))


#============================================
def label_allowed_target_from_text_origin(
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		line_width=0.0,
		attach_atom=None,
		attach_element=None,
		attach_site=None,
		chain_attach_site="core_center",
		target_kind=None,
		font_name=None):
	"""Resolve one paint-allowed label target from text-origin inputs."""
	contract = label_attach_contract_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		line_width=line_width,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		chain_attach_site=chain_attach_site,
		target_kind=target_kind,
		font_name=font_name,
	)
	return contract.allowed_target


#============================================
def label_attach_contract_from_text_origin(
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		line_width=0.0,
		attach_atom=None,
		attach_element=None,
		attach_site=None,
		chain_attach_site="core_center",
		target_kind=None,
		font_name=None):
	"""Resolve full runtime attach contract for one label at text origin."""
	policy = _resolve_label_attach_policy(
		text=text,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		chain_attach_site=chain_attach_site,
		target_kind=target_kind,
	)
	full_target = label_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		font_name=font_name,
	)
	attach_target = label_attach_target_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		attach_atom=policy.attach_atom,
		attach_element=policy.attach_element,
		attach_site=policy.attach_site,
		font_name=font_name,
	)
	endpoint_target = attach_target
	if policy.target_kind == "label_box":
		# Full-box bond trimming: use the entire label bounding box
		# for both endpoint and paint-allowed targets.
		endpoint_target = full_target
	elif policy.target_kind == "oxygen_circle":
		endpoint_target = _oxygen_circle_target_from_attach_target(
			attach_target=attach_target,
			font_size=font_size,
			line_width=line_width,
		)
	allowed_target = endpoint_target
	if policy.target_kind == "label_box":
		allowed_target = full_target
	elif policy.target_kind == "oxygen_circle":
		allowed_target = _oxygen_allowed_target(
			full_target=full_target,
			endpoint_target=endpoint_target,
		)
	elif (
			policy.target_kind == "attach_box"
			and policy.attach_element == "C"
			and endpoint_target.kind == "box"
			and full_target.kind == "box"
	):
		allowed_target = _chain_attach_allowed_target(
			full_target=full_target,
			attach_target=endpoint_target,
		)
	return LabelAttachContract(
		policy=policy,
		full_target=full_target,
		attach_target=attach_target,
		endpoint_target=endpoint_target,
		allowed_target=allowed_target,
	)


#============================================
def resolve_label_connector_endpoint_from_text_origin(
		bond_start,
		text_x,
		text_y,
		text,
		anchor,
		font_size,
		line_width=0.0,
		constraints=None,
		epsilon=0.5,
		attach_atom=None,
		attach_element=None,
		attach_site=None,
		chain_attach_site="core_center",
		target_kind=None,
		font_name=None):
	"""Resolve one connector endpoint via the shared label attach contract."""
	contract = label_attach_contract_from_text_origin(
		text_x=text_x,
		text_y=text_y,
		text=text,
		anchor=anchor,
		font_size=font_size,
		line_width=line_width,
		attach_atom=attach_atom,
		attach_element=attach_element,
		attach_site=attach_site,
		chain_attach_site=chain_attach_site,
		target_kind=target_kind,
		font_name=font_name,
	)
	if constraints is None:
		constraints = AttachConstraints()
	endpoint = resolve_attach_endpoint(
		bond_start=bond_start,
		target=contract.endpoint_target,
		interior_hint=contract.endpoint_target.centroid(),
		constraints=constraints,
	)
	# Label-box mode skips automatic alignment toward the attach-atom
	# centroid (the caller already positioned the text via anchor_x_offset
	# or _align_text_origin_*). An explicit alignment_center in
	# constraints is still honoured (used by chain ops for collinearity).
	if contract.policy.target_kind == "label_box":
		alignment_center = constraints.alignment_center
	else:
		alignment_center = constraints.alignment_center
		if alignment_center is None:
			alignment_center = contract.attach_target.centroid()
	if alignment_center is not None:
		endpoint = _correct_endpoint_for_alignment(
			bond_start=bond_start,
			endpoint=endpoint,
			alignment_center=alignment_center,
			target=contract.endpoint_target,
			tolerance=constraints.alignment_tolerance,
		)
	endpoint = retreat_endpoint_until_legal(
		line_start=bond_start,
		line_end=endpoint,
		line_width=line_width,
		forbidden_regions=[contract.full_target],
		allowed_regions=[contract.allowed_target],
		epsilon=epsilon,
	)
	if constraints.target_gap > 0.0:
		endpoint = _retreat_to_target_gap(
			line_start=bond_start,
			legal_endpoint=endpoint,
			target_gap=constraints.target_gap,
			forbidden_regions=[contract.endpoint_target],
		)
		# When endpoint_target is already the full label box (label_box
		# mode), the second retreat is redundant -- skip it.
		if contract.policy.target_kind != "label_box":
			# After retreating from the endpoint atom, the bond may still be
			# too close to the full label box (e.g. the bond over "HOH2C"
			# clears the C glyph but passes above the "2" subscript).
			# Apply a minimum gap from the full label using the base gap
			# constant, not the (possibly larger) connector-specific target.
			full_text_min_gap = ATTACH_GAP_TARGET
			full_gap = _min_distance_point_to_target_boundary(
				endpoint, contract.full_target,
			)
			if full_gap < full_text_min_gap:
				endpoint = _retreat_to_target_gap(
					line_start=bond_start,
					legal_endpoint=endpoint,
					target_gap=full_text_min_gap,
					forbidden_regions=[contract.full_target],
				)
	return endpoint, contract
