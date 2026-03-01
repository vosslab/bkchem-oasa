"""Text input and properties dialog."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
class TextDialog(PySide6.QtWidgets.QDialog):
	"""Dialog for entering/editing text annotations.

	Provides a text editor, font size spinner, font family selector,
	and a color picker button.

	Args:
		text: Initial text content.
		font_size: Initial font size in points.
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(self, text="", font_size=12, parent=None):
		"""Initialize the text dialog.

		Args:
			text: Initial text content.
			font_size: Initial font size in points.
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self._color = "#000000"
		self.setWindowTitle("Text Annotation")
		self.setMinimumWidth(350)
		self.setMinimumHeight(250)
		self._build_ui()
		# populate initial values
		self._text_edit.setPlainText(text)
		self._font_spin.setValue(font_size)

	#============================================
	def _build_ui(self) -> None:
		"""Build the layout with text editor and property controls."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)

		# text editor
		self._text_edit = PySide6.QtWidgets.QTextEdit()
		layout.addWidget(self._text_edit)

		# properties form below the editor
		form = PySide6.QtWidgets.QFormLayout()

		# font size
		self._font_spin = PySide6.QtWidgets.QSpinBox()
		self._font_spin.setRange(4, 144)
		self._font_spin.setValue(12)
		form.addRow("Font size:", self._font_spin)

		# font family
		self._font_combo = PySide6.QtWidgets.QFontComboBox()
		self._font_combo.setCurrentFont(PySide6.QtGui.QFont("Arial"))
		form.addRow("Font family:", self._font_combo)

		# color button
		self._color_button = PySide6.QtWidgets.QPushButton()
		self._color_button.setFixedHeight(24)
		self._color_button.clicked.connect(self._pick_color)
		self._update_color_button()
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
			PySide6.QtGui.QColor(self._color), self, "Text Color"
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
	def get_text(self) -> str:
		"""Return the entered text content.

		Returns:
			Plain text string from the editor.
		"""
		return self._text_edit.toPlainText()

	#============================================
	def get_font_size(self) -> int:
		"""Return the selected font size.

		Returns:
			Font size in points.
		"""
		return self._font_spin.value()

	#============================================
	@staticmethod
	def get_text_input(text="", font_size=12, parent=None) -> dict:
		"""Convenience method to show the dialog and return results.

		Args:
			text: Initial text content.
			font_size: Initial font size.
			parent: Optional parent widget.

		Returns:
			Dict with 'text', 'font_size', 'font_family', and 'color'
			keys if accepted, or None if cancelled.
		"""
		dialog = TextDialog(text, font_size, parent)
		result = dialog.exec()
		if result != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
			return None
		values = {
			"text": dialog.get_text(),
			"font_size": dialog.get_font_size(),
			"font_family": dialog._font_combo.currentFont().family(),
			"color": dialog._color,
		}
		return values
