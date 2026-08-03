"""Text annotation graphics item."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
from bkchem_qt.canvas.items import render_ops_painter

# -- visual constants --
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
	def __init__(self, text: str = "",
			parent: PySide6.QtWidgets.QGraphicsItem = None) -> None:
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
		# default color from theme
		self.setDefaultTextColor(render_ops_painter._default_color)
		# configure item flags
		self.setFlag(
			PySide6.QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
			True,
		)
		self.setAcceptHoverEvents(True)
		self._disposed = False

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
	def set_formatted_text_runs(
			self, runs: tuple[tuple[str, tuple[str, ...]], ...],
			) -> None:
		"""Build this disposable item's document from plain authored run values."""
		if type(runs) is not tuple:
			raise TypeError("Formatted Text runs must be an immutable tuple")
		document = self.document()
		document.clear()
		document.setDefaultFont(self.font())
		cursor = PySide6.QtGui.QTextCursor(document)
		for text, styles in runs:
			if type(text) is not str or type(styles) is not tuple:
				raise TypeError("Formatted Text runs must contain plain text/style tuples")
			format = PySide6.QtGui.QTextCharFormat()
			if "b" in styles:
				format.setFontWeight(PySide6.QtGui.QFont.Weight.Bold)
			if "i" in styles:
				format.setFontItalic(True)
			if "sub" in styles:
				format.setVerticalAlignment(
					PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSubScript,
				)
			if "sup" in styles:
				format.setVerticalAlignment(
					PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSuperScript,
				)
			cursor.insertText(text, format)

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
	def hoverEnterEvent(self, event: PySide6.QtWidgets.QGraphicsSceneHoverEvent) -> None:
		"""Show a subtle highlight when the mouse enters the text.

		Args:
			event: The hover enter event.
		"""
		self._hovered = True
		self.update()

	#============================================
	def hoverLeaveEvent(self, event: PySide6.QtWidgets.QGraphicsSceneHoverEvent) -> None:
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
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(render_ops_painter.get_canvas_color("selection")))
			pen.setWidthF(1.5)
			pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			painter.drawRect(self.boundingRect())
		elif self._hovered:
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(render_ops_painter.get_canvas_color("hover")))
			pen.setWidthF(1.0)
			painter.setPen(pen)
			painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
			painter.drawRect(self.boundingRect())
		# draw the text itself
		super().paint(painter, option, widget)

	#============================================
	def dispose(self) -> None:
		"""Release projection-owned callbacks before scene teardown."""
		self._disposed = True
