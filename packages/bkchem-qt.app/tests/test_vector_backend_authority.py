"""Focused authority checks for bounded VectorMode creation."""

# Standard Library
import math
import xml.dom.minidom

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.io.cdml_candidate
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.modes.vector_mode
import oasa.cdml_document
import oasa.cdml_writer
import oasa.safe_xml


#============================================
def _new_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Open and return one fresh public document session."""
	if not main_window.on_new():
		raise RuntimeError("Public New did not create a Vector test session")
	return next(session for session in main_window.sessions if session.document is main_window.document)


#============================================
def _close_clean_session(
		main_window: bkchem_qt.main_window.MainWindow,
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Close one test session after its final backend undo."""
	if not main_window.close_session_at(main_window.sessions.index(session)):
		raise RuntimeError("Public close did not remove the Vector test session")


#============================================
def _select_vector(
		session: bkchem_qt.models.document_session.DocumentSession, key: str,
		) -> bkchem_qt.modes.vector_mode.VectorMode:
	"""Select one public Vector submode through the mode manager."""
	session.mode_manager.set_mode("vector")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.vector_mode.VectorMode):
		raise TypeError("Vector selection did not install VectorMode")
	mode.set_submode(key)
	return mode


#============================================
def _drag_vector(
		session: bkchem_qt.models.document_session.DocumentSession,
		start: PySide6.QtCore.QPointF, end: PySide6.QtCore.QPointF,
		) -> None:
	"""Dispatch one normal Vector gesture through public mode routing."""
	session.mode_manager.mouse_press(start, object())
	session.mode_manager.mouse_move(end, object())
	session.mode_manager.mouse_release(end, object())


#============================================
def _canonical_vector(
		cdml: str, kind: str,
		) -> tuple[str, tuple[float, ...] | tuple[tuple[float, float], ...]] | None:
	"""Return one core Vector record after the owning CDML boundary accepts it."""
	oasa.cdml_document.CDMLDocument.parse(cdml, validation="compat")
	root = oasa.safe_xml.parse_dom_from_string(cdml).documentElement
	for child in root.childNodes:
		if not isinstance(child, xml.dom.minidom.Element) or child.localName != kind:
			continue
		if kind == "polyline":
			points = tuple(
				(float(point.getAttribute("x")[:-2]) * oasa.cdml_writer.POINTS_PER_CM,
					float(point.getAttribute("y")[:-2]) * oasa.cdml_writer.POINTS_PER_CM)
				for point in child.childNodes
				if isinstance(point, xml.dom.minidom.Element) and point.localName == "point"
			)
		else:
			points = tuple(
				float(child.getAttribute(name)[:-2]) * oasa.cdml_writer.POINTS_PER_CM
				for name in ("x1", "y1", "x2", "y2")
			)
		return child.getAttribute("id"), points
	return None


#============================================
def _points_match(actual: tuple, expected: tuple) -> bool:
	"""Return whether centimetre-rounded coordinates retain their scene meaning."""
	if len(actual) != len(expected):
		return False
	return all(abs(value - expected_value) <= 0.02 for value, expected_value in zip(actual, expected))


