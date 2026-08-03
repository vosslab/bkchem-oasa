"""Focused acceptance coverage for authoritative Bond Properties."""

# PIP3 modules
import PySide6.QtWidgets
import pytest

# local repo modules
import bkchem_qt.actions.context_menu
import bkchem_qt.actions.object_actions
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.dialogs.bond_dialog
import bkchem_qt.main_window
import bkchem_qt.models.bond_model
import bkchem_qt.models.document_session


_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O"><point x="3cm" y="1cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'</molecule></cdml>'
)


#============================================
def _install_native_session(main_window: bkchem_qt.main_window.MainWindow) -> object:
	"""Register one projected native-CDML session for a Properties action."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	projection = registered.retry_current_backend_projection()
	if projection.status != "accepted":
		raise AssertionError("Native CDML projection is unavailable")
	return registered


#============================================
def _bond_item(session: object) -> object:
	"""Return the projected direct-core bond item."""
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			return item
	raise AssertionError("Projected CDML did not produce a BondItem")


#============================================
def _properties_action(menu: PySide6.QtWidgets.QMenu) -> object:
	"""Return the public Properties action from one bond context menu."""
	for action in menu.actions():
		if action.text() == "Properties...":
			return action
	raise AssertionError("Bond Properties action is absent")


#============================================
def _selected_bond_ids(session: object) -> set[str]:
	"""Read direct-core durable bond IDs from the current selection."""
	return {
		item.bond_model.backend_durable_id
		for item in session.scene.selectedItems()
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
		and item.bond_model.backend_durable_id is not None
	}


#============================================
def _select_bond(session: object) -> object:
	"""Select and return this session's projected durable bond."""
	bond_item = _bond_item(session)
	bond_item.setSelected(True)
	return bond_item


#============================================
def _accept_changes(monkeypatch: pytest.MonkeyPatch, changes: tuple[tuple[str, object], ...]) -> None:
	"""Make the detached dialog accept precisely one explicit plain intent."""
	def accept(_dialog: object) -> int:
		"""Return the ordinary accepted dialog code without touching its model."""
		return PySide6.QtWidgets.QDialog.DialogCode.Accepted

	def returned_changes(_dialog: object) -> tuple[tuple[str, object], ...]:
		"""Return the caller-owned immutable intent."""
		return changes

	monkeypatch.setattr(bkchem_qt.dialogs.bond_dialog.BondDialog, "exec", accept)
	monkeypatch.setattr(bkchem_qt.dialogs.bond_dialog.BondDialog, "changes", returned_changes)


#============================================
def test_bond_dialog_is_detached_and_absent_center_is_inert(qapp: object) -> None:
	"""Opening, cancelling, or accepting no changes never touches the model."""
	model = bkchem_qt.models.bond_model.BondModel()
	model.center = None
	dialog = bkchem_qt.dialogs.bond_dialog.BondDialog(model)

	assert not hasattr(dialog, "_bond_model") and not dialog._center_check.isChecked()
	assert dialog.changes() == () and model.center is None


