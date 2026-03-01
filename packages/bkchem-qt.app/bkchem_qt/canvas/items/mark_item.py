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

# colors for charge marks
_PLUS_COLOR = PySide6.QtGui.QColor("#0000cc")
_MINUS_COLOR = PySide6.QtGui.QColor("#cc0000")
_RADICAL_COLOR = PySide6.QtGui.QColor("#000000")
_PAIR_COLOR = PySide6.QtGui.QColor("#000000")


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
	def __init__(self, parent_atom_item, mark_type: str, angle: float = 0.0):
		"""Initialize the mark item.

		Args:
			parent_atom_item: The AtomItem this mark is attached to.
			mark_type: Type string such as "plus", "minus", "radical",
				"electron_pair", or "lone_pair".
			angle: Placement angle in degrees from the positive x-axis.
		"""
		super().__init__(parent_atom_item)
		self._parent_atom = parent_atom_item
		self._mark_type = mark_type
		self._angle = angle
		# size of the mark symbol
		self._radius = 6.0
		# distance from atom center to mark center
		self._offset = 12.0
		# position the mark relative to the parent atom center
		self._update_position()

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
	def angle(self, value: float):
		"""Set the placement angle and reposition.

		Args:
			value: New angle in degrees.
		"""
		self._angle = value
		self._update_position()

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
			  widget: PySide6.QtWidgets.QWidget = None) -> None:
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
		pen = PySide6.QtGui.QPen(_PLUS_COLOR)
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
		pen = PySide6.QtGui.QPen(_MINUS_COLOR)
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
		dot_radius = 2.5
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		painter.setBrush(PySide6.QtGui.QBrush(_RADICAL_COLOR))
		painter.drawEllipse(PySide6.QtCore.QPointF(0, 0), dot_radius, dot_radius)

	#============================================
	def _paint_electron_pair(self, painter: PySide6.QtGui.QPainter) -> None:
		"""Draw two small dots for an electron pair mark.

		Args:
			painter: The QPainter to draw with.
		"""
		dot_radius = 1.5
		# spacing between the two dots
		spacing = 3.0
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		painter.setBrush(PySide6.QtGui.QBrush(_PAIR_COLOR))
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
	def __init__(self, parent_atom_item, positive: bool = True, angle: float = 45.0):
		"""Initialize the charge mark.

		Args:
			parent_atom_item: The AtomItem this mark is attached to.
			positive: True for plus mark, False for minus mark.
			angle: Placement angle in degrees from the positive x-axis.
		"""
		mark_type = MARK_PLUS if positive else MARK_MINUS
		super().__init__(parent_atom_item, mark_type, angle)


#============================================
class RadicalMarkItem(MarkItem):
	"""Radical dot mark.

	Convenience subclass that sets mark_type to radical.

	Args:
		parent_atom_item: The AtomItem this mark is attached to.
		angle: Placement angle in degrees.
	"""

	#============================================
	def __init__(self, parent_atom_item, angle: float = 90.0):
		"""Initialize the radical mark.

		Args:
			parent_atom_item: The AtomItem this mark is attached to.
			angle: Placement angle in degrees from the positive x-axis.
		"""
		super().__init__(parent_atom_item, MARK_RADICAL, angle)


#============================================
class ElectronPairMarkItem(MarkItem):
	"""Electron pair mark (two dots).

	Convenience subclass that sets mark_type to electron_pair.

	Args:
		parent_atom_item: The AtomItem this mark is attached to.
		angle: Placement angle in degrees.
	"""

	#============================================
	def __init__(self, parent_atom_item, angle: float = 180.0):
		"""Initialize the electron pair mark.

		Args:
			parent_atom_item: The AtomItem this mark is attached to.
			angle: Placement angle in degrees from the positive x-axis.
		"""
		super().__init__(parent_atom_item, MARK_ELECTRON_PAIR, angle)
