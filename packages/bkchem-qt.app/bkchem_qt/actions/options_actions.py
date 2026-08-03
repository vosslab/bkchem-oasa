"""Options menu action registrations for BKChem-Qt."""

# Standard Library
import logging

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.config.preferences
from bkchem_qt.actions.action_registry import MenuAction


#============================================
# UI labels are deliberately separate from the Python logging constants.  The
# preference is a BKChem application setting, not a serialized CDML property.
_LOGGING_LEVELS = {
	"Errors only": logging.ERROR,
	"Warnings": logging.WARNING,
	"Info": logging.INFO,
	"Debug": logging.DEBUG,
}


#============================================
def apply_saved_logging_level(
		prefs: bkchem_qt.config.preferences.Preferences,
		) -> str:
	"""Apply the persisted BKChem logging level and return its label."""
	chosen = str(prefs.value(
		bkchem_qt.config.preferences.Preferences.KEY_LOGGING_LEVEL,
		"Warnings",
	))
	if chosen not in _LOGGING_LEVELS:
		chosen = "Warnings"
	logging.getLogger().setLevel(_LOGGING_LEVELS[chosen])
	return chosen


#============================================
def _show_logging_dialog(app: object) -> None:
	"""Show a dialog for selecting the logging verbosity level.

	Stores the chosen level in Preferences under
	``general/logging_level`` and applies it immediately.

	Args:
		app: The main BKChem-Qt application window.
	"""
	prefs = app._prefs
	levels = list(_LOGGING_LEVELS)

	stored = str(prefs.value(
		bkchem_qt.config.preferences.Preferences.KEY_LOGGING_LEVEL,
		"Warnings",
	))
	current_idx = 0
	if stored in levels:
		current_idx = levels.index(stored)

	chosen, accepted = PySide6.QtWidgets.QInputDialog.getItem(
		app, "Logging Level", "Select logging level:", levels,
		current_idx, False,
	)
	if not accepted:
		return

	prefs.set_value(
		bkchem_qt.config.preferences.Preferences.KEY_LOGGING_LEVEL, chosen,
	)
	apply_saved_logging_level(prefs)
	app.statusBar().showMessage(
		f"Logging level set to {chosen} for this and future BKChem launches", 5000
	)


#============================================
def register_options_actions(registry: object, app: object) -> None:
	"""Register all Options menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# Set the delivered application's own Python logging verbosity.
	registry.register(MenuAction(
		id='options.logging',
		label_key='Logging Level...',
		help_key='Set BKChem logging verbosity now and for future launches',
		accelerator=None,
		handler=lambda: _show_logging_dialog(app),
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
