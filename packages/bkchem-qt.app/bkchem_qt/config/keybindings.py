"""Keyboard shortcut management for BKChem-Qt."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.config.preferences

# Default keybindings: action_name -> key sequence string
DEFAULT_KEYBINDINGS = {
	"file.new": "Ctrl+N",
	"file.open": "Ctrl+O",
	"file.save": "Ctrl+S",
	"file.save_as": "Ctrl+Shift+S",
	"file.export_svg": "",
	"file.export_png": "",
	"file.export_pdf": "",
	"file.quit": "Ctrl+Q",
	"edit.undo": "Ctrl+Z",
	"edit.redo": "Ctrl+Shift+Z",
	"edit.cut": "Ctrl+X",
	"edit.copy": "Ctrl+C",
	"edit.paste": "Ctrl+V",
	"edit.select_all": "Ctrl+A",
	"edit.delete": "Delete",
	"view.zoom_in": "Ctrl+=",
	"view.zoom_out": "Ctrl+-",
	"view.reset_zoom": "Ctrl+0",
	"view.toggle_grid": "Ctrl+G",
	"view.toggle_theme": "",
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


#============================================
class KeybindingManager(PySide6.QtCore.QObject):
	"""Manages keyboard shortcuts and allows customization.

	Loads keybindings from preferences on startup. Each action name
	maps to a QShortcut on the main window. Bindings can be changed
	at runtime and persisted back to preferences.

	Args:
		main_window: The QMainWindow that owns the shortcuts.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, main_window, parent=None):
		"""Initialize the keybinding manager.

		Args:
			main_window: The QMainWindow that owns the shortcuts.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._main_window = main_window
		self._shortcuts = {}
		self._bindings = dict(DEFAULT_KEYBINDINGS)
		# load saved bindings from preferences, overriding defaults
		self._load_from_preferences()

	#============================================
	def _load_from_preferences(self) -> None:
		"""Load saved keybindings from QSettings, overriding defaults."""
		prefs = bkchem_qt.config.preferences.Preferences.instance()
		for action_name in self._bindings:
			key = _SETTINGS_PREFIX + action_name
			saved = prefs.value(key)
			if saved is not None and isinstance(saved, str):
				self._bindings[action_name] = saved

	#============================================
	def setup_shortcuts(self) -> None:
		"""Create QShortcut objects for all bindings.

		Removes any existing shortcuts and creates fresh ones from the
		current bindings dict. Shortcuts with empty key sequences are
		created but remain inactive.
		"""
		# remove old shortcuts
		for shortcut in self._shortcuts.values():
			shortcut.setEnabled(False)
			shortcut.deleteLater()
		self._shortcuts.clear()
		# create new shortcuts
		for action_name, key_seq_str in self._bindings.items():
			shortcut = PySide6.QtWidgets.QShortcut(self._main_window)
			if key_seq_str:
				shortcut.setKey(PySide6.QtGui.QKeySequence(key_seq_str))
			shortcut.setContext(
				PySide6.QtCore.Qt.ShortcutContext.ApplicationShortcut
			)
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
		self._bindings[action_name] = key_sequence
		# update the live shortcut if it exists
		if action_name in self._shortcuts:
			self._shortcuts[action_name].setKey(
				PySide6.QtGui.QKeySequence(key_sequence)
			)
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
		for action_name, default_seq in DEFAULT_KEYBINDINGS.items():
			self._bindings[action_name] = default_seq
			# update live shortcut
			if action_name in self._shortcuts:
				self._shortcuts[action_name].setKey(
					PySide6.QtGui.QKeySequence(default_seq)
				)
			# clear saved override
			prefs.set_value(_SETTINGS_PREFIX + action_name, default_seq)

	#============================================
	def connect_action(self, action_name: str, callback) -> None:
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

	#============================================
	def get_all_bindings(self) -> dict:
		"""Return a copy of all current bindings.

		Returns:
			Dict mapping action names to key sequence strings.
		"""
		return dict(self._bindings)
