"""Main application window for BKChem-Qt."""

# Standard Library
import dataclasses
import functools
import os
import pathlib
import enum

# PIP3 modules
import yaml
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.config.geometry_units
import bkchem_qt.config.keybindings
import bkchem_qt.config.preferences
import bkchem_qt.widgets.status_bar
import bkchem_qt.widgets.zoom_controls
import bkchem_qt.widgets.icon_loader
import bkchem_qt.setup.canvas_setup
import bkchem_qt.setup.mode_setup
import bkchem_qt.setup.toolbar_setup
import bkchem_qt.actions.file_actions
import bkchem_qt.actions.options_actions
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.graphics_retirement
import bkchem_qt.canvas.molecule_projection
import bkchem_qt.io.clipboard_manager
import bkchem_qt.io.import_capabilities
import bkchem_qt.io.user_template_catalog
import bkchem_qt.bridge.user_template_inspection
import bkchem_qt.dialogs.about_dialog
import bkchem_qt.dialogs.preferences_dialog
import bkchem_qt.dialogs.theme_chooser_dialog
import bkchem_qt.models.document
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.io.export
import bkchem_qt.themes.theme_loader
import bkchem_qt.undo.commands
import bkchem_qt.resource_paths


#============================================
@dataclasses.dataclass
class _PendingSessionDeletion:
	"""Long-lived Qt roots and detached graphics retained during terminal close."""

	wrappers: list[object]
	retained_graphics_records: object = None
	session_destroyed: bool = False

	#============================================
	@property
	def retained_detached_graphics(self) -> object:
		"""Expose detached roots for existing focused lifecycle assertions."""
		if self.retained_graphics_records is None:
			return None
		return self.retained_graphics_records.detached


class ShutdownState(enum.StrEnum):
	"""Public MainWindow shutdown lifecycle for Qt behavior tests and hosts."""

	LIVE = "live"
	DRAINING = "draining"
	READY = "ready"


