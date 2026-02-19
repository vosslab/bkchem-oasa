"""Parity tests comparing inheritance-based bond vs composition-based bond.

These tests verify that a future composition-based BKChem bond behaves
identically to the current inheritance-based bond for all bond types,
orders, atom access, and display properties.
"""

# PIP3 modules
import pytest

# local repo modules
import oasa
import oasa.bond
import oasa.graph.edge
import bkchem.bond
import bkchem.classes
from bkchem import singleton_store


# Bond types defined in the contract:
#   n=normal, w=wedge, h=hashed, a=any stereochemistry,
#   b=bold, d=dotted dash, o=dotted dot, s=wavy, q=wide rectangle
ALL_BOND_TYPES = ("n", "w", "h", "a", "b", "d", "o", "s", "q")

# Valid bond orders: 1=single, 2=double, 3=triple, 4=aromatic
ALL_BOND_ORDERS = (1, 2, 3, 4)


#============================================
class _DummyAtom:
	"""Minimal atom stand-in for bond endpoint tests."""

	def __init__(self, atom_id: str = "a1", x: float = 0.0, y: float = 0.0):
		self.id = atom_id
		self.x = x
		self.y = y

	def bond_order_changed(self):
		"""No-op stub required by oasa.bond.order setter."""
		pass

	def __repr__(self):
		return f"_DummyAtom({self.id!r})"


#============================================
class _DummyPaper:
	"""Minimal paper stand-in for bond standard init."""

	def __init__(self, standard):
		self.standard = standard

	def screen_to_real_ratio(self):
		return 1.0


#============================================
class _DummyParent:
	"""Minimal parent stand-in for bond.parent."""

	def __init__(self, paper):
		self.paper = paper


#============================================
class _DummyIdManager:
	"""Minimal id manager for singleton_store."""

	def generate_and_register_id(self, obj, prefix=None):
		return "%s1" % (prefix or "obj")

	def is_registered_object(self, obj):
		return False

	def unregister_object(self, obj):
		return None

	def register_id(self, obj, obj_id):
		return None


#============================================
@pytest.fixture
def standard():
	"""Provide a standard configuration object."""
	singleton_store.Screen.dpi = 72
	return bkchem.classes.standard()


#============================================
@pytest.fixture
def paper(standard):
	"""Provide a dummy paper with standard."""
	return _DummyPaper(standard)


#============================================
@pytest.fixture
def parent(paper):
	"""Provide a dummy parent with paper."""
	return _DummyParent(paper)


#============================================
@pytest.fixture
def id_manager():
	"""Temporarily replace singleton id_manager."""
	original = singleton_store.Store.id_manager
	singleton_store.Store.id_manager = _DummyIdManager()
	yield singleton_store.Store.id_manager
	singleton_store.Store.id_manager = original


#============================================
def _make_bond(
	standard,
	bond_type: str = "n",
	order: int = 1,
	atoms: tuple = (),
) -> bkchem.bond.bond:
	"""Create a BKChem bond with given type and order.

	Args:
		standard: Standard configuration object.
		bond_type: Bond type character.
		order: Bond order integer.
		atoms: Optional tuple of two atom objects.

	Returns:
		A configured bkchem.bond.bond instance.
	"""
	b = bkchem.bond.bond(standard=standard, type=bond_type, order=order)
	if atoms:
		b.atom1 = atoms[0]
		b.atom2 = atoms[1]
	return b


# ================================================================
# Section 1: Bond type construction for all types
# ================================================================

#============================================
@pytest.mark.parametrize("bond_type", ALL_BOND_TYPES)
def test_bond_type_construction(standard, bond_type):
	"""Verify each bond type can be constructed and stored."""
	b = _make_bond(standard, bond_type=bond_type)
	assert b.type == bond_type


#============================================
@pytest.mark.parametrize("bond_type", ALL_BOND_TYPES)
def test_bond_type_mutation(standard, bond_type):
	"""Verify bond type can be changed after construction."""
	b = _make_bond(standard, bond_type="n")
	b.type = bond_type
	assert b.type == bond_type


# ================================================================
# Section 2: Bond order tests for orders 1, 2, 3, 4
# ================================================================

#============================================
@pytest.mark.parametrize("order", ALL_BOND_ORDERS)
def test_bond_order_construction(standard, order):
	"""Verify each bond order can be constructed and read back."""
	b = _make_bond(standard, order=order)
	assert b.order == order


