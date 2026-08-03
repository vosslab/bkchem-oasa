"""Exercise the full Qt Arrow Mode route through backend CDML authority."""

# Standard Library
import collections.abc
import contextlib
import os
import pathlib


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtTest
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.backend_revision_history
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.themes.theme_manager
import e2e_qt_lifecycle


_OPAQUE_XML = '<x:note keep="yes"><x:payload>opaque</x:payload></x:note>'
_MIXED_CDML = (
	'<cdml xmlns="http://www.freesoftware.fsf.org/bkchem/cdml" '
	'xmlns:x="urn:authority-e2e" version="0.15">'
	'<molecule id="mol-1"><atom id="atom-1" name="C">'
	'<point x="1cm" y="1cm"/></atom></molecule>'
	+ _OPAQUE_XML
	+ '</cdml>'
)


#============================================
#============================================
def _install_projection_port(session: object, deliver: object) -> None:
	"""Install one fresh typed projection lifecycle port for this session."""
	port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
		session, deliver,
	)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(snapshot: object) -> object:
	"""Report one deliberately unavailable typed projection outcome."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
	)


def _fail(message: str) -> int:
	"""Print one actionable E2E failure and return a nonzero status."""
	print("FAIL: %s" % message, flush=True)
	return 1


#============================================
#============================================
def _draw_arrow(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Submit one normal Arrow Mode gesture and retain its real action outcome."""
	outcomes = []
	main_window._mode_manager.set_mode("arrow")
	mode = main_window._mode_manager.current_mode
	original_operation = mode._persistent_operation
	if original_operation is None:
		raise RuntimeError("Arrow Mode has no setup-installed persistent session action")

	def capture_outcome(request: object) -> object:
		"""Call the setup-installed immutable operation and record its result."""
		outcome = original_operation(request)
		outcomes.append(outcome)
		return outcome

	mode.set_persistent_operation(capture_outcome)
	try:
		mode.mouse_press(PySide6.QtCore.QPointF(20.0, 30.0), object())
		mode.mouse_release(PySide6.QtCore.QPointF(120.0, 30.0), object())
	finally:
		mode.set_persistent_operation(original_operation)
	if len(outcomes) != 1:
		raise RuntimeError("Arrow Mode did not invoke its persistent session action")
	return outcomes[0]


#============================================
class _LegacyMarkerCommand(PySide6.QtGui.QUndoCommand):
	"""Record the legacy stack branch chosen by real QAction entry points."""

	#============================================
	def __init__(self, marker: list[str]) -> None:
		"""Keep the marker outside graphics so the E2E can inspect it safely."""
		super().__init__("legacy marker")
		self._marker = marker

	#============================================
	def redo(self) -> None:
		"""Record legacy redo delivery."""
		self._marker.append("redo")

	#============================================
	def undo(self) -> None:
		"""Record legacy undo delivery."""
		self._marker.append("undo")


#============================================
def _arrow_model(main_window: bkchem_qt.main_window.MainWindow) -> object | None:
	"""Return the current projected arrow model, if any."""
	for item in main_window.document.presentation_objects:
		if item.kind == "arrow":
			return item
	return None


#============================================
def _menu_action(main_window: bkchem_qt.main_window.MainWindow, key: str) -> object:
	"""Return one real registered menu QAction or fail loudly."""
	action = main_window._adapter.get_action_by_key(key)
	if action is None:
		raise RuntimeError("Missing registered QAction '%s'" % key)
	return action


#============================================
def _keyboard_action(
		app: PySide6.QtWidgets.QApplication,
		main_window: bkchem_qt.main_window.MainWindow, key: int,
		modifiers: PySide6.QtCore.Qt.KeyboardModifier,
		) -> None:
	"""Deliver a real menu-QAction shortcut through the focused window."""
	main_window.show()
	main_window.activateWindow()
	main_window.setFocus()
	app.processEvents()
	PySide6.QtTest.QTest.keyClick(main_window, key, modifiers)
	app.processEvents()


