"""Fast protocol checks for the backend-owned Arrow Mode slice."""

# PIP3 modules
import pytest
import PySide6.QtCore

# local repo modules
import bkchem_qt.io.cdml_candidate
import bkchem_qt.main_window
import bkchem_qt.models.backend_revision_history
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import oasa.cdml_document
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
def _invalid_arrow_candidate(*_args: object) -> str:
	"""Model a typed candidate rejection before the backend sees a mutation."""
	raise ValueError("invalid arrow")


#============================================
def test_backend_commit_preserves_opaque_content_semantically() -> None:
	"""OASA keeps an opaque extension record while accepting an arrow."""
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml" '
		'xmlns:x="urn:extension" version="0.15"><x:note keep="yes"/></c:cdml>',
	)
	candidate = bkchem_qt.io.cdml_candidate.append_arrow_candidate(
		session.snapshot().cdml,
		"__bkchem_new__arrow-r0-1", (0.0, 0.0), (72.0, 0.0),
	)
	commit = session.commit(expected_revision=0, complete_cdml=candidate)
	note = oasa.safe_xml.parse_dom_from_string(commit.cdml).getElementsByTagNameNS(
		"urn:extension", "note",
	)[0]

	assert (note.namespaceURI, note.getAttribute("keep")) == ("urn:extension", "yes")


#============================================
def test_registered_arrow_projection_uses_oasa_durable_id(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""The real projection receives OASA's mapped ID, never the Qt token."""
	session = main_window._active_session
	original_append = bkchem_qt.io.cdml_candidate.append_arrow_candidate
	provisional_ids = []

	def capture_candidate(
			complete_cdml: str, provisional_id: str,
			start: tuple[float, float], end: tuple[float, float],
			) -> str:
		"""Capture the frontend-only token passed into the real candidate builder."""
		provisional_ids.append(provisional_id)
		return original_append(complete_cdml, provisional_id, start, end)

	monkeypatch.setattr(bkchem_qt.io.cdml_candidate, "append_arrow_candidate", capture_candidate)
	outcome = session.commit_arrow((0.0, 0.0), (40.0, 0.0))
	projected_arrow = session.document.presentation_objects[-1]

	assert outcome.status == "accepted" and outcome.commit is not None
	durable_id = outcome.commit.id_map[provisional_ids[0]]
	assert (
		projected_arrow.object_id,
		provisional_ids[0] in outcome.commit.cdml,
	) == (durable_id, False)


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
def test_typed_candidate_rejection_keeps_the_backend_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A rejected candidate leaves the visible projection and navigation intact."""
	main_window._on_new()
	session = main_window._active_session
	accepted = session.commit_arrow((0.0, 0.0), (40.0, 0.0))
	projected_arrow = session.document.presentation_objects[-1]
	monkeypatch.setattr(
		bkchem_qt.io.cdml_candidate, "append_arrow_candidate",
		_invalid_arrow_candidate,
	)
	outcome = session.commit_arrow((40.0, 0.0), (80.0, 0.0))

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
		(("start", (0.0, 0.0)), ("end", (40.0, 0.0))),
	)
	outcome = capability(request)

	assert outcome.status == "accepted"
	assert main_window._active_session.backend_snapshot.revision == 0
	original.document.mark_clean()
	main_window.close_session_at(main_window._sessions.index(main_window._active_session))
	main_window.close_session_at(main_window._sessions.index(original))


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
		(("start", (0.0, 0.0)), ("end", (40.0, 0.0))),
	)
	outcome = capability(request)

	assert outcome.status == "unavailable"
	assert not outcome.submitted
