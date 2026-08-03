"""Context menu system for right-click menus."""

# PIP3 modules
import weakref

import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets
import shiboken6

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
	# A synchronized Delete action captures only its originating session and
	# immutable durable request.  Release the scene-query wrappers before the
	# nested event loop can trigger an accepted projection replacement.
	items.clear()
	del items
	try:
		del item
	except UnboundLocalError:
		pass
	target_item = None
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
	molecule = bkchem_qt.canvas.scene_queries.find_molecule_for_atom(view, atom_model)
	molecule_id = getattr(molecule, "mol_id", None)
	atom_id = getattr(atom_model, "backend_durable_id", None)
	molecule_key = str(molecule_id) if isinstance(molecule_id, str) else ""
	atom_key = str(atom_id) if isinstance(atom_id, str) else ""
	action_route = _context_menu_action_route(view)
	model_ref = weakref.ref(atom_model)

	# delete action
	delete_action = menu.addAction("Delete")
	delete_action.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Delete)
	delete_action.triggered.connect(_structure_delete_callback(view, atom_item))

	menu.addSeparator()

	# properties action (opens atom dialog)
	props_action = menu.addAction("Properties...")
	props_action.triggered.connect(_atom_properties_callback(
		view, action_route, molecule_key, atom_key, model_ref,
	))

	menu.addSeparator()

	# set element submenu
	element_menu = menu.addMenu("Set Element")
	for symbol in _COMMON_ELEMENTS:
		action = element_menu.addAction(symbol)
		action.triggered.connect(_atom_symbol_callback(
			view, action_route, molecule_key, atom_key, model_ref, symbol,
		))

	return menu


#============================================
def _delete_atom(view: object, atom_item: object) -> None:
	"""Delete an atom and its connected bonds with undo support.

	Args:
		view: The ChemView widget.
		atom_item: The AtomItem to delete.
	"""
	callback = _structure_delete_callback(view, atom_item)
	del atom_item
	callback()


#============================================
def _delete_atom_local(view: object, atom_item: object) -> None:
	"""Delete one atom through the explicitly local undo route."""
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
def _show_structure_delete_outcome(view: object, outcome: object) -> None:
	"""Publish one structure-delete outcome through the owning window."""
	window = view.window()
	show_outcome = getattr(window, "_show_persistent_action_outcome", None)
	if callable(show_outcome):
		show_outcome(outcome)


#============================================
def _structure_delete_callback(view: object, item: object) -> object:
	"""Freeze one context-menu Delete route without retaining synchronized wrappers."""
	session = _origin_document_session(view)
	if session is None:
		return _local_structure_delete_callback(view, weakref.ref(item))
	if _active_document_session(view) is not session:
		from bkchem_qt.models import document_session
		outcome = document_session.PersistentActionOutcome(
			"unavailable", "Delete unavailable for this document", None,
		)
		return lambda: _show_structure_delete_outcome(view, outcome)
	context = session.structure_delete_context()
	if (
		type(context) is not tuple
		or len(context) != 2
		or context[0] not in ("backend", "local", "unavailable")
	):
		raise ValueError("Structure Delete context returned an unknown state")
	authority, expected_revision = context
	if authority == "local":
		return _local_structure_delete_callback(view, weakref.ref(item))
	if authority == "unavailable":
		if expected_revision is not None:
			raise ValueError("Unavailable Structure Delete must not capture a revision")
		from bkchem_qt.models import document_session
		outcome = document_session.PersistentActionOutcome(
			"unavailable", "Delete unavailable for this document", None,
		)
		return lambda: _show_structure_delete_outcome(view, outcome)
	targets = bkchem_qt.canvas.document_projection.structure_delete_targets_for_items(
		session.document, (item,),
	)
	if targets is None or type(expected_revision) is not int:
		from bkchem_qt.models import document_session
		outcome = document_session.PersistentActionOutcome(
			"unavailable",
			"Delete unavailable: select a durable atom or bond from one molecule",
			None,
		)
		return lambda: _show_structure_delete_outcome(view, outcome)
	molecule_id, atom_ids, bond_ids = targets
	from bkchem_qt.models import document_session
	request = document_session.build_structure_delete_request(
		expected_revision, molecule_id, atom_ids, bond_ids,
	)

	def submit() -> None:
		"""Submit only to the still-active originating session."""
		if _active_document_session(view) is not session:
			return
		outcome = session.submit_persistent_operation(request)
		_show_structure_delete_outcome(view, outcome)

	return submit


#============================================
def _local_structure_delete_callback(
		view: object, item_ref: weakref.ReferenceType,
		) -> object:
	"""Build one local Delete callback that resolves its item at trigger time."""
	def invoke() -> None:
		"""Delete one still-current local wrapper through its existing undo route."""
		item = item_ref()
		if not _is_current_local_structure_item(view, item):
			return
		_delete_structure_item_local(view, item)
	return invoke


