"""Focused authority checks for rectangular and round BracketMode creation."""

import math

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets
import shiboken6

import bkchem_qt.canvas.items.atom_item
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.bracket_pair_selection
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.modes.bracket_mode
import oasa.cdml_document
import oasa.cdml_writer
import oasa.cdml_xml


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
		main_window: bkchem_qt.main_window.MainWindow,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Create one public temporary session."""
	if not main_window.on_new():
		raise RuntimeError("Public New did not create a Bracket test session")
	return next(
		session for session in main_window.sessions
		if session.document is main_window.document
	)


def _close_clean(
		main_window: bkchem_qt.main_window.MainWindow,
		session: bkchem_qt.models.document_session.DocumentSession,
		) -> None:
	"""Close a final-backend-clean temporary session."""
	if not main_window.close_session_at(main_window.sessions.index(session)):
		raise RuntimeError("Public close did not remove Bracket test session")


def _bracket_mode(
		session: bkchem_qt.models.document_session.DocumentSession,
		style: str = "rectangular",
		) -> bkchem_qt.modes.bracket_mode.BracketMode:
	"""Select one public Bracket submode."""
	session.mode_manager.set_mode("bracket")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.bracket_mode.BracketMode):
		raise TypeError("Bracket selection did not install BracketMode")
	mode.set_submode(style + "bracket")
	return mode


def _drag(
		mode: bkchem_qt.modes.bracket_mode.BracketMode,
		start: tuple[float, float], end: tuple[float, float],
		) -> None:
	"""Drive one public manual bracket gesture."""
	begin = PySide6.QtCore.QPointF(*start)
	finish = PySide6.QtCore.QPointF(*end)
	mode.mouse_press(begin, object())
	mode.mouse_move(finish, object())
	mode.mouse_release(finish, object())


#============================================
class _EditEvent:
	"""Supply only the keyboard modifier fact consumed by EditMode gestures."""

	#============================================
	def __init__(self, modifiers: PySide6.QtCore.Qt.KeyboardModifier) -> None:
		"""Store the explicit modifier state for one selection gesture."""
		self._modifiers = modifiers

	#============================================
	def modifiers(self) -> PySide6.QtCore.Qt.KeyboardModifier:
		"""Return the gesture's explicit modifier state."""
		return self._modifiers


#============================================
def _edit_mode(session: bkchem_qt.models.document_session.DocumentSession) -> object:
	"""Activate the public Edit mode for one bracket selection gesture."""
	session.mode_manager.set_mode("edit")
	return session.mode_manager.current_mode


def _polylines(
		cdml: str,
		) -> tuple[tuple[str, str, tuple[tuple[float, float], ...]], ...]:
	"""Read direct core polyline values through the owning CDML parser."""
	oasa.cdml_document.CDMLDocument.parse(cdml, validation="strict")
	root = oasa.cdml_xml.parse_cdml_dom(cdml.encode("utf-8")).documentElement
	values = []
	for child in root.childNodes:
		if child.nodeType != child.ELEMENT_NODE or child.localName != "polyline":
			continue
		points = []
		for point in child.childNodes:
			if point.nodeType == point.ELEMENT_NODE and point.localName == "point":
				points.append(tuple(
					float(point.getAttribute(axis).removesuffix("cm")) * oasa.cdml_writer.POINTS_PER_CM
					for axis in ("x", "y")
				))
		values.append((child.getAttribute("id"), child.getAttribute("spline"), tuple(points)))
	return tuple(values)


def _points_match(
		actual: tuple[tuple[float, float], ...],
		expected: tuple[tuple[float, float], ...],
		) -> bool:
	"""Return whether CDML centimetre rounding retains scene geometry."""
	return len(actual) == len(expected) and all(
		abs(actual_value - expected_value) <= 0.02
		for actual_point, expected_point in zip(actual, expected)
		for actual_value, expected_value in zip(actual_point, expected_point)
	)


