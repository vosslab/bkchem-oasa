"""Context menu system for right-click menus."""

# PIP3 modules
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.dialogs.atom_dialog
import bkchem_qt.dialogs.bond_dialog
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

# -- bond type labels --
_BOND_TYPE_LABELS = {
	"n": "Normal",
	"w": "Wedge",
	"h": "Hashed",
	"b": "Bold",
	"d": "Dotted",
	"q": "Wavy",
}
# reverse mapping: label -> type char
_BOND_TYPE_VALUES = {v: k for k, v in _BOND_TYPE_LABELS.items()}


#============================================
def show_context_menu(view, scene_pos, screen_pos) -> None:
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
	menu.exec(screen_pos)


#============================================
def _find_undo_stack(view):
	"""Locate the document's QUndoStack through the view.

	Args:
		view: The ChemView widget.

	Returns:
		QUndoStack or None.
	"""
	if hasattr(view, "document") and view.document is not None:
		return view.document.undo_stack
	return None


#============================================
def _find_molecule_for_atom(view, atom_model):
	"""Find the MoleculeModel containing an atom.

	Args:
		view: The ChemView widget.
		atom_model: The AtomModel to search for.

	Returns:
		MoleculeModel or None.
	"""
	if not hasattr(view, "document") or view.document is None:
		return None
	for mol_model in view.document.molecules:
		if atom_model in mol_model.atoms:
			return mol_model
	return None


#============================================
def _find_molecule_for_bond(view, bond_model):
	"""Find the MoleculeModel containing a bond.

	Args:
		view: The ChemView widget.
		bond_model: The BondModel to search for.

	Returns:
		MoleculeModel or None.
	"""
	if not hasattr(view, "document") or view.document is None:
		return None
	for mol_model in view.document.molecules:
		if bond_model in mol_model.bonds:
			return mol_model
	return None


#============================================
def _find_connected_bond_items(scene, atom_model):
	"""Find all BondItems connected to an atom.

	Args:
		scene: The QGraphicsScene.
		atom_model: The AtomModel whose bonds to find.

	Returns:
		List of (BondModel, BondItem) tuples.
	"""
	connected = []
	for item in scene.items():
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			bm = item.bond_model
			if bm.atom1 is atom_model or bm.atom2 is atom_model:
				connected.append((bm, item))
	return connected


#============================================
def _atom_context_menu(atom_item, view) -> PySide6.QtWidgets.QMenu:
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
		lambda: bkchem_qt.dialogs.atom_dialog.AtomDialog.edit_atom(
			atom_model, view,
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
def _delete_atom(view, atom_item) -> None:
	"""Delete an atom and its connected bonds with undo support.

	Args:
		view: The ChemView widget.
		atom_item: The AtomItem to delete.
	"""
	scene = view.scene()
	if scene is None:
		return
	undo_stack = _find_undo_stack(view)
	atom_model = atom_item.atom_model
	mol_model = _find_molecule_for_atom(view, atom_model)
	if mol_model is None or undo_stack is None:
		return
	connected_bonds = _find_connected_bond_items(scene, atom_model)
	cmd = bkchem_qt.undo.commands.RemoveAtomCommand(
		scene, mol_model, atom_model, atom_item, connected_bonds,
	)
	undo_stack.push(cmd)


#============================================
def _set_atom_symbol(view, atom_model, symbol: str) -> None:
	"""Change an atom's element symbol with undo support.

	Args:
		view: The ChemView widget.
		atom_model: The AtomModel to change.
		symbol: New element symbol.
	"""
	undo_stack = _find_undo_stack(view)
	if undo_stack is None:
		atom_model.symbol = symbol
		return
	old_symbol = atom_model.symbol
	if old_symbol == symbol:
		return
	cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
		atom_model, "symbol", old_symbol, symbol,
		text=f"Set element to {symbol}",
	)
	undo_stack.push(cmd)


#============================================
def _bond_context_menu(bond_item, view) -> PySide6.QtWidgets.QMenu:
	"""Build context menu for a bond item with connected callbacks.

	Args:
		bond_item: The BondItem that was right-clicked.
		view: The ChemView widget (used as menu parent).

	Returns:
		QMenu populated with bond-specific actions.
	"""
	menu = PySide6.QtWidgets.QMenu(view)
	bond_model = bond_item.bond_model

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
		lambda: bkchem_qt.dialogs.bond_dialog.BondDialog.edit_bond(
			bond_model, view,
		)
	)

	menu.addSeparator()

	# set order submenu
	order_menu = menu.addMenu("Set Order")
	for order_val, label in _BOND_ORDER_LABELS.items():
		action = order_menu.addAction(label)
		action.triggered.connect(
			lambda checked=False, o=order_val: _set_bond_order(view, bond_model, o)
		)

	# set type submenu
	type_menu = menu.addMenu("Set Type")
	for type_char, label in _BOND_TYPE_LABELS.items():
		action = type_menu.addAction(label)
		action.triggered.connect(
			lambda checked=False, t=type_char: _set_bond_type(view, bond_model, t)
		)

	return menu


#============================================
def _delete_bond(view, bond_item) -> None:
	"""Delete a bond with undo support.

	Args:
		view: The ChemView widget.
		bond_item: The BondItem to delete.
	"""
	scene = view.scene()
	if scene is None:
		return
	undo_stack = _find_undo_stack(view)
	bond_model = bond_item.bond_model
	mol_model = _find_molecule_for_bond(view, bond_model)
	if mol_model is None or undo_stack is None:
		return
	cmd = bkchem_qt.undo.commands.RemoveBondCommand(
		scene, mol_model, bond_model, bond_item,
	)
	undo_stack.push(cmd)


#============================================
def _set_bond_order(view, bond_model, order: int) -> None:
	"""Change a bond's order with undo support.

	Args:
		view: The ChemView widget.
		bond_model: The BondModel to change.
		order: New bond order (1, 2, or 3).
	"""
	undo_stack = _find_undo_stack(view)
	old_order = bond_model.order
	if old_order == order:
		return
	if undo_stack is None:
		bond_model.order = order
		return
	cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
		bond_model, "order", old_order, order,
		text=f"Set bond order to {order}",
	)
	undo_stack.push(cmd)


#============================================
def _set_bond_type(view, bond_model, bond_type: str) -> None:
	"""Change a bond's type with undo support.

	Args:
		view: The ChemView widget.
		bond_model: The BondModel to change.
		bond_type: New bond type character.
	"""
	undo_stack = _find_undo_stack(view)
	old_type = bond_model.type
	if old_type == bond_type:
		return
	if undo_stack is None:
		bond_model.type = bond_type
		return
	cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
		bond_model, "type", old_type, bond_type,
		text=f"Set bond type to {bond_type}",
	)
	undo_stack.push(cmd)


#============================================
def _empty_context_menu(view) -> PySide6.QtWidgets.QMenu:
	"""Build context menu for empty canvas space.

	Args:
		view: The ChemView widget (used as menu parent).

	Returns:
		QMenu populated with general canvas actions.
	"""
	menu = PySide6.QtWidgets.QMenu(view)

	# paste action (stub)
	paste_action = menu.addAction("Paste")
	paste_action.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Paste)
	paste_action.setEnabled(False)

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
def _select_all(view) -> None:
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
