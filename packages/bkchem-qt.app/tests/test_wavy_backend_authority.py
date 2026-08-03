"""Focused public authority checks for creation-only normal Wavy placement."""

# Standard Library
import pathlib
import xml.dom.minidom

# PIP3 modules
import pytest
import PySide6.QtCore

# local repo modules
import bkchem_qt.io.cdml_candidate
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.modes.misc_mode
import oasa.cdml_document
import oasa.cdml_writer
import oasa.safe_xml


_MIXED_CDML = '''<bk:cdml xmlns:bk="http://www.freesoftware.fsf.org/bkchem/cdml"
xmlns:vendor="urn:example:vendor" version="0.15"><bk:molecule id="molecule_1"><bk:atom
id="atom_1" name="C"><bk:point x="1cm" y="1cm" /></bk:atom></bk:molecule><bk:text
id="text_1"><bk:ftext>yield</bk:ftext></bk:text><vendor:note keep="yes">opaque
<vendor:child flag="keep">child text</vendor:child></vendor:note></bk:cdml>'''


#============================================
def _direct_elements(root: xml.dom.minidom.Element) -> list[xml.dom.minidom.Element]:
	"""Return direct element children in source order."""
	return [child for child in root.childNodes if isinstance(child, xml.dom.minidom.Element)]


#============================================
def _element_by_semantics(
		root: xml.dom.minidom.Element, namespace: str, local_name: str,
		object_id: str | None = None,
		) -> xml.dom.minidom.Element | None:
	"""Return one direct record selected by namespace, local name, and durable ID."""
	for element in _direct_elements(root):
		if element.namespaceURI != namespace or element.localName != local_name:
			continue
		if object_id is None or element.getAttribute("id") == object_id:
			return element
	return None


#============================================
def _direct_child(element: xml.dom.minidom.Element, name: str) -> xml.dom.minidom.Element:
	"""Return one direct child by local name."""
	return next(child for child in _direct_elements(element) if child.localName == name)


#============================================
def _direct_text(element: xml.dom.minidom.Element) -> str:
	"""Return direct text content without surrounding fixture whitespace."""
	return "".join(
		child.data for child in element.childNodes
		if child.nodeType == xml.dom.Node.TEXT_NODE
	).strip()


#============================================
def _scene_points(element: xml.dom.minidom.Element) -> tuple[tuple[float, float], ...]:
	"""Recover CDML centimetre coordinates as scene points."""
	return tuple(
		(
			float(point.getAttribute("x")[:-2]) * oasa.cdml_writer.POINTS_PER_CM,
			float(point.getAttribute("y")[:-2]) * oasa.cdml_writer.POINTS_PER_CM,
		)
		for point in _direct_elements(element)
		if point.localName == "point"
	)


#============================================
def _points_match(
		actual: tuple[tuple[float, float], ...], expected: tuple[tuple[float, float], ...],
		) -> bool:
	"""Return whether two semantic scene-point sequences agree within CDML precision."""
	return len(actual) == len(expected) and all(
		abs(actual_x - expected_x) <= 0.02 and abs(actual_y - expected_y) <= 0.02
		for (actual_x, actual_y), (expected_x, expected_y) in zip(actual, expected)
	)


#============================================
def _has_wavy_bend(points: tuple[tuple[float, float], ...]) -> bool:
	"""Return whether a Wavy geometry includes a point off its end-to-end line."""
	if len(points) < 3:
		return False
	start_x, start_y = points[0]
	end_x, end_y = points[-1]
	return any(
		abs((point_x - start_x) * (end_y - start_y) - (point_y - start_y) * (end_x - start_x))
		> 0.02
		for point_x, point_y in points[1:-1]
	)


#============================================
def _mixed_candidate() -> tuple[str, str]:
	"""Return canonical CDML and the backend-assigned durable Wavy ID."""
	token = "__bkchem_new__wavy-candidate"
	session = oasa.cdml_document.CDMLDocumentSession.load(_MIXED_CDML)
	commit = session.commit(
		expected_revision=0,
		complete_cdml=bkchem_qt.io.cdml_candidate.append_wavy_candidate(
			session.snapshot().cdml, token, ((0.0, 0.0), (36.0, 4.0), (72.0, 0.0)),
		),
	)
	return commit.cdml, commit.id_map[token]


