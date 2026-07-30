"""Unit tests for sugar_code_to_smiles Phase 6 conversions."""

# Third Party
import pytest

import oasa.sugar_code_smiles as sugar_code_smiles
import oasa.sugar_code_names as sugar_code_names
import oasa.smiles_lib as oasa_smiles


# ============================================
# Canonical aldose reference tests
# ============================================

#============================================
def test_glucose_alpha_pyranose() -> None:
	"""Alpha-D-glucopyranose (ARLRDM) matches known reference SMILES."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
	assert text == "O[C@@H]1O[C@@H](CO)[C@@H](O)[C@H](O)[C@H]1O"


#============================================
def test_glucose_beta_pyranose() -> None:
	"""Beta-D-glucopyranose differs from alpha only at anomeric carbon."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "beta")
	# Only C1 chirality changes: @@ -> @
	assert text == "O[C@H]1O[C@@H](CO)[C@@H](O)[C@H](O)[C@H]1O"


#============================================
def test_galactose_alpha_pyranose() -> None:
	"""Alpha-D-galactopyranose (ARLLDM) differs from glucose at C4."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARLLDM", "pyranose", "alpha")
	# C4 changes from R(@@) to L(@)
	assert text == "O[C@@H]1O[C@@H](CO)[C@H](O)[C@H](O)[C@H]1O"


#============================================
def test_mannose_alpha_pyranose() -> None:
	"""Alpha-D-mannopyranose (ALLRDM) differs from glucose at C2."""
	text = sugar_code_smiles.sugar_code_to_smiles("ALLRDM", "pyranose", "alpha")
	# C2 changes from R(@) to L(@@)
	assert text == "O[C@@H]1O[C@@H](CO)[C@@H](O)[C@H](O)[C@@H]1O"


#============================================
def test_ribose_beta_furanose() -> None:
	"""Beta-D-ribofuranose (ARRDM)."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARRDM", "furanose", "beta")
	# Furanose ring C1-C2-C3-C4-O, C5 exocyclic
	assert text == "O[C@H]1O[C@@H](CO)[C@@H](O)[C@H]1O"


#============================================
def test_erythrose_alpha_furanose() -> None:
	"""Alpha-D-erythrofuranose (ARDM) - minimal 4-carbon aldofuranose."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARDM", "furanose", "alpha")
	# 4-carbon furanose: C4 closure has no exocyclic chain (achiral C)
	assert text == "O[C@@H]1OC[C@@H](O)[C@H]1O"


# ============================================
# Ketose reference tests
# ============================================

#============================================
def test_fructose_beta_furanose() -> None:
	"""Beta-D-fructofuranose (MKLRDM)."""
	text = sugar_code_smiles.sugar_code_to_smiles("MKLRDM", "furanose", "beta")
	# Ketofuranose: C2 anomeric (no H), C1 branch, ring C2-C3-C4-C5-O
	assert "O" in text
	assert "CO" in text
	# Verify it parses to a valid molecule
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	assert len(list(mol.atoms)) == 12


#============================================
def test_fructose_alpha_pyranose() -> None:
	"""Alpha-D-fructopyranose (MKLRDM)."""
	text = sugar_code_smiles.sugar_code_to_smiles("MKLRDM", "pyranose", "alpha")
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	assert len(list(mol.atoms)) == 12


# ============================================
# Ring type coverage
# ============================================

#============================================
def test_glucose_furanose() -> None:
	"""D-glucose in furanose form (6-carbon aldose in 5-ring)."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "furanose", "alpha")
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	# 6 carbons + 6 oxygens = 12 heavy atoms
	assert len(list(mol.atoms)) == 12


#============================================
def test_ribose_pyranose() -> None:
	"""D-ribose in pyranose form (5-carbon aldose in 6-ring)."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARRDM", "pyranose", "alpha")
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	# 5 carbons + 5 oxygens = 10 heavy atoms
	assert len(list(mol.atoms)) == 10


# ============================================
# L-series tests
# ============================================

#============================================
def test_l_glucose_alpha_pyranose() -> None:
	"""Alpha-L-glucopyranose (ALRLLM) - all chirality flipped from D."""
	text_l = sugar_code_smiles.sugar_code_to_smiles("ALRLLM", "pyranose", "alpha")
	text_d = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
	# L and D should produce different SMILES
	assert text_l != text_d
	# Both parse to 12 atoms
	mol_l = oasa_smiles.text_to_mol(text_l, calc_coords=0)
	mol_d = oasa_smiles.text_to_mol(text_d, calc_coords=0)
	assert len(list(mol_l.atoms)) == len(list(mol_d.atoms)) == 12


# ============================================
# Modification tests
# ============================================

#============================================
def test_deoxyribose_beta_furanose() -> None:
	"""Beta-D-2-deoxyribofuranose (AdRDM) - deoxy at C2."""
	text = sugar_code_smiles.sugar_code_to_smiles("AdRDM", "furanose", "beta")
	# C2 is deoxy (no OH, achiral) so C2 has no chirality marker
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	# 5C + 4O = 9 heavy atoms (one fewer O than ribose)
	assert len(list(mol.atoms)) == 9


#============================================
def test_glucosamine_alpha_pyranose() -> None:
	"""Alpha-D-glucosamine (AnLRDM) - amino at C2."""
	text = sugar_code_smiles.sugar_code_to_smiles("AnLRDM", "pyranose", "alpha")
	# Should have N in the SMILES
	assert "N" in text
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	n_atoms = len(list(mol.atoms))
	assert n_atoms >= 12


# ============================================
# Heptose tests
# ============================================

#============================================
def test_heptose_pyranose() -> None:
	"""D-glycero-D-gluco-heptose pyranose (ARLRRDM)."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARLRRDM", "pyranose", "alpha")
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	# 7 carbons + 7 oxygens = 14 heavy atoms
	assert len(list(mol.atoms)) == 14


