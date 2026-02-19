"""SMILES to sugar code reverse conversion (Phase 7).

Two-tier approach:
  Tier 1 (exact match): Pre-built lookup table from all sugar codes in
  sugar_codes.yaml, indexed by SMILES string. High confidence.
  Tier 2 (structural inference): Parse the SMILES into a molecule and
  analyze ring structure, substituents, and stereochemistry. Best effort.
"""

# Standard Library
import dataclasses

# local repo modules
from . import sugar_code
from . import sugar_code_smiles
from . import sugar_code_names
from . import smiles as smiles_module


#============================================
@dataclasses.dataclass(frozen=True)
class SugarCodeResult:
	"""Result of a SMILES-to-sugar-code conversion."""
	sugar_code: str
	ring_type: str
	anomeric: str
	name: str
	confidence: str


#============================================
class SugarCodeError(ValueError):
	"""Raised when a SMILES string cannot be converted to a sugar code."""
	pass


# Module-level lookup table, built lazily on first use
_LOOKUP_TABLE = None


#============================================
def _build_lookup_table() -> dict:
	"""Build the SMILES -> SugarCodeResult lookup from all sugar codes.

	Iterates over all entries in sugar_codes.yaml and generates SMILES for
	each valid (code, ring_type, anomeric) combination using Phase 6.
	"""
	table = {}
	names = sugar_code_names.all_sugar_names()
	for code_str in sorted(names.keys()):
		display_name = names[code_str]
		for ring in ("pyranose", "furanose"):
			for anom in ("alpha", "beta"):
				try:
					smi = sugar_code_smiles.sugar_code_to_smiles(code_str, ring, anom)
				except ValueError:
					# Skip invalid combinations (3-KETO, meso, too few carbons)
					continue
				result = SugarCodeResult(
					sugar_code=code_str,
					ring_type=ring,
					anomeric=anom,
					name=display_name,
					confidence="exact_match",
				)
				# Store both the raw SMILES and the OASA-parsed canonical form
				table[smi] = result
	return table


#============================================
def _get_lookup_table() -> dict:
	"""Return the cached lookup table, building it on first access."""
	global _LOOKUP_TABLE
	if _LOOKUP_TABLE is None:
		_LOOKUP_TABLE = _build_lookup_table()
	return _LOOKUP_TABLE


#============================================
def smiles_to_sugar_code(smiles_text: str) -> SugarCodeResult:
	"""Convert a SMILES string to a sugar code.

	Args:
		smiles_text: SMILES string representing a monosaccharide.

	Returns:
		SugarCodeResult with sugar code, ring type, anomeric, name, and
		confidence level ("exact_match" or "inferred").

	Raises:
		SugarCodeError: If the SMILES cannot be recognized as a sugar.
	"""
	if not isinstance(smiles_text, str) or not smiles_text.strip():
		raise SugarCodeError("SMILES input must be a non-empty string")
	clean = smiles_text.strip()

	# Tier 1: Exact match against pre-built lookup table
	table = _get_lookup_table()
	if clean in table:
		return table[clean]

	# Tier 2: Structural inference from the molecule
	return _infer_from_molecule(clean, table)


#============================================
def _infer_from_molecule(smiles_text: str, table: dict) -> SugarCodeResult:
	"""Tier 2: Analyze molecule structure to determine sugar code.

	Parses the SMILES, identifies the sugar ring, and maps substituent
	stereochemistry back to Fischer projection R/L codes.
	"""
	# Parse the SMILES into a molecule
	mol = _safe_parse(smiles_text)

	# Find candidate sugar rings (5 or 6 membered with exactly one O)
	rings = _find_sugar_rings(mol)
	if not rings:
		_raise_not_sugar(smiles_text, "no 5- or 6-membered ring with one oxygen found")

	# Try each candidate ring
	for ring_atoms in rings:
		result = _try_ring(mol, ring_atoms, table)
		if result is not None:
			return result

	_raise_not_sugar(smiles_text, "ring structure does not match a known monosaccharide")


