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
		color: Color string (hex format).
	"""

	#============================================
	def __init__(self, parent=None, start_head=False, end_head=True,
			line_width=2.0, color="#000000"):
		"""Initialize the arrow properties dialog.

		Args:
			parent: Optional parent widget.
			start_head: Initial state for start arrowhead.
			end_head: Initial state for end arrowhead.
			line_width: Initial line width.
			color: Initial color in hex format.
		"""
		super().__init__(parent)
		self._color = color
		self.setWindowTitle("Arrow Properties")
		self.setMinimumWidth(280)
		self._build_ui()
		# populate initial values
		self._start_head_check.setChecked(start_head)
		self._end_head_check.setChecked(end_head)
		self._line_width_spin.setValue(line_width)
		self._update_color_button()

	#============================================
	def _build_ui(self) -> None:
		"""Build the form layout with all property fields."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		form = PySide6.QtWidgets.QFormLayout()

		# start head
		self._start_head_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Start arrowhead:", self._start_head_check)

		# end head
		self._end_head_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("End arrowhead:", self._end_head_check)

		# line width
		self._line_width_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._line_width_spin.setRange(0.5, 20.0)
		self._line_width_spin.setSingleStep(0.5)
		self._line_width_spin.setDecimals(1)
		self._line_width_spin.setValue(2.0)
		form.addRow("Line width:", self._line_width_spin)

		# spline curve
		self._spline_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Spline curve:", self._spline_check)

		# color button
		self._color_button = PySide6.QtWidgets.QPushButton()
		self._color_button.setFixedHeight(24)
		self._color_button.clicked.connect(self._pick_color)
		form.addRow("Color:", self._color_button)

		layout.addLayout(form)

		# ok / cancel buttons
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
		self._color_button.setStyleSheet(
			f"background-color: {self._color}; border: 1px solid #888;"
		)

	#============================================
	def get_values(self) -> dict:
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
