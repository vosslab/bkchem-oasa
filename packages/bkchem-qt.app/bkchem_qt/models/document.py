"""Document model holding molecules and providing undo support."""

# Standard Library
import os
import typing

# PIP3 modules
import PySide6.QtCore
import PySide6.QtGui
import PySide6.QtWidgets
import shiboken6

# local repo modules
import oasa.safe_xml
import bkchem_qt.models.molecule_model
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.document_object

if typing.TYPE_CHECKING:
	import bkchem_qt.canvas.graphics_retirement


#============================================
class DocumentUndoStack(PySide6.QtGui.QUndoStack):
	"""Keep terminal undo-history disposal under the owning Document.

	Qt retains graphics wrappers in structural commands while they remain
	undoable.  When a new command replaces an undone redo branch, however, Qt
	destroys those commands immediately.  This small history surface gives the
	Document a last explicit opportunity to retire the branch's already-detached
	graphics before Qt releases the commands themselves.
	"""

	#============================================
	def __init__(self, document: "Document") -> None:
		"""Create a QUndoStack whose terminal history transitions use ``document``."""
		super().__init__(document)

	#============================================
	def _owner(self) -> "Document":
		"""Return the still-live QObject parent that owns this history surface."""
		document = self.parent()
		if not isinstance(document, Document):
			raise RuntimeError("Document undo history has no live document owner")
		return document

	#============================================
	def push(self, command: PySide6.QtGui.QUndoCommand) -> None:
		"""Retire an obsolete redo branch before accepting its replacement."""
		self._owner()._retire_discarded_redo_graphics()
		super().push(command)

	#============================================
	def clear(self) -> None:
		"""Retire detached command graphics before Qt clears its history."""
		self._owner()._retire_all_history_graphics()
		super().clear()

	#============================================
	def setUndoLimit(self, limit: int) -> None:
		"""Keep graphics-retaining history unlimited until eviction is explicit.

		Qt may evict commands without a Python callback when a finite undo limit is
		configured.  The current history contract is unlimited, so rejecting a
		finite value makes a future eviction implementation choose and test its own
		terminal graphics handoff rather than silently dropping native wrappers.
		"""
		if limit != 0:
			raise ValueError(
				"Document undo history requires unlimited capacity until eviction "
				"owns graphics retirement",
			)
		super().setUndoLimit(limit)


