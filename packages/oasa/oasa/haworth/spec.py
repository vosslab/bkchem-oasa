#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Generate Haworth substituent specifications from parsed sugar codes."""

# Standard Library
import dataclasses
import re

# local repo modules
from oasa.sugar_code import ParsedSugarCode


#============================================
_RING_RULES = {
	"ALDO": {
		"furanose": {"anomeric": 1, "closure": 4, "min_carbons": 4},
		"pyranose": {"anomeric": 1, "closure": 5, "min_carbons": 5},
	},
	"KETO": {
		"furanose": {"anomeric": 2, "closure": 5, "min_carbons": 5},
		"pyranose": {"anomeric": 2, "closure": 6, "min_carbons": 6},
	},
	"3-KETO": {
		"furanose": {"anomeric": 3, "closure": 6, "min_carbons": 6},
		"pyranose": {"anomeric": 3, "closure": 7, "min_carbons": 7},
	},
}

_STEREO_TO_LABELS = {
	"R": ("H", "OH"),
	"L": ("OH", "H"),
	"D": ("H", "OH"),
	"d": ("H", "H"),
	"a": ("H", "NH2"),
	"n": ("H", "NHAc"),
	"p": ("H", "OPO3"),
	"P": ("OPO3", "H"),
	"f": ("H", "F"),
	"c": ("H", "COOH"),
}

_MODIFIER_LABELS = {
	"M": "CH2OH",
	"c": "COOH",
	"p": "OPO3",
	"P": "OPO3",
	"a": "NH2",
	"n": "NHAc",
	"f": "F",
	"d": "CH3",
}

_PATHWAY_DISALLOWED_VALUE_PATTERNS = [
	re.compile(r"C=\d+\([EZ]\)", re.IGNORECASE),
	re.compile(r"C=C", re.IGNORECASE),
	re.compile(r"EPO3", re.IGNORECASE),
	re.compile(r"C\(=O\)OPO3", re.IGNORECASE),
	re.compile(r"C\(=O\)SCOA", re.IGNORECASE),
]


#============================================
@dataclasses.dataclass(frozen=True)
class HaworthSpec:
	ring_type: str
	anomeric: str
	substituents: dict[str, str]
	carbon_count: int
	title: str


