"""Object-menu Configure dialog persistence tests."""

# local repo modules
import bkchem_qt.actions.object_actions
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.dialogs.atom_dialog
import bkchem_qt.dialogs.bond_dialog
import bkchem_qt.models.document_session


_CDML = (
	'<cdml version="26.07"><molecule id="m1">'
	'<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>'
	'<atom id="a2" name="O"><point x="3cm" y="1cm"/></atom>'
	'<bond id="b1" start="a1" end="a2" type="n1"/>'
	'</molecule></cdml>'
)


#============================================
def _draw_atom(main_window: object, x: float, y: float) -> object:
	"""Create one selected-ready atom through the ordinary draw mode."""
	main_window._mode_manager.set_mode("draw")
	draw_mode = main_window._mode_manager.current_mode
	item = draw_mode._create_atom_at(x, y, "C")
	return item


#============================================
def _install_native_session(main_window: object) -> object:
	"""Register one active native CDML session for Object Configure."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native CDML projection is unavailable")
	return registered


#============================================
def _projected_item(session: object, item_type: type) -> object:
	"""Return one direct-core projected item of the requested Qt type."""
	for item in session.scene.items():
		if isinstance(item, item_type):
			return item
	raise AssertionError("Native projection omitted the requested item")


#============================================
def test_configure_atom_is_one_backend_history_dirty_edit(
		main_window: object, monkeypatch: object,
		) -> None:
	"""Object Configure commits atom intent through backend history, not Qt undo."""
	session = _install_native_session(main_window)
	atom_item = _projected_item(session, bkchem_qt.canvas.items.atom_item.AtomItem)
	atom_item.setSelected(True)
	atom_id = atom_item.atom_model.backend_durable_id
	before = session.backend_snapshot

	def accept_atom(_dialog: object) -> int:
		"""Accept the detached dialog without mutating the projection."""
		return 1

	def atom_changes(_dialog: object) -> tuple[tuple[str, object], ...]:
		"""Return the explicit backend-owned atom property intent."""
		return (("element", "N"), ("font_size", 18))

	monkeypatch.setattr(
		bkchem_qt.dialogs.atom_dialog.AtomDialog, "exec", accept_atom,
	)
	monkeypatch.setattr(bkchem_qt.dialogs.atom_dialog.AtomDialog, "changes", atom_changes)
	bkchem_qt.actions.object_actions.handle_configure(main_window)

	assert (
		session.backend_snapshot.revision == before.revision + 1
		and 'id="%s"' % atom_id in session.backend_snapshot.cdml
		and 'name="N"' in session.backend_snapshot.cdml
		and session.can_undo_backend and session.document.dirty
		and session.document.undo_stack.count() == 0
	)


#============================================
def test_configure_bond_is_one_backend_history_dirty_edit(
		main_window: object, monkeypatch: object,
		) -> None:
	"""Object Configure commits bond intent through backend history, not Qt undo."""
	session = _install_native_session(main_window)
	bond_item = _projected_item(session, bkchem_qt.canvas.items.bond_item.BondItem)
	bond_item.setSelected(True)
	bond_id = bond_item.bond_model.backend_durable_id
	before = session.backend_snapshot

	def accept_bond(_dialog: object) -> int:
		"""Accept the detached dialog without mutating the projection."""
		return 1

	def bond_changes(_dialog: object) -> tuple[tuple[str, object], ...]:
		"""Return the explicit backend-owned bond property intent."""
		return (("line_width", 4.0),)

	monkeypatch.setattr(
		bkchem_qt.dialogs.bond_dialog.BondDialog, "exec", accept_bond,
	)
	monkeypatch.setattr(bkchem_qt.dialogs.bond_dialog.BondDialog, "changes", bond_changes)
	bkchem_qt.actions.object_actions.handle_configure(main_window)

	assert (
		session.backend_snapshot.revision == before.revision + 1
		and 'id="%s"' % bond_id in session.backend_snapshot.cdml
		and 'line_width="4"' in session.backend_snapshot.cdml
		and session.can_undo_backend and session.document.dirty
		and session.document.undo_stack.count() == 0
	)


#============================================
def test_configure_cancel_and_noop_leave_clean_document(
		main_window: object, monkeypatch: object,
		) -> None:
	"""Cancelled or unchanged dialogs do not create a dirty undo entry."""
	atom_item = _draw_atom(main_window, 20.0, 20.0)
	atom_item.setSelected(True)
	main_window.document.mark_clean()

	def accept_without_change(_dialog: object) -> int:
		"""Simulate accepting a dialog without changing a value."""
		return 1

	def cancel_atom(_dialog: object) -> int:
		"""Simulate closing a dialog through Cancel."""
		return 0

	def no_changes(_dialog: object) -> tuple[tuple[str, object], ...]:
		"""Return the explicit no-op intent from an accepted detached dialog."""
		return ()

	monkeypatch.setattr(
		bkchem_qt.dialogs.atom_dialog.AtomDialog, "exec",
		accept_without_change,
	)
	monkeypatch.setattr(bkchem_qt.dialogs.atom_dialog.AtomDialog, "changes", no_changes)
	bkchem_qt.actions.object_actions.handle_configure(main_window)
	monkeypatch.setattr(
		bkchem_qt.dialogs.atom_dialog.AtomDialog, "exec", cancel_atom,
	)
	bkchem_qt.actions.object_actions.handle_configure(main_window)
	assert not main_window.document.dirty


#============================================
def test_configure_idless_synchronized_atom_is_inert(
		main_window: object, monkeypatch: object,
		) -> None:
	"""Object Configure keeps an unaddressable synchronized atom unchanged."""
	session = _install_native_session(main_window)
	try:
		atom_item = _projected_item(session, bkchem_qt.canvas.items.atom_item.AtomItem)
		atom_item.setSelected(True)
		atom_model = atom_item.atom_model
		atom_model.bind_backend_durable_id(None)
		before = session.backend_snapshot
		before_symbol = atom_model.symbol

		def fail_fallback(_atom: object, _parent: object) -> bool:
			"""Expose a forbidden local fallback from the synchronized window route."""
			raise AssertionError("Object Configure opened the atom local fallback")

		monkeypatch.setattr(bkchem_qt.dialogs.atom_dialog.AtomDialog, "edit_atom", fail_fallback)
		bkchem_qt.actions.object_actions.handle_configure(main_window)

		assert (
			session.backend_snapshot == before and atom_model.symbol == before_symbol
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_configure_idless_synchronized_bond_is_inert(
		main_window: object, monkeypatch: object,
		) -> None:
	"""Object Configure keeps an unaddressable synchronized bond unchanged."""
	session = _install_native_session(main_window)
	try:
		bond_item = _projected_item(session, bkchem_qt.canvas.items.bond_item.BondItem)
		bond_item.setSelected(True)
		bond_model = bond_item.bond_model
		bond_model.bind_backend_durable_id(None)
		before = session.backend_snapshot
		before_order = bond_model.order

		def fail_fallback(_bond: object, _parent: object) -> bool:
			"""Expose a forbidden local fallback from the synchronized window route."""
			raise AssertionError("Object Configure opened the bond local fallback")

		monkeypatch.setattr(bkchem_qt.dialogs.bond_dialog.BondDialog, "edit_bond", fail_fallback)
		bkchem_qt.actions.object_actions.handle_configure(main_window)

		assert (
			session.backend_snapshot == before and bond_model.order == before_order
			and session.document.undo_stack.count() == 0
		)
	finally:
		if session in main_window.sessions:
			main_window._remove_session(session)
