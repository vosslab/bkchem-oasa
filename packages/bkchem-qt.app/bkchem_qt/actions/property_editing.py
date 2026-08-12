"""Backend-first property dialog operations shared by Qt interaction surfaces."""

# local repo modules
import bkchem_qt.dialogs.atom_dialog
import bkchem_qt.dialogs.arrow_dialog
import bkchem_qt.dialogs.bond_dialog
import bkchem_qt.dialogs.geometric_properties_dialog
import bkchem_qt.dialogs.plus_dialog
import bkchem_qt.dialogs.text_dialog
import bkchem_qt.dialogs.wavy_dialog
import bkchem_qt.io.cdml_inspection
import bkchem_qt.models.bracket_pair_selection
import bkchem_qt.undo.commands


_GEOMETRIC_KINDS = frozenset({"rect", "square", "oval", "circle", "polygon", "polyline"})
_GEOMETRIC_TITLES = {
	"rect": "Rectangle", "square": "Square", "oval": "Oval", "circle": "Circle",
	"polygon": "Polygon", "polyline": "Polyline",
}


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
def _presentation_properties_submission(
		parent: object, model: object, capture_name: str,
		) -> tuple[int, object, str] | None:
	"""Return one frozen synchronized durable presentation target."""
	window, view = _owning_window_and_view(parent)
	identifier = getattr(model, "object_id", None)
	if not getattr(model, "editable", False) or not isinstance(identifier, str) or not identifier:
		return None
	capture_for_view = getattr(window, capture_name, None)
	if not callable(capture_for_view):
		return None
	captured = capture_for_view(view, identifier)
	if (
		captured is None or type(captured) is not tuple or len(captured) != 2
		or type(captured[0]) is not int or not callable(captured[1])
	):
		return None
	return captured[0], captured[1], identifier


#============================================
def _single_selected_presentation(
		parent: object, kind: str | frozenset[str], *, style: str | None = None,
		) -> object | None:
	"""Return one exact current editable presentation root of the requested kind."""
	window, _view = _owning_window_and_view(parent)
	document = getattr(window, "document", None)
	if document is None or document.selected_atoms or document.selected_bonds:
		return None
	presentations = document.selected_presentation_objects
	presentation_ids = document.selected_presentation_stack_root_ids
	if len(presentations) != 1 or len(presentation_ids) != 1:
		return None
	model = presentations[0]
	kinds = frozenset({kind}) if type(kind) is str else kind
	if (
		model.kind not in kinds or not model.editable
		or model.object_id != presentation_ids[0]
		or style is not None and model.attributes.get("style") != style
	):
		return None
	return model


#============================================
def _single_selected_plus(parent: object) -> object | None:
	"""Return one exact current durable Plus projection inside this helper frame."""
	return _single_selected_presentation(parent, "plus")


#============================================
def has_single_selected_plus(parent: object) -> bool:
	"""Report exact Plus Configure eligibility without retaining its QObject."""
	selected = _single_selected_plus(parent)
	return selected is not None


#============================================
def _single_selected_wavy(parent: object) -> object | None:
	"""Return one exact current durable Wavy projection inside this helper frame."""
	return _single_selected_presentation(parent, "polyline", style="wavy")


#============================================
def has_single_selected_wavy(parent: object) -> bool:
	"""Report exact Wavy Configure eligibility without retaining its QObject."""
	return _single_selected_wavy(parent) is not None


#============================================
def _single_selected_arrow(parent: object) -> object | None:
	"""Return one exact current durable Arrow projection inside this helper frame."""
	return _single_selected_presentation(parent, "arrow")


#============================================
def has_single_selected_arrow(parent: object) -> bool:
	"""Report exact Arrow Configure eligibility without retaining its QObject."""
	return _single_selected_arrow(parent) is not None


#============================================
def _single_selected_geometric(parent: object) -> object | None:
	"""Return one ordinary shape or line handled by the shared appearance patch."""
	model = _single_selected_presentation(parent, _GEOMETRIC_KINDS)
	if model is not None and (
		model.kind != "polyline" or model.attributes.get("style") != "wavy"
	):
		return model
	return None


#============================================
def has_single_selected_geometric(parent: object) -> bool:
	"""Report geometric Configure eligibility without retaining its QObject."""
	return _single_selected_geometric(parent) is not None


