"""Non-GUI coverage for OASA/CDML bond depiction bridge fields."""

# Standard Library
import math

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml_bond_io
import oasa.cdml_document
import oasa.cdml_writer
import oasa.safe_xml

import bkchem_qt.bridge.oasa_bridge
import bkchem_qt.canvas.items.bond_item


#============================================
def _accepted_oasa_molecule(cdml_text: str) -> object:
	"""Load one molecule only after the backend has accepted complete CDML."""
	accepted = oasa.cdml_document.CDMLDocument.parse(cdml_text)
	document = oasa.safe_xml.parse_dom_from_string(accepted.serialize())
	molecule_element = document.getElementsByTagName("molecule")[0]
	return oasa.cdml_writer.read_cdml_molecule_element(molecule_element)


#============================================
def test_new_oxygen_uses_its_periodic_table_valency() -> None:
	"""New scalar heteroatoms retain their element's chemistry default."""
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	assert molecule.create_atom("O").valency == 2


#============================================
def test_cdml_bond_display_fields_survive_oasa_qt_oasa_bridge() -> None:
	"""A colored triangular wedge remains visibly configured after bridging."""
	oasa_molecule = _accepted_oasa_molecule("""
	<cdml>
		<molecule id="m1">
			<atom id="a1" name="C"><point x="1cm" y="1cm"/></atom>
			<atom id="a2" name="O"><point x="2cm" y="1cm"/></atom>
			<bond id="b1" type="w2" start="a1" end="a2"
				line_width="1.5" bond_width="5.5" wedge_width="10.5"
				double_ratio="0.6" center="yes" auto_sign="-1" equithick="1"
				simple_double="1" color="#123456" wavy_style="triangle"/>
		</molecule>
	</cdml>
	""")

	qt_molecule = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(
		oasa_molecule, bond_length_pt=None,
	)
	roundtrip_molecule = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(qt_molecule)
	roundtrip_element = oasa.cdml_writer.write_cdml_molecule_element(roundtrip_molecule)
	roundtrip_bond = roundtrip_element.getElementsByTagName("bond")[0]
	assert (
		roundtrip_bond.getAttribute("type"),
		roundtrip_bond.getAttribute("color"),
		roundtrip_bond.getAttribute("wavy_style"),
	) == ("w2", "#123456", "triangle")


#============================================
def test_cdml_atom_display_fields_survive_oasa_qt_oasa_bridge() -> None:
	"""Atom-label visibility and typography survive the bridge round-trip."""
	oasa_molecule = _accepted_oasa_molecule("""
	<cdml>
		<molecule id="m1">
			<atom id="a1" name="C" show="yes" hydrogens="on">
				<point x="1cm" y="1cm"/>
				<font size="18" family="Courier New" color="#654321"/>
			</atom>
			<atom id="a2" name="O" show="no" hydrogens="off">
				<point x="2cm" y="1cm"/>
			</atom>
			<bond id="b1" type="n1" start="a1" end="a2"/>
		</molecule>
	</cdml>
	""")

	qt_molecule = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(
		oasa_molecule, bond_length_pt=None,
	)
	roundtrip_molecule = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(qt_molecule)
	roundtrip_element = oasa.cdml_writer.write_cdml_molecule_element(roundtrip_molecule)
	atom_elements = {
		atom_element.getAttribute("id"): atom_element
		for atom_element in roundtrip_element.getElementsByTagName("atom")
	}
	roundtrip_carbon = atom_elements["a1"]
	roundtrip_oxygen = atom_elements["a2"]
	carbon_font = roundtrip_carbon.getElementsByTagName("font")[0]
	assert (
		roundtrip_carbon.getAttribute("show"),
		roundtrip_carbon.getAttribute("hydrogens"),
		carbon_font.getAttribute("family"),
		carbon_font.getAttribute("color"),
	) == ("yes", "on", "Courier New", "#654321")
	assert (
		roundtrip_oxygen.getAttribute("show"),
		roundtrip_oxygen.getAttribute("hydrogens"),
	) == ("no", "off")


