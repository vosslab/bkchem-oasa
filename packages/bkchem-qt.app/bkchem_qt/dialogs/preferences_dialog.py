"""Preferences dialog for application settings."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.config.preferences


#============================================
class PreferencesDialog(PySide6.QtWidgets.QDialog):
	"""Multi-tab preferences dialog.

	Provides tabs for appearance, drawing defaults, file handling,
	and keyboard shortcuts. Changes are applied when the user clicks
	OK or Apply.

	Args:
		parent: Optional parent widget.
	"""

	#============================================
	def __init__(self, parent=None):
		"""Initialize the preferences dialog with all tabs.

		Args:
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self.setWindowTitle(self.tr("Preferences"))
		self.resize(500, 400)
		self._prefs = bkchem_qt.config.preferences.Preferences.instance()
		self._build_ui()
		self._populate_from_prefs()

	#============================================
	def _build_ui(self) -> None:
		"""Build the tab widget, all tabs, and the button box."""
		layout = PySide6.QtWidgets.QVBoxLayout(self)

		# tab widget
		self._tabs = PySide6.QtWidgets.QTabWidget()
		self._tabs.addTab(self._create_appearance_tab(), self.tr("Appearance"))
		self._tabs.addTab(self._create_drawing_tab(), self.tr("Drawing"))
		self._tabs.addTab(self._create_file_tab(), self.tr("Files"))
		self._tabs.addTab(self._create_shortcuts_tab(), self.tr("Shortcuts"))
		layout.addWidget(self._tabs)

		# OK / Cancel / Apply buttons
		button_box = PySide6.QtWidgets.QDialogButtonBox(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel
			| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Apply
		)
		button_box.accepted.connect(self._accept_and_apply)
		button_box.rejected.connect(self.reject)
		# connect Apply button
		apply_btn = button_box.button(
			PySide6.QtWidgets.QDialogButtonBox.StandardButton.Apply
		)
		apply_btn.clicked.connect(self._apply)
		layout.addWidget(button_box)

	#============================================
	def _create_appearance_tab(self) -> PySide6.QtWidgets.QWidget:
		"""Create the appearance settings tab.

		Contains theme selection and grid visibility toggle.

		Returns:
			The appearance tab widget.
		"""
		widget = PySide6.QtWidgets.QWidget()
		form = PySide6.QtWidgets.QFormLayout(widget)

		# theme combo
		self._theme_combo = PySide6.QtWidgets.QComboBox()
		self._theme_combo.addItems(["dark", "light"])
		form.addRow(self.tr("Theme:"), self._theme_combo)

		# grid visible checkbox
		self._grid_check = PySide6.QtWidgets.QCheckBox()
		form.addRow(self.tr("Show grid:"), self._grid_check)

		# spacer to push controls to the top
		form.addItem(PySide6.QtWidgets.QSpacerItem(
			0, 0,
			PySide6.QtWidgets.QSizePolicy.Policy.Minimum,
			PySide6.QtWidgets.QSizePolicy.Policy.Expanding,
		))
		return widget

	#============================================
	def _create_drawing_tab(self) -> PySide6.QtWidgets.QWidget:
		"""Create the drawing defaults tab.

		Contains default element, bond length, and font size settings.

		Returns:
			The drawing tab widget.
		"""
		widget = PySide6.QtWidgets.QWidget()
		form = PySide6.QtWidgets.QFormLayout(widget)

		# default element
		self._element_edit = PySide6.QtWidgets.QLineEdit()
		self._element_edit.setMaxLength(3)
		self._element_edit.setPlaceholderText("C")
		form.addRow(self.tr("Default element:"), self._element_edit)

		# default bond length
		self._bond_length_spin = PySide6.QtWidgets.QDoubleSpinBox()
		self._bond_length_spin.setRange(10.0, 200.0)
		self._bond_length_spin.setValue(40.0)
		self._bond_length_spin.setSuffix(" px")
		form.addRow(self.tr("Bond length:"), self._bond_length_spin)

		# default font size
		self._font_size_spin = PySide6.QtWidgets.QSpinBox()
		self._font_size_spin.setRange(4, 72)
		self._font_size_spin.setValue(12)
		form.addRow(self.tr("Font size:"), self._font_size_spin)

		# spacer
		form.addItem(PySide6.QtWidgets.QSpacerItem(
			0, 0,
			PySide6.QtWidgets.QSizePolicy.Policy.Minimum,
			PySide6.QtWidgets.QSizePolicy.Policy.Expanding,
		))
		return widget

	#============================================
	def _create_file_tab(self) -> PySide6.QtWidgets.QWidget:
		"""Create the file handling tab.

		Contains recent files count and auto-save interval settings.

		Returns:
			The file tab widget.
		"""
		widget = PySide6.QtWidgets.QWidget()
		form = PySide6.QtWidgets.QFormLayout(widget)

		# recent files count
		self._recent_count_spin = PySide6.QtWidgets.QSpinBox()
		self._recent_count_spin.setRange(0, 30)
		self._recent_count_spin.setValue(10)
		form.addRow(self.tr("Recent files count:"), self._recent_count_spin)

		# auto-save interval (0 = disabled)
		self._autosave_spin = PySide6.QtWidgets.QSpinBox()
		self._autosave_spin.setRange(0, 60)
		self._autosave_spin.setSuffix(self.tr(" min"))
		self._autosave_spin.setSpecialValueText(self.tr("Disabled"))
		self._autosave_spin.setValue(0)
		form.addRow(self.tr("Auto-save interval:"), self._autosave_spin)

		# spacer
		form.addItem(PySide6.QtWidgets.QSpacerItem(
			0, 0,
			PySide6.QtWidgets.QSizePolicy.Policy.Minimum,
			PySide6.QtWidgets.QSizePolicy.Policy.Expanding,
		))
		return widget

	#============================================
	def _create_shortcuts_tab(self) -> PySide6.QtWidgets.QWidget:
		"""Create the keyboard shortcuts tab.

		Displays a table of action names and their key sequences.
		Users can double-click the key sequence column to edit.

		Returns:
			The shortcuts tab widget.
		"""
		widget = PySide6.QtWidgets.QWidget()
		layout = PySide6.QtWidgets.QVBoxLayout(widget)

		# shortcuts table
		self._shortcuts_table = PySide6.QtWidgets.QTableWidget()
		self._shortcuts_table.setColumnCount(2)
		self._shortcuts_table.setHorizontalHeaderLabels([
			self.tr("Action"), self.tr("Shortcut"),
		])
		# stretch the columns
		header = self._shortcuts_table.horizontalHeader()
		header.setStretchLastSection(True)
		header.setSectionResizeMode(
			0, PySide6.QtWidgets.QHeaderView.ResizeMode.Stretch
		)
		layout.addWidget(self._shortcuts_table)

		# reset defaults button
		reset_btn = PySide6.QtWidgets.QPushButton(self.tr("Reset to Defaults"))
		reset_btn.clicked.connect(self._reset_shortcuts)
		layout.addWidget(reset_btn)

		return widget

	#============================================
	def _populate_from_prefs(self) -> None:
		"""Fill all dialog fields from current preferences."""
		# appearance
		theme = self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_THEME
		)
		idx = self._theme_combo.findText(str(theme))
		if idx >= 0:
			self._theme_combo.setCurrentIndex(idx)
		grid_vis = self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_VISIBLE
		)
		self._grid_check.setChecked(bool(grid_vis))

		# drawing defaults
		element = self._prefs.value("drawing/default_element", "C")
		self._element_edit.setText(str(element))
		bond_len = self._prefs.value("drawing/bond_length", 40.0)
		self._bond_length_spin.setValue(float(bond_len))
		font_sz = self._prefs.value("drawing/font_size", 12)
		self._font_size_spin.setValue(int(font_sz))

		# file
		recent_count = self._prefs.value("files/recent_count", 10)
		self._recent_count_spin.setValue(int(recent_count))
		autosave = self._prefs.value("files/autosave_interval", 0)
		self._autosave_spin.setValue(int(autosave))

		# shortcuts table
		self._populate_shortcuts_table()

	#============================================
	def _populate_shortcuts_table(self) -> None:
		"""Fill the shortcuts table from keybinding defaults and prefs."""
		# import here to avoid circular dependency at module level
		import bkchem_qt.config.keybindings
		bindings = dict(bkchem_qt.config.keybindings.DEFAULT_KEYBINDINGS)
		# override with any saved values from preferences
		for action_name in bindings:
			saved = self._prefs.value("keybindings/" + action_name)
			if saved is not None and isinstance(saved, str):
				bindings[action_name] = saved
		# fill table
		sorted_actions = sorted(bindings.keys())
		self._shortcuts_table.setRowCount(len(sorted_actions))
		for row, action_name in enumerate(sorted_actions):
			# action name column (read-only)
			name_item = PySide6.QtWidgets.QTableWidgetItem(action_name)
			name_item.setFlags(
				PySide6.QtCore.Qt.ItemFlag.ItemIsEnabled
				| PySide6.QtCore.Qt.ItemFlag.ItemIsSelectable
			)
			self._shortcuts_table.setItem(row, 0, name_item)
			# key sequence column (editable)
			seq_item = PySide6.QtWidgets.QTableWidgetItem(bindings[action_name])
			self._shortcuts_table.setItem(row, 1, seq_item)

	#============================================
	def _reset_shortcuts(self) -> None:
		"""Reset the shortcuts table to default values."""
		import bkchem_qt.config.keybindings
		bindings = bkchem_qt.config.keybindings.DEFAULT_KEYBINDINGS
		sorted_actions = sorted(bindings.keys())
		self._shortcuts_table.setRowCount(len(sorted_actions))
		for row, action_name in enumerate(sorted_actions):
			name_item = PySide6.QtWidgets.QTableWidgetItem(action_name)
			name_item.setFlags(
				PySide6.QtCore.Qt.ItemFlag.ItemIsEnabled
				| PySide6.QtCore.Qt.ItemFlag.ItemIsSelectable
			)
			self._shortcuts_table.setItem(row, 0, name_item)
			seq_item = PySide6.QtWidgets.QTableWidgetItem(bindings[action_name])
			self._shortcuts_table.setItem(row, 1, seq_item)

	#============================================
	def _apply(self) -> None:
		"""Save all settings to Preferences."""
		# appearance
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_THEME,
			self._theme_combo.currentText(),
		)
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_VISIBLE,
			self._grid_check.isChecked(),
		)
		# drawing
		self._prefs.set_value(
			"drawing/default_element",
			self._element_edit.text().strip() or "C",
		)
		self._prefs.set_value(
			"drawing/bond_length",
			self._bond_length_spin.value(),
		)
		self._prefs.set_value(
			"drawing/font_size",
			self._font_size_spin.value(),
		)
		# file
		self._prefs.set_value(
			"files/recent_count",
			self._recent_count_spin.value(),
		)
		self._prefs.set_value(
			"files/autosave_interval",
			self._autosave_spin.value(),
		)
		# shortcuts
		row_count = self._shortcuts_table.rowCount()
		for row in range(row_count):
			name_item = self._shortcuts_table.item(row, 0)
			seq_item = self._shortcuts_table.item(row, 1)
			if name_item is not None and seq_item is not None:
				action_name = name_item.text()
				key_seq = seq_item.text()
				self._prefs.set_value("keybindings/" + action_name, key_seq)

	#============================================
	def _accept_and_apply(self) -> None:
		"""Apply settings and close the dialog."""
		self._apply()
		self.accept()

	#============================================
	@staticmethod
	def show_preferences(parent=None) -> bool:
		"""Convenience method: show dialog, return True if applied.

		Args:
			parent: Optional parent widget.

		Returns:
			True if the user accepted the dialog, False otherwise.
		"""
		dialog = PreferencesDialog(parent)
		result = dialog.exec()
		accepted = result == PySide6.QtWidgets.QDialog.DialogCode.Accepted
		return accepted
