"""Unit tests for Haworth spec generation."""

# Standard Library
import sys

# Third Party
import pytest

# Local repo modules
import conftest

sys.path.insert(0, conftest.repo_tests_path("fixtures"))

import oasa.haworth_spec as haworth_spec
import oasa.sugar_code as sugar_code
from archive_ground_truth import ARCHIVE_GROUND_TRUTH


#============================================
def _generate(code: str, ring_type: str, anomeric: str) -> haworth_spec.HaworthSpec:
	parsed = sugar_code.parse(code)
	return haworth_spec.generate(parsed, ring_type=ring_type, anomeric=anomeric)


#============================================
def test_standard_sanity_label_map_cases():
	"""Keep one compact sanity matrix for human spot-check expectations."""
	glucose_alpha = _generate("ARLRDM", "pyranose", "alpha")
	assert glucose_alpha.substituents["C1_down"] == "OH"
	assert glucose_alpha.substituents["C1_up"] == "H"

	glucose_beta = _generate("ARLRDM", "pyranose", "beta")
	assert glucose_beta.substituents["C1_up"] == "OH"
	assert glucose_beta.substituents["C1_down"] == "H"

	fructose_alpha = _generate("MKLRDM", "furanose", "alpha")
	fructose_beta = _generate("MKLRDM", "furanose", "beta")
	assert fructose_alpha.substituents["C2_up"] == "CH2OH"
	assert fructose_alpha.substituents["C2_down"] == "OH"
	assert fructose_beta.substituents["C2_up"] == "OH"
	assert fructose_beta.substituents["C2_down"] == "CH2OH"
	assert fructose_alpha.substituents["C2_up"] == fructose_beta.substituents["C2_down"]
	assert fructose_alpha.substituents["C2_down"] == fructose_beta.substituents["C2_up"]


#============================================
def test_glucose_alpha_pyranose():
	spec = _generate("ARLRDM", "pyranose", "alpha")
	assert spec.carbon_count == 5
	assert spec.substituents["C1_up"] == "H"
	assert spec.substituents["C1_down"] == "OH"
	assert spec.substituents["C2_down"] == "OH"
	assert spec.substituents["C3_up"] == "OH"
	assert spec.substituents["C5_up"] == "CH2OH"


#============================================
def test_glucose_beta_pyranose():
	spec = _generate("ARLRDM", "pyranose", "beta")
	assert spec.substituents["C1_up"] == "OH"
	assert spec.substituents["C1_down"] == "H"


#============================================
def test_galactose_alpha():
	spec = _generate("ARLLDM", "pyranose", "alpha")
	assert spec.substituents["C4_up"] == "OH"
	assert spec.substituents["C4_down"] == "H"


#============================================
def test_deoxyribose_furanose():
	spec = _generate("AdRDM", "furanose", "beta")
	assert spec.substituents["C1_up"] == "OH"
	assert spec.substituents["C2_up"] == "H"
	assert spec.substituents["C2_down"] == "H"
	assert spec.substituents["C4_up"] == "CH2OH"


#============================================
def test_fructose_beta_furanose():
	spec = _generate("MKLRDM", "furanose", "beta")
	assert spec.substituents["C2_up"] == "OH"
	assert spec.substituents["C2_down"] == "CH2OH"


#============================================
def test_fructose_alpha_furanose():
	spec = _generate("MKLRDM", "furanose", "alpha")
	assert spec.substituents["C2_up"] == "CH2OH"
	assert spec.substituents["C2_down"] == "OH"


#============================================
def test_fructose_anomeric_both_wide():
	spec = _generate("MKLRDM", "furanose", "beta")
	assert spec.substituents["C2_up"] != "H"
	assert spec.substituents["C2_down"] != "H"


#============================================
def test_triose_haworth_not_cyclizable():
	with pytest.raises(ValueError):
		_generate("ADM", "furanose", "alpha")
	with pytest.raises(ValueError):
		_generate("MKM", "pyranose", "alpha")


#============================================
def test_glucose_furanose():
	spec = _generate("ARLRDM", "furanose", "alpha")
	assert spec.carbon_count == 4
	assert spec.substituents["C4_up"] == "CH(OH)CH2OH"
	assert spec.substituents["C4_down"] == "H"


#============================================
def test_ribose_pyranose():
	spec = _generate("ARRDM", "pyranose", "alpha")
	assert spec.substituents["C5_up"] == "H"
	assert spec.substituents["C5_down"] == "H"


#============================================
def test_erythrose_furanose():
	spec = _generate("ARDM", "furanose", "beta")
	assert spec.substituents["C4_up"] == "H"
	assert spec.substituents["C4_down"] == "H"


