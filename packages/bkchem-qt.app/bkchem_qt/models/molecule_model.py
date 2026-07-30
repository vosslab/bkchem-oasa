"""Qt composition wrapper around an OASA Molecule with change signals."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.fragment_model
import bkchem_qt.models.group_model


#============================================
class MoleculeModel(PySide6.QtCore.QObject):
	"""Composition wrapper that owns an OASA Molecule and emits Qt signals.

	Maintains parallel tracking dicts that map OASA atoms/bonds to their
	AtomModel/BondModel wrappers. Graph queries (connectivity, cycles) are
	delegated to the internal ``oasa.molecule_lib.Molecule``. Mutation methods
	emit ``atom_added``, ``atom_removed``, ``bond_added``, or ``bond_removed``
	signals so the scene can react.

	Args:
		oasa_mol: Existing OASA Molecule to wrap. A new empty molecule is
			created when ``None``.
		parent: Optional parent QObject.
	"""

	# signals for structural changes
	atom_added = PySide6.QtCore.Signal(object)
	atom_removed = PySide6.QtCore.Signal(object)
	bond_added = PySide6.QtCore.Signal(object)
	bond_removed = PySide6.QtCore.Signal(object)

	#============================================
	def __init__(self, oasa_mol: oasa.molecule_lib.Molecule | None = None,
			parent: PySide6.QtCore.QObject | None = None) -> None:
		"""Initialize the molecule model.

		Args:
			oasa_mol: Existing OASA Molecule to wrap, or None for a new
				empty molecule.
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		# chemistry backend
		self._chem_mol = oasa_mol or oasa.molecule_lib.Molecule()
		# tracking dicts: oasa object -> Qt model wrapper
		self._atom_models = {}
		self._bond_models = {}
		# metadata properties
		self._name = ""
		self._mol_id = ""
		self._cdml_source_xml = None
		# Fragments are presentation metadata, but their atom/bond references
		# are stable CDML IDs rather than live OASA graph objects.
		self._fragments: list[bkchem_qt.models.fragment_model.FragmentModel] = []
		self._unsupported_fragment_xml: list[str] = []
		# CDML groups are pseudo-vertices owned by the frontend.  They remain
		# outside OASA until an explicit future expansion command converts them.
		self._groups: list[bkchem_qt.models.group_model.GroupModel] = []
		# template attachment points
		self._t_bond_first = None
		self._t_bond_second = None
		self._t_atom = None

	# ------------------------------------------------------------------
	# Collection properties
	# ------------------------------------------------------------------

	#============================================
	@property
	def atoms(self) -> list:
		"""Return all AtomModel wrappers in this molecule.

		Returns:
			List of AtomModel instances.
		"""
		return list(self._atom_models.values())

	#============================================
	@property
	def bonds(self) -> list:
		"""Return all BondModel wrappers in this molecule.

		Returns:
			List of BondModel instances.
		"""
		return list(self._bond_models.values())

	#============================================
	@property
	def name(self) -> str:
		"""User-assigned molecule name."""
		return self._name

	#============================================
	@name.setter
	def name(self, value: str) -> None:
		self._name = str(value)

	#============================================
	@property
	def mol_id(self) -> str:
		"""User-assigned molecule identifier."""
		return self._mol_id

	#============================================
	@mol_id.setter
	def mol_id(self, value: str) -> None:
		self._mol_id = str(value)

	#============================================
	@property
	def cdml_source_xml(self) -> str | None:
		"""Original molecule XML retained for CDML fidelity checks."""
		return self._cdml_source_xml

	#============================================
	@cdml_source_xml.setter
	def cdml_source_xml(self, value: str | None) -> None:
		"""Store the original molecule XML, or clear the retained source."""
		self._cdml_source_xml = value

	#============================================
	@property
	def fragments(self) -> tuple[bkchem_qt.models.fragment_model.FragmentModel, ...]:
		"""Return ordered, valid fragment metadata for this molecule."""
		return tuple(self._fragments)

	#============================================
	@property
	def unsupported_fragment_xml(self) -> tuple[str, ...]:
		"""Return retained fragment XML that cannot safely become editable."""
		return tuple(self._unsupported_fragment_xml)

	#============================================
	@property
	def groups(self) -> tuple[bkchem_qt.models.group_model.GroupModel, ...]:
		"""Return ordered native CDML group pseudo-vertices for this molecule."""
		return tuple(self._groups)

	#============================================
	def add_group(self, group: bkchem_qt.models.group_model.GroupModel) -> None:
		"""Own a group with a molecule-local, stable CDML identifier."""
		if any(existing.group_id == group.group_id for existing in self._groups):
			raise ValueError("group ID must be unique within a molecule")
		group.setParent(self)
		self._groups.append(group)

	#============================================
	def add_fragment(self, fragment: bkchem_qt.models.fragment_model.FragmentModel) -> None:
		"""Add a fragment whose stable references currently resolve.

		Raises:
			ValueError: The fragment is not representable by this molecule.
		"""
		if not self._fragment_is_valid(fragment):
			raise ValueError("fragment references atoms or bonds outside this molecule")
		if any(existing.fragment_id == fragment.fragment_id for existing in self._fragments):
			raise ValueError("fragment ID must be unique within a molecule")
		self._fragments.append(fragment)

	#============================================
	def insert_fragment(
			self, position: int,
			fragment: bkchem_qt.models.fragment_model.FragmentModel,
			) -> None:
		"""Insert a valid fragment at its durable metadata position."""
		if not self._fragment_is_valid(fragment):
			raise ValueError("fragment references atoms or bonds outside this molecule")
		if any(existing.fragment_id == fragment.fragment_id for existing in self._fragments):
			raise ValueError("fragment ID must be unique within a molecule")
		self._fragments.insert(position, fragment)

	#============================================
	def remove_fragment(self, fragment_id: str) -> tuple[
			int, bkchem_qt.models.fragment_model.FragmentModel,
			]:
		"""Remove one editable fragment and return its original position."""
		for position, fragment in enumerate(self._fragments):
			if fragment.fragment_id == fragment_id:
				self._fragments.pop(position)
				return position, fragment
		raise ValueError("fragment ID is not editable metadata for this molecule")

	#============================================
	def can_add_fragment(self, fragment: bkchem_qt.models.fragment_model.FragmentModel) -> bool:
		"""Return whether a fragment is valid and has a unique stable ID."""
		return (
				self._fragment_is_valid(fragment)
				and not any(existing.fragment_id == fragment.fragment_id
							for existing in self._fragments)
				)

	#============================================
	def retain_unsupported_fragment_xml(self, raw_xml: str) -> None:
		"""Keep an unrepresentable fragment visible for lossless round-tripping."""
		self._unsupported_fragment_xml.append(raw_xml)

	#============================================
	def fragment_snapshot(self) -> tuple[bkchem_qt.models.fragment_model.FragmentModel, ...]:
		"""Return a durable ordered fragment snapshot for structural undo."""
		return tuple(self._fragments)

	#============================================
	def restore_fragment_snapshot(
			self, snapshot: tuple[bkchem_qt.models.fragment_model.FragmentModel, ...],
			) -> None:
		"""Restore a previously valid snapshot after undo restores graph objects."""
		self._fragments = list(snapshot)

	#============================================
	def prune_invalid_fragments(self) -> tuple[bkchem_qt.models.fragment_model.FragmentModel, ...]:
		"""Remove fragments whose references or linear-form geometry are stale."""
		removed = tuple(fragment for fragment in self._fragments
						if not self._fragment_is_valid(fragment)
						or not self._linear_fragment_is_current(fragment))
		self._fragments = [fragment for fragment in self._fragments
						if self._fragment_is_valid(fragment)
						and self._linear_fragment_is_current(fragment)]
		return removed

	#============================================
	def linear_fragment_snapshot_after_geometry(
			self, coordinates: dict[object, tuple[float, float]],
			) -> tuple[bkchem_qt.models.fragment_model.FragmentModel, ...]:
		"""Return fragments that remain valid after a planned coordinate change.

		Linear-form metadata is a compact rendering contract, not a free-form
		selection tag.  Commands use this snapshot to remove a linear fragment
		when a later edit bends, spaces, or disconnects its represented chain.
		"""
		snapshot = tuple(
			fragment for fragment in self._fragments
			if self._linear_fragment_is_current(fragment, coordinates)
		)
		return snapshot

	#============================================
	def _fragment_is_valid(self, fragment: bkchem_qt.models.fragment_model.FragmentModel) -> bool:
		"""Return whether all fragment references target present stable IDs."""
		atom_ids = {str(getattr(atom._chem_atom, "id", "")) for atom in self.atoms}
		bond_ids = {str(getattr(bond._chem_bond, "id", "")) for bond in self.bonds}
		return set(fragment.atom_ids).issubset(atom_ids) and set(fragment.bond_ids).issubset(bond_ids)

	#============================================
	def _linear_fragment_is_current(
			self, fragment: bkchem_qt.models.fragment_model.FragmentModel,
			coordinates: dict[object, tuple[float, float]] | None = None,
			) -> bool:
		"""Return whether a linear form still has its declared path geometry."""
		if fragment.fragment_type != "linear_form":
			return True
		bond_length_text = None
		for property_model in fragment.properties:
			if property_model.name == "bond_length":
				bond_length_text = property_model.value
				break
		if bond_length_text is None:
			return False
		try:
			bond_length = float(bond_length_text)
		except ValueError:
			return False
		if bond_length <= 0.0:
			return False
		atoms_by_id = {
			str(getattr(atom._chem_atom, "id", "")): atom
			for atom in self.atoms
		}
		bonds_by_id = {
			str(getattr(bond._chem_bond, "id", "")): bond
			for bond in self.bonds
		}
		if len(fragment.atom_ids) != len(set(fragment.atom_ids)):
			return False
		if len(fragment.bond_ids) != len(set(fragment.bond_ids)):
			return False
		if not fragment.atom_ids:
			return False
		if not set(fragment.atom_ids).issubset(atoms_by_id):
			return False
		if not set(fragment.bond_ids).issubset(bonds_by_id):
			return False
		atoms = [atoms_by_id[atom_id] for atom_id in fragment.atom_ids]
		bonds = [bonds_by_id[bond_id] for bond_id in fragment.bond_ids]
		if len(bonds) != len(atoms) - 1:
			return False
		atom_set = set(atoms)
		neighbors = {atom: [] for atom in atoms}
		for bond in bonds:
			if bond.atom1 not in atom_set or bond.atom2 not in atom_set:
				return False
			neighbors[bond.atom1].append(bond.atom2)
			neighbors[bond.atom2].append(bond.atom1)
		if any(len(atom_neighbors) > 2 for atom_neighbors in neighbors.values()):
			return False
		if len(atoms) > 1 and sum(
				1 for atom_neighbors in neighbors.values() if len(atom_neighbors) == 1
				) != 2:
			return False
		pending = [atoms[0]]
		visited = set()
		while pending:
			atom = pending.pop()
			if atom in visited:
				continue
			visited.add(atom)
			pending.extend(neighbors[atom])
		if len(visited) != len(atoms):
			return False
		positions = coordinates if coordinates is not None else {}
		points = [positions.get(atom, (atom.x, atom.y)) for atom in atoms]
		y_values = [point[1] for point in points]
		if max(y_values) - min(y_values) > 0.001:
			return False
		x_values = sorted(point[0] for point in points)
		for first, second in zip(x_values, x_values[1:]):
			if abs((second - first) - bond_length) > 0.001:
				return False
		return True

	# ------------------------------------------------------------------
	# Graph mutation
	# ------------------------------------------------------------------

	#============================================
	def add_atom(self, atom_model: bkchem_qt.models.atom_model.AtomModel) -> None:
		"""Add an atom to the molecule.

		Registers the AtomModel's underlying OASA atom with the backend
		molecule and stores the mapping.

		Args:
			atom_model: AtomModel to add.
		"""
		oasa_atom = atom_model._chem_atom
		self._chem_mol.add_vertex(oasa_atom)
		self._atom_models[id(oasa_atom)] = atom_model
		atom_model._molecule_model = self
		self.atom_added.emit(atom_model)

	#============================================
	def remove_atom(self, atom_model: bkchem_qt.models.atom_model.AtomModel) -> None:
		"""Remove an atom and all its bonds from the molecule.

		Also removes any BondModels connected to this atom.

		Args:
			atom_model: AtomModel to remove.
		"""
		oasa_atom = atom_model._chem_atom
		# remove bonds connected to this atom first
		bonds_to_remove = []
		for bond_id, bond_model in list(self._bond_models.items()):
			if bond_model.atom1 is atom_model or bond_model.atom2 is atom_model:
				bonds_to_remove.append(bond_model)
		for bond_model in bonds_to_remove:
			self.remove_bond(bond_model)
		# remove the atom from the backend
		self._chem_mol.remove_vertex(oasa_atom)
		self._atom_models.pop(id(oasa_atom), None)
		atom_model._molecule_model = None
		self.prune_invalid_fragments()
		self.atom_removed.emit(atom_model)

	#============================================
	def add_bond(self, atom1_model: bkchem_qt.models.atom_model.AtomModel,
					atom2_model: bkchem_qt.models.atom_model.AtomModel,
					bond_model: bkchem_qt.models.bond_model.BondModel) -> None:
		"""Add a bond between two atoms.

		Registers the BondModel's underlying OASA bond as an edge in the
		backend molecule and updates the BondModel's endpoint references.

		Args:
			atom1_model: First endpoint AtomModel.
			atom2_model: Second endpoint AtomModel.
			bond_model: BondModel to add as the connecting edge.
		"""
		oasa_atom1 = atom1_model._chem_atom
		oasa_atom2 = atom2_model._chem_atom
		oasa_bond = bond_model._chem_bond
		# add the edge to the backend graph
		self._chem_mol.add_edge(oasa_atom1, oasa_atom2, e=oasa_bond)
		# set endpoint references on the bond model
		bond_model._atom1 = atom1_model
		bond_model._atom2 = atom2_model
		# store the mapping
		self._bond_models[id(oasa_bond)] = bond_model
		self.bond_added.emit(bond_model)

	#============================================
	def remove_bond(self, bond_model: bkchem_qt.models.bond_model.BondModel) -> None:
		"""Remove a bond from the molecule.

		Disconnects the OASA edge and clears the BondModel's endpoint
		references.

		Args:
			bond_model: BondModel to remove.
		"""
		oasa_bond = bond_model._chem_bond
		self._chem_mol.disconnect_edge(oasa_bond)
		self._bond_models.pop(id(oasa_bond), None)
		# clear endpoint references
		bond_model._atom1 = None
		bond_model._atom2 = None
		self.prune_invalid_fragments()
		self.bond_removed.emit(bond_model)

	# ------------------------------------------------------------------
