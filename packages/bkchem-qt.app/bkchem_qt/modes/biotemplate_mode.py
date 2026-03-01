"""Biomolecule template mode for placing biomolecule SMILES templates."""

# Standard Library
import logging

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.modes.base_mode
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item

# module-level logger
_log = logging.getLogger(__name__)


#============================================
class BioTemplateMode(bkchem_qt.modes.base_mode.BaseMode):
	"""Mode for placing biomolecule templates from YAML SMILES data.

	Loads biomolecule entries via biomolecule_loader and organizes
	them into category and template submode groups. Selecting a
	category filters the template grid to show matching molecules.

	Args:
		view: The ChemView widget that dispatches events.
		parent: Optional parent QObject.
	"""

	#============================================
	def __init__(self, view, parent=None):
		"""Initialize biomolecule template mode.

		Args:
			view: The ChemView widget that dispatches events.
			parent: Optional parent QObject.
		"""
		super().__init__(view, parent)
		self._name = "biomolecule templates"
		self._cursor = PySide6.QtCore.Qt.CursorShape.CrossCursor
		self._current_smiles = None
		self._current_template_name = None

		# biomolecule data structures
		self._category_keys = []
		self._category_labels = []
		self._category_label_to_key = {}
		self._category_template_names = {}
		self._category_template_labels = {}
		self._category_template_smiles = {}

		# load biomolecule entries and build categorized submodes
		self._load_biomolecules()

	# ------------------------------------------------------------------
	# Biomolecule loading
	# ------------------------------------------------------------------

	#============================================
	def _load_biomolecules(self) -> None:
		"""Load biomolecule entries and build categorized submode data.

		Uses bkchem.biomolecule_loader to read the YAML file, then
		groups entries by category for the two-level submode system.
		"""
		entries = self._load_entries()
		if not entries:
			_log.warning("No biomolecule entries loaded")
			return
		self._build_categorized_submodes(entries)

	#============================================
	def _load_entries(self) -> list:
		"""Load biomolecule entries from the YAML file.

		Returns:
			List of entry dicts with category, name, label, smiles keys.
		"""
		import bkchem.biomolecule_loader
		return bkchem.biomolecule_loader.load_biomolecule_entries()

	#============================================
	def _build_categorized_submodes(self, entries: list) -> None:
		"""Build category and template submode groups from entries.

		Group 0 is the category row. Group 1 is the template grid
		filtered by the selected category.

		Args:
			entries: List of biomolecule entry dicts.
		"""
		# group entries by category, preserving insertion order
		category_order = []
		category_entries = {}
		for entry in entries:
			cat = entry['category']
			if cat not in category_entries:
				category_order.append(cat)
				category_entries[cat] = []
			category_entries[cat].append(entry)

		self._category_keys = category_order
		# build display labels from category keys
		self._category_labels = [
			k.replace('_', ' ').strip() for k in self._category_keys
		]
		self._category_label_to_key = dict(
			zip(self._category_labels, self._category_keys)
		)

		# build per-category template data
		for key in self._category_keys:
			cat_entries = category_entries[key]
			names = []
			labels = []
			smiles_list = []
			for entry in cat_entries:
				names.append(entry['name'])
				labels.append(entry['label'])
				smiles_list.append(entry['smiles'])
			self._category_template_names[key] = names
			self._category_template_labels[key] = labels
			self._category_template_smiles[key] = smiles_list

		# apply initial category selection
		initial_names = []
		initial_labels = []
		if self._category_keys:
			first_key = self._category_keys[0]
			initial_names = list(
				self._category_template_names.get(first_key, [])
			)
			initial_labels = list(
				self._category_template_labels.get(first_key, [])
			)

		# set submode data for the ribbon widget
		# group 0 = categories, group 1 = templates
		self.submodes = [list(self._category_labels), initial_names]
		self.submodes_names = [
			list(self._category_labels), initial_labels
		]
		self.submode = [0, 0]
		self.group_layouts = ['row', 'grid']
		self.group_labels = ['Category', 'Templates']

		# build tooltip map for template names
		for key in self._category_keys:
			for mol_name in self._category_template_names.get(key, []):
				self.tooltip_map[mol_name] = mol_name.replace('_', ' ')

		# set initial template SMILES from first entry
		if initial_names and self._category_keys:
			first_key = self._category_keys[0]
			smiles = self._category_template_smiles.get(first_key, [])
			if smiles:
				self._current_smiles = smiles[0]
				self._current_template_name = initial_names[0]

	# ------------------------------------------------------------------
	# Submode switching
	# ------------------------------------------------------------------

	#============================================
	def on_submode_switch(self, submode_index: int, name: str) -> None:
		"""Handle submode selection changes.

		When group 0 (category) changes, rebuild group 1 templates.
		When group 1 (template) changes, set the active SMILES.

		Args:
			submode_index: Group index of the changed submode.
			name: Key string of the newly selected submode.
		"""
		if submode_index == 0:
			# category changed: update template list for group 1
			self._apply_category_selection(name)
			# refresh the ribbon widget for group 1
			main_window = self._view.window()
			if hasattr(main_window, '_submode_ribbon'):
				main_window._submode_ribbon.refresh_group(1)
		elif submode_index == 1:
			# template selected: resolve SMILES for placement
			self._apply_template_selection(name)

	#============================================
	def _apply_category_selection(self, label: str) -> None:
		"""Update template lists for the selected category label.

		Args:
			label: Display label of the selected category.
		"""
		key = self._category_label_to_key.get(label)
		if not key and self._category_keys:
			key = self._category_keys[0]
		if not key:
			return

		# update group 1 submode data in place
		new_names = list(
			self._category_template_names.get(key, [])
		)
		new_labels = list(
			self._category_template_labels.get(key, [])
		)
		self.submodes[1] = new_names
		self.submodes_names[1] = new_labels
		# reset template selection to first entry
		if new_names:
			self.submode[1] = 0
			smiles = self._category_template_smiles.get(key, [])
			if smiles:
				self._current_smiles = smiles[0]
				self._current_template_name = new_names[0]
		else:
			self._current_smiles = None
			self._current_template_name = None

	#============================================
	def _apply_template_selection(self, name: str) -> None:
		"""Set the current template SMILES from the selected name.

		Args:
			name: Template name key from the submode.
		"""
		# find which category contains this template
		for key in self._category_keys:
			names = self._category_template_names.get(key, [])
			if name in names:
				idx = names.index(name)
				smiles = self._category_template_smiles.get(key, [])
				if idx < len(smiles):
					self._current_smiles = smiles[idx]
					self._current_template_name = name
					self.status_message.emit(
						f"Template: {name}"
					)
				return
		_log.warning("Unknown template name: %s", name)

	# ------------------------------------------------------------------
	# Event handlers
	# ------------------------------------------------------------------

	#============================================
	def activate(self) -> None:
		"""Called when this mode becomes active."""
		super().activate()
		if self._current_template_name:
			msg = f"Biomolecule mode: {self._current_template_name}"
		else:
			msg = "Biomolecule mode: no template selected"
		self.status_message.emit(msg)

	#============================================
	def mouse_press(
		self, scene_pos: PySide6.QtCore.QPointF, event
	) -> None:
		"""Handle a mouse press to place a biomolecule template.

		Args:
			scene_pos: Position in scene coordinates.
			event: The mouse event.
		"""
		if self._current_smiles is None:
			self.status_message.emit("No template selected")
			return
		# check if an atom is under the cursor
		item = self._item_at(scene_pos)
		if isinstance(
			item, bkchem_qt.canvas.items.atom_item.AtomItem
		):
			self._place_template(
				item.atom_model.x, item.atom_model.y
			)
		else:
			self._place_template(scene_pos.x(), scene_pos.y())

	# ------------------------------------------------------------------
	# Placement helpers
	# ------------------------------------------------------------------

	#============================================
	def _place_template(self, x: float, y: float) -> None:
		"""Load and place a biomolecule template at the given position.

		Parses the current SMILES to an OASA molecule, generates
		coordinates, converts to a Qt MoleculeModel, repositions
		to (x, y), and adds to the scene with undo.

		Args:
			x: Target X coordinate in scene units.
			y: Target Y coordinate in scene units.
		"""
		import oasa.smiles_lib
		import bkchem_qt.bridge.oasa_bridge
		import bkchem_qt.models.molecule_model

		# parse SMILES to OASA molecule with coordinate generation
		oasa_mol = oasa.smiles_lib.text_to_mol(self._current_smiles)
		if oasa_mol is None:
			self.status_message.emit(
				f"Failed to parse: {self._current_template_name}"
			)
			return

		# convert to Qt model (rescales and centers automatically)
		mol_model = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(
			oasa_mol
		)

		# compute centroid and translate to target position
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
		self.status_message.emit(
			f"Placed: {self._current_template_name}"
		)

	#============================================
	def _add_template_to_scene(self, mol_model) -> None:
		"""Add a template MoleculeModel to the scene with undo.

		Creates AtomItem and BondItem graphics, registers the
		molecule with the document, and pushes grouped undo commands.

		Args:
			mol_model: The MoleculeModel to add.
		"""
		scene = self._view.scene()
		if scene is None:
			return
		view = self._view
		if not hasattr(view, "document") or view.document is None:
			return
		doc = view.document
		undo_stack = doc.undo_stack
		# register molecule with document
		doc.add_molecule(mol_model)
		# group all additions into a single undo macro
		template_name = self._current_template_name or "biomolecule"
		undo_stack.beginMacro(f"Place {template_name}")
		# create atom items
		for atom_model in mol_model.atoms:
			atom_item = bkchem_qt.canvas.items.atom_item.AtomItem(
				atom_model
			)
			scene.addItem(atom_item)
		# create bond items
		for bond_model in mol_model.bonds:
			bond_item = bkchem_qt.canvas.items.bond_item.BondItem(
				bond_model
			)
			scene.addItem(bond_item)
		undo_stack.endMacro()
