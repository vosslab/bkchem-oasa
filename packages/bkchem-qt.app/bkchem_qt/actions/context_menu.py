"""Context menu system for right-click menus."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.bond_presentation
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.scene_queries
import bkchem_qt.actions.property_editing
import bkchem_qt.undo.commands


# -- common element symbols for quick-set submenu --
_COMMON_ELEMENTS = ["C", "N", "O", "S", "P", "F", "Cl", "Br", "I"]

# -- bond order labels --
_BOND_ORDER_LABELS = {
	1: "Single",
	2: "Double",
	3: "Triple",
}
# reverse mapping: label -> order int
_BOND_ORDER_VALUES = {v: k for k, v in _BOND_ORDER_LABELS.items()}

#============================================
def show_context_menu(view: object, scene_pos: object, screen_pos: object) -> None:
	"""Build and show context menu for items at scene_pos.

	Dispatches to atom/bond/molecule-specific menus based on
	what is under the cursor. Falls back to an empty-space menu
	when no interactive item is found.

	Args:
		view: The ChemView widget.
		scene_pos: Position in scene coordinates.
		screen_pos: Position in screen coordinates for menu placement.
	"""
	scene = view.scene()
	if scene is None:
		return
	# find the topmost interactive item at the click position
	items = scene.items(scene_pos)
	target_item = None
	for item in items:
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			target_item = item
			break
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			target_item = item
			break
	# dispatch to the appropriate menu builder
	if isinstance(target_item, bkchem_qt.canvas.items.atom_item.AtomItem):
		menu = _atom_context_menu(target_item, view)
	elif isinstance(target_item, bkchem_qt.canvas.items.bond_item.BondItem):
		menu = _bond_context_menu(target_item, view)
	else:
		menu = _empty_context_menu(view)
	# ``exec()`` owns a nested Qt event loop.  The transient menu and its action
	# tree therefore stay live through the user's choice, then retire through
	# Qt's ordinary deferred-delete delivery rather than remaining view children.
	try:
		menu.exec(screen_pos)
	finally:
		menu.deleteLater()




#============================================
def _atom_context_menu(atom_item: object, view: object) -> PySide6.QtWidgets.QMenu:
	"""Build context menu for an atom item with connected callbacks.

	Args:
		atom_item: The AtomItem that was right-clicked.
		view: The ChemView widget (used as menu parent).

	Returns:
		QMenu populated with atom-specific actions.
	"""
	menu = PySide6.QtWidgets.QMenu(view)
	atom_model = atom_item.atom_model

	# delete action
	delete_action = menu.addAction("Delete")
	delete_action.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Delete)
	delete_action.triggered.connect(
		lambda: _delete_atom(view, atom_item)
	)

	menu.addSeparator()

	# properties action (opens atom dialog)
	props_action = menu.addAction("Properties...")
	props_action.triggered.connect(
		lambda: bkchem_qt.actions.property_editing.edit_atom_properties(
			atom_model, view,
			bkchem_qt.canvas.scene_queries.find_undo_stack(view),
		)
	)

	menu.addSeparator()

	# set element submenu
	element_menu = menu.addMenu("Set Element")
	for symbol in _COMMON_ELEMENTS:
		action = element_menu.addAction(symbol)
		# capture symbol in closure via default arg
		action.triggered.connect(
			lambda checked=False, s=symbol: _set_atom_symbol(view, atom_model, s)
		)

	return menu


#============================================
def _delete_atom(view: object, atom_item: object) -> None:
	"""Delete an atom and its connected bonds with undo support.

	Args:
		view: The ChemView widget.
		atom_item: The AtomItem to delete.
	"""
	scene = view.scene()
	if scene is None:
		return
	undo_stack = bkchem_qt.canvas.scene_queries.find_undo_stack(view)
	atom_model = atom_item.atom_model
	mol_model = bkchem_qt.canvas.scene_queries.find_molecule_for_atom(view, atom_model)
	if mol_model is None or undo_stack is None:
		return
	connected_bonds = bkchem_qt.canvas.scene_queries.find_connected_bond_items(scene, atom_model)
	cmd = bkchem_qt.undo.commands.RemoveAtomCommand(
		scene, mol_model, atom_model, atom_item, connected_bonds,
	)
	undo_stack.push(cmd)


#============================================
def _active_document_session(view: object) -> object | None:
	"""Return the one live active session registered for view."""
	window = view.window()
	session = getattr(window, "_active_session", None)
	if session is None or session.view is not view:
		return None
	if session.is_disposed or session not in window.sessions:
		return None
	return session


#============================================
def _select_fresh_atom(view: object, atom_id: str) -> None:
	"""Restore selection through one accepted projection's durable atom ID."""
	scene = view.scene()
	if scene is None:
		return
	scene.clearSelection()
	bkchem_qt.canvas.document_projection.select_projected_persistent_keys(
		scene, frozenset({("atom", atom_id)}),
	)


