"""Bond alignment mode for align/mirror/invert operations."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item

# supported alignment operations
ALIGN_HORIZONTAL = "align_horizontal"
ALIGN_VERTICAL = "align_vertical"
MIRROR_HORIZONTAL = "mirror_horizontal"
MIRROR_VERTICAL = "mirror_vertical"


#============================================
class BondAlignMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for aligning and mirroring molecule geometry.

	Click to apply the current alignment operation to all selected
	atom items. The operation can be changed via ``set_operation()``.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize the bond alignment mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Align"
		# current alignment submode operation
		self._operation = ALIGN_HORIZONTAL
		self._cursor = PySide6.QtCore.Qt.CursorShape.SizeAllCursor

	#============================================
	@property
	def operation(self) -> str:
		"""Return the current alignment operation name."""
		return self._operation

	#============================================
	def set_operation(self, operation: str) -> None:
		"""Set the alignment operation for subsequent clicks.

		Args:
			operation: One of the ALIGN_* or MIRROR_* constants.
		"""
		self._operation = operation
		self.status_message.emit(f"Align mode: {operation}")

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Apply the alignment operation to selected items.

		Collects all selected AtomItems, computes the centroid or
		axis, and applies the appropriate transformation.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		scene = self._view.scene()
		if scene is None:
			return
		# collect selected atom items
		atom_items = []
		for item in scene.selectedItems():
			if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				atom_items.append(item)
		if not atom_items:
			self.status_message.emit("No atoms selected")
			return
		# dispatch to the appropriate operation
		if self._operation == ALIGN_HORIZONTAL:
			_align_horizontal(atom_items)
		elif self._operation == ALIGN_VERTICAL:
			_align_vertical(atom_items)
		elif self._operation == MIRROR_HORIZONTAL:
			_mirror_horizontal(atom_items)
		elif self._operation == MIRROR_VERTICAL:
			_mirror_vertical(atom_items)
		# update any bond items that depend on moved atoms
		for item in scene.items():
			if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				item.update_from_model()
		self.status_message.emit(f"Applied {self._operation}")


#============================================
def _align_horizontal(atom_items: list) -> None:
	"""Align selected atoms to the same y-coordinate (average y).

	Args:
		atom_items: List of AtomItem instances to align.
	"""
	if not atom_items:
		return
	# compute average y
	total_y = 0.0
	for item in atom_items:
		total_y += item.atom_model.y
	avg_y = total_y / len(atom_items)
	# set all atoms to the average y
	for item in atom_items:
		item.atom_model.set_xyz(item.atom_model.x, avg_y, item.atom_model.z)


#============================================
def _align_vertical(atom_items: list) -> None:
	"""Align selected atoms to the same x-coordinate (average x).

	Args:
		atom_items: List of AtomItem instances to align.
	"""
	if not atom_items:
		return
	# compute average x
	total_x = 0.0
	for item in atom_items:
		total_x += item.atom_model.x
	avg_x = total_x / len(atom_items)
	# set all atoms to the average x
	for item in atom_items:
		item.atom_model.set_xyz(avg_x, item.atom_model.y, item.atom_model.z)


#============================================
def _mirror_horizontal(atom_items: list) -> None:
	"""Mirror selected atoms across a horizontal axis (flip y around centroid).

	Args:
		atom_items: List of AtomItem instances to mirror.
	"""
	if not atom_items:
		return
	# compute centroid y
	total_y = 0.0
	for item in atom_items:
		total_y += item.atom_model.y
	center_y = total_y / len(atom_items)
	# mirror each atom's y around the centroid
	for item in atom_items:
		new_y = 2.0 * center_y - item.atom_model.y
		item.atom_model.set_xyz(item.atom_model.x, new_y, item.atom_model.z)


#============================================
def _mirror_vertical(atom_items: list) -> None:
	"""Mirror selected atoms across a vertical axis (flip x around centroid).

	Args:
		atom_items: List of AtomItem instances to mirror.
	"""
	if not atom_items:
		return
	# compute centroid x
	total_x = 0.0
	for item in atom_items:
		total_x += item.atom_model.x
	center_x = total_x / len(atom_items)
	# mirror each atom's x around the centroid
	for item in atom_items:
		new_x = 2.0 * center_x - item.atom_model.x
		item.atom_model.set_xyz(new_x, item.atom_model.y, item.atom_model.z)
