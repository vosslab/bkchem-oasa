"""Sugar code to SMILES conversion (Phase 6).

Converts parsed sugar codes into SMILES strings with stereochemistry
by algorithmically mapping Fischer projection stereocenters to SMILES
chirality annotations (@/@@) based on a fixed ring traversal order.
"""

# local repo modules
from oasa import sugar_code
from oasa.haworth import spec as haworth_spec


# Fischer token -> (Haworth direction of functional group, SMILES fragment)
# Direction is "down" or "up" for the non-H substituent in Haworth projection.
# From haworth/spec.py _STEREO_TO_LABELS: R -> (H_up, OH_down), L -> (OH_up, H_down).
_TOKEN_SUB_MAP = {
	"R": ("down", "O"),
	"L": ("up", "O"),
	"D": ("down", "O"),
	"d": (None, None),
	"a": ("down", "N"),
	"n": ("down", "NC(C)=O"),
	"p": ("down", "OP(=O)(O)O"),
	"P": ("up", "OP(=O)(O)O"),
	"f": ("down", "F"),
	"c": ("down", "C(=O)O"),
}

# Terminal token -> SMILES fragment for a single exocyclic carbon
_TERMINAL_SMILES = {
	"M": "CO",
	"d": "C",
	"c": "C(=O)O",
	"p": "COP(=O)(O)O",
	"P": "COP(=O)(O)O",
}


#============================================
def sugar_code_to_smiles(code_string: str, ring_type: str, anomeric: str) -> str:
	"""Convert sugar code + ring parameters to a SMILES string.

	Args:
		code_string: Sugar code string (e.g. "ARLRDM" for D-glucose).
		ring_type: Ring form, "pyranose" or "furanose".
		anomeric: Anomeric configuration, "alpha" or "beta".

	Returns:
		SMILES string with stereochemistry annotations.

	Raises:
		ValueError: If inputs are invalid or the sugar code cannot be converted.
	"""
	ring_text = str(ring_type).strip().lower()
	if ring_text not in ("pyranose", "furanose"):
		raise ValueError(f"Unsupported ring_type {ring_type!r}; expected pyranose or furanose")
	anomeric_text = str(anomeric).strip().lower()
	if anomeric_text not in ("alpha", "beta"):
		raise ValueError(f"Unsupported anomeric {anomeric!r}; expected alpha or beta")

	parsed = sugar_code.parse(code_string)

	# Only ALDO and KETO prefixes are supported
	prefix_rules = haworth_spec._RING_RULES.get(parsed.prefix)
	if prefix_rules is None:
		raise ValueError(
			f"sugar_code_to_smiles supports ALDO/KETO prefixes; "
			f"got prefix={parsed.prefix} (sugar_code={parsed.sugar_code})"
		)
	ring_rule = prefix_rules[ring_text]
	num_carbons = len(parsed.positions)
	min_carbons = ring_rule["min_carbons"]
	if num_carbons < min_carbons:
		raise ValueError(
			f"Sugar {parsed.sugar_code} has {num_carbons} carbons but "
			f"{ring_text} requires at least {min_carbons}"
		)
	if parsed.config not in ("DEXTER", "LAEVUS"):
		raise ValueError(
			f"Meso sugars cannot form chiral rings; got config={parsed.config} "
			f"(sugar_code={parsed.sugar_code})"
		)

	raw_smiles = _build_ring_smiles(parsed, ring_text, anomeric_text, ring_rule)
	return raw_smiles


