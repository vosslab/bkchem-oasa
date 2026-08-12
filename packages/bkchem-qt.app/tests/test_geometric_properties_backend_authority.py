"""Focused Qt behavior for backend-authoritative geometric Configure."""

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import oasa.cdml_document


_CDML = (
	'<cdml version="26.07"><rect id="shape1" x1="1cm" y1="1cm" '
	'x2="3cm" y2="2cm" width="1.5" line_color="#ABC" area_color="#DDEEFF"/>'
	'<polyline id="line1" width="2" color="#123456" spline="1">'
	'<point x="4cm" y="1cm"/><point x="5cm" y="2cm"/></polyline></cdml>'
)


#============================================
def _install_native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Register one projected native session with closed and open geometry."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native geometric CDML projection is unavailable")
	return registered


#============================================
def _presentation_attributes(cdml: str, identifier: str) -> dict[str, str]:
	"""Read observable presentation values without accessing a Qt projection."""
	backend = oasa.cdml_document.CDMLDocumentSession.load(cdml)
	description = backend.presentation_description(
		oasa.cdml_document.CDMLPresentationDescriptionQuery(backend.revision),
	)
	record = next(record for record in description.records if record.identifier == identifier)
	return dict(record.attributes)


#============================================
def test_geometric_capability_commits_dirty_history_and_undoes(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Accepted detached geometric intent changes, projects, and undoes atomically."""
	session = _install_native_session(main_window)
	try:
		before = session.backend_snapshot
		captured = main_window.capture_geometric_properties_for_view(session.view, "shape1")
		if captured is None:
			raise AssertionError("Live geometric capability was unavailable")
		expected_revision, submit = captured
		outcome = submit(expected_revision, "shape1", (("area_color", None),))
		attributes = _presentation_attributes(session.backend_snapshot.cdml, "shape1")

		assert outcome.status == "accepted" and attributes["area_color"] == "none"
		main_window.on_undo()
		assert (
			session.backend_snapshot.cdml == before.cdml
			and not session.backend_snapshot.is_dirty
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_closed_geometric_capability_cannot_retarget_another_tab(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A closed geometric dialog capability cannot mutate an unrelated session."""
	origin = _install_native_session(main_window)
	other = None
	try:
		captured = main_window.capture_geometric_properties_for_view(origin.view, "shape1")
		if captured is None:
			raise AssertionError("Live geometric capability was unavailable")
		expected_revision, submit = captured
		main_window.on_new()
		other = next(session for session in main_window.sessions if session is not origin)
		other_before = other.backend_snapshot
		main_window.close_session_at(main_window.sessions.index(origin))
		outcome = submit(expected_revision, "shape1", (("line_width", 2.5),))

		assert outcome.status == "unavailable"
		assert other.backend_snapshot == other_before
	finally:
		if other is not None and other in main_window.sessions:
			main_window._remove_session(other)
		if origin in main_window.sessions:
			main_window._remove_session(origin)
