"""Qt-only molecule topology projection with change signals."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.fragment_model
import bkchem_qt.models.group_model


#============================================
class MoleculeModel(PySide6.QtCore.QObject):
	"""Own one disposable Qt molecule topology and emit projection changes.

	The model stores ordered AtomModel and BondModel wrappers with endpoint
	relationships.  OASA values enter or leave only through bridge conversions;
	this projection never retains a graph object from the backend.
	"""

	# signals for structural changes
	atom_added = PySide6.QtCore.Signal(object)
	atom_removed = PySide6.QtCore.Signal(object)
	bond_added = PySide6.QtCore.Signal(object)
	bond_removed = PySide6.QtCore.Signal(object)

	#============================================
	def __init__(self, parent: PySide6.QtCore.QObject | None = None) -> None:
		"""Initialize the molecule model.

		Args:
			parent: Optional parent QObject.
		"""
		super().__init__(parent)
		# Ordered wrapper storage is the complete Qt topology source of truth.
		self._atom_models: list[bkchem_qt.models.atom_model.AtomModel] = []
		self._bond_models: list[bkchem_qt.models.bond_model.BondModel] = []
		# metadata properties
		self._name = ""
		self._mol_id = ""
		# Only the explicitly named compatibility decoder retains source XML.
		# Synchronized projections receive durable backend observations instead,
		# so rebuilding or discarding them cannot make Qt a document authority.
		self._compatibility_source_xml = None
		# Fragments are presentation metadata, but their atom/bond references
		# are stable CDML IDs rather than live OASA graph objects.
		self._fragments: list[bkchem_qt.models.fragment_model.FragmentModel] = []
		self._unsupported_fragment_xml: list[str] = []
		self._fragment_notices: list[str] = []
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
		return list(self._atom_models)

	#============================================
	@property
	def bonds(self) -> list:
		"""Return all BondModel wrappers in this molecule.

		Returns:
			List of BondModel instances.
		"""
		return list(self._bond_models)

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
	def compatibility_source_xml(self) -> str | None:
		"""Return XML retained only for the legacy-isolated compatibility route.

		Synchronized backend projections leave this value unset.  Their saved
		molecule XML, including unknown extensions, remains owned by OASA and is
		retrieved through an authoritative fragment query when needed.
		"""
		return self._compatibility_source_xml

	#============================================
	@compatibility_source_xml.setter
	def compatibility_source_xml(self, value: str | None) -> None:
		"""Store compatibility-only XML for legacy clipboard/export handling."""
		self._compatibility_source_xml = value

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
	def fragment_notices(self) -> tuple[str, ...]:
		"""Return backend-described read-only fragment notices for this projection."""
		return tuple(self._fragment_notices)

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
	def add_fragment_notice(self, notice: str) -> None:
		"""Retain one plain backend fragment notice without retaining XML."""
		self._fragment_notices.append(notice)

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
		atom_ids = {str(atom.atom_id or "") for atom in self.atoms}
		bond_ids = {str(bond.bond_id or "") for bond in self.bonds}
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
		atoms_by_id = {str(atom.atom_id or ""): atom for atom in self.atoms}
		bonds_by_id = {str(bond.bond_id or ""): bond for bond in self.bonds}
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
		"""Add an atom to this Qt topology projection.

		Args:
			atom_model: AtomModel to add.
		"""
		if not isinstance(atom_model, bkchem_qt.models.atom_model.AtomModel):
			raise TypeError("atom_model must be an AtomModel")
		if any(existing is atom_model for existing in self._atom_models):
			raise ValueError("atom_model already belongs to this molecule")
		if atom_model.molecule_model is not None:
			raise ValueError("atom_model already belongs to a molecule")
		if atom_model.parent() is not None:
			raise ValueError("atom_model already has a QObject owner")
		self._atom_models.append(atom_model)
		atom_model.setParent(self)
		atom_model.set_molecule_model(self)
		self.atom_added.emit(atom_model)

	#============================================
	def remove_atom(self, atom_model: bkchem_qt.models.atom_model.AtomModel) -> None:
		"""Remove an atom and all its bonds from the molecule.

		Also removes any BondModels connected to this atom.

		Args:
			atom_model: AtomModel to remove.
		"""
		if not isinstance(atom_model, bkchem_qt.models.atom_model.AtomModel):
			raise TypeError("atom_model must be an AtomModel")
		if not any(existing is atom_model for existing in self._atom_models):
			raise ValueError("atom_model does not belong to this molecule")
		# remove bonds connected to this atom first
		bonds_to_remove = []
		for bond_model in list(self._bond_models):
			if bond_model.atom1 is atom_model or bond_model.atom2 is atom_model:
				bonds_to_remove.append(bond_model)
		for bond_model in bonds_to_remove:
			self.remove_bond(bond_model)
		self._atom_models.remove(atom_model)
		atom_model.set_molecule_model(None)
		atom_model.setParent(None)
		self.prune_invalid_fragments()
		self.atom_removed.emit(atom_model)

	#============================================
	def add_bond(self, atom1_model: bkchem_qt.models.atom_model.AtomModel,
					atom2_model: bkchem_qt.models.atom_model.AtomModel,
					bond_model: bkchem_qt.models.bond_model.BondModel) -> None:
		"""Add a bond between two atom wrappers in this projection.

		Args:
			atom1_model: First endpoint AtomModel.
			atom2_model: Second endpoint AtomModel.
			bond_model: BondModel to add as the connecting edge.
		"""
		if not isinstance(atom1_model, bkchem_qt.models.atom_model.AtomModel):
			raise TypeError("atom1_model must be an AtomModel")
		if not isinstance(atom2_model, bkchem_qt.models.atom_model.AtomModel):
			raise TypeError("atom2_model must be an AtomModel")
		if not isinstance(bond_model, bkchem_qt.models.bond_model.BondModel):
			raise TypeError("bond_model must be a BondModel")
		if atom1_model is atom2_model:
			raise ValueError("bond endpoints must be distinct atoms")
		if not any(existing is atom1_model for existing in self._atom_models):
			raise ValueError("atom1_model does not belong to this molecule")
		if not any(existing is atom2_model for existing in self._atom_models):
			raise ValueError("atom2_model does not belong to this molecule")
		if any(existing is bond_model for existing in self._bond_models):
			raise ValueError("bond_model already belongs to this molecule")
		if bond_model.atom1 is not None or bond_model.atom2 is not None:
			raise ValueError("bond_model already has projection endpoints")
		if bond_model.parent() is not None:
			raise ValueError("bond_model already has a QObject owner")
		if any(
				{existing.atom1, existing.atom2} == {atom1_model, atom2_model}
				for existing in self._bond_models
				):
			raise ValueError("projection already contains a bond between these atoms")
		# set endpoint references on the bond model
		bond_model._atom1 = atom1_model
		bond_model._atom2 = atom2_model
		self._bond_models.append(bond_model)
		bond_model.setParent(self)
		self.bond_added.emit(bond_model)

	#============================================
	def remove_bond(self, bond_model: bkchem_qt.models.bond_model.BondModel) -> None:
		"""Remove a bond from this Qt topology projection.

		Args:
			bond_model: BondModel to remove.
		"""
		if not isinstance(bond_model, bkchem_qt.models.bond_model.BondModel):
			raise TypeError("bond_model must be a BondModel")
		if not any(existing is bond_model for existing in self._bond_models):
			raise ValueError("bond_model does not belong to this molecule")
		self._bond_models.remove(bond_model)
		# clear endpoint references
		bond_model._atom1 = None
		bond_model._atom2 = None
		bond_model.setParent(None)
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
	def _projection_neighbors(
			self,
			) -> dict[
				bkchem_qt.models.atom_model.AtomModel,
				list[tuple[
					bkchem_qt.models.atom_model.AtomModel,
					bkchem_qt.models.bond_model.BondModel,
					]],
				]:
		"""Build the ordered wrapper adjacency used by projection graph queries."""
		neighbors = {atom: [] for atom in self._atom_models}
		for bond in self._bond_models:
			atom1 = bond.atom1
			atom2 = bond.atom2
			if atom1 not in neighbors or atom2 not in neighbors:
				raise ValueError("bond endpoints do not belong to this molecule")
			neighbors[atom1].append((atom2, bond))
			neighbors[atom2].append((atom1, bond))
		return neighbors

	#============================================
	def _breadth_first_parents(
			self,
			root: bkchem_qt.models.atom_model.AtomModel,
			neighbors: dict[
				bkchem_qt.models.atom_model.AtomModel,
				list[tuple[
					bkchem_qt.models.atom_model.AtomModel,
					bkchem_qt.models.bond_model.BondModel,
					]],
				],
			atom_positions: dict[bkchem_qt.models.atom_model.AtomModel, int],
			) -> dict[
				bkchem_qt.models.atom_model.AtomModel,
				tuple[
					bkchem_qt.models.atom_model.AtomModel | None,
					bkchem_qt.models.bond_model.BondModel | None,
					],
				]:
		"""Build one deterministic shortest-path tree from wrapper topology."""
		parents = {root: (None, None)}
		pending = [root]
		while pending:
			atom = pending.pop(0)
			ordered_neighbors = sorted(
				neighbors[atom], key=lambda item: atom_positions[item[0]],
			)
			for neighbor, bond in ordered_neighbors:
				if neighbor in parents:
					continue
				parents[neighbor] = (atom, bond)
				pending.append(neighbor)
		return parents

	#============================================
	def _cycle_from_tree_edge(
			self,
			atom1: bkchem_qt.models.atom_model.AtomModel,
			atom2: bkchem_qt.models.atom_model.AtomModel,
			parents: dict[
				bkchem_qt.models.atom_model.AtomModel,
				tuple[
					bkchem_qt.models.atom_model.AtomModel | None,
					bkchem_qt.models.bond_model.BondModel | None,
					],
				],
			) -> tuple[
				list[bkchem_qt.models.atom_model.AtomModel],
				list[bkchem_qt.models.bond_model.BondModel],
				]:
		"""Return the tree path closed by one non-tree bond."""
		path1 = [atom1]
		path2 = [atom2]
		while parents[path1[-1]][0] is not None:
			path1.append(parents[path1[-1]][0])
		while parents[path2[-1]][0] is not None:
			path2.append(parents[path2[-1]][0])
		positions1 = {atom: position for position, atom in enumerate(path1)}
		for position2, atom in enumerate(path2):
			if atom in positions1:
				position1 = positions1[atom]
				break
		else:
			raise ValueError("tree edge endpoints do not share a projection root")
		cycle = path1[:position1 + 1] + list(reversed(path2[:position2]))
		tree_bonds = [parents[atom][1] for atom in path1[:position1]]
		tree_bonds.extend(parents[atom][1] for atom in path2[:position2])
		if any(bond is None for bond in tree_bonds):
			raise ValueError("tree path is not present in projection topology")
		return cycle, tree_bonds

	#============================================
	def _cycle_edge_mask(
			self,
			tree_bonds: list[bkchem_qt.models.bond_model.BondModel],
			closing_bond: bkchem_qt.models.bond_model.BondModel,
			bond_positions: dict[bkchem_qt.models.bond_model.BondModel, int],
			) -> int:
		"""Encode one cycle's projection bonds as a GF(2) vector."""
		edge_mask = 1 << bond_positions[closing_bond]
		for bond in tree_bonds:
			edge_mask ^= 1 << bond_positions[bond]
		return edge_mask

	#============================================
	def _add_independent_cycle(self, edge_mask: int, basis: dict[int, int]) -> bool:
		"""Add one independent cycle vector to an in-place GF(2) basis."""
		current = edge_mask
		while current:
			pivot = current.bit_length() - 1
			if pivot not in basis:
				basis[pivot] = current
				return True
			current ^= basis[pivot]
		return False

	#============================================
	def is_connected(self) -> bool:
		"""Check whether the molecule graph is connected.

		Returns:
			True if all atoms are reachable from any other atom.
		"""
		if not self._atom_models:
			return False
		neighbors = self._projection_neighbors()
		pending = [self._atom_models[0]]
		visited = set()
		while pending:
			atom = pending.pop()
			if atom in visited:
				continue
			visited.add(atom)
			pending.extend(neighbor for neighbor, unused_bond in neighbors[atom])
		return len(visited) == len(self._atom_models)

	#============================================
	def get_smallest_independent_cycles(
			self,
			) -> list[tuple[bkchem_qt.models.atom_model.AtomModel, ...]]:
		"""Return a deterministic independent cycle basis.

		Returns:
			Ordered Qt-wrapper tuples. Each tuple names an independent cycle
			without repeating its closing atom. The historical method name is
			retained for callers; it does not promise a canonical SSSR.
		"""
		if len(self._atom_models) < 3:
			return []
		neighbors = self._projection_neighbors()
		atom_positions = {atom: position for position, atom in enumerate(self._atom_models)}
		bond_positions = {bond: position for position, bond in enumerate(self._bond_models)}
		candidates = []
		for root in self._atom_models:
			parents = self._breadth_first_parents(root, neighbors, atom_positions)
			for bond in self._bond_models:
				atom1 = bond.atom1
				atom2 = bond.atom2
				if atom1 is None or atom2 is None:
					raise ValueError("bond endpoints do not belong to this molecule")
				if atom1 not in parents or atom2 not in parents:
					continue
				if parents[atom1][0] is atom2 or parents[atom2][0] is atom1:
					continue
				cycle, tree_bonds = self._cycle_from_tree_edge(atom1, atom2, parents)
				if len(cycle) < 3:
					continue
				edge_mask = self._cycle_edge_mask(tree_bonds, bond, bond_positions)
				candidates.append(
						(len(cycle), tuple(atom_positions[atom] for atom in cycle),
						edge_mask, cycle),
						)
		candidates.sort(key=lambda candidate: (candidate[0], candidate[1]))
		basis: dict[int, int] = {}
		cycles = []
		for unused_length, unused_positions, edge_mask, cycle in candidates:
			if self._add_independent_cycle(edge_mask, basis):
				cycles.append(tuple(cycle))
		return cycles

	#============================================
	def contains_cycle(self) -> bool:
		"""Check whether the molecule contains any ring.

		Returns:
			True if the molecule contains at least one cycle.
		"""
		return bool(self.get_smallest_independent_cycles())

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
		atom_model = bkchem_qt.models.atom_model.AtomModel.create(symbol=symbol)
		return atom_model

	#============================================
	def create_bond(
			self, order: int = 1, bond_type: str = 'n',
			) -> bkchem_qt.models.bond_model.BondModel:
		"""Create a new BondModel with the given order and type.

		The bond is not automatically added to the molecule; call
		``add_bond()`` separately.

		Args:
			order: Bond order (1, 2, 3, or 4 for aromatic).
			bond_type: Bond type character ('n','w','h','a','b','d','o','s','q').

		Returns:
			A new BondModel instance.
		"""
		bond_model = bkchem_qt.models.bond_model.BondModel.create(
			order=order, bond_type=bond_type,
		)
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
