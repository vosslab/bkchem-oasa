"""Focused plain-value editor for a Plus sign's visible root properties."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
class PlusDialog(PySide6.QtWidgets.QDialog):
	"""Edit the portable font and colors of one plain Plus."""

	#============================================
	def __init__(
			self, font_size: int, color: str, parent: object | None = None,
			background_color: str | None = None, font_family: str = "helvetica",
			) -> None:
		"""Initialize the detached Plus property dialog from plain values."""
		super().__init__(parent)
		self._color = PySide6.QtGui.QColor(color).name()
		self._background_color = PySide6.QtGui.QColor(
			background_color or "#ffffff",
		).name()
		self.setWindowTitle("Plus Properties")
		layout = PySide6.QtWidgets.QFormLayout(self)
		self._font_size_spin = PySide6.QtWidgets.QSpinBox()
		self._font_size_spin.setRange(4, 144)
		self._font_size_spin.setValue(font_size)
		layout.addRow("Font size:", self._font_size_spin)
		self._font_family_combo = PySide6.QtWidgets.QFontComboBox()
		self._font_family_combo.setCurrentFont(PySide6.QtGui.QFont(font_family))
		self._font_family_combo.setAccessibleName("Plus font family")
		self._font_family_combo.setToolTip("Choose the Plus font family")
		layout.addRow("Font family:", self._font_family_combo)
		self._color_button = PySide6.QtWidgets.QPushButton()
		self._color_button.setMinimumHeight(28)
		self._color_button.setAccessibleName("Plus color")
		self._color_button.setToolTip("Choose the Plus foreground color")
		self._color_button.clicked.connect(self._pick_color)
		layout.addRow("Foreground color:", self._color_button)
		self._background_check = PySide6.QtWidgets.QCheckBox("Fill background")
		self._background_check.setChecked(background_color is not None)
		self._background_check.setAccessibleName("Fill Plus background")
		layout.addRow("Background:", self._background_check)
		self._background_button = PySide6.QtWidgets.QPushButton()
		self._background_button.setMinimumHeight(28)
		self._background_button.setAccessibleName("Plus background color")
		self._background_button.setToolTip(
			"Choose the color used when Fill background is selected",
		)
		self._background_button.clicked.connect(self._pick_background_color)
		layout.addRow("Background color:", self._background_button)
		self._update_color_button()
		buttons = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel,
		)
		buttons.button(PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok).setText("Apply")
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
	def _pick_background_color(self) -> None:
		"""Choose one background color without changing persistent state."""
		color = PySide6.QtWidgets.QColorDialog.getColor(
			PySide6.QtGui.QColor(self._background_color), self, "Plus Background Color",
		)
		if color.isValid():
			self._background_color = color.name()
			self._update_color_button()

	def _update_color_button(self) -> None:
		"""Show both selected colors as readable text and background swatches."""
		self._style_color_button(self._color_button, self._color)
		self._style_color_button(self._background_button, self._background_color)

	#============================================
	def _style_color_button(self, button: object, color: str) -> None:
		"""Style one picker with a contrasting textual color value."""
		button.setText(color)
		display_color = "#f5f5f5" if color == "#ffffff" else color
		foreground = (
			"#ffffff" if PySide6.QtGui.QColor(color).lightness() < 128 else "#000000"
		)
		button.setStyleSheet(
			f"QPushButton {{ background-color: {display_color}; color: {foreground}; "
			f"border: 1px solid #888; }}",
		)

	#============================================
	def get_font_size(self) -> int:
		"""Return the plain font size value."""
		return self._font_size_spin.value()

	#============================================
	def get_font_family(self) -> str:
		"""Return the selected installed font family."""
		return self._font_family_combo.currentFont().family()

	#============================================
	def get_color(self) -> str:
		"""Return the canonical six-digit lowercase color value."""
		return self._color

	#============================================
	def get_background_color(self) -> str | None:
		"""Return the explicit background color or transparent intent."""
		if not self._background_check.isChecked():
			return None
		return self._background_color

	#============================================
	def get_values(self) -> dict[str, object]:
		"""Return every plain editable Plus value."""
		values = {
			"font_family": self.get_font_family(), "font_size": self.get_font_size(),
			"color": self.get_color(),
			"background_color": self.get_background_color(),
		}
		return values

	#============================================
	def changes(self) -> tuple[tuple[str, object], ...]:
		"""Return only explicit values changed after widget initialization."""
		changes = tuple(
			(name, value) for name, value in self.get_values().items()
			if value != self._initial_values[name]
		)
		return changes