#============================================
def generate(
		parsed: ParsedSugarCode,
		ring_type: str,
		anomeric: str,
		) -> HaworthSpec:
	"""Generate ring-carbon up/down labels for Haworth rendering."""
	if ring_type not in ("pyranose", "furanose"):
		raise ValueError(f"Unsupported ring_type '{ring_type}'. Use 'pyranose' or 'furanose'.")
	if anomeric not in ("alpha", "beta"):
		raise ValueError(f"Unsupported anomeric '{anomeric}'. Use 'alpha' or 'beta'.")
	_ensure_haworth_eligible(parsed, ring_type=ring_type)
	ring_rule = _resolve_ring_rule(parsed, ring_type=ring_type)
	num_carbons = len(parsed.positions)
	min_carbons = ring_rule["min_carbons"]
	if num_carbons < min_carbons:
		raise ValueError(
			"Ring-capacity error for prefix=%s ring_type=%s: minimum carbons=%d, provided=%d "
			"(sugar_code=%s)"
			% (parsed.prefix, ring_type, min_carbons, num_carbons, parsed.sugar_code)
		)
	if parsed.config == "MESO":
		raise ValueError(
			"Ring-capacity error for prefix=%s ring_type=%s: meso forms are non-cyclizable "
			"in Phase 0 (sugar_code=%s)"
			% (parsed.prefix, ring_type, parsed.sugar_code)
		)
	if parsed.config not in ("DEXTER", "LAEVUS"):
		raise ValueError(f"Unsupported parser config '{parsed.config}' for Haworth generation.")
	anomeric_carbon = ring_rule["anomeric"]
	closure_carbon = ring_rule["closure"]
	ring_carbons = list(range(anomeric_carbon, closure_carbon + 1))
	substituents = {}
	for carbon in ring_carbons:
		substituents[f"C{carbon}_up"] = "H"
		substituents[f"C{carbon}_down"] = "H"

	# 1) anomeric OH orientation, including ketose pre-anomeric group.
	oh_dir = _anomeric_oh_direction(parsed.config, anomeric)
	if parsed.prefix == "3-KETO":
		# pre-anomeric chain is C1-C2 (2 carbons before anomeric C3)
		pre_chain = "CH(OH)CH2OH"
		_set_pair(
			substituents,
			anomeric_carbon,
			up_label="OH" if oh_dir == "up" else pre_chain,
			down_label="OH" if oh_dir == "down" else pre_chain,
		)
	elif parsed.prefix == "KETO":
		_set_pair(
			substituents,
			anomeric_carbon,
			up_label="OH" if oh_dir == "up" else "CH2OH",
			down_label="OH" if oh_dir == "down" else "CH2OH",
		)
	else:
		_set_pair(
			substituents,
			anomeric_carbon,
			up_label="OH" if oh_dir == "up" else "H",
			down_label="OH" if oh_dir == "down" else "H",
		)

	# 2) interior ring carbons: stereochemistry tokens resolve to up/down labels.
	for carbon in ring_carbons:
		if carbon in (anomeric_carbon, closure_carbon):
			continue
		token = parsed.positions[carbon - 1][0]
		up_label, down_label = _labels_for_ring_token(token, carbon, parsed.footnotes)
		_set_pair(substituents, carbon, up_label=up_label, down_label=down_label)

	# 3/4/5) closure carbon gets post-closure chain (or no chain).
	# For furanose two-carbon tails, use closure-carbon stereochemistry
	# (not anomeric state and not global D/L alone) to pick face.
	post_chain_len = num_carbons - closure_carbon
	chain_dir = _post_chain_direction(
		parsed,
		ring_type=ring_type,
		closure_carbon=closure_carbon,
		post_chain_len=post_chain_len,
	)
	chain_label = _post_chain_label(parsed, closure_carbon, post_chain_len)
	if chain_label is not None:
		if chain_dir == "up":
			_set_pair(substituents, closure_carbon, up_label=chain_label, down_label="H")
		else:
			_set_pair(substituents, closure_carbon, up_label="H", down_label=chain_label)
	else:
		# No exocyclic chain from closure carbon in this ring form.
		_set_pair(substituents, closure_carbon, up_label="H", down_label="H")

	series_letter = "D" if parsed.config == "DEXTER" else "L"
	title = f"{anomeric}-{series_letter}-{parsed.sugar_code}-{_ring_title(ring_type)}"
	carbon_count = 5 if ring_type == "pyranose" else 4
	return HaworthSpec(
		ring_type=ring_type,
		anomeric=anomeric,
		substituents=substituents,
		carbon_count=carbon_count,
		title=title,
	)


#============================================
def _resolve_ring_rule(parsed: ParsedSugarCode, ring_type: str) -> dict[str, int]:
	"""Resolve ring closure constants for the parsed prefix and ring type."""
	prefix_rules = _RING_RULES.get(parsed.prefix)
	if prefix_rules is None:
		raise ValueError(
			"Haworth Phase 0 supports prefixes A/MK/MRK/MLK only for conversion; "
			"got prefix=%s (sugar_code=%s)"
			% (parsed.prefix, parsed.sugar_code)
		)
	return prefix_rules[ring_type]


#============================================
def _ensure_haworth_eligible(parsed: ParsedSugarCode, ring_type: str) -> None:
	"""Reject pathway-profile chemistry that Phase 0 Haworth cannot represent."""
	carbon_state_keys = [key for key in sorted(parsed.footnotes) if key.endswith("C")]
	if carbon_state_keys:
		raise ValueError(
			"Haworth-ineligible sugar_code=%s ring_type=%s: carbon-state keys %s are not "
			"supported in Phase 0"
			% (parsed.sugar_code_raw, ring_type, ", ".join(carbon_state_keys))
		)
	bad_values = []
	for value in parsed.footnotes.values():
		for pattern in _PATHWAY_DISALLOWED_VALUE_PATTERNS:
			if pattern.search(value):
				bad_values.append(value)
				break
	if bad_values:
		unique = sorted(set(bad_values))
		raise ValueError(
			"Haworth-ineligible sugar_code=%s ring_type=%s: pathway carbon-state tokens "
			"not supported (%s)"
			% (parsed.sugar_code_raw, ring_type, ", ".join(unique))
		)


#============================================
def _anomeric_oh_direction(config: str, anomeric: str) -> str:
	"""Return up/down direction for anomeric OH after series inversion."""
	is_d_series = config == "DEXTER"
	if is_d_series:
		return "down" if anomeric == "alpha" else "up"
	return "up" if anomeric == "alpha" else "down"


#============================================
def _set_pair(
		substituents: dict[str, str],
		carbon: int,
		up_label: str,
		down_label: str) -> None:
	"""Write a carbon's up/down labels into the substitution table."""
	substituents[f"C{carbon}_up"] = up_label
	substituents[f"C{carbon}_down"] = down_label


