"""Platform-aware menu adapter for BKChem-Qt."""

# Standard Library
import sys

# PIP3 modules
import PySide6.QtGui

# macOS Unicode modifier symbols for the keyboard shortcuts dialog
_MAC_CMD = '\u2318'
_MAC_SHIFT = '\u21e7'
_MAC_OPT = '\u2325'
_MAC_CTRL = '\u2303'


#============================================
def format_accelerator(accel_str: str) -> str:
	"""Convert internal accelerator notation to Qt shortcut string.

	Qt handles Cmd display on macOS automatically when you use Ctrl+
	notation with QKeySequence, so this always outputs Ctrl+ format
	regardless of platform.

	Args:
		accel_str: Internal notation like '(C-S-z)' or None.

	Returns:
		Qt shortcut string like 'Ctrl+Shift+Z', or None if input is None
		or not convertible.
	"""
	if accel_str is None:
		return None
	# strip parentheses wrapper
	inner = accel_str.strip()
	if inner.startswith('(') and inner.endswith(')'):
		inner = inner[1:-1]
	else:
		# already in display format (e.g. 'Ctrl+N'), pass through
		return accel_str
	# skip multi-key sequences (contain spaces between key groups)
	if ' ' in inner:
		return None
	# handle edge case: key char is '-' itself (e.g., 'C--')
	# split('C--') would give ['C', '', ''] which is wrong
	if inner.endswith('--'):
		# modifier-minus pattern: everything before trailing '--' is modifiers
		mod_part = inner[:-2]
		key_char = '-'
		modifiers = [p for p in mod_part.split('-') if p]
	else:
		parts = inner.split('-')
		# last part is the key character
		key_char = parts[-1]
		modifiers = parts[:-1]
	# build Qt shortcut string with Ctrl+ notation
	mod_names = []
	if 'C' in modifiers or 'M' in modifiers:
		mod_names.append('Ctrl')
	if 'A' in modifiers:
		mod_names.append('Alt')
	if 'S' in modifiers:
		mod_names.append('Shift')
	mod_names.append(key_char.upper())
	return '+'.join(mod_names)


#============================================
def format_accelerator_display(accel_str: str) -> str:
	"""Convert internal notation to Unicode display for non-menu contexts.

	Used by the keyboard shortcuts dialog where we need Unicode symbols
	directly (not Qt menu-rendered text).

	Args:
		accel_str: Internal notation like '(C-S-z)' or None.

	Returns:
		Unicode display string, or None if input is None.
	"""
	if accel_str is None:
		return None
	# strip parentheses wrapper
	inner = accel_str.strip()
	if inner.startswith('(') and inner.endswith(')'):
		inner = inner[1:-1]
	# handle edge case: key char is '-' itself (e.g., 'C--')
	if inner.endswith('--'):
		mod_part = inner[:-2]
		key_char = '-'
		modifiers = [p for p in mod_part.split('-') if p]
	else:
		parts = inner.split('-')
		key_char = parts[-1].upper()
		modifiers = [p for p in parts[:-1]]
	is_mac = sys.platform == 'darwin'
	if is_mac:
		result = ''
		if 'C' in modifiers or 'M' in modifiers:
			result += _MAC_CMD
		if 'A' in modifiers:
			result += _MAC_OPT
		if 'S' in modifiers:
			result += _MAC_SHIFT
		result += key_char.upper()
		return result
	# Linux/Windows: text format
	mod_names = []
	if 'C' in modifiers:
		mod_names.append('Ctrl')
	if 'M' in modifiers:
		mod_names.append('Meta')
	if 'A' in modifiers:
		mod_names.append('Alt')
	if 'S' in modifiers:
		mod_names.append('Shift')
	mod_names.append(key_char.upper())
	return '+'.join(mod_names)


