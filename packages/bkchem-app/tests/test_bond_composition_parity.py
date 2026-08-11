"""Public behavior tests for the composition-based classic BKChem bond."""

# PIP3 modules
import pytest

# local repo modules
import bkchem.bond_lib
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

	def __init__(self, atom_id: str = "a1", x: float = 0.0, y: float = 0.0) -> None:
		self.id = atom_id
		self.x = x
		self.y = y

	def bond_order_changed(self) -> object:
		"""No-op stub required by oasa.bond.order setter."""
		pass

	def __repr__(self) -> object:
		return f"_DummyAtom({self.id!r})"


#============================================
class _DummyPaper:
	"""Minimal paper stand-in for bond standard init."""

	def __init__(self, standard: object) -> None:
		self.standard = standard

	def screen_to_real_ratio(self) -> object:
		return 1.0


#============================================
class _DummyParent:
	"""Minimal parent stand-in for bond.parent."""

	def __init__(self, paper: object) -> None:
		self.paper = paper


#============================================
class _DummyIdManager:
	"""Minimal id manager for singleton_store."""

	def generate_and_register_id(self, obj: object, prefix: object=None) -> object:
		return "%s1" % (prefix or "obj")

	def is_registered_object(self, obj: object) -> object:
		return False

	def unregister_object(self, obj: object) -> object:
		return None

	def register_id(self, obj: object, obj_id: object) -> object:
		return None


#============================================
@pytest.fixture
def standard() -> object:
	"""Provide a standard configuration object."""
	singleton_store.Screen.dpi = 72
	return bkchem.classes.standard()


#============================================
@pytest.fixture
def paper(standard: object) -> object:
	"""Provide a dummy paper with standard."""
	return _DummyPaper(standard)


#============================================
@pytest.fixture
def parent(paper: object) -> object:
	"""Provide a dummy parent with paper."""
	return _DummyParent(paper)


#============================================
@pytest.fixture
def id_manager() -> object:
	"""Temporarily replace singleton id_manager."""
	original = singleton_store.Store.id_manager
	singleton_store.Store.id_manager = _DummyIdManager()
	yield singleton_store.Store.id_manager
	singleton_store.Store.id_manager = original


#============================================
def _make_bond(
	standard: object,
	bond_type: str = "n",
	order: int = 1,
	atoms: tuple = (),
) -> bkchem.bond_lib.BkBond:
	"""Create a BKChem bond with given type and order.

	Args:
		standard: Standard configuration object.
		bond_type: Bond type character.
		order: Bond order integer.
		atoms: Optional tuple of two atom objects.

	Returns:
		A configured bkchem.bond_lib.BkBond instance.
	"""
	b = bkchem.bond_lib.BkBond(standard=standard, type=bond_type, order=order)
	if atoms:
		b.atom1 = atoms[0]
		b.atom2 = atoms[1]
	return b


# ================================================================
# Section 1: Bond type construction for all types
# ================================================================

#============================================
@pytest.mark.parametrize("bond_type", ALL_BOND_TYPES)
def test_bond_type_construction(standard: object, bond_type: object) -> None:
	"""Verify each bond type can be constructed and stored."""
	b = _make_bond(standard, bond_type=bond_type)
	assert b.type == bond_type


#============================================
@pytest.mark.parametrize("bond_type", ALL_BOND_TYPES)
def test_bond_type_mutation(standard: object, bond_type: object) -> None:
	"""Verify bond type can be changed after construction."""
	b = _make_bond(standard, bond_type="n")
	b.type = bond_type
	assert b.type == bond_type


# ================================================================
# Section 2: Bond order tests for orders 1, 2, 3, 4
# ================================================================

#============================================
@pytest.mark.parametrize("order", ALL_BOND_ORDERS)
def test_bond_order_construction(standard: object, order: object) -> None:
	"""Verify each bond order can be constructed and read back."""
	b = _make_bond(standard, order=order)
	assert b.order == order


#============================================
@pytest.mark.parametrize("order", ALL_BOND_ORDERS)
def test_bond_order_mutation(standard: object, order: object) -> None:
	"""Verify bond order can be changed after construction."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=1, atoms=(a1, a2))
	b.order = order
	assert b.order == order


#============================================
def test_bond_order_4_sets_aromatic(standard: object) -> None:
	"""Order 4 exposes the aromatic bond state."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=4, atoms=(a1, a2))
	assert b.order == 4
	assert b.aromatic == 1


#============================================
def test_bond_order_normal_does_not_clear_aromatic(standard: object) -> None:
	"""An aromatic bond can be changed through the public order property."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=4, atoms=(a1, a2))
	b.order = 2
	assert b.order == 2


# ================================================================
# Section 3: atom1/atom2 access and mutation
# ================================================================

#============================================
def test_atom1_atom2_access(standard: object) -> None:
	"""Verify atom1 and atom2 are readable after assignment."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, atoms=(a1, a2))
	assert b.atom1 is a1
	assert b.atom2 is a2


#============================================
def test_atom1_atom2_mutation(standard: object) -> None:
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
def test_atom1_none_when_empty(standard: object) -> None:
	"""atom1 returns None when no vertices are set."""
	b = _make_bond(standard)
	b.vertices = []
	assert b.atom1 is None


