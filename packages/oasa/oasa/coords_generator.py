"""Coordinate generator for OASA molecules -- delegates to RDKit.

Public API matching the legacy coords_generator signature. All coordinate
generation is handled by RDKit's Compute2DCoords via rdkit_bridge.
"""

# Standard Library
import math

# local repo modules
from oasa import rdkit_bridge


#============================================
def _all_coords_set(mol) -> bool:
	"""Return True if every atom has non-None x and y."""
	for v in mol.vertices:
		if v.x is None or v.y is None:
			return False
	return True


#============================================
def _measure_avg_bond_length(mol) -> float:
	"""Compute average bond length from existing coordinates.

	Returns 1.0 if no bonds have both endpoints placed.
	"""
	total = 0.0
	count = 0
	for e in mol.edges:
		a1, a2 = e.vertices
		if a1.x is None or a1.y is None:
			continue
		if a2.x is None or a2.y is None:
			continue
		dx = a1.x - a2.x
		dy = a1.y - a2.y
		total += math.sqrt(dx * dx + dy * dy)
		count += 1
	if count == 0:
		return 1.0
	return total / count


#============================================
def calculate_coords(mol, bond_length: float = 0, force: int = 0) -> None:
	"""Generate 2D coordinates for an OASA molecule using RDKit.

	Drop-in replacement for the legacy coords_generator and coords_generator2
	interfaces. Delegates to rdkit_bridge.calculate_coords_rdkit().

	Args:
		mol: OASA molecule object (modified in place).
		bond_length: Target bond length for output coordinates.
			0 -> use default (1.0).
			-1 -> derive from existing coordinates.
			>0 -> use specified value.
		force: When 0, skip generation if all atoms already have coords.
			When 1, regenerate all coordinates unconditionally.
	"""
	# skip if all atoms already have coordinates and force is not set
	if not force and _all_coords_set(mol):
		return

	# resolve bond_length
	if bond_length == -1:
		bl = _measure_avg_bond_length(mol)
	elif bond_length <= 0:
		bl = 1.0
	else:
		bl = bond_length

	# delegate to RDKit
	rdkit_bridge.calculate_coords_rdkit(mol, bond_length=bl)

	# ensure z is set on all atoms
	for v in mol.vertices:
		if v.z is None:
			v.z = 0
