"""Chemical mark items for atoms (charge, radical, electron pair)."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# mark type constants
MARK_PLUS = "plus"
MARK_MINUS = "minus"
MARK_RADICAL = "radical"
MARK_ELECTRON_PAIR = "electron_pair"
MARK_LONE_PAIR = "lone_pair"

# local repo modules
import bkchem_qt.canvas.items.render_ops_painter

#============================================
class MarkItem(PySide6.QtWidgets.QGraphicsItem):
	"""Base class for chemical marks attached to atoms.

	Marks are drawn at a configurable angle and distance from the parent
	atom center. Setting the parent item to the atom item makes the mark
	move automatically when the atom moves.

	Args:
		parent_atom_item: The AtomItem this mark is attached to.
		mark_type: One of the MARK_* constants defining the mark kind.
		angle: Placement angle in degrees from the positive x-axis.
	"""

	#============================================
	def __init__(self, parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			mark_type: str, angle: float = 0.0, offset: float = 12.0,
			size: float = 4.0) -> None:
		"""Initialize the mark item.

		Args:
			parent_atom_item: The AtomItem this mark is attached to.
			mark_type: Type string such as "plus", "minus", "radical",
				"electron_pair", or "lone_pair".
			angle: Placement angle in degrees from the positive x-axis.
			offset: Distance in scene points from the atom centre to mark centre.
			size: CDML mark diameter in scene points.
		"""
		super().__init__(parent_atom_item)
		self._parent_atom = parent_atom_item
		self._mark_type = mark_type
		self._angle = angle
		# CDML stores mark size as a diameter, matching legacy BKChem marks.
		self._radius = max(0.0, size) / 2.0
		# distance from atom center to mark center
		self._offset = max(0.0, offset)
		# position the mark relative to the parent atom center
		self._update_position()
		self._disposed = False

	#============================================
	def _update_position(self) -> None:
		"""Recompute position based on angle and offset from parent center.

		Converts the angle (in degrees) to an x/y offset and sets the
		item position in parent-local coordinates.
		"""
		angle_rad = math.radians(self._angle)
		dx = self._offset * math.cos(angle_rad)
		dy = self._offset * math.sin(angle_rad)
		self.setPos(dx, dy)

	#============================================
	@property
	def mark_type(self) -> str:
		"""Return the mark type string."""
		return self._mark_type

	#============================================
	@property
	def angle(self) -> float:
		"""Return the placement angle in degrees."""
		return self._angle

	#============================================
	@angle.setter
	def angle(self, value: float) -> None:
		"""Set the placement angle and reposition.

		Args:
			value: New angle in degrees.
		"""
		self._angle = value
		self._update_position()

	#============================================
	@property
	def offset(self) -> float:
		"""Return the mark centre's radial distance from its atom."""
		return self._offset

	#============================================
	@offset.setter
	def offset(self, value: float) -> None:
		"""Set the radial distance and update parent-local position."""
		self._offset = max(0.0, value)
		self._update_position()

	#============================================
	@property
	def size(self) -> float:
		"""Return the CDML mark diameter in scene points."""
		diameter = self._radius * 2.0
		return diameter

	#============================================
	@size.setter
	def size(self, value: float) -> None:
		"""Set the CDML diameter and notify Qt that bounds changed."""
		new_radius = max(0.0, value) / 2.0
		if new_radius == self._radius:
			return
		self.prepareGeometryChange()
		self._radius = new_radius
		self.update()

	#============================================
	def dispose(self) -> None:
		"""Release projection-owned callbacks before scene teardown."""
		self._disposed = True

	#============================================
	def boundingRect(self) -> PySide6.QtCore.QRectF:
		"""Return the bounding rectangle for this mark.

		Returns:
			QRectF centered on the mark position with radius-based size.
		"""
		r = self._radius + 1.0
		rect = PySide6.QtCore.QRectF(-r, -r, 2 * r, 2 * r)
		return rect

	#============================================
	def paint(self, painter: PySide6.QtGui.QPainter,
			option: PySide6.QtWidgets.QStyleOptionGraphicsItem,
			widget: PySide6.QtWidgets.QWidget | None = None) -> None:
		"""Paint the mark by dispatching to the appropriate draw method.

		Args:
			painter: The QPainter provided by the scene.
			option: Style options (unused).
			widget: Target widget (unused).
		"""
		if self._mark_type == MARK_PLUS:
			self._paint_plus(painter)
		elif self._mark_type == MARK_MINUS:
			self._paint_minus(painter)
		elif self._mark_type == MARK_RADICAL:
			self._paint_radical(painter)
		elif self._mark_type in (MARK_ELECTRON_PAIR, MARK_LONE_PAIR):
			self._paint_electron_pair(painter)

	#============================================
	def _paint_plus(self, painter: PySide6.QtGui.QPainter) -> None:
		"""Draw a plus sign inside a circle outline.

		Args:
			painter: The QPainter to draw with.
		"""
		r = self._radius
		# draw circle outline
		charge_color = bkchem_qt.canvas.items.render_ops_painter.get_charge_color(
			"plus",
		)
		color = PySide6.QtGui.QColor(charge_color)
		pen = PySide6.QtGui.QPen(color)
		pen.setWidthF(1.0)
		painter.setPen(pen)
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
		painter.drawEllipse(PySide6.QtCore.QPointF(0, 0), r, r)
		# draw the plus: horizontal and vertical lines
		half = r * 0.6
		painter.drawLine(
			PySide6.QtCore.QPointF(-half, 0),
			PySide6.QtCore.QPointF(half, 0),
		)
		painter.drawLine(
			PySide6.QtCore.QPointF(0, -half),
			PySide6.QtCore.QPointF(0, half),
		)

	#============================================
	def _paint_minus(self, painter: PySide6.QtGui.QPainter) -> None:
		"""Draw a minus sign inside a circle outline.

		Args:
			painter: The QPainter to draw with.
		"""
		r = self._radius
		# draw circle outline
		charge_color = bkchem_qt.canvas.items.render_ops_painter.get_charge_color(
			"minus",
		)
		color = PySide6.QtGui.QColor(charge_color)
		pen = PySide6.QtGui.QPen(color)
		pen.setWidthF(1.0)
		painter.setPen(pen)
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
		painter.drawEllipse(PySide6.QtCore.QPointF(0, 0), r, r)
		# draw the minus: horizontal line only
		half = r * 0.6
		painter.drawLine(
			PySide6.QtCore.QPointF(-half, 0),
			PySide6.QtCore.QPointF(half, 0),
		)

	#============================================
	def _paint_radical(self, painter: PySide6.QtGui.QPainter) -> None:
		"""Draw a filled black dot for a radical mark.

		Args:
			painter: The QPainter to draw with.
		"""
		dot_radius = self._radius
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		painter.setBrush(PySide6.QtGui.QBrush(
			bkchem_qt.canvas.items.render_ops_painter._default_color,
		))
		painter.drawEllipse(PySide6.QtCore.QPointF(0, 0), dot_radius, dot_radius)

	#============================================
	def _paint_electron_pair(self, painter: PySide6.QtGui.QPainter) -> None:
		"""Draw two small dots for an electron pair mark.

		Args:
			painter: The QPainter to draw with.
		"""
		dot_radius = max(1.0, self._radius * 0.3)
		# spacing between the two dots
		spacing = max(dot_radius, self._radius * 0.6)
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		painter.setBrush(PySide6.QtGui.QBrush(
			bkchem_qt.canvas.items.render_ops_painter._default_color,
		))
		# draw two dots side by side perpendicular to the radial direction
		angle_rad = math.radians(self._angle)
		# perpendicular direction
		perp_x = -math.sin(angle_rad) * spacing
		perp_y = math.cos(angle_rad) * spacing
		painter.drawEllipse(
			PySide6.QtCore.QPointF(perp_x, perp_y), dot_radius, dot_radius,
		)
		painter.drawEllipse(
			PySide6.QtCore.QPointF(-perp_x, -perp_y), dot_radius, dot_radius,
		)