#============================================
def _canonical_wavy_semantics(
		cdml: str, durable_id: str,
		) -> tuple[str, str, tuple[str, ...], tuple[tuple[float, float], ...]] | None:
	"""Return OASA-described Wavy facts selected by an accepted durable ID."""
	description = oasa.cdml_document.CDMLDocument.parse(
		cdml, validation="strict",
	).presentation_description(0)
	wavy = next(
		(
			record for record in description.records
			if record.identifier == durable_id and record.kind == "polyline"
			and dict(record.attributes).get("style") == "wavy"
		),
		None,
	)
	if wavy is None:
		return None
	attributes = dict(wavy.attributes)
	return (
		wavy.kind,
		wavy.identifier,
		tuple(attributes[name] for name in ("line_color", "width", "spline", "style")),
		tuple(point[:2] for point in wavy.points),
	)


#============================================
def _projected_wavy_semantics(
		document: object, durable_id: str,
		) -> tuple[str, str, tuple[str, ...], tuple[tuple[float, float], ...]] | None:
	"""Return plain projected Wavy facts selected by public model identity."""
	model = next(
		(
			candidate for candidate in document.presentation_objects
			if candidate.object_id == durable_id and candidate.kind == "polyline"
			and candidate.attributes["style"] == "wavy"
		),
		None,
	)
	if model is None:
		return None
	return (
		model.kind,
		model.object_id,
		tuple(model.attributes[name] for name in ("line_color", "width", "spline", "style")),
		tuple(point[:2] for point in model.points),
	)


#============================================
def _live_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Return the live public session that owns the window's public document."""
	return next(session for session in main_window.sessions if session.document is main_window.document)


#============================================
def _new_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Open and return one public fresh session."""
	if not main_window.on_new():
		raise RuntimeError("Public New did not create a Wavy test session")
	return _live_session(main_window)


#============================================
def _close_clean_session(
		main_window: bkchem_qt.main_window.MainWindow,
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Close one already-clean fresh session through the public tab API."""
	if not main_window.close_session_at(main_window.sessions.index(session)):
		raise RuntimeError("Public close did not remove the clean Wavy test session")


#============================================
def _select_wavy(
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> bkchem_qt.modes.misc_mode.MiscMode:
	"""Select the Wavy submode through the public session mode manager."""
	session.mode_manager.set_mode("misc")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.misc_mode.MiscMode):
		raise TypeError("Misc selection did not install MiscMode")
	mode.set_submode("wavy")
	return mode


#============================================
def _drag_wavy(
		session: bkchem_qt.models.document_session.DocumentSession,
		start: PySide6.QtCore.QPointF, end: PySide6.QtCore.QPointF,
		) -> None:
	"""Dispatch one normal Wavy drag through the public mode manager."""
	session.mode_manager.mouse_press(start, object())
	session.mode_manager.mouse_move(end, object())
	session.mode_manager.mouse_release(end, object())


#============================================
def _projected_wavy_id(document: object) -> str:
	"""Return the one public projected Wavy durable identity."""
	for model in document.presentation_objects:
		if model.kind == "polyline" and model.attributes["style"] == "wavy":
			return model.object_id
	raise RuntimeError("Normal Wavy drag did not create a projected Wavy record")


#============================================
def _submit_status(
		session: bkchem_qt.models.document_session.DocumentSession,
		payload: tuple[tuple[str, object], ...],
		target_keys: frozenset[tuple[str, str]] = frozenset(),
		) -> str:
	"""Return the public rejection status for one Wavy payload."""
	try:
		request = bkchem_qt.models.document_session.PersistentOperationRequest(
			"wavy.add", "Wavy", payload, target_keys,
		)
	except TypeError:
		return "construction-rejected"
	return session.submit_persistent_operation(request).status


#============================================
def test_wavy_candidate_preserves_existing_core_records() -> None:
	"""Appending Wavy retains existing molecule and text records by semantic identity."""
	cdml, _durable_id = _mixed_candidate()
	root = oasa.safe_xml.parse_dom_from_string(cdml).documentElement
	molecule = _element_by_semantics(root, root.namespaceURI, "molecule", "molecule_1")
	text = _element_by_semantics(root, root.namespaceURI, "text", "text_1")

	assert (
		(molecule.namespaceURI, molecule.localName, molecule.getAttribute("id")),
		(text.namespaceURI, text.localName, text.getAttribute("id")),
	) == ((root.namespaceURI, "molecule", "molecule_1"), (root.namespaceURI, "text", "text_1"))