#============================================
def test_heptose_furanose() -> None:
	"""D-glycero-D-gluco-heptose furanose (ARLRRDM)."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARLRRDM", "furanose", "alpha")
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	assert len(list(mol.atoms)) == 14


# ============================================
# Validation tests
# ============================================

#============================================
def test_invalid_ring_type_raises() -> None:
	with pytest.raises(ValueError) as error:
		sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "heptanose", "alpha")
	assert "ring_type" in str(error.value)


#============================================
def test_invalid_anomeric_raises() -> None:
	with pytest.raises(ValueError) as error:
		sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "gamma")
	assert "anomeric" in str(error.value)


#============================================
@pytest.mark.parametrize(
	"code,ring,formula",
	(
		("MRKLDM", "furanose", "C6H12O6"),
		("MLKLDM", "furanose", "C6H12O6"),
		("MRKLRDM", "pyranose", "C7H14O7"),
		("MLKLRDM", "pyranose", "C7H14O7"),
	),
)
def test_3keto_ring_forms_parse_with_complete_preanomeric_chain(
		code: str,
		ring: str,
		formula: str) -> None:
	"""3-ketose ring forms retain the C1--C2 pre-anomeric chain."""
	text = sugar_code_smiles.sugar_code_to_smiles(code, ring, "alpha")
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	assert str(mol.get_formula_dict()) == formula


#============================================
def test_3keto_prefix_and_anomeric_stereochemistry_differ() -> None:
	"""C2 prefix and anomeric configuration both remain stereochemical inputs."""
	r_alpha = sugar_code_smiles.sugar_code_to_smiles("MRKLRDM", "pyranose", "alpha")
	l_alpha = sugar_code_smiles.sugar_code_to_smiles("MLKLRDM", "pyranose", "alpha")
	r_beta = sugar_code_smiles.sugar_code_to_smiles("MRKLRDM", "pyranose", "beta")
	assert r_alpha != l_alpha
	assert r_alpha != r_beta


#============================================
def test_too_few_carbons_raises() -> None:
	"""Sugar with insufficient carbons for the requested ring raises."""
	# 4-carbon sugar in pyranose (needs 5)
	with pytest.raises(ValueError) as error:
		sugar_code_smiles.sugar_code_to_smiles("ARDM", "pyranose", "alpha")
	assert "carbons" in str(error.value)


#============================================
def test_ring_and_anomeric_case_normalized() -> None:
	"""Ring type and anomeric strings are case/whitespace normalized."""
	text = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", " Pyranose ", " Alpha ")
	assert text == "O[C@@H]1O[C@@H](CO)[C@@H](O)[C@H](O)[C@H]1O"


# ============================================
# Consistency and determinism
# ============================================

#============================================
def test_canonical_deterministic() -> None:
	"""Same input always produces the same output string."""
	result1 = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
	result2 = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
	assert result1 == result2


#============================================
def test_alpha_beta_differ() -> None:
	"""Alpha and beta of the same sugar produce different SMILES."""
	alpha = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "alpha")
	beta = sugar_code_smiles.sugar_code_to_smiles("ARLRDM", "pyranose", "beta")
	assert alpha != beta


# ============================================
# Full matrix smoke test
# ============================================

def _all_valid_combos() -> object:
	"""Generate (code, ring, anomeric) for all valid combinations."""
	names = sugar_code_names.all_sugar_names()
	combos = []
	for code in sorted(names.keys()):
		for ring in ("pyranose", "furanose"):
			for anom in ("alpha", "beta"):
				combos.append((code, ring, anom))
	return combos


@pytest.mark.parametrize("code,ring,anom", _all_valid_combos())
def test_smoke_matrix(code: object, ring: object, anom: object) -> None:
	"""Every valid sugar code x ring x anomeric produces parseable SMILES."""
	try:
		text = sugar_code_smiles.sugar_code_to_smiles(code, ring, anom)
	except ValueError:
		# Expected for meso forms or insufficient ring capacity
		return
	# Must be a non-empty string
	assert isinstance(text, str)
	assert len(text) > 0
	# Must parse as a valid molecule
	mol = oasa_smiles.text_to_mol(text, calc_coords=0)
	assert len(list(mol.atoms)) >= 5
