"""Minimal selectable projection for a native CDML group pseudo-vertex."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets


_PADDING = 4.0


#============================================
class GroupItem(PySide6.QtWidgets.QGraphicsItem):
	"""Paint one GroupModel label without making the projection authoritative."""

	#============================================
	def __init__(self, group_model: object,
			parent: PySide6.QtWidgets.QGraphicsItem | None = None) -> None:
		"""Create the selectable group label at its retained CDML position."""
		super().__init__(parent)
		self._group_model = group_model
		self._font = _font_for(group_model)
		self._rect = _label_rect(group_model.name, self._font)
		self.setPos(group_model.x, group_model.y)
		self.setFlag(PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
		self.setAcceptHoverEvents(True)
		self.setToolTip(_tooltip_for(group_model))
		group_model.changed.connect(self._refresh)
		self._connected = True

	#============================================
	def boundingRect(self) -> PySide6.QtCore.QRectF:
		"""Return the label bounds with a stable selection margin."""
		return self._rect.adjusted(-_PADDING, -_PADDING, _PADDING, _PADDING)

	#============================================
	def paint(self, painter: PySide6.QtGui.QPainter,
			option: PySide6.QtWidgets.QStyleOptionGraphicsItem,
			widget: PySide6.QtWidgets.QWidget | None = None) -> None:
		"""Paint the abbreviation and a warning border for retained raw content."""
		painter.setFont(self._font)
		painter.setPen(PySide6.QtGui.QColor("#b35a00") if not self._group_model.supported
				else PySide6.QtGui.QColor("black"))
		painter.drawText(self._rect, PySide6.QtCore.Qt.AlignmentFlag.AlignCenter,
				self._group_model.name or "?")
		if self.isSelected() or not self._group_model.supported:
			pen = PySide6.QtGui.QPen(
				PySide6.QtGui.QColor("#d67b00") if not self._group_model.supported
				else PySide6.QtGui.QColor("#3b82f6"),
				1.25,
			)
			pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			painter.drawRect(self.boundingRect())

	#============================================
	def dispose(self) -> None:
		"""Disconnect the model signal before scene or Python teardown."""
		if not self._connected:
			return
		try:
			self._group_model.changed.disconnect(self._refresh)
		except (RuntimeError, TypeError):
			pass
		self._connected = False

	#============================================
	@property
	def group_model(self) -> object:
		"""Return this item's durable GroupModel identity."""
		return self._group_model

	#============================================
	def _refresh(self) -> None:
		"""Refresh retained position/style after a future structural update."""
		self.prepareGeometryChange()
		self._font = _font_for(self._group_model)
		self._rect = _label_rect(self._group_model.name, self._font)
		self.setPos(self._group_model.x, self._group_model.y)
		self.setToolTip(_tooltip_for(self._group_model))
		self.update()


#============================================
def _font_for(group_model: object) -> PySide6.QtGui.QFont:
	"""Build a label font from retained CDML style without global defaults."""
	attributes = dict(group_model.font_attributes)
	font = PySide6.QtGui.QFont(attributes.get("family", "Arial"))
	if "size" in attributes:
		font.setPointSizeF(float(attributes["size"]))
	return font


#============================================
def _label_rect(text: str, font: PySide6.QtGui.QFont) -> PySide6.QtCore.QRectF:
	"""Measure label geometry in the item's local coordinate system."""
	metrics = PySide6.QtGui.QFontMetricsF(font)
	rect = metrics.boundingRect(text or "?")
	rect.moveCenter(PySide6.QtCore.QPointF())
	return rect


#============================================
def _tooltip_for(group_model: object) -> str:
	"""Expose retained unsupported content rather than presenting it as editable."""
	if group_model.supported:
		return "CDML group: %s" % (group_model.name or "unnamed")
	return "CDML group retained without editing: %s" % group_model.unsupported_reason
