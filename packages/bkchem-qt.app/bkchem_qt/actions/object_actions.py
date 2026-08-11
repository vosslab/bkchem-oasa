"""Object menu action registrations for BKChem-Qt."""

# Standard Library
import re

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction
import bkchem_qt.actions.property_editing
import bkchem_qt.actions.top_level_transform_actions
import bkchem_qt.canvas.document_projection
import bkchem_qt.dialogs.scale_dialog
import bkchem_qt.dialogs.rich_text_dialog
import bkchem_qt.geometry
import bkchem_qt.models.document_object
import bkchem_qt.models.document_session
import bkchem_qt.models.molecule_model
import bkchem_qt.undo.commands


#============================================
def _rich_text_font_values(text_model: object) -> tuple[str, int, str] | None:
	"""Copy valid visible root font values without normalizing persistent attributes."""
	font_attributes = text_model.font_attributes
	attributes = text_model.attributes
	family = font_attributes.get("family", "Arial")
	if type(family) is not str or not family.strip():
		return None
	size_text = font_attributes.get("size", attributes.get("font_size", "12"))
	if type(size_text) is not str or not size_text.isdecimal():
		return None
	size = int(size_text)
	if not 4 <= size <= 144:
		return None
	color = font_attributes.get(
		"color", attributes.get("line_color", attributes.get("color", "#000000")),
	)
	if type(color) is not str or re.fullmatch(r"#[0-9A-Fa-f]{6}", color) is None:
		return None
	return family, size, color


#============================================
def _has_authored_rich_style(text_model: object) -> bool:
	"""Return whether supported authored runs contain at least one visible style."""
	runs = text_model.formatted_text_runs
	return runs is not None and any(styles for _text, styles in runs)

#============================================
def _active_presentation_stack_session(app: object) -> object | None:
	"""Return the registered synchronized session owning all active aliases."""
	session = getattr(app, "_active_session", None)
	document = getattr(app, "document", None)
	scene = getattr(app, "scene", None)
	view = getattr(app, "view", None)
	sessions = getattr(app, "sessions", ())
	if session is None or document is None or scene is None or view is None:
		return None
	if session.is_disposed or session not in sessions:
		return None
	if session.document is not document or session.scene is not scene or session.view is not view:
		return None
	return session


#============================================
def _submit_presentation_stack_reorder(app: object, mode: str) -> None:
	"""Submit one eligible presentation-stack action through backend authority."""
	session = _active_presentation_stack_session(app)
	if session is None or not session.can_commit_persistent_action:
		app.statusBar().showMessage("Presentation stack action is unavailable", 3000)
		return
	root_ids = bkchem_qt.canvas.document_projection.selected_presentation_stack_root_ids(
		session.document, session.scene,
	)
	if not root_ids:
		app.statusBar().showMessage(
			"Select only durable presentation objects to reorder", 3000,
		)
		return
	if mode == "swap-at-slots" and len(root_ids) < 2:
		app.statusBar().showMessage("Select at least two items to swap", 3000)
		return
	try:
		submit = app.persistent_operation_capability_for(session)
	except ValueError:
		app.statusBar().showMessage("Presentation stack action is unavailable", 3000)
		return
	if _active_presentation_stack_session(app) is not session:
		app.statusBar().showMessage("Presentation stack action no longer applies to this tab", 3000)
		return
	request = bkchem_qt.models.document_session.build_presentation_stack_request(
		session.backend_snapshot.revision, mode, root_ids,
	)
	outcome = submit(request)
	app._show_persistent_action_outcome(outcome)
	app._refresh_document_actions()


#============================================
def handle_bring_to_front(app: object) -> None:
	"""Bring eligible direct presentation roots to the front authoritatively."""
	_submit_presentation_stack_reorder(app, "bring-to-front")


#============================================
def handle_send_back(app: object) -> None:
	"""Send eligible direct presentation roots to the back authoritatively."""
	_submit_presentation_stack_reorder(app, "send-back")