#============================================
class MainWindow(PySide6.QtWidgets.QMainWindow):
	"""Main application window with menus, canvas, toolbar, and status bar.

	Args:
		theme_manager: ThemeManager instance for toggling themes.
	"""

	worker_retirement_drained = PySide6.QtCore.Signal()

	#============================================
	def __init__(self, theme_manager: object,
			parent: PySide6.QtWidgets.QWidget | None = None, *,
			user_template_directory: str | pathlib.Path | None = None) -> None:
		"""Initialize the main window with all UI components.

		Args:
			theme_manager: ThemeManager instance for theme toggling.
			parent: Optional parent widget.
			user_template_directory: Explicit frontend-owned directory used for
				discovering saved user templates, or None for an empty embedded catalog.
		"""
		super().__init__(parent)
		self._theme_manager = theme_manager
		self._prefs = bkchem_qt.config.preferences.Preferences.instance()
		bkchem_qt.actions.options_actions.apply_saved_logging_level(self._prefs)
		self._shutdown_prepared = False
		self._shutdown_state = ShutdownState.LIVE
		self._ui_signals_connected = False
		# The active document has four window-owned callbacks.  Keep their
		# ownership as explicit state so a projection preparation failure can
		# detach and restore the same document without asking Qt to disconnect
		# callbacks that were never installed.
		self._document_signal_source = None
		self._tab_change_blocked = False
		self._sessions = []
		self._sessions_by_view = {}
		self._pending_session_deletions = {}
		# A destroyed-session callback retries retained terminal graphics once.
		# A transient native failure gets one further ordinary event-loop retry;
		# persistent failures remain explicitly retained for shutdown diagnostics
		# instead of scheduling an unbounded zero-delay loop.
		self._pending_session_graphics_retry_scheduled = False
		self._retired_import_workers = set()
		self._shutdown_sessions_pending_disposal = []
		self._initial_view_framing_scheduled = False
		self._active_session = None
		self._user_template_directory = (
			pathlib.Path(user_template_directory)
			if user_template_directory is not None else None
		)
		self._user_template_catalog = self._scan_user_template_catalog()
		self._clipboard_manager = bkchem_qt.io.clipboard_manager.ClipboardManager()
		self._clipboard = PySide6.QtWidgets.QApplication.clipboard()

		self.setWindowTitle(self.tr("BKChem-Qt"))
		style = PySide6.QtWidgets.QApplication.style()
		window_icon = style.standardIcon(
			PySide6.QtWidgets.QStyle.StandardPixmap.SP_FileIcon
		)
		if not window_icon.isNull():
			app = PySide6.QtWidgets.QApplication.instance()
			if app is not None:
				app.setWindowIcon(window_icon)
			self.setWindowIcon(window_icon)
		self.resize(1280, 800)

		# build the UI components
		self._setup_canvas()
		self._setup_mode_system()
		self._setup_menus()
		self._setup_toolbars()
		self._setup_status_bar()
		self._connect_signals()
		self._apply_geometry_preferences()
		self._apply_view_preferences()
		self._show_user_template_catalog_status(self._user_template_catalog)

	#============================================
	def showEvent(self, event: PySide6.QtGui.QShowEvent) -> None:
		"""Frame the active document after the first real window layout."""
		super().showEvent(event)
		if self._initial_view_framing_scheduled:
			return
		self._initial_view_framing_scheduled = True
		self._schedule_initial_view_framing(self._active_session)

	#============================================
	def _schedule_initial_view_framing(
			self, session: bkchem_qt.models.document_session.DocumentSession | None,
			) -> None:
		"""Queue one page fit after Qt has laid out a new tab."""
		if session is None or session.is_disposed:
			return
		PySide6.QtCore.QTimer.singleShot(
			0, functools.partial(self._frame_session_for_first_use, session),
		)

	#============================================
	def _frame_session_for_first_use(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Make a new tab's complete drawable page immediately visible."""
		if (
			self._shutdown_prepared or not self.isVisible()
			or session.is_disposed or session not in self._sessions
		):
			return
		session.view.zoom_to_fit()

	#============================================
	@property
	def user_template_catalog(self) -> bkchem_qt.io.user_template_catalog.UserTemplateCatalogSnapshot:
		"""Return the immutable frontend-owned saved-template catalog snapshot."""
		return self._user_template_catalog

	#============================================
	def _scan_user_template_catalog(
			self,
			) -> bkchem_qt.io.user_template_catalog.UserTemplateCatalogSnapshot:
		"""Return one immutable scan of the explicitly configured directory."""
		if self._user_template_directory is None:
			return bkchem_qt.io.user_template_catalog.UserTemplateCatalogSnapshot((), ())
		return bkchem_qt.io.user_template_catalog.scan_user_template_catalog(
			self._user_template_directory,
		)

	#============================================
	def _show_user_template_catalog_status(
			self,
			snapshot: bkchem_qt.io.user_template_catalog.UserTemplateCatalogSnapshot,
			) -> None:
		"""Present one concise catalog outcome without hiding admitted neighbors."""
		if self._user_template_directory is None:
			self.statusBar().showMessage(self.tr("User template directory is not configured"), 3000)
			return
		if not snapshot.failures:
			self.statusBar().showMessage(
				self.tr("User templates refreshed: %d available") % len(snapshot.entries), 3000,
			)
			return
		first_failure = snapshot.failures[0]
		self.statusBar().showMessage(
			self.tr("User templates refreshed: %d available; skipped %s: %s") % (
				len(snapshot.entries), first_failure.source_name, first_failure.message,
			),
			5000,
		)

	#============================================
	def rescan_user_templates(
			self,
			) -> bkchem_qt.io.user_template_catalog.UserTemplateCatalogSnapshot:
		"""Replace the delivered saved-template catalog in every live session."""
		snapshot = self._scan_user_template_catalog()
		for session in tuple(self._sessions):
			if not session.is_disposed:
				session.replace_user_template_catalog(snapshot.entries)
		self._user_template_catalog = snapshot
		if self._active_mode_name() == "usertemplate":
			self._on_mode_changed("usertemplate")
		self._show_user_template_catalog_status(snapshot)
		return snapshot

	#============================================
	def refresh_user_templates(
			self,
			) -> bkchem_qt.io.user_template_catalog.UserTemplateCatalogSnapshot:
		"""Refresh saved templates through the visible File-action behavior."""
		return self._on_refresh_user_templates()

	#============================================
	def _on_refresh_user_templates(
			self,
			) -> bkchem_qt.io.user_template_catalog.UserTemplateCatalogSnapshot:
		"""Run one explicit catalog refresh and present all recoverable skips."""
		snapshot = self.rescan_user_templates()
		if snapshot.failures:
			details = "\n".join(
				"%s: %s" % (failure.source_name, failure.message)
				for failure in snapshot.failures
			)
			PySide6.QtWidgets.QMessageBox.information(
				self,
				self.tr("User Template Refresh"),
				self.tr("Some user templates were skipped.\n\n%s") % details,
			)
		return snapshot

	#============================================
	@property
	def shutdown_state(self) -> ShutdownState:
		"""Return the observable application retirement state."""
		return self._shutdown_state

	#============================================
	@property
	def retiring_worker_count(self) -> int:
		"""Return the number of adopted workers still awaiting ``finished``."""
		return len(self._retired_import_workers)

	#============================================
	@property
	def document(self) -> bkchem_qt.models.document.Document:
		"""The active document."""
		return self._document

	#============================================
	@property
	def scene(self) -> PySide6.QtWidgets.QGraphicsScene:
		"""The active graphics scene."""
		return self._scene

	#============================================
	@property
	def view(self) -> PySide6.QtWidgets.QGraphicsView:
		"""The active graphics view."""
		return self._view

	#============================================
	@property
	def sessions(self) -> list:
		"""Return the open document sessions in tab order."""
		return list(self._sessions)

	#============================================
	def persistent_operation_capability_for(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> object:
		"""Freeze a non-mode operation capability onto one exact registered tab."""
		if not isinstance(session, bkchem_qt.models.document_session.DocumentSession):
			raise TypeError("Persistent operation capability requires a DocumentSession")
		if session.is_disposed or session not in self._sessions:
			raise ValueError("Persistent operation capability requires a live registered session")
		def submit(
				request: bkchem_qt.models.document_session.PersistentOperationRequest,
				) -> bkchem_qt.models.document_session.PersistentActionOutcome:
			"""Submit only while the captured session remains live and registered."""
			if (
				not isinstance(
					request, bkchem_qt.models.document_session.PersistentOperationRequest,
				)
			):
				raise TypeError("Persistent operations require PersistentOperationRequest")
			if session.is_disposed or session not in self._sessions:
				return bkchem_qt.models.document_session.PersistentActionOutcome(
					"unavailable", "Document cannot accept a persistent edit", None, False,
				)
			return session.submit_persistent_operation(request)
		return submit

	#============================================
	def bond_properties_capability_for(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> object:
		"""Freeze one narrow direct-bond patch capability onto a registered tab."""
		if not isinstance(session, bkchem_qt.models.document_session.DocumentSession):
			raise TypeError("Bond properties capability requires a DocumentSession")
		if session.is_disposed or session not in self._sessions:
			raise ValueError("Bond properties capability requires a live registered session")
		def submit(
				expected_revision: int, molecule_id: str, bond_id: str,
				changes: tuple[tuple[str, object], ...],
				) -> bkchem_qt.models.document_session.PersistentActionOutcome:
			"""Submit only while the exact captured session remains registered."""
			if session.is_disposed or session not in self._sessions:
				return bkchem_qt.models.document_session.PersistentActionOutcome(
					"unavailable", "Document cannot accept a persistent edit", None, False,
				)
			return session.submit_bond_properties_patch(
				expected_revision, molecule_id, bond_id, changes,
			)
		return submit

	#============================================
	def bond_properties_capability_for_view(self, view: object) -> object | None:
		"""Return one frozen bond-patch capability for this registered view.

		Interaction surfaces provide the view that owned their selected item.  The
		window resolves that view once, so a dialog or retained callback cannot be
		redirected merely because another tab later becomes active.
		"""
		session = self._sessions_by_view.get(view)
		if session is None or session.is_disposed:
			return None
		return self.bond_properties_capability_for(session)

	#============================================
	def capture_bond_properties_for_view(
			self, view: object, molecule_id: str, bond_id: str,
			) -> tuple[int, object] | None:
		"""Capture one revision and exact-tab bond patch callback for one intent."""
		session = self._sessions_by_view.get(view)
		return self.capture_bond_properties_for(session, molecule_id, bond_id)

	#============================================
	def capture_bond_properties_for(
			self, session: object, molecule_id: str, bond_id: str,
			) -> tuple[int, object] | None:
		"""Capture one revision and callback for a known registered bond session."""
		if (
			not isinstance(session, bkchem_qt.models.document_session.DocumentSession)
			or session.is_disposed or session not in self._sessions
			or session.document is None or not session.can_commit_persistent_action
			or not isinstance(molecule_id, str) or not molecule_id
			or not isinstance(bond_id, str) or not bond_id
		):
			return None
		return session.backend_snapshot.revision, self.bond_properties_capability_for(session)

	#============================================
	def atom_properties_capability_for(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> object:
		"""Freeze one narrow direct-atom patch capability onto a registered tab."""
		if not isinstance(session, bkchem_qt.models.document_session.DocumentSession):
			raise TypeError("Atom properties capability requires a DocumentSession")
		if session.is_disposed or session not in self._sessions:
			raise ValueError("Atom properties capability requires a live registered session")
		def submit(
				expected_revision: int, molecule_id: str, atom_id: str,
				changes: tuple[tuple[str, object], ...],
				) -> bkchem_qt.models.document_session.PersistentActionOutcome:
			"""Submit only while the exact captured session remains registered."""
			if session.is_disposed or session not in self._sessions:
				return bkchem_qt.models.document_session.PersistentActionOutcome(
					"unavailable", "Document cannot accept a persistent edit", None, False,
				)
			return session.submit_atom_properties_patch(
				expected_revision, molecule_id, atom_id, changes,
			)
		return submit

	#============================================
	def atom_properties_capability_for_view(self, view: object) -> object | None:
		"""Return one frozen atom-patch capability for this registered view."""
		session = self._sessions_by_view.get(view)
		if session is None or session.is_disposed:
			return None
		return self.atom_properties_capability_for(session)

	#============================================
	def capture_atom_properties_for_view(
			self, view: object, molecule_id: str, atom_id: str,
			) -> tuple[int, object] | None:
		"""Capture one revision and exact-tab atom patch callback for one intent."""
		session = self._sessions_by_view.get(view)
		return self.capture_atom_properties_for(session, molecule_id, atom_id)

	#============================================
	def capture_atom_properties_for(
			self, session: object, molecule_id: str, atom_id: str,
			) -> tuple[int, object] | None:
		"""Capture one revision and callback for a known registered atom session."""
		if (
			not isinstance(session, bkchem_qt.models.document_session.DocumentSession)
			or session.is_disposed or session not in self._sessions
			or session.document is None or not session.can_commit_persistent_action
			or not isinstance(molecule_id, str) or not molecule_id
			or not isinstance(atom_id, str) or not atom_id
		):
			return None
		return session.backend_snapshot.revision, self.atom_properties_capability_for(session)

	#============================================
	def text_properties_capability_for(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> object:
		"""Freeze one narrow direct-root plain Text patch onto a registered tab."""
		if not isinstance(session, bkchem_qt.models.document_session.DocumentSession):
			raise TypeError("Text properties capability requires a DocumentSession")
		if session.is_disposed or session not in self._sessions:
			raise ValueError("Text properties capability requires a live registered session")
		def submit(
				expected_revision: int, text_id: str,
				changes: tuple[tuple[str, object], ...],
				) -> bkchem_qt.models.document_session.PersistentActionOutcome:
			"""Submit only while the exact captured session remains registered."""
			if session.is_disposed or session not in self._sessions:
				return bkchem_qt.models.document_session.PersistentActionOutcome(
					"unavailable", "Document cannot accept a persistent edit", None, False,
				)
			return session.submit_text_properties_patch(
				expected_revision, text_id, changes,
			)
		return submit

	#============================================
	def rich_text_capability_for(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> object:
		"""Freeze one authored rich-Text patch capability onto a registered tab."""
		if not isinstance(session, bkchem_qt.models.document_session.DocumentSession):
			raise TypeError("Rich Text capability requires a DocumentSession")
		if session.is_disposed or session not in self._sessions:
			raise ValueError("Rich Text capability requires a live registered session")
		def submit(
				expected_revision: int, text_id: str,
			runs: tuple[tuple[str, tuple[str, ...]], ...],
			changes: tuple[tuple[str, object], ...] = (),
				) -> bkchem_qt.models.document_session.PersistentActionOutcome:
			"""Submit only while the exact captured session remains registered."""
			if session.is_disposed or session not in self._sessions:
				return bkchem_qt.models.document_session.PersistentActionOutcome(
					"unavailable", "Document cannot accept a persistent edit", None, False,
				)
			return session.submit_rich_text_patch(expected_revision, text_id, runs, changes)
		return submit

	#============================================
	def capture_rich_text_for_view(
			self, view: object, text_id: str,
			) -> tuple[int, object] | None:
		"""Capture one revision and exact-tab rich Text callback for one dialog."""
		session = self._sessions_by_view.get(view)
		if (
			session is None or session.is_disposed or session.document is None
			or not session.can_commit_persistent_action
			or not isinstance(text_id, str) or not text_id
		):
			return None
		return session.backend_snapshot.revision, self.rich_text_capability_for(session)

	#============================================
	def capture_text_properties_for_view(
			self, view: object, text_id: str,
			) -> tuple[int, object] | None:
		"""Capture one revision and exact-tab Text patch callback for one intent."""
		session = self._sessions_by_view.get(view)
		if (
			session is None or session.is_disposed or session.document is None
			or not session.can_commit_persistent_action
			or not isinstance(text_id, str) or not text_id
		):
			return None
		return session.backend_snapshot.revision, self.text_properties_capability_for(session)

	#============================================
	def plus_properties_capability_for(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> object:
		"""Freeze one narrow direct-root plain Plus patch onto a registered tab."""
		if not isinstance(session, bkchem_qt.models.document_session.DocumentSession):
			raise TypeError("Plus properties capability requires a DocumentSession")
		if session.is_disposed or session not in self._sessions:
			raise ValueError("Plus properties capability requires a live registered session")
		def submit(
				expected_revision: int, plus_id: str,
				changes: tuple[tuple[str, object], ...],
				) -> bkchem_qt.models.document_session.PersistentActionOutcome:
			"""Submit only while the exact captured session remains registered."""
			if session.is_disposed or session not in self._sessions:
				return bkchem_qt.models.document_session.PersistentActionOutcome(
					"unavailable", "Document cannot accept a persistent edit", None, False,
				)
			return session.submit_plus_properties_patch(
				expected_revision, plus_id, changes,
			)
		return submit

	#============================================
	def capture_plus_properties_for_view(
			self, view: object, plus_id: str,
			) -> tuple[int, object] | None:
		"""Capture one revision and exact-tab Plus patch callback for one intent."""
		session = self._sessions_by_view.get(view)
		if (
			session is None or session.is_disposed or session.document is None
			or not session.can_commit_persistent_action
			or not isinstance(plus_id, str) or not plus_id
		):
			return None
		return session.backend_snapshot.revision, self.plus_properties_capability_for(session)

	#============================================
	def wavy_properties_capability_for(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> object:
		"""Freeze one narrow direct-root plain Wavy patch onto a registered tab."""
		if not isinstance(session, bkchem_qt.models.document_session.DocumentSession):
			raise TypeError("Wavy properties capability requires a DocumentSession")
		if session.is_disposed or session not in self._sessions:
			raise ValueError("Wavy properties capability requires a live registered session")
		def submit(
				expected_revision: int, wavy_id: str,
				changes: tuple[tuple[str, object], ...],
				) -> bkchem_qt.models.document_session.PersistentActionOutcome:
			"""Submit only while the exact captured session remains registered."""
			if session.is_disposed or session not in self._sessions:
				return bkchem_qt.models.document_session.PersistentActionOutcome(
					"unavailable", "Document cannot accept a persistent edit", None, False,
				)
			return session.submit_wavy_properties_patch(
				expected_revision, wavy_id, changes,
			)
		return submit

	#============================================
	def capture_wavy_properties_for_view(
			self, view: object, wavy_id: str,
			) -> tuple[int, object] | None:
		"""Capture one revision and exact-tab Wavy patch callback for one intent."""
		session = self._sessions_by_view.get(view)
		if (
			session is None or session.is_disposed or session.document is None
			or not session.can_commit_persistent_action
			or not isinstance(wavy_id, str) or not wavy_id
		):
			return None
		return session.backend_snapshot.revision, self.wavy_properties_capability_for(session)

	#============================================
	def _bind_property_dock(
			self,
			session: bkchem_qt.models.document_session.DocumentSession | None,
			) -> None:
		"""Bind the dock to one live projection and its exact session callbacks.

		This is the sole MainWindow binding seam for the disposable projection:
		all dock callbacks close over the supplied session rather than active
		window aliases, so tab activation and recovery cannot redirect an edit.
		"""
		if not hasattr(self, "_property_dock"):
			return
		if (
			session is None or session.is_disposed or session not in self._sessions
			or session.document is None
		):
			self._property_dock.set_document(None)
			return
		def capture_bond(molecule_id: str, bond_id: str) -> tuple[int, object] | None:
			"""Capture one dock bond intent for the bound session."""
			return self.capture_bond_properties_for(session, molecule_id, bond_id)

		def capture_atom(molecule_id: str, atom_id: str) -> tuple[int, object] | None:
			"""Capture one dock atom intent for the bound session."""
			return self.capture_atom_properties_for(session, molecule_id, atom_id)

		self._property_dock.set_document(
			session.document,
			bond_properties_capture=capture_bond,
			atom_properties_capture=capture_atom,
		)

	#============================================
	def _setup_canvas(self) -> None:
		"""Create the tab host and its initial independent document session."""
		self._tab_widget = PySide6.QtWidgets.QTabWidget(self)
		self._tab_widget.setTabsClosable(True)
		self._tab_widget.setMovable(False)
		self.setCentralWidget(self._tab_widget)
		session = self._create_session(activate=True)
		self._set_active_session_aliases(session)

	#============================================
	def _construct_session(
			self, *,
			file_path: str | None = None, display_name: str | None = None,
			origin_path: str | None = None,
			prepared_native_cdml: (
				bkchem_qt.models.document_session.PreparedNativeCDML | None
			) = None,
			prepared_imported_cdml: (
				bkchem_qt.models.document_session.PreparedImportedCDML | None
			) = None,
			) -> bkchem_qt.models.document_session.DocumentSession:
		"""Build one detached session without changing the live tab graph."""
		return bkchem_qt.models.document_session.DocumentSession(
			parent=self,
			theme_manager=self._theme_manager,
			prefs=self._prefs,
			mode_host=self,
			view_parent=self,
			file_path=file_path,
			display_name=display_name,
			origin_path=origin_path,
			prepared_native_cdml=prepared_native_cdml,
			prepared_imported_cdml=prepared_imported_cdml,
			user_template_catalog=self._user_template_catalog.entries,
		)

	#============================================
	def _register_session(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			*, index: int | None = None, activate: bool = True,
			) -> bkchem_qt.models.document_session.DocumentSession:
		"""Register one viable detached session without disturbing another tab."""
		if session.is_disposed or session in self._sessions:
			raise ValueError("Session must be live and unregistered")
		if session.view in self._sessions_by_view:
			raise ValueError("Session view is already registered")
		if index is None:
			index = self._tab_widget.count()
		if index < 0 or index > len(self._sessions):
			raise IndexError("Session insertion index is out of range")
		previous_session = self._active_session
		previous_index = self._tab_widget.currentIndex()
		title_connected = False
		previous_block = self._tab_widget.blockSignals(True)
		previous_tab_change_blocked = self._tab_change_blocked
		self._tab_change_blocked = True
		try:
			self._sessions.insert(index, session)
			self._sessions_by_view[session.view] = session
			self._tab_widget.insertTab(index, session.view, session.title)
			session.title_changed.connect(self._on_session_title_changed)
			title_connected = True
			if activate:
				self._tab_widget.setCurrentIndex(index)
				if self._active_session is not session:
					self._activate_session(session)
			else:
				current_mode = session.mode_manager.current_mode
				if current_mode is not None:
					current_mode.deactivate()
		except Exception:
			self._unregister_session_without_disposal(session, title_connected)
			if previous_session is not None and previous_session in self._sessions:
				self._restore_active_session(previous_session, previous_index)
			elif self._active_session is session:
				self._clear_active_session_aliases()
			self._dispose_session_later(session)
			raise
		finally:
			self._tab_change_blocked = previous_tab_change_blocked
			self._tab_widget.blockSignals(previous_block)
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session,
				lambda snapshot: self._replace_session_projection(session, snapshot),
				self._consume_session_projection_notice,
			),
		)
		if session is self._active_session and hasattr(self, "_undo_action"):
			self._refresh_document_actions()
		if self.isVisible():
			self._schedule_initial_view_framing(session)
		return session
	#============================================
	def _consume_session_projection_notice(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			result: bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult,
			) -> None:
		"""Refresh only the emitting active session's disposable UI aliases."""
		if session.is_disposed or session not in self._sessions:
			return
		if session is not self._active_session:
			return
		self._set_active_session_aliases(session)
		self._refresh_active_session_controls()

	#============================================
	def _create_session(
			self, index: int | None = None, activate: bool = True,
			display_name: str | None = None, origin_path: str | None = None,
			) -> bkchem_qt.models.document_session.DocumentSession:
		"""Create, register, and optionally activate one tab session."""
		session = self._construct_session(
			display_name=display_name,
			origin_path=origin_path,
		)
		return self._register_session(session, index=index, activate=activate)

	#============================================
	def _set_active_session_aliases(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Point compatibility aliases at exactly one active session."""
		self._active_session = session
		self._document = session.document
		self._scene = session.scene
		self._view = session.view
		self._mode_manager = session.mode_manager

	#============================================
	def _clear_active_session_aliases(self) -> None:
		"""Clear compatibility aliases while no live session is active."""
		self._active_session = None
		self._document = None
		self._scene = None
		self._view = None
		self._mode_manager = None

	#============================================
	def _replace_session_projection(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			snapshot: object,
			) -> bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult:
		"""Rebuild one registered Qt projection from an accepted backend snapshot.

		The session, tab, scene, view, modes, and workers remain in place.  Only
		the document-owned graphics and models are replaced after the exact current
		backend snapshot has prepared successfully.
		"""
		if session.is_disposed or session not in self._sessions:
			return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.SESSION_UNAVAILABLE,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.SESSION,
			)
		active = session is self._active_session
		old_document = session.document
		if active:
			if self._ui_signals_connected and old_document is not None:
				self._disconnect_document_signals(old_document)
			self._bind_property_dock(None)
		try:
			replaced = session.replace_projection_from_backend_snapshot(snapshot)
		except Exception:
			if active and old_document is not None and session.document is old_document:
				if self._ui_signals_connected:
					self._connect_document_signals(old_document)
				self._bind_property_dock(session)
			elif active and session.document is None:
				self._set_active_session_aliases(session)
				current_mode = session.mode_manager.current_mode
				if current_mode is not None:
					current_mode.deactivate()
				self._bind_property_dock(None)
			raise
		if active:
			self._set_active_session_aliases(session)
			if replaced.installed and self._ui_signals_connected and session.document is not None:
				self._connect_document_signals(session.document)
			if replaced.installed:
				self._bind_property_dock(session)
			else:
				self._bind_property_dock(None)
				if session.document is None:
					current_mode = session.mode_manager.current_mode
					if current_mode is not None:
						current_mode.deactivate()
		return replaced

	#============================================
	def _setup_mode_system(self) -> None:
		"""Expose the active session's already-owned mode manager."""
		self._mode_manager = self._active_session.mode_manager

	#============================================
	def _setup_menus(self) -> None:
		"""Create the menu bar from YAML menu structure and action registry."""
		from bkchem_qt.actions.action_registry import register_all_actions
		from bkchem_qt.actions.platform_menu import PlatformMenuAdapter
		from bkchem_qt.actions.menu_builder import (
			MenuBuilder,
			preflight_required_menu_actions,
		)
		# register all per-menu action modules
		self._registry = register_all_actions(self)
		# create the Qt menu adapter wrapping QMenuBar
		self._adapter = PlatformMenuAdapter(self)
		# Load the menu definition installed with the Qt package.
		yaml_path = str(bkchem_qt.resource_paths.get_resource_path("menus.yaml"))
		preflight_required_menu_actions(self._registry, yaml_path)
		# build all menus from YAML structure
		self._menu_builder = MenuBuilder(
			yaml_path, self._registry, self._adapter,
		)
		self._menu_builder.build_menus()
		# The Import cascade is driven by the same capability registry as the
		# file chooser and extension router.  Each action delegates to the
		# session-aware loader instead of starting an independent worker.
		for capability in (
				bkchem_qt.io.import_capabilities.worker_import_capabilities()
		):
			self._adapter.add_command_to_cascade(
				"Import",
				self.tr("Import %s..." % capability.label),
				self.tr("Import %s" % capability.description),
				lambda _checked=False, capability=capability: (
					bkchem_qt.actions.file_actions.import_capability(
						self, capability,
					)
				),
				action_key="file.import.%s" % capability.codec_name,
			)
		# populate the Export cascade with export handlers
		export_cascade_label = "Export"
		self._adapter.add_command_to_cascade(
			export_cascade_label, "Export SVG...",
			"Export the current document as SVG",
			self._on_export_svg,
			action_key="file.export_svg",
		)
		self._adapter.add_command_to_cascade(
			export_cascade_label, "Export PNG...",
			"Export the current document as PNG",
			self._on_export_png,
			action_key="file.export_png",
		)
		self._adapter.add_command_to_cascade(
			export_cascade_label, "Export PDF...",
			"Export the current document as PDF",
			self._on_export_pdf,
			action_key="file.export_pdf",
		)
		# retrieve QActions by frozen English key for later enable/disable
		self._action_save = self._adapter.get_action_by_key("file.save")
		self._action_open = self._adapter.get_action_by_key("file.load")
		self._action_new = self._adapter.get_action_by_key("file.new")
		self._action_exit = self._adapter.get_action_by_key("file.exit")
		self._action_undo = self._adapter.get_action_by_key("edit.undo")
		self._action_redo = self._adapter.get_action_by_key("edit.redo")
		self._action_toggle_theme = self._adapter.get_action_by_key(
			"options.theme"
		)
		self._action_about = self._adapter.get_action_by_key("help.about")
		# grid toggle is not in menus.yaml (it is a view feature)
		# create it as a standalone checkable action
		view_menu = self._adapter.get_menu_component("View")
		if view_menu is not None:
			self._adapter.add_separator("View")
			self._action_toggle_grid = self._adapter.add_direct_action(
				"View", self.tr("Toggle &Grid"), "view.toggle_grid",
			)
			self._action_toggle_grid.setCheckable(True)
			self._action_toggle_grid.setChecked(self._scene.grid_visible)
			self._action_toggle_grid.triggered.connect(self._on_toggle_grid)
			self._action_toggle_grid_snap = self._adapter.add_direct_action(
				"View", self.tr("Snap To &Grid"), "view.toggle_grid_snap",
			)
			self._action_toggle_grid_snap.setCheckable(True)
			self._action_toggle_grid_snap.setChecked(
				self._scene.grid_snap_enabled
			)
			self._action_toggle_grid_snap.setShortcut(
				PySide6.QtGui.QKeySequence(self.tr("Shift+Ctrl+G"))
			)
			self._action_toggle_grid_snap.triggered.connect(
				self._on_toggle_grid_snap
			)
		# populate the Recent files cascade from stored preferences
		self.refresh_recent_files_menu()
		# Install one shortcut authority after every menu and direct action exists.
		# Its callbacks resolve the active document session when invoked.
		self._keybinding_manager = bkchem_qt.config.keybindings.KeybindingManager(
			self, self._registry, parent=self,
		)
		self._keybinding_manager.setup_shortcuts()

	#============================================
	def _setup_toolbars(self) -> None:
		"""Create the mode toolbar, submode ribbon, edit ribbon, and docks."""
		widgets = bkchem_qt.setup.toolbar_setup.setup_toolbars(
			self, self._mode_manager, self._document, self._theme_manager,
		)
		self._mode_toolbar = widgets["mode_toolbar"]
		self._submode_ribbon = widgets["submode_ribbon"]
		self._submode_toolbar = widgets["submode_toolbar"]
		self._edit_ribbon = widgets["edit_ribbon"]
		self._edit_ribbon_toolbar = widgets["edit_ribbon_toolbar"]
		self._property_dock = widgets["property_dock"]
		self._undo_action = widgets["undo_action"]
		self._redo_action = widgets["redo_action"]

	#============================================
	def _setup_status_bar(self) -> None:
		"""Create and install the status bar with zoom controls."""
		self._status_bar = bkchem_qt.widgets.status_bar.StatusBar(self)
		self.setStatusBar(self._status_bar)
		# add zoom controls as a permanent widget on the right
		self._zoom_controls = bkchem_qt.widgets.zoom_controls.ZoomControls(self)
		self._status_bar.addPermanentWidget(self._zoom_controls)

	#============================================
	def _connect_signals(self) -> None:
		"""Wire all signals between components."""
		self._tab_widget.currentChanged.connect(self._on_tab_changed)
		self._tab_widget.tabCloseRequested.connect(
			self._on_tab_close_requested
		)

		# Global controls resolve the active session at invocation time.
		self._mode_toolbar.mode_selected.connect(self._on_mode_selected)

		# submode ribbon -> active mode submode selection
		self._submode_ribbon.submode_selected.connect(
			self._on_submode_selected
		)

		# edit ribbon -> draw mode
		self._edit_ribbon.element_changed.connect(self._on_element_changed)
		self._edit_ribbon.bond_order_changed.connect(self._on_bond_order_changed)
		self._edit_ribbon.bond_type_changed.connect(self._on_bond_type_changed)

		# theme changes -> icon refresh and menu text update
		self._theme_manager.theme_changed.connect(self._on_theme_changed)

		# zoom controls -> handler methods
		self._zoom_controls.zoom_in_clicked.connect(self.on_zoom_in)
		self._zoom_controls.zoom_out_clicked.connect(self.on_zoom_out)
		self._zoom_controls.reset_zoom_clicked.connect(self.on_reset_zoom)
		self._zoom_controls.zoom_to_fit_clicked.connect(self.on_zoom_to_fit)
		self._zoom_controls.zoom_to_content_clicked.connect(
			self.on_zoom_to_content
		)
		self._zoom_controls.zoom_slider_changed.connect(
			self._on_zoom_slider_changed
		)
		self._clipboard.dataChanged.connect(self._on_clipboard_data_changed)

		self._ui_signals_connected = True
		self._connect_active_session_signals(self._active_session)
		self._refresh_document_actions()

		# trigger initial mode visibility (submode ribbon + edit ribbon)
		self._synchronize_active_session_ui()

	#============================================
	@PySide6.QtCore.Slot()
	def _on_clipboard_data_changed(self) -> None:
		"""Refresh document actions after a system clipboard transition."""
		if self._shutdown_prepared or not self._ui_signals_connected:
			return
		self._refresh_document_actions()

	#============================================
	def _connect_active_session_signals(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Connect view, mode, and document signals for the active tab only."""
		session.view.mouse_moved.connect(self._status_bar.update_coords)
		session.view.zoom_changed.connect(
			self._zoom_controls.update_zoom_display
		)
		session.mode_manager.mode_changed.connect(
			self._mode_toolbar.set_active_mode
		)
		session.mode_manager.mode_changed.connect(self._status_bar.update_mode)
		session.mode_manager.mode_changed.connect(self._on_mode_changed)
		for mode in session.mode_manager._modes.values():
			mode.status_message.connect(self._show_mode_message)
		if session.document is not None:
			self._connect_document_signals(session.document)

	#============================================
	def _disconnect_active_session_signals(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Disconnect every active-only callback before a switch or close."""
		connections = (
			(session.view.mouse_moved, self._status_bar.update_coords),
			(
				session.view.zoom_changed,
				self._zoom_controls.update_zoom_display,
			),
			(
				session.mode_manager.mode_changed,
				self._mode_toolbar.set_active_mode,
			),
			(session.mode_manager.mode_changed, self._status_bar.update_mode),
			(session.mode_manager.mode_changed, self._on_mode_changed),
		)
		for signal, slot in connections:
			try:
				signal.disconnect(slot)
			except (RuntimeError, SystemError, TypeError):
				pass
		for mode in session.mode_manager._modes.values():
			try:
				mode.status_message.disconnect(self._show_mode_message)
			except (RuntimeError, SystemError, TypeError):
				pass
		if session.document is not None:
			self._disconnect_document_signals(session.document)

	#============================================
	def _activate_session(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Switch all active-document consumers to one existing session."""
		if session.is_disposed or session not in self._sessions:
			return
		previous = self._active_session
		if not session.has_live_projection:
			if previous is session:
				self._bind_property_dock(None)
				current_mode = session.mode_manager.current_mode
				if current_mode is not None:
					current_mode.deactivate()
				self._synchronize_active_session_ui()
				return
			if previous is not None:
				if self._ui_signals_connected:
					self._disconnect_active_session_signals(previous)
				previous_mode = previous.mode_manager.current_mode
				if previous_mode is not None:
					previous_mode.deactivate()
			self._set_active_session_aliases(session)
			self._bind_property_dock(None)
			if self._ui_signals_connected:
				self._connect_active_session_signals(session)
			current_mode = session.mode_manager.current_mode
			if current_mode is not None:
				current_mode.deactivate()
			self._synchronize_active_session_ui()
			return
		if previous is session:
			if hasattr(self, "_property_dock"):
				self._synchronize_active_session_ui()
			return
		try:
			if previous is not None:
				if self._ui_signals_connected:
					self._disconnect_active_session_signals(previous)
				previous_mode = previous.mode_manager.current_mode
				if previous_mode is not None:
					previous_mode.deactivate()
			self._set_active_session_aliases(session)
			self._bind_property_dock(session)
			if self._ui_signals_connected:
				self._connect_active_session_signals(session)
				active_mode = session.mode_manager.current_mode
				if active_mode is not None:
					active_mode.activate()
				self._synchronize_active_session_ui()
		except Exception:
			if previous is not None and previous in self._sessions:
				previous_index = self._tab_widget.indexOf(previous.view)
				self._restore_active_session(previous, previous_index)
			else:
				self._clear_active_session_aliases()
			raise

	#============================================
	def _synchronize_active_session_ui(self, bind_property_dock: bool = True) -> None:
		"""Refresh controls after creating or activating a document session."""
		self._refresh_active_session_controls()
		if self._active_session is None:
			return
		if bind_property_dock:
			self._bind_property_dock(self._active_session)
		else:
			self._bind_property_dock(None)

	#============================================
	def _refresh_active_session_controls(self) -> None:
		"""Refresh active-session controls without changing dock projection ownership."""
		if self._active_session is None:
			return
		mode_name = self._active_mode_name()
		if mode_name is not None:
			self._mode_toolbar.set_active_mode(mode_name)
			self._status_bar.update_mode(mode_name)
			self._on_mode_changed(mode_name)
		self._zoom_controls.update_zoom_display(
			float(self._view.zoom_percent)
		)
		if hasattr(self, "_action_toggle_grid"):
			self._action_toggle_grid.setChecked(self._scene.grid_visible)
		if hasattr(self, "_action_toggle_grid_snap"):
			self._action_toggle_grid_snap.setChecked(
				self._scene.grid_snap_enabled
			)
		self._refresh_document_actions()

	#============================================
	def _active_mode_name(self) -> str | None:
		"""Return the registered name of the active session's current mode."""
		current_mode = self._mode_manager.current_mode
		for name in self._mode_manager.mode_names():
			if self._mode_manager._modes[name] is current_mode:
				return name
		return None

	#============================================
	@PySide6.QtCore.Slot(str)
	def _on_mode_selected(self, mode_name: str) -> None:
		"""Apply a toolbar mode selection to the active session."""
		self._mode_manager.set_mode(mode_name)

	#============================================
	@PySide6.QtCore.Slot(int)
	def _on_zoom_slider_changed(self, percent: int) -> None:
		"""Apply a zoom-slider change to the active session's view."""
		self._view.set_zoom_percent(float(percent))

	#============================================
	@PySide6.QtCore.Slot(int)
	def _on_tab_changed(self, index: int) -> None:
		"""Activate the session owning the selected tab page."""
		if self._tab_change_blocked or index < 0:
			return
		session = self._sessions_by_view.get(self._tab_widget.widget(index))
		if session is not None:
			self._activate_session(session)

	#============================================
	@PySide6.QtCore.Slot(int)
	def _on_tab_close_requested(self, index: int) -> None:
		"""Close the requested tab through its save guard."""
		self.close_session_at(index)

	#============================================
	@PySide6.QtCore.Slot(str)
	def _on_session_title_changed(self, title: str) -> None:
		"""Update the tab belonging to the session that emitted a title."""
		session = self.sender()
		if not isinstance(
			session, bkchem_qt.models.document_session.DocumentSession,
		):
			return
		index = self._tab_widget.indexOf(session.view)
		if index >= 0:
			self._tab_widget.setTabText(index, title)

	#============================================
	def _connect_document_signals(
			self, document: bkchem_qt.models.document.Document,
			) -> None:
		"""Bind window callbacks to one active document exactly once."""
		if self._document_signal_source is document:
			return
		if self._document_signal_source is not None:
			self._disconnect_document_signals(self._document_signal_source)
		document.selection_changed.connect(
			self._property_dock.update_from_selection
		)
		document.selection_changed.connect(self._update_menu_predicates)
		document.undo_stack.canUndoChanged.connect(
			self._on_document_undo_state_changed
		)
		document.undo_stack.canRedoChanged.connect(
			self._on_document_undo_state_changed
		)
		self._document_signal_source = document

	#============================================
	def _disconnect_document_signals(
			self, document: bkchem_qt.models.document.Document,
			) -> None:
		"""Release callbacks only when this window owns their binding."""
		if self._document_signal_source is not document:
			return
		connections = (
			(document.selection_changed, self._property_dock.update_from_selection),
			(document.selection_changed, self._update_menu_predicates),
			(
				document.undo_stack.canUndoChanged,
				self._on_document_undo_state_changed,
			),
			(
				document.undo_stack.canRedoChanged,
				self._on_document_undo_state_changed,
			),
		)
		try:
			for signal, slot in connections:
				signal.disconnect(slot)
		finally:
			self._document_signal_source = None

	#============================================
	def _on_document_undo_state_changed(self, _available: bool) -> None:
		"""Refresh actions after either undo availability signal changes."""
		self._refresh_document_actions()

	#============================================
	def _on_document_modified_changed(self, _dirty: bool) -> None:
		"""Refresh the active tab title after dirty-state transitions."""
		self._update_document_title()

	#============================================
	def _refresh_document_actions(self) -> None:
		"""Synchronize active-document undo/redo and menu state."""
		session = self._active_session
		if self._document is None or session is None:
			self._undo_action.setEnabled(False)
			self._redo_action.setEnabled(False)
			self._update_menu_predicates()
			return
		self._undo_action.setEnabled(self.can_undo())
		self._redo_action.setEnabled(self.can_redo())
		self._update_menu_predicates()

	#============================================
	def can_paste(self) -> bool:
		"""Return whether the active session can accept the current clipboard."""
		session = self._active_session
		return bool(
			session is not None
			and session in self._sessions
			and not session.is_disposed
			and session.can_commit_persistent_action
			and self._clipboard_manager.can_paste()
		)

	#============================================
	def can_undo(self) -> bool:
		"""Return the single active undo capability for menus and shortcuts."""
		return self._legacy_undo_capability("undo")

	#============================================
	def can_redo(self) -> bool:
		"""Return the single active redo capability for menus and shortcuts."""
		return self._legacy_undo_capability("redo")

	#============================================
	def _legacy_undo_capability(self, direction: str) -> bool:
		"""Resolve backend history first, with legacy history only when isolated."""
		session = self._active_session
		if session is None or self._document is None:
			return False
		if session.legacy_isolated:
			stack = self._document.undo_stack
			if stack is None:
				return False
			try:
				available = stack.canUndo() if direction == "undo" else stack.canRedo()
			except RuntimeError:
				return False
			return available
		if not session.has_backend_navigation:
			return False
		available = (
			session.can_undo_backend if direction == "undo"
			else session.can_redo_backend
		)
		return available

	#============================================
	def _update_document_title(self) -> None:
		"""Show the active document name and unsaved marker."""
		if self._active_session is None:
			return
		index = self._tab_widget.indexOf(self._active_session.view)
		if index >= 0:
			self._tab_widget.setTabText(index, self._active_session.title)

	# ------------------------------------------------------------------
	# Public action methods (used by menu action registrations)
	# ------------------------------------------------------------------

	#============================================
	def on_new(self) -> bool:
		"""Public wrapper for toolbar New button."""
		return self._on_new()

	#============================================
	def on_open(self) -> bool:
		"""Public wrapper for toolbar Open button."""
		return self._on_open()

	#============================================
	def on_save(self) -> bool:
		"""Public wrapper for toolbar Save button."""
		return self._on_save()

	#============================================
	def on_undo(self) -> None:
		"""Public wrapper for toolbar Undo button."""
		if self._active_session is None or self._document is None:
			return
		if self._active_session.legacy_isolated:
			self._document.undo_stack.undo()
			return
		if self._active_session.has_backend_navigation:
			if self._active_session.can_undo_backend:
				self._show_persistent_action_outcome(self._active_session.undo_backend())
			else:
				self.statusBar().showMessage("Backend undo is unavailable", 3000)
			self._refresh_document_actions()
			return
		return

	#============================================
	def on_redo(self) -> None:
		"""Public wrapper for toolbar Redo button."""
		if self._active_session is None or self._document is None:
			return
		if self._active_session.legacy_isolated:
			self._document.undo_stack.redo()
			return
		if self._active_session.has_backend_navigation:
			if self._active_session.can_redo_backend:
				self._show_persistent_action_outcome(self._active_session.redo_backend())
			else:
				self.statusBar().showMessage("Backend redo is unavailable", 3000)
			self._refresh_document_actions()
			return
		return

	#============================================
	def _show_persistent_action_outcome(
			self,
			outcome: bkchem_qt.models.document_session.PersistentActionOutcome,
			) -> None:
		"""Display one concise frontend persistent-action result."""
		self.statusBar().showMessage(outcome.message, 3000)

	#============================================
	def discard_legacy_and_retry_projection(
			self,
			session: bkchem_qt.models.document_session.DocumentSession | None = None,
			) -> bkchem_qt.models.document_session.PersistentActionOutcome | None:
		"""Confirm discarding local edits before exact backend-only reprojection."""
		target = self._active_session if session is None else session
		if (
			target is None
			or target.is_disposed
			or target not in self._sessions
			or not target.has_live_projection
			or not target.legacy_isolated
		):
			return None
		answer = PySide6.QtWidgets.QMessageBox.question(
			self,
			self.tr("Discard Qt-local edits?"),
			self.tr(
				"Discard local Qt edits and rebuild this tab from the current "
				"authoritative backend document?",
			),
			PySide6.QtWidgets.QMessageBox.StandardButton.Yes
			| PySide6.QtWidgets.QMessageBox.StandardButton.Cancel,
			PySide6.QtWidgets.QMessageBox.StandardButton.Cancel,
		)
		if answer != PySide6.QtWidgets.QMessageBox.StandardButton.Yes:
			return None
		outcome = target._discard_legacy_and_retry_projection()
		self._show_persistent_action_outcome(outcome)
		self._refresh_document_actions()
		return outcome

	#============================================
	@PySide6.QtCore.Slot(str)
	def _show_mode_message(self, message: str) -> None:
		"""Deliver a mode result to the live window status bar."""
		self.statusBar().showMessage(message, 3000)

	#============================================
	def on_cut(self) -> None:
		"""Copy one selection, then delete its durable roots when synchronized."""
		target = self._active_cut_session()
		if target is None:
			return
		if target.legacy_isolated:
			self._cut_legacy_isolated(target)
			return
		self._cut_synchronized(target)

	#============================================
	def _cut_synchronized(
			self, target: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Copy first, then submit a request frozen from one synchronized tab.

		Clipboard delivery is an application callback boundary.  This method
		captures its complete plain backend request before that boundary and
		releases every Qt projection reference before the eventual submission.
		"""
		document = target.document
		scene = target.scene
		if document is None or scene is None or not document.has_selection:
			return
		structural_targets = self._selected_cut_structural_targets(document, scene)
		if structural_targets is False:
			self.statusBar().showMessage(
				self.tr("Cut selection cannot be committed"), 3000,
			)
			return
		if structural_targets is not None:
			# Structural extraction can accept and reproject synchronously.  Its
			# immutable targets are the only projection-derived values it needs.
			del document
			del scene
			self._cut_synchronized_structure(target, structural_targets)
			return
		targets = self._selected_cut_root_targets(document, scene)
		request = None
		submit = None
		fragment_cdml = None
		if targets is not None and target.can_commit_persistent_action:
			root_ids, target_keys = targets
			try:
				submit = self.persistent_operation_capability_for(target)
			except ValueError:
				submit = None
			if submit is not None:
				revision = target.backend_snapshot.revision
				request = bkchem_qt.models.document_session.PersistentOperationRequest(
					"top-level.delete", "Cut",
					(("expected_revision", revision), ("root_ids", root_ids)), target_keys,
				)
				try:
					fragment = target.extract_top_level_fragment(
						revision, root_ids,
					)
					fragment_cdml = fragment.fragment_cdml
					del fragment
				except ValueError as exc:
					self.statusBar().showMessage(str(exc), 3000)
					return
		# Keep only session-bound callable and immutable plain request data after
		# the callback boundary.  An accepted commit can now replace this entire
		# projection without an old wrapper remaining in this stack frame.
		del document
		del scene
		del targets
		del target
		if fragment_cdml is None:
			self.statusBar().showMessage(
				self.tr("Cut selection cannot be committed"), 3000,
			)
			return
		try:
			self._clipboard_manager.publish_fragment(fragment_cdml)
		except (RuntimeError, TypeError, ValueError) as exc:
			self.statusBar().showMessage(
				self.tr("Could not copy selection; nothing was cut: %s") % exc, 3000,
			)
			return
		if submit is None or request is None:
			self.statusBar().showMessage(
				self.tr("Cut selection cannot be committed"), 3000,
			)
			self._refresh_document_actions()
			return
		# The captured capability is session-bound.  It remains attached to the
		# originating tab across tab activation, while its own liveness predicate
		# rejects disposal, stale projection, and legacy-isolation transitions.
		outcome = submit(request)
		self._show_persistent_action_outcome(outcome)
		self._refresh_document_actions()

	#============================================
	def _selected_cut_structural_targets(
			self, document: object, scene: object,
			) -> tuple[str, tuple[str, ...], tuple[str, ...]] | bool | None:
		"""Resolve an exact direct atom/bond Cut selection, or reject its mixture."""
		items = tuple(scene.selectedItems())
		if not items:
			return None
		classification = bkchem_qt.canvas.document_projection.classify_structural_selection(
			document, items,
		)
		if classification.kind is bkchem_qt.canvas.document_projection.StructuralSelectionKind.EXACT:
			return classification.targets
		if classification.kind is bkchem_qt.canvas.document_projection.StructuralSelectionKind.INVALID:
			return False
		for item in items:
			# A structural wrapper must prove membership before any native model
			# field is observed.  Unsupported marks and structural/presentation
			# mixtures are inert for this bounded partial-Cut grammar.
			if not document.is_current_projection_item(item):
				return False
			if document.molecule_for_current_projection_item(item) is not None:
				return False
		return None

	#============================================
	def _cut_synchronized_structure(
			self, target: bkchem_qt.models.document_session.DocumentSession,
			targets: tuple[str, tuple[str, ...], tuple[str, ...]],
			) -> None:
		"""Extract, publish, then delete one backend-authoritative subgraph."""
		molecule_id, atom_ids, bond_ids = targets
		if not target.can_commit_persistent_action:
			self.statusBar().showMessage(self.tr("Cut selection cannot be committed"), 3000)
			return
		revision = target.backend_snapshot.revision
		try:
			submit = self.persistent_operation_capability_for(target)
			request = bkchem_qt.models.document_session.build_structure_delete_request(
				revision, molecule_id, atom_ids, bond_ids,
			)
			fragment = target.extract_structure_fragment(
				revision, molecule_id, atom_ids, bond_ids,
			)
		except ValueError as exc:
			self.statusBar().showMessage(str(exc), 3000)
			return
		fragment_cdml = fragment.fragment_cdml
		del fragment
		del target
		try:
			self._clipboard_manager.publish_fragment(fragment_cdml)
		except (RuntimeError, TypeError, ValueError) as exc:
			self.statusBar().showMessage(
				self.tr("Could not copy selection; nothing was cut: %s") % exc, 3000,
			)
			return
		outcome = submit(request)
		self._show_persistent_action_outcome(outcome)
		self._refresh_document_actions()

	#============================================
	def _cut_legacy_isolated(
			self, target: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Run legacy Cut only after its isolated projection proves unchanged."""
		document = target.document
		if document is None or not document.has_selection:
			return
		selected_object_ids = tuple(
			id(object_model) for object_model in document.selected_top_level_objects
		)
		if not selected_object_ids:
			return
		document_identity = id(document)
		persistent_generation = document.persistent_generation
		try:
			count = self._clipboard_manager.copy_selection(document)
		except ValueError as exc:
			self.statusBar().showMessage(str(exc), 3000)
			return
		del document
		if count == 0:
			self.statusBar().showMessage(
				self.tr("Could not copy selection; nothing was cut"), 3000,
			)
			return
		current = self._active_cut_session()
		if (
			current is not target
			or not current.legacy_isolated
			or current.document is None
			or id(current.document) != document_identity
			or current.document.persistent_generation != persistent_generation
			or tuple(
				id(object_model)
				for object_model in current.document.selected_top_level_objects
			) != selected_object_ids
		):
			self.statusBar().showMessage(
				self.tr("Cut no longer applies to this document"), 3000,
			)
			self._refresh_document_actions()
			return
		self._remove_top_level_objects(current.document.selected_top_level_objects)
		self.statusBar().showMessage(self.tr("Cut %d object(s)") % count, 3000)

	#============================================
	def _active_cut_session(self) -> bkchem_qt.models.document_session.DocumentSession | None:
		"""Return the exact live session represented by current Cut aliases."""
		target = self._active_session
		if (
			target is None
			or target.is_disposed
			or target not in self._sessions
			or target.document is not self._document
			or target.scene is not self._scene
			or target.view is not self._view
		):
			return None
		return target

	#============================================
	def _selected_cut_root_targets(
			self, document: object, scene: object,
			) -> tuple[tuple[str, ...], frozenset[tuple[str, str]]] | None:
		"""Capture durable direct roots from one current selected projection.

		This frontend-only bridge resolves atom, bond, and mark hits to their
		owning molecule before producing plain immutable root IDs for OASA.
		Every selected graphics item must prove current document ownership so a
		foreign, stale, unsupported, or ID-less wrapper cannot downgrade a
		synchronized Cut into a local mutation.
		"""
		selected_items = tuple(scene.selectedItems())
		objects = tuple(document.selected_top_level_objects)
		if not selected_items or not objects:
			return None
		selected_model_ids = {id(object_model) for object_model in objects}
		for item in selected_items:
			# Atom, bond, and mark projections may also expose their child model as
			# ``document_object_model``.  Their owning molecule takes precedence;
			# only otherwise-unowned items are presentation-root candidates.
			if not document.is_current_projection_item(item):
				return None
			molecule = document.molecule_for_current_projection_item(item)
			if molecule is not None:
				if id(molecule) not in selected_model_ids:
					return None
				continue
			model = getattr(item, "document_object_model", None)
			if model is not None:
				if (
					id(model) not in selected_model_ids
					or model not in document.presentation_objects
					or not getattr(model, "supported", False)
					or not bkchem_qt.canvas.document_projection.is_bound_presentation_projection(
						item, model,
					)
				):
					return None
				continue
			if model is None:
				return None
		root_ids = []
		target_keys = set()
		for object_model in objects:
			molecule_id = getattr(object_model, "mol_id", "")
			if molecule_id:
				if object_model not in document.molecules:
					return None
				root_ids.append(molecule_id)
				target_keys.add(("molecule", molecule_id))
				continue
			object_id = getattr(object_model, "object_id", "")
			if (
				object_model not in document.presentation_objects
				or not getattr(object_model, "supported", False)
				or not isinstance(object_id, str)
				or not object_id
			):
				return None
			root_ids.append(object_id)
			target_keys.add(("presentation", object_id))
		if len(root_ids) != len(set(root_ids)):
			return None
		return tuple(root_ids), frozenset(target_keys)

	#============================================
	def on_copy(self) -> None:
		"""Copy an exact structural selection or existing selected top-level roots."""
		target = self._active_cut_session()
		if target is not None and not target.legacy_isolated:
			document = target.document
			scene = target.scene
			if document is not None and scene is not None and document.has_selection:
				classification = bkchem_qt.canvas.document_projection.classify_structural_selection(
					document, tuple(scene.selectedItems()),
				)
				if classification.kind is bkchem_qt.canvas.document_projection.StructuralSelectionKind.EXACT:
					targets = classification.targets
					fragment_cdml = self._extract_synchronized_structure_fragment(target, targets)
					del document
					del scene
					del classification
					del targets
					del target
					if fragment_cdml is not None:
						self._publish_structural_copy_fragment(fragment_cdml)
					return
				if classification.kind is bkchem_qt.canvas.document_projection.StructuralSelectionKind.INVALID:
					self.statusBar().showMessage(self.tr("Copy selection cannot be copied"), 3000)
					return
				del classification
				root_targets = self._selected_cut_root_targets(document, scene)
				if root_targets is None:
					self.statusBar().showMessage(self.tr("Copy selection cannot be copied"), 3000)
					return
				root_ids, _target_keys = root_targets
				revision = target.backend_snapshot.revision
				try:
					fragment = target.extract_top_level_fragment(revision, root_ids)
				except ValueError as exc:
					self.statusBar().showMessage(str(exc), 3000)
					return
				fragment_cdml = fragment.fragment_cdml
				del fragment
				del root_targets
				del root_ids
				del _target_keys
				del revision
				del document
				del scene
				del target
				self._publish_synchronized_top_level_fragment(fragment_cdml)
				return
			del document
			del scene
		# The native clipboard can synchronously invoke application callbacks.  Both
		# synchronized root/mixed Copy and legacy-isolated whole-root Copy reach the
		# shared publication path below, so neither may retain its origin session.
		if target is not None:
			del target
		try:
			count = self._clipboard_manager.copy_selection(self._document)
		except ValueError as exc:
			self.statusBar().showMessage(str(exc), 3000)
			return
		if count == 0:
			self.statusBar().showMessage(
				self.tr("Nothing selected to copy"), 3000,
			)
			return
		self.statusBar().showMessage(
			self.tr("Copied %d object(s)") % count, 3000,
		)

	#============================================
	def _publish_synchronized_top_level_fragment(self, fragment_cdml: str) -> None:
		"""Publish OASA-owned direct-root CDML after wrappers leave scope."""
		try:
			self._clipboard_manager.publish_fragment(fragment_cdml)
		except (RuntimeError, TypeError, ValueError) as exc:
			self.statusBar().showMessage(
				self.tr("Could not copy selection: %s") % exc, 3000,
			)
			return
		self.statusBar().showMessage(self.tr("Copied selection"), 3000)

	#============================================
	def _extract_synchronized_structure_fragment(
			self, target: bkchem_qt.models.document_session.DocumentSession,
			targets: tuple[str, tuple[str, ...], tuple[str, ...]] | None,
			) -> str | None:
		"""Extract one read-only authoritative fragment before native publication."""
		if targets is None:
			return None
		molecule_id, atom_ids, bond_ids = targets
		revision = target.backend_snapshot.revision
		try:
			fragment = target.extract_structure_fragment(
				revision, molecule_id, atom_ids, bond_ids,
			)
		except ValueError as exc:
			self.statusBar().showMessage(str(exc), 3000)
			return None
		fragment_cdml = fragment.fragment_cdml
		del fragment
		return fragment_cdml

	#============================================
	def _publish_structural_copy_fragment(self, fragment_cdml: str) -> None:
		"""Publish raw structural CDML after all origin projection state is gone."""
		try:
			self._clipboard_manager.publish_fragment(fragment_cdml)
		except (RuntimeError, TypeError, ValueError) as exc:
			self.statusBar().showMessage(
				self.tr("Could not copy selection: %s") % exc, 3000,
			)
			return
		self.statusBar().showMessage(self.tr("Copied 1 object(s)"), 3000)

	#============================================
	def on_paste(self) -> None:
		"""Submit one raw clipboard fragment to the captured document session."""
		target = self._active_session
		if (
			target is None
			or target.is_disposed
			or target not in self._sessions
			or not target.can_commit_persistent_action
		):
			self.statusBar().showMessage(
				self.tr("Document cannot accept a persistent edit"), 3000,
			)
			self._refresh_document_actions()
			return
		status, fragment_cdml = self._clipboard_manager.read_fragment()
		if status == "no_data":
			self.statusBar().showMessage(
				self.tr("No CDML data on clipboard"), 3000,
			)
			return
		if status == "decode_error":
			self.statusBar().showMessage(
				self.tr("Could not decode clipboard CDML data"), 3000,
			)
			return
		if fragment_cdml is None:
			return
		if (
			target.is_disposed
			or target not in self._sessions
			or not target.can_commit_persistent_action
		):
			self.statusBar().showMessage(
				self.tr("Document cannot accept a persistent edit"), 3000,
			)
			self._refresh_document_actions()
			return
		outcome = target.submit_clipboard_fragment(fragment_cdml)
		self._show_persistent_action_outcome(outcome)
		self._refresh_document_actions()

	#============================================
	def _remove_top_level_objects(self, selected_objects: list) -> None:
		"""Remove complete selected molecules and artwork through undo commands."""
		scene = self._scene
		document = self._document
		document.undo_stack.beginMacro("Cut")
		for object_model in selected_objects:
			if hasattr(object_model, "atoms"):
				self._remove_molecule_with_marks(object_model)
				continue
			graphics_item = self._presentation_item(object_model)
			if graphics_item is not None:
				document.undo_stack.push(
					bkchem_qt.undo.commands.RemovePresentationObjectCommand(
						document, scene, object_model, graphics_item,
					)
				)
		document.undo_stack.endMacro()

	#============================================
	def _remove_molecule_with_marks(self, molecule_model: object) -> None:
		"""Queue atomic removal of one molecule and all atom-attached marks."""
		document = self._document
		scene = self._scene
		for mark_model in document.marks:
			if mark_model.atom_model not in molecule_model.atoms:
				continue
			mark_item = self._mark_item(mark_model)
			parent_atom_item = self._atom_item(mark_model.atom_model)
			if mark_item is None or parent_atom_item is None:
				continue
			document.undo_stack.push(
				bkchem_qt.undo.commands.RemoveAtomMarkCommand(
					document, mark_model, mark_item, parent_atom_item,
				)
			)
		graphics_items = [
			item for item in scene.items()
			if getattr(item, "molecule_model", None) is molecule_model
		]
		document.undo_stack.push(
			bkchem_qt.undo.commands.RemoveMoleculeCommand(
				document, scene, molecule_model, graphics_items,
			)
		)

	#============================================
	def _atom_item(self, atom_model: object) -> PySide6.QtWidgets.QGraphicsItem | None:
		"""Return the active atom projection for one atom model."""
		for item in self._scene.items():
			if getattr(item, "atom_model", None) is atom_model:
				return item
		return None

	#============================================
	def _mark_item(self, mark_model: object) -> PySide6.QtWidgets.QGraphicsItem | None:
		"""Return the active mark projection for one persistent mark model."""
		for item in self._scene.items():
			if getattr(item, "atom_mark_model", None) is mark_model:
				return item
		return None

	#============================================
	def _presentation_item(
			self, object_model: object,
			) -> PySide6.QtWidgets.QGraphicsItem | None:
		"""Return the active projection for one presentation model."""
		for item in self._scene.items():
			if getattr(item, "document_object_model", None) is object_model:
				return item
		return None

	#============================================
	def on_select_all(self) -> None:
		"""Select all interactive items in the scene."""
		import bkchem_qt.canvas.items.atom_item
		import bkchem_qt.canvas.items.bond_item
		for item in self._scene.items():
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				item.setSelected(True)
			elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				item.setSelected(True)
			elif getattr(item, "document_object_model", None) in self.document.presentation_objects:
				item.setSelected(True)

	#============================================
	def _delete_selected(self) -> None:
		"""Delete all selected atoms and bonds with undo support."""
		import bkchem_qt.canvas.items.atom_item
		import bkchem_qt.canvas.items.bond_item
		import bkchem_qt.undo.commands
		scene = self._scene
		undo_stack = self._document.undo_stack
		# begin undo macro for compound delete
		undo_stack.beginMacro("Cut")
		# delete selected bonds first
		for bond_item in list(self._document.selected_bonds):
			bond_model = bond_item.bond_model
			mol = self._document._find_molecule_for_bond(bond_model)
			if mol is not None:
				cmd = bkchem_qt.undo.commands.RemoveBondCommand(
					scene, mol, bond_model, bond_item,
				)
				undo_stack.push(cmd)
		# delete selected atoms and their remaining connected bonds
		for atom_item in list(self._document.selected_atoms):
			atom_model = atom_item.atom_model
			mol = self._document._find_molecule_for_atom(atom_model)
			if mol is None:
				continue
			# find connected bond items still in scene
			connected = []
			for item in scene.items():
				if isinstance(
					item, bkchem_qt.canvas.items.bond_item.BondItem
				):
					bm = item.bond_model
					if bm.atom1 is atom_model or bm.atom2 is atom_model:
						connected.append((bm, item))
			cmd = bkchem_qt.undo.commands.RemoveAtomCommand(
				scene, mol, atom_model, atom_item, connected,
			)
			undo_stack.push(cmd)
		undo_stack.endMacro()

	#============================================
	def on_zoom_in(self) -> None:
		"""Zoom in on the canvas."""
		self._view.zoom_in()

	#============================================
	def on_zoom_out(self) -> None:
		"""Zoom out on the canvas."""
		self._view.zoom_out()

	#============================================
	def on_reset_zoom(self) -> None:
		"""Reset zoom to 100%."""
		self._view.reset_zoom()

	#============================================
	def on_zoom_to_fit(self) -> None:
		"""Zoom to page (fit paper in viewport)."""
		self._view.zoom_to_fit()

	#============================================
	def on_zoom_to_content(self) -> None:
		"""Zoom to fit all drawn content."""
		self._view.zoom_to_content()

	#============================================
	def on_toggle_grid(self) -> None:
		"""Toggle grid visibility from toolbar."""
		current = self._scene.grid_visible
		self._on_toggle_grid(not current)
		# keep the menu action checkmark in sync
		self._action_toggle_grid.setChecked(not current)

	#============================================
	def on_toggle_grid_snap(self) -> None:
		"""Toggle snap-to-grid from toolbar or command."""
		current = self._scene.grid_snap_enabled
		self._on_toggle_grid_snap(not current)
		# keep the menu action checkmark in sync
		if hasattr(self, "_action_toggle_grid_snap"):
			self._action_toggle_grid_snap.setChecked(not current)

	# ------------------------------------------------------------------
	# Mode and submode switching
	# ------------------------------------------------------------------

	#============================================
	def _update_menu_predicates(self) -> None:
		"""Re-evaluate enabled_when predicates on all menu actions.

		Called when selection changes, undo/redo state changes, or
		tab switches to keep menu items in sync with document state.
		"""
		if hasattr(self, '_menu_builder') and self._menu_builder is not None:
			self._menu_builder.update_menu_states(self)

	#============================================
	def _on_mode_changed(self, mode_name: str) -> None:
		"""Handle a mode switch by rebuilding the submode ribbon.

		Shows or hides the edit ribbon based on the mode's
		show_edit_pool flag. Rebuilds the submode ribbon with
		the new mode's submode groups.

		Args:
			mode_name: Name of the newly active mode.
		"""
		mode = self._mode_manager.current_mode
		if mode is None:
			return
		# rebuild the submode ribbon for the new mode
		self._submode_ribbon.rebuild(mode_name)
		# keep submode toolbar always visible at a fixed minimum height
		# to prevent layout jumps when switching between modes
		self._submode_toolbar.setVisible(True)
		self._submode_toolbar.setMinimumHeight(32)
		# show/hide the edit ribbon based on mode's show_edit_pool flag
		show_edit = getattr(mode, 'show_edit_pool', False)
		self._edit_ribbon_toolbar.setVisible(show_edit)

	#============================================
	def _on_submode_selected(self, key: str) -> None:
		"""Forward a submode button click to the active mode.

		Args:
			key: The submode key string selected in the ribbon.
		"""
		mode = self._mode_manager.current_mode
		if mode is not None:
			mode.set_submode(key)

	# ------------------------------------------------------------------
	# Private action handlers
	# ------------------------------------------------------------------

	#============================================
	def _begin_import_request(self) -> int:
		"""Compatibility wrapper for the active session's import token."""
		return self._active_session.begin_import_request()

	#============================================
	def _invalidate_import_requests(self) -> None:
		"""Invalidate asynchronous imports targeting the active session."""
		if self._active_session is not None:
			self._active_session.invalidate_import_requests()

	#============================================
	def _import_request_is_current(self, token: int) -> bool:
		"""Return whether an import still targets the active live session."""
		return (
			not self._shutdown_prepared
			and self._active_session is not None
			and self._active_session.import_request_is_current(token)
		)

	#============================================
	def _track_import_worker(self, worker: PySide6.QtCore.QThread) -> None:
		"""Compatibility wrapper retaining a worker in the active session."""
		self._active_session.track_import_worker(worker)

	#============================================
	def _release_import_worker(self, worker: PySide6.QtCore.QThread) -> None:
		"""Release one finished worker without dereferencing a retired session.

		Queued ``QThread.finished`` slots can run after a closing tab has removed
		its session and released its Python-owned graph.  The window outlives those
		slots, so it is the terminal owner: it releases only workers still found in
		registered live sessions and otherwise retires the stopped worker directly.
		"""
		if worker in self._retired_import_workers:
			self._retired_import_workers.discard(worker)
			if not worker.isRunning():
				worker.deleteLater()
			self._emit_worker_retirement_drained()
			return
		for session in self._sessions:
			if worker in session._import_workers:
				session.release_import_worker(worker)
				return
		try:
			if not worker.isRunning():
				worker.deleteLater()
		except RuntimeError:
			# Session disposal may already have queued native worker deletion.
			pass

	#============================================
	def _retain_retiring_session_workers(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Transfer a result-delivering worker to the window's terminal owner.

		A same-tab replacement can be initiated by the worker's queued result
		slot before the native thread emits ``finished``.  The retiring session
		must therefore release ownership without joining that still-delivering
		thread; the window retains it until the relay observes ``finished``.
		"""
		for worker in session.retire_import_workers():
			self._retired_import_workers.add(worker)

	#============================================
	def _emit_worker_retirement_drained(self) -> None:
		"""Publish the terminal drain only after every adopted worker finished."""
		if self._shutdown_prepared and not self._retired_import_workers:
			self._shutdown_state = ShutdownState.READY
			self._complete_shutdown_session_disposal()
			self.worker_retirement_drained.emit()

	#============================================
	def _complete_shutdown_session_disposal(self) -> None:
		"""Queue detached session roots only after worker retirement drains."""
		sessions = tuple(self._shutdown_sessions_pending_disposal)
		self._shutdown_sessions_pending_disposal.clear()
		for session in sessions:
			self._dispose_session_later(session)

	#============================================
	def _stop_import_workers(self) -> None:
		"""Move all workers into delivery-cancelled window retirement."""
		for session in tuple(self._sessions):
			self._retain_retiring_session_workers(session)
		for worker in tuple(self._retired_import_workers):
			worker.requestInterruption()

	#============================================
	def _registered_recovery_export_session(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			*, require_active: bool,
			) -> bkchem_qt.models.document_session.DocumentSession | None:
		"""Return one still-registered exportable session without retargeting it."""
		if require_active and self._active_session is not session:
			return None
		if session.is_disposed or not any(item is session for item in self._sessions):
			return None
		if not session.can_recovery_export:
			return None
		return session

	#============================================
	def _active_recovery_export_session(
			self,
			) -> bkchem_qt.models.document_session.DocumentSession | None:
		"""Return the exact active registered session eligible for Recovery Export."""
		session = self._active_session
		if session is None:
			return None
		return self._registered_recovery_export_session(session, require_active=True)

	#============================================
	def can_recovery_export(self) -> bool:
		"""Return the total File-action predicate for Recovery Export."""
		return self._active_recovery_export_session() is not None

	#============================================
	def can_save_authoritatively(self) -> bool:
		"""Return whether the active document may use ordinary Save or Save As."""
		session = self._active_session
		return bool(
			session is not None
			and session in self._sessions
			and session.can_write_authoritative_snapshot
		)

	#============================================
	def can_save_as_template(self) -> bool:
		"""Return whether Template export has one current backend snapshot to publish."""
		return self._user_template_directory is not None and self.can_recovery_export()

	#============================================
	def can_refresh_user_templates(self) -> bool:
		"""Return whether this window has an explicit user-template directory."""
		return self._user_template_directory is not None

	#============================================
	def _export_captured_backend_snapshot(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			*, require_active: bool, dialog_title: str,
			) -> bool:
		"""Prompt and publish only the session captured before the prompt."""
		file_path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self,
			self.tr(dialog_title),
			"",
			self.tr(bkchem_qt.actions.file_actions.CDML_FILTER),
		)[0]
		if not file_path:
			return False
		path = pathlib.Path(file_path)
		if not path.suffix:
			path = path.with_suffix(".cdml")
		elif path.suffix.lower() != ".cdml":
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Unsupported Recovery Export Format"),
				self.tr("Recovery Export writes BKChem CDML files with a .cdml extension."),
			)
			return False
		captured = self._registered_recovery_export_session(
			session, require_active=require_active,
		)
		if captured is not session:
			return False
		absolute_path = os.path.abspath(str(path))
		try:
			session.export_backend_snapshot(absolute_path)
		except bkchem_qt.models.document_session.BackendSnapshotPublicationError as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Recovery Export Durability Unconfirmed"),
				self.tr(
					"The exact canonical snapshot may be present at %s, but export "
					"durability is unconfirmed. No session state changed; the tab "
					"remains open.\n\n%s"
				) % (absolute_path, exc),
			)
			return False
		except Exception as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Recovery Export Error"),
				self.tr("Could not export backend CDML to %s:\n%s") % (
					absolute_path, exc,
				),
			)
			return False
		self.statusBar().showMessage(
			self.tr("Backend snapshot exported: %s") % absolute_path,
			3000,
		)
		return True

	#============================================
	def _recovery_export_close_choice(self, message: str) -> str:
		"""Run the Recovery Export close prompt and dispose it before returning."""
		dialog = PySide6.QtWidgets.QMessageBox(self)
		try:
			dialog.setWindowTitle(self.tr("Unsaved Backend Changes"))
			dialog.setText(message)
			export_button = dialog.addButton(
				self.tr("Recovery Export"),
				PySide6.QtWidgets.QMessageBox.ButtonRole.ActionRole,
			)
			discard_button = dialog.addButton(
				PySide6.QtWidgets.QMessageBox.StandardButton.Discard,
			)
			dialog.addButton(PySide6.QtWidgets.QMessageBox.StandardButton.Cancel)
			dialog.exec()
			if dialog.clickedButton() is export_button:
				choice = "export"
			elif dialog.clickedButton() is discard_button:
				choice = "discard"
			else:
				choice = "cancel"
			return choice
		finally:
			dialog.deleteLater()

	#============================================
	def _on_recovery_export(self) -> bool:
		"""Export only the exact active backend session captured before the dialog."""
		session = self._active_recovery_export_session()
		if session is None:
			return False
		return self._export_captured_backend_snapshot(
			session, require_active=True, dialog_title="Recovery Export Backend CDML",
		)

	#============================================
	def _confirm_recovery_export_or_discard(
			self, operation: str,
			session: bkchem_qt.models.document_session.DocumentSession,
			state: bkchem_qt.models.document_session.CloseState,
			) -> bool:
		"""Offer Recovery Export only when ordinary authoritative Save is unsafe."""
		message = self.tr(
			"The current backend document cannot be saved authoritatively before %s."
		) % operation
		if state.legacy_local_pending:
			message += "\n\n" + self.tr(
				"Recovery Export saves the backend document only; Qt-local edits are excluded.",
			)
		elif state.backend_unseen:
			message += "\n\n" + self.tr(
				"The saved backend document cannot currently be shown in the Qt projection.",
			)
		choice = self._recovery_export_close_choice(message)
		if choice == "export":
			return self._export_captured_backend_snapshot(
				session, require_active=False, dialog_title="Recovery Export Backend CDML",
			)
		if choice == "discard":
			return True
		return False

	#============================================
	def _confirm_save_if_dirty(
			self, operation: str,
			session: bkchem_qt.models.document_session.DocumentSession | None = None,
			) -> bool:
		"""Return whether a destructive operation may continue for one tab."""
		target = session if session is not None else self._active_session
		if target is None:
			return True
		if target.is_disposed:
			return False
		try:
			state = target.close_state()
		except RuntimeError:
			return False
		if not state.needs_confirmation:
			return True
		if state.uses_recovery_export:
			return self._confirm_recovery_export_or_discard(operation, target, state)
		reply = PySide6.QtWidgets.QMessageBox.question(
			self,
			self.tr("Unsaved Changes"),
			self.tr("Save changes before %s?") % operation,
			(PySide6.QtWidgets.QMessageBox.StandardButton.Save
				| PySide6.QtWidgets.QMessageBox.StandardButton.Discard
				| PySide6.QtWidgets.QMessageBox.StandardButton.Cancel),
			PySide6.QtWidgets.QMessageBox.StandardButton.Save,
		)
		if reply == PySide6.QtWidgets.QMessageBox.StandardButton.Cancel:
			return False
		if reply == PySide6.QtWidgets.QMessageBox.StandardButton.Save:
			return self._save_session(target)
		return True

	#============================================
	def _dispose_scene_items(
			self,
			session: bkchem_qt.models.document_session.DocumentSession | None = None,
			) -> None:
		"""Disconnect live and undo-retained graphics callbacks."""
		target = session if session is not None else self._active_session
		if target is None:
			return
		from bkchem_qt.canvas.graphics_retirement import GraphicsRetirementCoordinator
		coordinator = GraphicsRetirementCoordinator()
		coordinator.prepare_scene_retirement(target.scene, target.document.undo_stack)
		coordinator.raise_if_callback_failed(
			"Scene graphics callbacks were released after a disposal failure",
		)

	#============================================
	def _select_session(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> bool:
		"""Select and activate an existing live session."""
		if session.is_disposed or session not in self._sessions:
			return False
		index = self._tab_widget.indexOf(session.view)
		if index < 0:
			return False
		self._tab_widget.setCurrentIndex(index)
		if self._active_session is not session:
			self._activate_session(session)
		return True

	#============================================
	def _pristine_startup_session(
			self,
			) -> bkchem_qt.models.document_session.DocumentSession | None:
		"""Return the sole untouched startup tab, if it still exists."""
		if len(self._sessions) != 1:
			return None
		session = self._sessions[0]
		document = session.document
		if document is None:
			return None
		if (
				not document.objects
				and document.file_path is None
				and not document.dirty
				and session.origin_path is None
		):
			return session
		return None

	#============================================
	def _detach_tab_page(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			index: int,
			) -> None:
		"""Remove a tab page and transfer its native ownership from QTabWidget."""
		self._tab_widget.removeTab(index)
		session.view.hide()
		session.view.setParent(None)

	#============================================
	def _ensure_session_tab_attached(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			index: int,
			) -> None:
		"""Restore a registered session's page after a failed transition."""
		if self._tab_widget.indexOf(session.view) < 0:
			self._tab_widget.insertTab(index, session.view, session.title)

	#============================================
	def _unregister_session_without_disposal(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			title_connected: bool,
			) -> None:
		"""Remove a failed session while leaving its owner responsible to dispose it."""
		session.clear_projection_lifecycle_port()
		tab_index = self._tab_widget.indexOf(session.view)
		if tab_index >= 0:
			self._tab_widget.removeTab(tab_index)
			session.view.hide()
			session.view.setParent(None)
		self._sessions_by_view.pop(session.view, None)
		if session in self._sessions:
			self._sessions.remove(session)
		if title_connected:
			try:
				session.title_changed.disconnect(self._on_session_title_changed)
			except (RuntimeError, TypeError):
				pass

	#============================================
	def _restore_active_session(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			index: int,
			) -> None:
		"""Restore a live session after another session's activation failed."""
		current = self._active_session
		if current is not None and current is not session:
			if self._ui_signals_connected:
				self._disconnect_active_session_signals(current)
			current_mode = current.mode_manager.current_mode
			if current_mode is not None:
				current_mode.deactivate()
		if current is session and self._ui_signals_connected:
			self._disconnect_active_session_signals(session)
		self._set_active_session_aliases(session)
		self._bind_property_dock(session)
		if self._ui_signals_connected:
			self._connect_active_session_signals(session)
			active_mode = session.mode_manager.current_mode
			if active_mode is not None:
				active_mode.activate()
		if index >= 0:
			self._tab_widget.setCurrentIndex(index)

	#============================================
	def _dispose_session_later(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			) -> None:
		"""Retain a detached session until Qt confirms native destruction.

		``deleteLater()`` does not keep the Python wrapper strongly owned.
		Without this registry, a removed session can lose its final Python
		reference before Qt delivers its queued child-deletion events.
		"""
		session_key = id(session)
		document = session.document
		scene = session.scene
		view = session.view
		mode_manager = session.mode_manager
		# Keep only QObject roots while the session breaks its nested Python
		# reference graph.  Scene-owned QGraphicsItem wrappers must never cross
		# the synchronous scene-content disposal boundary into this reaper.
		retained_wrappers = [
			session,
			scene,
			view,
			mode_manager,
			*tuple(mode_manager._modes.values()),
		]
		if document is not None:
			retained_wrappers.extend((document, document.undo_stack))
		pending = _PendingSessionDeletion(retained_wrappers)
		self._pending_session_deletions[session_key] = pending
		session.destroyed.connect(functools.partial(
			self._release_disposed_session_later, session_key,
		))
		dispose_error = None
		try:
			session.dispose()
		except Exception as exc:
			dispose_error = exc
		if session._teardown_phase == "roots_queued":
			pending.retained_graphics_records = (
				session.take_retained_graphics_records()
			)
			session.release_python_references()
			session.setParent(None)
			session.deleteLater()
		else:
			raise RuntimeError(
				"Session roots remain retained because Qt teardown did not reach "
				"the queued terminal phase",
			) from dispose_error
		if dispose_error is not None:
			raise RuntimeError(
				"Session was queued after a disposal failure",
			) from dispose_error

	#============================================
	def _release_disposed_session_later(
			self, session_key: int, _destroyed_object: object = None,
			) -> None:
		"""Release an invalid session after its retained graphics are resolved."""
		pending = self._pending_session_deletions.get(session_key)
		if pending is None:
			return
		pending.session_destroyed = True
		if self._pending_session_graphics_are_resolved(pending):
			PySide6.QtCore.QTimer.singleShot(0, functools.partial(
				self._pending_session_deletions.pop, session_key, None,
			))
		else:
			self._schedule_pending_session_graphics_retry()

	#============================================
	def _schedule_pending_session_graphics_retry(self) -> None:
		"""Schedule one bounded ordinary retry for destroyed-session graphics.

		The destroyed callback is the first MainWindow-owned resolution pass.  A
		second zero-delay pass covers a transient native deletion failure after
		Qt has advanced normally.  Further failures stay retained for explicit
		shutdown draining so this path cannot create a busy event-loop retry.
		"""
		if self._shutdown_prepared or self._pending_session_graphics_retry_scheduled:
			return
		self._pending_session_graphics_retry_scheduled = True
		PySide6.QtCore.QTimer.singleShot(
			0, self._retry_pending_session_graphics_once,
		)

	#============================================
	def _retry_pending_session_graphics_once(self) -> None:
		"""Run the one queued retry through the normal MainWindow resolver."""
		self._pending_session_graphics_retry_scheduled = False
		if self._shutdown_prepared:
			return
		self._resolve_pending_session_graphics()

	#============================================
	def _pending_session_graphics_are_resolved(
			self, pending: _PendingSessionDeletion,
			) -> bool:
		"""Resolve retained graphics only through the coordinator's native boundary."""
		records = pending.retained_graphics_records
		if records is None or not records.unresolved:
			return True
		from bkchem_qt.canvas.graphics_retirement import DetachedGraphicsRetirementReaper
		reaper = DetachedGraphicsRetirementReaper()
		reaper.retain_graphics_records(records)
		reaper.drain()
		pending.retained_graphics_records = reaper.take_retained_graphics_records()
		return not pending.retained_graphics_records.unresolved

	#============================================
	def _resolve_pending_session_graphics(self) -> None:
		"""Advance terminal graphics records during the controlled reaper drain."""
		for session_key, pending in tuple(self._pending_session_deletions.items()):
			if not self._pending_session_graphics_are_resolved(pending):
				continue
			if pending.session_destroyed:
				self._pending_session_deletions.pop(session_key, None)

	#============================================
	def _remove_session(
			self, session: bkchem_qt.models.document_session.DocumentSession,
			) -> bool:
		"""Remove and deterministically dispose one session without prompting."""
		if session not in self._sessions:
			return False
		index = self._sessions.index(session)
		was_active = session is self._active_session
		if was_active:
			if self._ui_signals_connected:
				self._disconnect_active_session_signals(session)
			self._bind_property_dock(None)
			self._active_session = None
			self._document = None
			self._scene = None
			self._view = None
			self._mode_manager = None
		try:
			session.title_changed.disconnect(self._on_session_title_changed)
		except (RuntimeError, TypeError):
			pass
		session.clear_projection_lifecycle_port()

		previous_block = self._tab_widget.blockSignals(True)
		self._tab_change_blocked = True
		try:
			self._detach_tab_page(session, index)
			self._sessions.pop(index)
			self._sessions_by_view.pop(session.view, None)
			if was_active and self._sessions:
				next_index = min(index, len(self._sessions) - 1)
				self._tab_widget.setCurrentIndex(next_index)
		finally:
			self._tab_change_blocked = False
			self._tab_widget.blockSignals(previous_block)

		self._retain_retiring_session_workers(session)
		self._dispose_session_later(session)
		if was_active and self._sessions:
			next_view = self._tab_widget.currentWidget()
			next_session = self._sessions_by_view.get(next_view)
			if next_session is None:
				next_session = self._sessions[0]
				self._tab_widget.setCurrentIndex(0)
			self._activate_session(next_session)
		return True

	#============================================
	def _replace_with_prebuilt_session(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			replacement: bkchem_qt.models.document_session.DocumentSession,
			*, activate: bool | None = None,
			) -> bkchem_qt.models.document_session.DocumentSession | None:
		"""Atomically swap a viable detached session into one registered tab."""
		if replacement.is_disposed or replacement in self._sessions:
			raise ValueError("Replacement session must be live and unregistered")
		if replacement.view in self._sessions_by_view:
			raise ValueError("Replacement view is already registered")
		if session not in self._sessions:
			self._dispose_session_later(replacement)
			return None
		index = self._sessions.index(session)
		was_active = session is self._active_session
		should_activate = was_active if activate is None else activate
		previous_index = self._tab_widget.currentIndex()
		active_target: bkchem_qt.models.document_session.DocumentSession | None = None
		if should_activate:
			active_target = replacement
		elif was_active:
			for candidate in self._sessions:
				if candidate is not session:
					active_target = candidate
					break
			if active_target is None:
				active_target = replacement
		replacement_registered = False
		old_title_disconnected = False

		previous_block = self._tab_widget.blockSignals(True)
		self._tab_change_blocked = True
		try:
			self._register_session(replacement, index=index, activate=False)
			replacement_registered = True
			if active_target is not None:
				active_index = self._tab_widget.indexOf(active_target.view)
				self._tab_widget.setCurrentIndex(active_index)
				self._activate_session(active_target)
			try:
				session.title_changed.disconnect(self._on_session_title_changed)
				old_title_disconnected = True
			except (RuntimeError, TypeError):
				pass
			self._detach_tab_page(session, index + 1)
			self._sessions.pop(index + 1)
			self._sessions_by_view.pop(session.view, None)
		except Exception:
			if session in self._sessions:
				self._ensure_session_tab_attached(session, index + 1)
				if old_title_disconnected:
					session.title_changed.connect(self._on_session_title_changed)
			if was_active and session in self._sessions:
				old_index = self._tab_widget.indexOf(session.view)
				self._restore_active_session(session, old_index)
			if replacement_registered:
				self._unregister_session_without_disposal(replacement, True)
				self._dispose_session_later(replacement)
			if session in self._sessions:
				old_index = self._tab_widget.indexOf(session.view)
				if old_index >= 0:
					self._tab_widget.setCurrentIndex(old_index)
			elif previous_index >= 0:
				self._tab_widget.setCurrentIndex(previous_index)
			raise
		finally:
			self._tab_change_blocked = False
			self._tab_widget.blockSignals(previous_block)

		self._retain_retiring_session_workers(session)
		self._dispose_session_later(session)
		return replacement

	#============================================
	def close_session_at(self, index: int) -> bool:
		"""Close one tab, or close the application when it is the final tab."""
		if index < 0 or index >= len(self._sessions):
			return False
		if len(self._sessions) == 1:
			return bool(self.close())
		session = self._sessions[index]
		if not self._confirm_save_if_dirty("closing this tab", session):
			self._select_session(session)
			return False
		return self._remove_session(session)

	#============================================
	def close_current_tab(self) -> bool:
		"""Close the currently selected tab through its save guard."""
		return self.close_session_at(self._tab_widget.currentIndex())

	#============================================
	def _on_new(self) -> bool:
		"""Create and activate a new independent document tab."""
		self._create_session(activate=True)
		return True

	#============================================
	def _on_open(self) -> bool:
		"""Open a file in a new document tab."""
		file_path = PySide6.QtWidgets.QFileDialog.getOpenFileName(
			self,
			self.tr("Open Chemistry File"),
			"",
			self.tr(bkchem_qt.actions.file_actions.CHEMISTRY_FILTER),
		)[0]
		if not file_path:
			return False
		return self.open_file_path(file_path)

	#============================================
	def _on_open_same_tab(self) -> bool:
		"""Open a file by deliberately replacing the current tab."""
		file_path = PySide6.QtWidgets.QFileDialog.getOpenFileName(
			self,
			self.tr("Open Chemistry File in Current Tab"),
			"",
			self.tr(bkchem_qt.actions.file_actions.CHEMISTRY_FILTER),
		)[0]
		if not file_path:
			return False
		return self.open_file_path(file_path, replace_current=True)

	#============================================
	def _open_path_replacing_current(self, file_path: str) -> bool:
		"""Compatibility wrapper for deliberate same-tab opening."""
		return self.open_file_path(file_path, replace_current=True)

	#============================================
	def open_file_path(
			self, file_path: str, replace_current: bool = False,
			) -> bool:
		"""Open a path in a new tab or deliberately replace the active tab."""
		absolute_path = os.path.abspath(file_path)
		canonical_path = os.path.normcase(os.path.realpath(absolute_path))
		for session in self._sessions:
			origin_path = session.origin_path
			if origin_path is None:
				continue
			existing_path = os.path.normcase(
				os.path.realpath(os.path.abspath(origin_path))
			)
			if existing_path == canonical_path:
				return self._select_session(session)

		extension = os.path.splitext(absolute_path)[1].lower()
		try:
			capability = (
				bkchem_qt.io.import_capabilities.capability_for_extension(
					extension,
				)
			)
		except ValueError as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("File Read Error"),
				self.tr("Could not open %s:\n%s") % (absolute_path, exc),
			)
			return False
		if capability.route == "worker":
			return self._start_async_import(
				capability.codec_name,
				absolute_path,
				replace_current,
			)
		if capability.route != "native":
			raise RuntimeError(
				"Qt import capability '%s' has no loading route."
				% capability.codec_name
			)

		try:
			with open(absolute_path, encoding="utf-8") as source:
				cdml_text = source.read()
			prepared_native_cdml = (
				bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
					cdml_text,
				)
			)
		except Exception as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("File Read Error"),
				self.tr("Could not open %s:\n%s") % (absolute_path, exc),
			)
			return False
		target = self._active_session if replace_current else None
		if target is not None and not self._confirm_save_if_dirty(
				"opening another file", target,
		):
			return False
		return self._install_prepared_native_cdml(
			absolute_path,
			prepared_native_cdml,
			replace_session=target,
		)

	#============================================
	def _start_async_import(
			self, codec_name: str, file_path: str, replace_current: bool,
			) -> bool:
		"""Start one session-owned non-CDML import."""
		startup_session = None
		if replace_current:
			target = self._active_session
		else:
			startup_session = self._pristine_startup_session()
			target = self._create_session(
				activate=True,
				display_name=self.tr(
					"Loading %s..." % os.path.basename(file_path)
				),
				origin_path=file_path,
			)
		request_token = target.begin_import_request()
		bkchem_qt.actions.file_actions._load_with_worker(
			self,
			codec_name,
			file_path,
			on_loaded=lambda prepared_cdml: self._complete_async_import(
				target,
				request_token,
				file_path,
				prepared_cdml,
				replace_current,
				startup_session,
			),
			should_deliver=lambda: (
				not self._shutdown_prepared
				and target in self._sessions
				and target.import_request_is_current(request_token)
			),
			worker_owner=target,
			on_error=lambda message: self._handle_async_import_error(
				target, request_token, file_path, message, replace_current,
			),
		)
		return True

	#============================================
	def _complete_async_import(
			self,
			target: bkchem_qt.models.document_session.DocumentSession,
			request_token: int,
			file_path: str,
			prepared_cdml: bkchem_qt.bridge.worker.PreparedCompleteCDML,
			replace_current: bool,
			startup_session: (
				bkchem_qt.models.document_session.DocumentSession | None
			),
			) -> bool:
		"""Install a prepared worker result only into its originating tab."""
		if (
				self._shutdown_prepared
				or target not in self._sessions
				or not target.import_request_is_current(request_token)
		):
			return False
		if not isinstance(prepared_cdml, bkchem_qt.bridge.worker.PreparedCompleteCDML):
			self._handle_async_import_error(
				target,
				request_token,
				file_path,
				self.tr("No molecules found"),
				replace_current,
			)
			return False
		try:
			prepared_imported_cdml = (
				bkchem_qt.models.document_session.DocumentSession.prepare_imported_cdml(
					prepared_cdml.complete_cdml,
				)
			)
		except Exception as exc:
			self._handle_async_import_error(
				target, request_token, file_path, str(exc), replace_current,
			)
			return False
		if replace_current:
			if not self._confirm_save_if_dirty(
				"opening another file", target,
			):
				return False
			return self._install_prepared_imported_cdml(
				file_path, prepared_imported_cdml, replace_session=target,
			)

		installed = self._install_prepared_imported_cdml(
			file_path, prepared_imported_cdml, replace_session=target,
		)
		if (
			installed
			and startup_session is not None
			and startup_session in self._sessions
			and self._pristine_startup_session() is None
			and not startup_session.document.objects
			and not startup_session.document.dirty
			and startup_session.origin_path is None
		):
			self._remove_session(startup_session)
		return installed

	#============================================
	def _handle_async_import_error(
			self,
			target: bkchem_qt.models.document_session.DocumentSession,
			request_token: int,
			file_path: str,
			message: str,
			replace_current: bool,
			) -> None:
		"""Report a current import error and remove only a loading tab."""
		if (
				target not in self._sessions
				or not target.import_request_is_current(request_token)
			):
			return
		PySide6.QtWidgets.QMessageBox.warning(
			self,
			self.tr("File Read Error"),
			self.tr("Could not open %s:\n%s") % (file_path, message),
		)
		if replace_current:
			return
		if len(self._sessions) == 1:
			replacement = self._construct_session()
			self._replace_with_prebuilt_session(target, replacement, activate=True)
		else:
			self._remove_session(target)

	#============================================
	def _install_prepared_native_cdml(
			self, file_path: str,
			prepared_native_cdml: (
				bkchem_qt.models.document_session.PreparedNativeCDML
			), *,
			replace_session: (
				bkchem_qt.models.document_session.DocumentSession | None
			) = None,
			) -> bool:
		"""Install an OASA-staged native projection after it is fully viable."""
		absolute_path = os.path.abspath(file_path)
		startup_session = None
		session: bkchem_qt.models.document_session.DocumentSession | None = None
		if replace_session is None:
			startup_session = self._pristine_startup_session()
		try:
			session = self._construct_session(
				file_path=absolute_path,
				origin_path=absolute_path,
				prepared_native_cdml=prepared_native_cdml,
			)
			molecule_projections = bkchem_qt.canvas.molecule_projection.project_molecules_to_scene(
				session.scene, session.document.molecules,
			)
			presentation_projections = bkchem_qt.canvas.document_projection.project_document_presentation(
				session.document, session.scene,
			)
			session.document.register_current_projection_items(
				tuple(
					item for _molecule, items in molecule_projections for item in items
				) + tuple(presentation_projections["presentation"].values())
				+ tuple(presentation_projections["marks"].values()),
			)
		except Exception as exc:
			if session is not None:
				self._dispose_session_later(session)
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("File Read Error"),
				self.tr("Could not open %s:\n%s") % (absolute_path, exc),
			)
			return False

		try:
			if replace_session is None:
				self._register_session(session, activate=True)
			else:
				session = self._replace_with_prebuilt_session(
					replace_session, session,
					activate=replace_session is self._active_session,
				)
				if session is None:
					raise RuntimeError("The target tab is no longer available")
		except Exception as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("File Read Error"),
				self.tr("Could not open %s:\n%s") % (absolute_path, exc),
			)
			return False

		bkchem_qt.actions.file_actions._record_recent_file(self, absolute_path)
		self._warn_unsupported_content(session, absolute_path)
		self.statusBar().showMessage(
			self.tr("Loaded %d molecule(s), %d drawing object(s)") % (
				len(session.document.molecules),
				len(session.document.presentation_objects),
			),
			3000,
		)
		if (
			startup_session is not None
			and startup_session is not session
			and startup_session in self._sessions
		):
			self._remove_session(startup_session)
		return True

	#============================================
	def _install_prepared_imported_cdml(
			self, file_path: str,
			prepared_imported_cdml: (
				bkchem_qt.models.document_session.PreparedImportedCDML
			), *,
			replace_session: (
				bkchem_qt.models.document_session.DocumentSession | None
			) = None,
			) -> bool:
		"""Install a fully staged external document without adopting its source path."""
		absolute_path = os.path.abspath(file_path)
		startup_session = None
		session = None
		if replace_session is None:
			startup_session = self._pristine_startup_session()
		try:
			session = self._construct_session(
				display_name=os.path.basename(absolute_path),
				origin_path=absolute_path,
				prepared_imported_cdml=prepared_imported_cdml,
			)
			molecule_projections = bkchem_qt.canvas.molecule_projection.project_molecules_to_scene(
				session.scene, session.document.molecules,
			)
			presentation_projections = bkchem_qt.canvas.document_projection.project_document_presentation(
				session.document, session.scene,
			)
			session.document.register_current_projection_items(
				tuple(
					item for _molecule, items in molecule_projections for item in items
				) + tuple(presentation_projections["presentation"].values())
				+ tuple(presentation_projections["marks"].values()),
			)
		except Exception as exc:
			if session is not None:
				self._dispose_session_later(session)
			PySide6.QtWidgets.QMessageBox.warning(
				self, self.tr("File Read Error"),
				self.tr("Could not open %s:\n%s") % (absolute_path, exc),
			)
			return False
		try:
			if replace_session is None:
				self._register_session(session, activate=True)
			else:
				session = self._replace_with_prebuilt_session(
					replace_session, session,
					activate=replace_session is self._active_session,
				)
				if session is None:
					raise RuntimeError("The target tab is no longer available")
		except Exception as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self, self.tr("File Read Error"),
				self.tr("Could not open %s:\n%s") % (absolute_path, exc),
			)
			return False
		bkchem_qt.actions.file_actions._record_recent_file(self, absolute_path)
		self._warn_unsupported_content(session, absolute_path)
		self.statusBar().showMessage(
			self.tr("Imported %d molecule(s); save as CDML to publish") % (
				len(session.document.molecules),
			), 3000,
		)
		if (
				startup_session is not None
				and startup_session is not session
				and startup_session in self._sessions
			):
			self._remove_session(startup_session)
		return True

	#============================================
	def _warn_unsupported_content(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			file_path: str,
			) -> None:
		"""Report retained CDML content that the Qt canvas cannot edit yet."""
		warnings = session.document.unsupported_content
		if not warnings:
			return
		details = []
		for warning in warnings:
			label = warning.tag
			if warning.object_id:
				label += f" id={warning.object_id}"
			details.append(f"{warning.path}: {label} - {warning.reason}")
		message = self.tr(
			"Some content in %s is not editable in the PySide6 frontend yet. "
			"It will be preserved when the document is saved.\n\n%s"
		) % (file_path, "\n".join(details))
		PySide6.QtWidgets.QMessageBox.warning(
			self, self.tr("Unsupported CDML Content"), message,
		)

	#============================================
	def _save_session_to_path(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			file_path: str,
			) -> bool:
		"""Authoritatively save one explicit session to CDML and establish a clean point."""
		if not session.can_write_authoritative_snapshot:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Authoritative Save Unavailable"),
				self.tr(
					"This document cannot be saved while its Qt projection is not an "
					"exact current backend snapshot. Use Recovery Export Backend CDML "
					"to publish the current backend snapshot without changing this "
					"document's saved state.",
				),
			)
			return False
		path = pathlib.Path(file_path)
		if not path.suffix:
			path = path.with_suffix(".cdml")
		elif path.suffix.lower() != ".cdml":
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Unsupported Save Format"),
				self.tr("BKChem-Qt native documents must use the .cdml extension."),
			)
			return False
		absolute_path = os.path.abspath(str(path))
		try:
			session.write_backend_snapshot(absolute_path)
		except bkchem_qt.models.document_session.BackendSnapshotPublicationError as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Save Durability Unconfirmed"),
				self.tr(
					"The exact canonical snapshot may be present at %s, but Save "
					"durability is unconfirmed. The backend saved state was not updated."
				) % absolute_path + "\n\n" + str(exc),
			)
			return False
		except Exception as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Save Error"),
				self.tr("Could not save %s:\n%s") % (absolute_path, exc),
			)
			return False
		self._record_successful_save_bookkeeping(
			session, absolute_path,
		)
		return True

	#============================================
	def _record_successful_save_bookkeeping(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			absolute_path: str,
			) -> None:
		"""Apply nonessential post-save presentation updates without falsifying Save.

		The file has already been published and OASA has updated its saved baseline.
		Title/status/recent-file errors
		therefore cannot turn a completed persistence operation into a false Save
		failure.
		"""
		try:
			session.set_file_path(absolute_path)
		except Exception:
			pass
		try:
			message = self.tr("Saved: %s") % absolute_path
			self.statusBar().showMessage(message, 3000)
		except Exception:
			pass
		try:
			bkchem_qt.actions.file_actions._record_recent_file(
				self, absolute_path,
			)
		except Exception:
			pass

	#============================================
	def _save_document_to_path(self, file_path: str) -> bool:
		"""Compatibility wrapper saving the active document session."""
		return self._save_session_to_path(self._active_session, file_path)

	#============================================
	def _save_session(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			force_save_as: bool = False,
			) -> bool:
		"""Save one session, prompting when it has no native CDML path."""
		if not session.can_write_authoritative_snapshot:
			return self._save_session_to_path(session, "")
		file_path = None if force_save_as else session.document.file_path
		if file_path is None:
			file_path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
				self,
				self.tr(
					"Save CDML File As"
					if force_save_as
					else "Save CDML File"
				),
				session.document.file_path or "",
				self.tr("CDML Files (*.cdml);;All Files (*)"),
			)[0]
			if not file_path:
				return False
		return self._save_session_to_path(session, file_path)

	#============================================
	def _on_save(self) -> bool:
		"""Save the active document to its native CDML path."""
		return self._save_session(self._active_session)

	#============================================
	def _on_save_as(self) -> bool:
		"""Save the active document under a newly selected CDML path."""
		return self._save_session(self._active_session, force_save_as=True)

	#============================================
	def _save_template_session_to_path(
			self,
			session: bkchem_qt.models.document_session.DocumentSession,
			file_path: str,
			) -> bool:
		"""Publish canonical backend CDML as a template without saving the session."""
		if not session.can_recovery_export:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Export Unavailable"),
				self.tr("No readable backend snapshot is available for this template."),
			)
			return False
		try:
			session.export_backend_snapshot(file_path)
		except bkchem_qt.models.document_session.BackendSnapshotPublicationError as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Export Durability Unconfirmed"),
				self.tr("The canonical template may be present, but durability is unconfirmed.\n\n%s") % exc,
			)
			return False
		except Exception as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Export Error"),
				self.tr("Could not export template CDML to %s:\n%s") % (file_path, exc),
			)
			return False
		self.statusBar().showMessage(self.tr("Template saved: %s") % file_path, 3000)
		return True

	#============================================
	def _on_save_as_template(self) -> bool:
		"""Prompt for a template destination and publish the current backend snapshot."""
		session = self._active_recovery_export_session()
		if session is None:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Export Unavailable"),
				self.tr("No active backend snapshot is available for template export."),
			)
			return False
		snapshot = session.backend_snapshot
		try:
			bkchem_qt.bridge.user_template_inspection.inspect_user_template_display_name(
				snapshot.cdml,
			)
		except bkchem_qt.bridge.user_template_inspection.UserTemplateInspectionError as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Not Eligible"),
				self.tr("Save As Template accepts one detached molecule with valid geometry.\n\n%s") % exc,
			)
			return False
		if self._user_template_directory is None:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Directory Unavailable"),
				self.tr("This embedded BKChem window has no user template directory."),
			)
			return False
		try:
			self._user_template_directory.mkdir(parents=True, exist_ok=True)
		except OSError as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Directory Unavailable"),
				self.tr("Could not create the user template directory:\n%s") % exc,
			)
			return False
		file_path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Save As Template"), str(self._user_template_directory),
			self.tr("CDML Template (*.cdml);;All Files (*)"),
		)[0]
		if not file_path:
			return False
		if self._registered_recovery_export_session(session, require_active=True) is None:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Export Unavailable"),
				self.tr("The active document changed before template publication."),
			)
			return False
		current_snapshot = session.backend_snapshot
		if current_snapshot != snapshot:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Export Unavailable"),
				self.tr("The document changed before template publication. Please try again."),
			)
			return False
		try:
			bkchem_qt.bridge.user_template_inspection.inspect_user_template_display_name(
				current_snapshot.cdml,
			)
		except bkchem_qt.bridge.user_template_inspection.UserTemplateInspectionError as exc:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Not Eligible"),
				self.tr("The document changed to an ineligible template.\n\n%s") % exc,
			)
			return False
		path = pathlib.Path(file_path)
		if not path.suffix:
			path = path.with_suffix(".cdml")
		elif path.suffix != ".cdml":
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Unsupported Template Format"),
				self.tr("BKChem templates must use the lowercase .cdml extension."),
			)
			return False
		template_directory = self._user_template_directory.resolve()
		candidate = path.resolve()
		if candidate.parent != template_directory:
			PySide6.QtWidgets.QMessageBox.warning(
				self,
				self.tr("Template Destination Outside Catalog"),
				self.tr("Save templates directly in the configured user template directory."),
			)
			return False
		if not self._save_template_session_to_path(session, str(candidate)):
			return False
		self.rescan_user_templates()
		return True

	#============================================
	def save_as_template(self) -> bool:
		"""Publish one eligible active backend snapshot through File behavior."""
		return self._on_save_as_template()

	#============================================
	def _export_snapshot_to_path(self, format_name: str, path: str) -> bool:
		"""Render the active backend snapshot to one selected artifact path."""
		session = self._active_session
		if session is None or session not in self._sessions:
			self.statusBar().showMessage(self.tr("Visual export unavailable"), 3000)
			return False
		result = bkchem_qt.io.export.write_session_snapshot_artifact(
			session, format_name, path,
		)
		if not result.succeeded:
			self.statusBar().showMessage(result.message, 5000)
			return False
		message = self.tr("Exported %s") % path
		if result.warnings:
			message += self.tr(" (%d unsupported persistent object(s) omitted)") % len(result.warnings)
		self.statusBar().showMessage(message, 5000)
		return True

	#============================================
	def _on_export_svg(self) -> None:
		"""Export the active backend snapshot to SVG."""
		path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Export SVG"), "", self.tr("SVG Files (*.svg)")
		)[0]
		if path:
			self._export_snapshot_to_path("svg", path)

	#============================================
	def _on_export_png(self) -> None:
		"""Export the active backend snapshot to PNG."""
		path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Export PNG"), "", self.tr("PNG Files (*.png)")
		)[0]
		if path:
			self._export_snapshot_to_path("png", path)

	#============================================
	def _on_export_pdf(self) -> None:
		"""Export the active backend snapshot to PDF."""
		path = PySide6.QtWidgets.QFileDialog.getSaveFileName(
			self, self.tr("Export PDF"), "", self.tr("PDF Files (*.pdf)")
		)[0]
		if path:
			self._export_snapshot_to_path("pdf", path)

	#============================================
	def _on_toggle_grid(self, checked: bool) -> None:
		"""Toggle the grid visibility on the scene.

		Args:
			checked: Whether the grid action is checked.
		"""
		self._scene.set_grid_visible(checked)
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_VISIBLE, checked
		)

	#============================================
	def _on_toggle_grid_snap(self, checked: bool) -> None:
		"""Toggle snap-to-grid behavior on the scene.

		Args:
			checked: Whether the snap action is checked.
		"""
		self._scene.set_grid_snap_enabled(checked)
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_SNAP_ENABLED,
			checked,
		)
		if checked:
			self.statusBar().showMessage(self.tr("Snap to grid enabled"), 2000)
		else:
			self.statusBar().showMessage(self.tr("Snap to grid disabled"), 2000)

	#============================================
	def _on_toggle_theme(self) -> None:
		"""Toggle between dark and light themes."""
		self._theme_manager.toggle_theme()

	#============================================
	def _on_choose_theme(self) -> None:
		"""Open the theme chooser dialog and apply the selected theme."""
		current = self._theme_manager.current_theme
		chosen = bkchem_qt.dialogs.theme_chooser_dialog.ThemeChooserDialog \
			.choose_theme(self, current)
		# apply only if user selected a different theme
		if chosen is not None and chosen != current:
			self._theme_manager.apply_theme(chosen)

	#============================================
	def _on_theme_changed(self, theme_name: str) -> None:
		"""Handle a theme change by refreshing icons and updating menu text.

		Args:
			theme_name: The new theme name ('dark' or 'light').
		"""
		# update icon_loader theme and clear cache
		bkchem_qt.widgets.icon_loader.set_theme(theme_name)
		bkchem_qt.widgets.icon_loader.reload_icons()

		# refresh mode toolbar icons
		modes_yaml_path = bkchem_qt.setup.mode_setup.get_modes_yaml_path()
		modes_config = {}
		if modes_yaml_path.is_file():
			with open(modes_yaml_path, "r") as fh:
				modes_config = yaml.safe_load(fh) or {}
		modes_defs = modes_config.get("modes", {})
		for name, action in self._mode_toolbar._actions.items():
			# look up the icon name from modes.yaml
			mode_def = modes_defs.get(name, {})
			icon_name = mode_def.get("icon", name)
			icon = bkchem_qt.widgets.icon_loader.get_icon(icon_name)
			self._mode_toolbar.update_action_icon(name, icon)

		# update every session canvas from the YAML theme
		bkchem_qt.themes.theme_loader.clear_cache()
		surround = bkchem_qt.themes.theme_loader.get_canvas_surround(theme_name)
		for session in self._sessions:
			session.view.set_background_color(surround)
			session.scene.apply_theme(theme_name)

		# update chemistry and canvas colors from new theme
		bkchem_qt.setup.canvas_setup._apply_theme_colors(theme_name)

		# refresh submode ribbon icons for new theme
		mode = self._mode_manager.current_mode
		if mode is not None:
			mode_name = mode.name
			# find the registered name for rebuild
			for name in self._mode_manager.mode_names():
				if self._mode_manager._modes[name] is mode:
					mode_name = name
					break
			self._submode_ribbon.rebuild(mode_name)

	#============================================
	def _apply_geometry_preferences(self) -> None:
		"""Apply canonical geometry settings and remove legacy keys."""
		bond_length_pt = bkchem_qt.config.geometry_units.resolve_bond_length_pt(
			self._prefs
		)
		for session in self._sessions:
			session.scene.set_grid_spacing_pt(bond_length_pt)
		self._prefs.remove_value(
			bkchem_qt.config.preferences.Preferences.KEY_BOND_LENGTH
		)

	#============================================
	def _apply_view_preferences(self) -> None:
		"""Apply persisted view toggles (grid visibility and snapping)."""
		grid_visible = bool(self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_VISIBLE,
			True,
		))
		grid_snap_enabled = bool(self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_GRID_SNAP_ENABLED,
			True,
		))
		for session in self._sessions:
			session.scene.set_grid_visible(grid_visible)
			session.scene.set_grid_snap_enabled(grid_snap_enabled)
		if hasattr(self, "_action_toggle_grid"):
			self._action_toggle_grid.setChecked(grid_visible)
		if hasattr(self, "_action_toggle_grid_snap"):
			self._action_toggle_grid_snap.setChecked(grid_snap_enabled)

	#============================================
	def refresh_recent_files_menu(self) -> None:
		"""Rebuild the Recent files submenu from preferences.

		Clears the existing submenu entries and repopulates from
		the stored recent files list. Each entry shows just the
		filename, with the full path as a tooltip. When the list
		is empty, shows a single disabled placeholder entry.
		"""
		if self._adapter.get_menu_component("Recent files") is None:
			return
		# read the current recent files list
		recent = self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_RECENT_FILES
		)
		# QSettings may return a string for single-item lists
		if recent is None:
			recent = []
		elif isinstance(recent, str):
			recent = [recent] if recent else []
		commands = []
		if not recent:
			commands.append((self.tr("(No recent files)"), None, False, None))
		else:
			for file_path in recent:
				# show just the filename as the menu label
				display_name = os.path.basename(file_path)
				def open_recent_file(
						_checked: bool = False, path: str = file_path,
						) -> None:
					"""Open the immutable path bound to one dynamic menu action."""
					self._open_recent_file(path)
				commands.append((display_name, open_recent_file, True, file_path))
		self._adapter.replace_cascade_commands("Recent files", commands)

	#============================================
	def _open_recent_file(self, file_path: str) -> None:
		"""Open a file from the recent files list.

		Verifies the file still exists before attempting to load.

		Args:
			file_path: Absolute path to the file to open.
		"""
		if not os.path.isfile(file_path):
			PySide6.QtWidgets.QMessageBox.warning(
				self, self.tr("File Not Found"),
				self.tr("The file no longer exists:\n%s") % file_path,
			)
			return
		self.open_file_path(file_path)

	#============================================
	def _on_preferences(self) -> None:
		"""Show the preferences dialog."""
		accepted = bkchem_qt.dialogs.preferences_dialog.PreferencesDialog \
			.show_preferences(self)
		if accepted:
			chosen_theme = str(self._prefs.value(
				bkchem_qt.config.preferences.Preferences.KEY_THEME,
				self._theme_manager.current_theme,
			))
			if chosen_theme != self._theme_manager.current_theme:
				self._theme_manager.apply_theme(chosen_theme)
			self._apply_geometry_preferences()
			self._apply_view_preferences()
			self.statusBar().showMessage(
				self.tr(
					"Preferences saved. Display and drawing changes are applied now; "
					"shortcuts are loaded when BKChem starts."
				),
				5000,
			)

	#============================================
	def _on_about(self) -> None:
		"""Show the About dialog."""
		bkchem_qt.dialogs.about_dialog.AboutDialog.show_about(self)

	#============================================
	def _on_element_changed(self, symbol: str) -> None:
		"""Forward element change from ribbon to active Draw/Atom mode.

		Args:
			symbol: New element symbol.
		"""
		symbol = str(symbol).strip()
		if not symbol:
			return
		mode = self._mode_manager.current_mode
		set_element = getattr(mode, "set_element", None)
		if callable(set_element):
			set_element(symbol)
			return
		if hasattr(mode, 'current_element'):
			try:
				mode.current_element = symbol
			except AttributeError:
				pass

	#============================================
	def _on_bond_order_changed(self, order: int) -> None:
		"""Forward bond order change from ribbon to draw mode.

		Args:
			order: New bond order.
		"""
		mode = self._mode_manager.current_mode
		if hasattr(mode, 'current_bond_order'):
			mode.current_bond_order = order

	#============================================
	def _on_bond_type_changed(self, bond_type: str) -> None:
		"""Forward bond type change from ribbon to draw mode.

		Args:
			bond_type: New bond type character.
		"""
		mode = self._mode_manager.current_mode
		if hasattr(mode, 'current_bond_type'):
			mode.current_bond_type = bond_type

	#============================================
	def restore_geometry(self) -> None:
		"""Restore window geometry from saved preferences.

		Only restores window size and position, not toolbar state,
		because toolbar layout changes between versions would conflict
		with stale saved state.
		"""
		geometry = self._prefs.value(
			bkchem_qt.config.preferences.Preferences.KEY_WINDOW_GEOMETRY
		)
		if geometry is not None:
			self.restoreGeometry(geometry)

	#============================================
	def prepare_application_shutdown(self) -> bool:
		"""Approve and start the one terminal MainWindow retirement sequence.

		Returns:
			True when every live session has entered the terminal reaper path.
			False when a Save, Recovery Export, or Cancel decision keeps the
			window live.

		This is the explicit application-lifetime boundary shared by an ordinary
		window close and an event loop that ends programmatically.  It owns the
		ordered Qt teardown only after the existing close decisions approve it.
		"""
		if self._shutdown_prepared:
			return True
		for session in tuple(self._sessions):
			if not self._confirm_save_if_dirty(
					"closing BKChem-Qt", session,
			):
				self._select_session(session)
				return False
		self._prefs.set_value(
			bkchem_qt.config.preferences.Preferences.KEY_WINDOW_GEOMETRY,
			self.saveGeometry(),
		)
		self._shutdown_prepared = True
		self._shutdown_state = ShutdownState.DRAINING
		self._stop_import_workers()
		try:
			self._clipboard.dataChanged.disconnect(self._on_clipboard_data_changed)
		except (RuntimeError, TypeError):
			pass
		if self._active_session is not None and self._ui_signals_connected:
			self._disconnect_active_session_signals(self._active_session)
		self._bind_property_dock(None)

		sessions = tuple(self._sessions)
		previous_block = self._tab_widget.blockSignals(True)
		self._tab_change_blocked = True
		try:
			for session in sessions:
				index = self._tab_widget.indexOf(session.view)
				if index >= 0:
					self._detach_tab_page(session, index)
			self._sessions.clear()
			self._sessions_by_view.clear()
			self._clear_active_session_aliases()
		finally:
			self._tab_change_blocked = False
			self._tab_widget.blockSignals(previous_block)

		for session in sessions:
			try:
				session.title_changed.disconnect(
					self._on_session_title_changed
				)
			except (RuntimeError, TypeError):
				pass
			self._shutdown_sessions_pending_disposal.append(session)
		self._emit_worker_retirement_drained()
		return True

	#============================================
	def closeEvent(self, event: PySide6.QtGui.QCloseEvent) -> None:
		"""Guard unsaved work and tear down Qt callbacks before closing.

		Args:
			event: The close event.
		"""
		if not self.prepare_application_shutdown():
			event.ignore()
			return
		super().closeEvent(event)

