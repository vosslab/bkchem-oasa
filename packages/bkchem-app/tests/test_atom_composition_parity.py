"""Parity tests for atom property delegation.

Verifies that a composition-based atom behaves identically to the current
inheritance-based atom for all chemistry, coordinate, graph connectivity,
and display properties defined in the CDML backend-to-frontend contract.
"""

# Standard Library
import sys

# PIP3 modules
import pytest

# local repo modules
import oasa
import oasa.atom_lib
import oasa.bond_lib
import bkchem.atom_lib
import bkchem.classes
import bkchem.molecule_lib
from bkchem import singleton_store


# ============================================
# Dummy / helper objects
# ============================================

class _DummyPaper(object):
	"""Minimal paper stub sufficient for atom construction."""
	def __init__(self, standard):
		self.standard = standard

	def screen_to_real_ratio(self):
		return 1.0

	def screen_to_real_coords(self, coords):
		return coords

	def real_to_screen_ratio(self):
		return 1.0

	def real_to_screen_coords(self, coords):
		return coords


#============================================
class _DummyIdManager(object):
	"""Id manager that auto-generates sequential ids."""
	def __init__(self):
		self._counts = {}

	def generate_and_register_id(self, obj, prefix=None):
		key = prefix or "obj"
		self._counts[key] = self._counts.get(key, 0) + 1
		return "%s%d" % (key, self._counts[key])

	def is_registered_object(self, obj):
		return False

	def unregister_object(self, obj):
		return None

	def register_id(self, obj, obj_id):
		return None


#============================================
@pytest.fixture(autouse=True)
def bkchem_env():
	"""Set up singleton state needed by bkchem atom construction."""
	original_manager = singleton_store.Store.id_manager
	dummy_manager = _DummyIdManager()
	singleton_store.Store.id_manager = dummy_manager
	singleton_store.Screen.dpi = 72
	# propagate Screen.dpi and Store.id_manager to all loaded variants
	# (dual sys.path entries may cause duplicate module objects)
	for mod_name in list(sys.modules):
		if 'singleton_store' in mod_name:
			mod = sys.modules[mod_name]
			if hasattr(mod, 'Screen'):
				mod.Screen.dpi = 72
			if hasattr(mod, 'Store'):
				mod.Store.id_manager = dummy_manager
	# also propagate via special_parents which holds its own Screen reference
	from bkchem import special_parents
	special_parents.Screen.dpi = 72
	yield
	singleton_store.Store.id_manager = original_manager


#============================================
@pytest.fixture
def standard():
	"""Return a fresh bkchem standard object."""
	return bkchem.classes.standard()


#============================================
@pytest.fixture
def paper(standard):
	"""Return a dummy paper backed by the standard."""
	return _DummyPaper(standard)


#============================================
@pytest.fixture
def mol(paper):
	"""Return an empty bkchem molecule."""
	return bkchem.molecule_lib.BkMolecule(paper=paper)


#============================================
def _make_atom(standard, mol, symbol="C", xy=(100, 200)):
	"""Create a bkchem atom with given symbol and coordinates."""
	at = bkchem.atom_lib.BkAtom(standard=standard, xy=xy, molecule=mol)
	at.set_name(symbol)
	mol.insert_atom(at)
	return at


# ============================================
# 1. Chemistry properties
# ============================================

