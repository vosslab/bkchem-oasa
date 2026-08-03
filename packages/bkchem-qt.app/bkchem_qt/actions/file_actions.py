"""File menu actions for BKChem-Qt."""

# Standard Library
import os

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.bridge.worker
import bkchem_qt.canvas.molecule_projection
import bkchem_qt.config.geometry_units
import bkchem_qt.config.preferences
import bkchem_qt.dialogs.paper_properties_dialog
import bkchem_qt.io.import_capabilities
import bkchem_qt.models.document_session
import bkchem_qt.undo.commands
from bkchem_qt.actions.action_registry import MenuAction

# maximum number of entries in the recent files list
MAX_RECENT_FILES = 10

# file filter strings for QFileDialog
CDML_FILTER = "BKChem CDML (*.cdml);;All Files (*)"
CHEMISTRY_FILTER = bkchem_qt.io.import_capabilities.chemistry_file_filter()

# map file extensions to OASA codec names for non-CDML formats
_EXTENSION_TO_CODEC = {
	extension: capability.codec_name
	for capability in bkchem_qt.io.import_capabilities.worker_import_capabilities()
	for extension in capability.extensions
}


#============================================
class _ImportResultRelay(PySide6.QtCore.QObject):
	"""Deliver one worker's result through slots owned by the GUI thread."""

	#============================================
	def __init__(
			self, main_window: object, worker: PySide6.QtCore.QThread,
			file_path: str, on_loaded: object = None,
			should_deliver: object = None, worker_owner: object = None,
			on_error: object = None,
			) -> None:
		"""Retain request data until the worker's native thread finishes."""
		super().__init__(main_window)
		self._main_window = main_window
		self._worker = worker
		self._file_path = file_path
		self._on_loaded = on_loaded
		self._should_deliver = should_deliver
		# A DocumentSession owns work started for it.  Retain the MainWindow
		# fallback for callers that predate sessions.
		self._worker_owner = worker_owner
		self._on_error = on_error

	#============================================
	def _request_is_current(self) -> bool:
		"""Return whether this worker may still update the window."""
		return (
			not callable(self._should_deliver)
			or bool(self._should_deliver())
		)

	#============================================
	@PySide6.QtCore.Slot(object)
	def on_result(self, result: object) -> None:
		"""Deliver a current worker result through its typed public boundary."""
		if not self._request_is_current():
			return
		if type(result) is bkchem_qt.bridge.worker.PreparedCompleteCDML:
			if callable(self._on_loaded):
				self._on_loaded(result)
				return
			failure = TypeError(
				"Complete CDML imports require a session-aware delivery",
			)
			if callable(self._on_error):
				self._on_error(failure)
				return
			self.on_error(failure)
			return
		if result is None:
			if callable(self._on_error):
				self._on_error("No molecules found")
				return
			self._main_window.statusBar().showMessage(
				"No molecules found", 3000,
			)
			return
		failure = TypeError(
			"File imports must return PreparedCompleteCDML or None",
		)
		if callable(self._on_error):
			self._on_error(failure)
			return
		self.on_error(failure)

	#============================================
	@PySide6.QtCore.Slot(object)
	def on_error(self, message: object) -> None:
		"""Show a current import error in the GUI thread."""
		if not self._request_is_current():
			return
		if callable(self._on_error):
			self._on_error(message)
			return
		PySide6.QtWidgets.QMessageBox.warning(
			self._main_window, "File Read Error", str(message),
		)

	#============================================
	@PySide6.QtCore.Slot()
	def on_thread_finished(self) -> None:
		"""Release through a terminal-safe window owner when available."""
		release = getattr(self._main_window, "_release_import_worker", None)
		if not callable(release):
			owner = self._worker_owner or self._main_window
			release = getattr(owner, "release_import_worker", None)
			if not callable(release):
				release = getattr(owner, "_release_import_worker", None)
		if callable(release):
			release(self._worker)
		elif getattr(self._main_window, "_active_worker", None) is self._worker:
			self._main_window._active_worker = None
		self.deleteLater()


#============================================
def push_recent_file(file_path: str) -> list:
	"""Add a file path to the recent files list in preferences.

	Moves the path to the front if it already exists, and caps
	the list at MAX_RECENT_FILES entries. Returns the updated list
	so callers can refresh menus immediately.

	Args:
		file_path: Absolute path to the file to record.

	Returns:
		The updated recent files list (most recent first).
	"""
	prefs = bkchem_qt.config.preferences.Preferences.instance()
	recent = prefs.value(
		bkchem_qt.config.preferences.Preferences.KEY_RECENT_FILES
	)
	# QSettings may return a string for single-item lists
	if recent is None:
		recent = []
	elif isinstance(recent, str):
		recent = [recent] if recent else []
	else:
		recent = list(recent)
	# normalise to absolute path for consistent dedup
	abs_path = os.path.abspath(file_path)
	# remove existing entry (dedup) before inserting at the front
	recent = [p for p in recent if p != abs_path]
	recent.insert(0, abs_path)
	# cap the list length
	recent = recent[:MAX_RECENT_FILES]
	prefs.set_value(
		bkchem_qt.config.preferences.Preferences.KEY_RECENT_FILES,
		recent,
	)
	return recent


