"""Test that oasa_atom_to_bkchem_atom copies multiplicity from the source OASA atom."""

# PIP3 modules
import pytest

# local repo modules
import oasa
import bkchem.classes
import bkchem.singleton_store
import bkchem.oasa_bridge

Store = bkchem.singleton_store.Store
Screen = bkchem.singleton_store.Screen


#============================================
class _DummyPaper:
	"""Minimal paper stub with standard settings."""

	def __init__(self, standard):
		self.standard = standard


#============================================
class _DummyIdManager:
	"""Minimal id manager stub."""

	def __init__(self):
		self._registry = {}
		self._counts = {}

	def generate_and_register_id(self, obj, prefix=None):
		key = prefix or "obj"
		self._counts[key] = self._counts.get(key, 0) + 1
		obj_id = "%s%d" % (key, self._counts[key])
		self._registry[obj_id] = obj
		return obj_id

	def is_registered_object(self, obj):
		return any(v is obj for v in self._registry.values())

	def unregister_object(self, obj):
		return None

	def register_id(self, obj, obj_id):
		self._registry[str(obj_id)] = obj

	def get_object_with_id(self, obj_id):
		return self._registry.get(str(obj_id))


#============================================
@pytest.fixture(autouse=True)
def _setup_singletons():
	"""Set up singleton store with dummy id_manager for all tests."""
	original_manager = Store.id_manager
	original_dpi = getattr(Screen, "dpi", 72)
	Store.id_manager = _DummyIdManager()
	Screen.dpi = 72
	yield
	Store.id_manager = original_manager
	Screen.dpi = original_dpi


#============================================
@pytest.fixture()
def paper():
	"""Return a dummy paper with standard settings."""
	standard = bkchem.classes.standard()
	return _DummyPaper(standard)


#============================================
@pytest.fixture()
def molecule(paper):
	"""Return a minimal BKChem molecule for atom creation."""
	import bkchem.molecule_lib
	mol = bkchem.molecule_lib.BkMolecule(paper=paper)
	return mol


#============================================
def _make_oasa_atom(symbol: str = "C", multiplicity: int = 1) -> oasa.Atom:
	"""Create a pure OASA atom with the given multiplicity.

	Args:
		symbol: Element symbol.
		multiplicity: Spin multiplicity (1=singlet, 2=doublet/radical, 3=triplet).

	Returns:
		oasa.Atom with coordinates and multiplicity set.
	"""
	a = oasa.Atom(symbol=symbol)
	a.x = 0.0
	a.y = 0.0
	a.z = 0.0
	a.multiplicity = multiplicity
	return a


#============================================
def test_multiplicity_radical(paper, molecule):
	"""Multiplicity=2 (radical) is copied from OASA atom to BKChem atom."""
	a = _make_oasa_atom("C", multiplicity=2)
	bk_atom = bkchem.oasa_bridge.oasa_atom_to_bkchem_atom(a, paper, molecule)
	assert bk_atom.multiplicity == 2


#============================================
def test_multiplicity_triplet(paper, molecule):
	"""Multiplicity=3 (triplet) is copied from OASA atom to BKChem atom."""
	a = _make_oasa_atom("O", multiplicity=3)
	bk_atom = bkchem.oasa_bridge.oasa_atom_to_bkchem_atom(a, paper, molecule)
	assert bk_atom.multiplicity == 3


#============================================
def test_multiplicity_default_singlet(paper, molecule):
	"""Default multiplicity=1 (singlet) is preserved."""
	a = _make_oasa_atom("N", multiplicity=1)
	bk_atom = bkchem.oasa_bridge.oasa_atom_to_bkchem_atom(a, paper, molecule)
	assert bk_atom.multiplicity == 1