# Graph queries
	# ------------------------------------------------------------------

	#============================================
	def connected_display_atoms(
			self,
			atom_model: bkchem_qt.models.atom_model.AtomModel,
			) -> tuple[tuple[bkchem_qt.models.atom_model.AtomModel, int], ...]:
		"""Return displayed neighbors and bond orders in bond insertion order.

		Args:
			atom_model: Displayed atom belonging to this molecule.

		Returns:
			Immutable ``(AtomModel, bond_order)`` pairs for incident displayed bonds.

		Raises:
			ValueError: The atom does not belong to this molecule, or a displayed
				bond is not fully wired to atoms in this molecule.
		"""
		# Membership is identity-based because projection wrappers are QObject values.
		atoms = self.atoms
		if not any(display_atom is atom_model for display_atom in atoms):
			raise ValueError("atom_model does not belong to this molecule")
		connections = []
		for bond_model in self.bonds:
			atom1_model = bond_model.atom1
			atom2_model = bond_model.atom2
			# A displayed bond must have two displayed endpoints in this projection.
			if (atom1_model is None or atom2_model is None
					or not any(display_atom is atom1_model for display_atom in atoms)
					or not any(display_atom is atom2_model for display_atom in atoms)):
				raise ValueError("bond endpoints do not belong to this molecule")
			if atom1_model is atom_model:
				connections.append((atom2_model, bond_model.order))
			elif atom2_model is atom_model:
				connections.append((atom1_model, bond_model.order))
		return tuple(connections)

	#============================================
	def is_connected(self) -> bool:
		"""Check whether the molecule graph is connected.

		Returns:
			True if all atoms are reachable from any other atom.
		"""
		return self._chem_mol.is_connected()

	#============================================
	def get_smallest_independent_cycles(self) -> list:
		"""Return the smallest set of independent cycles (SSSR).

		Returns:
			List of cycle vertex lists from the OASA backend.
		"""
		return self._chem_mol.get_smallest_independent_cycles()

	#============================================
	def contains_cycle(self) -> bool:
		"""Check whether the molecule contains any ring.

		Returns:
			True if the molecule contains at least one cycle.
		"""
		return self._chem_mol.contains_cycle()

	# ------------------------------------------------------------------
	# Factory methods
	# ------------------------------------------------------------------

	#============================================
	def create_atom(self, symbol: str = "C") -> bkchem_qt.models.atom_model.AtomModel:
		"""Create a new AtomModel with the given element symbol.

		The atom is not automatically added to the molecule; call
		``add_atom()`` separately.

		Args:
			symbol: Element symbol (default 'C' for carbon).

		Returns:
			A new AtomModel instance.
		"""
		oasa_atom = oasa.atom_lib.Atom(symbol=symbol)
		atom_model = bkchem_qt.models.atom_model.AtomModel(oasa_atom=oasa_atom)
		return atom_model

	#============================================
	def create_bond(self, order: int = 1, bond_type: str = 'n') -> bkchem_qt.models.bond_model.BondModel:
		"""Create a new BondModel with the given order and type.

		The bond is not automatically added to the molecule; call
		``add_bond()`` separately.

		Args:
			order: Bond order (1, 2, 3, or 4 for aromatic).
			bond_type: Bond type character ('n','w','h','a','b','d','o','s','q').

		Returns:
			A new BondModel instance.
		"""
		oasa_bond = oasa.bond_lib.Bond(order=order, type=bond_type)
		bond_model = bkchem_qt.models.bond_model.BondModel(oasa_bond=oasa_bond)
		return bond_model

	# ------------------------------------------------------------------
	# Template support
	# ------------------------------------------------------------------

	#============================================
	@property
	def t_bond_first(self) -> object | None:
		"""First template attachment bond (BondModel or None)."""
		return self._t_bond_first

	#============================================
	@t_bond_first.setter
	def t_bond_first(self, value: object | None) -> None:
		self._t_bond_first = value

	#============================================
	@property
	def t_bond_second(self) -> object | None:
		"""Second template attachment bond (BondModel or None)."""
		return self._t_bond_second

	#============================================
	@t_bond_second.setter
	def t_bond_second(self, value: object | None) -> None:
		self._t_bond_second = value

	#============================================
	@property
	def t_atom(self) -> object | None:
		"""Template attachment atom (AtomModel or None)."""
		return self._t_atom

	#============================================
	@t_atom.setter
	def t_atom(self, value: object | None) -> None:
		self._t_atom = value

	#============================================
	def __repr__(self) -> str:
		"""Return a developer-friendly string representation."""
		n_atoms = len(self._atom_models)
		n_bonds = len(self._bond_models)
		return f"MoleculeModel({n_atoms} atoms, {n_bonds} bonds)"