#============================================
def open_file(main_window: object) -> None:
	"""Show a file dialog and load the selected chemistry file.

	Prompts the user with a native file dialog filtered to supported
	chemistry formats. On selection, delegates to ``open_file_path()``
	to parse and display the file.

	Args:
		main_window: MainWindow instance providing scene and document.
	"""
	file_path, _selected_filter = PySide6.QtWidgets.QFileDialog.getOpenFileName(
		main_window,
		"Open Chemistry File",
		"",
		CHEMISTRY_FILTER,
	)
	if not file_path:
		return
	open_file_path(main_window, file_path)


#============================================
def import_capability(
		main_window: object,
		capability: bkchem_qt.io.import_capabilities.ImportCapability,
		) -> None:
	"""Choose one advertised external format and use the common loader.

	The action deliberately delegates to ``open_file_path`` rather than
	starting a worker itself, so MainWindow remains the owner of the session,
	request token, and worker lifetime.
	"""
	if capability.route != "worker":
		raise ValueError(
			"File > Import only accepts worker-backed formats, got '%s'."
			% capability.codec_name
		)
	file_path, _selected_filter = PySide6.QtWidgets.QFileDialog.getOpenFileName(
		main_window,
		"Import %s" % capability.label,
		"",
		bkchem_qt.io.import_capabilities.capability_file_filter(capability),
	)
	if file_path:
		open_file_path(main_window, file_path)


#============================================
def open_file_path(main_window: object, file_path: str) -> None:
	"""Delegate a specific path to the session-aware document loader.

	MainWindow owns the full-document CDML envelope, tab lifecycle, and
	async import requests.  This action helper must not parse files itself:
	the legacy molecule-only CDML loader loses presentation objects and
	document metadata.

	Args:
		main_window: Session-aware MainWindow or same-tab replacement host.
		file_path: Absolute or relative path to the file to load.
	"""
	open_handler = getattr(main_window, "open_file_path", None)
	if callable(open_handler):
		open_handler(file_path)
		return
	replace_handler = getattr(main_window, "_open_path_replacing_current", None)
	if callable(replace_handler):
		replace_handler(file_path)
		return
	raise TypeError(
		"File actions require a session-aware host with open_file_path() "
		"or _open_path_replacing_current()."
	)


#============================================
def _load_with_worker(
	main_window: object, codec_name: str, file_path: str,
	on_loaded: object = None,
	should_deliver: object = None, worker_owner: object = None,
	on_error: object = None,
) -> None:
	"""Load a non-CDML file asynchronously using FileImportWorker.

	Runs parsing, coordinate generation, and strict complete-CDML preparation in
	a background thread. On completion, its immutable prepared-CDML result is
	installed through the originating session.

	Args:
		main_window: MainWindow instance.
		codec_name: OASA codec name (e.g. 'molfile', 'smiles').
		file_path: Path to the chemistry file.
		on_loaded: Optional callback receiving prepared complete CDML.
		should_deliver: Optional callback that rejects a stale request.
		worker_owner: Optional session-like owner providing
			``track_import_worker`` and ``release_import_worker``.
		on_error: Optional GUI-thread callback receiving an import error.
	"""
	worker = bkchem_qt.bridge.worker.FileImportWorker(codec_name, file_path)
	_start_prepared_import_worker(
		main_window,
		worker,
		file_path,
		on_loaded=on_loaded,
		should_deliver=should_deliver,
		worker_owner=worker_owner,
		on_error=on_error,
	)


