"""Test that unknown CDML attributes survive read_package/get_package round-trip
for all four vertex types: atom, group, query, and text."""

# Standard Library
import xml.dom.minidom

# PIP3 modules
import pytest

# local repo modules
import bkchem.atom_lib
import bkchem.group_lib
import bkchem.queryatom_lib
import bkchem.textatom_lib
import bkchem.molecule_lib
import bkchem.classes
import bkchem.singleton_store

Store = bkchem.singleton_store.Store
Screen = bkchem.singleton_store.Screen


#============================================
class _DummyPaper:
	"""Minimal paper stub."""

	def __init__(self, standard):
		self.standard = standard

	def real_to_screen_ratio(self):
		return 1.0

	def screen_to_real_ratio(self):
		return 1.0

	def real_to_screen_coords(self, coords):
		return coords

	def screen_to_real_coords(self, coords):
		return coords


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
	"""Return a minimal BKChem molecule wired to paper."""
	mol = bkchem.molecule_lib.BkMolecule(paper=paper)
	return mol


#============================================
def _make_element(tag: str, attrs: dict) -> xml.dom.minidom.Element:
	"""Create a DOM element with the given tag and attributes.

	Also adds a <point> child element required by vertex read_package.

	Args:
		tag: Element tag name (atom, group, query, text).
		attrs: dict of attribute name -> value.

	Returns:
		DOM element ready for read_package.
	"""
	doc = xml.dom.minidom.Document()
	el = doc.createElement(tag)
	for name, value in attrs.items():
		el.setAttribute(name, value)
	# all vertex types expect a <point> child with x,y coordinates
	point = doc.createElement("point")
	point.setAttribute("x", "1.000cm")
	point.setAttribute("y", "1.000cm")
	el.appendChild(point)
	return el


#============================================
def test_atom_unknown_attr_roundtrip(paper, molecule):
	"""Unknown CDML attribute on <atom> survives read_package -> get_package."""
	el = _make_element("atom", {
		"id": "a1",
		"name": "C",
		"pos": "center-first",
		"data-custom": "hello",
	})
	atom = bkchem.atom_lib.BkAtom(standard=paper.standard, molecule=molecule)
	atom.read_package(el)
	# verify unknown attr was stored
	assert atom.properties_.get("data-custom") == "hello"
	# serialize and check DOM
	doc = xml.dom.minidom.Document()
	out_el = atom.get_package(doc)
	assert out_el.getAttribute("data-custom") == "hello"


#============================================
def test_group_unknown_attr_roundtrip(paper, molecule):
	"""Unknown CDML attribute on <group> survives read_package -> get_package."""
	el = _make_element("group", {
		"id": "g1",
		"name": "CH3",
		"pos": "center-first",
		"group-type": "builtin",
		"data-custom": "world",
	})
	group = bkchem.group_lib.BkGroup(standard=paper.standard, molecule=molecule)
	group.read_package(el)
	assert group.properties_.get("data-custom") == "world"
	doc = xml.dom.minidom.Document()
	out_el = group.get_package(doc)
	assert out_el.getAttribute("data-custom") == "world"


#============================================
def test_query_unknown_attr_roundtrip(paper, molecule):
	"""Unknown CDML attribute on <query> survives read_package -> get_package."""
	el = _make_element("query", {
		"id": "q1",
		"name": "X",
		"pos": "center-first",
		"data-custom": "query-val",
	})
	query = bkchem.queryatom_lib.BkQueryatom(standard=paper.standard, molecule=molecule)
	query.read_package(el)
	assert query.properties_.get("data-custom") == "query-val"
	doc = xml.dom.minidom.Document()
	out_el = query.get_package(doc)
	assert out_el.getAttribute("data-custom") == "query-val"


#============================================
def test_text_unknown_attr_roundtrip(paper, molecule):
	"""Unknown CDML attribute on <text> survives read_package -> get_package."""
	doc = xml.dom.minidom.Document()
	el = doc.createElement("text")
	el.setAttribute("id", "t1")
	el.setAttribute("pos", "center-first")
	el.setAttribute("data-custom", "text-val")
	# text atoms need a <point> child
	point = doc.createElement("point")
	point.setAttribute("x", "1.000cm")
	point.setAttribute("y", "1.000cm")
	el.appendChild(point)
	# text atoms need an <ftext> child
	ftext = doc.createElement("ftext")
	ftext.appendChild(doc.createTextNode("ABC"))
	el.appendChild(ftext)

	text_atom = bkchem.textatom_lib.BkTextatom(standard=paper.standard, molecule=molecule)
	text_atom.read_package(el)
	assert text_atom.properties_.get("data-custom") == "text-val"
	out_el = text_atom.get_package(doc)
	assert out_el.getAttribute("data-custom") == "text-val"
