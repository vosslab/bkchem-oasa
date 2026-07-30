"""Scene query helpers for locating items and model objects.

Consolidates lookup helpers that were previously duplicated across
edit_mode.py, draw_mode.py, and context_menu.py into standalone
functions that take explicit view/scene parameters.
"""

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item


#============================================
def find_undo_stack(view: object) -> object:
	"""Locate the document's QUndoStack through the view.

	Args:
		view: The ChemView widget.

	Returns:
		QUndoStack or None if not accessible.
	"""
	if hasattr(view, "document") and view.document is not None:
		return view.document.undo_stack
	return None


#============================================
def find_molecule_for_atom(view: object, atom_model: object) -> object:
	"""Find the MoleculeModel that contains a given AtomModel.

	Args:
		view: The ChemView widget.
		atom_model: The AtomModel to search for.

	Returns:
		MoleculeModel or None.
	"""
	if not hasattr(view, "document") or view.document is None:
		return None
	for mol_model in view.document.molecules:
		if atom_model in mol_model.atoms:
			return mol_model
	return None


#============================================
def find_molecule_for_bond(view: object, bond_model: object) -> object:
	"""Find the MoleculeModel that contains a given BondModel.

	Args:
		view: The ChemView widget.
		bond_model: The BondModel to search for.

	Returns:
		MoleculeModel or None.
	"""
	if not hasattr(view, "document") or view.document is None:
		return None
	for mol_model in view.document.molecules:
		if bond_model in mol_model.bonds:
			return mol_model
	return None


#============================================
def find_connected_bond_items(scene: object, atom_model: object) -> list:
	"""Find all BondItems connected to an atom.

	Args:
		scene: The QGraphicsScene.
		atom_model: The AtomModel whose bonds to find.

	Returns:
		List of (BondModel, BondItem) tuples.
	"""
	if scene is None:
		return []
	connected = []
	for item in scene.items():
		if isinstance(item, bkchem_qt.canvas.items.bond_item.BondItem):
			bm = item.bond_model
			if bm.atom1 is atom_model or bm.atom2 is atom_model:
				connected.append((bm, item))
	return connected
