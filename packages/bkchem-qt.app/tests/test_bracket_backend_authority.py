"""Focused authority checks for rectangular BracketMode creation."""

import math
import xml.dom.minidom

import PySide6.QtCore
import pytest
import shiboken6

import bkchem_qt.canvas.items.atom_item
import bkchem_qt.io.cdml_candidate
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.modes.bracket_mode
import oasa.cdml_document
import oasa.cdml_writer
import oasa.safe_xml


#============================================
def _install_projection_port(session: object, deliver: object) -> None:
	"""Install one fresh typed projection lifecycle port for this session."""
	port = bkchem_qt.models.document_session.SessionProjectionLifecyclePort(session, deliver)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(snapshot: object) -> object:
	"""Report one deliberately unavailable typed projection outcome."""
	return bkchem_qt.models.document_session.ProjectionLifecycleResult(
		bkchem_qt.models.document_session.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.document_session.ProjectionLifecyclePhase.PREPARATION,
	)


def _new_session(main_window: bkchem_qt.main_window.MainWindow) -> bkchem_qt.models.document_session.DocumentSession:
	"""Create one public temporary session."""
	if not main_window.on_new():
		raise RuntimeError("Public New did not create a Bracket test session")
	return next(session for session in main_window.sessions if session.document is main_window.document)


def _close_clean(main_window: bkchem_qt.main_window.MainWindow, session: bkchem_qt.models.document_session.DocumentSession) -> None:
	"""Close a final-backend-clean temporary session."""
	if not main_window.close_session_at(main_window.sessions.index(session)):
		raise RuntimeError("Public close did not remove Bracket test session")


def _bracket_mode(session: bkchem_qt.models.document_session.DocumentSession) -> bkchem_qt.modes.bracket_mode.BracketMode:
	"""Select the public rectangular Bracket mode."""
	session.mode_manager.set_mode("bracket")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.bracket_mode.BracketMode):
		raise TypeError("Bracket selection did not install BracketMode")
	return mode


def _drag(mode: bkchem_qt.modes.bracket_mode.BracketMode, start: tuple[float, float], end: tuple[float, float]) -> None:
	"""Drive one public manual bracket gesture."""
	begin = PySide6.QtCore.QPointF(*start)
	finish = PySide6.QtCore.QPointF(*end)
	mode.mouse_press(begin, object())
	mode.mouse_move(finish, object())
	mode.mouse_release(finish, object())


def _polylines(cdml: str) -> tuple[tuple[str, tuple[tuple[float, float], ...]], ...]:
	"""Read direct core polyline values through the owning CDML parser."""
	oasa.cdml_document.CDMLDocument.parse(cdml, validation="strict")
	root = oasa.safe_xml.parse_dom_from_string(cdml).documentElement
	values = []
	for child in root.childNodes:
		if not isinstance(child, xml.dom.minidom.Element) or child.localName != "polyline":
			continue
		points = []
		for point in child.childNodes:
			if isinstance(point, xml.dom.minidom.Element) and point.localName == "point":
				points.append(tuple(
					float(point.getAttribute(axis).removesuffix("cm")) * oasa.cdml_writer.POINTS_PER_CM
					for axis in ("x", "y")
				))
		values.append((child.getAttribute("id"), tuple(points)))
	return tuple(values)


def _points_match(actual: tuple[tuple[float, float], ...], expected: tuple[tuple[float, float], ...]) -> bool:
	"""Return whether CDML centimetre rounding retains scene geometry."""
	return len(actual) == len(expected) and all(
		abs(actual_value - expected_value) <= 0.02
		for actual_point, expected_point in zip(actual, expected)
		for actual_value, expected_value in zip(actual_point, expected_point)
	)


