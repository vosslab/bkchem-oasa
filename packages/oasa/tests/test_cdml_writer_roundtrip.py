# SPDX-License-Identifier: LGPL-3.0-or-later

"""Round-trip tests for the OASA CDML molecule writer."""

# Standard Library
import os
import xml.dom.minidom

# Local repo modules
import conftest

# local repo modules
import oasa


FIXTURES_DIR = conftest.repo_tests_path("fixtures", "cdml_roundtrip")


#============================================
def _roundtrip_molecule(name):
	path = os.path.join(FIXTURES_DIR, name)
	with open(path, "r", encoding="utf-8") as handle:
		text = handle.read()
	mol = oasa.cdml.text_to_mol(text)
	if mol is None:
		raise AssertionError("Failed to load CDML fixture: %s" % path)
	doc = xml.dom.minidom.Document()
	root = doc.createElement("cdml")
	root.setAttribute("version", "26.02")
	doc.appendChild(root)
	root.appendChild(oasa.cdml_writer.write_cdml_molecule_element(mol, doc=doc, policy="present_only"))
	return oasa.cdml.text_to_mol(doc.toxml("utf-8"))


#============================================
def test_cdml_writer_roundtrip_custom_attrs():
	mol = _roundtrip_molecule("custom_attr.cdml")
	assert mol is not None
	bond = next(iter(mol.edges))
	assert bond.properties_.get("custom") == "keep"


#============================================
def test_cdml_writer_roundtrip_wavy_color():
	mol = _roundtrip_molecule("wavy_color.cdml")
	assert mol is not None
	bond = next(iter(mol.edges))
	assert bond.type == "s"
	assert bond.wavy_style == "triangle"
	assert bond.line_color == "#239e2d"


#============================================
def test_cdml_writer_roundtrip_vertex_ordering():
	mol = _roundtrip_molecule("vertex_ordering.cdml")
	assert mol is not None
	bonds = [bond for bond in mol.edges if bond.type in ("w", "h")]
	assert bonds
	for bond in bonds:
		v1, v2 = bond.vertices
		front = v1
		if v2.y > v1.y:
			front = v2
		elif v2.y == v1.y and v2.x > v1.x:
			front = v2
		assert v2 is front
