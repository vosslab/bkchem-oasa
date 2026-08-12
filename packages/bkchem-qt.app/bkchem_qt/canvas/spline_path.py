"""Shared Qt painter-path construction for authored spline control points."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui


#============================================
def curve_path(
		start: PySide6.QtCore.QPointF,
		controls: tuple[PySide6.QtCore.QPointF, ...],
		end: PySide6.QtCore.QPointF,
		) -> PySide6.QtGui.QPainterPath:
	"""Return a continuous curve through one ordered control-point sequence."""
	path = PySide6.QtGui.QPainterPath(start)
	if not controls:
		path.lineTo(end)
	elif len(controls) == 1:
		path.quadTo(controls[0], end)
	elif len(controls) == 2:
		path.cubicTo(controls[0], controls[1], end)
	else:
		for control, next_control in zip(controls, controls[1:]):
			midpoint = PySide6.QtCore.QPointF(
				(control.x() + next_control.x()) / 2.0,
				(control.y() + next_control.y()) / 2.0,
			)
			path.quadTo(control, midpoint)
		path.quadTo(controls[-1], end)
	return path


#============================================
def presentation_path(
		points: list[PySide6.QtCore.QPointF], spline: bool,
		) -> PySide6.QtGui.QPainterPath:
	"""Return one straight polyline or authored-control spline presentation path."""
	if not points:
		return PySide6.QtGui.QPainterPath()
	if spline and len(points) >= 2:
		return curve_path(points[0], tuple(points[1:-1]), points[-1])
	path = PySide6.QtGui.QPainterPath(points[0])
	for point in points[1:]:
		path.lineTo(point)
	return path
