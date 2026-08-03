"""Backend-first property dialog operations shared by Qt interaction surfaces."""

# local repo modules
import bkchem_qt.dialogs.atom_dialog
import bkchem_qt.dialogs.bond_dialog
import bkchem_qt.dialogs.plus_dialog
import bkchem_qt.dialogs.text_dialog
import bkchem_qt.dialogs.wavy_dialog
import bkchem_qt.io.cdml_inspection
import bkchem_qt.undo.commands


#============================================
def _owning_window_and_view(parent: object) -> tuple[object, object | None]:
	"""Resolve one dialog parent to its owning window and exact document view.

	A menu action owns the main window directly, while context and edit-mode
	actions own the view.  Keeping that distinction here ensures every property
	route asks the same registered-session question before considering the
	isolated-document fallback.
	"""
	# A MainWindow is identified by the application session surface it owns, not
	# by PySide wrapper identity.  The wrapper handed to a menu callback need not
	# be the same Python object that originally registered the window.
	if hasattr(parent, "_sessions_by_view"):
		return parent, getattr(parent, "view", None)
	parent_window = getattr(parent, "window", None)
	window = parent_window() if callable(parent_window) else parent
	return window, parent


#============================================
def _synchronized_application_context(parent: object) -> bool:
	"""Report whether an interaction belongs to the session-owning application.

	An unregistered view still belongs to this context.  It must be inert rather
	than being mistaken for an isolated document and given a local undo fallback.
	"""
	window, _view = _owning_window_and_view(parent)
	return hasattr(window, "_sessions_by_view")


#============================================
def _bond_properties_submission(
		parent: object, bond_model: object,
		) -> tuple[int, object, str, str] | None:
	"""Return the frozen synchronized durable bond target for this owning view."""
	window, view = _owning_window_and_view(parent)
	molecule = None
	if hasattr(view, "scene"):
		from bkchem_qt.canvas.scene_queries import find_molecule_for_bond
		molecule = find_molecule_for_bond(view, bond_model)
	molecule_id = getattr(molecule, "mol_id", None)
	bond_id = getattr(bond_model, "backend_durable_id", None)
	if not isinstance(molecule_id, str) or not molecule_id:
		return None
	if not isinstance(bond_id, str) or not bond_id:
		return None
	capture_for_view = getattr(window, "capture_bond_properties_for_view", None)
	if not callable(capture_for_view):
		return None
	captured = capture_for_view(view, molecule_id, bond_id)
	if (
		captured is None or type(captured) is not tuple or len(captured) != 2
		or type(captured[0]) is not int or not callable(captured[1])
	):
		return None
	return captured[0], captured[1], molecule_id, bond_id


#============================================
def _atom_properties_submission(
		parent: object, atom_model: object,
		) -> tuple[int, object, str, str] | None:
	"""Return the frozen synchronized durable atom target for this owning view."""
	window, view = _owning_window_and_view(parent)
	molecule = None
	if hasattr(view, "scene"):
		from bkchem_qt.canvas.scene_queries import find_molecule_for_atom
		molecule = find_molecule_for_atom(view, atom_model)
	molecule_id = getattr(molecule, "mol_id", None)
	atom_id = getattr(atom_model, "backend_durable_id", None)
	if not isinstance(molecule_id, str) or not molecule_id:
		return None
	if not isinstance(atom_id, str) or not atom_id:
		return None
	capture_for_view = getattr(window, "capture_atom_properties_for_view", None)
	if not callable(capture_for_view):
		return None
	captured = capture_for_view(view, molecule_id, atom_id)
	if (
		captured is None or type(captured) is not tuple or len(captured) != 2
		or type(captured[0]) is not int or not callable(captured[1])
	):
		return None
	return captured[0], captured[1], molecule_id, atom_id


#============================================
def _text_properties_submission(
		parent: object, text_model: object,
		) -> tuple[int, object, str] | None:
	"""Return the frozen synchronized durable Text target for this owning view."""
	window, view = _owning_window_and_view(parent)
	text_id = getattr(text_model, "object_id", None)
	if not getattr(text_model, "editable", False) or not isinstance(text_id, str) or not text_id:
		return None
	capture_for_view = getattr(window, "capture_text_properties_for_view", None)
	if not callable(capture_for_view):
		return None
	captured = capture_for_view(view, text_id)
	if (
		captured is None or type(captured) is not tuple or len(captured) != 2
		or type(captured[0]) is not int or not callable(captured[1])
	):
		return None
	return captured[0], captured[1], text_id


