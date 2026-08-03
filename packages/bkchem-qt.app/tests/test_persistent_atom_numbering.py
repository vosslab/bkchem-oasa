"""Focused backend-authoritative atom-numbering behavior for Qt."""

# PIP3 modules
import pytest
import PySide6.QtCore

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.modes.misc_mode
import oasa.cdml_document
import oasa.safe_xml


_NUMBER_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O" number="8" show_number="no">'
	'<point x="3cm" y="1cm"/></atom>'
	'</molecule>'
	'<x:molecule xmlns:x="urn:extension"><x:atom id="foreign" number="999"/>'
	'</x:molecule>'
	'</cdml>'
)


#============================================
#============================================
def _install_projection_port(session: object, deliver: object) -> None:
	"""Install one fresh typed projection lifecycle port for this session."""
	port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(session, deliver)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(snapshot: object) -> object:
	"""Report one deliberately unavailable typed projection outcome."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
	)


def _new_session(
		main_window: bkchem_qt.main_window.MainWindow, cdml_text: str = _NUMBER_CDML,
		) -> object:
	"""Create one private synchronized session from complete CDML."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(
		cdml_text,
	)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window,
		theme_manager=main_window._theme_manager,
		prefs=main_window._prefs,
		mode_host=main_window,
		prepared_native_cdml=prepared,
	)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	projection = session.retry_current_backend_projection()
	if projection.status != "accepted":
		raise RuntimeError("Numbering test session did not project its backend snapshot")
	return session


#============================================
def _dispose_session(session: object) -> None:
	"""Release a private session through its MainWindow-owned safe reaper."""
	owner = session.parent()
	if not isinstance(owner, bkchem_qt.main_window.MainWindow):
		raise TypeError("Numbering test session has no MainWindow owner")
	owner._dispose_session_later(session)


#============================================
def _atom_number(cdml_text: str, atom_id: str) -> tuple[str, str]:
	"""Read accepted canonical number fields after the CDML boundary."""
	accepted = oasa.cdml_document.CDMLDocumentSession.load(cdml_text).snapshot().cdml
	document = oasa.safe_xml.parse_dom_from_string(accepted)
	for atom in document.getElementsByTagName("atom"):
		if atom.getAttribute("id") == atom_id:
			return atom.getAttribute("number"), atom.getAttribute("show_number")
	raise AssertionError("Canonical CDML omitted requested atom")


#============================================
def _number_request(
		session: object, atom_id: str, number: int | None, show_number: bool | None,
		) -> object:
	"""Build one exact plain atom-number request against the live revision."""
	return bkchem_qt.models.document_session.PersistentOperationRequest(
		"atom.number.set", "Set atom number",
		(
			("expected_revision", session.backend_snapshot.revision),
			("molecule_id", "m1"), ("atom_id", atom_id),
			("number", number), ("show_number", show_number),
		),
		frozenset({("molecule", "m1"), ("atom", atom_id)}),
	)


#============================================
def _misc_mode(session: object) -> bkchem_qt.modes.misc_mode.MiscMode:
	"""Activate and return the private session's Misc mode."""
	session.mode_manager.set_mode("misc")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.misc_mode.MiscMode):
		raise AssertionError("MiscMode did not activate")
	return mode


#============================================
def _atom_item(session: object, atom_id: str) -> object:
	"""Find one current projection item before submitting a gesture."""
	for item in session.scene.items():
		if (
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.atom_id == atom_id
		):
			return item
	raise AssertionError("Current projection omitted requested atom")


