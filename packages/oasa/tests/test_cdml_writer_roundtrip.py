"""Round-trip tests for the OASA CDML molecule writer."""

# Standard Library
import xml.dom.minidom

# local repo modules
import oasa


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

VERTEX_ORDERING_CDML = """\
<?xml version="1.0" encoding="utf-8"?>
<cdml version="26.02" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
  <molecule id="m1">
    <atom id="a1" name="C">
      <point x="0.0cm" y="0.0cm" />
    </atom>
    <atom id="a2" name="C">
      <point x="0.0cm" y="1.0cm" />
    </atom>
    <bond type="w1" start="a1" end="a2" />
  </molecule>
</cdml>
"""


#============================================
def _roundtrip_molecule(cdml_text: str):
	"""Parse CDML, write it back out, and parse again.

	Args:
		cdml_text: raw CDML XML string.

	Returns:
		molecule object from the second parse.
	"""
	mol = oasa.cdml.text_to_mol(cdml_text)
	if mol is None:
		raise AssertionError("Failed to load CDML text")
	# write back to XML
	doc = xml.dom.minidom.Document()
	root = doc.createElement("cdml")
	root.setAttribute("version", "26.02")
	doc.appendChild(root)
	root.appendChild(
		oasa.cdml_writer.write_cdml_molecule_element(
			mol, doc=doc, policy="present_only",
		)
	)
	return oasa.cdml.text_to_mol(doc.toxml("utf-8"))


#============================================
def test_cdml_writer_roundtrip_wavy_color():
	"""Wavy style and color survive write-then-read round-trip."""
	mol = _roundtrip_molecule(WAVY_COLOR_CDML)
	assert mol is not None
	bond = next(iter(mol.edges))
	assert bond.type == "s"
	assert bond.wavy_style == "triangle"
	assert bond.line_color == "#239e2d"


#============================================
def test_cdml_writer_roundtrip_vertex_ordering():
	"""Wedge bond vertex ordering survives write-then-read round-trip."""
	mol = _roundtrip_molecule(VERTEX_ORDERING_CDML)
	assert mol is not None
	bonds = [bond for bond in mol.edges if bond.type in ("w", "h")]
	assert bonds
	for bond in bonds:
		v1, v2 = bond.vertices
		# v2 should be the front vertex after canonicalization
		front = v1
		if v2.y > v1.y:
			front = v2
		elif v2.y == v1.y and v2.x > v1.x:
			front = v2
		assert v2 is front
