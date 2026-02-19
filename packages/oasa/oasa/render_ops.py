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

"""Render ops for shared Cairo/SVG drawing."""

# Standard Library
import dataclasses
import json
import math

# local repo modules
from oasa import dom_extensions
from oasa import safe_xml


#============================================
@dataclasses.dataclass(frozen=True)
class LineOp:
	p1: tuple[float, float]
	p2: tuple[float, float]
	width: float
	cap: str = "butt"
	join: str = ""
	color: object | None = None
	z: int = 0
	op_id: str | None = None


#============================================
@dataclasses.dataclass(frozen=True)
class PolygonOp:
	points: tuple[tuple[float, float], ...]
	fill: object | None
	stroke: object | None = None
	stroke_width: float = 0.0
	z: int = 0
	op_id: str | None = None


#============================================
@dataclasses.dataclass(frozen=True)
class CircleOp:
	center: tuple[float, float]
	radius: float
	fill: object | None
	stroke: object | None = None
	stroke_width: float = 0.0
	z: int = 0
	op_id: str | None = None


#============================================
@dataclasses.dataclass(frozen=True)
class PathOp:
	commands: tuple[tuple[str, tuple[float, ...] | None], ...]
	fill: object | None
	stroke: object | None = None
	stroke_width: float = 0.0
	cap: str = ""
	join: str = ""
	z: int = 0
	op_id: str | None = None


#============================================
@dataclasses.dataclass(frozen=True)
class TextOp:
	x: float
	y: float
	text: str
	font_size: float = 12.0
	font_name: str = "sans-serif"
	anchor: str = "start"
	weight: str = "normal"
	color: object | None = None
	z: int = 0
	op_id: str | None = None


#============================================
def _text_segments(text):
	if "<" not in text and ">" not in text:
		return [(text, set())]
	try:
		root = safe_xml.parse_xml_string(f"<text>{text}</text>")
	except Exception:
		return [(text, set())]
	segments = []

	def _walk(node, attrs):
		if node.text:
			segments.append((node.text, set(attrs)))
		for child in list(node):
			_walk(child, attrs + [child.tag])
			if child.tail:
				segments.append((child.tail, set(attrs)))

	_walk(root, [])
	return segments


#============================================
def _segment_baseline_state(tags):
	if "sub" in tags:
		return "sub"
	if "sup" in tags:
		return "sup"
	return "base"


#============================================
SCRIPT_FONT_SCALE = 0.65
SUBSCRIPT_OFFSET_EM = 0.40
SUPERSCRIPT_OFFSET_EM = 0.45


#============================================
def _segment_font_size(font_size, baseline_state):
	if baseline_state in ("sub", "sup"):
		return font_size * SCRIPT_FONT_SCALE
	return font_size


#============================================
def _baseline_offset_em(baseline_state):
	if baseline_state == "sub":
		return SUBSCRIPT_OFFSET_EM
	if baseline_state == "sup":
		return -SUPERSCRIPT_OFFSET_EM
	return 0.0


#============================================
def _baseline_transition_dy_em(previous_state, next_state):
	return _baseline_offset_em(next_state) - _baseline_offset_em(previous_state)


#============================================
def _baseline_transition_dy_px(font_size, previous_state, next_state):
	"""Return absolute SVG dy in user units for one baseline-state change."""
	return font_size * _baseline_transition_dy_em(previous_state, next_state)


#============================================
def _normalize_hex_color(text):
	if text.lower() == "none":
		return "none"
	if not text.startswith("#"):
		return text
	value = text[1:]
	if len(value) == 3:
		value = "".join(ch * 2 for ch in value)
	if len(value) != 6:
		return text
	return "#" + value.lower()


#============================================
def _color_tuple_to_hex(color):
	if len(color) not in (3, 4):
		return None
	values = list(color[:3])
	scale = 255.0
	if max(values) <= 1.0:
		scale = 255.0
	else:
		scale = 1.0
	channels = []
	for value in values:
		channel = int(round(value * scale))
		channel = max(0, min(channel, 255))
		channels.append(channel)
	return "#%02x%02x%02x" % (channels[0], channels[1], channels[2])


#============================================
def color_to_hex(color):
	if color is None:
		return None
	if isinstance(color, str):
		text = color.strip()
		if not text:
			return None
		return _normalize_hex_color(text)
	if isinstance(color, (tuple, list)):
		return _color_tuple_to_hex(color)
	return None


