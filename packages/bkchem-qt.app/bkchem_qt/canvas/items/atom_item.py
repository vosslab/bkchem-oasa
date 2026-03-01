"""QGraphicsItem subclass for rendering an atom using OASA render ops."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
from bkchem_qt.canvas.items import render_ops_painter
from bkchem_qt.models.atom_model import AtomModel
import oasa.render_lib.molecule_ops

# -- visual constants --
# extra padding around bounding rect for comfortable selection targeting
_BOUNDS_PADDING = 4.0
# pen width for selection highlight rectangle
_SELECTION_PEN_WIDTH = 1.5
# selection highlight color (semi-transparent blue)
_SELECTION_COLOR = "#3399ff"
# hover highlight color (semi-transparent light blue)
_HOVER_COLOR = "#66bbff"
# hover highlight pen width
_HOVER_PEN_WIDTH = 1.0
# z-value for atom items (above bonds)
ATOM_Z_VALUE = 10


#============================================
class AtomItem(PySide6.QtWidgets.QGraphicsItem):
	"""Visual representation of a single atom on the chemistry canvas.

	Delegates rendering to OASA's ``build_vertex_ops()`` and paints the
	resulting render ops through ``render_ops_painter.paint_ops()``.
	Listens to the wrapped ``AtomModel.property_changed`` signal to
	regenerate ops when chemistry or display properties change.

	Args:
		atom_model: The AtomModel composition wrapper to visualize.
		parent: Optional parent QGraphicsItem.
	"""

	#============================================
	def __init__(self, atom_model: AtomModel, parent: PySide6.QtWidgets.QGraphicsItem = None):
		"""Initialize the atom item from an AtomModel.

		Args:
			atom_model: AtomModel whose chemistry and position drive rendering.
			parent: Optional parent QGraphicsItem.
		"""
		super().__init__(parent)
		self._atom_model = atom_model
		# cached render ops from OASA
		self._ops: list = []
		# cached bounding rectangle
		self._bounding_rect = PySide6.QtCore.QRectF()
		# hover state tracked locally
		self._hovered = False
		# configure item flags
		self.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
		self.setAcceptHoverEvents(True)
		# z-value puts atoms above bonds
		self.setZValue(ATOM_Z_VALUE)
		# initial position from model
		self.setPos(atom_model.x, atom_model.y)
		# connect model change signal
		atom_model.property_changed.connect(self._on_property_changed)
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
		"""Paint the atom using cached render ops.

		Draws selection and hover highlights as colored rectangles
		behind the atom label when the item is selected or hovered.

		Args:
			painter: The QPainter provided by the scene.
			option: Style options (unused beyond selection state).
			widget: Target widget (unused).
		"""
		# draw selection highlight behind atom ops
		if self.isSelected():
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(_SELECTION_COLOR))
			pen.setWidthF(_SELECTION_PEN_WIDTH)
			pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			painter.drawRect(self._bounding_rect)
		# draw hover highlight behind atom ops
		elif self._hovered:
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(_HOVER_COLOR))
			pen.setWidthF(_HOVER_PEN_WIDTH)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			painter.drawRect(self._bounding_rect)
		# paint OASA render ops
		render_ops_painter.paint_ops(self._ops, painter)

	#============================================
	def shape(self) -> PySide6.QtGui.QPainterPath:
		"""Return the shape used for hit testing and collision detection.

		Returns:
			QPainterPath slightly larger than bounding rect for easier clicking.
		"""
		path = PySide6.QtGui.QPainterPath()
		# inflate the bounding rect a bit for easier targeting
		inflated = self._bounding_rect.adjusted(
			-_BOUNDS_PADDING, -_BOUNDS_PADDING,
			_BOUNDS_PADDING, _BOUNDS_PADDING,
		)
		path.addRect(inflated)
		return path

	# ------------------------------------------------------------------
	# Hover events
	# ------------------------------------------------------------------

	#============================================
	def hoverEnterEvent(self, event: PySide6.QtWidgets.QGraphicsSceneHoverEvent) -> None:
		"""Show a subtle highlight when the mouse enters the atom.

		Args:
			event: The hover enter event.
		"""
		self._hovered = True
		self.update()

	#============================================
	def hoverLeaveEvent(self, event: PySide6.QtWidgets.QGraphicsSceneHoverEvent) -> None:
		"""Remove the highlight when the mouse leaves the atom.

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
		"""Regenerate render ops from the atom model and update geometry.

		Calls ``oasa.render_lib.molecule_ops.build_vertex_ops()`` on the
		underlying OASA atom, using local item coordinates (the item's
		scene position is set separately via ``setPos``). The bounding
		rectangle is recomputed from the resulting ops.
		"""
		self.prepareGeometryChange()
		# position this item at the model coordinates
		self.setPos(self._atom_model.x, self._atom_model.y)
		# build ops in local coordinates (origin at atom position)
		# pass the underlying OASA atom so render_lib can read chemistry
		chem_atom = self._atom_model._chem_atom
		# temporarily set chem_atom coords to 0,0 for local-space rendering
		saved_x = chem_atom.x
		saved_y = chem_atom.y
		chem_atom.x = 0.0
		chem_atom.y = 0.0
		self._ops = oasa.render_lib.molecule_ops.build_vertex_ops(
			chem_atom,
			transform_xy=None,
			show_hydrogens_on_hetero=self._atom_model.show_hydrogens,
			color_atoms=True,
			atom_colors=None,
			font_name="Arial",
			font_size=self._atom_model.font_size,
		)
		# restore chem_atom coords
		chem_atom.x = saved_x
		chem_atom.y = saved_y
		# recompute bounding rect from ops
		self._bounding_rect = _bounding_rect_from_ops(self._ops)
		self.update()

	#============================================
	def _on_property_changed(self, name: str, value: object) -> None:
		"""Slot called when any AtomModel property changes.

		Args:
			name: Name of the changed property.
			value: New value of the property.
		"""
		if name in ("x", "y"):
			self.setPos(self._atom_model.x, self._atom_model.y)
		# regenerate ops for any visual change
		self.update_from_model()

	# ------------------------------------------------------------------
	# Public properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def atom_model(self) -> AtomModel:
		"""The AtomModel this item visualizes."""
		return self._atom_model


