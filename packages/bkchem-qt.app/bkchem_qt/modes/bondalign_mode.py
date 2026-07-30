"""Backend-authoritative atom alignment mode."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.modes.base_mode


ALIGN_HORIZONTAL = "horizontal"
ALIGN_VERTICAL = "vertical"
_SUBMODE_AXIS = {"tohoriz": ALIGN_HORIZONTAL, "tovert": ALIGN_VERTICAL}


#============================================
class BondAlignMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Submit selected durable atoms to the backend alignment operation."""

	#============================================
	def __init__(self, view: object, parent: PySide6.QtCore.QObject | None = None) -> None:
		"""Initialize the mode with its horizontal default."""
		super().__init__(view, parent)
		self._name = "bondalign"
		self._axis = ALIGN_HORIZONTAL
		self._atom_align_operation = None
		self._cursor = PySide6.QtCore.Qt.CursorShape.SizeAllCursor

	#============================================
	def set_atom_align_operation(self, operation: object | None) -> None:
		"""Install the session-owned atom-alignment client callback."""
		if operation is not None and not callable(operation):
			raise TypeError("Atom alignment operation must be callable")
		self._atom_align_operation = operation

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Map the two supported YAML controls to their exact backend axis."""
		if submode_index != 0:
			return
		axis = _SUBMODE_AXIS.get(name)
		if axis is None:
			self.status_message.emit("This transform is unavailable in the Qt release")
			return
		self._axis = axis
		self.status_message.emit("Align selected atoms %s" % axis)

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return the current bounded interaction guidance."""
		return "Select durable atoms then click to align %s" % self._axis

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Submit one selected direct-atom set without a local geometry command."""
		scene = self._env.scene
		if scene is None or self._atom_align_operation is None:
			self.status_message.emit("Alignment unavailable for this document")
			return
		targets = []
		for item in scene.selectedItems():
			if not isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
				continue
			atom_model = item.atom_model
			atom_id = atom_model.backend_durable_id
			molecule = getattr(atom_model, "_molecule_model", None)
			molecule_id = getattr(molecule, "mol_id", None)
			if not atom_id or not molecule_id:
				self.status_message.emit("Alignment unavailable: selected atom lacks durable identity")
				return
			targets.append((str(molecule_id), str(atom_id)))
		if not targets:
			self.status_message.emit("No atoms selected")
			return
		outcome = self._atom_align_operation(self._axis, tuple(targets))
		self.status_message.emit(outcome.message)
