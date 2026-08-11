"""Intent-only editor for authoritative document drawing defaults."""

# Standard Library
import re

# PIP3 modules
import PySide6.QtWidgets


_COLOR = re.compile(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?")


#============================================
def _width_editor(value: float) -> PySide6.QtWidgets.QDoubleSpinBox:
	"""Build one bounded point-width editor."""
	editor = PySide6.QtWidgets.QDoubleSpinBox()
	editor.setRange(0.01, 1000.0)
	editor.setDecimals(2)
	editor.setSingleStep(0.25)
	editor.setSuffix(" pt")
	editor.setValue(value)
	return editor


#============================================
class DrawingStandardDialog(PySide6.QtWidgets.QDialog):
	"""Collect a plain patch for the current document's inherited styles."""

	#============================================
	def __init__(
			self, observation: object,
			parent: PySide6.QtWidgets.QWidget | None = None,
			selected_root_count: int = 0,
			personal_default_exists: bool = False,
			) -> None:
		"""Build a focused form from one immutable backend observation."""
		super().__init__(parent)
		self._selected_root_count = max(0, int(selected_root_count))
		self._personal_default_exists = bool(personal_default_exists)
		self._remove_personal_default = False
		self._initial = {
			"line_width": float(observation.line_width),
			"font_size": int(observation.font_size),
			"font_family": str(observation.font_family),
			"line_color": str(observation.line_color),
			"area_color": str(observation.area_color),
			"bond_width": float(observation.bond_width),
			"wedge_width": float(observation.wedge_width),
			"double_ratio": float(observation.double_ratio),
			"show_hydrogens": bool(observation.show_hydrogens),
		}
		self.setWindowTitle("Document Drawing Style")
		self.setMinimumWidth(500)
		self._build_ui(tuple(observation.issues))

	#============================================
	def _build_ui(self, issues: tuple[str, ...]) -> None:
		"""Build compact atom, color, and bond control groups."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		intro = PySide6.QtWidgets.QLabel(
			"Set this document's drawing defaults. You can also copy the values "
			"onto existing objects as explicit style overrides.",
		)
		intro.setWordWrap(True)
		layout.addWidget(intro)
		layout.addWidget(self._build_general_group())
		layout.addWidget(self._build_bond_group())
		layout.addWidget(self._build_application_group())
		layout.addWidget(self._build_personal_group())
		if issues:
			warning = PySide6.QtWidgets.QLabel(
				"Some malformed saved values are shown using safe defaults. "
				"Applying changes will leave unrelated saved content untouched.",
			)
			warning.setWordWrap(True)
			warning.setStyleSheet("color: #8a4b00;")
			layout.addWidget(warning)
		self._error_label = PySide6.QtWidgets.QLabel()
		self._error_label.setWordWrap(True)
		self._error_label.setStyleSheet("color: #b00020;")
		layout.addWidget(self._error_label)
		buttons = PySide6.QtWidgets.QDialogButtonBox()
		self._apply_button = buttons.addButton(
			"Apply to document", PySide6.QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole,
		)
		buttons.addButton(PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)
		self._sync_scope_controls()

	#============================================
	def _build_general_group(self) -> PySide6.QtWidgets.QGroupBox:
		"""Build atom-label, color, and general line controls."""
		group = PySide6.QtWidgets.QGroupBox("Lines and atom labels")
		form = PySide6.QtWidgets.QFormLayout(group)
		self._line_width_spin = _width_editor(self._initial["line_width"])
		form.addRow("Line width:", self._line_width_spin)
		self._line_color_edit = PySide6.QtWidgets.QLineEdit(self._initial["line_color"])
		self._line_color_edit.setPlaceholderText("#000000")
		form.addRow("Line and text color:", self._line_color_edit)
		self._area_color_edit = PySide6.QtWidgets.QLineEdit(self._initial["area_color"])
		self._area_color_edit.setPlaceholderText("Transparent when empty")
		form.addRow("Label background:", self._area_color_edit)
		self._font_family_edit = PySide6.QtWidgets.QLineEdit(self._initial["font_family"])
		form.addRow("Font family:", self._font_family_edit)
		self._font_size_spin = PySide6.QtWidgets.QSpinBox()
		self._font_size_spin.setRange(4, 144)
		self._font_size_spin.setSuffix(" pt")
		self._font_size_spin.setValue(self._initial["font_size"])
		form.addRow("Font size:", self._font_size_spin)
		self._hydrogens_check = PySide6.QtWidgets.QCheckBox(
			"Show hydrogens on heteroatoms by default",
		)
		self._hydrogens_check.setChecked(self._initial["show_hydrogens"])
		form.addRow("Hydrogens:", self._hydrogens_check)
		return group

	#============================================
	def _build_bond_group(self) -> PySide6.QtWidgets.QGroupBox:
		"""Build inherited bond geometry controls."""
		group = PySide6.QtWidgets.QGroupBox("Bonds")
		form = PySide6.QtWidgets.QFormLayout(group)
		self._bond_width_spin = _width_editor(self._initial["bond_width"])
		form.addRow("Multiple-bond spacing:", self._bond_width_spin)
		self._wedge_width_spin = _width_editor(self._initial["wedge_width"])
		form.addRow("Wedge width:", self._wedge_width_spin)
		self._double_ratio_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._double_ratio_spin.setRange(0.01, 1.0)
		self._double_ratio_spin.setDecimals(2)
		self._double_ratio_spin.setSingleStep(0.05)
		self._double_ratio_spin.setValue(self._initial["double_ratio"])
		self._double_ratio_spin.setToolTip(
			"Length of the shorter double-bond line relative to the full bond.",
		)
		form.addRow("Double-line length ratio:", self._double_ratio_spin)
		return group

	#============================================
	def _build_application_group(self) -> PySide6.QtWidgets.QGroupBox:
		"""Build explicit scope and changed/all-value choices."""
		group = PySide6.QtWidgets.QGroupBox("Apply to")
		layout = PySide6.QtWidgets.QVBoxLayout(group)
		self._defaults_scope = PySide6.QtWidgets.QRadioButton(
			"Document defaults and future objects",
		)
		self._selected_scope = PySide6.QtWidgets.QRadioButton(
			"Selected objects and document defaults",
		)
		self._all_scope = PySide6.QtWidgets.QRadioButton(
			"All objects and document defaults",
		)
		self._defaults_scope.setChecked(True)
		self._selected_scope.setEnabled(self._selected_root_count > 0)
		if self._selected_root_count == 0:
			self._selected_scope.setText(
				"Selected objects and document defaults (no eligible selection)",
			)
		for button in (self._defaults_scope, self._selected_scope, self._all_scope):
			button.toggled.connect(lambda _checked: self._sync_scope_controls())
			layout.addWidget(button)
		values = PySide6.QtWidgets.QWidget()
		values_layout = PySide6.QtWidgets.QHBoxLayout(values)
		values_layout.setContentsMargins(22, 0, 0, 0)
		self._changed_values = PySide6.QtWidgets.QRadioButton("Changed values only")
		self._all_values = PySide6.QtWidgets.QRadioButton("All style values")
		self._changed_values.setChecked(True)
		values_layout.addWidget(self._changed_values)
		values_layout.addWidget(self._all_values)
		values_layout.addStretch(1)
		self._override_value_choices = values
		layout.addWidget(values)
		return group

	#============================================
	def _build_personal_group(self) -> PySide6.QtWidgets.QGroupBox:
		"""Build optional frontend preference storage without touching CDML."""
		group = PySide6.QtWidgets.QGroupBox("New documents")
		layout = PySide6.QtWidgets.QVBoxLayout(group)
		self._save_personal_check = PySide6.QtWidgets.QCheckBox(
			"Also use these values as my default for new documents",
		)
		self._save_personal_check.toggled.connect(self._personal_save_toggled)
		layout.addWidget(self._save_personal_check)
		self._personal_status = PySide6.QtWidgets.QLabel()
		self._personal_status.setWordWrap(True)
		if self._personal_default_exists:
			self._personal_status.setText(
				"A personal default is already saved. Selecting the option above replaces it.",
			)
			self._remove_personal_button = PySide6.QtWidgets.QPushButton(
				"Remove saved personal default",
			)
			self._remove_personal_button.clicked.connect(self._request_personal_removal)
			layout.addWidget(self._remove_personal_button)
		else:
			self._remove_personal_button = None
		layout.addWidget(self._personal_status)
		return group

	#============================================
	def _sync_scope_controls(self) -> None:
		"""Keep override choices and the primary action label context-sensitive."""
		scope = self.application_scope()
		self._override_value_choices.setEnabled(scope != "defaults")
		labels = {
			"defaults": "Apply document defaults",
			"selected": "Apply to %d selected object%s" % (
				self._selected_root_count,
				"" if self._selected_root_count == 1 else "s",
			),
			"all": "Apply to all objects",
		}
		self._apply_button.setText(labels[scope])

	#============================================
	def _personal_save_toggled(self, checked: bool) -> None:
		"""Let an explicit save choice supersede pending removal intent."""
		if checked:
			self._remove_personal_default = False
			if self._remove_personal_button is not None:
				self._remove_personal_button.setEnabled(True)

	#============================================
	def _request_personal_removal(self) -> None:
		"""Record reversible removal intent; Cancel still has no side effects."""
		self._save_personal_check.setChecked(False)
		self._remove_personal_default = True
		self._remove_personal_button.setEnabled(False)
		self._personal_status.setText(
			"The saved personal default will be removed when you apply.",
		)

	#============================================
	def accept(self) -> None:
		"""Keep invalid text visible and explain how the user can recover."""
		line_color = self._line_color_edit.text().strip()
		area_color = self._area_color_edit.text().strip()
		if _COLOR.fullmatch(line_color) is None:
			self._error_label.setText(
				"Line and text color must be a hexadecimal color such as #224466.",
			)
			self._line_color_edit.setFocus()
			return
		if area_color and _COLOR.fullmatch(area_color) is None:
			self._error_label.setText(
				"Label background must be a hexadecimal color, or empty for transparent.",
			)
			self._area_color_edit.setFocus()
			return
		if not self._font_family_edit.text().strip():
			self._error_label.setText("Font family cannot be empty.")
			self._font_family_edit.setFocus()
			return
		self._error_label.clear()
		super().accept()

	#============================================
	def changes(self) -> tuple[tuple[str, object], ...]:
		"""Return only values intentionally changed from the shown observation."""
		return tuple(
			(name, value) for name, value in self.values()
			if value != self._initial[name]
		)

	#============================================
	def values(self) -> tuple[tuple[str, object], ...]:
		"""Return every displayed style value as immutable plain data."""
		return (
			("line_width", self._line_width_spin.value()),
			("line_color", self._line_color_edit.text().strip()),
			("area_color", self._area_color_edit.text().strip()),
			("font_family", self._font_family_edit.text().strip()),
			("font_size", self._font_size_spin.value()),
			("show_hydrogens", self._hydrogens_check.isChecked()),
			("bond_width", self._bond_width_spin.value()),
			("wedge_width", self._wedge_width_spin.value()),
			("double_ratio", self._double_ratio_spin.value()),
		)

	#============================================
	def application_scope(self) -> str:
		"""Return the exact backend application scope selected by the user."""
		if self._selected_scope.isChecked():
			return "selected"
		if self._all_scope.isChecked():
			return "all"
		return "defaults"

	#============================================
	def override_fields(self) -> tuple[str, ...]:
		"""Return fields to materialize on existing target objects."""
		if self.application_scope() == "defaults":
			return ()
		if self._all_values.isChecked():
			return tuple(name for name, _value in self.values())
		return tuple(name for name, _value in self.changes())

	#============================================
	def personal_action(self) -> str:
		"""Return accepted preference intent independently from document scope."""
		if self._save_personal_check.isChecked():
			return "save"
		if self._remove_personal_default:
			return "remove"
		return "none"