#============================================
def test_atom_number_operations_use_backend_history_for_assignment_clear_and_redo(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Numbering and clearing mutate canonical CDML through backend history."""
	session = _new_session(main_window)
	try:
		assigned = session.submit_persistent_operation(
			_number_request(session, "a2", 11, False),
		)
		assigned_snapshot = session.backend_snapshot
		cleared = session.submit_persistent_operation(
			_number_request(session, "a2", None, None),
		)
		undone = session.undo_backend()
		undone_snapshot = session.backend_snapshot
		redone = session.redo_backend()

		assert all(
			outcome.status == "accepted"
			for outcome in (assigned, cleared, undone, redone)
		)
		assert (
			_atom_number(assigned_snapshot.cdml, "a2"),
			_atom_number(undone_snapshot.cdml, "a2"),
			_atom_number(session.backend_snapshot.cdml, "a2"),
		) == (("11", "no"), ("11", "no"), ("", ""))
	finally:
		_dispose_session(session)


#============================================
def test_numbering_ribbon_uses_authoritative_hidden_number_for_its_candidate(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""The public numbering submode derives its next value from canonical CDML."""
	session = _new_session(main_window)
	try:
		mode = _misc_mode(session)
		mode.on_submode_switch(0, "numbering")
		item = _atom_item(session, "a1")
		position = PySide6.QtCore.QPointF(item.atom_model.x, item.atom_model.y)
		del item
		session.mode_manager.mouse_press(position, object())

		assert _atom_number(session.backend_snapshot.cdml, "a1") == ("9", "yes")
		assert session.backend_projection_synchronized
	finally:
		_dispose_session(session)


#============================================
def test_malformed_number_request_leaves_authoritative_snapshot_unchanged(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Mixed nullable values are rejected without a projection or history change."""
	session = _new_session(main_window)
	before = session.backend_snapshot
	try:
		outcome = session.submit_persistent_operation(
			_number_request(session, "a1", None, True),
		)

		assert outcome.status == "rejected"
		assert session.backend_snapshot == before
	finally:
		_dispose_session(session)


#============================================
def test_clear_on_an_unnumbered_atom_is_a_visible_no_op(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Clear preserves its established no-op behavior when no number exists."""
	session = _new_session(main_window)
	try:
		mode = _misc_mode(session)
		mode.on_submode_switch(0, "clear-numbers")
		item = _atom_item(session, "a1")
		position = PySide6.QtCore.QPointF(item.atom_model.x, item.atom_model.y)
		del item
		before = session.backend_snapshot
		session.mode_manager.mouse_press(position, object())

		assert session.backend_snapshot == before
	finally:
		_dispose_session(session)


#============================================
def test_direct_legacy_number_mark_is_rejected_without_changing_the_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A targeted legacy number mark remains an atomic backend compatibility failure."""
	legacy_cdml = (
		'<cdml version="26.07"><molecule id="m1">'
		'<atom id="a1" name="C"><point x="1cm" y="1cm"/>'
		'<mark type="atom_number"/></atom></molecule></cdml>'
	)
	session = _new_session(main_window, legacy_cdml)
	before = session.backend_snapshot
	try:
		outcome = session.submit_persistent_operation(
			_number_request(session, "a1", 3, True),
		)

		assert outcome.status == "rejected"
		assert session.backend_snapshot == before
	finally:
		_dispose_session(session)


#============================================
def test_stale_and_mismatched_atom_number_requests_leave_backend_navigation_unchanged(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Rejected atom-number envelopes do not publish a snapshot or history entry."""
	session = _new_session(main_window)
	before = session.backend_snapshot
	try:
		stale = bkchem_qt.models.document_session.PersistentOperationRequest(
			"atom.number.set", "Set atom number",
			(
				("expected_revision", before.revision - 1),
				("molecule_id", "m1"), ("atom_id", "a1"),
				("number", 3), ("show_number", True),
			),
			frozenset({("molecule", "m1"), ("atom", "a1")}),
		)
		mismatched_target = bkchem_qt.models.document_session.PersistentOperationRequest(
			"atom.number.set", "Set atom number",
			(
				("expected_revision", before.revision),
				("molecule_id", "m1"), ("atom_id", "a1"),
				("number", 3), ("show_number", True),
			),
			frozenset({("molecule", "m1"), ("atom", "a2")}),
		)
		stale_outcome = session.submit_persistent_operation(stale)
		mismatched_outcome = session.submit_persistent_operation(mismatched_target)

		assert stale_outcome.status == "rejected" and mismatched_outcome.status == "rejected"
		assert (
			session.backend_snapshot == before
			and not session.can_undo_backend
			and not session.can_redo_backend
		)
	finally:
		_dispose_session(session)


#============================================
def test_accepted_number_recovers_by_reprojecting_its_current_snapshot(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A failed number projection recovers the accepted state without resubmission."""
	session = _new_session(main_window)
	original_install = session._install_prepared_projection
	initial_install = True

	def fail_initial_install(*args: object, **kwargs: object) -> None:
		"""Fail the next real projection installation and allow an explicit retry."""
		nonlocal initial_install
		if initial_install:
			initial_install = False
			raise RuntimeError("intentional number projection failure")
		original_install(*args, **kwargs)

	monkeypatch.setattr(session, "_install_prepared_projection", fail_initial_install)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	try:
		outcome = session.submit_persistent_operation(
			_number_request(session, "a1", 9, True),
		)
		accepted = session.backend_snapshot
		recovered = session.retry_current_backend_projection()

		assert outcome.status == "unavailable" and outcome.submitted
		assert (
			recovered.status == "accepted"
			and session.backend_snapshot == accepted
			and session.backend_projection_synchronized
		)
	finally:
		_dispose_session(session)
