"""Non-GUI coverage for OASA/CDML bond depiction bridge fields."""

# Standard Library
import math

# local repo modules
import oasa.cdml_bond_io
import oasa.cdml_document
import oasa.cdml_writer
import oasa.render_ops
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
	"""Explicit adder choices drive the OASA edge rendered by BondItem."""
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
	depiction = oasa.cdml_bond_io.resolve_bond_depiction(
		bond_model._chem_bond,
	)
	item = bkchem_qt.canvas.items.bond_item.BondItem(bond_model)
	paths = [op for op in item._ops if isinstance(op, oasa.render_ops.PathOp)]
	lengths = sorted(
		abs(path.commands[-1][1][0] - path.commands[0][1][0])
		for path in paths
	)
	assert (
		depiction.simple_double,
		depiction.double_ratio,
		depiction.equithick,
		depiction.explicit_fields,
	) == (
		False,
		0.5,
		True,
		frozenset({
			"bond_width", "center", "double_ratio", "equithick",
			"line_width", "simple_double", "wedge_width",
		}),
	)
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
	path_count = sum(
		isinstance(op, oasa.render_ops.PathOp) for op in item._ops
	)
	line_count = sum(
		isinstance(op, oasa.render_ops.LineOp) for op in item._ops
	)
	assert (
		bond_model.simple_double,
		bond_model._chem_bond.simple_double,
		path_count,
		line_count,
	) == (True, 1, 1, 2)
	assert not roundtrip_bond.hasAttribute("simple_double")