def test_manual_bracket_uses_backend_history_and_fresh_projection(main_window: bkchem_qt.main_window.MainWindow) -> None:
	"""An accepted manual pair uses canonical backend undo/redo, not Qt undo."""
	session = _new_session(main_window)
	try:
		mode = _bracket_mode(session)
		before = session.backend_snapshot
		before_document = session.document
		_drag(mode, (10.0, 20.0), (50.0, 70.0))
		accepted = session.backend_snapshot
		accepted_document = session.document
		accepted_polylines = _polylines(accepted.cdml)
		undone = session.undo_backend()
		undone_document = session.document
		undone_snapshot = session.backend_snapshot
		can_undo_after_undo = session.can_undo_backend
		redone = session.redo_backend()
		redone_document = session.document
		redone_snapshot = session.backend_snapshot
	finally:
		if session.can_undo_backend:
			cleanup = session.undo_backend()
			if cleanup.status != "accepted":
				raise RuntimeError("Bracket cleanup undo did not restore the clean baseline")
		_close_clean(main_window, session)

	assert accepted.revision != before.revision
	assert len(accepted_polylines) == 2 and all(identifier for identifier, _points in accepted_polylines)
	assert _points_match(accepted_polylines[0][1], ((18.0, 20.0), (10.0, 20.0), (10.0, 70.0), (18.0, 70.0)))
	assert _points_match(accepted_polylines[1][1], ((42.0, 20.0), (50.0, 20.0), (50.0, 70.0), (42.0, 70.0)))
	assert accepted_document is not before_document and accepted_document.undo_stack.count() == 0
	assert undone.status == "accepted" and undone_snapshot.cdml == before.cdml
	assert not can_undo_after_undo
	assert redone.status == "accepted" and redone_snapshot.cdml == accepted.cdml
	assert undone_document is not accepted_document
	assert redone_document is not undone_document and redone_document is not accepted_document
	assert redone_document.undo_stack.count() == 0


def test_bracket_threshold_and_invalid_request_are_atomic(main_window: bkchem_qt.main_window.MainWindow) -> None:
	"""Exact manual threshold and malformed bounds preserve backend state."""
	session = _new_session(main_window)
	try:
		mode = _bracket_mode(session)
		before = session.backend_snapshot
		_drag(mode, (10.0, 10.0), (20.0, 40.0))
		width_threshold = session.backend_snapshot
		_drag(mode, (10.0, 10.0), (40.0, 20.0))
		height_threshold = session.backend_snapshot
		nonfinite_request = bkchem_qt.models.document_session.PersistentOperationRequest(
			"bracket.add", "Add Brackets", (("bounds", (0.0, 0.0, math.nan, 10.0)),),
		)
		nonfinite_outcome = session.submit_persistent_operation(nonfinite_request)
		reversed_request = bkchem_qt.models.document_session.PersistentOperationRequest(
			"bracket.add", "Add Brackets", (("bounds", (5.0, 0.0, 4.0, 10.0)),),
		)
		reversed_outcome = session.submit_persistent_operation(reversed_request)
		invalid = session.backend_snapshot
	finally:
		_close_clean(main_window, session)

	assert width_threshold == before and height_threshold == before
	assert nonfinite_outcome.status == "rejected" and reversed_outcome.status == "rejected"
	assert invalid == before


def test_bracket_candidate_preserves_opaque_order_and_maps_both_issued_ids() -> None:
	"""One complete pair candidate retains opaque XML and receives two durable IDs."""
	source = ('<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml" '
		'xmlns:x="urn:example:opaque" version="0.15"><!--keep--><x:note/><c:text id="text_1"/></c:cdml>')
	backend = oasa.cdml_document.CDMLDocumentSession.load(source)
	before = backend.snapshot()
	tokens = ("__bkchem_new__bracket-r0-1-left", "__bkchem_new__bracket-r0-1-right")
	commit = backend.commit(
		expected_revision=before.revision,
		complete_cdml=bkchem_qt.io.cdml_candidate.append_rectangular_bracket_candidate(
			before.cdml, tokens, (10.0, 20.0, 50.0, 70.0),
		),
	)
	root = oasa.safe_xml.parse_dom_from_string(commit.cdml).documentElement
	children = tuple(root.childNodes)
	polyline_ids = tuple(
		child.getAttribute("id") for child in children
		if isinstance(child, xml.dom.minidom.Element) and child.localName == "polyline"
	)

	assert children[0].nodeType == xml.dom.minidom.Node.COMMENT_NODE and children[0].data == "keep"
	assert isinstance(children[1], xml.dom.minidom.Element)
	assert children[1].namespaceURI == "urn:example:opaque" and children[1].localName == "note"
	assert isinstance(children[2], xml.dom.minidom.Element) and children[2].localName == "text"
	assert polyline_ids == (commit.id_map[tokens[0]], commit.id_map[tokens[1]])
	assert set(commit.id_map) == set(tokens) and len(set(commit.id_map.values())) == 2
	assert all(token not in commit.cdml for token in tokens)


