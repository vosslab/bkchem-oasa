"""Unit coverage for CDML bond IO helpers."""

# local repo modules
import oasa
import oasa.cdml_bond_io as cdml_bond_io
import oasa.dom_extensions as dom_ext
import oasa.safe_xml as safe_xml


#============================================
def _make_cdml_text():
	return (
		"<?xml version='1.0' encoding='utf-8'?>\n"
		"<cdml version=\"26.02\" xmlns=\"http://www.freesoftware.fsf.org/bkchem/cdml\">\n"
		"  <molecule id=\"m1\">\n"
		"    <atom id=\"a1\" name=\"C\"><point x=\"1.0cm\" y=\"1.0cm\" /></atom>\n"
		"    <atom id=\"a2\" name=\"C\"><point x=\"2.0cm\" y=\"1.0cm\" /></atom>\n"
		"    <bond id=\"b1\" type=\"n1\" start=\"a1\" end=\"a2\" "
		"line_width=\"1.2\" color=\"#123456\" custom=\"keep\" />\n"
		"    </molecule>\n"
		"  </cdml>\n"
	)


#============================================
def test_read_cdml_bond_attributes_preserves_unknown():
	doc = safe_xml.parse_dom_from_string(_make_cdml_text())
	bond_el = dom_ext.simpleXPathSearch(doc, "//bond")[0]
	bond = oasa.bond(order=1, type="n")
	cdml_bond_io.read_cdml_bond_attributes(
		bond_el,
		bond,
		preserve_attrs={"line_width"},
	)
	assert bond.line_color == "#123456"
	assert bond.properties_.get("custom") == "keep"
	present = cdml_bond_io.get_cdml_present(bond)
	assert present is not None
	assert "line_width" in present
	assert "custom" in present


#============================================
def test_select_cdml_attributes_skips_defaults():
	values = {
		"line_width": "1.0",
		"color": "#000",
	}
	defaults = {
		"line_width": "1.0",
		"color": "#000",
	}
	present = {"line_width", "color"}
	selected = cdml_bond_io.select_cdml_attributes(values, defaults, present)
	assert selected == []


#============================================
def test_select_cdml_attributes_keeps_non_default():
	values = {
		"line_width": "2.0",
	}
	defaults = {
		"line_width": "1.0",
	}
	selected = cdml_bond_io.select_cdml_attributes(values, defaults, present=set())
	assert selected == [("line_width", "2.0")]
