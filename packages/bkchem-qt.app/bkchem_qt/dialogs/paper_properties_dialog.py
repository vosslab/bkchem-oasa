"""Intent-only document paper-properties dialog."""

# PIP3 modules
import collections.abc
import math
import re
import PySide6.QtWidgets

_DECIMAL_RE = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
_INTEGER_RE = re.compile(r"[0-9]+")
_EDITOR_MAXIMUM = 1000000000000.0


#============================================
def _attribute_is_true(attributes: dict[str, str], name: str) -> bool:
	"""Return whether an optional legacy CDML boolean is enabled."""
	value = attributes.get(name, "0").strip().lower()
	return value in ("1", "true", "yes", "on")


#============================================
class PaperPropertiesDialog(PySide6.QtWidgets.QDialog):
	"""Edit the paper fields that the document model persists in CDML."""

	#============================================
	def __init__(
			self, paper_attributes: collections.abc.Mapping[str, str],
			paper_catalog: collections.abc.Mapping[str, list[float] | None],
			default_type: str = "A4", default_orientation: str = "portrait",
			parent: PySide6.QtWidgets.QWidget | None = None,
			) -> None:
		"""Build a form that returns only explicit, plain paper-field intent."""
		super().__init__(parent)
		self._attributes = dict(paper_attributes)
		self._catalog = dict(paper_catalog)
		if not self._catalog or "custom" not in self._catalog:
			raise ValueError("Paper catalog must include authored custom paper")
		if default_type not in self._catalog or default_type == "custom":
			raise ValueError("Paper default type must be one named catalog paper")
		if default_orientation not in ("portrait", "landscape"):
			raise ValueError("Paper default orientation is unsupported")
		self._default_type = default_type
		self._default_orientation = default_orientation
		self._width_lexical = "215.9"
		self._height_lexical = "279.4"
		self._crop_margin_lexical = "10"
		self._initial_type = ""
		self._initial_orientation = ""
		self._initial_display_type = default_type
		self._initial_display_orientation = default_orientation
		self._initial_crop_svg = False
		self._initial_use_real_minus = False
		self._initial_replace_minus = False
		self._initial_width = None
		self._initial_height = None
		self._initial_crop_margin = None
		self._width_changed = False
		self._height_changed = False
		self._crop_margin_changed = False
		self.setWindowTitle("Document Properties")
		self.setMinimumWidth(340)
		self._build_ui()
		self._populate()

	#============================================
	def _build_ui(self) -> None:
		"""Build the fixed-size paper and export property form."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		form = PySide6.QtWidgets.QFormLayout()
		self._type_combo = PySide6.QtWidgets.QComboBox()
		for paper_type in self._catalog:
			self._type_combo.addItem(paper_type)
		self._type_combo.currentTextChanged.connect(self._update_custom_enabled)
		form.addRow("Paper type:", self._type_combo)
		self._orientation_combo = PySide6.QtWidgets.QComboBox()
		self._orientation_combo.addItem("portrait")
		self._orientation_combo.addItem("landscape")
		form.addRow("Orientation:", self._orientation_combo)
		self._width_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._width_spin.setRange(0.0, _EDITOR_MAXIMUM)
		self._width_spin.setDecimals(1)
		self._width_spin.setSuffix(" mm")
		form.addRow("Custom width:", self._width_spin)
		self._height_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._height_spin.setRange(0.0, _EDITOR_MAXIMUM)
		self._height_spin.setDecimals(1)
		self._height_spin.setSuffix(" mm")
		form.addRow("Custom height:", self._height_spin)
		self._crop_svg_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Crop SVG:", self._crop_svg_check)
		self._crop_margin_spin = PySide6.QtWidgets.QSpinBox()
		self._crop_margin_spin.setRange(0, 2147483647)
		self._crop_margin_spin.setSuffix(" px")
		form.addRow("Crop margin:", self._crop_margin_spin)
		self._use_real_minus_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Use real minus character:", self._use_real_minus_check)
		self._replace_minus_check = PySide6.QtWidgets.QCheckBox()
		form.addRow("Replace hyphens in SVG:", self._replace_minus_check)
		layout.addLayout(form)
		self._error_label = PySide6.QtWidgets.QLabel()
		self._error_label.setStyleSheet("color: #b00020;")
		layout.addWidget(self._error_label)
		buttons = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel,
		)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)

	#============================================
	def _populate(self) -> None:
		"""Fill controls while retaining unsupported raw values until changed."""
		attributes = self._attributes
		self._initial_type = attributes.get("type", "")
		paper_type = self._initial_type or self._default_type
		self._initial_display_type = paper_type
		if paper_type not in self._catalog:
			self._type_combo.insertItem(0, paper_type)
		self._type_combo.setCurrentText(paper_type)
		self._initial_orientation = attributes.get("orientation", "")
		orientation = self._initial_orientation or self._default_orientation
		self._initial_display_orientation = orientation
		if orientation not in ("portrait", "landscape"):
			self._orientation_combo.insertItem(0, orientation)
		self._orientation_combo.setCurrentText(orientation)
		self._width_lexical = attributes.get("size_x", "215.9")
		self._height_lexical = attributes.get("size_y", "279.4")
		self._crop_margin_lexical = attributes.get("crop_margin", "10")
		self._initial_width = _valid_decimal(self._width_lexical)
		self._initial_height = _valid_decimal(self._height_lexical)
		self._initial_crop_margin = _valid_integer(self._crop_margin_lexical)
		self._width_spin.setValue(self._initial_width or 215.9)
		self._height_spin.setValue(self._initial_height or 279.4)
		self._initial_crop_svg = _attribute_is_true(attributes, "crop_svg")
		self._crop_svg_check.setChecked(self._initial_crop_svg)
		self._crop_margin_spin.setValue(self._initial_crop_margin or 10)
		self._initial_use_real_minus = _attribute_is_true(attributes, "use_real_minus")
		self._use_real_minus_check.setChecked(self._initial_use_real_minus)
		self._initial_replace_minus = _attribute_is_true(attributes, "replace_minus")
		self._replace_minus_check.setChecked(self._initial_replace_minus)
		self._update_custom_enabled(paper_type)
		self._width_spin.valueChanged.connect(self._mark_width_changed)
		self._height_spin.valueChanged.connect(self._mark_height_changed)
		self._crop_margin_spin.valueChanged.connect(self._mark_crop_margin_changed)

	#============================================
	def _mark_width_changed(self, _value: float) -> None:
		"""Record an intentional custom-width edit after initial raw loading."""
		self._width_changed = True

	#============================================
	def _mark_height_changed(self, _value: float) -> None:
		"""Record an intentional custom-height edit after initial raw loading."""
		self._height_changed = True

	#============================================
	def _mark_crop_margin_changed(self, _value: int) -> None:
		"""Record an intentional crop-margin edit after initial raw loading."""
		self._crop_margin_changed = True

	#============================================
	def _update_custom_enabled(self, paper_type: str) -> None:
		"""Enable dimensions only when the document uses a custom paper size."""
		custom = paper_type == "custom"
		self._width_spin.setEnabled(custom)
		self._height_spin.setEnabled(custom)

	#============================================
	def accept(self) -> None:
		"""Validate a custom transition before accepting its plain change-set."""
		if self._type_combo.currentText() == "custom":
			if self._width_spin.value() <= 0 or self._height_spin.value() <= 0:
				self._error_label.setText("Custom paper dimensions must be positive.")
				return
		super().accept()

	#============================================
	def changes(self) -> tuple[tuple[str, object], ...]:
		"""Return the exact explicit field intent for one accepted dialog."""
		changes = []
		paper_type = self._type_combo.currentText()
		orientation = self._orientation_combo.currentText()
		if paper_type != self._initial_display_type:
			changes.append(("type", paper_type))
		if orientation != self._initial_display_orientation:
			changes.append(("orientation", orientation))
		for name, control, original in (
				("crop_svg", self._crop_svg_check, self._initial_crop_svg),
				("use_real_minus", self._use_real_minus_check, self._initial_use_real_minus),
				("replace_minus", self._replace_minus_check, self._initial_replace_minus),
			):
			if control.isChecked() != original:
				changes.append((name, control.isChecked()))
		margin = self._crop_margin_spin.value()
		if self._crop_margin_changed and margin != self._initial_crop_margin:
			changes.append(("crop_margin", margin))
		if paper_type == "custom":
			dimensions = (self._width_spin.value(), self._height_spin.value())
			if (
				paper_type != self._initial_display_type
				or self._width_changed or self._height_changed
			) and dimensions != (self._initial_width, self._initial_height):
				changes.append(("dimensions", dimensions))
			elif paper_type != self._initial_display_type:
				changes.append(("dimensions", dimensions))
		return tuple(changes)


#============================================
def _valid_decimal(text: str) -> float | None:
	"""Return one safe raw decimal, or ``None`` without normalizing it."""
	if len(text) > 50 or _DECIMAL_RE.fullmatch(text.strip()) is None:
		return None
	value = float(text)
	if not math.isfinite(value) or value > _EDITOR_MAXIMUM or value <= 0:
		return None
	return value


#============================================
def _valid_integer(text: str) -> int | None:
	"""Return one safe raw integer, or ``None`` without normalizing it."""
	if len(text) > 9 or _INTEGER_RE.fullmatch(text.strip()) is None:
		return None
	value = int(text)
	if value > 2147483647:
		return None
	return value
