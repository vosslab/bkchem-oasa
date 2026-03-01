"""Qt composition wrapper around an OASA Molecule with change signals."""

# PIP3 modules
import PySide6.QtCore

# local repo modules
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model


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
	def __init__(self, oasa_mol: oasa.molecule_lib.Molecule = None, parent: PySide6.QtCore.QObject = None):
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

	# ------------------------------------------------------------------
	# Graph mutation
	# ------------------------------------------------------------------

	#============================================
	def add_atom(self, atom_model: bkchem_qt.models.atom_model.AtomModel):
		"""Add an atom to the molecule.

		Registers the AtomModel's underlying OASA atom with the backend
		molecule and stores the mapping.

		Args:
			atom_model: AtomModel to add.
		"""
		oasa_atom = atom_model._chem_atom
		self._chem_mol.add_vertex(oasa_atom)
		self._atom_models[id(oasa_atom)] = atom_model
		self.atom_added.emit(atom_model)

	#============================================
	def remove_atom(self, atom_model: bkchem_qt.models.atom_model.AtomModel):
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
		self.atom_removed.emit(atom_model)

	#============================================
	def add_bond(self, atom1_model: bkchem_qt.models.atom_model.AtomModel,
				 atom2_model: bkchem_qt.models.atom_model.AtomModel,
				 bond_model: bkchem_qt.models.bond_model.BondModel):
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
	def remove_bond(self, bond_model: bkchem_qt.models.bond_model.BondModel):
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
		self.bond_removed.emit(bond_model)

	# ------------------------------------------------------------------
	# Graph queries (delegated to _chem_mol)
	# ------------------------------------------------------------------

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
	def t_bond_first(self):
		"""First template attachment bond (BondModel or None)."""
		return self._t_bond_first

	#============================================
	@t_bond_first.setter
	def t_bond_first(self, value):
		self._t_bond_first = value

	#============================================
	@property
	def t_bond_second(self):
		"""Second template attachment bond (BondModel or None)."""
		return self._t_bond_second

	#============================================
	@t_bond_second.setter
	def t_bond_second(self, value):
		self._t_bond_second = value

	#============================================
	@property
	def t_atom(self):
		"""Template attachment atom (AtomModel or None)."""
		return self._t_atom

	#============================================
	@t_atom.setter
	def t_atom(self, value):
		self._t_atom = value

	#============================================
	def __repr__(self) -> str:
		"""Return a developer-friendly string representation."""
		n_atoms = len(self._atom_models)
		n_bonds = len(self._bond_models)
		return f"MoleculeModel({n_atoms} atoms, {n_bonds} bonds)"
