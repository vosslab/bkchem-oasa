"""Controlled CDML 26.07 rich-text editing dialog."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
def is_valid_color(value: object) -> bool:
	"""Return whether one legacy or current visible color value can be displayed."""
	return type(value) is str and PySide6.QtGui.QColor(value).isValid()


#============================================
class _PlainPasteTextEdit(PySide6.QtWidgets.QTextEdit):
	"""QTextEdit that accepts clipboard content only as literal plain text."""

	#============================================
	def insertFromMimeData(self, source: PySide6.QtCore.QMimeData) -> None:
		"""Insert clipboard text without importing HTML or document formatting."""
		self.textCursor().insertText(source.text())


#============================================
class RichTextDialog(PySide6.QtWidgets.QDialog):
	"""Edit compact CDML rich runs with only the authored formatting controls."""

	#============================================
	def __init__(
			self, runs: tuple[tuple[str, tuple[str, ...]], ...],
			font_family: str = "Arial", font_size: int = 12, font_color: str = "#000000",
			parent: PySide6.QtWidgets.QWidget | None = None,
			) -> None:
		"""Create one modal rich-text editor from immutable plain run values."""
		super().__init__(parent)
		self.setWindowTitle("Edit Rich Text")
		self.setMinimumSize(360, 260)
		self._build_ui()
		self._install_runs(runs)
		self._font_combo.setCurrentFont(PySide6.QtGui.QFont(font_family))
		self._font_spin.setValue(font_size)
		self._color = PySide6.QtGui.QColor(font_color).name()
		self._update_color_button()
		self._initial_font_values = self.font_values()
		self._update_controls()

	#============================================
	def _build_ui(self) -> None:
		"""Build the fixed formatting toolbar and plain-input editor."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)
		toolbar = PySide6.QtWidgets.QHBoxLayout()
		self._bold_button = self._format_button("B", "b")
		self._italic_button = self._format_button("I", "i")
		self._sub_button = self._format_button("Sub", "sub")
		self._sup_button = self._format_button("Sup", "sup")
		for button in (
				self._bold_button, self._italic_button,
				self._sub_button, self._sup_button,
			):
			toolbar.addWidget(button)
		toolbar.addStretch()
		layout.addLayout(toolbar)
		form = PySide6.QtWidgets.QFormLayout()
		self._font_combo = PySide6.QtWidgets.QFontComboBox(self)
		form.addRow("Font family:", self._font_combo)
		self._font_spin = PySide6.QtWidgets.QSpinBox(self)
		self._font_spin.setRange(4, 144)
		form.addRow("Font size:", self._font_spin)
		self._color = "#000000"
		self._color_button = PySide6.QtWidgets.QPushButton(self)
		self._color_button.clicked.connect(self._pick_color)
		form.addRow("Color:", self._color_button)
		layout.addLayout(form)
		self._text_edit = _PlainPasteTextEdit(self)
		self._text_edit.setAcceptRichText(False)
		self._text_edit.cursorPositionChanged.connect(self._update_controls)
		layout.addWidget(self._text_edit)
		self._message = PySide6.QtWidgets.QLabel(self)
		self._message.setStyleSheet("color: #a00000;")
		layout.addWidget(self._message)
		buttons = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Save
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel,
		)
		buttons.accepted.connect(self.accept)
		buttons.rejected.connect(self.reject)
		layout.addWidget(buttons)

	#============================================
	def _pick_color(self) -> None:
		"""Choose one root font color without changing persistent state."""
		color = PySide6.QtWidgets.QColorDialog.getColor(
			PySide6.QtGui.QColor(self._color), self, "Text Color",
		)
		if color.isValid():
			self._color = color.name()
			self._update_color_button()

	#============================================
	def _update_color_button(self) -> None:
		"""Show the current root font color on its bounded control."""
		self._color_button.setStyleSheet(
			f"background-color: {self._color}; border: 1px solid #888;",
		)

	#============================================
	def font_values(self) -> dict[str, object]:
		"""Return the dialog's canonical plain root-font values."""
		return {
			"font_family": self._font_combo.currentFont().family().strip(),
			"font_size": self._font_spin.value(),
			"font_color": self._color.lower(),
		}

	#============================================
	def changes(self) -> tuple[tuple[str, object], ...]:
		"""Return only root font fields changed from this dialog's displayed baseline."""
		values = self.font_values()
		return tuple(
			(name, value) for name, value in values.items()
			if value != self._initial_font_values[name]
		)

	#============================================
	def _format_button(self, label: str, style: str) -> PySide6.QtWidgets.QToolButton:
		"""Create one checkable authored-style control."""
		button = PySide6.QtWidgets.QToolButton(self)
		button.setText(label)
		button.setCheckable(True)
		button.clicked.connect(
			lambda checked, value=style: self._toggle_style(value, checked),
		)
		return button

	#============================================
	def _install_runs(self, runs: tuple[tuple[str, tuple[str, ...]], ...]) -> None:
		"""Build the dialog document with QTextCursor, never HTML source."""
		if type(runs) is not tuple:
			raise TypeError("Rich Text runs must be an immutable tuple")
		document = self._text_edit.document()
		document.clear()
		cursor = PySide6.QtGui.QTextCursor(document)
		for text, styles in runs:
			format = self._format_for_styles(text, styles)
			cursor.insertText(text, format)

	#============================================
	def _format_for_styles(
			self, text: str, styles: tuple[str, ...],
			) -> PySide6.QtGui.QTextCharFormat:
		"""Return one character format for an exact plain authored run."""
		if type(text) is not str or type(styles) is not tuple:
			raise TypeError("Rich Text runs must contain plain text/style tuples")
		if any(style not in ("b", "i", "sub", "sup") for style in styles):
			raise ValueError("Rich Text contains an unsupported style")
		if len(set(styles)) != len(styles) or ("sub" in styles and "sup" in styles):
			raise ValueError("Rich Text styles must have one baseline shift")
		format = PySide6.QtGui.QTextCharFormat()
		if "b" in styles:
			format.setFontWeight(PySide6.QtGui.QFont.Weight.Bold)
		if "i" in styles:
			format.setFontItalic(True)
		if "sub" in styles:
			format.setVerticalAlignment(
				PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSubScript,
			)
		if "sup" in styles:
			format.setVerticalAlignment(
				PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSuperScript,
			)
		return format

	#============================================
	def _toggle_style(self, style: str, enabled: bool) -> None:
		"""Apply one authored style while keeping subscript and superscript exclusive."""
		format = PySide6.QtGui.QTextCharFormat()
		if style == "b":
			weight = (
				PySide6.QtGui.QFont.Weight.Bold
				if enabled else PySide6.QtGui.QFont.Weight.Normal
			)
			format.setFontWeight(weight)
		elif style == "i":
			format.setFontItalic(enabled)
		else:
			alignment = PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignNormal
			if enabled:
				alignment = (
					PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSubScript
					if style == "sub" else
					PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSuperScript
				)
			format.setVerticalAlignment(alignment)
		cursor = self._text_edit.textCursor()
		cursor.mergeCharFormat(format)
		self._text_edit.mergeCurrentCharFormat(format)
		self._update_controls()

	#============================================
	def _update_controls(self) -> None:
		"""Reflect the active cursor format in the four independent controls."""
		format = self._text_edit.currentCharFormat()
		alignment = format.verticalAlignment()
		self._bold_button.setChecked(format.fontWeight() >= PySide6.QtGui.QFont.Weight.Bold)
		self._italic_button.setChecked(format.fontItalic())
		self._sub_button.setChecked(
			alignment == PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSubScript,
		)
		self._sup_button.setChecked(
			alignment == PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSuperScript,
		)

	#============================================
	def get_runs(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
		"""Return exact immutable plain runs from QTextDocument blocks and fragments."""
		runs: list[tuple[str, tuple[str, ...]]] = []
		block = self._text_edit.document().begin()
		while block.isValid():
			iterator = block.begin()
			while not iterator.atEnd():
				fragment = iterator.fragment()
				self._append_run(runs, fragment.text(), fragment.charFormat())
				iterator += 1
			block = block.next()
			if block.isValid():
				self._append_run(runs, "\n", PySide6.QtGui.QTextCharFormat())
		result = tuple(runs)
		return result

	#============================================
	def _append_run(
			self, runs: list[tuple[str, tuple[str, ...]]], text: str,
			format: PySide6.QtGui.QTextCharFormat,
			) -> None:
		"""Append one nonempty canonical run while coalescing adjacent equal styles."""
		if not text:
			return
		styles = []
		if format.fontWeight() >= PySide6.QtGui.QFont.Weight.Bold:
			styles.append("b")
		if format.fontItalic():
			styles.append("i")
		alignment = format.verticalAlignment()
		if alignment == PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSubScript:
			styles.append("sub")
		elif alignment == PySide6.QtGui.QTextCharFormat.VerticalAlignment.AlignSuperScript:
			styles.append("sup")
		style_tuple = tuple(styles)
		if runs and runs[-1][1] == style_tuple:
			previous_text, _previous_styles = runs[-1]
			runs[-1] = (previous_text + text, style_tuple)
		else:
			runs.append((text, style_tuple))

	#============================================
	def accept(self) -> None:
		"""Accept only nonblank rendered content with a plain immutable result."""
		if not any(text.strip() for text, _styles in self.get_runs()):
			self._message.setText("Rich text cannot be blank.")
			return
		self._message.clear()
		super().accept()
