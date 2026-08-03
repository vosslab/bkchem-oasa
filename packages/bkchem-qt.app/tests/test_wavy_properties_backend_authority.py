"""Focused Qt behavior for backend-authoritative plain Wavy Configure."""

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.actions.object_actions
import bkchem_qt.dialogs.wavy_dialog
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle


_CDML = (
	'<cdml version="26.07"><polyline id="w1" style="wavy" width="1.5" '
	'line_color="#112233" spline="no" keep="yes"><point x="1cm" y="1cm"/>'
	'<point x="2cm" y="2cm"/></polyline></cdml>'
)


#============================================
def _install_native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Register one projected native-CDML session with a durable plain Wavy."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native Wavy CDML projection is unavailable")
	return registered


#============================================
def _wavy_item(session: object) -> object:
	"""Return the current durable Wavy graphics projection."""
	for item in session.scene.items():
		model = getattr(item, "document_object_model", None)
		if getattr(model, "object_id", None) == "w1":
			return item
	raise AssertionError("Projected CDML did not produce the durable Wavy item")


#============================================
def _selected_wavy_ids(session: object) -> set[str]:
	"""Return durable IDs selected in the current replacement projection."""
	return {
		item.document_object_model.object_id for item in session.scene.selectedItems()
		if getattr(item, "document_object_model", None) is not None
	}


#============================================
def test_object_configure_uses_backend_history_and_restores_wavy_selection(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Configure reprojects one accepted Wavy patch without local undo ownership."""
	session = _install_native_session(main_window)
	try:
		old_document = session.document
		_wavy_item(session).setSelected(True)
		monkeypatch.setattr(
			bkchem_qt.dialogs.wavy_dialog.WavyDialog, "exec",
			lambda _dialog: PySide6.QtWidgets.QDialog.DialogCode.Accepted,
		)
		monkeypatch.setattr(
			bkchem_qt.dialogs.wavy_dialog.WavyDialog, "changes",
			lambda _dialog: (("width", 2.5), ("line_color", "#AABBCC")),
		)
		bkchem_qt.actions.object_actions.handle_configure(main_window)

		assert "width=\"2.5\"" in session.backend_snapshot.cdml and session.can_undo_backend
		assert (
			session.document is not old_document and _selected_wavy_ids(session) == {"w1"}
			and session.document.undo_stack.canUndo() is False
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_captured_wavy_action_is_unavailable_after_origin_close(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An origin-bound Wavy callback cannot mutate another tab after close."""
	origin = _install_native_session(main_window)
	captured = main_window.capture_wavy_properties_for_view(origin.view, "w1")
	if captured is None:
		raise AssertionError("Live Wavy capability was unavailable")
	expected_revision, submit = captured
	main_window.on_new()
	other = next(session for session in main_window.sessions if session is not origin)
	other_before = other.backend_snapshot
	closed = main_window.close_session_at(main_window.sessions.index(origin))
	outcome = submit(expected_revision, "w1", (("width", 2.0),))

	assert closed and outcome.status == "unavailable" and outcome.commit is None
	assert other.backend_snapshot == other_before


#============================================
def test_modal_wavy_configure_remains_bound_to_origin_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Activating another tab while WavyDialog is open cannot retarget intent."""
	origin = _install_native_session(main_window)
	other = None
	try:
		_wavy_item(origin).setSelected(True)
		def activate_other(_dialog: object) -> int:
			"""Open and activate an independent tab before accepting the dialog."""
			main_window.on_new()
			return PySide6.QtWidgets.QDialog.DialogCode.Accepted

		monkeypatch.setattr(bkchem_qt.dialogs.wavy_dialog.WavyDialog, "exec", activate_other)
		monkeypatch.setattr(
			bkchem_qt.dialogs.wavy_dialog.WavyDialog, "changes",
			lambda _dialog: (("width", 2.5),),
		)
		bkchem_qt.actions.object_actions.handle_configure(main_window)
		other = next(session for session in main_window.sessions if session is not origin)

		assert 'width="2.5"' in origin.backend_snapshot.cdml
		assert 'width="2.5"' not in other.backend_snapshot.cdml
	finally:
		if other is not None and other in main_window.sessions:
			main_window._remove_session(other)
		if origin in main_window.sessions:
			main_window._remove_session(origin)


#============================================
def test_projection_retry_uses_only_the_accepted_wavy_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed Wavy projection recovers without resubmitting its patch intent."""
	session = _install_native_session(main_window)

	def unavailable(_snapshot: object) -> object:
		"""Report one post-acceptance projection installation failure."""
		return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
			bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
			bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
		)

	try:
		_wavy_item(session).setSelected(True)
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, unavailable),
		)
		outcome = session.submit_wavy_properties_patch(
			session.backend_snapshot.revision, "w1", (("width", 3.0),),
		)
		if outcome.commit is None:
			raise AssertionError("Accepted Wavy patch returned no backend snapshot")
		accepted = outcome.commit.snapshot

		def resubmission_must_not_run(*_args: object) -> object:
			"""Expose any retry that re-enters the public Wavy patch action."""
			raise AssertionError("Projection retry resubmitted the accepted Wavy patch")

		monkeypatch.setattr(session, "submit_wavy_properties_patch", resubmission_must_not_run)
		session.install_projection_lifecycle_port(
			bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
				session, session.replace_projection_from_backend_snapshot,
			),
		)
		retry = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and outcome.submitted
		assert retry.status == "accepted" and session.backend_snapshot == accepted and _selected_wavy_ids(session) == {"w1"}
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)