#============================================
def handle_swap_on_stack(app: object) -> None:
	"""Reverse eligible presentation roots in their backend stack slots."""
	_submit_presentation_stack_reorder(app, "swap-at-slots")


#============================================
def _selection_bounds(objects: list) -> tuple[float, float, float, float] | None:
	"""Return persistent aggregate bounds for selected document top levels."""
	bounds = bkchem_qt.geometry.union_bounds([
		bkchem_qt.geometry.top_level_bounds(object_model)
		for object_model in objects
	])
	return bounds


#============================================
def _push_affine_transform(
		document: object, objects: tuple[object, ...], origin: tuple[float, float],
		scale_x: float, scale_y: float, text: str,
		) -> bool:
	"""Push a non-merging model-state affine transform for selected objects."""
	atom_changes = []
	presentation_changes = []
	for object_model in objects:
		if isinstance(
			object_model, bkchem_qt.models.molecule_model.MoleculeModel,
			):
			for atom_model in object_model.atoms:
				before = (atom_model.x, atom_model.y)
				after = bkchem_qt.geometry.transform_point(
					before, origin, scale_x, scale_y,
				)
				if after != before:
					atom_changes.append((atom_model, before, after))
		elif isinstance(
			object_model, bkchem_qt.models.document_object.PresentationObject,
			):
			before_points = object_model.points
			before_bounds = object_model.bounds
			after_points = [
				(*bkchem_qt.geometry.transform_point(
					(x, y), origin, scale_x, scale_y,
				), z)
				for x, y, z in before_points
			]
			after_bounds = bkchem_qt.geometry.transform_bounds(
				before_bounds, origin, scale_x, scale_y,
			)
			if after_points != before_points or after_bounds != before_bounds:
				presentation_changes.append((
					object_model,
					(before_points, before_bounds),
					(after_points, after_bounds),
				))
		else:
			raise TypeError(f"Unsupported document object: {type(object_model)!r}")
	if not atom_changes and not presentation_changes:
		return False
	document.undo_stack.push(
		bkchem_qt.undo.commands.TransformGeometryCommand(
			atom_changes, presentation_changes, text,
		),
	)
	return True


#============================================
def _handle_vertical_mirror_locally(app: object) -> None:
	"""Reflect legacy-isolated selected objects through Qt-local undo."""
	objects = app.document.selected_top_level_objects
	bounds = _selection_bounds(objects)
	if bounds is None:
		app.statusBar().showMessage(
			"Select objects to mirror", 3000
		)
		return
	left, top, right, bottom = bounds
	if _push_affine_transform(
			app.document, tuple(objects), ((left + right) / 2.0, (top + bottom) / 2.0),
			-1.0, 1.0, "Vertical Mirror",
		):
		app.statusBar().showMessage("Vertical mirror applied", 2000)


#============================================
def _handle_horizontal_mirror_locally(app: object) -> None:
	"""Reflect legacy-isolated selected objects through Qt-local undo."""
	objects = app.document.selected_top_level_objects
	bounds = _selection_bounds(objects)
	if bounds is None:
		app.statusBar().showMessage(
			"Select objects to mirror", 3000
		)
		return
	left, top, right, bottom = bounds
	if _push_affine_transform(
			app.document, tuple(objects), ((left + right) / 2.0, (top + bottom) / 2.0),
			1.0, -1.0, "Horizontal Mirror",
		):
		app.statusBar().showMessage("Horizontal mirror applied", 2000)


#============================================
def _active_legacy_scale_session(app: object) -> object | None:
	"""Return one active legacy-isolated session with a live projection."""
	session = bkchem_qt.actions.top_level_transform_actions.active_transform_session(app)
	if (
		session is None
		or not session.legacy_isolated
		or not session.has_live_projection
		or session.document is None
	):
		return None
	return session


