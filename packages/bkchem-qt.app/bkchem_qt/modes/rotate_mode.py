"""Rotation mode for 2D rotation of selected items."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item


#============================================
class RotateMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for rotating selected items around a center point.

	On the first click, the rotation center is set. On drag, selected
	items rotate around that center by the angle swept by the mouse.
	On release, the rotation is finalized.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the rotate mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Rotate"
		# rotation center in scene coordinates
		self._center = None
		# angle at the start of the drag in radians
		self._start_angle = 0.0
		# accumulated rotation for the current drag
		self._accumulated_angle = 0.0
		# original positions of selected atom items before rotation
		self._original_positions = {}
		self._cursor = PySide6.QtCore.Qt.CursorShape.SizeAllCursor

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Set the rotation center and record initial positions.

		On the first press, the rotation center is set to the click
		position. Original positions of all selected atom items are
		saved for incremental rotation during drag.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._view.scene()
		if scene is None:
			return
		# set rotation center to click position
		self._center = scene_pos
		self._start_angle = 0.0
		self._accumulated_angle = 0.0
		# save original positions of selected atom items
		self._original_positions = {}
		for item in scene.selectedItems():
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				model = item.atom_model
				self._original_positions[id(item)] = (model.x, model.y, item)
		self.status_message.emit("Drag to rotate selected items")

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Compute rotation angle and rotate selected items incrementally.

		Calculates the angle between the initial mouse direction and the
		current mouse position relative to the rotation center, then
		applies that rotation to all saved atom positions.

		Args:
			scene_pos: Current position in scene coordinates.
			event: The mouse event.
		"""
		if self._center is None:
			return
		if not self._original_positions:
			return
		# compute angle from center to current mouse position
		dx = scene_pos.x() - self._center.x()
		dy = scene_pos.y() - self._center.y()
		current_angle = math.atan2(dy, dx)
		# on the first move, set the start angle
		if self._start_angle == 0.0 and (abs(dx) > 1.0 or abs(dy) > 1.0):
			self._start_angle = current_angle
			return
		# compute the rotation delta from the start
		rotation = current_angle - self._start_angle
		# apply rotation to each saved original position
		cx = self._center.x()
		cy = self._center.y()
		cos_r = math.cos(rotation)
		sin_r = math.sin(rotation)
		for item_id, (orig_x, orig_y, item) in self._original_positions.items():
			# translate to origin, rotate, translate back
			rel_x = orig_x - cx
			rel_y = orig_y - cy
			new_x = cx + rel_x * cos_r - rel_y * sin_r
			new_y = cy + rel_x * sin_r + rel_y * cos_r
			item.atom_model.set_xyz(new_x, new_y, item.atom_model.z)
		self._accumulated_angle = rotation
		# update bond items after moving atoms
		scene = self._view.scene()
		if scene is not None:
			for item in scene.items():
				if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
					item.update_from_model()

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Finalize the rotation.

		Clears the saved original positions and rotation state.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		self._center = None
		self._start_angle = 0.0
		self._accumulated_angle = 0.0
		self._original_positions = {}
		self.status_message.emit("Rotate mode active")

	#============================================
	def deactivate(self) -> None:
		"""Clean up rotation state when leaving the mode."""
		self._center = None
		self._original_positions = {}
		super().deactivate()
