"""Focused Qt authority checks for atomic Atom Properties commits."""

# PIP3 modules
import PySide6.QtWidgets
import PySide6.QtCore
import pytest

# local repo modules
import bkchem_qt.actions.context_menu
import bkchem_qt.actions.object_actions
import bkchem_qt.actions.property_editing
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.dialogs.atom_dialog
import bkchem_qt.main_window
import bkchem_qt.modes.draw_mode
import bkchem_qt.models.document_session


_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'</molecule></cdml>'
)


#============================================
def _active_session(main_window: object) -> object:
	"""Return the session currently projected by the public main window."""
	return next(session for session in main_window.sessions if session.document is main_window.document)


#============================================
def _draw_atom(session: object) -> object:
	"""Create one synchronized atom and return its live projected model."""
	session.mode_manager.set_mode("draw")
	mode = session.mode_manager.current_mode
	if not isinstance(mode, bkchem_qt.modes.draw_mode.DrawMode):
		raise AssertionError("Draw mode unavailable")
	position = PySide6.QtCore.QPointF(100.0, 100.0)
	mode.mouse_press(position, None)
	mode.mouse_release(position, None)
	return next(
		item.atom_model for item in session.scene.items()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
	)


#============================================
def _install_native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Register one native CDML session with a durable atom target."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native CDML projection is unavailable")
	return registered


#============================================
def _atom_item(session: object) -> object:
	"""Return the session's one direct-core atom projection."""
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			return item
	raise AssertionError("Projected CDML did not produce an AtomItem")


#============================================
def _properties_action(menu: PySide6.QtWidgets.QMenu) -> object:
	"""Return the public atom Properties action from a context menu."""
	for action in menu.actions():
		if action.text() == "Properties...":
			return action
	raise AssertionError("Atom Properties action is absent")


#============================================
def _selected_atom_ids(session: object) -> set[str]:
	"""Read durable atom IDs from the current fresh projection selection."""
	return {
		item.atom_model.backend_durable_id
		for item in session.scene.selectedItems()
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		and item.atom_model.backend_durable_id is not None
	}


#============================================
def _accept_changes(monkeypatch: pytest.MonkeyPatch, changes: tuple[tuple[str, object], ...]) -> None:
	"""Make the detached dialog return one explicit immutable atom intent."""
	def accept(_dialog: object) -> int:
		"""Return the ordinary accepted dialog code."""
		return PySide6.QtWidgets.QDialog.DialogCode.Accepted

	def returned_changes(_dialog: object) -> tuple[tuple[str, object], ...]:
		"""Return exactly the caller-provided plain operation fields."""
		return changes

	monkeypatch.setattr(bkchem_qt.dialogs.atom_dialog.AtomDialog, "exec", accept)
	monkeypatch.setattr(bkchem_qt.dialogs.atom_dialog.AtomDialog, "changes", returned_changes)


#============================================
def test_atom_dialog_detaches_from_model_after_initialization(qtbot: object) -> None:
	"""Dialog retains scalar inputs rather than a potentially retired projection model."""
	class Atom:
		symbol = "C"
		charge = 0
		valency = 0
		isotope = None
		multiplicity = 1
		show = False
		show_hydrogens = False
		font_size = 12
		line_color = "#000000"

	dialog = bkchem_qt.dialogs.atom_dialog.AtomDialog(Atom())
	qtbot.addWidget(dialog)

	assert not hasattr(dialog, "_atom_model") and dialog.changes() == ()