#============================================
def test_styled_values_reach_composed_qt_render_edge(qapp: object) -> None:
	"""Explicit adder choices reach one temporary bridge materialization."""
	del qapp
	oasa_molecule = _accepted_oasa_molecule("""
	<cdml>
		<molecule id="m1">
			<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom>
			<atom id="a2" name="C"><point x="2cm" y="0cm"/></atom>
			<bond id="b1" type="a2" start="a1" end="a2"
				line_width="2" bond_width="8" wedge_width="10"
				double_ratio="0.5" center="no" equithick="1"
				simple_double="0"/>
		</molecule>
	</cdml>
	""")
	qt_molecule = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(
		oasa_molecule, bond_length_pt=None,
	)
	bond_model = qt_molecule.bonds[0]
	materialized = bkchem_qt.bridge.oasa_bridge.materialize_oasa_bond(bond_model)
	item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
	paths = [op for op in item._ops if op.kind == "path"]
	lengths = sorted(
		abs(path.commands[-1][1][0] - path.commands[0][1][0])
		for path in paths
	)
	depiction = oasa.cdml_bond_io.resolve_bond_depiction(materialized)
	assert depiction.double_ratio == 0.5 and depiction.simple_double is False
	assert len(paths) == 2 and math.isclose(lengths[0], lengths[1] * 0.5)


#============================================
def test_absent_simple_double_stays_absent_through_qt_projection(
		qapp: object,
		) -> None:
	"""The semantic default is rendered but is not authored on round-trip."""
	del qapp
	oasa_molecule = _accepted_oasa_molecule("""
	<cdml>
		<molecule id="m1">
			<atom id="a1" name="C"><point x="0cm" y="0cm"/></atom>
			<atom id="a2" name="C"><point x="2cm" y="0cm"/></atom>
			<bond id="b1" type="a3" start="a1" end="a2"/>
		</molecule>
	</cdml>
	""")
	qt_molecule = bkchem_qt.bridge.oasa_bridge.oasa_mol_to_qt_mol(
		oasa_molecule, bond_length_pt=None,
	)
	bond_model = qt_molecule.bonds[0]
	item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
	roundtrip = bkchem_qt.bridge.oasa_bridge.qt_mol_to_oasa_mol(qt_molecule)
	roundtrip_element = oasa.cdml_writer.write_cdml_molecule_element(roundtrip)
	roundtrip_bond = roundtrip_element.getElementsByTagName("bond")[0]
	path_lengths = [
		abs(path.commands[-1][1][0] - path.commands[0][1][0])
		for path in item._ops if path.kind == "path"
	]
	assert bond_model.simple_double and max(path_lengths) > 0.0
	assert not roundtrip_bond.hasAttribute("simple_double")


#============================================
def test_legacy_bond_render_error_leaves_scalar_projection_usable(
		monkeypatch: pytest.MonkeyPatch, qapp: object,
		) -> None:
	"""A failed temporary bridge render does not poison the scalar projection."""
	del qapp
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	first = molecule.create_atom()
	second = molecule.create_atom()
	molecule.add_atom(first)
	molecule.add_atom(second)
	bond = molecule.create_bond()
	molecule.add_bond(first, second, bond)
	item = bkchem_qt.canvas.items.bond_item.BondItem(bond)
	def raise_render_error(*unused_args: object, **unused_kwargs: object) -> list:
		raise RuntimeError("render failure")
	monkeypatch.setattr(
		oasa.render_lib.bond_ops, "build_bond_ops", raise_render_error,
	)
	with pytest.raises(RuntimeError, match="render failure"):
		item.update_from_model()
	monkeypatch.undo()
	item.update_from_model()
	assert item.boundingRect().width() > 0.0
