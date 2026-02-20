"""Three-layer 2D coordinate generator for OASA molecules.

Thin re-export shim. The actual implementation lives in the coords_gen/
sub-package, split into one file per phase for maintainability.

Same interface as coords_generator: calculate_coords(mol, bond_length, force).
"""

from oasa.coords_gen import calculate as _calculate_mod


#============================================
def calculate_coords(mol, bond_length: float = 1.0, force: int = 0) -> None:
	"""Module-level convenience function matching coords_generator signature."""
	_calculate_mod.calculate_coords(mol, bond_length=bond_length, force=force)
