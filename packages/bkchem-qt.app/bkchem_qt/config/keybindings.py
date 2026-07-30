"""Keyboard shortcut management for BKChem-Qt."""

# Standard Library
import functools

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.config.preferences

# Non-registry defaults: action_name -> key sequence string.
#
# Menu action accelerators belong to ActionRegistry and are converted through
# PlatformMenuAdapter.  Keeping only direct controls and modes here prevents
# a second spelling of the same menu shortcut from drifting out of sync.
DEFAULT_KEYBINDINGS = {
	"view.toggle_grid": "Ctrl+G",
	"view.toggle_grid_snap": "Ctrl+Shift+G",
	"mode.edit": "Ctrl+1",
	"mode.draw": "Ctrl+2",
	"mode.template": "Ctrl+3",
	"mode.arrow": "Ctrl+4",
	"mode.text": "Ctrl+5",
	"mode.rotate": "Ctrl+6",
	"mode.mark": "Ctrl+7",
	"mode.atom": "Ctrl+8",
}

# settings key prefix for stored keybindings
_SETTINGS_PREFIX = "keybindings/"

# Earlier Qt builds exposed these IDs in Preferences even though their action
# registry names were different.  Continue to honor an existing preference,
# but only the registry IDs are used from this point onward.
_LEGACY_ACTION_IDS = {
	"file.load": "file.open",
	"file.exit": "file.quit",
	"view.zoom_reset": "view.reset_zoom",
}


#============================================
class KeybindingConflictError(ValueError):
	"""Report two active commands configured for the same key sequence."""


#============================================
class KeybindingRegistrationError(ValueError):
	"""Report a configured shortcut with no action or command target."""


