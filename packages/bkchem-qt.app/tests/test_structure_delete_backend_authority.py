"""Behavioral coverage for Qt's backend-authoritative partial Delete route."""

# PIP3 modules
import weakref

import pytest
import PySide6.QtCore
import PySide6.QtWidgets
import shiboken6

# local repo modules
import bkchem_qt.actions.context_menu
import bkchem_qt.canvas.items.arrow_item
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.main_window
import bkchem_qt.models.document_session
import bkchem_qt.models.projection_lifecycle
import oasa.cdml_document


_CHAIN_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/>'
	'<mark type="plus" x="1cm" y="2cm" size="10"/></atom>'
	'<atom id="a2" name="C"><point x="2cm" y="1cm"/></atom>'
	'<atom id="a3" name="C"><point x="3cm" y="1cm"/></atom>'
	'<atom id="a4" name="C"><point x="4cm" y="1cm"/></atom>'
	'<atom id="a5" name="O"><point x="5cm" y="1cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'<bond id="b2" start="a2" end="a3" type="n1"/>'
	'<bond id="b3" start="a3" end="a4" type="n1"/>'
	'<bond id="b4" start="a4" end="a5" type="n1"/>'
	'</molecule><molecule id="m2">'
	'<atom id="a6" name="N"><point x="7cm" y="1cm"/></atom>'
	'</molecule><arrow id="arrow1"><point x="1cm" y="3cm"/>'
	'<point x="3cm" y="3cm"/></arrow></cdml>'
)


#============================================
def _new_session(
		main_window: bkchem_qt.main_window.MainWindow,
		cdml_text: str = _CHAIN_CDML,
		) -> bkchem_qt.models.document_session.DocumentSession:
	"""Create and project one standalone native chain session."""
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
	assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
	return session


#============================================
def _install_projection_port(session: object, deliver: object) -> None:
	"""Install one fresh typed projection lifecycle port."""
	port = bkchem_qt.models.projection_lifecycle.SessionProjectionLifecyclePort(
		session, deliver,
	)
	session.install_projection_lifecycle_port(port)


#============================================
def _projection_unavailable(_snapshot: object) -> object:
	"""Return one typed projection preparation failure."""
	return bkchem_qt.models.projection_lifecycle.ProjectionLifecycleResult(
		bkchem_qt.models.projection_lifecycle.ProjectionLifecycleStatus.PREPARATION_UNAVAILABLE,
		bkchem_qt.models.projection_lifecycle.ProjectionLifecyclePhase.PREPARATION,
	)


#============================================
def _dispose_session(session: object) -> None:
	"""Release one standalone session through its MainWindow reaper."""
	owner = session.parent()
	if not isinstance(owner, bkchem_qt.main_window.MainWindow):
		raise TypeError("Standalone test session requires a MainWindow owner")
	owner._dispose_session_later(session)


#============================================
def _atom_item(session: object, atom_id: str) -> object:
	"""Return a current atom projection by durable ID."""
	return next(
		item for item in session.scene.items()
		if (
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id == atom_id
		)
	)


#============================================
def _bond_item(session: object, bond_id: str) -> object:
	"""Return a current bond projection by durable ID."""
	return next(
		item for item in session.scene.items()
		if (
			isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
			and item.bond_model.backend_durable_id == bond_id
		)
	)


#============================================
def _submit_ineligible_structure_delete(
		edit_mode: object, document: object, items: tuple[object, ...],
		) -> bool:
	"""Prove one public classifier rejection consumes the synchronized gesture."""
	assert bkchem_qt.canvas.document_projection.structure_delete_targets_for_items(
		document, items,
	) is None
	return edit_mode._submit_structure_delete(list(items))