#============================================
def _plus_properties_submission(
		parent: object, plus_model: object,
		) -> tuple[int, object, str] | None:
	"""Return the frozen synchronized durable Plus target for this owning view."""
	window, view = _owning_window_and_view(parent)
	plus_id = getattr(plus_model, "object_id", None)
	if not getattr(plus_model, "editable", False) or not isinstance(plus_id, str) or not plus_id:
		return None
	capture_for_view = getattr(window, "capture_plus_properties_for_view", None)
	if not callable(capture_for_view):
		return None
	captured = capture_for_view(view, plus_id)
	if (
		captured is None or type(captured) is not tuple or len(captured) != 2
		or type(captured[0]) is not int or not callable(captured[1])
	):
		return None
	return captured[0], captured[1], plus_id


#============================================
def _wavy_properties_submission(
		parent: object, wavy_model: object,
		) -> tuple[int, object, str] | None:
	"""Return the frozen synchronized durable Wavy target for this owning view."""
	window, view = _owning_window_and_view(parent)
	wavy_id = getattr(wavy_model, "object_id", None)
	if not getattr(wavy_model, "editable", False) or not isinstance(wavy_id, str) or not wavy_id:
		return None
	capture_for_view = getattr(window, "capture_wavy_properties_for_view", None)
	if not callable(capture_for_view):
		return None
	captured = capture_for_view(view, wavy_id)
	if (
		captured is None or type(captured) is not tuple or len(captured) != 2
		or type(captured[0]) is not int or not callable(captured[1])
	):
		return None
	return captured[0], captured[1], wavy_id


#============================================
def _single_selected_plus(parent: object) -> object | None:
	"""Return one exact current durable Plus projection inside this helper frame."""
	window, _view = _owning_window_and_view(parent)
	document = getattr(window, "document", None)
	if document is None:
		return None
	if document.selected_atoms or document.selected_bonds:
		return None
	presentations = document.selected_presentation_objects
	presentation_ids = document.selected_presentation_stack_root_ids
	if (
		len(presentations) != 1 or len(presentation_ids) != 1
		or presentations[0].kind != "plus"
		or not presentations[0].editable
		or presentations[0].object_id != presentation_ids[0]
	):
		return None
	return presentations[0]


#============================================
def has_single_selected_plus(parent: object) -> bool:
	"""Report exact Plus Configure eligibility without retaining its QObject."""
	selected = _single_selected_plus(parent)
	return selected is not None


#============================================
def _single_selected_wavy(parent: object) -> object | None:
	"""Return one exact current durable Wavy projection inside this helper frame."""
	window, _view = _owning_window_and_view(parent)
	document = getattr(window, "document", None)
	if document is None or document.selected_atoms or document.selected_bonds:
		return None
	presentations = document.selected_presentation_objects
	presentation_ids = document.selected_presentation_stack_root_ids
	if (
		len(presentations) != 1 or len(presentation_ids) != 1
		or presentations[0].kind != "polyline"
		or not presentations[0].editable
		or presentations[0].object_id != presentation_ids[0]
		or presentations[0].attributes.get("style") != "wavy"
	):
		return None
	return presentations[0]


#============================================
def has_single_selected_wavy(parent: object) -> bool:
	"""Report exact Wavy Configure eligibility without retaining its QObject."""
	return _single_selected_wavy(parent) is not None


#============================================
def capture_selected_plus_properties(
		parent: object,
		) -> tuple[int, object, str, tuple[tuple[str, object], ...]] | None:
	"""Capture dialog intent while all disposable Plus wrappers stay local."""
	plus_model = _single_selected_plus(parent)
	if plus_model is None:
		return None
	synchronized = _plus_properties_submission(parent, plus_model)
	if synchronized is None:
		window, _view = _owning_window_and_view(parent)
		status_bar = getattr(window, "statusBar", None)
		if callable(status_bar):
			status_bar().showMessage("Plus properties are unavailable for this document", 3000)
		return None
	attributes = plus_model.attributes
	font_size = int(attributes.get("font_size", "14"))
	color = attributes.get("color", "#000000")
	dialog = bkchem_qt.dialogs.plus_dialog.PlusDialog(font_size, color, parent)
	expected_revision, submit, plus_id = synchronized
	changes = ()
	if dialog.exec() == dialog.DialogCode.Accepted:
		changes = dialog.changes()
	return expected_revision, submit, plus_id, changes


