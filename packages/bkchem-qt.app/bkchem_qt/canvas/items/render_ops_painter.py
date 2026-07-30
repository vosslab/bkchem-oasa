"""Translate OASA render operations to QPainter draw calls."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui

# local repo modules
import oasa.render_ops

# -- default fallback color (updated at runtime by set_default_color) --
_default_color = PySide6.QtGui.QColor(0, 0, 0)

# -- default area/paper color for masking backgrounds behind atom labels --
_default_area_color = PySide6.QtGui.QColor(255, 255, 255)
# Render ops cache geometry, so use a symbolic fill for atom masks and resolve
# it while painting.  Theme switches then recolor existing AtomItems without
# rebuilding their cached ops.
_DEFAULT_AREA_COLOR_TOKEN = "__bkchem_default_area__"

# -- canvas interaction colors (selection, hover, preview) --
_canvas_colors = {"selection": "#3399ff", "hover": "#66bbff", "preview": "#888888"}

# -- charge mark colors --
_charge_colors = {"plus": "#3366ff", "minus": "#ff3333"}

# -- light theme default line color used as sentinel for theme remapping --
_light_default_line = "#000000"

# -- font scale and vertical offsets for sub/sup text --
_SCRIPT_FONT_SCALE = oasa.render_ops.SCRIPT_FONT_SCALE
_SUBSCRIPT_OFFSET_EM = oasa.render_ops.SUBSCRIPT_OFFSET_EM
_SUPERSCRIPT_OFFSET_EM = oasa.render_ops.SUPERSCRIPT_OFFSET_EM


#============================================
def set_default_color(hex_color: str) -> None:
	"""Update the module-level default color used when ops have no explicit color.

	Called at startup and on theme change so bonds/atoms render in
	the correct theme color instead of hardcoded black.

	Args:
		hex_color: CSS hex color string (e.g. '#e0e0e0').
	"""
	global _default_color
	_default_color = PySide6.QtGui.QColor(hex_color)


#============================================
def set_default_area_color(hex_color: str) -> None:
	"""Update the module-level default area (paper) color.

	Used by AtomItem to paint a paper-colored background behind atom
	labels so bonds are masked. Called at startup and on theme change.

	Args:
		hex_color: CSS hex color string (e.g. '#ffffff').
	"""
	global _default_area_color
	_default_area_color = PySide6.QtGui.QColor(hex_color)


#============================================
def set_canvas_colors(colors: dict) -> None:
	"""Update the module-level canvas interaction colors.

	Called at startup and on theme change so selection/hover/preview
	colors match the active theme.

	Args:
		colors: Dict with keys 'selection', 'hover', 'preview'.
	"""
	for key in ("selection", "hover", "preview"):
		if key in colors:
			_canvas_colors[key] = colors[key]


#============================================
def get_canvas_color(key: str) -> str:
	"""Return a canvas interaction color by key.

	Args:
		key: One of 'selection', 'hover', 'preview'.

	Returns:
		Hex color string.
	"""
	return _canvas_colors.get(key, "#888888")


#============================================
def set_charge_colors(colors: dict) -> None:
	"""Update the module-level charge mark colors.

	Called at startup and on theme change so charge marks use
	the theme-specified colors.

	Args:
		colors: Dict with keys 'plus' and 'minus'.
	"""
	for key in ("plus", "minus"):
		if key in colors:
			_charge_colors[key] = colors[key]


#============================================
def get_charge_color(key: str) -> str:
	"""Return a charge mark color by key.

	Args:
		key: 'plus' or 'minus'.

	Returns:
		Hex color string.
	"""
	return _charge_colors.get(key, "#000000")


#============================================
def set_light_default_line(hex_color: str) -> None:
	"""Set the light theme default line color used as sentinel.

	The sentinel is compared against incoming colors in _color_to_qcolor
	to remap the light theme's default line color to the active theme's
	default color, enabling dark mode support.

	Args:
		hex_color: Hex color string from the light theme's chemistry.default_line.
	"""
	global _light_default_line
	# normalize through color_to_hex so 3-char shorthand (#000) expands to
	# 6-char (#000000), matching _color_to_qcolor's normalized comparison
	_light_default_line = oasa.render_ops.color_to_hex(hex_color) or hex_color.lower()


#============================================
def paint_ops(ops: list, painter: PySide6.QtGui.QPainter) -> None:
	"""Paint a list of render operations using the given QPainter.

	Sorts by z-order (stable with insertion order), then dispatches each
	op to the appropriate QPainter draw method.

	Args:
		ops: List of OASA render op dataclass instances.
		painter: Active QPainter to draw into.
	"""
	sorted_ops = oasa.render_ops.sort_ops(ops)
	for op in sorted_ops:
		if isinstance(op, oasa.render_ops.LineOp):
			_paint_line(op, painter)
		elif isinstance(op, oasa.render_ops.PolygonOp):
			_paint_polygon(op, painter)
		elif isinstance(op, oasa.render_ops.CircleOp):
			_paint_circle(op, painter)
		elif isinstance(op, oasa.render_ops.PathOp):
			_paint_path(op, painter)
		elif isinstance(op, oasa.render_ops.TextOp):
			_paint_text(op, painter)


#============================================
def _paint_line(op: oasa.render_ops.LineOp, painter: PySide6.QtGui.QPainter) -> None:
	"""Draw a LineOp as a single line segment.

	Args:
		op: LineOp with endpoints, width, color, cap, and join.
		painter: Active QPainter.
	"""
	color = _color_to_qcolor(op.color)
	if color is None:
		color = _default_color
	pen = PySide6.QtGui.QPen(color)
	pen.setWidthF(op.width)
	pen.setCapStyle(_cap_to_qt(op.cap))
	if op.join:
		pen.setJoinStyle(_join_to_qt(op.join))
	painter.setPen(pen)
	painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
	p1 = PySide6.QtCore.QPointF(op.p1[0], op.p1[1])
	p2 = PySide6.QtCore.QPointF(op.p2[0], op.p2[1])
	painter.drawLine(p1, p2)


#============================================
def _paint_polygon(op: oasa.render_ops.PolygonOp, painter: PySide6.QtGui.QPainter) -> None:
	"""Draw a PolygonOp as a filled and/or stroked polygon.

	Args:
		op: PolygonOp with points, fill, stroke, and stroke_width.
		painter: Active QPainter.
	"""
	polygon = PySide6.QtGui.QPolygonF()
	for x, y in op.points:
		polygon.append(PySide6.QtCore.QPointF(x, y))
	# fill brush
	fill_color = _color_to_qcolor(op.fill)
	if fill_color is not None:
		painter.setBrush(PySide6.QtGui.QBrush(fill_color))
	else:
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
	# stroke pen
	stroke_color = _color_to_qcolor(op.stroke)
	if stroke_color is not None and op.stroke_width > 0:
		pen = PySide6.QtGui.QPen(stroke_color)
		pen.setWidthF(op.stroke_width)
		painter.setPen(pen)
	else:
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
	painter.drawPolygon(polygon)


#============================================
def _paint_circle(op: oasa.render_ops.CircleOp, painter: PySide6.QtGui.QPainter) -> None:
	"""Draw a CircleOp as an ellipse with equal radii.

	Args:
		op: CircleOp with center, radius, fill, stroke, and stroke_width.
		painter: Active QPainter.
	"""
	# fill brush
	fill_color = _color_to_qcolor(op.fill)
	if fill_color is not None:
		painter.setBrush(PySide6.QtGui.QBrush(fill_color))
	else:
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
	# stroke pen
	stroke_color = _color_to_qcolor(op.stroke)
	if stroke_color is not None and op.stroke_width > 0:
		pen = PySide6.QtGui.QPen(stroke_color)
		pen.setWidthF(op.stroke_width)
		painter.setPen(pen)
	else:
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
	center = PySide6.QtCore.QPointF(op.center[0], op.center[1])
	painter.drawEllipse(center, op.radius, op.radius)


#============================================
def _paint_path(op: oasa.render_ops.PathOp, painter: PySide6.QtGui.QPainter) -> None:
	"""Draw a PathOp by building a QPainterPath from M/L/ARC/Z commands.

	Args:
		op: PathOp with commands list, fill, stroke, cap, join.
		painter: Active QPainter.
	"""
	path = PySide6.QtGui.QPainterPath()
	for cmd, payload in op.commands:
		if cmd == "M":
			path.moveTo(payload[0], payload[1])
		elif cmd == "L":
			path.lineTo(payload[0], payload[1])
		elif cmd == "ARC":
			# payload: (cx, cy, r, angle1, angle2)
			cx, cy, r, angle1, angle2 = payload
			# QPainterPath.arcTo uses a bounding rect and angles in degrees
			rect = PySide6.QtCore.QRectF(cx - r, cy - r, 2 * r, 2 * r)
			# convert radians to degrees; Qt uses counter-clockwise positive
			start_deg = -math.degrees(angle1)
			sweep_deg = -math.degrees(angle2 - angle1)
			path.arcTo(rect, start_deg, sweep_deg)
		elif cmd == "Z":
			path.closeSubpath()
	# fill brush
	fill_color = _color_to_qcolor(op.fill)
	if fill_color is not None:
		painter.setBrush(PySide6.QtGui.QBrush(fill_color))
	else:
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
	# stroke pen
	stroke_color = _color_to_qcolor(op.stroke)
	if stroke_color is not None and op.stroke_width > 0:
		pen = PySide6.QtGui.QPen(stroke_color)
		pen.setWidthF(op.stroke_width)
		if op.cap:
			pen.setCapStyle(_cap_to_qt(op.cap))
		if op.join:
			pen.setJoinStyle(_join_to_qt(op.join))
		painter.setPen(pen)
	else:
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
	painter.drawPath(path)


#============================================
def _paint_text(op: oasa.render_ops.TextOp, painter: PySide6.QtGui.QPainter) -> None:
	"""Draw a TextOp with sub/sup support and anchor alignment.

	Parses simple ``<sub>`` and ``<sup>`` tags in ``op.text`` using the
	same segment model as ``oasa.render_ops._text_segments``. Each segment
	is drawn individually with appropriate font size and vertical offset.

	Args:
		op: TextOp with position, text, font, anchor, weight, and color.
		painter: Active QPainter.
	"""
	color = _color_to_qcolor(op.color)
	if color is None:
		color = _default_color
	painter.setPen(PySide6.QtGui.QPen(color))
	painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
	# parse text into segments with baseline state tags
	segments = oasa.render_ops._text_segments(op.text)
	# resolve weight
	qt_weight = PySide6.QtGui.QFont.Weight.Bold if op.weight == "bold" else PySide6.QtGui.QFont.Weight.Normal
	# measure total advance width for anchor alignment
	total_width = _measure_segments_width(segments, op.font_name, op.font_size, qt_weight, painter)
	# compute starting x based on anchor
	x = op.x
	if op.anchor == "middle":
		x -= total_width / 2.0
	elif op.anchor == "end":
		x -= total_width
	# draw each segment
	for chunk, tags in segments:
		baseline_state = oasa.render_ops._segment_baseline_state(tags)
		seg_font_size = oasa.render_ops._segment_font_size(op.font_size, baseline_state)
		# vertical offset for sub/sup
		dy = op.font_size * oasa.render_ops._baseline_offset_em(baseline_state)
		y = op.y + dy
		# set font for this segment
		font = PySide6.QtGui.QFont(op.font_name)
		font.setPixelSize(max(1, int(round(seg_font_size))))
		font.setWeight(qt_weight)
		painter.setFont(font)
		# draw segment text
		painter.drawText(PySide6.QtCore.QPointF(x, y), chunk)
		# advance x by measured width
		metrics = PySide6.QtGui.QFontMetricsF(font)
		x += metrics.horizontalAdvance(chunk)


#============================================
def _measure_segments_width(segments: list, font_name: str, font_size: float,
		qt_weight: PySide6.QtGui.QFont.Weight, painter: PySide6.QtGui.QPainter) -> float:
	"""Measure the total horizontal advance of all text segments.

	Args:
		segments: List of (text, tags_set) tuples from _text_segments.
		font_name: Font family name.
		font_size: Base font size in pixels.
		qt_weight: Qt font weight enum value.
		painter: QPainter (unused but available for device metrics).

	Returns:
		Total width in pixels.
	"""
	total = 0.0
	for chunk, tags in segments:
		baseline_state = oasa.render_ops._segment_baseline_state(tags)
		seg_font_size = oasa.render_ops._segment_font_size(font_size, baseline_state)
		font = PySide6.QtGui.QFont(font_name)
		font.setPixelSize(max(1, int(round(seg_font_size))))
		font.setWeight(qt_weight)
		metrics = PySide6.QtGui.QFontMetricsF(font)
		total += metrics.horizontalAdvance(chunk)
	return total


#============================================
def _color_to_qcolor(color: object) -> PySide6.QtGui.QColor:
	"""Convert a color spec (hex string, RGB tuple, or None) to QColor.

	Args:
		color: A hex string like '#ff0000', an RGB/RGBA tuple with values
			0-1 or 0-255, or None.

	Returns:
		QColor instance, or None if color is None or 'none'.
	"""
	if color is None:
		return None
	if isinstance(color, str):
		text = color.strip()
		if not text or text.lower() == "none":
			return None
		if text == _DEFAULT_AREA_COLOR_TOKEN:
			return _default_area_color
		# normalize through OASA helper then build QColor
		normalized = oasa.render_ops.color_to_hex(text)
		if normalized is None:
			return _default_color
		# remap the light theme default line color to the active theme color
		# so dark mode renders bonds/labels in light gray
		if normalized == _light_default_line:
			return _default_color
		return PySide6.QtGui.QColor(normalized)
	if isinstance(color, (tuple, list)):
		hex_text = oasa.render_ops.color_to_hex(color)
		if hex_text is None:
			return _default_color
		# remap the light theme default line color to active theme color
		if hex_text == _light_default_line:
			return _default_color
		return PySide6.QtGui.QColor(hex_text)
	return _default_color


#============================================
def _cap_to_qt(cap: str) -> PySide6.QtCore.Qt.PenCapStyle:
	"""Map a cap style string to a Qt PenCapStyle enum.

	Args:
		cap: One of 'butt', 'round', or 'square'.

	Returns:
		Corresponding Qt.PenCapStyle value.
	"""
	if cap == "round":
		return PySide6.QtCore.Qt.PenCapStyle.RoundCap
	if cap == "square":
		return PySide6.QtCore.Qt.PenCapStyle.SquareCap
	# default: butt
	return PySide6.QtCore.Qt.PenCapStyle.FlatCap


#============================================
def _join_to_qt(join: str) -> PySide6.QtCore.Qt.PenJoinStyle:
	"""Map a join style string to a Qt PenJoinStyle enum.

	Args:
		join: One of 'round', 'bevel', or 'miter'.

	Returns:
		Corresponding Qt.PenJoinStyle value.
	"""
	if join == "round":
		return PySide6.QtCore.Qt.PenJoinStyle.RoundJoin
	if join == "bevel":
		return PySide6.QtCore.Qt.PenJoinStyle.BevelJoin
	# default: miter
	return PySide6.QtCore.Qt.PenJoinStyle.MiterJoin
