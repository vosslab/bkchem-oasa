"""Scale dialog for resizing molecules."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets


#============================================
class ScaleDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for scaling X/Y with optional aspect ratio lock.

	Presents two spinners for X and Y scale factors and a checkbox
	to lock the aspect ratio so that changing one updates the other.

	Args:
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(self, parent=None):
		"""Initialize the scale dialog.

		Args:
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self.setWindowTitle("Scale")
		self.setMinimumWidth(250)
		self._updating = False
		self._build_ui()

	#============================================
	def _build_ui(self) -> None:
		"""Build the form layout with scale fields and lock checkbox."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		form = PySide6.QtWidgets.QFormLayout()

		# scale x
		self._scale_x_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._scale_x_spin.setRange(0.01, 100.0)
		self._scale_x_spin.setSingleStep(0.1)
		self._scale_x_spin.setDecimals(2)
		self._scale_x_spin.setValue(1.0)
		form.addRow("Scale X:", self._scale_x_spin)

		# scale y
		self._scale_y_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._scale_y_spin.setRange(0.01, 100.0)
		self._scale_y_spin.setSingleStep(0.1)
		self._scale_y_spin.setDecimals(2)
		self._scale_y_spin.setValue(1.0)
		form.addRow("Scale Y:", self._scale_y_spin)

		# lock aspect ratio
		self._lock_check = PySide6.QtWidgets.QCheckBox("Lock aspect ratio")
		self._lock_check.setChecked(True)
		form.addRow("", self._lock_check)

		layout.addLayout(form)

		# connect value changes for aspect ratio lock
		self._scale_x_spin.valueChanged.connect(self._on_x_changed)
		self._scale_y_spin.valueChanged.connect(self._on_y_changed)

		# ok / cancel buttons
		button_box = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel
		)
		button_box.accepted.connect(self.accept)
		button_box.rejected.connect(self.reject)
		layout.addWidget(button_box)

	#============================================
	def _on_x_changed(self, value: float) -> None:
		"""Sync Y to X when aspect ratio is locked.

		Args:
			value: New X scale value.
		"""
		if self._updating:
			return
		if self._lock_check.isChecked():
			self._updating = True
			self._scale_y_spin.setValue(value)
			self._updating = False

	#============================================
	def _on_y_changed(self, value: float) -> None:
		"""Sync X to Y when aspect ratio is locked.

		Args:
			value: New Y scale value.
		"""
		if self._updating:
			return
		if self._lock_check.isChecked():
			self._updating = True
			self._scale_x_spin.setValue(value)
			self._updating = False

	#============================================
	def get_scale(self) -> tuple:
		"""Return (scale_x, scale_y).

		Returns:
			Tuple of (scale_x, scale_y) float values.
		"""
		scale_x = self._scale_x_spin.value()
		scale_y = self._scale_y_spin.value()
		return (scale_x, scale_y)

	#============================================
	@staticmethod
	def get_scale_factors(parent=None) -> tuple:
		"""Convenience method to show the dialog and return scale factors.

		Args:
			parent: Optional parent widget.

		Returns:
			Tuple of (scale_x, scale_y) if accepted, or None if cancelled.
		"""
		dialog = ScaleDialog(parent)
		result = dialog.exec()
		if result != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			return None
		return dialog.get_scale()
