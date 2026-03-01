"""Text annotation graphics item."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# -- visual constants --
# selection highlight color
_SELECTION_COLOR = "#3399ff"
# hover highlight color
_HOVER_COLOR = "#66bbff"
# default font family
_DEFAULT_FONT_FAMILY = "Arial"
# default font size
_DEFAULT_FONT_SIZE = 12


#============================================
class TextItem(PySide6.QtWidgets.QGraphicsTextItem):
	"""Rich text item for annotations on the canvas.

	Wraps QGraphicsTextItem with selection and hover highlighting,
	plus convenience methods for setting text, font size, and color.

	Args:
		text: Initial text content.
		parent: Optional parent QGraphicsItem.
	"""

	#============================================
	def __init__(self, text="", parent=None):
		"""Initialize the text item.

		Args:
			text: Initial text content.
			parent: Optional parent QGraphicsItem.
		"""
		super().__init__(text, parent)
		self._hovered = False
		# set default font
		font = PySide6.QtGui.QFont(_DEFAULT_FONT_FAMILY, _DEFAULT_FONT_SIZE)
		self.setFont(font)
		# default color
		self.setDefaultTextColor(PySide6.QtGui.QColor("#000000"))
		# configure item flags
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
			True,
		)
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
			True,
		)
		self.setAcceptHoverEvents(True)

	# ------------------------------------------------------------------
	# Convenience methods
	# ------------------------------------------------------------------

	#============================================
	def set_text(self, text: str) -> None:
		"""Set the displayed text content.

		Args:
			text: Plain text string to display.
		"""
		self.setPlainText(text)

	#============================================
	def set_font_size(self, size: int) -> None:
		"""Set the font size.

		Args:
			size: Font size in points.
		"""
		font = self.font()
		font.setPointSize(size)
		self.setFont(font)

	#============================================
	def set_color(self, color: str) -> None:
		"""Set the text color.

		Args:
			color: Color string in hex format (e.g. '#ff0000').
		"""
		self.setDefaultTextColor(PySide6.QtGui.QColor(color))

	# ------------------------------------------------------------------
	# Hover events
	# ------------------------------------------------------------------

	#============================================
	def hoverEnterEvent(self, event) -> None:
		"""Show a subtle highlight when the mouse enters the text.

		Args:
			event: The hover enter event.
		"""
		self._hovered = True
		self.update()

	#============================================
	def hoverLeaveEvent(self, event) -> None:
		"""Remove the highlight when the mouse leaves the text.

		Args:
			event: The hover leave event.
		"""
		self._hovered = False
		self.update()

	#============================================
	def paint(self, painter: PySide6.QtGui.QPainter,
			option: PySide6.QtWidgets.QStyleOptionGraphicsItem,
			widget: PySide6.QtWidgets.QWidget = None) -> None:
		"""Paint the text item with optional selection/hover highlight.

		Args:
			painter: The QPainter provided by the scene.
			option: Style options.
			widget: Target widget (unused).
		"""
		# draw highlight rectangle behind the text
		if self.isSelected():
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(_SELECTION_COLOR))
			pen.setWidthF(1.5)
			pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			painter.drawRect(self.boundingRect())
		elif self._hovered:
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(_HOVER_COLOR))
			pen.setWidthF(1.0)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			painter.drawRect(self.boundingRect())
		# draw the text itself
		super().paint(painter, option, widget)
