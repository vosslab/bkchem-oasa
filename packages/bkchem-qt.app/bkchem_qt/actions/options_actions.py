"""Options menu action registrations for BKChem-Qt."""

# Standard Library
import os
import logging

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.config.geometry_units
import bkchem_qt.config.preferences
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _show_standard_dialog(app: object) -> None:
	"""Show a dialog for setting default drawing style values.

	Presents a form with bond length, line width, font size, and
	font family controls.  Accepted values are stored in Preferences
	under the ``drawing/`` key group.

	Args:
		app: The main BKChem-Qt application window.
	"""
	prefs = app._prefs

	dialog = PySide6.QtWidgets.QDialog(app)
	dialog.setWindowTitle("Drawing Style Defaults")
	dialog.setMinimumWidth(360)

	layout = PySide6.QtWidgets.QFormLayout(dialog)

	# bond length spin box
	bond_spin = PySide6.QtWidgets.QDoubleSpinBox()
	bond_spin.setRange(10.0, 100.0)
	bond_spin.setSingleStep(1.0)
	bond_spin.setDecimals(1)
	bond_spin.setSuffix(" pt")
	stored_bond = prefs.value(
		bkchem_qt.config.preferences.Preferences.KEY_BOND_LENGTH_PT,
		bkchem_qt.config.geometry_units.DEFAULT_BOND_LENGTH_PT,
	)
	bond_spin.setValue(float(stored_bond))
	layout.addRow("Bond length:", bond_spin)

	# line width spin box
	line_spin = PySide6.QtWidgets.QDoubleSpinBox()
	line_spin.setRange(0.5, 10.0)
	line_spin.setSingleStep(0.5)
	line_spin.setDecimals(1)
	stored_line = prefs.value("drawing/line_width", 2.0)
	line_spin.setValue(float(stored_line))
	layout.addRow("Line width:", line_spin)

	# font size spin box
	font_spin = PySide6.QtWidgets.QSpinBox()
	font_spin.setRange(6, 48)
	stored_font_size = prefs.value("drawing/font_size", 12)
	font_spin.setValue(int(stored_font_size))
	layout.addRow("Font size:", font_spin)

	# font family combo box
	font_combo = PySide6.QtWidgets.QComboBox()
	families = ["Helvetica", "Arial", "Times New Roman", "Courier"]
	font_combo.addItems(families)
	stored_family = prefs.value("drawing/font_family", "Helvetica")
	idx = font_combo.findText(str(stored_family))
	if idx >= 0:
		font_combo.setCurrentIndex(idx)
	layout.addRow("Font family:", font_combo)

	# OK / Cancel buttons
	buttons = PySide6.QtWidgets.QDialogButtonBox(
		PySide6.QtWidgets.QDialogButtonBox.StandardButton.Ok
		| PySide6.QtWidgets.QDialogButtonBox.StandardButton.Cancel
	)
	buttons.accepted.connect(dialog.accept)
	buttons.rejected.connect(dialog.reject)
	layout.addRow(buttons)

	if dialog.exec() == PySide6.QtWidgets.QDialog.DialogCode.Accepted:
		prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_BOND_LENGTH_PT,
			bond_spin.value(),
		)
		prefs.set_value("drawing/line_width", line_spin.value())
		prefs.set_value("drawing/font_size", font_spin.value())
		prefs.set_value("drawing/font_family", font_combo.currentText())
		if hasattr(app, "_apply_geometry_preferences"):
			app._apply_geometry_preferences()
		app.statusBar().showMessage(
			"Drawing style defaults saved", 3000
		)


#============================================
def _show_language_dialog(app: object) -> None:
	"""Show a dialog for selecting the application language.

	Stores the chosen language in Preferences under
	``general/language`` and notifies that a restart is needed.

	Args:
		app: The main BKChem-Qt application window.
	"""
	prefs = app._prefs
	languages = ["English", "Czech", "French", "German", "Spanish"]
	stored = str(prefs.value("general/language", "English"))

	# determine pre-selected index
	current_idx = 0
	if stored in languages:
		current_idx = languages.index(stored)

	chosen, accepted = PySide6.QtWidgets.QInputDialog.getItem(
		app, "Language", "Select language:", languages,
		current_idx, False,
	)
	if not accepted:
		return

	prefs.set_value("general/language", chosen)
	PySide6.QtWidgets.QMessageBox.information(
		app, "Language Changed",
		f"Language set to {chosen}.\n"
		"This change takes effect on the next restart.",
	)