#============================================
def test_fructose_pyranose():
	spec = _generate("MKLRDM", "pyranose", "beta")
	assert spec.substituents["C2_up"] == "OH"
	assert spec.substituents["C2_down"] == "CH2OH"
	assert spec.substituents["C6_up"] == "H"
	assert spec.substituents["C6_down"] == "H"


#============================================
def test_triose_ring_capacity_error():
	with pytest.raises(ValueError):
		_generate("MKM", "furanose", "beta")
	with pytest.raises(ValueError):
		_generate("MKM", "pyranose", "beta")


#============================================
def test_haworth_rejects_pathway_carbon_state():
	parsed = sugar_code.parse("c23[2C=C3(EPO3),3C=CH2]")
	with pytest.raises(ValueError) as error:
		haworth_spec.generate(parsed, ring_type="furanose", anomeric="alpha")
	assert "ineligible" in str(error.value).lower()


#============================================
def test_haworth_rejects_acyl_state_tokens():
	parsed = sugar_code.parse("A2M[2L=H,2R=C(=O)SCoA]")
	with pytest.raises(ValueError) as error:
		haworth_spec.generate(parsed, ring_type="furanose", anomeric="alpha")
	assert "ineligible" in str(error.value).lower()


#============================================
def test_exocyclic_0():
	spec = _generate("ARRDM", "pyranose", "beta")
	assert spec.substituents["C5_up"] == "H"
	assert spec.substituents["C5_down"] == "H"


#============================================
def test_exocyclic_1():
	spec = _generate("ARLRDM", "pyranose", "alpha")
	assert spec.substituents["C5_up"] == "CH2OH"
	assert spec.substituents["C5_down"] == "H"


#============================================
def test_exocyclic_2():
	spec = _generate("ARLRDM", "furanose", "alpha")
	assert spec.substituents["C4_up"] == "CH(OH)CH2OH"
	assert spec.substituents["C4_down"] == "H"


#============================================
@pytest.mark.parametrize("anomeric", ("alpha", "beta"))
def test_galactose_furanose_two_carbon_tail_points_down(anomeric):
	spec = _generate("ARLLDM", "furanose", anomeric)
	assert spec.substituents["C4_up"] == "H"
	assert spec.substituents["C4_down"] == "CH(OH)CH2OH"


#============================================
@pytest.mark.parametrize(
	"code,expected_up,expected_down",
	[
		("ARLRDM", "CH(OH)CH2OH", "H"),
		("ALLRDM", "CH(OH)CH2OH", "H"),
		("ARRLDM", "H", "CH(OH)CH2OH"),
		("ALRLDM", "H", "CH(OH)CH2OH"),
	],
)
def test_furanose_two_carbon_tail_tracks_closure_stereocenter(code, expected_up, expected_down):
	spec = _generate(code, "furanose", "alpha")
	assert spec.substituents["C4_up"] == expected_up
	assert spec.substituents["C4_down"] == expected_down


#============================================
@pytest.mark.parametrize("code", ("ALRRLd", "ARRLLd"))
@pytest.mark.parametrize("anomeric", ("alpha", "beta"))
def test_terminal_deoxy_pyranose_one_carbon_chain_renders_methyl(code, anomeric):
	spec = _generate(code, "pyranose", anomeric)
	assert spec.substituents["C5_down"] == "CH3"
	assert spec.substituents["C5_up"] == "H"
	assert "CH2OH" not in spec.substituents.values()


#============================================
def test_prefix_ring_mismatch():
	with pytest.raises(ValueError) as error:
		_generate("ARDM", "pyranose", "alpha")
	assert "minimum carbons" in str(error.value)


#============================================
# Parametrized ground-truth tests from NEUROtiker archive
#============================================

_GROUND_TRUTH_IDS = [
	f"{code}_{ring}_{anom}"
	for (code, ring, anom) in sorted(ARCHIVE_GROUND_TRUTH.keys())
]

_GROUND_TRUTH_PARAMS = sorted(ARCHIVE_GROUND_TRUTH.items())


@pytest.mark.parametrize(
	"key,expected_subs",
	_GROUND_TRUTH_PARAMS,
	ids=_GROUND_TRUTH_IDS,
)
def test_archive_ground_truth(key, expected_subs):
	"""Every substituent must match the manually verified ground truth."""
	code, ring_type, anomeric = key
	spec = _generate(code, ring_type, anomeric)
	for label_key, expected_value in expected_subs.items():
		actual = spec.substituents.get(label_key, "MISSING")
		assert actual == expected_value, (
			f"{code} {ring_type} {anomeric}: {label_key} "
			f"expected {expected_value!r}, got {actual!r}"
		)