#============================================
class ChargeMarkItem(MarkItem):
	"""Plus or minus charge mark.

	Convenience subclass that sets mark_type to plus or minus
	based on the charge sign.

	Args:
		parent_atom_item: The AtomItem this mark is attached to.
		positive: True for plus, False for minus.
		angle: Placement angle in degrees.
	"""

	#============================================
	def __init__(self, parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			positive: bool = True, angle: float = 45.0) -> None:
		"""Initialize the charge mark.

		Args:
			parent_atom_item: The AtomItem this mark is attached to.
			positive: True for plus mark, False for minus mark.
			angle: Placement angle in degrees from the positive x-axis.
		"""
		mark_type = MARK_PLUS if positive else MARK_MINUS
		super().__init__(parent_atom_item, mark_type, angle, size=10.0)


#============================================
class RadicalMarkItem(MarkItem):
	"""Radical dot mark.

	Convenience subclass that sets mark_type to radical.

	Args:
		parent_atom_item: The AtomItem this mark is attached to.
		angle: Placement angle in degrees.
	"""

	#============================================
	def __init__(self, parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			angle: float = 90.0) -> None:
		"""Initialize the radical mark.

		Args:
			parent_atom_item: The AtomItem this mark is attached to.
			angle: Placement angle in degrees from the positive x-axis.
		"""
		super().__init__(parent_atom_item, MARK_RADICAL, angle, size=4.0)


#============================================
class ElectronPairMarkItem(MarkItem):
	"""Electron pair mark (two dots).

	Convenience subclass that sets mark_type to electron_pair.

	Args:
		parent_atom_item: The AtomItem this mark is attached to.
		angle: Placement angle in degrees.
	"""

	#============================================
	def __init__(self, parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			angle: float = 180.0) -> None:
		"""Initialize the electron pair mark.

		Args:
			parent_atom_item: The AtomItem this mark is attached to.
			angle: Placement angle in degrees from the positive x-axis.
		"""
		super().__init__(parent_atom_item, MARK_ELECTRON_PAIR, angle, size=10.0)
