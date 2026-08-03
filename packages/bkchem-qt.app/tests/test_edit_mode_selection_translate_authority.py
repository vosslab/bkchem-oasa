"""Focused backend-authority checks for EditMode mixed selection drags."""

# PIP3 modules
import PySide6.QtCore
import pytest
import shiboken6

# local repo modules
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.models.document_object
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import bkchem_qt.modes.edit_mode
import bkchem_qt.undo.commands
import oasa.cdml_document


_CDML = (
	'<cdml version="26.07"><molecule id="m1"><atom id="a1" name="C">'
	'<point x="1cm" y="1cm"/></atom></molecule><arrow id="arrow1">'
	'<point x="3cm" y="1cm"/><point x="5cm" y="1cm"/>'
	'</arrow></cdml>'
)


#============================================
class _MouseEvent:
	"""Provide the deterministic modifier state expected by EditMode."""

	#============================================
	def modifiers(self) -> PySide6.QtCore.Qt.KeyboardModifier:
		"""Return the no-modifier gesture state."""
		return PySide6.QtCore.Qt.KeyboardModifier.NoModifier


#============================================
def _native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Install one native session containing one atom and one arrow root."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise RuntimeError("Native CDML projection is unavailable")
	return registered


#============================================
def _projection_pair(session: object) -> tuple[object, object]:
	"""Return the native atom and arrow wrappers from the current projection."""
	atom = next(
		item for item in session.scene.items()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
	)
	arrow = next(
		item for item in session.scene.items()
		if getattr(getattr(item, "document_object_model", None), "kind", None) == "arrow"
	)
	return atom, arrow


#============================================
def _selected_pair(session: object) -> tuple[object, object]:
	"""Select and return the native atom and arrow wrappers."""
	atom, arrow = _projection_pair(session)
	atom.setSelected(True)
	arrow.setSelected(True)
	return atom, arrow


#============================================
def _edit_mode(session: object) -> bkchem_qt.modes.edit_mode.EditMode:
	"""Activate and return the session-owned edit interaction mode."""
	session.mode_manager.set_mode("edit")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.edit_mode.EditMode):
		raise TypeError("Edit mode unavailable")
	return mode


#============================================
def _mixed_drag(mode: object, atom: object, delta: tuple[float, float]) -> None:
	"""Drive one complete native mixed-selection drag from the atom wrapper."""
	start = atom.scenePos()
	finish = PySide6.QtCore.QPointF(start.x() + delta[0], start.y() + delta[1])
	event = _MouseEvent()
	mode.mouse_press(start, event)
	mode.mouse_move(finish, event)
	mode.mouse_release(finish, event)


