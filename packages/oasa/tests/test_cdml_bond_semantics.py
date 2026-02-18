"""Phase 1 CDML bond semantics checks."""

# local repo modules
import oasa


#============================================
def _make_cdml_text(bond_type):
	return (
		"<?xml version='1.0' encoding='utf-8'?>\n"
		"<cdml version=\"26.02\" xmlns=\"http://www.freesoftware.fsf.org/bkchem/cdml\">\n"
		"  <info>\n"
		"    <author_program version=\"26.02\">BKchem</author_program>\n"
		"    </info>\n"
		"  <paper crop_svg=\"0\" orientation=\"portrait\" type=\"A4\" />\n"
		"  <viewport viewport=\"0.000000 0.000000 640.000000 480.000000\" />\n"
		"  <standard area_color=\"#ffffff\" font_family=\"helvetica\" font_size=\"14\" "
		"line_color=\"#000\" line_width=\"2.0px\" paper_crop_svg=\"0\" "
		"paper_orientation=\"portrait\" paper_type=\"A4\">\n"
		"    <bond double-ratio=\"0.75\" length=\"1.0cm\" wedge-width=\"5.0px\" "
		"width=\"6.0px\" />\n"
		"    <arrow length=\"1.6cm\" />\n"
		"    </standard>\n"
		"  <molecule id=\"molecule1\" name=\"phase1\">\n"
		"    <atom id=\"atom_1\" name=\"C\">\n"
		"      <point x=\"1.000cm\" y=\"1.000cm\" />\n"
		"      </atom>\n"
		"    <atom id=\"atom_2\" name=\"C\">\n"
		"      <point x=\"2.000cm\" y=\"1.000cm\" />\n"
		"      </atom>\n"
		"    <bond double_ratio=\"0.75\" end=\"atom_2\" line_width=\"1.0\" "
		"start=\"atom_1\" type=\"%s\" />\n"
		"    </molecule>\n"
		"  </cdml>\n"
	) % bond_type


#============================================
def test_cdml_legacy_bond_type_normalization():
	text = _make_cdml_text("l1")
	mol = oasa.cdml.text_to_mol(text)
	assert mol is not None
	assert mol.edges
	bond = next(iter(mol.edges))
	assert bond.type == "h"
	assert bond.properties_.get("legacy_bond_type") == "l"


#============================================
def test_cdml_canonicalizes_wedge_vertices():
	text = _make_cdml_text("w1")
	mol = oasa.cdml.text_to_mol(text)
	assert mol is not None
	bond = next(iter(mol.edges))
	v1, v2 = bond.vertices
	assert v2.x >= v1.x


#============================================
def test_cdml_canonicalizes_hashed_vertices():
	text = _make_cdml_text("h1")
	mol = oasa.cdml.text_to_mol(text)
	assert mol is not None
	bond = next(iter(mol.edges))
	v1, v2 = bond.vertices
	assert v2.x >= v1.x
