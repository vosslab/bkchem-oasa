"""User preferences backed by QSettings for BKChem-Qt."""

# PIP3 modules
import PySide6.QtCore


#============================================
class Preferences:
	"""Singleton wrapper around QSettings for application preferences.

	Access the shared instance via ``Preferences.instance()``.  All reads
	fall back to sensible defaults defined in ``DEFAULTS`` when a key has
	not been explicitly stored.

	Example::

		prefs = Preferences.instance()
		theme = prefs.value(Preferences.KEY_THEME)
		prefs.set_value(Preferences.KEY_ZOOM_LEVEL, 150.0)
	"""

	# -- singleton storage --
	_instance: "Preferences" = None

	# -- settings key constants --
	KEY_WINDOW_GEOMETRY: str = "window/geometry"
	KEY_WINDOW_STATE: str = "window/state"
	KEY_THEME: str = "appearance/theme"
	KEY_GRID_VISIBLE: str = "appearance/grid_visible"
	KEY_RECENT_FILES: str = "files/recent"
	KEY_ZOOM_LEVEL: str = "view/zoom_level"

	# -- default values for every key --
	DEFAULTS: dict = {
		KEY_WINDOW_GEOMETRY: None,
		KEY_WINDOW_STATE: None,
		KEY_THEME: "dark",
		KEY_GRID_VISIBLE: True,
		KEY_RECENT_FILES: [],
		KEY_ZOOM_LEVEL: 100.0,
	}

	#============================================
	def __init__(self):
		"""Create the QSettings backend.

		Callers should use ``Preferences.instance()`` instead of
		constructing directly.
		"""
		self._settings = PySide6.QtCore.QSettings("BKChem", "BKChem-Qt")

	#============================================
	@classmethod
	def instance(cls) -> "Preferences":
		"""Return the shared Preferences singleton.

		Creates the instance on first call.

		Returns:
			The single Preferences instance for the application.
		"""
		if cls._instance is None:
			cls._instance = cls()
		return cls._instance

	#============================================
	def value(self, key: str, default=None):
		"""Read a preference value.

		Lookup order:
		1. Explicit *default* argument (when not None).
		2. Entry in ``DEFAULTS`` for the given key.
		3. None.

		Args:
			key: Settings key string (use the KEY_* class constants).
			default: Optional override for the fallback value.

		Returns:
			The stored value, or the resolved default.
		"""
		if default is None:
			default = self.DEFAULTS.get(key)
		stored = self._settings.value(key, default)
		return stored

	#============================================
	def set_value(self, key: str, val) -> None:
		"""Store a preference value and sync to disk.

		Args:
			key: Settings key string (use the KEY_* class constants).
			val: Value to persist.
		"""
		self._settings.setValue(key, val)
		self._settings.sync()
