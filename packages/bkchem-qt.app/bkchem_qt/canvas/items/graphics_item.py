"""Vector graphics items (rectangle, oval, polygon, polyline)."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
class RectItem(PySide6.QtWidgets.QGraphicsRectItem):
	"""Rectangle with configurable fill and stroke.

	Supports selection and hover events for interactive editing.

	Args:
		rect: QRectF defining the rectangle geometry.
		parent: Optional parent QGraphicsItem.
	"""

	#============================================
	def __init__(self, rect: PySide6.QtCore.QRectF,
				 parent: PySide6.QtWidgets.QGraphicsItem = None):
		"""Initialize the rectangle item.

		Args:
			rect: QRectF defining the rectangle geometry.
			parent: Optional parent QGraphicsItem.
		"""
		super().__init__(rect, parent)
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
		)
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True,
		)
		self.setAcceptHoverEvents(True)
		# default appearance
		self.setPen(PySide6.QtGui.QPen(PySide6.QtCore.Qt.GlobalColor.black, 1.0))
		self.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)


#============================================
class OvalItem(PySide6.QtWidgets.QGraphicsEllipseItem):
	"""Oval/ellipse with configurable fill and stroke.

	Supports selection and hover events for interactive editing.

	Args:
		rect: QRectF defining the bounding rectangle of the ellipse.
		parent: Optional parent QGraphicsItem.
	"""

	#============================================
	def __init__(self, rect: PySide6.QtCore.QRectF,
				 parent: PySide6.QtWidgets.QGraphicsItem = None):
		"""Initialize the oval item.

		Args:
			rect: QRectF defining the bounding rectangle of the ellipse.
			parent: Optional parent QGraphicsItem.
		"""
		super().__init__(rect, parent)
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
		)
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True,
		)
		self.setAcceptHoverEvents(True)
		# default appearance
		self.setPen(PySide6.QtGui.QPen(PySide6.QtCore.Qt.GlobalColor.black, 1.0))
		self.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)


#============================================
class PolygonItem(PySide6.QtWidgets.QGraphicsPolygonItem):
	"""Polygon with configurable fill and stroke.

	Supports selection and hover events for interactive editing.

	Args:
		points: List of (x, y) tuples or QPointF objects defining vertices.
		parent: Optional parent QGraphicsItem.
	"""

	#============================================
	def __init__(self, points: list,
				 parent: PySide6.QtWidgets.QGraphicsItem = None):
		"""Initialize the polygon item from a list of points.

		Args:
			points: List of (x, y) tuples or QPointF defining polygon vertices.
			parent: Optional parent QGraphicsItem.
		"""
		# convert tuples to QPointF if needed
		qt_points = []
		for pt in points:
			if isinstance(pt, PySide6.QtCore.QPointF):
				qt_points.append(pt)
			else:
				qt_points.append(PySide6.QtCore.QPointF(pt[0], pt[1]))
		polygon = PySide6.QtGui.QPolygonF(qt_points)
		super().__init__(polygon, parent)
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True,
		)
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True,
		)
		self.setAcceptHoverEvents(True)
		# default appearance
		self.setPen(PySide6.QtGui.QPen(PySide6.QtCore.Qt.GlobalColor.black, 1.0))
		self.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