#============================================
def _selected_bracket_pair(parent: object) -> tuple[object, ...] | None:
	"""Return one wholly selected current bracket pair observation."""
	window, _view = _owning_window_and_view(parent)
	document = getattr(window, "document", None)
	if document is None:
		return None
	return bkchem_qt.models.bracket_pair_selection.selected_pair(document)


#============================================
def has_selected_bracket_pair(parent: object) -> bool:
	"""Report whether Configure can edit exactly one observed bracket pair."""
	return _selected_bracket_pair(parent) is not None


#============================================
def capture_selected_bracket_properties(
		parent: object,
		) -> tuple[int, object, str, tuple[tuple[str, object], ...]] | None:
	"""Capture detached pair appearance intent from plain projection facts."""
	pair = _selected_bracket_pair(parent)
	if pair is None:
		return None
	pair_id, _member_ids, _style, width, color = pair
	window, view = _owning_window_and_view(parent)
	capture = getattr(window, "capture_bracket_properties_for_view", None)
	if not callable(capture):
		return None
	synchronized = capture(view, pair_id)
	if (
		synchronized is None or type(synchronized) is not tuple or len(synchronized) != 2
		or type(synchronized[0]) is not int or not callable(synchronized[1])
	):
		return None
	# Imported disagreement is intentionally represented as an unchanged baseline;
	# users may positively choose a value, but merely opening/accepting is inert.
	dialog = bkchem_qt.dialogs.geometric_properties_dialog.GeometricPropertiesDialog(
		title="Bracket appearance", line_width=width if width is not None else 1.0,
		line_color=color if color is not None else "#000000", area_color=None,
		fillable=False, parent=parent,
	)
	expected_revision, submit = synchronized
	changes = ()
	if dialog.exec() == dialog.DialogCode.Accepted:
		changes = dialog.changes()
	return expected_revision, submit, pair_id, changes


#============================================
def capture_selected_plus_properties(
		parent: object,
		) -> tuple[int, object, str, tuple[tuple[str, object], ...]] | None:
	"""Capture dialog intent while all disposable Plus wrappers stay local."""
	plus_model = _single_selected_plus(parent)
	if plus_model is None:
		return None
	synchronized = _presentation_properties_submission(
		parent, plus_model, "capture_plus_properties_for_view",
	)
	if synchronized is None:
		window, _view = _owning_window_and_view(parent)
		status_bar = getattr(window, "statusBar", None)
		if callable(status_bar):
			status_bar().showMessage("Plus properties are unavailable for this document", 3000)
		return None
	attributes = plus_model.attributes
	font_size = int(attributes.get("font_size", "14"))
	color = attributes.get("color", "#000000")
	background_color = attributes.get("background-color") or None
	font_family = plus_model.effective_font_family or "helvetica"
	dialog = bkchem_qt.dialogs.plus_dialog.PlusDialog(
		font_size, color, parent, background_color=background_color,
		font_family=font_family,
	)
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
	synchronized = _presentation_properties_submission(
		parent, wavy_model, "capture_wavy_properties_for_view",
	)
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
def capture_selected_arrow_properties(
		parent: object,
		) -> tuple[int, object, str, tuple[tuple[str, object], ...]] | None:
	"""Capture one Arrow dialog intent before disposable wrappers are released."""
	arrow_model = _single_selected_arrow(parent)
	if arrow_model is None:
		return None
	synchronized = _presentation_properties_submission(
		parent, arrow_model, "capture_arrow_properties_for_view",
	)
	if synchronized is None:
		return None
	attributes = arrow_model.attributes
	start_head = attributes.get("start", "no").lower() in ("yes", "true", "1", "both")
	end_head = attributes.get("end", "yes").lower() not in ("no", "false", "0")
	spline = attributes.get("spline", "no").lower() in ("yes", "true", "1")
	dialog = bkchem_qt.dialogs.arrow_dialog.ArrowDialog(
		parent=parent, start_head=start_head, end_head=end_head,
		line_width=float(attributes.get("width", "1")), spline=spline,
		color=attributes.get("color", "#000000"),
	)
	expected_revision, submit, arrow_id = synchronized
	changes = ()
	if dialog.exec() == dialog.DialogCode.Accepted:
		changes = dialog.changes()
	return expected_revision, submit, arrow_id, changes