#============================================
def drain_pending_session_deletions(
		app: PySide6.QtWidgets.QApplication,
		target_window: object = None,
		max_passes: int = 4,
		) -> bool:
	"""Prove one live window's QObject reaper has released every record."""
	if target_window is None:
		raise ValueError("A MainWindow is required to prove reaper completion")
	while target_window._retired_import_workers:
		loop = PySide6.QtCore.QEventLoop()
		target_window.worker_retirement_drained.connect(loop.quit)
		if target_window._retired_import_workers:
			loop.exec()
		try:
			target_window.worker_retirement_drained.disconnect(loop.quit)
		except (RuntimeError, TypeError):
			pass
	for _pass in range(max_passes):
		target_window._resolve_pending_session_graphics()
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.DeferredDelete,
		)
		app.processEvents()
		if not target_window._pending_session_deletions:
			return True
	return False


#============================================
def delete_qobject_and_wait(
		app: PySide6.QtWidgets.QApplication,
		target: PySide6.QtCore.QObject,
		max_passes: int = 4,
		) -> bool:
	"""Queue one QObject deletion and prove its destroyed signal was delivered."""
	if not bkchem_qt.canvas.graphics_retirement.is_valid_native_wrapper(target):
		raise RuntimeError("Cannot retire an already-retired QObject")
	destroyed = []

	#============================================
	def record_destroyed(*_args: object) -> None:
		"""Record either PySide6 destroyed-signal signature."""
		destroyed.append(True)

	target.destroyed.connect(record_destroyed)
	target.deleteLater()
	for _pass in range(max_passes):
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.DeferredDelete,
		)
		app.processEvents()
		if destroyed:
			return True
	return False
