"""Focused plain-value editor for one Wavy line's visible root properties."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
class WavyDialog(PySide6.QtWidgets.QDialog):
	"""Edit only the portable root width and color of one plain Wavy line."""

	#============================================
	def __init__(self, width: float, line_color: str, parent: object | None = None) -> None:
		"""Initialize the detached Wavy property dialog from plain values."""
		super().__init__(parent)
		self._line_color = PySide6.QtGui.QColor(line_color).name()
		self.setWindowTitle("Wavy Properties")
		layout = PySide6.QtWidgets.QFormLayout(self)
		self._width_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._width_spin.setRange(0.1, 20.0)
		self._width_spin.setDecimals(3)
		self._width_spin.setValue(width)
		layout.addRow("Width:", self._width_spin)
		self._color_button = PySide6.QtWidgets.QPushButton()
		self._color_button.setFixedHeight(24)
		self._color_button.clicked.connect(self._pick_color)
		self._update_color_button()
		layout.addRow("Color:", self._color_button)
		buttons = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel,
		)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addRow(buttons)
		self._initial_values = self.get_values()

	#============================================
	def _pick_color(self) -> None:
		"""Choose one display color without changing persistent state."""
		color = PySide6.QtWidgets.QColorDialog.getColor(
			PySide6.QtGui.QColor(self._line_color), self, "Wavy Color",
		)
		if color.isValid():
			self._line_color = color.name()
			self._update_color_button()

	#============================================
	def _update_color_button(self) -> None:
		"""Show the selected color on its picker button."""
		self._color_button.setStyleSheet(
			f"background-color: {self._line_color}; border: 1px solid #888;",
		)

	#============================================
	def get_width(self) -> float:
		"""Return the plain visible line width."""
		return self._width_spin.value()

	#============================================
	def get_line_color(self) -> str:
		"""Return the canonical six-digit lowercase line color."""
		return self._line_color

	#============================================
	def get_values(self) -> dict[str, object]:
		"""Return every plain editable Wavy value."""
		return {"width": self.get_width(), "line_color": self.get_line_color()}

	#============================================
	def changes(self) -> tuple[tuple[str, object], ...]:
		"""Return only explicit values changed after widget initialization."""
		return tuple(
			(name, value) for name, value in self.get_values().items()
			if value != self._initial_values[name]
		)
