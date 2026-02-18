"""Unit tests for sugar-code parser behavior."""

# Third Party
import pytest

import oasa.sugar_code as sugar_code


#============================================
def test_parse_simple_aldose():
	parsed = sugar_code.parse("ARLRDM")
	assert parsed.prefix == "ALDO"
	assert parsed.config == "DEXTER"
	assert parsed.terminal[0] == "M"
	assert parsed.sugar_code == "ARLRDM"
	assert parsed.sugar_code_raw == "ARLRDM"


#============================================
def test_parse_pentose():
	parsed = sugar_code.parse("ARRDM")
	assert parsed.prefix == "ALDO"
	assert parsed.config == "DEXTER"
	assert len(parsed.positions) == 5


#============================================
def test_parse_ketose():
	parsed = sugar_code.parse("MKLRDM")
	assert parsed.prefix == "KETO"
	assert parsed.config == "DEXTER"
	assert parsed.sugar_code == "MKLRDM"


#============================================
def test_parse_letter_code():
	parsed = sugar_code.parse("AdRDM")
	assert parsed.prefix == "ALDO"
	assert parsed.positions[1][0] == "d"
	assert parsed.positions[1][1] == ("deoxy",)


#============================================
def test_parse_with_footnotes():
	parsed = sugar_code.parse("A2LRDM[2R=CH3]")
	assert parsed.sugar_code == "A2LRDM"
	assert parsed.sugar_code_raw == "A2LRDM[2R=CH3]"
	assert parsed.footnotes["2R"] == "CH3"
	assert parsed.footnotes["2L"] == "H"


#============================================
def test_parse_raw_and_body_split():
	parsed = sugar_code.parse("A2LRDM[2R=CH3]")
	assert parsed.sugar_code == "A2LRDM"
	assert parsed.sugar_code_raw == "A2LRDM[2R=CH3]"
	assert parsed.sugar_code_raw.startswith(parsed.sugar_code)


#============================================
def test_parse_mixed():
	parsed = sugar_code.parse("AdLRD6[6=sulfate]")
	assert parsed.prefix == "ALDO"
	assert parsed.footnotes["6"] == "sulfate"
	assert parsed.terminal[0] == "6"


#============================================
def test_parse_meso_forms():
	parsed = sugar_code.parse("MKM")
	assert parsed.prefix == "KETO"
	assert parsed.config == "MESO"


#============================================
def test_parse_meso_modified_triose():
	parsed = sugar_code.parse("MKp")
	assert parsed.prefix == "KETO"
	assert parsed.config == "MESO"
	assert parsed.terminal[0] == "p"


#============================================
def test_parse_config_normalization():
	dexter = sugar_code.parse("ARLRDM")
	laevus = sugar_code.parse("ARLRLM")
	assert dexter.config == "DEXTER"
	assert laevus.config == "LAEVUS"


#============================================
def test_parse_numeric_pathway_override():
	parsed = sugar_code.parse("c23[2C=C3(EPO3),3C=CH2]")
	assert parsed.prefix == "ALDO"
	assert parsed.config == "MESO"
	assert parsed.footnotes["2C"] == "C3(EPO3)"
	assert parsed.footnotes["3C"] == "CH2"


#============================================
def test_parse_numeric_pathway_carbon_state():
	parsed = sugar_code.parse("c23[2C=C3(EPO3),3C=CH2]")
	assert "carbon=C3(EPO3)" in parsed.positions[1][1]
	assert "carbon=CH2" in parsed.positions[2][1]


#============================================
def test_parse_numeric_pathway_duplicate_index_invalid():
	with pytest.raises(ValueError):
		sugar_code.parse("c23[2=OH,2C=CH2,3C=CH2]")


#============================================
def test_parse_invalid_key_mix_same_index():
	with pytest.raises(ValueError):
		sugar_code.parse("A2M[2C=CH2,2L=OH]")


#============================================
def test_parse_compound_carbon_state_single_key():
	parsed = sugar_code.parse("c23[2C=C3(EPO3),3C=CH2]")
	assert parsed.footnotes["2C"] == "C3(EPO3)"
	with pytest.raises(ValueError):
		sugar_code.parse("c23[2C=C3(EPO3),2R=OH,3C=CH2]")


#============================================
def test_parse_side_qualified_footnotes():
	parsed = sugar_code.parse("A2M[2L=COOH,2R=CH3]")
	assert parsed.footnotes["2L"] == "COOH"
	assert parsed.footnotes["2R"] == "CH3"


#============================================
def test_parse_side_qualified_footnotes_single_defaults_h():
	parsed = sugar_code.parse("A2M[2L=OH]")
	assert parsed.footnotes["2L"] == "OH"
	assert parsed.footnotes["2R"] == "H"


#============================================
def test_parse_side_qualified_footnotes_single_defaults_h_right():
	parsed = sugar_code.parse("A2M[2R=OH]")
	assert parsed.footnotes["2R"] == "OH"
	assert parsed.footnotes["2L"] == "H"


#============================================
def test_parse_invalid_raises():
	with pytest.raises(ValueError):
		sugar_code.parse("ARLRMM")
	with pytest.raises(ValueError):
		sugar_code.parse("A2LRDM")
	with pytest.raises(ValueError):
		sugar_code.parse("A2LRDM[3=CH3]")


#============================================
def test_parse_invalid_digit_position():
	with pytest.raises(ValueError):
		sugar_code.parse("A1LRDM[1=CH3]")


#============================================
def test_parse_invalid_chiral_plain_key():
	with pytest.raises(ValueError):
		sugar_code.parse("A2LRDM[2=CH3]")


#============================================
def test_parse_too_short_invalid():
	with pytest.raises(ValueError):
		sugar_code.parse("A")
	with pytest.raises(ValueError):
		sugar_code.parse("MK")


#============================================
def test_parse_mrk_mlk_prefix_supported():
	mrk = sugar_code.parse("MRKDM")
	mlk = sugar_code.parse("MLKDM")
	assert mrk.prefix == "3-KETO"
	assert mlk.prefix == "3-KETO"
	assert mrk.config == "DEXTER"
	assert mlk.config == "DEXTER"


#============================================
def test_parse_prefix_only_invalid():
	with pytest.raises(ValueError):
		sugar_code.parse("MRK")
	with pytest.raises(ValueError):
		sugar_code.parse("MLK")


#============================================
def test_parse_unknown_letter_code_raises():
	with pytest.raises(ValueError) as error:
		sugar_code.parse("AzRDM")
	assert "z" in str(error.value)
	assert "position 2" in str(error.value)


#============================================
def test_parse_unknown_letter_code_uppercase_not_affected():
	parsed = sugar_code.parse("ARLRDM")
	assert parsed.config == "DEXTER"
	assert parsed.terminal[0] == "M"


#============================================
def test_parse_pathway_profile_haworth_ineligible_marker():
	parsed = sugar_code.parse("c23[2C=C3(EPO3),3C=CH2]")
	assert parsed.prefix == "ALDO"
	assert "2C" in parsed.footnotes
	assert "3C" in parsed.footnotes
