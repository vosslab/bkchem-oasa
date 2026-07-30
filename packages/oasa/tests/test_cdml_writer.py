# SPDX-License-Identifier: LGPL-3.0-or-later

"""Unit tests for OASA CDML molecule writer."""

# PIP3 modules
import pytest

# local repo modules
import oasa
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib
from oasa import cdml_writer


#============================================
def _two_atom_molecule(bond_type: str, order: int) -> oasa.molecule_lib.Molecule:
	"""Build one two-atom graph with the requested bond serialization pair."""
	mol = oasa.molecule_lib.Molecule()
	first = oasa.atom_lib.Atom(symbol="C")
	second = oasa.atom_lib.Atom(symbol="C")
	mol.add_vertex(first)
	mol.add_vertex(second)
	mol.add_edge(first, second, oasa.bond_lib.Bond(order=order, type=bond_type))
	return mol


#============================================
def test_cdml_writer_basic() -> None:
	mol = oasa.molecule_lib.Molecule()
	a1 = oasa.atom_lib.Atom(symbol="O")
	a1.x = 0.0
	a1.y = 0.0
	a2 = oasa.atom_lib.Atom(symbol="C")
	a2.x = 12.0
	a2.y = 0.0
	mol.add_vertex(a1)
	mol.add_vertex(a2)
	b = oasa.bond_lib.Bond(order=1, type="n")
	b.vertices = (a1, a2)
	b.line_color = "#123456"
	b.properties_["line_color"] = "#123456"
	mol.add_edge(a1, a2, b)

	element = cdml_writer.write_cdml_molecule_element(mol, policy="always")
	assert element.tagName == "molecule"
	atoms = element.getElementsByTagName("atom")
	assert len(atoms) == 2
	point = atoms[0].getElementsByTagName("point")[0]
	assert point.getAttribute("x").endswith("cm")
	bonds = element.getElementsByTagName("bond")
	assert len(bonds) == 1
	assert bonds[0].getAttribute("type") == "n1"
	assert bonds[0].getAttribute("color") == "#123456"


#============================================
def test_cdml_writer_reserves_output_ids_without_assigning_live_ids() -> None:
	"""Reserved IDs affect emitted XML only, leaving new graph objects blank."""
	mol = oasa.molecule_lib.Molecule()
	first = oasa.atom_lib.Atom(symbol="C")
	second = oasa.atom_lib.Atom(symbol="N")
	mol.add_vertex(first)
	mol.add_vertex(second)
	bond = oasa.bond_lib.Bond(order=1, type="n")
	mol.add_edge(first, second, bond)
	element = cdml_writer.write_cdml_molecule_element(
			mol, reserved_atom_ids={"a1"}, reserved_bond_ids={"b1"},
		)
	assert (
		[atom.getAttribute("id") for atom in element.getElementsByTagName("atom")],
		element.getElementsByTagName("bond")[0].getAttribute("id"),
		getattr(first, "id", None), getattr(second, "id", None), getattr(bond, "id", None),
	) == (["a2", "a3"], "b2", None, None, None)


#============================================
def test_cdml_writer_authors_haworth_front_edge_as_single_bond() -> None:
	"""A Haworth front edge has the one authored q1 spelling."""
	element = cdml_writer.write_cdml_molecule_element(_two_atom_molecule("q", 1))
	assert element.getElementsByTagName("bond")[0].getAttribute("type") == "q1"


#============================================
def test_cdml_writer_rejects_non_authored_haworth_front_edge_order() -> None:
	"""A q2 graph edge cannot become a newly authored CDML bond."""
	with pytest.raises(ValueError, match=r"^Unsupported authored CDML bond type/order pair: q2$"):
		cdml_writer.write_cdml_molecule_element(_two_atom_molecule("q", 2))


#============================================
def test_cdml_writer_authors_ordinary_styled_double_bond() -> None:
	"""Existing styled ordinary bonds retain their supported authored orders."""
	element = cdml_writer.write_cdml_molecule_element(_two_atom_molecule("d", 2))
	assert element.getElementsByTagName("bond")[0].getAttribute("type") == "d2"
