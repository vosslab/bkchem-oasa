"""QGraphicsItem subclass consuming portable bond render primitives."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
from bkchem_qt.canvas.items import primitive_ops_painter
from bkchem_qt.canvas.items import render_ops_painter
from bkchem_qt.bridge import oasa_bridge
from bkchem_qt.models.bond_model import BondModel

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

	Consumes either an exact backend primitive batch or a bridge-normalized
	standalone compatibility batch and delegates every paint path to the same
	portable Qt painter.

	The bond item uses scene coordinates directly (it is not parented to
	an atom item) so that it can span between two atom positions.

	Args:
		bond_model: An object exposing ``atom1``, ``atom2`` (each with x, y),
			``order``, ``type``, and scalar depiction facts.
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
		# cached portable primitives from the backend/session or compatibility bridge
		self._ops: tuple[object, ...] = ()
		# A synchronized batch is immutable.  This Qt-local cache is replaced on
		# every endpoint update during a transient drag and never reaches OASA.
		self._backend_preview_operations: tuple[object, ...] = ()
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
		operations = self._backend_preview_operations or self._ops
		primitive_ops_painter.paint(
			operations, painter,
			render_ops_painter._default_area_color, render_ops_painter._default_color,
		)

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

		Uses an exact backend primitive batch when supplied.  Otherwise it passes
		scalar endpoint models and finite positions to the compatibility bridge,
		which owns OASA context and label clipping construction.
		"""
		self.prepareGeometryChange()
		batch = getattr(self._bond_model, "_backend_render_batch", None)
		if batch is not None:
			self._ops = ()
			self._backend_preview_operations = self._backend_drag_operations(batch)
			bounds = primitive_ops_painter.bounds(
				self._backend_preview_operations, _BOUNDS_PADDING,
			)
			self._bounding_rect = _interaction_bounds(bounds, self._endpoint_positions())
			self.update()
			return
		start, end = self._endpoint_positions()
		a1_model = self._bond_model.atom1
		a2_model = self._bond_model.atom2
		self._ops = oasa_bridge.legacy_bond_render_operations(
			self._bond_model, a1_model, a2_model, start, end,
		)
		bounds = primitive_ops_painter.bounds(self._ops, _BOUNDS_PADDING)
		self._bounding_rect = _interaction_bounds(bounds, (start, end))
		self._backend_preview_operations = ()
		self.update()

	#============================================
	def _backend_drag_operations(self, batch: object) -> tuple[object, ...]:
		"""Derive the live Qt drag geometry from immutable accepted bond facts."""
		if batch.endpoint_positions is None:
			return batch.operations
		return primitive_ops_painter.transformed_operations(
			batch.operations, batch.endpoint_positions, self._endpoint_positions(),
		)

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
		self._backend_preview_operations = ()
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
def _interaction_bounds(
		bounds: PySide6.QtCore.QRectF,
		endpoints: tuple[tuple[float, float], tuple[float, float]],
		) -> PySide6.QtCore.QRectF:
	"""Include the full selection/hover axis in one conservative item bound."""
	start, end = endpoints
	half_width = _HIT_PATH_WIDTH / 2.0
	axis_bounds = PySide6.QtCore.QRectF(
		min(start[0], end[0]) - half_width,
		min(start[1], end[1]) - half_width,
		abs(end[0] - start[0]) + _HIT_PATH_WIDTH,
		abs(end[1] - start[1]) + _HIT_PATH_WIDTH,
	)
	return bounds.united(axis_bounds)


#============================================