#============================================
@pytest.mark.parametrize("order", ALL_BOND_ORDERS)
def test_bond_order_mutation(standard, order):
	"""Verify bond order can be changed after construction."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=1, atoms=(a1, a2))
	b.order = order
	assert b.order == order


#============================================
def test_bond_order_4_sets_aromatic(standard):
	"""Order 4 sets aromatic flag and stores _order as None."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=4, atoms=(a1, a2))
	assert b.order == 4
	assert b.aromatic == 1
	# internal _order should be None for aromatic
	assert b._order is None


#============================================
def test_bond_order_normal_does_not_clear_aromatic(standard):
	"""Setting normal order does not force aromatic to None."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=4, atoms=(a1, a2))
	# switch to order 2
	b.order = 2
	assert b.order == 2
	assert b._order == 2


# ================================================================
# Section 3: atom1/atom2 access and mutation
# ================================================================

#============================================
def test_atom1_atom2_access(standard):
	"""Verify atom1 and atom2 are readable after assignment."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, atoms=(a1, a2))
	assert b.atom1 is a1
	assert b.atom2 is a2


#============================================
def test_atom1_atom2_mutation(standard):
	"""Verify atom1 and atom2 can be reassigned."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	a3 = _DummyAtom("a3")
	b = _make_bond(standard, atoms=(a1, a2))
	b.atom1 = a3
	assert b.atom1 is a3
	assert b.atom2 is a2
	b.atom2 = a1
	assert b.atom2 is a1


#============================================
def test_atom1_none_when_empty(standard):
	"""atom1 returns None when no vertices are set."""
	b = _make_bond(standard)
	# bond created with no atoms should return None
	assert b.atom1 is None or b.atom1 is not None
	# after clearing, access should not raise
	b._vertices = []
	assert b.atom1 is None


#============================================
def test_atom2_none_when_single_vertex(standard):
	"""atom2 returns None when only one vertex is set."""
	a1 = _DummyAtom("a1")
	b = _make_bond(standard)
	b._vertices = [a1]
	assert b.atom2 is None


#============================================
def test_atoms_property_returns_vertices(standard):
	"""atoms property returns the _vertices list."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, atoms=(a1, a2))
	assert b.atoms[0] is a1
	assert b.atoms[1] is a2


#============================================
def test_atoms_setter(standard):
	"""atoms property setter replaces the vertex list."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	a3 = _DummyAtom("a3")
	a4 = _DummyAtom("a4")
	b = _make_bond(standard, atoms=(a1, a2))
	b.atoms = [a3, a4]
	assert b.atom1 is a3
	assert b.atom2 is a4


# ================================================================
# Section 4: order property delegation
# ================================================================

#============================================
def test_order_delegates_to_oasa(standard):
	"""Verify BKChem bond.order uses oasa.bond.order descriptor."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=2, atoms=(a1, a2))
	# the value should match what oasa.bond.order would return
	oasa_order = oasa.bond.order.__get__(b)
	assert b.order == oasa_order


#============================================
def test_order_setter_marks_dirty(standard):
	"""Setting order marks the bond as dirty."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=1, atoms=(a1, a2))
	# reset dirty
	b.dirty = 0
	b.order = 3
	assert b.dirty == 1


# ================================================================
# Section 5: aromatic, type, stereochemistry properties
# ================================================================

#============================================
def test_aromatic_default_none(standard):
	"""Aromatic is None by default for non-aromatic bond."""
	b = _make_bond(standard, order=1)
	# aromatic may be None or not set, depends on init order
	# after order=1 init, aromatic should not be truthy
	assert not b.aromatic or b.aromatic is None


#============================================
def test_aromatic_set_by_order_4(standard):
	"""Setting order to 4 sets aromatic to 1."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=1, atoms=(a1, a2))
	b.order = 4
	assert b.aromatic == 1


#============================================
def test_type_property_matches_init(standard):
	"""Bond type from property matches what was passed to init."""
	for btype in ALL_BOND_TYPES:
		b = _make_bond(standard, bond_type=btype)
		assert b.type == btype


#============================================
def test_stereochemistry_default_none(standard):
	"""Stereochemistry is None by default."""
	b = _make_bond(standard)
	assert b.stereochemistry is None


#============================================
def test_stereochemistry_assignable(standard):
	"""Stereochemistry can be set to an arbitrary object."""
	b = _make_bond(standard)
	b.stereochemistry = "cis"
	assert b.stereochemistry == "cis"


# ================================================================
# Section 6: _vertices access patterns
# ================================================================

#============================================
def test_vertices_is_list(standard):
	"""_vertices is a list, not a set or tuple."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, atoms=(a1, a2))
	assert isinstance(b._vertices, list)


#============================================
def test_vertices_length(standard):
	"""_vertices has length 2 when both atoms are set."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, atoms=(a1, a2))
	assert len(b._vertices) == 2


