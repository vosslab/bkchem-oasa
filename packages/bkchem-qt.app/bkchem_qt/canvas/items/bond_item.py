"""QGraphicsItem subclass for rendering a bond using OASA render ops."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
from bkchem_qt.canvas.items import render_ops_painter
import oasa.render_ops
import oasa.render_lib.molecule_ops
import oasa.render_lib.bond_ops
import oasa.render_lib.data_types

# -- visual constants --
# extra padding around bounding rect for hit testing
_BOUNDS_PADDING = 6.0
# width of the expanded shape path for easier click targeting
_HIT_PATH_WIDTH = 10.0
# pen width for selection highlight
_SELECTION_PEN_WIDTH = 1.5
# selection highlight color
_SELECTION_COLOR = "#3399ff"
# hover highlight color
_HOVER_COLOR = "#66bbff"
# hover pen width
_HOVER_PEN_WIDTH = 1.0
# z-value for bond items (below atoms)
BOND_Z_VALUE = 5


#============================================
class BondItem(PySide6.QtWidgets.QGraphicsItem):
	"""Visual representation of a single bond on the chemistry canvas.

	Renders the bond by calling ``oasa.render_lib.bond_ops.build_bond_ops()``
	on the underlying OASA edge and painting the resulting render ops via
	``render_ops_painter.paint_ops()``.

	The bond item uses scene coordinates directly (it is not parented to
	an atom item) so that it can span between two atom positions.

	Args:
		bond_model: An object exposing ``atom1``, ``atom2`` (each with x, y),
			``order``, ``type``, and ``_chem_bond`` (the underlying OASA bond).
		parent: Optional parent QGraphicsItem.
	"""

	#============================================
	def __init__(self, bond_model, parent: PySide6.QtWidgets.QGraphicsItem = None):
		"""Initialize the bond item from a bond model.

		Args:
			bond_model: Bond data source with atom endpoints and chemistry.
			parent: Optional parent QGraphicsItem.
		"""
		super().__init__(parent)
		self._bond_model = bond_model
		# cached render ops from OASA
		self._ops: list = []
		# cached bounding rectangle
		self._bounding_rect = PySide6.QtCore.QRectF()
		# hover state
		self._hovered = False
		# configure item flags
		self.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
		self.setAcceptHoverEvents(True)
		# z-value puts bonds below atoms
		self.setZValue(BOND_Z_VALUE)
		# build initial render ops
		self.update_from_model()

	# ------------------------------------------------------------------
	# QGraphicsItem interface
	# ------------------------------------------------------------------

	#============================================
	def boundingRect(self) -> PySide6.QtCore.QRectF:
		"""Return the bounding rectangle for this item.

		Returns:
			QRectF that encloses all painted content plus padding.
		"""
		return self._bounding_rect

	#============================================
	def paint(self, painter: PySide6.QtGui.QPainter,
			option: PySide6.QtWidgets.QStyleOptionGraphicsItem,
			widget: PySide6.QtWidgets.QWidget = None) -> None:
		"""Paint the bond using cached render ops.

		Draws selection or hover highlights as a colored thick line
		along the bond axis before rendering the actual bond ops.

		Args:
			painter: The QPainter provided by the scene.
			option: Style options (unused beyond selection state).
			widget: Target widget (unused).
		"""
		# draw selection or hover highlight behind bond ops
		if self.isSelected() or self._hovered:
			if self.isSelected():
				highlight_color = PySide6.QtGui.QColor(_SELECTION_COLOR)
			else:
				highlight_color = PySide6.QtGui.QColor(_HOVER_COLOR)
			highlight_color.setAlpha(80)
			pen = PySide6.QtGui.QPen(highlight_color)
			pen.setWidthF(_HIT_PATH_WIDTH)
			pen.setCapStyle(PySide6.QtCore.Qt.PenCapStyle.RoundCap)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			# draw a thick highlight line between atom endpoints
			start, end = self._endpoint_positions()
			painter.drawLine(
				PySide6.QtCore.QPointF(start[0], start[1]),
				PySide6.QtCore.QPointF(end[0], end[1]),
			)
		# paint OASA render ops
		render_ops_painter.paint_ops(self._ops, painter)

	#============================================
	def shape(self) -> PySide6.QtGui.QPainterPath:
		"""Return a thick path along the bond line for easier click targeting.

		Returns:
			QPainterPath with a stroked outline around the bond axis.
		"""
		start, end = self._endpoint_positions()
		# build a thin line path
		line_path = PySide6.QtGui.QPainterPath()
		line_path.moveTo(start[0], start[1])
		line_path.lineTo(end[0], end[1])
		# stroke it into a thick region for hit testing
		stroker = PySide6.QtGui.QPainterPathStroker()
		stroker.setWidth(_HIT_PATH_WIDTH)
		stroker.setCapStyle(PySide6.QtCore.Qt.PenCapStyle.RoundCap)
		thick_path = stroker.createStroke(line_path)
		return thick_path

	# ------------------------------------------------------------------
	# Hover events
	# ------------------------------------------------------------------

	#============================================
	def hoverEnterEvent(self, event: PySide6.QtWidgets.QGraphicsSceneHoverEvent) -> None:
		"""Show a highlight when the mouse enters the bond.

		Args:
			event: The hover enter event.
		"""
		self._hovered = True
		self.update()

	#============================================
	def hoverLeaveEvent(self, event: PySide6.QtWidgets.QGraphicsSceneHoverEvent) -> None:
		"""Remove the highlight when the mouse leaves the bond.

		Args:
			event: The hover leave event.
		"""
		self._hovered = False
		self.update()

	# ------------------------------------------------------------------
	# Model synchronization
	# ------------------------------------------------------------------

	#============================================
	def update_from_model(self) -> None:
		"""Regenerate render ops from the bond model and update geometry.

		Reads atom endpoint positions from the bond model, builds render
		ops via ``build_bond_ops()``, and recomputes the bounding rect.
		"""
		self.prepareGeometryChange()
		start, end = self._endpoint_positions()
		# build a minimal BondRenderContext for standalone bond rendering
		chem_bond = self._bond_model._chem_bond
		context = oasa.render_lib.data_types.BondRenderContext(
			molecule=None,
			line_width=2.0,
			bond_width=6.0,
			wedge_width=6.0,
			bold_line_width_multiplier=1.2,
			bond_second_line_shortening=0.0,
			color_bonds=True,
			atom_colors=None,
			shown_vertices=set(),
			bond_coords={chem_bond: (start, end)},
			bond_coords_provider={chem_bond: (start, end)}.get,
			point_for_atom=None,
			label_targets={},
			attach_targets={},
			attach_constraints=oasa.render_lib.data_types.make_attach_constraints(),
		)
		self._ops = oasa.render_lib.bond_ops.build_bond_ops(
			chem_bond, start, end, context,
		)
		# recompute bounding rect from ops
		self._bounding_rect = _bounding_rect_from_ops(self._ops, start, end)
		self.update()

	#============================================
	def _endpoint_positions(self) -> tuple:
		"""Return start and end positions as (x, y) tuples.

		Reads from the bond model's atom1 and atom2 coordinate attributes.

		Returns:
			Tuple of ((x1, y1), (x2, y2)).
		"""
		a1 = self._bond_model.atom1
		a2 = self._bond_model.atom2
		start = (a1.x, a1.y)
		end = (a2.x, a2.y)
		return (start, end)

	# ------------------------------------------------------------------
	# Public properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def bond_model(self):
		"""The bond model this item visualizes."""
		return self._bond_model


#============================================
def _bounding_rect_from_ops(ops: list, start: tuple, end: tuple) -> PySide6.QtCore.QRectF:
	"""Compute a bounding rectangle from render ops and bond endpoints.

	Falls back to the bond endpoint line if ops produce no geometry.

	Args:
		ops: List of OASA render op dataclass instances.
		start: (x, y) tuple for the first atom.
		end: (x, y) tuple for the second atom.

	Returns:
		QRectF enclosing all ops and endpoints with padding.
	"""
	xs = [start[0], end[0]]
	ys = [start[1], end[1]]
	for op in ops:
		if isinstance(op, oasa.render_ops.LineOp):
			xs.extend([op.p1[0], op.p2[0]])
			ys.extend([op.p1[1], op.p2[1]])
		elif isinstance(op, oasa.render_ops.PolygonOp):
			for px, py in op.points:
				xs.append(px)
				ys.append(py)
		elif isinstance(op, oasa.render_ops.CircleOp):
			xs.extend([op.center[0] - op.radius, op.center[0] + op.radius])
			ys.extend([op.center[1] - op.radius, op.center[1] + op.radius])
		elif isinstance(op, oasa.render_ops.PathOp):
			for cmd, payload in op.commands:
				if payload is None:
					continue
				if cmd in ("M", "L"):
					xs.append(payload[0])
					ys.append(payload[1])
				elif cmd == "ARC":
					cx, cy, r = payload[0], payload[1], payload[2]
					xs.extend([cx - r, cx + r])
					ys.extend([cy - r, cy + r])
		elif isinstance(op, oasa.render_ops.TextOp):
			xs.append(op.x)
			ys.extend([op.y - op.font_size, op.y + op.font_size * 0.3])
	x_min = min(xs) - _BOUNDS_PADDING
	y_min = min(ys) - _BOUNDS_PADDING
	x_max = max(xs) + _BOUNDS_PADDING
	y_max = max(ys) + _BOUNDS_PADDING
	rect = PySide6.QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min)
	return rect