#============================================
def _bounding_rect_from_ops(ops: list) -> PySide6.QtCore.QRectF:
	"""Compute a bounding rectangle that encloses all render ops.

	Examines line endpoints, polygon points, circle extents, path
	command coordinates, and text origins to find the enclosing rect.

	Args:
		ops: List of OASA render op dataclass instances.

	Returns:
		QRectF enclosing all ops, with padding. Returns a small default
		rect if ops is empty.
	"""
	if not ops:
		# default small rect so the item is still clickable
		return PySide6.QtCore.QRectF(-8, -8, 16, 16)
	import oasa.render_ops
	xs = []
	ys = []
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
					# approximate with center +/- radius
					cx, cy, r = payload[0], payload[1], payload[2]
					xs.extend([cx - r, cx + r])
					ys.extend([cy - r, cy + r])
		elif isinstance(op, oasa.render_ops.TextOp):
			# rough estimate: text occupies font_size height and some width
			xs.append(op.x)
			ys.append(op.y - op.font_size)
			ys.append(op.y + op.font_size * 0.3)
			# estimate width from character count
			estimated_width = len(op.text) * op.font_size * 0.6
			xs.append(op.x + estimated_width)
	if not xs or not ys:
		return PySide6.QtCore.QRectF(-8, -8, 16, 16)
	x_min = min(xs) - _BOUNDS_PADDING
	y_min = min(ys) - _BOUNDS_PADDING
	x_max = max(xs) + _BOUNDS_PADDING
	y_max = max(ys) + _BOUNDS_PADDING
	rect = PySide6.QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min)
	return rect