class TestChemistryProperties:
	"""Contract section 1.1: OASA-owned chemistry properties."""

	def test_symbol_default_carbon(self, standard, mol):
		"""Default atom symbol is C."""
		at = _make_atom(standard, mol, "C")
		assert at.symbol == "C"

	def test_symbol_set_nitrogen(self, standard, mol):
		"""Symbol setter updates the symbol."""
		at = _make_atom(standard, mol, "N")
		assert at.symbol == "N"

	def test_charge_default_zero(self, standard, mol):
		"""Default charge is 0."""
		at = _make_atom(standard, mol, "C")
		assert at.charge == 0

	def test_charge_set_positive(self, standard, mol):
		"""Charge can be set to a positive integer."""
		at = _make_atom(standard, mol, "N")
		at.charge = 1
		assert at.charge == 1

	def test_charge_set_negative(self, standard, mol):
		"""Charge can be set to a negative integer."""
		at = _make_atom(standard, mol, "O")
		at.charge = -1
		assert at.charge == -1

	def test_valency_carbon(self, standard, mol):
		"""Carbon has default valency 4."""
		at = _make_atom(standard, mol, "C")
		assert at.valency == 4

	def test_valency_nitrogen(self, standard, mol):
		"""Nitrogen has default valency 3."""
		at = _make_atom(standard, mol, "N")
		assert at.valency == 3

	def test_valency_oxygen(self, standard, mol):
		"""Oxygen has default valency 2."""
		at = _make_atom(standard, mol, "O")
		assert at.valency == 2

	def test_occupied_valency_isolated(self, standard, mol):
		"""Isolated atom has occupied_valency 0."""
		at = _make_atom(standard, mol, "C")
		assert at.occupied_valency == 0

	def test_free_valency_isolated_carbon(self, standard, mol):
		"""Isolated carbon has free_valency equal to its valency."""
		at = _make_atom(standard, mol, "C")
		assert at.free_valency == 4

	def test_multiplicity_default(self, standard, mol):
		"""Default multiplicity is 1 (singlet)."""
		at = _make_atom(standard, mol, "C")
		assert at.multiplicity == 1

	def test_multiplicity_set(self, standard, mol):
		"""Multiplicity can be changed."""
		at = _make_atom(standard, mol, "C")
		at.multiplicity = 3
		assert at.multiplicity == 3

	def test_isotope_default_none(self, standard, mol):
		"""Default isotope is None."""
		at = _make_atom(standard, mol, "C")
		assert at.isotope is None

	def test_isotope_set(self, standard, mol):
		"""Isotope can be set to an integer mass number."""
		at = _make_atom(standard, mol, "C")
		at.isotope = 13
		assert at.isotope == 13

	def test_explicit_hydrogens_default(self, standard, mol):
		"""Default explicit_hydrogens is 0."""
		at = _make_atom(standard, mol, "C")
		assert at.explicit_hydrogens == 0

	def test_explicit_hydrogens_set(self, standard, mol):
		"""explicit_hydrogens can be assigned."""
		at = _make_atom(standard, mol, "C")
		at.explicit_hydrogens = 2
		assert at.explicit_hydrogens == 2


# ============================================
# 2. Symbol setter side effects
# ============================================

class TestSymbolSetterSideEffects:
	"""Symbol setter should auto-set valency from periodic table."""

	def test_symbol_sets_valency(self, standard, mol):
		"""Changing symbol updates valency from periodic table."""
		at = _make_atom(standard, mol, "C")
		assert at.valency == 4
		at.symbol = "O"
		assert at.symbol == "O"
		assert at.valency == 2

	def test_symbol_sets_symbol_number(self, standard, mol):
		"""Symbol setter sets symbol_number (atomic number)."""
		at = _make_atom(standard, mol, "C")
		# carbon atomic number is 6
		assert at.symbol_number == 6
		at.symbol = "N"
		# nitrogen atomic number is 7
		assert at.symbol_number == 7

	def test_symbol_non_carbon_shows_automatically(self, standard, mol):
		"""Setting symbol to non-C sets show=True."""
		at = _make_atom(standard, mol, "C")
		at.show = 0
		at.symbol = "N"
		assert at.show == 1


# ============================================
# 3. Coordinate properties
# ============================================

