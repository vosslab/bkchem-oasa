"""Focused backend-authority checks for EditMode presentation-only drags."""

# Standard Library
import re

# PIP3 modules
import PySide6.QtCore
import pytest

# local repo modules
import bkchem_qt.main_window
import bkchem_qt.canvas.document_projection
import bkchem_qt.models.document_object
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.modes.edit_mode
import bkchem_qt.undo.commands
import oasa.cdml_document


_CDML = (
	'<cdml xmlns:vendor="urn:vendor" version="26.07">'
	'<arrow id="arrow1"><point x="1cm" y="1cm"/>'
	'<point x="3cm" y="1cm"/></arrow>'
	'<vendor:note keep="yes">opaque</vendor:note></cdml>'
)
_IDLESS_CDML = _CDML.replace('arrow id="arrow1"', "arrow")


#============================================
class _MouseEvent:
	"""Provide deterministic modifier state for direct EditMode dispatch."""

	#============================================
	def __init__(self, modifiers: PySide6.QtCore.Qt.KeyboardModifier) -> None:
		"""Store the modifier mask used by the gesture."""
		self._modifiers = modifiers

	#============================================
	def modifiers(self) -> PySide6.QtCore.Qt.KeyboardModifier:
		"""Return the modifier mask expected by EditMode."""
		return self._modifiers


#============================================
def _native_session(main_window: bkchem_qt.main_window.MainWindow, cdml: str = _CDML) -> object:
	"""Install one native session containing a durable presentation root."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(cdml)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise RuntimeError("Native CDML projection is unavailable")
	return registered


#============================================
def _presentation_item(session: object) -> object:
	"""Return the projected arrow root from one controlled native session."""
	return next(
		item for item in session.scene.items()
		if getattr(getattr(item, "document_object_model", None), "kind", None) == "arrow"
	)


#============================================
def _edit_mode(session: object) -> bkchem_qt.modes.edit_mode.EditMode:
	"""Activate and return the session-owned EditMode instance."""
	session.mode_manager.set_mode("edit")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.edit_mode.EditMode):
		raise TypeError("Edit mode unavailable")
	return mode


#============================================
def _drag(
		mode: bkchem_qt.modes.edit_mode.EditMode, item: object,
		delta: tuple[float, float],
		) -> None:
	"""Dispatch one complete presentation-only drag at a durable item point."""
	model = item.document_object_model
	x, y, _z = model.points[0]
	start = PySide6.QtCore.QPointF(x, y)
	finish = PySide6.QtCore.QPointF(x + delta[0], y + delta[1])
	event = _MouseEvent(PySide6.QtCore.Qt.KeyboardModifier.NoModifier)
	mode.mouse_press(start, event)
	mode.mouse_move(finish, event)
	mode.mouse_release(finish, event)


#============================================
def _first_point(snapshot: object, identifier: str) -> tuple[float, float]:
	"""Read a durable root's first point through the hardened CDML boundary."""
	document = oasa.cdml_document.CDMLDocument.parse(snapshot.cdml, validation="strict")
	record = document.find_by_id(identifier)
	if record is None:
		raise AssertionError("Accepted CDML did not retain root: %s" % identifier)
	values = dict(re.findall(r'\b([xy])="([^"]+)"', record.raw_xml))
	return (
		float(values["x"].removesuffix("cm")),
		float(values["y"].removesuffix("cm")),
	)


