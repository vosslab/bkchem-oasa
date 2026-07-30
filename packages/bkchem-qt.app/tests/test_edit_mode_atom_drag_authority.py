"""Focused backend-authority checks for EditMode atom-only mouse drags."""

# Standard Library
import re

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.document_projection
import bkchem_qt.main_window
import bkchem_qt.models.document_object
import bkchem_qt.models.document_session
import bkchem_qt.modes.edit_mode
import bkchem_qt.undo.commands
import oasa.cdml_document


_CDML = (
	'<cdml xmlns:vendor="urn:vendor" version="26.07">'
	'<molecule id="m1"><atom id="a1" name="C"><point x="1cm" y="1cm"/>'
	'<mark type="plus"/></atom><atom id="a2" name="O"><point x="2cm" y="1cm"/>'
	'</atom></molecule><vendor:note keep="yes">opaque</vendor:note></cdml>'
)


#============================================
class _MouseEvent:
	"""Provide deterministic modifier state for direct EditMode dispatch."""

	#============================================
	def __init__(self, modifiers: PySide6.QtCore.Qt.KeyboardModifier) -> None:
		"""Store the modifier mask used by the active gesture."""
		self._modifiers = modifiers

	#============================================
	def modifiers(self) -> PySide6.QtCore.Qt.KeyboardModifier:
		"""Return the event modifier mask."""
		return self._modifiers


#============================================
def _native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Install one native backend session containing two durable atoms."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise RuntimeError("Native CDML projection is unavailable")
	return registered


#============================================
def _atom_items(session: object) -> tuple[object, object]:
	"""Return direct-core atom items in durable identifier order."""
	items = sorted(
		(
			item for item in session.scene.items()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		),
		key=lambda item: item.atom_model.backend_durable_id,
	)
	if len(items) != 2:
		raise AssertionError("Expected two projected atom items")
	return tuple(items)


#============================================
def _edit_mode(session: object) -> bkchem_qt.modes.edit_mode.EditMode:
	"""Select the session-owned EditMode instance."""
	session.mode_manager.set_mode("edit")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.edit_mode.EditMode):
		raise TypeError("Edit mode unavailable")
	return mode


#============================================
def _drag(
		mode: bkchem_qt.modes.edit_mode.EditMode, item: object,
		delta: tuple[float, float], modifiers: PySide6.QtCore.Qt.KeyboardModifier,
		) -> None:
	"""Dispatch one complete atom drag from an item's current scene position."""
	start = item.scenePos()
	finish = PySide6.QtCore.QPointF(start.x() + delta[0], start.y() + delta[1])
	mode.mouse_press(start, _MouseEvent(PySide6.QtCore.Qt.KeyboardModifier.NoModifier))
	gesture_event = _MouseEvent(modifiers)
	mode.mouse_move(finish, gesture_event)
	mode.mouse_release(finish, gesture_event)


#============================================
def _selected_ids(session: object) -> set[str]:
	"""Read durable selected atom identifiers from the current projection."""
	return {
		item.atom_model.backend_durable_id
		for item in session.scene.selectedItems()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
	}


#============================================
def _accepted_coordinates(snapshot: object) -> dict[str, tuple[float, float]]:
	"""Read coordinates only after the hardened CDML boundary accepts them."""
	document = oasa.cdml_document.CDMLDocument.parse(snapshot.cdml, validation="strict")
	coordinates = {}
	for atom_id in ("a1", "a2"):
		record = document.find_by_id(atom_id)
		if record is None:
			raise AssertionError("Accepted CDML did not retain atom: %s" % atom_id)
		values = dict(re.findall(r'\b([xy])="([^"]+)"', record.raw_xml))
		coordinates[atom_id] = tuple(
			float(values[axis].removesuffix("cm")) for axis in ("x", "y")
		)
	return coordinates