#============================================
def test_atom_properties_use_exact_backend_session_and_no_qt_undo(
		main_window: object, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Accepted Properties intent replaces the projection from one backend commit."""
	session = _active_session(main_window)
	atom = _draw_atom(session)
	atom_id = atom.backend_durable_id
	before = session.backend_snapshot

	def accept_with_charge(dialog: object) -> object:
		"""Set deterministic dialog intent before accepting it."""
		dialog._charge_spin.setValue(1)
		return PySide6.QtWidgets.QDialog.DialogCode.Accepted

	monkeypatch.setattr(bkchem_qt.dialogs.atom_dialog.AtomDialog, "exec", accept_with_charge)
	changed = bkchem_qt.actions.property_editing.edit_atom_properties(
		atom, session.view, session.document.undo_stack,
	)

	assert (
		changed and session.backend_snapshot.revision == before.revision + 1
		and 'id="%s"' % atom_id in session.backend_snapshot.cdml
		and 'charge="1"' in session.backend_snapshot.cdml
		and session.document.undo_stack.count() == 0
	)


#============================================
def test_atom_properties_session_outcome_unwraps_the_accepted_commit(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Session results expose the accepted commit, not the backend result wrapper."""
	session = _install_native_session(main_window)
	try:
		outcome = session.submit_atom_properties_patch(
			session.backend_snapshot.revision, "m1", "a1", (("charge", 1),),
		)

		assert outcome.status == "accepted" and outcome.commit.snapshot.revision == 1
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_atom_properties_validation_failure_has_a_plain_kind(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An invalid property scalar exposes validation without backend mutation."""
	session = _install_native_session(main_window)
	try:
		before = session.backend_snapshot
		outcome = session.submit_atom_properties_patch(
			before.revision, "m1", "a1", (("charge", "invalid"),),
		)

		assert (
			outcome.status == "rejected" and outcome.failure_kind == "validation"
			and session.backend_snapshot == before
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_atom_dialog_rejects_a_revision_changed_while_modal(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A modal atom intent cannot silently apply to a newer backend snapshot."""
	session = _install_native_session(main_window)
	try:
		atom_item = _atom_item(session)
		atom_item.setSelected(True)
		outcomes = []
		original_submit = session.submit_atom_properties_patch

		def capture_submit(
				expected_revision: int, molecule_id: str, atom_id: str,
				changes: tuple[tuple[str, object], ...],
				) -> object:
			"""Record both modal submissions while retaining the live session path."""
			outcome = original_submit(expected_revision, molecule_id, atom_id, changes)
			outcomes.append(outcome)
			return outcome

		monkeypatch.setattr(session, "submit_atom_properties_patch", capture_submit)
		def accept_after_intervening_commit(_dialog: object) -> int:
			"""Advance the authoritative revision while the dialog is open."""
			outcome = session.submit_atom_properties_patch(
				session.backend_snapshot.revision, "m1", "a1", (("charge", 2),),
			)
			if outcome.status != "accepted":
				raise AssertionError("intervening backend edit was rejected")
			return PySide6.QtWidgets.QDialog.DialogCode.Accepted

		def returned_changes(_dialog: object) -> tuple[tuple[str, object], ...]:
			"""Return the stale atom intent after the intervening commit."""
			return (("charge", 1),)

		monkeypatch.setattr(bkchem_qt.dialogs.atom_dialog.AtomDialog, "exec", accept_after_intervening_commit)
		monkeypatch.setattr(
			bkchem_qt.dialogs.atom_dialog.AtomDialog, "changes",
			returned_changes,
		)
		changed = bkchem_qt.actions.property_editing.edit_atom_properties(
			atom_item.atom_model, session.view, session.document.undo_stack,
		)
		post_intervening_snapshot = outcomes[0].commit.snapshot
		post_intervening_document = session.document
		post_intervening_history = tuple(session._backend_history.entries)
		stale_outcome = outcomes[-1]

		assert (
			not changed and stale_outcome.status == "rejected"
			and stale_outcome.failure_kind == "revision-conflict"
			and session.backend_snapshot == post_intervening_snapshot
			and session.document is post_intervening_document
			and tuple(session._backend_history.entries) == post_intervening_history
			and session.document.dirty and _selected_atom_ids(session) == {"a1"}
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_stale_atom_patch_rejects_before_property_executor(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Session rejects a stale plain atom request before calling OASA's patch executor."""
	session = _install_native_session(main_window)
	try:
		_atom_item(session).setSelected(True)
		stale_revision = session.backend_snapshot.revision
		accepted = session.submit_atom_properties_patch(
			stale_revision, "m1", "a1", (("charge", 2),),
		)
		if accepted.status != "accepted":
			raise AssertionError("intervening backend edit was rejected")
		post_intervening_snapshot = session.backend_snapshot
		post_intervening_document = session.document
		post_intervening_history = tuple(session._backend_history.entries)
		def fail_executor(_request: object) -> object:
			"""Fail if a stale request reaches the backend patch executor."""
			raise AssertionError("stale atom request reached the property executor")

		monkeypatch.setattr(session._backend_session, "patch_atom_properties", fail_executor)
		outcome = session.submit_atom_properties_patch(
			stale_revision, "m1", "a1", (("charge", 1),),
		)

		assert (
			outcome.status == "rejected" and outcome.failure_kind == "revision-conflict"
			and session.backend_snapshot == post_intervening_snapshot
			and session.document is post_intervening_document
			and tuple(session._backend_history.entries) == post_intervening_history
			and session.document.dirty and _selected_atom_ids(session) == {"a1"}
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
@pytest.mark.parametrize("route", ("context", "object-configure", "edit-double-click"))
def test_public_atom_properties_routes_commit_only_their_own_session(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		route: str,
		) -> None:
	"""Every public atom Properties route commits the captured tab once."""
	first = _install_native_session(main_window)
	second = _install_native_session(main_window)
	menu = None
	try:
		atom_item = _atom_item(first)
		atom_item.setSelected(True)
		_accept_changes(monkeypatch, (("charge", 1),))
		if route == "context":
			menu = bkchem_qt.actions.context_menu._atom_context_menu(atom_item, first.view)
			_properties_action(menu).trigger()
		elif route == "object-configure":
			main_window._activate_session(first)
			bkchem_qt.actions.object_actions.handle_configure(main_window)
		else:
			first.mode_manager.set_mode("edit")
			first.mode_manager.current_mode.mouse_double_click(atom_item.scenePos(), None)

		assert (
			'charge="1"' in first.backend_snapshot.cdml
			and 'charge="1"' not in second.backend_snapshot.cdml
			and _selected_atom_ids(first) == {"a1"}
			and first.document.undo_stack.count() == 0
		)
	finally:
		if menu is not None:
			menu.close()
		if second in main_window.sessions:
			main_window._remove_session(second)
		if first in main_window.sessions:
			main_window._remove_session(first)


#============================================
def test_atom_properties_projection_retry_reuses_accepted_snapshot_once(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An accepted atom patch recovers by reprojection without a second commit."""
	session = _install_native_session(main_window)
	menu = None
	try:
		atom_item = _atom_item(session)
		menu = bkchem_qt.actions.context_menu._atom_context_menu(atom_item, session.view)
		_accept_changes(monkeypatch, (("charge", 1),))
		backend_patch = session._backend_session.patch_atom_properties
		install_projection = session._install_prepared_projection
		calls = 0
		fail_once = True

		def count_patch(request: object) -> object:
			"""Count backend acceptance while preserving the production operation."""
			nonlocal calls
			calls += 1
			return backend_patch(request)

		def fail_first_install(
				prepared: object, selected_keys: object, file_path: object,
				projected_snapshot: object,
				) -> None:
			"""Fail only the first accepted-snapshot installation."""
			nonlocal fail_once
			if fail_once:
				fail_once = False
				raise RuntimeError("one-time atom projection failure")
			install_projection(prepared, selected_keys, file_path, projected_snapshot)

		monkeypatch.setattr(session._backend_session, "patch_atom_properties", count_patch)
		monkeypatch.setattr(session, "_install_prepared_projection", fail_first_install)
		_properties_action(menu).trigger()
		accepted = session.backend_snapshot
		retry = session.retry_current_backend_projection()

		assert (
			calls == 1 and retry.status == "accepted"
			and session.backend_snapshot == accepted and _selected_atom_ids(session) == {"a1"}
		)
	finally:
		if menu is not None:
			menu.close()
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_synchronized_idless_atom_properties_are_inert(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""An ID-less synchronized target remains inert instead of using Qt fallback."""
	session = _install_native_session(main_window)
	try:
		atom = _atom_item(session).atom_model
		atom.bind_backend_durable_id(None)
		before = session.backend_snapshot

		def fail_dialog(_dialog: object) -> int:
			"""Expose an accidental fallback that would open a local dialog."""
			raise AssertionError("synchronized ID-less target opened a local dialog")

		monkeypatch.setattr(bkchem_qt.dialogs.atom_dialog.AtomDialog, "exec", fail_dialog)
		changed = bkchem_qt.actions.property_editing.edit_atom_properties(
			atom, session.view, session.document.undo_stack,
		)

		assert not changed and session.backend_snapshot == before
		assert session.document.undo_stack.count() == 0
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_retained_unregistered_view_is_inert_while_another_tab_is_active(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A retained context callback cannot become an isolated local edit."""
	first = _install_native_session(main_window)
	second = _install_native_session(main_window)
	menu = None
	try:
		atom_item = _atom_item(first)
		menu = bkchem_qt.actions.context_menu._atom_context_menu(atom_item, first.view)
		first_before = first.backend_snapshot
		second_before = second.backend_snapshot
		removed = main_window._sessions_by_view.pop(first.view)

		def fail_local_fallback(_atom: object, _parent: object) -> bool:
			"""Expose a stale callback taking the isolated-document route."""
			raise AssertionError("unregistered synchronized view opened local fallback")

		monkeypatch.setattr(
			bkchem_qt.dialogs.atom_dialog.AtomDialog, "edit_atom", fail_local_fallback,
		)
		_properties_action(menu).trigger()

		assert (
			removed is first
			and first.backend_snapshot == first_before
			and second.backend_snapshot == second_before
			and first.document.undo_stack.count() == 0
			and second.document.undo_stack.count() == 0
		)
	finally:
		if first in main_window.sessions and first.view not in main_window._sessions_by_view:
			main_window._sessions_by_view[first.view] = first
		if menu is not None:
			menu.close()
		if second in main_window.sessions:
			main_window._remove_session(second)
		if first in main_window.sessions:
			main_window._remove_session(first)


#============================================
def test_atom_properties_capability_never_redirects_to_another_tab(main_window: object) -> None:
	"""A captured atom capability remains bound to its original session."""
	first = _install_native_session(main_window)
	capability = main_window.atom_properties_capability_for(first)
	first_before = first.backend_snapshot
	second = _install_native_session(main_window)
	second_before = second.backend_snapshot
	try:
		outcome = capability(
			first_before.revision, "m1", "a1", (("charge", 1),),
		)

		assert outcome.status == "accepted" and first.backend_snapshot.revision == first_before.revision + 1
		assert 'charge="1"' in first.backend_snapshot.cdml and second.backend_snapshot == second_before
	finally:
		if second in main_window.sessions:
			main_window._remove_session(second)
		if first in main_window.sessions:
			main_window._remove_session(first)
