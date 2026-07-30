"""Repair mode for normalizing molecular geometry.

Dispatches to repair_actions handlers based on the active submode.
Each submode maps to a geometry repair operation (normalize bond
lengths, snap to hex grid, etc.) that runs on submode selection
and on mouse click.
"""

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.actions.repair_actions


# maps submode keys from modes.yaml to handler functions
_REPAIR_HANDLERS = {
	'normalize-lengths': bkchem_qt.actions.repair_actions._handle_normalize_bond_lengths,
	'normalize-angles': bkchem_qt.actions.repair_actions._handle_normalize_bond_angles,
	'normalize-rings': bkchem_qt.actions.repair_actions._handle_normalize_rings,
	'straighten': bkchem_qt.actions.repair_actions._handle_straighten_bonds,
	'snap-hex': bkchem_qt.actions.repair_actions._handle_snap_to_hex_grid,
	'clean': bkchem_qt.actions.repair_actions._handle_clean_geometry,
}

_BACKEND_REPAIR_KEYS = frozenset((
	"normalize-angles", "normalize-lengths", "snap-hex", "clean",
))


#============================================
class RepairMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for normalizing bond lengths and angles via OASA.

	Each submode corresponds to a specific geometry repair operation.
	Selecting a submode runs the repair immediately. Clicking on the
	canvas re-runs the active submode's repair operation.

	Args:
		view: The ChemView widget that owns this mode.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view: object, parent: object = None) -> None:
		"""Initialize the repair mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Repair"
		# track the active submode key for click dispatch
		self._active_submode_key = None

	#============================================
	@property
	def status_hint(self) -> str:
		"""Return repair mode hint for the status bar.

		Returns:
			A short description of available interactions.
		"""
		return "Click a molecule to apply the active repair"

	#============================================
	def _run_handler(
			self, submode_key: str, target_molecule: object = None,
			) -> None:
		"""Look up and execute the repair handler for a submode key.

		Resolves the app reference from the view's parent window and
		dispatches to the matching handler function. Shows a status
		message if the submode key is not recognized.

		Args:
			submode_key: The submode key string from modes.yaml.
		"""
		handler = _REPAIR_HANDLERS.get(submode_key)
		if handler is None:
			self.status_message.emit(
				f"Repair mode: unknown submode '{submode_key}'"
			)
			return
		# get the main application window from the environment
		app = self._env.window
		if app is None:
			self.status_message.emit("Repair mode: no application window")
			return
		handler(app, target_molecule)

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Dispatch to the repair handler when a submode is selected.

		Stores the active submode key and immediately runs the
		corresponding repair operation.

		Args:
			submode_index: Group index of the changed submode.
			name: Key string of the newly selected submode.
		"""
		# remember the active submode for click re-dispatch
		self._active_submode_key = name
		self._run_handler(name)

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event: object) -> None:
		"""Re-run the active repair operation on mouse click.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._active_submode_key is None:
			self.status_message.emit("Repair mode: select a repair operation")
			return
		app = self._env.window
		scene = self._env.scene
		if app is None or scene is None:
			self.status_message.emit("Repair mode: no active document")
			return
		item = scene.itemAt(scene_pos, PySide6.QtGui.QTransform())
		if item is None:
			self.status_message.emit("Repair mode: click a molecule")
			return
		molecule = app.document.molecule_for_graphics_item(item)
		if molecule is None:
			self.status_message.emit("Repair mode: click a molecule")
			return
		if self._active_submode_key in _BACKEND_REPAIR_KEYS:
			# The backend route accepts durable identity only.  The accepted
			# commit replaces Qt's projection, so release old item/model wrappers
			# before the synchronous session submission begins.
			molecule_id = molecule.mol_id
			del item
			del molecule
			del scene
			handler = _REPAIR_HANDLERS[self._active_submode_key]
			handler(app, target_molecule_id=molecule_id)
			return
		self._run_handler(self._active_submode_key, molecule)