#============================================
def _start_prepared_import_worker(
		main_window: object, worker: PySide6.QtCore.QThread,
		source_label: str, on_loaded: object = None,
		should_deliver: object = None, worker_owner: object = None,
		on_error: object = None,
		) -> None:
	"""Start one prepared-import worker with the common GUI-thread relay.

	Both path imports and interactive text imports use this helper so request
	tokens, session worker retention, queued delivery, and cleanup stay one
	contract.  ``source_label`` is only user-facing context for the relay.

	Args:
		main_window: MainWindow providing status and the QObject relay parent.
		worker: Started-once worker that produces prepared complete CDML.
		source_label: Human-readable source identity for default delivery.
		on_loaded: Optional GUI-thread callback receiving prepared complete CDML.
		should_deliver: Optional session/token liveness predicate.
		worker_owner: Optional session-like owner retaining the worker.
		on_error: Optional GUI-thread callback receiving an error message.
	"""
	relay = _ImportResultRelay(
		main_window,
		worker,
		source_label,
		on_loaded=on_loaded,
		should_deliver=should_deliver,
		worker_owner=worker_owner,
		on_error=on_error,
	)
	# Keep the Python wrapper reachable until both queued slots and the native
	# thread completion have been delivered.
	worker._result_relay = relay
	connection_type = PySide6.QtCore.Qt.ConnectionType.QueuedConnection
	worker.result.connect(relay.on_result, connection_type)
	worker.error.connect(relay.on_error, connection_type)
	worker.finished.connect(relay.on_thread_finished, connection_type)
	owner = worker_owner or main_window
	track = getattr(owner, "track_import_worker", None)
	if not callable(track):
		track = getattr(owner, "_track_import_worker", None)
	if callable(track):
		track(worker)
	else:
		# Compatibility for simple hosts outside MainWindow.
		main_window._active_worker = worker
	main_window.statusBar().showMessage("Loading %s..." % source_label, 0)
	worker.start()


#============================================
def _record_recent_file(main_window: object, file_path: str) -> None:
	"""Push a file path to recent files and refresh the submenu.

	Args:
		main_window: MainWindow instance with ``refresh_recent_files_menu``.
		file_path: Path to the file just opened or saved.
	"""
	push_recent_file(file_path)
	# ask the main window to rebuild the Recent files submenu
	refresh = getattr(main_window, "refresh_recent_files_menu", None)
	if callable(refresh):
		refresh()


#============================================
def _add_molecules_to_scene(
		main_window: object, molecules: list, undoable: bool = True,
		*, session: object = None, document: object = None,
		scene: object = None,
		) -> None:
	"""Add a list of MoleculeModel objects to the active scene.

	For each molecule, creates AtomItem and BondItem graphics items,
	then stores the molecule and scene projection as an undo command.
	File loading may opt out because the loaded state is a clean baseline.
	Bond items are added before atom items so that atoms render on top.

	Args:
		main_window: MainWindow instance with ``_scene`` and optionally
			a ``_document`` attribute. Retained as the compatibility target.
		molecules: List of MoleculeModel instances to display.
		undoable: Whether insertion belongs on the document undo stack.
		session: Optional DocumentSession target. Its document and scene are
			used unless explicitly supplied.
		document: Optional explicit Document target.
		scene: Optional explicit QGraphicsScene target.
	"""
	if session is not None:
		if scene is None:
			scene = session.scene
		if document is None:
			document = session.document
	if scene is None:
		scene = main_window._scene
	if document is None:
		document = getattr(main_window, "_document", None)
	projections = bkchem_qt.canvas.molecule_projection.build_molecule_projections(
		molecules,
	)

	if document is None:
		bkchem_qt.canvas.molecule_projection.install_molecule_projections(
			scene, projections,
		)
		return

	if undoable:
		if len(projections) > 1:
			document.undo_stack.beginMacro("Add Molecules")
		for mol_model, graphics_items in projections:
			document.undo_stack.push(
				bkchem_qt.undo.commands.AddMoleculeCommand(
					document,
					scene,
					mol_model,
					graphics_items,
				)
			)
		if len(projections) > 1:
			document.undo_stack.endMacro()
		return

	for mol_model, graphics_items in projections:
		document.add_molecule(mol_model, mark_dirty=False)
		for item in graphics_items:
			scene.addItem(item)

#============================================
#============================================
def _load_same_tab(app: object) -> None:
	"""Open a file replacing the current tab contents.

	Delegates to MainWindow's parse-before-replace lifecycle.

	Args:
		app: MainWindow instance.
	"""
	app._on_open_same_tab()


#============================================
def _active_paper_properties_session(app: object) -> object | None:
	"""Return the one registered active session that owns every live alias."""
	session = getattr(app, "_active_session", None)
	document = getattr(app, "document", None)
	scene = getattr(app, "scene", None)
	view = getattr(app, "view", None)
	sessions = getattr(app, "sessions", ())
	if session is None or document is None or scene is None or view is None:
		return None
	if session.is_disposed or session not in sessions:
		return None
	if (
			session.document is not document
			or session.scene is not scene
			or session.view is not view
		):
		return None
	return session


#============================================
def _paper_properties_request(
		expected_revision: int, changes: tuple[tuple[str, object], ...],
		) -> object:
	"""Build one explicit-field backend patch request from dialog intent."""
	return bkchem_qt.models.document_session.build_paper_properties_request(
		expected_revision, changes,
	)


