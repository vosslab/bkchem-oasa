"""Translate OASA render operations to QPainter draw calls."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui

# local repo modules
import oasa.render_ops

# -- default fallback color --
_DEFAULT_COLOR = PySide6.QtGui.QColor(0, 0, 0)

# -- font scale and vertical offsets for sub/sup text --
_SCRIPT_FONT_SCALE = oasa.render_ops.SCRIPT_FONT_SCALE
_SUBSCRIPT_OFFSET_EM = oasa.render_ops.SUBSCRIPT_OFFSET_EM
_SUPERSCRIPT_OFFSET_EM = oasa.render_ops.SUPERSCRIPT_OFFSET_EM


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
def _color_to_qcolor(color) -> PySide6.QtGui.QColor:
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
		# normalize through OASA helper then build QColor
		normalized = oasa.render_ops.color_to_hex(text)
		if normalized is None:
			return _DEFAULT_COLOR
		return PySide6.QtGui.QColor(normalized)
	if isinstance(color, (tuple, list)):
		hex_text = oasa.render_ops.color_to_hex(color)
		if hex_text is None:
			return _DEFAULT_COLOR
		return PySide6.QtGui.QColor(hex_text)
	return _DEFAULT_COLOR


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