#============================================
def _color_to_rgba(color):
	if color is None:
		return None
	if isinstance(color, str):
		text = color.strip()
		if not text or text.lower() == "none":
			return None
		if not text.startswith("#"):
			return None
		value = text[1:]
		if len(value) == 3:
			value = "".join(ch * 2 for ch in value)
		if len(value) != 6:
			return None
		r = int(value[0:2], 16) / 255.0
		g = int(value[2:4], 16) / 255.0
		b = int(value[4:6], 16) / 255.0
		return (r, g, b, 1.0)
	if isinstance(color, (tuple, list)):
		if len(color) not in (3, 4):
			return None
		scale = 1.0
		values = list(color)
		if max(values) > 1.0:
			scale = 1.0 / 255.0
		r = values[0] * scale
		g = values[1] * scale
		b = values[2] * scale
		a = values[3] if len(values) == 4 else 1.0
		if max(r, g, b, a) > 1.0:
			r = min(r, 1.0)
			g = min(g, 1.0)
			b = min(b, 1.0)
			a = min(a, 1.0)
		return (r, g, b, a)
	return None


#============================================
def sort_ops(ops):
	ordered = []
	for index, op in sorted(enumerate(ops), key=lambda item: (getattr(item[1], "z", 0), item[0])):
		ordered.append(op)
	return ordered


#============================================
def _serialize_number(value, digits):
	if isinstance(value, int):
		return value
	if isinstance(value, float):
		return round(value, digits)
	return value


#============================================
def _serialize_list(value, digits):
	return [ _serialize_number(item, digits) for item in value ]


#============================================
def ops_to_json_dict(ops, round_digits=3):
	serialized = []
	for op in sort_ops(ops):
		if isinstance(op, LineOp):
			entry = {
				"kind": "line",
				"p1": _serialize_list(op.p1, round_digits),
				"p2": _serialize_list(op.p2, round_digits),
				"width": _serialize_number(op.width, round_digits),
				"cap": op.cap,
				"join": op.join,
				"color": color_to_hex(op.color),
				"z": op.z,
			}
		elif isinstance(op, PolygonOp):
			entry = {
				"kind": "polygon",
				"points": [ _serialize_list(point, round_digits) for point in op.points ],
				"fill": color_to_hex(op.fill),
				"stroke": color_to_hex(op.stroke),
				"stroke_width": _serialize_number(op.stroke_width, round_digits),
				"z": op.z,
			}
		elif isinstance(op, CircleOp):
			entry = {
				"kind": "circle",
				"center": _serialize_list(op.center, round_digits),
				"radius": _serialize_number(op.radius, round_digits),
				"fill": color_to_hex(op.fill),
				"stroke": color_to_hex(op.stroke),
				"stroke_width": _serialize_number(op.stroke_width, round_digits),
				"z": op.z,
			}
		elif isinstance(op, PathOp):
			commands = []
			for cmd, payload in op.commands:
				if payload is None:
					commands.append([cmd, None])
					continue
				commands.append([cmd, [ _serialize_number(item, round_digits) for item in payload ]])
			entry = {
				"kind": "path",
				"commands": commands,
				"fill": color_to_hex(op.fill),
				"stroke": color_to_hex(op.stroke),
				"stroke_width": _serialize_number(op.stroke_width, round_digits),
				"cap": op.cap,
				"join": op.join,
				"z": op.z,
			}
		elif isinstance(op, TextOp):
			entry = {
				"kind": "text",
				"x": _serialize_number(op.x, round_digits),
				"y": _serialize_number(op.y, round_digits),
				"text": op.text,
				"font_size": _serialize_number(op.font_size, round_digits),
				"font_name": op.font_name,
				"anchor": op.anchor,
				"weight": op.weight,
				"color": color_to_hex(op.color),
				"z": op.z,
			}
		else:
			continue
		if op.op_id:
			entry["id"] = op.op_id
		serialized.append(entry)
	return serialized


#============================================
def ops_to_json_text(ops, round_digits=3):
	return json.dumps(ops_to_json_dict(ops, round_digits=round_digits), indent=2, sort_keys=True)


#============================================
def supports_text_ops():
	return True


#============================================
def _set_cairo_color(context, color):
	rgba = _color_to_rgba(color)
	if not rgba:
		return False
	r, g, b, a = rgba
	if a >= 1.0:
		context.set_source_rgb(r, g, b)
	else:
		context.set_source_rgba(r, g, b, a)
	return True