#============================================
def test_wavy_candidate_preserves_opaque_namespace_text() -> None:
	"""Appending Wavy retains opaque namespaced content and its direct text."""
	cdml, _durable_id = _mixed_candidate()
	root = oasa.safe_xml.parse_dom_from_string(cdml).documentElement
	note = _element_by_semantics(root, "urn:example:vendor", "note")
	if note is None:
		raise RuntimeError("Canonical CDML omitted the opaque vendor note")
	note_child = _direct_child(note, "child")

	assert (
		note.getAttribute("keep"), _direct_text(note),
		note_child.getAttribute("flag"), _direct_text(note_child),
	) == ("yes", "opaque", "keep", "child text")


#============================================
def test_wavy_candidate_assigns_durable_identity_and_defaults() -> None:
	"""A candidate receives the backend identity and canonical Wavy defaults."""
	cdml, durable_id = _mixed_candidate()
	canonical = _canonical_wavy_semantics(cdml, durable_id)
	if canonical is None:
		raise RuntimeError("Canonical CDML omitted the accepted Wavy record")

	assert canonical[:3] == ("polyline", durable_id, ("#000000", "1.5", "no", "wavy"))


#============================================
def test_wavy_candidate_preserves_requested_geometry() -> None:
	"""A canonical Wavy candidate retains its requested endpoint geometry."""
	cdml, durable_id = _mixed_candidate()
	canonical = _canonical_wavy_semantics(cdml, durable_id)
	if canonical is None:
		raise RuntimeError("Canonical CDML omitted the accepted Wavy geometry")

	assert _points_match(canonical[3], ((0.0, 0.0), (36.0, 4.0), (72.0, 0.0)))


#============================================
@pytest.mark.parametrize("payload, expected", (
	((('start', (0.0, 0.0)),), "rejected"),
	((('start', (0.0, 0.0)), ('end', (0.0, 0.0))), "rejected"),
	((('start', (-1e308, 0.0)), ('end', (1e308, 0.0))), "rejected"),
	((('start', (0.0, 0.0)), ('end', (60000.0, 0.0))), "rejected"),
	((('start', [0.0, 0.0]), ('end', (1.0, 0.0))), "construction-rejected"),
))
def test_wavy_rejections_preserve_registered_backend(
		main_window: bkchem_qt.main_window.MainWindow,
		payload: tuple[tuple[str, object], ...], expected: str,
		) -> None:
	"""Invalid Wavy requests report rejection without changing public backend authority."""
	session = _live_session(main_window)
	before_snapshot = session.backend_snapshot

	assert _submit_status(session, payload) == expected
	assert session.backend_snapshot == before_snapshot


