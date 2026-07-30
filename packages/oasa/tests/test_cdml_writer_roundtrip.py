"""Round-trip tests for the OASA CDML molecule writer."""

# PIP3 modules
import pytest

# local repo modules
import oasa.cdml
import oasa.cdml_document
import oasa.cdml_xml
import oasa.cdml_writer
import oasa.atom_lib
import oasa.bond_lib
import oasa.molecule_lib


# -- inline CDML test data --

WAVY_COLOR_CDML = """\
<?xml version="1.0" encoding="utf-8"?>
<cdml version="26.02" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
  <molecule id="m1">
    <atom id="a1" name="C">
      <point x="1.0cm" y="1.0cm" />
    </atom>
    <atom id="a2" name="C">
      <point x="2.0cm" y="1.0cm" />
    </atom>
    <bond type="s1" start="a1" end="a2" color="#239e2d" wavy_style="triangle" />
  </molecule>
</cdml>
"""

DIRECTED_WEDGE_CDML = """\
<?xml version="1.0" encoding="utf-8"?>
<cdml version="26.07" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
  <molecule id="m1">
    <atom id="a1" name="C">
      <point x="0.0cm" y="1.0cm" />
    </atom>
    <atom id="a2" name="C">
      <point x="0.0cm" y="0.0cm" />
    </atom>
    <atom id="a3" name="C">
      <point x="1.0cm" y="1.0cm" />
    </atom>
    <atom id="a4" name="C">
      <point x="1.0cm" y="0.0cm" />
    </atom>
    <bond type="w1" start="a1" end="a2" />
    <bond type="n1" start="a2" end="a3" />
    <bond type="h1" start="a3" end="a4" />
  </molecule>
</cdml>
"""

PREFIXED_HAWORTH_CDML = """\
<cdml:cdml xmlns:cdml="http://www.freesoftware.fsf.org/bkchem/cdml">
  <cdml:molecule id="m1">
    <cdml:atom id="a1" name="C"><cdml:point x="0cm" y="0cm"/></cdml:atom>
    <cdml:atom id="a2" name="C"><cdml:point x="1cm" y="0cm"/></cdml:atom>
    <cdml:bond type="q1" start="a1" end="a2" cdml:haworth_position="front"/>
  </cdml:molecule>
</cdml:cdml>
"""


#============================================
def _roundtrip_molecule(cdml_text: str) -> oasa.molecule_lib.Molecule:
	"""Parse CDML, write it back out, and parse again.

	Args:
		cdml_text: raw CDML XML string.

	Returns:
		molecule object from the second parse.
	"""
	oasa.cdml_document.CDMLDocument.parse(cdml_text)
	mol = oasa.cdml.text_to_mol(cdml_text)
	if mol is None:
		raise AssertionError("Failed to load CDML text")
	serialized = oasa.cdml_writer.mol_to_text(mol, policy="present_only")
	oasa.cdml_document.CDMLDocument.parse(serialized)
	return oasa.cdml.text_to_mol(serialized)


#============================================
def test_cdml_writer_new_document_declares_authored_profile() -> None:
	"""A new OASA molecule document declares the current authored CDML profile."""
	mol = oasa.molecule_lib.Molecule()
	document = oasa.cdml_xml.inspect_cdml_xml(
		oasa.cdml_writer.mol_to_text(mol).encode("utf-8"),
	)
	proposal = oasa.cdml_xml.inspect_cdml_xml(
		oasa.cdml_writer.molecules_to_insertion_proposal([mol], token_stem="profile").encode("utf-8"),
	)
	assert (
		document.version,
		proposal.version,
	) == ("26.07", "26.07")


#============================================
def test_cdml_writer_roundtrip_wavy_color() -> None:
	"""Wavy style and color survive write-then-read round-trip."""
	mol = _roundtrip_molecule(WAVY_COLOR_CDML)
	assert mol is not None
	bond = next(iter(mol.edges))
	assert bond.type == "s"
	assert bond.wavy_style == "triangle"
	assert bond.line_color == "#239e2d"


