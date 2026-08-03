"""QGraphicsItem subclass consuming portable atom render primitives."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
from bkchem_qt.canvas.items import render_ops_painter
from bkchem_qt.canvas.items import primitive_ops_painter
from bkchem_qt.bridge import oasa_bridge
from bkchem_qt.models.atom_model import AtomModel

# -- visual constants --
# extra padding around bounding rect for comfortable selection targeting
_BOUNDS_PADDING = 4.0
# pen width for selection highlight rectangle
_SELECTION_PEN_WIDTH = 1.5
# hover highlight pen width
_HOVER_PEN_WIDTH = 1.0
# z-value for atom items (above bonds)
ATOM_Z_VALUE = 10
# Number labels are a model projection, so they are children of their atom and
# naturally follow atom movement without becoming independent document items.
_NUMBER_FONT_FAMILY = "Arial"
_NUMBER_FONT_SIZE = 9
_NUMBER_OFFSET_X = 8.0
_NUMBER_OFFSET_Y = -12.0


#============================================
class AtomItem(PySide6.QtWidgets.QGraphicsItem):
	"""Visual representation of a single atom on the chemistry canvas.

	Consumes either an exact backend primitive batch or a bridge-normalized
	standalone compatibility batch, then delegates every paint path to the same
	portable Qt painter.
	Listens to the wrapped ``AtomModel.property_changed`` signal to
	regenerate ops when chemistry or display properties change.

	Args:
		atom_model: The AtomModel composition wrapper to visualize.
		parent: Optional parent QGraphicsItem.
	"""

	#============================================
	def __init__(self, atom_model: AtomModel, parent: PySide6.QtWidgets.QGraphicsItem = None) -> None:
		"""Initialize the atom item from an AtomModel.

		Args:
			atom_model: AtomModel whose chemistry and position drive rendering.
			parent: Optional parent QGraphicsItem.
		"""
		super().__init__(parent)
		self._atom_model = atom_model
		# cached portable primitives from the backend/session or compatibility bridge
		self._ops: tuple[object, ...] = ()
		# cached bounding rectangle
		self._bounding_rect = PySide6.QtCore.QRectF()
		# hover state tracked locally
		self._hovered = False
		# Keep a direct reference rather than discovering child graphics items by
		# a data tag. The model is the single source of truth for numbering.
		self._number_label: PySide6.QtWidgets.QGraphicsSimpleTextItem | None = None
		# configure item flags
		self.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
		self.setAcceptHoverEvents(True)
		# z-value puts atoms above bonds
		self.setZValue(ATOM_Z_VALUE)
		# initial position from model
		self.setPos(atom_model.x, atom_model.y)
		# connect model change signal
		atom_model.property_changed.connect(self._on_property_changed)
		self._model_signal_connected = True
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
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(render_ops_painter.get_canvas_color("selection")))
			pen.setWidthF(_SELECTION_PEN_WIDTH)
			pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			# QPainter centers a stroke on the supplied rectangle.  Keep the
			# interaction outline inside boundingRect(), as required by the
			# QGraphicsItem geometry contract.
			inset = _SELECTION_PEN_WIDTH / 2.0
			painter.drawRect(self._bounding_rect.adjusted(inset, inset, -inset, -inset))
		# draw hover highlight behind atom ops
		elif self._hovered:
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(render_ops_painter.get_canvas_color("hover")))
			pen.setWidthF(_HOVER_PEN_WIDTH)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			inset = _HOVER_PEN_WIDTH / 2.0
			painter.drawRect(self._bounding_rect.adjusted(inset, inset, -inset, -inset))
		primitive_ops_painter.paint(
			self._ops, painter,
			render_ops_painter._default_area_color, render_ops_painter._default_color,
		)

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

		Uses an exact backend primitive batch when supplied; standalone models
		request a normalized compatibility batch from the bridge.  The item never
		materializes or inspects an OASA operation.
		"""
		self.prepareGeometryChange()
		# position this item at the model coordinates
		self.setPos(self._atom_model.x, self._atom_model.y)
		batch = getattr(self._atom_model, "_backend_render_batch", None)
		if batch is not None:
			self._ops = batch.operations
			self._bounding_rect = primitive_ops_painter.bounds(batch.operations, _BOUNDS_PADDING)
			self._sync_number_label()
			self.update()
			return
		self._ops = oasa_bridge.legacy_atom_render_operations(self._atom_model)
		self._bounding_rect = primitive_ops_painter.bounds(self._ops, _BOUNDS_PADDING)
		self._sync_number_label()
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
		if name in ("number", "show_number"):
			self._sync_number_label()
		# regenerate ops for any visual change
		self.update_from_model()

	#============================================
	def _sync_number_label(self) -> None:
		"""Create, update, or hide the attached number label from model state."""
		number = self._atom_model.number
		visible = number is not None and self._atom_model.show_number
		if not visible:
			self._hide_number_label()
			return
		if self._number_label is None:
			label = PySide6.QtWidgets.QGraphicsSimpleTextItem(parent=self)
			font = PySide6.QtGui.QFont(_NUMBER_FONT_FAMILY, _NUMBER_FONT_SIZE)
			label.setFont(font)
			label.setBrush(PySide6.QtGui.QBrush(PySide6.QtGui.QColor(0, 0, 200)))
			label.setPos(_NUMBER_OFFSET_X, _NUMBER_OFFSET_Y)
			self._number_label = label
		self._number_label.setVisible(True)
		self._number_label.setText(str(number))

	#============================================
	def _hide_number_label(self) -> None:
		"""Keep an optional label attached until its parent crosses retirement."""
		if self._number_label is None:
			return
		self._number_label.setVisible(False)

	#============================================
	def dispose(self) -> None:
		"""Disconnect Python callbacks before the owning scene deletes the item."""
		# The label remains an attached graphics child until the coordinator has
		# snapshotted and terminally deleted the full tree.  Releasing this Python
		# attribute here cannot make native ownership fall through to GC.
		self._number_label = None
		if not self._model_signal_connected:
			return
		try:
			self._atom_model.property_changed.disconnect(
				self._on_property_changed
			)
		except (RuntimeError, TypeError):
			pass
		self._model_signal_connected = False

	# ------------------------------------------------------------------
	# Public properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def atom_model(self) -> AtomModel:
		"""The AtomModel this item visualizes."""
		return self._atom_model

	#============================================
	@property
	def number_label(self) -> PySide6.QtWidgets.QGraphicsSimpleTextItem | None:
		"""Return the model-projected number label, if it is currently visible."""
		return self._number_label


#============================================