def test_bracket_candidate_stale_commit_leaves_current_snapshot_unchanged() -> None:
	"""A complete candidate from an earlier revision gets a typed atomic rejection."""
	source = '<cdml version="26.07"><text id="text_1"/></cdml>'
	backend = oasa.cdml_document.CDMLDocumentSession.load(source)
	before = backend.snapshot()
	accepted_candidate = bkchem_qt.io.cdml_candidate.append_rectangular_bracket_candidate(
		before.cdml,
		("__bkchem_new__bracket-r0-1-left", "__bkchem_new__bracket-r0-1-right"),
		(10.0, 20.0, 50.0, 70.0),
	)
	stale_candidate = bkchem_qt.io.cdml_candidate.append_rectangular_bracket_candidate(
		before.cdml,
		("__bkchem_new__bracket-r0-2-left", "__bkchem_new__bracket-r0-2-right"),
		(20.0, 30.0, 60.0, 80.0),
	)
	accepted = backend.commit(expected_revision=before.revision, complete_cdml=accepted_candidate)

	with pytest.raises(oasa.cdml_document.CDMLRevisionConflictError):
		backend.commit(expected_revision=before.revision, complete_cdml=stale_candidate)

	assert backend.snapshot() == accepted.snapshot


def test_selected_bracket_retires_interrupted_preview_before_operation_callback(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Selected-atom submission retires its old drag preview before backend work."""
	cdml = (
		'<cdml version="26.07"><molecule id="m1">'
		'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
		'</molecule></cdml>'
	)
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(cdml)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window, theme_manager=main_window._theme_manager,
		prefs=main_window._prefs, mode_host=main_window, prepared_native_cdml=prepared,
	)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable atom projection is unavailable")
	try:
		mode = _bracket_mode(session)
		mode.mouse_press(PySide6.QtCore.QPointF(10.0, 10.0), object())
		mode.mouse_move(PySide6.QtCore.QPointF(40.0, 25.0), object())
		preview = mode._preview_rect
		atom = next(
			item for item in session.scene.items()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		)
		atom.setSelected(True)
		observed = {}

		def submit(request: object) -> bkchem_qt.models.document_session.PersistentActionOutcome:
			observed["request"] = request
			observed["drag_start"] = mode._drag_start
			observed["preview"] = mode._preview_rect
			observed["preview_valid"] = shiboken6.isValid(preview)
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"accepted", "Bracket accepted", None, True,
			)

		mode.set_persistent_operation(submit)
		mode.mouse_press(PySide6.QtCore.QPointF(), object())
	finally:
		session.dispose()

	assert preview is not None
	assert isinstance(observed["request"], bkchem_qt.models.document_session.PersistentOperationRequest)
	assert observed["drag_start"] is None and observed["preview"] is None
	assert not observed["preview_valid"]


def test_selected_atoms_use_union_margin_and_restore_selection(main_window: bkchem_qt.main_window.MainWindow) -> None:
	"""Selected durable atoms create margin-expanded brackets and reselect by ID."""
	cdml = (
		'<cdml version="26.07"><molecule id="m1">'
		'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
		'<atom id="a2" name="O"><point x="3cm" y="1cm"/></atom>'
		'<bond id="b1" start="a1" end="a2" type="n1"/>'
		'</molecule></cdml>'
	)
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(cdml)
	session = bkchem_qt.models.document_session.DocumentSession(
		parent=main_window, theme_manager=main_window._theme_manager,
		prefs=main_window._prefs, mode_host=main_window, prepared_native_cdml=prepared,
	)
	_install_projection_port(session, session.replace_projection_from_backend_snapshot)
	if not session.replace_projection_from_backend_snapshot(session.backend_snapshot):
		raise AssertionError("Durable atom projection is unavailable")
	try:
		atoms = tuple(
			item for item in session.scene.items()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		)
		for atom in atoms:
			atom.setSelected(True)
		selected_bounds = bkchem_qt.modes.bracket_mode._expanded_union_bounds(atoms)
		_bracket_mode(session).mouse_press(PySide6.QtCore.QPointF(), object())
		selected_ids = {
			item.atom_model.backend_durable_id for item in session.scene.selectedItems()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		}
		polylines = _polylines(session.backend_snapshot.cdml)
	finally:
		session.dispose()

	left, top, right, bottom = selected_bounds
	assert selected_ids == {"a1", "a2"}
	assert _points_match(polylines[0][1], ((left + 8.0, top), (left, top), (left, bottom), (left + 8.0, bottom)))
	assert _points_match(polylines[1][1], ((right - 8.0, top), (right, top), (right, bottom), (right - 8.0, bottom)))