#============================================
def test_mixed_drag_commits_one_backend_revision_and_reprojects(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A native atom-and-arrow move has backend history and fresh wrappers."""
	session = _native_session(main_window)
	try:
		atom, arrow = _selected_pair(session)
		old_wrappers = {id(atom), id(arrow)}
		session.scene.set_grid_snap_enabled(False)
		before = session.backend_snapshot
		_mixed_drag(_edit_mode(session), atom, (18.0, 0.0))
		after = session.backend_snapshot
		accepted = oasa.cdml_document.CDMLDocument.parse(after.cdml, validation="strict")
		before_document = oasa.cdml_document.CDMLDocument.parse(before.cdml, validation="strict")
		new_atom, new_arrow = _projection_pair(session)
		selected = set(session.scene.selectedItems())
		saved_geometry_changed = (
			accepted.find_by_id("a1").raw_xml != before_document.find_by_id("a1").raw_xml
			and accepted.find_by_id("arrow1").raw_xml != before_document.find_by_id("arrow1").raw_xml
		)
		projection_rebuilt_with_selection = (
			id(new_atom) not in old_wrappers and id(new_arrow) not in old_wrappers
			and new_atom in selected and new_arrow in selected
			and not shiboken6.isValid(atom) and not shiboken6.isValid(arrow)
		)

		assert after.revision == before.revision + 1 and session.document.undo_stack.count() == 0
		assert saved_geometry_changed and projection_rebuilt_with_selection
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_mixed_drag_uses_the_press_session_after_tab_activation(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A tab switch after press cannot redirect a frozen mixed-drag callback."""
	first_session = _native_session(main_window)
	second_session = _native_session(main_window)
	try:
		atom, _arrow = _selected_pair(first_session)
		first_session.scene.set_grid_snap_enabled(False)
		mode = _edit_mode(first_session)
		start = atom.scenePos()
		finish = PySide6.QtCore.QPointF(start.x() + 18.0, start.y())
		event = _MouseEvent()
		mode.mouse_press(start, event)
		main_window._activate_session(second_session)
		mode.mouse_move(finish, event)
		mode.mouse_release(finish, event)
		press_session_only_committed = (
			first_session.backend_snapshot.revision == 1
			and second_session.backend_snapshot.revision == 0
		)

		assert press_session_only_committed
	finally:
		for session in (second_session, first_session):
			if session in main_window.sessions:
				main_window._remove_session(session)


#============================================
def test_unavailable_mixed_drag_restores_preview_without_local_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An unavailable synchronized mixed route is inert after preview recovery."""
	session = _native_session(main_window)
	try:
		atom, arrow = _selected_pair(session)
		start = (atom.atom_model.x, arrow.document_object_model.points)
		session.scene.set_grid_snap_enabled(False)
		mode = _edit_mode(session)
		mode.set_selection_translate_context(lambda: ("unavailable", None))
		_mixed_drag(mode, atom, (18.0, 0.0))

		assert session.backend_snapshot.revision == 0 and session.document.undo_stack.count() == 0
		assert (atom.atom_model.x, arrow.document_object_model.points) == start
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
@pytest.mark.parametrize(
	"failure_kind", ("revision-conflict", "validation"),
)
def test_rejected_mixed_drag_restores_preview_without_history(
		failure_kind: str, main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Typed rejection preserves the pre-gesture document and preview geometry."""
	session = _native_session(main_window)
	try:
		atom, arrow = _selected_pair(session)
		start = (atom.atom_model.x, arrow.document_object_model.points)
		submissions = []
		mode = _edit_mode(session)

		def reject(*request: object) -> bkchem_qt.models.document_session.PersistentActionOutcome:
			"""Return one deterministic typed backend outcome through the press seam."""
			submissions.append(request)
			return bkchem_qt.models.document_session.PersistentActionOutcome(
				"rejected", "Move rejected", None, False, None, failure_kind,
			)

		mode.set_selection_translate_operation(reject)
		session.scene.set_grid_snap_enabled(False)
		_mixed_drag(mode, atom, (18.0, 0.0))
		preview_and_local_history_unchanged = (
			(atom.atom_model.x, arrow.document_object_model.points) == start
			and session.document.undo_stack.count() == 0
		)

		assert len(submissions) == 1 and session.backend_snapshot.revision == 0
		assert preview_and_local_history_unchanged
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_mixed_drag_recovery_uses_accepted_snapshot_without_resubmission(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Recovery installs one accepted move without repeating its backend intent."""
	session = _native_session(main_window)
	try:
		atom, arrow = _selected_pair(session)
		before = session.backend_snapshot
		before_document = oasa.cdml_document.CDMLDocument.parse(
			before.cdml, validation="strict",
		)
		executor = session._operation_commit_executors["selection-translate"]
		submissions = []

		def record(prepared: object) -> object:
			"""Record the one accepted backend executor call."""
			submissions.append(prepared)
			return executor(prepared)

		def unavailable(_snapshot: object) -> object:
			"""Report the first accepted installation as unavailable."""
			return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
				bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.INSTALLATION_FAILED,
				bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.INSTALLATION,
			)

		port = session._projection_lifecycle_port
		if port is None:
			raise RuntimeError("Native session has no projection lifecycle port")
		delivery = port._deliver
		session._operation_commit_executors["selection-translate"] = record
		port._deliver = unavailable
		session.scene.set_grid_snap_enabled(False)
		_mixed_drag(_edit_mode(session), atom, (18.0, 0.0))
		accepted = session.backend_snapshot
		accepted_document = oasa.cdml_document.CDMLDocument.parse(
			accepted.cdml, validation="strict",
		)
		accepted_backend_state = (
			len(submissions) == 1
			and accepted.revision == before.revision + 1
			and session.document.undo_stack.count() == 0
			and accepted_document.find_by_id("a1").raw_xml
			!= before_document.find_by_id("a1").raw_xml
			and accepted_document.find_by_id("arrow1").raw_xml
			!= before_document.find_by_id("arrow1").raw_xml
		)
		port._deliver = delivery
		retried = session.retry_current_backend_projection()
		new_atom, new_arrow = _projection_pair(session)
		selected = set(session.scene.selectedItems())
		recovered_projection_state = (
			retried.status == "accepted"
			and session.backend_snapshot == accepted
			and session.has_backend_navigation and session.can_undo_backend
			and shiboken6.isValid(new_atom) and shiboken6.isValid(new_arrow)
			and new_atom in selected and new_arrow in selected
			and not shiboken6.isValid(atom) and not shiboken6.isValid(arrow)
			and len(submissions) == 1
		)

		assert accepted_backend_state
		assert recovered_projection_state
	finally:
		if "port" in locals() and "delivery" in locals():
			port._deliver = delivery
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_lookalike_mixed_drag_restores_preview_without_backend_submission(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A selected unregistered wrapper for a real arrow is inert."""
	session = _native_session(main_window)
	lookalike = None
	try:
		atom, arrow = _selected_pair(session)
		arrow.setSelected(False)
		lookalike = bkchem_qt.canvas.document_projection.create_presentation_item(
			arrow.document_object_model,
		)
		if lookalike is None:
			raise RuntimeError("Lookalike presentation test item is unavailable")
		session.scene.addItem(lookalike)
		lookalike.setSelected(True)
		lookalike_not_current = not session.document.is_current_projection_item(lookalike)
		start = (atom.atom_model.x, arrow.document_object_model.points)
		executor = session._operation_commit_executors["selection-translate"]
		submissions = []

		def record(prepared: object) -> object:
			"""Record any invalid submission before delegating to the backend."""
			submissions.append(prepared)
			return executor(prepared)

		session._operation_commit_executors["selection-translate"] = record
		session.scene.set_grid_snap_enabled(False)
		_mixed_drag(_edit_mode(session), atom, (18.0, 0.0))
		inert_without_persistence = (
			lookalike_not_current and not submissions
			and session.backend_snapshot.revision == 0
			and session.document.undo_stack.count() == 0
		)
		preview_restored = (atom.atom_model.x, arrow.document_object_model.points) == start

		assert inert_without_persistence
		assert preview_restored
	finally:
		if lookalike is not None and shiboken6.isValid(lookalike):
			lookalike_scene = lookalike.scene()
			if lookalike_scene is not None and shiboken6.isValid(lookalike_scene):
				lookalike_scene.removeItem(lookalike)
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_unequal_mixed_drag_deltas_restore_preview_without_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A reshaped mixed preview cannot be reduced to one backend translation."""
	session = _native_session(main_window)
	try:
		atom, arrow = _selected_pair(session)
		start = (atom.atom_model.x, arrow.document_object_model.points)
		mode = _edit_mode(session)
		origin = atom.scenePos()
		finish = PySide6.QtCore.QPointF(origin.x() + 18.0, origin.y())
		session.scene.set_grid_snap_enabled(False)
		mode.mouse_press(origin, _MouseEvent())
		mode.mouse_move(finish, _MouseEvent())
		arrow.document_object_model.set_points([
			(x + 1.0, y, z) for x, y, z in arrow.document_object_model.points
		])
		mode.mouse_release(finish, _MouseEvent())

		assert session.backend_snapshot.revision == 0 and session.document.undo_stack.count() == 0
		assert (atom.atom_model.x, arrow.document_object_model.points) == start
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_legacy_isolated_mixed_drag_uses_one_local_macro(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A real legacy mutation retains the one-macro local mixed-drag route."""
	session = _native_session(main_window)
	try:
		legacy = bkchem_qt.models.document_object.PresentationObject(
			"polyline", points=[(1.0, 1.0, None), (2.0, 2.0, None)],
		)
		legacy_item = bkchem_qt.canvas.document_projection.create_presentation_item(legacy)
		if legacy_item is None:
			raise RuntimeError("Legacy presentation test item is unavailable")
		session.document.undo_stack.push(
			bkchem_qt.undo.commands.AddPresentationObjectCommand(
				session.document, session.scene, legacy, legacy_item,
			),
		)
		atom, _arrow = _selected_pair(session)
		undo_count = session.document.undo_stack.count()
		session.scene.set_grid_snap_enabled(False)
		_mixed_drag(_edit_mode(session), atom, (18.0, 0.0))
		legacy_macro_added = (
			session.backend_snapshot.revision == 0
			and session.document.undo_stack.count() == undo_count + 1
		)

		assert legacy_macro_added
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)