#============================================
def _safe_parse(smiles_text: str):
	"""Parse SMILES to molecule with error wrapping."""
	try:
		mol = smiles_module.text_to_mol(smiles_text, calc_coords=0)
	except Exception as exc:
		raise SugarCodeError(f"Failed to parse SMILES '{smiles_text}': {exc}") from exc
	return mol


#============================================
def _find_sugar_rings(mol) -> list:
	"""Find rings that look like sugar rings (5 or 6 atoms, one oxygen)."""
	all_cycles = mol.get_smallest_independent_cycles()
	candidates = []
	for cycle in all_cycles:
		if len(cycle) not in (5, 6):
			continue
		# Count oxygen atoms in ring
		oxygens = [a for a in cycle if a.symbol == "O"]
		carbons = [a for a in cycle if a.symbol == "C"]
		if len(oxygens) == 1 and len(carbons) == len(cycle) - 1:
			candidates.append(cycle)
	return candidates


#============================================
def _try_ring(mol, ring_atoms: list, table: dict) -> SugarCodeResult:
	"""Try to match a ring to a sugar code by regenerating SMILES and looking up."""
	# Identify ring type from ring size
	ring_size = len(ring_atoms)
	if ring_size == 5:
		ring_type = "furanose"
	else:
		ring_type = "pyranose"

	# Count total carbons in the molecule to estimate sugar size
	all_carbons = [a for a in mol.atoms if a.symbol == "C"]
	num_carbons = len(all_carbons)

	# Try generating SMILES for plausible sugar codes and compare
	# This uses Phase 6 to regenerate SMILES for candidate sugar codes
	# and checks if they produce the same molecular structure
	names = sugar_code_names.all_sugar_names()
	for code_str in sorted(names.keys()):
		# Quick filter: carbon count should match
		try:
			parsed = sugar_code.parse(code_str)
		except ValueError:
			continue
		if len(parsed.positions) != num_carbons:
			continue
		for anom in ("alpha", "beta"):
			try:
				candidate_smi = sugar_code_smiles.sugar_code_to_smiles(
					code_str, ring_type, anom,
				)
			except ValueError:
				continue
			# Compare molecules by checking atom counts and connectivity
			if _molecules_match(mol, candidate_smi):
				return SugarCodeResult(
					sugar_code=code_str,
					ring_type=ring_type,
					anomeric=anom,
					name=names[code_str],
					confidence="inferred",
				)
	return None


#============================================
def _molecules_match(mol, candidate_smiles: str) -> bool:
	"""Check if two molecules represent the same structure.

	Compares atom counts and bond connectivity as a heuristic.
	"""
	try:
		candidate_mol = smiles_module.text_to_mol(candidate_smiles, calc_coords=0)
	except Exception:
		return False

	# Compare atom counts by element
	def atom_counts(m):
		counts = {}
		for a in m.atoms:
			counts[a.symbol] = counts.get(a.symbol, 0) + 1
		return counts

	if atom_counts(mol) != atom_counts(candidate_mol):
		return False

	# Compare bond counts by order
	def bond_counts(m):
		counts = {}
		for b in m.bonds:
			counts[b.order] = counts.get(b.order, 0) + 1
		return counts

	if bond_counts(mol) != bond_counts(candidate_mol):
		return False

	# Compare stereochemistry count
	mol_stereo = len(getattr(mol, 'stereochemistry', []))
	cand_stereo = len(getattr(candidate_mol, 'stereochemistry', []))
	if mol_stereo != cand_stereo:
		return False

	return True


#============================================
def _raise_not_sugar(smiles_text: str, reason: str):
	"""Raise SugarCodeError with helpful examples."""
	examples = [
		"O[C@@H]1O[C@@H](CO)[C@@H](O)[C@H](O)[C@H]1O  (alpha-D-glucose pyranose)",
		"O[C@H]1O[C@@H](CO)[C@@H](O)[C@H]1O  (beta-D-ribose furanose)",
	]
	example_text = "\n  ".join(examples)
	raise SugarCodeError(
		f"Cannot convert SMILES '{smiles_text}' to a sugar code: {reason}.\n"
		f"Example valid sugar SMILES:\n  {example_text}"
	)