#============================================
def _document_properties(app: object) -> None:
	"""Commit accepted document paper scalars through the active backend session."""
	session = _active_paper_properties_session(app)
	if session is None or not session.can_commit_persistent_action:
		app.statusBar().showMessage("Document Properties is unavailable", 3000)
		return
	snapshot = session.backend_snapshot
	try:
		submit = app.persistent_operation_capability_for(session)
	except ValueError:
		app.statusBar().showMessage("Document Properties is unavailable", 3000)
		return
	context = session.paper_properties_context()
	attributes = context["attributes"]
	default_type = context["default_type"]
	default_orientation = context["default_orientation"]
	if (
		not isinstance(attributes, dict)
		or not isinstance(default_type, str)
		or not isinstance(default_orientation, str)
	):
		app.statusBar().showMessage("Document Properties is unavailable", 3000)
		return
	dialog = bkchem_qt.dialogs.paper_properties_dialog.PaperPropertiesDialog(
		attributes, session.paper_catalog(), default_type, default_orientation, app,
	)
	if dialog.exec() != PySide6.QtWidgets.QDialog.DialogCode.Accepted:
		return
	changes = dialog.changes()
	if _active_paper_properties_session(app) is not session:
		app.statusBar().showMessage("Document Properties no longer applies to this tab", 3000)
		return
	request = _paper_properties_request(snapshot.revision, changes)
	outcome = submit(request)
	app._show_persistent_action_outcome(outcome)
	app._refresh_document_actions()


#============================================
def register_file_actions(registry: object, app: object) -> None:
	"""Register all File menu actions for BKChem-Qt.

	Maps each file action to the appropriate Qt handler method on the
	main window. Actions without a Qt implementation use a stub lambda
	that shows a status bar message.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# create a new file in a new document tab
	registry.register(MenuAction(
		id='file.new',
		label_key='New',
		help_key='Create a new file',
		accelerator='(C-n)',
		handler=app._on_new,
		enabled_when=None,
	))
	# save the current file
	registry.register(MenuAction(
		id='file.save',
		label_key='Save',
		help_key='Save the file',
		accelerator='(C-s)',
		handler=app._on_save,
		enabled_when=app.can_save_authoritatively,
	))
	# save under a different name
	registry.register(MenuAction(
		id='file.save_as',
		label_key='Save As...',
		help_key='Save the file under a different name',
		accelerator='(C-S-s)',
		handler=app._on_save_as,
		enabled_when=app.can_save_authoritatively,
	))
	# export the authoritative backend snapshot without changing session state
	registry.register(MenuAction(
		id='file.recovery_export',
		label_key='Recovery Export Backend CDML...',
		help_key='Export the current backend snapshot without saving the document',
		accelerator=None,
		handler=app._on_recovery_export,
		enabled_when=app.can_recovery_export,
	))
	# save as a template file
	registry.register(MenuAction(
		id='file.save_as_template',
		label_key='Save As Template',
		help_key='Export the current backend CDML snapshot as a template',
		accelerator=None,
		handler=app.save_as_template,
		enabled_when=app.can_save_as_template,
	))
	# refresh the frontend-owned saved user-template catalog
	registry.register(MenuAction(
		id='file.refresh_user_templates',
		label_key='Refresh User Templates',
		help_key='Rescan the configured user template directory',
		accelerator=None,
		handler=app.refresh_user_templates,
		enabled_when=app.can_refresh_user_templates,
	))
	# open a file in a new tab
	registry.register(MenuAction(
		id='file.load',
		label_key='Open',
		help_key='Open a file',
		accelerator='(C-o)',
		handler=app._on_open,
		enabled_when=None,
	))
	# open a file replacing the current tab
	registry.register(MenuAction(
		id='file.load_same_tab',
		label_key='Open in same tab',
		help_key='Open a file replacing the current one',
		accelerator=None,
		handler=lambda: _load_same_tab(app),
		enabled_when=None,
	))
	# document properties dialog
	registry.register(MenuAction(
		id='file.properties',
		label_key='Document Properties...',
		help_key='Set the paper size and other properties of the document',
		accelerator=None,
		handler=lambda: _document_properties(app),
		enabled_when=None,
	))
	# close the current tab
	registry.register(MenuAction(
		id='file.close_tab',
		label_key='Close tab',
		help_key='Close the current tab, exit when there is only one tab',
		accelerator='(C-w)',
		handler=lambda: app.close_current_tab(),
		enabled_when=None,
	))
	# exit the application
	registry.register(MenuAction(
		id='file.exit',
		label_key='Quit',
		help_key='Quit BKChem',
		accelerator='(C-q)',
		handler=app.close,
		enabled_when=None,
	))
