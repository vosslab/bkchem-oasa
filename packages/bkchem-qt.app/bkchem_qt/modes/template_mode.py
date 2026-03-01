"""Template mode for applying molecular templates."""

# Standard Library
import logging

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.undo.commands

# module-level logger
_log = logging.getLogger(__name__)


#============================================
class TemplateMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for placing molecular group templates.

	Loads available template names from OASA known_groups and allows
	the user to click on the canvas to place a template at that
	position, or click on an existing atom to attach it there.

	Args:
		view: The ChemView widget that dispatches events.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize template mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "Template"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		self._current_template = None
		self._template_names = []
		self._load_templates()

	# ------------------------------------------------------------------
	# Template management
	# ------------------------------------------------------------------

	#============================================
	def _load_templates(self) -> None:
		"""Load available templates from OASA known_groups.

		Attempts to import oasa.known_groups and read the group name
		list. Logs a warning if the module is not available.
		"""
		try:
			import oasa.known_groups
			self._template_names = list(oasa.known_groups.name_to_smiles.keys())
		except (ImportError, AttributeError):
			_log.warning("Could not load OASA known_groups for templates")
			self._template_names = []

	#============================================
	def set_template(self, name: str) -> None:
		"""Set the current template by name.

		Args:
			name: Name of the template to activate.
		"""
		if name in self._template_names:
			self._current_template = name
			self.status_message.emit(f"Template: {name}")
		else:
			_log.warning("Unknown template name: %s", name)

	#============================================
	@property
	def template_names(self) -> list:
		"""Return list of available template names.

		Returns:
			List of template name strings.
		"""
		return list(self._template_names)

	# ------------------------------------------------------------------
	# Event handlers
	# ------------------------------------------------------------------

	#============================================
	def activate(self) -> None:
		"""Called when this mode becomes active."""
		super().activate()
		if self._current_template:
			msg = f"Template mode: {self._current_template}"
		else:
			msg = "Template mode: no template selected"
		self.status_message.emit(msg)

	#============================================
	def mouse_press(self, scene_pos: PySide6.QtCore.QPointF, event) -> None:
		"""Handle a mouse press to place or attach a template.

		If clicked on an existing atom, attaches the template to that
		atom. If clicked on empty space, places the template at that
		position.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._current_template is None:
			self.status_message.emit("No template selected")
			return
		# check if an atom is under the cursor
		item = self._item_at(scene_pos)
		if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem):
			self._place_template(item.atom_model.x, item.atom_model.y)
			self.status_message.emit(
				f"Placed template '{self._current_template}' at atom"
			)
		else:
			self._place_template(scene_pos.x(), scene_pos.y())
			self.status_message.emit(
				f"Placed template '{self._current_template}' at "
				f"({scene_pos.x():.0f}, {scene_pos.y():.0f})"
			)

	# ------------------------------------------------------------------
	# Placement helpers
	# ------------------------------------------------------------------

	#============================================
	def _place_template(self, x: float, y: float) -> None:
		"""Load and place a template molecule at the given position.

		Converts the template SMILES to an OASA molecule, generates
		coordinates, converts to a Qt MoleculeModel, repositions to
		(x, y), and adds all atoms and bonds to the scene with undo.

		Args:
			x: Target X coordinate in scene units.
			y: Target Y coordinate in scene units.
		"""
		import oasa.known_groups
		import oasa.smiles_lib
		import bkchem_qt.bridge.oasa_bridge
		import bkchem_qt.models.molecule_model

		smiles = oasa.known_groups.name_to_smiles.get(self._current_template)
		if smiles is None:
			self.status_message.emit(f"No SMILES for template: {self._current_template}")
			return

		# parse SMILES to OASA molecule with coordinate generation
		oasa_mol = oasa.smiles_lib.text_to_mol(smiles)
		if oasa_mol is None:
			self.status_message.emit(f"Failed to parse template: {self._current_template}")
			return

		# convert to Qt model (rescales and centers automatically)
		mol_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(oasa_mol)

		# compute current centroid and translate to target position
		atoms = mol_model.atoms
		if not atoms:
			return
		cx = sum(a.x for a in atoms) / len(atoms)
		cy = sum(a.y for a in atoms) / len(atoms)
		dx = x - cx
		dy = y - cy
		for a in atoms:
			a.set_xyz(a.x + dx, a.y + dy, a.z)

		# add to scene and document with undo support
		self._add_template_to_scene(mol_model)

	#============================================
	def _add_template_to_scene(self, mol_model) -> None:
		"""Add a template MoleculeModel to the scene with undo support.

		Creates AtomItem and BondItem graphics, registers the molecule
		with the document, and pushes grouped undo commands.

		Args:
			mol_model: The MoleculeModel to add.
		"""
		scene = self._view.scene()
		if scene is None:
			return
		# get or create document reference
		view = self._view
		if not hasattr(view, "document") or view.document is None:
			return
		doc = view.document
		undo_stack = doc.undo_stack
		# register molecule with document
		doc.add_molecule(mol_model)
		# group all additions into a single undo macro
		undo_stack.beginMacro(f"Place template {self._current_template}")
		# create atom items and add via undo commands
		atom_items = {}
		for atom_model in mol_model.atoms:
			atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(atom_model)
			scene.addItem(atom_item)
			atom_items[id(atom_model)] = atom_item
		# create bond items
		for bond_model in mol_model.bonds:
			bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
			scene.addItem(bond_item)
		undo_stack.endMacro()
