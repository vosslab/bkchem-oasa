"""Draw mode for creating new atoms and bonds."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.undo.commands

# default bond length in scene units
_DEFAULT_BOND_LENGTH = 40.0
# snap radius: if release is within this distance of an atom, snap to it
_SNAP_RADIUS = 15.0


#============================================
class DrawMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for drawing new atoms and bonds.

	Click on empty space to create a standalone atom. Drag from an
	existing atom to create a new atom connected by a bond. Drag between
	two existing atoms to bond them. A preview line shows the bond
	being drawn during the drag.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the draw mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Draw"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		# current drawing settings
		self._current_element = "C"
		self._current_bond_order = 1
		self._current_bond_type = "n"
		# drag state
		self._preview_line = None
		self._start_atom = None
		self._dragging = False
		self._press_pos = None

	# ------------------------------------------------------------------
	# Drawing settings
	# ------------------------------------------------------------------

	#============================================
	@property
	def current_element(self) -> str:
		"""The element symbol used for new atoms."""
		return self._current_element

	#============================================
	@current_element.setter
	def current_element(self, symbol: str):
		self._current_element = str(symbol)

	#============================================
	@property
	def current_bond_order(self) -> int:
		"""The bond order used for new bonds (1, 2, or 3)."""
		return self._current_bond_order

	#============================================
	@current_bond_order.setter
	def current_bond_order(self, order: int):
		self._current_bond_order = int(order)

	#============================================
	@property
	def current_bond_type(self) -> str:
		"""The bond type character used for new bonds."""
		return self._current_bond_type

	#============================================
	@current_bond_type.setter
	def current_bond_type(self, bond_type: str):
		self._current_bond_type = str(bond_type)

	# ------------------------------------------------------------------
	# Lifecycle
	# ------------------------------------------------------------------

	#============================================
	def deactivate(self) -> None:
		"""Remove any preview line and reset drag state."""
		self._remove_preview_line()
		self._start_atom = None
		self._dragging = False
		self._press_pos = None
		super().deactivate()

	# ------------------------------------------------------------------
	# Mouse event handlers
	# ------------------------------------------------------------------

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse press to begin drawing.

		If pressed on an existing atom, begins a bond drag from that
		atom. If pressed on empty space, records the position for a
		potential new standalone atom.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self._press_pos = scene_pos
		existing_atom = self._find_atom_at(scene_pos)
		if existing_atom is not None:
			# start bond drag from existing atom
			self._start_atom = existing_atom
			self._dragging = True
			self.status_message.emit("Drag to create bond")
		else:
			# record press position for potential standalone atom
			self._start_atom = None
			self._dragging = False

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse move to show a bond preview line.

		Only draws a preview when dragging from an existing atom.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if not self._dragging or self._start_atom is None:
			return
		# determine the start point from the atom model
		start_model = self._start_atom.atom_model
		start_x = start_model.x
		start_y = start_model.y
		# draw or update the preview line
		scene = self._view.scene()
		if scene is None:
			return
		if self._preview_line is None:
			pen = PySide6.QtGui.QPen(PySide6.QtGui.QColor("#888888"))
			pen.setWidthF(1.5)
			pen.setStyle(PySide6.QtCore.Qt.PenStyle.DashLine)
			self._preview_line = scene.addLine(
				start_x, start_y, scene_pos.x(), scene_pos.y(), pen,
			)
		else:
			self._preview_line.setLine(
				start_x, start_y, scene_pos.x(), scene_pos.y(),
			)

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle mouse release to finalize atom/bond creation.

		If dragging from an atom and releasing on a different atom,
		creates a bond between them. If releasing on empty space,
		creates a new atom and bonds it to the start atom. If this
		was a simple click on empty space (no drag), creates a
		standalone atom.

		All created items are pushed onto the undo stack.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self._remove_preview_line()
		if self._dragging and self._start_atom is not None:
			# was dragging from an existing atom
			end_atom = self._find_atom_at(scene_pos)
			if end_atom is not None and end_atom is not self._start_atom:
				# bond to existing atom
				self._create_bond_between(self._start_atom, end_atom)
			else:
				# create new atom at release position and bond to start
				new_atom_item = self._create_atom_at(
					scene_pos.x(), scene_pos.y(),
				)
				if new_atom_item is not None:
					self._create_bond_between(self._start_atom, new_atom_item)
		elif self._press_pos is not None:
			# simple click on empty space: create standalone atom
			self._create_atom_at(scene_pos.x(), scene_pos.y())
		# reset state
		self._start_atom = None
		self._dragging = False
		self._press_pos = None

	# ------------------------------------------------------------------
	# Creation helpers
	# ------------------------------------------------------------------

	#============================================
	def _create_atom_at(self, x: float, y: float, symbol: str = None):
		"""Create a new atom at a scene position with undo support.

		Creates an AtomModel and AtomItem, adds the atom to the active
		molecule (creating one if needed), and pushes an AddAtomCommand.

		Args:
			x: X coordinate in scene units.
			y: Y coordinate in scene units.
			symbol: Element symbol (defaults to current_element).

		Returns:
			The created AtomItem, or None if creation failed.
		"""
		scene = self._view.scene()
		if scene is None:
			return None
		element = symbol or self._current_element
		# get or create the active molecule
		mol_model = self._get_active_molecule()
		if mol_model is None:
			return None
		# create the atom model
		atom_model = mol_model.create_atom(symbol=element)
		atom_model.x = x
		atom_model.y = y
		# create the visual item
		atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom_model)
		# push undo command
		undo_stack = self._find_undo_stack()
		if undo_stack is not None:
			cmd = bkchem_qt.undo.commands.AddAtomCommand(
				scene, mol_model, atom_model, atom_item,
			)
			undo_stack.push(cmd)
		else:
			# no undo stack: add directly
			mol_model.add_atom(atom_model)
			scene.addItem(atom_item)
		self.status_message.emit(f"Added {element} atom")
		return atom_item

	#============================================
	def _create_bond_between(self, atom1_item, atom2_item):
		"""Create a bond between two atom items with undo support.

		Adds the bond to the molecule graph first so the BondItem
		constructor can compute render ops from atom positions, then
		pushes an AddBondCommand for undo support.

		Args:
			atom1_item: First endpoint AtomItem.
			atom2_item: Second endpoint AtomItem.

		Returns:
			The created BondItem, or None if creation failed.
		"""
		scene = self._view.scene()
		if scene is None:
			return None
		mol_model = self._get_active_molecule()
		if mol_model is None:
			return None
		# create the bond model
		bond_model = mol_model.create_bond(
			order=self._current_bond_order,
			bond_type=self._current_bond_type,
		)
		# add bond to molecule graph first so BondItem can access vertices
		atom1_model = atom1_item.atom_model
		atom2_model = atom2_item.atom_model
		mol_model.add_bond(atom1_model, atom2_model, bond_model)
		# create the visual item (needs bond in graph for render ops)
		bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
		scene.addItem(bond_item)
		# push undo command (bond already added, skip first redo)
		undo_stack = self._find_undo_stack()
		if undo_stack is not None:
			cmd = bkchem_qt.undo.commands.AddBondCommand(
				scene, mol_model, bond_model, bond_item,
			)
			cmd._first_redo = True
			undo_stack.push(cmd)
		order_name = {1: "single", 2: "double", 3: "triple"}.get(
			self._current_bond_order, str(self._current_bond_order),
		)
		self.status_message.emit(f"Added {order_name} bond")
		return bond_item

	#============================================
	def _find_atom_at(self, scene_pos: PySide6.QtCore.QPointF):
		"""Find an AtomItem near a scene position within snap radius.

		Searches for AtomItems and returns the closest one within
		``_SNAP_RADIUS``, or None if none are close enough.

		Args:
			scene_pos: Position in scene coordinates.

		Returns:
			AtomItem or None.
		"""
		scene = self._view.scene()
		if scene is None:
			return None
		# check items in a rectangle around the position
		snap_rect = PySide6.QtCore.QRectF(
			scene_pos.x() - _SNAP_RADIUS,
			scene_pos.y() - _SNAP_RADIUS,
			_SNAP_RADIUS * 2,
			_SNAP_RADIUS * 2,
		)
		candidates = scene.items(snap_rect)
		best_item = None
		best_dist = _SNAP_RADIUS
		for item in candidates:
			if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				continue
			model = item.atom_model
			dx = model.x - scene_pos.x()
			dy = model.y - scene_pos.y()
			dist = math.sqrt(dx * dx + dy * dy)
			if dist < best_dist:
				best_dist = dist
				best_item = item
		return best_item

	# ------------------------------------------------------------------
	# Preview line helpers
	# ------------------------------------------------------------------

	#============================================
	def _remove_preview_line(self) -> None:
		"""Remove the bond preview line from the scene."""
		if self._preview_line is not None:
			scene = self._view.scene()
			if scene is not None:
				scene.removeItem(self._preview_line)
			self._preview_line = None

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
		if hasattr(view, "document") and view.document is not None:
			return view.document.undo_stack
		return None

	#============================================
	def _get_active_molecule(self):
		"""Get or create the active MoleculeModel for drawing.

		If the document has molecules, returns the first one. Otherwise
		creates a new molecule and adds it to the document.

		Returns:
			MoleculeModel or None if no document is available.
		"""
		view = self._view
		if not hasattr(view, "document") or view.document is None:
			return None
		doc = view.document
		if doc.molecules:
			return doc.molecules[0]
		# create a new molecule for the document
		import bkchem_qt.models.molecule_model
		mol_model = bkchem_qt.models.molecule_model.MoleculeModel()
		doc.add_molecule(mol_model)
		return mol_model
