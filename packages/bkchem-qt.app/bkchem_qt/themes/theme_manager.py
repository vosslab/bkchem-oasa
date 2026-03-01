"""Theme manager for switching between dark and light themes."""

# PySide6 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.themes.palettes
import bkchem_qt.themes.theme_loader


#============================================
class ThemeManager(PySide6.QtCore.QObject):
	"""Manages application theme switching between dark and light modes.

	Applies QPalette and QSS stylesheet to the QApplication instance and
	emits a signal when the theme changes. Can detect the system theme
	and follow live system changes unless the user has explicitly overridden.

	Args:
		app: The QApplication instance to theme.
	"""

	# signal emitted with the new theme name after a switch
	theme_changed = PySide6.QtCore.Signal(str)

	def __init__(self, app: PySide6.QtWidgets.QApplication) -> None:
		"""Initialize the theme manager.

		Args:
			app: The QApplication instance to apply themes to.
		"""
		super().__init__(parent=app)
		self._app = app
		self._current_theme = "light"
		# tracks whether user explicitly chose a theme (overrides system)
		self._user_override = False

	#============================================
	@property
	def current_theme(self) -> str:
		"""Return the name of the currently active theme.

		Returns:
			Theme name string, either 'dark' or 'light'.
		"""
		return self._current_theme

	#============================================
	def apply_theme(self, name: str) -> None:
		"""Apply the named theme to the application.

		Sets both the QPalette and QSS stylesheet on the stored
		QApplication reference, then emits theme_changed.

		Args:
			name: Theme name, must be 'dark' or 'light'.

		Raises:
			ValueError: If name is not 'dark' or 'light'.
		"""
		if name not in ("dark", "light"):
			msg = self.tr("Unknown theme: '{0}'. Use 'dark' or 'light'.").format(name)
			raise ValueError(msg)

		# clear theme cache so YAML changes take effect
		bkchem_qt.themes.theme_loader.clear_cache()
		palette = bkchem_qt.themes.palettes.build_palette(name)
		stylesheet = bkchem_qt.themes.palettes.build_qss(name)

		# apply palette and stylesheet to the application
		self._app.setPalette(palette)
		self._app.setStyleSheet(stylesheet)
		self._current_theme = name

		# persist preference if Preferences is available
		self._save_preference(name)

		# notify listeners
		self.theme_changed.emit(name)

	#============================================
	def toggle_theme(self) -> None:
		"""Switch between dark and light themes.

		If the current theme is dark, switches to light and vice versa.
		Marks the choice as a user override so system changes are ignored.
		"""
		self._user_override = True
		if self._current_theme == "dark":
			new_theme = "light"
		else:
			new_theme = "dark"
		self.apply_theme(new_theme)

	#============================================
	def detect_system_theme(self) -> str:
		"""Detect the operating system theme preference.

		Uses Qt's styleHints().colorScheme() when available (Qt 6.5+),
		falling back to palette brightness heuristic.

		Returns:
			'dark' or 'light' based on the system setting.
		"""
		hints = self._app.styleHints()
		# Qt 6.5+ exposes colorScheme()
		if hasattr(hints, "colorScheme"):
			scheme = hints.colorScheme()
			if scheme == PySide6.QtCore.Qt.ColorScheme.Dark:
				return "dark"
			return "light"
		# fallback: check if the default window background is dark
		bg = self._app.palette().color(
			PySide6.QtWidgets.QPalette.ColorRole.Window
		)
		if bg.lightness() < 128:
			return "dark"
		return "light"

	#============================================
	def restore_theme(self) -> None:
		"""Restore the theme from saved preference or system detection.

		Checks saved preference first. If none is saved, detects the
		system theme. Connects to live system theme changes so the app
		follows the OS setting unless the user explicitly toggles.
		"""
		# check for a saved user preference
		saved_theme = None
		try:
			import bkchem_qt.config.preferences
			prefs = bkchem_qt.config.preferences.Preferences.instance()
			saved_theme = prefs.value(
				bkchem_qt.config.preferences.Preferences.KEY_THEME
			)
		except ImportError:
			pass

		if saved_theme in ("dark", "light"):
			# user had a saved preference, respect it
			self._user_override = True
			self.apply_theme(saved_theme)
		else:
			# no saved preference, follow the system
			self._user_override = False
			detected = self.detect_system_theme()
			self.apply_theme(detected)

		# connect to live system theme changes (Qt 6.5+)
		hints = self._app.styleHints()
		if hasattr(hints, "colorSchemeChanged"):
			hints.colorSchemeChanged.connect(self._on_system_theme_changed)

	#============================================
	def _on_system_theme_changed(self, scheme) -> None:
		"""Handle live system theme change from the OS.

		Only applies if the user has not explicitly overridden the theme.

		Args:
			scheme: The new Qt.ColorScheme value from the system.
		"""
		if self._user_override:
			return
		if scheme == PySide6.QtCore.Qt.ColorScheme.Dark:
			new_theme = "dark"
		else:
			new_theme = "light"
		self.apply_theme(new_theme)

	#============================================
	def _save_preference(self, name: str) -> None:
		"""Persist the theme preference if the Preferences module is available.

		Args:
			name: Theme name to save.
		"""
		try:
			import bkchem_qt.config.preferences
			prefs = bkchem_qt.config.preferences.Preferences.instance()
			prefs.set_value(bkchem_qt.config.preferences.Preferences.KEY_THEME, name)
		except ImportError:
			# preferences module not available, skip persistence
			pass
