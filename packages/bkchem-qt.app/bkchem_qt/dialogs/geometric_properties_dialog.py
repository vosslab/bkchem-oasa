"""Detached editor for geometric presentation stroke and fill appearance."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
def _button_foreground(color: str) -> str:
	"""Return readable text for one valid color-button background."""
	return "#ffffff" if PySide6.QtGui.QColor(color).lightness() < 128 else "#000000"


#============================================
class GeometricPropertiesDialog(PySide6.QtWidgets.QDialog):
	"""Edit width, stroke color, and optional fill as detached plain values."""

	#============================================
	def __init__(
			self, title: str, line_width: float, line_color: str,
			area_color: str | None, fillable: bool,
			parent: object | None = None,
			) -> None:
		"""Initialize one focused geometric appearance form."""
		super().__init__(parent)
		self._line_color = PySide6.QtGui.QColor(line_color).name()
		self._area_color = PySide6.QtGui.QColor(area_color or "#ffffff").name()
		self._fillable = fillable
		self.setWindowTitle(f"{title} Properties")
		self.setMinimumWidth(300)
		layout = PySide6.QtWidgets.QFormLayout(self)
		self._width_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._width_spin.setRange(0.1, 20.0)
		self._width_spin.setDecimals(3)
		self._width_spin.setSingleStep(0.1)
		self._width_spin.setValue(line_width)
		self._width_spin.setAccessibleName("Stroke width")
		layout.addRow("Stroke width:", self._width_spin)
		self._line_color_button = self._color_button(
			"Stroke color", "Choose the shape or line stroke color", self._pick_line_color,
		)
		layout.addRow("Stroke color:", self._line_color_button)
		self._fill_check = None
		self._area_color_button = None
		if fillable:
			self._fill_check = PySide6.QtWidgets.QCheckBox("Fill shape")
			self._fill_check.setChecked(area_color is not None)
			self._fill_check.setAccessibleName("Fill shape")
			self._fill_check.toggled.connect(self._set_fill_enabled)
			layout.addRow("Fill:", self._fill_check)
			self._area_color_button = self._color_button(
				"Fill color", "Choose the shape fill color", self._pick_area_color,
			)
			layout.addRow("Fill color:", self._area_color_button)
			self._set_fill_enabled(self._fill_check.isChecked())
		buttons = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel,
		)
		buttons.button(PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok).setText("Apply")
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addRow(buttons)
		self._refresh_color_buttons()
		self._initial_values = self.get_values()

	#============================================
	def _color_button(self, name: str, tooltip: str, callback: object) -> object:
		"""Build one labeled, keyboard-focusable color picker."""
		button = PySide6.QtWidgets.QPushButton()
		button.setMinimumHeight(28)
		button.setAccessibleName(name)
		button.setToolTip(tooltip)
		button.clicked.connect(callback)
		return button

	#============================================
	def _pick_line_color(self) -> None:
		"""Choose a stroke color without changing persistent state."""
		color = PySide6.QtWidgets.QColorDialog.getColor(
			PySide6.QtGui.QColor(self._line_color), self, "Stroke Color",
		)
		if color.isValid():
			self._line_color = color.name()
			self._refresh_color_buttons()

	#============================================
	def _pick_area_color(self) -> None:
		"""Choose a fill color without changing persistent state."""
		color = PySide6.QtWidgets.QColorDialog.getColor(
			PySide6.QtGui.QColor(self._area_color), self, "Fill Color",
		)
		if color.isValid():
			self._area_color = color.name()
			self._refresh_color_buttons()

	#============================================
	def _set_fill_enabled(self, enabled: bool) -> None:
		"""Expose fill color only while the positive Fill shape option is active."""
		if self._area_color_button is not None:
			self._area_color_button.setEnabled(enabled)

	#============================================
	def _refresh_color_buttons(self) -> None:
		"""Show color values as readable text as well as background swatches."""
		self._style_color_button(self._line_color_button, self._line_color)
		if self._area_color_button is not None:
			self._style_color_button(self._area_color_button, self._area_color)

	#============================================
	def _style_color_button(self, button: object, color: str) -> None:
		"""Apply one accessible text-and-swatch representation to a button."""
		button.setText(color)
		foreground = _button_foreground(color)
		button.setStyleSheet(
			f"background-color: {color}; color: {foreground}; "
			"border: 1px solid #888;",
		)

	#============================================
	def get_values(self) -> dict[str, object]:
		"""Return every plain editable appearance value."""
		values = {
			"line_width": self._width_spin.value(),
			"line_color": self._line_color,
		}
		if self._fillable:
			values["area_color"] = (
				self._area_color if self._fill_check.isChecked() else None
			)
		return values

	#============================================
	def changes(self) -> tuple[tuple[str, object], ...]:
		"""Return only explicit values changed after widget initialization."""
		return tuple(
			(name, value) for name, value in self.get_values().items()
			if value != self._initial_values[name]
		)