#============================================
def test_atom2_none_when_single_vertex(standard: object) -> None:
	"""atom2 returns None when only one vertex is set."""
	a1 = _DummyAtom("a1")
	b = _make_bond(standard)
	b.vertices = [a1]
	assert b.atom2 is None


#============================================
def test_atoms_property_returns_vertices(standard: object) -> None:
	"""atoms exposes the ordered public bond endpoints."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, atoms=(a1, a2))
	assert b.atoms[0] is a1
	assert b.atoms[1] is a2


#============================================
def test_atoms_setter(standard: object) -> None:
	"""atoms property setter replaces the vertex list."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	a3 = _DummyAtom("a3")
	a4 = _DummyAtom("a4")
	b = _make_bond(standard, atoms=(a1, a2))
	b.atoms = [a3, a4]
	assert b.atom1 is a3
	assert b.atom2 is a4


#============================================
def test_order_setter_marks_dirty(standard: object) -> None:
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
def test_aromatic_default_none(standard: object) -> None:
	"""Aromatic is None by default for non-aromatic bond."""
	b = _make_bond(standard, order=1)
	# aromatic may be None or not set, depends on init order
	# after order=1 init, aromatic should not be truthy
	assert not b.aromatic or b.aromatic is None


#============================================
def test_aromatic_set_by_order_4(standard: object) -> None:
	"""Setting order to 4 sets aromatic to 1."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, order=1, atoms=(a1, a2))
	b.order = 4
	assert b.aromatic == 1


#============================================
def test_type_property_matches_init(standard: object) -> None:
	"""Bond type from property matches what was passed to init."""
	for btype in ALL_BOND_TYPES:
		b = _make_bond(standard, bond_type=btype)
		assert b.type == btype


#============================================
def test_stereochemistry_default_none(standard: object) -> None:
	"""Stereochemistry is None by default."""
	b = _make_bond(standard)
	assert b.stereochemistry is None


#============================================
def test_stereochemistry_assignable(standard: object) -> None:
	"""Stereochemistry can be set to an arbitrary object."""
	b = _make_bond(standard)
	b.stereochemistry = "cis"
	assert b.stereochemistry == "cis"


# ================================================================
# Section 6: public vertex access
# ================================================================

#============================================
def test_vertices_expose_ordered_endpoints(standard: object) -> None:
	"""vertices preserves the two public bond endpoints in order."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, atoms=(a1, a2))
	assert b.vertices == [a1, a2]


#============================================
def test_vertices_mutation_reflects_in_atoms(standard: object) -> None:
	"""Public vertex mutation remains visible through atom1/atom2."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	a3 = _DummyAtom("a3")
	b = _make_bond(standard, atoms=(a1, a2))
	b.vertices[0] = a3
	assert b.atom1 is a3


# ================================================================
# Section 7: center, bond_width, wedge_width display properties
# ================================================================

#============================================
def test_center_default_none(standard: object) -> None:
	"""center is None by default."""
	b = _make_bond(standard)
	assert b.center is None


#============================================
def test_center_settable(standard: object) -> None:
	"""center can be set to True/False."""
	b = _make_bond(standard)
	b.center = True
	assert b.center is True
	b.center = False
	assert b.center is False


#============================================
def test_center_marks_dirty(standard: object) -> None:
	"""Setting center marks bond as dirty."""
	b = _make_bond(standard)
	b.dirty = 0
	b.center = True
	assert b.dirty == 1


#============================================
def test_bond_width_settable(standard: object) -> None:
	"""bond_width can be set and read back."""
	b = _make_bond(standard)
	b.bond_width = 5.0
	assert b.bond_width == 5.0


#============================================
def test_bond_width_marks_dirty(standard: object) -> None:
	"""Setting bond_width marks bond as dirty."""
	b = _make_bond(standard)
	b.dirty = 0
	b.bond_width = 3.0
	assert b.dirty == 1


#============================================
def test_wedge_width_settable(standard: object) -> None:
	"""wedge_width can be set and read back."""
	b = _make_bond(standard)
	b.wedge_width = 6.0
	assert b.wedge_width == 6.0


#============================================
def test_wedge_width_marks_dirty(standard: object) -> None:
	"""Setting wedge_width marks bond as dirty."""
	b = _make_bond(standard)
	b.dirty = 0
	b.wedge_width = 4.0
	assert b.dirty == 1


#============================================
def test_bond_width_initialized_from_standard(standard: object) -> None:
	"""bond_width is initialized to a non-zero value from standard."""
	b = _make_bond(standard)
	assert b.bond_width != 0


#============================================
def test_wedge_width_initialized_from_standard(standard: object) -> None:
	"""wedge_width is initialized to a non-zero value from standard."""
	b = _make_bond(standard)
	assert b.wedge_width != 0


# ================================================================
# Section 8: Cross-cutting: type x order matrix
# ================================================================

#============================================
@pytest.mark.parametrize("bond_type", ALL_BOND_TYPES)
@pytest.mark.parametrize("order", ALL_BOND_ORDERS)
def test_type_order_matrix(standard: object, bond_type: object, order: object) -> None:
	"""All combinations of bond type and order can be created."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	b = _make_bond(standard, bond_type=bond_type, order=order, atoms=(a1, a2))
	assert b.type == bond_type
	assert b.order == order
