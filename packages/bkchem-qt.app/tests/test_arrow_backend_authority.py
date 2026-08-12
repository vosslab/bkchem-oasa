"""Fast protocol checks for the backend-owned Arrow Mode slice."""

# Standard Library
import math

# PIP3 modules
import pytest
import PySide6.QtCore

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.models.backend_revision_history
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import oasa.cdml_document
import oasa.cdml_presentation_insert
import oasa.safe_xml


#============================================
def _standalone_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Return a live but deliberately unregistered backend-session client."""
	return bkchem_qt.models.document_session.DocumentSession(
		parent=main_window,
		theme_manager=main_window._theme_manager,
		prefs=main_window._prefs,
		mode_host=main_window,
	)


#============================================
def _dispose_session(
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Release a standalone session through the production-safe reaper."""
	owner = session.parent()
	if not isinstance(owner, bkchem_qt.main_window.MainWindow):
		raise TypeError("Standalone session has no MainWindow owner")
	owner._dispose_session_later(session)


#============================================
def _install_projection_port(
		session: bkchem_qt.models.document_session.DocumentSession,
		deliver: object,
		) -> None:
	"""Install one fresh typed projection lifecycle port for this session."""
	port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, deliver)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(_snapshot: object) -> bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult:
	"""Report a deliberately unavailable projection without claiming installation."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
	)


#============================================
def _projection_installed(_snapshot: object) -> bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult:
	"""Model an installed projection where no real replacement is required."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLED,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.COMPLETE,
	)


#============================================
def _projection_raises(_snapshot: object) -> bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult:
	"""Model a frontend projection callback that cannot install a snapshot."""
	raise RuntimeError("projection unavailable")


#============================================
def test_backend_commit_preserves_opaque_content_semantically() -> None:
	"""OASA keeps an opaque extension record while accepting an arrow."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml" '
		'xmlns:x="urn:extension" version="0.15"><x:note keep="yes"/></c:cdml>',
	)
	result = oasa.cdml_presentation_insert.insert_arrow(
		session,
		oasa.cdml_presentation_insert.CDMLArrowInsertRequest(
			session.revision, "normal", False, ((0.0, 0.0), (72.0, 0.0)),
		),
	)
	note = oasa.safe_xml.parse_dom_from_string(result.snapshot.cdml).getElementsByTagNameNS(
		"urn:extension", "note",
	)[0]

	assert (note.namespaceURI, note.getAttribute("keep")) == ("urn:extension", "yes")


#============================================
def test_registered_arrow_projection_uses_oasa_durable_id(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""The real projection receives OASA's durable identity without a Qt token."""
	session = main_window._active_session
	outcome = session.commit_arrow((0.0, 0.0), (40.0, 0.0))
	projected_arrow = session.document.presentation_objects[-1]

	assert outcome.status == "accepted" and outcome.commit is not None
	assert projected_arrow.object_id in outcome.commit.id_map.values()
	assert "__bkchem_new__" not in outcome.commit.cdml


