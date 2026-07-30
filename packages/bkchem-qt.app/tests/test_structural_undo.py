"""One structural graph-undo invariant."""

# PIP3 modules
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.canvas.items.atom_item
import bkchem_qt.canvas.items.bond_item
import bkchem_qt.models.atom_model
import bkchem_qt.models.bond_model
import bkchem_qt.models.document
import bkchem_qt.models.molecule_model
import bkchem_qt.undo.commands
import tests.graphics_test_retirement


#============================================
def test_remove_atom_undo_restores_bond_endpoints(
		qapp: PySide6.QtWidgets.QApplication,
		) -> None:
	"""Undo reconnects the original two atom wrappers to the retained bond."""
	document = bkchem_qt.models.document.Document()
	scene = PySide6.QtWidgets.QGraphicsScene()
	document.set_scene(scene)
	molecule = bkchem_qt.models.molecule_model.MoleculeModel()
	first = bkchem_qt.models.atom_model.AtomModel()
	second = bkchem_qt.models.atom_model.AtomModel()
	second.x = 100.0
	molecule.add_atom(first)
	molecule.add_atom(second)
	bond = bkchem_qt.models.bond_model.BondModel()
	molecule.add_bond(first, second, bond)
	first_item = bkchem_qt.canvas.items.atom_item.AtomItem(first)
	second_item = bkchem_qt.canvas.items.atom_item.AtomItem(second)
	bond_item = bkchem_qt.canvas.items.bond_item.BondItem(bond)
	with tests.graphics_test_retirement.bare_document_scene_retirement(qapp, document, scene):
		document.add_molecule(molecule, mark_dirty=False)
		for item in (first_item, second_item, bond_item):
			scene.addItem(item)
		document.undo_stack.push(bkchem_qt.undo.commands.RemoveAtomCommand(
			scene, molecule, first, first_item, [(bond, bond_item)],
		))
		document.undo_stack.undo()
		assert bond.atom1 is first and bond.atom2 is second
