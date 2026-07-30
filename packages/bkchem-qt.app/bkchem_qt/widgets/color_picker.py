"""Color picker button widget."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
from bkchem_qt.canvas.items import render_ops_painter


#============================================
class ColorPickerButton(PySide6.QtWidgets.QPushButton):
	"""Button that shows current color and opens QColorDialog on click.

	Displays a color swatch on the button face. Clicking opens a
	standard color dialog. When a new color is selected, the
	``color_changed`` signal is emitted with the hex color string.

	Args:
		color: Initial hex color string (e.g. "#000000").
		parent: Optional parent widget.
	"""

	# emitted when the user picks a new color
	color_changed = PySide6.QtCore.Signal(str)

	#============================================
	def __init__(self, color: str = "#000000", parent: object = None) -> None:
		"""Initialize the color picker button.

		Args:
			color: Initial hex color string.
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self._color = color
		self.setFixedSize(48, 24)
		self.setCursor(PySide6.QtCore.Qt.CursorShape.PointingHandCursor)
		self.clicked.connect(self._pick_color)
		self._update_style()

	#============================================
	@property
	def color(self) -> str:
		"""Return the current hex color string."""
		return self._color

	#============================================
	@color.setter
	def color(self, hex_color: str) -> None:
		"""Set the current color and update the swatch.

		Args:
			hex_color: Hex color string (e.g. "#ff0000").
		"""
		if hex_color != self._color:
			self._color = hex_color
			self._update_style()
			self.color_changed.emit(self._color)

	#============================================
	def _pick_color(self) -> None:
		"""Open QColorDialog and update color if user accepts."""
		initial = PySide6.QtGui.QColor(self._color)
		chosen = PySide6.QtWidgets.QColorDialog.getColor(
			initial, self, self.tr("Pick Color")
		)
		if chosen.isValid():
			self.color = chosen.name()

	#============================================
	def _update_style(self) -> None:
		"""Update the button stylesheet to show the current color swatch."""
		border_color = render_ops_painter.get_canvas_color("preview")
		self.setStyleSheet(
			f"background-color: {self._color}; border: 1px solid {border_color};"
		)

	#============================================
	def paintEvent(self, event: object) -> None:
		"""Draw the color swatch on the button.

		Fills the button with the current color and draws a thin
		border for contrast.

		Args:
			event: The QPaintEvent.
		"""
		# use the default push button painting first
		super().paintEvent(event)
		# overlay the color swatch
		painter = PySide6.QtGui.QPainter(self)
		painter.setRenderHint(PySide6.QtGui.QPainter.RenderHint.Antialiasing)
		# inset rectangle for the swatch
		margin = 3
		rect = self.rect().adjusted(margin, margin, -margin, -margin)
		painter.setPen(PySide6.QtCore.Qt.PenStyle.NoPen)
		painter.setBrush(PySide6.QtGui.QColor(self._color))
		painter.drawRect(rect)
		# thin border around the swatch
		painter.setPen(PySide6.QtGui.QPen(PySide6.QtGui.QColor(render_ops_painter.get_canvas_color("preview")), 1))
		painter.setBrush(PySide6.QtCore.Qt.BrushStyle.NoBrush)
		painter.drawRect(rect)
		painter.end()
