"""Focused durable-ID coverage for the Set Bond Order context-menu route."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.actions.context_menu
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.main_window
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
	"""Register one active projected native-CDML session for a menu interaction."""
	prepared = bkchem_qt.models.document_session.DocumentSession.prepare_native_cdml(_CDML)
	session = main_window._construct_session(prepared_native_cdml=prepared)
	registered = main_window._register_session(session, activate=True)
	if not main_window._replace_session_projection(registered, registered.backend_snapshot):
		raise AssertionError("Native CDML projection is unavailable")
	return registered


#============================================
def _bond_item(session: object) -> object:
	"""Return the one live projected durable bond item."""
	for item in session.scene.items():
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			return item
	raise AssertionError("Projected CDML did not produce a BondItem")


#============================================
def _menu_action(menu: PySide6.QtWidgets.QMenu, text: str) -> PySide6.QtGui.QAction:
	"""Return one user-facing action by text from the specified menu."""
	for action in menu.actions():
		if action.text() == text:
			return action
	raise AssertionError("Context menu action is absent: %s" % text)


#============================================
def _selected_bond_ids(session: object) -> set[str]:
	"""Read durable selected bond IDs after the current canonical projection."""
	return {
		item.bond_model.backend_durable_id
		for item in session.scene.selectedItems()
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)
		and item.bond_model.backend_durable_id is not None
	}


#============================================
def test_retained_set_order_action_uses_durable_ids_after_reprojection(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A retained Double action commits through durable IDs after its item is stale."""
	session = _install_native_session(main_window)
	menu = None
	try:
		menu = bkchem_qt.actions.context_menu._bond_context_menu(_bond_item(session), session.view)
		order_menu = next(
			(child for child in menu.findChildren(PySide6.QtWidgets.QMenu)
			 if child.title() == "Set Order"),
			None,
		)
		if order_menu is None:
			raise AssertionError("Set Order did not create its submenu")
		double_action = _menu_action(order_menu, "Double")
		original_document = session.document
		if not main_window._replace_session_projection(session, session.backend_snapshot):
			raise AssertionError("Canonical reprojection failed before retained action")
		if session.document is original_document:
			raise AssertionError("Canonical reprojection retained the old document wrapper")

		double_action.trigger()

		assert (
			'type="n2"' in session.backend_snapshot.cdml
			and _selected_bond_ids(session) == {"b1"}
			and session.document.undo_stack.count() == 0
		)
	finally:
		if menu is not None:
			menu.close()
		if session in main_window.sessions:
			main_window._remove_session(session)


#============================================
def test_retained_set_type_action_uses_durable_ids_backend_history_and_noop(
		main_window: bkchem_qt.main_window.MainWindow,
		) -> None:
	"""A retained Hashed wedge action remains authoritative after projection replacement."""
	session = _install_native_session(main_window)
	menu = None
	try:
		menu = bkchem_qt.actions.context_menu._bond_context_menu(_bond_item(session), session.view)
		type_menu = next(
			(child for child in menu.findChildren(PySide6.QtWidgets.QMenu)
			 if child.title() == "Set Type"),
			None,
		)
		if type_menu is None:
			raise AssertionError("Set Type did not create its submenu")
		hashed_action = _menu_action(type_menu, "Hashed wedge")
		original_document = session.document
		if not main_window._replace_session_projection(session, session.backend_snapshot):
			raise AssertionError("Canonical reprojection failed before retained action")
		if session.document is original_document:
			raise AssertionError("Canonical reprojection retained the old document wrapper")

		hashed_action.trigger()
		accepted = session.backend_snapshot
		hashed_action.trigger()

		assert (
			'type="h1"' in accepted.cdml
			and session.backend_snapshot == accepted
			and _selected_bond_ids(session) == {"b1"}
			and session.document.undo_stack.count() == 0
			and session._backend_history.can_undo
		)
	finally:
		if menu is not None:
			menu.close()
		if session in main_window.sessions:
			main_window._remove_session(session)