#============================================
def test_context_properties_commits_once_and_restores_fresh_selection(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Public Properties creates one backend revision and selects its fresh bond."""
	session = _install_native_session(main_window)
	menu = None
	try:
		menu = bkchem_qt.actions.context_menu._bond_context_menu(_bond_item(session), session.view)
		_accept_changes(monkeypatch, (("type", "h"), ("color", "#112233")))
		old_document = session.document
		_properties_action(menu).trigger()

		assert (
			'type="h1"' in session.backend_snapshot.cdml
			and 'color="#112233"' in session.backend_snapshot.cdml
			and session.document is not old_document
			and _selected_bond_ids(session) == {"b1"}
			and session.document.undo_stack.count() == 0
		)
	finally:
		if menu is not None:
			menu.close()
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_bond_dialog_rejects_a_revision_changed_while_modal(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A modal bond intent cannot apply after a newer backend commit."""
	session = _install_native_session(main_window)
	try:
		bond_item = _select_bond(session)
		outcomes = []
		original_submit = session.submit_bond_properties_patch

		def capture_submit(
				expected_revision: int, molecule_id: str, bond_id: str,
				changes: tuple[tuple[str, object], ...],
				) -> object:
			"""Record both modal submissions while retaining the live session path."""
			outcome = original_submit(expected_revision, molecule_id, bond_id, changes)
			outcomes.append(outcome)
			return outcome

		monkeypatch.setattr(session, "submit_bond_properties_patch", capture_submit)
		def accept_after_intervening_commit(_dialog: object) -> int:
			"""Advance the authoritative revision while the dialog is active."""
			outcome = session.submit_bond_properties_patch(
				session.backend_snapshot.revision, "m1", "b1", (("order", 2),),
			)
			if outcome.status != "accepted":
				raise AssertionError("intervening backend edit was rejected")
			return PySide6.QtWidgets.QDialog.DialogCode.Accepted

		def returned_changes(_dialog: object) -> tuple[tuple[str, object], ...]:
			"""Return the stale bond intent after the intervening commit."""
			return (("order", 3),)

		monkeypatch.setattr(bkchem_qt.dialogs.bond_dialog.BondDialog, "exec", accept_after_intervening_commit)
		monkeypatch.setattr(bkchem_qt.dialogs.bond_dialog.BondDialog, "changes", returned_changes)
		changed = bkchem_qt.actions.property_editing.edit_bond_properties(
			bond_item.bond_model, session.view, session.document.undo_stack,
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
			and session.document.dirty and _selected_bond_ids(session) == {"b1"}
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_stale_bond_patch_rejects_before_property_executor(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""Session rejects a stale plain bond request before calling OASA's patch executor."""
	session = _install_native_session(main_window)
	try:
		_select_bond(session)
		stale_revision = session.backend_snapshot.revision
		accepted = session.submit_bond_properties_patch(
			stale_revision, "m1", "b1", (("order", 2),),
		)
		if accepted.status != "accepted":
			raise AssertionError("intervening backend edit was rejected")
		post_intervening_snapshot = session.backend_snapshot
		post_intervening_document = session.document
		post_intervening_history = tuple(session._backend_history.entries)
		def fail_executor(_request: object) -> object:
			"""Fail if a stale request reaches the backend patch executor."""
			raise AssertionError("stale bond request reached the property executor")

		monkeypatch.setattr(session._backend_session, "patch_bond_properties", fail_executor)
		outcome = session.submit_bond_properties_patch(
			stale_revision, "m1", "b1", (("order", 3),),
		)

		assert (
			outcome.status == "rejected" and outcome.failure_kind == "revision-conflict"
			and session.backend_snapshot == post_intervening_snapshot
			and session.document is post_intervening_document
			and tuple(session._backend_history.entries) == post_intervening_history
			and session.document.dirty and _selected_bond_ids(session) == {"b1"}
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_invalid_bond_patch_preserves_the_installed_qt_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""An invalid bond intent leaves the complete projected session untouched."""
	session = _install_native_session(main_window)
	try:
		_select_bond(session)
		before_snapshot = session.backend_snapshot
		before_document = session.document
		before_history = tuple(session._backend_history.entries)
		outcome = session.submit_bond_properties_patch(
			before_snapshot.revision, "m1", "b1", (("color", "invalid"),),
		)

		assert (
			outcome.status == "rejected" and outcome.failure_kind == "validation"
			and session.backend_snapshot == before_snapshot
			and session.backend_snapshot.revision == before_snapshot.revision
			and tuple(session._backend_history.entries) == before_history
			and session.document is before_document and not session.document.dirty
			and _selected_bond_ids(session) == {"b1"}
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
@pytest.mark.parametrize("route", ("Object > Configure", "EditMode Properties"))
def test_bond_property_dialog_routes_commit_authoritative_projection(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		route: str,
		) -> None:
	"""Object Configure and EditMode share the synchronized bond patch route."""
	session = _install_native_session(main_window)
	try:
		bond_item = _select_bond(session)
		_accept_changes(monkeypatch, (("color", "#112233"),))
		old_document = session.document
		if route == "Object > Configure":
			bkchem_qt.actions.object_actions.handle_configure(main_window)
		else:
			session.mode_manager.set_mode("edit")
			session.mode_manager.current_mode._edit_bond_properties(bond_item)

		assert (
			'color="#112233"' in session.backend_snapshot.cdml
			and session.document is not old_document
			and _selected_bond_ids(session) == {"b1"}
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_properties_projection_retry_never_resubmits_and_restores_selection(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A post-acceptance failure retries only the committed snapshot and selection."""
	session = _install_native_session(main_window)
	menu = None
	try:
		menu = bkchem_qt.actions.context_menu._bond_context_menu(_bond_item(session), session.view)
		_accept_changes(monkeypatch, (("order", 2),))
		install_projection = session._install_prepared_projection
		backend_patch = session._backend_session.patch_bond_properties
		calls = 0
		failure_pending = True

		def count_backend_patch(request: object) -> object:
			"""Count the only backend mutation made by the public action."""
			nonlocal calls
			calls += 1
			return backend_patch(request)

		def fail_first_install(
				prepared: object, selected_keys: object, file_path: object,
				projected_snapshot: object,
				) -> None:
			"""Reject only the initial accepted-snapshot projection installation."""
			nonlocal failure_pending
			if failure_pending:
				failure_pending = False
				raise RuntimeError("one-time projection installation failure")
			install_projection(prepared, selected_keys, file_path, projected_snapshot)

		monkeypatch.setattr(session._backend_session, "patch_bond_properties", count_backend_patch)
		monkeypatch.setattr(session, "_install_prepared_projection", fail_first_install)
		_properties_action(menu).trigger()
		accepted = session.backend_snapshot
		retry = session.retry_current_backend_projection()

		assert (
			calls == 1
			and retry.status == "accepted"
			and session.backend_snapshot == accepted
			and _selected_bond_ids(session) == {"b1"}
		)
	finally:
		if menu is not None:
			menu.close()
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_property_dock_rebind_keeps_its_prior_tab_capability(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A dock callback captured before a tab switch cannot redirect to the new tab."""
	first = _install_native_session(main_window)
	second = None
	try:
		first_capture = main_window._property_dock._bond_properties_capture
		second = _install_native_session(main_window)
		second_capture = main_window._property_dock._bond_properties_capture
		expected_revision, first_capability = first_capture("m1", "b1")
		outcome = first_capability(expected_revision, "m1", "b1", (("order", 2),))

		assert (
			outcome.status == "accepted"
			and first_capture is not second_capture
			and 'type="n2"' in first.backend_snapshot.cdml
			and 'type="n1"' in second.backend_snapshot.cdml
		)
	finally:
		if second is not None and second in main_window.sessions:
			main_window._remove_session(second)
		if first in main_window.sessions:
			main_window._remove_session(first)


#============================================
def test_property_dock_canonical_bond_noop_retains_its_originating_session(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A dock-provided same-value intent consumes no history in its original tab."""
	first = _install_native_session(main_window)
	second = None
	try:
		_select_bond(first)
		main_window._property_dock.update_from_selection()
		first_capture = main_window._property_dock._bond_properties_capture
		before_snapshot = first.backend_snapshot
		before_document = first.document
		before_history = tuple(first._backend_history.entries)
		second = _install_native_session(main_window)
		expected_revision, submit = first_capture("m1", "b1")
		outcome = submit(expected_revision, "m1", "b1", (("order", 1),))

		assert (
			outcome.status == "accepted" and outcome.commit is None
			and first.backend_snapshot == before_snapshot
			and first.backend_snapshot.revision == before_snapshot.revision
			and tuple(first._backend_history.entries) == before_history
			and first.document is before_document and not first.document.dirty
			and _selected_bond_ids(first) == {"b1"}
			and first.document.undo_stack.count() == 0
			and second.backend_snapshot.revision == 0
		)
	finally:
		if second is not None and second in main_window.sessions:
			main_window._remove_session(second)
		if first in main_window.sessions:
			main_window._remove_session(first)


#============================================
def test_property_dock_combo_commits_its_synchronized_tab_only(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A dock control commits its bound tab before a later tab becomes active."""
	first = _install_native_session(main_window)
	second = None
	try:
		_select_bond(first)
		main_window._property_dock.update_from_selection()
		second = _install_native_session(main_window)
		main_window._activate_session(first)
		_select_bond(first)
		main_window._property_dock.update_from_selection()
		combo = main_window._property_dock._bond_order_combo
		combo.setCurrentIndex(combo.findData(2))
		main_window._activate_session(second)

		assert (
			'type="n2"' in first.backend_snapshot.cdml
			and first.document.undo_stack.count() == 0
			and 'type="n1"' in second.backend_snapshot.cdml
			and main_window._active_session is second
		)
	finally:
		if second is not None and second in main_window.sessions:
			main_window._remove_session(second)
		if first in main_window.sessions:
			main_window._remove_session(first)


#============================================
def test_property_dock_bond_stale_event_refreshes_without_local_undo(
		main_window: bkchem_qt.main_window.MainWindow, monkeypatch: pytest.MonkeyPatch,
		) -> None:
	"""A stale dock event keeps the intervening bond snapshot authoritative."""
	session = _install_native_session(main_window)
	try:
		_select_bond(session)
		main_window._property_dock.update_from_selection()
		original_capture = main_window._property_dock._bond_properties_capture
		observed = {}

		def stale_capture(molecule_id: str, bond_id: str) -> tuple[int, object] | None:
			"""Advance authority after capture and return one stale revision callback."""
			captured = original_capture(molecule_id, bond_id)
			if captured is None:
				return None
			accepted = session.submit_bond_properties_patch(
				session.backend_snapshot.revision, molecule_id, bond_id, (("order", 3),),
			)
			if accepted.status != "accepted":
				raise AssertionError("intervening backend edit was rejected")
			observed["snapshot"] = session.backend_snapshot
			observed["document"] = session.document
			observed["history"] = tuple(session._backend_history.entries)

			def reject_stale(
					expected_revision: int, captured_molecule_id: str,
					captured_bond_id: str, changes: tuple[tuple[str, object], ...],
					) -> object:
				"""Record the stale result without letting it reach OASA's executor."""
				outcome = captured[1](
					expected_revision, captured_molecule_id, captured_bond_id, changes,
				)
				observed["outcome"] = outcome
				return outcome

			def fail_executor(_request: object) -> object:
				"""Fail if the stale dock event reaches the bond patch executor."""
				raise AssertionError("stale dock event reached the property executor")

			monkeypatch.setattr(session._backend_session, "patch_bond_properties", fail_executor)
			return captured[0], reject_stale

		main_window._property_dock._bond_properties_capture = stale_capture
		combo = main_window._property_dock._bond_order_combo
		combo.setCurrentIndex(combo.findData(2))
		outcome = observed["outcome"]

		assert (
			outcome.status == "rejected" and outcome.failure_kind == "revision-conflict"
			and session.backend_snapshot == observed["snapshot"]
			and session.document is observed["document"]
			and tuple(session._backend_history.entries) == observed["history"]
			and session.document.dirty and session.document.undo_stack.count() == 0
			and main_window._property_dock._bond_order_combo.currentData() == 3
			and _selected_bond_ids(session) == {"b1"}
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_active_session_recovery_rebinds_bond_properties_capability(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""Activation recovery restores the dock with its exact session capability."""
	first = _install_native_session(main_window)
	second = None
	try:
		second = _install_native_session(main_window)
		main_window._restore_active_session(
			first, main_window._tab_widget.indexOf(first.view),
		)
		expected_revision, submit = main_window._property_dock._bond_properties_capture(
			"m1", "b1",
		)
		outcome = submit(expected_revision, "m1", "b1", (("order", 2),))

		assert (
			outcome.status == "accepted"
			and 'type="n2"' in first.backend_snapshot.cdml
			and 'type="n1"' in second.backend_snapshot.cdml
		)
	finally:
		if second is not None and second in main_window.sessions:
			main_window._remove_session(second)
		if first in main_window.sessions:
			main_window._remove_session(first)