#============================================
def _labels_for_ring_token(
		token: str,
		carbon: int,
		footnotes: dict[str, str],
		) -> tuple[str, str]:
	"""Resolve one ring carbon token into (up, down) labels."""
	if token.isdigit():
		return _labels_for_digit_marker(carbon, footnotes)
	if token in _STEREO_TO_LABELS:
		return _STEREO_TO_LABELS[token]
	# Non-stereocenter tokens inside ring default to implicit hydrogens.
	return ("H", "H")


#============================================
def _labels_for_digit_marker(carbon: int, footnotes: dict[str, str]) -> tuple[str, str]:
	"""Resolve one numeric marker using nL/nR or plain n definitions."""
	left_key = f"{carbon}L"
	right_key = f"{carbon}R"
	plain_key = str(carbon)
	if left_key in footnotes or right_key in footnotes:
		left_label = _normalize_group_label(footnotes.get(left_key, "H"))
		right_label = _normalize_group_label(footnotes.get(right_key, "H"))
		return (left_label, right_label)
	if plain_key in footnotes:
		return ("H", _normalize_group_label(footnotes[plain_key]))
	# Parser validation should prevent this for body digits.
	return ("H", "H")


#============================================
def _post_chain_label(parsed: ParsedSugarCode, closure_carbon: int, post_chain_len: int) -> str | None:
	"""Return the closure-carbon exocyclic label for chain lengths >= 1."""
	if post_chain_len <= 0:
		return None
	if post_chain_len == 1:
		terminal_carbon = len(parsed.positions)
		terminal_token = parsed.terminal[0]
		if terminal_token.isdigit():
			plain_key = str(terminal_carbon)
			left_key = f"{terminal_carbon}L"
			right_key = f"{terminal_carbon}R"
			if plain_key in parsed.footnotes:
				return _normalize_terminal_chain_label(parsed.footnotes[plain_key])
			if left_key in parsed.footnotes:
				return _normalize_terminal_chain_label(parsed.footnotes[left_key])
			if right_key in parsed.footnotes:
				return _normalize_terminal_chain_label(parsed.footnotes[right_key])
			return terminal_token
		return _normalize_terminal_chain_label(_MODIFIER_LABELS.get(terminal_token, terminal_token))
	# 2+ post-closure carbons are rendered as mini-chains in Phase 3.
	_ = closure_carbon
	if post_chain_len == 2:
		return "CH(OH)CH2OH"
	return f"CHAIN{post_chain_len}"


#============================================
def _post_chain_direction(
		parsed: ParsedSugarCode,
		ring_type: str,
		closure_carbon: int,
		post_chain_len: int) -> str:
	"""Return up/down direction for post-closure exocyclic chain."""
	default_dir = "up" if parsed.config == "DEXTER" else "down"
	if ring_type != "furanose" or post_chain_len != 2:
		return default_dir
	if not (1 <= closure_carbon <= len(parsed.positions)):
		return default_dir
	closure_token = parsed.positions[closure_carbon - 1][0]
	up_label, down_label = _labels_for_ring_token(closure_token, closure_carbon, parsed.footnotes)
	# Exocyclic chain replaces closure-carbon hydroxyl; use opposite face.
	if up_label != "H" and down_label == "H":
		return "down"
	if down_label != "H" and up_label == "H":
		return "up"
	return default_dir


#============================================
def _normalize_group_label(value: str) -> str:
	"""Normalize known substituent aliases to display labels."""
	text = (value or "").strip()
	upper = text.upper()
	if upper in ("H", "OH", "NH2", "NHAC", "F", "COOH", "COO-", "OPO3", "CH3", "CH2", "CH"):
		return upper if upper not in ("NHAC",) else "NHAc"
	if upper == "PHOSPHATE":
		return "OPO3"
	if upper == "SULFATE":
		return "SO4"
	if upper == "METHYL":
		return "CH3"
	if upper == "AMINO":
		return "NH2"
	if upper == "DEOXY":
		return "H"
	return text


#============================================
def _normalize_terminal_chain_label(value: str) -> str:
	"""Normalize one-carbon post-closure terminal labels with deoxy->methyl rule."""
	text = (value or "").strip()
	if text.lower() == "d" or text.upper() == "DEOXY":
		return "CH3"
	return _normalize_group_label(text)


#============================================
def _ring_title(ring_type: str) -> str:
	"""Return a title-cased ring family name."""
	if ring_type == "pyranose":
		return "Pyranose"
	return "Furanose"
