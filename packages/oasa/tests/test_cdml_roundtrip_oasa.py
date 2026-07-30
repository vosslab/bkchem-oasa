"""OASA CDML round-trip metadata checks."""

# local repo modules
import oasa.cdml
import oasa.cdml_document


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
      <point x="0.0cm" y="1.0cm" />
    </atom>
    <atom id="a2" name="C">
      <point x="0.0cm" y="0.0cm" />
    </atom>
    <bond type="w1" start="a1" end="a2" />
  </molecule>
</cdml>
"""


#============================================
def test_oasa_preserves_wavy_and_color() -> None:
	"""Wavy style and line color survive CDML parse."""
	mol = oasa.cdml.text_to_mol(WAVY_COLOR_CDML)
	bond = next(iter(mol.edges))
	assert bond.type == "s"
	assert bond.wavy_style == "triangle"
	assert bond.line_color == "#239e2d"


#============================================
def test_oasa_preserves_authored_vertex_ordering() -> None:
	"""Wedge endpoints retain the serialized start-to-end order."""
	oasa.cdml_document.CDMLDocument.parse(VERTEX_ORDERING_CDML)
	mol = oasa.cdml.text_to_mol(VERTEX_ORDERING_CDML)
	bonds = [bond for bond in mol.edges if bond.type in ("w", "h")]
	assert bonds
	assert tuple((bond.vertices[0].y, bond.vertices[1].y) for bond in bonds) == ((72.0 / 2.54, 0.0),)