#============================================
def ops_to_svg(parent, ops):
	for op in sort_ops(ops):
		if isinstance(op, LineOp):
			color = color_to_hex(op.color) or "#000"
			attrs = (( 'x1', str(op.p1[0])),
					( 'y1', str(op.p1[1])),
					( 'x2', str(op.p2[0])),
					( 'y2', str(op.p2[1])),
					( 'stroke-width', str(op.width)),
					( 'stroke', color))
			if op.cap:
				attrs += (( 'stroke-linecap', op.cap),)
			if op.join:
				attrs += (( 'stroke-linejoin', op.join),)
			dom_extensions.elementUnder(parent, 'line', attrs)
			continue
		if isinstance(op, PolygonOp):
			points_text = " ".join("%s,%s" % (x, y) for x, y in op.points)
			fill = color_to_hex(op.fill) or "none"
			attrs = (( 'points', points_text),
					( 'fill', fill))
			stroke = color_to_hex(op.stroke)
			if stroke:
				attrs += (( 'stroke', stroke),
						( 'stroke-width', str(op.stroke_width)))
			else:
				attrs += (( 'stroke', "none"),)
			dom_extensions.elementUnder(parent, 'polygon', attrs)
			continue
		if isinstance(op, CircleOp):
			fill = color_to_hex(op.fill) or "none"
			attrs = (( 'cx', str(op.center[0])),
					( 'cy', str(op.center[1])),
					( 'r', str(op.radius)),
					( 'fill', fill))
			stroke = color_to_hex(op.stroke)
			if stroke:
				attrs += (( 'stroke', stroke),
						( 'stroke-width', str(op.stroke_width)))
			else:
				attrs += (( 'stroke', "none"),)
			dom_extensions.elementUnder(parent, 'circle', attrs)
			continue
		if isinstance(op, PathOp):
			d_parts = []
			for cmd, payload in op.commands:
				if cmd == "Z":
					d_parts.append("Z")
					continue
				if cmd == "M":
					d_parts.append("M %s %s" % (payload[0], payload[1]))
					continue
				if cmd == "L":
					d_parts.append("L %s %s" % (payload[0], payload[1]))
					continue
				if cmd == "ARC":
					cx, cy, r, angle1, angle2 = payload
					x = cx + r * math.cos(angle2)
					y = cy + r * math.sin(angle2)
					large_arc = 1 if abs(angle2 - angle1) > math.pi else 0
					sweep = 1 if angle2 >= angle1 else 0
					d_parts.append("A %s %s 0 %s %s %s %s" % (r, r, large_arc, sweep, x, y))
			fill = color_to_hex(op.fill) or "none"
			attrs = (( 'd', " ".join(d_parts)),
					( 'fill', fill))
			stroke = color_to_hex(op.stroke)
			if stroke:
				attrs += (( 'stroke', stroke),
						( 'stroke-width', str(op.stroke_width)))
			else:
				attrs += (( 'stroke', "none"),)
			if op.cap:
				attrs += (( 'stroke-linecap', op.cap),)
			if op.join:
				attrs += (( 'stroke-linejoin', op.join),)
			dom_extensions.elementUnder(parent, 'path', attrs)
			continue
		if isinstance(op, TextOp):
			fill = color_to_hex(op.color) or "#000"
			segments = _text_segments(op.text)
			attrs = (
				("x", str(op.x)),
				("y", str(op.y)),
				("font-family", op.font_name),
				("font-size", str(op.font_size)),
				("text-anchor", op.anchor),
				("fill", fill),
				("stroke", "none"),
			)
			if op.weight and op.weight != "normal":
				attrs += (("font-weight", op.weight),)
			if len(segments) == 1 and not segments[0][1]:
				dom_extensions.textOnlyElementUnder(parent, "text", op.text, attrs)
				continue
			text_el = dom_extensions.elementUnder(parent, "text", attrs)
			baseline_state = "base"
			for chunk, tags in segments:
				span_attrs = ()
				segment_state = _segment_baseline_state(tags)
				if segment_state in ("sub", "sup"):
					span_attrs += (("font-size", str(_segment_font_size(op.font_size, segment_state))),)
				dy_px = _baseline_transition_dy_px(op.font_size, baseline_state, segment_state)
				if abs(dy_px) > 1e-9:
					span_attrs += (("dy", f"{dy_px:.2f}"),)
				dom_extensions.textOnlyElementUnder(text_el, "tspan", chunk, span_attrs)
				baseline_state = segment_state
			continue


