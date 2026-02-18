"""Unit tests for smiles_to_sugar_code Phase 7 reverse conversions."""

# Third Party
import pytest

import oasa.smiles_to_sugar_code as smiles_to_sugar_code
import oasa.sugar_code_smiles as sugar_code_smiles
import oasa.sugar_code_names as sugar_code_names


# ============================================
# Tier 1: Exact match from known SMILES
# ============================================

#============================================
def test_glucose_from_smiles():
	"""Alpha-D-glucose pyranose SMILES -> ARLRDM."""
	smi = "O[C@@H]1O[C@@H](CO)[C@@H](O)[C@H](O)[C@H]1O"
	result = smiles_to_sugar_code.smiles_to_sugar_code(smi)
	assert result.sugar_code == "ARLRDM"
	assert result.ring_type == "pyranose"
	assert result.anomeric == "alpha"
	assert result.confidence == "exact_match"
	assert "Glucose" in result.name


#============================================
def test_galactose_from_smiles():
	"""Alpha-D-galactose pyranose SMILES -> ARLLDM."""
	smi = sugar_code_smiles.sugar_code_to_smiles("ARLLDM", "pyranose", "alpha")
	result = smiles_to_sugar_code.smiles_to_sugar_code(smi)
	assert result.sugar_code == "ARLLDM"
	assert result.ring_type == "pyranose"
	assert result.anomeric == "alpha"


#============================================
def test_deoxyribose_from_smiles():
	"""Modified sugar (deoxyribose) is not in sugar_codes.yml lookup."""
	smi = sugar_code_smiles.sugar_code_to_smiles("AdRDM", "furanose", "beta")
	# Modified sugars are not in the YAML, so they raise SugarCodeError
	with pytest.raises(smiles_to_sugar_code.SugarCodeError):
		smiles_to_sugar_code.smiles_to_sugar_code(smi)


#============================================
def test_fructose_from_smiles():
	"""Beta-D-fructose furanose SMILES -> MKLRDM."""
	smi = sugar_code_smiles.sugar_code_to_smiles("MKLRDM", "furanose", "beta")
	result = smiles_to_sugar_code.smiles_to_sugar_code(smi)
	assert result.sugar_code == "MKLRDM"
	assert result.ring_type == "furanose"
	assert result.anomeric == "beta"
	assert "Fructose" in result.name


#============================================
def test_mannose_from_smiles():
	"""Alpha-D-mannose pyranose SMILES -> ALLRDM."""
	smi = sugar_code_smiles.sugar_code_to_smiles("ALLRDM", "pyranose", "alpha")
	result = smiles_to_sugar_code.smiles_to_sugar_code(smi)
	assert result.sugar_code == "ALLRDM"


#============================================
def test_ribose_from_smiles():
	"""Beta-D-ribose furanose SMILES -> ARRDM."""
	smi = sugar_code_smiles.sugar_code_to_smiles("ARRDM", "furanose", "beta")
	result = smiles_to_sugar_code.smiles_to_sugar_code(smi)
	assert result.sugar_code == "ARRDM"
	assert result.ring_type == "furanose"


# ============================================
# Round-trip tests
# ============================================

def _common_round_trip_codes():
	"""Return a list of common sugar codes for round-trip testing."""
	return [
		("ARLRDM", "pyranose", "alpha"),
		("ARLRDM", "pyranose", "beta"),
		("ARLLDM", "pyranose", "alpha"),
		("ALLRDM", "pyranose", "alpha"),
		("ARRRDM", "pyranose", "beta"),
		("ARRDM", "furanose", "beta"),
		("ARRDM", "pyranose", "alpha"),
		("ARDM", "furanose", "alpha"),
		("MKLRDM", "furanose", "beta"),
		("MKLRDM", "pyranose", "alpha"),
		("MKRDM", "furanose", "alpha"),
	]


@pytest.mark.parametrize("code,ring,anom", _common_round_trip_codes())
def test_round_trip_common(code, ring, anom):
	"""Common sugars round-trip: sugar code -> SMILES -> sugar code."""
	smi = sugar_code_smiles.sugar_code_to_smiles(code, ring, anom)
	result = smiles_to_sugar_code.smiles_to_sugar_code(smi)
	assert result.sugar_code == code
	assert result.ring_type == ring
	assert result.anomeric == anom


def _all_round_trip_combos():
	"""Generate all valid (code, ring, anomeric) combos for round-trip."""
	names = sugar_code_names.all_sugar_names()
	combos = []
	for code_str in sorted(names.keys()):
		for ring in ("pyranose", "furanose"):
			for anom in ("alpha", "beta"):
				combos.append((code_str, ring, anom))
	return combos


@pytest.mark.parametrize("code,ring,anom", _all_round_trip_combos())
def test_round_trip_all(code, ring, anom):
	"""All sugar codes round-trip through SMILES and back."""
	try:
		smi = sugar_code_smiles.sugar_code_to_smiles(code, ring, anom)
	except ValueError:
		# Expected for 3-KETO, meso, too few carbons
		return
	result = smiles_to_sugar_code.smiles_to_sugar_code(smi)
	assert result.sugar_code == code
	assert result.ring_type == ring
	assert result.anomeric == anom


# ============================================
# Error handling tests
# ============================================

#============================================
def test_unsupported_smiles_benzene():
	"""Benzene raises SugarCodeError."""
	with pytest.raises(smiles_to_sugar_code.SugarCodeError):
		smiles_to_sugar_code.smiles_to_sugar_code("c1ccccc1")


#============================================
def test_unsupported_smiles_ethanol():
	"""Ethanol raises SugarCodeError."""
	with pytest.raises(smiles_to_sugar_code.SugarCodeError):
		smiles_to_sugar_code.smiles_to_sugar_code("CCO")


#============================================
def test_empty_smiles_raises():
	"""Empty string raises SugarCodeError."""
	with pytest.raises(smiles_to_sugar_code.SugarCodeError):
		smiles_to_sugar_code.smiles_to_sugar_code("")


#============================================
def test_error_message_has_examples():
	"""Error messages include example valid sugar SMILES."""
	with pytest.raises(smiles_to_sugar_code.SugarCodeError) as exc_info:
		smiles_to_sugar_code.smiles_to_sugar_code("CCO")
	error_msg = str(exc_info.value)
	assert "Example" in error_msg
	assert "glucose" in error_msg.lower() or "C@@H" in error_msg


# ============================================
# Confidence level tests
# ============================================

#============================================
def test_exact_match_confidence():
	"""Tier 1 matches report exact_match confidence."""
	smi = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
	result = smiles_to_sugar_code.smiles_to_sugar_code(smi)
	assert result.confidence == "exact_match"


#============================================
def test_result_has_name():
	"""Results include the display name from sugar_codes.yml."""
	smi = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
	result = smiles_to_sugar_code.smiles_to_sugar_code(smi)
	assert result.name is not None
	assert len(result.name) > 0