#============================================
class PlatformMenuAdapter:
	"""Uniform wrapper around Qt QMenuBar/QMenu/QAction widgets."""

	#============================================
	def __init__(self, parent_window: object) -> None:
		"""Create the menu adapter for the given main window.

		Args:
			parent_window: QMainWindow instance.
		"""
		self._parent = parent_window
		self._menubar = parent_window.menuBar()
		# One adapter-owned Python retention tree mirrors the complete native menu
		# tree. Qt parents own deletion; this keeps every wrapper valid while the
		# live MainWindow still needs to update menu state.
		self._owned_menu_tree = {"menus": [], "actions": []}
		# menu_name -> QMenu
		self._menus = {}
		# action_key -> QAction (frozen English key lookup)
		self._actions = {}
		# (menu_name, label) -> QAction (legacy label-based lookup)
		self._actions_by_label = {}
		# cascade_name -> current dynamically replaced QAction wrappers
		self._dynamic_cascade_actions = {}

	#============================================
	def _retain_menu(self, menu: object) -> None:
		"""Keep one native QMenu wrapper live for this adapter lifetime."""
		self._owned_menu_tree["menus"].append(menu)

	#============================================
	def _retain_action(self, action: object) -> None:
		"""Keep one native QAction wrapper live for this adapter lifetime."""
		self._owned_menu_tree["actions"].append(action)

	#============================================
	def add_menu(self, name: str, help_text: str, side: str = 'left') -> None:
		"""Add a top-level menu to the menu bar.

		Args:
			name: Menu label text.
			help_text: Help text (stored but not displayed).
			side: Layout side (accepted for compat, ignored in Qt).
		"""
		menu = self._menubar.addMenu(name)
		self._menus[name] = menu
		self._retain_menu(menu)
		self._retain_action(menu.menuAction())

	#============================================
	def add_command(self, menu_name: str, label: str,
					accelerator: str, help_text: str,
					command: object,
					action_key: str = None) -> None:
		"""Add a command entry to a menu.

		Args:
			menu_name: Parent menu label.
			label: Command label text.
			accelerator: Keyboard shortcut string or None.
			help_text: Status help text (accepted for compat).
			command: Callable to invoke when triggered.
			action_key: Frozen English key for lookup (e.g. 'file.save').
		"""
		menu = self._menus[menu_name]
		action = menu.addAction(label)
		self._retain_action(action)
		# set keyboard shortcut if convertible
		qt_accel = format_accelerator(accelerator)
		if qt_accel is not None:
			action.setShortcut(PySide6.QtGui.QKeySequence(qt_accel))
		# connect the callback
		if command is not None:
			action.triggered.connect(command)
		# store by frozen key if provided
		if action_key is not None:
			self._actions[action_key] = action
		# store by label for legacy lookup
		self._actions_by_label[(menu_name, label)] = action

	#============================================
	def add_separator(self, menu_name: str) -> None:
		"""Add a separator to a menu.

		Args:
			menu_name: Parent menu label.
		"""
		action = self._menus[menu_name].addSeparator()
		self._retain_action(action)

	#============================================
	def add_direct_action(self, menu_name: str, label: str,
			action_key: str | None = None) -> object:
		"""Add and retain one programmatic QAction outside the YAML menu tree.

		Args:
			menu_name: Parent menu label.
			label: Visible action text.
			action_key: Optional frozen English key for later lookup.

		Returns:
			The retained QAction for caller-owned configuration.
		"""
		action = self._menus[menu_name].addAction(label)
		self._retain_action(action)
		if action_key is not None:
			self._actions[action_key] = action
		return action

	#============================================
	def add_cascade(self, menu_name: str, cascade_name: str,
					help_text: str) -> None:
		"""Add a cascade (submenu) to a menu.

		Args:
			menu_name: Parent menu label.
			cascade_name: Submenu label text.
			help_text: Help text (accepted for compat).
		"""
		parent_menu = self._menus[menu_name]
		sub_menu = parent_menu.addMenu(cascade_name)
		self._menus[cascade_name] = sub_menu
		self._retain_menu(sub_menu)
		self._retain_action(sub_menu.menuAction())

	#============================================
	def add_command_to_cascade(self, cascade_name: str, label: str,
								help_text: str, command: object,
								action_key: str = None) -> None:
		"""Add a command to an existing cascade submenu.

		Args:
			cascade_name: The cascade to add to.
			label: Command label text.
			help_text: Status help text (accepted for compat).
			command: Callable to invoke when triggered.
			action_key: Frozen English key for lookup (e.g. 'file.export_svg').
		"""
		menu = self._menus[cascade_name]
		action = menu.addAction(label)
		self._retain_action(action)
		if command is not None:
			action.triggered.connect(command)
		# store by frozen key if provided
		if action_key is not None:
			self._actions[action_key] = action
		# store by label for legacy lookup
		self._actions_by_label[(cascade_name, label)] = action

	#============================================
	def replace_cascade_commands(
			self, cascade_name: str,
			commands: list[tuple[str, object, bool, str | None]],
			) -> None:
		"""Replace one cascade's dynamic commands with adapter-owned wrappers.

		Qt clears the native submenu before this adapter releases the previous
		Python wrappers.  The replacement actions are retained for as long as
		they remain live in the cascade.

		Args:
			cascade_name: Existing cascade menu label.
			commands: Visible label, optional callback, enabled state, and optional
				full-path tooltip for each current command.
		"""
		menu = self._menus[cascade_name]
		obsolete_actions = self._dynamic_cascade_actions.pop(cascade_name, [])
		menu.clear()
		self._owned_menu_tree["actions"] = [
			candidate for candidate in self._owned_menu_tree["actions"]
			if not any(candidate is obsolete for obsolete in obsolete_actions)
		]
		current_actions = []
		for label, command, enabled, tooltip in commands:
			action = menu.addAction(label)
			action.setEnabled(enabled)
			if tooltip is not None:
				action.setToolTip(tooltip)
			if command is not None:
				action.triggered.connect(command)
			self._retain_action(action)
			current_actions.append(action)
		self._dynamic_cascade_actions[cascade_name] = current_actions

	#============================================
	def get_action_by_key(self, action_key: str) -> object:
		"""Look up a QAction by its frozen English key.

		Args:
			action_key: Dotted key like 'file.save' or 'edit.undo'.

		Returns:
			The QAction, or None if not found.
		"""
		return self._actions.get(action_key)

	#============================================
	def get_action(self, menu_name: str, label: str) -> object:
		"""Look up a QAction by menu name and label (legacy).

		Prefer get_action_by_key() for new code.

		Args:
			menu_name: The menu containing the action.
			label: The action's label text.

		Returns:
			The QAction, or None if not found.
		"""
		return self._actions_by_label.get((menu_name, label))

	#============================================
	def set_item_state_by_key(self, action_key: str,
								enabled: bool) -> None:
		"""Enable or disable a menu item by frozen English key.

		Args:
			action_key: Dotted key like 'file.save'.
			enabled: True to enable, False to disable.
		"""
		action = self._actions.get(action_key)
		if action is not None:
			action.setEnabled(enabled)

	#============================================
	def set_item_state(self, menu_name: str, label: str,
						enabled: bool) -> None:
		"""Enable or disable a menu item (legacy label-based).

		Prefer set_item_state_by_key() for new code.

		Args:
			menu_name: Parent menu label.
			label: The item label to configure.
			enabled: True to enable, False to disable.
		"""
		action = self._actions_by_label.get((menu_name, label))
		if action is not None:
			action.setEnabled(enabled)

	#============================================
	def register_direct_action(self, action_key: str,
								qaction: object) -> None:
		"""Register a QAction created outside the menu builder.

		Used for actions added directly to menus (e.g. grid toggle,
		export items) that are not in the YAML menu structure.

		Args:
			action_key: Frozen English key for the action.
			qaction: The QAction instance to register.
		"""
		self._actions[action_key] = qaction
		self._retain_action(qaction)

	#============================================
	def component(self, name: str) -> object:
		"""Get the underlying QMenu widget by name.

		Supports 'MenuName-menu' (Pmw convention) and plain 'MenuName'.

		Args:
			name: Component name.

		Returns:
			The QMenu widget, or None if not found.
		"""
		# strip '-menu' suffix for Pmw compatibility
		if name.endswith('-menu'):
			menu_name = name[:-5]
		else:
			menu_name = name
		return self._menus.get(menu_name)

	#============================================
	def get_menu_component(self, menu_name: str) -> object:
		"""Get the QMenu widget for a menu.

		Args:
			menu_name: The menu label.

		Returns:
			The QMenu widget, or None if not found.
		"""
		return self._menus.get(menu_name)
