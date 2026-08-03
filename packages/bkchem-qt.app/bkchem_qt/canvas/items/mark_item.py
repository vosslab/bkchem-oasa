"""Disposable Qt projections for persistent CDML atom marks."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.render_ops_painter


# CDML mark type constants.  The two historical aliases remain for callers
# that construct old Qt-only marks; canonical CDML decoding uses ``electronpair``.
MARK_PLUS = "plus"
MARK_MINUS = "minus"
MARK_RADICAL = "radical"
MARK_BIRADICAL = "biradical"
MARK_ELECTRONPAIR = "electronpair"
MARK_DOTTED_ELECTRONPAIR = "dotted_electronpair"
MARK_PZ_ORBITAL = "pz_orbital"
MARK_ELECTRON_PAIR = "electron_pair"
MARK_LONE_PAIR = "lone_pair"


#============================================
class MarkItem(PySide6.QtWidgets.QGraphicsItem):
	"""Render one CDML mark as a child of its atom projection.

	The item contains only the current frontend rendering of an immutable
	backend snapshot.  Its position is parent-local, so it follows the atom
	without becoming an independent scene or persistent-document object.
	"""

	#============================================
	def __init__(self, parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			mark_type: str, angle: float = 0.0, offset: float = 12.0,
			size: float = 4.0, draw_circle: bool = True,
			line_width: float = 1.0) -> None:
		"""Initialize a child projection from normalized display values."""
		super().__init__(parent_atom_item)
		self._parent_atom = parent_atom_item
		self._mark_type = mark_type
		self._angle = angle
		self._radius = size / 2.0
		self._offset = offset
		self._draw_circle = draw_circle
		self._line_width = line_width
		self._disposed = False
		self._update_position()

	#============================================
	def _update_position(self) -> None:
		"""Place the mark at its persisted atom-relative position."""
		angle_rad = math.radians(self._angle)
		dx = self._offset * math.cos(angle_rad)
		dy = self._offset * math.sin(angle_rad)
		self.setPos(dx, dy)

	#============================================
	@property
	def mark_type(self) -> str:
		"""Return the projected CDML mark kind."""
		return self._mark_type

	#============================================
	@property
	def angle(self) -> float:
		"""Return the atom-to-mark radial angle in degrees."""
		return self._angle

	#============================================
	@angle.setter
	def angle(self, value: float) -> None:
		"""Set a validated radial angle and retain the authored position."""
		self._angle = value
		self._update_position()
		self.update()

	#============================================
	@property
	def offset(self) -> float:
		"""Return the mark centre's radial distance from its atom."""
		return self._offset

	#============================================
	@offset.setter
	def offset(self, value: float) -> None:
		"""Set a validated radial distance and update parent-local position."""
		self._offset = value
		self._update_position()
		self.update()

	#============================================
	@property
	def size(self) -> float:
		"""Return the projected CDML mark diameter in scene points."""
		return self._radius * 2.0

	#============================================
	@size.setter
	def size(self, value: float) -> None:
		"""Set a validated CDML diameter and refresh Qt geometry."""
		new_radius = value / 2.0
		if new_radius == self._radius:
			return
		self.prepareGeometryChange()
		self._radius = new_radius
		self.update()

	#============================================
	@property
	def draw_circle(self) -> bool:
		"""Return whether a charge mark includes its CDML circle outline."""
		return self._draw_circle

	#============================================
	@draw_circle.setter
	def draw_circle(self, value: bool) -> None:
		"""Set the frontend circle rendering flag for a charge mark."""
		self._draw_circle = value
		self.update()

	#============================================
	@property
	def line_width(self) -> float:
		"""Return the projected electron-pair line width."""
		return self._line_width

	#============================================
	@line_width.setter
	def line_width(self, value: float) -> None:
		"""Set the frontend electron-pair line width."""
		self._line_width = value
		self.update()

	#============================================
	@property
	def rendering_kind(self) -> str:
		"""Return the stable semantic rendering category for this projection."""
		if self._mark_type == MARK_ELECTRONPAIR:
			return "perpendicular-line"
		if self._mark_type in (MARK_BIRADICAL, MARK_DOTTED_ELECTRONPAIR,
				MARK_ELECTRON_PAIR, MARK_LONE_PAIR):
			return "perpendicular-dot-pair"
		if self._mark_type == MARK_PZ_ORBITAL:
			return "figure-eight"
		if self._mark_type == MARK_RADICAL:
			return "dot"
		return "charge"

	#============================================
	def dispose(self) -> None:
		"""Release projection-only references before parent scene teardown."""
		self._disposed = True
		self._parent_atom = None

	#============================================
	def _paint_extent(self) -> float:
		"""Return the largest local half-extent for this mark's drawing."""
		if self._mark_type == MARK_PZ_ORBITAL:
			return self._radius * 1.1
		return self._radius

	#============================================
	def boundingRect(self) -> PySide6.QtCore.QRectF:
		"""Return a conservative local rectangle for Qt invalidation and picking."""
		extent = self._paint_extent() + max(1.0, self._line_width / 2.0)
		return PySide6.QtCore.QRectF(-extent, -extent, 2.0 * extent, 2.0 * extent)

	#============================================
	def paint(self, painter: PySide6.QtGui.QPainter,
			option: PySide6.QtWidgets.QStyleOptionGraphicsItem,
			widget: PySide6.QtWidgets.QWidget | None = None) -> None:
		"""Paint the projected CDML semantics using current theme colors."""
		if self._mark_type == MARK_PLUS:
			self._paint_charge(painter, positive=True)
		elif self._mark_type == MARK_MINUS:
			self._paint_charge(painter, positive=False)
		elif self._mark_type == MARK_RADICAL:
			self._paint_dot(painter)
		elif self._mark_type in (MARK_BIRADICAL, MARK_DOTTED_ELECTRONPAIR,
				MARK_ELECTRON_PAIR, MARK_LONE_PAIR):
			self._paint_dot_pair(painter)
		elif self._mark_type == MARK_ELECTRONPAIR:
			self._paint_electron_pair(painter)
		elif self._mark_type == MARK_PZ_ORBITAL:
			self._paint_pz_orbital(painter)

	#============================================
	def _default_pen(self) -> PySide6.QtGui.QPen:
		"""Build the standard themed mark pen."""
		pen = PySide6.QtGui.QPen(
			bkchem_qt.canvas.items.render_ops_painter._default_color,
			self._line_width,
		)
		return pen

	#============================================
	def _paint_charge(self, painter: PySide6.QtGui.QPainter,
			positive: bool) -> None:
		"""Draw a themed plus or minus, optionally surrounded by a circle."""
		mark_key = MARK_PLUS if positive else MARK_MINUS
		color = PySide6.QtGui.QColor(
			bkchem_qt.canvas.items.render_ops_painter.get_charge_color(mark_key),
		)
		pen = PySide6.QtGui.QPen(color, 1.0)
		painter.setPen(pen)
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
		if self._draw_circle:
			painter.drawEllipse(PySide6.QtCore.QPointF(), self._radius, self._radius)
		half = self._radius * 0.6
		painter.drawLine(PySide6.QtCore.QPointF(-half, 0.0),
				PySide6.QtCore.QPointF(half, 0.0))
		if positive:
			painter.drawLine(PySide6.QtCore.QPointF(0.0, -half),
					PySide6.QtCore.QPointF(0.0, half))

	#============================================
	def _paint_dot(self, painter: PySide6.QtGui.QPainter) -> None:
		"""Draw one centered radical dot."""
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		painter.setBrush(bkchem_qt.canvas.items.render_ops_painter._default_color)
		painter.drawEllipse(PySide6.QtCore.QPointF(), self._radius, self._radius)

	#============================================
	def _perpendicular_vector(self, spacing: float) -> tuple[float, float]:
		"""Return an atom-radial perpendicular vector of ``spacing`` points."""
		angle_rad = math.radians(self._angle)
		return (-math.sin(angle_rad) * spacing, math.cos(angle_rad) * spacing)

	#============================================
	def _paint_dot_pair(self, painter: PySide6.QtGui.QPainter) -> None:
		"""Draw the two dots used by biradical and dotted lone-pair marks."""
		dot_radius = max(1.0, self._radius * 0.3)
		spacing = max(dot_radius, self._radius * 0.6)
		perp_x, perp_y = self._perpendicular_vector(spacing)
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		painter.setBrush(bkchem_qt.canvas.items.render_ops_painter._default_color)
		painter.drawEllipse(PySide6.QtCore.QPointF(perp_x, perp_y), dot_radius, dot_radius)
		painter.drawEllipse(PySide6.QtCore.QPointF(-perp_x, -perp_y), dot_radius, dot_radius)

	#============================================
	def _paint_electron_pair(self, painter: PySide6.QtGui.QPainter) -> None:
		"""Draw a line perpendicular to the atom-to-mark radial direction."""
		perp_x, perp_y = self._perpendicular_vector(self._radius)
		painter.setPen(self._default_pen())
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
		painter.drawLine(PySide6.QtCore.QPointF(-perp_x, -perp_y),
				PySide6.QtCore.QPointF(perp_x, perp_y))

	#============================================
	def _paint_pz_orbital(self, painter: PySide6.QtGui.QPainter) -> None:
		"""Draw the legacy-style two-lobed pz orbital around its mark centre."""
		painter.save()
		# A point at the atom uses the established vertical default.  A separately
		# authored point rotates the lobe axis with its radial direction.
		painter.rotate(self._angle)
		painter.setPen(self._default_pen())
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
		lobe_width = self._radius * 0.45
		lobe_height = self._radius * 0.65
		painter.drawEllipse(PySide6.QtCore.QPointF(0.0, -self._radius * 0.38),
				lobe_width, lobe_height)
		painter.drawEllipse(PySide6.QtCore.QPointF(0.0, self._radius * 0.38),
				lobe_width, lobe_height)
		painter.restore()


#============================================
class ChargeMarkItem(MarkItem):
	"""Compatibility constructor for a plus or minus charge mark."""

	#============================================
	def __init__(self, parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			positive: bool = True, angle: float = 45.0) -> None:
		"""Initialize a conventional ten-point circled charge projection."""
		mark_type = MARK_PLUS if positive else MARK_MINUS
		super().__init__(parent_atom_item, mark_type, angle, size=10.0)


#============================================
class RadicalMarkItem(MarkItem):
	"""Compatibility constructor for a radical-dot projection."""

	#============================================
	def __init__(self, parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			angle: float = 90.0) -> None:
		"""Initialize a conventional four-point radical projection."""
		super().__init__(parent_atom_item, MARK_RADICAL, angle, size=4.0)


#============================================
class ElectronPairMarkItem(MarkItem):
	"""Compatibility constructor for a line electron-pair projection."""

	#============================================
	def __init__(self, parent_atom_item: PySide6.QtWidgets.QGraphicsItem,
			angle: float = 180.0) -> None:
		"""Initialize a conventional ten-point electron-pair projection."""
		super().__init__(parent_atom_item, MARK_ELECTRONPAIR, angle, size=10.0)
