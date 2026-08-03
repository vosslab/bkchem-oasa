"""Qt-local painter and conservative geometry for portable molecule primitives."""

# Standard Library
import dataclasses
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui


_SCRIPT_SCALE = 0.65
_BACKGROUND_ROLE = "document-background"


#============================================
def paint(operations: tuple[object, ...], painter: PySide6.QtGui.QPainter,
		background: PySide6.QtGui.QColor, foreground: PySide6.QtGui.QColor) -> None:
	"""Paint the backend's closed primitive grammar with public Qt APIs."""
	for operation in sorted(operations, key=lambda value: value.z):
		if operation.kind == "text":
			_text(operation, painter, background, foreground)
			continue
		path = _geometry_path(operation)
		_style(painter, operation, background, foreground)
		painter.drawPath(path)


#============================================
def bounds(operations: tuple[object, ...], padding: float) -> PySide6.QtCore.QRectF:
	"""Return a conservative bound formed by the same Qt paths used for paint."""
	combined = PySide6.QtGui.QPainterPath()
	for operation in operations:
		if operation.kind == "text":
			combined.addPath(_text_path(operation))
			continue
		path = _geometry_path(operation)
		combined.addPath(path)
		if operation.stroke is not None or operation.stroke_role is not None:
			stroker = PySide6.QtGui.QPainterPathStroker()
			stroker.setWidth(operation.stroke_width or 0.0)
			stroker.setCapStyle(_cap(operation.cap))
			stroker.setJoinStyle(_join(operation.join))
			combined.addPath(stroker.createStroke(path))
	if combined.isEmpty():
		return PySide6.QtCore.QRectF(-padding, -padding, 2 * padding, 2 * padding)
	return combined.boundingRect().adjusted(-padding, -padding, padding, padding)


#============================================
def text_horizontal_bounds(operations: tuple[object, ...]) -> tuple[float, float]:
	"""Measure portable text-run extents while retaining legacy zero anchoring.

	Compatibility callers historically used the atom origin as part of an
	empty-side label bound.  Keep that local Qt behavior without exposing an
	OASA text operation to actions or models.
	"""
	left = 0.0
	right = 0.0
	for operation in operations:
		if operation.kind != "text":
			continue
		parts = _text_parts(operation)
		text_left, unused_y = _text_origin(operation, parts)
		width = sum(part[3] for part in parts)
		left = min(left, text_left)
		right = max(right, text_left + width)
	return left, right


#============================================
def transformed_operations(
		operations: tuple[object, ...],
		accepted_endpoints: tuple[tuple[float, float], tuple[float, float]],
		current_endpoints: tuple[tuple[float, float], tuple[float, float]],
		) -> tuple[object, ...]:
	"""Return a Qt-local drag view without mutating immutable backend batches.

	Coincident accepted endpoints use the deterministic translation from the
	accepted first endpoint.  That keeps an in-progress drag paintable while an
	exact accepted reprojection remains the authority for final geometry.
	"""
	old_start, old_end = accepted_endpoints
	new_start, new_end = current_endpoints
	old_dx, old_dy = old_end[0] - old_start[0], old_end[1] - old_start[1]
	new_dx, new_dy = new_end[0] - new_start[0], new_end[1] - new_start[1]
	old_length = math.hypot(old_dx, old_dy)
	new_length = math.hypot(new_dx, new_dy)
	if old_length == 0.0:
		def point(value: tuple[float, float]) -> tuple[float, float]:
			return value[0] - old_start[0] + new_start[0], value[1] - old_start[1] + new_start[1]
		scale = 1.0
	else:
		cosine = (old_dx * new_dx + old_dy * new_dy) / (old_length * new_length) if new_length else 1.0
		sine = (old_dx * new_dy - old_dy * new_dx) / (old_length * new_length) if new_length else 0.0
		scale = new_length / old_length if new_length else 0.0
		def point(value: tuple[float, float]) -> tuple[float, float]:
			x, y = value[0] - old_start[0], value[1] - old_start[1]
			return new_start[0] + scale * (cosine * x - sine * y), new_start[1] + scale * (sine * x + cosine * y)
	transformed = []
	for operation in operations:
		commands = []
		for command, payload in operation.commands:
			if command in {"M", "L"}:
				commands.append((command, point((payload[0], payload[1]))))
			elif command == "ARC":
				center = point((payload[0], payload[1]))
				commands.append((command, (center[0], center[1], payload[2] * scale, payload[3], payload[4])))
			else:
				commands.append((command, payload))
		transformed.append(dataclasses.replace(
			operation, points=tuple(point(value) for value in operation.points),
			commands=tuple(commands),
			radius=None if operation.radius is None else operation.radius * scale,
		))
	return tuple(transformed)


