"""Edit mode for selecting, moving, and deleting items."""

# Standard Library
import importlib
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.document_projection
import bkchem_qt.canvas.items.mark_item
import bkchem_qt.canvas.graphics_retirement
from bkchem_qt.canvas.items import render_ops_painter
import bkchem_qt.undo.commands
import bkchem_qt.actions.context_menu
import bkchem_qt.actions.property_editing
import bkchem_qt.modes.edit_item_interaction
import bkchem_qt.models.bracket_pair_selection

# minimum drag distance in pixels before a move begins
_DRAG_THRESHOLD = 3.0
# nudge distance for arrow key movement
_NUDGE_DISTANCE = 2.0


#============================================
class EditMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for selecting and manipulating existing items.

	Supports click-to-select, shift-click for multi-select, rubber band
	box selection, drag-to-move selected items, and keyboard shortcuts
	for deletion, nudging, and clipboard operations.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(
			self, view: object,
			parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize the edit mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Edit"
		self._cursor = PySide6.QtCore.Qt.CursorShape.ArrowCursor
		# drag state
		self._dragging = False
		self._drag_start = None
		self._drag_last = None
		self._drag_anchor_item = None
		self._drag_anchor_start = None
		self._drag_atom_start_positions = {}
		self._drag_presentation_start_geometry = {}
		# rubber band selection rectangle
		self._rubber_band = None
		self._rubber_band_scene = None
		self._rubber_band_origin = None
		# items being dragged
		self._moved_items = []
		self._persistent_operation = None
		self._atom_translate_operation = None
		self._atom_translate_authority = None
		self._presentation_translate_operation = None
		self._presentation_translate_context = None
		self._selection_translate_operation = None
		self._selection_translate_context = None
		self._top_level_delete_context = None
		self._structure_delete_context = None
		self._atom_mark_delete_context = None
		self._drag_presentation_authority = "local"
		self._drag_presentation_operation = None
		self._drag_presentation_revision = None
		self._drag_presentation_state = "none"
		self._drag_selection_authority = "local"
		self._drag_selection_operation = None
		self._drag_selection_revision = None
		self._drag_selection_state = "none"

	#============================================
	def set_persistent_operation(self, operation: object | None) -> None:
		"""Install the session-owned plain persistent-operation callback."""
		self._persistent_operation = operation if callable(operation) else None

	#============================================
	def set_atom_translate_operation(self, operation: object | None) -> None:
		"""Install the session-owned direct-atom translation callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Atom translation operation must be callable")
		self._atom_translate_operation = operation

	#============================================
	def set_atom_translate_authority(self, authority: object | None) -> None:
		"""Install the frontend-only drag-authority query for this session."""
		if authority is not None and not callable(authority):
			raise TypeError("Atom translation authority must be callable")
		self._atom_translate_authority = authority

	#============================================
	def set_presentation_translate_operation(self, operation: object | None) -> None:
		"""Install the session-owned top-level translation callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Presentation translation operation must be callable")
		self._presentation_translate_operation = operation

	#============================================
	def set_presentation_translate_context(self, context: object | None) -> None:
		"""Install the plain authority/revision query for presentation drags."""
		if context is not None and not callable(context):
			raise TypeError("Presentation translation context must be callable")
		self._presentation_translate_context = context

	#============================================
	def set_selection_translate_operation(self, operation: object | None) -> None:
		"""Install the session-owned mixed-selection translation callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Selection translation operation must be callable")
		self._selection_translate_operation = operation

	#============================================
	def set_selection_translate_context(self, context: object | None) -> None:
		"""Install the plain authority/revision query for mixed selection drags."""
		if context is not None and not callable(context):
			raise TypeError("Selection translation context must be callable")
		self._selection_translate_context = context

	#============================================
	def set_top_level_delete_context(self, context: object | None) -> None:
		"""Install the plain authority/revision query for complete-root Delete."""
		if context is not None and not callable(context):
			raise TypeError("Top-level Delete context must be callable")
		self._top_level_delete_context = context

	#============================================
	def set_structure_delete_context(self, context: object | None) -> None:
		"""Install the plain authority/revision query for partial structure Delete."""
		if context is not None and not callable(context):
			raise TypeError("Structure Delete context must be callable")
		self._structure_delete_context = context

	#============================================
	def set_atom_mark_delete_context(self, context: object | None) -> None:
		"""Install the plain authority/revision query for selected-mark Delete."""
		if context is not None and not callable(context):
			raise TypeError("Atom-mark Delete context must be callable")
		self._atom_mark_delete_context = context

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return edit mode interaction hint for the status bar.

		Returns:
			A short description of available edit interactions.
		"""
		return "Click to select | Drag to move | Shift-click for multi-select"

	# ------------------------------------------------------------------
	# Lifecycle
	# ------------------------------------------------------------------

	#============================================
	def deactivate(self) -> None:
		"""Clean up any drag or rubber band state when leaving edit mode."""
		self._restore_drag_preview()
		self._reset_drag_state()
		super().deactivate()

	# ------------------------------------------------------------------
	# Mouse event handlers
	# ------------------------------------------------------------------

	#============================================
	def mouse_press3(
			self, scene_pos: PySide6.QtCore.QPointF, event: object,
			) -> None:
		"""Handle right-click to show context menu.

		Dispatched via view -> mode_manager -> mouse_press3 for
		Tk parity with mode.mouse_down3().

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		screen_pos = event.globalPosition().toPoint()
		bkchem_qt.actions.context_menu.show_context_menu(
			self._view, scene_pos, screen_pos,
		)

	#============================================
	def mouse_press(
			self, scene_pos: PySide6.QtCore.QPointF, event: object,
			) -> None:
		"""Handle mouse press for selection and drag initiation.

		Click on an item selects it (shift-click adds to selection).
		Click on empty space clears selection and starts rubber band.
		Click on an already-selected item starts a drag operation.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		item = self._item_at(scene_pos)
		shift_held = bool(event.modifiers() & PySide6.QtCore.Qt.KeyboardModifier.ShiftModifier)
		scene = self._env.scene
		if scene is None:
			return
		if item is not None:
			# clicking on an item
			if item.isSelected() and not shift_held:
				# start dragging the already-selected items
				self._dragging = True
				self._drag_start = scene_pos
				self._drag_last = scene_pos
				self._moved_items = scene.selectedItems()
				self._capture_drag_start_state(clicked_item=item)
			elif shift_held:
				# toggle selection on shift-click
				if not bkchem_qt.models.bracket_pair_selection.toggle_selection(
						self._env.document, item,
					):
					item.setSelected(not item.isSelected())
			else:
				# clear selection and select this item
				scene.clearSelection()
				item.setSelected(True)
				bkchem_qt.models.bracket_pair_selection.expand_selection(self._env.document)
				# prepare for potential drag
				self._dragging = True
				self._drag_start = scene_pos
				self._drag_last = scene_pos
				# Pair selection expands before a drag begins.  Capture the final
				# selection so one gesture submits both durable bracket roots.
				self._moved_items = scene.selectedItems()
				self._capture_drag_start_state(clicked_item=item)
		else:
			# click on empty space: clear selection and start rubber band
			if not shift_held:
				scene.clearSelection()
			self._rubber_band_origin = scene_pos
			self.status_message.emit("Drag to select area")

	#============================================
	def mouse_move(
			self, scene_pos: PySide6.QtCore.QPointF, event: object,
			) -> None:
		"""Handle mouse move for dragging items or updating rubber band.

		Drags selected items by the delta from the last move position.
		If rubber-banding, updates the selection rectangle.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._dragging and self._drag_last is not None:
			scene = self._env.scene
			if scene is None:
				return
			# compute delta from last tracked position
			dx = scene_pos.x() - self._drag_last.x()
			dy = scene_pos.y() - self._drag_last.y()
			# axis-lock: Ctrl constrains to vertical, Shift to horizontal
			modifiers = (
				event.modifiers() if event is not None
				else PySide6.QtCore.Qt.KeyboardModifier.NoModifier
			)
			if modifiers & PySide6.QtCore.Qt.KeyboardModifier.ControlModifier:
				dx = 0
			if modifiers & PySide6.QtCore.Qt.KeyboardModifier.ShiftModifier:
				dy = 0
			# only start moving after exceeding threshold
			total_dx = dx
			total_dy = dy
			if self._drag_start is not None:
				total_dx = scene_pos.x() - self._drag_start.x()
				total_dy = scene_pos.y() - self._drag_start.y()
				if modifiers & PySide6.QtCore.Qt.KeyboardModifier.ControlModifier:
					total_dx = 0
				if modifiers & PySide6.QtCore.Qt.KeyboardModifier.ShiftModifier:
					total_dy = 0
				distance = (total_dx ** 2 + total_dy ** 2) ** 0.5
				if distance < _DRAG_THRESHOLD:
					return
			# Tk parity: move by snapped anchor delta when grid snap is enabled.
			move_dx = dx
			move_dy = dy
			if (
				getattr(scene, "grid_snap_enabled", True)
				and self._drag_anchor_item is not None
				and self._drag_anchor_start is not None
				and hasattr(scene, "snap_to_grid")
			):
				target_x = self._drag_anchor_start[0] + total_dx
				target_y = self._drag_anchor_start[1] + total_dy
				snap_x, snap_y = scene.snap_to_grid(target_x, target_y)
				anchor_model = self._drag_anchor_item.atom_model
				move_dx = snap_x - anchor_model.x
				move_dy = snap_y - anchor_model.y
			# move each selected item
			for item in self._moved_items:
				if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
					model = item.atom_model
					model.x = model.x + move_dx
					model.y = model.y + move_dy
				elif self._is_presentation_item(item):
					self._translate_presentation_model(
						item.document_object_model, move_dx, move_dy,
					)
			self._drag_last = scene_pos
		elif self._rubber_band_origin is not None:
			# update or create the rubber band rectangle
			self._update_rubber_band(scene_pos)

	#============================================
	def mouse_release(
			self, scene_pos: PySide6.QtCore.QPointF, event: object,
			) -> None:
		"""Handle mouse release to finalize moves or rubber band selection.

		Synchronized atom-only, presentation-only, and mixed drags each restore
		their responsive preview before submitting one backend-owned request.
		Explicitly isolated sessions retain their established local undo behavior.
		If rubber-banding, selects items within the rectangle.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._env.scene
		if self._dragging and self._drag_start is not None and scene is not None:
			if self._drag_selection_state != "none":
				authority = self._drag_selection_authority
				if authority != "local":
					# This helper returns only immutable IDs and scalar geometry.  Its
					# graphics wrappers go out of scope before reset and the synchronous
					# session callback can retire and rebuild the projection.
					selection_drag = self._mixed_selection_drag_plan()
					operation = self._drag_selection_operation
					revision = self._drag_selection_revision
					self._restore_drag_preview()
					self._reset_drag_state()
					if authority == "backend" and selection_drag is not None:
						atom_targets, root_keys, delta = selection_drag
						self._submit_selection_drag(
							operation, revision, atom_targets, root_keys, delta,
						)
					elif authority == "backend":
						self.status_message.emit(
							"Move unavailable: mixed selection lacks durable current identity",
						)
					else:
						self.status_message.emit(
							"Move unavailable until the document projection recovers",
						)
					return
			# Local completion may retain wrappers in undo commands.  Build those
			# wrapper-bearing lists only after the synchronized mixed branch has
			# returned or explicitly selected local authority.
			items_and_offsets = self._atom_drag_offsets()
			presentation_changes = self._presentation_drag_changes()
			presentation_drag = self._presentation_only_drag_request(presentation_changes)
			if self._drag_presentation_state != "none" and presentation_changes:
				authority = self._drag_presentation_authority
				if authority != "local":
					operation = self._drag_presentation_operation
					revision = self._drag_presentation_revision
					self._restore_drag_preview()
					self._reset_drag_state()
					if authority == "backend" and presentation_drag is not None:
						root_keys, delta = presentation_drag
						self._submit_presentation_drag(operation, revision, root_keys, delta)
					elif authority == "backend":
						self.status_message.emit(
							"Move unavailable: selected presentation lacks durable current identity",
						)
					else:
						self.status_message.emit(
							"Move unavailable until the document projection recovers",
						)
					return
			atom_only = self._is_atom_only_drag(presentation_changes)
			atom_drag = self._atom_only_drag_request(items_and_offsets, presentation_changes)
			if atom_only and items_and_offsets:
				authority = self._drag_authority()
				if authority != "local":
					# The backend owns an atom-only completion.  Restore the complete
					# preview before a callback can replace its live Qt projection.
					self._restore_drag_preview()
					self._reset_drag_state()
					if authority == "backend" and atom_drag is not None:
						targets, delta = atom_drag
						self._submit_atom_drag(targets, delta)
					elif authority == "backend":
						self.status_message.emit("Move unavailable: selected atom lacks durable identity")
					else:
						self.status_message.emit("Move unavailable until the document projection recovers")
					return
			if items_and_offsets or presentation_changes:
				undo_stack = self._env.undo_stack
				if undo_stack is not None:
					# Keep a mixed molecule/artwork drag as one history action.
					undo_stack.beginMacro("Move Selected")
					if items_and_offsets:
						undo_stack.push(bkchem_qt.undo.commands.MoveAtomsCommand(
							items_and_offsets,
						))
					if presentation_changes:
						undo_stack.push(
							bkchem_qt.undo.commands.MovePresentationObjectsCommand(
								presentation_changes,
							),
						)
					undo_stack.endMacro()
		elif self._rubber_band_origin is not None and scene is not None:
			# select items within the rubber band rectangle
			self._finalize_rubber_band(scene_pos)
		self._reset_drag_state()

	#============================================
	def mouse_double_click(
			self, scene_pos: PySide6.QtCore.QPointF, event: object,
			) -> None:
		"""Route an eligible projected item to its detached property editor."""
		item = self._item_at(scene_pos)
		if item is None:
			return
		bkchem_qt.modes.edit_item_interaction.open_item_editor(
			item, self._edit_atom_properties, self._edit_bond_properties,
			self._env.scene, self._env.window,
		)

	# ------------------------------------------------------------------
	# Keyboard event handlers
	# ------------------------------------------------------------------

	#============================================
	def key_press(self, event: object) -> None:
		"""Handle key presses for deletion, nudging, and clipboard ops.

		Supported keys:
		- Delete/Backspace: delete selected items
		- Arrow keys: nudge selected items
		- Ctrl+A: select all
		- Escape: clear selection

		Args:
			event: The QKeyEvent.
		"""
		key = event.key()
		modifiers = event.modifiers()
		ctrl = bool(modifiers & PySide6.QtCore.Qt.KeyboardModifier.ControlModifier)
		# delete selected items
		if key in (PySide6.QtCore.Qt.Key.Key_Delete, PySide6.QtCore.Qt.Key.Key_Backspace):
			self._delete_selected()
			return
		# select all
		if ctrl and key == PySide6.QtCore.Qt.Key.Key_A:
			self._select_all()
			return
		# escape clears selection
		if key == PySide6.QtCore.Qt.Key.Key_Escape:
			if self._dragging:
				self._restore_drag_preview()
				self._reset_drag_state()
				self.status_message.emit("Move cancelled")
				return
			scene = self._env.scene
			if scene is not None:
				scene.clearSelection()
			return
		# arrow key nudging
		nudge_map = {
			PySide6.QtCore.Qt.Key.Key_Left: (-_NUDGE_DISTANCE, 0),
			PySide6.QtCore.Qt.Key.Key_Right: (_NUDGE_DISTANCE, 0),
			PySide6.QtCore.Qt.Key.Key_Up: (0, -_NUDGE_DISTANCE),
			PySide6.QtCore.Qt.Key.Key_Down: (0, _NUDGE_DISTANCE),
		}
		if key in nudge_map:
			dx, dy = nudge_map[key]
			self._nudge_selected(dx, dy)
			return

	# ------------------------------------------------------------------
	# Action helpers
	# ------------------------------------------------------------------

	#============================================
	def _capture_drag_start_state(
			self, clicked_item: object | None = None,
			) -> None:
		"""Capture atom start positions and choose a snap anchor.

		Args:
			clicked_item: Item under the cursor when drag starts.
		"""
		self._drag_atom_start_positions = {}
		self._drag_presentation_start_geometry = {}
		self._drag_anchor_item = None
		self._drag_anchor_start = None
		self._drag_presentation_authority = "local"
		self._drag_presentation_operation = None
		self._drag_presentation_revision = None
		self._drag_presentation_state = "none"
		self._drag_selection_authority = "local"
		self._drag_selection_operation = None
		self._drag_selection_revision = None
		self._drag_selection_state = "none"
		for item in self._moved_items:
			if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				if self._is_presentation_item(item):
					model = item.document_object_model
					self._drag_presentation_start_geometry[id(model)] = (
						model, self._presentation_geometry(model),
					)
				continue
			model = item.atom_model
			self._drag_atom_start_positions[id(item)] = (model.x, model.y)
			if self._drag_anchor_item is None:
				self._drag_anchor_item = item
		if (
			isinstance(clicked_item, bkchem_qt.canvas.items.atom_item.AtomItem)
			and clicked_item in self._moved_items
		):
			self._drag_anchor_item = clicked_item
		if self._drag_anchor_item is not None:
			anchor_model = self._drag_anchor_item.atom_model
			self._drag_anchor_start = (anchor_model.x, anchor_model.y)
		self._capture_presentation_drag_context()
		self._capture_selection_translate_context()

	#============================================
	def _capture_selection_translate_context(self) -> None:
		"""Freeze one mixed drag's origin capability before its preview starts."""
		items = tuple(self._moved_items)
		if not items:
			return
		has_atom = any(
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			for item in items
		)
		# A selected presentation lookalike must enter the mixed eligibility gate
		# too.  Otherwise the atom-only route could silently commit while a
		# foreign graphics item remains part of the user's visible selection.
		has_presentation = any(
			getattr(item, "document_object_model", None) is not None
			for item in items
		)
		if not has_atom or not has_presentation:
			return
		document = self._env.document
		if (
			document is None
			or bkchem_qt.canvas.document_projection.selection_translate_targets_for_items(
				document, items,
			) is None
		):
			self._drag_selection_authority = "unavailable"
			self._drag_selection_state = "ineligible"
			return
		self._drag_selection_state = "eligible"
		if self._selection_translate_context is None:
			return
		context = self._selection_translate_context()
		if (
			type(context) is not tuple or len(context) != 2
			or context[0] not in ("backend", "local", "unavailable")
		):
			raise ValueError("Selection translation context returned an unknown state")
		authority, revision = context
		if authority == "backend":
			if type(revision) is not int or self._selection_translate_operation is None:
				raise ValueError("Backend selection translation requires a captured revision")
			self._drag_selection_operation = self._selection_translate_operation
			self._drag_selection_revision = revision
		elif revision is not None:
			raise ValueError("Non-backend selection translation must not capture a revision")
		self._drag_selection_authority = authority

	#============================================
	def _capture_presentation_drag_context(self) -> None:
		"""Freeze one presentation drag's authority, revision, and callback."""
		if not self._moved_items or not all(
			self._is_presentation_item(item) for item in self._moved_items
		):
			return
		document = self._env.document
		if document is None or not all(
			self._is_current_supported_presentation_item(document, item)
			for item in self._moved_items
		):
			self._drag_presentation_authority = "unavailable"
			self._drag_presentation_state = "ineligible"
			return
		self._drag_presentation_state = "eligible"
		if self._presentation_translate_context is None:
			return
		context = self._presentation_translate_context()
		if (
			type(context) is not tuple or len(context) != 2
			or context[0] not in ("backend", "local", "unavailable")
		):
			raise ValueError("Presentation translation context returned an unknown state")
		authority, revision = context
		if authority == "backend":
			if type(revision) is not int or self._presentation_translate_operation is None:
				raise ValueError("Backend presentation translation requires a captured revision")
			self._drag_presentation_operation = self._presentation_translate_operation
			self._drag_presentation_revision = revision
		elif revision is not None:
			raise ValueError("Non-backend presentation translation must not capture a revision")
		self._drag_presentation_authority = authority

	#============================================
	def _is_current_supported_presentation_item(self, document: object, item: object) -> bool:
		"""Return whether one drag item is a durable current presentation binding."""
		model = getattr(item, "document_object_model", None)
		return (
			document.is_current_projection_item(item)
			and getattr(model, "supported", False)
			and getattr(model, "editable", False)
			and model in document.presentation_objects
			and model in document.objects
			and type(getattr(model, "object_id", None)) is str
			and bool(model.object_id)
			and bkchem_qt.canvas.document_projection.is_bound_presentation_projection(item, model)
		)

	#============================================
	def _presentation_only_drag_request(
			self, presentation_changes: list,
			) -> tuple[tuple[tuple[str, str], ...], tuple[float, float]] | None:
		"""Capture a durable presentation-only translation request at release."""
		if self._drag_presentation_state != "eligible" or not presentation_changes:
			return None
		document = self._env.document
		if document is None:
			return None
		items = tuple(self._moved_items)
		root_keys = bkchem_qt.canvas.document_projection.top_level_presentation_keys_for_items(
			document, items,
		)
		if not root_keys:
			return None
		deltas = []
		for _model, before, after in presentation_changes:
			delta = self._presentation_geometry_delta(before, after)
			if delta is None:
				return None
			deltas.append(delta)
		if len(deltas) != len(items):
			return None
		first_delta = deltas[0]
		if any(
			abs(delta[0] - first_delta[0]) >= 1e-6
			or abs(delta[1] - first_delta[1]) >= 1e-6
			for delta in deltas[1:]
		):
			return None
		return root_keys, first_delta

	#============================================
	def _presentation_geometry_delta(
			self, before: tuple, after: tuple,
			) -> tuple[float, float] | None:
		"""Return one exact shared translation when geometry contains no reshape."""
		before_points, before_bounds = before
		after_points, after_bounds = after
		deltas = []
		if len(before_points) != len(after_points):
			return None
		for before_point, after_point in zip(before_points, after_points, strict=True):
			before_x, before_y, before_z = before_point
			after_x, after_y, after_z = after_point
			if before_z != after_z:
				return None
			deltas.append((after_x - before_x, after_y - before_y))
		if before_bounds is None or after_bounds is None:
			if before_bounds != after_bounds:
				return None
		else:
			before_x, before_y, before_width, before_height = before_bounds
			after_x, after_y, after_width, after_height = after_bounds
			if before_width != after_width or before_height != after_height:
				return None
			deltas.append((after_x - before_x, after_y - before_y))
		if not deltas:
			return None
		first_delta = deltas[0]
		if any(
			abs(delta[0] - first_delta[0]) >= 1e-6
			or abs(delta[1] - first_delta[1]) >= 1e-6
			for delta in deltas[1:]
		):
			return None
		return first_delta

	#============================================
	def _atom_only_drag_request(
			self, items_and_offsets: list, presentation_changes: list,
			) -> tuple[tuple[tuple[str, str], ...], tuple[float, float]] | None:
		"""Capture one durable atom-only drag request from the live preview.

		The caller must restore the preview before submitting this result because
		an accepted callback can retire the entire current projection.
		"""
		if presentation_changes or not items_and_offsets:
			return None
		if not self._moved_items or any(
			not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			for item in self._moved_items
		):
			return None
		if len(items_and_offsets) != len(self._moved_items):
			return None
		first_delta = (items_and_offsets[0][1], items_and_offsets[0][2])
		if any(
			abs(dx - first_delta[0]) >= 1e-6 or abs(dy - first_delta[1]) >= 1e-6
			for _item, dx, dy in items_and_offsets[1:]
		):
			return None
		targets = []
		for item, _dx, _dy in items_and_offsets:
			model = item.atom_model
			atom_id = getattr(model, "backend_durable_id", None)
			molecule = getattr(model, "_molecule_model", None)
			molecule_id = getattr(molecule, "mol_id", None)
			if not isinstance(atom_id, str) or not atom_id:
				return None
			if not isinstance(molecule_id, str) or not molecule_id:
				return None
			targets.append((molecule_id, atom_id))
		return tuple(targets), first_delta

	#============================================
	def _atom_drag_offsets(self) -> list:
		"""Return local atom-wrapper offsets after authority routing is settled."""
		items_and_offsets = []
		for item in self._moved_items:
			if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				continue
			start_pos = self._drag_atom_start_positions.get(id(item))
			if start_pos is None:
				continue
			model = item.atom_model
			dx = model.x - start_pos[0]
			dy = model.y - start_pos[1]
			if abs(dx) < 1e-6 and abs(dy) < 1e-6:
				continue
			items_and_offsets.append((item, dx, dy))
		return items_and_offsets

	#============================================
	def _mixed_selection_drag_plan(
			self,
			) -> tuple[
				tuple[tuple[str, str], ...], tuple[tuple[str, str], ...], tuple[float, float],
				] | None:
		"""Return a plain mixed-drag request while all graphics stay frame-local.

		This is deliberately a distinct stack frame: accepted session submission
		can synchronously replace the projection, so its caller must retain only
		durable IDs and scalar deltas after this method returns.
		"""
		if self._drag_selection_state != "eligible":
			return None
		items_and_offsets = self._atom_drag_offsets()
		presentation_changes = self._presentation_drag_changes()
		if not items_and_offsets or not presentation_changes:
			return None
		document = self._env.document
		if document is None:
			return None
		targets = bkchem_qt.canvas.document_projection.selection_translate_targets_for_items(
			document, tuple(self._moved_items),
		)
		if targets is None:
			return None
		atom_targets, presentation_keys = targets
		atom_items = [
			item for item in self._moved_items
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
		]
		if len(items_and_offsets) != len(atom_items):
			return None
		if len(presentation_changes) != len(presentation_keys):
			return None
		deltas = [(dx, dy) for _item, dx, dy in items_and_offsets]
		for _model, before, after in presentation_changes:
			delta = self._presentation_geometry_delta(before, after)
			if delta is None:
				return None
			deltas.append(delta)
		first_delta = deltas[0]
		if not all(math.isfinite(value) for value in first_delta):
			return None
		if any(
			abs(delta[0] - first_delta[0]) >= 1e-6
			or abs(delta[1] - first_delta[1]) >= 1e-6
			or not all(math.isfinite(value) for value in delta)
			for delta in deltas[1:]
		):
			return None
		return atom_targets, presentation_keys, first_delta

	#============================================
	def _is_atom_only_drag(self, presentation_changes: list) -> bool:
		"""Return whether the current drag selection contains only atom projections."""
		return bool(self._moved_items) and not presentation_changes and all(
			isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)
			for item in self._moved_items
		)

	#============================================
	def _drag_authority(self) -> str:
		"""Return the current session's explicit atom-drag authority state."""
		if self._atom_translate_authority is None:
			return "local"
		authority = self._atom_translate_authority()
		if authority in ("backend", "local", "unavailable"):
			return authority
		raise ValueError("Atom translation authority returned an unknown state")

	#============================================
	def _restore_drag_preview(self) -> None:
		"""Restore every transient atom and presentation geometry preview."""
		for item in self._moved_items:
			if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				continue
			start = self._drag_atom_start_positions.get(id(item))
			if start is None:
				continue
			model = item.atom_model
			model.x, model.y = start
		for object_model, geometry in self._drag_presentation_start_geometry.values():
			points, bounds = geometry
			object_model.set_points(points)
			object_model.set_bounds(bounds)

	#============================================
	def _submit_atom_drag(
			self, targets: tuple[tuple[str, str], ...], delta: tuple[float, float],
			) -> None:
		"""Submit a plain captured atom drag through its originating session seam."""
		if self._atom_translate_operation is None:
			self.status_message.emit("Move unavailable for this document")
			return
		outcome = self._atom_translate_operation(targets, delta)
		self.status_message.emit(outcome.message)

	#============================================
	def _submit_presentation_drag(
			self, operation: object, revision: object,
			root_keys: tuple[tuple[str, str], ...], delta: tuple[float, float],
			) -> None:
		"""Submit one captured durable presentation move through its origin seam."""
		if not callable(operation) or type(revision) is not int:
			self.status_message.emit("Move unavailable for this document")
			return
		outcome = operation(revision, "translate", root_keys, delta=delta)
		self.status_message.emit(outcome.message)

	#============================================
	def _submit_selection_drag(
			self, operation: object, revision: object,
			atom_targets: tuple[tuple[str, str], ...],
			presentation_keys: tuple[tuple[str, str], ...], delta: tuple[float, float],
			) -> None:
		"""Submit one frozen mixed drag through its originating session seam."""
		if not callable(operation) or type(revision) is not int:
			self.status_message.emit("Move unavailable for this document")
			return
		outcome = operation(revision, atom_targets, presentation_keys, delta)
		self.status_message.emit(outcome.message)

	#============================================
	def _reset_drag_state(self) -> None:
		"""Drop all transient drag wrappers after local completion or submission."""
		self._dragging = False
		self._drag_start = None
		self._drag_last = None
		self._drag_anchor_item = None
		self._drag_anchor_start = None
		self._drag_atom_start_positions = {}
		self._drag_presentation_start_geometry = {}
		self._drag_presentation_authority = "local"
		self._drag_presentation_operation = None
		self._drag_presentation_revision = None
		self._drag_presentation_state = "none"
		self._drag_selection_authority = "local"
		self._drag_selection_operation = None
		self._drag_selection_revision = None
		self._drag_selection_state = "none"
		self._moved_items = []
		self._rubber_band_origin = None
		self._cancel_rubber_band()

	#============================================
	def _delete_selected(self) -> None:
		"""Delete all selected items with chemistry-aware cleanup.

		Port of Tk paper_selection.delete_selected(). Handles:
		- Bonds: remove from graph, then remove orphan atoms (atoms
		  with no remaining bonds and not themselves selected).
		- Atoms: remove from molecule with connected bond cleanup.
		- Molecule integrity: after deletion, check if the parent
		  molecule has become disconnected and split into separate
		  MoleculeModel instances.

		All deletions are grouped in a single undo macro.
		"""
		scene = self._env.scene
		if scene is None:
			return
		selected = scene.selectedItems()
		if not selected:
			return
		if self._submit_top_level_delete(selected):
			return
		if self._submit_atom_mark_delete(selected):
			return
		if self._submit_structure_delete(selected):
			return
		undo_stack = self._env.undo_stack
		if undo_stack is None:
			return
		# Separate chemistry items from document-owned presentation artwork.
		atom_items = []
		bond_items = []
		presentation_items = []
		for item in selected:
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				atom_items.append(item)
			elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				bond_items.append(item)
			elif self._is_presentation_item(item):
				presentation_items.append(item)
		if not atom_items and not bond_items and not presentation_items:
			return
		# collect atom model ids for quick lookup
		selected_atom_ids = set(id(ai.atom_model) for ai in atom_items)
		# use a macro to group all deletions
		undo_stack.beginMacro("Delete Selected")
		for item in presentation_items:
			undo_stack.push(
				bkchem_qt.undo.commands.RemovePresentationObjectCommand(
					self._env.document, scene, item.document_object_model, item,
				),
			)
		# remove bonds first
		for bond_item in bond_items:
			mol_model = self._env.find_molecule_for_bond(bond_item.bond_model)
			if mol_model is not None:
				cmd = bkchem_qt.undo.commands.RemoveBondCommand(
					scene, mol_model, bond_item.bond_model, bond_item,
				)
				undo_stack.push(cmd)
		# remove atoms (which also removes their connected bonds)
		for atom_item in atom_items:
			mol_model = self._env.find_molecule_for_atom(atom_item.atom_model)
			if mol_model is not None:
				# find connected bond items not already removed
				connected_bonds = self._env.find_connected_bond_items(atom_item.atom_model)
				cmd = bkchem_qt.undo.commands.RemoveAtomCommand(
					scene, mol_model, atom_item.atom_model,
					atom_item, connected_bonds,
				)
				undo_stack.push(cmd)
		# orphan cleanup: after bond deletion, remove atoms that have
		# no remaining bonds and were not explicitly selected
		orphan_atoms = self._find_orphan_atoms_after_bond_delete(
			bond_items, selected_atom_ids,
		)
		for orphan_item in orphan_atoms:
			mol_model = self._env.find_molecule_for_atom(orphan_item.atom_model)
			if mol_model is not None:
				connected_bonds = self._env.find_connected_bond_items(orphan_item.atom_model)
				cmd = bkchem_qt.undo.commands.RemoveAtomCommand(
					scene, mol_model, orphan_item.atom_model,
					orphan_item, connected_bonds,
				)
				undo_stack.push(cmd)
		undo_stack.endMacro()
		self.status_message.emit("Deleted selected items")

	#============================================
	def _submit_top_level_delete(self, selected: list) -> bool:
		"""Route one complete direct-root selection through its proven authority.

		Partial atom/bond selections intentionally return ``False`` so their
		legacy structural-delete grammar continues to own the interaction.
		"""
		scene = self._env.scene
		document = self._env.document
		if scene is None or document is None:
			return False
		allowed_presentation = {
			"arrow", "plus", "text", "rect", "square", "oval", "circle",
			"polygon", "polyline",
		}
		selected_set = set(selected)
		for item in selected:
			if not document.is_current_projection_item(item):
				return False
			if isinstance(item, (
				bkchem_qt.canvas.items.atom_item.AtomItem,
				bkchem_qt.canvas.items.bond_item.BondItem,
			)):
				continue
			if not self._is_presentation_item(item):
				return False
			model = item.document_object_model
			if (
				not getattr(model, "editable", False)
				or not getattr(model, "object_id", "")
				or getattr(model, "kind", "") not in allowed_presentation
			):
				return False
		root_ids = []
		target_keys = set()
		for object_model in document.selected_top_level_objects:
			molecule_id = getattr(object_model, "mol_id", "")
			if molecule_id:
				primary_items = [
					item for item in scene.items()
					if isinstance(item, (
						bkchem_qt.canvas.items.atom_item.AtomItem,
						bkchem_qt.canvas.items.bond_item.BondItem,
					)) and document.molecule_for_graphics_item(item) is object_model
				]
				if not primary_items or any(item not in selected_set for item in primary_items):
					return False
				root_ids.append(molecule_id)
				target_keys.add(("molecule", molecule_id))
				continue
			object_id = getattr(object_model, "object_id", "")
			if (
				not getattr(object_model, "editable", False)
				or not object_id
				or getattr(object_model, "kind", "") not in allowed_presentation
			):
				return False
			root_ids.append(object_id)
			target_keys.add(("presentation", object_id))
		if not root_ids:
			return False
		# A selection may include every molecule primary item plus a mark.  Marks
		# are view-only children for this operation and need no durable root key.
		covered = set()
		for item in selected:
			if self._is_presentation_item(item):
				covered.add(item)
			elif isinstance(item, (
				bkchem_qt.canvas.items.atom_item.AtomItem,
				bkchem_qt.canvas.items.bond_item.BondItem,
			)):
				covered.add(item)
		if covered != selected_set:
			return False
		context = self._top_level_delete_context
		if context is None:
			return False
		authority_and_revision = context()
		if (
			type(authority_and_revision) is not tuple
			or len(authority_and_revision) != 2
			or authority_and_revision[0] not in ("backend", "local", "unavailable")
		):
			raise ValueError("Top-level Delete context returned an unknown state")
		authority, expected_revision = authority_and_revision
		if authority == "local":
			return False
		if authority == "unavailable":
			if expected_revision is not None:
				raise ValueError("Unavailable top-level Delete must not capture a revision")
			self.status_message.emit("Delete unavailable for this document")
			return True
		if type(expected_revision) is not int or self._persistent_operation is None:
			raise ValueError("Backend top-level Delete requires a captured revision")
		document_session = importlib.import_module("bkchem_qt.models.document_session")
		request = document_session.PersistentOperationRequest(
			"top-level.delete", "Delete",
			(("expected_revision", expected_revision), ("root_ids", tuple(root_ids))),
			frozenset(target_keys),
		)
		outcome = self._persistent_operation(request)
		# A complete supported selection has crossed the authoritative operation
		# boundary. Its accepted, stale, or rejected result is final for this
		# Delete gesture; the local structural grammar applies only to a local
		# authority state or a selection that failed the eligibility gate above.
		self.status_message.emit(outcome.message)
		return True

	#============================================
	def _submit_atom_mark_delete(self, selected: list) -> bool:
		"""Delete one selected current atom mark through backend authority only."""
		has_mark = any(
			isinstance(item, bkchem_qt.canvas.items.mark_item.MarkItem)
			for item in selected
		)
		if not has_mark:
			return False
		context = self._atom_mark_delete_context
		if context is None:
			return False
		authority_and_revision = context()
		if (
			type(authority_and_revision) is not tuple
			or len(authority_and_revision) != 2
			or authority_and_revision[0] not in ("backend", "local", "unavailable")
			):
			raise ValueError("Atom-mark Delete context returned an unknown state")
		authority, expected_revision = authority_and_revision
		if authority == "local":
			return False
		if authority == "unavailable":
			if expected_revision is not None:
				raise ValueError("Unavailable atom-mark Delete must not capture a revision")
			self.status_message.emit("Delete unavailable for this document")
			return True
		document = self._env.document
		if document is None or type(expected_revision) is not int or self._persistent_operation is None:
			return True
		items = tuple(selected)
		target = bkchem_qt.canvas.document_projection.atom_mark_delete_target_for_items(
			document, items,
		)
		# A synchronized mark selection is never allowed to fall into Qt undo.
		# Keep only plain durable intent before projection can retire its wrappers.
		selected.clear()
		del items
		if target is None:
			self.status_message.emit("Delete requires one current supported atom mark")
			return True
		molecule_id, atom_id, mark_type, matching_mark_index = target
		del target
		del document
		document_session = importlib.import_module("bkchem_qt.models.document_session")
		request = document_session.build_atom_mark_request(
			expected_revision, molecule_id, atom_id, "remove", mark_type,
			matching_mark_index,
		)
		outcome = self._persistent_operation(request)
		self.status_message.emit(outcome.message)
		return True

	#============================================
	def _submit_structure_delete(self, selected: list) -> bool:
		"""Route one partial atom/bond selection through its explicit authority."""
		context = self._structure_delete_context
		if context is None:
			return False
		authority_and_revision = context()
		if (
			type(authority_and_revision) is not tuple
			or len(authority_and_revision) != 2
			or authority_and_revision[0] not in ("backend", "local", "unavailable")
		):
			raise ValueError("Structure Delete context returned an unknown state")
		authority, expected_revision = authority_and_revision
		if authority == "local":
			return False
		if authority == "unavailable":
			if expected_revision is not None:
				raise ValueError("Unavailable Structure Delete must not capture a revision")
			self.status_message.emit("Delete unavailable for this document")
			return True
		if type(expected_revision) is not int or self._persistent_operation is None:
			self.status_message.emit("Delete unavailable for this document")
			return True
		document = self._env.document
		if document is None:
			self.status_message.emit("Delete unavailable for this document")
			return True
		items = tuple(selected)
		targets = (
			bkchem_qt.canvas.document_projection.structure_delete_targets_for_items(
				document, items,
			)
		)
		del items
		if targets is None:
			self.status_message.emit(
				"Delete unavailable: select durable atoms or bonds from one molecule",
			)
			return True
		molecule_id, atom_ids, bond_ids = targets
		document_session = importlib.import_module("bkchem_qt.models.document_session")
		request = document_session.build_structure_delete_request(
			expected_revision, molecule_id, atom_ids, bond_ids,
		)
		# Accepted submission may synchronously retire every selected wrapper.
		# Release this frame's list before crossing that replacement boundary.
		selected.clear()
		del targets
		outcome = self._persistent_operation(request)
		self.status_message.emit(outcome.message)
		return True

	#============================================
	def _find_orphan_atoms_after_bond_delete(
			self, deleted_bond_items: list, selected_atom_ids: set,
			) -> list:
		"""Find atoms that became orphans after bond deletion.

		An orphan is an atom that: (1) was an endpoint of a deleted bond,
		(2) was not itself selected for deletion, and (3) has no remaining
		bonds in the scene after the deletion.

		Args:
			deleted_bond_items: List of BondItems that were deleted.
			selected_atom_ids: Set of id() values for explicitly selected atoms.

		Returns:
			List of AtomItem instances that are orphaned.
		"""
		scene = self._env.scene
		if scene is None:
			return []
		# collect candidate atoms from deleted bonds
		candidates = {}
		for bond_item in deleted_bond_items:
			bm = bond_item.bond_model
			for atom_model in (bm.atom1, bm.atom2):
				if atom_model is None:
					continue
				if id(atom_model) in selected_atom_ids:
					continue
				candidates[id(atom_model)] = atom_model
		if not candidates:
			return []
		# find AtomItems for candidates and check if they have remaining bonds
		orphans = []
		for item in scene.items():
			if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				continue
			if id(item.atom_model) not in candidates:
				continue
			# check if this atom has any remaining bonds in the scene
			has_bonds = False
			for other_item in scene.items():
				if not isinstance(other_item, bkchem_qt.canvas.items.bond_item.BondItem):
					continue
				bm = other_item.bond_model
				if bm.atom1 is item.atom_model or bm.atom2 is item.atom_model:
					has_bonds = True
					break
			if not has_bonds:
				orphans.append(item)
		return orphans

	#============================================
	def _select_all(self) -> None:
		"""Select all interactive items in the scene."""
		scene = self._env.scene
		if scene is None:
			return
		for item in scene.items():
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				item.setSelected(True)
			elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				item.setSelected(True)
			elif self._is_presentation_item(item):
				item.setSelected(True)
		self.status_message.emit("Selected all")

	#============================================
	def _nudge_selected(self, dx: float, dy: float) -> None:
		"""Submit one selected durable-atom nudge without local geometry mutation.

		Args:
			dx: Horizontal offset in scene units.
			dy: Vertical offset in scene units.
		"""
		scene = self._env.scene
		if scene is None:
			return
		targets = []
		for item in scene.selectedItems():
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				atom_model = item.atom_model
				atom_id = atom_model.backend_durable_id
				molecule = getattr(atom_model, "_molecule_model", None)
				molecule_id = getattr(molecule, "mol_id", None)
				if not atom_id or not molecule_id:
					self.status_message.emit(
						"Nudge unavailable: selected atom lacks durable identity",
					)
					return
				targets.append((str(molecule_id), str(atom_id)))
		if not targets:
			return
		if self._atom_translate_operation is None:
			self.status_message.emit("Nudge unavailable for this document")
			return
		outcome = self._atom_translate_operation(tuple(targets), (dx, dy))
		self.status_message.emit(outcome.message)

	# ------------------------------------------------------------------
	# Property editing helpers
	# ------------------------------------------------------------------

	#============================================
	def _edit_atom_properties(
			self, atom_item: bkchem_qt.canvas.items.atom_item.AtomItem,
			) -> None:
		"""Open the atom dialog and submit one revision-bound persistent patch.

		Dialog acceptance submits exactly the revision captured before the modal
		interaction. A changed backend acceptance installs canonical reprojection;
		a canonical no-op keeps projection and history unchanged. A stale submission
		rejects atomically. Intentionally isolated documents retain local undo.

		Args:
			atom_item: The AtomItem to edit.
		"""
		undo_stack = self._env.undo_stack
		if undo_stack is None:
			return
		model = atom_item.atom_model
		# Capture status text before an accepted backend commit replaces this projection.
		symbol = model.symbol
		changed = bkchem_qt.actions.property_editing.edit_atom_properties(
			model, self._view, undo_stack,
		)
		if changed:
			self.status_message.emit(f"Edited atom {symbol}")

	#============================================
	def _edit_bond_properties(
			self, bond_item: bkchem_qt.canvas.items.bond_item.BondItem,
			) -> None:
		"""Open a bond dialog for detached persistent intent.

		An ineligible durable bond ID or unavailable synchronized capability is inert
		before dialog or commit routing. After the dialog captures its target and
		capability, a revision that becomes stale reaches the backend as a typed
		atomic rejection and leaves the authoritative snapshot, projection, history,
		and dirty state unchanged. A changed accepted synchronized edit submits one
		exact-session backend patch and installs its canonical reprojection; backend
		history owns undo and dirty state. A canonical no-op creates no history and
		keeps the installed projection.
		Intentionally isolated documents retain local ChangePropertyCommand undo.

		Args:
			bond_item: The BondItem to edit.
		"""
		undo_stack = self._env.undo_stack
		if undo_stack is None:
			return
		model = bond_item.bond_model
		changed = bkchem_qt.actions.property_editing.edit_bond_properties(
			model, self._view, undo_stack,
		)
		if changed:
			self.status_message.emit("Edited bond properties")

	# ------------------------------------------------------------------
	# Rubber band helpers
	# ------------------------------------------------------------------

	#============================================
	def _update_rubber_band(self, scene_pos: PySide6.QtCore.QPointF) -> None:
		"""Update or create the rubber band selection rectangle.

		Args:
			scene_pos: Current mouse position in scene coordinates.
		"""
		scene = self._env.scene
		if scene is None or self._rubber_band_origin is None:
			return
		# compute the rectangle from origin to current position
		rect = PySide6.QtCore.QRectF(self._rubber_band_origin, scene_pos).normalized()
		if self._rubber_band is None:
			# create a semi-transparent rubber band rectangle
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor(render_ops_painter.get_canvas_color("selection")))
			pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
			brush = PySide6.QtGui.QBrush(PySide6.QtGui.QColor(51, 153, 255, 40))
			self._rubber_band = scene.addRect(rect, pen, brush)
			self._rubber_band_scene = scene
		else:
			self._rubber_band.setRect(rect)

	#============================================
	def _finalize_rubber_band(self, scene_pos: PySide6.QtCore.QPointF) -> None:
		"""Select all interactive items within the rubber band rectangle.

		Args:
			scene_pos: Final mouse position in scene coordinates.
		"""
		scene = self._env.scene
		if scene is None or self._rubber_band_origin is None:
			return
		rect = PySide6.QtCore.QRectF(self._rubber_band_origin, scene_pos).normalized()
		# select items within the rectangle
		items_in_rect = scene.items(rect)
		for item in items_in_rect:
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				item.setSelected(True)
			elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				item.setSelected(True)
			elif self._is_presentation_item(item):
				item.setSelected(True)
		bkchem_qt.models.bracket_pair_selection.expand_selection(self._env.document)

	#============================================
	def _cancel_rubber_band(self) -> None:
		"""Terminally retire the known rubber band before releasing its wrapper."""
		rubber_band = self._rubber_band
		rubber_band_scene = self._rubber_band_scene
		if rubber_band is None:
			return
		try:
			coordinator = bkchem_qt.canvas.graphics_retirement.GraphicsRetirementCoordinator()
			if rubber_band_scene is None:
				coordinator.retire_detached_projection_items(
					[rubber_band], reaper=self._graphics_retirement_reaper,
				)
			else:
				coordinator.retire_scene_projection_items(
					rubber_band_scene, [rubber_band],
					reaper=self._graphics_retirement_reaper,
				)
			coordinator.raise_if_callback_failed("Edit selection preview retirement failed")
		finally:
			self._rubber_band = None
			self._rubber_band_scene = None

	#============================================
	def _item_at(self, scene_pos: PySide6.QtCore.QPointF) -> object | None:
		"""Return the topmost selectable chemistry or presentation item."""
		item = super()._item_at(scene_pos)
		if item is not None:
			return item
		scene = self._env.scene
		if scene is None:
			return None
		for candidate in scene.items(scene_pos):
			if self._is_presentation_item(candidate):
				return candidate
		return None

	#============================================
	def _is_presentation_item(self, item: object) -> bool:
		"""Whether an item projects a persistent document presentation model."""
		document = self._env.document
		object_model = getattr(item, "document_object_model", None)
		return document is not None and object_model in document.presentation_objects

	#============================================
	def _presentation_geometry(self, object_model: object) -> tuple:
		"""Copy one presentation model's editable points and bounds."""
		return (object_model.points, object_model.bounds)

	#============================================
	def _translate_presentation_model(
			self, object_model: object, dx: float, dy: float,
			) -> None:
		"""Translate points and bounds through the persistent presentation model."""
		points, bounds = self._presentation_geometry(object_model)
		object_model.set_points([
			(x + dx, y + dy, z) for x, y, z in points
		])
		if bounds is not None:
			x, y, width, height = bounds
			object_model.set_bounds((x + dx, y + dy, width, height))

	#============================================
	def _presentation_drag_changes(self) -> list:
		"""Return changed presentation-model geometry in drag-start order."""
		changes = []
		for object_model, before in self._drag_presentation_start_geometry.values():
			after = self._presentation_geometry(object_model)
			if after != before:
				changes.append((object_model, before, after))
		return changes
