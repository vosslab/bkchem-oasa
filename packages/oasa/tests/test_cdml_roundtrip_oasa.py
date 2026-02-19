"""OASA CDML round-trip metadata checks."""

# local repo modules
import oasa


# -- inline CDML test data --

CUSTOM_ATTR_CDML = """\
<?xml version="1.0" encoding="utf-8"?>
<cdml version="26.02" xmlns="http://www.freesoftware.fsf.org/bkchem/cdml">
  <molecule id="m1">
    <atom id="a1" name="C">
      <point x="1.0cm" y="1.0cm" />
    </atom>
    <atom id="a2" name="O">
      <point x="2.0cm" y="1.0cm" />
    </atom>
    <bond type="n1" start="a1" end="a2" custom="keep" />
  </molecule>
</cdml>
"""

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
def test_oasa_preserves_custom_attributes():
	"""Custom bond attributes survive CDML parse round-trip."""
	mol = oasa.cdml.text_to_mol(CUSTOM_ATTR_CDML)
	assert mol is not None
	assert mol.edges
	bond = next(iter(mol.edges))
	assert bond.properties_.get("custom") == "keep"
	present = bond.properties_.get("_cdml_present")
	assert present is not None
	assert "custom" in present


#============================================
def test_oasa_preserves_wavy_and_color():
	"""Wavy style and line color survive CDML parse."""
	mol = oasa.cdml.text_to_mol(WAVY_COLOR_CDML)
	bond = next(iter(mol.edges))
	assert bond.type == "s"
	assert bond.wavy_style == "triangle"
	assert bond.line_color == "#239e2d"


#============================================
def test_oasa_canonicalizes_vertex_ordering():
	"""Wedge bond vertices are canonicalized so v2 is the front vertex."""
	mol = oasa.cdml.text_to_mol(VERTEX_ORDERING_CDML)
	bonds = [bond for bond in mol.edges if bond.type in ("w", "h")]
	assert bonds
	for bond in bonds:
		v1, v2 = bond.vertices
		# v2 should be the front vertex (larger y, or larger x if y tied)
		front = v1
		if v2.y > v1.y:
			front = v2
		elif v2.y == v1.y and v2.x > v1.x:
			front = v2
		assert v2 is front