#============================================
def _handle_scale_locally(app: object, session: object) -> None:
	"""Scale legacy-isolated selected objects around their aggregate bounds.

	The dialog retains its existing independent X/Y scale choices.  Its pivot is
	the center of the selected document objects' aggregate persistent bounds.
	"""
	document = session.document
	objects = tuple(document.selected_top_level_objects)
	bounds = _selection_bounds(list(objects))
	if bounds is None:
		app.statusBar().showMessage(
			"Select objects to scale", 3000
		)
		return
	object_ids = tuple(id(object_model) for object_model in objects)
	persistent_generation = document.persistent_generation
	# show scale dialog
	result = bkchem_qt.dialogs.scale_dialog.ScaleDialog.get_scale_factors(
		app
	)
	if result is None:
		return
	scale_x, scale_y = result
	# avoid no-op scaling
	if scale_x == 1.0 and scale_y == 1.0:
		return
	current = _active_legacy_scale_session(app)
	if (
		current is not session
		or session.document is not document
		or document.persistent_generation != persistent_generation
		or tuple(
			id(object_model) for object_model in document.selected_top_level_objects
		) != object_ids
	):
		app.statusBar().showMessage("Scale no longer applies to this document", 3000)
		app._refresh_document_actions()
		return
	left, top, right, bottom = bounds
	if _push_affine_transform(
			document, objects, ((left + right) / 2.0, (top + bottom) / 2.0),
		scale_x, scale_y, "Scale",
		):
		app.statusBar().showMessage("Scale applied", 2000)


#============================================
def handle_vertical_mirror(app: object) -> None:
	"""Reflect selected roots through the backend or isolated local authority."""
	session = bkchem_qt.actions.top_level_transform_actions.active_transform_session(app)
	if session is not None and session.legacy_isolated:
		_handle_vertical_mirror_locally(app)
		return
	bkchem_qt.actions.top_level_transform_actions.submit_backend_transform(
		app, "mirror-vertical",
	)


#============================================
def handle_horizontal_mirror(app: object) -> None:
	"""Reflect selected roots through the backend or isolated local authority."""
	session = bkchem_qt.actions.top_level_transform_actions.active_transform_session(app)
	if session is not None and session.legacy_isolated:
		_handle_horizontal_mirror_locally(app)
		return
	bkchem_qt.actions.top_level_transform_actions.submit_backend_transform(
		app, "mirror-horizontal",
	)


#============================================
def handle_scale(app: object) -> None:
	"""Scale selected roots through backend authority or isolated local undo."""
	session = _active_legacy_scale_session(app)
	if session is not None:
		_handle_scale_locally(app, session)
		return
	bkchem_qt.actions.top_level_transform_actions.submit_scale_transform(
		app, bkchem_qt.dialogs.scale_dialog.ScaleDialog.get_scale_factors,
	)


