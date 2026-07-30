"""Backend-authoritative 2D rotation mode for selected durable atoms."""

# Standard Library
import math

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.modes.base_mode


#============================================
class RotateMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Preview a 2D atom rotation, then submit one backend-owned commit."""

	#============================================
	def __init__(
			self, view: object, parent: PySide6.QtCore.QObject | None = None,
			) -> None:
		"""Initialize a transient preview with no local persistent owner."""
		super().__init__(view, parent)
		self._name = "Rotate"
		self._atom_rotate_operation = None
		self._center = None
		self._last_angle = None
		self._accumulated_angle = 0.0
		self._original_positions = {}
		self._targets = ()
		self._drag_operation = None
		self._cursor = PySide6.QtCore.Qt.CursorShape.SizeAllCursor

	#============================================
	def set_atom_rotate_operation(self, operation: object | None) -> None:
		"""Install the session-owned atom-rotation client callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Persistent operation must be callable")
		self._atom_rotate_operation = operation

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return the bounded 2D rotation interaction guidance."""
		return "Click and drag to rotate selected durable atoms in 2D"

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Capture durable atom targets and starting coordinates for one preview."""
		scene = self._env.scene
		self._clear_drag_state()
		if scene is None or self._atom_rotate_operation is None:
			self.status_message.emit("Rotation unavailable for this document")
			return
		targets = []
		positions = {}
		for item in scene.selectedItems():
			if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				continue
			atom = item.atom_model
			atom_id = atom.backend_durable_id
			molecule = getattr(atom, "_molecule_model", None)
			molecule_id = getattr(molecule, "mol_id", None)
			if not atom_id or not molecule_id:
				self.status_message.emit("Rotation unavailable: selected atom lacks durable identity")
				return
			target = (str(molecule_id), str(atom_id))
			targets.append(target)
			positions[target] = (atom.x, atom.y, item)
		if not targets:
			self.status_message.emit("No durable atoms selected")
			return
		self._center = PySide6.QtCore.QPointF(scene_pos)
		self._targets = tuple(targets)
		self._original_positions = positions
		# The bound session callback is part of this gesture's origin.  A tab or
		# mode rebind after press must not redirect the accepted persistent intent.
		self._drag_operation = self._atom_rotate_operation
		self.status_message.emit("Drag to rotate selected atoms")

	#============================================
	def mouse_move(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Apply a transient unwrapped angular preview to selected atom items."""
		if self._center is None or not self._original_positions:
			return
		dx = scene_pos.x() - self._center.x()
		dy = scene_pos.y() - self._center.y()
		if abs(dx) <= 1.0 and abs(dy) <= 1.0 and self._last_angle is None:
			return
		current_angle = math.atan2(dy, dx)
		if self._last_angle is None:
			self._last_angle = current_angle
			return
		delta = current_angle - self._last_angle
		if delta > math.pi:
			delta -= math.tau
		elif delta < -math.pi:
			delta += math.tau
		self._accumulated_angle += delta
		self._last_angle = current_angle
		self._apply_preview()

	#============================================
	def mouse_release(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Restore preview items, then submit exactly one immutable rotation intent."""
		if self._center is None or not self._original_positions:
			self._clear_drag_state()
			return
		center = (self._center.x(), self._center.y())
		targets = self._targets
		angle = self._accumulated_angle
		operation = self._drag_operation
		self._restore_original_positions()
		self._clear_drag_state()
		if angle == 0.0 or operation is None:
			self.status_message.emit("Rotate mode active")
			return
		outcome = operation(targets, center, angle)
		self.status_message.emit(outcome.message)

	#============================================
	def deactivate(self) -> None:
		"""Cancel any live preview without creating a persistent mutation."""
		self._restore_original_positions()
		self._clear_drag_state()
		super().deactivate()

	#============================================
	def _apply_preview(self) -> None:
		"""Project the accumulated transient angle onto the selected atom models."""
		if self._center is None:
			return
		cosine = math.cos(self._accumulated_angle)
		sine = math.sin(self._accumulated_angle)
		center_x = self._center.x()
		center_y = self._center.y()
		for original_x, original_y, item in self._original_positions.values():
			x = center_x + (original_x - center_x) * cosine - (original_y - center_y) * sine
			y = center_y + (original_x - center_x) * sine + (original_y - center_y) * cosine
			item.atom_model.set_xyz(x, y, item.atom_model.z)
		self._update_bond_items()

	#============================================
	def _restore_original_positions(self) -> None:
		"""Return transient preview atoms to their captured geometry."""
		for original_x, original_y, item in self._original_positions.values():
			item.atom_model.set_xyz(original_x, original_y, item.atom_model.z)
		self._update_bond_items()

	#============================================
	def _clear_drag_state(self) -> None:
		"""Release all wrapper references retained by the transient drag."""
		self._center = None
		self._last_angle = None
		self._accumulated_angle = 0.0
		self._original_positions = {}
		self._targets = ()
		self._drag_operation = None

	#============================================
	def _update_bond_items(self) -> None:
		"""Refresh bond projections after a preview coordinate update."""
		scene = self._env.scene
		if scene is not None:
			for item in scene.items():
				if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
					item.update_from_model()