#============================================
def _is_current_local_structure_item(view: object, item: object) -> bool:
	"""Validate one local Delete target immediately before native access."""
	if not (
		isinstance(view, PySide6.QtWidgets.QGraphicsView)
		and shiboken6.isValid(view)
		and isinstance(item, PySide6.QtWidgets.QGraphicsItem)
		and shiboken6.isValid(item)
	):
		return False
	scene = view.scene()
	if scene is None or not shiboken6.isValid(scene):
		return False
	try:
		if item.scene() is not scene:
			return False
	except RuntimeError:
		return False
	session = _origin_document_session(view)
	if session is None:
		return True
	if _active_document_session(view) is not session:
		return False
	document = getattr(session, "document", None)
	is_current = getattr(document, "is_current_projection_item", None)
	if callable(is_current) and bool(is_current(item)):
		return True
	if not getattr(session, "legacy_isolated", False):
		return False
	molecule_for_item = getattr(document, "molecule_for_graphics_item", None)
	return callable(molecule_for_item) and molecule_for_item(item) is not None


#============================================
def _delete_structure_item_local(view: object, item: object) -> None:
	"""Dispatch one explicitly local atom or bond deletion."""
	if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
		_delete_atom_local(view, item)
	elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
		_delete_bond_local(view, item)


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
def _context_menu_action_route(view: object) -> tuple[str, object | None]:
	"""Classify one menu origin without retaining its disposable projection."""
	session = _origin_document_session(view)
	if session is None:
		return "local", None
	if _active_document_session(view) is not session:
		return "inactive", session
	if getattr(session, "legacy_isolated", False):
		return "local", session
	return "synchronized", session


#============================================
def _is_valid_qobject(value: object) -> bool:
	"""Return whether one Qt model wrapper can safely receive attribute access."""
	return isinstance(value, PySide6.QtCore.QObject) and shiboken6.isValid(value)


#============================================
def _find_current_atom(document: object, molecule_id: str, atom_id: str) -> object | None:
	"""Resolve one durable atom from the current document projection."""
	if not isinstance(molecule_id, str) or not molecule_id:
		return None
	if not isinstance(atom_id, str) or not atom_id:
		return None
	for molecule in getattr(document, "molecules", ()):
		if getattr(molecule, "mol_id", None) != molecule_id:
			continue
		for atom_model in molecule.atoms:
			if getattr(atom_model, "backend_durable_id", None) == atom_id:
				return atom_model
		return None
	return None


#============================================
def _find_current_bond(document: object, molecule_id: str, bond_id: str) -> object | None:
	"""Resolve one durable bond from the current document projection."""
	if not isinstance(molecule_id, str) or not molecule_id:
		return None
	if not isinstance(bond_id, str) or not bond_id:
		return None
	for molecule in getattr(document, "molecules", ()):
		if getattr(molecule, "mol_id", None) != molecule_id:
			continue
		for bond_model in molecule.bonds:
			if getattr(bond_model, "backend_durable_id", None) == bond_id:
				return bond_model
		return None
	return None


#============================================
def _resolve_synchronized_atom(session: object, molecule_id: str, atom_id: str) -> tuple[object, object] | None:
	"""Return the active session's current atom only when its tab still owns it."""
	if getattr(session, "is_disposed", True):
		return None
	view = getattr(session, "view", None)
	if view is None or _active_document_session(view) is not session:
		return None
	atom_model = _find_current_atom(getattr(session, "document", None), molecule_id, atom_id)
	if not _is_valid_qobject(atom_model):
		return None
	return view, atom_model


#============================================
def _resolve_synchronized_bond(session: object, molecule_id: str, bond_id: str) -> tuple[object, object] | None:
	"""Return the active session's current bond only when its tab still owns it."""
	if getattr(session, "is_disposed", True):
		return None
	view = getattr(session, "view", None)
	if view is None or _active_document_session(view) is not session:
		return None
	bond_model = _find_current_bond(getattr(session, "document", None), molecule_id, bond_id)
	if not _is_valid_qobject(bond_model):
		return None
	return view, bond_model


#============================================
def _resolve_local_atom(
		view: object, molecule_id: str, atom_id: str, model_ref: weakref.ReferenceType,
		) -> object | None:
	"""Prefer the live local projection, with a weak legacy model fallback."""
	document = getattr(view, "document", None)
	atom_model = _find_current_atom(document, molecule_id, atom_id)
	if _is_valid_qobject(atom_model):
		return atom_model
	atom_model = model_ref()
	if not _is_valid_qobject(atom_model):
		return None
	if bkchem_qt.canvas.scene_queries.find_molecule_for_atom(view, atom_model) is None:
		return None
	return atom_model


#============================================
def _resolve_local_bond(
		view: object, molecule_id: str, bond_id: str, model_ref: weakref.ReferenceType,
		) -> object | None:
	"""Prefer the live local projection, with a weak legacy model fallback."""
	document = getattr(view, "document", None)
	bond_model = _find_current_bond(document, molecule_id, bond_id)
	if _is_valid_qobject(bond_model):
		return bond_model
	bond_model = model_ref()
	if not _is_valid_qobject(bond_model):
		return None
	if bkchem_qt.canvas.scene_queries.find_molecule_for_bond(view, bond_model) is None:
		return None
	return bond_model


