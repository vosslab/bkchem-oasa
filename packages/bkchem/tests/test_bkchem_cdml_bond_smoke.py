"""Smoke checks for BKChem CDML bond serialization."""

# Standard Library
import xml.dom.minidom

# local repo modules
import bkchem.bond
import bkchem.classes
import singleton_store


class _DummyPaper(object):
	def __init__(self, standard):
		self.standard = standard

	def screen_to_real_ratio(self):
		return 1.0


class _DummyParent(object):
	def __init__(self, paper):
		self.paper = paper


class _DummyAtom(object):
	def __init__(self, atom_id):
		self.id = atom_id


class _DummyIdManager(object):
	def generate_and_register_id(self, obj, prefix=None):
		return "%s1" % (prefix or "obj")

	def is_registered_object(self, obj):
		return False

	def unregister_object(self, obj):
		return None

	def register_id(self, obj, obj_id):
		return None


#============================================
def test_bkchem_bond_serialization_smoke():
	original_manager = singleton_store.Store.id_manager
	singleton_store.Store.id_manager = _DummyIdManager()
	try:
		standard = bkchem.classes.standard()
		singleton_store.Screen.dpi = 72
		paper = _DummyPaper(standard)
		parent = _DummyParent(paper)
		bond = bkchem.bond.bond(standard=standard, type="n", order=1)
		bond.parent = parent
		bond.atom1 = _DummyAtom("a1")
		bond.atom2 = _DummyAtom("a2")
		bond.line_width = 1.0
		bond.wavy_style = "triangle"
		bond.properties_["custom"] = "keep"
		bond.properties_["_cdml_present"] = {
			"custom",
			"line_width",
			"wavy_style",
		}
		doc = xml.dom.minidom.Document()
		element = bond.get_package(doc)
		assert element.getAttribute("custom") == "keep"
		assert element.getAttribute("wavy_style") == "triangle"
		assert not element.hasAttribute("line_width")
	finally:
		singleton_store.Store.id_manager = original_manager