#============================================
@pytest.mark.parametrize(
	("atom_ids", "bond_ids"),
	((("a2",), ()), ((), ("b3",)), (("a4",), ("b1",))),
)
def test_structure_delete_dispatches_plain_targets_once_without_qt_undo(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		atom_ids: tuple[str, ...], bond_ids: tuple[str, ...],
		) -> None:
	"""Atom-only, bond-only, and mixed requests share one immutable dispatcher."""
	session = _new_session(main_window)
	before = session.backend_snapshot
	undo_count = session.document.undo_stack.count()
	request = bkchem_qt.models.document_session.build_structure_delete_request(
		before.revision, "m1", atom_ids, bond_ids,
	)
	calls = []
	original = session._backend_session.delete_structure

	def execute(value: object) -> object:
		"""Record the exact backend value at the dispatch boundary."""
		calls.append(value)
		return original(value)

	monkeypatch.setattr(session._backend_session, "delete_structure", execute)
	try:
		outcome = session.submit_persistent_operation(request)
		assert (
			outcome.status == "accepted"
			and outcome.structural_result is None
			and len(calls) == 1
			and type(calls[0]) is oasa.cdml_document.CDMLStructureDeleteRequest
			and calls[0].atom_ids == atom_ids
			and calls[0].bond_ids == bond_ids
		)
		assert session._backend_history.can_undo
		assert session.document.undo_stack.count() == undo_count
		assert session.scene.selectedItems() == []
	finally:
		_dispose_session(session)