#============================================
def _inert_callback() -> object:
	"""Return one no-op callback for an inactive session-owned menu."""
	def invoke() -> None:
		"""Consume an action whose originating session is no longer active."""
		return
	return invoke


#============================================
def _atom_properties_callback(
		view: object, route: tuple[str, object | None], molecule_id: str,
		atom_id: str, model_ref: weakref.ReferenceType,
		) -> object:
	"""Build one atom Properties callback without retaining a projection model."""
	kind, session = route
	if kind == "inactive":
		return _inert_callback()
	if kind == "synchronized":
		def invoke_synchronized() -> None:
			"""Resolve the active current atom immediately before opening its dialog."""
			resolved = _resolve_synchronized_atom(session, molecule_id, atom_id)
			if resolved is None:
				return
			current_view, atom_model = resolved
			bkchem_qt.actions.property_editing.edit_atom_properties(
				atom_model, current_view,
				bkchem_qt.canvas.scene_queries.find_undo_stack(current_view),
			)
		return invoke_synchronized
	def invoke_local() -> None:
		"""Resolve the local atom when its explicitly local action is chosen."""
		atom_model = _resolve_local_atom(view, molecule_id, atom_id, model_ref)
		if atom_model is None:
			return
		bkchem_qt.actions.property_editing.edit_atom_properties(
			atom_model, view, bkchem_qt.canvas.scene_queries.find_undo_stack(view),
		)
	return invoke_local


#============================================
def _atom_symbol_callback(
		view: object, route: tuple[str, object | None], molecule_id: str,
		atom_id: str, model_ref: weakref.ReferenceType, symbol: str,
		) -> object:
	"""Build one Set Element callback without retaining a projection model."""
	kind, session = route
	if kind == "inactive":
		return _inert_callback()
	if kind == "synchronized":
		def invoke_synchronized() -> None:
			"""Resolve the active current atom immediately before submitting element intent."""
			resolved = _resolve_synchronized_atom(session, molecule_id, atom_id)
			if resolved is None:
				return
			current_view, atom_model = resolved
			_set_atom_symbol(current_view, atom_model, symbol)
		return invoke_synchronized
	def invoke_local() -> None:
		"""Route a local current atom through the existing element boundary."""
		atom_model = _resolve_local_atom(view, molecule_id, atom_id, model_ref)
		if atom_model is None:
			return
		_set_atom_symbol(view, atom_model, symbol)
	return invoke_local


#============================================
def _origin_document_session(view: object) -> object | None:
	"""Return the session that owns this view's scene, including when inactive."""
	scene = view.scene()
	if scene is None:
		return None
	session = scene.parent()
	if (
		getattr(session, "view", None) is not view
		or not callable(getattr(session, "structure_delete_context", None))
	):
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
	action_route = _context_menu_action_route(view)
	model_ref = weakref.ref(bond_model)

	# delete action
	delete_action = menu.addAction("Delete")
	delete_action.setShortcut(PySide6.QtGui.QKeySequence.StandardKey.Delete)
	delete_action.triggered.connect(_structure_delete_callback(view, bond_item))

	menu.addSeparator()

	# properties action (opens bond dialog)
	props_action = menu.addAction("Properties...")
	props_action.triggered.connect(_bond_properties_callback(
		view, action_route, molecule_key, bond_key, model_ref,
	))

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
def _bond_properties_callback(
		view: object, route: tuple[str, object | None], molecule_id: str,
		bond_id: str, model_ref: weakref.ReferenceType,
		) -> object:
	"""Build one bond Properties callback without retaining a projection model."""
	kind, session = route
	if kind == "inactive":
		return _inert_callback()
	if kind == "synchronized":
		def invoke_synchronized() -> None:
			"""Resolve the active current bond immediately before opening its dialog."""
			resolved = _resolve_synchronized_bond(session, molecule_id, bond_id)
			if resolved is None:
				return
			current_view, bond_model = resolved
			bkchem_qt.actions.property_editing.edit_bond_properties(
				bond_model, current_view,
				bkchem_qt.canvas.scene_queries.find_undo_stack(current_view),
			)
		return invoke_synchronized
	def invoke_local() -> None:
		"""Resolve the local bond when its explicitly local action is chosen."""
		bond_model = _resolve_local_bond(view, molecule_id, bond_id, model_ref)
		if bond_model is None:
			return
		bkchem_qt.actions.property_editing.edit_bond_properties(
			bond_model, view, bkchem_qt.canvas.scene_queries.find_undo_stack(view),
		)
	return invoke_local


#============================================
def _delete_bond(view: object, bond_item: object) -> None:
	"""Delete a bond with undo support.

	Args:
		view: The ChemView widget.
		bond_item: The BondItem to delete.
	"""
	callback = _structure_delete_callback(view, bond_item)
	del bond_item
	callback()


#============================================
def _delete_bond_local(view: object, bond_item: object) -> None:
	"""Delete one bond through the explicitly local undo route."""
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
