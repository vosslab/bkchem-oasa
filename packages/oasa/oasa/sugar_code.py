#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""Sugar code parsing helpers for Haworth schematic rendering."""

# Standard Library
import dataclasses
import re


#============================================
_FOOTNOTE_KEY_RE = re.compile(r"^([1-9])([LRC]?)$")
_CORE_PREFIX_RE = re.compile(r"^(A|MK|M[RL]K)")
_KNOWN_LETTER_CODES = {
	"d": ("deoxy",),
	"a": ("amino",),
	"n": ("n-acetyl",),
	"p": ("phosphate",),
	"P": ("phosphate-left",),
	"f": ("fluoro",),
	"c": ("carboxyl",),
}
_TOKEN_MEANINGS = {
	"A": ("aldehyde",),
	"K": ("keto",),
	"R": ("right",),
	"L": ("left",),
	"D": ("dexter",),
	"M": ("hydroxymethyl",),
}
_PREFIX_KIND_MAP = {
	"A": "ALDO",
	"MK": "KETO",
	"MRK": "3-KETO",
	"MLK": "3-KETO",
}


#============================================
@dataclasses.dataclass(frozen=True)
class ParsedSugarCode:
	prefix: str
	positions: list[tuple[str, tuple]]
	config: str
	terminal: tuple[str, tuple]
	footnotes: dict[str, str]
	sugar_code: str
	sugar_code_raw: str


#============================================
def parse(code_string: str) -> ParsedSugarCode:
	"""Parse a sugar code into normalized parser fields."""
	if not isinstance(code_string, str):
		raise ValueError("Sugar code must be a string")
	raw_input = code_string.strip()
	if not raw_input:
		raise ValueError("Sugar code must not be empty")
	body, footnotes_raw = _extract_footnotes(raw_input)
	if len(body) < 3:
		raise ValueError("Sugar code body must have at least 3 characters")
	if body in ("MRK", "MLK"):
		raise ValueError(f"Prefix-only sugar code is invalid: {body}")
	prefix_token, prefix_kind = _parse_prefix(body)
	_validate_body(body)
	footnotes = _validate_and_resolve_footnotes(body, footnotes_raw, prefix_token)
	positions, config, terminal = _parse_config_and_terminal(
		body,
		footnotes,
		prefix_token=prefix_token,
	)
	_validate_split_invariants(body, raw_input, bool(footnotes_raw))
	return ParsedSugarCode(
		prefix=prefix_kind,
		positions=positions,
		config=config,
		terminal=terminal,
		footnotes=footnotes,
		sugar_code=body,
		sugar_code_raw=raw_input,
	)


#============================================
def _extract_footnotes(s: str) -> tuple[str, dict[str, str]]:
	"""Return body and raw footnote mapping from one sugar-code string."""
	if "[" not in s:
		return s, {}
	open_index = s.find("[")
	if open_index <= 0:
		raise ValueError("Footnote block must follow a non-empty sugar code body")
	if not s.endswith("]"):
		raise ValueError("Footnote block must end with ']'")
	body = s[:open_index]
	block = s[open_index + 1:-1]
	if "[" in block or "]" in block:
		raise ValueError("Nested footnote blocks are not supported")
	entries = _split_footnote_entries(block)
	footnotes = {}
	last_index = 0
	for entry in entries:
		if "=" not in entry:
			raise ValueError(f"Invalid footnote entry '{entry}'")
		key, value = [part.strip() for part in entry.split("=", 1)]
		match = _FOOTNOTE_KEY_RE.match(key)
		if not match:
			raise ValueError(f"Invalid footnote key '{key}'")
		if not value:
			raise ValueError(f"Footnote '{key}' has an empty value")
		index = int(match.group(1))
		if index < last_index:
			raise ValueError("Footnote definitions must be in ascending index order")
		last_index = index
		if key in footnotes:
			raise ValueError(f"Duplicate footnote key '{key}'")
		footnotes[key] = value
	return body, footnotes


