"""Focused plain-value editor for a Plus sign's visible root properties."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
class PlusDialog(PySide6.QtWidgets.QDialog):
	"""Edit only the portable root font size and color of one plain Plus."""

	#============================================
	def __init__(
			self, font_size: int, color: str, parent: object | None = None,
			) -> None:
		"""Initialize the detached Plus property dialog from plain values."""
		super().__init__(parent)
		self._color = PySide6.QtGui.QColor(color).name()
		self.setWindowTitle("Plus Properties")
		layout = PySide6.QtWidgets.QFormLayout(self)
		self._font_size_spin = PySide6.QtWidgets.QSpinBox()
		self._font_size_spin.setRange(4, 144)
		self._font_size_spin.setValue(font_size)
		layout.addRow("Font size:", self._font_size_spin)
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
			PySide6.QtGui.QColor(self._color), self, "Plus Color",
		)
		if color.isValid():
			self._color = color.name()
			self._update_color_button()

	#============================================
	def _update_color_button(self) -> None:
		"""Show the selected color on its picker button."""
		self._color_button.setStyleSheet(
			f"background-color: {self._color}; border: 1px solid #888;",
		)

	#============================================
	def get_font_size(self) -> int:
		"""Return the plain font size value."""
		return self._font_size_spin.value()

	#============================================
	def get_color(self) -> str:
		"""Return the canonical six-digit lowercase color value."""
		return self._color

	#============================================
	def get_values(self) -> dict[str, object]:
		"""Return every plain editable Plus value."""
		values = {"font_size": self.get_font_size(), "color": self.get_color()}
		return values

	#============================================
	def changes(self) -> tuple[tuple[str, object], ...]:
		"""Return only explicit values changed after widget initialization."""
		changes = tuple(
			(name, value) for name, value in self.get_values().items()
			if value != self._initial_values[name]
		)
		return changes
