"""Arrow properties dialog."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
class ArrowDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for editing arrow properties.

	Presents checkboxes for start/end arrowheads, a line width spinner,
	a spline curve toggle, and a color picker button.

	Args:
		parent: Optional parent widget.
		start_head: Whether the arrow has a head at the start.
		end_head: Whether the arrow has a head at the end.
		line_width: Line width in pixels.
		spline: Whether the arrow uses its authored spline control points.
		color: Color string (hex format).
	"""

	#============================================
	def __init__(self, parent: object | None = None, start_head: bool = False,
			end_head: bool = True, line_width: float = 2.0,
			spline: bool = False, color: str = "#000000") -> None:
		"""Initialize the arrow properties dialog.

		Args:
			parent: Optional parent widget.
			start_head: Initial state for start arrowhead.
			end_head: Initial state for end arrowhead.
			line_width: Initial line width.
			spline: Initial spline state.
			color: Initial color in hex format.
		"""
		super().__init__(parent)
		self._color = PySide6.QtGui.QColor(color).name()
		self.setWindowTitle("Arrow Properties")
		self.setMinimumWidth(280)
		self._build_ui()
		self._start_head_check.setChecked(start_head)
		self._end_head_check.setChecked(end_head)
		self._line_width_spin.setValue(line_width)
		self._spline_check.setChecked(spline)
		self._update_color_button()
		self._initial_values = self.get_values()

	#============================================
	def _build_ui(self) -> None:
		"""Build the form layout with all property fields."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		form = PySide6.QtWidgets.QFormLayout()

		self._start_head_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Start arrowhead:", self._start_head_check)

		self._end_head_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("End arrowhead:", self._end_head_check)

		self._line_width_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._line_width_spin.setRange(0.1, 20.0)
		self._line_width_spin.setSingleStep(0.1)
		self._line_width_spin.setDecimals(3)
		self._line_width_spin.setValue(2.0)
		form.addRow("Line width:", self._line_width_spin)

		self._spline_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Spline curve:", self._spline_check)

		self._color_button = PySide6.QtWidgets.QPushButton()
		self._color_button.setFixedHeight(24)
		self._color_button.setAccessibleName("Arrow color")
		self._color_button.setToolTip("Choose the arrow line color")
		self._color_button.clicked.connect(self._pick_color)
		form.addRow("Color:", self._color_button)

		layout.addLayout(form)

		button_box = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel
		)
		button_box.accepted.connect(self.accept)
		button_box.rejected.connect(self.reject)
		layout.addWidget(button_box)

	#============================================
	def _pick_color(self) -> None:
		"""Open a color picker dialog and update the color button."""
		color = PySide6.QtWidgets.QColorDialog.getColor(
			PySide6.QtGui.QColor(self._color), self, "Arrow Color"
		)
		if color.isValid():
			self._color = color.name()
			self._update_color_button()

	#============================================
	def _update_color_button(self) -> None:
		"""Set the color button background to the currently selected color."""
		self._color_button.setText(self._color)
		foreground = (
			"#ffffff" if PySide6.QtGui.QColor(self._color).lightness() < 128
			else "#000000"
		)
		self._color_button.setStyleSheet(
			f"background-color: {self._color}; color: {foreground}; "
			"border: 1px solid #888;"
		)

	#============================================
	def get_values(self) -> dict[str, object]:
		"""Return dict of edited arrow property values.

		Returns:
			Dictionary with 'start_head', 'end_head', 'line_width',
			'spline', and 'color' keys.
		"""
		values = {
			"start_head": self._start_head_check.isChecked(),
			"end_head": self._end_head_check.isChecked(),
			"line_width": self._line_width_spin.value(),
			"spline": self._spline_check.isChecked(),
			"color": self._color,
		}
		return values

	#============================================
	def changes(self) -> tuple[tuple[str, object], ...]:
		"""Return only explicit values changed after widget initialization."""
		return tuple(
			(name, value) for name, value in self.get_values().items()
			if value != self._initial_values[name]
		)