#============================================
def _split_footnote_entries(block: str) -> list[str]:
	"""Split a footnote body by top-level commas."""
	if not block.strip():
		return []
	parts = []
	current = []
	depth = 0
	for ch in block:
		if ch == "(":
			depth += 1
			current.append(ch)
			continue
		if ch == ")":
			depth -= 1
			if depth < 0:
				raise ValueError("Unbalanced ')' in footnote block")
			current.append(ch)
			continue
		if ch == "," and depth == 0:
			piece = "".join(current).strip()
			if not piece:
				raise ValueError("Empty footnote entry")
			parts.append(piece)
			current = []
			continue
		current.append(ch)
	if depth != 0:
		raise ValueError("Unbalanced '(' in footnote block")
	tail = "".join(current).strip()
	if tail:
		parts.append(tail)
	return parts


#============================================
def _parse_prefix(body: str) -> tuple[str, str]:
	"""Return literal prefix token and normalized prefix kind."""
	match = _CORE_PREFIX_RE.match(body)
	if match:
		token = match.group(1)
		return token, _PREFIX_KIND_MAP[token]
	if len(body) >= 3 and body[1] == "K":
		return "", "KETO"
	if len(body) >= 3 and body[2] == "K":
		return "", "3-KETO"
	return "", "ALDO"


#============================================
def _validate_body(body: str) -> None:
	"""Validate body-level token syntax and positional digit semantics."""
	for index, token in enumerate(body, start=1):
		if token.isdigit():
			if int(token) != index:
				raise ValueError(
					f"Digit '{token}' at backbone position {index} must equal the position index"
				)
			continue
		if token.islower():
			if token in _KNOWN_LETTER_CODES:
				continue
			raise ValueError(
				f"Unknown letter code '{token}' at backbone position {index}"
			)
		if token == "D" and index != len(body) - 1:
			raise ValueError("D token is only valid in the penultimate position")
		if token.isupper() and token in _TOKEN_MEANINGS:
			continue
		raise ValueError(f"Invalid sugar code token '{token}' at backbone position {index}")


#============================================
def _validate_and_resolve_footnotes(
		body: str,
		footnotes: dict[str, str],
		prefix_token: str) -> dict[str, str]:
	"""Validate raw footnote keys and return footnotes with side defaults."""
	digit_positions = _digit_positions(body)
	if not digit_positions and footnotes:
		raise ValueError("Footnotes were provided, but the body contains no digit markers")
	usage = {}
	for key, value in footnotes.items():
		index = int(key[0])
		if index not in digit_positions:
			raise ValueError(
				f"Footnote key '{key}' references backbone position {index}, "
				f"which is not a digit marker in '{body}'"
			)
		entry = usage.setdefault(
			index,
			{"plain": None, "carbon": None, "L": None, "R": None},
		)
		suffix = key[1:]
		if suffix == "":
			if entry["plain"] is not None:
				raise ValueError(f"Duplicate plain footnote key for index {index}")
			entry["plain"] = value
			continue
		if suffix == "C":
			if entry["carbon"] is not None:
				raise ValueError(f"Duplicate carbon-state footnote key for index {index}")
			entry["carbon"] = value
			continue
		if suffix in ("L", "R"):
			if entry[suffix] is not None:
				raise ValueError(f"Duplicate side footnote key '{key}'")
			entry[suffix] = value
			continue
		raise ValueError(f"Invalid footnote suffix in key '{key}'")
	for index in sorted(digit_positions):
		if index not in usage:
			raise ValueError(f"Digit marker {index} is missing a footnote definition")
	for index, entry in usage.items():
		has_plain = entry["plain"] is not None
		has_carbon = entry["carbon"] is not None
		has_side = (entry["L"] is not None) or (entry["R"] is not None)
		if has_plain and has_carbon:
			raise ValueError(
				f"Backbone position {index} cannot use both plain and carbon-state keys"
			)
		if (has_plain or has_carbon) and has_side:
			raise ValueError(
				f"Backbone position {index} cannot mix plain/carbon-state keys with side keys"
			)
		if has_plain and _is_chiral_position(index, body, prefix_token):
			raise ValueError(
				f"Plain key '{index}=...' is invalid at chiral backbone position {index}; "
				"use side-qualified keys or nC"
			)
	resolved = dict(footnotes)
	for index, entry in usage.items():
		if entry["L"] is not None and entry["R"] is None:
			resolved[f"{index}R"] = "H"
		if entry["R"] is not None and entry["L"] is None:
			resolved[f"{index}L"] = "H"
	return resolved


