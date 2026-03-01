"""Atom properties dialog."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets


# -- multiplicity labels indexed by value --
_MULTIPLICITY_LABELS = {
	1: "Singlet",
	2: "Doublet",
	3: "Triplet",
}
_MULTIPLICITY_VALUES = {v: k for k, v in _MULTIPLICITY_LABELS.items()}


#============================================
class AtomDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for editing atom properties.

	Presents a form with fields for element symbol, charge, valency,
	isotope, multiplicity, visibility, hydrogens, font size, and color.

	Args:
		atom_model: The AtomModel whose properties to edit.
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(self, atom_model, parent=None):
		"""Initialize the atom properties dialog.

		Args:
			atom_model: The AtomModel whose properties to edit.
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self._atom_model = atom_model
		self._color = atom_model.line_color
		self.setWindowTitle("Atom Properties")
		self.setMinimumWidth(300)
		self._build_ui()
		self._populate_from_model()

	#============================================
	def _build_ui(self) -> None:
		"""Build the form layout with all property fields."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		form = PySide6.QtWidgets.QFormLayout()

		# symbol
		self._symbol_edit = PySide6.QtWidgets.QLineEdit()
		self._symbol_edit.setMaxLength(3)
		form.addRow("Symbol:", self._symbol_edit)

		# charge
		self._charge_spin = PySide6.QtWidgets.QSpinBox()
		self._charge_spin.setRange(-9, 9)
		form.addRow("Charge:", self._charge_spin)

		# valency
		self._valency_spin = PySide6.QtWidgets.QSpinBox()
		self._valency_spin.setRange(0, 10)
		form.addRow("Valency:", self._valency_spin)

		# isotope (0 means none)
		self._isotope_spin = PySide6.QtWidgets.QSpinBox()
		self._isotope_spin.setRange(0, 300)
		self._isotope_spin.setSpecialValueText("None")
		form.addRow("Isotope:", self._isotope_spin)

		# multiplicity
		self._multiplicity_combo = PySide6.QtWidgets.QComboBox()
		for label in _MULTIPLICITY_LABELS.values():
			self._multiplicity_combo.addItem(label)
		form.addRow("Multiplicity:", self._multiplicity_combo)

		# show atom
		self._show_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Show atom:", self._show_check)

		# show hydrogens
		self._hydrogens_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Show hydrogens:", self._hydrogens_check)

		# font size
		self._font_spin = PySide6.QtWidgets.QSpinBox()
		self._font_spin.setRange(4, 72)
		form.addRow("Font size:", self._font_spin)

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
		"""Fill dialog fields from the current atom model values."""
		self._symbol_edit.setText(self._atom_model.symbol)
		self._charge_spin.setValue(self._atom_model.charge)
		self._valency_spin.setValue(self._atom_model.valency)
		# isotope: None maps to 0 in the spin box
		isotope_val = self._atom_model.isotope
		if isotope_val is None:
			isotope_val = 0
		self._isotope_spin.setValue(isotope_val)
		# multiplicity
		mult_label = _MULTIPLICITY_LABELS.get(self._atom_model.multiplicity, "Singlet")
		idx = self._multiplicity_combo.findText(mult_label)
		if idx >= 0:
			self._multiplicity_combo.setCurrentIndex(idx)
		self._show_check.setChecked(self._atom_model.show)
		self._hydrogens_check.setChecked(self._atom_model.show_hydrogens)
		self._font_spin.setValue(self._atom_model.font_size)
		self._color = self._atom_model.line_color
		self._update_color_button()

	#============================================
	def _pick_color(self) -> None:
		"""Open a color picker dialog and update the color button."""
		color = PySide6.QtWidgets.QColorDialog.getColor(
			PySide6.QtGui.QColor(self._color), self, "Atom Color"
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
		# isotope: 0 maps back to None
		isotope_val = self._isotope_spin.value()
		if isotope_val == 0:
			isotope_val = None
		# multiplicity label to int
		mult_label = self._multiplicity_combo.currentText()
		mult_value = _MULTIPLICITY_VALUES.get(mult_label, 1)
		values = {
			"symbol": self._symbol_edit.text().strip(),
			"charge": self._charge_spin.value(),
			"valency": self._valency_spin.value(),
			"isotope": isotope_val,
			"multiplicity": mult_value,
			"show": self._show_check.isChecked(),
			"show_hydrogens": self._hydrogens_check.isChecked(),
			"font_size": self._font_spin.value(),
			"line_color": self._color,
		}
		return values

	#============================================
	@staticmethod
	def edit_atom(atom_model, parent=None) -> bool:
		"""Convenience: show dialog, apply changes if accepted.

		Args:
			atom_model: The AtomModel to edit.
			parent: Optional parent widget.

		Returns:
			True if changes were accepted and applied, False otherwise.
		"""
		dialog = AtomDialog(atom_model, parent)
		result = dialog.exec()
		if result != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			return False
		values = dialog.get_values()
		# apply each value to the model
		for key, value in values.items():
			setattr(atom_model, key, value)
		return True