def test_manual_bracket_uses_backend_history_and_fresh_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
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
	dx = 0.05 * math.hypot(40.0, 50.0)
	assert len(accepted_polylines) == 2
	assert all(identifier and spline == "no" for identifier, spline, _points in accepted_polylines)
	assert _points_match(
		accepted_polylines[0][2],
		((10.0 + dx, 20.0), (10.0, 20.0), (10.0, 70.0), (10.0 + dx, 70.0)),
	)
	assert _points_match(
		accepted_polylines[1][2],
		((50.0 - dx, 20.0), (50.0, 20.0), (50.0, 70.0), (50.0 - dx, 70.0)),
	)
	assert accepted_document is not before_document and accepted_document.undo_stack.count() == 0
	assert undone.status == "accepted" and undone_snapshot.cdml == before.cdml
	assert not can_undo_after_undo
	assert redone.status == "accepted" and redone_snapshot.cdml == accepted.cdml
	assert undone_document is not accepted_document
	assert redone_document is not undone_document and redone_document is not accepted_document
	assert redone_document.undo_stack.count() == 0


def test_round_submode_commits_classic_spline_geometry(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""The visible Round choice reaches OASA and canonically reprojects curves."""
	session = _new_session(main_window)
	try:
		mode = _bracket_mode(session, "round")
		_drag(mode, (10.0, 20.0), (50.0, 70.0))
		polylines = _polylines(session.backend_snapshot.cdml)
		curve_types = tuple(
			tuple(item.path().elementAt(index).type for index in range(item.path().elementCount()))
			for item in session.scene.items()
			if isinstance(item, PySide6.QtWidgets.QGraphicsPathItem)
		)
	finally:
		if session.can_undo_backend:
			session.undo_backend()
		_close_clean(main_window, session)

	dx = 0.05 * math.hypot(40.0, 50.0)
	assert "Round" in mode.status_hint
	assert len(polylines) == 2 and all(spline == "yes" for _id, spline, _points in polylines)
	assert len(curve_types) == 2 and all(
		PySide6.QtGui.QPainterPath.ElementType.CurveToElement in types
		for types in curve_types
	)
	assert _points_match(
		polylines[0][2],
		((10.0 + dx, 20.0), (10.0, 22.5), (10.0, 67.5), (10.0 + dx, 70.0)),
	)
	assert _points_match(
		polylines[1][2],
		((50.0 - dx, 20.0), (50.0, 22.5), (50.0, 67.5), (50.0 - dx, 70.0)),
	)


def test_edit_selection_treats_an_observed_bracket_as_one_pair(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Click and Shift-toggle preserve explicit pair identity, not proximity."""
	session = _new_session(main_window)
	try:
		_drag(_bracket_mode(session), (10.0, 20.0), (50.0, 70.0))
		mode = _edit_mode(session)
		plain = _EditEvent(PySide6.QtCore.Qt.KeyboardModifier.NoModifier)
		shift = _EditEvent(PySide6.QtCore.Qt.KeyboardModifier.ShiftModifier)
		mode.mouse_press(PySide6.QtCore.QPointF(10.0, 45.0), plain)
		selected = bkchem_qt.models.bracket_pair_selection.selected_pair(session.document)
		mode.mouse_press(PySide6.QtCore.QPointF(10.0, 45.0), shift)
		deselected = session.document.selected_presentation_stack_root_ids
	finally:
		if session.can_undo_backend:
			session.undo_backend()
		_close_clean(main_window, session)

	assert selected is not None
	assert len(selected[1]) == 2
	assert deselected == ()


def test_dragging_a_newly_selected_bracket_moves_both_durable_members(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""One direct gesture translates the observed pair as one persistent unit."""
	session = _new_session(main_window)
	try:
		_drag(_bracket_mode(session), (10.0, 20.0), (50.0, 70.0))
		before = _polylines(session.backend_snapshot.cdml)
		mode = _edit_mode(session)
		event = _EditEvent(PySide6.QtCore.Qt.KeyboardModifier.NoModifier)
		start = PySide6.QtCore.QPointF(10.0, 45.0)
		finish = PySide6.QtCore.QPointF(25.0, 45.0)
		mode.mouse_press(start, event)
		mode.mouse_move(finish, event)
		mode.mouse_release(finish, event)
		after = _polylines(session.backend_snapshot.cdml)
	finally:
		while session.can_undo_backend:
			session.undo_backend()
		_close_clean(main_window, session)

	assert len(before) == len(after) == 2
	assert all(
		_points_match(
			after_points,
			tuple((x_coordinate + 15.0, y_coordinate) for x_coordinate, y_coordinate in before_points),
		)
		for (_before_id, _before_spline, before_points),
		(_after_id, _after_spline, after_points) in zip(before, after, strict=True)
	)


def test_pair_appearance_patch_is_one_backend_history_action(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Pair-addressed Qt intent updates both roots and supports backend undo."""
	session = _new_session(main_window)
	try:
		_drag(_bracket_mode(session), (10.0, 20.0), (50.0, 70.0))
		mode = _edit_mode(session)
		mode.mouse_press(
			PySide6.QtCore.QPointF(10.0, 45.0),
			_EditEvent(PySide6.QtCore.Qt.KeyboardModifier.NoModifier),
		)
		pair = bkchem_qt.models.bracket_pair_selection.selected_pair(session.document)
		if pair is None:
			raise AssertionError("Edit click did not select the observed bracket pair")
		before = session.backend_snapshot
		outcome = session.submit_bracket_properties_patch(
			before.revision, pair[0], (("line_width", 2.5), ("line_color", "#123456")),
		)
		accepted = session.backend_snapshot
		undone = session.undo_backend()
		undone_snapshot = session.backend_snapshot
	finally:
		if session.can_undo_backend:
			session.undo_backend()
		_close_clean(main_window, session)

	root = oasa.cdml_xml.parse_cdml_dom(accepted.cdml.encode("utf-8")).documentElement
	paired_lines = tuple(
		child for child in root.childNodes
		if (
			child.nodeType == child.ELEMENT_NODE
			and child.localName == "polyline"
			and child.getAttribute("bracket_pair") == pair[0]
		)
	)
	assert outcome.status == "accepted" and outcome.commit is not None
	assert len(paired_lines) == 2
	assert all(
		line.getAttribute("width") == "2.5" and line.getAttribute("line_color") == "#123456"
		for line in paired_lines
	)
	assert undone.status == "accepted" and undone_snapshot.cdml == before.cdml


def test_bracket_threshold_and_invalid_request_are_atomic(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
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
			"bracket.add", "Add Brackets",
			(("style", "rectangular"), ("bounds", (0.0, 0.0, math.nan, 10.0))),
		)
		nonfinite_outcome = session.submit_persistent_operation(nonfinite_request)
		reversed_request = bkchem_qt.models.document_session.PersistentOperationRequest(
			"bracket.add", "Add Brackets",
			(("style", "rectangular"), ("bounds", (5.0, 0.0, 4.0, 10.0))),
		)
		reversed_outcome = session.submit_persistent_operation(reversed_request)
		invalid = session.backend_snapshot
	finally:
		_close_clean(main_window, session)

	assert width_threshold == before and height_threshold == before
	assert nonfinite_outcome.status == "rejected" and reversed_outcome.status == "rejected"
	assert invalid == before


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
	assert isinstance(
		observed["request"],
		bkchem_qt.models.document_session.PersistentOperationRequest,
	)
	assert observed["drag_start"] is None and observed["preview"] is None
	assert not observed["preview_valid"]


def test_selected_atoms_use_union_margin_and_restore_selection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
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
	dx = 0.05 * math.hypot(right - left, bottom - top)
	assert selected_ids == {"a1", "a2"}
	assert _points_match(
		polylines[0][2],
		((left + dx, top), (left, top), (left, bottom), (left + dx, bottom)),
	)
	assert _points_match(
		polylines[1][2],
		((right - dx, top), (right, top), (right, bottom), (right - dx, bottom)),
	)