#============================================
def _digit_positions(body: str) -> set[int]:
	"""Collect backbone indices where the body carries a digit marker."""
	positions = set()
	for index, token in enumerate(body, start=1):
		if token.isdigit():
			positions.add(index)
	return positions


#============================================
def _is_chiral_position(index: int, body: str, prefix_token: str) -> bool:
	"""Return True when index is a chiral stereocenter in monosaccharide mode."""
	if index <= 0 or index >= len(body):
		return False
	if prefix_token == "A":
		return index >= 2 and index <= len(body) - 1
	if prefix_token == "MK":
		return index >= 3 and index <= len(body) - 1
	if prefix_token in ("MRK", "MLK"):
		if index == 2:
			return True
		return index >= 4 and index <= len(body) - 1
	return False


#============================================
def _parse_config_and_terminal(
		remainder: str,
		footnotes: dict[str, str],
		prefix_token: str = "") -> tuple[list[tuple[str, tuple]], str, tuple[str, tuple]]:
	"""Parse positional tokens and derive config + terminal metadata."""
	config_token = remainder[-2]
	if config_token == "D":
		config = "DEXTER"
	elif config_token == "L":
		config = "LAEVUS"
	elif prefix_token == "MK" and len(remainder) == 3:
		config = "MESO"
	elif prefix_token in ("MRK", "MLK") and len(remainder) == 5:
		# 3-keto meso: e.g. MRKRM has 5-char body, no D/L penultimate
		config = "MESO"
	elif prefix_token == "A" and len(remainder) == 3 and remainder[1].isdigit():
		config = "MESO"
	elif not prefix_token:
		config = "MESO"
	else:
		raise ValueError(
			"Missing D/L config token for monosaccharide-mode sugar code body"
		)
	terminal_index = len(remainder)
	terminal_token = remainder[-1]
	terminal = (terminal_token, _token_details(terminal_index, terminal_token, footnotes))
	positions = []
	for index, token in enumerate(remainder, start=1):
		positions.append((token, _token_details(index, token, footnotes)))
	return positions, config, terminal


#============================================
def _token_details(index: int, token: str, footnotes: dict[str, str]) -> tuple:
	"""Return normalized token details used by parser output."""
	if token.isdigit():
		parts = []
		plain_key = str(index)
		carbon_key = f"{index}C"
		left_key = f"{index}L"
		right_key = f"{index}R"
		if plain_key in footnotes:
			parts.append(f"plain={footnotes[plain_key]}")
		if carbon_key in footnotes:
			parts.append(f"carbon={footnotes[carbon_key]}")
		if left_key in footnotes:
			parts.append(f"L={footnotes[left_key]}")
		if right_key in footnotes:
			parts.append(f"R={footnotes[right_key]}")
		return tuple(parts)
	if token in _KNOWN_LETTER_CODES:
		return _KNOWN_LETTER_CODES[token]
	if token in _TOKEN_MEANINGS:
		return _TOKEN_MEANINGS[token]
	return ()


#============================================
def _validate_split_invariants(body: str, raw_input: str, has_footnotes: bool) -> None:
	"""Validate sugar_code/sugar_code_raw invariants."""
	if not has_footnotes:
		if raw_input != body:
			raise ValueError("Internal split invariant failed for sugar_code_raw")
		return
	if not raw_input.startswith(body):
		raise ValueError("Internal split invariant failed: raw input must start with body")
	suffix = raw_input[len(body):]
	if not (suffix.startswith("[") and suffix.endswith("]")):
		raise ValueError("Internal split invariant failed for footnote suffix")
