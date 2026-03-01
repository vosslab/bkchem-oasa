"""Bond properties dialog."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets


# -- bond order labels indexed by value --
_ORDER_LABELS = {
	1: "Single",
	2: "Double",
	3: "Triple",
}
_ORDER_VALUES = {v: k for k, v in _ORDER_LABELS.items()}

# -- bond type labels indexed by type character --
_TYPE_LABELS = {
	"n": "Normal",
	"w": "Wedge",
	"h": "Hashed",
	"b": "Bold",
	"a": "Aromatic",
	"d": "Dotted",
	"o": "Dashed",
	"s": "Stereo",
	"q": "Wavy",
}
_TYPE_VALUES = {v: k for k, v in _TYPE_LABELS.items()}


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
	def __init__(self, bond_model, parent=None):
		"""Initialize the bond properties dialog.

		Args:
			bond_model: The BondModel whose properties to edit.
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self._bond_model = bond_model
		self._color = bond_model.line_color
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
		for label in _TYPE_LABELS.values():
			self._type_combo.addItem(label)
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
		order_label = _ORDER_LABELS.get(self._bond_model.order, "Single")
		idx = self._order_combo.findText(order_label)
		if idx >= 0:
			self._order_combo.setCurrentIndex(idx)
		# type
		type_label = _TYPE_LABELS.get(self._bond_model.type, "Normal")
		idx = self._type_combo.findText(type_label)
		if idx >= 0:
			self._type_combo.setCurrentIndex(idx)
		# center
		center_val = self._bond_model.center
		self._center_check.setChecked(bool(center_val))
		# widths
		self._line_width_spin.setValue(self._bond_model.line_width)
		self._bond_width_spin.setValue(self._bond_model.bond_width)
		self._wedge_width_spin.setValue(self._bond_model.wedge_width)
		# color
		self._color = self._bond_model.line_color
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
		type_label = self._type_combo.currentText()
		type_val = _TYPE_VALUES.get(type_label, "n")
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
	@staticmethod
	def edit_bond(bond_model, parent=None) -> bool:
		"""Convenience: show dialog, apply changes if accepted.

		Args:
			bond_model: The BondModel to edit.
			parent: Optional parent widget.

		Returns:
			True if changes were accepted and applied, False otherwise.
		"""
		dialog = BondDialog(bond_model, parent)
		result = dialog.exec()
		if result != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			return False
		values = dialog.get_values()
		for key, value in values.items():
			setattr(bond_model, key, value)
		return True