#============================================
def _open_native_without_opaque_modal(
		main_window: bkchem_qt.main_window.MainWindow, path: pathlib.Path,
		) -> bool:
	"""Use native open while suppressing only the known opaque-content modal."""
	original_warning = PySide6.QtWidgets.QMessageBox.warning
	PySide6.QtWidgets.QMessageBox.warning = lambda *_args: None
	try:
		opened = main_window.open_file_path(str(path))
	finally:
		PySide6.QtWidgets.QMessageBox.warning = original_warning
	return opened


#============================================
@contextlib.contextmanager
def _e2e_discard_close_decision(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> collections.abc.Iterator[list[str]]:
	"""Provide temporary close decisions and record their production seam."""
	original_question = PySide6.QtWidgets.QMessageBox.question
	original_recovery_choice = main_window._recovery_export_close_choice
	decisions = []

	def choose_discard(*_args: object) -> PySide6.QtWidgets.QMessageBox.StandardButton:
		"""Choose Discard through the ordinary production close prompt."""
		decisions.append("ordinary-discard")
		return PySide6.QtWidgets.QMessageBox.StandardButton.Discard

	def choose_recovery_discard(_message: str) -> str:
		"""Choose Discard from the production Recovery Export close prompt."""
		decisions.append("recovery-export-discard")
		return "discard"

	PySide6.QtWidgets.QMessageBox.question = choose_discard
	main_window._recovery_export_close_choice = choose_recovery_discard
	try:
		yield decisions
	finally:
		PySide6.QtWidgets.QMessageBox.question = original_question
		main_window._recovery_export_close_choice = original_recovery_choice


#============================================
def _backend_navigation_contract(
		app: PySide6.QtWidgets.QApplication,
		main_window: bkchem_qt.main_window.MainWindow,
		) -> int:
	"""Check real mode commit plus menu, toolbar, and keyboard routing."""
	session = main_window._active_session
	outcome = _draw_arrow(main_window)
	first_model = _arrow_model(main_window)
	if outcome.status != "accepted" or outcome.commit is None or first_model is None:
		return _fail("real Arrow Mode did not return an accepted projected backend commit")
	provisional = "__bkchem_new__arrow-r0-1"
	durable_id = outcome.commit.id_map.get(provisional)
	if (
		durable_id is None
		or first_model.object_id != durable_id
		or provisional in outcome.commit.snapshot.cdml
		or durable_id not in session.backend_snapshot.cdml
	):
		return _fail("projected arrow ID did not come from the backend commit id_map")
	if (
		main_window.document.undo_stack.canUndo()
		or not main_window._undo_action.isEnabled()
		or not main_window._registry.is_enabled("edit.undo", main_window)
	):
		return _fail("accepted arrow did not select backend-only undo ownership")
	_menu_action(main_window, "edit.undo").trigger()
	if _arrow_model(main_window) is not None or not main_window._redo_action.isEnabled():
		return _fail("registered Undo menu QAction did not route through backend restore")
	main_window._redo_action.trigger()
	second_model = _arrow_model(main_window)
	if second_model is None or second_model is first_model:
		return _fail("toolbar Redo QAction did not install a fresh backend projection")
	_keyboard_action(
		app, main_window, PySide6.QtCore.Qt.Key.Key_Z,
		PySide6.QtCore.Qt.KeyboardModifier.ControlModifier,
	)
	if _arrow_model(main_window) is not None:
		return _fail("Ctrl+Z shortcut did not invoke backend Undo")
	_keyboard_action(
		app, main_window, PySide6.QtCore.Qt.Key.Key_Z,
		PySide6.QtCore.Qt.KeyboardModifier.ControlModifier
		| PySide6.QtCore.Qt.KeyboardModifier.ShiftModifier,
	)
	if _arrow_model(main_window) is None:
		return _fail("Ctrl+Shift+Z shortcut did not invoke backend Redo")
	return 0


#============================================
def _save_and_reopen_contract(
		app: PySide6.QtWidgets.QApplication,
		main_window: bkchem_qt.main_window.MainWindow, target: pathlib.Path,
		) -> int:
	"""Use the authoritative Save gate, then the native Open/install route."""
	session = main_window._active_session
	saved_arrow = _arrow_model(main_window)
	if not main_window._save_session_to_path(session, str(target)):
		return _fail("production authoritative Save gate rejected an accepted arrow")
	saved_cdml = target.read_text(encoding="utf-8")
	if _OPAQUE_XML not in saved_cdml or session.backend_snapshot.is_dirty:
		return _fail("production Save did not retain opaque CDML or mark backend clean")
	main_window._on_new()
	index = main_window.sessions.index(session)
	if not main_window.close_session_at(index):
		return _fail("clean authoritative Save session did not close before reopen")
	if not e2e_qt_lifecycle.drain_main_window_deletions(app, main_window):
		return _fail("saved session remained in the production session reaper")
	if not _open_native_without_opaque_modal(main_window, target):
		return _fail("production native Open route did not install the saved CDML")
	reopened = main_window._active_session
	arrow = _arrow_model(main_window)
	if (
		reopened is session
		or _OPAQUE_XML not in reopened.backend_snapshot.cdml
		or reopened.backend_snapshot.is_dirty
		or arrow is None
		or arrow is saved_arrow
		or arrow.object_id not in reopened.backend_snapshot.cdml
	):
		return _fail("native reopen did not reconstruct a distinct clean CDML projection")
	return 0


#============================================
def _unavailable_and_isolation_contract(
		app: PySide6.QtWidgets.QApplication,
		main_window: bkchem_qt.main_window.MainWindow,
		) -> int:
	"""Exercise C2 recovery, legacy isolation, and no-fallback endpoint failure."""
	main_window._on_new()
	session = main_window._active_session
	restore_delivery = lambda snapshot: main_window._replace_session_projection(session, snapshot)
	_install_projection_port(session, _projection_unavailable)
	try:
		outcome = session.commit_arrow((20.0, 30.0), (120.0, 30.0))
		if (
			outcome.status != "unavailable"
			or not session.has_backend_navigation
			or session.can_write_authoritative_snapshot
			or main_window.can_undo()
		):
			return _fail("post-acceptance unavailable projection still exposed Save or navigation")
		_install_projection_port(session, restore_delivery)
		if (
			session.retry_current_backend_projection().status != "accepted"
			or not session.can_write_authoritative_snapshot
			or not main_window.can_undo()
		):
			return _fail("literal-true retry did not restore authoritative Save and navigation")
		marker = []
		session.document.undo_stack.push(_LegacyMarkerCommand(marker))
		_menu_action(main_window, "edit.undo").trigger()
		main_window._redo_action.trigger()
		_keyboard_action(
			app, main_window, PySide6.QtCore.Qt.Key.Key_Z,
			PySide6.QtCore.Qt.KeyboardModifier.ControlModifier,
		)
		if marker[-3:] != ["undo", "redo", "undo"] or not session.legacy_isolated:
			return _fail("legacy-isolated QAction paths did not use only the Qt stack")
		original_question = PySide6.QtWidgets.QMessageBox.question
		PySide6.QtWidgets.QMessageBox.question = lambda *_args: (
			PySide6.QtWidgets.QMessageBox.StandardButton.Yes
		)
		try:
			outcome = main_window.discard_legacy_and_retry_projection(session)
		finally:
			PySide6.QtWidgets.QMessageBox.question = original_question
		if outcome is None or outcome.status != "accepted":
			return _fail("confirmed discard did not restore the backend projection")
		session.document.undo_stack.push(_LegacyMarkerCommand(marker))
		session._legacy_isolated = False
		before_revision = session.backend_snapshot.revision
		session._backend_history = (
			bkchem_qt.models.backend_revision_history.BackendRevisionHistory(
				(
					bkchem_qt.models.backend_revision_history.BackendHistoryEntry(
						"unavailable Arrow", 999,
					),
					bkchem_qt.models.backend_revision_history.BackendHistoryEntry(
						"current Arrow", before_revision,
					),
				),
				1,
			)
		)
		_menu_action(main_window, "edit.undo").trigger()
		if session.backend_snapshot.revision != before_revision or marker[-1:] == ["undo"]:
			return _fail("unavailable backend Undo endpoint fell through to Qt history")
		if session.retry_current_backend_projection().status != "accepted":
			return _fail("exact backend reprojection did not restore Arrow Save provenance")
		return 0
	finally:
		if not session.is_disposed:
			_install_projection_port(session, restore_delivery)


#============================================
def _coordinator_teardown_contract(
		app: PySide6.QtWidgets.QApplication,
		main_window: bkchem_qt.main_window.MainWindow,
		) -> int:
	"""Close the arrow-bearing exercised tab and prove callback disposal."""
	session = main_window._active_session
	if _arrow_model(main_window) is None:
		return _fail("teardown target does not retain an arrow-bearing projection")
	state = session.close_state()
	if (
		not session.backend_snapshot.is_dirty
		or not state.backend_dirty
		or not state.authoritative_save_eligible
	):
		return _fail(
			"accepted Arrow document was not backend-dirty and Save-eligible before "
			"close (snapshot_dirty=%s, state_dirty=%s, save_eligible=%s)" % (
				session.backend_snapshot.is_dirty,
				state.backend_dirty,
				state.authoritative_save_eligible,
			),
		)
	main_window._on_new()
	index = main_window.sessions.index(session)
	with _e2e_discard_close_decision(main_window) as decisions:
		closed = main_window.close_session_at(index)
	if not closed:
		return _fail("arrow-bearing tab did not close through the production lifecycle")
	if "ordinary-discard" not in decisions:
		return _fail("dirty Arrow tab did not invoke the ordinary production Discard decision")
	if not e2e_qt_lifecycle.drain_main_window_deletions(app, main_window):
		return _fail("arrow-bearing session remained in the production session reaper")
	if session.can_commit_persistent_action:
		return _fail("closed arrow-bearing session retained projection capability")
	return 0


#============================================
def main() -> int:
	"""Run the M3 arrow route with real Qt projections outside pytest's fast lane."""
	repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
	tmp_dir = pathlib.Path(repo_root) / "tmp" / "authority_m3"
	tmp_dir.mkdir(parents=True, exist_ok=True)
	source = tmp_dir / "arrow-authority-source.cdml"
	target = tmp_dir / "arrow-authority-saved.cdml"
	source.write_text(_MIXED_CDML, encoding="utf-8")
	app = PySide6.QtWidgets.QApplication.instance()
	if app is None:
		app = PySide6.QtWidgets.QApplication([])
	theme_manager = bkchem_qt.themes.theme_manager.ThemeManager(app)
	main_window = bkchem_qt.main_window.MainWindow(theme_manager)
	try:
		if not _open_native_without_opaque_modal(main_window, source):
			return _fail("production native Open route did not load mixed backend CDML")
		if _backend_navigation_contract(app, main_window) != 0:
			return 1
		if _save_and_reopen_contract(app, main_window, target) != 0:
			return 1
		if _unavailable_and_isolation_contract(app, main_window) != 0:
			return 1
		if _coordinator_teardown_contract(app, main_window) != 0:
			return 1
		print("PASS: Arrow Mode uses backend CDML authority and disposable Qt projections")
		return 0
	finally:
		with _e2e_discard_close_decision(main_window):
			e2e_qt_lifecycle.shutdown_main_window(app, main_window)
		for path in (source, target):
			if path.exists():
				path.unlink()


if __name__ == "__main__":
	raise SystemExit(main())
