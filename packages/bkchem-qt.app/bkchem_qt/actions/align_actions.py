"""Align menu action registrations for BKChem-Qt."""

# local repo modules
import bkchem_qt.geometry
import bkchem_qt.models.document_object
import bkchem_qt.models.molecule_model
import bkchem_qt.undo.commands
import bkchem_qt.actions.top_level_transform_actions
from bkchem_qt.actions.action_registry import MenuAction


#============================================
def _push_top_level_transform(
		app: object, objects_and_offsets: list[tuple[object, float, float]],
		text: str,
		) -> bool:
	"""Commit top-level translation snapshots through the document undo stack."""
	atom_changes = []
	presentation_changes = []
	for object_model, dx, dy in objects_and_offsets:
		if isinstance(
			object_model, bkchem_qt.models.molecule_model.MoleculeModel,
			):
			for atom_model in object_model.atoms:
				before = (atom_model.x, atom_model.y)
				after = (before[0] + dx, before[1] + dy)
				if after != before:
					atom_changes.append((atom_model, before, after))
		elif isinstance(
			object_model, bkchem_qt.models.document_object.PresentationObject,
			):
			before_points = object_model.points
			before_bounds = object_model.bounds
			after_points = [
				(x + dx, y + dy, z) for x, y, z in before_points
			]
			after_bounds = bkchem_qt.geometry.translate_bounds(
				before_bounds, dx, dy,
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
def _align_target(direction: str, bounds: list[tuple[float, float, float, float]]) -> float:
	"""Return the legacy top-level bbox alignment coordinate."""
	if direction == "top":
		return min(bound[1] for bound in bounds)
	if direction == "bottom":
		return max(bound[3] for bound in bounds)
	if direction == "left":
		return min(bound[0] for bound in bounds)
	if direction == "right":
		return max(bound[2] for bound in bounds)
	if direction == "center_h":
		centers = [(bound[0] + bound[2]) / 2.0 for bound in bounds]
		return (min(centers) + max(centers)) / 2.0
	if direction == "center_v":
		centers = [(bound[1] + bound[3]) / 2.0 for bound in bounds]
		return (min(centers) + max(centers)) / 2.0
	raise ValueError(f"Unknown align direction: {direction}")


#============================================
def _align_selection_locally(app: object, direction: str) -> None:
	"""Align legacy-isolated selected top-level objects through local undo."""
	objects = app.document.selected_top_level_objects
	objects_and_bounds = [
		(object_model, bkchem_qt.geometry.top_level_bounds(object_model))
		for object_model in objects
	]
	objects_and_bounds = [
		(object_model, bounds) for object_model, bounds in objects_and_bounds
		if bounds is not None
	]
	if len(objects_and_bounds) < 2:
		app.statusBar().showMessage(
			"Select at least 2 objects to align", 3000,
		)
		return
	try:
		target = _align_target(
			direction, [bounds for _object_model, bounds in objects_and_bounds],
		)
	except ValueError:
		app.statusBar().showMessage(f"Unknown align direction: {direction}", 3000)
		return
	offsets = []
	for object_model, bounds in objects_and_bounds:
		left, top, right, bottom = bounds
		dx = 0.0
		dy = 0.0
		if direction == "top":
			dy = target - top
		elif direction == "bottom":
			dy = target - bottom
		elif direction == "left":
			dx = target - left
		elif direction == "right":
			dx = target - right
		elif direction == "center_h":
			dx = target - (left + right) / 2.0
		elif direction == "center_v":
			dy = target - (top + bottom) / 2.0
		offsets.append((object_model, dx, dy))
	if not _push_top_level_transform(app, offsets, f"Align {direction}"):
		app.statusBar().showMessage("Items already aligned", 3000)
		return
	app.statusBar().showMessage(f"Aligned {direction}", 2000)


#============================================
def _align_selection(app: object, direction: str) -> None:
	"""Route alignment through backend authority or isolated local undo."""
	mode_by_direction = {
		"top": "align-top",
		"bottom": "align-bottom",
		"left": "align-left",
		"right": "align-right",
		"center_h": "align-center-x",
		"center_v": "align-center-y",
	}
	mode = mode_by_direction.get(direction)
	if mode is None:
		app.statusBar().showMessage(f"Unknown align direction: {direction}", 3000)
		return
	session = bkchem_qt.actions.top_level_transform_actions.active_transform_session(app)
	if session is not None and session.legacy_isolated:
		_align_selection_locally(app, direction)
		return
	bkchem_qt.actions.top_level_transform_actions.submit_backend_transform(app, mode)


#============================================
def register_align_actions(registry: object, app: object) -> None:
	"""Register all Align menu actions."""
	def has_selection() -> bool:
		"""Return whether any document-backed item is selected."""
		return app.document is not None and app.document.has_selection

	for action_id, label, help_key, direction in (
		("align.top", "Top", "Align the tops of selected objects", "top"),
		("align.bottom", "Bottom", "Align the bottoms of selected objects", "bottom"),
		("align.left", "Left", "Align the left sides of selected objects", "left"),
		("align.right", "Right", "Align the right sides of selected objects", "right"),
		("align.center_h", "Center horizontally", "Align the horizontal centers of selected objects", "center_h"),
		("align.center_v", "Center vertically", "Align the vertical centers of selected objects", "center_v"),
	):
		registry.register(MenuAction(
			id=action_id,
			label_key=label,
			help_key=help_key,
			accelerator=None,
			handler=lambda direction=direction: _align_selection(app, direction),
			enabled_when=has_selection,
		))