#============================================
def capture_selected_geometric_properties(
		parent: object,
		) -> tuple[int, object, str, tuple[tuple[str, object], ...]] | None:
	"""Capture one shape/line appearance dialog as detached scalar intent."""
	model = _single_selected_geometric(parent)
	if model is None:
		return None
	synchronized = _presentation_properties_submission(
		parent, model, "capture_geometric_properties_for_view",
	)
	if synchronized is None:
		return None
	attributes = model.attributes
	line_color = attributes.get("line_color", attributes.get("color", "#000000"))
	fillable = model.kind != "polyline"
	area_color = attributes.get("area_color", attributes.get("background-color"))
	if area_color in ("", "none") or not fillable:
		area_color = None
	dialog = bkchem_qt.dialogs.geometric_properties_dialog.GeometricPropertiesDialog(
		title=_GEOMETRIC_TITLES[model.kind],
		line_width=float(attributes.get("width", "1")), line_color=line_color,
		area_color=area_color, fillable=fillable, parent=parent,
	)
	expected_revision, submit, presentation_id = synchronized
	changes = ()
	if dialog.exec() == dialog.DialogCode.Accepted:
		changes = dialog.changes()
	return expected_revision, submit, presentation_id, changes


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
		"background_color": attributes.get("background-color") or None,
	}
	return values


#============================================
def _push_local_property_changes(
		model: object, changes: tuple[tuple[str, object], ...],
		undo_stack: object, macro_text: str, aliases: dict[str, str],
		) -> bool:
	"""Push detached dialog intent as one isolated local undoable edit.

	The dialog never changes the projected model.  This explicit compatibility
	boundary translates backend field spellings to local model properties, then
	lets each command's initial redo perform the first mutation.

	Args:
		model: AtomModel or BondModel receiving the accepted values.
		changes: Unique detached field/value intent returned by the dialog.
		undo_stack: QUndoStack for the intentionally isolated local document.
		macro_text: One user-visible description for the grouped edit.
		aliases: Backend field names whose local model names differ.

	Returns:
		True when the dialog changed at least one persisted property.
	"""
	commands = []
	for field_name, new_value in changes:
		property_name = aliases[field_name] if field_name in aliases else field_name
		old_value = getattr(model, property_name)
		if new_value == old_value:
			continue
		commands.append((property_name, old_value, new_value))
	if not commands:
		return False
	undo_stack.beginMacro(macro_text)
	for property_name, old_value, new_value in commands:
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
	if synchronized is None and _synchronized_application_context(parent):
		return False
	if synchronized is None and undo_stack is None:
		return False
	dialog = bkchem_qt.dialogs.atom_dialog.AtomDialog(atom_model, parent)
	if dialog.exec() != dialog.DialogCode.Accepted:
		return False
	changes = dialog.changes()
	if not changes:
		return False
	if synchronized is not None:
		expected_revision, submit, molecule_id, atom_id = synchronized
		outcome = submit(expected_revision, molecule_id, atom_id, changes)
		window, _view = _owning_window_and_view(parent)
		show_outcome = getattr(window, "_show_persistent_action_outcome", None)
		if callable(show_outcome):
			show_outcome(outcome)
		return outcome.status == "accepted" and outcome.commit is not None
	changed = _push_local_property_changes(
		atom_model, changes, undo_stack, "Edit Atom Properties",
		{"element": "symbol"},
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
	if synchronized is None and _synchronized_application_context(parent):
		return False
	if synchronized is None and undo_stack is None:
		return False
	dialog = bkchem_qt.dialogs.bond_dialog.BondDialog(bond_model, parent)
	if dialog.exec() != dialog.DialogCode.Accepted:
		return False
	changes = dialog.changes()
	if not changes:
		return False
	if synchronized is not None:
		expected_revision, submit, molecule_id, bond_id = synchronized
		outcome = submit(expected_revision, molecule_id, bond_id, changes)
		window, _view = _owning_window_and_view(parent)
		show_outcome = getattr(window, "_show_persistent_action_outcome", None)
		if callable(show_outcome):
			show_outcome(outcome)
		return outcome.status == "accepted" and outcome.commit is not None
	changed = _push_local_property_changes(
		bond_model, changes, undo_stack, "Edit Bond Properties",
		{"color": "line_color"},
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
		font_color=initial["font_color"], background_color=initial["background_color"],
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