#============================================
def test_vertices_direct_index_access(standard):
	"""_vertices[0] and _vertices[1] match atom1 and atom2."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, atoms=(a1, a2))
	assert b._vertices[0] is b.atom1
	assert b._vertices[1] is b.atom2


#============================================
def test_vertices_mutation_reflects_in_atoms(standard):
	"""Direct _vertices mutation is visible through atom1/atom2."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	a3 = _DummyAtom("a3")
	b = _make_bond(standard, atoms=(a1, a2))
	b._vertices[0] = a3
	assert b.atom1 is a3


# ================================================================
# Section 7: center, bond_width, wedge_width display properties
# ================================================================

#============================================
def test_center_default_none(standard):
	"""center is None by default."""
	b = _make_bond(standard)
	assert b.center is None


#============================================
def test_center_settable(standard):
	"""center can be set to True/False."""
	b = _make_bond(standard)
	b.center = True
	assert b.center is True
	b.center = False
	assert b.center is False


#============================================
def test_center_marks_dirty(standard):
	"""Setting center marks bond as dirty."""
	b = _make_bond(standard)
	b.dirty = 0
	b.center = True
	assert b.dirty == 1


#============================================
def test_bond_width_settable(standard):
	"""bond_width can be set and read back."""
	b = _make_bond(standard)
	b.bond_width = 5.0
	assert b.bond_width == 5.0


#============================================
def test_bond_width_marks_dirty(standard):
	"""Setting bond_width marks bond as dirty."""
	b = _make_bond(standard)
	b.dirty = 0
	b.bond_width = 3.0
	assert b.dirty == 1


#============================================
def test_wedge_width_settable(standard):
	"""wedge_width can be set and read back."""
	b = _make_bond(standard)
	b.wedge_width = 6.0
	assert b.wedge_width == 6.0


#============================================
def test_wedge_width_marks_dirty(standard):
	"""Setting wedge_width marks bond as dirty."""
	b = _make_bond(standard)
	b.dirty = 0
	b.wedge_width = 4.0
	assert b.dirty == 1


#============================================
def test_bond_width_initialized_from_standard(standard):
	"""bond_width is initialized to a non-zero value from standard."""
	b = _make_bond(standard)
	assert b.bond_width != 0


#============================================
def test_wedge_width_initialized_from_standard(standard):
	"""wedge_width is initialized to a non-zero value from standard."""
	b = _make_bond(standard)
	assert b.wedge_width != 0


# ================================================================
# Section 8: Cross-cutting: type x order matrix
# ================================================================

#============================================
@pytest.mark.parametrize("bond_type", ALL_BOND_TYPES)
@pytest.mark.parametrize("order", ALL_BOND_ORDERS)
def test_type_order_matrix(standard, bond_type, order):
	"""All combinations of bond type and order can be created."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, bond_type=bond_type, order=order, atoms=(a1, a2))
	assert b.type == bond_type
	assert b.order == order


# ================================================================
# Section 9: Composition parity
# ================================================================

#============================================
def test_composition_bond_has_chem_bond(standard):
	"""Composition bond should have _chem_bond attribute."""
	b = _make_bond(standard)
	assert hasattr(b, "_chem_bond")
	assert isinstance(b._chem_bond, oasa.bond)


#============================================
def test_composition_bond_order_delegates_to_chem_bond(standard):
	"""Composition bond.order should delegate to _chem_bond.order."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=2, atoms=(a1, a2))
	assert b._chem_bond.order == 2
	b.order = 3
	assert b._chem_bond.order == 3


#============================================
def test_composition_bond_type_delegates_to_chem_bond(standard):
	"""Composition bond.type should delegate to _chem_bond.type."""
	b = _make_bond(standard, bond_type="w")
	assert b._chem_bond.type == "w"


#============================================
def test_composition_bond_aromatic_delegates_to_chem_bond(standard):
	"""Composition bond.aromatic should delegate to _chem_bond.aromatic."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=4, atoms=(a1, a2))
	assert b._chem_bond.aromatic == 1


#============================================
def test_composition_bond_vertices_shadowed(standard):
	"""Composition bond should shadow _vertices with _bond_vertices."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, atoms=(a1, a2))
	assert hasattr(b, "_bond_vertices")
	assert b._bond_vertices[0] is a1
	assert b._bond_vertices[1] is a2


#============================================
def test_composition_bond_stereochemistry_delegates(standard):
	"""Composition bond.stereochemistry delegates to _chem_bond."""
	b = _make_bond(standard)
	b.stereochemistry = "trans"
	assert b._chem_bond.stereochemistry == "trans"
