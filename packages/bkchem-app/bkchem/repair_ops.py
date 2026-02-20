"""BKChem thin wrappers for OASA repair algorithms.

Each function handles selection, unit conversion, undo, and redraw.
All geometry algorithms live in oasa.repair_ops.
"""

# local repo modules
import oasa.repair_ops

from bkchem.singleton_store import Screen, Store


#============================================
def _get_target_molecules(paper) -> list:
	"""Return molecules to operate on: selected if any, else all.

	Args:
		paper: The BKChem paper (canvas) object.

	Returns:
		List of BKChem molecule objects.
	"""
	mols = paper.selected_mols
	if mols:
		Store.log(f"Repairing {len(mols)} selected molecule(s)")
		return mols
	mols = paper.molecules
	if mols:
		Store.log(f"Repairing all {len(mols)} molecule(s)")
	else:
		Store.log("No molecules on canvas")
	return mols


#============================================
def _get_bond_length_px(paper) -> float:
	"""Return the standard bond length in pixels.

	Args:
		paper: The BKChem paper object.

	Returns:
		Standard bond length in pixels.
	"""
	return Screen.any_to_px(paper.standard.bond_length)


#============================================
def normalize_bond_lengths(paper) -> None:
	"""Set all bonds to the standard bond length using BFS.

	Args:
		paper: The BKChem paper object.
	"""
	bond_length = _get_bond_length_px(paper)
	mols = _get_target_molecules(paper)
	for mol in mols:
		oasa.repair_ops.normalize_bond_lengths(mol, bond_length)
		mol.redraw(reposition_double=1)
	if mols:
		paper.start_new_undo_record()


#============================================
def normalize_bond_angles(paper) -> None:
	"""Round non-ring bond angles to nearest 60-degree multiple.

	Args:
		paper: The BKChem paper object.
	"""
	bond_length = _get_bond_length_px(paper)
	mols = _get_target_molecules(paper)
	for mol in mols:
		oasa.repair_ops.normalize_bond_angles(mol, bond_length)
		mol.redraw(reposition_double=1)
	if mols:
		paper.start_new_undo_record()


#============================================
def normalize_rings(paper) -> None:
	"""Reshape each ring to a regular polygon centered on its centroid.

	Args:
		paper: The BKChem paper object.
	"""
	bond_length = _get_bond_length_px(paper)
	mols = _get_target_molecules(paper)
	for mol in mols:
		oasa.repair_ops.normalize_rings(mol, bond_length)
		mol.redraw(reposition_double=1)
	if mols:
		paper.start_new_undo_record()


#============================================
def straighten_bonds(paper) -> None:
	"""Snap terminal and chain bond angles to nearest 30-degree direction.

	Args:
		paper: The BKChem paper object.
	"""
	mols = _get_target_molecules(paper)
	for mol in mols:
		oasa.repair_ops.straighten_bonds(mol)
		mol.redraw(reposition_double=1)
	if mols:
		paper.start_new_undo_record()


#============================================
def snap_to_hex_grid(paper) -> None:
	"""Move every atom to the nearest hex grid point.

	Args:
		paper: The BKChem paper object.
	"""
	bond_length = _get_bond_length_px(paper)
	mols = _get_target_molecules(paper)
	for mol in mols:
		oasa.repair_ops.snap_to_hex_grid(mol, bond_length)
		mol.redraw(reposition_double=1)
	if mols:
		paper.start_new_undo_record()


#============================================
def clean_geometry(paper) -> None:
	"""Full coordinate regeneration for molecules.

	If molecules are selected, delegates to paper.clean_selected().
	If nothing is selected, selects all molecules first, cleans,
	then restores the empty selection.

	Args:
		paper: The BKChem paper object.
	"""
	if paper.selected:
		paper.clean_selected()
	else:
		# select all atoms and bonds on every molecule, then clean
		all_items = []
		for mol in paper.molecules:
			all_items.extend(mol.atoms)
			all_items.extend(mol.bonds)
		if not all_items:
			Store.log("No molecules on canvas to clean")
			return
		paper.select(all_items)
		paper.clean_selected()
		paper.unselect_all()
	paper.start_new_undo_record()
