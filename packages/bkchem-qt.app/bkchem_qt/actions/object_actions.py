"""Object menu action registrations for BKChem-Qt."""

# local repo modules
from bkchem_qt.actions.action_registry import MenuAction
import bkchem_qt.actions.property_editing
import bkchem_qt.canvas.document_projection
import bkchem_qt.geometry
import bkchem_qt.models.document_object
import bkchem_qt.models.document_session
import bkchem_qt.models.molecule_model
import bkchem_qt.undo.commands

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
		app: object, objects: list, origin: tuple[float, float],
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
	app.document.undo_stack.push(
		bkchem_qt.undo.commands.TransformGeometryCommand(
			atom_changes, presentation_changes, text,
		),
	)
	return True


#============================================
def handle_vertical_mirror(app: object) -> None:
	"""Reflect selected top levels across their aggregate vertical center."""
	objects = app.document.selected_top_level_objects
	bounds = _selection_bounds(objects)
	if bounds is None:
		app.statusBar().showMessage(
			"Select objects to mirror", 3000
		)
		return
	left, top, right, bottom = bounds
	if _push_affine_transform(
			app, objects, ((left + right) / 2.0, (top + bottom) / 2.0),
			-1.0, 1.0, "Vertical Mirror",
		):
		app.statusBar().showMessage("Vertical mirror applied", 2000)


#============================================
def handle_horizontal_mirror(app: object) -> None:
	"""Reflect selected top levels across their aggregate horizontal center."""
	objects = app.document.selected_top_level_objects
	bounds = _selection_bounds(objects)
	if bounds is None:
		app.statusBar().showMessage(
			"Select objects to mirror", 3000
		)
		return
	left, top, right, bottom = bounds
	if _push_affine_transform(
			app, objects, ((left + right) / 2.0, (top + bottom) / 2.0),
			1.0, -1.0, "Horizontal Mirror",
		):
		app.statusBar().showMessage("Horizontal mirror applied", 2000)


#============================================
def handle_scale(app: object) -> None:
	"""Scale selected top levels around their aggregate bounding-box center.

	The dialog retains its existing independent X/Y scale choices.  Its pivot is
	the center of the selected document objects' aggregate persistent bounds.
	"""
	objects = app.document.selected_top_level_objects
	bounds = _selection_bounds(objects)
	if bounds is None:
		app.statusBar().showMessage(
			"Select objects to scale", 3000
		)
		return
	# show scale dialog
	import bkchem_qt.dialogs.scale_dialog
	result = bkchem_qt.dialogs.scale_dialog.ScaleDialog.get_scale_factors(
		app
	)
	if result is None:
		return
	scale_x, scale_y = result
	# avoid no-op scaling
	if scale_x == 1.0 and scale_y == 1.0:
		return
	left, top, right, bottom = bounds
	if _push_affine_transform(
			app, objects, ((left + right) / 2.0, (top + bottom) / 2.0),
		scale_x, scale_y, "Scale",
		):
		app.statusBar().showMessage("Scale applied", 2000)


#============================================
def handle_configure(app: object) -> None:
	"""Open the properties dialog for a single selected atom or bond.

	If exactly one atom is selected, opens AtomDialog. If exactly
	one bond is selected, opens BondDialog. Otherwise shows a
	status message explaining the selection requirement.

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
	app.statusBar().showMessage(
		"Select a single atom or bond to configure", 3000
	)


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
