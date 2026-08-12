"""Focused Qt behavior for backend-authoritative plain Plus properties."""

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document_session


_CDML = (
	'<cdml version="26.07"><plus id="plus1" font_size="13" color="#112233" '
	'background-color="#DDEEFF"><point x="3cm" y="4cm"/>'
	'<font family="Courier"/></plus></cdml>'
)


#============================================
def _install_native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Register one projected native-CDML session with a durable plain Plus."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native Plus CDML projection is unavailable")
	return registered


#============================================
def test_plus_capability_commits_dirty_history_and_undoes(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Accepted detached Plus intent changes only its captured backend session."""
	session = _install_native_session(main_window)
	try:
		before = session.backend_snapshot
		captured = main_window.capture_plus_properties_for_view(session.view, "plus1")
		if captured is None:
			raise AssertionError("Live Plus capability was unavailable")
		expected_revision, submit = captured
		outcome = submit(expected_revision, "plus1", (("font_size", 21),))

		assert outcome.status == "accepted" and session.backend_snapshot.is_dirty
		main_window.on_undo()
		assert (
			session.backend_snapshot.cdml == before.cdml
			and not session.backend_snapshot.is_dirty
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_closed_plus_capability_cannot_retarget_another_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A closed dialog capability remains bound to its original tab."""
	origin = _install_native_session(main_window)
	other = None
	try:
		captured = main_window.capture_plus_properties_for_view(origin.view, "plus1")
		if captured is None:
			raise AssertionError("Live Plus capability was unavailable")
		expected_revision, submit = captured
		main_window.on_new()
		other = next(session for session in main_window.sessions if session is not origin)
		other_before = other.backend_snapshot
		main_window.close_session_at(main_window.sessions.index(origin))
		outcome = submit(expected_revision, "plus1", (("font_size", 22),))

		assert outcome.status == "unavailable"
		assert other.backend_snapshot == other_before
	finally:
		if other is not None and other in main_window.sessions:
			main_window._remove_session(other)
		if origin in main_window.sessions:
			main_window._remove_session(origin)