#============================================
class Document(PySide6.QtCore.QObject):
	"""Top-level document that holds molecules, file state, and undo stack.

	The Document is the Qt projection's owner for the object stack, undo
	history, and local file state.  Persistent CDML authority remains in the
	backend session; this object records only the live frontend projection.
	Selection state lives in the QGraphicsScene but Document provides query
	helpers that give modes chemistry-aware access to the selection.

	Emits ``modified_changed`` whenever the dirty flag transitions so the
	window title can show an unsaved-changes indicator. Emits
	``selection_changed`` after selection queries detect a change.

	Args:
		parent: Optional parent QObject.
	"""

	# emitted when the dirty flag changes
	modified_changed = PySide6.QtCore.Signal(bool)
	# emitted when the selection changes (forwarded from scene)
	selection_changed = PySide6.QtCore.Signal()
	# emitted when top-level CDML content is inserted or removed
	object_added = PySide6.QtCore.Signal(object)
	object_removed = PySide6.QtCore.Signal(object)
	# emitted when a mark is inserted or removed
	mark_added = PySide6.QtCore.Signal(object)
	mark_removed = PySide6.QtCore.Signal(object)
	# emitted after paper or viewport state changes
	paper_changed = PySide6.QtCore.Signal(object)
	# emitted after every Qt-local persistent mutation boundary advances
	persistent_mutated = PySide6.QtCore.Signal(int)

	#============================================
	def __init__(self, parent: PySide6.QtCore.QObject | None = None) -> None:
		"""Initialize an empty document.

		Args:
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		self._molecules = []
		self._object_stack = []
		self._presentation_objects = []
		self._marks = []
		self._paper = bkchem_qt.models.document_object.PaperModel()
		self._cdml_envelope = bkchem_qt.models.document_object.CdmlEnvelope()
		self._unsupported_content = []
		self._file_path = None
		self._undo_stack = DocumentUndoStack(self)
		self._graphics_retirement_reaper = None
		self._persistent_generation = 0
		# Undoable edits use QUndoStack's clean point. Direct structural
		# mutations remain supported while older actions are migrated.
		self._direct_dirty = False
		self._dirty = False
		self._undo_stack.cleanChanged.connect(self._on_undo_clean_changed)
		self._undo_stack.indexChanged.connect(self._on_undo_index_changed)
		# scene reference for selection queries (set by MainWindow)
		self._scene = None

	# ------------------------------------------------------------------
	# Properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def molecules(self) -> list:
		"""Return the list of MoleculeModel instances in this document.

		Returns:
			List of MoleculeModel objects.
		"""
		return list(self._molecules)

	#============================================
	@property
	def objects(self) -> list:
		"""Return the ordered top-level molecule and presentation stack."""
		return list(self._object_stack)

	#============================================
	@property
	def presentation_objects(self) -> list:
		"""Return non-molecule drawable CDML objects."""
		return list(self._presentation_objects)

	#============================================
	@property
	def marks(self) -> list:
		"""Return atom-attached CDML mark models."""
		return list(self._marks)

	#============================================
	@property
	def paper(self) -> bkchem_qt.models.document_object.PaperModel:
		"""Return preserved paper and viewport state."""
		return self._paper

	#============================================
	@property
	def cdml_envelope(self) -> bkchem_qt.models.document_object.CdmlEnvelope:
		"""Return preserved document-level CDML content."""
		return self._cdml_envelope

	#============================================
	@property
	def unsupported_content(self) -> list:
		"""Return retained CDML content not yet projected by the Qt UI."""
		return list(self._unsupported_content)

	#============================================
	@property
	def file_path(self) -> str | None:
		"""Absolute path to the saved file, or None if unsaved.

		Returns:
			str or None.
		"""
		return self._file_path

	#============================================
	@file_path.setter
	def file_path(self, value: str | None) -> None:
		self._file_path = value

	#============================================
	@property
	def dirty(self) -> bool:
		"""Whether the document has unsaved changes."""
		return self._direct_dirty or not self._undo_stack.isClean()

	#============================================
	@dirty.setter
	def dirty(self, value: bool) -> None:
		"""Set or clear the document's compatibility dirty state.

		New persistent edits should use undo commands. The true branch remains
		available for older direct-mutation paths so they cannot bypass close
		guards while those paths are migrated.
		"""
		if value:
			self.mark_dirty()
			return
		self.mark_clean()

	#============================================
	@property
	def undo_stack(self) -> PySide6.QtGui.QUndoStack:
		"""The QUndoStack for undo/redo operations.

		Returns:
			QUndoStack instance owned by this document.
		"""
		return self._undo_stack

	#============================================
	def set_graphics_retirement_reaper(
			self,
			reaper: "bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper | None",
			) -> None:
		"""Assign this projection's session-owned terminal graphics reaper.

		The reaper is a frontend lifetime capability rather than a backend-facing
		contract.  A bare Document uses the process reaper; a live session supplies
		its own record so failed history retirement survives tab replacement and
		then transfers through the existing MainWindow chain.
		"""
		self._graphics_retirement_reaper = reaper

	#============================================
	def _retire_discarded_redo_graphics(self) -> None:
		"""Terminally retire detached graphics in the redo branch Qt will prune."""
		if self._undo_stack.index() >= self._undo_stack.count():
			return
		commands = [
			self._undo_stack.command(index)
			for index in range(self._undo_stack.index(), self._undo_stack.count())
		]
		self._retire_detached_history_graphics(commands)

	#============================================
	def _retire_all_history_graphics(self) -> None:
		"""Terminally retire every detached item no longer needed after clear."""
		commands = [
			self._undo_stack.command(index)
			for index in range(self._undo_stack.count())
		]
		self._retire_detached_history_graphics(commands)

	#============================================
	def _retire_detached_history_graphics(
			self, commands: list[PySide6.QtGui.QUndoCommand],
			) -> None:
		"""Retire only command trees already detached from the live scene.

		Applied commands may retain graphics still owned by the live scene.  Clear
		must leave those projections to their scene owner, while an undone redo
		branch has detached roots that lose their only future owner when Qt drops
		the commands.  Snapshot every candidate before the terminal coordinator
		changes any native parent relationship.
		"""
		reaper = self._effective_terminal_graphics_reaper()
		items = []
		seen_commands = set()
		seen_items = set()

		#============================================
		def visit(command: PySide6.QtGui.QUndoCommand) -> None:
			"""Collect graphics from one command and its macro children."""
			if id(command) in seen_commands:
				return
			seen_commands.add(id(command))
			graphics_items = getattr(command, "graphics_items", None)
			if callable(graphics_items):
				for item in graphics_items():
					if id(item) in seen_items:
						continue
					seen_items.add(id(item))
					# A failed terminal transition already has one durable owner.
					# This history scan must not inspect its scene or begin another
					# deletion attempt before the reaper's controlled resolution pass.
					if self._terminal_reaper_owns_graphics_root(item, reaper):
						continue
					if not shiboken6.isValid(item):
						continue
					# This is the stable pre-retirement ownership check.  No
					# item is touched again after the coordinator begins deletion.
					try:
						is_detached = item.scene() is None
					except RuntimeError:
						is_detached = False
					if is_detached:
						items.append(item)
			for index in range(command.childCount()):
				visit(command.child(index))

		for command in commands:
			visit(command)
		if not items:
			return
		from bkchem_qt.canvas.graphics_retirement import GraphicsRetirementCoordinator
		coordinator = GraphicsRetirementCoordinator()
		coordinator.retire_detached_projection_items(
			items, reaper,
		)

	#============================================
	def _effective_terminal_graphics_reaper(
			self,
			) -> "bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper":
		"""Return the sole long-lived owner for failed terminal graphics.

		Live sessions install their own reaper so tab teardown can transfer every
		unresolved record to MainWindow.  A standalone Document has no session
		owner, so it deliberately uses the process reaper for both failed-root
		transfer and every later history ownership check.
		"""
		if self._graphics_retirement_reaper is not None:
			return self._graphics_retirement_reaper
		from bkchem_qt.canvas.graphics_retirement import (
			detached_graphics_retirement_reaper,
		)
		return detached_graphics_retirement_reaper

	#============================================
	def _terminal_reaper_owns_graphics_root(
			self,
			item: PySide6.QtWidgets.QGraphicsItem,
			reaper: "bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper | None" = None,
			) -> bool:
		"""Return whether an earlier terminal transition exclusively owns ``item``.

		The reaper uses Python identity only.  This check runs before history asks
		the wrapper for scene ownership, so a failed terminal deletion cannot be
		rediscovered by a later undo-stack clear.
		"""
		effective_reaper = reaper or self._effective_terminal_graphics_reaper()
		return (
			effective_reaper.owns_detached_root(item)
			or effective_reaper.owns_scene_projection_root(item)
		)

	#============================================
	@property
	def persistent_generation(self) -> int:
		"""Return this projection's monotonic persistent-mutation generation."""
		return self._persistent_generation

	#============================================
	def mark_clean(self) -> None:
		"""Mark the current undo-stack position as the saved document state."""
		self._direct_dirty = False
		self._undo_stack.setClean()
		self._sync_dirty_state()

	#============================================
	def mark_dirty(self) -> None:
		"""Mark a direct, non-command mutation as unsaved."""
		self._advance_persistent_generation()
		self._direct_dirty = True
		self._sync_dirty_state()

	#============================================
	def unique_cdml_id(self, prefix: str) -> str:
		"""Return a document-global CDML identifier using a stable prefix.

		IDs share one XML namespace across molecule metadata, atoms, bonds, and
		top-level objects.  Retained raw fragments are parsed safely so a new
		editable fragment cannot silently collide with lossless raw XML.
		"""
		used = self._used_cdml_ids()
		index = 1
		candidate = "%s%d" % (prefix, index)
		while candidate in used:
			index += 1
			candidate = "%s%d" % (prefix, index)
		return candidate

	#============================================
	def planned_fragment_id_changes(
			self, molecule: bkchem_qt.models.molecule_model.MoleculeModel,
			) -> tuple[tuple[tuple[object, str, str], ...], tuple[tuple[object, str, str], ...]]:
		"""Plan global-safe atom and bond IDs without mutating live models."""
		used = self._used_cdml_ids(exclude_molecule=molecule)
		if molecule.mol_id:
			used.add(molecule.mol_id)
		used.update(fragment.fragment_id for fragment in molecule.fragments)
		for raw_xml in molecule.unsupported_fragment_xml:
			used.update(self._raw_fragment_ids(raw_xml))
		atom_changes = self._planned_model_ids(molecule.atoms, "_chem_atom", "atom", used)
		bond_changes = self._planned_model_ids(molecule.bonds, "_chem_bond", "bond", used)
		return tuple(atom_changes), tuple(bond_changes)

	#============================================
	def _used_cdml_ids(
			self, exclude_molecule: bkchem_qt.models.molecule_model.MoleculeModel | None = None,
			) -> set[str]:
		"""Collect IDs from durable projected and retained document content."""
		used = set()
		for molecule in self._molecules:
			if molecule is exclude_molecule:
				continue
			if molecule.mol_id:
				used.add(molecule.mol_id)
			for atom_model in molecule.atoms:
				identifier = str(getattr(atom_model._chem_atom, "id", "") or "")
				if identifier:
					used.add(identifier)
			for bond_model in molecule.bonds:
				identifier = str(getattr(bond_model._chem_bond, "id", "") or "")
				if identifier:
					used.add(identifier)
			for group_model in molecule.groups:
				if group_model.group_id:
					used.add(group_model.group_id)
			for fragment in molecule.fragments:
				used.add(fragment.fragment_id)
			for raw_xml in molecule.unsupported_fragment_xml:
				used.update(self._raw_fragment_ids(raw_xml))
		for object_model in self._presentation_objects:
			if object_model.object_id:
				used.add(object_model.object_id)
		for unsupported in self._unsupported_content:
			if unsupported.object_id:
				used.add(unsupported.object_id)
		return used

	#============================================
	def _raw_fragment_ids(self, raw_xml: str) -> set[str]:
		"""Read retained raw fragment IDs without treating XML as text."""
		try:
			element = oasa.safe_xml.parse_dom_from_string(raw_xml).documentElement
		except ValueError:
			return set()
		identifier = element.getAttribute("id")
		return {identifier} if identifier else set()

	#============================================
	def _planned_model_ids(
			self, models: list, chemistry_name: str, prefix: str, used: set[str],
			) -> list[tuple[object, str, str]]:
		"""Return deterministic before/after IDs while reserving each result."""
		changes = []
		for model in models:
			chemistry = getattr(model, chemistry_name)
			before = str(getattr(chemistry, "id", "") or "")
			after = before
			if not after or after in used:
				index = 1
				after = "%s%d" % (prefix, index)
				while after in used:
					index += 1
					after = "%s%d" % (prefix, index)
			used.add(after)
			changes.append((model, before, after))
		return changes

	#============================================
	def _on_undo_clean_changed(self, _clean: bool) -> None:
		"""Emit document modification changes from the undo stack clean state."""
		self._sync_dirty_state()

	#============================================
	def _on_undo_index_changed(self, _index: int) -> None:
		"""Record every command-stack position transition as persistent state."""
		self._advance_persistent_generation()

	#============================================
	def _advance_persistent_generation(self) -> None:
		"""Advance and publish Qt-local persistent mutation provenance."""
		self._persistent_generation += 1
		self.persistent_mutated.emit(self._persistent_generation)

	#============================================
	def _sync_dirty_state(self) -> None:
		"""Emit a transition when combined direct/undo dirty state changes."""
		dirty = self.dirty
		if dirty != self._dirty:
			self._dirty = dirty
			self.modified_changed.emit(dirty)

	# ------------------------------------------------------------------
	# Scene wiring
	# ------------------------------------------------------------------

	#============================================
	def set_scene(self, scene: PySide6.QtWidgets.QGraphicsScene | None) -> None:
		"""Wire the scene for selection change forwarding.

		Connects the scene's selectionChanged signal so Document can
		re-emit it as ``selection_changed`` for menu predicates and
		mode state updates.

		Args:
			scene: QGraphicsScene instance (ChemScene).
		"""
		if self._scene is not None:
			# disconnect old scene
			self._scene.selectionChanged.disconnect(self._on_scene_selection_changed)
		self._scene = scene
		if scene is not None:
			scene.selectionChanged.connect(self._on_scene_selection_changed)

	#============================================
	def _on_scene_selection_changed(self) -> None:
		"""Forward scene selection changes as a Document signal."""
		self.selection_changed.emit()

	# ------------------------------------------------------------------
	# Selection queries
	# ------------------------------------------------------------------

	#============================================
	@property
	def selected_atoms(self) -> list:
		"""Return selected AtomItems from the scene.

		Returns:
			List of AtomItem instances currently selected.
		"""
		import bkchem_qt.canvas.items.atom_item
		if self._scene is None:
			return []
		return [item for item in self._scene.selectedItems()
				if isinstance(item, bkchem_qt.canvas.items.atom_item.AtomItem)]

	#============================================
	@property
	def selected_bonds(self) -> list:
		"""Return selected BondItems from the scene.

		Returns:
			List of BondItem instances currently selected.
		"""
		import bkchem_qt.canvas.items.bond_item
		if self._scene is None:
			return []
		return [item for item in self._scene.selectedItems()
				if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem)]

	#============================================
	@property
	def selected_groups(self) -> list:
		"""Return selected native CDML group items in scene selection order."""
		import bkchem_qt.canvas.items.group_item
		if self._scene is None:
			return []
		return [item for item in self._scene.selectedItems()
				if isinstance(item, bkchem_qt.canvas.items.group_item.GroupItem)]

	#============================================
	@property
	def groups_selected(self) -> bool:
		"""Whether selection contains at least one group for menu predicates."""
		return bool(self.selected_groups)

	#============================================
	@property
	def selected_mols(self) -> list:
		"""Return MoleculeModels that have at least one selected atom.

		Deduplicates so each molecule appears at most once.

		Returns:
			List of MoleculeModel instances with selected content.
		"""
		seen = set()
		result = []
		for atom_item in self.selected_atoms:
			mol = self._find_molecule_for_atom(atom_item.atom_model)
			if mol is not None and id(mol) not in seen:
				seen.add(id(mol))
				result.append(mol)
		return result

	#============================================
	@property
	def selected_presentation_objects(self) -> list:
		"""Return selected presentation objects in canonical document order.

		The scene is only an interaction surface: its selected-item order and
		z-order must never become the persistence order for CDML objects.

		Returns:
			Selected PresentationObject instances in ``Document.objects`` order.
		"""
		if self._scene is None:
			return []
		selected_ids = {
			id(getattr(item, "document_object_model", None))
			for item in self._scene.selectedItems()
		}
		return [
			object_model for object_model in self._object_stack
			if (
				isinstance(
					object_model,
					bkchem_qt.models.document_object.PresentationObject,
				)
				and id(object_model) in selected_ids
			)
		]

	#============================================
	@property
	def selected_presentation_stack_root_ids(self) -> tuple[str, ...]:
		"""Return durable selected presentation roots only when every item is valid.

		Stack reordering is deliberately stricter than ordinary presentation
		selection: every selected scene item must directly identify one supported,
		durable presentation model owned by this exact document.  Child graphics,
		molecule projections, marks, foreign wrappers, and ID-less records make the
		whole request ineligible rather than being silently discarded.
		"""
		# The projection boundary owns proof that a graphics item is a real binding,
		# not merely an arbitrary item carrying a lookalike model attribute.
		import bkchem_qt.canvas.document_projection
		return bkchem_qt.canvas.document_projection.selected_presentation_stack_root_ids(
			self, self._scene,
		)

	#============================================
	@property
	def selected_top_level_objects(self) -> list:
		"""Return selected molecules and artwork in canonical document order.

		Atoms, bonds, and atom-attached marks resolve to the molecule that owns
		their model.  Presentation graphics resolve through their explicit
		``document_object_model`` identity.  This keeps commands independent of
		the incidental order returned by ``QGraphicsScene.selectedItems()``.

		Returns:
			Selected molecule and presentation models in ``Document.objects`` order.
		"""
		if self._scene is None:
			return []
		selected_ids = set()
		for item in self._scene.selectedItems():
			object_model = getattr(item, "document_object_model", None)
			if object_model in self._presentation_objects:
				selected_ids.add(id(object_model))
			molecule = self.molecule_for_graphics_item(item)
			if molecule is not None:
				selected_ids.add(id(molecule))
		return [
			object_model for object_model in self._object_stack
			if id(object_model) in selected_ids
		]

	#============================================
	@property
	def selected_direct_root_molecule_ids(self) -> tuple[str, ...]:
		"""Return one durable molecule ID per supported selected root.

		This is a frontend selection bridge, not a chemistry conversion.  It
		uses the canonical top-level selection resolver so an atom, bond, or
		attached mark selects its owning direct-root molecule.  This root-only
		observation needs the molecule's durable ID, not a durable child ID:
		compatibility-loaded ID-less children can therefore observe their durable
		root without becoming child-addressable.  A presentation selection or
		mixed molecule/presentation selection is deliberately not a usable
		molecule query target.

		Returns:
			Durable direct-root molecule IDs in canonical document order, or an
			empty tuple when the selection is not wholly supported.
		"""
		objects = self.selected_top_level_objects
		if not objects:
			return ()
		if any(
			not isinstance(object_model, bkchem_qt.models.molecule_model.MoleculeModel)
			or not object_model.mol_id
			for object_model in objects
		):
			return ()
		return tuple(object_model.mol_id for object_model in objects)

	#============================================
	@property
	def has_selection(self) -> bool:
		"""Whether any interactive item is selected."""
		if self._scene is None:
			return False
		return bool(self._scene.selectedItems())

	#============================================
	def selected_to_unique_top_levels(self) -> tuple:
		"""Dedup selected items to their parent containers.

		Port of Tk paper_selection.selected_to_unique_top_levels().
		Maps atoms and bonds to their parent MoleculeModel, removing
		duplicates. Returns (unique_top_levels, is_unique) where
		is_unique is True when each container had at most one selected
		child.

		Returns:
			Tuple of (list of unique top-level objects, bool is_unique).
		"""
		filtrate = []
		unique = True
		seen_ids = set()
		for atom_item in self.selected_atoms:
			mol = self._find_molecule_for_atom(atom_item.atom_model)
			if mol is not None:
				if id(mol) not in seen_ids:
					seen_ids.add(id(mol))
					filtrate.append(mol)
				else:
					unique = False
		for bond_item in self.selected_bonds:
			mol = self._find_molecule_for_bond(bond_item.bond_model)
			if mol is not None:
				if id(mol) not in seen_ids:
					seen_ids.add(id(mol))
					filtrate.append(mol)
				else:
					unique = False
		return (filtrate, unique)

	#============================================
	@property
	def one_mol_selected(self) -> bool:
		"""Whether exactly one molecule has selected content."""
		return len(self.selected_mols) == 1

	#============================================
	def bonds_to_update(self) -> list:
		"""Return bonds adjacent to selected atoms that need redraw.

		Port of Tk paper_selection.bonds_to_update(). Finds bonds
		connected to any selected atom, excluding bonds that are
		themselves selected.

		Returns:
			List of BondModel instances needing update.
		"""
		import bkchem_qt.canvas.items.bond_item
		if self._scene is None:
			return []
		# collect selected atom models
		selected_atom_models = set()
		for atom_item in self.selected_atoms:
			selected_atom_models.add(id(atom_item.atom_model))
		# collect selected bond models to exclude
		selected_bond_models = set()
		for bond_item in self.selected_bonds:
			selected_bond_models.add(id(bond_item.bond_model))
		# find bonds connected to selected atoms but not themselves selected
		result = []
		for item in self._scene.items():
			if not isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
				continue
			bm = item.bond_model
			if id(bm) in selected_bond_models:
				continue
			if bm.atom1 is not None and id(bm.atom1) in selected_atom_models:
				result.append(bm)
			elif bm.atom2 is not None and id(bm.atom2) in selected_atom_models:
				result.append(bm)
		return result

	#============================================
	def atoms_to_update(self) -> list:
		"""Return atoms adjacent to selected bonds that need redraw.

		Port of Tk paper_selection.atoms_to_update(). Finds atoms
		connected to any selected bond, excluding atoms that are
		themselves selected.

		Returns:
			List of AtomModel instances needing update.
		"""
		# collect selected atom models to exclude
		selected_atom_models = set()
		for atom_item in self.selected_atoms:
			selected_atom_models.add(id(atom_item.atom_model))
		# find atoms connected to selected bonds but not themselves selected
		seen = set()
		result = []
		for bond_item in self.selected_bonds:
			bm = bond_item.bond_model
			for atom_model in (bm.atom1, bm.atom2):
				if atom_model is None:
					continue
				if id(atom_model) in selected_atom_models:
					continue
				if id(atom_model) not in seen:
					seen.add(id(atom_model))
					result.append(atom_model)
		return result

	#============================================
	def _find_molecule_for_atom(
			self, atom_model: bkchem_qt.models.atom_model.AtomModel,
			) -> bkchem_qt.models.molecule_model.MoleculeModel | None:
		"""Find the MoleculeModel containing a given AtomModel.

		Args:
			atom_model: AtomModel to search for.

		Returns:
			MoleculeModel or None.
		"""
		for mol_model in self._molecules:
			if atom_model in mol_model.atoms:
				return mol_model
		return None

	#============================================
	def _find_molecule_for_bond(
			self, bond_model: bkchem_qt.models.bond_model.BondModel,
			) -> bkchem_qt.models.molecule_model.MoleculeModel | None:
		"""Find the MoleculeModel containing a given BondModel.

		Args:
			bond_model: BondModel to search for.

		Returns:
			MoleculeModel or None.
		"""
		for mol_model in self._molecules:
			if bond_model in mol_model.bonds:
				return mol_model
		return None

	#============================================
	def molecule_for_graphics_item(
			self, item: PySide6.QtWidgets.QGraphicsItem,
			) -> bkchem_qt.models.molecule_model.MoleculeModel | None:
		"""Resolve a graphics item to its document-owned molecule model."""
		molecule = getattr(item, "molecule_model", None)
		if molecule in self._molecules:
			return molecule
		atom_model = getattr(item, "atom_model", None)
		if atom_model is not None:
			molecule = self._find_molecule_for_atom(atom_model)
			if molecule is not None:
				return molecule
		bond_model = getattr(item, "bond_model", None)
		if bond_model is not None:
			molecule = self._find_molecule_for_bond(bond_model)
			if molecule is not None:
				return molecule
		mark_model = getattr(item, "atom_mark_model", None)
		if mark_model is not None:
			return self._find_molecule_for_atom(mark_model.atom_model)
		parent_item = item.parentItem()
		if parent_item is not None:
			return self.molecule_for_graphics_item(parent_item)
		return None

	# ------------------------------------------------------------------
	# Mutation
	# ------------------------------------------------------------------

	#============================================
	def add_molecule(self, mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
					mark_dirty: bool = True, index: int | None = None) -> None:
		"""Add a molecule to the document.

		Args:
			mol_model: MoleculeModel to add.
			mark_dirty: Whether this direct mutation represents a user edit.
			index: Optional top-level stack insertion position.
		"""
		self.insert_molecule(mol_model, index=index, mark_dirty=mark_dirty)

	#============================================
	def insert_molecule(
			self, mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
			index: int | None = None, mark_dirty: bool = True,
			) -> None:
		"""Insert a molecule at a canonical top-level stack position."""
		if mol_model in self._molecules:
			return
		stack_index = self._normalized_insert_index(index)
		self._molecules.append(mol_model)
		self._object_stack.insert(stack_index, mol_model)
		mol_model.setParent(self)
		self.object_added.emit(mol_model)
		if mark_dirty:
			self.mark_dirty()

	#============================================
	def remove_molecule(self, mol_model: bkchem_qt.models.molecule_model.MoleculeModel,
						mark_dirty: bool = True) -> None:
		"""Remove a molecule from the document.

		Args:
			mol_model: MoleculeModel to remove.
			mark_dirty: Whether this direct mutation represents a user edit.

		Raises:
			ValueError: If the molecule is not in the document.
		"""
		self._molecules.remove(mol_model)
		self._object_stack.remove(mol_model)
		mol_model.setParent(None)
		self.object_removed.emit(mol_model)
		if mark_dirty:
			self.mark_dirty()

	#============================================
	def add_presentation_object(
			self,
			object_model: bkchem_qt.models.document_object.PresentationObject,
			mark_dirty: bool = True,
			index: int | None = None,
			) -> None:
		"""Add a non-molecule object to the ordered document stack.

		Args:
			object_model: Presentation object to own.
			mark_dirty: Whether this direct mutation represents a user edit.
			index: Optional top-level stack insertion position.
		"""
		self.insert_presentation_object(
			object_model, index=index, mark_dirty=mark_dirty,
		)

	#============================================
	def insert_presentation_object(
			self,
			object_model: bkchem_qt.models.document_object.PresentationObject,
			index: int | None = None, mark_dirty: bool = True,
			) -> None:
		"""Insert presentation artwork at a canonical stack position."""
		if object_model in self._presentation_objects:
			return
		stack_index = self._normalized_insert_index(index)
		self._presentation_objects.append(object_model)
		self._object_stack.insert(stack_index, object_model)
		object_model.setParent(self)
		self.object_added.emit(object_model)
		if mark_dirty:
			self.mark_dirty()

	#============================================
	def object_index(self, object_model: object) -> int:
		"""Return the identity-based index of one top-level document object.

		Raises:
			ValueError: If ``object_model`` is not owned by this document.
		"""
		for index, current_object in enumerate(self._object_stack):
			if current_object is object_model:
				return index
		raise ValueError("Object is not owned by this document")

	#============================================
	def replace_object_order(self, objects: list, mark_dirty: bool = True) -> None:
		"""Replace the top-level stack after validating exact object identity.

		The supplied sequence must contain every current object exactly once.
		This prevents a reorder command from silently dropping or duplicating a
		model when two distinct QObject wrappers happen to compare alike.
		"""
		if len(objects) != len(self._object_stack):
			raise ValueError("Object order must contain every document object")
		current_ids = {id(object_model) for object_model in self._object_stack}
		proposed_ids = [id(object_model) for object_model in objects]
		if len(set(proposed_ids)) != len(proposed_ids) or set(proposed_ids) != current_ids:
			raise ValueError("Object order must contain each document object once")
		self._object_stack = list(objects)
		self._synchronize_scene_object_stack()
		if mark_dirty:
			self.mark_dirty()

	#============================================
	def _normalized_insert_index(self, index: int | None) -> int:
		"""Return a Python-list insertion index for a top-level object."""
		if index is None:
			return len(self._object_stack)
		if index < 0 or index > len(self._object_stack):
			raise IndexError("Object insertion index is outside the document stack")
		return index

	#============================================
	def _synchronize_scene_object_stack(self) -> None:
		"""Refresh projected z values after a top-level order replacement."""
		if self._scene is None:
			return
		import bkchem_qt.canvas.document_projection
		bkchem_qt.canvas.document_projection.synchronize_document_stack_z_order(
			self, self._scene,
		)

	#============================================
	def remove_presentation_object(
			self,
			object_model: bkchem_qt.models.document_object.PresentationObject,
			mark_dirty: bool = True,
			) -> None:
		"""Remove a non-molecule object from the document stack.

		Args:
			object_model: Presentation object to detach.
			mark_dirty: Whether this direct mutation represents a user edit.

		Raises:
			ValueError: If the object is not in this document.
		"""
		self._presentation_objects.remove(object_model)
		self._object_stack.remove(object_model)
		object_model.setParent(None)
		self.object_removed.emit(object_model)
		if mark_dirty:
			self.mark_dirty()

	#============================================
	def add_mark(
			self,
			mark_model: bkchem_qt.models.document_object.AtomMarkModel,
			mark_dirty: bool = True,
			) -> None:
		"""Add an atom-attached mark to the document.

		Args:
			mark_model: Atom mark model to own.
			mark_dirty: Whether this direct mutation represents a user edit.
		"""
		if mark_model in self._marks:
			return
		self._marks.append(mark_model)
		mark_model.setParent(self)
		self.mark_added.emit(mark_model)
		if mark_dirty:
			self.mark_dirty()

	#============================================
	def remove_mark(
			self,
			mark_model: bkchem_qt.models.document_object.AtomMarkModel,
			mark_dirty: bool = True,
			) -> None:
		"""Remove an atom-attached mark from the document.

		Args:
			mark_model: Atom mark model to detach.
			mark_dirty: Whether this direct mutation represents a user edit.

		Raises:
			ValueError: If the mark is not in this document.
		"""
		self._marks.remove(mark_model)
		mark_model.setParent(None)
		self.mark_removed.emit(mark_model)
		if mark_dirty:
			self.mark_dirty()

	#============================================
	def set_cdml_state(
			self,
			envelope: bkchem_qt.models.document_object.CdmlEnvelope,
			paper: bkchem_qt.models.document_object.PaperModel,
			unsupported_content: list[bkchem_qt.models.document_object.UnsupportedContent],
			) -> None:
		"""Install parsed CDML metadata as a clean document baseline.

		Args:
			envelope: Root, header, reaction, and external-data state.
			paper: Paper and viewport state.
			unsupported_content: Retained nodes without a UI representation.
		"""
		self._cdml_envelope = envelope
		self._paper = paper
		self._unsupported_content = list(unsupported_content)
		self.paper_changed.emit(paper)
		self.mark_clean()

	#============================================
	def replace_paper(self, replacement: bkchem_qt.models.document_object.PaperModel) -> None:
		"""Replace the modeled paper state and notify its scene projection.

		The existing PaperModel remains document-owned so callers that retain the
		model during a dialog or undo command do not acquire a stale object.
		"""
		self._paper.replace(replacement)
		self.paper_changed.emit(self._paper)

	#============================================
	def unique_object_id(self, prefix: str) -> str:
		"""Return the first unused stable top-level CDML identifier."""
		existing_ids = set()
		for object_model in self._object_stack:
			object_id = getattr(object_model, "object_id", None)
			if object_id is None:
				object_id = getattr(object_model, "mol_id", None)
			if object_id:
				existing_ids.add(str(object_id))
		index = 1
		candidate = f"{prefix}-{index}"
		while candidate in existing_ids:
			index += 1
			candidate = f"{prefix}-{index}"
		return candidate

	#============================================
	def clear(self) -> None:
		"""Remove all document-owned state and reset to an empty baseline.

		Graphics projections are deliberately disconnected before their models or
		undo commands can release their final Python references.  This mirrors
		:class:`DocumentSession` teardown while leaving ChemScene's paper and grid
		decorations in place for the next document.
		"""
		first_error = None
		try:
			self._dispose_document_graphics()
		except Exception as exc:
			# Continue severing QObject model ownership.  A graphics callback must
			# never make a partially disposed Document safe to reuse or delete by
			# parent cascade.
			first_error = exc
		for object_model in list(self._object_stack):
			try:
				object_model.setParent(None)
			except Exception as exc:
				if first_error is None:
					first_error = exc
			try:
				self.object_removed.emit(object_model)
			except Exception as exc:
				if first_error is None:
					first_error = exc
		for mark_model in list(self._marks):
			try:
				mark_model.setParent(None)
			except Exception as exc:
				if first_error is None:
					first_error = exc
			try:
				self.mark_removed.emit(mark_model)
			except Exception as exc:
				if first_error is None:
					first_error = exc
		self._molecules.clear()
		self._object_stack.clear()
		self._presentation_objects.clear()
		self._marks.clear()
		self._paper = bkchem_qt.models.document_object.PaperModel()
		self._cdml_envelope = bkchem_qt.models.document_object.CdmlEnvelope()
		self._unsupported_content.clear()
		self._file_path = None
		self._direct_dirty = False
		try:
			self._undo_stack.clear()
			self._undo_stack.setClean()
		except Exception as exc:
			if first_error is None:
				first_error = exc
		self.paper_changed.emit(self._paper)
		self._sync_dirty_state()
		if first_error is not None:
			raise RuntimeError("Document was cleared after a disposal failure") from first_error

	#============================================
	def _dispose_document_graphics(
			self,
			reaper: "bkchem_qt.canvas.graphics_retirement.DetachedGraphicsRetirementReaper | None" = None,
			) -> None:
		"""Disconnect and detach graphics owned by the current document.

		The undo command module imports :mod:`document`, so its helper is imported
		locally after this model is fully initialized.  A document may share a
		ChemScene with persistent paper/grid decorations; only items that expose a
		model from this document are detached here.
		"""
		# A session installs its terminal reaper once, when it adopts this
		# projection.  Callers that clear the document later must keep using that
		# owner rather than silently falling back to the process reaper.
		if reaper is None:
			reaper = self._effective_terminal_graphics_reaper()
		first_error = None
		if self._scene is not None:
			from bkchem_qt.canvas.graphics_retirement import GraphicsRetirementCoordinator
			owned_model_ids = self._owned_graphics_model_ids()
			items = [
				item for item in self._scene.items()
				if self._item_belongs_to_document(item, owned_model_ids)
			]
			coordinator = GraphicsRetirementCoordinator()
			# The live scene owns the applied projection tree.  Detached graphics
			# retained by commands are a separate terminal transition owned by
			# DocumentUndoStack.clear(), so do not walk the undo stack here.
			coordinator.retire_scene_projection_items(self._scene, items, reaper=reaper)
			if coordinator.report.callback_errors:
				first_error = coordinator.report.callback_errors[0]
		else:
			from bkchem_qt.canvas.graphics_retirement import GraphicsRetirementCoordinator
			coordinator = GraphicsRetirementCoordinator()
			# With no scene, this method has no current projection roots to retire.
			# The following DocumentUndoStack.clear() owns any detached history tree.
		if first_error is not None:
			raise RuntimeError(
				"Document graphics were detached after a disposal failure",
			) from first_error

	#============================================
	def _owned_graphics_model_ids(self) -> set:
		"""Return identities exposed by current document graphics items."""
		owned_model_ids = {
			id(object_model) for object_model in self._object_stack
		}
		owned_model_ids.update(id(mark_model) for mark_model in self._marks)
		for molecule in self._molecules:
			owned_model_ids.update(id(atom_model) for atom_model in molecule.atoms)
			owned_model_ids.update(id(bond_model) for bond_model in molecule.bonds)
			owned_model_ids.update(id(group_model) for group_model in molecule.groups)
		return owned_model_ids

	#============================================
	def _item_belongs_to_document(
			self, item: PySide6.QtWidgets.QGraphicsItem,
			owned_model_ids: set,
			) -> bool:
		"""Return whether an item exposes a current document model identity."""
		for attribute in (
				"document_object_model", "atom_mark_model", "atom_model",
				"bond_model", "group_model",
			):
			model = getattr(item, attribute, None)
			if model is not None and id(model) in owned_model_ids:
				return True
		return False

	# ------------------------------------------------------------------
	# File info
	# ------------------------------------------------------------------

	#============================================
	def title(self) -> str:
		"""Return a display title for the document.

		Uses the filename from ``file_path`` if available, otherwise
		returns 'Untitled'.

		Returns:
			Title string.
		"""
		if self._file_path:
			basename = os.path.basename(self._file_path)
			return basename
		return "Untitled"

	#============================================
	def __repr__(self) -> str:
		"""Return a developer-friendly string representation."""
		n_mols = len(self._molecules)
		title = self.title()
		return f"Document('{title}', {n_mols} molecules)"