#============================================
def _build_ring_smiles(
		parsed: sugar_code.ParsedSugarCode,
		ring_type: str,
		anomeric: str,
		ring_rule: dict) -> str:
	"""Build SMILES string with stereochemistry for a monosaccharide ring.

	Traversal order: anomeric_C -> ring_O -> closure_C -> ... -> anomeric_C+1.
	This produces a deterministic SMILES with the ring-open digit at the
	anomeric carbon and the ring-close digit at anomeric_C+1.
	"""
	anomeric_c = ring_rule["anomeric"]
	closure_c = ring_rule["closure"]
	num_carbons = len(parsed.positions)
	is_aldo = (parsed.prefix == "ALDO")
	is_d = (parsed.config == "DEXTER")
	post_chain_len = num_carbons - closure_c

	# Determine anomeric OH direction in Haworth projection
	anom_oh_dir = _anomeric_oh_direction(is_d, anomeric)

	# Ring traversal: anomeric, closure, closure-1, ..., anomeric+1
	traversal = [anomeric_c]
	for c in range(closure_c, anomeric_c, -1):
		traversal.append(c)

	parts = []
	for idx, carbon in enumerate(traversal):
		is_first = (idx == 0)
		is_second = (idx == 1)
		is_last = (idx == len(traversal) - 1)

		if is_first:
			# Anomeric carbon: OH before, ring digit, then ring O
			parts.append(_build_anomeric(parsed, anomeric_c, anom_oh_dir, is_aldo))
			parts.append("O")
			continue

		if is_second:
			# Closure carbon (first after ring O, "o_adjacent" position)
			parts.append(_build_closure(
				parsed, closure_c, post_chain_len, ring_type, is_d,
			))
			continue

		if is_last:
			# Ring-closure carbon (sub follows ring digit)
			token = parsed.positions[carbon - 1][0]
			parts.append(_build_ring_close(token, carbon, parsed))
			continue

		# Interior ring carbon (sub in branch before next carbon)
		token = parsed.positions[carbon - 1][0]
		parts.append(_build_interior(token, carbon, parsed))

	return "".join(parts)


#============================================
def _build_anomeric(
		parsed: sugar_code.ParsedSugarCode,
		anomeric_c: int,
		anom_oh_dir: str,
		is_aldo: bool) -> str:
	"""Build SMILES fragment for the anomeric carbon.

	Aldose C1: has H, pattern is O[C{chiral}H]1
	Ketose C2: no H, has C1 branch, pattern is O[C{chiral}]1(CO)
	"""
	if is_aldo:
		chiral = _chirality_marker(anom_oh_dir, "anomeric")
		return f"O[C{chiral}H]1"
	# Ketose anomeric: no explicit H, has pre-anomeric C1 branch
	pre_branch = _pre_anomeric_smiles(parsed, anomeric_c)
	chiral = _chirality_marker(anom_oh_dir, "anomeric_no_h")
	return f"O[C{chiral}]1({pre_branch})"


#============================================
def _build_closure(
		parsed: sugar_code.ParsedSugarCode,
		closure_c: int,
		post_chain_len: int,
		ring_type: str,
		is_d: bool) -> str:
	"""Build SMILES fragment for the closure carbon (first after ring O).

	The closure carbon's Fischer OH forms the ring oxygen bridge.
	Its chirality depends on the exocyclic chain direction, not the OH.
	With no exocyclic chain, the carbon has two H's and is achiral.
	"""
	if post_chain_len == 0:
		# No exocyclic chain: two H's, not a stereocenter
		return "C"
	# Exocyclic chain exists: carbon is chiral
	chain_dir = _chain_direction(parsed, ring_type, closure_c, post_chain_len, is_d)
	chain_smi = _chain_smiles(parsed, closure_c, post_chain_len)
	chiral = _chirality_marker(chain_dir, "o_adjacent")
	return f"[C{chiral}H]({chain_smi})"


#============================================
def _build_interior(
		token: str,
		carbon: int,
		parsed: sugar_code.ParsedSugarCode) -> str:
	"""Build SMILES fragment for an interior ring carbon (branch pattern)."""
	sub_dir, sub_smi = _resolve_carbon_sub(token, carbon, parsed)
	if sub_dir is None:
		# Achiral (deoxy): no substituent branch
		return "C"
	chiral = _chirality_marker(sub_dir, "interior")
	return f"[C{chiral}H]({sub_smi})"


#============================================
def _build_ring_close(
		token: str,
		carbon: int,
		parsed: sugar_code.ParsedSugarCode) -> str:
	"""Build SMILES fragment for the ring-closure carbon (last in traversal).

	The substituent follows the ring-closure digit, reversing the @/@@ sense.
	"""
	sub_dir, sub_smi = _resolve_carbon_sub(token, carbon, parsed)
	if sub_dir is None:
		# Achiral (deoxy)
		return "C1"
	chiral = _chirality_marker(sub_dir, "ring_close")
	return f"[C{chiral}H]1{sub_smi}"