#============================================
def _show_logging_dialog(app: object) -> None:
	"""Show a dialog for selecting the logging verbosity level.

	Stores the chosen level in Preferences under
	``general/logging_level`` and applies it immediately.

	Args:
		app: The main BKChem-Qt application window.
	"""
	prefs = app._prefs
	levels = ["Errors only", "Warnings", "Info", "Debug"]
	# map display names to Python logging levels
	level_map = {
		"Errors only": logging.ERROR,
		"Warnings": logging.WARNING,
		"Info": logging.INFO,
		"Debug": logging.DEBUG,
	}

	stored = str(prefs.value("general/logging_level", "Warnings"))
	current_idx = 0
	if stored in levels:
		current_idx = levels.index(stored)

	chosen, accepted = PySide6.QtWidgets.QInputDialog.getItem(
		app, "Logging Level", "Select logging level:", levels,
		current_idx, False,
	)
	if not accepted:
		return

	prefs.set_value("general/logging_level", chosen)

	# apply the chosen level immediately to the root logger
	py_level = level_map.get(chosen, logging.WARNING)
	logging.getLogger().setLevel(py_level)
	app.statusBar().showMessage(
		f"Logging level set to {chosen}", 3000
	)


#============================================
def _show_inchi_path_dialog(app: object) -> None:
	"""Show a file dialog to locate the InChI executable.

	Validates that the selected file exists and is executable,
	then stores the path in Preferences under
	``chemistry/inchi_path``.

	Args:
		app: The main BKChem-Qt application window.
	"""
	prefs = app._prefs
	stored = str(prefs.value("chemistry/inchi_path", ""))

	path, _ = PySide6.QtWidgets.QFileDialog.getOpenFileName(
		app, "Locate InChI Program", stored,
		"All Files (*)",
	)
	if not path:
		return

	# verify the file exists and is executable
	if not os.path.isfile(path):
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Invalid Path",
			f"File not found:\n{path}",
		)
		return

	if not os.access(path, os.X_OK):
		PySide6.QtWidgets.QMessageBox.warning(
			app, "Not Executable",
			f"The selected file is not executable:\n{path}",
		)
		return

	prefs.set_value("chemistry/inchi_path", path)
	PySide6.QtWidgets.QMessageBox.information(
		app, "InChI Path Set",
		f"InChI program path saved:\n{path}",
	)


#============================================
def register_options_actions(registry: object, app: object) -> None:
	"""Register all Options menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# set the default drawing style
	registry.register(MenuAction(
		id='options.standard',
		label_key='Standard',
		help_key='Set the default drawing style here',
		accelerator=None,
		handler=lambda: _show_standard_dialog(app),
		enabled_when=None,
	))

	# set the language used after next restart
	registry.register(MenuAction(
		id='options.language',
		label_key='Language',
		help_key='Set the language used after next restart',
		accelerator=None,
		handler=lambda: _show_language_dialog(app),
		enabled_when=None,
	))

	# set how messages in BKChem are displayed
	registry.register(MenuAction(
		id='options.logging',
		label_key='Logging',
		help_key='Set how messages in BKChem are displayed to you',
		accelerator=None,
		handler=lambda: _show_logging_dialog(app),
		enabled_when=None,
	))

	# set the path to the InChI program
	registry.register(MenuAction(
		id='options.inchi_path',
		label_key='InChI program path',
		help_key='To use InChI in BKChem you must first give it '
			'a path to the InChI program here',
		accelerator=None,
		handler=lambda: _show_inchi_path_dialog(app),
		enabled_when=None,
	))

	# choose a color theme
	registry.register(MenuAction(
		id='options.theme',
		label_key='Theme',
		help_key='Choose a color theme',
		accelerator=None,
		handler=app._on_choose_theme,
		enabled_when=None,
	))

	# open the preferences dialog
	registry.register(MenuAction(
		id='options.preferences',
		label_key='Preferences',
		help_key='Preferences',
		accelerator=None,
		handler=app._on_preferences,
		enabled_when=None,
	))
