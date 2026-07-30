"""Focused save-cancellation behavior coverage."""

# Standard Library
import pathlib

# PIP3 modules
import pytest
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document_session


#============================================
def _force_projection_unavailable(
		main_window: bkchem_qt.main_window.MainWindow,
		session: bkchem_qt.models.document_session.DocumentSession,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Enter typed projection-unavailable through the production replacement path."""
	original_installer = session._install_prepared_projection

	def reject_installation(*_args: object, **_kwargs: object) -> None:
		"""Make the requested installation fail after safe disposal."""
		raise RuntimeError("controlled projection installation failure")

	monkeypatch.setattr(session, "_install_prepared_projection", reject_installation)
	try:
		result = main_window._replace_session_projection(session, session.backend_snapshot)
		if result.status != "installation-failed":
			raise RuntimeError("Controlled replacement did not report installation-failed")
	finally:
		monkeypatch.setattr(session, "_install_prepared_projection", original_installer)
	if session.document is not None or session._projection_error is None:
		raise RuntimeError("Projection replacement did not enter projection-unavailable")


#============================================
def test_recovery_export_cancellation_blocks_ineligible_tab_close(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Cancelling the required recovery choice leaves its local tab intact."""
	main_window._on_new()
	target = main_window._active_session
	target.document.mark_dirty()
	monkeypatch.setattr(
		main_window,
		"_recovery_export_close_choice",
		lambda _message: "cancel",
	)

	assert not main_window.close_current_tab()
	assert target in main_window.sessions
	monkeypatch.setattr(
		main_window,
		"_recovery_export_close_choice",
		lambda _message: "discard",
	)
	assert main_window.close_current_tab()
	assert bkchem_qt.main_window.drain_pending_session_deletions(
		PySide6.QtWidgets.QApplication.instance(), main_window,
	)


#============================================
def test_recovery_export_action_rejects_a_switched_captured_session(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Recovery Export never retargets a newly active tab after its path prompt."""
	captured = main_window._active_session
	calls = []

	def switch_tab_then_return_path(*_args: object, **_kwargs: object) -> tuple[str, str]:
		"""Model a tab switch while the modal destination picker is open."""
		main_window._on_new()
		return ("recovery.cdml", "")

	def record_export(_path: str) -> object:
		"""Record any impermissible publication after the stale callback."""
		calls.append(_path)
		return captured.backend_snapshot

	monkeypatch.setattr(
		PySide6.QtWidgets.QFileDialog, "getSaveFileName", switch_tab_then_return_path,
	)
	monkeypatch.setattr(captured, "export_backend_snapshot", record_export)

	assert main_window.can_recovery_export() is True
	assert (main_window._on_recovery_export(), calls) == (False, [])


#============================================
def test_recovery_export_rejects_a_backend_snapshot_failure_at_the_close_boundary(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A malformed backend rejects action and close eligibility without escaping."""
	main_window._on_new()
	session = main_window._active_session

	def fail_snapshot() -> object:
		"""Model one backend adapter whose snapshot query cannot complete."""
		raise ValueError("malformed backend handle")

	monkeypatch.setattr(session._backend_session, "snapshot", fail_snapshot)

	assert (
		session.can_recovery_export,
		main_window.can_recovery_export(),
		main_window.close_current_tab(),
	) == (False, False, False)


#============================================
def test_recovery_export_close_dialog_queues_explicit_cleanup(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The close prompt returns its choice and queues its owned dialog once."""
	original_box = PySide6.QtWidgets.QMessageBox
	cleanup_calls = []

	class ImmediateExportDialog:
		"""Controlled QMessageBox replacement that never enters a native modal loop."""

		ButtonRole = original_box.ButtonRole
		StandardButton = original_box.StandardButton

		def __init__(self, _parent: object) -> None:
			"""Construct one controlled dialog owned by the production helper."""
			self._export_button = object()
			self._discard_button = object()

		def setWindowTitle(self, _title: str) -> None:
			"""Accept the production title configuration."""

		def setText(self, _message: str) -> None:
			"""Accept the production explanatory text."""

		def addButton(self, button: object, *_args: object) -> object:
			"""Return stable controlled buttons for the production comparison."""
			if button == self.StandardButton.Discard:
				return self._discard_button
			return self._export_button

		def exec(self) -> int:
			"""Complete immediately without starting a native event loop."""
			return 0

		def clickedButton(self) -> object:
			"""Select Recovery Export deterministically."""
			return self._export_button

		def deleteLater(self) -> None:
			"""Record explicit deferred QObject disposal."""
			cleanup_calls.append("queued")

	monkeypatch.setattr(PySide6.QtWidgets, "QMessageBox", ImmediateExportDialog)

	assert (
		main_window._recovery_export_close_choice("backend recovery required"),
		cleanup_calls,
	) == ("export", ["queued"])


#============================================
def test_projection_unavailable_recovery_export_close_removes_exact_session(
		main_window: bkchem_qt.main_window.MainWindow,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A successful inactive close exports only its captured unavailable session."""
	target = main_window._active_session
	main_window._on_new()
	companion = main_window._active_session
	destination = tmp_path / "captured-recovery.cdml"
	target.commit_complete_candidate('<cdml version="0.15"><arrow id="a"/></cdml>')
	captured_snapshot = target.backend_snapshot
	_force_projection_unavailable(main_window, target, monkeypatch)
	monkeypatch.setattr(main_window, "_recovery_export_close_choice", lambda _message: "export")
	monkeypatch.setattr(
		PySide6.QtWidgets.QFileDialog,
		"getSaveFileName",
		lambda *_args, **_kwargs: (str(destination), ""),
	)

	assert main_window.close_session_at(main_window.sessions.index(target))
	assert (
		destination.read_text(encoding="utf-8"),
		target in main_window.sessions,
		target.is_disposed,
		companion in main_window.sessions,
		companion.is_disposed,
	) == (captured_snapshot.cdml, False, True, True, False)


#============================================
def test_recovery_export_action_is_enabled_without_projection_and_disabled_on_disposal(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The File action follows session liveness, not Qt projection availability."""
	main_window._on_new()
	session = main_window._active_session
	try:
		_force_projection_unavailable(main_window, session, monkeypatch)
		assert main_window.can_recovery_export()
		main_window._remove_session(session)
		assert main_window._registered_recovery_export_session(
			session, require_active=False,
		) is None
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)
		assert bkchem_qt.main_window.drain_pending_session_deletions(
			PySide6.QtWidgets.QApplication.instance(), main_window,
		)


#============================================
def test_legacy_close_discloses_excluded_qt_local_edits_without_a_modal_loop(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Legacy close uses the injectable choice seam and direct Discard disposal."""
	main_window._on_new()
	session = main_window._active_session
	messages = []

	def choose_discard(message: str) -> str:
		"""Capture the explanatory text without entering a Qt modal event loop."""
		messages.append(message)
		return "discard"

	def reject_save(_session: object) -> bool:
		"""Reject an impermissible authoritative Save route."""
		raise AssertionError("legacy close invoked authoritative Save")

	session._on_persistent_mutated(0)
	monkeypatch.setattr(main_window, "_recovery_export_close_choice", choose_discard)
	monkeypatch.setattr(main_window, "_save_session", reject_save)

	assert main_window.close_current_tab()
	assert (
		"Recovery Export saves the backend document only; Qt-local edits are excluded."
		in messages[0]
		and session.is_disposed
	)


#============================================
def test_post_replace_recovery_export_failure_keeps_the_tab_open(
		main_window: bkchem_qt.main_window.MainWindow,
		tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An unconfirmed replacement reports export facts and blocks close."""
	session = main_window._active_session
	warnings = []

	def choose_export(_message: str) -> str:
		"""Select Recovery Export without entering a modal event loop."""
		return "export"

	def fail_after_replace(_path: str) -> object:
		"""Model the atomic writer's post-replacement durability failure."""
		raise bkchem_qt.models.document_session.BackendSnapshotPublicationError(
			"directory durability failed",
		)

	def capture_warning(*args: object, **_kwargs: object) -> None:
		"""Capture the user-visible partial-publication diagnostic."""
		warnings.append(args[2])

	try:
		session._on_persistent_mutated(0)
		monkeypatch.setattr(main_window, "_recovery_export_close_choice", choose_export)
		monkeypatch.setattr(session, "export_backend_snapshot", fail_after_replace)
		monkeypatch.setattr(
			PySide6.QtWidgets.QFileDialog,
			"getSaveFileName",
			lambda *_args, **_kwargs: (str(tmp_path / "uncertain.cdml"), ""),
		)
		monkeypatch.setattr(PySide6.QtWidgets.QMessageBox, "warning", capture_warning)

		assert not main_window.close_current_tab()
		assert (
			session in main_window.sessions
			and "exact canonical snapshot may be present" in warnings[0]
			and "durability is unconfirmed" in warnings[0]
			and "No session state changed; the tab remains open" in warnings[0]
		)
	finally:
		# Leave the shared window fixture synchronized for controlled teardown.
		saved = session._backend_session.mark_saved(
			expected_revision=session.backend_snapshot.revision,
		)
		session._legacy_isolated = False
		session._backend_projection_synchronized = True
		session._projected_backend_snapshot = saved
		session.document.mark_clean()


#============================================
def test_projection_unavailable_recovery_failure_retains_the_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed Recovery Export blocks close even without a live Qt document."""
	session = main_window._active_session
	calls = []
	main_window._on_new()
	main_window._select_session(session)

	def reject_recovery(
			_operation: str, target: object, _state: object,
			) -> bool:
		"""Model a cancelled or failed Recovery Export publication."""
		calls.append(target)
		return False

	try:
		session.commit_complete_candidate('<cdml version="0.15"><arrow id="a"/></cdml>')
		_force_projection_unavailable(main_window, session, monkeypatch)
		monkeypatch.setattr(main_window, "_confirm_recovery_export_or_discard", reject_recovery)
		assert not main_window.close_current_tab()
		assert (calls, session in main_window.sessions) == ([session], True)
	finally:
		# Dispose the unavailable session through production tab removal.
		if session in main_window.sessions:
			main_window._remove_session(session)