#============================================
class KeybindingManager(PySide6.QtCore.QObject):
	"""Manages keyboard shortcuts and allows customization.

	Loads keybindings from preferences on startup. Menu actions keep their
	native QAction shortcuts so they remain visible in menus; mode commands use
	QShortcut instances on the main window. Bindings can be changed at runtime
	and persisted back to preferences.

	Args:
		main_window: The QMainWindow that owns the shortcuts.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, main_window: PySide6.QtWidgets.QMainWindow,
			registry: object,
			parent: PySide6.QtCore.QObject | None = None) -> None:
		"""Initialize the keybinding manager.

		Args:
			main_window: The QMainWindow that owns the shortcuts.
			registry: ActionRegistry containing the menu action contract.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._main_window = main_window
		self._registry = registry
		self._shortcuts = {}
		self._menu_actions = {}
		self._bindings = self.default_bindings()
		# load saved bindings from preferences, overriding defaults
		self._load_from_preferences()

	#============================================
	def default_bindings(self) -> dict:
		"""Return registry, direct-action, and mode shortcut defaults."""
		from bkchem_qt.actions.platform_menu import format_accelerator
		bindings = {}
		for action_name, action in self._registry.all_actions().items():
			sequence = format_accelerator(action.accelerator)
			bindings[action_name] = sequence if sequence is not None else ""
		for action_name, sequence in DEFAULT_KEYBINDINGS.items():
			if action_name in bindings:
				raise KeybindingRegistrationError(
					"Direct shortcut '%s' duplicates an ActionRegistry ID."
					% action_name
				)
			bindings[action_name] = sequence
		return bindings

	#============================================
	def _load_from_preferences(self) -> None:
		"""Load saved keybindings from QSettings, overriding defaults."""
		prefs = bkchem_qt.config.preferences.Preferences.instance()
		for action_name in self._bindings:
			key = _SETTINGS_PREFIX + action_name
			saved = prefs.value(key)
			if saved is None and action_name in _LEGACY_ACTION_IDS:
				legacy_key = _SETTINGS_PREFIX + _LEGACY_ACTION_IDS[action_name]
				saved = prefs.value(legacy_key)
			if saved is not None and isinstance(saved, str):
				self._bindings[action_name] = saved

	#============================================
	def _validate_bindings(self) -> None:
		"""Reject empty, invalid, or ambiguous active key sequences."""
		sequences = {}
		for action_name, key_sequence in self._bindings.items():
			if not key_sequence:
				continue
			sequence = PySide6.QtGui.QKeySequence(key_sequence)
			normalized = sequence.toString(
				PySide6.QtGui.QKeySequence.SequenceFormat.PortableText,
			)
			if not normalized:
				raise KeybindingRegistrationError(
					f"Invalid key sequence for '{action_name}': {key_sequence!r}"
				)
			sequences.setdefault(normalized, []).append(action_name)
		conflicts = {
			sequence: action_names
			for sequence, action_names in sequences.items()
			if len(action_names) > 1
		}
		if conflicts:
			details = "; ".join(
				f"{sequence}: {', '.join(action_names)}"
				for sequence, action_names in sorted(conflicts.items())
			)
			raise KeybindingConflictError(
				f"Conflicting BKChem keyboard shortcuts: {details}"
			)

	#============================================
	def _mode_callback(self, action_name: str) -> object:
		"""Return the active-session callback for a mode shortcut."""
		if not action_name.startswith("mode."):
			raise KeybindingRegistrationError(
				f"No shortcut target is registered for '{action_name}'."
			)
		mode_name = action_name.split(".", 1)[1]
		return functools.partial(self._activate_mode, mode_name)

	#============================================
	def _activate_mode(self, mode_name: str) -> None:
		"""Select a mode on whichever document session is active now."""
		self._main_window._on_mode_selected(mode_name)

	#============================================
	def setup_shortcuts(self) -> None:
		"""Create QShortcut objects for all bindings.

		Menu commands use their existing QActions so their current shortcut is
		visible in the native menu.  Commands without menu actions (currently
		mode selection) receive a QShortcut on the window.  Every callback
		resolves the active session when it fires, never when shortcuts are set
		up.
		"""
		self._validate_bindings()
		# remove old shortcuts
		for shortcut in self._shortcuts.values():
			shortcut.setEnabled(False)
			shortcut.deleteLater()
		self._shortcuts.clear()
		self._menu_actions.clear()
		# apply menu actions or create standalone mode shortcuts
		for action_name, key_seq_str in self._bindings.items():
			menu_action = self._main_window._adapter.get_action_by_key(
				action_name
			)
			if menu_action is not None:
				menu_action.setShortcut(PySide6.QtGui.QKeySequence(key_seq_str))
				self._menu_actions[action_name] = menu_action
				continue
			shortcut = PySide6.QtGui.QShortcut(
				PySide6.QtGui.QKeySequence(key_seq_str), self._main_window,
			)
			shortcut.setContext(
				PySide6.QtCore.Qt.ShortcutContext.WindowShortcut
			)
			shortcut.activated.connect(self._mode_callback(action_name))
			self._shortcuts[action_name] = shortcut

	#============================================
	def set_binding(self, action_name: str, key_sequence: str) -> None:
		"""Change a keybinding and persist it.

		Updates the in-memory binding, updates the QShortcut if it
		exists, and saves to preferences.

		Args:
			action_name: Dotted action identifier (e.g. "file.new").
			key_sequence: Qt key sequence string (e.g. "Ctrl+N") or
				empty string to clear.
		"""
		if action_name not in self._bindings:
			raise KeybindingRegistrationError(
				f"Unknown BKChem keyboard action '{action_name}'."
			)
		previous = self._bindings[action_name]
		self._bindings[action_name] = key_sequence
		try:
			self._validate_bindings()
		except (KeybindingConflictError, KeybindingRegistrationError):
			self._bindings[action_name] = previous
			raise
		# update the live shortcut if it exists
		sequence = PySide6.QtGui.QKeySequence(key_sequence)
		if action_name in self._menu_actions:
			self._menu_actions[action_name].setShortcut(sequence)
		if action_name in self._shortcuts:
			self._shortcuts[action_name].setKey(sequence)
		# persist to preferences
		prefs = bkchem_qt.config.preferences.Preferences.instance()
		prefs.set_value(_SETTINGS_PREFIX + action_name, key_sequence)

	#============================================
	def get_binding(self, action_name: str) -> str:
		"""Get current key sequence for an action.

		Args:
			action_name: Dotted action identifier.

		Returns:
			The key sequence string, or empty string if unbound.
		"""
		return self._bindings.get(action_name, "")

	#============================================
	def reset_defaults(self) -> None:
		"""Reset all keybindings to defaults.

		Restores default bindings, updates all live shortcuts, and
		clears saved overrides from preferences.
		"""
		prefs = bkchem_qt.config.preferences.Preferences.instance()
		self._bindings = self.default_bindings()
		self._validate_bindings()
		for action_name, default_seq in self._bindings.items():
			sequence = PySide6.QtGui.QKeySequence(default_seq)
			if action_name in self._menu_actions:
				self._menu_actions[action_name].setShortcut(sequence)
			if action_name in self._shortcuts:
				self._shortcuts[action_name].setKey(sequence)
			prefs.set_value(_SETTINGS_PREFIX + action_name, default_seq)

	#============================================
	def connect_action(self, action_name: str, callback: object) -> None:
		"""Connect a callback to a named action's shortcut.

		The callback is invoked when the shortcut's key sequence is
		activated. If no shortcut exists for the action, this is a
		no-op.

		Args:
			action_name: Dotted action identifier.
			callback: Callable to invoke on shortcut activation.
		"""
		if action_name in self._shortcuts:
			self._shortcuts[action_name].activated.connect(callback)
		elif action_name in self._menu_actions:
			self._menu_actions[action_name].triggered.connect(callback)

	#============================================
	def get_all_bindings(self) -> dict:
		"""Return a copy of all current bindings.

		Returns:
			Dict mapping action names to key sequence strings.
		"""
		return dict(self._bindings)
