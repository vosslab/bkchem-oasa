"""Smoke tests for parser+Haworth-spec generation matrix."""

# Third Party
import pytest

import oasa.haworth_spec as haworth_spec
import oasa.sugar_code as sugar_code


#============================================
def _build(code: str, ring_type: str, anomeric: str) -> haworth_spec.HaworthSpec:
	parsed = sugar_code.parse(code)
	return haworth_spec.generate(parsed, ring_type=ring_type, anomeric=anomeric)


#============================================
def test_haworth_spec_smoke_matrix():
	cases = [
		("ARLRDM", "pyranose"),
		("ARLRDM", "furanose"),
		("ARRDM", "pyranose"),
		("ARRDM", "furanose"),
		("ARDM", "furanose"),
		("MKLRDM", "pyranose"),
		("MKLRDM", "furanose"),
		("AdRDM", "furanose"),
	]
	for code, ring_type in cases:
		alpha = _build(code, ring_type, "alpha")
		beta = _build(code, ring_type, "beta")
		assert alpha.substituents
		assert beta.substituents
		anomeric_carbon = 1 if code.startswith("A") else 2
		up_key = f"C{anomeric_carbon}_up"
		down_key = f"C{anomeric_carbon}_down"
		assert alpha.substituents[up_key] != beta.substituents[up_key]
		assert alpha.substituents[down_key] != beta.substituents[down_key]


#============================================
@pytest.mark.parametrize("ring_type", ["furanose", "pyranose"])
def test_haworth_spec_smoke_meso_ring_capacity_error(ring_type):
	parsed = sugar_code.parse("MKM")
	with pytest.raises(ValueError) as error:
		haworth_spec.generate(parsed, ring_type=ring_type, anomeric="alpha")
	text = str(error.value)
	assert "ring_type" in text
	assert "KETO" in text