#============================================
def capture_selected_wavy_properties(
		parent: object,
		) -> tuple[int, object, str, tuple[tuple[str, object], ...]] | None:
	"""Capture one Wavy dialog intent before disposable wrappers are released."""
	wavy_model = _single_selected_wavy(parent)
	if wavy_model is None:
		return None
	synchronized = _wavy_properties_submission(parent, wavy_model)
	if synchronized is None:
		return None
	attributes = wavy_model.attributes
	width = float(attributes.get("width", "1"))
	line_color = attributes.get("line_color", attributes.get("color", "#000000"))
	dialog = bkchem_qt.dialogs.wavy_dialog.WavyDialog(width, line_color, parent)
	expected_revision, submit, wavy_id = synchronized
	changes = ()
	if dialog.exec() == dialog.DialogCode.Accepted:
		changes = dialog.changes()
	return expected_revision, submit, wavy_id, changes


#============================================
def _plain_text_values(text_model: object) -> dict[str, object] | None:
	"""Copy current Text projection values into detached plain dialog scalars."""
	fragment = text_model.xml_ftext
	if fragment is None:
		plain_text = text_model.display_text
	else:
		plain_text = bkchem_qt.io.cdml_inspection.direct_ftext_text(fragment)
	if plain_text is None:
		return None
	font = text_model.font_attributes
	attributes = text_model.attributes
	values = {
		"text": plain_text,
		"font_family": font.get("family", "Arial"),
		"font_size": int(font.get("size", attributes.get("font_size", "12"))),
		"font_color": font.get(
			"color", attributes.get("line_color", attributes.get("color", "#000000")),
		),
	}
	return values


#============================================
def _apply_changed_properties(
		model: object, old_values: dict, undo_stack: object,
		macro_text: str,
		) -> bool:
	"""Turn an isolated dialog-mutated model into one local undoable edit.

	The legacy dialogs intentionally apply their accepted values directly to
	the supplied model.  This boundary restores each changed value before
	placing a command on the stack, so the command's initial redo updates the
	model and its projections through the normal property signals.

	Args:
		model: AtomModel or BondModel changed by an accepted dialog.
		old_values: Values captured before opening the dialog.
		undo_stack: QUndoStack for the intentionally isolated local document.
		macro_text: One user-visible description for the grouped edit.

	Returns:
		True when the dialog changed at least one persisted property.
	"""
	changes = []
	for property_name, old_value in old_values.items():
		new_value = getattr(model, property_name)
		if new_value != old_value:
			changes.append((property_name, old_value, new_value))
	if not changes:
		return False
	# Restore dialog mutations so push() invokes each command's redo normally.
	for property_name, old_value, _new_value in changes:
		setattr(model, property_name, old_value)
	undo_stack.beginMacro(macro_text)
	for property_name, old_value, new_value in changes:
		undo_stack.push(bkchem_qt.undo.commands.ChangePropertyCommand(
			model, property_name, old_value, new_value,
			text=f"Change {property_name}",
		))
	undo_stack.endMacro()
	return True


