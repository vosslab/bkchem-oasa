"""Focused geometry tests for curved reaction-arrow projections."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.arrow_item


#============================================
def _render_arrow(
		item: bkchem_qt.canvas.items.arrow_item.ArrowItem,
		) -> PySide6.QtGui.QImage:
	"""Render one item onto a transparent image in its local coordinates."""
	image = PySide6.QtGui.QImage(
		200, 160, PySide6.QtGui.QImage.Format.Format_ARGB32_Premultiplied,
	)
	image.fill(PySide6.QtCore.Qt.GlobalColor.transparent)
	painter = PySide6.QtGui.QPainter(image)
	painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.Antialiasing)
	painter.translate(30.0, 30.0)
	item.paint(painter, PySide6.QtWidgets.QStyleOptionGraphicsItem(), None)
	painter.end()
	return image


#============================================
def _cubic_spline_arrow() -> bkchem_qt.canvas.items.arrow_item.ArrowItem:
	"""Return one cubic arrow with a visibly curved center section."""
	item = bkchem_qt.canvas.items.arrow_item.ArrowItem(
		PySide6.QtCore.QPointF(0.0, 0.0),
		PySide6.QtCore.QPointF(100.0, 0.0),
	)
	item.spline = True
	item.control_points = [
		PySide6.QtCore.QPointF(0.0, 100.0),
		PySide6.QtCore.QPointF(100.0, 100.0),
	]
	item.start_head = True
	return item


#============================================
def _quadratic_spline_arrow() -> bkchem_qt.canvas.items.arrow_item.ArrowItem:
	"""Return the legacy one-control-point spline representation."""
	item = bkchem_qt.canvas.items.arrow_item.ArrowItem(
		PySide6.QtCore.QPointF(0.0, 0.0),
		PySide6.QtCore.QPointF(100.0, 0.0),
	)
	item.spline = True
	item.control_points = [PySide6.QtCore.QPointF(50.0, 100.0)]
	return item


#============================================
def test_spline_arrow_shape_and_bounds_follow_the_visible_curve(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A cubic arrow is clickable and bounded at its curved midpoint."""
	del qapp
	item = _cubic_spline_arrow()

	curve_midpoint = PySide6.QtCore.QPointF(50.0, 75.0)
	straight_chord = PySide6.QtCore.QPointF(50.0, 0.0)
	assert (
		item.shape().contains(curve_midpoint)
		and item.boundingRect().contains(curve_midpoint)
	)
	assert not item.shape().contains(straight_chord)

#============================================
def test_selected_spline_arrow_highlights_the_curve(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Selection paint adds visible emphasis at the cubic curve."""
	del qapp
	item = _cubic_spline_arrow()
	plain_image = _render_arrow(item)
	item.setSelected(True)
	highlighted_image = _render_arrow(item)

	assert (
		highlighted_image.pixelColor(80, 100).alpha()
		> plain_image.pixelColor(80, 100).alpha()
	)


#============================================
def test_loaded_three_point_spline_uses_its_interior_control_point(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A legacy start-control-end spline projects as a quadratic curve."""
	del qapp
	item = _quadratic_spline_arrow()
	quadratic_midpoint = PySide6.QtCore.QPointF(50.0, 50.0)
	straight_chord = PySide6.QtCore.QPointF(50.0, 0.0)
	assert (
		item.shape().contains(quadratic_midpoint)
		and item.boundingRect().contains(quadratic_midpoint)
	)
	assert not item.shape().contains(straight_chord)

#============================================
def test_loaded_three_point_spline_paints_at_its_quadratic_midpoint(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""The legacy control point affects the rendered quadratic curve."""
	del qapp

	assert _render_arrow(
		_quadratic_spline_arrow(),
	).pixelColor(80, 80).alpha() > 0
