"""Save-load-compare tests for CDML bond serialization round-trips."""

# Standard Library
import xml.dom.minidom

# PIP3 modules
import pytest

# local repo modules
import bkchem.bond
import bkchem.classes
import bkchem.singleton_store

# Use the same Store/Screen that bkchem.bond uses internally.
# The conftest adds bkchem/bkchem to sys.path, so bare "import singleton_store"
# creates a different module object than "bkchem.singleton_store".
Store = bkchem.singleton_store.Store
Screen = bkchem.singleton_store.Screen


# -- Dummy helpers matching existing test patterns --

class _DummyPaper(object):
	"""Minimal paper stub with screen/real ratio methods."""

	def __init__(self, standard):
		self.standard = standard

	def screen_to_real_ratio(self):
		return 1.0

	def real_to_screen_ratio(self):
		return 1.0


#============================================
class _DummyParent(object):
	def __init__(self, paper):
		self.paper = paper


#============================================
class _DummyAtom(object):
	"""Atom stub with id and registerable in id_manager."""

	def __init__(self, atom_id):
		self.id = atom_id


#============================================
class _DummyIdManager(object):
	"""Id manager that tracks objects by id for round-trip lookup."""

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


# -- Fixtures --

#============================================
@pytest.fixture(autouse=True)
def _setup_singletons():
	"""Set up singleton store with dummy id_manager and DPI for all tests."""
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
def atoms():
	"""Return a pair of dummy atoms registered in the id manager."""
	a1 = _DummyAtom("a1")
	a2 = _DummyAtom("a2")
	Store.id_manager.register_id(a1, "a1")
	Store.id_manager.register_id(a2, "a2")
	return a1, a2


#============================================
def _make_bond(paper, atoms, bond_type="n", order=1):
	"""Create a bond wired to dummy paper and atoms.

	Args:
		paper: _DummyPaper instance.
		atoms: Tuple of (_DummyAtom, _DummyAtom).
		bond_type: Bond type character.
		order: Bond order integer.

	Returns:
		bkchem.bond.bond instance ready for serialization.
	"""
	standard = paper.standard
	bnd = bkchem.bond.bond(standard=standard, type=bond_type, order=order)
	bnd.parent = _DummyParent(paper)
	bnd.atom1 = atoms[0]
	bnd.atom2 = atoms[1]
	return bnd


#============================================
def _roundtrip(bond):
	"""Serialize a bond to CDML and deserialize into a fresh bond.

	Args:
		bond: Source bkchem bond to serialize.

	Returns:
		bkchem.bond.bond loaded from the serialized DOM element.
	"""
	doc = xml.dom.minidom.Document()
	element = bond.get_package(doc)
	# create a fresh bond and read the serialized element
	loaded = bkchem.bond.bond(
		standard=bond.parent.paper.standard,
		type="n",
		order=1,
	)
	loaded.parent = bond.parent
	loaded.read_package(element)
	return loaded


# -- Test: bond type and order round-trip --

# all documented bond types
BOND_TYPES = ["n", "w", "h", "a", "b", "d", "o", "s", "q"]
BOND_ORDERS = [1, 2, 3]


#============================================
@pytest.mark.parametrize("bond_type", BOND_TYPES)
@pytest.mark.parametrize("order", BOND_ORDERS)
def test_bond_type_order_roundtrip(paper, atoms, bond_type, order):
	"""Bond type and order survive get_package -> read_package."""
	bond = _make_bond(paper, atoms, bond_type=bond_type, order=order)
	loaded = _roundtrip(bond)
	assert loaded.type == bond_type
	assert loaded.order == order


# -- Test: unknown CDML attributes preserved --

#============================================
def test_unknown_cdml_attributes_preserved(paper, atoms):
	"""Unknown CDML attributes stored in properties_ round-trip through save/load."""
	bond = _make_bond(paper, atoms)
	# inject an unknown attribute
	bond.properties_["custom_data"] = "hello"
	bond.properties_["_cdml_present"] = {
		"type", "start", "end", "id", "custom_data",
	}
	doc = xml.dom.minidom.Document()
	element = bond.get_package(doc)
	# the unknown attribute should appear in the DOM
	assert element.getAttribute("custom_data") == "hello"
	# load into a new bond
	loaded = bkchem.bond.bond(standard=paper.standard, type="n", order=1)
	loaded.parent = _DummyParent(paper)
	loaded.read_package(element)
	assert loaded.properties_.get("custom_data") == "hello"


# -- Test: coordinate unit conversion round-trip --

#============================================
def test_coordinate_cm_px_roundtrip():
	"""cm -> px -> cm conversion round-trips within rounding tolerance."""
	# use 72 dpi (set in fixture)
	cm_str = "3.500cm"
	px_value = Screen.any_to_px(cm_str)
	# convert back
	cm_back_str = Screen.px_to_text_with_unit(px_value)
	assert cm_back_str == cm_str


# -- Test: bond_width sign preservation --

#============================================
def test_bond_width_positive_roundtrip(paper, atoms):
	"""Positive bond_width survives round-trip for double bonds."""
	bond = _make_bond(paper, atoms, bond_type="n", order=2)
	bond.bond_width = 6.0
	loaded = _roundtrip(bond)
	assert abs(loaded.bond_width - 6.0) < 0.01