#============================================
def _chirality_marker(sub_dir: str, pos_type: str) -> str:
	"""Return @ or @@ based on substituent direction and SMILES position type.

	The SMILES chirality depends on the atom's neighbor ordering, which
	differs by position in the ring traversal.

	Standard positions (anomeric with H, interior):
	  Neighbors: from_atom, H, substituent(branch), next_ring_atom
	  Rule: down -> @@, up -> @

	Reversed positions (o_adjacent, ring_close):
	  o_adjacent: from_atom is ring O (higher priority reverses handedness)
	  ring_close: substituent follows ring digit (ordering swap)
	  Rule: down -> @, up -> @@

	Ketose anomeric (no H): currently uses reversed mapping.
	"""
	if pos_type == "anomeric_no_h":
		# Ketose C2: neighbors are O_anom(from), C3(ring), C1(branch), O_ring(next)
		# C1 replaces H; C1 has higher CIP than H, reversing handedness
		is_reversed = True
	else:
		is_reversed = pos_type in ("o_adjacent", "ring_close")
	if sub_dir == "down":
		return "@" if is_reversed else "@@"
	# sub_dir == "up"
	return "@@" if is_reversed else "@"


#============================================
def _anomeric_oh_direction(is_d: bool, anomeric: str) -> str:
	"""Return Haworth direction for the anomeric OH.

	alpha-D -> down, beta-D -> up, alpha-L -> up, beta-L -> down.
	"""
	if is_d:
		return "down" if anomeric == "alpha" else "up"
	return "up" if anomeric == "alpha" else "down"


#============================================
def _resolve_carbon_sub(
		token: str,
		carbon: int,
		parsed: sugar_code.ParsedSugarCode) -> tuple:
	"""Resolve an interior/ring-close carbon token to (direction, smiles).

	Returns:
		Tuple of (direction_string, smiles_fragment) where direction is
		"up", "down", or None (achiral). smiles_fragment is None for achiral.
	"""
	if token in _TOKEN_SUB_MAP:
		return _TOKEN_SUB_MAP[token]
	if token.isdigit():
		# Footnote-defined substituent
		return _resolve_footnote_sub(carbon, parsed)
	raise ValueError(f"Unknown ring carbon token '{token}' at position {carbon}")


#============================================
def _resolve_footnote_sub(
		carbon: int,
		parsed: sugar_code.ParsedSugarCode) -> tuple:
	"""Resolve a footnote-defined substituent for SMILES."""
	left_key = f"{carbon}L"
	right_key = f"{carbon}R"
	# Side-qualified keys
	if left_key in parsed.footnotes or right_key in parsed.footnotes:
		left_val = parsed.footnotes.get(left_key, "H")
		right_val = parsed.footnotes.get(right_key, "H")
		# Right in Fischer = down in Haworth
		if right_val != "H" and left_val == "H":
			return ("down", _group_to_smiles(right_val))
		# Left in Fischer = up in Haworth
		if left_val != "H" and right_val == "H":
			return ("up", _group_to_smiles(left_val))
		# Both H
		if left_val == "H" and right_val == "H":
			return (None, None)
	# Plain key (non-chiral position)
	plain_key = str(carbon)
	if plain_key in parsed.footnotes:
		return ("down", _group_to_smiles(parsed.footnotes[plain_key]))
	return (None, None)


#============================================
def _group_to_smiles(group_name: str) -> str:
	"""Convert a functional group name to a SMILES fragment."""
	upper = (group_name or "").upper().strip()
	mapping = {
		"OH": "O",
		"O": "O",
		"NH2": "N",
		"NHAC": "NC(C)=O",
		"F": "F",
		"OPO3": "OP(=O)(O)O",
		"PHOSPHATE": "OP(=O)(O)O",
		"COOH": "C(=O)O",
		"COO-": "C(=O)O",
		"CH2OH": "CO",
		"CH3": "C",
		"METHYL": "C",
		"H": "",
	}
	if upper in mapping:
		return mapping[upper]
	return group_name


#============================================
def _pre_anomeric_smiles(
		parsed: sugar_code.ParsedSugarCode,
		anomeric_c: int) -> str:
	"""Return SMILES for the pre-anomeric branch in ketoses.

	For KETO prefix, C1 is an exocyclic CH2OH branch on C2.
	"""
	# C1 is always position 0 (token 'M' = hydroxymethyl)
	c1_token = parsed.positions[0][0]
	if c1_token == "M":
		return "CO"
	# Fallback
	return "CO"