#============================================
def test_cdml_writer_preserves_authored_directed_wedges_through_authority() -> None:
	"""Writer and strict insertion retain direction despite opposite Y ordering."""
	molecule = _roundtrip_molecule(DIRECTED_WEDGE_CDML)
	proposal = oasa.cdml_writer.molecules_to_insertion_proposal(
		[molecule], token_stem="directed",
	)
	session = oasa.cdml_document.CDMLDocumentSession.load(
		'<cdml version="26.07" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml"/>',
	)
	accepted = session.insert_molecules(
		oasa.cdml_document.CDMLMoleculeInsertionRequest(
			expected_revision=session.revision,
			proposal_cdml=proposal,
			label="Directed wedges",
		),
	)
	oasa.cdml_document.CDMLDocument.parse(accepted.cdml, validation="strict")
	reloaded = next(oasa.cdml.read_cdml(accepted.cdml))
	writer_endpoints = _directed_endpoint_ids(molecule)
	accepted_endpoints = _directed_endpoint_ids(reloaded)
	accepted_ids = accepted.id_map
	assert (writer_endpoints, accepted_endpoints) == (
		(("h", "a3", "a4"), ("w", "a1", "a2")),
		(
			("h", accepted_ids["__bkchem_new__directed_a3"], accepted_ids["__bkchem_new__directed_a4"]),
			("w", accepted_ids["__bkchem_new__directed_a1"], accepted_ids["__bkchem_new__directed_a2"]),
		),
	)


#============================================
def _directed_endpoint_ids(
		molecule: oasa.molecule_lib.Molecule,
		) -> tuple[tuple[str, str, str], ...]:
	"""Return typed CDML endpoint order for directional wedge styles."""
	return tuple(sorted(
		(str(bond.type), str(bond.vertices[0].id), str(bond.vertices[1].id))
		for bond in molecule.edges
		if bond.type in {"w", "h"}
	))


#============================================
def test_cdml_writer_roundtrip_preserves_prefixed_haworth_front_tag() -> None:
	"""A qualified Haworth depiction tag reloads as standard native CDML."""
	mol = _roundtrip_molecule(PREFIXED_HAWORTH_CDML)
	bond = next(iter(mol.edges))
	assert bond.properties_["haworth_position"] == "front"


#============================================
def test_cdml_writer_roundtrip_atom_chemistry_metadata() -> None:
	"""Atom chemistry metadata and three-dimensional coordinates round-trip."""
	mol = oasa.molecule_lib.Molecule()
	atom = oasa.atom_lib.Atom(
		symbol="N",
		charge=1,
		coords=(
			oasa.cdml_writer.POINTS_PER_CM * 1.25,
			-oasa.cdml_writer.POINTS_PER_CM * 0.5,
			oasa.cdml_writer.POINTS_PER_CM * 0.25,
		),
	)
	atom.multiplicity = 2
	atom.valency = 5
	atom.free_sites = 2
	atom.isotope = 15
	atom.explicit_hydrogens = 1
	mol.add_vertex(atom)

	atom_element = oasa.cdml_writer.write_cdml_molecule_element(mol)
	encoded_atom = atom_element.getElementsByTagName("atom")[0]
	loaded_mol = oasa.cdml_writer.read_cdml_molecule_element(atom_element)
	loaded_atom = next(iter(loaded_mol.vertices))

	assert (
		encoded_atom.getAttribute("isotope"),
		encoded_atom.getAttribute("explicit_hydrogens"),
		loaded_atom.charge,
		loaded_atom.multiplicity,
		loaded_atom.valency,
		loaded_atom.free_sites,
		loaded_atom.isotope,
		loaded_atom.explicit_hydrogens,
	) == ("15", "1", 1, 2, 5, 2, 15, 1)
	assert loaded_atom.coords == pytest.approx(atom.coords)


#============================================
def test_cdml_writer_loaded_molecule_new_atom_gets_unused_id() -> None:
	"""Saving an edited loaded molecule never duplicates a retained atom ID."""
	mol = oasa.cdml.text_to_mol(WAVY_COLOR_CDML)
	assert mol is not None
	new_atom = oasa.atom_lib.Atom(symbol="O", coords=(84.0, 28.0, 0.0))
	mol.add_vertex(new_atom)
	mol.add_edge(next(iter(mol.vertices)), new_atom, e=oasa.bond_lib.Bond())

	molecule_element = oasa.cdml_writer.write_cdml_molecule_element(mol)
	atom_elements = molecule_element.getElementsByTagName("atom")
	bond_elements = molecule_element.getElementsByTagName("bond")
	new_atom_element = next(
			atom_element for atom_element in atom_elements
			if atom_element.getAttribute("name") == "O"
		)
	new_atom_id = new_atom_element.getAttribute("id")
	new_bond_element = next(
			bond_element for bond_element in bond_elements
			if new_atom_id in {
				bond_element.getAttribute("start"),
				bond_element.getAttribute("end"),
			}
		)

	assert new_atom_id not in {"a1", "a2"}
	assert {
		new_bond_element.getAttribute("start"),
		new_bond_element.getAttribute("end"),
	} == {"a1", new_atom_id}
