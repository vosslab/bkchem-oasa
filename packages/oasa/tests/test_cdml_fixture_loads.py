"""Load inline CDML test data in OASA."""

# Standard Library
import tempfile
import os

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
def test_custom_attr_cdml_loads():
	"""Custom attribute CDML loads without error."""
	mol = oasa.cdml.text_to_mol(CUSTOM_ATTR_CDML)
	assert mol is not None
	assert len(list(mol.vertices)) >= 2
	assert len(list(mol.edges)) >= 1


#============================================
def test_wavy_color_cdml_loads():
	"""Wavy bond with color CDML loads without error."""
	mol = oasa.cdml.text_to_mol(WAVY_COLOR_CDML)
	assert mol is not None
	assert len(list(mol.vertices)) >= 2
	assert len(list(mol.edges)) >= 1


#============================================
def test_vertex_ordering_cdml_loads():
	"""Wedge bond vertex ordering CDML loads without error."""
	mol = oasa.cdml.text_to_mol(VERTEX_ORDERING_CDML)
	assert mol is not None
	assert len(list(mol.vertices)) >= 2
	assert len(list(mol.edges)) >= 1