#============================================
def test_presentation_drag_uses_backend_history_and_reprojects_selection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A native presentation drag commits canonical CDML without Qt undo state."""
	session = _native_session(main_window)
	try:
		submissions = []
		apply = session._backend_session.apply_top_level_transform
		def record(request: object) -> object:
			"""Record the plain backend request while preserving its execution."""
			submissions.append(request)
			return apply(request)

		session._backend_session.apply_top_level_transform = record
		item = _presentation_item(session)
		old_item = id(item)
		before = session.backend_snapshot
		before_point = _first_point(before, "arrow1")
		session.scene.set_grid_snap_enabled(False)
		_drag(_edit_mode(session), item, (18.0, 0.0))
		after = session.backend_snapshot
		after_item = _presentation_item(session)
		moved_point = _first_point(after, "arrow1")
		after_item_id = id(after_item)
		selected_after_commit = after_item.isSelected()
		undo = session.undo_backend()

		assert (
			after.revision == before.revision + 1
			and moved_point[0] > before_point[0]
			and '<vendor:note keep="yes">opaque</vendor:note>' in after.cdml
			and submissions[0].mode == "translate"
			and submissions[0].delta == pytest.approx((18.0, 0.0))
			and session.document.undo_stack.count() == 0
			and after_item_id != old_item
			and selected_after_commit
			and undo.status == "accepted"
			and _first_point(session.backend_snapshot, "arrow1") == before_point
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_unavailable_and_idless_presentation_drags_restore_preview_without_undo(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Unaddressable synchronized presentation drags remain inert."""
	session = _native_session(main_window)
	idless_session = _native_session(main_window, _IDLESS_CDML)
	try:
		item = _presentation_item(session)
		start = item.document_object_model.points
		mode = _edit_mode(session)
		mode.set_presentation_translate_context(lambda: ("unavailable", None))
		session.scene.set_grid_snap_enabled(False)
		_drag(mode, item, (18.0, 0.0))
		unavailable_state = item.document_object_model.points
		idless_item = _presentation_item(idless_session)
		idless_start = idless_item.document_object_model.points
		idless_session.scene.set_grid_snap_enabled(False)
		_drag(_edit_mode(idless_session), idless_item, (18.0, 0.0))

		assert (
			session.backend_snapshot.revision == 0
			and unavailable_state == start
			and session.document.undo_stack.count() == 0
			and idless_session.backend_snapshot.revision == 0
			and idless_item.document_object_model.points == idless_start
			and idless_session.document.undo_stack.count() == 0
		)
	finally:
		for current in (idless_session, session):
			if current in main_window.sessions:
				main_window._remove_session(current)


#============================================
def test_presentation_drag_stays_with_its_originating_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A mode callback moves its own tab after another tab becomes active."""
	first_session = _native_session(main_window)
	second_session = _native_session(main_window)
	try:
		item = _presentation_item(first_session)
		first_session.scene.set_grid_snap_enabled(False)
		main_window._activate_session(second_session)
		_drag(_edit_mode(first_session), item, (18.0, 0.0))

		assert (
			first_session.backend_snapshot.revision == 1
			and second_session.backend_snapshot.revision == 0
			and first_session.document.undo_stack.count() == 0
		)
	finally:
		for current in (second_session, first_session):
			if current in main_window.sessions:
				main_window._remove_session(current)


#============================================
def test_presentation_drag_recovery_reprojects_without_resubmission(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Accepted presentation movement remains final when projection installation fails."""
	session = _native_session(main_window)
	try:
		submissions = []
		apply = session._backend_session.apply_top_level_transform
		def record(request: object) -> object:
			"""Record one backend request while preserving the real transform."""
			submissions.append(request)
			return apply(request)

		def unavailable(_snapshot: object) -> object:
			"""Report one post-acceptance projection installation failure."""
			return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
			)

		session._backend_session.apply_top_level_transform = record
		port = session._projection_lifecycle_port
		if port is None:
			raise RuntimeError("Native session has no projection lifecycle port")
		port._deliver = unavailable
		item = _presentation_item(session)
		session.scene.set_grid_snap_enabled(False)
		_drag(_edit_mode(session), item, (18.0, 0.0))
		accepted = session.backend_snapshot
		port._deliver = session.replace_projection_from_backend_snapshot
		retry = session.retry_current_backend_projection()

		assert (
			accepted.revision == 1
			and session.document.undo_stack.count() == 0
			and retry.status == "accepted"
			and session.backend_snapshot == accepted
			and len(submissions) == 1
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_presentation_drag_retains_local_move_for_a_legacy_isolated_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A real local edit retains the existing isolated presentation undo route."""
	session = _native_session(main_window)
	try:
		legacy_model = bkchem_qt.models.document_object.PresentationObject(
			"polyline", points=[(1.0, 1.0, None), (2.0, 2.0, None)],
		)
		legacy_item = bkchem_qt.canvas.document_projection.create_presentation_item(
			legacy_model,
		)
		if legacy_item is None:
			raise RuntimeError("Legacy presentation test item is unavailable")
		session.document.undo_stack.push(
			bkchem_qt.undo.commands.AddPresentationObjectCommand(
				session.document, session.scene, legacy_model, legacy_item,
			),
		)
		item = _presentation_item(session)
		undo_count = session.document.undo_stack.count()
		session.scene.set_grid_snap_enabled(False)
		_drag(_edit_mode(session), item, (18.0, 0.0))

		assert (
			session.presentation_translate_drag_authority() == "local"
			and session.backend_snapshot.revision == 0
			and session.document.undo_stack.count() == undo_count + 1
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)
