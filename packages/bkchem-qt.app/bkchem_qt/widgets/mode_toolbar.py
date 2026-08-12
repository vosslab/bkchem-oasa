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
	_COMPACT_BREAKPOINT = 1120

	#============================================
	def __init__(self, parent: object = None) -> None:
		"""Initialize the mode toolbar with an exclusive action group.

		Args:
			parent: Optional parent widget.
		"""
		super().__init__("Mode", parent)
		self.setMovable(False)
		self.setSizePolicy(
			PySide6.QtWidgets.QSizePolicy.Policy.Ignored,
			PySide6.QtWidgets.QSizePolicy.Policy.Fixed,
		)
		self.setIconSize(PySide6.QtCore.QSize(32, 32))
		# show icon with text below, matching old compound='top' layout
		self.setToolButtonStyle(PySide6.QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
		# action group enforces mutual exclusion
		self._action_group = PySide6.QtGui.QActionGroup(self)
		self._action_group.setExclusive(True)
		# map mode name -> QAction for programmatic selection
		self._actions = {}
		self._mode_actions = []
		self._mode_widget_actions = []
		self._compact_actions = []
		self._mode_chooser = None
		self._mode_chooser_action = None

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
		action.setObjectName(f"mode-action-{name}")
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
		button = PySide6.QtWidgets.QToolButton(self)
		button.setObjectName(f"mode-button-{name}")
		button.setDefaultAction(action)
		button.setToolButtonStyle(
			PySide6.QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon
		)
		button_action = self.addWidget(button)
		self._actions[name] = action
		self._mode_actions.append(action)
		self._mode_widget_actions.append(button_action)

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
		action.setObjectName(f"mode-action-{name}")
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
	def add_separator_marker(self, collapse_in_compact: bool = True) -> None:
		"""Insert a visual separator with spacing between mode groups."""
		separator = self.addSeparator()
		# add 8px spacer after separator for visual breathing room
		spacer = PySide6.QtWidgets.QWidget()
		spacer.setFixedWidth(8)
		spacer_action = self.addWidget(spacer)
		if collapse_in_compact:
			self._compact_actions.extend((separator, spacer_action))

	#============================================
	def add_compact_chooser(self) -> None:
		"""Add the responsive menu used when the toolbar is narrow.

		The menu reuses the mode actions, so shortcuts, checked state, and
		selection signals have one authoritative implementation.
		"""
		if self._mode_chooser is not None:
			raise RuntimeError("A mode toolbar can only have one compact chooser")
		chooser = PySide6.QtWidgets.QToolButton(self)
		chooser.setPopupMode(
			PySide6.QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup
		)
		chooser.setToolButtonStyle(
			PySide6.QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
		)
		chooser.setAccessibleName("Mode chooser")
		chooser.setObjectName("mode-chooser")
		menu = PySide6.QtWidgets.QMenu(chooser)
		for action in self._mode_actions:
			menu.addAction(action)
		chooser.setMenu(menu)
		self._mode_chooser = chooser
		self._mode_chooser_action = self.addWidget(chooser)
		self._sync_compact_chooser()
		PySide6.QtCore.QTimer.singleShot(0, self._sync_compact_chooser)

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
		self._sync_compact_chooser()

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
			self._sync_compact_chooser()

	def event(self, event: PySide6.QtCore.QEvent) -> bool:
		"""React to toolbar layout changes on every supported Qt platform."""
		result = super().event(event)
		if event.type() == PySide6.QtCore.QEvent.Type.Resize:
			PySide6.QtCore.QTimer.singleShot(0, self._sync_compact_chooser)
		return result

	#============================================
	def minimumSizeHint(self) -> PySide6.QtCore.QSize:
		"""Keep the workspace resizable even while wide mode buttons show."""
		base_hint = super().minimumSizeHint()
		return PySide6.QtCore.QSize(320, base_hint.height())

	#============================================
	def resizeEvent(self, event: PySide6.QtGui.QResizeEvent) -> None:
		"""Update the chooser as Qt lays out the containing main window."""
		super().resizeEvent(event)
		self._sync_compact_chooser()

	#============================================
	def _sync_compact_chooser(self) -> None:
		"""Show either the full mode row or its compact menu equivalent."""
		if self._mode_chooser is None or self._mode_chooser_action is None:
			return
		compact = self.window().width() < self._COMPACT_BREAKPOINT
		for action in self._mode_widget_actions:
			action.setVisible(not compact)
		for action in self._compact_actions:
			action.setVisible(not compact)
		self._mode_chooser_action.setVisible(compact)
		active_action = next(
			(action for action in self._mode_actions if action.isChecked()), None
		)
		if active_action is None:
			return
		self._mode_chooser.setText(f"Mode: {active_action.text()}")
		self._mode_chooser.setIcon(active_action.icon())
		self._mode_chooser.setToolTip(
			f"Current mode: {active_action.text()}. Select another drawing mode."
		)
		self._mode_chooser.setAccessibleDescription(
			f"Current mode is {active_action.text()}. Open to select a mode."
		)