#============================================
def _geometry_path(operation: object) -> PySide6.QtGui.QPainterPath:
	"""Build one exact public QPainterPath for a non-text primitive."""
	path = PySide6.QtGui.QPainterPath()
	if operation.kind == "line":
		path.moveTo(*operation.points[0])
		path.lineTo(*operation.points[1])
	elif operation.kind == "polygon":
		polygon = PySide6.QtGui.QPolygonF([PySide6.QtCore.QPointF(*point) for point in operation.points])
		path.addPolygon(polygon)
	elif operation.kind == "circle":
		center = operation.points[0]
		path.addEllipse(PySide6.QtCore.QPointF(*center), operation.radius, operation.radius)
	elif operation.kind == "path":
		for command, payload in operation.commands:
			if command == "M":
				path.moveTo(payload[0], payload[1])
			elif command == "L":
				path.lineTo(payload[0], payload[1])
			elif command == "Z":
				path.closeSubpath()
			elif command == "ARC":
				rect = PySide6.QtCore.QRectF(payload[0] - payload[2], payload[1] - payload[2], 2 * payload[2], 2 * payload[2])
				path.arcTo(rect, -math.degrees(payload[3]), -math.degrees(payload[4] - payload[3]))
	else:
		raise ValueError("unsupported portable primitive kind")
	return path


#============================================
def _color(value: str | None, role: str | None, background: PySide6.QtGui.QColor,
		foreground: PySide6.QtGui.QColor) -> PySide6.QtGui.QColor | None:
	"""Resolve one backend-neutral color fact at the Qt paint boundary."""
	if role == _BACKGROUND_ROLE:
		return background
	if role == "foreground":
		return foreground
	return PySide6.QtGui.QColor(value) if value else None


#============================================
def _cap(value: str | None) -> PySide6.QtCore.Qt.PenCapStyle:
	"""Map the closed primitive cap vocabulary to Qt."""
	return {"round": PySide6.QtCore.Qt.PenCapStyle.RoundCap, "square": PySide6.QtCore.Qt.PenCapStyle.SquareCap}.get(value, PySide6.QtCore.Qt.PenCapStyle.FlatCap)


#============================================
def _join(value: str | None) -> PySide6.QtCore.Qt.PenJoinStyle:
	"""Map the closed primitive join vocabulary to Qt."""
	return {"round": PySide6.QtCore.Qt.PenJoinStyle.RoundJoin, "bevel": PySide6.QtCore.Qt.PenJoinStyle.BevelJoin}.get(value, PySide6.QtCore.Qt.PenJoinStyle.MiterJoin)


#============================================
def _style(painter: PySide6.QtGui.QPainter, operation: object, background: PySide6.QtGui.QColor,
		foreground: PySide6.QtGui.QColor) -> None:
	"""Install one primitive's fill and stroke state."""
	fill = _color(operation.fill, operation.fill_role, background, foreground)
	painter.setBrush(PySide6.QtGui.QBrush(fill) if fill else PySide6.QtCore.Qt.BrushStyle.NoBrush)
	stroke = _color(operation.stroke, operation.stroke_role, background, foreground)
	if stroke is not None and operation.stroke_width:
		pen = PySide6.QtGui.QPen(stroke)
		pen.setWidthF(operation.stroke_width)
		pen.setCapStyle(_cap(operation.cap))
		pen.setJoinStyle(_join(operation.join))
		painter.setPen(pen)
	else:
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)


#============================================
def _text_parts(operation: object) -> tuple[tuple[str, str, PySide6.QtGui.QFont, float], ...]:
	"""Build measured text runs shared by paint and conservative bounds."""
	parts = []
	for text, baseline in operation.text_runs:
		font = PySide6.QtGui.QFont(operation.font_family or "Arial")
		font.setPixelSize(max(1, round(operation.font_size * (_SCRIPT_SCALE if baseline != "base" else 1.0))))
		font.setWeight(PySide6.QtGui.QFont.Weight.Bold if operation.weight == "bold" else PySide6.QtGui.QFont.Weight.Normal)
		parts.append((text, baseline, font, PySide6.QtGui.QFontMetricsF(font).horizontalAdvance(text)))
	return tuple(parts)


#============================================
def _text_origin(operation: object, parts: tuple[tuple[str, str, PySide6.QtGui.QFont, float], ...]) -> tuple[float, float]:
	"""Resolve a structured text anchor with actual per-run character widths."""
	x, y = operation.points[0]
	width = sum(part[3] for part in parts)
	if operation.anchor == "middle":
		x -= width / 2.0
	elif operation.anchor == "end":
		x -= width
	return x, y


#============================================
def _text_path(operation: object) -> PySide6.QtGui.QPainterPath:
	"""Return font-metric conservative text geometry including scripts."""
	path = PySide6.QtGui.QPainterPath()
	parts = _text_parts(operation)
	x, y = _text_origin(operation, parts)
	for text, baseline, font, advance in parts:
		metrics = PySide6.QtGui.QFontMetricsF(font)
		dy = operation.font_size * {"sub": .40, "sup": -.45}.get(baseline, 0.0)
		rect = metrics.boundingRect(text).translated(x, y + dy)
		path.addRect(rect)
		x += advance
	return path


#============================================
def _text(operation: object, painter: PySide6.QtGui.QPainter, background: PySide6.QtGui.QColor,
		foreground: PySide6.QtGui.QColor) -> None:
	"""Paint structured text with the same run metrics used by bounds."""
	color = _color(operation.fill, operation.fill_role, background, foreground) or foreground
	painter.setPen(PySide6.QtGui.QPen(color))
	parts = _text_parts(operation)
	x, y = _text_origin(operation, parts)
	for text, baseline, font, advance in parts:
		painter.setFont(font)
		dy = operation.font_size * {"sub": .40, "sup": -.45}.get(baseline, 0.0)
		painter.drawText(PySide6.QtCore.QPointF(x, y + dy), text)
		x += advance