#============================================
def test_unregistered_session_cannot_commit_an_arrow(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A mode facade cannot mutate OASA before tab registration succeeds."""
	session = _standalone_session(main_window)
	try:
		outcome = session.commit_arrow((0.0, 0.0), (40.0, 0.0))

		assert (outcome.status, session.backend_snapshot.revision) == ("unavailable", 0)
	finally:
		_dispose_session(session)


#============================================
def test_arrow_mode_same_point_release_is_a_noop(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A release without any gesture displacement never mutates the backend."""
	main_window._on_new()
	session = main_window._active_session
	mode = session.mode_manager._modes["arrow"]
	before_revision = session.backend_snapshot.revision
	point = PySide6.QtCore.QPointF(40.0, 40.0)
	mode.mouse_press(point, object())
	mode.mouse_release(point, object())

	assert session.backend_snapshot.revision == before_revision


#============================================
def test_arrow_submodes_shape_one_immutable_gesture_request(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Visible Arrow choices become declared backend intent, not ribbon decoration."""
	main_window._on_new()
	session = main_window._active_session
	session.mode_manager.set_mode("arrow")
	mode = session.mode_manager.current_mode
	requests = []

	class RecordedOutcome:
		"""Provide the ordinary status text consumed by a mode callback."""

		message = "Arrow created"

	def record(request: object) -> RecordedOutcome:
		"""Keep the mode's opaque immutable request for semantic inspection."""
		requests.append(request)
		return RecordedOutcome()

	mode.set_persistent_operation(record)
	mode.set_submode("6")
	mode.set_submode("freestyle")
	mode.set_submode("spline")
	mode.set_submode("equilibrium")
	session.mode_manager.mouse_press(PySide6.QtCore.QPointF(0.0, 0.0), object())
	session.mode_manager.mouse_release(PySide6.QtCore.QPointF(30.0, 10.0), object())
	request = requests[0]
	payload = dict(request.payload)
	end_x, end_y = payload["endpoints"][1]
	angle = round(math.degrees(math.atan2(end_y, end_x)))

	assert (payload["kind"], payload["spline"], angle) == ("equilibrium", True, 18)


#============================================
def test_fixed_arrow_uses_scene_grid_length(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Fixed-length Arrow creation uses the active scene's canonical grid spacing."""
	main_window._on_new()
	session = main_window._active_session
	session.mode_manager.set_mode("arrow")
	mode = session.mode_manager.current_mode
	requests = []

	class RecordedOutcome:
		"""Provide the normal user-facing callback result."""

		message = "Arrow created"

	def record(request: object) -> RecordedOutcome:
		"""Retain one immutable request without constructing presentation XML."""
		requests.append(request)
		return RecordedOutcome()

	mode.set_persistent_operation(record)
	mode.set_submode("fixed")
	session.scene.set_grid_spacing_pt(42.0)
	session.mode_manager.mouse_press(PySide6.QtCore.QPointF(10.0, 10.0), object())
	session.mode_manager.mouse_release(PySide6.QtCore.QPointF(100.0, 10.0), object())
	payload = dict(requests[0].payload)
	start, end = payload["endpoints"]

	assert abs(end[0] - start[0]) == 42.0 and end[1] == start[1]


#============================================
def test_typed_arrow_rejection_keeps_the_backend_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A rejected Arrow intent leaves projection and backend navigation intact."""
	main_window._on_new()
	session = main_window._active_session
	accepted = session.commit_arrow((0.0, 0.0), (40.0, 0.0))
	projected_arrow = session.document.presentation_objects[-1]
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"arrow.add", "Arrow",
		(
			("kind", "normal"), ("spline", False),
			("endpoints", ((40.0, 0.0), (float("nan"), 0.0))),
		),
	)
	outcome = session.submit_persistent_operation(request)

	assert (accepted.status, outcome.status) == ("accepted", "rejected")
	assert (
		session.backend_snapshot.revision,
		session.document.presentation_objects[-1] is projected_arrow, session.can_undo_backend,
	) == (1, True, True)


#============================================
def test_truthy_projection_callback_is_not_an_accepted_arrow(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Only literal True may claim that an accepted snapshot was projected."""
	session = _standalone_session(main_window)
	_install_projection_port(session, lambda _snapshot: 1)
	try:
		with pytest.raises(TypeError, match="Projection lifecycle delivery"):
			session.commit_arrow((0.0, 0.0), (40.0, 0.0))

		assert "arrow" in session.backend_snapshot.cdml
	finally:
		_dispose_session(session)


#============================================
def test_projection_false_retains_the_accepted_backend_arrow(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A failed replacement disables Save and backend navigation after acceptance."""
	main_window._on_new()
	session = main_window._active_session
	_install_projection_port(session, _projection_unavailable)
	outcome = session.commit_arrow((0.0, 0.0), (40.0, 0.0))

	assert (outcome.status, session.backend_snapshot.revision) == ("unavailable", 1)
	assert (
		session.can_write_authoritative_snapshot, session.can_undo_backend,
	) == (False, False)


#============================================
def test_projection_exception_retains_the_accepted_backend_arrow(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A post-acceptance exception is unavailable, never a backend rollback."""
	main_window._on_new()
	session = main_window._active_session
	_install_projection_port(session, _projection_raises)
	outcome = session.commit_arrow((0.0, 0.0), (40.0, 0.0))

	assert (outcome.status, session.backend_snapshot.revision) == ("unavailable", 1)
	assert (
		session.can_write_authoritative_snapshot, session.can_undo_backend,
	) == (False, False)


#============================================
def test_retry_uses_the_exact_current_backend_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Exact retry restores the unavailable session's Save and undo capabilities."""
	main_window._on_new()
	session = main_window._active_session
	projected = []

	def record_false(snapshot: object) -> bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult:
		"""Record the failed post-acceptance snapshot for comparison."""
		projected.append(snapshot)
		return _projection_unavailable(snapshot)

	def record_true(snapshot: object) -> bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult:
		"""Record the retried snapshot and acknowledge literal projection success."""
		projected.append(snapshot)
		return main_window._replace_session_projection(session, snapshot)

	_install_projection_port(session, record_false)
	session.commit_arrow((0.0, 0.0), (40.0, 0.0))
	_install_projection_port(session, record_true)
	outcome = session.retry_current_backend_projection()

	assert (outcome.status, projected[0] == projected[1]) == ("accepted", True)
	assert (
		session.can_write_authoritative_snapshot, session.can_undo_backend,
	) == (True, True)


#============================================
def test_legacy_isolation_refuses_an_ordinary_backend_projection_retry(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A generic retry cannot silently replace a later Qt-local edit."""
	session = _standalone_session(main_window)
	_install_projection_port(session, _projection_installed)
	try:
		session.document.mark_dirty()
		retry = session.retry_current_backend_projection()

		assert (retry.status, session.legacy_isolated) == ("unavailable", True)
	finally:
		_dispose_session(session)


#============================================
def test_arrow_adapter_records_acceptance_in_plain_revision_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""The real Arrow adapter appends through the Qt-free history boundary."""
	main_window._on_new()
	session = main_window._active_session
	accepted = session.commit_arrow((0.0, 0.0), (40.0, 0.0))

	assert accepted.status == "accepted"
	assert isinstance(
		session._backend_history,
		bkchem_qt.models.backend_revision_history.BackendRevisionHistory,
	)


#============================================
def test_persistent_operation_request_rejects_mutable_payload_values() -> None:
	"""The frontend/backend request boundary cannot retain mutable payload data."""
	with pytest.raises(TypeError, match="immutable plain data"):
		bkchem_qt.models.document_session.PersistentOperationRequest(
			"arrow.add", "Arrow", (("start", [0.0, 0.0]),),
		)


#============================================
def test_session_discovers_and_clears_persistent_mode_capabilities(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Construction and production close manage the discovered Arrow callback."""
	main_window._on_new()
	session = main_window._active_session
	mode = session.mode_manager._modes["arrow"]
	was_installed = callable(mode._persistent_operation)
	main_window.close_session_at(main_window._sessions.index(session))

	assert was_installed
	assert mode._persistent_operation is None


#============================================
def test_captured_non_mode_capability_uses_its_original_registered_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A frozen capability does not retarget the active tab after tab creation."""
	main_window._on_new()
	original = main_window._active_session
	capability = main_window.persistent_operation_capability_for(original)
	main_window._on_new()
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"arrow.add", "Arrow",
		(
			("kind", "normal"), ("spline", False),
			("endpoints", ((0.0, 0.0), (40.0, 0.0))),
		),
	)
	outcome = capability(request)

	assert outcome.status == "accepted"
	assert main_window._active_session.backend_snapshot.revision == 0
	assert main_window._remove_session(main_window._active_session)
	assert main_window._remove_session(original)


#============================================
def test_closed_non_mode_capability_is_unavailable_before_submission(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A closed captured tab cannot retarget a later persistent submission."""
	main_window._on_new()
	session = main_window._active_session
	capability = main_window.persistent_operation_capability_for(session)
	main_window.close_session_at(main_window._sessions.index(session))
	request = bkchem_qt.models.document_session.PersistentOperationRequest(
		"arrow.add", "Arrow",
		(
			("kind", "normal"), ("spline", False),
			("endpoints", ((0.0, 0.0), (40.0, 0.0))),
		),
	)
	outcome = capability(request)

	assert outcome.status == "unavailable"
	assert not outcome.submitted
