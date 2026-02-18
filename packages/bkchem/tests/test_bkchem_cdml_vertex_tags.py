# Standard Library
import xml.dom.minidom

# local repo modules
import bkchem.atom
import bkchem.classes
import bkchem.group
import bkchem.molecule
import bkchem.queryatom
import bkchem.textatom
import singleton_store


class _DummyPaper(object):
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


class _DummyIdManager(object):
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
def test_bkchem_cdml_vertex_tags():
	original_manager = singleton_store.Store.id_manager
	singleton_store.Store.id_manager = _DummyIdManager()
	try:
		standard = bkchem.classes.standard()
		singleton_store.Screen.dpi = 72
		paper = _DummyPaper(standard)
		mol = bkchem.molecule.molecule(paper=paper)

		atom = bkchem.atom.atom(standard=standard, xy=(0, 0), molecule=mol)
		atom.set_name("N")
		atom.charge = 1
		mol.insert_atom(atom)

		group = bkchem.group.group(standard=standard, xy=(20, 0), molecule=mol)
		group.group_type = "builtin"
		group.symbol = "Me"
		mol.insert_atom(group)

		text = bkchem.textatom.textatom(standard=standard, xy=(40, 0), molecule=mol)
		text.symbol = "Label"
		mol.insert_atom(text)

		query = bkchem.queryatom.queryatom(standard=standard, xy=(60, 0), molecule=mol)
		query.set_name("R")
		query.free_sites = 2
		mol.insert_atom(query)

		doc = xml.dom.minidom.Document()
		element = mol.get_package(doc)
		vertex_nodes = [
			node
			for node in element.childNodes
			if node.nodeType == node.ELEMENT_NODE and node.tagName in ("atom", "group", "text", "query")
		]
		output_ids = [node.getAttribute("id") for node in vertex_nodes]
		expected_ids = [str(vertex.id) for vertex in mol.vertices]
		assert output_ids == expected_ids
		by_id = {node.getAttribute("id"): node for node in vertex_nodes}
		for vertex in mol.vertices:
			vertex_id = str(vertex.id)
			node = by_id.get(vertex_id)
			assert node is not None
			point = node.getElementsByTagName("point")[0]
			expected_x = singleton_store.Screen.px_to_text_with_unit(vertex.x)
			expected_y = singleton_store.Screen.px_to_text_with_unit(vertex.y)
			assert point.getAttribute("x") == expected_x
			assert point.getAttribute("y") == expected_y

		atom_el = by_id[str(atom.id)]
		assert atom_el.tagName == "atom"
		assert atom_el.getAttribute("name") == "N"
		assert atom_el.getAttribute("charge") == "1"

		group_el = by_id[str(group.id)]
		assert group_el.tagName == "group"
		assert group_el.getAttribute("group-type") == "builtin"
		assert group_el.getAttribute("name") == "Me"

		text_el = by_id[str(text.id)]
		assert text_el.tagName == "text"
		ftext_nodes = text_el.getElementsByTagName("ftext")
		assert ftext_nodes
		assert ftext_nodes[0].firstChild.nodeValue == "Label"

		query_el = by_id[str(query.id)]
		assert query_el.tagName == "query"
		assert query_el.getAttribute("name") == "R"
		assert query_el.getAttribute("free_sites") == "2"

		loaded = bkchem.molecule.molecule(paper=paper)
		loaded.read_package(element)
		assert len([v for v in loaded.atoms if v.__class__.__name__ == "atom"]) == 1
		assert len([v for v in loaded.atoms if v.__class__.__name__ == "group"]) == 1
		assert len([v for v in loaded.atoms if v.__class__.__name__ == "textatom"]) == 1
		assert len([v for v in loaded.atoms if v.__class__.__name__ == "queryatom"]) == 1
	finally:
		singleton_store.Store.id_manager = original_manager