#============================================
def _set_atom_symbol(view: object, atom_model: object, symbol: str) -> None:
	"""Submit one backend-authoritative atom element substitution.

	Args:
		view: The ChemView widget.
		atom_model: The currently projected AtomModel identifying the target.
		symbol: New element symbol.
	"""
	if not isinstance(symbol, str) or not symbol:
		return
	session = _active_document_session(view)
	if session is None:
		return
	old_symbol = atom_model.symbol
	if old_symbol == symbol:
		return
	molecule = bkchem_qt.canvas.scene_queries.find_molecule_for_atom(view, atom_model)
	molecule_id = getattr(molecule, "mol_id", None)
	atom_id = atom_model.backend_durable_id
	if not molecule_id or not atom_id:
		return
	# Capture only durable scalar request data before accepting a replacement projection.
	molecule_key = str(molecule_id)
	atom_key = str(atom_id)
	snapshot = session.backend_snapshot
	from bkchem_qt.models import document_session
	request = document_session.build_atom_element_request(
		snapshot.revision, molecule_key, atom_key, symbol,
	)
	outcome = session.submit_persistent_operation(request)
	if outcome.status == "accepted":
		_select_fresh_atom(view, atom_key)
	window = view.window()
	show_outcome = getattr(window, "_show_persistent_action_outcome", None)
	if callable(show_outcome):
		show_outcome(outcome)


#============================================
def _bond_context_menu(bond_item: object, view: object) -> PySide6.QtWidgets.QMenu:
	"""Build context menu for a bond item with connected callbacks.

	Args:
		bond_item: The BondItem that was right-clicked.
		view: The ChemView widget (used as menu parent).

	Returns:
		QMenu populated with bond-specific actions.
	"""
	menu = PySide6.QtWidgets.QMenu(view)
	bond_model = bond_item.bond_model
	molecule = bkchem_qt.canvas.scene_queries.find_molecule_for_bond(view, bond_model)
	molecule_id = getattr(molecule, "mol_id", None)
	bond_id = getattr(bond_model, "backend_durable_id", None)
	molecule_key = str(molecule_id) if isinstance(molecule_id, str) else ""
	bond_key = str(bond_id) if isinstance(bond_id, str) else ""

	# delete action
	delete_action = menu.addAction("Delete")
	delete_action.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Delete)
	delete_action.triggered.connect(
		lambda: _delete_bond(view, bond_item)
	)

	menu.addSeparator()

	# properties action (opens bond dialog)
	props_action = menu.addAction("Properties...")
	props_action.triggered.connect(
		lambda: bkchem_qt.actions.property_editing.edit_bond_properties(
			bond_model, view,
			bkchem_qt.canvas.scene_queries.find_undo_stack(view),
		)
	)

	menu.addSeparator()

	# set order submenu
	order_menu = menu.addMenu("Set Order")
	for order_val, label in _BOND_ORDER_LABELS.items():
		action = order_menu.addAction(label)
		action.triggered.connect(
			lambda checked=False, o=order_val, m=molecule_key, b=bond_key: _set_bond_order(
				view, m, b, o,
			)
		)

	# set type submenu
	type_menu = menu.addMenu("Set Type")
	for type_char, label in bkchem_qt.bond_presentation.ORDINARY_BOND_TYPE_CHOICES:
		action = type_menu.addAction(label)
		action.triggered.connect(
			lambda checked=False, t=type_char, m=molecule_key, b=bond_key: _set_bond_type(
				view, m, b, t,
			)
		)
	# Keep submenu wrappers alive for this QMenu's native ownership lifetime.
	menu._bkchem_submenus = (order_menu, type_menu)

	return menu