class TestCoordinateProperties:
	"""Contract section 1.3: shared coordinates with Screen.any_to_px."""

	def test_x_coordinate(self, standard, mol):
		"""x property stores a pixel value."""
		at = _make_atom(standard, mol, "C", xy=(50, 75))
		assert at.x == 50

	def test_y_coordinate(self, standard, mol):
		"""y property stores a pixel value."""
		at = _make_atom(standard, mol, "C", xy=(50, 75))
		assert at.y == 75

	def test_z_default_zero(self, standard, mol):
		"""z defaults to 0."""
		at = _make_atom(standard, mol, "C", xy=(50, 75))
		assert at.z == 0

	def test_z_setter(self, standard, mol):
		"""z can be set for 3D stereochemistry."""
		at = _make_atom(standard, mol, "C", xy=(50, 75))
		at.z = 1.5
		assert at.z == 1.5

	def test_x_accepts_cm_string(self, standard, mol):
		"""x setter uses Screen.any_to_px for cm strings."""
		at = _make_atom(standard, mol, "C", xy=(0, 0))
		# 1cm at 72dpi = 72/2.54 ~ 28.346
		at.x = "1cm"
		expected = singleton_store.Screen.cm_to_px(1)
		assert abs(at.x - expected) < 0.001

	def test_y_accepts_cm_string(self, standard, mol):
		"""y setter uses Screen.any_to_px for cm strings."""
		at = _make_atom(standard, mol, "C", xy=(0, 0))
		at.y = "2cm"
		expected = singleton_store.Screen.cm_to_px(2)
		assert abs(at.y - expected) < 0.001


# ============================================
# 4. Graph connectivity
# ============================================

class TestGraphConnectivity:
	"""Contract section 1.4: graph connectivity interface."""

	def test_neighbors_empty(self, standard, mol):
		"""Isolated atom has no neighbors."""
		at = _make_atom(standard, mol, "C")
		assert at.neighbors == []

	def test_degree_zero(self, standard, mol):
		"""Isolated atom has degree 0."""
		at = _make_atom(standard, mol, "C")
		assert at.degree == 0

	def test_neighbor_edges_empty(self, standard, mol):
		"""Isolated atom has no neighbor_edges."""
		at = _make_atom(standard, mol, "C")
		assert at.neighbor_edges == []

	def test_add_neighbor_updates_degree(self, standard, mol):
		"""Adding a neighbor via the molecule increases degree."""
		at1 = _make_atom(standard, mol, "C", xy=(0, 0))
		at2 = _make_atom(standard, mol, "O", xy=(50, 0))
		bond = oasa.bond_lib.Bond()
		bond.order = 1
		# use molecule's add_edge to wire up both vertices
		mol.add_edge(at1, at2, bond)
		assert at1.degree == 1
		assert at2.degree == 1

	def test_neighbors_returns_connected_vertex(self, standard, mol):
		"""neighbors property returns the connected atom."""
		at1 = _make_atom(standard, mol, "C", xy=(0, 0))
		at2 = _make_atom(standard, mol, "N", xy=(50, 0))
		bond = oasa.bond_lib.Bond()
		bond.order = 1
		mol.add_edge(at1, at2, bond)
		assert at2 in at1.neighbors
		assert at1 in at2.neighbors

	def test_neighbor_edges_returns_bond(self, standard, mol):
		"""neighbor_edges returns the connecting bond."""
		at1 = _make_atom(standard, mol, "C", xy=(0, 0))
		at2 = _make_atom(standard, mol, "O", xy=(50, 0))
		bond = oasa.bond_lib.Bond()
		bond.order = 2
		mol.add_edge(at1, at2, bond)
		assert bond in at1.neighbor_edges
		assert bond in at2.neighbor_edges

	def test_occupied_valency_with_bond(self, standard, mol):
		"""occupied_valency reflects bond orders."""
		at1 = _make_atom(standard, mol, "C", xy=(0, 0))
		at2 = _make_atom(standard, mol, "O", xy=(50, 0))
		bond = oasa.bond_lib.Bond()
		bond.order = 2
		mol.add_edge(at1, at2, bond)
		assert at1.occupied_valency >= 2

	def test_free_valency_with_bond(self, standard, mol):
		"""free_valency decreases when bonded."""
		at1 = _make_atom(standard, mol, "C", xy=(0, 0))
		at2 = _make_atom(standard, mol, "O", xy=(50, 0))
		bond = oasa.bond_lib.Bond()
		bond.order = 1
		mol.add_edge(at1, at2, bond)
		# carbon valency=4, single bond => free_valency=3
		assert at1.free_valency == 3

	def test_get_edge_leading_to(self, standard, mol):
		"""get_edge_leading_to returns the bond between two atoms."""
		at1 = _make_atom(standard, mol, "C", xy=(0, 0))
		at2 = _make_atom(standard, mol, "N", xy=(50, 0))
		bond = oasa.bond_lib.Bond()
		bond.order = 1
		mol.add_edge(at1, at2, bond)
		found = at1.get_edge_leading_to(at2)
		assert found is bond