#============================================
def test_wavy_targeted_creation_request_preserves_registered_authority(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A creation-only Wavy request rejects a durable target without mutation."""
	session = _live_session(main_window)
	before_snapshot = session.backend_snapshot

	assert _submit_status(
		session, (("start", (0.0, 0.0)), ("end", (40.0, 0.0))),
		frozenset({("polyline", "polyline_1")}),
	) == "rejected"
	assert session.backend_snapshot == before_snapshot


#============================================
def test_wavy_validation_precedes_candidate_building(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Invalid Wavy geometry reaches no candidate builder."""
	session = _live_session(main_window)
	builder_called = False
	original = bkchem_qt.io.cdml_candidate.append_wavy_candidate

	def capture(
			complete_cdml: str, provisional_id: str,
			points: tuple[tuple[float, float], ...],
			) -> str:
		"""Record whether validated input reaches the candidate builder."""
		nonlocal builder_called
		builder_called = True
		return original(complete_cdml, provisional_id, points)

	monkeypatch.setattr(bkchem_qt.io.cdml_candidate, "append_wavy_candidate", capture)

	assert _submit_status(session, (("start", (-1e308, 0.0)), ("end", (1e308, 0.0)))) == "rejected"
	assert builder_called is False


#============================================
def test_registered_wavy_drag_matches_canonical_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A normal Wavy drag projects the canonical record selected by durable ID."""
	session = _new_session(main_window)
	try:
		_select_wavy(session)
		_drag_wavy(session, PySide6.QtCore.QPointF(20.0, 30.0), PySide6.QtCore.QPointF(110.0, 60.0))
		durable_id = _projected_wavy_id(session.document)
		canonical = _canonical_wavy_semantics(session.backend_snapshot.cdml, durable_id)
		projected = _projected_wavy_semantics(session.document, durable_id)
		main_window.on_undo()
	finally:
		_close_clean_session(main_window, session)

	assert canonical == projected


#============================================
def test_registered_wavy_drag_has_requested_endpoints_and_bend(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A normal Wavy drag preserves its endpoints and includes a visible bend."""
	session = _new_session(main_window)
	try:
		_select_wavy(session)
		_drag_wavy(session, PySide6.QtCore.QPointF(20.0, 30.0), PySide6.QtCore.QPointF(110.0, 60.0))
		canonical = _canonical_wavy_semantics(
			session.backend_snapshot.cdml, _projected_wavy_id(session.document),
		)
		if canonical is None:
			raise RuntimeError("Normal Wavy drag did not create canonical geometry")
		points = canonical[3]
		main_window.on_undo()
	finally:
		_close_clean_session(main_window, session)

	assert _points_match((points[0], points[-1]), ((20.0, 30.0), (110.0, 60.0)))
	assert _has_wavy_bend(points)


#============================================
def test_registered_wavy_drag_uses_backend_history_not_qt_undo(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A registered Wavy uses backend history while the Qt stack remains empty."""
	session = _new_session(main_window)
	try:
		_select_wavy(session)
		_drag_wavy(session, PySide6.QtCore.QPointF(20.0, 30.0), PySide6.QtCore.QPointF(110.0, 60.0))
		qt_undo_available = session.document.undo_stack.canUndo()
		backend_undo_available = session.can_undo_backend
		main_window.on_undo()
	finally:
		_close_clean_session(main_window, session)

	assert (qt_undo_available, backend_undo_available) == (False, True)


#============================================
def test_registered_wavy_public_undo_redo_reprojects_state(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Public backend undo and redo remove then restore canonical and projected Wavy."""
	session = _new_session(main_window)
	try:
		_select_wavy(session)
		_drag_wavy(session, PySide6.QtCore.QPointF(20.0, 30.0), PySide6.QtCore.QPointF(110.0, 60.0))
		durable_id = _projected_wavy_id(session.document)
		created = _canonical_wavy_semantics(session.backend_snapshot.cdml, durable_id)
		main_window.on_undo()
		undone = (
			_canonical_wavy_semantics(session.backend_snapshot.cdml, durable_id),
			_projected_wavy_semantics(session.document, durable_id),
		)
		main_window.on_redo()
		redone = (
			_canonical_wavy_semantics(session.backend_snapshot.cdml, durable_id),
			_projected_wavy_semantics(session.document, durable_id),
		)
		main_window.on_undo()
	finally:
		_close_clean_session(main_window, session)

	assert (undone, redone) == ((None, None), (created, created))


#============================================
def test_registered_wavy_authoritative_save_publishes_clean_snapshot(
		main_window: bkchem_qt.main_window.MainWindow, tmp_path: pathlib.Path,
		) -> None:
	"""Authoritative Save publishes the canonical Wavy and resets its backend baseline."""
	session = _new_session(main_window)
	try:
		_select_wavy(session)
		_drag_wavy(session, PySide6.QtCore.QPointF(20.0, 30.0), PySide6.QtCore.QPointF(110.0, 60.0))
		durable_id = _projected_wavy_id(session.document)
		canonical = _canonical_wavy_semantics(session.backend_snapshot.cdml, durable_id)
		saved = session.write_backend_snapshot(str(tmp_path / "wavy-history.cdml"))
		published = _canonical_wavy_semantics(
			(tmp_path / "wavy-history.cdml").read_text(encoding="utf-8"), durable_id,
		)
	finally:
		_close_clean_session(main_window, session)

	assert published == canonical
	assert saved.is_dirty is False