#============================================
def test_atom_only_drag_commits_originating_backend_and_restores_selection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An axis-locked two-atom drag commits once and preserves unrelated CDML."""
	session = _native_session(main_window)
	try:
		first, second = _atom_items(session)
		old_projection_ids = {id(first), id(second)}
		session.scene.set_grid_snap_enabled(False)
		first.setSelected(True)
		second.setSelected(True)
		before = session.backend_snapshot
		before_coordinates = _accepted_coordinates(before)
		mode = _edit_mode(session)
		_drag(mode, first, (12.0, 7.0), PySide6.QtCore.Qt.KeyboardModifier.ShiftModifier)
		after = session.backend_snapshot
		after_coordinates = _accepted_coordinates(after)
		first_after, second_after = _atom_items(session)
		selected_after_commit = _selected_ids(session)
		backend_undo_available = session.can_undo_backend
		shared_deltas = tuple(
			after_coordinates[atom_id][0] - before_coordinates[atom_id][0]
			for atom_id in ("a1", "a2")
		)
		backend_undo = session.undo_backend()
		restored_coordinates = _accepted_coordinates(session.backend_snapshot)

		assert (
			after.revision == before.revision + 1
			and '<vendor:note keep="yes">opaque</vendor:note>' in after.cdml
			and '<mark type="plus"/>' in after.cdml
			and session.document.undo_stack.count() == 0
			and shared_deltas[0] == shared_deltas[1]
			and shared_deltas[0] > 0.0
			and all(
				after_coordinates[atom_id][1] == before_coordinates[atom_id][1]
				for atom_id in ("a1", "a2")
			)
			and backend_undo_available
			and backend_undo.status == "accepted"
			and restored_coordinates == before_coordinates
			and all(id(item) not in old_projection_ids for item in (first_after, second_after))
			and selected_after_commit == {"a1", "a2"}
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_atom_drag_uses_its_own_tab_when_another_tab_is_active(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A callback captured by the first mode cannot redirect to the active tab."""
	first_session = _native_session(main_window)
	second_session = _native_session(main_window)
	try:
		first, _second = _atom_items(first_session)
		first_session.scene.set_grid_snap_enabled(False)
		first.setSelected(True)
		mode = _edit_mode(first_session)
		main_window._activate_session(second_session)
		_drag(mode, first, (12.0, 0.0), PySide6.QtCore.Qt.KeyboardModifier.NoModifier)

		assert (
			first_session.backend_snapshot.revision == 1
			and second_session.backend_snapshot.revision == 0
			and first_session.document.undo_stack.count() == 0
		)
	finally:
		for session in (second_session, first_session):
			if session in main_window.sessions:
				main_window._remove_session(session)


#============================================
def test_unavailable_or_idless_atom_drag_restores_preview_without_local_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Unavailable and unaddressable synchronized drags remain inert."""
	session = _native_session(main_window)
	try:
		first, second = _atom_items(session)
		session.scene.set_grid_snap_enabled(False)
		first.setSelected(True)
		second.setSelected(True)
		before = session.backend_snapshot
		first_start = (first.atom_model.x, first.atom_model.y)
		mode = _edit_mode(session)
		mode.set_atom_translate_authority(lambda: "unavailable")
		_drag(mode, first, (12.0, 0.0), PySide6.QtCore.Qt.KeyboardModifier.NoModifier)
		unavailable_state = (first.atom_model.x, first.atom_model.y)
		mode.set_atom_translate_authority(session.atom_translate_drag_authority)
		first.atom_model.bind_backend_durable_id(None)
		_drag(mode, first, (12.0, 0.0), PySide6.QtCore.Qt.KeyboardModifier.NoModifier)

		assert (
			session.backend_snapshot == before
			and unavailable_state == first_start
			and (first.atom_model.x, first.atom_model.y) == first_start
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_rejected_atom_drag_restores_preview_without_local_history(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A typed session rejection cannot leave the responsive preview committed."""
	session = _native_session(main_window)
	try:
		first, _second = _atom_items(session)
		session.scene.set_grid_snap_enabled(False)
		first.setSelected(True)
		before = session.backend_snapshot
		start = (first.atom_model.x, first.atom_model.y)
		mode = _edit_mode(session)
		mode.set_atom_translate_operation(
			lambda _targets, _delta: bkchem_qt.models.document_session.PersistentActionOutcome(
				"rejected", "Move rejected", None, False,
			),
		)
		_drag(mode, first, (12.0, 0.0), PySide6.QtCore.Qt.KeyboardModifier.NoModifier)

		assert (
			session.backend_snapshot == before
			and (first.atom_model.x, first.atom_model.y) == start
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_legacy_isolated_atom_drag_keeps_one_local_undoable_move(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A real prior local edit selects the intended local drag authority."""
	session = _native_session(main_window)
	try:
		first, _second = _atom_items(session)
		session.scene.set_grid_snap_enabled(False)
		legacy_model = bkchem_qt.models.document_object.PresentationObject(
			"polyline", points=[(1.0, 1.0, None), (2.0, 2.0, None)],
		)
		legacy_item = bkchem_qt.canvas.document_projection.create_presentation_item(
			legacy_model,
		)
		session.document.undo_stack.push(
			bkchem_qt.undo.commands.AddPresentationObjectCommand(
				session.document, session.scene, legacy_model, legacy_item,
			),
		)
		first.setSelected(True)
		undo_count = session.document.undo_stack.count()
		mode = _edit_mode(session)
		_drag(mode, first, (12.0, 0.0), PySide6.QtCore.Qt.KeyboardModifier.NoModifier)

		assert (
			session.atom_translate_drag_authority() == "local"
			and session.document.undo_stack.count() == undo_count + 1
			and session.backend_snapshot.revision == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)