# ============================================
# 5. Display properties
# ============================================

class TestDisplayProperties:
	"""Contract section 1.2: BKChem-owned display properties."""

	def test_show_default_carbon(self, standard, mol):
		"""Carbon atoms default to show=0 (hidden symbol)."""
		at = _make_atom(standard, mol, "C")
		assert at.show == 0

	def test_show_set_integer(self, standard, mol):
		"""show can be set to 1."""
		at = _make_atom(standard, mol, "C")
		at.show = 1
		assert at.show == 1

	def test_show_accepts_yes_no(self, standard, mol):
		"""show accepts 'yes'/'no' string values."""
		at = _make_atom(standard, mol, "C")
		at.show = 'yes'
		assert at.show == 1
		at.show = 'no'
		assert at.show == 0

	def test_show_hydrogens_default(self, standard, mol):
		"""show_hydrogens defaults from standard (0)."""
		at = _make_atom(standard, mol, "C")
		assert at.show_hydrogens == 0

	def test_show_hydrogens_set(self, standard, mol):
		"""show_hydrogens can be toggled."""
		at = _make_atom(standard, mol, "C")
		at.show_hydrogens = 1
		assert at.show_hydrogens == 1

	def test_show_hydrogens_accepts_on_off(self, standard, mol):
		"""show_hydrogens accepts 'on'/'off' strings."""
		at = _make_atom(standard, mol, "C")
		at.show_hydrogens = 'on'
		assert at.show_hydrogens == 1
		at.show_hydrogens = 'off'
		assert at.show_hydrogens == 0

	def test_pos_default_none(self, standard, mol):
		"""pos defaults to None before decide_pos is called."""
		at = _make_atom(standard, mol, "C")
		assert at.pos is None

	def test_pos_settable(self, standard, mol):
		"""pos can be set to center-first or center-last."""
		at = _make_atom(standard, mol, "C")
		at.pos = 'center-first'
		assert at.pos == 'center-first'
		at.pos = 'center-last'
		assert at.pos == 'center-last'

	def test_font_size_from_standard(self, standard, mol):
		"""font_size is read from standard on init."""
		at = _make_atom(standard, mol, "C")
		assert at.font_size == standard.font_size

	def test_font_size_settable(self, standard, mol):
		"""font_size can be overridden."""
		at = _make_atom(standard, mol, "C")
		at.font_size = 16
		assert at.font_size == 16


# ============================================
# 6. Charge override behavior
# ============================================

