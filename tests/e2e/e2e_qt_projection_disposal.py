"""Exercise the native Qt projection teardown path outside the pytest fast lane."""

# Standard Library
import argparse
import gc
import math
import os

# PIP3 modules
import shiboken6


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.io.cdml_document_io
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.themes.theme_manager
import e2e_qt_lifecycle


_ARROW_CDML = (
	'<cdml version="0.15"><arrow id="arrow-1">'
	'<point x="1cm" y="1cm"/><point x="3cm" y="1cm"/>'
	'</arrow></cdml>'
)
_ARROW_AND_PLUS_CDML = (
	'<cdml version="0.15"><arrow id="arrow-1">'
	'<point x="1cm" y="1cm"/><point x="3cm" y="1cm"/>'
	'</arrow><plus id="plus-1"><point x="4cm" y="1cm"/>'
	'</plus></cdml>'
)
_RECT_CDML = (
	'<cdml version="0.15"><rect id="rect-1">'
	'<point x="1cm" y="1cm"/><point x="3cm" y="2cm"/>'
	'</rect></cdml>'
)


#============================================
def _persistent_arrow(
		scene: PySide6.QtWidgets.QGraphicsScene,
		) -> PySide6.QtWidgets.QGraphicsItem:
	"""Return the projected arrow with the durable fixture identifier."""
	for item in scene.items():
		if bkchem_qt.canvas.document_projection.persistent_selection_key(item) == (
				"presentation", "arrow-1",
			):
			return item
	raise RuntimeError("The fixture arrow was not projected")


#============================================
def _fail(message: str) -> int:
	"""Report a failed E2E lifecycle oracle and return a failure status."""
	print("FAIL: %s" % message)
	return 1


#============================================
class _RunDeadline:
	"""Bound one direct Qt E2E invocation, including nested modal event loops."""

	def __init__(
			self, app: PySide6.QtWidgets.QApplication, seconds: float,
			) -> None:
		"""Create the application-owned timer for one explicit E2E deadline."""
		self._app = app
		self._seconds = seconds
		self.expired = False
		self._timer = PySide6.QtCore.QTimer(app)
		self._timer.setSingleShot(True)
		self._timer.timeout.connect(self._expire)

	#============================================
	def start(self) -> None:
		"""Start the deadline before code can enter a nested modal event loop."""
		self._timer.start(round(self._seconds * 1000))

	#============================================
	def stop(self) -> None:
		"""Stop the deadline after the E2E returns through its normal path."""
		self._timer.stop()

	#============================================
	def _expire(self) -> None:
		"""Reject a nested dialog and request a bounded failing application exit."""
		self.expired = True
		print("FAIL: Qt projection disposal E2E exceeded %.1f seconds" % self._seconds)
		for widget in self._app.topLevelWidgets():
			if isinstance(widget, PySide6.QtWidgets.QDialog):
				widget.reject()
		self._app.exit(124)