#============================================
def test_vector_modes_create_canonical_backend_records(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Rectangle, Oval, and Polyline gestures create canonical durable records."""
	session = _new_session(main_window)
	try:
		_select_vector(session, "rectangle")
		_drag_vector(session, PySide6.QtCore.QPointF(40.0, 30.0), PySide6.QtCore.QPointF(10.0, 60.0))
		rect = _canonical_vector(session.backend_snapshot.cdml, "rect")
		_select_vector(session, "oval")
		_drag_vector(session, PySide6.QtCore.QPointF(20.0, 40.0), PySide6.QtCore.QPointF(70.0, 80.0))
		oval = _canonical_vector(session.backend_snapshot.cdml, "oval")
		_select_vector(session, "polyline")
		_drag_vector(session, PySide6.QtCore.QPointF(5.0, 10.0), PySide6.QtCore.QPointF(65.0, 35.0))
		polyline = _canonical_vector(session.backend_snapshot.cdml, "polyline")
		while session.can_undo_backend:
			main_window.on_undo()
	finally:
		_close_clean_session(main_window, session)

	assert rect is not None and rect[0] != "" and _points_match(rect[1], (10.0, 30.0, 40.0, 60.0))
	assert oval is not None and oval[0] != "" and _points_match(oval[1], (20.0, 40.0, 70.0, 80.0))
	assert polyline is not None and polyline[0] != "" and all(
		_points_match(actual, expected)
		for actual, expected in zip(polyline[1], ((5.0, 10.0), (65.0, 35.0)))
	)


#============================================
def test_vector_threshold_axis_is_accepted_and_uses_backend_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A box at the historical drag threshold is accepted outside Qt undo."""
	session = _new_session(main_window)
	try:
		_select_vector(session, "rectangle")
		_drag_vector(session, PySide6.QtCore.QPointF(10.0, 25.0), PySide6.QtCore.QPointF(15.0, 25.0))
		created = _canonical_vector(session.backend_snapshot.cdml, "rect")
		projected = any(
			model.kind == "rect" and model.object_id == created[0]
			for model in session.document.presentation_objects
		) if created is not None else False
		qt_undo = session.document.undo_stack.canUndo()
		main_window.on_undo()
		undone = _canonical_vector(session.backend_snapshot.cdml, "rect")
		projection_before_redo = session.document
		main_window.on_redo()
		redone = _canonical_vector(session.backend_snapshot.cdml, "rect")
		projection_replaced = session.document is not projection_before_redo
		redone_projected = any(
			model.kind == "rect" and model.object_id == redone[0]
			for model in session.document.presentation_objects
		) if redone is not None else False
		main_window.on_undo()
	finally:
		_close_clean_session(main_window, session)

	assert created is not None and projected and _points_match(created[1], (10.0, 25.0, 15.0, 25.0))
	assert (qt_undo, undone, redone, projection_replaced, redone_projected) == (
		False, None, created, True, True,
	)


#============================================
def test_vector_short_and_invalid_requests_are_atomic(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A short drag and invalid finite-coordinate request leave the session unchanged."""
	session = _new_session(main_window)
	try:
		_select_vector(session, "oval")
		before = session.backend_snapshot
		_drag_vector(session, PySide6.QtCore.QPointF(10.0, 10.0), PySide6.QtCore.QPointF(14.0, 14.0))
		short_after = session.backend_snapshot
		request = bkchem_qt.models.document_session.PersistentOperationRequest(
			"vector.add", "Vector", (("shape", "rect"), ("start", (0.0, 0.0)),
			("end", (math.nan, 10.0))),
		)
		outcome = session.submit_persistent_operation(request)
		invalid_after = session.backend_snapshot
	finally:
		_close_clean_session(main_window, session)

	assert (short_after.revision, short_after.cdml) == (before.revision, before.cdml)
	assert outcome.status == "rejected"
	assert (invalid_after.revision, invalid_after.cdml) == (before.revision, before.cdml)


#============================================
def test_vector_candidate_preserves_opaque_root_order_and_maps_issued_id() -> None:
	"""One complete candidate retains opaque root content and replaces its token."""
	source = (
		'<c:cdml xmlns:c="http://www.freesoftware.fsf.org/bkchem/cdml" '
		'xmlns:x="urn:example:opaque" version="0.15"><!--keep-->'
		'<x:note keep="yes"/><c:text id="text_1"><c:ftext>note</c:ftext></c:text></c:cdml>'
	)
	backend = oasa.cdml_document.CDMLDocumentSession.load(source)
	before = backend.snapshot()
	token = "__bkchem_new__vector-r0-1"
	commit = backend.commit(
		expected_revision=before.revision,
		complete_cdml=bkchem_qt.io.cdml_candidate.append_vector_candidate(
			before.cdml, token, "rect", (0.0, 0.0), (36.0, 18.0),
		),
	)
	oasa.cdml_document.CDMLDocument.parse(commit.cdml, validation="compat")
	root = oasa.safe_xml.parse_dom_from_string(commit.cdml).documentElement
	elements = [
		child for child in root.childNodes
		if isinstance(child, xml.dom.minidom.Element)
	]
	comments = [
		child.data for child in root.childNodes
		if child.nodeType == xml.dom.minidom.Node.COMMENT_NODE
	]

	assert [element.localName for element in elements] == ["note", "text", "rect"]
	assert comments == ["keep"] and commit.id_map[token] == elements[-1].getAttribute("id") and token not in commit.cdml