#============================================
def test_edit_mode_partial_delete_reprojects_canonical_components(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""EditMode deletes one durable atom and selects nothing in fresh components."""
	session = _new_session(main_window)
	edit_mode = session.mode_manager._modes["edit"]
	try:
		_atom_item(session, "a3").setSelected(True)
		edit_mode._delete_selected()
		fresh_atom_ids = {
			item.atom_model.backend_durable_id
			for item in session.scene.items()
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		}
		fresh_molecule_ids = {molecule.mol_id for molecule in session.document.molecules}
		assert (
			fresh_atom_ids == {"a1", "a2", "a4", "a5", "a6"}
			and "m1" in fresh_molecule_ids
			and len(fresh_molecule_ids) == 3
			and session.scene.selectedItems() == []
			and session.document.undo_stack.count() == 0
			and session.backend_projection_synchronized
		)
	finally:
		_dispose_session(session)


#============================================
@pytest.mark.parametrize("case", ("stale", "validation"))
def test_edit_mode_structure_delete_rejection_has_no_local_fallback(
		main_window: bkchem_qt.main_window.MainWindow,
		case: str,
		) -> None:
	"""Stale and typed backend rejection are final for one EditMode gesture."""
	cdml_text = _CHAIN_CDML
	if case == "validation":
		cdml_text = cdml_text.replace(
			'<molecule id="m1">', '<molecule id="m1" unsupported="yes">', 1,
		)
	session = _new_session(main_window, cdml_text)
	before = session.backend_snapshot
	edit_mode = session.mode_manager._modes["edit"]
	atom_item = _atom_item(session, "a2")
	if case == "stale":
		edit_mode.set_structure_delete_context(
			lambda: ("backend", before.revision - 1),
		)
	try:
		atom_item.setSelected(True)
		edit_mode._delete_selected()
		assert (
			session.backend_snapshot == before
			and session.document.undo_stack.count() == 0
			and session.backend_projection_synchronized
			and not session.legacy_isolated
			and atom_item in session.scene.items()
		)
	finally:
		atom_item = None
		_dispose_session(session)


#============================================
def test_accepted_projection_failure_retries_snapshot_without_resubmission(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An accepted Delete records once and retry only installs backend_snapshot."""
	session = _new_session(main_window)
	calls = []
	original = session._operation_commit_executors["structure-delete"]

	def execute(prepared: object) -> object:
		"""Count candidate execution without changing its backend behavior."""
		calls.append(prepared)
		return original(prepared)

	monkeypatch.setitem(session._operation_commit_executors, "structure-delete", execute)
	_install_projection_port(session, _projection_unavailable)
	request = bkchem_qt.models.document_session.build_structure_delete_request(
		session.backend_snapshot.revision, "m1", ("a2",), (),
	)
	try:
		outcome = session.submit_persistent_operation(request)
		accepted = session.backend_snapshot
		_install_projection_port(
			session, session.replace_projection_from_backend_snapshot,
		)
		recovered = session.retry_current_backend_projection()
		assert (
			outcome.status == "unavailable"
			and outcome.submitted
			and len(calls) == 1
			and session._backend_history.can_undo
		)
		assert (
			recovered.status == "accepted"
			and session.backend_snapshot == accepted
			and session.backend_projection_synchronized
			and len(calls) == 1
		)
	finally:
		_dispose_session(session)


#============================================
@pytest.mark.parametrize(
		"case",
		(
			"two-molecules", "presentation", "foreign", "id-less", "mixed-mark",
			"unavailable",
		),
)
def test_synchronized_ineligible_partial_delete_is_inert(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch, case: str,
		) -> None:
	"""Representative invalid synchronized selections never become Qt commands."""
	session = _new_session(main_window)
	edit_mode = session.mode_manager._modes["edit"]
	before = session.backend_snapshot
	try:
		first = _atom_item(session, "a2")
		if case == "two-molecules":
			second = _atom_item(session, "a6")
		elif case == "presentation":
			second = next(
				item for item in session.scene.items()
				if getattr(getattr(item, "document_object_model", None), "object_id", None)
				== "arrow1"
			)
		elif case == "foreign":
			monkeypatch.setattr(
				session.document, "is_current_projection_item", lambda _item: False,
			)
			second = None
		elif case == "mixed-mark":
			first = next(
				item for item in session.scene.items()
				if isinstance(item, bkchem_qt.canvas.items.mark_item.MarkItem)
			)
			second = _atom_item(session, "a2")
		elif case == "unavailable":
			session.clear_projection_lifecycle_port()
			second = None
		else:
			first.atom_model.bind_backend_durable_id(None)
			second = None
		first.setSelected(True)
		if second is not None:
			second.setSelected(True)
		edit_mode._delete_selected()
		assert (
			session.backend_snapshot == before
			and not session.document.undo_stack.canUndo()
			and not session.legacy_isolated
		)
	finally:
		first = None
		second = None
		_dispose_session(session)


#============================================
@pytest.mark.parametrize(
		"case", ("duplicate", "retired", "lookalike", "unsupported"),
)
def test_ineligible_structure_delete_classifier_consumes_without_local_fallback(
		main_window: bkchem_qt.main_window.MainWindow, case: str,
		) -> None:
	"""Invalid current-projection evidence leaves a synchronized Delete inert."""
	session = _new_session(main_window)
	other_session = None
	edit_mode = session.mode_manager._modes["edit"]
	before = session.backend_snapshot
	before_history = session._backend_history
	before_can_undo = session.can_undo_backend
	before_can_redo = session.can_redo_backend
	item = None
	lookalike = None
	unsupported = None
	items = ()
	try:
		if case == "duplicate":
			item = _atom_item(session, "a2")
			items = (item, item)
		elif case == "retired":
			item = _atom_item(session, "a2")
			session.document.register_current_projection_items(())
			assert not session.document.is_current_projection_item(item)
			items = (item,)
		elif case == "lookalike":
			other_session = _new_session(main_window)
			lookalike = _atom_item(other_session, "a2")
			assert other_session.document.is_current_projection_item(lookalike)
			items = (lookalike,)
		else:
			unsupported = next(
				item for item in session.scene.items()
				if isinstance(item, bkchem_qt.canvas.items.arrow_item.ArrowItem)
			)
			assert session.document.is_current_projection_item(unsupported)
			items = (unsupported,)
		assert _submit_ineligible_structure_delete(
			edit_mode, session.document, items,
		)
		assert (
			session.backend_snapshot == before
			and session.backend_snapshot.revision == before.revision
			and session._backend_history is before_history
			and session.can_undo_backend == before_can_undo
			and session.can_redo_backend == before_can_redo
			and session.document.undo_stack.count() == 0
			and not session.legacy_isolated
		)
	finally:
		items = ()
		item = None
		lookalike = None
		unsupported = None
		if other_session is not None:
			_dispose_session(other_session)
		_dispose_session(session)


#============================================
def test_context_menu_structure_delete_uses_one_backend_request_and_fresh_projection(
		main_window: bkchem_qt.main_window.MainWindow,
		monkeypatch: pytest.MonkeyPatch, qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""The production popup Delete submits once and retires before reprojection."""
	session = _new_session(main_window)
	main_window._register_session(session, activate=True)
	before = session.backend_snapshot
	calls = []
	original = session._backend_session.delete_structure

	def execute(request: object) -> object:
		"""Record the one plain request received by the backend authority."""
		calls.append(request)
		return original(request)

	def trigger_popup_delete() -> None:
		"""Activate and close the menu owned by production's nested popup loop."""
		popup = qapp.activePopupWidget()
		if not isinstance(popup, PySide6.QtWidgets.QMenu):
			raise AssertionError("Context menu did not enter the Qt popup loop")
		delete_action = next(
			action for action in popup.actions()
			if action.text().replace("&", "") == "Delete"
		)
		delete_action.trigger()
		popup.close()
		del delete_action
		del popup

	monkeypatch.setattr(session._backend_session, "delete_structure", execute)
	try:
		target = _bond_item(session, "b2")
		scene_position = target.sceneBoundingRect().center()
		view_position = session.view.mapFromScene(scene_position)
		screen_position = session.view.mapToGlobal(view_position)
		target = None
		PySide6.QtCore.QTimer.singleShot(0, trigger_popup_delete)
		bkchem_qt.actions.context_menu.show_context_menu(
			session.view, scene_position, screen_position,
		)
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.DeferredDelete,
		)
		qapp.processEvents()
		fresh_bond_ids = {
			item.bond_model.backend_durable_id
			for item in session.scene.items()
			if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
		}
		assert (
			len(calls) == 1
			and session.backend_snapshot.revision == before.revision + 1
			and 'id="b2"' not in session.backend_snapshot.cdml
			and "b2" not in fresh_bond_ids
			and session.document.undo_stack.count() == 0
			and session._backend_history.can_undo
			and session.backend_projection_synchronized
		)
	finally:
		main_window._remove_session(session)


#============================================
def test_legacy_context_delete_callback_holds_weak_item_reference_only(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Local Delete callbacks retain only the view and one weak item reference."""
	session = _new_session(main_window)
	main_window._register_session(session, activate=True)
	session._legacy_isolated = True
	callback = None
	try:
		target = _atom_item(session, "a2")
		callback = bkchem_qt.actions.context_menu._structure_delete_callback(
			session.view, target,
		)
		values = tuple(
			cell.cell_contents for cell in callback.__closure__ or ()
		)
		assert (
			any(isinstance(value, weakref.ReferenceType) for value in values)
			and not any(
				isinstance(value, PySide6.QtWidgets.QGraphicsItem)
				for value in values
			)
		)
	finally:
		callback = None
		main_window._remove_session(session)


#============================================
def test_legacy_context_menu_delete_is_undoable_and_popup_retires(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A production legacy popup deletes locally, supports undo, and retires."""
	session = _new_session(main_window)
	main_window._register_session(session, activate=True)
	session._legacy_isolated = True
	captured_popup = []
	destroyed = []
	try:
		target = _atom_item(session, "a2")
		scene_position = target.sceneBoundingRect().center()
		view_position = session.view.mapFromScene(scene_position)
		screen_position = session.view.mapToGlobal(view_position)
		target = None

		def trigger_popup_delete() -> None:
			"""Choose Delete through the production nested popup event loop."""
			popup = qapp.activePopupWidget()
			if not isinstance(popup, PySide6.QtWidgets.QMenu):
				raise AssertionError("Context menu did not enter the Qt popup loop")
			captured_popup.append(popup)
			popup.destroyed.connect(lambda: destroyed.append(True))
			delete_action = next(
				action for action in popup.actions()
				if action.text().replace("&", "") == "Delete"
			)
			delete_action.trigger()
			popup.close()
			del delete_action
			del popup

		PySide6.QtCore.QTimer.singleShot(0, trigger_popup_delete)
		bkchem_qt.actions.context_menu.show_context_menu(
			session.view, scene_position, screen_position,
		)
		PySide6.QtCore.QCoreApplication.sendPostedEvents(
			None, PySide6.QtCore.QEvent.Type.DeferredDelete,
		)
		qapp.processEvents()
		assert (
			session.document.undo_stack.count() == 1
			and not any(
				isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
				and item.atom_model.backend_durable_id == "a2"
				for item in session.scene.items()
			)
			and captured_popup
			and destroyed
			and not shiboken6.isValid(captured_popup[0])
		)
		session.document.undo_stack.undo()
		assert any(
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and item.atom_model.backend_durable_id == "a2"
			for item in session.scene.items()
		)
	finally:
		captured_popup.clear()
		main_window._remove_session(session)


#============================================
def test_retired_legacy_context_delete_target_is_inert(
		main_window: bkchem_qt.main_window.MainWindow,
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""A retired local target cannot enter the undo route after reprojection."""
	session = _new_session(main_window)
	main_window._register_session(session, activate=True)
	session._legacy_isolated = True
	callback = None
	try:
		target = _atom_item(session, "a2")
		callback = bkchem_qt.actions.context_menu._structure_delete_callback(
			session.view, target,
		)
		target = None
		assert session.replace_projection_from_backend_snapshot(session.backend_snapshot)
		qapp.processEvents()
		callback()
		assert session.document.undo_stack.count() == 0
	finally:
		callback = None
		main_window._remove_session(session)