#============================================
def handle_configure(app: object) -> None:
	"""Open properties for one selected atom, bond, Text, Plus, Wavy, or Arrow.

	If exactly one atom is selected, opens AtomDialog. If exactly
	one bond is selected, opens BondDialog. One synchronized durable top-level
	Text, plain Plus, Wavy, or Arrow opens its detached dialog. Otherwise the
	action reports its selection boundary.

	Args:
		app: The main application object.
	"""
	atoms = app.document.selected_atoms
	bonds = app.document.selected_bonds
	# exactly one atom, no bonds
	if len(atoms) == 1 and len(bonds) == 0:
		changed = bkchem_qt.actions.property_editing.edit_atom_properties(
			atoms[0].atom_model, app, app.document.undo_stack,
		)
		if changed:
			app.statusBar().showMessage("Edited atom properties", 2000)
		return
	# exactly one bond, no atoms
	if len(bonds) == 1 and len(atoms) == 0:
		changed = bkchem_qt.actions.property_editing.edit_bond_properties(
			bonds[0].bond_model, app, app.document.undo_stack,
		)
		if changed:
			app.statusBar().showMessage("Edited bond properties", 2000)
		return
	# Capture and finish the complete Plus projection/dialog frame before submit.
	# This local receives only plain immutable values and one session capability,
	# never a PresentationObject or QGraphics wrapper that reprojection retires.
	plus_capture = bkchem_qt.actions.property_editing.capture_selected_plus_properties(app)
	if plus_capture is not None:
		expected_revision, submit, plus_id, changes = plus_capture
		if changes:
			outcome = submit(expected_revision, plus_id, changes)
			show_outcome = getattr(app, "_show_persistent_action_outcome", None)
			if callable(show_outcome):
				show_outcome(outcome)
			if outcome.status == "accepted" and outcome.commit is not None:
				app.statusBar().showMessage("Edited Plus properties", 2000)
		return
	if bkchem_qt.actions.property_editing.has_single_selected_plus(app):
		return
	# Capture and finish the complete Wavy projection/dialog frame before submit.
	# This retains only plain values and an origin-bound session capability.
	wavy_capture = bkchem_qt.actions.property_editing.capture_selected_wavy_properties(app)
	if wavy_capture is not None:
		expected_revision, submit, wavy_id, changes = wavy_capture
		if changes:
			outcome = submit(expected_revision, wavy_id, changes)
			show_outcome = getattr(app, "_show_persistent_action_outcome", None)
			if callable(show_outcome):
				show_outcome(outcome)
			if outcome.status == "accepted" and outcome.commit is not None:
				app.statusBar().showMessage("Edited Wavy properties", 2000)
		return
	if bkchem_qt.actions.property_editing.has_single_selected_wavy(app):
		return
	# Capture only plain Arrow values and the exact origin session callback.
	arrow_capture = bkchem_qt.actions.property_editing.capture_selected_arrow_properties(app)
	if arrow_capture is not None:
		expected_revision, submit, arrow_id, changes = arrow_capture
		if changes:
			outcome = submit(expected_revision, arrow_id, changes)
			show_outcome = getattr(app, "_show_persistent_action_outcome", None)
			if callable(show_outcome):
				show_outcome(outcome)
			if outcome.status == "accepted" and outcome.commit is not None:
				app.statusBar().showMessage("Edited Arrow properties", 2000)
		return
	if bkchem_qt.actions.property_editing.has_single_selected_arrow(app):
		return
	# exactly one current durable Text presentation root
	presentations = app.document.selected_presentation_objects
	presentation_ids = app.document.selected_presentation_stack_root_ids
	if (
		len(atoms) == 0 and len(bonds) == 0
		and len(presentations) == 1 and len(presentation_ids) == 1
		and presentations[0].kind == "text"
		and presentations[0].editable
		and presentations[0].object_id == presentation_ids[0]
	):
		if _has_authored_rich_style(presentations[0]):
			app.statusBar().showMessage("Use Object > Edit Rich Text for formatted Text", 3000)
			return
		changed = bkchem_qt.actions.property_editing.edit_text_properties(
			presentations[0], app,
		)
		if changed:
			app.statusBar().showMessage("Edited Text properties", 2000)
		return
	app.statusBar().showMessage(
		"Select a single atom, bond, durable Text, Plus, Wavy, or Arrow to configure", 3000
	)


