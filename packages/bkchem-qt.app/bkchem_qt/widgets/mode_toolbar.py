"""Mode selection toolbar."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets


#============================================
class ModeToolbar(PySide6.QtWidgets.QToolBar):
	"""Toolbar for switching between interaction modes.

	Presents a row of mutually exclusive toggle buttons, one per mode.
	Clicking a button emits ``mode_selected`` with the mode name string
	so the mode manager can switch. Supports icons and visual separator
	markers between mode groups.

	Args:
		parent: Optional parent widget.
	"""

	# emitted when the user clicks a mode button
	mode_selected = PySide6.QtCore.Signal(str)

	#============================================
	def __init__(self, parent: object = None) -> None:
		"""Initialize the mode toolbar with an exclusive action group.

		Args:
			parent: Optional parent widget.
		"""
		super().__init__("Mode", parent)
		self.setMovable(False)
		self.setIconSize(PySide6.QtCore.QSize(32, 32))
		# show icon with text below, matching old compound='top' layout
		self.setToolButtonStyle(PySide6.QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
		# action group enforces mutual exclusion
		self._action_group = PySide6.QtGui.QActionGroup(self)
		self._action_group.setExclusive(True)
		# map mode name -> QAction for programmatic selection
		self._actions = {}

	#============================================
	def add_mode(self, name: str, label: str, tooltip: str = "",
			icon: PySide6.QtGui.QIcon = None) -> None:
		"""Add a mode button to the toolbar.

		Creates a checkable action in the exclusive action group and
		connects it to emit ``mode_selected`` when triggered.

		Args:
			name: Internal mode name (e.g. 'edit', 'draw').
			label: Display text on the button.
			tooltip: Optional tooltip string.
			icon: Optional QIcon to display on the button.
		"""
		action = PySide6.QtGui.QAction(label, self)
		action.setCheckable(True)
		if tooltip:
			action.setToolTip(tooltip)
		if icon is not None and not icon.isNull():
			action.setIcon(icon)
		# store the mode name on the action for lookup
		action.setData(name)
		# connect triggered signal
		action.triggered.connect(
			lambda checked, n=name: self._on_action_triggered(n, checked)
		)
		self._action_group.addAction(action)
		self.addAction(action)
		self._actions[name] = action

	#============================================
	def add_action_button(self, name: str, label: str, tooltip: str = "",
			icon: PySide6.QtGui.QIcon = None,
			callback: object = None) -> PySide6.QtGui.QAction:
		"""Add a non-checkable action button to the toolbar.

		Used for actions like Undo/Redo that are not mode toggles.
		The button is not added to the exclusive action group.

		Args:
			name: Internal action name.
			label: Display text on the button.
			tooltip: Optional tooltip string.
			icon: Optional QIcon to display.
			callback: Optional callable to connect to triggered signal.

		Returns:
			The created QAction.
		"""
		action = PySide6.QtGui.QAction(label, self)
		action.setCheckable(False)
		if tooltip:
			action.setToolTip(tooltip)
		if icon is not None and not icon.isNull():
			action.setIcon(icon)
		if callback is not None:
			action.triggered.connect(callback)
		self.addAction(action)
		self._actions[name] = action
		return action

	#============================================
	def add_separator_marker(self) -> None:
		"""Insert a visual separator with spacing between mode groups."""
		self.addSeparator()
		# add 8px spacer after separator for visual breathing room
		spacer = PySide6.QtWidgets.QWidget()
		spacer.setFixedWidth(8)
		self.addWidget(spacer)

	#============================================
	def set_active_mode(self, name: str) -> None:
		"""Highlight the button for the given mode.

		Checks the corresponding action without emitting a signal
		to avoid feedback loops when the mode manager calls this.

		Args:
			name: Internal mode name to activate.
		"""
		action = self._actions.get(name)
		if action is None:
			return
		for mode_action in self._action_group.actions():
			mode_action.setChecked(mode_action is action)

	#============================================
	def update_action_icon(self, name: str, icon: PySide6.QtGui.QIcon) -> None:
		"""Update the icon on an existing mode action.

		Used when the theme changes and icons need to be reloaded.

		Args:
			name: Internal mode name.
			icon: New QIcon to set.
		"""
		action = self._actions.get(name)
		if action is not None:
			action.setIcon(icon)

	#============================================
	def _on_action_triggered(self, name: str, checked: bool) -> None:
		"""Handle an action click by emitting the mode name.

		Args:
			name: The mode name associated with the clicked action.
			checked: Whether this mode action became checked.
		"""
		if checked:
			self.mode_selected.emit(name)
