"""Unit coverage for CDML bond IO helpers."""

# local repo modules
import oasa.cdml_bond_io as cdml_bond_io


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
