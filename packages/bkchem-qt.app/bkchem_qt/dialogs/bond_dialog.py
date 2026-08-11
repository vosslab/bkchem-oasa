"""Bond properties dialog."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.bond_presentation


# -- bond order labels indexed by value --
_ORDER_LABELS = {
	1: "Single",
	2: "Double",
	3: "Triple",
}
_ORDER_VALUES = {v: k for k, v in _ORDER_LABELS.items()}

#============================================
class BondDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for editing bond properties.

	Presents a form with fields for bond order, type, centering,
	line width, bond width, wedge width, and color.

	Args:
		bond_model: The BondModel whose properties to edit.
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(self, bond_model: object, parent: object | None = None) -> None:
		"""Initialize a detached bond-properties value editor.

		Args:
			bond_model: The BondModel whose properties to edit.
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		# Copy every display scalar before constructing Qt controls.  The accepted
		# backend patch can replace the projected BondModel while this dialog still
		# exists, so it must never retain or later inspect that transient wrapper.
		self._initial_values = {
			"order": bond_model.order,
			"type": bond_model.type,
			"center": bool(bond_model.center),
			"line_width": bond_model.line_width,
			"bond_width": bond_model.bond_width,
			"wedge_width": bond_model.wedge_width,
			"color": bond_model.line_color,
		}
		self._color = self._initial_values["color"]
		self.setWindowTitle("Bond Properties")
		self.setMinimumWidth(300)
		self._build_ui()
		self._populate_from_model()

	#============================================
	def _build_ui(self) -> None:
		"""Build the form layout with all property fields."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		form = PySide6.QtWidgets.QFormLayout()

		# order
		self._order_combo = PySide6.QtWidgets.QComboBox()
		for label in _ORDER_LABELS.values():
			self._order_combo.addItem(label)
		form.addRow("Order:", self._order_combo)

		# type
		self._type_combo = PySide6.QtWidgets.QComboBox()
		for type_char, label in bkchem_qt.bond_presentation.choices_for_display(
				self._initial_values["type"],
			):
			self._type_combo.addItem(label, type_char)
		form.addRow("Type:", self._type_combo)

		# center double bond
		self._center_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Center double bond:", self._center_check)

		# line width
		self._line_width_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._line_width_spin.setRange(0.1, 20.0)
		self._line_width_spin.setSingleStep(0.5)
		self._line_width_spin.setDecimals(1)
		form.addRow("Line width:", self._line_width_spin)

		# bond width
		self._bond_width_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._bond_width_spin.setRange(0.1, 40.0)
		self._bond_width_spin.setSingleStep(0.5)
		self._bond_width_spin.setDecimals(1)
		form.addRow("Bond width:", self._bond_width_spin)

		# wedge width
		self._wedge_width_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._wedge_width_spin.setRange(0.1, 40.0)
		self._wedge_width_spin.setSingleStep(0.5)
		self._wedge_width_spin.setDecimals(1)
		form.addRow("Wedge width:", self._wedge_width_spin)

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
	def _populate_from_model(self) -> None:
		"""Fill dialog fields from the current bond model values."""
		# order
		order_label = _ORDER_LABELS.get(self._initial_values["order"], "Single")
		idx = self._order_combo.findText(order_label)
		if idx >= 0:
			self._order_combo.setCurrentIndex(idx)
		# type
		idx = self._type_combo.findData(self._initial_values["type"])
		if idx >= 0:
			self._type_combo.setCurrentIndex(idx)
		# center
		center_val = self._initial_values["center"]
		self._center_check.setChecked(bool(center_val))
		# widths
		self._line_width_spin.setValue(self._initial_values["line_width"])
		self._bond_width_spin.setValue(self._initial_values["bond_width"])
		self._wedge_width_spin.setValue(self._initial_values["wedge_width"])
		# color
		self._color = self._initial_values["color"]
		self._update_color_button()

	#============================================
	def _pick_color(self) -> None:
		"""Open a color picker dialog and update the color button."""
		color = PySide6.QtWidgets.QColorDialog.getColor(
			PySide6.QtGui.QColor(self._color), self, "Bond Color"
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
		"""Return dict of edited values.

		Returns:
			Dictionary mapping property names to their new values.
		"""
		order_label = self._order_combo.currentText()
		order_val = _ORDER_VALUES.get(order_label, 1)
		type_val = self._type_combo.currentData()
		values = {
			"order": order_val,
			"type": type_val,
			"center": self._center_check.isChecked(),
			"line_width": self._line_width_spin.value(),
			"bond_width": self._bond_width_spin.value(),
			"wedge_width": self._wedge_width_spin.value(),
			"line_color": self._color,
		}
		return values

	#============================================
	def changes(self) -> tuple[tuple[str, object], ...]:
		"""Return only deliberate value changes using backend CDML field names."""
		values = self.get_values()
		current = {
			"order": values["order"], "type": values["type"],
			"center": values["center"], "line_width": values["line_width"],
			"bond_width": values["bond_width"], "wedge_width": values["wedge_width"],
			"color": values["line_color"],
		}
		return tuple(
			(name, value) for name, value in current.items()
			if value != self._initial_values[name]
		)