#============================================
def edit_atom_properties(
		atom_model: object, parent: object, undo_stack: object,
		) -> bool:
	"""Open the atom dialog and apply accepted changes through its owner.

	Synchronized sessions submit a backend atom-properties patch and receive
	canonical reprojection. Explicitly isolated documents retain the local
	undo fallback.

	Args:
		atom_model: AtomModel selected for editing.
		parent: Widget that owns the dialog.
		undo_stack: Active document QUndoStack.

	Returns:
		True when accepted dialog changes were recorded.
	"""
	synchronized = _atom_properties_submission(parent, atom_model)
	if synchronized is not None:
		dialog = bkchem_qt.dialogs.atom_dialog.AtomDialog(atom_model, parent)
		if dialog.exec() != dialog.DialogCode.Accepted:
			return False
		changes = dialog.changes()
		if not changes:
			return False
		expected_revision, submit, molecule_id, atom_id = synchronized
		outcome = submit(expected_revision, molecule_id, atom_id, changes)
		window, _view = _owning_window_and_view(parent)
		show_outcome = getattr(window, "_show_persistent_action_outcome", None)
		if callable(show_outcome):
			show_outcome(outcome)
		return outcome.status == "accepted" and outcome.commit is not None
	if _synchronized_application_context(parent):
		return False
	if undo_stack is None:
		return False
	old_values = {
		"symbol": atom_model.symbol,
		"charge": atom_model.charge,
		"valency": atom_model.valency,
		"isotope": atom_model.isotope,
		"multiplicity": atom_model.multiplicity,
		"show": atom_model.show,
		"show_hydrogens": atom_model.show_hydrogens,
		"font_size": atom_model.font_size,
		"line_color": atom_model.line_color,
	}
	accepted = bkchem_qt.dialogs.atom_dialog.AtomDialog.edit_atom(
		atom_model, parent,
	)
	if not accepted:
		return False
	changed = _apply_changed_properties(
		atom_model, old_values, undo_stack, "Edit Atom Properties",
	)
	return changed


#============================================
def edit_bond_properties(
		bond_model: object, parent: object, undo_stack: object,
		) -> bool:
	"""Open the bond dialog and apply accepted changes through its owner.

	Synchronized sessions submit a backend bond-properties patch and receive
	canonical reprojection. Explicitly isolated documents retain the local
	undo fallback.

	Args:
		bond_model: BondModel selected for editing.
		parent: Widget that owns the dialog.
		undo_stack: Active document QUndoStack.

	Returns:
		True when accepted dialog changes were recorded.
	"""
	synchronized = _bond_properties_submission(parent, bond_model)
	if synchronized is not None:
		dialog = bkchem_qt.dialogs.bond_dialog.BondDialog(bond_model, parent)
		if dialog.exec() != dialog.DialogCode.Accepted:
			return False
		changes = dialog.changes()
		if not changes:
			return False
		expected_revision, submit, molecule_id, bond_id = synchronized
		outcome = submit(expected_revision, molecule_id, bond_id, changes)
		window, _view = _owning_window_and_view(parent)
		show_outcome = getattr(window, "_show_persistent_action_outcome", None)
		if callable(show_outcome):
			show_outcome(outcome)
		return outcome.status == "accepted" and outcome.commit is not None
	if _synchronized_application_context(parent):
		return False
	if undo_stack is None:
		return False
	old_values = {
		"order": bond_model.order,
		"type": bond_model.type,
		"center": bond_model.center,
		"line_width": bond_model.line_width,
		"bond_width": bond_model.bond_width,
		"wedge_width": bond_model.wedge_width,
		"line_color": bond_model.line_color,
	}
	accepted = bkchem_qt.dialogs.bond_dialog.BondDialog.edit_bond(
		bond_model, parent,
	)
	if not accepted:
		return False
	changed = _apply_changed_properties(
		bond_model, old_values, undo_stack, "Edit Bond Properties",
	)
	return changed


#============================================
def edit_text_properties(text_model: object, parent: object) -> bool:
	"""Open one detached plain Text dialog and submit through captured authority.

	Plain Configure is intentionally synchronized-session only. Rich Text and
	legacy-local Text mutation remain outside this bounded operation.
	"""
	synchronized = _text_properties_submission(parent, text_model)
	if synchronized is None:
		return False
	initial = _plain_text_values(text_model)
	if initial is None:
		return False
	dialog = bkchem_qt.dialogs.text_dialog.TextDialog(
		text=initial["text"], font_size=initial["font_size"],
		parent=parent, font_family=initial["font_family"],
		font_color=initial["font_color"],
	)
	if dialog.exec() != dialog.DialogCode.Accepted:
		return False
	changes = dialog.changes()
	if not changes:
		return False
	expected_revision, submit, text_id = synchronized
	outcome = submit(expected_revision, text_id, changes)
	window, _view = _owning_window_and_view(parent)
	show_outcome = getattr(window, "_show_persistent_action_outcome", None)
	if callable(show_outcome):
		show_outcome(outcome)
	return outcome.status == "accepted" and outcome.commit is not None