#============================================
def _parse_args() -> argparse.Namespace:
	"""Read the explicit wall-clock budget for this direct Qt E2E program."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--kill-after", type=float, default=3.0, metavar="SECONDS",
		help="fail and leave nested Qt event loops after this many seconds (default: 3)",
	)
	args = parser.parse_args()
	if not math.isfinite(args.kill_after) or args.kill_after <= 0:
		parser.error("--kill-after requires a finite positive number of seconds")
	return args


#============================================
def _new_backend_candidate(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> tuple[object, object]:
	"""Open one blank tab and stage an arrow snapshot without projecting it."""
	main_window._on_new()
	session = main_window.sessions[-1]
	return session, session.commit_complete_candidate(_ARROW_CDML).snapshot


#============================================
def _fail_projection_install(
		_prepared: object, _selected_keys: frozenset[tuple[str, str]],
		_file_path: str | None, _projection_snapshot: object,
		) -> None:
	"""Make one exact-current projection installation fail."""
	raise RuntimeError("projection install failed")


#============================================
def _enter_unavailable_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> tuple[object, object, object] | None:
	"""Return an error-state session, snapshot, and original installer."""
	session, snapshot = _new_backend_candidate(main_window)
	original_install = session._install_prepared_projection
	session._install_prepared_projection = _fail_projection_install
	result = main_window._replace_session_projection(session, snapshot)
	if result.status == "installation-failed":
		return session, snapshot, original_install
	session._install_prepared_projection = original_install
	main_window._remove_session(session)
	return None


#============================================
def _restore_and_remove_error_session(
		main_window: bkchem_qt.main_window.MainWindow,
		session: object, snapshot: object, original_install: object,
		) -> bool:
	"""Repair a deliberately unavailable tab and remove it without a prompt."""
	session._install_prepared_projection = original_install
	if not session.has_live_projection:
		if not main_window._replace_session_projection(session, snapshot):
			return False
	return main_window._remove_session(session)


#============================================
def _unavailable_projection_contracts(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> int:
	"""Run error-tab, save, selection, and retry contracts outside pytest."""
	main_window._on_new()
	control_session = main_window.sessions[-1]
	pending_entry = None
	try:
		pending_entry = _enter_unavailable_projection(main_window)
		if pending_entry is None:
			return _fail("double installation failure did not report an error")
		session, snapshot, original_install = pending_entry
		if session.document is not None or session.projection_error is None:
			return _fail("double installation failure retained a live projection")
		if not _restore_and_remove_error_session(
				main_window, session, snapshot, original_install,
			):
			return _fail("unavailable projection could not be restored for cleanup")
		pending_entry = None

		pending_entry = _enter_unavailable_projection(main_window)
		if pending_entry is None:
			return _fail("save-refusal setup did not report an unavailable projection")
		session, snapshot, original_install = pending_entry
		try:
			session.write_backend_snapshot("unavailable.cdml")
		except bkchem_qt.models.document_session.BackendProjectionOutOfSyncError:
			pass
		else:
			return _fail("unavailable projection accepted a backend snapshot save")
		if not _restore_and_remove_error_session(
				main_window, session, snapshot, original_install,
			):
			return _fail("save-refusal error tab could not be removed")
		pending_entry = None

		pending_entry = _enter_unavailable_projection(main_window)
		if pending_entry is None:
			return _fail("tab-round-trip setup did not report an unavailable projection")
		session, snapshot, original_install = pending_entry
		if not (
				main_window._select_session(control_session)
				and main_window._select_session(session)
				and main_window._active_session is session
			):
			return _fail("unavailable projection lost its active binding after tab round-trip")
		if not _restore_and_remove_error_session(
				main_window, session, snapshot, original_install,
			):
			return _fail("tab-round-trip error tab could not be removed")
		pending_entry = None

		pending_entry = _enter_unavailable_projection(main_window)
		if pending_entry is None:
			return _fail("retry setup did not report an unavailable projection")
		session, snapshot, original_install = pending_entry
		session._install_prepared_projection = original_install
		if not (
				main_window._replace_session_projection(session, snapshot)
				and session.backend_projection_synchronized
				and session.has_live_projection
			):
			return _fail("unavailable projection did not rebuild from its backend snapshot")
		if not main_window._remove_session(session):
			return _fail("retried projection tab could not be removed")
		pending_entry = None
		return 0
	finally:
		if pending_entry is not None:
			session, snapshot, original_install = pending_entry
			_restore_and_remove_error_session(
				main_window, session, snapshot, original_install,
			)
		if control_session in main_window.sessions:
			main_window._remove_session(control_session)


#============================================
def _backend_arrow_projection_contract(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> int:
	"""Confirm an arrow backend commit replaces only the disposable projection."""
	main_window._on_new()
	session = main_window.sessions[-1]
	try:
		roots = (session, session.view, session.scene, session.mode_manager)
		commit = session.commit_complete_candidate(_ARROW_CDML)
		if not main_window._replace_session_projection(session, commit.snapshot):
			return _fail("backend arrow commit did not replace its projection")
		if roots != (session, session.view, session.scene, session.mode_manager):
			return _fail("backend arrow commit replaced persistent tab roots")
		_persistent_arrow(session.scene)
		return 0
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def _selection_restore_contract(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> int:
	"""Confirm selection follows a durable CDML ID across projection rebuilds."""
	main_window._on_new()
	session = main_window.sessions[-1]
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		if not main_window._replace_session_projection(session, first.snapshot):
			return _fail("selection restore setup did not project the arrow")
		old_item = _persistent_arrow(session.scene)
		old_item.setSelected(True)
		second = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)
		if not main_window._replace_session_projection(session, second.snapshot):
			return _fail("selection restore second projection was refused")
		new_item = _persistent_arrow(session.scene)
		if new_item is old_item or not new_item.isSelected():
			return _fail("selection did not follow the durable arrow identifier")
		return 0
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def _install_failure_recovery_contract(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> int:
	"""Confirm a post-retirement fault needs one explicit exact-current retry."""
	main_window._on_new()
	session = main_window.sessions[-1]
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		if not main_window._replace_session_projection(session, first.snapshot):
			return _fail("install-recovery setup did not project the arrow")
		old_document = session.document
		second = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)
		original_install = session._install_prepared_projection
		calls = []

		def fail_once(
				prepared: object, selected_keys: frozenset[tuple[str, str]],
				file_path: str | None, projection_snapshot: object,
				) -> None:
			"""Fail once, then allow the explicit exact-current retry to install."""
			calls.append(prepared)
			if len(calls) == 1:
				raise RuntimeError("install failed")
			original_install(prepared, selected_keys, file_path, projection_snapshot)

		session._install_prepared_projection = fail_once
		replaced = main_window._replace_session_projection(session, second.snapshot)
		if (
				replaced
			or session.document is old_document
			or session.backend_projection_synchronized
			or session.document is not None
			or main_window._property_dock._document is not None
			):
			return _fail("install fault did not leave projection-unavailable")
		retry = session.retry_current_backend_projection()
		session._install_prepared_projection = original_install
		recovery_arrow = _persistent_arrow(session.scene)
		if (
				retry.status != "accepted"
			or len(calls) != 2
			or session.document is old_document
			or not session.backend_projection_synchronized
			or recovery_arrow.scene() is not session.scene
			or main_window._property_dock._document is not session.document
			):
			return _fail("explicit retry did not install the current backend projection")
		return 0
	finally:
		if "original_install" in locals():
			session._install_prepared_projection = original_install
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def _detached_builder_retry_contract(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> int:
	"""Confirm a detached-builder failure preserves the old projection for retry."""
	main_window._on_new()
	session = main_window.sessions[-1]
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		if not main_window._replace_session_projection(session, first.snapshot):
			return _fail("detached-builder retry setup could not project the arrow")
		old_document = session.document
		selected_item = _persistent_arrow(session.scene)
		selected_item.setSelected(True)
		second = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)
		original_builder = bkchem_qt.io.cdml_document_io.prepare_synchronized_projection

		def fail_builder(_cdml: str, _observations: object, _reaper: object) -> object:
			"""Fail before the replacement candidate reaches the live scene."""
			raise RuntimeError("detached builder failed")

		bkchem_qt.io.cdml_document_io.prepare_synchronized_projection = fail_builder
		result = main_window._replace_session_projection(session, second.snapshot)
		if result.status != "preparation-unavailable":
			return _fail("detached-builder fault did not report preparation-unavailable")
		if (
				session.document is not old_document
				or not selected_item.isSelected()
				or main_window._property_dock._document is not None
				or session.backend_projection_synchronized
			):
			return _fail("detached-builder fault did not retain only a view-only projection")
		bkchem_qt.io.cdml_document_io.prepare_synchronized_projection = original_builder
		if not main_window._replace_session_projection(session, second.snapshot):
			return _fail("detached-builder retry did not install the backend candidate")
		return 0
	finally:
		if "original_builder" in locals():
			bkchem_qt.io.cdml_document_io.prepare_synchronized_projection = original_builder
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def _rectangle_replacement_close_contract(
		main_window: bkchem_qt.main_window.MainWindow,
		app: PySide6.QtWidgets.QApplication,
		) -> int:
	"""Exercise the multi-stage rectangle replacement and terminal close path."""
	main_window._on_new()
	session = main_window.sessions[-1]
	try:
		rectangle_commit = session.commit_complete_candidate(_RECT_CDML)
		if not main_window._replace_session_projection(
			session, rectangle_commit.snapshot,
		):
			return _fail("rectangle replacement did not project the rectangle")
		arrow_commit = session.commit_complete_candidate(_ARROW_CDML)
		if not main_window._replace_session_projection(session, arrow_commit.snapshot):
			return _fail("rectangle replacement did not project the arrow")
		if session.document.presentation_objects[0].kind != "arrow":
			return _fail("rectangle replacement did not project the arrow")
		saved = session._backend_session.mark_saved(
			expected_revision=session.backend_snapshot.revision,
		)
		session._projected_backend_snapshot = saved
		session._backend_projection_synchronized = True
		session.document.mark_clean()
		if not main_window.close_session_at(main_window.sessions.index(session)):
			return _fail("rectangle replacement session did not close")
		if not e2e_qt_lifecycle.drain_main_window_deletions(app, main_window):
			return _fail("rectangle replacement session remained in the reaper")
		return 0
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def main(kill_after: float) -> int:
	"""Confirm faulty old-projection teardown cannot retain stale Qt state."""
	app = PySide6.QtWidgets.QApplication.instance()
	if app is None:
		app = PySide6.QtWidgets.QApplication([])
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)
	deadline = _RunDeadline(app, kill_after)
	deadline.start()
	main_window._on_new()
	session = main_window.sessions[-1]
	old_document = None
	middle_document = None
	old_item = None
	try:
		first = session.commit_complete_candidate(_ARROW_CDML)
		if not main_window._replace_session_projection(session, first.snapshot):
			return _fail("first backend projection replacement was refused")
		old_document = session.document
		old_item = _persistent_arrow(session.scene)
		old_item_scene = old_item.scene()
		old_item_parent = old_item.parentItem()
		old_item_binding_was_connected = old_item._projection_binding._connected
		original_dispose = old_document._dispose_document_graphics

		def dispose_then_fail(reaper: object) -> None:
			"""Fault after old graphics have detached from their live scene."""
			original_dispose(reaper)
			raise RuntimeError("old projection disposal failed")

		old_document._dispose_document_graphics = dispose_then_fail
		second = session.commit_complete_candidate(_ARROW_AND_PLUS_CDML)
		if main_window._replace_session_projection(session, second.snapshot):
			return _fail("old-projection disposal fault did not report failure")
		middle_document = session.document
		failure_reasons = []
		if old_item_scene is not session.scene:
			failure_reasons.append("fixture arrow was not attached to its original scene")
		if old_item_parent is not None:
			failure_reasons.append("fixture arrow unexpectedly had a graphics parent")
		if not old_item_binding_was_connected:
			failure_reasons.append("fixture arrow callback was not connected")
		if old_document.parent() is not None:
			failure_reasons.append("old document retained a QObject parent")
		if old_document._scene is not None:
			failure_reasons.append("old document retained its scene")
		if old_item._projection_binding is not None:
			failure_reasons.append("old arrow callback remained connected")
		if middle_document is not None or main_window.document is not None:
			failure_reasons.append("post-retirement failure retained a live document")
		if session.backend_projection_synchronized:
			failure_reasons.append("post-retirement failure claimed synchronization")
		if failure_reasons:
			return _fail(
				"old projection did not reach terminal retirement: "
				+ "; ".join(failure_reasons),
			)
		retry = session.retry_current_backend_projection()
		if retry.status != "accepted":
			return _fail("explicit exact-current projection retry was refused")
		middle_document = session.document
		retried_arrow = _persistent_arrow(session.scene)
		if (
			middle_document is old_document
			or retried_arrow is old_item
			or not session.backend_projection_synchronized
			or session.backend_snapshot != second.snapshot
		):
			return _fail("exact-current retry reused terminal old projection ownership")
		if not main_window._remove_session(session):
			return _fail("projection tab removal was refused")
		if not e2e_qt_lifecycle.drain_main_window_deletions(app, main_window):
			return _fail("projection tab remained in the session reaper")
		gc.collect()
		if shiboken6.isValid(old_document) or shiboken6.isValid(middle_document):
			return _fail("obsolete projection documents remained valid after close")
		if shiboken6.isValid(old_item):
			return _fail("obsolete arrow native wrapper remained valid after close")
		if _backend_arrow_projection_contract(main_window) != 0:
			return 1
		if _selection_restore_contract(main_window) != 0:
			return 1
		if _install_failure_recovery_contract(main_window) != 0:
			return 1
		if _detached_builder_retry_contract(main_window) != 0:
			return 1
		if _unavailable_projection_contracts(main_window) != 0:
			return 1
		if _rectangle_replacement_close_contract(main_window, app) != 0:
			return 1
		if deadline.expired:
			return 124
		print("PASS: old projection disposal fault required one exact-current retry")
		return 0
	finally:
		try:
			e2e_qt_lifecycle.shutdown_main_window(app, main_window)
		except RuntimeError:
			if not deadline.expired:
				raise
		finally:
			deadline.stop()
		if deadline.expired:
			return 124


if __name__ == "__main__":
	raise SystemExit(main(_parse_args().kill_after))
