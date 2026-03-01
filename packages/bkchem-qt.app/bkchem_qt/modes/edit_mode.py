"""Edit mode for selecting, moving, and deleting items."""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.undo.commands
import bkchem_qt.dialogs.atom_dialog
import bkchem_qt.dialogs.bond_dialog
import bkchem_qt.actions.context_menu

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
	def __init__(self, view, parent=None):
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
		# rubber band selection rectangle
		self._rubber_band = None
		self._rubber_band_origin = None
		# items being dragged
		self._moved_items = []

	# ------------------------------------------------------------------
	# Lifecycle
	# ------------------------------------------------------------------

	#============================================
	def deactivate(self) -> None:
		"""Clean up any drag or rubber band state when leaving edit mode."""
		self._cancel_rubber_band()
		self._dragging = False
		self._drag_start = None
		self._drag_last = None
		self._moved_items = []
		super().deactivate()

	# ------------------------------------------------------------------
	# Mouse event handlers
	# ------------------------------------------------------------------

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse press for selection and drag initiation.

		Click on an item selects it (shift-click adds to selection).
		Click on empty space clears selection and starts rubber band.
		Click on an already-selected item starts a drag operation.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		# right-click opens context menu
		if event.button() == PySide6.QtCore.Qt.MouseButton.RightButton:
			screen_pos = event.globalPosition().toPoint()
			bkchem_qt.actions.context_menu.show_context_menu(
				self._view, scene_pos, screen_pos,
			)
			return
		item = self._item_at(scene_pos)
		shift_held = bool(event.modifiers() & PySide6.QtCore.Qt.KeyboardModifier.ShiftModifier)
		scene = self._view.scene()
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
			elif shift_held:
				# toggle selection on shift-click
				item.setSelected(not item.isSelected())
			else:
				# clear selection and select this item
				scene.clearSelection()
				item.setSelected(True)
				# prepare for potential drag
				self._dragging = True
				self._drag_start = scene_pos
				self._drag_last = scene_pos
				self._moved_items = [item]
		else:
			# click on empty space: clear selection and start rubber band
			if not shift_held:
				scene.clearSelection()
			self._rubber_band_origin = scene_pos
			self.status_message.emit("Drag to select area")

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse move for dragging items or updating rubber band.

		Drags selected items by the delta from the last move position.
		If rubber-banding, updates the selection rectangle.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._dragging and self._drag_last is not None:
			# compute delta from last tracked position
			dx = scene_pos.x() - self._drag_last.x()
			dy = scene_pos.y() - self._drag_last.y()
			# only start moving after exceeding threshold
			if self._drag_start is not None:
				total_dx = scene_pos.x() - self._drag_start.x()
				total_dy = scene_pos.y() - self._drag_start.y()
				distance = (total_dx ** 2 + total_dy ** 2) ** 0.5
				if distance < _DRAG_THRESHOLD:
					return
			# move each selected item
			for item in self._moved_items:
				if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
					model = item.atom_model
					model.x = model.x + dx
					model.y = model.y + dy
			self._drag_last = scene_pos
		elif self._rubber_band_origin is not None:
			# update or create the rubber band rectangle
			self._update_rubber_band(scene_pos)

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse release to finalize moves or rubber band selection.

		If items were dragged, pushes a MoveAtomsCommand onto the undo
		stack. If rubber-banding, selects items within the rectangle.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._view.scene()
		if self._dragging and self._drag_start is not None and scene is not None:
			# compute total offset for undo command
			total_dx = scene_pos.x() - self._drag_start.x()
			total_dy = scene_pos.y() - self._drag_start.y()
			distance = (total_dx ** 2 + total_dy ** 2) ** 0.5
			if distance >= _DRAG_THRESHOLD:
				# build items_and_offsets list for the undo command
				items_and_offsets = []
				for item in self._moved_items:
					if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
						items_and_offsets.append((item, total_dx, total_dy))
				if items_and_offsets:
					# find the document undo stack
					undo_stack = self._find_undo_stack()
					if undo_stack is not None:
						cmd = bkchem_qt.undo.commands.MoveAtomsCommand(
							items_and_offsets,
						)
						# push without redo since items are already moved
						undo_stack.push(cmd)
		elif self._rubber_band_origin is not None and scene is not None:
			# select items within the rubber band rectangle
			self._finalize_rubber_band(scene_pos)
		# reset drag state
		self._dragging = False
		self._drag_start = None
		self._drag_last = None
		self._moved_items = []
		self._rubber_band_origin = None
		self._cancel_rubber_band()

	#============================================
	def mouse_double_click(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Open a property dialog for the item under the cursor.

		For atoms, opens AtomDialog; for bonds, opens BondDialog. Changes
		are wrapped in ChangePropertyCommand for undo support.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		item = self._item_at(scene_pos)
		if item is None:
			return
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			self._edit_atom_properties(item)
		elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			self._edit_bond_properties(item)

	# ------------------------------------------------------------------
	# Keyboard event handlers
	# ------------------------------------------------------------------

	#============================================
	def key_press(self, event) -> None:
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
			scene = self._view.scene()
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
	def _delete_selected(self) -> None:
		"""Delete all selected items with undo support.

		Removes bonds first, then atoms, each as a separate undo
		command grouped under a macro.
		"""
		scene = self._view.scene()
		if scene is None:
			return
		selected = scene.selectedItems()
		if not selected:
			return
		undo_stack = self._find_undo_stack()
		if undo_stack is None:
			return
		# separate atoms and bonds
		atom_items = []
		bond_items = []
		for item in selected:
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				atom_items.append(item)
			elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				bond_items.append(item)
		if not atom_items and not bond_items:
			return
		# use a macro to group all deletions
		undo_stack.beginMacro("Delete Selected")
		# remove bonds first
		for bond_item in bond_items:
			mol_model = self._find_molecule_for_bond(bond_item.bond_model)
			if mol_model is not None:
				cmd = bkchem_qt.undo.commands.RemoveBondCommand(
					scene, mol_model, bond_item.bond_model, bond_item,
				)
				undo_stack.push(cmd)
		# remove atoms (which also removes their connected bonds)
		for atom_item in atom_items:
			mol_model = self._find_molecule_for_atom(atom_item.atom_model)
			if mol_model is not None:
				# find connected bond items
				connected_bonds = self._find_connected_bond_items(atom_item)
				cmd = bkchem_qt.undo.commands.RemoveAtomCommand(
					scene, mol_model, atom_item.atom_model,
					atom_item, connected_bonds,
				)
				undo_stack.push(cmd)
		undo_stack.endMacro()
		self.status_message.emit("Deleted selected items")

	#============================================
	def _select_all(self) -> None:
		"""Select all interactive items in the scene."""
		scene = self._view.scene()
		if scene is None:
			return
		for item in scene.items():
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				item.setSelected(True)
			elif isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				item.setSelected(True)
		self.status_message.emit("Selected all")

	#============================================
	def _nudge_selected(self, dx: float, dy: float) -> None:
		"""Move selected atom items by a small offset with undo support.

		Args:
			dx: Horizontal offset in scene units.
			dy: Vertical offset in scene units.
		"""
		scene = self._view.scene()
		if scene is None:
			return
		selected = scene.selectedItems()
		items_and_offsets = []
		for item in selected:
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				model = item.atom_model
				model.x = model.x + dx
				model.y = model.y + dy
				items_and_offsets.append((item, dx, dy))
		if items_and_offsets:
			undo_stack = self._find_undo_stack()
			if undo_stack is not None:
				cmd = bkchem_qt.undo.commands.MoveAtomsCommand(items_and_offsets)
				undo_stack.push(cmd)

	# ------------------------------------------------------------------
	# Property editing helpers
	# ------------------------------------------------------------------

	#============================================
	def _edit_atom_properties(self, atom_item) -> None:
		"""Open the atom dialog and apply changes with undo support.

		Args:
			atom_item: The AtomItem to edit.
		"""
		model = atom_item.atom_model
		# snapshot old values before dialog opens
		old_values = {
			"symbol": model.symbol,
			"charge": model.charge,
			"valency": model.valency,
			"isotope": model.isotope,
			"multiplicity": model.multiplicity,
			"show": model.show,
			"show_hydrogens": model.show_hydrogens,
			"font_size": model.font_size,
			"line_color": model.line_color,
		}
		accepted = bkchem_qt.dialogs.atom_dialog.AtomDialog.edit_atom(
			model, self._view,
		)
		if not accepted:
			return
		# push undo commands for each changed property
		undo_stack = self._find_undo_stack()
		if undo_stack is None:
			return
		undo_stack.beginMacro("Edit Atom Properties")
		for key, old_val in old_values.items():
			new_val = getattr(model, key)
			if new_val != old_val:
				# revert to old so the redo applies the new value
				setattr(model, key, old_val)
				cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
					model, key, old_val, new_val,
					text=f"Change {key}",
				)
				undo_stack.push(cmd)
		undo_stack.endMacro()
		self.status_message.emit(f"Edited atom {model.symbol}")

	#============================================
	def _edit_bond_properties(self, bond_item) -> None:
		"""Open the bond dialog and apply changes with undo support.

		Args:
			bond_item: The BondItem to edit.
		"""
		model = bond_item.bond_model
		# snapshot old values before dialog opens
		old_values = {
			"order": model.order,
			"type": model.type,
			"center": model.center,
			"line_width": model.line_width,
			"bond_width": model.bond_width,
			"wedge_width": model.wedge_width,
			"line_color": model.line_color,
		}
		accepted = bkchem_qt.dialogs.bond_dialog.BondDialog.edit_bond(
			model, self._view,
		)
		if not accepted:
			return
		# push undo commands for each changed property
		undo_stack = self._find_undo_stack()
		if undo_stack is None:
			return
		undo_stack.beginMacro("Edit Bond Properties")
		for key, old_val in old_values.items():
			new_val = getattr(model, key)
			if new_val != old_val:
				# revert to old so the redo applies the new value
				setattr(model, key, old_val)
				cmd = bkchem_qt.undo.commands.ChangePropertyCommand(
					model, key, old_val, new_val,
					text=f"Change {key}",
				)
				undo_stack.push(cmd)
		undo_stack.endMacro()
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
		scene = self._view.scene()
		if scene is None or self._rubber_band_origin is None:
			return
		# compute the rectangle from origin to current position
		rect = PySide6.QtCore.QRectF(self._rubber_band_origin, scene_pos).normalized()
		if self._rubber_band is None:
			# create a semi-transparent rubber band rectangle
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor("#3399ff"))
			pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
			brush = PySide6.QtGui.QBrush(PySide6.QtGui.QColor(51, 153, 255, 40))
			self._rubber_band = scene.addRect(rect, pen, brush)
		else:
			self._rubber_band.setRect(rect)

	#============================================
	def _finalize_rubber_band(self, scene_pos: PySide6.QtCore.QPointF) -> None:
		"""Select all interactive items within the rubber band rectangle.

		Args:
			scene_pos: Final mouse position in scene coordinates.
		"""
		scene = self._view.scene()
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

	#============================================
	def _cancel_rubber_band(self) -> None:
		"""Remove the rubber band rectangle from the scene."""
		if self._rubber_band is not None:
			scene = self._view.scene()
			if scene is not None:
				scene.removeItem(self._rubber_band)
			self._rubber_band = None

	# ------------------------------------------------------------------
	# Lookup helpers
	# ------------------------------------------------------------------

	#============================================
	def _find_undo_stack(self):
		"""Locate the document's QUndoStack through the view.

		Returns:
			QUndoStack or None if not accessible.
		"""
		view = self._view
		# the view is expected to expose a document property
		if hasattr(view, "document") and view.document is not None:
			return view.document.undo_stack
		return None

	#============================================
	def _find_molecule_for_atom(self, atom_model):
		"""Find the MoleculeModel that contains a given AtomModel.

		Args:
			atom_model: The AtomModel to search for.

		Returns:
			MoleculeModel or None.
		"""
		view = self._view
		if not hasattr(view, "document") or view.document is None:
			return None
		for mol_model in view.document.molecules:
			if atom_model in mol_model.atoms:
				return mol_model
		return None

	#============================================
	def _find_molecule_for_bond(self, bond_model):
		"""Find the MoleculeModel that contains a given BondModel.

		Args:
			bond_model: The BondModel to search for.

		Returns:
			MoleculeModel or None.
		"""
		view = self._view
		if not hasattr(view, "document") or view.document is None:
			return None
		for mol_model in view.document.molecules:
			if bond_model in mol_model.bonds:
				return mol_model
		return None

	#============================================
	def _find_connected_bond_items(self, atom_item):
		"""Find all BondItems connected to a given AtomItem.

		Args:
			atom_item: The AtomItem whose bonds to find.

		Returns:
			List of (BondModel, BondItem) tuples.
		"""
		scene = self._view.scene()
		if scene is None:
			return []
		connected = []
		atom_model = atom_item.atom_model
		for item in scene.items():
			if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				bond_model = item.bond_model
				if bond_model.atom1 is atom_model or bond_model.atom2 is atom_model:
					connected.append((bond_model, item))
		return connected
