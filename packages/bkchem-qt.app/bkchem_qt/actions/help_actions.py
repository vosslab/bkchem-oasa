"""Help menu action registrations for BKChem-Qt."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _format_accelerator(accel: str) -> str:
	"""Convert an internal accelerator string to human-readable form.

	Translates the compact ``(C-x)`` / ``(C-S-x)`` format into
	the conventional ``Ctrl+X`` / ``Ctrl+Shift+X`` display format.

	Args:
		accel: Internal accelerator string, e.g. ``"(C-S-z)"``.

	Returns:
		Human-readable shortcut string, e.g. ``"Ctrl+Shift+Z"``.
	"""
	# strip surrounding parentheses
	inner = accel.strip("()")
	parts = inner.split("-")
	# build the human-readable form
	result_parts = []
	for part in parts[:-1]:
		if part == "C":
			result_parts.append("Ctrl")
		elif part == "S":
			result_parts.append("Shift")
		elif part == "M":
			result_parts.append("Alt")
		else:
			result_parts.append(part)
	# last part is the key character
	key = parts[-1]
	# handle special key names
	if key == "+":
		result_parts.append("+")
	elif key == "-":
		# the split on "-" loses a trailing "-"; detect from original
		result_parts.append("-")
	else:
		result_parts.append(key.upper())
	formatted = "+".join(result_parts)
	return formatted


#============================================
def _extract_category(action_id: str) -> str:
	"""Extract the menu category from a dotted action ID.

	Args:
		action_id: Dotted action ID like ``"file.save"`` or
			``"edit.undo"``.

	Returns:
		Capitalized category string, e.g. ``"File"`` or ``"Edit"``.
	"""
	prefix = action_id.split(".")[0]
	category = prefix.capitalize()
	return category


#============================================
def _show_keyboard_shortcuts(app: object) -> None:
	"""Show a modal dialog listing all registered keyboard shortcuts.

	Iterates the action registry, filters to actions with non-None
	accelerators, and displays them in a sortable three-column table
	grouped by menu category.

	Args:
		app: The main BKChem-Qt application window.
	"""
	# gather all actions with keyboard shortcuts
	all_actions = app._registry.all_actions()
	shortcut_actions = []
	for action_id, action in all_actions.items():
		if action.accelerator is not None:
			shortcut_actions.append((action_id, action))

	# sort by category (action ID prefix), then by action label
	shortcut_actions.sort(
		key=lambda pair: (
			_extract_category(pair[0]),
			pair[1].label,
		)
	)

	# build the dialog
	dialog = PySide6.QtWidgets.QDialog(app)
	dialog.setWindowTitle("Keyboard Shortcuts Reference")
	dialog.resize(560, 420)

	layout = PySide6.QtWidgets.QVBoxLayout(dialog)

	# create the table
	table = PySide6.QtWidgets.QTableWidget()
	table.setColumnCount(3)
	table.setHorizontalHeaderLabels(["Category", "Action", "Shortcut"])
	table.setRowCount(len(shortcut_actions))
	table.setEditTriggers(
		PySide6.QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
	)
	table.setSelectionBehavior(
		PySide6.QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
	)
	table.verticalHeader().setVisible(False)

	# populate rows
	for row_idx, (action_id, action) in enumerate(shortcut_actions):
		category = _extract_category(action_id)
		label = action.label
		shortcut = _format_accelerator(action.accelerator)

		cat_item = PySide6.QtWidgets.QTableWidgetItem(category)
		label_item = PySide6.QtWidgets.QTableWidgetItem(label)
		key_item = PySide6.QtWidgets.QTableWidgetItem(shortcut)

		table.setItem(row_idx, 0, cat_item)
		table.setItem(row_idx, 1, label_item)
		table.setItem(row_idx, 2, key_item)

	# stretch columns to fill available width
	header = table.horizontalHeader()
	header.setSectionResizeMode(
		0, PySide6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents
	)
	header.setSectionResizeMode(
		1, PySide6.QtWidgets.QHeaderView.ResizeMode.Stretch
	)
	header.setSectionResizeMode(
		2, PySide6.QtWidgets.QHeaderView.ResizeMode.ResizeToContents
	)

	layout.addWidget(table)

	# Close button
	buttons = PySide6.QtWidgets.QDialogButtonBox(
		PySide6.QtWidgets.QDialogButtonBox.StandardButton.Close
	)
	buttons.rejected.connect(dialog.reject)
	layout.addWidget(buttons)

	dialog.exec()


#============================================
def register_help_actions(registry: object, app: object) -> None:
	"""Register all Help menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# show keyboard shortcut reference
	registry.register(MenuAction(
		id='help.keyboard_shortcuts',
		label_key='Keyboard Shortcuts',
		help_key='Show keyboard shortcut reference',
		accelerator=None,
		handler=lambda: _show_keyboard_shortcuts(app),
		enabled_when=None,
	))

	# show general information about BKChem
	registry.register(MenuAction(
		id='help.about',
		label_key='About',
		help_key='General information about BKChem',
		accelerator=None,
		handler=app._on_about,
		enabled_when=None,
	))