#============================================
def _delete_bond(view: object, bond_item: object) -> None:
	"""Delete a bond with undo support.

	Args:
		view: The ChemView widget.
		bond_item: The BondItem to delete.
	"""
	scene = view.scene()
	if scene is None:
		return
	undo_stack = bkchem_qt.canvas.scene_queries.find_undo_stack(view)
	bond_model = bond_item.bond_model
	mol_model = bkchem_qt.canvas.scene_queries.find_molecule_for_bond(view, bond_model)
	if mol_model is None or undo_stack is None:
		return
	cmd = bkchem_qt.undo.commands.RemoveBondCommand(
		scene, mol_model, bond_model, bond_item,
	)
	undo_stack.push(cmd)


#============================================
def _set_bond_order(view: object, molecule_id: str, bond_id: str, order: int) -> None:
	"""Submit one backend-authoritative exact bond-order change.

	Args:
		view: The ChemView widget.
		molecule_id: Durable direct-root molecule identifier.
		bond_id: Durable direct-core bond identifier.
		order: New bond order (1, 2, or 3).
	"""
	if (
		type(order) is not int or order not in _BOND_ORDER_LABELS
		or not isinstance(molecule_id, str) or not molecule_id
		or not isinstance(bond_id, str) or not bond_id
	):
		return
	session = _active_document_session(view)
	if session is None:
		return
	outcome = session.submit_bond_order(molecule_id, bond_id, order)
	window = view.window()
	show_outcome = getattr(window, "_show_persistent_action_outcome", None)
	if callable(show_outcome):
		show_outcome(outcome)


#============================================
def _set_bond_type(
		view: object, molecule_id: str, bond_id: str, bond_type: str,
		) -> None:
	"""Submit one backend-authoritative exact bond-type change.

	Args:
		view: The ChemView widget.
		molecule_id: Durable direct-root molecule identifier.
		bond_id: Durable direct-core bond identifier.
		bond_type: New bond type character.
	"""
	if (
		bond_type not in dict(bkchem_qt.bond_presentation.ORDINARY_BOND_TYPE_CHOICES)
		or not isinstance(molecule_id, str) or not molecule_id
		or not isinstance(bond_id, str) or not bond_id
	):
		return
	session = _active_document_session(view)
	if session is None:
		return
	outcome = session.submit_bond_type(molecule_id, bond_id, bond_type)
	window = view.window()
	show_outcome = getattr(window, "_show_persistent_action_outcome", None)
	if callable(show_outcome):
		show_outcome(outcome)


#============================================
def _empty_context_menu(view: object) -> PySide6.QtWidgets.QMenu:
	"""Build context menu for empty canvas space.

	Args:
		view: The ChemView widget (used as menu parent).

	Returns:
		QMenu populated with general canvas actions.
	"""
	menu = PySide6.QtWidgets.QMenu(view)

	# Paste is available only when both the clipboard and current session qualify.
	paste_action = menu.addAction("Paste")
	paste_action.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Paste)
	# connect to main window's paste handler
	main_window = view.window()
	can_paste = getattr(main_window, "can_paste", None)
	paste_action.setEnabled(bool(can_paste and can_paste()))
	if hasattr(main_window, 'on_paste'):
		paste_action.triggered.connect(main_window.on_paste)

	menu.addSeparator()

	# select all action
	select_all_action = menu.addAction("Select All")
	select_all_action.setShortcut(
		PySide6.QtGui.QKeySequence.StandardKey.SelectAll
	)
	select_all_action.triggered.connect(
		lambda: _select_all(view)
	)

	return menu


#============================================
def _select_all(view: object) -> None:
	"""Select all interactive items in the scene.

	Args:
		view: The ChemView widget.
	"""
	scene = view.scene()
	if scene is None:
		return
	for item in scene.items():
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			item.setSelected(True)
		elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			item.setSelected(True)