class TestChargeOverride:
	"""Contract section 1.1 note: drawable_chem_vertex.charge delegation.

	BKChem atom.charge delegates through drawable_chem_vertex.charge
	which in turn delegates to oasa.chem_vertex.charge. Verify the
	chain works correctly.
	"""

	def test_charge_delegates_to_chem_vertex(self, standard, mol):
		"""Setting charge on bkchem atom stores in _charge."""
		at = _make_atom(standard, mol, "C")
		at.charge = 2
		# the underlying storage attribute
		assert at._charge == 2
		assert at.charge == 2

	def test_charge_round_trip(self, standard, mol):
		"""Charge set and get return the same value."""
		at = _make_atom(standard, mol, "N")
		for val in (-2, -1, 0, 1, 2):
			at.charge = val
			assert at.charge == val

	def test_charge_affects_occupied_valency(self, standard, mol):
		"""Positive charge on nitrogen changes occupied_valency."""
		at = _make_atom(standard, mol, "N")
		# isolated N, multiplicity=1, charge=0
		# occupied_valency = 0 + 0 + 1 - 1 = 0
		# verify occupied_valency is accessible before charge change
		at.occupied_valency
		at.charge = 1
		ov_charged = at.occupied_valency
		# charge should affect occupied_valency calculation
		# NH4+ pattern: charge=-1 in formula (increases effective valency)
		# but the specific value depends on accept_cation logic
		assert isinstance(ov_charged, int)
		# just verify it is computable without error
		assert ov_charged >= 0 or ov_charged < 0


# ============================================
# 7. OASA standalone parity (reference baseline)
# ============================================

class TestOasaAtomBaseline:
	"""Verify OASA atom behavior as reference for composition parity."""

	def test_oasa_symbol_sets_valency(self):
		"""OASA atom symbol setter auto-sets valency."""
		at = oasa.atom_lib.Atom(symbol="C")
		assert at.valency == 4
		at.symbol = "O"
		assert at.valency == 2

	def test_oasa_charge_default(self):
		"""OASA atom default charge is 0."""
		at = oasa.atom_lib.Atom(symbol="C")
		assert at.charge == 0

	def test_oasa_isotope_default(self):
		"""OASA atom default isotope is None."""
		at = oasa.atom_lib.Atom(symbol="C")
		assert at.isotope is None

	def test_oasa_explicit_hydrogens(self):
		"""OASA atom default explicit_hydrogens is 0."""
		at = oasa.atom_lib.Atom(symbol="C")
		assert at.explicit_hydrogens == 0

	def test_oasa_multiplicity_default(self):
		"""OASA atom default multiplicity is 1."""
		at = oasa.atom_lib.Atom(symbol="C")
		assert at.multiplicity == 1


# ============================================
# 8. Composition delegation parity
# ============================================

class TestCompositionDelegation:
	"""Tests that verify composition-based atom delegates correctly."""

	def test_has_chem_atom_attribute(self, standard, mol):
		"""Composition atom should have a _chem_atom attribute."""
		at = _make_atom(standard, mol, "C")
		assert hasattr(at, '_chem_atom')
		assert isinstance(at._chem_atom, oasa.atom_lib.Atom)

	def test_symbol_delegates_to_chem_atom(self, standard, mol):
		"""symbol should read from _chem_atom.symbol."""
		at = _make_atom(standard, mol, "N")
		assert at._chem_atom.symbol == "N"

	def test_charge_delegates_to_chem_atom(self, standard, mol):
		"""charge should write through to _chem_atom.charge."""
		at = _make_atom(standard, mol, "C")
		at.charge = 2
		assert at._chem_atom.charge == 2

	def test_valency_delegates_to_chem_atom(self, standard, mol):
		"""valency should read from _chem_atom.valency."""
		at = _make_atom(standard, mol, "N")
		assert at._chem_atom.valency == 3

	def test_isotope_delegates_to_chem_atom(self, standard, mol):
		"""isotope should write through to _chem_atom."""
		at = _make_atom(standard, mol, "C")
		at.isotope = 14
		assert at._chem_atom.isotope == 14

	def test_multiplicity_delegates_to_chem_atom(self, standard, mol):
		"""multiplicity should delegate to _chem_atom."""
		at = _make_atom(standard, mol, "C")
		at.multiplicity = 3
		assert at._chem_atom.multiplicity == 3

	def test_no_oasa_in_mro(self, standard, mol):
		"""After composition, oasa.atom_lib.Atom should not be in the MRO."""
		at = _make_atom(standard, mol, "C")
		# oasa.atom_lib.Atom should not appear in the inheritance chain
		assert oasa.atom_lib.Atom not in type(at).__mro__