#============================================
def handle_edit_rich_text(app: object) -> None:
	"""Edit one selected authored Text through a captured backend-only patch."""
	presentations = app.document.selected_presentation_objects
	presentation_ids = app.document.selected_presentation_stack_root_ids
	if len(presentations) != 1 or len(presentation_ids) != 1:
		app.statusBar().showMessage("Select one editable rich Text object", 3000)
		return
	text_model = presentations[0]
	if (
			text_model.kind != "text" or not text_model.editable
			or text_model.object_id != presentation_ids[0]
			or not text_model.rich_text_editable
		):
		app.statusBar().showMessage("Rich text editing is unavailable for this object", 3000)
		return
	runs = text_model.formatted_text_runs
	if runs is None:
		app.statusBar().showMessage("Rich text editing is unavailable for this object", 3000)
		return
	text_id = text_model.object_id
	font_values = _rich_text_font_values(text_model)
	if font_values is None:
		app.statusBar().showMessage("Rich text editing is unavailable for this object", 3000)
		return
	font_family, font_size, font_color = font_values
	capture = app.capture_rich_text_for_view(app.view, text_id)
	if capture is None:
		app.statusBar().showMessage("Rich text editing is unavailable for this object", 3000)
		return
	expected_revision, submit = capture
	del presentations
	del presentation_ids
	del text_model
	dialog = bkchem_qt.dialogs.rich_text_dialog.RichTextDialog(
		runs, font_family, font_size, font_color, app,
	)
	if dialog.exec() != dialog.DialogCode.Accepted:
		return
	accepted_runs = dialog.get_runs()
	changes = dialog.changes()
	del dialog
	outcome = submit(expected_revision, text_id, accepted_runs, changes)
	app._show_persistent_action_outcome(outcome)
	app._refresh_document_actions()


#============================================
def register_object_actions(registry: object, app: object) -> None:
	"""Register all Object menu actions.

	Args:
		registry: ActionRegistry instance to register actions with.
		app: The main BKChem-Qt application object providing handler methods.
	"""
	# predicate: true when the document has selected items
	def has_selection() -> bool:
		return app.document is not None and app.document.has_selection

	# scale selected objects
	registry.register(MenuAction(
		id='object.scale',
		label_key='Scale',
		help_key='Scale selected objects',
		accelerator=None,
		handler=lambda: handle_scale(app),
		enabled_when=has_selection,
	))

	# lift selected objects to the top of the stack
	registry.register(MenuAction(
		id='object.bring_to_front',
		label_key='Bring to front',
		help_key='Lift selected objects to the top of the stack',
		accelerator=None,
		handler=lambda: handle_bring_to_front(app),
		enabled_when=has_selection,
	))

	# lower selected objects to the bottom of the stack
	registry.register(MenuAction(
		id='object.send_back',
		label_key='Send back',
		help_key='Lower the selected objects to the bottom of the stack',
		accelerator=None,
		handler=lambda: handle_send_back(app),
		enabled_when=has_selection,
	))

	# reverse the ordering of selected objects on the stack
	registry.register(MenuAction(
		id='object.swap_on_stack',
		label_key='Swap on stack',
		help_key=(
			'Reverse the ordering of the selected objects on the stack'
		),
		accelerator=None,
		handler=lambda: handle_swap_on_stack(app),
		enabled_when=has_selection,
	))

	# create a vertical-axis reflection of selected objects
	registry.register(MenuAction(
		id='object.vertical_mirror',
		label_key='Vertical mirror',
		help_key=(
			'Creates a reflection of the selected objects, the reflection'
			' axis is the common vertical axis of all the selected objects'
		),
		accelerator=None,
		handler=lambda: handle_vertical_mirror(app),
		enabled_when=has_selection,
	))

	# create a horizontal-axis reflection of selected objects
	registry.register(MenuAction(
		id='object.horizontal_mirror',
		label_key='Horizontal mirror',
		help_key=(
			'Creates a reflection of the selected objects, the reflection'
			' axis is the common horizontal axis of all the selected objects'
		),
		accelerator=None,
		handler=lambda: handle_horizontal_mirror(app),
		enabled_when=has_selection,
	))

	# configure properties of the selected object
	registry.register(MenuAction(
		id='object.configure',
		label_key='Configure',
		help_key=(
			'Set the properties of the object, such as color,'
			' font size etc.'
		),
		accelerator=None,
		handler=lambda: handle_configure(app),
		enabled_when=has_selection,
	))

	registry.register(MenuAction(
		id='object.edit_rich_text',
		label_key='Edit Rich Text...',
		help_key='Edit authored Text formatting',
		accelerator=None,
		handler=lambda: handle_edit_rich_text(app),
		enabled_when=has_selection,
	))