#============================================
def _chain_direction(
		parsed: sugar_code.ParsedSugarCode,
		ring_type: str,
		closure_c: int,
		post_chain_len: int,
		is_d: bool) -> str:
	"""Return Haworth direction for the exocyclic chain on the closure carbon.

	The closure carbon's Fischer OH forms the ring oxygen. The exocyclic
	chain goes on the opposite face from where the OH would have been.
	"""
	closure_token = parsed.positions[closure_c - 1][0]
	# Use closure carbon's own Fischer direction
	if closure_token in _TOKEN_SUB_MAP:
		sub_dir, _ = _TOKEN_SUB_MAP[closure_token]
		if sub_dir is not None:
			# Chain goes opposite the OH direction
			return "up" if sub_dir == "down" else "down"
	# Fallback to D/L config
	return "up" if is_d else "down"


#============================================
def _chain_smiles(
		parsed: sugar_code.ParsedSugarCode,
		closure_c: int,
		post_chain_len: int) -> str:
	"""Return SMILES fragment for the exocyclic chain from closure carbon."""
	if post_chain_len == 1:
		# Single exocyclic carbon (e.g. CH2OH for terminal M)
		terminal_token = parsed.positions[-1][0]
		return _TERMINAL_SMILES.get(terminal_token, "CO")
	if post_chain_len == 2:
		# Two exocyclic carbons (heptoses in pyranose, hexoses in furanose)
		return _two_carbon_chain_smiles(parsed, closure_c)
	if post_chain_len == 3:
		# Three exocyclic carbons (heptoses in furanose)
		return _three_carbon_chain_smiles(parsed, closure_c)
	raise ValueError(
		f"Unsupported exocyclic chain length {post_chain_len} "
		f"for closure carbon C{closure_c}"
	)


#============================================
def _two_carbon_chain_smiles(
		parsed: sugar_code.ParsedSugarCode,
		closure_c: int) -> str:
	"""Build SMILES for a 2-carbon exocyclic chain (e.g. -CH(OH)-CH2OH)."""
	# The first exocyclic carbon (closure_c+1)
	c_next = closure_c + 1
	c_next_token = parsed.positions[c_next - 1][0]
	sub_dir, sub_smi = _resolve_carbon_sub(c_next_token, c_next, parsed)
	# Terminal carbon (closure_c+2)
	terminal_token = parsed.positions[-1][0]
	terminal_smi = _TERMINAL_SMILES.get(terminal_token, "CO")
	if sub_dir is not None:
		# Chiral exocyclic carbon (branch pattern, same as interior)
		chiral = _chirality_marker(sub_dir, "interior")
		return f"[C{chiral}H]({sub_smi}){terminal_smi}"
	# Achiral exocyclic carbon
	return f"C{terminal_smi}"


#============================================
def _three_carbon_chain_smiles(
		parsed: sugar_code.ParsedSugarCode,
		closure_c: int) -> str:
	"""Build SMILES for a 3-carbon exocyclic chain (heptose furanose)."""
	# First exocyclic carbon (closure_c+1)
	c1_idx = closure_c + 1
	c1_token = parsed.positions[c1_idx - 1][0]
	c1_dir, c1_smi = _resolve_carbon_sub(c1_token, c1_idx, parsed)
	# Second exocyclic carbon (closure_c+2)
	c2_idx = closure_c + 2
	c2_token = parsed.positions[c2_idx - 1][0]
	c2_dir, c2_smi = _resolve_carbon_sub(c2_token, c2_idx, parsed)
	# Terminal carbon
	terminal_token = parsed.positions[-1][0]
	terminal_smi = _TERMINAL_SMILES.get(terminal_token, "CO")
	# Build chain with chirality at each chiral carbon
	parts = []
	if c1_dir is not None:
		chiral = _chirality_marker(c1_dir, "interior")
		parts.append(f"[C{chiral}H]({c1_smi})")
	else:
		parts.append("C")
	if c2_dir is not None:
		chiral = _chirality_marker(c2_dir, "interior")
		parts.append(f"[C{chiral}H]({c2_smi})")
	else:
		parts.append("C")
	parts.append(terminal_smi)
	return "".join(parts)
