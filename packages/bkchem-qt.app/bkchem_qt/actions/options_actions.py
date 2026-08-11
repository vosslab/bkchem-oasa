"""Options menu action registrations for BKChem-Qt."""

# Standard Library
import logging

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.config.drawing_standard_preferences
import bkchem_qt.config.preferences
import bkchem_qt.dialogs.drawing_standard_dialog
import bkchem_qt.models.document_session
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
def _active_drawing_standard_session(app: object) -> object | None:
	"""Return the synchronized active session behind every public window alias."""
	session = getattr(app, "_active_session", None)
	document = getattr(app, "document", None)
	scene = getattr(app, "scene", None)
	view = getattr(app, "view", None)
	sessions = getattr(app, "sessions", ())
	if not isinstance(sessions, (list, tuple)):
		return None
	if session is None or document is None or scene is None or view is None:
		return None
	if session.is_disposed or session not in sessions:
		return None
	if session.document is not document or session.scene is not scene or session.view is not view:
		return None
	return session


#============================================
def _can_edit_drawing_standard(app: object) -> bool:
	"""Return whether the active tab can accept one authoritative style patch."""
	session = _active_drawing_standard_session(app)
	return bool(session is not None and session.can_commit_persistent_action)


#============================================
def _edit_drawing_standard(app: object) -> None:
	"""Apply accepted defaults, overrides, and personal preference intent."""
	session = _active_drawing_standard_session(app)
	if session is None or not session.can_commit_persistent_action:
		app.statusBar().showMessage("Document Drawing Style is unavailable", 3000)
		return
	snapshot = session.backend_snapshot
	try:
		submit = app.persistent_operation_capability_for(session)
		observation = session.drawing_standard()
		selected_root_keys = (
			bkchem_qt.canvas.document_projection.selected_top_level_transform_keys(
				session.document, session.scene,
			)
		)
		personal_exists = (
			bkchem_qt.config.drawing_standard_preferences.has_personal_drawing_standard(
				app._prefs,
			)
		)
	except (RuntimeError, ValueError):
		app.statusBar().showMessage("Document Drawing Style is unavailable", 3000)
		return
	dialog = bkchem_qt.dialogs.drawing_standard_dialog.DrawingStandardDialog(
		observation, app,
		selected_root_count=len(selected_root_keys),
		personal_default_exists=personal_exists,
	)
	if dialog.exec() != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
		return
	changes = dialog.changes()
	values = dialog.values()
	apply_scope = dialog.application_scope()
	override_fields = dialog.override_fields()
	personal_action = dialog.personal_action()
	if _active_drawing_standard_session(app) is not session:
		app.statusBar().showMessage(
			"Document Drawing Style no longer applies to this tab", 3000,
		)
		return
	if apply_scope == "selected" and not selected_root_keys:
		app.statusBar().showMessage("No eligible selected objects remain", 3000)
		return
	has_document_intent = bool(changes or override_fields)
	if not has_document_intent and personal_action == "none":
		app.statusBar().showMessage("Document drawing style is unchanged", 3000)
		return
	if has_document_intent:
		request = bkchem_qt.models.document_session.build_drawing_standard_request(
			snapshot.revision, changes, apply_scope,
			selected_root_keys if apply_scope == "selected" else (),
			override_fields,
		)
		outcome = submit(request)
		app._show_persistent_action_outcome(outcome)
		if outcome.status != "accepted":
			app._refresh_document_actions()
			return
	if personal_action == "save":
		bkchem_qt.config.drawing_standard_preferences.save_personal_drawing_standard(
			app._prefs, values,
		)
		app.statusBar().showMessage(
			"Drawing style applied; personal default saved for new documents", 5000,
		)
	elif personal_action == "remove":
		bkchem_qt.config.drawing_standard_preferences.remove_personal_drawing_standard(
			app._prefs,
		)
		app.statusBar().showMessage(
			"Saved personal drawing default removed", 5000,
		)
	app._refresh_document_actions()


#============================================
def register_options_actions(registry: object, app: object) -> None:
	"""Register all Options menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	registry.register(MenuAction(
		id='options.standard',
		label_key='Document Drawing Style...',
		help_key='Set document defaults or apply drawing style to selected or all objects',
		accelerator=None,
		handler=lambda: _edit_drawing_standard(app),
		enabled_when=lambda: _can_edit_drawing_standard(app),
	))

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
