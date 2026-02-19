"""Smoke tests for sugar-code parser against curated sugar_codes.yaml."""

# Standard Library
import os

# PIP3 modules
import yaml

# local repo modules
import oasa.sugar_code as sugar_code


# path to the canonical sugar codes YAML shipped with oasa
_SUGAR_CODES_YML = os.path.join(
	os.path.dirname(__file__), '..', '..', 'oasa_data', 'sugar_codes.yaml',
)

# hand-picked strings that must raise ValueError
_INVALID_CODES = [
	"",
	"X",
	"ZZZ",
	"AAAA",
	"123",
	"arrdm",
]


#============================================
def _load_valid_codes() -> list:
	"""Extract every sugar code from sugar_codes.yaml.

	Returns:
		list of (code, common_name) tuples.
	"""
	with open(_SUGAR_CODES_YML, "r", encoding="utf-8") as handle:
		data = yaml.safe_load(handle)
	codes = []
	for group_name, entries in data.items():
		for code, name in entries.items():
			codes.append((code, name))
	return codes


#============================================
def test_all_yaml_codes_parse():
	"""Every code in sugar_codes.yaml should parse successfully."""
	codes = _load_valid_codes()
	# sanity: the YAML should have a reasonable number of sugars
	assert len(codes) >= 40, f"Expected 40+ codes, got {len(codes)}"
	for code, name in codes:
		parsed = sugar_code.parse(code)
		assert parsed.sugar_code_raw == code, (
			f"sugar_code_raw mismatch for {code} ({name})"
		)
		# codes without bracket modifiers should round-trip exactly
		if "[" not in code:
			assert parsed.sugar_code_raw == parsed.sugar_code, (
				f"sugar_code mismatch for {code} ({name})"
			)


#============================================
def test_invalid_codes_raise():
	"""Known-invalid codes must raise ValueError."""
	for code in _INVALID_CODES:
		try:
			sugar_code.parse(code)
		except ValueError:
			continue
		raise AssertionError(
			f"Expected ValueError for invalid code: {code!r}"
		)
