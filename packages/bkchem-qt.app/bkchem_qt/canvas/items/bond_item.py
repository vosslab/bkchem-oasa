"""QGraphicsItem subclass for rendering a bond using OASA render ops."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
from bkchem_qt.canvas.items import render_ops_painter
from bkchem_qt.models.atom_model import AtomModel
from bkchem_qt.models.bond_model import BondModel
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

	# atom property names that affect label geometry and bond clipping
	_LABEL_AFFECTING_PROPS = frozenset({
		"symbol", "charge", "font_family", "font_size", "show", "show_hydrogens", "x", "y",
	})
	# BondModel fields that change OASA render ops or their geometry.
	_RENDER_AFFECTING_PROPS = frozenset({
		"order", "type", "aromatic", "line_color", "line_width", "bond_width",
		"wedge_width", "center", "simple_double", "auto_bond_sign",
		"double_length_ratio", "equithick", "wavy_style",
	})

	#============================================
	def __init__(self, bond_model: BondModel, parent: PySide6.QtWidgets.QGraphicsItem = None) -> None:
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
		self._connected_endpoint_models = []
		self._model_signals_connected = True
		# connect endpoint atom signals so label changes trigger bond redraw
		self._connect_endpoint_signals()
		self._bond_model.property_changed.connect(self._on_bond_property_changed)
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
				highlight_color = PySide6.QtGui.QColor(render_ops_painter.get_canvas_color("selection"))
			else:
				highlight_color = PySide6.QtGui.QColor(render_ops_painter.get_canvas_color("hover"))
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
		Computes label attach targets for both endpoint atoms so bonds
		clip at atom label boundaries instead of drawing through them.
		"""
		self.prepareGeometryChange()
		start, end = self._endpoint_positions()
		chem_bond = self._bond_model._chem_bond
		# compute label attach targets for endpoint atoms
		a1_model = self._bond_model.atom1
		a2_model = self._bond_model.atom2
		shown_vertices, label_targets, attach_targets = _endpoint_label_targets(
			(a1_model, a2_model),
		)
		context = oasa.render_lib.data_types.BondRenderContext(
			molecule=None,
			line_width=self._bond_model.line_width,
			bond_width=self._bond_model.bond_width,
			wedge_width=self._bond_model.wedge_width,
			bold_line_width_multiplier=1.2,
			bond_second_line_shortening=0.0,
			color_bonds=True,
			atom_colors=None,
			shown_vertices=shown_vertices,
			bond_coords={chem_bond: (start, end)},
			bond_coords_provider={chem_bond: (start, end)}.get,
			point_for_atom=None,
			label_targets=label_targets,
			attach_targets=attach_targets,
			attach_constraints=oasa.render_lib.data_types.make_attach_constraints(
			),
		)
		self._ops = oasa.render_lib.bond_ops.build_bond_ops(
			chem_bond, start, end, context,
		)
		# recompute bounding rect from ops
		self._bounding_rect = _bounding_rect_from_ops(self._ops, start, end)
		self.update()

	#============================================
	def _connect_endpoint_signals(self) -> None:
		"""Connect property_changed signals from both endpoint AtomModels.

		When an endpoint atom's label-affecting property changes (symbol,
		charge, font_size, etc.), the bond needs to recompute its render
		ops so bond endpoints clip correctly at label boundaries.
		"""
		a1_model = self._bond_model.atom1
		a2_model = self._bond_model.atom2
		if a1_model is not None:
			a1_model.property_changed.connect(self._on_endpoint_property_changed)
			self._connected_endpoint_models.append(a1_model)
		if a2_model is not None:
			a2_model.property_changed.connect(self._on_endpoint_property_changed)
			self._connected_endpoint_models.append(a2_model)

	#============================================
	def _on_endpoint_property_changed(self, name: str, value: object) -> None:
		"""Handle property changes on endpoint atoms.

		Filters on label-affecting properties and triggers a full
		update_from_model() to recompute bond clipping.

		Args:
			name: Name of the changed property.
			value: New value of the property (unused).
		"""
		if name in self._LABEL_AFFECTING_PROPS:
			self.update_from_model()

	#============================================
	def _on_bond_property_changed(self, name: str, value: object) -> None:
		"""Rebuild cached geometry after a render-affecting bond mutation.

		Args:
			name: Name of the changed bond property.
			value: New value of the property (unused).
		"""
		if name in self._RENDER_AFFECTING_PROPS:
			self.update_from_model()

	#============================================
	def dispose(self) -> None:
		"""Disconnect model callbacks before the owning scene deletes the item."""
		if not self._model_signals_connected:
			return
		for atom_model in self._connected_endpoint_models:
			try:
				atom_model.property_changed.disconnect(
					self._on_endpoint_property_changed
				)
			except (RuntimeError, TypeError):
				pass
		try:
			self._bond_model.property_changed.disconnect(
				self._on_bond_property_changed
			)
		except (RuntimeError, TypeError):
			pass
		self._connected_endpoint_models.clear()
		self._model_signals_connected = False

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
	def bond_model(self) -> BondModel:
		"""The bond model this item visualizes."""
		return self._bond_model


#============================================
def _endpoint_label_targets(
		atom_models: tuple[AtomModel, AtomModel],
		) -> tuple[set[object], dict[object, object], dict[object, object]]:
	"""Build clipping targets with each endpoint's own display typography.

	The OASA target builder accepts one typography configuration per call.  A
	bond can join independently styled atoms, so calculate each endpoint
	separately and merge their model-keyed targets for the shared bond context.
	"""
	shown_vertices = set()
	label_targets = {}
	attach_targets = {}
	for atom_model in atom_models:
		# AtomModel.show is a frontend display override.  A hidden atom has no
		# visible label, so its bond endpoint must remain at the atom position.
		if not atom_model.show:
			continue
		shown, labels, attaches = (
			oasa.render_lib.molecule_ops.build_label_attach_targets(
				vertices=[atom_model._chem_atom],
				show_hydrogens_on_hetero=bool(atom_model.show_hydrogens),
				font_name=atom_model.font_family,
				font_size=float(atom_model.font_size),
			)
		)
		shown_vertices.update(shown)
		label_targets.update(labels)
		attach_targets.update(attaches)
	return shown_vertices, label_targets, attach_targets


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