#============================================
def ops_to_cairo(context, ops):
	for op in sort_ops(ops):
		if isinstance(op, LineOp):
			context.set_line_width(op.width)
			if op.cap == "round":
				context.set_line_cap(1)
			elif op.cap == "square":
				context.set_line_cap(2)
			else:
				context.set_line_cap(0)
			if op.join == "round":
				context.set_line_join(1)
			elif op.join == "bevel":
				context.set_line_join(2)
			else:
				context.set_line_join(0)
			if not _set_cairo_color(context, op.color):
				context.set_source_rgb(0, 0, 0)
			context.move_to(op.p1[0], op.p1[1])
			context.line_to(op.p2[0], op.p2[1])
			context.stroke()
			continue
		if isinstance(op, PolygonOp):
			points = list(op.points)
			if not points:
				continue
			context.new_path()
			context.move_to(points[0][0], points[0][1])
			for x, y in points[1:]:
				context.line_to(x, y)
			context.close_path()
			if op.fill and op.fill != "none":
				if not _set_cairo_color(context, op.fill):
					context.set_source_rgb(0, 0, 0)
				if op.stroke:
					context.fill_preserve()
				else:
					context.fill()
			if op.stroke:
				if not _set_cairo_color(context, op.stroke):
					context.set_source_rgb(0, 0, 0)
				context.set_line_width(op.stroke_width)
				context.stroke()
			continue
		if isinstance(op, CircleOp):
			context.new_path()
			context.arc(op.center[0], op.center[1], op.radius, 0, 2 * math.pi)
			if op.fill and op.fill != "none":
				if not _set_cairo_color(context, op.fill):
					context.set_source_rgb(0, 0, 0)
				if op.stroke:
					context.fill_preserve()
				else:
					context.fill()
			if op.stroke:
				if not _set_cairo_color(context, op.stroke):
					context.set_source_rgb(0, 0, 0)
				context.set_line_width(op.stroke_width)
				context.stroke()
			continue
		if isinstance(op, PathOp):
			context.new_path()
			for cmd, payload in op.commands:
				if cmd == "Z":
					context.close_path()
					continue
				if cmd == "M":
					context.move_to(payload[0], payload[1])
					continue
				if cmd == "L":
					context.line_to(payload[0], payload[1])
					continue
				if cmd == "ARC":
					cx, cy, r, angle1, angle2 = payload
					if angle2 >= angle1:
						context.arc(cx, cy, r, angle1, angle2)
					else:
						context.arc_negative(cx, cy, r, angle1, angle2)
			if op.fill and op.fill != "none":
				if not _set_cairo_color(context, op.fill):
					context.set_source_rgb(0, 0, 0)
				if op.stroke:
					context.fill_preserve()
				else:
					context.fill()
			if op.stroke:
				if op.cap == "round":
					context.set_line_cap(1)
				elif op.cap == "square":
					context.set_line_cap(2)
				else:
					context.set_line_cap(0)
				if op.join == "round":
					context.set_line_join(1)
				elif op.join == "bevel":
					context.set_line_join(2)
				else:
					context.set_line_join(0)
				if not _set_cairo_color(context, op.stroke):
					context.set_source_rgb(0, 0, 0)
				context.set_line_width(op.stroke_width)
				context.stroke()
			continue
		if isinstance(op, TextOp):
			if not _set_cairo_color(context, op.color):
				context.set_source_rgb(0, 0, 0)
			weight = 1 if op.weight == "bold" else 0
			segments = _text_segments(op.text)
			context.select_font_face(op.font_name, 0, weight)
			total_width = 0.0
			for chunk, tags in segments:
				segment_state = _segment_baseline_state(tags)
				context.set_font_size(_segment_font_size(op.font_size, segment_state))
				extents = context.text_extents(chunk)
				total_width += extents.x_advance
			x = op.x
			if op.anchor == "middle":
				x -= total_width / 2.0
			elif op.anchor == "end":
				x -= total_width
			for chunk, tags in segments:
				segment_state = _segment_baseline_state(tags)
				context.set_font_size(_segment_font_size(op.font_size, segment_state))
				y = op.y + (op.font_size * _baseline_offset_em(segment_state))
				extents = context.text_extents(chunk)
				context.move_to(x, y)
				context.show_text(chunk)
				x += extents.x_advance
			continue


#============================================