#============================================
def test_bond_width_negative_roundtrip(paper, atoms):
	"""Negative bond_width survives round-trip for double bonds."""
	bond = _make_bond(paper, atoms, bond_type="n", order=2)
	bond.bond_width = -6.0
	loaded = _roundtrip(bond)
	# bond_width is multiplied by screen_to_real_ratio on write
	# and by real_to_screen_ratio on read; both are 1.0 in our dummy
	assert abs(loaded.bond_width - (-6.0)) < 0.01


# -- Test: center and auto_sign preservation for double bonds --

#============================================
def test_center_yes_roundtrip(paper, atoms):
	"""center=yes survives round-trip for order-2 bonds."""
	bond = _make_bond(paper, atoms, bond_type="n", order=2)
	bond.center = 1
	bond.auto_bond_sign = -1
	loaded = _roundtrip(bond)
	# center is stored as yes/no, read back as index into ["no","yes"]
	assert loaded.center == 1
	assert loaded.auto_bond_sign == -1


#============================================
def test_center_no_roundtrip(paper, atoms):
	"""center=no survives round-trip for order-2 bonds."""
	bond = _make_bond(paper, atoms, bond_type="n", order=2)
	bond.center = 0
	loaded = _roundtrip(bond)
	assert loaded.center == 0


#============================================
def test_center_none_for_single_bond(paper, atoms):
	"""Single bonds do not serialize center attribute."""
	bond = _make_bond(paper, atoms, bond_type="n", order=1)
	doc = xml.dom.minidom.Document()
	element = bond.get_package(doc)
	# center should not be in the DOM for single bonds
	assert not element.hasAttribute("center")


# -- Test: wavy_style preservation --

#============================================
def test_wavy_style_roundtrip(paper, atoms):
	"""wavy_style attribute survives round-trip."""
	bond = _make_bond(paper, atoms, bond_type="s", order=1)
	bond.wavy_style = "triangle"
	loaded = _roundtrip(bond)
	assert loaded.wavy_style == "triangle"


#============================================
def test_wavy_style_none_not_serialized(paper, atoms):
	"""Bonds with no wavy_style do not emit the attribute."""
	bond = _make_bond(paper, atoms, bond_type="n", order=1)
	bond.wavy_style = None
	doc = xml.dom.minidom.Document()
	element = bond.get_package(doc)
	assert not element.hasAttribute("wavy_style")


# -- Test: line_color round-trip --

#============================================
def test_line_color_roundtrip(paper, atoms):
	"""Non-default line_color survives round-trip."""
	bond = _make_bond(paper, atoms)
	bond.line_color = "#ff0000"
	loaded = _roundtrip(bond)
	assert loaded.line_color == "#ff0000"


#============================================
def test_default_color_not_serialized(paper, atoms):
	"""Default color #000 is omitted from CDML output."""
	bond = _make_bond(paper, atoms)
	bond.line_color = "#000"
	doc = xml.dom.minidom.Document()
	element = bond.get_package(doc)
	assert not element.hasAttribute("color")


# -- Test: equithick round-trip --

#============================================
def test_equithick_roundtrip(paper, atoms):
	"""equithick=1 survives round-trip."""
	bond = _make_bond(paper, atoms, bond_type="w", order=1)
	bond.equithick = 1
	loaded = _roundtrip(bond)
	assert loaded.equithick == 1


#============================================
def test_equithick_zero_default(paper, atoms):
	"""equithick defaults to 0 when not in CDML."""
	bond = _make_bond(paper, atoms)
	bond.equithick = 0
	doc = xml.dom.minidom.Document()
	element = bond.get_package(doc)
	# equithick=0 should not be serialized (it is the default)
	assert not element.hasAttribute("equithick")


# -- Test: double_length_ratio round-trip --

#============================================
def test_double_length_ratio_roundtrip(paper, atoms):
	"""double_length_ratio survives round-trip for double bonds."""
	bond = _make_bond(paper, atoms, bond_type="n", order=2)
	bond.double_length_ratio = 0.6
	loaded = _roundtrip(bond)
	assert abs(loaded.double_length_ratio - 0.6) < 0.001


# -- Test: simple_double round-trip for non-normal bonds --

#============================================
def test_simple_double_roundtrip(paper, atoms):
	"""simple_double survives round-trip for non-normal bond with order > 1."""
	bond = _make_bond(paper, atoms, bond_type="w", order=2)
	bond.simple_double = 0
	loaded = _roundtrip(bond)
	assert loaded.simple_double == 0


# -- Test: wedge_width round-trip for non-normal bonds --

#============================================
def test_wedge_width_roundtrip(paper, atoms):
	"""wedge_width survives round-trip for non-normal (wedge) bonds."""
	bond = _make_bond(paper, atoms, bond_type="w", order=1)
	bond.wedge_width = 5.0
	loaded = _roundtrip(bond)
	# screen_to_real_ratio and real_to_screen_ratio both 1.0
	assert abs(loaded.wedge_width - 5.0) < 0.01


# -- Test: auto_bond_sign default is 1 --

#============================================
def test_auto_bond_sign_default(paper, atoms):
	"""auto_bond_sign defaults to 1 when not serialized."""
	bond = _make_bond(paper, atoms, bond_type="n", order=2)
	bond.center = 1
	bond.auto_bond_sign = 1
	doc = xml.dom.minidom.Document()
	element = bond.get_package(doc)
	# auto_sign should not be serialized when it equals the default of 1
	assert not element.hasAttribute("auto_sign")
