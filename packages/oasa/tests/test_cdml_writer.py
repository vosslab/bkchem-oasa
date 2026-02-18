# SPDX-License-Identifier: LGPL-3.0-or-later

"""Unit tests for OASA CDML molecule writer."""

# local repo modules
import oasa
from oasa import cdml_writer


#============================================
def test_cdml_writer_basic():
	mol = oasa.molecule()
	a1 = oasa.atom(symbol="O")
	a1.x = 0.0
	a1.y = 0.0
	a1._cdml_unknown_attrs = {"custom": "1"}
	a1._cdml_present = {"custom"}
	a2 = oasa.atom(symbol="C")
	a2.x = 12.0
	a2.y = 0.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	b = oasa.bond(order=1, type="n")
	b.vertices = (a1, a2)
	b.line_color = "#123456"
	b.properties_["line_color"] = "#123456"
	mol.add_edge(a1, a2, b)

	element = cdml_writer.write_cdml_molecule_element(mol, policy="always")
	assert element.tagName == "molecule"
	atoms = element.getElementsByTagName("atom")
	assert len(atoms) == 2
	assert atoms[0].getAttribute("custom") == "1"
	point = atoms[0].getElementsByTagName("point")[0]
	assert point.getAttribute("x").endswith("cm")
	bonds = element.getElementsByTagName("bond")
	assert len(bonds) == 1
	assert bonds[0].getAttribute("type") == "n1"
	assert bonds[0].getAttribute("color") == "#123456"
